# v0.12.0 数据模型单元测试
# 覆盖 GoalAchievementEvaluation / LongTermPlan / TrainingCycle / SmartTrainingAdvice

import pytest

from src.core.models import (
    GoalAchievementEvaluation,
    LongTermPlan,
    SmartTrainingAdvice,
    TrainingCycle,
)


class TestGoalAchievementEvaluation:
    """GoalAchievementEvaluation 测试"""

    def test_create_valid(self) -> None:
        evaluation = GoalAchievementEvaluation(
            goal_type="vdot",
            goal_value=50.0,
            current_value=45.0,
            achievement_probability=0.72,
            key_risks=["训练量不足"],
            improvement_suggestions=["增加间歇训练"],
            estimated_weeks_to_achieve=12,
            confidence=0.85,
        )
        assert evaluation.goal_type == "vdot"
        assert evaluation.achievement_probability == 0.72
        assert len(evaluation.key_risks) == 1

    def test_gap_property(self) -> None:
        evaluation = GoalAchievementEvaluation(
            goal_type="vdot",
            goal_value=50.0,
            current_value=45.0,
            achievement_probability=0.5,
            key_risks=[],
            improvement_suggestions=[],
            estimated_weeks_to_achieve=None,
            confidence=0.8,
        )
        assert evaluation.gap == 5.0

    def test_achievement_rate_property(self) -> None:
        evaluation = GoalAchievementEvaluation(
            goal_type="vdot",
            goal_value=50.0,
            current_value=45.0,
            achievement_probability=0.5,
            key_risks=[],
            improvement_suggestions=[],
            estimated_weeks_to_achieve=None,
            confidence=0.8,
        )
        assert evaluation.achievement_rate == 0.9

    def test_achievement_rate_capped_at_one(self) -> None:
        evaluation = GoalAchievementEvaluation(
            goal_type="vdot",
            goal_value=50.0,
            current_value=55.0,
            achievement_probability=1.0,
            key_risks=[],
            improvement_suggestions=[],
            estimated_weeks_to_achieve=None,
            confidence=0.9,
        )
        assert evaluation.achievement_rate == 1.0

    def test_achievement_rate_zero_goal(self) -> None:
        evaluation = GoalAchievementEvaluation(
            goal_type="vdot",
            goal_value=0.0,
            current_value=5.0,
            achievement_probability=0.5,
            key_risks=[],
            improvement_suggestions=[],
            estimated_weeks_to_achieve=None,
            confidence=0.5,
        )
        assert evaluation.achievement_rate == 0.0

    def test_invalid_achievement_probability(self) -> None:
        with pytest.raises(ValueError, match="achievement_probability"):
            GoalAchievementEvaluation(
                goal_type="vdot",
                goal_value=50.0,
                current_value=45.0,
                achievement_probability=1.5,
                key_risks=[],
                improvement_suggestions=[],
                estimated_weeks_to_achieve=None,
                confidence=0.8,
            )

    def test_invalid_confidence(self) -> None:
        with pytest.raises(ValueError, match="confidence"):
            GoalAchievementEvaluation(
                goal_type="vdot",
                goal_value=50.0,
                current_value=45.0,
                achievement_probability=0.5,
                key_risks=[],
                improvement_suggestions=[],
                estimated_weeks_to_achieve=None,
                confidence=-0.1,
            )

    def test_to_dict(self) -> None:
        evaluation = GoalAchievementEvaluation(
            goal_type="vdot",
            goal_value=50.0,
            current_value=45.0,
            achievement_probability=0.723,
            key_risks=["风险1"],
            improvement_suggestions=["建议1"],
            estimated_weeks_to_achieve=8,
            confidence=0.856,
        )
        d = evaluation.to_dict()
        assert d["goal_type"] == "vdot"
        assert d["achievement_probability"] == 0.72
        assert d["confidence"] == 0.86
        assert d["gap"] == 5.0
        assert d["achievement_rate"] == 0.9
        assert d["estimated_weeks_to_achieve"] == 8


class TestTrainingCycle:
    """TrainingCycle 测试"""

    def test_create_valid(self) -> None:
        cycle = TrainingCycle(
            cycle_type="base",
            start_date="2026-05-01",
            end_date="2026-05-28",
            weekly_volume_km=40.0,
            key_workouts=["轻松跑", "长距离跑"],
            goal="建立有氧基础",
        )
        assert cycle.cycle_type == "base"
        assert cycle.weekly_volume_km == 40.0

    def test_to_dict(self) -> None:
        cycle = TrainingCycle(
            cycle_type="build",
            start_date="2026-05-01",
            end_date="2026-05-28",
            weekly_volume_km=50.0,
            key_workouts=["间歇跑"],
            goal="提升速度",
        )
        d = cycle.to_dict()
        assert d["cycle_type"] == "build"
        assert d["weekly_volume_km"] == 50.0
        assert len(d["key_workouts"]) == 1


class TestLongTermPlan:
    """LongTermPlan 测试"""

    def _make_cycles(self) -> list[TrainingCycle]:
        return [
            TrainingCycle(
                cycle_type="base",
                start_date="2026-05-01",
                end_date="2026-06-01",
                weekly_volume_km=40.0,
                key_workouts=["轻松跑"],
                goal="有氧基础",
            ),
            TrainingCycle(
                cycle_type="build",
                start_date="2026-06-02",
                end_date="2026-07-01",
                weekly_volume_km=50.0,
                key_workouts=["间歇跑"],
                goal="速度提升",
            ),
        ]

    def test_create_valid(self) -> None:
        plan = LongTermPlan(
            plan_name="半马备赛计划",
            target_race="城市半马",
            target_date="2026-10-01",
            current_vdot=42.0,
            target_vdot=48.0,
            total_weeks=16,
            cycles=self._make_cycles(),
            weekly_volume_range_km=(30.0, 60.0),
            key_milestones=["完成30km长距离", "VDOT达到45"],
        )
        assert plan.plan_name == "半马备赛计划"
        assert plan.total_weeks == 16

    def test_has_target_race_true(self) -> None:
        plan = LongTermPlan(
            plan_name="测试计划",
            target_race="城市半马",
            target_date="2026-10-01",
            current_vdot=42.0,
            target_vdot=48.0,
            total_weeks=16,
            cycles=self._make_cycles(),
            weekly_volume_range_km=(30.0, 60.0),
            key_milestones=[],
        )
        assert plan.has_target_race is True

    def test_has_target_race_false_no_race(self) -> None:
        plan = LongTermPlan(
            plan_name="测试计划",
            target_race=None,
            target_date=None,
            current_vdot=42.0,
            target_vdot=48.0,
            total_weeks=16,
            cycles=self._make_cycles(),
            weekly_volume_range_km=(30.0, 60.0),
            key_milestones=[],
        )
        assert plan.has_target_race is False

    def test_has_target_race_false_no_date(self) -> None:
        plan = LongTermPlan(
            plan_name="测试计划",
            target_race="城市半马",
            target_date=None,
            current_vdot=42.0,
            target_vdot=48.0,
            total_weeks=16,
            cycles=self._make_cycles(),
            weekly_volume_range_km=(30.0, 60.0),
            key_milestones=[],
        )
        assert plan.has_target_race is False

    def test_invalid_total_weeks(self) -> None:
        with pytest.raises(ValueError, match="total_weeks"):
            LongTermPlan(
                plan_name="测试计划",
                target_race=None,
                target_date=None,
                current_vdot=42.0,
                target_vdot=48.0,
                total_weeks=2,
                cycles=self._make_cycles(),
                weekly_volume_range_km=(30.0, 60.0),
                key_milestones=[],
            )

    def test_to_dict(self) -> None:
        plan = LongTermPlan(
            plan_name="半马备赛",
            target_race="城市半马",
            target_date="2026-10-01",
            current_vdot=42.0,
            target_vdot=48.0,
            total_weeks=16,
            cycles=self._make_cycles(),
            weekly_volume_range_km=(30.0, 60.0),
            key_milestones=["VDOT达到45"],
        )
        d = plan.to_dict()
        assert d["plan_name"] == "半马备赛"
        assert len(d["cycles"]) == 2
        assert d["weekly_volume_range_km"] == [30.0, 60.0]
        assert d["has_target_race"] is True


class TestSmartTrainingAdvice:
    """SmartTrainingAdvice 测试"""

    def test_create_valid_training(self) -> None:
        advice = SmartTrainingAdvice(
            advice_type="training",
            content="增加间歇训练频率",
            priority="high",
            context="VDOT提升停滞",
            confidence=0.85,
            related_metrics=["vdot", "interval_pace"],
        )
        assert advice.advice_type == "training"
        assert advice.priority == "high"

    def test_create_valid_recovery(self) -> None:
        advice = SmartTrainingAdvice(
            advice_type="recovery",
            content="增加恢复日",
            priority="medium",
            context="疲劳累积",
            confidence=0.7,
            related_metrics=["ctl", "tsb"],
        )
        assert advice.advice_type == "recovery"

    def test_create_valid_nutrition(self) -> None:
        advice = SmartTrainingAdvice(
            advice_type="nutrition",
            content="增加碳水摄入",
            priority="low",
            context="长距离跑后恢复",
            confidence=0.6,
            related_metrics=["weekly_volume"],
        )
        assert advice.advice_type == "nutrition"

    def test_create_valid_injury_prevention(self) -> None:
        advice = SmartTrainingAdvice(
            advice_type="injury_prevention",
            content="增加力量训练",
            priority="high",
            context="髂胫束风险",
            confidence=0.75,
            related_metrics=["injury_risk"],
        )
        assert advice.advice_type == "injury_prevention"

    def test_invalid_advice_type(self) -> None:
        with pytest.raises(ValueError, match="advice_type"):
            SmartTrainingAdvice(
                advice_type="invalid",
                content="测试",
                priority="high",
                context="测试",
                confidence=0.8,
                related_metrics=[],
            )

    def test_invalid_priority(self) -> None:
        with pytest.raises(ValueError, match="priority"):
            SmartTrainingAdvice(
                advice_type="training",
                content="测试",
                priority="urgent",
                context="测试",
                confidence=0.8,
                related_metrics=[],
            )

    def test_invalid_confidence(self) -> None:
        with pytest.raises(ValueError, match="confidence"):
            SmartTrainingAdvice(
                advice_type="training",
                content="测试",
                priority="high",
                context="测试",
                confidence=1.5,
                related_metrics=[],
            )

    def test_to_dict(self) -> None:
        advice = SmartTrainingAdvice(
            advice_type="training",
            content="增加间歇训练",
            priority="high",
            context="VDOT停滞",
            confidence=0.856,
            related_metrics=["vdot"],
        )
        d = advice.to_dict()
        assert d["advice_type"] == "training"
        assert d["confidence"] == 0.86
        assert d["related_metrics"] == ["vdot"]
