from __future__ import annotations

from src.core.prediction.baselines.banister_ir import BanisterIRModel
from src.core.prediction.models import TrainingResponse
from src.core.prediction.training_response_predictor import TrainingResponsePredictor


class TestTrainingResponseEasy:
    def test_easy_run(self):
        predictor = TrainingResponsePredictor(
            banister_model=BanisterIRModel(),
            base_vdot=45.0,
        )
        result = predictor.predict(
            session_type="easy",
            duration_min=45,
            intensity="low",
        )
        assert isinstance(result, TrainingResponse)
        assert result.prediction_type == "parametric"
        assert result.predicted_recovery_hours < 24


class TestTrainingResponseThreshold:
    def test_threshold_run(self):
        predictor = TrainingResponsePredictor(
            banister_model=BanisterIRModel(),
            base_vdot=45.0,
        )
        result = predictor.predict(
            session_type="threshold",
            duration_min=60,
            intensity="high",
        )
        assert isinstance(result, TrainingResponse)
        assert result.predicted_recovery_hours >= 24


class TestTrainingResponseInterval:
    def test_interval_run(self):
        predictor = TrainingResponsePredictor(
            banister_model=BanisterIRModel(),
            base_vdot=45.0,
        )
        result = predictor.predict(
            session_type="interval",
            duration_min=60,
            intensity="very_high",
        )
        assert isinstance(result, TrainingResponse)
        assert result.predicted_recovery_hours >= 36


class TestTrainingResponseAllFields:
    def test_all_fields_populated(self):
        predictor = TrainingResponsePredictor(
            banister_model=BanisterIRModel(),
            base_vdot=45.0,
        )
        result = predictor.predict(
            session_type="threshold",
            duration_min=60,
            intensity="high",
        )
        assert result.session_type == "threshold"
        assert result.duration_min == 60
        assert result.intensity == "high"
        assert result.predicted_vdot_impact >= 0
        assert result.predicted_fatigue_impact >= 0
        assert result.predicted_recovery_hours > 0
        assert result.predicted_injury_risk_delta >= 0
        assert result.banister_fitness_delta >= 0
        assert result.banister_fatigue_delta >= 0
