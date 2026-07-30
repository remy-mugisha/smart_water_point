import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'smart_water.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"
    UPLOAD_FOLDER = str(BASE_DIR / "data" / "uploaded")
    ALLOWED_EXTENSIONS = {"csv", "xlsx"}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    APP_NAME = "Smart Water Point Monitoring System"
    ADMIN_EMAIL = "admin@smartwater.rw"

    # Flask-Mail / SMTP
    MAIL_SERVER = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("SMTP_PORT", 587))
    MAIL_USE_TLS = os.environ.get("SMTP_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.environ.get("SMTP_USER")
    MAIL_PASSWORD = os.environ.get("SMTP_PASS")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_FROM", "noreply@smartwater.rw")


class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SESSION_COOKIE_SECURE = False
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    SESSION_COOKIE_SECURE = True
