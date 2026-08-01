import pandas as pd

from app import db
from app.dashboard import process_water_point_data
from app.models import MaintenanceTask, User, WaterPoint
from app.services.water_point_service import (
    find_duplicate_groups,
    find_matching_water_point,
    merge_all_duplicates,
    merge_duplicate_group,
    normalize_point_id,
)
from tests.conftest import make_water_point


def _upload(df):
    process_water_point_data(df, "Bugesera", 1)


def test_normalize_point_id():
    assert normalize_point_id("  WP-001  ") == "WP-001"
    assert normalize_point_id("wp-001") == "WP-001"
    assert normalize_point_id("WP - 001") == "WP - 001"
    assert normalize_point_id(None) == ""
    assert normalize_point_id("") == ""


def test_find_matching_water_point_by_id_variant(app):
    with app.app_context():
        make_water_point(db, water_point_id="WP-001", district="Bugesera")
        match = find_matching_water_point(" wp-001 ", -2.15, 30.10, "Bugesera")
        assert match is not None
        assert match.water_point_id == "WP-001"


def test_find_matching_water_point_by_location(app):
    with app.app_context():
        make_water_point(db, water_point_id="WP-001", district="Bugesera")
        match = find_matching_water_point("TOTALLY-DIFFERENT-ID", -2.1500001, 30.1000001, "Bugesera")
        assert match is not None
        assert match.water_point_id == "WP-001"
        no_match = find_matching_water_point("TOTALLY-DIFFERENT-ID", -2.5, 30.5, "Bugesera")
        assert no_match is None


def test_upload_does_not_create_duplicates(app):
    with app.app_context():
        _upload(
            pd.DataFrame(
                [
                    {"water_point_id": "WP-100", "latitude": -2.15, "longitude": 30.10, "technology_type": "borehole"},
                    {"water_point_id": " wp-100 ", "latitude": -2.15, "longitude": 30.10, "technology_type": "borehole"},
                ]
            )
        )
        assert WaterPoint.query.count() == 1
        assert WaterPoint.query.first().water_point_id == "WP-100"


def test_upload_dedupes_identical_location_different_id(app):
    with app.app_context():
        _upload(
            pd.DataFrame(
                [
                    {"water_point_id": "A-1", "latitude": -2.15, "longitude": 30.10, "technology_type": "borehole"},
                    {"water_point_id": "A-2", "latitude": -2.15, "longitude": 30.10, "technology_type": "borehole"},
                ]
            )
        )
        assert WaterPoint.query.count() == 1


def test_find_duplicate_groups_detects_id_and_location(app):
    with app.app_context():
        make_water_point(db, water_point_id="WP-001", district="Bugesera")
        make_water_point(db, water_point_id="wp-001 ", district="Bugesera")
        for i, (lat, lng) in enumerate([(-2.10, 30.00), (-2.20, 30.20), (-2.30, 30.30)]):
            db.session.add(
                WaterPoint(
                    water_point_id=f"WP-00{i + 2}",
                    district="Bugesera",
                    latitude=lat,
                    longitude=lng,
                    technology_type="borehole",
                )
            )
        db.session.add(
            WaterPoint(
                water_point_id="WP-005",
                district="Bugesera",
                latitude=-2.40,
                longitude=30.40,
                technology_type="borehole",
            )
        )
        db.session.add(
            WaterPoint(
                water_point_id="WP-006",
                district="Bugesera",
                latitude=-2.40,
                longitude=30.40,
                technology_type="borehole",
            )
        )
        db.session.commit()

        groups = find_duplicate_groups()
        assert len(groups) == 2
        reasons = sorted(group["reason"] for group in groups)
        assert reasons == ["id", "location"]


def test_merge_all_duplicates_repoints_tasks(app):
    with app.app_context():
        admin = User(
            username="admin1",
            email="admin1@example.rw",
            full_name="Admin One",
            password_hash="x",
            role="admin",
            is_approved=True,
            is_active=True,
        )
        db.session.add(admin)
        db.session.commit()

        keep = make_water_point(db, water_point_id="WP-001", district="Bugesera")
        dup = make_water_point(db, water_point_id="wp-001", district="Bugesera")
        task = MaintenanceTask(
            water_point_id=dup.id,
            created_by_id=admin.id,
            title="Test task",
            description="x",
        )
        db.session.add(task)
        db.session.commit()
        task_id = task.id

        summary = merge_all_duplicates()
        assert summary["removed"] == 1
        assert summary["groups"] == 1
        assert WaterPoint.query.count() == 1
        moved = db.session.get(MaintenanceTask, task_id)
        assert moved.water_point_id == keep.id
        assert db.session.get(WaterPoint, dup.id) is None
