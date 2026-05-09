from __future__ import annotations

import numpy as np

from src.core.prediction.baselines.logistic_injury import LogisticInjuryModel


class TestLogisticInjuryModelUnfitted:
    def test_predict_proba_unfitted(self):
        model = LogisticInjuryModel()
        X = np.random.randn(5, 8)
        proba = model.predict_proba(X)
        assert proba.shape[0] == 5
        assert all(0.0 <= p <= 1.0 for p in proba)


class TestLogisticInjuryModelFitted:
    def test_fit_and_predict(self):
        model = LogisticInjuryModel()
        np.random.seed(42)
        X = np.random.randn(150, 8)
        y = (X[:, 0] > 0).astype(int)
        model.fit(X, y)
        proba = model.predict_proba(X[:5])
        assert proba.shape[0] == 5
        assert all(0.0 <= p <= 1.0 for p in proba)


class TestLogisticInjuryModelPersistence:
    def test_save_and_load(self, tmp_path):
        model = LogisticInjuryModel()
        np.random.seed(42)
        X = np.random.randn(50, 8)
        y = (X[:, 0] > 0).astype(int)
        model.fit(X, y)
        original_proba = model.predict_proba(X[:3])

        model_path = tmp_path / "logistic_model.joblib"
        model.save(str(model_path))

        loaded_model = LogisticInjuryModel()
        loaded_model.load(str(model_path))
        loaded_proba = loaded_model.predict_proba(X[:3])

        np.testing.assert_array_almost_equal(original_proba, loaded_proba)
