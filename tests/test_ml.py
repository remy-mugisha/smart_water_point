import time

import pandas as pd
import pytest

from app import ml_inference
from app.ml_features import FEATURE_NAMES, build_feature_matrix, build_feature_row, fit_feature_metadata
from app.ml_train import clean_dataset, load_dataset, train_model


@pytest.fixture(autouse=True)
def reset_model_cache(monkeypatch, tmp_path):
    """ml_inference caches the loaded model as module-level state keyed on
    the pickle's mtime. Without pointing MODEL_PATH/METADATA_PATH at a
    per-test tmp_path and clearing the cache, one test's trained model would
    leak into the next test that merely checks for "no model available".
    """
    monkeypatch.setattr(ml_inference, "MODEL_PATH", tmp_path / "water_point_model.pkl")
    monkeypatch.setattr(ml_inference, "METADATA_PATH", tmp_path / "feature_names.pkl")
    ml_inference._cache.model = None
    ml_inference._cache.metadata = None
    ml_inference._cache.mtime = None
    yield
    ml_inference._cache.model = None
    ml_inference._cache.metadata = None
    ml_inference._cache.mtime = None


def _sample_df(n=40, seed=7):
    import numpy as np

    rng = np.random.default_rng(seed)
    year_installed = rng.integers(2005, 2024, n)
    population_served = rng.integers(80, 1600, n)
    monthly_rainfall = rng.uniform(15, 130, n)
    technology_type = rng.choice(["hand_pump", "borehole", "solar_pump"], n)
    age = 2026 - year_installed
    risk = 0.05 * age + 0.001 * population_served - 0.02 * monthly_rainfall + rng.normal(0, 2, n)
    status = pd.Series(risk).rank(pct=True).apply(lambda p: "Non-Functional" if p > 0.6 else "Functional")
    return pd.DataFrame(
        {
            "water_point_id": [f"WP-{i}" for i in range(n)],
            "year_installed": year_installed,
            "population_served": population_served,
            "monthly_rainfall": monthly_rainfall,
            "technology_type": technology_type,
            "current_status": status,
        }
    )


class TestFeatureEngineering:
    def test_build_feature_row_shape(self):
        metadata = {
            "feature_names": FEATURE_NAMES,
            "technology_categories": {"borehole": 0, "hand_pump": 1},
            "technology_fallback_code": 0,
            "population_density_thresholds": {"p33": 300, "p66": 800},
            "medians": {"year_installed": 2015, "population_served": 500, "monthly_rainfall": 70},
        }
        row = build_feature_row(
            year_installed=2010, population_served=900, monthly_rainfall=80,
            technology_type="Hand_Pump", catchment_pressure=1.5, metadata=metadata,
        )
        assert set(row.keys()) == set(metadata["feature_names"])
        assert row["tech_encoded"] == 1  # normalized "hand_pump" matched despite mixed case
        assert row["population_density_category"] == 2  # 900 > p66=800
        assert row["rainy_season_flag"] == 1.0

    def test_build_feature_row_handles_missing_values(self):
        metadata = fit_feature_metadata(_sample_df())
        row = build_feature_row(
            year_installed=None, population_served=None, monthly_rainfall=None,
            technology_type=None, catchment_pressure=None, metadata=metadata,
        )
        assert all(pd.notna(v) for v in row.values())

    def test_build_feature_matrix_matches_row_builder(self):
        df = _sample_df(n=5)
        metadata = fit_feature_metadata(df)
        matrix = build_feature_matrix(df, metadata)
        assert list(matrix.columns) == metadata["feature_names"]
        assert len(matrix) == 5

        first_row = build_feature_row(
            year_installed=df.iloc[0]["year_installed"],
            population_served=df.iloc[0]["population_served"],
            monthly_rainfall=df.iloc[0]["monthly_rainfall"],
            technology_type=df.iloc[0]["technology_type"],
            catchment_pressure=0.0,
            metadata=metadata,
        )
        for name in metadata["feature_names"]:
            assert matrix.iloc[0][name] == pytest.approx(first_row[name])

    def test_unseen_technology_maps_to_fallback(self):
        metadata = fit_feature_metadata(_sample_df())
        row = build_feature_row(
            year_installed=2015, population_served=400, monthly_rainfall=60,
            technology_type="never_seen_before", catchment_pressure=0.0, metadata=metadata,
        )
        assert row["tech_encoded"] == metadata["technology_fallback_code"]


class TestTrainingPipeline:
    def test_train_model_runs_end_to_end(self, tmp_path):
        data_path = tmp_path / "training.csv"
        _sample_df(n=60).to_csv(data_path, index=False)

        metrics = train_model(
            data_path, test_size=0.25, random_state=1,
            output_dir=tmp_path / "models", images_dir=tmp_path / "images",
        )

        assert (tmp_path / "models" / "water_point_model.pkl").exists()
        assert (tmp_path / "models" / "scaler.pkl").exists()
        assert (tmp_path / "models" / "feature_names.pkl").exists()
        assert (tmp_path / "models" / "training_metrics.json").exists()
        assert (tmp_path / "images" / "confusion_matrix.png").exists()
        assert (tmp_path / "images" / "roc_curve.png").exists()
        assert (tmp_path / "images" / "feature_importance.png").exists()

        for key in ("accuracy", "precision", "recall", "f1_score"):
            assert 0.0 <= metrics[key] <= 1.0

    def test_load_dataset_rejects_missing_columns(self, tmp_path):
        data_path = tmp_path / "bad.csv"
        pd.DataFrame({"water_point_id": ["WP-1"]}).to_csv(data_path, index=False)
        with pytest.raises(ValueError):
            load_dataset(data_path)

    def test_load_dataset_drops_non_binary_status_rows(self, tmp_path):
        df = _sample_df(n=10)
        df.loc[0, "current_status"] = "Under Repair"
        data_path = tmp_path / "mixed.csv"
        df.to_csv(data_path, index=False)

        loaded = load_dataset(data_path)
        assert set(loaded["current_status"].unique()) <= {"Functional", "Non-Functional"}
        assert len(loaded) == 9

    def test_clean_dataset_imputes_and_removes_outliers(self):
        df = _sample_df(n=30)
        df.loc[0, "population_served"] = None
        df.loc[1, "population_served"] = 999999  # extreme outlier
        cleaned = clean_dataset(df)
        assert cleaned["population_served"].isna().sum() == 0
        assert 999999 not in cleaned["population_served"].values


class TestInference:
    def test_predict_single_returns_none_without_trained_model(self):
        assert ml_inference.is_model_available() is False
        assert ml_inference.predict_single({"year_installed": 2010, "population_served": 500,
                                             "monthly_rainfall": 60, "technology_type": "borehole"}) is None

    def test_predict_batch_degrades_gracefully_without_model(self):
        df = _sample_df(n=5)
        result = ml_inference.predict_batch(df)
        assert "predicted_status" in result.columns
        assert result["predicted_status"].isna().all()

    def test_predict_single_and_batch_after_training(self, tmp_path):
        data_path = tmp_path / "training.csv"
        _sample_df(n=60).to_csv(data_path, index=False)
        train_model(data_path, output_dir=tmp_path, images_dir=tmp_path / "images")

        assert ml_inference.is_model_available() is True

        wp = {"water_point_id": "WP-X", "year_installed": 2008, "population_served": 1200,
              "monthly_rainfall": 20, "technology_type": "hand_pump"}
        prediction = ml_inference.predict_single(wp)
        assert prediction is not None
        assert 0.0 <= prediction.probability <= 1.0
        assert prediction.status in ("Functional", "At Risk", "Non-Functional")
        assert prediction.confidence in ("High", "Medium")

        batch_df = _sample_df(n=20)
        result = ml_inference.predict_batch(batch_df)
        assert result["risk_probability"].between(0, 1).all()
        assert result["predicted_status"].isin(["Functional", "At Risk", "Non-Functional"]).all()

    def test_model_cache_reloads_on_file_change(self, tmp_path):
        data_path = tmp_path / "training.csv"
        _sample_df(n=60, seed=1).to_csv(data_path, index=False)
        train_model(data_path, output_dir=tmp_path, images_dir=tmp_path / "images")
        first_model, _ = ml_inference._load_if_needed()

        time.sleep(0.05)
        _sample_df(n=60, seed=2).to_csv(data_path, index=False)
        train_model(data_path, output_dir=tmp_path, images_dir=tmp_path / "images")
        second_model, _ = ml_inference._load_if_needed()

        assert first_model is not second_model  # re-loaded, not served from stale cache

    def test_classify_status_boundaries(self):
        assert ml_inference.classify_status(0.1) == "Functional"
        assert ml_inference.classify_status(0.5) == "At Risk"
        assert ml_inference.classify_status(0.9) == "Non-Functional"

    def test_confidence_level_boundaries(self):
        assert ml_inference.confidence_level(0.1) == "High"
        assert ml_inference.confidence_level(0.5) == "Medium"
        assert ml_inference.confidence_level(0.95) == "High"

    def test_predict_batch_handles_1000_rows_quickly(self, tmp_path):
        data_path = tmp_path / "training.csv"
        _sample_df(n=60).to_csv(data_path, index=False)
        train_model(data_path, output_dir=tmp_path, images_dir=tmp_path / "images")

        big_df = _sample_df(n=1000, seed=99)
        start = time.perf_counter()
        result = ml_inference.predict_batch(big_df)
        elapsed = time.perf_counter() - start

        assert len(result) == 1000
        assert elapsed < 5.0
