"""Prediction module for the water point failure-risk model.

Deliberately Flask- and database-agnostic (like report_queries.py): it knows
nothing about WaterPoint, requests, or SQLAlchemy sessions. app/dashboard.py
is the glue layer — it builds the plain dict/DataFrame this module expects
from ORM objects, calls into here, and writes the results back onto the
model. That split keeps this module trivially unit-testable and reusable
from the training/EDA scripts without booting the web app.

The model is cached as a module-level singleton and only re-loaded when the
pickle's mtime changes, so a `flask train-model` re-run is picked up by a
running app without a restart, but a normal request doesn't re-read the
file from disk every time.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import joblib
import pandas as pd

from app.ml_features import build_feature_matrix, build_feature_row

logger = logging.getLogger(__name__)

MODEL_PATH = Path("models/water_point_model.pkl")
METADATA_PATH = Path("models/feature_names.pkl")

# Same cut points as the Predictive Risk report's Low/Medium/High buckets
# (see app/report_queries.py), reused here as the Functional / At Risk /
# Non-Functional status boundaries so a water point's dashboard status and
# its report risk bucket are always describing the same probability.
RISK_LOW_MAX = 0.33
RISK_MEDIUM_MAX = 0.66

HIGH_CONFIDENCE_LOW = 0.2
HIGH_CONFIDENCE_HIGH = 0.8


@dataclass
class Prediction:
    probability: float
    status: str
    confidence: str


class _ModelCache:
    model: Any = None
    metadata: Optional[dict] = None
    mtime: Optional[float] = None


_cache = _ModelCache()

# Admin testing switch. When False the model is "offline": is_model_available()
# reports False and predict_single/predict_batch return their no-model
# placeholder so callers degrade gracefully. The cached model is kept so
# flipping back online is instant.
MODEL_ENABLED = True


def _load_if_needed():
    if not MODEL_PATH.exists() or not METADATA_PATH.exists():
        _cache.model, _cache.metadata, _cache.mtime = None, None, None
        return None, None

    mtime = MODEL_PATH.stat().st_mtime
    if _cache.model is None or _cache.mtime != mtime:
        try:
            _cache.model = joblib.load(MODEL_PATH)
            _cache.metadata = joblib.load(METADATA_PATH)
            _cache.mtime = mtime
            logger.info("Loaded prediction model from %s (mtime=%s)", MODEL_PATH, mtime)
        except Exception:
            logger.warning("Failed to load prediction model from %s", MODEL_PATH, exc_info=True)
            _cache.model, _cache.metadata, _cache.mtime = None, None, None
    return _cache.model, _cache.metadata


def is_model_available() -> bool:
    if not MODEL_ENABLED:
        return False
    model, _ = _load_if_needed()
    return model is not None


def is_model_enabled() -> bool:
    return MODEL_ENABLED


def toggle_model(enabled: bool) -> bool:
    """Enable or disable predictions without discarding the cached model.

    Disabled (offline) mode makes is_model_available() report False and makes
    predict_single/predict_batch return their no-model placeholder, so callers
    degrade gracefully while the admin testing switch is off.
    """
    global MODEL_ENABLED
    MODEL_ENABLED = bool(enabled)
    logger.info("Prediction model %s", "enabled" if MODEL_ENABLED else "disabled")
    return MODEL_ENABLED


def model_metadata() -> Optional[dict]:
    _, metadata = _load_if_needed()
    return metadata


def classify_status(probability: float) -> str:
    if probability < RISK_LOW_MAX:
        return "Functional"
    if probability < RISK_MEDIUM_MAX:
        return "At Risk"
    return "Non-Functional"


def confidence_level(probability: float) -> str:
    return "High" if probability <= HIGH_CONFIDENCE_LOW or probability >= HIGH_CONFIDENCE_HIGH else "Medium"


def _field(row: Any, name: str, default=None):
    """Read `name` off a dict, a pandas Series, or an object with attributes
    (e.g. a WaterPoint ORM instance) — whichever predict_single is handed."""
    if isinstance(row, dict):
        return row.get(name, default)
    if isinstance(row, pd.Series):
        return row.get(name, default)
    return getattr(row, name, default)


def predict_single(row: Any, catchment_pressure: float = 0.0) -> Optional[Prediction]:
    """Predict for one water point. `row` may be a dict, pandas Series, or an
    object exposing year_installed/population_served/monthly_rainfall/
    technology_type attributes (a WaterPoint instance satisfies this).
    Returns None (with a warning logged) if no trained model is available or
    the model is offline — callers must treat prediction as optional, never
    load-bearing.
    """
    if not MODEL_ENABLED:
        logger.warning("predict_single called but the model is offline; skipping.")
        return None
    model, metadata = _load_if_needed()
    if model is None:
        logger.warning("predict_single called but no trained model is available; skipping.")
        return None

    features = build_feature_row(
        year_installed=_field(row, "year_installed"),
        population_served=_field(row, "population_served"),
        monthly_rainfall=_field(row, "monthly_rainfall"),
        technology_type=_field(row, "technology_type"),
        catchment_pressure=catchment_pressure,
        metadata=metadata,
    )
    frame = pd.DataFrame([features])[metadata["feature_names"]]

    try:
        probability = float(model.predict_proba(frame)[0][1])
    except Exception:
        logger.exception("Prediction failed for row %s", _field(row, "water_point_id", "?"))
        return None

    return Prediction(probability=probability, status=classify_status(probability), confidence=confidence_level(probability))


def predict_batch(df: pd.DataFrame) -> pd.DataFrame:
    """Vectorized prediction for many rows at once — the path used by CSV
    upload and bulk re-prediction, since scoring a whole feature matrix in
    one predict_proba() call is what keeps 1000+ rows well under a few
    seconds (a Python-level per-row loop would not).

    Expects (optionally missing) columns: year_installed, population_served,
    monthly_rainfall, technology_type, catchment_pressure. Returns a copy of
    df with risk_probability, predicted_status, prediction_confidence added
    (all NaN/None if no model is available or the model is offline).
    """
    result = df.copy()
    if not MODEL_ENABLED:
        logger.warning("predict_batch called but the model is offline; skipping %d rows.", len(df))
        result["risk_probability"] = None
        result["predicted_status"] = None
        result["prediction_confidence"] = None
        return result
    model, metadata = _load_if_needed()
    if model is None:
        logger.warning("predict_batch called but no trained model is available; skipping %d rows.", len(df))
        result["risk_probability"] = None
        result["predicted_status"] = None
        result["prediction_confidence"] = None
        return result

    features = build_feature_matrix(df, metadata)
    probabilities = model.predict_proba(features)[:, 1]
    result["risk_probability"] = probabilities
    result["predicted_status"] = [classify_status(p) for p in probabilities]
    result["prediction_confidence"] = [confidence_level(p) for p in probabilities]
    return result
