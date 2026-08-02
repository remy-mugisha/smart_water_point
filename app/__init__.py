from flask import Flask, flash, jsonify, redirect, render_template, request, url_for
from flask_login import LoginManager, current_user
from flask_mail import Mail
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

from config import DevelopmentConfig as Config

from app.utils import home_for

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
mail = Mail()


def create_app(config_class=Config):
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)
    login_manager.login_view = "auth.login"

    @login_manager.unauthorized_handler
    def unauthorized():
        if request.blueprint == "api":
            return jsonify({"error": "Authentication required"}), 401
        return redirect(url_for("auth.login", next=request.url))

    from app.admin import admin_bp
    from app.api import api_bp
    from app.auth import auth_bp
    from app.dashboard import dashboard_bp, technician_bp
    from app.notifications import notifications_bp
    from app.reports import reports_bp
    from app.tasks import tasks_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(dashboard_bp, url_prefix="/dashboard")
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(tasks_bp, url_prefix="/tasks")
    app.register_blueprint(notifications_bp, url_prefix="/notifications")
    app.register_blueprint(reports_bp, url_prefix="/reports")
    app.register_blueprint(technician_bp)

    @app.before_request
    def _load_runtime_settings():
        from app.settings import apply_settings_to_config

        try:
            apply_settings_to_config()
        except Exception:
            pass

    @app.after_request
    def _prevent_page_caching(response):
        if request.endpoint != "static":
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

    @app.route("/")
    def home():
        if current_user.is_authenticated:
            return redirect(url_for(home_for()))
        return render_template("landing.html")

    @app.route("/create-admin-now", methods=["GET", "POST"])
    def create_admin_now():
        """Secret URL for first-time admin bootstrap. Lives at app level (no
        /auth prefix) and redirects to login once an admin exists."""
        from app.auth import admin_register

        return admin_register()

    def _block_admin_register():
        """Decoy for guessed admin-setup URLs: only /create-admin-now works."""
        flash("An administrator already exists. Contact your system admin for access.", "danger")
        return redirect(url_for("auth.login"))

    for _path in ("/admin-register", "/create-admin", "/register-admin", "/setup-admin"):
        app.add_url_rule(
            _path,
            endpoint="block_admin_register_" + _path.strip("/"),
            view_func=_block_admin_register,
            methods=["GET", "POST"],
        )

    @app.context_processor
    def inject_unread_notification_count():
        from flask_login import current_user

        from app.models import Notification

        if current_user.is_authenticated:
            count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
        else:
            count = 0
        return {"unread_notification_count": count}

    @app.context_processor
    def inject_system_scope():
        from app.settings import get_setting

        try:
            return {"system_district": get_setting("default_district") or "Bugesera"}
        except Exception:
            return {"system_district": "Bugesera"}

    return app


@login_manager.user_loader
def load_user(user_id):
    from app.models import User

    return db.session.get(User, int(user_id))
