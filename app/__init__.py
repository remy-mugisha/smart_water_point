from flask import Flask, redirect, url_for
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from config import Config

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()


def create_app(config_class=Config):
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "warning"

    from app.admin import admin_bp
    from app.api import api_bp
    from app.auth import auth_bp
    from app.dashboard import dashboard_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(dashboard_bp, url_prefix="/dashboard")
    app.register_blueprint(api_bp, url_prefix="/api")

    @app.route("/")
    def home():
        return redirect(url_for("dashboard.index"))

    return app


@login_manager.user_loader
def load_user(user_id):
    from app.models import User

    return User.query.get(int(user_id))
