import os
import sys
from collections import Counter, defaultdict

import openpyxl
from flask import current_app

from app import create_app, db
from app.models import WaterSource

WEIGHTS = {
    "electricity generation": 3.0,
    "electricity production": 3.0,
    "energy production": 3.0,
    "irrigation": 2.5,
    "irrigating the golf course": 2.5,
    "irrigation/domestic water supply": 2.5,
    "mining": 2.5,
    "mining activities": 2.5,
    "mining and quarrying": 2.5,
    "washing mineral ores": 2.5,
    "industrial": 2.0,
    "aquaculture using cages": 1.5,
    "aquaculture in fish ponds": 1.5,
    "coffee washing station": 1.5,
    "fish farming": 1.0,
    "domestic water supply": 1.0,
    "package bottle water plant": 1.2,
    "hotel activities": 0.8,
    "research": 0.5,
    "groundwater investigation": 0.3,
    "potable services and construction activities": 0.5,
}


def infer_source_type(name: str) -> str:
    n = name.lower()
    for keyword, label in [
        ("lake", "Lake"),
        ("river", "River"),
        ("stream", "Stream"),
        ("spring", "Spring"),
        ("dam", "Dam"),
        ("borehole", "Borehole"),
        ("well", "Borehole"),
        ("groundwater", "Groundwater"),
        ("pond", "Pond"),
    ]:
        if keyword in n:
            return label
    return "Other"


def normalize_key(name: str) -> str:
    return (name or "").strip().lower()


def import_rwb_sources(path: str = None):
    if path is None:
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "raw data", "rwanda_water_users.xlsx")

    wb = openpyxl.load_workbook(path)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))[1:]

    grouped = defaultdict(list)
    for r in rows:
        source_name = (r[2] or "").strip()
        grouped[normalize_key(source_name)].append({
            "display_name": source_name,
            "catchment": (r[1] or "").strip() or None,
            "usage_type": (r[3] or "").strip() or None,
        })

    imported = 0
    skipped = 0

    for norm_name, entries in grouped.items():
        display_names = [e["display_name"] for e in entries]
        display_name = sorted(set(display_names), key=len)[-1]  # pick longest/most complete
        if not display_name:
            skipped += 1
            continue

        catchments = [e["catchment"] for e in entries if e["catchment"]]
        catchment = Counter(catchments).most_common(1)[0][0] if catchments else None

        usage_types = sorted(set(e["usage_type"] for e in entries if e["usage_type"]))
        usage_types_text = " | ".join(usage_types)

        score = max(WEIGHTS.get(u.lower(), 0.0) for u in usage_types) if usage_types else 0.0

        source = WaterSource(
            name=display_name,
            catchment=catchment,
            source_type=infer_source_type(display_name),
            usage_types=usage_types_text,
            industrial_pressure_score=score,
        )
        db.session.add(source)
        imported += 1

    db.session.commit()
    print(f"Imported {imported} water sources. Skipped {skipped}.")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        import_rwb_sources()
