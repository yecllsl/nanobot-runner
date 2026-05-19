from __future__ import annotations

from unittest.mock import MagicMock

from src.core.base.exceptions import NanobotRunnerError
from src.core.prediction.models import (
    ModelTrainingResult,
    PredictionStatusReport,
)
from src.core.prediction.prediction_engine import PredictionEngine


def _make_vdot_predictor():
    vp = MagicMock()
    vp.predict.return_value = MagicMock(
        current_vdot=45.0,
        predicted_vdot=46.0,
        prediction_days=30,
        confidence_interval=(45.0, 47.0),
        confidence=0.85,
        trend_slope=0.05,
        key_factors=[],
        data_quality="sufficient",
        prediction_type="ml_enhanced",
        model_info=None,
    )
    vp.train_model.return_value = ModelTrainingResult(
        model_type="vdot_predictor",
        version="v1",
        training_samples=500,
        validation_error=1.5,
        training_duration_seconds=45.0,
        success=True,
        message="训练完成",
    )
    return vp


def _make_race_predictor():
    rp = MagicMock()
    rp.predict.return_value = MagicMock(
        distance_km=42.195,
        predicted_time="3:45:00",
        predicted_time_seconds=13500.0,
        confidence=0.8,
        best_case="3:35:00",
        worst_case="3:55:00",
        predicted_vdot=46.0,
        pace_strategy=None,
        prediction_type="personalized",
        personalization_info=None,
    )
    return rp


def _make_injury_predictor():
    ip = MagicMock()
    ip.predict.return_value = MagicMock(
        risk_score=30.0,
        risk_level="low",
        risk_timeline=[],
        acute_load_risk=None,
        chronic_risk=None,
        body_signal_risk=None,
        top_risk_factors=[],
        recommendations=[],
        data_quality="sufficient",
        prediction_type="ml_enhanced",
    )
    ip.report_injury.return_value = MagicMock(
        injury_id="inj_001",
        injury_type="overuse",
        severity="moderate",
        date="2026-05-08",
        label_type="confirmed",
        created_at="2026-05-08T10:00:00",
        success=True,
    )
    ip.train_model.return_value = ModelTrainingResult(
        model_type="injury_predictor",
        version="v1",
        training_samples=300,
        validation_error=0.05,
        training_duration_seconds=30.0,
        success=True,
        message="训练完成",
    )
    return ip


def _make_training_response_predictor():
    tp = MagicMock()
    tp.predict.return_value = MagicMock(
        session_type="threshold",
        duration_min=60,
        intensity="high",
        predicted_vdot_impact=0.3,
        predicted_fatigue_impact=15.0,
        predicted_recovery_hours=36.0,
        predicted_injury_risk_delta=0.05,
        banister_fitness_delta=0.5,
        banister_fatigue_delta=8.0,
        prediction_type="parametric",
    )
    return tp


def _make_data_assessor():
    da = MagicMock()
    da.get_full_status.return_value = PredictionStatusReport(
        vdot_status=MagicMock(),
        race_status=MagicMock(),
        injury_status=MagicMock(),
        overall_ready_count=2,
        advice=["数据充足"],
    )
    return da


def _make_model_manager():
    mm = MagicMock()
    mm.get_model_status.return_value = MagicMock(is_available=True)
    return mm


def _make_engine():
    return PredictionEngine(
        vdot_predictor=_make_vdot_predictor(),
        race_predictor=_make_race_predictor(),
        injury_predictor=_make_injury_predictor(),
        training_response_predictor=_make_training_response_predictor(),
        data_assessor=_make_data_assessor(),
        model_manager=_make_model_manager(),
    )


class TestPredictionEngineManageModel:
    def test_manage_model_status(self):
        engine = _make_engine()
        result = engine.manage_model(action="status", model_type="vdot_predictor")
        assert result.success is True
        assert "可用" in result.message

    def test_manage_model_train_vdot(self):
        engine = _make_engine()
        result = engine.manage_model(action="train", model_type="vdot_predictor")
        assert result.success is True

    def test_manage_model_train_injury(self):
        engine = _make_engine()
        result = engine.manage_model(action="train", model_type="injury_predictor")
        assert result.success is True

    def test_manage_model_train_unsupported(self):
        engine = _make_engine()
        result = engine.manage_model(action="train", model_type="unknown_model")
        assert result.success is False
        assert "暂不支持" in result.message

    def test_manage_model_rollback(self):
        mm = _make_model_manager()
        mm.rollback.return_value = True
        engine = PredictionEngine(
            vdot_predictor=_make_vdot_predictor(),
            race_predictor=_make_race_predictor(),
            injury_predictor=_make_injury_predictor(),
            training_response_predictor=_make_training_response_predictor(),
            data_assessor=_make_data_assessor(),
            model_manager=mm,
        )
        result = engine.manage_model(action="rollback", model_type="vdot_predictor")
        assert result.success is True

    def test_manage_model_rollback_no_versions(self):
        mm = _make_model_manager()
        mm.rollback.return_value = False
        engine = PredictionEngine(
            vdot_predictor=_make_vdot_predictor(),
            race_predictor=_make_race_predictor(),
            injury_predictor=_make_injury_predictor(),
            training_response_predictor=_make_training_response_predictor(),
            data_assessor=_make_data_assessor(),
            model_manager=mm,
        )
        result = engine.manage_model(action="rollback", model_type="vdot_predictor")
        assert result.success is False

    def test_manage_model_rollback_no_manager(self):
        engine = PredictionEngine(
            vdot_predictor=_make_vdot_predictor(),
            race_predictor=_make_race_predictor(),
            injury_predictor=_make_injury_predictor(),
            training_response_predictor=_make_training_response_predictor(),
            data_assessor=_make_data_assessor(),
            model_manager=None,
        )
        result = engine.manage_model(action="rollback", model_type="vdot_predictor")
        assert result.success is False
        assert "未注入" in result.message

    def test_manage_model_rollback_exception(self):
        mm = _make_model_manager()
        mm.rollback.side_effect = NanobotRunnerError("rollback error")
        engine = PredictionEngine(
            vdot_predictor=_make_vdot_predictor(),
            race_predictor=_make_race_predictor(),
            injury_predictor=_make_injury_predictor(),
            training_response_predictor=_make_training_response_predictor(),
            data_assessor=_make_data_assessor(),
            model_manager=mm,
        )
        result = engine.manage_model(action="rollback", model_type="vdot_predictor")
        assert result.success is False
        assert "回滚失败" in result.message

    def test_manage_model_unknown_action(self):
        engine = _make_engine()
        result = engine.manage_model(action="unknown", model_type="vdot_predictor")
        assert result.success is False
        assert "未知操作" in result.message


class TestPredictionEngineCacheExtended:
    def test_cache_race_result(self):
        engine = _make_engine()
        result1 = engine.predict_race_result(distance_km=42.195)
        result2 = engine.predict_race_result(distance_km=42.195)
        assert result1 is result2

    def test_cache_injury_result(self):
        engine = _make_engine()
        result1 = engine.predict_injury_risk(days=21)
        result2 = engine.predict_injury_risk(days=21)
        assert result1 is result2

    def test_invalidate_cache_clears_all(self):
        engine = _make_engine()
        engine.predict_vdot_trend(days=30)
        engine.predict_race_result(distance_km=42.195)
        engine.predict_injury_risk(days=21)
        engine.invalidate_cache()
        assert engine._cache_vdot is None
        assert engine._cache_race is None
        assert engine._cache_injury is None
        assert engine._cache_date is None

    def test_training_response_no_cache(self):
        engine = _make_engine()
        result1 = engine.predict_training_response(
            session_type="threshold", duration_min=60, intensity="high"
        )
        result2 = engine.predict_training_response(
            session_type="threshold", duration_min=60, intensity="high"
        )
        assert result1 is not None
        assert result2 is not None


class TestPredictionEngineReportInjury:
    def test_report_injury_delegates(self):
        engine = _make_engine()
        result = engine.report_injury(
            injury_type="overuse", severity="moderate", date="2026-05-08"
        )
        assert result.success is True
        assert result.injury_type == "overuse"


class TestPredictionEngineCheckStatus:
    def test_check_prediction_status(self):
        engine = _make_engine()
        result = engine.check_prediction_status()
        assert isinstance(result, PredictionStatusReport)
        assert result.overall_ready_count == 2
