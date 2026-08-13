from datetime import datetime
from pathlib import Path

import bcrypt
import json
from flask import Blueprint, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload

from app import db
from app.forms import AdminApprovalForm, ChangeRoleForm, CreateTechnicianForm, SetPasswordForm
from app.models import (
    AuditLog,
    MaintenanceTask,
    Notification,
    ReportLog,
    TaskStatusHistory,
    User,
    WaterPoint,
)
from app.report_export import build_excel_report, build_pdf_report
from app.rwanda_geo import BUGESERA_SECTORS
from app.utils import admin_required, utcnow

admin_bp = Blueprint("admin", __name__)


def _district_choices():
    """District options for the technician form — Amazi is scoped to the
    districts present in the data (Bugesera), with the same fallback the
    upload form uses before any data is loaded."""
    from app.dashboard import available_district_choices

    return available_district_choices()


GEO_HIERARCHY = {"Bugesera": BUGESERA_SECTORS}


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None


REPORT_LOG_SORT_COLUMNS = {
    "time": ReportLog.generated_at,
    "report": ReportLog.report_type,
    "format": ReportLog.export_format,
    "user": User.full_name,
    "scope": ReportLog.district_scope,
    "rows": ReportLog.row_count,
}

AUDIT_LOG_SORT_COLUMNS = {
    "time": AuditLog.timestamp,
    "action": AuditLog.action,
    "user": User.full_name,
    "details": AuditLog.details,
}


def _apply_sort(query, args, columns, default="time", tie_breaker=None):
    sort_by = args.get("sort_by", default) or default
    sort_dir = (args.get("sort_dir") or "desc").lower()
    column = columns.get(sort_by, columns[default])
    ordered = column.desc() if sort_dir == "desc" else column.asc()
    if tie_breaker is None:
        tie_breaker = columns.get("id", column)
    return query.order_by(ordered, tie_breaker.desc())


@admin_bp.route("/dashboard")
@login_required
@admin_required
def dashboard():
    return render_template(
        "admin/dashboard.html",
        total_users=User.query.count(),
        pending_users=User.query.filter_by(is_approved=False, is_active=True).count(),
        total_water_points=WaterPoint.query.count(),
        at_risk_points=WaterPoint.query.filter_by(current_status="At Risk").count(),
        recent_logs=AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(20).all(),
    )


def _user_delete_blockers(user):
    """Return a human-readable reason a user cannot be deleted, or None if
    deletion is safe (no data would be orphaned or lost)."""
    if user.id == current_user.id:
        return "You cannot delete your own account."
    if user.role == "admin" and User.query.filter_by(role="admin").count() <= 1:
        return "This is the only administrator account; it cannot be deleted."
    if MaintenanceTask.query.filter_by(created_by_id=user.id).count() > 0:
        return f"{user.username} has created maintenance tasks; reassign or remove them first."
    if MaintenanceTask.query.filter_by(verified_by_id=user.id).count() > 0:
        return f"{user.username} has verified tasks; that record would be lost."
    if TaskStatusHistory.query.filter_by(changed_by_id=user.id).count() > 0:
        return f"{user.username} has task status history entries; the audit trail would be lost."
    if ReportLog.query.filter_by(generated_by_id=user.id).count() > 0:
        return f"{user.username} has generated reports; those records would be lost."
    if (
        MaintenanceTask.query.filter(
            MaintenanceTask.assigned_to_id == user.id,
            MaintenanceTask.status.notin_(["completed", "verified"]),
        ).count()
        > 0
    ):
        return f"{user.username} still has open assigned tasks; reassign them first."
    return None


@admin_bp.route("/users")
@login_required
@admin_required
def users():
    users = User.query.order_by(User.created_at.desc()).all()
    delete_allowed = {u.id: _user_delete_blockers(u) is None for u in users}
    return render_template("admin/users.html", users=users, delete_allowed=delete_allowed)


@admin_bp.route("/users/<int:user_id>/approve", methods=["GET", "POST"])
@login_required
@admin_required
def approve_user(user_id):
    user = User.query.get_or_404(user_id)
    form = AdminApprovalForm()
    if form.validate_on_submit():
        if form.action.data == "approve":
            user.is_approved = True
            user.is_active = True
            user.approved_by = current_user.id
            user.approved_at = utcnow()
            flash(f"User {user.username} has been approved.", "success")
        else:
            user.is_active = False
            flash(f"User {user.username} has been rejected.", "warning")

        db.session.add(
            AuditLog(
                user_id=current_user.id,
                action=f"user_{form.action.data}d",
                details=f"User {user.username} {form.action.data}d by admin. Notes: {form.notes.data or 'none'}",
            )
        )
        db.session.commit()
        return redirect(url_for("admin.users"))

    return render_template("admin/approve_user.html", user=user, form=form)


@admin_bp.route("/users/<int:user_id>/change-role", methods=["POST"])
@login_required
@admin_required
def change_role(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot change your own role.", "danger")
        return redirect(url_for("admin.users"))

    form = ChangeRoleForm()
    if not form.validate_on_submit():
        flash("Invalid role selection.", "danger")
        return redirect(url_for("admin.users"))

    old_role = user.role
    user.role = form.role.data
    db.session.add(
        AuditLog(
            user_id=current_user.id,
            action="user_role_changed",
            details=f"{user.username}'s role changed from {old_role} to {user.role} by {current_user.username}",
        )
    )
    db.session.commit()
    flash(f"{user.username}'s role has been updated to {user.role}.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/toggle-active", methods=["POST"])
@login_required
@admin_required
def toggle_user_active(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot deactivate yourself.", "danger")
        return redirect(url_for("admin.users"))

    user.is_active = not user.is_active
    status = "activated" if user.is_active else "deactivated"
    db.session.add(AuditLog(user_id=current_user.id, action=f"user_{status}", details=f"{user.username} {status}"))
    db.session.commit()
    flash(f"User {user.username} has been {status}.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    blocker = _user_delete_blockers(user)
    if blocker:
        flash(blocker, "danger")
        return redirect(url_for("admin.users"))

    username, email = user.username, user.email

    Notification.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    AuditLog.query.filter_by(user_id=user.id).update({"user_id": None}, synchronize_session=False)
    WaterPoint.query.filter_by(uploaded_by_id=user.id).update({"uploaded_by_id": None}, synchronize_session=False)
    MaintenanceTask.query.filter_by(assigned_to_id=user.id).update({"assigned_to_id": None}, synchronize_session=False)
    User.query.filter_by(approved_by=user.id).update({"approved_by": None}, synchronize_session=False)

    db.session.add(
        AuditLog(
            user_id=current_user.id,
            action="user_deleted",
            details=f"User {username} ({email}) deleted by {current_user.username}",
        )
    )
    db.session.delete(user)
    db.session.commit()
    flash(f"User {username} has been deleted.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/reset-password", methods=["GET", "POST"])
@login_required
@admin_required
def reset_password(user_id):
    user = User.query.get_or_404(user_id)
    form = SetPasswordForm()
    if form.validate_on_submit():
        user.password_hash = bcrypt.hashpw(
            form.new_password.data.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")
        user.must_change_password = True
        db.session.add(
            AuditLog(
                user_id=current_user.id,
                action="password_reset",
                details=f"Password reset for {user.username} ({user.email}) by {current_user.username}",
            )
        )
        db.session.commit()
        flash(f"Password reset for {user.full_name}. They must change it on next login.", "success")
        return redirect(url_for("admin.users"))

    return render_template("admin/reset_password.html", user=user, form=form)


@admin_bp.route("/technicians")
@login_required
@admin_required
def technicians():
    techs = User.query.filter_by(role="district_technician").order_by(User.created_at.desc()).all()
    create_form = CreateTechnicianForm()
    create_form.district.choices = _district_choices()
    return render_template(
        "admin/technicians.html",
        technicians=techs,
        form=create_form,
        create_modal_open=False,
        geo_hierarchy=GEO_HIERARCHY,
    )


@admin_bp.route("/technicians/create", methods=["GET", "POST"])
@login_required
@admin_required
def create_technician():
    """Create a technician from the overlay dialog on the technicians page.

    POST success redirects to the list; GET and invalid POST render the list
    page again with the dialog open so field errors stay in context.
    """
    form = CreateTechnicianForm()
    form.district.choices = _district_choices()
    if form.validate_on_submit():
        from app.services.technician_service import create_technician

        data = {
            "first_name": form.first_name.data,
            "last_name": form.last_name.data,
            "email": form.email.data,
            "phone": form.phone.data,
            "district": form.district.data,
            "sector": form.sector.data,
            "cell": form.cell.data,
            "village": form.village.data,
        }
        user, temp_password, email_error = create_technician(data, current_user)

        if user is None:
            flash(temp_password, "danger")
            return render_template(
                "admin/technicians.html",
                technicians=User.query.filter_by(role="district_technician").order_by(User.created_at.desc()).all(),
                form=form,
                create_modal_open=True,
                geo_hierarchy=GEO_HIERARCHY,
            )

        if email_error:
            flash(
                f"Account created for {user.full_name}. The welcome email could not be delivered: {email_error}. "
                f"You can resend credentials from the technicians list.",
                "warning",
            )
        else:
            flash(
                f"Technician {user.full_name} created successfully. "
                f"Credentials have been sent to {user.email}.",
                "success",
            )

        return redirect(url_for("admin.technicians"))

    techs = User.query.filter_by(role="district_technician").order_by(User.created_at.desc()).all()
    return render_template(
        "admin/technicians.html",
        technicians=techs,
        form=form,
        create_modal_open=True,
        geo_hierarchy=GEO_HIERARCHY,
    )


@admin_bp.route("/technicians/<int:user_id>/resend-credentials", methods=["POST"])
@login_required
@admin_required
def resend_credentials(user_id):
    from app.services.technician_service import resend_credentials

    user, error = resend_credentials(user_id, current_user)
    if error:
        flash(error, "danger")
    else:
        flash(f"New credentials have been sent to {user.email}.", "success")
    return redirect(url_for("admin.technicians"))


@admin_bp.route("/debug/models")
@login_required
@admin_required
def debug_models():
    models_dir = Path("models")
    files = sorted(
        (p.name, p.stat().st_size, p.stat().st_mtime)
        for p in models_dir.iterdir()
        if p.is_file()
    ) if models_dir.exists() else None
    return json.dumps(
        {
            "cwd": str(Path.cwd()),
            "models_dir_exists": models_dir.exists(),
            "models_dir_absolute": str(models_dir.resolve()) if models_dir.exists() else None,
            "files": [
                {"name": name, "size_bytes": size, "mtime": mtime}
                for name, size, mtime in (files or [])
            ],
        },
        indent=2,
    )


@admin_bp.route("/model-performance")
@login_required
@admin_required
def model_performance():
    metrics = None
    path = Path("models/training_metrics.json")
    if path.exists():
        try:
            metrics = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            metrics = None

    from app.ml_inference import is_model_available, model_metadata
    from app.settings import all_settings, get_setting

    coefficients = sorted(
        (metrics or {}).get("coefficients", {}).items(),
        key=lambda kv: abs(kv[1]),
        reverse=True,
    )
    return render_template(
        "admin/model_performance.html",
        model_available=is_model_available(),
        metadata=model_metadata(),
        metrics=metrics,
        coefficients=coefficients,
        settings=all_settings(),
        risk_threshold=get_setting("risk_threshold", 0.5),
    )


@admin_bp.route("/audit-logs")
@login_required
@admin_required
def audit_logs():
    filters = {
        "action": request.args.get("action") or None,
        "user_id": request.args.get("user_id", type=int),
        "date_from": _parse_date(request.args.get("date_from")),
        "date_to": _parse_date(request.args.get("date_to")),
    }

    query = AuditLog.query
    if filters["action"]:
        query = query.filter(AuditLog.action.ilike(f"%{filters['action']}%"))
    if filters["user_id"]:
        query = query.filter(AuditLog.user_id == filters["user_id"])
    if filters["date_from"]:
        query = query.filter(AuditLog.timestamp >= filters["date_from"])
    if filters["date_to"]:
        query = query.filter(AuditLog.timestamp <= filters["date_to"])
    query = query.options(joinedload(AuditLog.user))
    query = _apply_sort(query, request.args, AUDIT_LOG_SORT_COLUMNS, default="time", tie_breaker=AuditLog.id)

    logs = query.paginate(page=request.args.get("page", 1, type=int), per_page=50, error_out=False)
    user_choices = [(u.id, u.full_name) for u in User.query.order_by(User.full_name).all()]
    return render_template(
        "admin/audit_logs.html",
        logs=logs,
        filters=filters,
        sort_by=request.args.get("sort_by", "time"),
        sort_dir=request.args.get("sort_dir", "desc"),
        user_choices=user_choices,
    )


@admin_bp.route("/audit-logs/export/pdf")
@login_required
@admin_required
def audit_logs_pdf():
    filters, rows = _build_audit_log_rows(request.args)
    headers = ["Time", "User", "Action", "Details"]
    summary = {"total_entries": len(rows)}
    buffer = build_pdf_report("Audit Log", current_user, filters, summary, headers, rows)
    return send_file(buffer, mimetype="application/pdf", as_attachment=True, download_name="audit_log.pdf")


@admin_bp.route("/audit-logs/export/excel")
@login_required
@admin_required
def audit_logs_excel():
    filters, rows = _build_audit_log_rows(request.args)
    headers = ["Time", "User", "Action", "Details"]
    summary = {"total_entries": len(rows)}
    buffer = build_excel_report("Audit Log", current_user, filters, summary, headers, rows)
    return send_file(
        buffer,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="audit_log.xlsx",
    )


def _build_audit_log_rows(args):
    filters = {
        "action": args.get("action") or None,
        "user_id": args.get("user_id", type=int),
        "date_from": _parse_date(args.get("date_from")),
        "date_to": _parse_date(args.get("date_to")),
    }
    query = AuditLog.query
    if filters["action"]:
        query = query.filter(AuditLog.action.ilike(f"%{filters['action']}%"))
    if filters["user_id"]:
        query = query.filter(AuditLog.user_id == filters["user_id"])
    if filters["date_from"]:
        query = query.filter(AuditLog.timestamp >= filters["date_from"])
    if filters["date_to"]:
        query = query.filter(AuditLog.timestamp <= filters["date_to"])
    query = query.options(joinedload(AuditLog.user))
    query = _apply_sort(query, args, AUDIT_LOG_SORT_COLUMNS, default="time", tie_breaker=AuditLog.id)

    rows = [
        [
            log.timestamp.strftime("%Y-%m-%d %H:%M") if log.timestamp else "-",
            log.user.full_name if log.user else (log.user_id or "-"),
            log.action,
            log.details or "-",
        ]
        for log in query.all()
    ]
    return filters, rows



@admin_bp.route("/report-logs")
@login_required
@admin_required
def report_logs():
    filters, logs, choices = _build_report_log_view(request.args)
    return render_template(
        "admin/report_logs.html",
        logs=logs,
        filters=filters,
        choices=choices,
        sort_by=request.args.get("sort_by", "time"),
        sort_dir=request.args.get("sort_dir", "desc"),
    )


@admin_bp.route("/report-logs/export/pdf")
@login_required
@admin_required
def report_logs_pdf():
    filters, rows, _ = _build_report_log_rows(request.args)
    headers = ["Time", "Report", "Format", "Generated By", "Scope", "Rows", "Filters"]
    summary = {"total_entries": len(rows)}
    buffer = build_pdf_report("Report Activity Log", current_user, filters, summary, headers, rows)
    return send_file(buffer, mimetype="application/pdf", as_attachment=True, download_name="report_activity_log.pdf")


@admin_bp.route("/report-logs/export/excel")
@login_required
@admin_required
def report_logs_excel():
    filters, rows, _ = _build_report_log_rows(request.args)
    headers = ["Time", "Report", "Format", "Generated By", "Scope", "Rows", "Filters"]
    summary = {"total_entries": len(rows)}
    buffer = build_excel_report("Report Activity Log", current_user, filters, summary, headers, rows)
    return send_file(
        buffer,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="report_activity_log.xlsx",
    )


def _build_report_log_filters(args):
    return {
        "report_type": args.get("report_type") or None,
        "export_format": args.get("export_format") or None,
        "user_id": args.get("user_id", type=int),
        "district_scope": args.get("district_scope") or None,
        "date_from": _parse_date(args.get("date_from")),
        "date_to": _parse_date(args.get("date_to")),
    }


def _build_report_log_query(filters):
    query = ReportLog.query
    if filters["report_type"]:
        query = query.filter(ReportLog.report_type == filters["report_type"])
    if filters["export_format"]:
        query = query.filter(ReportLog.export_format == filters["export_format"])
    if filters["user_id"]:
        query = query.filter(ReportLog.generated_by_id == filters["user_id"])
    if filters["district_scope"]:
        query = query.filter(ReportLog.district_scope == filters["district_scope"])
    if filters["date_from"]:
        query = query.filter(ReportLog.generated_at >= filters["date_from"])
    if filters["date_to"]:
        query = query.filter(ReportLog.generated_at <= filters["date_to"])
    return query.options(joinedload(ReportLog.generated_by))


def _build_report_log_view(args):
    filters = _build_report_log_filters(args)
    query = _build_report_log_query(filters)
    query = _apply_sort(query, args, REPORT_LOG_SORT_COLUMNS, default="time")
    logs = query.paginate(page=args.get("page", 1, type=int), per_page=50, error_out=False)

    report_type_choices = [
        (key, key.replace("_", " ").title()) for key in sorted({r[0] for r in db.session.query(ReportLog.report_type).distinct() if r[0]})
    ]
    scope_choices = sorted({r[0] for r in db.session.query(ReportLog.district_scope).distinct() if r[0]})
    user_choices = [(u.id, u.full_name) for u in User.query.order_by(User.full_name).all()]
    choices = {
        "report_types": report_type_choices,
        "formats": [("view", "View"), ("pdf", "PDF"), ("excel", "Excel")],
        "scopes": scope_choices,
        "users": user_choices,
    }
    return filters, logs, choices


def _build_report_log_rows(args):
    filters = _build_report_log_filters(args)
    query = _build_report_log_query(filters)
    query = _apply_sort(query, args, REPORT_LOG_SORT_COLUMNS, default="time")
    rows = [
        [
            log.generated_at.strftime("%Y-%m-%d %H:%M") if log.generated_at else "-",
            log.report_type.replace("_", " ").title(),
            log.export_format.upper(),
            log.generated_by.full_name if log.generated_by else "-",
            log.district_scope or "All districts",
            log.row_count if log.row_count is not None else "-",
            log.filters_json or "None",
        ]
        for log in query.all()
    ]
    return filters, rows, None
