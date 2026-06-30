from functools import wraps

from flask import flash, redirect, request, url_for
from flask_login import current_user


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


def district_match_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        district = kwargs.get("district") or request.args.get("district") or request.form.get("district")
        if current_user.role == "admin":
            return f(*args, **kwargs)
        if district and current_user.district != district:
            flash("You do not have access to data from other districts.", "danger")
            return redirect(url_for("dashboard.index"))
        return f(*args, **kwargs)

    return decorated_function


def allowed_file(filename, allowed_extensions):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions
