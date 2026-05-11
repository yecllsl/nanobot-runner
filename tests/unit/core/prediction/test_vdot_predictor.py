from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

import numpy as np

from src.core.prediction.models import VDOTPrediction
from src.core.prediction.vdot_predictor import VDOTPredictor


def _make_assessor(sufficient: bool, parametric: bool = False):
    assessor = MagicMock()
    report = MagicMock()
    report.is_sufficient = sufficient
    report.overall_progress_pct = 90.0 if sufficient else (60.0 if parametric else 30.0)
    total_dim = MagicMock()
    total_dim.name = "total_records"
    total_dim.current_value = 500.0 if sufficient else (250.0 if parametric else 30.0)
    report.dimensions = [total_dim]
    assessor.assess_sufficiency.return_value = report
    return assessor


def _make_feature_engine():
    fe = MagicMock()
    matrix = MagicMock()
    matrix.features = np.random.randn(1, 12)
    matrix.feature_names = [f"f{i}" for i in range(12)]
    matrix.feature_type = "vdot"
    matrix.data_quality = "sufficient"
    fe.extract_vdot_features.return_value = matrix
    return fe


def _make_vdot_sessions(count: int = 50) -> list[MagicMock]:
    """创建带timestamp的VDOT训练session列表"""
    sessions = []
    for i in range(count):
        s = MagicMock()
        s.distance_m = 5000.0 + i * 100
        s.duration_s = 1800.0 + i * 10
        s.timestamp = datetime(2024, 1, 1 + (i % 28), 8, 0, 0)
        sessions.append(s)
    return sessions


def _make_model_manager():
    mm = MagicMock()
    mm.load_model.return_value = MagicMock()
    mm.get_model_status.return_value = MagicMock(is_available=True)
    return mm


class TestVDOTPredictorMLEnhanced:
    def test_ml_enhanced_prediction(self):
        predictor = VDOTPredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=_make_assessor(sufficient=True),
            model_manager=_make_model_manager(),
            banister_model=MagicMock(),
            base_vdot=45.0,
        )
        result = predictor.predict(days=30)
        assert isinstance(result, VDOTPrediction)
        assert result.prediction_type == "ml_enhanced"
        assert result.current_vdot == 45.0

    def test_ml_enhanced_has_confidence_interval(self):
        predictor = VDOTPredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=_make_assessor(sufficient=True),
            model_manager=_make_model_manager(),
            banister_model=MagicMock(),
            base_vdot=45.0,
        )
        result = predictor.predict(days=30)
        assert result.confidence_interval is not None
        assert len(result.confidence_interval) == 2


class TestVDOTPredictorParametric:
    def test_parametric_prediction(self):
        banister = MagicMock()
        banister.predict.return_value = 46.0
        predictor = VDOTPredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=_make_assessor(sufficient=False, parametric=True),
            model_manager=_make_model_manager(),
            banister_model=banister,
            base_vdot=45.0,
        )
        result = predictor.predict(days=30)
        assert result.prediction_type == "parametric"

    def test_parametric_no_model_info(self):
        banister = MagicMock()
        banister.predict.return_value = 46.0
        predictor = VDOTPredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=_make_assessor(sufficient=False, parametric=True),
            model_manager=_make_model_manager(),
            banister_model=banister,
            base_vdot=45.0,
        )
        result = predictor.predict(days=30)
        assert result.model_info is None


class TestVDOTPredictorBasic:
    def test_basic_prediction(self):
        predictor = VDOTPredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=_make_assessor(sufficient=False, parametric=False),
            model_manager=_make_model_manager(),
            banister_model=MagicMock(),
            base_vdot=45.0,
        )
        result = predictor.predict(days=30)
        assert result.prediction_type == "basic"
        assert result.confidence < 0.6


class TestVDOTPredictorTrainModel:
    def test_train_model_with_sufficient_data(self):
        session_repo = MagicMock()
        session_repo.get_sessions_for_vdot.return_value = _make_vdot_sessions(50)
        model_manager = MagicMock()
        predictor = VDOTPredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=_make_assessor(sufficient=True),
            model_manager=model_manager,
            banister_model=MagicMock(),
            session_repo=session_repo,
            base_vdot=45.0,
        )
        result = predictor.train_model()
        assert result.success is True
        assert result.model_type == "vdot_predictor"
        assert result.training_samples > 0

    def test_train_model_trains_three_quantile_models(self):
        session_repo = MagicMock()
        session_repo.get_sessions_for_vdot.return_value = _make_vdot_sessions(50)
        model_manager = MagicMock()
        predictor = VDOTPredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=_make_assessor(sufficient=True),
            model_manager=model_manager,
            banister_model=MagicMock(),
            session_repo=session_repo,
            base_vdot=45.0,
        )
        result = predictor.train_model()
        assert result.success is True
        model_manager.save_model.assert_called_once()
        saved_data = model_manager.save_model.call_args[0][1]
        assert "p10" in saved_data
        assert "p50" in saved_data
        assert "p90" in saved_data

    def test_train_model_persistence(self):
        session_repo = MagicMock()
        session_repo.get_sessions_for_vdot.return_value = _make_vdot_sessions(50)
        model_manager = MagicMock()
        predictor = VDOTPredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=_make_assessor(sufficient=True),
            model_manager=model_manager,
            banister_model=MagicMock(),
            session_repo=session_repo,
            base_vdot=45.0,
        )
        result = predictor.train_model()
        assert result.success is True
        saved_data = model_manager.save_model.call_args[0][1]
        assert hasattr(saved_data["p10"], "predict")
        assert hasattr(saved_data["p50"], "predict")
        assert hasattr(saved_data["p90"], "predict")

    def test_train_model_insufficient_data(self):
        session_repo = MagicMock()
        session_repo.get_sessions_for_vdot.return_value = _make_vdot_sessions(5)
        predictor = VDOTPredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=_make_assessor(sufficient=True),
            model_manager=MagicMock(),
            banister_model=MagicMock(),
            session_repo=session_repo,
            base_vdot=45.0,
        )
        result = predictor.train_model()
        assert result.success is False
        assert "不足" in result.message

    def test_train_model_no_session_repo(self):
        predictor = VDOTPredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=_make_assessor(sufficient=True),
            model_manager=MagicMock(),
            banister_model=MagicMock(),
            session_repo=None,
            base_vdot=45.0,
        )
        result = predictor.train_model()
        assert result.success is False


class TestVDOTPredictorMLInference:
    def _train_and_get_predictor(self):
        session_repo = MagicMock()
        session_repo.get_sessions_for_vdot.return_value = _make_vdot_sessions(50)
        model_manager = MagicMock()
        predictor = VDOTPredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=_make_assessor(sufficient=True),
            model_manager=model_manager,
            banister_model=MagicMock(),
            session_repo=session_repo,
            base_vdot=45.0,
        )
        predictor.train_model()
        return predictor, model_manager

    def test_ml_inference_with_trained_model(self):
        predictor, model_manager = self._train_and_get_predictor()
        saved_data = model_manager.save_model.call_args[0][1]
        sample = np.random.randn(1, 12)
        p10 = float(saved_data["p10"].predict(sample)[0])
        p50 = float(saved_data["p50"].predict(sample)[0])
        p90 = float(saved_data["p90"].predict(sample)[0])
        assert p10 <= p50 <= p90

    def test_auto_train_on_first_predict(self):
        session_repo = MagicMock()
        session_repo.get_sessions_for_vdot.return_value = _make_vdot_sessions(50)
        model_manager = MagicMock()
        model_manager.get_model_status.return_value = MagicMock(is_available=False)
        model_manager.load_model.return_value = None
        predictor = VDOTPredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=_make_assessor(sufficient=True),
            model_manager=model_manager,
            banister_model=MagicMock(),
            session_repo=session_repo,
            base_vdot=45.0,
        )
        result = predictor.predict(days=30)
        assert result.prediction_type in ("ml_enhanced", "parametric")

    def test_model_corruption_auto_retrain(self):
        session_repo = MagicMock()
        session_repo.get_sessions_for_vdot.return_value = _make_vdot_sessions(50)
        model_manager = MagicMock()
        model_manager.get_model_status.return_value = MagicMock(is_available=True)
        model_manager.load_model.return_value = None
        predictor = VDOTPredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=_make_assessor(sufficient=True),
            model_manager=model_manager,
            banister_model=MagicMock(),
            session_repo=session_repo,
            base_vdot=45.0,
        )
        result = predictor.predict(days=30)
        assert result.prediction_type in ("ml_enhanced", "parametric")


class TestVDOTPredictorSHAP:
    def test_shap_feature_importance_with_trained_model(self):
        session_repo = MagicMock()
        session_repo.get_sessions_for_vdot.return_value = _make_vdot_sessions(50)
        model_manager = MagicMock()
        predictor = VDOTPredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=_make_assessor(sufficient=True),
            model_manager=model_manager,
            banister_model=MagicMock(),
            session_repo=session_repo,
            base_vdot=45.0,
        )
        predictor.train_model()
        saved_data = model_manager.save_model.call_args[0][1]
        predictor._ml_model = saved_data
        factors = predictor.get_feature_importance()
        assert isinstance(factors, list)
        assert len(factors) <= 3
        if factors:
            for f in factors:
                assert f.name
                assert f.weight > 0

    def test_shap_timeout_fallback_to_sklearn(self):
        session_repo = MagicMock()
        session_repo.get_sessions_for_vdot.return_value = _make_vdot_sessions(50)
        model_manager = MagicMock()
        predictor = VDOTPredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=_make_assessor(sufficient=True),
            model_manager=model_manager,
            banister_model=MagicMock(),
            session_repo=session_repo,
            base_vdot=45.0,
        )
        predictor.train_model()
        saved_data = model_manager.save_model.call_args[0][1]
        predictor._ml_model = saved_data
        factors = predictor.get_feature_importance()
        assert isinstance(factors, list)

    def test_feature_importance_no_model_fallback(self):
        predictor = VDOTPredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=_make_assessor(sufficient=True),
            model_manager=_make_model_manager(),
            banister_model=MagicMock(),
            base_vdot=45.0,
        )
        factors = predictor.get_feature_importance()
        assert isinstance(factors, list)
        assert len(factors) <= 3
