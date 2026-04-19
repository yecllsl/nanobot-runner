# v0.10.0数据模型扩展单元测试


from src.core.models import (
    DailyPlan,
    PlanExecutionStats,
    TrainingResponsePattern,
    TrainingType,
)


class TestDailyPlanExtension:
    """测试DailyPlan扩展字段"""

    def test_new_fields_default_values(self):
        plan = DailyPlan(
            date="2026-04-01",
            workout_type=TrainingType.EASY,
            distance_km=5.0,
            duration_min=30,
        )
        assert plan.completion_rate is None
        assert plan.effort_score is None
        assert plan.feedback_notes == ""

    def test_set_completion_rate(self):
        plan = DailyPlan(
            date="2026-04-01",
            workout_type=TrainingType.EASY,
            distance_km=5.0,
            duration_min=30,
            completion_rate=0.8,
        )
        assert plan.completion_rate == 0.8

    def test_set_effort_score(self):
        plan = DailyPlan(
            date="2026-04-01",
            workout_type=TrainingType.EASY,
            distance_km=5.0,
            duration_min=30,
            effort_score=7,
        )
        assert plan.effort_score == 7

    def test_set_feedback_notes(self):
        plan = DailyPlan(
            date="2026-04-01",
            workout_type=TrainingType.EASY,
            distance_km=5.0,
            duration_min=30,
            feedback_notes="感觉不错",
        )
        assert plan.feedback_notes == "感觉不错"

    def test_to_dict_includes_new_fields(self):
        plan = DailyPlan(
            date="2026-04-01",
            workout_type=TrainingType.EASY,
            distance_km=5.0,
            duration_min=30,
            completion_rate=0.85,
            effort_score=5,
            feedback_notes="轻松",
        )
        d = plan.to_dict()

        assert "completion_rate" in d
        assert d["completion_rate"] == 0.85
        assert "effort_score" in d
        assert d["effort_score"] == 5
        assert "feedback_notes" in d
        assert d["feedback_notes"] == "轻松"

    def test_to_dict_none_completion_rate(self):
        plan = DailyPlan(
            date="2026-04-01",
            workout_type=TrainingType.EASY,
            distance_km=5.0,
            duration_min=30,
        )
        d = plan.to_dict()
        assert d["completion_rate"] is None
        assert d["effort_score"] is None

    def test_to_dict_rounds_completion_rate(self):
        plan = DailyPlan(
            date="2026-04-01",
            workout_type=TrainingType.EASY,
            distance_km=5.0,
            duration_min=30,
            completion_rate=0.8567,
        )
        d = plan.to_dict()
        assert d["completion_rate"] == 0.86


class TestPlanExecutionStats:
    """测试PlanExecutionStats数据类"""

    def test_create_stats(self):
        stats = PlanExecutionStats(
            plan_id="test_plan",
            total_planned_days=7,
            completed_days=5,
            completion_rate=0.71,
            avg_effort_score=5.5,
            total_distance_km=25.0,
            total_duration_min=180,
            avg_hr=145,
            avg_hr_drift=2.5,
        )
        assert stats.plan_id == "test_plan"
        assert stats.total_planned_days == 7
        assert stats.completed_days == 5
        assert stats.completion_rate == 0.71

    def test_to_dict(self):
        stats = PlanExecutionStats(
            plan_id="test_plan",
            total_planned_days=7,
            completed_days=5,
            completion_rate=0.714,
            avg_effort_score=5.56,
            total_distance_km=25.123,
            total_duration_min=180,
            avg_hr=145,
            avg_hr_drift=2.567,
        )
        d = stats.to_dict()

        assert d["plan_id"] == "test_plan"
        assert d["completion_rate"] == 0.71
        assert d["avg_effort_score"] == 5.56
        assert d["total_distance_km"] == 25.12
        assert d["avg_hr_drift"] == 2.567

    def test_to_dict_none_optional_fields(self):
        stats = PlanExecutionStats(
            plan_id="test_plan",
            total_planned_days=7,
            completed_days=0,
            completion_rate=0.0,
            avg_effort_score=0.0,
            total_distance_km=0.0,
            total_duration_min=0,
            avg_hr=None,
            avg_hr_drift=None,
        )
        d = stats.to_dict()
        assert d["avg_hr"] is None
        assert d["avg_hr_drift"] is None


class TestTrainingResponsePattern:
    """测试TrainingResponsePattern数据类"""

    def test_create_pattern(self):
        pattern = TrainingResponsePattern(
            workout_type=TrainingType.EASY,
            avg_completion_rate=0.9,
            avg_effort_score=4.0,
            avg_hr_drift=1.5,
            sample_count=5,
            recommendation="适应良好",
        )
        assert pattern.workout_type == TrainingType.EASY
        assert pattern.avg_completion_rate == 0.9
        assert pattern.sample_count == 5

    def test_to_dict(self):
        pattern = TrainingResponsePattern(
            workout_type=TrainingType.TEMPO,
            avg_completion_rate=0.756,
            avg_effort_score=6.12,
            avg_hr_drift=2.834,
            sample_count=4,
            recommendation="适应一般",
        )
        d = pattern.to_dict()

        assert d["workout_type"] == "tempo"
        assert d["avg_completion_rate"] == 0.76
        assert d["avg_effort_score"] == 6.12
        assert d["avg_hr_drift"] == 2.834
        assert d["sample_count"] == 4
        assert d["recommendation"] == "适应一般"
