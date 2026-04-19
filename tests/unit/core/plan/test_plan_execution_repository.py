# PlanExecutionRepository单元测试

from unittest.mock import MagicMock

import pytest

from src.core.models import (
    DailyPlan,
    FitnessLevel,
    PlanType,
    TrainingPlan,
    TrainingResponsePattern,
    TrainingType,
    WeeklySchedule,
)
from src.core.plan.plan_execution_repository import (
    PlanExecutionRepository,
    PlanExecutionRepositoryError,
)
from src.core.plan.plan_manager import PlanManager


def create_test_plan_with_execution(
    plan_id: str = "test_plan",
    completed_days: int = 3,
    total_days: int = 7,
) -> TrainingPlan:
    """创建带执行数据的测试训练计划"""
    daily_plans = []
    workout_types = [
        TrainingType.EASY,
        TrainingType.TEMPO,
        TrainingType.INTERVAL,
        TrainingType.LONG,
        TrainingType.RECOVERY,
        TrainingType.EASY,
        TrainingType.REST,
    ]

    for i in range(total_days):
        day = DailyPlan(
            date=f"2026-04-{i + 1:02d}",
            workout_type=workout_types[i % len(workout_types)],
            distance_km=5.0 + i * 0.5,
            duration_min=30 + i * 5,
        )
        if i < completed_days:
            day.completed = True
            day.actual_distance_km = day.distance_km
            day.actual_duration_min = day.duration_min
            day.actual_avg_hr = 140 + i * 5
            day.completion_rate = 1.0 if i < 2 else 0.8
            day.effort_score = 4 + i
            day.hr_drift = 2.5 + i * 0.3
        daily_plans.append(day)

    week = WeeklySchedule(
        week_number=1,
        start_date="2026-04-01",
        end_date="2026-04-07",
        daily_plans=daily_plans,
    )
    return TrainingPlan(
        plan_id=plan_id,
        user_id="test_user",
        plan_type=PlanType.BASE,
        fitness_level=FitnessLevel.INTERMEDIATE,
        start_date="2026-04-01",
        end_date="2026-04-30",
        goal_distance_km=10.0,
        goal_date="2026-04-30",
        weeks=[week],
    )


class TestPlanExecutionRepositoryError:
    """测试仓储异常"""

    def test_error_has_default_code(self):
        error = PlanExecutionRepositoryError("test error")
        assert error.error_code == "PLAN_EXECUTION_REPO_ERROR"

    def test_error_with_custom_suggestion(self):
        error = PlanExecutionRepositoryError("test", recovery_suggestion="try again")
        assert error.recovery_suggestion == "try again"


class TestGetPlanExecutionStats:
    """测试获取计划执行统计"""

    def setup_method(self):
        self.mock_plan_manager = MagicMock(spec=PlanManager)
        self.repo = PlanExecutionRepository(self.mock_plan_manager)

    def test_returns_empty_stats_when_no_daily_plans(self):
        plan = TrainingPlan(
            plan_id="empty_plan",
            user_id="test_user",
            plan_type=PlanType.BASE,
            fitness_level=FitnessLevel.INTERMEDIATE,
            start_date="2026-04-01",
            end_date="2026-04-30",
            goal_distance_km=10.0,
            goal_date="2026-04-30",
            weeks=[],
        )
        self.mock_plan_manager.get_plan.return_value = plan

        stats = self.repo.get_plan_execution_stats("empty_plan")

        assert stats.total_planned_days == 0
        assert stats.completed_days == 0
        assert stats.completion_rate == 0.0

    def test_returns_correct_stats_with_execution_data(self):
        plan = create_test_plan_with_execution(completed_days=3, total_days=7)
        self.mock_plan_manager.get_plan.return_value = plan

        stats = self.repo.get_plan_execution_stats("test_plan")

        assert stats.total_planned_days == 7
        assert stats.completed_days == 3
        assert stats.completion_rate == pytest.approx(3 / 7, rel=1e-2)
        assert stats.total_distance_km > 0
        assert stats.total_duration_min > 0

    def test_raises_error_when_plan_not_found(self):
        self.mock_plan_manager.get_plan.return_value = None

        with pytest.raises(PlanExecutionRepositoryError, match="计划不存在"):
            self.repo.get_plan_execution_stats("nonexistent")

    def test_stats_avg_effort_score(self):
        plan = create_test_plan_with_execution(completed_days=3, total_days=7)
        self.mock_plan_manager.get_plan.return_value = plan

        stats = self.repo.get_plan_execution_stats("test_plan")

        assert stats.avg_effort_score > 0

    def test_stats_avg_hr(self):
        plan = create_test_plan_with_execution(completed_days=3, total_days=7)
        self.mock_plan_manager.get_plan.return_value = plan

        stats = self.repo.get_plan_execution_stats("test_plan")

        assert stats.avg_hr is not None
        assert stats.avg_hr > 0

    def test_stats_to_dict(self):
        plan = create_test_plan_with_execution(completed_days=3, total_days=7)
        self.mock_plan_manager.get_plan.return_value = plan

        stats = self.repo.get_plan_execution_stats("test_plan")
        result = stats.to_dict()

        assert "plan_id" in result
        assert "total_planned_days" in result
        assert "completion_rate" in result
        assert isinstance(result["completion_rate"], float)


class TestGetTrainingResponsePatterns:
    """测试获取训练响应模式"""

    def setup_method(self):
        self.mock_plan_manager = MagicMock(spec=PlanManager)
        self.repo = PlanExecutionRepository(self.mock_plan_manager)

    def test_returns_empty_when_no_completed_days(self):
        plan = create_test_plan_with_execution(completed_days=0, total_days=7)
        self.mock_plan_manager.get_plan.return_value = plan

        patterns = self.repo.get_training_response_patterns("test_plan")

        assert patterns == []

    def test_returns_patterns_grouped_by_workout_type(self):
        plan = create_test_plan_with_execution(completed_days=5, total_days=7)
        self.mock_plan_manager.get_plan.return_value = plan

        patterns = self.repo.get_training_response_patterns("test_plan")

        assert len(patterns) > 0
        for p in patterns:
            assert isinstance(p, TrainingResponsePattern)
            assert isinstance(p.workout_type, TrainingType)
            assert p.sample_count > 0

    def test_patterns_sorted_by_completion_rate(self):
        plan = create_test_plan_with_execution(completed_days=5, total_days=7)
        self.mock_plan_manager.get_plan.return_value = plan

        patterns = self.repo.get_training_response_patterns("test_plan")

        for i in range(len(patterns) - 1):
            assert (
                patterns[i].avg_completion_rate >= patterns[i + 1].avg_completion_rate
            )

    def test_pattern_to_dict(self):
        plan = create_test_plan_with_execution(completed_days=3, total_days=7)
        self.mock_plan_manager.get_plan.return_value = plan

        patterns = self.repo.get_training_response_patterns("test_plan")

        if patterns:
            result = patterns[0].to_dict()
            assert "workout_type" in result
            assert "avg_completion_rate" in result
            assert "recommendation" in result

    def test_raises_error_when_plan_not_found(self):
        self.mock_plan_manager.get_plan.return_value = None

        with pytest.raises(PlanExecutionRepositoryError, match="计划不存在"):
            self.repo.get_training_response_patterns("nonexistent")


class TestValidateExecutionFeedback:
    """测试执行反馈验证"""

    def setup_method(self):
        self.mock_plan_manager = MagicMock(spec=PlanManager)
        self.repo = PlanExecutionRepository(self.mock_plan_manager)

    def test_valid_completion_rate(self):
        errors = self.repo.validate_execution_feedback(completion_rate=0.8)
        assert len(errors) == 0

    def test_invalid_completion_rate_too_high(self):
        errors = self.repo.validate_execution_feedback(completion_rate=1.5)
        assert len(errors) == 1
        assert "0.0-1.0" in errors[0]

    def test_invalid_completion_rate_negative(self):
        errors = self.repo.validate_execution_feedback(completion_rate=-0.1)
        assert len(errors) == 1

    def test_valid_effort_score(self):
        errors = self.repo.validate_execution_feedback(effort_score=5)
        assert len(errors) == 0

    def test_invalid_effort_score_too_high(self):
        errors = self.repo.validate_execution_feedback(effort_score=11)
        assert len(errors) == 1
        assert "1-10" in errors[0]

    def test_invalid_effort_score_zero(self):
        errors = self.repo.validate_execution_feedback(effort_score=0)
        assert len(errors) == 1

    def test_both_invalid(self):
        errors = self.repo.validate_execution_feedback(
            completion_rate=2.0, effort_score=15
        )
        assert len(errors) == 2

    def test_none_values_pass(self):
        errors = self.repo.validate_execution_feedback(
            completion_rate=None, effort_score=None
        )
        assert len(errors) == 0


class TestGenerateRecommendation:
    """测试训练建议生成"""

    def setup_method(self):
        self.mock_plan_manager = MagicMock(spec=PlanManager)
        self.repo = PlanExecutionRepository(self.mock_plan_manager)

    def test_high_completion_low_effort(self):
        rec = self.repo._generate_recommendation(0.95, 4, None)
        assert "适应良好" in rec

    def test_moderate_completion_moderate_effort(self):
        rec = self.repo._generate_recommendation(0.75, 6, None)
        assert "维持" in rec

    def test_low_completion(self):
        rec = self.repo._generate_recommendation(0.4, 8, None)
        assert "适应较差" in rec

    def test_high_effort(self):
        rec = self.repo._generate_recommendation(0.6, 9, None)
        assert "适应较差" in rec

    def test_high_hr_drift(self):
        rec = self.repo._generate_recommendation(0.8, 5, 6.0)
        assert "心率漂移" in rec

    def test_normal_response(self):
        rec = self.repo._generate_recommendation(0.65, 7, 3.0)
        assert "尚可" in rec
