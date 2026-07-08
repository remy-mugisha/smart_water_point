from pathlib import Path

import joblib
import pandas as pd
from flask import Blueprint, current_app, flash, redirect, render_template, url_for
from flask_login import current_user, login_required
from sqlalchemy import func
from werkzeug.utils import secure_filename

from app import db
from app.forms import DISTRICT_CHOICES, DataUploadForm
from app.models import AuditLog, WaterPoint, WaterSource
from app.utils import allowed_file, role_required, scoped_by_district, utcnow

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def index():
    water_points = scoped_water_points().all()
    status_counts = {
        "total": len(water_points),
        "at_risk": len([wp for wp in water_points if wp.current_status == "At Risk"]),
        "functional": len([wp for wp in water_points if wp.current_status == "Functional"]),
        "non_functional": len([wp for wp in water_points if wp.current_status == "Non-Functional"]),
        "under_repair": len([wp for wp in water_points if wp.current_status == "Under Repair"]),
    }
    return render_template("dashboard/index.html", water_points=water_points, **status_counts)


@dashboard_bp.route("/map")
@login_required
def map_view():
    return render_template("dashboard/map.html", water_points=scoped_water_points().all())


@dashboard_bp.route("/water-points")
@login_required
def water_points():
    return render_template(
        "dashboard/water_points.html",
        water_points=scoped_water_points().order_by(WaterPoint.last_updated.desc()).all(),
    )


@dashboard_bp.route("/upload", methods=["GET", "POST"])
@login_required
@role_required("admin", "district_technician", "district_manager")
def upload_data():
    form = DataUploadForm()
    form.district.choices = available_district_choices()

    if form.validate_on_submit():
        upload = form.data_file.data
        filename = secure_filename(upload.filename)
        if not allowed_file(filename, current_app.config["ALLOWED_EXTENSIONS"]):
            flash("Only CSV and XLSX files are allowed.", "danger")
            return render_template("dashboard/upload.html", form=form)

        upload_dir = Path(current_app.config["UPLOAD_FOLDER"])
        upload_dir.mkdir(parents=True, exist_ok=True)
        filepath = upload_dir / filename
        upload.save(filepath)

        try:
            df = pd.read_csv(filepath) if filename.lower().endswith(".csv") else pd.read_excel(filepath)
            processed_count = process_water_point_data(df, form.district.data, current_user.id)
        except Exception as exc:
            db.session.rollback()
            filepath.unlink(missing_ok=True)
            flash(f"Error processing file: {exc}", "danger")
            return render_template("dashboard/upload.html", form=form)

        db.session.add(
            AuditLog(
                user_id=current_user.id,
                action="data_upload",
                details=f"Uploaded {processed_count} water points for {form.district.data}",
            )
        )
        db.session.commit()
        flash(f"Successfully processed {processed_count} water points for {form.district.data}.", "success")
        return redirect(url_for("dashboard.water_points"))

    return render_template("dashboard/upload.html", form=form)


def scoped_water_points():
    return scoped_by_district(WaterPoint.query, WaterPoint.district)


def available_district_choices():
    if current_user.role == "admin":
        existing = [d[0] for d in db.session.query(WaterPoint.district).distinct() if d[0]]
        districts = sorted(set(existing + [choice[0] for choice in DISTRICT_CHOICES if choice[0]]))
        return [("", "Select District")] + [(district, district) for district in districts]
    return [(current_user.district, current_user.district)]


def process_water_point_data(df, district, user_id):
    required = {"water_point_id", "latitude", "longitude", "technology_type"};
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

    count = 0
    model = load_prediction_model()

    catchment_pressures = {}
    if model is not None:
        catchment_pressures = dict(
            db.session.query(WaterSource.catchment, func.sum(WaterSource.industrial_pressure_score))
            .filter(WaterSource.catchment.isnot(None))
            .group_by(WaterSource.catchment)
            .all()
        )

    source_map = _build_source_map(df)

    for _, row in df.iterrows():
        water_point = WaterPoint.query.filter_by(water_point_id=str(row.get("water_point_id"))).first()
        if water_point is None:
            water_point = WaterPoint(water_point_id=str(row.get("water_point_id")), uploaded_by_id=user_id)
            db.session.add(water_point)

        water_point.district = district
        water_point.sector = value_or_none(row.get("sector"))
        water_point.cell = value_or_none(row.get("cell"))
        water_point.latitude = float(row.get("latitude"))
        water_point.longitude = float(row.get("longitude"))
        water_point.technology_type = str(row.get("technology_type"))
        water_point.year_installed = int(row.get("year_installed")) if pd.notna(row.get("year_installed")) else None
        water_point.population_served = (
            int(row.get("population_served")) if pd.notna(row.get("population_served")) else None
        )
        water_point.depth = float(row.get("depth")) if pd.notna(row.get("depth")) else None
        water_point.monthly_rainfall = float(row.get("rainfall")) if pd.notna(row.get("rainfall")) else None
        water_point.rainfall_month = value_or_none(row.get("rainfall_month"))
        water_point.last_updated = utcnow()
        water_point.water_source_id = source_map.get(value_or_none(row.get("water_source_name")))

        if model:
            prediction, probability = predict_risk(model, water_point, catchment_pressures)
            water_point.current_status = prediction
            water_point.risk_probability = probability
            water_point.last_prediction_date = utcnow()

        count += 1

    db.session.commit()
    return count


def _build_source_map(df):
    if "water_source_name" not in df.columns:
        return {}
    names = sorted(set(value_or_none(n) for n in df["water_source_name"].dropna() if value_or_none(n)))
    if not names:
        return {}

    map_ = {}
    for upload_name in names:
        source = (
            WaterSource.query.filter(func.lower(WaterSource.name) == upload_name.lower()).first()
            or WaterSource.query.filter(WaterSource.name.ilike(f"%{upload_name}%")).first()
            or WaterSource.query.filter(func.lower(WaterSource.name).like(f"%{upload_name.lower()}%")).first()
        )
        if source:
            map_[upload_name] = source.id
    return map_


def value_or_none(value):
    return None if pd.isna(value) else str(value)


def load_prediction_model():
    model_path = Path("models") / "water_point_model.pkl"
    if not model_path.exists():
        return None
    try:
        return joblib.load(model_path)
    except Exception:
        return None


def predict_risk(model, water_point, catchment_pressures=None):
    catchment_pressure = 0.0
    if getattr(water_point, "water_source", None) and water_point.water_source.catchment:
        catchment_pressure = catchment_pressures.get(water_point.water_source.catchment, 0.0) if catchment_pressures is not None else 0.0
    features = [[water_point.year_installed or 0, water_point.population_served or 0, water_point.monthly_rainfall or 0, catchment_pressure]]
    probability = model.predict_proba(features)[0]
    risk_prob = float(probability[1] if len(probability) > 1 else probability[0])
    return ("At Risk" if risk_prob > 0.5 else "Functional"), risk_prob
