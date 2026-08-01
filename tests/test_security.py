import re

from app import db
from tests.conftest import login, make_user


def test_csrf_blocks_post_without_token(csrf_app):
    client = csrf_app.test_client()
    with csrf_app.app_context():
        make_user(db, "admin", "Bugesera", "admin1")

    resp = client.post("/auth/login", data={"email": "admin1@example.rw", "password": "Password123!"})
    assert resp.status_code == 400


def test_toggle_active_form_carries_csrf_token(csrf_app):
    client = csrf_app.test_client()
    with csrf_app.app_context():
        make_user(db, "admin", "Bugesera", "admin1")
        target = make_user(db, "district_technician", "Bugesera", "tech1")
        target_id = target.id

    # log in without CSRF (Flask-WTF exempts GET, and login form itself carries its own token)
    login_page = client.get("/auth/login")
    token = _extract_csrf(login_page.data)
    client.post("/auth/login", data={"email": "admin1@example.rw", "password": "Password123!", "csrf_token": token})

    users_page = client.get("/admin/users")
    token = _extract_csrf(users_page.data)
    resp = client.post(f"/admin/users/{target_id}/toggle-active", data={"csrf_token": token}, follow_redirects=True)
    assert resp.status_code == 200
    assert b"has been deactivated" in resp.data


def test_api_requires_auth_returns_json_not_redirect(client):
    resp = client.get("/api/water-points")
    assert resp.status_code == 401
    assert resp.get_json() == {"error": "Authentication required"}


def test_api_role_required_returns_json_not_redirect(app, client):
    with app.app_context():
        make_user(db, "viewer", "Bugesera", "viewer1")

    login(client, "viewer1")
    resp = client.put("/api/water-points/WP-001/status", json={"status": "Functional"})
    assert resp.status_code == 403
    assert resp.get_json() == {"error": "Permission denied"}


def test_api_predict_blocks_viewer_role(app, client):
    with app.app_context():
        make_user(db, "viewer", "Bugesera", "viewer1")

    login(client, "viewer1")
    resp = client.post("/api/predict", json={"point_ids": []})
    assert resp.status_code == 403
    assert resp.get_json() == {"error": "Permission denied"}


def test_admin_redirected_to_admin_dashboard_after_login(app, client):
    with app.app_context():
        make_user(db, "admin", "Bugesera", "admin1")

    resp = client.post("/auth/login", data={"email": "admin1@example.rw", "password": "Password123!"})
    assert resp.status_code == 302
    assert resp.headers["Location"] == "/admin/dashboard"


def test_technician_redirected_to_technician_dashboard_after_login(app, client):
    with app.app_context():
        make_user(db, "district_technician", "Bugesera", "tech1")

    resp = client.post("/auth/login", data={"email": "tech1@example.rw", "password": "Password123!"})
    assert resp.status_code == 302
    assert resp.headers["Location"] == "/technician/dashboard"


def test_technician_blocked_from_admin_dashboard(app, client):
    with app.app_context():
        make_user(db, "district_technician", "Bugesera", "tech1")

    login(client, "tech1")
    resp = client.get("/admin/dashboard", follow_redirects=True)
    assert resp.status_code == 200
    assert b"You do not have permission" in resp.data


def test_login_page_shows_even_when_already_authenticated(app, client):
    """Clicking the login link from the welcome email must always show the
    login form, even if a session cookie from a previous login still exists."""
    with app.app_context():
        make_user(db, "district_technician", "Bugesera", "tech1")

    login(client, "tech1")
    resp = client.get("/auth/login")
    assert resp.status_code == 200
    assert b"Log In" in resp.data or b"Sign In" in resp.data


def test_first_user_can_register_as_admin(app, client):
    """When no admin exists, /create-admin-now creates the first administrator."""
    resp = client.post(
        "/create-admin-now",
        data={
            "full_name": "First Admin",
            "email": "admin@example.rw",
            "password": "Password123!",
            "confirm_password": "Password123!",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with app.app_context():
        from app.models import User

        admin = db.session.query(User).filter_by(email="admin@example.rw").first()
        assert admin is not None
        assert admin.role == "admin"
        assert admin.is_approved is True
        assert admin.is_active is True
        assert admin.must_change_password is False


def test_register_blocked_when_admin_exists(app, client):
    """Once an admin exists, public registration is disabled."""
    with app.app_context():
        make_user(db, "admin", "Bugesera", "admin1")

    resp = client.post(
        "/create-admin-now",
        data={
            "full_name": "Second Admin",
            "email": "admin2@example.rw",
            "password": "Password123!",
            "confirm_password": "Password123!",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"An administrator already exists" in resp.data
    with app.app_context():
        from app.models import User

        user = db.session.query(User).filter_by(email="admin2@example.rw").first()
        assert user is None, "No user should be created once an admin exists"


def test_admin_can_reset_user_password(app, client):
    with app.app_context():
        make_user(db, "admin", "Bugesera", "admin1")
        target = make_user(db, "district_technician", "Bugesera", "tech1")
        target_id = target.id

    login(client, "admin1")
    resp = client.post(
        f"/admin/users/{target_id}/reset-password",
        data={"new_password": "NewPassword123!", "confirm_new_password": "NewPassword123!"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"must change it on next login" in resp.data
    with app.app_context():
        from app.models import User

        import bcrypt

        user = db.session.get(User, target_id)
        assert user.must_change_password is True
        assert bcrypt.checkpw(b"NewPassword123!", user.password_hash.encode("utf-8"))


def _extract_csrf(html_bytes):
    html = html_bytes.decode("utf-8")
    match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    if not match:
        match = re.search(r'value="([^"]+)"[^>]*name="csrf_token"', html)
    return match.group(1)
