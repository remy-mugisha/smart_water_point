from datetime import datetime
from enum import Enum

from flask_login import UserMixin

from app import db


class UserRole(Enum):
    ADMIN = "admin"
    DISTRICT_TECHNICIAN = "district_technician"
    DISTRICT_MANAGER = "district_manager"
    VIEWER = "viewer"


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(20))
    role = db.Column(db.String(50), default=UserRole.VIEWER.value)
    district = db.Column(db.String(100))
    is_approved = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    approved_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    approved_at = db.Column(db.DateTime)

    water_points = db.relationship("WaterPoint", backref="uploaded_by", lazy=True)
    maintenance_visits = db.relationship("MaintenanceVisit", backref="technician", lazy=True)
    notifications = db.relationship("Notification", backref="user", lazy=True)

    def __repr__(self):
        return f"<User {self.username}>"


class WaterPoint(db.Model):
    __tablename__ = "water_points"

    id = db.Column(db.Integer, primary_key=True)
    water_point_id = db.Column(db.String(50), unique=True, nullable=False)
    district = db.Column(db.String(100), nullable=False)
    sector = db.Column(db.String(100))
    cell = db.Column(db.String(100))
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    technology_type = db.Column(db.String(50), nullable=False)
    year_installed = db.Column(db.Integer)
    population_served = db.Column(db.Integer)
    depth = db.Column(db.Float)
    current_status = db.Column(db.String(20), default="Functional")
    risk_probability = db.Column(db.Float, default=0.0)
    last_prediction_date = db.Column(db.DateTime)
    monthly_rainfall = db.Column(db.Float)
    rainfall_month = db.Column(db.String(10))
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    maintenance_visits = db.relationship("MaintenanceVisit", backref="water_point", lazy=True)

    def __repr__(self):
        return f"<WaterPoint {self.water_point_id}>"


class MaintenanceVisit(db.Model):
    __tablename__ = "maintenance_visits"

    id = db.Column(db.Integer, primary_key=True)
    water_point_id = db.Column(db.Integer, db.ForeignKey("water_points.id"), nullable=False)
    technician_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    visit_date = db.Column(db.DateTime, default=datetime.utcnow)
    issue_found = db.Column(db.Text)
    actions_taken = db.Column(db.Text)
    status_after_visit = db.Column(db.String(20))
    parts_replaced = db.Column(db.Text)
    cost_estimate = db.Column(db.Float)
    check_in_lat = db.Column(db.Float)
    check_in_lng = db.Column(db.Float)
    check_out_lat = db.Column(db.Float)
    check_out_lng = db.Column(db.Float)

    def __repr__(self):
        return f"<MaintenanceVisit {self.id}>"


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    link = db.Column(db.String(200))

    def __repr__(self):
        return f"<Notification {self.title}>"


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<AuditLog {self.action}>"
