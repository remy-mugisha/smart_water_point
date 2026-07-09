from datetime import datetime, timezone
from functools import wraps

from flask import flash, jsonify, redirect, url_for
from flask_login import current_user


def utcnow():
    """Naive UTC timestamp, matching how every existing DateTime column/comparison
    in this codebase already stores and compares time. datetime.utcnow() is
    deprecated; datetime.now(timezone.utc) is its replacement but returns a
    timezone-aware value, which SQLite doesn't store and which can't be compared
    or subtracted against the naive values already in the database. Stripping
    tzinfo here keeps behavior identical while avoiding the deprecation warning.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def api_role_required(*roles):
    """Same role gate as role_required, but returns JSON errors instead of redirecting.

    Use on api_bp routes: unlike HTML pages, API callers can't act on a redirect
    to a login page, so failures must come back as 401/403 JSON responses.
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({"error": "Authentication required"}), 401
            if current_user.role not in roles:
                return jsonify({"error": "Permission denied"}), 403
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Please log in to access this page.", "warning")
                return redirect(url_for("auth.login"))
            if current_user.role not in roles:
                flash("You do not have permission to access this page.", "danger")
                return redirect(url_for("dashboard.index"))
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def admin_required(f):
    return role_required("admin")(f)


def technician_required(f):
    return role_required("admin", "district_technician", "district_manager")(f)


def manager_required(f):
    return role_required("admin", "district_manager")(f)


def scoped_by_district(query, district_column):
    """Filter a query to the current user's district, unless they're an admin.

    Single source of truth for "is this user allowed to see this district's
    data" so district-scoping doesn't get reimplemented slightly differently
    in each blueprint.
    """
    if current_user.role == "admin":
        return query
    return query.filter(district_column == current_user.district)


def user_can_access_district(district):
    return current_user.role == "admin" or current_user.district == district


def allowed_file(filename, allowed_extensions):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions


def notify(user_id, title, message, link=None):
    """Create an in-app notification for a user. Caller is responsible for db.session.commit()."""
    from app import db
    from app.models import Notification, User

    if not user_id:
        return None
    recipient = db.session.get(User, user_id)
    if recipient is not None and not recipient.notifications_enabled:
        return None
    notification = Notification(user_id=user_id, title=title, message=message, link=link)
    db.session.add(notification)
    return notification
