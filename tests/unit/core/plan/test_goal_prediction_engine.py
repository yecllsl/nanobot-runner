# v0.12.0 预测引擎单元测试
# 覆盖 GoalPredictionEngine / PredictionEvaluator

import pytest

from src.core.models import GoalAchievementEvaluation
from src.core.plan.goal_prediction_engine import (
    GoalPredictionEngine,
    PredictionEvaluator,
)


class TestGoalPredictionEngine:
    """GoalPredictionEngine 测试"""

    def setup_method(self) -> None:
        self.engine = GoalPredictionEngine()

    def test_evaluate_vdot_goal_already_achieved(self) -> None:
        evaluation = self.engine.evaluate_goal(
            goal_type="vdot",
            goal_value=40.0,
            current_vdot=45.0,
        )
        assert evaluation.achievement_probability == 1.0
        assert evaluation.gap <= 0

    def test_evaluate_vdot_goal_with_gap(self) -> None:
        evaluation = self.engine.evaluate_goal(
            goal_type="vdot",
            goal_value=50.0,
            current_vdot=45.0,
            weekly_volume_km=40.0,
            training_consistency=0.8,
            weeks_available=16,
        )
        assert isinstance(evaluation, GoalAchievementEvaluation)
        assert evaluation.goal_type == "vdot"
        assert evaluation.current_value == 45.0
        assert 0.0 <= evaluation.achievement_probability <= 1.0

    def test_evaluate_vdot_goal_large_gap(self) -> None:
        evaluation = self.engine.evaluate_goal(
            goal_type="vdot",
            goal_value=60.0,
            current_vdot=40.0,
        )
        assert any("差距" in r for r in evaluation.key_risks)

    def test_evaluate_vdot_goal_with_trend(self) -> None:
        evaluation = self.engine.evaluate_goal(
            goal_type="vdot",
            goal_value=50.0,
            current_vdot=45.0,
            vdot_trend=[43.0, 44.0, 44.5, 45.0],
            weekly_volume_km=40.0,
            training_consistency=0.8,
        )
        assert evaluation.achievement_probability > 0.0

    def test_evaluate_5k_goal(self) -> None:
        evaluation = self.engine.evaluate_goal(
            goal_type="5k",
            goal_value=1500.0,
            current_vdot=45.0,
        )
        assert evaluation.goal_type == "5k"
        assert evaluation.current_value > 0

    def test_evaluate_marathon_goal(self) -> None:
        evaluation = self.engine.evaluate_goal(
            goal_type="marathon",
            goal_value=14400.0,
            current_vdot=45.0,
        )
        assert evaluation.goal_type == "marathon"

    def test_low_weekly_volume_risk(self) -> None:
        evaluation = self.engine.evaluate_goal(
            goal_type="vdot",
            goal_value=50.0,
            current_vdot=45.0,
            weekly_volume_km=15.0,
        )
        assert any("周跑量不足" in r for r in evaluation.key_risks)

    def test_high_weekly_volume_risk(self) -> None:
        evaluation = self.engine.evaluate_goal(
            goal_type="vdot",
            goal_value=50.0,
            current_vdot=45.0,
            weekly_volume_km=90.0,
        )
        assert any("周跑量偏高" in r or "伤病" in r for r in evaluation.key_risks)

    def test_low_training_consistency_risk(self) -> None:
        evaluation = self.engine.evaluate_goal(
            goal_type="vdot",
            goal_value=50.0,
            current_vdot=45.0,
            training_consistency=0.3,
        )
        assert any("训练一致性" in r for r in evaluation.key_risks)

    def test_improvement_suggestions_generated(self) -> None:
        evaluation = self.engine.evaluate_goal(
            goal_type="vdot",
            goal_value=50.0,
            current_vdot=45.0,
        )
        assert len(evaluation.improvement_suggestions) > 0

    def test_estimate_weeks_to_achieve(self) -> None:
        evaluation = self.engine.evaluate_goal(
            goal_type="vdot",
            goal_value=50.0,
            current_vdot=45.0,
            weekly_volume_km=40.0,
            training_consistency=0.8,
        )
        assert evaluation.estimated_weeks_to_achieve is not None
        assert evaluation.estimated_weeks_to_achieve >= 4

    def test_estimate_weeks_already_achieved(self) -> None:
        evaluation = self.engine.evaluate_goal(
            goal_type="vdot",
            goal_value=40.0,
            current_vdot=45.0,
        )
        assert evaluation.estimated_weeks_to_achieve == 0

    def test_confidence_with_trend_data(self) -> None:
        evaluation = self.engine.evaluate_goal(
            goal_type="vdot",
            goal_value=50.0,
            current_vdot=45.0,
            vdot_trend=[43.0, 44.0, 44.5, 45.0],
            training_consistency=0.8,
        )
        assert evaluation.confidence > 0.0

    def test_confidence_without_trend_data(self) -> None:
        evaluation = self.engine.evaluate_goal(
            goal_type="vdot",
            goal_value=50.0,
            current_vdot=45.0,
        )
        assert evaluation.confidence > 0.0

    def test_to_dict_output(self) -> None:
        evaluation = self.engine.evaluate_goal(
            goal_type="vdot",
            goal_value=50.0,
            current_vdot=45.0,
        )
        d = evaluation.to_dict()
        assert "goal_type" in d
        assert "achievement_probability" in d
        assert "key_risks" in d
        assert "improvement_suggestions" in d

    def test_low_vdot_risk(self) -> None:
        evaluation = self.engine.evaluate_goal(
            goal_type="vdot",
            goal_value=40.0,
            current_vdot=25.0,
        )
        assert any("VDOT较低" in r for r in evaluation.key_risks)

    def test_unknown_goal_type(self) -> None:
        evaluation = self.engine.evaluate_goal(
            goal_type="unknown",
            goal_value=100.0,
            current_vdot=45.0,
        )
        assert evaluation.goal_type == "unknown"
        assert evaluation.current_value == 45.0


class TestPredictionEvaluator:
    """PredictionEvaluator 测试"""

    def setup_method(self) -> None:
        self.evaluator = PredictionEvaluator()

    def test_evaluate_accuracy_accurate(self) -> None:
        result = self.evaluator.evaluate_prediction_accuracy(
            predicted_value=45.0,
            actual_value=44.5,
        )
        assert result["is_accurate"] is True
        assert result["relative_error_pct"] < 5.0

    def test_evaluate_accuracy_inaccurate(self) -> None:
        result = self.evaluator.evaluate_prediction_accuracy(
            predicted_value=50.0,
            actual_value=40.0,
        )
        assert result["is_accurate"] is False
        assert result["relative_error_pct"] > 5.0

    def test_evaluate_accuracy_zero_actual(self) -> None:
        result = self.evaluator.evaluate_prediction_accuracy(
            predicted_value=45.0,
            actual_value=0.0,
        )
        assert result["is_accurate"] is False

    def test_evaluate_batch(self) -> None:
        predictions = [45.0, 50.0, 42.0]
        actuals = [44.0, 49.0, 41.0]
        result = self.evaluator.evaluate_batch(predictions, actuals)
        assert result["count"] == 3
        assert result["accuracy_rate"] > 0.0

    def test_evaluate_batch_empty(self) -> None:
        result = self.evaluator.evaluate_batch([], [])
        assert result["count"] == 0

    def test_evaluate_batch_mismatched_length(self) -> None:
        with pytest.raises(ValueError, match="长度不一致"):
            self.evaluator.evaluate_batch([45.0], [44.0, 43.0])

    def test_calculate_prediction_metrics(self) -> None:
        predictions = [45.0, 50.0, 42.0]
        actuals = [44.0, 49.0, 41.0]
        result = self.evaluator.calculate_prediction_metrics(predictions, actuals)
        assert "vdot_bias" in result
        assert "bias_direction" in result

    def test_calculate_prediction_metrics_overestimate(self) -> None:
        predictions = [50.0, 55.0, 48.0]
        actuals = [45.0, 50.0, 43.0]
        result = self.evaluator.calculate_prediction_metrics(predictions, actuals)
        assert result["bias_direction"] == "overestimate"

    def test_calculate_prediction_metrics_underestimate(self) -> None:
        predictions = [40.0, 45.0, 38.0]
        actuals = [45.0, 50.0, 43.0]
        result = self.evaluator.calculate_prediction_metrics(predictions, actuals)
        assert result["bias_direction"] == "underestimate"
