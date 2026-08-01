import re
from collections import defaultdict

from sqlalchemy import func

from app import db
from app.models import MaintenanceTask, WaterPoint

# Coordinates rounded to this many decimals are treated as the same physical
# location (~11 m). Precise enough to catch re-uploaded points whose GPS fixes
# differ slightly, loose enough to avoid merging genuinely distinct points.
COORD_ROUND = 4


def normalize_point_id(value):
    """Canonical form of a water point ID so 'WP-001', 'wp-001' and ' WP-001 '
    are recognised as the same physical point. Returns '' for empty values."""
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip().upper()


def _round_coords(latitude, longitude):
    return (round(latitude, COORD_ROUND), round(longitude, COORD_ROUND))


def find_matching_water_point(water_point_id, latitude, longitude, district):
    """Return the existing WaterPoint that `row` really is, or None.

    Matches by normalised water_point_id first (case/whitespace tolerant),
    then by rounded coordinates within the same district as a fallback for
    points whose IDs differ between uploads but sit at the same physical spot.
    """
    normalized = normalize_point_id(water_point_id)
    if normalized:
        candidates = (
            WaterPoint.query.filter(func.lower(WaterPoint.water_point_id) == normalized.lower()).all()
        )
        for candidate in candidates:
            if normalize_point_id(candidate.water_point_id) == normalized:
                return candidate

    if latitude is not None and longitude is not None:
        return (
            WaterPoint.query.filter_by(district=district)
            .filter(
                func.abs(WaterPoint.latitude - latitude) < 10 ** -COORD_ROUND,
                func.abs(WaterPoint.longitude - longitude) < 10 ** -COORD_ROUND,
            )
            .order_by(WaterPoint.id.asc())
            .first()
        )
    return None


def find_duplicate_groups():
    """Return groups of water points that refer to the same physical point.

    Two points are connected when they share a normalised ID or share the same
    rounded coordinates in the same district. Each returned group has at least
    two members, ordered by id, and is a connected component of those two
    relations so chained duplicates (A~B by id, B~C by location) collapse into
    one group.
    """
    points = WaterPoint.query.order_by(WaterPoint.id.asc()).all()
    if len(points) < 2:
        return []

    parent = {wp.id: wp.id for wp in points}

    def find(point_id):
        while parent[point_id] != point_id:
            parent[point_id] = parent[parent[point_id]]
            point_id = parent[point_id]
        return point_id

    def union(a, b):
        root_a, root_b = find(a), find(b)
        if root_a != root_b:
            parent[root_b] = root_a

    by_id = defaultdict(list)
    by_location = defaultdict(list)
    for wp in points:
        normalized = normalize_point_id(wp.water_point_id)
        if normalized:
            by_id[normalized].append(wp.id)
        if wp.latitude is not None and wp.longitude is not None:
            by_location[(wp.district or "", *_round_coords(wp.latitude, wp.longitude))].append(wp.id)

    for member_ids in by_id.values():
        if len(member_ids) > 1:
            for other in member_ids[1:]:
                union(member_ids[0], other)
    for member_ids in by_location.values():
        if len(member_ids) > 1:
            for other in member_ids[1:]:
                union(member_ids[0], other)

    components = defaultdict(list)
    for wp in points:
        components[find(wp.id)].append(wp)

    groups = []
    for members in components.values():
        if len(members) < 2:
            continue
        ordered = sorted(members, key=lambda wp: wp.id)
        groups.append({"reason": _group_reason(ordered), "points": ordered})
    groups.sort(key=lambda group: group["points"][0].id)
    return groups


def _group_reason(points):
    ids = {normalize_point_id(wp.water_point_id) for wp in points if wp.water_point_id}
    if len(ids) == 1:
        return "id"
    return "location"


_MERGE_FIELDS = (
    "district",
    "sector",
    "cell",
    "latitude",
    "longitude",
    "technology_type",
    "year_installed",
    "population_served",
    "depth",
    "current_status",
    "risk_probability",
    "prediction_confidence",
    "monthly_rainfall",
    "rainfall_month",
    "water_source_id",
)


def merge_duplicate_group(group):
    """Keep the earliest-created point, absorb any missing fields from the
    duplicates, re-point maintenance tasks at the survivor, and delete the
    extra rows. Returns (kept_point, removed_count). Caller commits."""
    points = group["points"]
    kept = points[0]
    for duplicate in points[1:]:
        for field in _MERGE_FIELDS:
            if getattr(kept, field) is None and getattr(duplicate, field) is not None:
                setattr(kept, field, getattr(duplicate, field))
        MaintenanceTask.query.filter_by(water_point_id=duplicate.id).update(
            {"water_point_id": kept.id}
        )
        db.session.delete(duplicate)
    return kept, len(points) - 1


def merge_all_duplicates():
    """Merge every detected duplicate group. Returns a summary dict for the
    caller (who commits and audits)."""
    groups = find_duplicate_groups()
    removed = 0
    for group in groups:
        _, removed_in_group = merge_duplicate_group(group)
        removed += removed_in_group
    return {"groups": len(groups), "removed": removed, "kept": len(groups)}
