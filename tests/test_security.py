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


def test_register_disabled_redirects_to_login(app, client):
    """Public registration is disabled; POST to /auth/register redirects to login."""
    resp = client.post(
        "/auth/register",
        data={
            "username": "managerreg",
            "email": "managerreg@example.rw",
            "full_name": "Manager Reg",
            "phone": "0788123456",
            "district": "Bugesera",
            "sector": "Gashora",
            "cell": "Biryogo",
            "village": "Bidudu",
            "role": "district_manager",
            "password": "Password123!",
            "confirm_password": "Password123!",
            "agree_terms": "y",
        },
        follow_redirects=True,
    )

    assert resp.status_code == 200
    assert b"Self-registration is disabled" in resp.data
    with app.app_context():
        from app.models import User
        user = db.session.query(User).filter_by(username="managerreg").first()
        assert user is None, "No user should be created via public registration"


def _extract_csrf(html_bytes):
    html = html_bytes.decode("utf-8")
    match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    if not match:
        match = re.search(r'value="([^"]+)"[^>]*name="csrf_token"', html)
    return match.group(1)
