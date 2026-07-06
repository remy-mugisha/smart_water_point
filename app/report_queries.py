"""Data-builder functions for the Reporting & Analytics module.

Each build_*_report() function is a pure function (no Flask request/response
handling) so it can be unit tested directly. Routes in app/reports.py just
parse query params, call these, and render/export the result.
"""
import math
from datetime import datetime

from flask_login import current_user
from sqlalchemy import case, func

from app.dashboard import scoped_water_points
from app.models import MaintenanceTask, User, WaterPoint

RISK_LOW_MAX = 0.33
RISK_MEDIUM_MAX = 0.66

REPORT_TITLES = {
    "status": "Water Point Status Report",
    "technician_performance": "Technician Performance Report",
    "maintenance": "Maintenance Report",
    "predictive_risk": "Predictive Risk Report",
    "district_summary": "District/Sector Summary Report",
}


class SimplePagination:
    """Paginates an already-fetched list, duck-typed to match Flask-SQLAlchemy's
    Pagination object so both can be rendered by the same template partial."""

    def __init__(self, items_all, page, per_page=25):
        self.page = max(1, page)
        self.per_page = per_page
        self.total = len(items_all)
        self.pages = max(1, math.ceil(self.total / per_page))
        start = (self.page - 1) * per_page
        self.items = items_all[start : start + per_page]
        self.has_prev = self.page > 1
        self.has_next = self.page < self.pages
        self.prev_num = self.page - 1
        self.next_num = self.page + 1


def parse_common_filters(args):
    return {
        "district": args.get("district") or None,
        "sector": args.get("sector") or None,
        "technician_id": args.get("technician_id", type=int),
        "status": args.get("status") or None,
        "technology_type": args.get("technology_type") or None,
        "risk_level": args.get("risk_level") or None,
        "group_by": args.get("group_by") or None,
        "date_from": _parse_date(args.get("date_from")),
        "date_to": _parse_date(args.get("date_to")),
    }


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None


def bucket_risk_level(probability):
    if probability is None:
        return None
    if probability < RISK_LOW_MAX:
        return "Low"
    if probability < RISK_MEDIUM_MAX:
        return "Medium"
    return "High"


def _scoped_maintenance_tasks_query():
    """District-scoped for managers/viewers, own-tasks-only for technicians, all for admin.

    Deliberately not the same as tasks.scoped_tasks(): that helper falls through
    to "assigned to me" for any non-admin/non-manager role, which is correct for
    the task worklist (viewers can't reach it, gated by @technician_required) but
    would silently show viewers an empty maintenance report instead of their
    district's data.
    """
    query = MaintenanceTask.query.join(WaterPoint)
    if current_user.role == "admin":
        return query
    if current_user.role == "district_technician":
        return query.filter(MaintenanceTask.assigned_to_id == current_user.id)
    return query.filter(WaterPoint.district == current_user.district)


def build_status_report(filters):
    query = scoped_water_points()
    if filters["district"]:
        query = query.filter(WaterPoint.district == filters["district"])
    if filters["sector"]:
        query = query.filter(WaterPoint.sector == filters["sector"])

    status_counts = dict(
        query.with_entities(WaterPoint.current_status, func.count(WaterPoint.id)).group_by(WaterPoint.current_status).all()
    )
    total = sum(status_counts.values())
    summary = {
        "total": total,
        "functional": status_counts.get("Functional", 0),
        "at_risk": status_counts.get("At Risk", 0),
        "under_repair": status_counts.get("Under Repair", 0),
        "non_functional": status_counts.get("Non-Functional", 0),
    }
    chart_data = {
        "labels": list(status_counts.keys()),
        "datasets": [{"label": "Water Points", "values": list(status_counts.values())}],
    }
    return {"summary": summary, "chart_data": chart_data}


def build_technician_performance_report(filters, page=1):
    query = User.query.filter_by(role="district_technician")
    if current_user.role == "district_technician":
        query = query.filter_by(id=current_user.id)
    elif current_user.role != "admin":
        query = query.filter_by(district=current_user.district)
    elif filters["district"]:
        query = query.filter_by(district=filters["district"])
    if filters["technician_id"]:
        query = query.filter_by(id=filters["technician_id"])

    technicians = query.order_by(User.full_name).all()

    rows = []
    for tech in technicians:
        tasks_q = MaintenanceTask.query.filter_by(assigned_to_id=tech.id)
        if filters["date_from"]:
            tasks_q = tasks_q.filter(MaintenanceTask.assigned_at >= filters["date_from"])
        if filters["date_to"]:
            tasks_q = tasks_q.filter(MaintenanceTask.assigned_at <= filters["date_to"])

        tasks = tasks_q.all()
        assigned_count = len(tasks)
        completed = [t for t in tasks if t.status in ("completed", "verified")]
        completed_count = len(completed)
        in_progress_count = assigned_count - completed_count
        completion_rate = round(completed_count / assigned_count * 100, 1) if assigned_count else 0.0

        resolution_hours = [
            (t.completed_at - t.assigned_at).total_seconds() / 3600
            for t in completed
            if t.completed_at and t.assigned_at
        ]
        avg_resolution_hours = round(sum(resolution_hours) / len(resolution_hours), 1) if resolution_hours else None

        rows.append(
            {
                "technician": tech.full_name,
                "district": tech.district,
                "assigned": assigned_count,
                "completed": completed_count,
                "in_progress": in_progress_count,
                "completion_rate": completion_rate,
                "avg_resolution_hours": avg_resolution_hours,
            }
        )

    chart_data = {
        "labels": [r["technician"] for r in rows],
        "datasets": [
            {"label": "Completed", "values": [r["completed"] for r in rows]},
            {"label": "In Progress", "values": [r["in_progress"] for r in rows]},
        ],
    }
    pagination = SimplePagination(rows, page)
    summary = {
        "total_technicians": len(rows),
        "total_assigned": sum(r["assigned"] for r in rows),
        "total_completed": sum(r["completed"] for r in rows),
    }
    return {"summary": summary, "chart_data": chart_data, "rows": pagination.items, "rows_all": rows, "pagination": pagination}


def build_maintenance_report(filters, page=1):
    query = _scoped_maintenance_tasks_query()
    if filters["district"]:
        query = query.filter(WaterPoint.district == filters["district"])
    if filters["sector"]:
        query = query.filter(WaterPoint.sector == filters["sector"])
    if filters["technician_id"]:
        query = query.filter(MaintenanceTask.assigned_to_id == filters["technician_id"])
    if filters["status"]:
        query = query.filter(MaintenanceTask.status == filters["status"])
    if filters["date_from"]:
        query = query.filter(MaintenanceTask.created_at >= filters["date_from"])
    if filters["date_to"]:
        query = query.filter(MaintenanceTask.created_at <= filters["date_to"])

    tasks = query.order_by(MaintenanceTask.created_at.desc()).all()
    rows_all = [
        {
            "water_point": t.water_point.water_point_id,
            "district": t.water_point.district,
            "issue": t.title,
            "technician": t.technician.full_name if t.technician else "Unassigned",
            "repair_date": t.completed_at,
            "status": t.status,
            "remarks": t.completion_notes or "",
        }
        for t in tasks
    ]

    summary = {
        "total": len(tasks),
        "completed": sum(1 for t in tasks if t.status in ("completed", "verified")),
        "in_progress": sum(1 for t in tasks if t.status in ("assigned", "accepted", "in_progress")),
        "pending": sum(1 for t in tasks if t.status == "pending"),
    }

    monthly = (
        query.with_entities(func.strftime("%Y-%m", MaintenanceTask.created_at).label("month"), func.count(MaintenanceTask.id))
        .group_by("month")
        .order_by("month")
        .all()
    )
    chart_data = {
        "labels": [m for m, _ in monthly],
        "datasets": [{"label": "Tasks Created", "values": [c for _, c in monthly]}],
    }

    pagination = SimplePagination(rows_all, page)
    return {"summary": summary, "chart_data": chart_data, "rows": pagination.items, "rows_all": rows_all, "pagination": pagination}


def build_predictive_risk_report(filters, page=1):
    query = scoped_water_points().filter(WaterPoint.last_prediction_date.isnot(None))
    if filters["district"]:
        query = query.filter(WaterPoint.district == filters["district"])
    if filters["sector"]:
        query = query.filter(WaterPoint.sector == filters["sector"])
    if filters["technology_type"]:
        query = query.filter(WaterPoint.technology_type == filters["technology_type"])

    water_points = query.order_by(WaterPoint.last_prediction_date.desc()).all()
    rows_all = []
    risk_counts = {"Low": 0, "Medium": 0, "High": 0}
    for wp in water_points:
        risk_level = bucket_risk_level(wp.risk_probability)
        if risk_level is None:
            continue
        if filters["risk_level"] and risk_level != filters["risk_level"]:
            continue
        risk_counts[risk_level] += 1
        rows_all.append(
            {
                "water_point_id": wp.water_point_id,
                "location": ", ".join(filter(None, [wp.cell, wp.sector, wp.district])),
                "technology_type": wp.technology_type,
                "risk_level": risk_level,
                "prediction_date": wp.last_prediction_date,
            }
        )

    chart_data = {"labels": list(risk_counts.keys()), "datasets": [{"label": "Water Points", "values": list(risk_counts.values())}]}
    pagination = SimplePagination(rows_all, page)
    summary = {"total": len(rows_all), **{k.lower(): v for k, v in risk_counts.items()}}
    return {"summary": summary, "chart_data": chart_data, "rows": pagination.items, "rows_all": rows_all, "pagination": pagination}


def build_district_summary_report(filters):
    group_by_sector = filters.get("group_by") == "sector"
    columns = [WaterPoint.district, WaterPoint.sector] if group_by_sector else [WaterPoint.district]

    query = scoped_water_points().with_entities(
        *columns,
        func.count(WaterPoint.id).label("total"),
        func.sum(case((WaterPoint.current_status == "Functional", 1), else_=0)).label("functional"),
        func.sum(case((WaterPoint.current_status == "At Risk", 1), else_=0)).label("at_risk"),
        func.sum(case((WaterPoint.current_status == "Under Repair", 1), else_=0)).label("maintenance_cases"),
    ).group_by(*columns)

    results = query.order_by(*columns).all()
    rows = []
    for r in results:
        row = {
            "district": r.district,
            "total": r.total,
            "functional": r.functional,
            "at_risk": r.at_risk,
            "maintenance_cases": r.maintenance_cases,
        }
        if group_by_sector:
            row["sector"] = r.sector
        rows.append(row)

    chart_data = {
        "labels": [f"{r['district']} / {r['sector']}" if group_by_sector else r["district"] for r in rows],
        "datasets": [{"label": "Total Water Points", "values": [r["total"] for r in rows]}],
    }
    summary = {
        "total_groups": len(rows),
        "total": sum(r["total"] for r in rows),
        "functional": sum(r["functional"] for r in rows),
        "at_risk": sum(r["at_risk"] for r in rows),
        "maintenance_cases": sum(r["maintenance_cases"] for r in rows),
    }
    return {"summary": summary, "chart_data": chart_data, "rows": rows, "group_by_sector": group_by_sector}


def build_monthly_repair_outcomes():
    """Chart #6 data source: 'Functional vs At Risk over time', derived from completed
    maintenance tasks since WaterPoint only stores current status, not history."""
    query = (
        _scoped_maintenance_tasks_query()
        .filter(MaintenanceTask.completed_at.isnot(None))
        .with_entities(
            func.strftime("%Y-%m", MaintenanceTask.completed_at).label("month"),
            MaintenanceTask.resulting_status,
            func.count(MaintenanceTask.id),
        )
        .group_by("month", MaintenanceTask.resulting_status)
        .order_by("month")
    )

    by_month = {}
    for month, resulting_status, count in query.all():
        bucket = by_month.setdefault(month, {"Functional": 0, "At Risk": 0})
        if resulting_status == "Functional":
            bucket["Functional"] += count
        else:
            bucket["At Risk"] += count

    months = sorted(by_month.keys())
    return {
        "labels": months,
        "datasets": [
            {"label": "Functional", "values": [by_month[m]["Functional"] for m in months]},
            {"label": "At Risk", "values": [by_month[m]["At Risk"] for m in months]},
        ],
    }
