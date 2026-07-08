from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from app import db
from app.dashboard import load_prediction_model, predict_risk, process_water_point_data
from app.models import WaterPoint
from app.utils import api_role_required, scoped_by_district, user_can_access_district

api_bp = Blueprint("api", __name__)


@api_bp.route("/water-points", methods=["GET"])
@login_required
def get_water_points():
    query = scoped_by_district(WaterPoint.query, WaterPoint.district)
    return jsonify([serialize_water_point(wp) for wp in query.all()])


@api_bp.route("/water-points/<string:point_id>/status", methods=["PUT"])
@login_required
@api_role_required("admin", "district_technician", "district_manager")
def update_status(point_id):
    water_point = WaterPoint.query.filter_by(water_point_id=point_id).first()
    if water_point is None:
        return jsonify({"error": "Water point not found"}), 404
    if not user_can_access_district(water_point.district):
        return jsonify({"error": "Permission denied"}), 403

    status = (request.json or {}).get("status")
    if status not in {"Functional", "At Risk", "Non-Functional"}:
        return jsonify({"error": "Invalid status"}), 400

    water_point.current_status = status
    db.session.commit()
    return jsonify({"success": True, "message": "Status updated"})


@api_bp.route("/upload", methods=["POST"])
@login_required
@api_role_required("admin", "district_technician", "district_manager")
def upload_api():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    district = request.form.get("district")
    if not district:
        return jsonify({"error": "District required"}), 400
    if not user_can_access_district(district):
        return jsonify({"error": "Permission denied"}), 403

    file = request.files["file"]
    try:
        import pandas as pd

        df = pd.read_csv(file) if file.filename.lower().endswith(".csv") else pd.read_excel(file)
        count = process_water_point_data(df, district, current_user.id)
        return jsonify({"success": True, "processed": count})
    except Exception as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 500


@api_bp.route("/predict", methods=["POST"])
@login_required
@api_role_required("admin", "district_technician", "district_manager")
def predict():
    model = load_prediction_model()
    if model is None:
        return jsonify({"error": "Prediction model not found"}), 404

    results = []
    for point_id in (request.json or {}).get("point_ids", []):
        wp = WaterPoint.query.filter_by(water_point_id=point_id).first()
        if wp and user_can_access_district(wp.district):
            prediction, probability = predict_risk(model, wp)
            results.append({"id": point_id, "prediction": prediction, "probability": probability})

    return jsonify(results)


def serialize_water_point(wp):
    return {
        "id": wp.water_point_id,
        "district": wp.district,
        "sector": wp.sector,
        "cell": wp.cell,
        "latitude": wp.latitude,
        "longitude": wp.longitude,
        "status": wp.current_status,
        "risk_probability": wp.risk_probability,
        "technology_type": wp.technology_type,
        "population_served": wp.population_served,
        "last_updated": wp.last_updated.isoformat() if wp.last_updated else None,
    }
