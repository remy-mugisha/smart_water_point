import json

from flask import Blueprint, render_template, request, send_file
from flask_login import current_user, login_required

from app import db
from app.dashboard import available_district_choices
from app.models import ReportLog
from app.report_export import build_excel_report, build_pdf_report
from app.report_queries import (
    REPORT_TITLES,
    build_district_summary_report,
    build_maintenance_report,
    build_monthly_repair_outcomes,
    build_predictive_risk_report,
    build_status_report,
    build_technician_performance_report,
    parse_common_filters,
)
from app.tasks import available_technician_choices

reports_bp = Blueprint("reports", __name__)


@reports_bp.route("/")
@login_required
def index():
    return render_template("reports/index.html")


@reports_bp.route("/status")
@login_required
def status_report():
    filters = parse_common_filters(request.args)
    report = build_status_report(filters)
    _log_report("status", "view", filters, report["summary"]["total"])
    return render_template(
        "reports/status.html", report=report, filters=filters, district_choices=available_district_choices()
    )


@reports_bp.route("/status/export/pdf")
@login_required
def status_report_pdf():
    filters = parse_common_filters(request.args)
    report = build_status_report(filters)
    headers = ["Status", "Count"]
    rows = list(zip(report["chart_data"]["labels"], report["chart_data"]["datasets"][0]["values"]))
    _log_report("status", "pdf", filters, report["summary"]["total"])
    buffer = build_pdf_report(REPORT_TITLES["status"], current_user, filters, report["summary"], headers, rows)
    return send_file(buffer, mimetype="application/pdf", as_attachment=True, download_name="water_point_status_report.pdf")


@reports_bp.route("/status/export/excel")
@login_required
def status_report_excel():
    filters = parse_common_filters(request.args)
    report = build_status_report(filters)
    headers = ["Status", "Count"]
    rows = list(zip(report["chart_data"]["labels"], report["chart_data"]["datasets"][0]["values"]))
    _log_report("status", "excel", filters, report["summary"]["total"])
    buffer = build_excel_report(REPORT_TITLES["status"], current_user, filters, report["summary"], headers, rows)
    return send_file(
        buffer,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="water_point_status_report.xlsx",
    )


@reports_bp.route("/technician-performance")
@login_required
def technician_performance_report():
    filters = parse_common_filters(request.args)
    page = request.args.get("page", 1, type=int)
    report = build_technician_performance_report(filters, page)
    _log_report("technician_performance", "view", filters, report["summary"]["total_technicians"])
    return render_template("reports/technician_performance.html", report=report, filters=filters)


@reports_bp.route("/technician-performance/export/pdf")
@login_required
def technician_performance_report_pdf():
    filters = parse_common_filters(request.args)
    report = build_technician_performance_report(filters, page=1)
    headers = ["Technician", "District", "Assigned", "Completed", "In Progress", "Completion Rate (%)", "Avg Resolution (hrs)"]
    rows = [
        [r["technician"], r["district"], r["assigned"], r["completed"], r["in_progress"], r["completion_rate"], r["avg_resolution_hours"] or "-"]
        for r in report["rows_all"]
    ]
    _log_report("technician_performance", "pdf", filters, len(rows))
    buffer = build_pdf_report(REPORT_TITLES["technician_performance"], current_user, filters, report["summary"], headers, rows)
    return send_file(buffer, mimetype="application/pdf", as_attachment=True, download_name="technician_performance_report.pdf")


@reports_bp.route("/technician-performance/export/excel")
@login_required
def technician_performance_report_excel():
    filters = parse_common_filters(request.args)
    report = build_technician_performance_report(filters, page=1)
    headers = ["Technician", "District", "Assigned", "Completed", "In Progress", "Completion Rate (%)", "Avg Resolution (hrs)"]
    rows = [
        [r["technician"], r["district"], r["assigned"], r["completed"], r["in_progress"], r["completion_rate"], r["avg_resolution_hours"] or "-"]
        for r in report["rows_all"]
    ]
    _log_report("technician_performance", "excel", filters, len(rows))
    buffer = build_excel_report(REPORT_TITLES["technician_performance"], current_user, filters, report["summary"], headers, rows)
    return send_file(
        buffer,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="technician_performance_report.xlsx",
    )


@reports_bp.route("/maintenance")
@login_required
def maintenance_report():
    filters = parse_common_filters(request.args)
    page = request.args.get("page", 1, type=int)
    report = build_maintenance_report(filters, page)
    trend_chart_data = build_monthly_repair_outcomes()
    _log_report("maintenance", "view", filters, report["summary"]["total"])
    return render_template(
        "reports/maintenance.html",
        report=report,
        filters=filters,
        trend_chart_data=trend_chart_data,
        district_choices=available_district_choices(),
        technician_choices=[("", "All Technicians")] + available_technician_choices(),
    )


@reports_bp.route("/maintenance/export/pdf")
@login_required
def maintenance_report_pdf():
    filters = parse_common_filters(request.args)
    report = build_maintenance_report(filters, page=1)
    headers = ["Water Point", "District", "Reported Issue", "Assigned Technician", "Repair Date", "Status", "Remarks"]
    rows = [
        [r["water_point"], r["district"], r["issue"], r["technician"], _fmt_date(r["repair_date"]), r["status"], r["remarks"]]
        for r in report["rows_all"]
    ]
    _log_report("maintenance", "pdf", filters, len(rows))
    buffer = build_pdf_report(REPORT_TITLES["maintenance"], current_user, filters, report["summary"], headers, rows)
    return send_file(buffer, mimetype="application/pdf", as_attachment=True, download_name="maintenance_report.pdf")


@reports_bp.route("/maintenance/export/excel")
@login_required
def maintenance_report_excel():
    filters = parse_common_filters(request.args)
    report = build_maintenance_report(filters, page=1)
    headers = ["Water Point", "District", "Reported Issue", "Assigned Technician", "Repair Date", "Status", "Remarks"]
    rows = [
        [r["water_point"], r["district"], r["issue"], r["technician"], _fmt_date(r["repair_date"]), r["status"], r["remarks"]]
        for r in report["rows_all"]
    ]
    _log_report("maintenance", "excel", filters, len(rows))
    buffer = build_excel_report(REPORT_TITLES["maintenance"], current_user, filters, report["summary"], headers, rows)
    return send_file(
        buffer,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="maintenance_report.xlsx",
    )


@reports_bp.route("/predictive-risk")
@login_required
def predictive_risk_report():
    filters = parse_common_filters(request.args)
    page = request.args.get("page", 1, type=int)
    report = build_predictive_risk_report(filters, page)
    _log_report("predictive_risk", "view", filters, report["summary"]["total"])
    return render_template(
        "reports/predictive_risk.html", report=report, filters=filters, district_choices=available_district_choices()
    )


@reports_bp.route("/predictive-risk/export/pdf")
@login_required
def predictive_risk_report_pdf():
    filters = parse_common_filters(request.args)
    report = build_predictive_risk_report(filters, page=1)
    headers = ["Water Point ID", "Location", "Technology Type", "Risk Level", "Prediction Date"]
    rows = [
        [r["water_point_id"], r["location"], r["technology_type"], r["risk_level"], _fmt_date(r["prediction_date"])]
        for r in report["rows_all"]
    ]
    _log_report("predictive_risk", "pdf", filters, len(rows))
    buffer = build_pdf_report(REPORT_TITLES["predictive_risk"], current_user, filters, report["summary"], headers, rows)
    return send_file(buffer, mimetype="application/pdf", as_attachment=True, download_name="predictive_risk_report.pdf")


@reports_bp.route("/predictive-risk/export/excel")
@login_required
def predictive_risk_report_excel():
    filters = parse_common_filters(request.args)
    report = build_predictive_risk_report(filters, page=1)
    headers = ["Water Point ID", "Location", "Technology Type", "Risk Level", "Prediction Date"]
    rows = [
        [r["water_point_id"], r["location"], r["technology_type"], r["risk_level"], _fmt_date(r["prediction_date"])]
        for r in report["rows_all"]
    ]
    _log_report("predictive_risk", "excel", filters, len(rows))
    buffer = build_excel_report(REPORT_TITLES["predictive_risk"], current_user, filters, report["summary"], headers, rows)
    return send_file(
        buffer,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="predictive_risk_report.xlsx",
    )


@reports_bp.route("/district-summary")
@login_required
def district_summary_report():
    filters = parse_common_filters(request.args)
    report = build_district_summary_report(filters)
    _log_report("district_summary", "view", filters, report["summary"]["total_groups"])
    return render_template("reports/district_summary.html", report=report, filters=filters)


@reports_bp.route("/district-summary/export/pdf")
@login_required
def district_summary_report_pdf():
    filters = parse_common_filters(request.args)
    report = build_district_summary_report(filters)
    headers = (
        ["District", "Sector", "Total", "Functional", "At Risk", "Maintenance Cases"]
        if report["group_by_sector"]
        else ["District", "Total", "Functional", "At Risk", "Maintenance Cases"]
    )
    rows = [_district_row(r, report["group_by_sector"]) for r in report["rows"]]
    _log_report("district_summary", "pdf", filters, len(rows))
    buffer = build_pdf_report(REPORT_TITLES["district_summary"], current_user, filters, report["summary"], headers, rows)
    return send_file(buffer, mimetype="application/pdf", as_attachment=True, download_name="district_summary_report.pdf")


@reports_bp.route("/district-summary/export/excel")
@login_required
def district_summary_report_excel():
    filters = parse_common_filters(request.args)
    report = build_district_summary_report(filters)
    headers = (
        ["District", "Sector", "Total", "Functional", "At Risk", "Maintenance Cases"]
        if report["group_by_sector"]
        else ["District", "Total", "Functional", "At Risk", "Maintenance Cases"]
    )
    rows = [_district_row(r, report["group_by_sector"]) for r in report["rows"]]
    _log_report("district_summary", "excel", filters, len(rows))
    buffer = build_excel_report(REPORT_TITLES["district_summary"], current_user, filters, report["summary"], headers, rows)
    return send_file(
        buffer,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="district_summary_report.xlsx",
    )


def _district_row(r, group_by_sector):
    if group_by_sector:
        return [r["district"], r["sector"] or "-", r["total"], r["functional"], r["at_risk"], r["maintenance_cases"]]
    return [r["district"], r["total"], r["functional"], r["at_risk"], r["maintenance_cases"]]


def _fmt_date(value):
    return value.strftime("%Y-%m-%d") if value else "-"


def _log_report(report_type, export_format, filters, row_count):
    applied = {k: v for k, v in filters.items() if v}
    db.session.add(
        ReportLog(
            report_type=report_type,
            export_format=export_format,
            generated_by_id=current_user.id,
            filters_json=json.dumps(applied, default=str),
            district_scope=None if current_user.role == "admin" else current_user.district,
            row_count=row_count,
        )
    )
    db.session.commit()
