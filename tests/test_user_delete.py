from tests.conftest import login, make_user, make_water_point

from app.models import MaintenanceTask, User, WaterPoint


def _login_as_admin(app, client, db):
    with app.app_context():
        make_user(db, "admin", "Bugesera", "admin1")
    login(client, "admin1")


def test_cannot_delete_own_account(app, client, db):
    _login_as_admin(app, client, db)
    with app.app_context():
        target = User.query.filter_by(username="admin1").first()

    resp = client.post(f"/admin/users/{target.id}/delete", follow_redirects=True)
    assert resp.status_code == 200
    assert b"cannot delete your own account" in resp.data
    with app.app_context():
        assert User.query.filter_by(username="admin1").count() == 1


def test_delete_button_not_shown_when_not_safe(app, client, db):
    _login_as_admin(app, client, db)
    with app.app_context():
        wp = make_water_point(db)
        manager = make_user(db, "district_manager", "Bugesera", "manager1")
        db.session.add(
            MaintenanceTask(
                water_point_id=wp.id,
                created_by_id=manager.id,
                title="Fix pump",
                status="pending",
            )
        )
        db.session.commit()
        manager_id = manager.id

    body = client.get("/admin/users").data.decode()
    assert "Delete Manager1 permanently?" not in body
    assert "Delete Admin1 permanently?" not in body

    resp = client.post(f"/admin/users/{manager_id}/delete", follow_redirects=True)
    assert b"created maintenance tasks" in resp.data
    with app.app_context():
        assert User.query.filter_by(username="manager1").count() == 1


def test_delete_clean_user(app, client, db):
    _login_as_admin(app, client, db)
    with app.app_context():
        junk = make_user(db, "viewer", "Bugesera", "junkuser")
        wp = make_water_point(db, water_point_id="WP-DEL")
        wp.uploaded_by_id = junk.id
        db.session.commit()
        junk_id = junk.id
        wp_id = wp.id

    body = client.get("/admin/users").data.decode()
    assert "Delete Junkuser permanently?" in body

    resp = client.post(f"/admin/users/{junk_id}/delete", follow_redirects=True)
    assert resp.status_code == 200
    assert b"has been deleted" in resp.data
    with app.app_context():
        assert User.query.filter_by(id=junk_id).count() == 0
        wp = db.session.get(WaterPoint, wp_id)
        assert wp is not None
        assert wp.uploaded_by_id is None


def test_cannot_delete_only_admin(app, client, db):
    _login_as_admin(app, client, db)
    with app.app_context():
        admins = User.query.filter_by(role="admin").all()
        assert len(admins) == 1
        target = admins[0]

    resp = client.post(f"/admin/users/{target.id}/delete", follow_redirects=True)
    assert b"cannot delete your own account" in resp.data
    with app.app_context():
        assert User.query.filter_by(role="admin").count() == 1
