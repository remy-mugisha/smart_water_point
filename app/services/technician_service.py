import secrets

import bcrypt
from flask import current_app, url_for
from sqlalchemy import func

from app import db
from app.models import AuditLog, User
from app.services.mail_service import send_welcome_email


def _generate_username(email):
    prefix = email.split("@")[0].lower()
    candidate = prefix
    suffix = 1
    while User.query.filter_by(username=candidate).first():
        candidate = f"{prefix}{suffix}"
        suffix += 1
    return candidate


def _generate_temp_password():
    return secrets.token_urlsafe(12)


def create_technician(data, created_by):
    first_name = data["first_name"].strip()
    last_name = data["last_name"].strip()
    full_name = f"{first_name} {last_name}"
    email = data["email"].strip().lower()

    if User.query.filter(func.lower(User.email) == email).first():
        return None, None, "A user with this email already exists."

    username = _generate_username(email)
    temp_password = _generate_temp_password()
    password_hash = bcrypt.hashpw(temp_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    user = User(
        username=username,
        email=email,
        full_name=full_name,
        phone=data.get("phone", ""),
        district=data.get("district", ""),
        sector=data.get("sector", ""),
        cell=data.get("cell", ""),
        village=data.get("village", ""),
        role="district_technician",
        is_approved=True,
        is_active=True,
        must_change_password=True,
        password_hash=password_hash,
        approved_by=created_by.id,
        approved_at=db.func.now(),
    )
    db.session.add(user)
    db.session.flush()

    db.session.add(
        AuditLog(
            user_id=created_by.id,
            action="technician_created",
            details=f"Technician {user.full_name} ({user.email}) created by {created_by.username}",
        )
    )
    db.session.commit()

    login_url = url_for("auth.login", _external=True)
    email_sent, email_error = send_welcome_email(email, first_name, temp_password, login_url)

    if not email_sent:
        db.session.add(
            AuditLog(
                user_id=created_by.id,
                action="email_failed",
                details=f"Welcome email to {email} failed: {email_error}",
            )
        )
        db.session.commit()

    return user, temp_password, email_error if not email_sent else None


def resend_credentials(technician_id, requested_by):
    user = User.query.get(technician_id)
    if not user:
        return None, "Technician not found."
    if user.role != "district_technician":
        return None, "User is not a technician."

    temp_password = _generate_temp_password()
    user.password_hash = bcrypt.hashpw(temp_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user.must_change_password = True

    db.session.add(
        AuditLog(
            user_id=requested_by.id,
            action="credentials_resent",
            details=f"Credentials resent for {user.full_name} ({user.email}) by {requested_by.username}",
        )
    )
    db.session.commit()

    first_name = user.full_name.split()[0]
    login_url = url_for("auth.login", _external=True)
    email_sent, email_error = send_welcome_email(user.email, first_name, temp_password, login_url)

    if not email_sent:
        db.session.add(
            AuditLog(
                user_id=requested_by.id,
                action="email_failed",
                details=f"Resend email to {user.email} failed: {email_error}",
            )
        )
        db.session.commit()
        return user, f"Credentials updated but email could not be sent: {email_error}"

    return user, None
