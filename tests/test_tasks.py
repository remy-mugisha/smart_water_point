from app import db
from app.models import MaintenanceTask, Notification, TaskStatusHistory, User, WaterPoint
from tests.conftest import login, make_user, make_water_point


def _make_manager_and_tech(district="Bugesera"):
    manager = make_user(db, "district_manager", district, "manager1")
    tech = make_user(db, "district_technician", district, "tech1")
    wp = make_water_point(db, district=district)
    return manager, tech, wp


def test_full_task_lifecycle(app, client):
    with app.app_context():
        manager, tech, wp = _make_manager_and_tech()
        manager_id, tech_id, wp_id = manager.id, tech.id, wp.id

    login(client, "manager1")
    resp = client.post(
        "/tasks/create",
        data={
            "water_point": str(wp_id),
            "technician": str(tech_id),
            "title": "Fix broken handle",
            "description": "Handle snapped",
            "priority": "high",
            "deadline": "",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200

    with app.app_context():
        task = MaintenanceTask.query.first()
        assert task is not None
        assert task.status == "assigned"
        assert task.assigned_to_id == tech_id
        task_id = task.id
        assert Notification.query.filter_by(user_id=tech_id).count() == 1

    client.get("/auth/logout")
    login(client, "tech1")

    resp = client.post(f"/tasks/{task_id}/accept", follow_redirects=True)
    assert resp.status_code == 200
    with app.app_context():
        task = db.session.get(MaintenanceTask, task_id)
        assert task.status == "accepted"
        assert task.accepted_at is not None

    resp = client.post(f"/tasks/{task_id}/start", follow_redirects=True)
    assert resp.status_code == 200
    with app.app_context():
        task = db.session.get(MaintenanceTask, task_id)
        assert task.status == "in_progress"
        wp_obj = db.session.get(WaterPoint, wp_id)
        assert wp_obj.current_status == "Under Repair"

    resp = client.post(
        f"/tasks/{task_id}/progress", data={"note": "Ordered replacement handle"}, follow_redirects=True
    )
    assert resp.status_code == 200

    resp = client.post(
        f"/tasks/{task_id}/complete",
        data={"resulting_status": "Functional", "completion_notes": "Replaced handle"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with app.app_context():
        task = db.session.get(MaintenanceTask, task_id)
        assert task.status == "completed"
        wp_obj = db.session.get(WaterPoint, wp_id)
        assert wp_obj.current_status == "Functional"
        history_count = TaskStatusHistory.query.filter_by(task_id=task_id).count()
        assert history_count >= 5  # created, assigned, accepted, in_progress, progress-note, completed

    client.get("/auth/logout")
    login(client, "manager1")
    resp = client.post(f"/tasks/{task_id}/verify", data={"note": "Looks good"}, follow_redirects=True)
    assert resp.status_code == 200
    with app.app_context():
        task = db.session.get(MaintenanceTask, task_id)
        assert task.status == "verified"
        assert task.verified_by_id == manager_id


def test_technician_cannot_act_on_unassigned_task(app, client):
    with app.app_context():
        manager, tech, wp = _make_manager_and_tech()
        make_user(db, "district_technician", "Bugesera", "tech2")
        task = MaintenanceTask(
            water_point_id=wp.id, created_by_id=manager.id, assigned_to_id=tech.id, title="Leak repair", status="assigned"
        )
        db.session.add(task)
        db.session.commit()
        task_id = task.id

    login(client, "tech2")
    resp = client.post(f"/tasks/{task_id}/accept")
    assert resp.status_code == 403


def test_cannot_assign_technician_from_other_district(app, client):
    with app.app_context():
        manager = make_user(db, "district_manager", "Bugesera", "manager2")
        make_user(db, "district_technician", "Nyagatare", "tech_other")
        wp = make_water_point(db, water_point_id="WP-200", district="Bugesera")
        wp_id = wp.id
        other_tech_id = User.query.filter_by(username="tech_other").first().id

    login(client, "manager2")
    client.post(
        "/tasks/create",
        data={
            "water_point": str(wp_id),
            "technician": str(other_tech_id),
            "title": "Cross-district attempt",
            "priority": "medium",
            "deadline": "",
        },
        follow_redirects=True,
    )
    with app.app_context():
        assert MaintenanceTask.query.count() == 0


def test_viewer_cannot_access_task_list(app, client):
    with app.app_context():
        make_user(db, "viewer", "Bugesera", "viewer1")

    login(client, "viewer1")
    resp = client.get("/tasks/", follow_redirects=True)
    assert resp.status_code == 200
    assert b"You do not have permission" in resp.data


def test_out_of_order_transition_rejected(app, client):
    with app.app_context():
        manager, tech, wp = _make_manager_and_tech()
        task = MaintenanceTask(water_point_id=wp.id, created_by_id=manager.id, title="Pump noise", status="pending")
        db.session.add(task)
        db.session.commit()
        task_id = task.id

    login(client, "manager1")
    resp = client.post(f"/tasks/{task_id}/verify", data={"note": ""}, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Only completed tasks can be verified" in resp.data
    with app.app_context():
        task = db.session.get(MaintenanceTask, task_id)
        assert task.status == "pending"
