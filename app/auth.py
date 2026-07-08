from urllib.parse import urlsplit

import bcrypt
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app import db
from app.forms import LoginForm, RegistrationForm, UserProfileForm
from app.models import AuditLog, User
from app.rwanda_geo import BUGESERA_SECTORS
from app.utils import utcnow

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    form = RegistrationForm()
    if form.validate_on_submit():
        is_first_user = User.query.count() == 0
        # District Managers are trusted district staff, not public self-service
        # signups, so their accounts skip the admin-approval queue and go
        # straight to active - same as the bootstrap first-admin account.
        is_manager = form.role.data == "district_manager"
        auto_approved = is_first_user or is_manager

        password_hash = bcrypt.hashpw(form.password.data.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        user = User(
            username=form.username.data,
            email=form.email.data,
            full_name=form.full_name.data,
            phone=form.phone.data,
            district=form.district.data,
            sector=form.sector.data,
            cell=form.cell.data,
            village=form.village.data,
            role="admin" if is_first_user else form.role.data,
            is_approved=auto_approved,
            password_hash=password_hash,
        )
        db.session.add(user)
        db.session.flush()
        db.session.add(
            AuditLog(user_id=user.id, action="user_registered", details=f"User {user.username} registered")
        )
        db.session.commit()

        if is_first_user:
            flash("Registration successful. Your first account is an approved administrator.", "success")
            return redirect(url_for("auth.login"))

        if is_manager:
            flash("Registration successful. District Manager accounts are activated automatically.", "success")
            return redirect(url_for("auth.login"))

        flash("Registration successful. Please wait for admin approval.", "success")
        return redirect(url_for("auth.pending_approval"))

    return render_template("auth/register.html", form=form, sectors=BUGESERA_SECTORS)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
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
            flash(f"Welcome back, {user.full_name}.", "success")

            next_page = request.args.get("next")
            if next_page and urlsplit(next_page).netloc == "" and urlsplit(next_page).scheme == "":
                return redirect(next_page)
            return redirect(url_for("dashboard.index"))

        flash("Invalid username or password.", "danger")

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    db.session.add(AuditLog(user_id=current_user.id, action="logout", details=f"User {current_user.username} logged out"))
    db.session.commit()
    logout_user()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/pending-approval")
def pending_approval():
    return render_template("auth/pending_approval.html")


@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    form = UserProfileForm(obj=current_user)
    if form.validate_on_submit():
        current_user.full_name = form.full_name.data
        current_user.phone = form.phone.data
        current_user.email = form.email.data
        db.session.commit()
        flash("Profile updated successfully.", "success")
        return redirect(url_for("auth.profile"))
    return render_template("auth/profile.html", form=form)
