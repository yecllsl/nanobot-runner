from __future__ import annotations

import json

from src.core.prediction.model_manager import ModelManager
from src.core.prediction.models import PredictionRecord


class TestModelManagerSaveAndLoad:
    def test_save_and_load_model(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        model_data = {"weights": [1.0, 2.0, 3.0]}
        metadata = {
            "version": "v1",
            "training_samples": 500,
            "validation_error": 1.5,
            "trained_at": "2026-05-08T10:00:00",
        }
        mm.save_model("vdot_predictor", model_data, metadata)
        loaded = mm.load_model("vdot_predictor")
        assert loaded == model_data

    def test_save_model_default_version(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        mm.save_model("vdot_predictor", {"test": True})
        model_dir = tmp_path / "models" / "vdot_predictor"
        assert (model_dir / "v1" / "model.joblib").exists()

    def test_save_model_with_version(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        mm.save_model("vdot_predictor", {"test": True}, {"version": "v2"})
        model_dir = tmp_path / "models" / "vdot_predictor"
        assert (model_dir / "v2" / "model.joblib").exists()

    def test_load_model_specific_version(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        mm.save_model("vdot_predictor", {"v1_data": True}, {"version": "v1"})
        mm.save_model("vdot_predictor", {"v2_data": True}, {"version": "v2"})
        loaded = mm.load_model("vdot_predictor", version="v1")
        assert loaded == {"v1_data": True}

    def test_load_model_nonexistent(self, tmp_path):
        models_dir = tmp_path / "models"
        models_dir.mkdir(parents=True)
        nonexistent_dir = models_dir / "nonexistent_model"
        nonexistent_dir.mkdir(parents=True)
        mm = ModelManager(models_dir=str(models_dir))
        result = mm.load_model("nonexistent_model")
        assert result is None

    def test_load_model_no_version_dir(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        model_dir = tmp_path / "models" / "vdot_predictor"
        model_dir.mkdir(parents=True)
        result = mm.load_model("vdot_predictor")
        assert result is None


class TestModelManagerGetStatus:
    def test_get_status_no_model_dir(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        status = mm.get_model_status("vdot_predictor")
        assert status.is_available is False

    def test_get_status_with_metadata(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        metadata = {
            "version": "v1",
            "training_samples": 500,
            "validation_error": 1.5,
            "trained_at": "2026-05-08T10:00:00",
        }
        mm.save_model("vdot_predictor", {"test": True}, metadata)
        status = mm.get_model_status("vdot_predictor")
        assert status.is_available is True
        assert status.version == "v1"
        assert status.training_samples == 500

    def test_get_status_no_metadata(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        mm.save_model("vdot_predictor", {"test": True})
        status = mm.get_model_status("vdot_predictor")
        assert status.is_available is True
        assert status.version == ""

    def test_get_status_no_versions(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        model_dir = tmp_path / "models" / "vdot_predictor"
        model_dir.mkdir(parents=True)
        status = mm.get_model_status("vdot_predictor")
        assert status.is_available is False


class TestModelManagerRollback:
    def test_rollback_to_previous_version(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        mm.save_model("vdot_predictor", {"v1": True}, {"version": "v1"})
        mm.save_model("vdot_predictor", {"v2": True}, {"version": "v2"})
        result = mm.rollback("vdot_predictor")
        assert result is True

    def test_rollback_no_model_dir(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        result = mm.rollback("vdot_predictor")
        assert result is False

    def test_rollback_only_one_version(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        mm.save_model("vdot_predictor", {"v1": True}, {"version": "v1"})
        result = mm.rollback("vdot_predictor")
        assert result is False

    def test_rollback_to_specific_version(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        mm.save_model("vdot_predictor", {"v1": True}, {"version": "v1"})
        mm.save_model("vdot_predictor", {"v2": True}, {"version": "v2"})
        mm.save_model("vdot_predictor", {"v3": True}, {"version": "v3"})
        result = mm.rollback("vdot_predictor", target_version="v1")
        assert result is True

    def test_rollback_nonexistent_version(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        mm.save_model("vdot_predictor", {"v1": True}, {"version": "v1"})
        mm.save_model("vdot_predictor", {"v2": True}, {"version": "v2"})
        result = mm.rollback("vdot_predictor", target_version="v99")
        assert result is False


class TestModelManagerRollbackModel:
    def test_rollback_model_success(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        mm.save_model("vdot_predictor", {"v1": True}, {"version": "v1"})
        mm.save_model("vdot_predictor", {"v2": True}, {"version": "v2"})
        result = mm.rollback_model("vdot_predictor", "v1")
        assert result.success is True
        assert "v1" in result.message

    def test_rollback_model_nonexistent_version(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        mm.save_model("vdot_predictor", {"v1": True}, {"version": "v1"})
        result = mm.rollback_model("vdot_predictor", "v99")
        assert result.success is False
        assert "不存在" in result.message


class TestModelManagerRecordAndQueryPredictions:
    def test_record_and_query(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        record = PredictionRecord(
            prediction_date="2026-05-08",
            prediction_type="vdot",
            predicted_value=46.0,
            predicted_unit="vdot",
            actual_value=None,
            deviation_pct=None,
            prediction_method="ml_enhanced",
            model_version="v1",
            confidence=0.85,
        )
        mm.record_prediction(record)
        results = mm.query_predictions(prediction_type="vdot")
        assert len(results) == 1
        assert results[0].predicted_value == 46.0

    def test_query_no_predictions_dir(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        results = mm.query_predictions()
        assert results == []

    def test_query_with_date_filter(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        for i in range(5):
            record = PredictionRecord(
                prediction_date=f"2026-05-{8 + i:02d}",
                prediction_type="vdot",
                predicted_value=45.0 + i,
                predicted_unit="vdot",
                actual_value=None,
                deviation_pct=None,
                prediction_method="ml_enhanced",
                model_version="v1",
                confidence=0.85,
            )
            mm.record_prediction(record)
        results = mm.query_predictions(start_date="2026-05-10", end_date="2026-05-11")
        assert len(results) == 2

    def test_record_multiple_to_same_year(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        for i in range(3):
            record = PredictionRecord(
                prediction_date=f"2026-05-{8 + i:02d}",
                prediction_type="vdot",
                predicted_value=45.0,
                predicted_unit="vdot",
                actual_value=None,
                deviation_pct=None,
                prediction_method="ml_enhanced",
                model_version="v1",
                confidence=0.85,
            )
            mm.record_prediction(record)
        results = mm.query_predictions()
        assert len(results) == 3


class TestModelManagerAutoUpdate:
    def test_auto_update_new_samples(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        mm.save_model(
            "vdot_predictor",
            {"test": True},
            {"version": "v1", "trained_at": "2026-05-08T10:00:00"},
        )
        result = mm.trigger_auto_update_if_needed("vdot_predictor", new_samples=60)
        assert result is True

    def test_auto_update_old_training(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        mm.save_model(
            "vdot_predictor",
            {"test": True},
            {
                "version": "v1",
                "trained_at": "2025-01-01T10:00:00",
            },
        )
        result = mm.trigger_auto_update_if_needed("vdot_predictor", new_samples=0)
        assert result is True

    def test_auto_update_no_need(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        mm.save_model(
            "vdot_predictor",
            {"test": True},
            {
                "version": "v1",
                "trained_at": "2026-05-08T10:00:00",
            },
        )
        result = mm.trigger_auto_update_if_needed("vdot_predictor", new_samples=0)
        assert result is False

    def test_auto_update_model_not_available(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        result = mm.trigger_auto_update_if_needed("nonexistent", new_samples=0)
        assert result is True

    def test_check_auto_update_samples(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        result = mm.check_auto_update(
            "vdot_predictor", new_samples=60, days_since_last=0
        )
        assert result is True

    def test_check_auto_update_days(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        result = mm.check_auto_update(
            "vdot_predictor", new_samples=0, days_since_last=35
        )
        assert result is True

    def test_check_auto_update_no_need(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        result = mm.check_auto_update(
            "vdot_predictor", new_samples=0, days_since_last=10
        )
        assert result is False


class TestModelManagerSklearnCompat:
    def test_check_sklearn_compat_no_metadata(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        version_dir = tmp_path / "models" / "test" / "v1"
        version_dir.mkdir(parents=True)
        result = mm._check_sklearn_compat(version_dir)
        assert result is True

    def test_check_sklearn_compat_no_sklearn_version(self, tmp_path):
        mm = ModelManager(models_dir=str(tmp_path / "models"))
        version_dir = tmp_path / "models" / "test" / "v1"
        version_dir.mkdir(parents=True)
        (version_dir / "metadata.json").write_text(
            json.dumps({"version": "v1"}), encoding="utf-8"
        )
        result = mm._check_sklearn_compat(version_dir)
        assert result is True
