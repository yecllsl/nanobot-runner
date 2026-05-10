from __future__ import annotations

import json
from datetime import datetime

from src.core.prediction.model_manager import ModelManager
from src.core.prediction.models import ModelStatus, PredictionRecord


class TestModelManagerSaveLoad:
    def test_save_and_load(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        model_data = {"type": "test", "version": "v1"}
        mm.save_model(
            "vdot_predictor",
            model_data,
            metadata={
                "version": "v1",
                "trained_at": datetime.now().isoformat(),
                "training_samples": 500,
                "feature_count": 12,
                "validation_error": 1.5,
                "sklearn_version": "1.5.0",
            },
        )
        loaded = mm.load_model("vdot_predictor")
        assert loaded is not None
        assert loaded["type"] == "test"

    def test_metadata_json(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        mm.save_model(
            "vdot_predictor",
            {"type": "test"},
            metadata={
                "version": "v1",
                "trained_at": "2026-05-08T10:00:00",
                "training_samples": 500,
                "feature_count": 12,
                "validation_error": 1.5,
                "sklearn_version": "1.5.0",
            },
        )
        meta_path = tmp_path / "models" / "vdot_predictor" / "v1" / "metadata.json"
        assert meta_path.exists()
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        assert meta["version"] == "v1"
        assert meta["training_samples"] == 500


class TestModelManagerStatus:
    def test_get_model_status_available(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        mm.save_model(
            "vdot_predictor",
            {"type": "test"},
            metadata={
                "version": "v1",
                "trained_at": "2026-05-08T10:00:00",
                "training_samples": 500,
                "feature_count": 12,
                "validation_error": 1.5,
                "sklearn_version": "1.5.0",
            },
        )
        status = mm.get_model_status("vdot_predictor")
        assert isinstance(status, ModelStatus)
        assert status.is_available is True

    def test_get_model_status_not_available(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        status = mm.get_model_status("nonexistent")
        assert isinstance(status, ModelStatus)
        assert status.is_available is False


class TestModelManagerRollback:
    def test_rollback_model(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        mm.save_model(
            "vdot_predictor",
            {"type": "v1"},
            metadata={
                "version": "v1",
                "trained_at": "2026-05-08T10:00:00",
                "training_samples": 500,
                "feature_count": 12,
                "validation_error": 1.5,
                "sklearn_version": "1.5.0",
            },
        )
        mm.save_model(
            "vdot_predictor",
            {"type": "v2"},
            metadata={
                "version": "v2",
                "trained_at": "2026-05-09T10:00:00",
                "training_samples": 600,
                "feature_count": 12,
                "validation_error": 1.2,
                "sklearn_version": "1.5.0",
            },
        )
        result = mm.rollback_model("vdot_predictor", "v1")
        assert result.success is True

    def test_rollback_to_previous_version(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        mm.save_model(
            "vdot_predictor",
            {"type": "v1"},
            metadata={
                "version": "v1",
                "trained_at": "2026-05-08T10:00:00",
                "training_samples": 500,
                "sklearn_version": "1.5.0",
            },
        )
        mm.save_model(
            "vdot_predictor",
            {"type": "v2"},
            metadata={
                "version": "v2",
                "trained_at": "2026-05-09T10:00:00",
                "training_samples": 600,
                "sklearn_version": "1.5.0",
            },
        )
        result = mm.rollback("vdot_predictor")
        assert result is True
        loaded = mm.load_model("vdot_predictor")
        assert loaded is not None
        assert loaded["type"] == "v1"

    def test_rollback_no_previous_version(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        mm.save_model(
            "vdot_predictor",
            {"type": "v1"},
            metadata={
                "version": "v1",
                "trained_at": "2026-05-08T10:00:00",
                "training_samples": 500,
                "sklearn_version": "1.5.0",
            },
        )
        result = mm.rollback("vdot_predictor")
        assert result is False

    def test_rollback_nonexistent_model(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        result = mm.rollback("nonexistent")
        assert result is False


class TestModelManagerAutoUpdate:
    def test_check_auto_update(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        result = mm.check_auto_update(
            "vdot_predictor", new_samples=60, days_since_last=35
        )
        assert isinstance(result, bool)

    def test_check_auto_update_no_need(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        result = mm.check_auto_update(
            "vdot_predictor", new_samples=10, days_since_last=5
        )
        assert result is False


class TestModelManagerSklearnCompat:
    def test_sklearn_compat_same_version(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        import sklearn

        mm.save_model(
            "vdot_predictor",
            {"type": "test"},
            metadata={
                "version": "v1",
                "sklearn_version": sklearn.__version__,
            },
        )
        loaded = mm.load_model("vdot_predictor")
        assert loaded is not None

    def test_sklearn_compat_incompatible_version(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        mm.save_model(
            "vdot_predictor",
            {"type": "test"},
            metadata={
                "version": "v1",
                "sklearn_version": "0.24.0",
            },
        )
        loaded = mm.load_model("vdot_predictor")
        assert loaded is None

    def test_sklearn_compat_no_metadata(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        mm.save_model("vdot_predictor", {"type": "test"})
        loaded = mm.load_model("vdot_predictor")
        assert loaded is not None


class TestModelManagerPredictionHistory:
    def test_record_prediction(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        record = PredictionRecord(
            prediction_date="2026-05-10",
            prediction_type="vdot",
            predicted_value=45.2,
            predicted_unit="vdot",
            actual_value=None,
            deviation_pct=None,
            prediction_method="ml_enhanced",
            model_version="v1",
            confidence=0.85,
        )
        mm.record_prediction(record)

        predictions_dir = tmp_path / "models" / "predictions"
        assert predictions_dir.exists()
        parquet_path = predictions_dir / "predictions_2026.parquet"
        assert parquet_path.exists()

    def test_record_and_query_predictions(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        records = [
            PredictionRecord(
                prediction_date="2026-05-10",
                prediction_type="vdot",
                predicted_value=45.2,
                predicted_unit="vdot",
                actual_value=None,
                deviation_pct=None,
                prediction_method="ml_enhanced",
                model_version="v1",
                confidence=0.85,
            ),
            PredictionRecord(
                prediction_date="2026-05-11",
                prediction_type="race",
                predicted_value=12600.0,
                predicted_unit="seconds",
                actual_value=None,
                deviation_pct=None,
                prediction_method="parametric",
                model_version="v1",
                confidence=0.7,
            ),
        ]
        for r in records:
            mm.record_prediction(r)

        all_records = mm.query_predictions()
        assert len(all_records) == 2

        vdot_records = mm.query_predictions(prediction_type="vdot")
        assert len(vdot_records) == 1
        assert vdot_records[0].prediction_type == "vdot"

    def test_query_predictions_by_date_range(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        for i in range(5):
            mm.record_prediction(
                PredictionRecord(
                    prediction_date=f"2026-05-{10 + i:02d}",
                    prediction_type="vdot",
                    predicted_value=45.0 + i,
                    predicted_unit="vdot",
                    actual_value=None,
                    deviation_pct=None,
                    prediction_method="ml_enhanced",
                    model_version="v1",
                    confidence=0.8,
                )
            )

        filtered = mm.query_predictions(start_date="2026-05-12", end_date="2026-05-13")
        assert len(filtered) == 2

    def test_query_predictions_empty(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        result = mm.query_predictions()
        assert result == []

    def test_check_and_update_actual(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        mm.record_prediction(
            PredictionRecord(
                prediction_date="2026-05-10",
                prediction_type="vdot",
                predicted_value=45.0,
                predicted_unit="vdot",
                actual_value=None,
                deviation_pct=None,
                prediction_method="ml_enhanced",
                model_version="v1",
                confidence=0.8,
            )
        )
        count = mm.check_and_update_actual("vdot")
        assert isinstance(count, int)

    def test_check_and_update_actual_no_pending(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        mm.record_prediction(
            PredictionRecord(
                prediction_date="2026-05-10",
                prediction_type="vdot",
                predicted_value=45.0,
                predicted_unit="vdot",
                actual_value=46.0,
                deviation_pct=2.2,
                prediction_method="ml_enhanced",
                model_version="v1",
                confidence=0.8,
            )
        )
        count = mm.check_and_update_actual("vdot")
        assert count == 0


class TestModelManagerTriggerAutoUpdate:
    def test_trigger_when_no_model(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        result = mm.trigger_auto_update_if_needed("vdot_predictor")
        assert result is True

    def test_trigger_when_enough_new_samples(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        mm.save_model(
            "vdot_predictor",
            {"type": "test"},
            metadata={
                "version": "v1",
                "trained_at": datetime.now().isoformat(),
                "training_samples": 500,
                "sklearn_version": "1.5.0",
            },
        )
        result = mm.trigger_auto_update_if_needed("vdot_predictor", new_samples=60)
        assert result is True

    def test_no_trigger_when_recent_and_few_samples(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        mm.save_model(
            "vdot_predictor",
            {"type": "test"},
            metadata={
                "version": "v1",
                "trained_at": datetime.now().isoformat(),
                "training_samples": 500,
                "sklearn_version": "1.5.0",
            },
        )
        result = mm.trigger_auto_update_if_needed("vdot_predictor", new_samples=5)
        assert result is False

    def test_trigger_when_stale_model(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        mm.save_model(
            "vdot_predictor",
            {"type": "test"},
            metadata={
                "version": "v1",
                "trained_at": "2025-01-01T10:00:00",
                "training_samples": 500,
                "sklearn_version": "1.5.0",
            },
        )
        result = mm.trigger_auto_update_if_needed("vdot_predictor", new_samples=5)
        assert result is True
