from __future__ import annotations

import contextlib
from unittest.mock import MagicMock

import pytest

from src.core.prediction.feature_engine import FeatureEngine
from src.core.prediction.injury_predictor import InjuryPredictor
from src.core.prediction.model_manager import ModelManager
from src.core.prediction.prediction_engine import PredictionEngine
from src.core.prediction.race_predictor import RacePredictor
from src.core.prediction.vdot_predictor import VDOTPredictor


@pytest.fixture
def tmp_models_dir(tmp_path):
    return tmp_path / "models"


@pytest.fixture
def model_manager(tmp_models_dir):
    return ModelManager(models_dir=str(tmp_models_dir))


def _make_session_repo(n: int = 50):
    repo = MagicMock()
    repo.get_sessions_for_vdot.return_value = [
        MagicMock(
            distance_m=5000.0 + i * 100,
            duration_s=1800.0 + i * 10,
            date=f"2026-03-{(i % 28) + 1:02d}",
        )
        for i in range(n)
    ]
    repo.get_sessions_for_injury.return_value = [
        MagicMock(
            distance_m=5000.0 + i * 100,
            duration_s=1800.0 + i * 10,
            tss=50.0 + i * 2,
            date=f"2026-03-{(i % 28) + 1:02d}",
        )
        for i in range(n)
    ]
    repo.get_recent_sessions.return_value = [
        MagicMock(
            distance_m=5000.0 + i * 100,
            duration_s=1800.0 + i * 10,
            tss=50.0 + i * 2,
            date=f"2026-03-{(i % 28) + 1:02d}",
        )
        for i in range(n)
    ]
    return repo


def _make_load_analyzer():
    analyzer = MagicMock()
    analyzer.calculate_ctl.return_value = 50.0
    analyzer.calculate_atl.return_value = 40.0
    analyzer.calculate_tsb.return_value = 10.0
    analyzer.get_weekly_load.return_value = 300.0
    analyzer.get_load_ramp_rate.return_value = 0.05
    return analyzer


def _make_hrv_analyzer():
    analyzer = MagicMock()
    analyzer.get_resting_hr_deviation.return_value = 3.0
    analyzer.get_rmssd_trend.return_value = 0.0
    analyzer.get_sdnn_deviation.return_value = 0.0
    return analyzer


def _make_body_signal_engine():
    engine = MagicMock()
    engine.get_fatigue_score.return_value = 30.0
    engine.get_recovery_status.return_value = "green"
    return engine


def _make_vdot_calculator():
    calc = MagicMock()
    calc.calculate_vdot.return_value = 45.0
    return calc


def _make_injury_analyzer():
    analyzer = MagicMock()
    analyzer.assess.return_value = {
        "risk_level": "low",
        "risk_score": 20.0,
        "risk_factors": [],
        "dimension_scores": {},
        "advice": "训练负荷合理",
    }
    return analyzer


def _make_assessor(sufficient: bool):
    assessor = MagicMock()
    report = MagicMock()
    report.is_sufficient = sufficient
    report.overall_progress_pct = 90.0 if sufficient else 30.0
    total_dim = MagicMock()
    total_dim.name = "total_records"
    total_dim.current_value = 400.0 if sufficient else 30.0
    report.dimensions = [total_dim]
    assessor.assess_sufficiency.return_value = report
    return assessor


def _make_feature_engine():
    return FeatureEngine(
        session_repo=_make_session_repo(),
        training_load_analyzer=_make_load_analyzer(),
        hrv_analyzer=_make_hrv_analyzer(),
        body_signal_engine=_make_body_signal_engine(),
        vdot_calculator=_make_vdot_calculator(),
    )


class TestVDOTPredictionE2E:
    def test_vdot_prediction_e2e(self, model_manager):
        session_repo = _make_session_repo()
        feature_engine = _make_feature_engine()
        assessor = _make_assessor(sufficient=True)
        banister_model = MagicMock()

        predictor = VDOTPredictor(
            feature_engine=feature_engine,
            data_assessor=assessor,
            model_manager=model_manager,
            banister_model=banister_model,
            session_repo=session_repo,
            base_vdot=45.0,
        )

        train_result = predictor.train_model()
        assert train_result.success is True
        assert train_result.model_type == "vdot_predictor"
        assert train_result.training_samples > 0

        loaded = model_manager.load_model("vdot_predictor")
        assert loaded is not None
        predictor._ml_model = loaded

        factors = predictor.get_feature_importance()
        assert isinstance(factors, list)


class TestInjuryPredictionE2E:
    def test_injury_prediction_e2e(self, model_manager, tmp_path):
        session_repo = _make_session_repo()
        feature_engine = _make_feature_engine()
        assessor = _make_assessor(sufficient=True)
        injury_analyzer = _make_injury_analyzer()

        predictor = InjuryPredictor(
            feature_engine=feature_engine,
            data_assessor=assessor,
            model_manager=model_manager,
            injury_analyzer=injury_analyzer,
            rule_baseline=injury_analyzer,
            logistic_model=MagicMock(),
            session_repo=session_repo,
            injury_labels_dir=str(tmp_path / "labels"),
        )

        train_result = predictor.train_model()
        assert train_result.success is True
        assert train_result.model_type == "injury_predictor"

        loaded = model_manager.load_model("injury_predictor")
        assert loaded is not None
        predictor._ml_model = loaded

        result = predictor.predict(days=21)
        assert result.prediction_type == "ml_enhanced"
        assert len(result.risk_timeline) > 0

        report_result = predictor.report_injury(
            injury_type="overuse", severity="moderate", date="2026-05-08"
        )
        assert report_result.success is True
        labels_dir = tmp_path / "labels"
        assert labels_dir.exists()


class TestRacePredictionE2E:
    def test_race_prediction_e2e(self, model_manager):
        race_records = [
            {"distance_km": 5.0, "time_seconds": 1500.0},
            {"distance_km": 10.0, "time_seconds": 3300.0},
            {"distance_km": 21.1, "time_seconds": 7500.0},
            {"distance_km": 42.195, "time_seconds": 16500.0},
        ]
        feature_engine = _make_feature_engine()
        assessor = _make_assessor(sufficient=True)

        predictor = RacePredictor(
            feature_engine=feature_engine,
            data_assessor=assessor,
            model_manager=model_manager,
            current_vdot=45.0,
            race_records=race_records,
        )

        exponent = predictor.fit_riegel_curve()
        assert 0.95 <= exponent <= 1.15

        result = predictor.predict(distance_km=42.195)
        assert result.prediction_type == "personalized"
        assert result.predicted_time_seconds > 0
        assert result.pace_strategy is not None

        personalization = predictor.learn_personalization()
        assert personalization["runner_type"] in ("endurance", "speed", "balanced")


class TestDegradationE2E:
    def test_degradation_insufficient_data(self, model_manager):
        session_repo = MagicMock()
        session_repo.get_sessions_for_vdot.return_value = [
            MagicMock(distance_m=5000.0, duration_s=1800.0) for _ in range(5)
        ]
        feature_engine = _make_feature_engine()
        assessor = _make_assessor(sufficient=False)

        predictor = VDOTPredictor(
            feature_engine=feature_engine,
            data_assessor=assessor,
            model_manager=model_manager,
            banister_model=MagicMock(),
            session_repo=session_repo,
            base_vdot=45.0,
        )

        result = predictor.predict(days=30)
        assert result.prediction_type in ("parametric", "basic")

    def test_degradation_injury_basic(self, model_manager):
        rule_baseline = MagicMock()
        rule_baseline.assess.return_value = {
            "risk_level": "low",
            "risk_score": 20.0,
            "risk_factors": [],
            "dimension_scores": {},
            "advice": "训练负荷合理",
        }
        feature_engine = _make_feature_engine()
        assessor = _make_assessor(sufficient=False)

        predictor = InjuryPredictor(
            feature_engine=feature_engine,
            data_assessor=assessor,
            model_manager=model_manager,
            rule_baseline=rule_baseline,
            logistic_model=MagicMock(),
        )

        result = predictor.predict(days=21)
        assert result.prediction_type == "basic"

    def test_degradation_race_standard(self, model_manager):
        feature_engine = _make_feature_engine()
        assessor = _make_assessor(sufficient=False)

        predictor = RacePredictor(
            feature_engine=feature_engine,
            data_assessor=assessor,
            model_manager=model_manager,
            current_vdot=45.0,
        )

        result = predictor.predict(distance_km=42.195)
        assert result.prediction_type == "standard"


class TestCross01NewDataInvalidatesCache:
    def test_new_data_invalidates_prediction_cache(self, model_manager):
        session_repo = _make_session_repo()
        feature_engine = _make_feature_engine()
        assessor = _make_assessor(sufficient=True)

        predictor = VDOTPredictor(
            feature_engine=feature_engine,
            data_assessor=assessor,
            model_manager=model_manager,
            banister_model=MagicMock(),
            session_repo=session_repo,
            base_vdot=45.0,
        )

        train_result = predictor.train_model()
        assert train_result.success is True

        should_update = model_manager.trigger_auto_update_if_needed(
            "vdot_predictor", new_samples=60
        )
        assert should_update is True


class TestCross02BodySignalToInjury:
    def test_body_signal_flows_to_feature_engine(self, model_manager, tmp_path):
        body_signal_engine = MagicMock()
        body_signal_engine.get_fatigue_score.return_value = 75.0
        body_signal_engine.get_recovery_status.return_value = "red"

        session_repo = _make_session_repo()
        feature_engine = FeatureEngine(
            session_repo=session_repo,
            training_load_analyzer=_make_load_analyzer(),
            hrv_analyzer=_make_hrv_analyzer(),
            body_signal_engine=body_signal_engine,
            vdot_calculator=_make_vdot_calculator(),
        )

        matrix = feature_engine.extract_race_features()
        body_signal_engine.get_fatigue_score.assert_called()

        feature_names = matrix.feature_names
        fatigue_idx = feature_names.index("pre_race_fatigue")
        assert matrix.features[0, fatigue_idx] > 0


class TestCross03CLIToPredictionEngine:
    def test_cli_predict_degradation_chain(self, model_manager):
        vdot_predictor = MagicMock()
        vdot_result = MagicMock()
        vdot_result.prediction_type = "ml_enhanced"
        vdot_result.predicted_vdot = 46.0
        vdot_result.confidence = 0.85
        vdot_predictor.predict.return_value = vdot_result

        prediction_engine = PredictionEngine(
            vdot_predictor=vdot_predictor,
            race_predictor=MagicMock(),
            injury_predictor=MagicMock(),
            model_manager=model_manager,
        )

        result = prediction_engine.predict_vdot_trend(days=30)
        assert result.prediction_type == "ml_enhanced"

    def test_cli_predict_rollback(self, model_manager, tmp_models_dir):
        model_manager.save_model(
            "vdot_predictor",
            {"type": "v1"},
            metadata={"version": "v1", "sklearn_version": "1.5.0"},
        )
        model_manager.save_model(
            "vdot_predictor",
            {"type": "v2"},
            metadata={"version": "v2", "sklearn_version": "1.5.0"},
        )

        prediction_engine = PredictionEngine(
            vdot_predictor=MagicMock(),
            race_predictor=MagicMock(),
            injury_predictor=MagicMock(),
            model_manager=model_manager,
        )

        result = prediction_engine.manage_model(
            action="rollback", model_type="vdot_predictor"
        )
        assert result.success is True


class TestCross04AgentToolTimeout:
    def test_agent_tool_timeout_handling(self, model_manager):
        vdot_predictor = MagicMock()
        vdot_predictor.predict.side_effect = TimeoutError("prediction timed out")

        prediction_engine = PredictionEngine(
            vdot_predictor=vdot_predictor,
            race_predictor=MagicMock(),
            injury_predictor=MagicMock(),
            model_manager=model_manager,
        )

        with contextlib.suppress(TimeoutError):
            prediction_engine.predict_vdot_trend(days=30)
