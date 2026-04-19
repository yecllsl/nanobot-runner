# v0.12.0 模块内集成测试
# 验证预测引擎、规划引擎、建议引擎的联动逻辑

from unittest.mock import MagicMock, patch

from src.core.models import (
    GoalAchievementEvaluation,
    LongTermPlan,
    SmartTrainingAdvice,
)
from src.core.plan.goal_prediction_engine import GoalPredictionEngine
from src.core.plan.long_term_plan_generator import LongTermPlanGenerator
from src.core.plan.smart_advice_engine import SmartAdviceEngine
from tests.conftest import create_mock_context


class TestGoalPredictionToPlanIntegration:
    """目标预测→长期规划 集成测试"""

    def test_evaluate_then_plan(self) -> None:
        prediction_engine = GoalPredictionEngine()
        plan_generator = LongTermPlanGenerator()

        evaluation = prediction_engine.evaluate_goal(
            goal_type="vdot",
            goal_value=50.0,
            current_vdot=42.0,
            weeks_available=16,
        )

        assert isinstance(evaluation, GoalAchievementEvaluation)
        assert evaluation.achievement_probability > 0

        plan = plan_generator.generate_plan(
            plan_name="VDOT50冲刺计划",
            current_vdot=42.0,
            target_vdot=50.0,
            total_weeks=16,
        )

        assert isinstance(plan, LongTermPlan)
        assert plan.current_vdot == 42.0
        assert plan.target_vdot == 50.0
        assert len(plan.cycles) > 0

    def test_evaluate_unrealistic_goal(self) -> None:
        engine = GoalPredictionEngine()
        evaluation = engine.evaluate_goal(
            goal_type="vdot",
            goal_value=80.0,
            current_vdot=40.0,
            weeks_available=8,
        )

        assert evaluation.achievement_probability < 0.5
        assert len(evaluation.key_risks) > 0


class TestPlanToAdviceIntegration:
    """长期规划→智能建议 集成测试"""

    def test_plan_then_advice(self) -> None:
        plan_generator = LongTermPlanGenerator()
        advice_engine = SmartAdviceEngine()

        plan = plan_generator.generate_plan(
            plan_name="半马备赛",
            current_vdot=42.0,
            target_vdot=48.0,
            total_weeks=16,
        )

        advices = advice_engine.generate_advice(
            current_vdot=42.0,
            weekly_volume_km=plan.weekly_volume_range_km[0],
            goal_type="half_marathon",
        )

        assert len(advices) > 0
        assert all(isinstance(a, SmartTrainingAdvice) for a in advices)

    def test_high_injury_risk_advice(self) -> None:
        advice_engine = SmartAdviceEngine()
        advices = advice_engine.generate_advice(
            weekly_volume_km=60.0,
            injury_risk="high",
            training_consistency=0.5,
        )

        injury_advices = [a for a in advices if a.advice_type == "injury_prevention"]
        assert len(injury_advices) > 0


class TestFullPipelineIntegration:
    """完整流水线集成测试：评估→规划→建议"""

    def test_full_pipeline(self) -> None:
        prediction_engine = GoalPredictionEngine()
        plan_generator = LongTermPlanGenerator()
        advice_engine = SmartAdviceEngine()

        evaluation = prediction_engine.evaluate_goal(
            goal_type="vdot",
            goal_value=48.0,
            current_vdot=42.0,
            weeks_available=16,
        )

        plan = plan_generator.generate_plan(
            plan_name="VDOT48提升计划",
            current_vdot=42.0,
            target_vdot=48.0,
            total_weeks=16,
        )

        advices = advice_engine.generate_advice(
            current_vdot=42.0,
            weekly_volume_km=plan.weekly_volume_range_km[0],
            training_consistency=0.8,
            goal_type="half_marathon",
        )

        assert evaluation.achievement_probability > 0
        assert len(plan.cycles) == 4
        assert len(advices) > 0

        advice_types = {a.advice_type for a in advices}
        assert "training" in advice_types

    def test_pipeline_with_race_target(self) -> None:
        prediction_engine = GoalPredictionEngine()
        plan_generator = LongTermPlanGenerator()

        evaluation = prediction_engine.evaluate_goal(
            goal_type="half_marathon",
            goal_value=6300.0,
            current_vdot=42.0,
            weeks_available=20,
        )

        plan = plan_generator.generate_plan(
            plan_name="北京马拉松备赛",
            current_vdot=42.0,
            target_vdot=48.0,
            target_race="北京马拉松",
            target_date="2026-10-15",
            total_weeks=20,
        )

        assert plan.has_target_race is True
        assert plan.target_race == "北京马拉松"
        assert len(plan.cycles) > 0


class TestContextIntegration:
    """依赖注入集成测试"""

    def test_context_provides_v0120_engines(self) -> None:
        context = create_mock_context()

        with (
            patch(
                "src.core.plan.goal_prediction_engine.GoalPredictionEngine"
            ) as mock_goal,
            patch(
                "src.core.plan.long_term_plan_generator.LongTermPlanGenerator"
            ) as mock_plan,
            patch("src.core.plan.smart_advice_engine.SmartAdviceEngine") as mock_advice,
        ):
            mock_goal.return_value = GoalPredictionEngine()
            mock_plan.return_value = LongTermPlanGenerator()
            mock_advice.return_value = SmartAdviceEngine()

            goal_engine = context.goal_prediction_engine
            plan_gen = context.long_term_plan_generator
            advice_engine = context.smart_advice_engine

            assert isinstance(goal_engine, GoalPredictionEngine)
            assert isinstance(plan_gen, LongTermPlanGenerator)
            assert isinstance(advice_engine, SmartAdviceEngine)

    def test_runner_tools_v0120_integration(self) -> None:
        from src.agents.tools import RunnerTools

        context = create_mock_context()
        runner_tools = RunnerTools(context=context)

        with patch(
            "src.core.plan.goal_prediction_engine.GoalPredictionEngine"
        ) as mock_goal:
            mock_instance = MagicMock()
            mock_instance.evaluate_goal.return_value = MagicMock(
                to_dict=lambda: {
                    "goal_type": "vdot",
                    "goal_value": 50.0,
                    "current_value": 42.0,
                    "achievement_probability": 0.65,
                    "key_risks": [],
                    "improvement_suggestions": [],
                    "estimated_weeks_to_achieve": 14,
                    "confidence": 0.8,
                }
            )
            mock_goal.return_value = mock_instance

            result = runner_tools.evaluate_goal_achievement(
                goal_type="vdot",
                goal_value=50.0,
                current_vdot=42.0,
            )
            assert result["success"] is True
