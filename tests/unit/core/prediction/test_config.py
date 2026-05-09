from __future__ import annotations

import os

import pytest

from src.core.prediction.config import PredictionConfig


class TestPredictionConfigDefaults:
    def test_default_values(self):
        c = PredictionConfig()
        assert c.gb_n_estimators == 100
        assert c.gb_learning_rate == 0.05
        assert c.gb_max_depth == 5
        assert c.gb_min_samples_leaf == 30
        assert c.gb_subsample == 0.8
        assert c.logistic_c == 0.1
        assert c.logistic_max_iter == 1000
        assert c.vdot_min_months == 18
        assert c.vdot_min_records == 400
        assert c.vdot_parametric_min_records == 200
        assert c.race_min_races == 3
        assert c.injury_min_months == 12
        assert c.injury_min_records == 300
        assert c.injury_parametric_min_records == 100
        assert c.injury_min_hr_completeness == 0.5
        assert c.banister_tau_fitness == 42.0
        assert c.banister_tau_fatigue == 10.0
        assert c.banister_k1 == 0.0038
        assert c.banister_k2 == 0.043
        assert c.risk_warning_threshold == 0.7
        assert c.pre_race_fatigue_adjustment_range == (0.0, 0.05)
        assert c.pre_race_recovery_adjustment_range == (-0.03, 0.0)

    def test_frozen(self):
        c = PredictionConfig()
        with pytest.raises(AttributeError):
            c.gb_n_estimators = 200


class TestPredictionConfigValidation:
    def test_gb_n_estimators_too_low(self):
        with pytest.raises(ValueError, match="gb_n_estimators"):
            PredictionConfig(gb_n_estimators=5)

    def test_gb_learning_rate_zero(self):
        with pytest.raises(ValueError, match="gb_learning_rate"):
            PredictionConfig(gb_learning_rate=0.0)

    def test_gb_learning_rate_too_high(self):
        with pytest.raises(ValueError, match="gb_learning_rate"):
            PredictionConfig(gb_learning_rate=1.5)

    def test_gb_max_depth_zero(self):
        with pytest.raises(ValueError, match="gb_max_depth"):
            PredictionConfig(gb_max_depth=0)

    def test_vdot_min_months_too_low(self):
        with pytest.raises(ValueError, match="vdot_min_months"):
            PredictionConfig(vdot_min_months=3)

    def test_risk_warning_threshold_zero(self):
        with pytest.raises(ValueError, match="risk_warning_threshold"):
            PredictionConfig(risk_warning_threshold=0.0)

    def test_risk_warning_threshold_too_high(self):
        with pytest.raises(ValueError, match="risk_warning_threshold"):
            PredictionConfig(risk_warning_threshold=1.5)


class TestPredictionConfigToDict:
    def test_to_dict(self):
        c = PredictionConfig()
        d = c.to_dict()
        assert d["gb_n_estimators"] == 100
        assert d["pre_race_fatigue_adjustment_range"] == [0.0, 0.05]
        assert d["pre_race_recovery_adjustment_range"] == [-0.03, 0.0]
        assert isinstance(d["pre_race_fatigue_adjustment_range"], list)

    def test_to_dict_keys_count(self):
        c = PredictionConfig()
        d = c.to_dict()
        assert len(d) == 22


class TestPredictionConfigFromDict:
    def test_from_dict_partial(self):
        d = {"gb_n_estimators": 200, "gb_learning_rate": 0.1}
        c = PredictionConfig.from_dict(d)
        assert c.gb_n_estimators == 200
        assert c.gb_learning_rate == 0.1
        assert c.gb_max_depth == 5

    def test_from_dict_ignores_invalid_keys(self):
        d = {"gb_n_estimators": 200, "invalid_key": "value"}
        c = PredictionConfig.from_dict(d)
        assert c.gb_n_estimators == 200
        assert not hasattr(c, "invalid_key")

    def test_from_dict_empty(self):
        c = PredictionConfig.from_dict({})
        assert c.gb_n_estimators == 100


class TestPredictionConfigFromEnv:
    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("NANOBOT_PREDICTION_GB_N_ESTIMATORS", "200")
        monkeypatch.setenv("NANOBOT_PREDICTION_GB_LEARNING_RATE", "0.1")
        c = PredictionConfig.from_env()
        assert c.gb_n_estimators == 200
        assert c.gb_learning_rate == 0.1

    def test_from_env_no_vars(self, monkeypatch):
        for key in list(os.environ.keys()):
            if key.startswith("NANOBOT_PREDICTION_"):
                monkeypatch.delenv(key, raising=False)
        c = PredictionConfig.from_env()
        assert c.gb_n_estimators == 100
