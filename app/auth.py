from urllib.parse import urlsplit

import bcrypt
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app import db
from app.forms import (
    AdminBootstrapForm,
    ChangePasswordForm,
    LoginForm,
    PreferencesForm,
    SetPasswordForm,
    UserProfileForm,
)
from app.models import AuditLog, User
from app.utils import home_for, utcnow

auth_bp = Blueprint("auth", __name__)


def _generate_username(email):
    prefix = email.split("@")[0].lower()
    candidate = prefix
    suffix = 1
    while User.query.filter_by(username=candidate).first():
        candidate = f"{prefix}{suffix}"
        suffix += 1
    return candidate


def admin_register():
    """Bootstrap route: creates an administrator account.

    Mounted at the secret /create-admin-now URL in app/__init__.py rather than
    on the public auth blueprint, so the form isn't discoverable from the
    login page. It deliberately works even when admins already exist, so a new
    administrator can be provisioned at any time by anyone who knows the URL.
    """
    form = AdminBootstrapForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        admin = User(
            username=_generate_username(email),
            email=email,
            full_name=form.full_name.data.strip(),
            password_hash=bcrypt.hashpw(form.password.data.encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
            role="admin",
            is_approved=True,
            is_active=True,
            must_change_password=False,
            approved_at=utcnow(),
        )
        db.session.add(admin)
        db.session.flush()
        admin.approved_by = admin.id
        db.session.add(
            AuditLog(
                user_id=admin.id,
                action="admin_registered",
                details=f"Administrator {admin.full_name} ({admin.email}) registered via /create-admin-now",
            )
        )
        db.session.commit()
        login_user(admin)
        flash("Administrator account created. Welcome!", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = User.query.filter(db.func.lower(User.email) == email).first()
        if user and bcrypt.checkpw(form.password.data.encode("utf-8"), user.password_hash.encode("utf-8")):
            if not user.is_approved:
                flash("Your account is pending approval.", "warning")
                return redirect(url_for("auth.pending_approval"))
            if not user.is_active:
                flash("Your account has been deactivated. Contact admin.", "danger")
                return redirect(url_for("auth.login"))

            user.last_login = utcnow()
            db.session.add(AuditLog(user_id=user.id, action="login", details=f"User {user.username} logged in"))
            db.session.commit()
            login_user(user, remember=form.remember.data)

            if user.must_change_password:
                flash("You must change your temporary password before continuing.", "warning")
                return redirect(url_for("auth.change_temp_password"))

            next_page = request.args.get("next")
            if next_page and urlsplit(next_page).netloc == "" and urlsplit(next_page).scheme == "":
                return redirect(next_page)
            return redirect(url_for(home_for(user)))

        flash("Invalid username or password.", "danger")

    return render_template("auth/login.html", form=form)


@auth_bp.route("/change-temp-password", methods=["GET", "POST"])
@login_required
def change_temp_password():
    if not current_user.must_change_password:
        return redirect(url_for(home_for()))

    form = SetPasswordForm()
    if form.validate_on_submit():
        current_user.password_hash = bcrypt.hashpw(
            form.new_password.data.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")
        current_user.must_change_password = False
        db.session.add(
            AuditLog(
                user_id=current_user.id,
                action="temp_password_changed",
                details=f"User {current_user.username} changed their temporary password",
            )
        )
        db.session.commit()
        flash("Password changed successfully. Welcome to the system!", "success")
        return redirect(url_for(home_for()))

    return render_template("auth/change_temp_password.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    db.session.add(AuditLog(user_id=current_user.id, action="logout", details=f"User {current_user.username} logged out"))
    db.session.commit()
    logout_user()
    return redirect(url_for("auth.login"))


@auth_bp.route("/pending-approval")
def pending_approval():
    return render_template("auth/pending_approval.html")


@auth_bp.route("/privacy-policy")
def privacy_policy():
    return render_template("auth/privacy_policy.html")


@auth_bp.route("/settings")
@login_required
def settings():
    profile_form = UserProfileForm(obj=current_user)
    password_form = ChangePasswordForm()
    preferences_form = PreferencesForm(
        theme=current_user.theme_preference, notifications_enabled=current_user.notifications_enabled
    )
    return render_template(
        "auth/settings.html",
        profile_form=profile_form,
        password_form=password_form,
        preferences_form=preferences_form,
    )


@auth_bp.route("/settings/profile", methods=["POST"])
@login_required
def update_profile():
    form = UserProfileForm()
    if form.validate_on_submit():
        current_user.full_name = form.full_name.data
        current_user.phone = form.phone.data
        current_user.email = form.email.data
        db.session.commit()
        flash("Profile updated successfully.", "success")
    else:
        for error_list in form.errors.values():
            flash(error_list[0], "danger")
    return redirect(url_for("auth.settings"))


@auth_bp.route("/settings/password", methods=["POST"])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not bcrypt.checkpw(
            form.current_password.data.encode("utf-8"), current_user.password_hash.encode("utf-8")
        ):
            flash("Current password is incorrect.", "danger")
            return redirect(url_for("auth.settings"))

        current_user.password_hash = bcrypt.hashpw(
            form.new_password.data.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")
        db.session.add(
            AuditLog(
                user_id=current_user.id,
                action="password_changed",
                details=f"User {current_user.username} changed their password",
            )
        )
        db.session.commit()
        flash("Password changed successfully.", "success")
    else:
        for error_list in form.errors.values():
            flash(error_list[0], "danger")
    return redirect(url_for("auth.settings"))


@auth_bp.route("/settings/preferences", methods=["POST"])
@login_required
def update_preferences():
    form = PreferencesForm()
    if form.validate_on_submit():
        current_user.theme_preference = form.theme.data
        current_user.notifications_enabled = form.notifications_enabled.data
        db.session.commit()
        flash("Preferences updated.", "success")
    else:
        for error_list in form.errors.values():
            flash(error_list[0], "danger")
    return redirect(url_for("auth.settings"))
