from flask import Blueprint, abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app import db
from app.forms import TaskAssignForm, TaskCompleteForm, TaskCreateForm, TaskProgressForm, TaskVerifyForm
from app.models import AuditLog, MaintenanceTask, TaskStatus, TaskStatusHistory, User, WaterPoint
from app.utils import manager_required, notify, scoped_by_district, technician_required, user_can_access_district, utcnow

tasks_bp = Blueprint("tasks", __name__)


@tasks_bp.route("/")
@login_required
@technician_required
def list_tasks():
    tasks = scoped_tasks().order_by(MaintenanceTask.created_at.desc()).all()

    create_form = None
    if current_user.role in ("admin", "district_manager"):
        create_form = TaskCreateForm()
        create_form.water_point.choices = available_water_point_choices()
        create_form.technician.choices = [("", "Unassigned (assign later)")] + available_technician_choices()

    return render_template("tasks/list.html", tasks=tasks, create_form=create_form)


@tasks_bp.route("/create", methods=["GET", "POST"])
@login_required
@manager_required
def create_task():
    form = TaskCreateForm()
    form.water_point.choices = available_water_point_choices()
    form.technician.choices = [("", "Unassigned (assign later)")] + available_technician_choices()

    if form.validate_on_submit():
        water_point = db.session.get(WaterPoint, int(form.water_point.data))
        if water_point is None or not user_can_access_district(water_point.district):
            flash("Invalid water point selection.", "danger")
            return render_template("tasks/create.html", form=form)

        technician = None
        if form.technician.data:
            technician = db.session.get(User, int(form.technician.data))
            if technician is None or technician.district != water_point.district:
                flash("Selected technician must belong to the water point's district.", "danger")
                return render_template("tasks/create.html", form=form)

        task = MaintenanceTask(
            water_point_id=water_point.id,
            created_by_id=current_user.id,
            title=form.title.data,
            description=form.description.data,
            priority=form.priority.data,
            deadline=form.deadline.data,
            status=TaskStatus.PENDING.value,
        )
        db.session.add(task)
        db.session.flush()

        _record_transition(task, None, TaskStatus.PENDING.value, "Task created")

        if technician:
            _assign_technician(task, technician)

        db.session.add(
            AuditLog(user_id=current_user.id, action="task_created", details=f"Task '{task.title}' created for {water_point.water_point_id}")
        )
        db.session.commit()
        flash("Task created successfully.", "success")
        return redirect(url_for("tasks.task_detail", task_id=task.id))

    return render_template("tasks/create.html", form=form)


@tasks_bp.route("/<int:task_id>")
@login_required
@technician_required
def task_detail(task_id):
    task = MaintenanceTask.query.get_or_404(task_id)
    _ensure_task_access(task)
    assign_form = TaskAssignForm()
    assign_form.technician.choices = available_technician_choices(district=task.water_point.district)
    return render_template(
        "tasks/detail.html",
        task=task,
        assign_form=assign_form,
        progress_form=TaskProgressForm(),
        complete_form=TaskCompleteForm(),
        verify_form=TaskVerifyForm(),
    )


@tasks_bp.route("/<int:task_id>/assign", methods=["POST"])
@login_required
@manager_required
def assign_task(task_id):
    task = MaintenanceTask.query.get_or_404(task_id)
    _ensure_task_access(task)
    if task.status != TaskStatus.PENDING.value:
        flash("Only pending tasks can be assigned.", "danger")
        return redirect(url_for("tasks.task_detail", task_id=task.id))

    form = TaskAssignForm()
    form.technician.choices = available_technician_choices(district=task.water_point.district)
    if not form.validate_on_submit():
        flash("Please select a valid technician.", "danger")
        return redirect(url_for("tasks.task_detail", task_id=task.id))

    technician = db.session.get(User, int(form.technician.data))
    if technician is None or technician.district != task.water_point.district:
        flash("Technician must belong to the water point's district.", "danger")
        return redirect(url_for("tasks.task_detail", task_id=task.id))

    _assign_technician(task, technician)
    db.session.add(AuditLog(user_id=current_user.id, action="task_assigned", details=f"Task '{task.title}' assigned to {technician.username}"))
    db.session.commit()
    flash(f"Task assigned to {technician.full_name}.", "success")
    return redirect(url_for("tasks.task_detail", task_id=task.id))


@tasks_bp.route("/<int:task_id>/accept", methods=["POST"])
@login_required
@technician_required
def accept_task(task_id):
    task = MaintenanceTask.query.get_or_404(task_id)
    _ensure_assignee_or_admin(task)
    if task.status != TaskStatus.ASSIGNED.value:
        flash("Only assigned tasks can be accepted.", "danger")
        return redirect(url_for("tasks.task_detail", task_id=task.id))

    task.accepted_at = utcnow()
    _transition(task, TaskStatus.ACCEPTED.value, f"Accepted by {current_user.full_name}")
    notify(task.created_by_id, "Task accepted", f"{current_user.full_name} accepted task '{task.title}'.", link=url_for("tasks.task_detail", task_id=task.id))
    db.session.add(AuditLog(user_id=current_user.id, action="task_accepted", details=f"Task '{task.title}' accepted"))
    db.session.commit()
    flash("Task accepted.", "success")
    return redirect(url_for("tasks.task_detail", task_id=task.id))


@tasks_bp.route("/<int:task_id>/start", methods=["POST"])
@login_required
@technician_required
def start_task(task_id):
    task = MaintenanceTask.query.get_or_404(task_id)
    _ensure_assignee_or_admin(task)
    if task.status != TaskStatus.ACCEPTED.value:
        flash("Only accepted tasks can be started.", "danger")
        return redirect(url_for("tasks.task_detail", task_id=task.id))

    task.started_at = utcnow()
    task.water_point.current_status = "Under Repair"
    _transition(task, TaskStatus.IN_PROGRESS.value, f"Started by {current_user.full_name}")
    db.session.add(AuditLog(user_id=current_user.id, action="task_started", details=f"Task '{task.title}' started"))
    db.session.commit()
    flash("Task started. Water point marked Under Repair.", "success")
    return redirect(url_for("tasks.task_detail", task_id=task.id))


@tasks_bp.route("/<int:task_id>/progress", methods=["POST"])
@login_required
@technician_required
def update_progress(task_id):
    task = MaintenanceTask.query.get_or_404(task_id)
    _ensure_assignee_or_admin(task)
    if task.status != TaskStatus.IN_PROGRESS.value:
        flash("Progress updates are only allowed while a task is in progress.", "danger")
        return redirect(url_for("tasks.task_detail", task_id=task.id))

    form = TaskProgressForm()
    if not form.validate_on_submit():
        flash("Progress note is required.", "danger")
        return redirect(url_for("tasks.task_detail", task_id=task.id))

    db.session.add(
        TaskStatusHistory(task_id=task.id, changed_by_id=current_user.id, from_status=task.status, to_status=task.status, note=form.note.data)
    )
    db.session.commit()
    flash("Progress update recorded.", "success")
    return redirect(url_for("tasks.task_detail", task_id=task.id))


@tasks_bp.route("/<int:task_id>/complete", methods=["POST"])
@login_required
@technician_required
def complete_task(task_id):
    task = MaintenanceTask.query.get_or_404(task_id)
    _ensure_assignee_or_admin(task)
    if task.status != TaskStatus.IN_PROGRESS.value:
        flash("Only in-progress tasks can be completed.", "danger")
        return redirect(url_for("tasks.task_detail", task_id=task.id))

    form = TaskCompleteForm()
    if not form.validate_on_submit():
        flash("Completion notes and resulting status are required.", "danger")
        return redirect(url_for("tasks.task_detail", task_id=task.id))

    task.completed_at = utcnow()
    task.completion_notes = form.completion_notes.data
    task.resulting_status = form.resulting_status.data
    task.water_point.current_status = form.resulting_status.data
    _transition(task, TaskStatus.COMPLETED.value, f"Completed by {current_user.full_name}: {form.completion_notes.data}")
    notify(
        task.created_by_id,
        "Task completed",
        f"{current_user.full_name} completed task '{task.title}'. Awaiting verification.",
        link=url_for("tasks.task_detail", task_id=task.id),
    )
    db.session.add(AuditLog(user_id=current_user.id, action="task_completed", details=f"Task '{task.title}' completed"))
    db.session.commit()
    flash("Task marked completed and pending verification.", "success")
    return redirect(url_for("tasks.task_detail", task_id=task.id))


@tasks_bp.route("/<int:task_id>/verify", methods=["POST"])
@login_required
@manager_required
def verify_task(task_id):
    task = MaintenanceTask.query.get_or_404(task_id)
    _ensure_task_access(task)
    if task.status != TaskStatus.COMPLETED.value:
        flash("Only completed tasks can be verified.", "danger")
        return redirect(url_for("tasks.task_detail", task_id=task.id))

    form = TaskVerifyForm()
    task.verified_at = utcnow()
    task.verified_by_id = current_user.id
    _transition(task, TaskStatus.VERIFIED.value, form.note.data or f"Verified by {current_user.full_name}")
    if task.assigned_to_id:
        notify(
            task.assigned_to_id,
            "Task verified",
            f"Your completed task '{task.title}' has been verified by {current_user.full_name}.",
            link=url_for("tasks.task_detail", task_id=task.id),
        )
    db.session.add(AuditLog(user_id=current_user.id, action="task_verified", details=f"Task '{task.title}' verified"))
    db.session.commit()
    flash("Task verified.", "success")
    return redirect(url_for("tasks.task_detail", task_id=task.id))


def scoped_tasks():
    if current_user.role == "district_technician":
        return MaintenanceTask.query.filter_by(assigned_to_id=current_user.id)
    return scoped_by_district(MaintenanceTask.query.join(WaterPoint), WaterPoint.district)


def available_water_point_choices():
    query = scoped_by_district(WaterPoint.query, WaterPoint.district)
    return [(str(wp.id), f"{wp.water_point_id} — {wp.district} ({wp.current_status})") for wp in query.order_by(WaterPoint.water_point_id).all()]


def available_technician_choices(district=None):
    query = User.query.filter_by(role="district_technician", is_approved=True, is_active=True)
    scope_district = district or (current_user.district if current_user.role != "admin" else None)
    if scope_district:
        query = query.filter_by(district=scope_district)
    return [(str(u.id), f"{u.full_name} ({u.district})") for u in query.order_by(User.full_name).all()]


def _ensure_task_access(task):
    if current_user.role == "admin":
        return
    if current_user.role == "district_manager" and task.water_point.district == current_user.district:
        return
    if current_user.role == "district_technician" and task.assigned_to_id == current_user.id:
        return
    abort(403)


def _ensure_assignee_or_admin(task):
    if current_user.role == "admin":
        return
    if task.assigned_to_id != current_user.id:
        abort(403)


def _assign_technician(task, technician):
    task.assigned_to_id = technician.id
    task.assigned_at = utcnow()
    _transition(task, TaskStatus.ASSIGNED.value, f"Assigned to {technician.full_name}")
    notify(
        technician.id,
        "New task assigned",
        f"You have been assigned to task '{task.title}' at {task.water_point.water_point_id}.",
        link=url_for("tasks.task_detail", task_id=task.id),
    )


def _transition(task, new_status, note):
    _record_transition(task, task.status, new_status, note)
    task.status = new_status


def _record_transition(task, from_status, to_status, note):
    db.session.add(
        TaskStatusHistory(task_id=task.id, changed_by_id=current_user.id, from_status=from_status, to_status=to_status, note=note)
    )
