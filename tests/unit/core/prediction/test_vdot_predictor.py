from __future__ import annotations

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
    def test_train_model(self):
        predictor = VDOTPredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=_make_assessor(sufficient=True),
            model_manager=_make_model_manager(),
            banister_model=MagicMock(),
            base_vdot=45.0,
        )
        result = predictor.train_model()
        assert result.success is True
        assert result.model_type == "vdot_predictor"


class TestVDOTPredictorFeatureImportance:
    def test_get_feature_importance(self):
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
