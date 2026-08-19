from app import db
from app.dashboard import predict_risk
from app.models import WaterPoint
from app.settings import all_settings, get_setting, set_setting
from tests.conftest import login, make_user, make_water_point


def test_settings_page_requires_admin(app, client):
    with app.app_context():
        make_user(db, "viewer", "Bugesera", "viewer1")
        make_user(db, "admin", "Bugesera", "admin1")

    # System Settings route has been removed — 404 for everyone
    login(client, "viewer1")
    resp = client.get("/admin/system-settings")
    assert resp.status_code == 404

    client.get("/auth/logout")
    login(client, "admin1")
    resp = client.get("/admin/system-settings")
    assert resp.status_code == 404


def test_default_settings_present(app):
    with app.app_context():
        settings = all_settings()
        assert len(settings) == 6
        assert get_setting("risk_threshold", 0.5) == 0.5
        assert get_setting("app_name") == "AI-BASED WATER POINT FAILURE PREDICTION SYSTEM"


def test_settings_post_updates_value_and_pdf(app):
    """Settings can still be updated programmatically (admin UI route removed)."""
    with app.app_context():
        set_setting("app_name", "RWB Water Monitor")
        set_setting("admin_email", "ops@rwb.rw")
        set_setting("risk_threshold", 0.55)
        set_setting("max_upload_mb", 20)
        set_setting("default_district", "Bugesera")

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
