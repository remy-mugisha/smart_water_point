import re

from app import db
from tests.conftest import login, make_user


def test_csrf_blocks_post_without_token(csrf_app):
    client = csrf_app.test_client()
    with csrf_app.app_context():
        make_user(db, "admin", "Bugesera", "admin1")

    resp = client.post("/auth/login", data={"username": "admin1", "password": "Password123!"})
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
    client.post("/auth/login", data={"username": "admin1", "password": "Password123!", "csrf_token": token})

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


def _extract_csrf(html_bytes):
    html = html_bytes.decode("utf-8")
    match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    if not match:
        match = re.search(r'value="([^"]+)"[^>]*name="csrf_token"', html)
    return match.group(1)
