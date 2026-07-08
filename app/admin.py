from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.forms import AdminApprovalForm, ChangeRoleForm
from app.models import AuditLog, ReportLog, User, WaterPoint
from app.utils import admin_required, utcnow

admin_bp = Blueprint("admin", __name__)


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


@admin_bp.route("/users")
@login_required
@admin_required
def users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=users)


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


@admin_bp.route("/audit-logs")
@login_required
@admin_required
def audit_logs():
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).paginate(
        page=request.args.get("page", 1, type=int), per_page=50, error_out=False
    )
    return render_template("admin/audit_logs.html", logs=logs)


@admin_bp.route("/system-settings")
@login_required
@admin_required
def system_settings():
    return render_template("admin/system_settings.html")


@admin_bp.route("/report-logs")
@login_required
@admin_required
def report_logs():
    logs = ReportLog.query.order_by(ReportLog.generated_at.desc()).paginate(
        page=request.args.get("page", 1, type=int), per_page=50, error_out=False
    )
    return render_template("admin/report_logs.html", logs=logs)
