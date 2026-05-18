from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

import numpy as np

from src.core.prediction.models import DataQuality
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
    fe.get_feature_names.return_value = [f"f{i}" for i in range(12)]
    return fe


def _make_vdot_sessions(count: int = 50) -> list[MagicMock]:
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


class TestVDOTPredictorGetTssSeries:
    def test_get_tss_series_no_repo(self):
        predictor = VDOTPredictor(base_vdot=45.0)
        result = predictor._get_tss_series()
        assert result == []

    def test_get_tss_series_with_sessions(self):
        session_repo = MagicMock()
        sessions = []
        for i in range(5):
            s = MagicMock()
            s.date = f"2024-01-{10 + i:02d}"
            s.tss = 50.0 + i * 10
            sessions.append(s)
        session_repo.get_recent_sessions.return_value = sessions
        predictor = VDOTPredictor(session_repo=session_repo, base_vdot=45.0)
        result = predictor._get_tss_series()
        assert len(result) == 5
        assert result[0] == 50.0

    def test_get_tss_series_empty_sessions(self):
        session_repo = MagicMock()
        session_repo.get_recent_sessions.return_value = []
        predictor = VDOTPredictor(session_repo=session_repo, base_vdot=45.0)
        result = predictor._get_tss_series()
        assert result == []

    def test_get_tss_series_exception(self):
        session_repo = MagicMock()
        session_repo.get_recent_sessions.side_effect = Exception("db error")
        predictor = VDOTPredictor(session_repo=session_repo, base_vdot=45.0)
        result = predictor._get_tss_series()
        assert result == []

    def test_get_tss_series_aggregates_same_date(self):
        session_repo = MagicMock()
        sessions = []
        for i in range(4):
            s = MagicMock()
            s.date = "2024-01-10" if i < 2 else "2024-01-11"
            s.tss = 30.0
            sessions.append(s)
        session_repo.get_recent_sessions.return_value = sessions
        predictor = VDOTPredictor(session_repo=session_repo, base_vdot=45.0)
        result = predictor._get_tss_series()
        assert len(result) == 2
        assert result[0] == 60.0
        assert result[1] == 60.0


class TestVDOTPredictorGetTotalRecords:
    def test_get_total_records_none(self):
        predictor = VDOTPredictor(base_vdot=45.0)
        result = predictor._get_total_records(None)
        assert result == 0

    def test_get_total_records_with_dim(self):
        sufficiency = MagicMock()
        dim = MagicMock()
        dim.name = "total_records"
        dim.current_value = 300.0
        sufficiency.dimensions = [dim]
        predictor = VDOTPredictor(base_vdot=45.0)
        result = predictor._get_total_records(sufficiency)
        assert result == 300

    def test_get_total_records_no_matching_dim(self):
        sufficiency = MagicMock()
        dim = MagicMock()
        dim.name = "other_dim"
        dim.current_value = 300.0
        sufficiency.dimensions = [dim]
        predictor = VDOTPredictor(base_vdot=45.0)
        result = predictor._get_total_records(sufficiency)
        assert result == 0


class TestVDOTPredictorBuildTrainingData:
    def test_build_training_data_no_feature_engine(self):
        predictor = VDOTPredictor(base_vdot=45.0)
        X, y = predictor._build_training_data(_make_vdot_sessions(10))
        assert X.shape[0] == 0
        assert len(y) == 0

    def test_build_training_data_with_sessions(self):
        fe = _make_feature_engine()
        session_repo = MagicMock()
        session_repo.get_sessions_for_vdot.return_value = _make_vdot_sessions(50)
        predictor = VDOTPredictor(
            feature_engine=fe,
            session_repo=session_repo,
            base_vdot=45.0,
        )
        X, y = predictor._build_training_data(_make_vdot_sessions(50))
        assert X.shape[0] > 0
        assert len(y) > 0

    def test_build_training_data_short_distance_filtered(self):
        fe = _make_feature_engine()
        sessions = []
        for i in range(10):
            s = MagicMock()
            s.distance_m = 500.0
            s.duration_s = 300.0
            s.timestamp = datetime(2024, 1, 1 + i, 8, 0, 0)
            sessions.append(s)
        predictor = VDOTPredictor(feature_engine=fe, base_vdot=45.0)
        X, y = predictor._build_training_data(sessions)
        assert X.shape[0] == 0

    def test_build_training_data_no_timestamp(self):
        fe = _make_feature_engine()
        sessions = []
        for i in range(5):
            s = MagicMock()
            s.distance_m = 5000.0
            s.duration_s = 1800.0
            s.timestamp = None
            sessions.append(s)
        predictor = VDOTPredictor(feature_engine=fe, base_vdot=45.0)
        X, y = predictor._build_training_data(sessions)
        assert X.shape[0] == 0


class TestVDOTPredictorPredictParametric:
    def test_parametric_with_tss_series(self):
        banister = MagicMock()
        banister.predict.return_value = 46.5
        session_repo = MagicMock()
        sessions = []
        for i in range(5):
            s = MagicMock()
            s.date = f"2024-01-{10 + i:02d}"
            s.tss = 50.0
            sessions.append(s)
        session_repo.get_recent_sessions.return_value = sessions
        predictor = VDOTPredictor(
            data_assessor=_make_assessor(sufficient=False, parametric=True),
            banister_model=banister,
            session_repo=session_repo,
            base_vdot=45.0,
        )
        result = predictor._predict_parametric(days=30)
        assert result.prediction_type == "parametric"
        assert result.data_quality == DataQuality.INSUFFICIENT

    def test_parametric_banister_failure(self):
        banister = MagicMock()
        banister.predict.side_effect = Exception("model error")
        predictor = VDOTPredictor(
            data_assessor=_make_assessor(sufficient=False, parametric=True),
            banister_model=banister,
            base_vdot=45.0,
        )
        result = predictor._predict_parametric(days=30)
        assert result.prediction_type == "parametric"


class TestVDOTPredictorPredictBasic:
    def test_basic_prediction_values(self):
        predictor = VDOTPredictor(base_vdot=45.0)
        result = predictor._predict_basic(days=30)
        assert result.current_vdot == 45.0
        assert result.prediction_type == "basic"
        assert result.confidence == 0.5
        assert result.trend_slope == 0.01
        assert len(result.confidence_interval) == 2
        assert result.confidence_interval[0] < result.confidence_interval[1]


class TestVDOTPredictorMLEnhancedDegradation:
    def test_ml_enhanced_model_available_inference_fails_retrain_fails(self):
        fe = _make_feature_engine()
        mm = MagicMock()
        mm.get_model_status.return_value = MagicMock(is_available=True)
        mm.load_model.return_value = None
        session_repo = MagicMock()
        session_repo.get_sessions_for_vdot.return_value = _make_vdot_sessions(5)
        predictor = VDOTPredictor(
            feature_engine=fe,
            data_assessor=_make_assessor(sufficient=True),
            model_manager=mm,
            session_repo=session_repo,
            base_vdot=45.0,
        )
        result = predictor.predict(days=30)
        assert result.prediction_type in ("ml_enhanced", "parametric", "basic")

    def test_ml_enhanced_no_model_manager(self):
        fe = _make_feature_engine()
        session_repo = MagicMock()
        session_repo.get_sessions_for_vdot.return_value = _make_vdot_sessions(5)
        predictor = VDOTPredictor(
            feature_engine=fe,
            data_assessor=_make_assessor(sufficient=True),
            model_manager=None,
            session_repo=session_repo,
            base_vdot=45.0,
        )
        result = predictor.predict(days=30)
        assert result.prediction_type in ("ml_enhanced", "parametric", "basic")

    def test_ml_enhanced_no_data_assessor(self):
        fe = _make_feature_engine()
        predictor = VDOTPredictor(
            feature_engine=fe,
            data_assessor=None,
            model_manager=_make_model_manager(),
            base_vdot=45.0,
        )
        result = predictor.predict(days=30)
        assert result.prediction_type in ("basic", "parametric")


class TestVDOTPredictorFeatureImportance:
    def test_feature_importance_with_model_manager(self):
        fe = _make_feature_engine()
        mm = MagicMock()
        mock_model = MagicMock()
        mock_model.feature_importances_ = np.array(
            [0.3, 0.2, 0.15, 0.1, 0.08, 0.06, 0.04, 0.03, 0.02, 0.01, 0.005, 0.005]
        )
        mm.load_model.return_value = {"p50": mock_model}
        predictor = VDOTPredictor(
            feature_engine=fe,
            model_manager=mm,
            base_vdot=45.0,
        )
        factors = predictor.get_feature_importance()
        assert isinstance(factors, list)
        assert len(factors) <= 3

    def test_feature_importance_no_model_no_manager(self):
        fe = _make_feature_engine()
        predictor = VDOTPredictor(
            feature_engine=fe,
            model_manager=None,
            base_vdot=45.0,
        )
        factors = predictor.get_feature_importance()
        assert isinstance(factors, list)
        assert len(factors) <= 3
        if factors:
            for f in factors:
                assert f.weight > 0

    def test_feature_importance_no_feature_engine(self):
        predictor = VDOTPredictor(
            feature_engine=None,
            model_manager=None,
            base_vdot=45.0,
        )
        factors = predictor.get_feature_importance()
        assert isinstance(factors, list)
        assert len(factors) == 0


class TestVDOTPredictorTrainModelEdgeCases:
    def test_train_model_exception(self):
        session_repo = MagicMock()
        session_repo.get_sessions_for_vdot.side_effect = Exception("db error")
        predictor = VDOTPredictor(
            feature_engine=_make_feature_engine(),
            session_repo=session_repo,
            base_vdot=45.0,
        )
        result = predictor.train_model()
        assert result.success is False
        assert "训练失败" in result.message

    def test_train_model_valid_samples_insufficient(self):
        session_repo = MagicMock()
        sessions = []
        for i in range(5):
            s = MagicMock()
            s.distance_m = 500.0
            s.duration_s = 300.0
            s.timestamp = datetime(2024, 1, 1 + i, 8, 0, 0)
            sessions.append(s)
        session_repo.get_sessions_for_vdot.return_value = sessions
        predictor = VDOTPredictor(
            feature_engine=_make_feature_engine(),
            session_repo=session_repo,
            base_vdot=45.0,
        )
        result = predictor.train_model()
        assert result.success is False
