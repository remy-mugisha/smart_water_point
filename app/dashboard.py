import json
from datetime import datetime
from pathlib import Path

import joblib
import pandas as pd
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import case, func
from werkzeug.utils import secure_filename

from app import db, ml_inference
from app.forms import DISTRICT_CHOICES, DataUploadForm
from app.ml_features import FEATURE_NAMES, build_feature_row
from app.models import AuditLog, MaintenanceTask, WaterPoint, WaterSource
from app.services.water_point_service import find_matching_water_point
from app.utils import allowed_file, role_required, scoped_by_district, utcnow

dashboard_bp = Blueprint("dashboard", __name__)
technician_bp = Blueprint("technician", __name__, url_prefix="/technician")


def _model_metrics():
    """Read the deployed model's training metrics (accuracy, ROC-AUC, feature
    coefficients, last-trained time) or return None if no model exists."""
    path = Path("models/training_metrics.json")
    if not path.exists():
        return None
    try:
        with path.open(encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def _catchment_pressures():
    return dict(
        db.session.query(WaterSource.catchment, func.sum(WaterSource.industrial_pressure_score))
        .filter(WaterSource.catchment.isnot(None))
        .group_by(WaterSource.catchment)
        .all()
    )


def risk_factors_for(water_point):
    """Explain a single water point's risk: which domain factors push it
    toward failure and which pull it back, using the deployed model's
    coefficients. Never presents the AI as a black box."""
    metadata = ml_inference.model_metadata() or {}
    metrics = _model_metrics() or {}
    coefficients = metrics.get("coefficients") or {}
    if not coefficients:
        return []

    catchment_pressure = 0.0
    if water_point.water_source and water_point.water_source.catchment:
        catchment_pressure = _catchment_pressures().get(water_point.water_source.catchment, 0.0)

    features = build_feature_row(
        year_installed=water_point.year_installed,
        population_served=water_point.population_served,
        monthly_rainfall=water_point.monthly_rainfall,
        technology_type=water_point.technology_type,
        catchment_pressure=catchment_pressure,
        metadata=metadata,
    )

    def _human(name, value):
        if name == "age":
            return f"{int(value)} years"
        if name == "population_served":
            return f"{int(value):,} people"
        if name == "monthly_rainfall":
            return f"{value:.0f} mm"
        if name == "tech_encoded":
            return water_point.technology_type or "Unknown"
        if name == "catchment_pressure":
            return f"{value:.1f}"
        if name == "rainy_season_flag":
            return "Yes" if value else "No"
        if name == "population_density_category":
            return ("Low", "Medium", "High")[int(value)] if 0 <= int(value) <= 2 else "Unknown"
        return f"{value:.2f}"

    def _label(name):
        return {
            "age": "Infrastructure age",
            "population_served": "Population served",
            "monthly_rainfall": "Monthly rainfall",
            "tech_encoded": "Technology type",
            "catchment_pressure": "Catchment pressure",
            "rainy_season_flag": "Rainy season",
            "population_density_category": "Population density",
        }.get(name, name.replace("_", " ").title())

    factors = []
    for name in ("age", "population_served", "monthly_rainfall", "tech_encoded",
                 "catchment_pressure", "rainy_season_flag", "population_density_category"):
        coefficient = coefficients.get(name)
        if coefficient is None:
            continue
        contribution = float(coefficient) * float(features.get(name, 0.0))
        factors.append({
            "name": _label(name),
            "value": _human(name, features.get(name, 0.0)),
            "contribution": contribution,
            "direction": "up" if contribution > 0 else ("down" if contribution < 0 else "flat"),
            "weight": abs(contribution),
        })

    factors.sort(key=lambda f: f["weight"], reverse=True)
    return factors[:5]


def _index_context():
    counts = dict(
        scoped_water_points()
        .with_entities(WaterPoint.current_status, func.count(WaterPoint.id))
        .group_by(WaterPoint.current_status)
        .all()
    )
    total = sum(counts.values())
    functional = counts.get("Functional", 0)

    points = scoped_water_points().all()
    high_risk = [wp for wp in points if wp.current_status in ("At Risk", "Non-Functional")]
    high_risk.sort(key=lambda wp: wp.risk_probability or 0.0, reverse=True)

    task_query = MaintenanceTask.query
    if current_user.role == "district_technician":
        task_query = task_query.filter_by(assigned_to_id=current_user.id)
    elif current_user.role != "admin":
        task_query = task_query.join(WaterPoint).filter(WaterPoint.district == current_user.district)
    recent_tasks = task_query.order_by(MaintenanceTask.created_at.desc()).limit(5).all()

    district_rows = {
        (district, status): count
        for district, status, count in (
            scoped_water_points()
            .with_entities(WaterPoint.district, WaterPoint.current_status, func.count(WaterPoint.id))
            .group_by(WaterPoint.district, WaterPoint.current_status)
            .all()
        )
    }
    districts = {}
    for (district, status), count in district_rows.items():
        row = districts.setdefault(district, {"total": 0, "Functional": 0, "At Risk": 0,
                                              "Non-Functional": 0, "Under Repair": 0})
        row["total"] += count
        row[status] += count
    district_health = [
        {
            "name": name,
            "total": row["total"],
            "healthy": row["Functional"],
            "at_risk": row["At Risk"] + row["Non-Functional"],
            "health_pct": round(row["Functional"] / row["total"] * 100) if row["total"] else 0,
        }
        for name, row in sorted(districts.items(), key=lambda kv: kv[1]["Functional"] / kv[1]["total"] if kv[1]["total"] else 1)
    ]

    metrics = _model_metrics()
    last_prediction = (
        db.session.query(func.max(WaterPoint.last_prediction_date)).scalar()
    )

    if current_user.role == "admin":
        from app.settings import get_setting

        district_scope = get_setting("default_district") or "Bugesera"
    else:
        district_scope = current_user.district or "Bugesera"

    return {
        "water_points": points,
        "recent_water_points": sorted(points, key=lambda wp: wp.last_updated or datetime.min, reverse=True)[:8],
        "high_risk_points": high_risk[:5],
        "recent_tasks": recent_tasks,
        "district_health": district_health,
        "district_scope": district_scope,
        "total": total,
        "at_risk": counts.get("At Risk", 0),
        "functional": functional,
        "non_functional": counts.get("Non-Functional", 0),
        "under_repair": counts.get("Under Repair", 0),
        "health_pct": round(functional / total * 100) if total else 0,
        "model_available": ml_inference.is_model_available(),
        "model_metrics": metrics,
        "last_prediction": last_prediction,
    }


@dashboard_bp.route("/")
@login_required
def index():
    return render_template("dashboard/index.html", **_index_context())


@technician_bp.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard/index.html", **_index_context())


@dashboard_bp.route("/map")
@login_required
def map_view():
    from app.settings import get_setting

    from app.rwanda_geo import BUGESERA_BOUNDARY, BUGESERA_DISTRICT

    # The GIS map always shows the case-study district (Bugesera) so that every
    # pin is scoped to one territory, for admins and district staff alike.
    default_district = get_setting("default_district", BUGESERA_DISTRICT)
    points = (
        scoped_water_points()
        .filter(WaterPoint.district == default_district)
        .order_by(WaterPoint.water_point_id)
        .all()
    )
    sectors = sorted({wp.sector for wp in points if wp.sector})
    return render_template(
        "dashboard/map.html",
        water_points=points,
        district=default_district,
        sectors=sectors,
        boundary=BUGESERA_BOUNDARY,
        model_available=ml_inference.is_model_available(),
    )


@dashboard_bp.route("/districts")
@login_required
@role_required("admin", "district_manager")
def districts():
    rows = (
        scoped_water_points()
        .with_entities(WaterPoint.district, WaterPoint.sector, WaterPoint.current_status, func.count(WaterPoint.id))
        .group_by(WaterPoint.district, WaterPoint.sector, WaterPoint.current_status)
        .all()
    )
    agg = {}
    for district, sector, status, count in rows:
        key = (district, sector or "—")
        bucket = agg.setdefault(
            key,
            {"district": district, "sector": sector or "—", "total": 0,
             "Functional": 0, "At Risk": 0, "Non-Functional": 0, "Under Repair": 0},
        )
        bucket["total"] += count
        bucket[status] += count

    districts = {}
    for (district, sector), bucket in agg.items():
        d = districts.setdefault(
            district,
            {"name": district, "total": 0, "Functional": 0, "At Risk": 0,
             "Non-Functional": 0, "Under Repair": 0, "sectors": []},
        )
        d["total"] += bucket["total"]
        for status in ("Functional", "At Risk", "Non-Functional", "Under Repair"):
            d[status] += bucket[status]
        bucket["risk_pct"] = round((bucket["At Risk"] + bucket["Non-Functional"]) / bucket["total"] * 100) if bucket["total"] else 0
        d["sectors"].append(bucket)

    for d in districts.values():
        d["sectors"].sort(key=lambda s: s["risk_pct"], reverse=True)
        d["health_pct"] = round(d["Functional"] / d["total"] * 100) if d["total"] else 0
        d["risk_pct"] = round((d["At Risk"] + d["Non-Functional"]) / d["total"] * 100) if d["total"] else 0

    district_list = sorted(districts.values(), key=lambda d: d["risk_pct"], reverse=True)
    return render_template("dashboard/districts.html", districts=district_list)


@dashboard_bp.route("/water-points/<int:wp_id>")
@login_required
def water_point_detail(wp_id):
    water_point = db.session.get(WaterPoint, wp_id)
    if water_point is None:
        abort(404)
    if current_user.role != "admin" and current_user.district != water_point.district:
        abort(403)

    tasks = (
        MaintenanceTask.query.filter_by(water_point_id=water_point.id)
        .order_by(MaintenanceTask.created_at.desc())
        .all()
    )
    factors = risk_factors_for(water_point)
    risk_pct = round((water_point.risk_probability or 0) * 100)

    return render_template(
        "dashboard/water_point_detail.html",
        wp=water_point,
        tasks=tasks,
        factors=factors,
        risk_pct=risk_pct,
    )


@dashboard_bp.route("/water-points")
@login_required
def water_points():
    upload_form = None
    if current_user.role in ("admin", "district_technician", "district_manager"):
        upload_form = DataUploadForm()
        upload_form.district.choices = available_district_choices()

        from app.settings import get_setting

        default_district = get_setting("default_district", "Bugesera")
        if default_district and any(default_district == value for value, _ in upload_form.district.choices):
            upload_form.district.data = default_district

    points = scoped_water_points().order_by(WaterPoint.last_updated.desc()).all()
    at_risk_or_worse = sum(1 for wp in points if wp.current_status in ("At Risk", "Non-Functional"))
    ai_summary = {"total": len(points), "at_risk_or_worse": at_risk_or_worse} if points else None

    return render_template(
        "dashboard/water_points.html",
        water_points=points,
        ai_summary=ai_summary,
        upload_form=upload_form,
    )


@dashboard_bp.route("/predict", methods=["GET", "POST"])
@login_required
def predict():
    """Simple predict page: pick a water point from a dropdown, get its risk
    prediction instantly. No CSV upload required."""
    from app.ml_inference import is_model_available, predict_single
    from app.settings import get_setting
    from sqlalchemy import func

    points = scoped_water_points().order_by(WaterPoint.water_point_id).all()
    catchment_pressures = dict(
        db.session.query(WaterSource.catchment, func.sum(WaterSource.industrial_pressure_score))
        .filter(WaterSource.catchment.isnot(None))
        .group_by(WaterSource.catchment)
        .all()
    )

    result = None
    if request.method == "POST":
        point_id = request.form.get("water_point_id")
        selected = db.session.get(WaterPoint, int(point_id)) if point_id else None
        if selected is None:
            flash("Please select a valid water point.", "danger")
            return redirect(url_for("dashboard.predict"))

        if not is_model_available():
            flash("No trained model available. Run `flask train-model --data <file>` first.", "warning")
            return redirect(url_for("dashboard.predict"))

        catchment_pressure = 0.0
        if selected.water_source and selected.water_source.catchment:
            catchment_pressure = catchment_pressures.get(selected.water_source.catchment, 0.0)

        prediction = predict_single(selected, catchment_pressure=catchment_pressure)
        if prediction is None:
            flash("Prediction failed. Check server logs for details.", "danger")
            return redirect(url_for("dashboard.predict"))

        selected.risk_probability = prediction.probability
        selected.current_status = prediction.status
        selected.prediction_confidence = prediction.confidence
        selected.last_prediction_date = utcnow()
        db.session.commit()

        threshold = get_setting("risk_threshold", 0.5)
        result = {
            "water_point": selected,
            "status": prediction.status,
            "probability": round(prediction.probability * 100, 1),
            "confidence": prediction.confidence,
            "threshold": threshold,
            "factors": risk_factors_for(selected),
        }

    return render_template(
        "dashboard/predict.html",
        water_points=points,
        result=result,
        model_available=ml_inference.is_model_available(),
    )


@dashboard_bp.route("/rerun-predictions", methods=["POST"])
@login_required
@role_required("admin")
def rerun_predictions():
    if not ml_inference.is_model_available():
        flash("No trained model available. Run `flask train-model --data <file>` first.", "warning")
        return redirect(url_for("dashboard.water_points"))

    water_points = WaterPoint.query.all()
    catchment_pressures = dict(
        db.session.query(WaterSource.catchment, func.sum(WaterSource.industrial_pressure_score))
        .filter(WaterSource.catchment.isnot(None))
        .group_by(WaterSource.catchment)
        .all()
    )
    apply_predictions(water_points, catchment_pressures)
    db.session.add(
        AuditLog(
            user_id=current_user.id,
            action="rerun_predictions",
            details=f"Re-ran AI predictions for {len(water_points)} water points",
        )
    )
    db.session.commit()
    flash(f"Re-ran predictions for {len(water_points)} water points.", "success")
    return redirect(url_for("dashboard.water_points"))


@dashboard_bp.route("/upload", methods=["GET", "POST"])
@login_required
@role_required("admin", "district_technician", "district_manager")
def upload_data():
    form = DataUploadForm()
    form.district.choices = available_district_choices()

    if request.method == "GET" and not form.district.data:
        from app.settings import get_setting

        default_district = get_setting("default_district", "Bugesera")
        if default_district and any(default_district == value for value, _ in form.district.choices):
            form.district.data = default_district

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
    """Districts offered in upload/filter dropdowns.

    Amazi is scoped to a single district (Bugesera by default), so once any
    data is loaded the dropdowns list only the districts actually present in
    the database. Before any data exists the known districts are offered so a
    fresh install (and the settings tests) can still pick a default district.
    """
    if current_user.role == "admin":
        existing = [d[0] for d in db.session.query(WaterPoint.district).distinct() if d[0]]
        if existing:
            return [("", "Select District")] + [(district, district) for district in sorted(existing)]

        from app.settings import get_setting

        default_district = get_setting("default_district") or "Bugesera"
        districts = sorted(set([default_district] + [choice[0] for choice in DISTRICT_CHOICES if choice[0]]))
        return [("", "Select District")] + [(district, district) for district in districts]
    return [(current_user.district, current_user.district)]


def process_water_point_data(df, district, user_id):
    required = {"water_point_id", "latitude", "longitude", "technology_type"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

    model_available = ml_inference.is_model_available()
    catchment_pressures = {}
    if model_available:
        catchment_pressures = dict(
            db.session.query(WaterSource.catchment, func.sum(WaterSource.industrial_pressure_score))
            .filter(WaterSource.catchment.isnot(None))
            .group_by(WaterSource.catchment)
            .all()
        )

    source_map = _build_source_map(df)
    water_points = []

    for _, row in df.iterrows():
        raw_point_id = str(row.get("water_point_id")).strip()
        latitude = float(row.get("latitude"))
        longitude = float(row.get("longitude"))
        water_point = find_matching_water_point(raw_point_id, latitude, longitude, district)
        if water_point is None:
            water_point = WaterPoint(water_point_id=raw_point_id, uploaded_by_id=user_id)
            db.session.add(water_point)

        water_point.district = district
        water_point.sector = value_or_none(row.get("sector"))
        water_point.cell = value_or_none(row.get("cell"))
        water_point.latitude = latitude
        water_point.longitude = longitude
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
        water_points.append(water_point)

    if model_available and water_points:
        apply_predictions(water_points, catchment_pressures)

    db.session.commit()
    return len(water_points)


def apply_predictions(water_points, catchment_pressures=None):
    """Run the trained model over `water_points` in one vectorized batch and
    write predicted_status/risk_probability/prediction_confidence back onto
    each ORM object. Callers (upload, bulk re-run) are responsible for
    checking ml_inference.is_model_available() first and for committing.
    """
    catchment_pressures = catchment_pressures or {}
    frame = pd.DataFrame(
        [
            {
                "year_installed": wp.year_installed,
                "population_served": wp.population_served,
                "monthly_rainfall": wp.monthly_rainfall,
                "technology_type": wp.technology_type,
                "catchment_pressure": (
                    catchment_pressures.get(wp.water_source.catchment, 0.0)
                    if wp.water_source and wp.water_source.catchment
                    else 0.0
                ),
            }
            for wp in water_points
        ]
    )
    predictions = ml_inference.predict_batch(frame)
    now = utcnow()
    for water_point, (_, prediction) in zip(water_points, predictions.iterrows()):
        water_point.current_status = prediction["predicted_status"]
        water_point.risk_probability = float(prediction["risk_probability"])
        water_point.prediction_confidence = prediction["prediction_confidence"]
        water_point.last_prediction_date = now


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
    # Toggle feature — DISABLED (commented out).
    # from app.ml_inference import is_model_enabled
    # if not is_model_enabled():
    #     return None
    model_path = Path("models") / "water_point_model.pkl"
    if not model_path.exists():
        return None
    try:
        return joblib.load(model_path)
    except Exception:
        return None


def predict_risk(model, water_point, catchment_pressures=None):
    """Single ad-hoc prediction (used by the /api/predict endpoint), kept
    separate from the batch path in apply_predictions() above. Returns a
    binary Functional/At Risk label driven by the admin-configurable
    risk_threshold setting, rather than the three-way Functional/At Risk/
    Non-Functional bucketing the upload flow writes to current_status.
    """
    from app.settings import get_setting

    catchment_pressure = 0.0
    if getattr(water_point, "water_source", None) and water_point.water_source.catchment:
        catchment_pressure = catchment_pressures.get(water_point.water_source.catchment, 0.0) if catchment_pressures is not None else 0.0

    metadata = ml_inference.model_metadata() or {}
    feature_names = metadata.get("feature_names", FEATURE_NAMES)
    features = build_feature_row(
        year_installed=water_point.year_installed,
        population_served=water_point.population_served,
        monthly_rainfall=water_point.monthly_rainfall,
        technology_type=water_point.technology_type,
        catchment_pressure=catchment_pressure,
        metadata=metadata,
    )
    probability = model.predict_proba([[features[name] for name in feature_names]])[0]
    risk_prob = float(probability[1] if len(probability) > 1 else probability[0])
    threshold = get_setting("risk_threshold", 0.5)
    return ("At Risk" if risk_prob > threshold else "Functional"), risk_prob
