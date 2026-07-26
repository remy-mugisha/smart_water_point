"""Training pipeline for the water point failure-risk model.

Pure Python/pandas/sklearn — no Flask app context required — so it can run
standalone from the CLI (`flask train-model --data ...`) and be unit tested
without spinning up the web app. Produces the artifacts app/ml_inference.py
loads at prediction time: the fitted model pipeline, feature metadata, and a
metrics report consumed by the admin "Model Performance" page.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")  # headless: this runs from a CLI command, never a browser
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    RocCurveDisplay,
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.ml_features import (
    FEATURE_NAMES,
    build_feature_matrix,
    fit_feature_metadata,
    normalize_columns,
    remove_outliers_iqr,
)

logger = logging.getLogger(__name__)

MODELS_DIR = Path("models")
IMAGES_DIR = Path("static/images")
TARGET_COLUMN = "current_status"
POSITIVE_LABEL = "Non-Functional"  # what probability=1 means: at risk of / already failed
REQUIRED_COLUMNS = {"year_installed", "population_served", TARGET_COLUMN}
MAX_MISSING_FRACTION = 0.30


def load_dataset(data_path: str | Path) -> pd.DataFrame:
    path = Path(data_path)
    logger.info("Loading training data from %s", path)
    df = pd.read_csv(path) if path.suffix.lower() == ".csv" else pd.read_excel(path)
    df = normalize_columns(df)

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Training data is missing required columns: {', '.join(sorted(missing))}")

    df = df[df[TARGET_COLUMN].isin(["Functional", "Non-Functional"])].copy()
    logger.info("Loaded %d labeled rows (Functional/Non-Functional only)", len(df))
    return df


def clean_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Drop rows missing too much data, median-impute the rest, then strip
    age/population outliers via IQR. Mirrors the spec: >30% missing -> drop,
    otherwise fill with median."""
    numeric_cols = [c for c in ("year_installed", "population_served", "monthly_rainfall") if c in df.columns]
    missing_fraction = df[numeric_cols].isna().mean(axis=1)
    before = len(df)
    df = df[missing_fraction <= MAX_MISSING_FRACTION].copy()
    logger.info("Dropped %d rows with >%.0f%% missing values", before - len(df), MAX_MISSING_FRACTION * 100)

    for col in numeric_cols:
        median = pd.to_numeric(df[col], errors="coerce").median()
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(median)

    df["age"] = datetime.now().year - df["year_installed"]
    before = len(df)
    df = remove_outliers_iqr(df, ["age", "population_served"])
    logger.info("Dropped %d outlier rows (IQR on age/population_served)", before - len(df))
    return df


def train_model(
    data_path: str | Path,
    test_size: float = 0.2,
    random_state: int = 42,
    output_dir: str | Path = MODELS_DIR,
    images_dir: str | Path = IMAGES_DIR,
) -> dict:
    """Run the full pipeline end-to-end and return the metrics dict (also
    written to <output_dir>/training_metrics.json)."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    output_dir, images_dir = Path(output_dir), Path(images_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    df = load_dataset(data_path)
    df = clean_dataset(df)
    if len(df) < 10:
        raise ValueError(f"Only {len(df)} usable rows after cleaning — need at least 10 to train.")

    logger.info("Step: fitting feature metadata (technology encoding, population percentiles)")
    metadata = fit_feature_metadata(df)

    logger.info("Step: engineering features")
    X = build_feature_matrix(df, metadata)
    y = (df[TARGET_COLUMN] == POSITIVE_LABEL).astype(int)

    logger.info("Step: train/test split (%.0f%% test, stratified)", test_size * 100)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )

    logger.info("Step: training Logistic Regression (class_weight=balanced)")
    pipeline = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(class_weight="balanced", max_iter=1000, random_state=random_state)),
        ]
    )
    pipeline.fit(X_train, y_train)

    logger.info("Step: evaluating on held-out test set")
    y_pred = pipeline.predict(X_test)
    y_proba = pipeline.predict_proba(X_test)[:, 1]

    metrics = {
        "trained_at": datetime.now().isoformat(timespec="seconds"),
        "data_path": str(data_path),
        "positive_label": POSITIVE_LABEL,
        "dataset_size": len(df),
        "train_size": len(X_train),
        "test_size": len(X_test),
        "class_balance": {"functional": int((y == 0).sum()), "non_functional": int((y == 1).sum())},
        "accuracy": round(accuracy_score(y_test, y_pred), 4),
        "precision": round(precision_score(y_test, y_pred, zero_division=0), 4),
        "recall": round(recall_score(y_test, y_pred, zero_division=0), 4),
        "f1_score": round(f1_score(y_test, y_pred, zero_division=0), 4),
        "roc_auc": round(roc_auc_score(y_test, y_proba), 4) if len(set(y_test)) > 1 else None,
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        "feature_names": FEATURE_NAMES,
        "coefficients": dict(zip(FEATURE_NAMES, pipeline.named_steps["clf"].coef_[0].round(4).tolist())),
    }
    logger.info(
        "Metrics: accuracy=%.3f precision=%.3f recall=%.3f f1=%.3f roc_auc=%s",
        metrics["accuracy"], metrics["precision"], metrics["recall"], metrics["f1_score"], metrics["roc_auc"],
    )
    logger.info("Confusion matrix [[TN, FP], [FN, TP]]: %s", metrics["confusion_matrix"])

    _save_confusion_matrix_plot(y_test, y_pred, images_dir / "confusion_matrix.png")
    _save_roc_curve_plot(pipeline, X_test, y_test, images_dir / "roc_curve.png")
    _save_feature_importance_plot(metrics["coefficients"], images_dir / "feature_importance.png")

    joblib.dump(pipeline, output_dir / "water_point_model.pkl")
    joblib.dump(pipeline.named_steps["scaler"], output_dir / "scaler.pkl")
    joblib.dump(metadata, output_dir / "feature_names.pkl")
    with open(output_dir / "training_metrics.json", "w", encoding="utf-8") as fh:
        json.dump(metrics, fh, indent=2)

    logger.info("Saved model, scaler, feature metadata, and metrics to %s", output_dir)
    _log_sample_predictions(pipeline, X_test, y_test)
    return metrics


def _save_confusion_matrix_plot(y_test, y_pred, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(4.5, 4))
    ConfusionMatrixDisplay(confusion_matrix(y_test, y_pred), display_labels=["Functional", "Non-Functional"]).plot(
        ax=ax, cmap="Blues", colorbar=False
    )
    ax.set_title("Confusion Matrix")
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def _save_roc_curve_plot(pipeline, X_test, y_test, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(5, 4))
    if len(set(y_test)) > 1:
        RocCurveDisplay.from_estimator(pipeline, X_test, y_test, ax=ax)
    ax.plot([0, 1], [0, 1], linestyle="--", color="gray", label="Chance")
    ax.set_title("ROC Curve")
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def _save_feature_importance_plot(coefficients: dict, path: Path) -> None:
    names = list(coefficients.keys())
    values = list(coefficients.values())
    colors = ["#dc2626" if v > 0 else "#16a34a" for v in values]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.barh(names, values, color=colors)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Coefficient (positive = pushes toward Non-Functional)")
    ax.set_title("Feature Importance (Logistic Regression coefficients)")
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def _log_sample_predictions(pipeline, X_test, y_test, n: int = 5) -> None:
    sample = X_test.head(n)
    probabilities = pipeline.predict_proba(sample)[:, 1]
    logger.info("Sample predictions (probability of Non-Functional):")
    for (idx, row), prob, actual in zip(sample.iterrows(), probabilities, y_test.head(n)):
        logger.info(
            "  row %s: predicted=%.1f%% actual=%s",
            idx, prob * 100, "Non-Functional" if actual == 1 else "Functional",
        )
