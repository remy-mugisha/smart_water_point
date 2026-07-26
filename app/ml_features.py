"""Shared feature engineering for the water point failure-risk model.

This module is the single source of truth for turning a water point's raw
attributes into the numeric feature vector the model consumes. Both the
training pipeline (`app/ml_train.py`, which fits category encodings and
imputation values from a labeled dataset) and the inference module
(`app/ml_inference.py`, which applies those already-fitted values to one row
or a whole dataframe at prediction time) import from here, so the two can
never silently drift apart.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

FEATURE_NAMES = [
    "age",
    "population_served",
    "monthly_rainfall",
    "tech_encoded",
    "catchment_pressure",
    "interaction_age_pop",
    "interaction_age_rain",
    "rainy_season_flag",
    "population_density_category",
]

RAINY_SEASON_RAINFALL_MM = 50.0

# Training CSVs may reuse the operational upload column name ("rainfall")
# instead of the model's column name ("monthly_rainfall"); accept either.
COLUMN_ALIASES = {"rainfall": "monthly_rainfall"}


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Apply COLUMN_ALIASES so downstream code only has to know one name per field."""
    return df.rename(columns={old: new for old, new in COLUMN_ALIASES.items() if old in df.columns and new not in df.columns})


def reference_year() -> int:
    return datetime.now().year


def normalize_technology(value: Any) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "unknown"
    return str(value).strip().lower().replace(" ", "_")


def fit_feature_metadata(df: pd.DataFrame) -> dict:
    """Learn everything inference needs but can't compute from a single row:
    the technology_type -> code mapping, the fallback code for categories
    never seen in training, population-served percentile cut points, and
    medians used to impute missing numeric values. Returns a plain, JSON/
    joblib-serializable dict.
    """
    tech_series = df["technology_type"].map(normalize_technology) if "technology_type" in df.columns else pd.Series(dtype=str)
    tech_counts = tech_series.value_counts()
    categories = {name: idx for idx, name in enumerate(tech_counts.index.tolist())}
    if not categories:
        categories = {"unknown": 0}
    fallback_code = categories[tech_counts.index[0]] if len(tech_counts) else 0

    population = pd.to_numeric(df.get("population_served"), errors="coerce").dropna()
    if len(population) >= 3:
        p33, p66 = float(population.quantile(0.33)), float(population.quantile(0.66))
    else:
        p33, p66 = 300.0, 800.0

    return {
        "feature_names": FEATURE_NAMES,
        "technology_categories": categories,
        "technology_fallback_code": fallback_code,
        "population_density_thresholds": {"p33": p33, "p66": p66},
        "medians": {
            "year_installed": _safe_median(df.get("year_installed"), default=reference_year() - 10),
            "population_served": _safe_median(df.get("population_served"), default=500),
            "monthly_rainfall": _safe_median(df.get("monthly_rainfall"), default=70),
        },
    }


def _safe_median(series, default):
    if series is None:
        return float(default)
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    return float(numeric.median()) if len(numeric) else float(default)


def _population_density_category(population_served: float, thresholds: dict) -> int:
    if population_served < thresholds["p33"]:
        return 0  # low
    if population_served < thresholds["p66"]:
        return 1  # medium
    return 2  # high


def build_feature_row(
    *,
    year_installed,
    population_served,
    monthly_rainfall,
    technology_type,
    catchment_pressure,
    metadata: dict,
) -> dict:
    """Build one feature dict for a single water point. Missing numeric inputs
    fall back to the medians captured at training time (or sane defaults if
    no model/metadata has been trained yet), so a row with incomplete data
    still produces a usable prediction instead of raising.
    """
    medians = metadata.get("medians", {})
    year_installed = year_installed if year_installed not in (None, 0) else medians.get("year_installed", reference_year() - 10)
    population_served = population_served if population_served not in (None,) else medians.get("population_served", 500)
    monthly_rainfall = monthly_rainfall if monthly_rainfall not in (None,) else medians.get("monthly_rainfall", 70)
    catchment_pressure = catchment_pressure or 0.0

    age = max(reference_year() - int(year_installed), 0)
    categories = metadata.get("technology_categories", {"unknown": 0})
    fallback_code = metadata.get("technology_fallback_code", 0)
    tech_encoded = categories.get(normalize_technology(technology_type), fallback_code)
    thresholds = metadata.get("population_density_thresholds", {"p33": 300.0, "p66": 800.0})

    return {
        "age": age,
        "population_served": float(population_served),
        "monthly_rainfall": float(monthly_rainfall),
        "tech_encoded": float(tech_encoded),
        "catchment_pressure": float(catchment_pressure),
        "interaction_age_pop": age * float(population_served),
        "interaction_age_rain": age * float(monthly_rainfall),
        "rainy_season_flag": 1.0 if float(monthly_rainfall) > RAINY_SEASON_RAINFALL_MM else 0.0,
        "population_density_category": float(_population_density_category(float(population_served), thresholds)),
    }


def build_feature_matrix(df: pd.DataFrame, metadata: dict) -> pd.DataFrame:
    """Vectorized equivalent of build_feature_row for a whole dataframe.
    Expects (optionally missing) columns: year_installed, population_served,
    monthly_rainfall, technology_type, catchment_pressure.
    """
    df = normalize_columns(df)
    medians = metadata.get("medians", {})

    year_installed = pd.to_numeric(df.get("year_installed"), errors="coerce").fillna(medians.get("year_installed", reference_year() - 10))
    population_served = pd.to_numeric(df.get("population_served"), errors="coerce").fillna(medians.get("population_served", 500))
    monthly_rainfall = pd.to_numeric(df.get("monthly_rainfall"), errors="coerce").fillna(medians.get("monthly_rainfall", 70))
    catchment_pressure = pd.to_numeric(df.get("catchment_pressure"), errors="coerce").fillna(0.0) if "catchment_pressure" in df.columns else pd.Series(0.0, index=df.index)

    age = (reference_year() - year_installed).clip(lower=0)

    categories = metadata.get("technology_categories", {"unknown": 0})
    fallback_code = metadata.get("technology_fallback_code", 0)
    tech_source = df["technology_type"] if "technology_type" in df.columns else pd.Series("unknown", index=df.index)
    tech_encoded = tech_source.map(normalize_technology).map(lambda t: categories.get(t, fallback_code)).astype(float)

    thresholds = metadata.get("population_density_thresholds", {"p33": 300.0, "p66": 800.0})
    density_category = population_served.apply(lambda p: _population_density_category(p, thresholds))

    features = pd.DataFrame(
        {
            "age": age,
            "population_served": population_served,
            "monthly_rainfall": monthly_rainfall,
            "tech_encoded": tech_encoded,
            "catchment_pressure": catchment_pressure,
            "interaction_age_pop": age * population_served,
            "interaction_age_rain": age * monthly_rainfall,
            "rainy_season_flag": (monthly_rainfall > RAINY_SEASON_RAINFALL_MM).astype(float),
            "population_density_category": density_category.astype(float),
        },
        index=df.index,
    )
    return features[FEATURE_NAMES]


def remove_outliers_iqr(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Drop rows outside 1.5*IQR of the given columns. Used only at training
    time — inference must accept whatever data it's given."""
    mask = pd.Series(True, index=df.index)
    for column in columns:
        if column not in df.columns:
            continue
        series = pd.to_numeric(df[column], errors="coerce")
        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0 or pd.isna(iqr):
            continue
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        mask &= series.between(lower, upper) | series.isna()
    return df[mask]
