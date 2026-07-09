from app import db
from app.dashboard import predict_risk
from app.models import WaterPoint
from app.settings import all_settings, get_setting, set_setting
from tests.conftest import login, make_user, make_water_point


def test_settings_page_requires_admin(app, client):
    with app.app_context():
        make_user(db, "viewer", "Bugesera", "viewer1")
        make_user(db, "admin", "Bugesera", "admin1")

    login(client, "viewer1")
    resp = client.get("/admin/system-settings")
    assert resp.status_code == 302  # redirected, not authorized

    client.get("/auth/logout")
    login(client, "admin1")
    resp = client.get("/admin/system-settings")
    assert resp.status_code == 200
    assert b"System Name" in resp.data


def test_default_settings_present(app):
    with app.app_context():
        settings = all_settings()
        assert len(settings) == 6
        assert get_setting("risk_threshold", 0.5) == 0.5
        assert get_setting("app_name") == "Smart Water Point Monitoring System"


def test_settings_post_updates_value_and_pdf(app, client):
    with app.app_context():
        make_user(db, "admin", "Bugesera", "admin1")
        make_water_point(db, water_point_id="WP-1", district="Bugesera")

    login(client, "admin1")
    resp = client.post(
        "/admin/system-settings",
        data={
            "app_name": "RWB Water Monitor",
            "admin_email": "ops@rwb.rw",
            "risk_threshold": "0.55",
            "max_upload_mb": "20",
            "default_district": "Bugesera",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200

    with app.app_context():
        assert get_setting("app_name") == "RWB Water Monitor"
        assert get_setting("risk_threshold") == 0.55

    # The persisted name must be synced into Flask config (used by reports/PDFs)
    from app.settings import apply_settings_to_config
    from flask import current_app

    with app.app_context():
        apply_settings_to_config()
        assert current_app.config["APP_NAME"] == "RWB Water Monitor"


def test_risk_threshold_drives_prediction(app):
    class StubModel:
        def predict_proba(self, features):
            return [[0.4, 0.6]]  # probability of "at risk" class = 0.6

    with app.app_context():
        wp = make_water_point(db)
        set_setting("risk_threshold", 0.9)
        assert predict_risk(StubModel(), wp)[0] == "Functional"
        set_setting("risk_threshold", 0.5)
        assert predict_risk(StubModel(), wp)[0] == "At Risk"


def test_default_district_applies_to_upload_form(app, client):
    with app.app_context():
        make_user(db, "admin", "Bugesera", "admin1")
        set_setting("default_district", "Nyagatare")

    login(client, "admin1")
    resp = client.get("/dashboard/upload")
    html = resp.data.decode()
    assert resp.status_code == 200
    # the default district option should be pre-selected
    assert 'selected value="Nyagatare"' in html
