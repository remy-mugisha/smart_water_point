import bcrypt
import pytest

from app import create_app
from app import db as _db
from app.models import User, WaterPoint, WaterSource


class BaseTestConfig:
    SECRET_KEY = "test-secret-key"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = "./data/uploaded"
    ALLOWED_EXTENSIONS = {"csv", "xlsx"}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    SESSION_COOKIE_SECURE = False
    WTF_CSRF_ENABLED = False
    TESTING = True


class CSRFTestConfig(BaseTestConfig):
    WTF_CSRF_ENABLED = True


@pytest.fixture
def app():
    flask_app = create_app(BaseTestConfig)
    with flask_app.app_context():
        _db.create_all()
    # Do not hold the app context open across the yield: Flask-Login caches the
    # logged-in user on flask.g, which lives on the app context rather than the
    # request context. A held-open context lets that cache leak across requests
    # made by *different* test clients (i.e. different logged-in users) within
    # the same test, silently defeating any test that logs in two users to
    # check district/role isolation. Real requests never hit this because the
    # WSGI server pushes and pops a fresh context per request.
    yield flask_app
    with flask_app.app_context():
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def csrf_app():
    flask_app = create_app(CSRFTestConfig)
    with flask_app.app_context():
        _db.create_all()
    yield flask_app
    with flask_app.app_context():
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db(app):
    return _db


def make_user(db, role, district, username, password="Password123!"):
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user = User(
        username=username,
        email=f"{username}@example.rw",
        full_name=username.replace("_", " ").title(),
        role=role,
        district=district,
        is_approved=True,
        is_active=True,
        password_hash=password_hash,
    )
    db.session.add(user)
    db.session.commit()
    return user


def make_water_point(db, water_point_id="WP-100", district="Bugesera"):
    water_point = WaterPoint(
        water_point_id=water_point_id,
        district=district,
        latitude=-2.15,
        longitude=30.10,
        technology_type="borehole",
        current_status="At Risk",
    )
    db.session.add(water_point)
    db.session.commit()
    return water_point


def login(client, username, password="Password123!"):
    email = f"{username}@example.rw"
    return client.post("/auth/login", data={"email": email, "password": password}, follow_redirects=True)
