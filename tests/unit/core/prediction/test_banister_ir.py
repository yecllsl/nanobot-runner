from __future__ import annotations

import numpy as np

from src.core.prediction.baselines.banister_ir import BanisterIRModel


class TestBanisterIRModelDefaults:
    def test_default_params(self):
        model = BanisterIRModel()
        assert model.tau_fitness == 42.0
        assert model.tau_fatigue == 10.0
        assert model.k1 == 0.0038
        assert model.k2 == 0.043


class TestBanisterIRModelPredict:
    def test_predict_basic(self):
        model = BanisterIRModel()
        training_stress = np.array([50.0, 60.0, 70.0])
        result = model.predict(training_stress, base_vdot=45.0)
        assert isinstance(result, float)
        assert result > 0

    def test_predict_days_ahead(self):
        model = BanisterIRModel()
        training_stress = np.array([50.0, 60.0, 70.0])
        result = model.predict(training_stress, base_vdot=45.0, days_ahead=7)
        assert isinstance(result, float)


class TestBanisterIRModelFit:
    def test_fit_and_predict(self):
        model = BanisterIRModel()
        np.random.seed(42)
        n = 200
        training_stress = np.random.uniform(30, 100, n)
        vdot_values = (
            45.0
            + 0.0038 * np.cumsum(training_stress * np.exp(-np.arange(n) / 42.0))
            - 0.043 * np.cumsum(training_stress * np.exp(-np.arange(n) / 10.0))
        )
        model.fit(training_stress, vdot_values)
        result = model.predict(training_stress, base_vdot=45.0)
        assert isinstance(result, float)

    def test_fitted_params_within_range(self):
        model = BanisterIRModel()
        np.random.seed(42)
        n = 200
        training_stress = np.random.uniform(30, 100, n)
        vdot_values = 45.0 + np.random.normal(0, 0.5, n)
        model.fit(training_stress, vdot_values)
        assert 0.0027 <= model.k1 <= 0.0049
        assert 0.030 <= model.k2 <= 0.056
        assert 30 <= model.tau_fitness <= 55
        assert 7 <= model.tau_fatigue <= 14
