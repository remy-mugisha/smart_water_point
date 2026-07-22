from flask import Flask, jsonify, redirect, request, url_for
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

from config import Config

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()


def create_app(config_class=Config):
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    login_manager.login_view = "auth.login"

    @login_manager.unauthorized_handler
    def unauthorized():
        if request.blueprint == "api":
            return jsonify({"error": "Authentication required"}), 401
        return redirect(url_for("auth.login", next=request.url))

    from app.admin import admin_bp
    from app.api import api_bp
    from app.auth import auth_bp
    from app.dashboard import dashboard_bp
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

    @app.before_request
    def _load_runtime_settings():
        from app.settings import apply_settings_to_config

        try:
            apply_settings_to_config()
        except Exception:
            # settings table may not exist yet on a fresh DB; fall back to config.py
            pass

    @app.after_request
    def _prevent_page_caching(response):
        # Without this, the browser's back/forward cache can redisplay an
        # authenticated page (e.g. the dashboard) after logout without a
        # fresh request ever reaching @login_required, letting a shared
        # device fall back into a previous user's session via the back button.
        if request.endpoint != "static":
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

    @app.route("/")
    def home():
        return redirect(url_for("dashboard.index"))

    @app.context_processor
    def inject_unread_notification_count():
        from flask_login import current_user

        from app.models import Notification

        if current_user.is_authenticated:
            count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
        else:
            count = 0
        return {"unread_notification_count": count}

    return app


@login_manager.user_loader
def load_user(user_id):
    from app.models import User

    return db.session.get(User, int(user_id))
