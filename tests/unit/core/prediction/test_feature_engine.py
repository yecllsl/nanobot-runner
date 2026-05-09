from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np

from src.core.prediction.feature_engine import FeatureEngine, FeatureMatrix


class TestFeatureEngineVDOT:
    def test_extract_vdot_features(self):
        engine = _create_engine()
        matrix = engine.extract_vdot_features(days=30)
        assert isinstance(matrix, FeatureMatrix)
        assert matrix.feature_type == "vdot"
        assert len(matrix.feature_names) >= 12
        assert matrix.features.shape[0] == 1
        assert matrix.features.shape[1] >= 12

    def test_get_feature_names_vdot(self):
        engine = _create_engine()
        names = engine.get_feature_names("vdot")
        assert len(names) >= 12
        assert "ctl_value" in names
        assert "tsb_value" in names


class TestFeatureEngineInjury:
    def test_extract_injury_features(self):
        engine = _create_engine()
        matrix = engine.extract_injury_features(days=30)
        assert isinstance(matrix, FeatureMatrix)
        assert matrix.feature_type == "injury"
        assert len(matrix.feature_names) >= 8
        assert matrix.features.shape[1] >= 8

    def test_get_feature_names_injury(self):
        engine = _create_engine()
        names = engine.get_feature_names("injury")
        assert len(names) >= 8
        assert "atl_ctl_ratio" in names


class TestFeatureEngineRace:
    def test_extract_race_features(self):
        engine = _create_engine()
        matrix = engine.extract_race_features()
        assert isinstance(matrix, FeatureMatrix)
        assert matrix.feature_type == "race"
        assert len(matrix.feature_names) >= 5
        assert matrix.features.shape[1] >= 5

    def test_get_feature_names_race(self):
        engine = _create_engine()
        names = engine.get_feature_names("race")
        assert len(names) >= 5
        assert "current_vdot" in names


class TestFeatureEngineEdgeCases:
    def test_dependency_exception_returns_default(self):
        engine = FeatureEngine(session_repo=None)
        matrix = engine.extract_vdot_features(days=30)
        assert isinstance(matrix, FeatureMatrix)
        assert matrix.features.shape[0] == 1

    def test_invalidate_cache(self):
        engine = _create_engine()
        engine.extract_vdot_features(days=30)
        engine.invalidate_cache()
        assert len(engine._cache) == 0

    def test_same_day_cache_hit(self):
        engine = _create_engine()
        result1 = engine.extract_vdot_features(days=30)
        result2 = engine.extract_vdot_features(days=30)
        assert result1 is result2


class TestFeatureMatrix:
    def test_to_dict(self):
        matrix = FeatureMatrix(
            features=np.array([[1.0, 2.0]]),
            feature_names=["a", "b"],
            feature_type="vdot",
        )
        d = matrix.to_dict()
        assert d["feature_type"] == "vdot"
        assert len(d["feature_names"]) == 2
        assert d["data_quality"] == "sufficient"


def _create_engine() -> FeatureEngine:
    repo = MagicMock()
    repo.get_recent_sessions.return_value = []

    load_analyzer = MagicMock()
    load_analyzer.calculate_ctl.return_value = 50.0
    load_analyzer.calculate_atl.return_value = 40.0
    load_analyzer.calculate_tsb.return_value = 10.0
    load_analyzer.get_weekly_load.return_value = 300.0
    load_analyzer.get_load_ramp_rate.return_value = 0.05

    hrv_analyzer = MagicMock()
    hrv_analyzer.get_resting_hr_deviation.return_value = 3.0
    hrv_analyzer.get_rmssd_trend.return_value = 0.0
    hrv_analyzer.get_sdnn_deviation.return_value = 0.0

    body_signal_engine = MagicMock()
    body_signal_engine.get_fatigue_score.return_value = 30.0
    body_signal_engine.get_recovery_status.return_value = "green"

    vdot_calculator = MagicMock()
    vdot_calculator.calculate_vdot.return_value = 45.0

    return FeatureEngine(
        session_repo=repo,
        training_load_analyzer=load_analyzer,
        hrv_analyzer=hrv_analyzer,
        body_signal_engine=body_signal_engine,
        vdot_calculator=vdot_calculator,
    )
