from __future__ import annotations

import json
from datetime import datetime

from src.core.prediction.model_manager import ModelManager
from src.core.prediction.models import ModelStatus


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
