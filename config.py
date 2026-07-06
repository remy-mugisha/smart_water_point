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
