# v0.12.0 Agent工具单元测试
# 覆盖 EvaluateGoalAchievementTool / CreateLongTermPlanTool / GetSmartTrainingAdviceTool

from unittest.mock import MagicMock, patch

import pytest

from src.agents.tools import (
    CreateLongTermPlanTool,
    EvaluateGoalAchievementTool,
    GetSmartTrainingAdviceTool,
    RunnerTools,
)
from tests.conftest import create_mock_context


def _create_mock_context_with_v0120() -> tuple:
    context = create_mock_context()
    mocks: dict[str, MagicMock] = {}

    goal_engine = MagicMock()
    goal_engine.evaluate_goal.return_value = MagicMock(
        to_dict=lambda: {
            "goal_type": "vdot",
            "goal_value": 50.0,
            "current_value": 45.0,
            "achievement_probability": 0.72,
            "key_risks": ["目标VDOT差距较大"],
            "improvement_suggestions": ["增加间歇训练"],
            "estimated_weeks_to_achieve": 12,
            "confidence": 0.8,
        }
    )
    mocks["goal_engine"] = goal_engine

    plan_generator = MagicMock()
    plan_generator.generate_plan.return_value = MagicMock(
        to_dict=lambda: {
            "plan_name": "半马备赛",
            "target_race": None,
            "target_date": None,
            "current_vdot": 42.0,
            "target_vdot": 48.0,
            "total_weeks": 16,
            "cycles": [],
            "weekly_volume_range_km": [30.0, 55.0],
            "key_milestones": ["完成基础期"],
        }
    )
    mocks["plan_generator"] = plan_generator

    advice_engine = MagicMock()
    advice_engine.generate_advice.return_value = [
        MagicMock(
            to_dict=lambda: {
                "advice_type": "training",
                "content": "增加间歇训练",
                "priority": "high",
                "context": "VDOT提升停滞",
                "confidence": 0.85,
                "related_metrics": ["vdot"],
            }
        )
    ]
    mocks["advice_engine"] = advice_engine

    return context, mocks


class TestEvaluateGoalAchievementTool:
    """EvaluateGoalAchievementTool 测试"""

    def test_name(self) -> None:
        with patch("src.core.storage.StorageManager"):
            context = create_mock_context()
            runner_tools = RunnerTools(context=context)
            tool = EvaluateGoalAchievementTool(runner_tools)
            assert tool.name == "evaluate_goal_achievement"

    def test_description(self) -> None:
        with patch("src.core.storage.StorageManager"):
            context = create_mock_context()
            runner_tools = RunnerTools(context=context)
            tool = EvaluateGoalAchievementTool(runner_tools)
            assert "目标达成概率" in tool.description

    def test_parameters(self) -> None:
        with patch("src.core.storage.StorageManager"):
            context = create_mock_context()
            runner_tools = RunnerTools(context=context)
            tool = EvaluateGoalAchievementTool(runner_tools)
            params = tool.parameters
            assert "goal_type" in params["properties"]
            assert "goal_value" in params["properties"]
            assert "current_vdot" in params["properties"]

    @pytest.mark.asyncio
    async def test_execute_success(self) -> None:
        context, mocks = _create_mock_context_with_v0120()
        runner_tools = RunnerTools(context=context)

        with patch(
            "src.core.plan.goal_prediction_engine.GoalPredictionEngine",
            return_value=mocks["goal_engine"],
        ):
            tool = EvaluateGoalAchievementTool(runner_tools)
            result = await tool.execute(
                goal_type="vdot",
                goal_value=50.0,
                current_vdot=45.0,
            )
            assert '"success": true' in result.lower() or "success" in result

    @pytest.mark.asyncio
    async def test_execute_with_weeks(self) -> None:
        context, mocks = _create_mock_context_with_v0120()
        runner_tools = RunnerTools(context=context)

        with patch(
            "src.core.plan.goal_prediction_engine.GoalPredictionEngine",
            return_value=mocks["goal_engine"],
        ):
            tool = EvaluateGoalAchievementTool(runner_tools)
            result = await tool.execute(
                goal_type="vdot",
                goal_value=50.0,
                current_vdot=45.0,
                weeks_available=16,
            )
            assert "success" in result


class TestCreateLongTermPlanTool:
    """CreateLongTermPlanTool 测试"""

    def test_name(self) -> None:
        with patch("src.core.storage.StorageManager"):
            context = create_mock_context()
            runner_tools = RunnerTools(context=context)
            tool = CreateLongTermPlanTool(runner_tools)
            assert tool.name == "create_long_term_plan"

    def test_description(self) -> None:
        with patch("src.core.storage.StorageManager"):
            context = create_mock_context()
            runner_tools = RunnerTools(context=context)
            tool = CreateLongTermPlanTool(runner_tools)
            assert "长期训练规划" in tool.description

    def test_parameters(self) -> None:
        with patch("src.core.storage.StorageManager"):
            context = create_mock_context()
            runner_tools = RunnerTools(context=context)
            tool = CreateLongTermPlanTool(runner_tools)
            params = tool.parameters
            assert "plan_name" in params["properties"]
            assert "current_vdot" in params["properties"]
            assert "target_vdot" in params["properties"]

    @pytest.mark.asyncio
    async def test_execute_success(self) -> None:
        context, mocks = _create_mock_context_with_v0120()
        runner_tools = RunnerTools(context=context)

        with patch(
            "src.core.plan.long_term_plan_generator.LongTermPlanGenerator",
            return_value=mocks["plan_generator"],
        ):
            tool = CreateLongTermPlanTool(runner_tools)
            result = await tool.execute(
                plan_name="半马备赛",
                current_vdot=42.0,
                target_vdot=48.0,
                total_weeks=16,
            )
            assert "success" in result

    @pytest.mark.asyncio
    async def test_execute_with_race(self) -> None:
        context, mocks = _create_mock_context_with_v0120()
        runner_tools = RunnerTools(context=context)

        with patch(
            "src.core.plan.long_term_plan_generator.LongTermPlanGenerator",
            return_value=mocks["plan_generator"],
        ):
            tool = CreateLongTermPlanTool(runner_tools)
            result = await tool.execute(
                plan_name="全马备赛",
                current_vdot=45.0,
                target_vdot=50.0,
                target_race="北京马拉松",
                target_date="2026-10-15",
            )
            assert "success" in result


class TestGetSmartTrainingAdviceTool:
    """GetSmartTrainingAdviceTool 测试"""

    def test_name(self) -> None:
        with patch("src.core.storage.StorageManager"):
            context = create_mock_context()
            runner_tools = RunnerTools(context=context)
            tool = GetSmartTrainingAdviceTool(runner_tools)
            assert tool.name == "get_smart_training_advice"

    def test_description(self) -> None:
        with patch("src.core.storage.StorageManager"):
            context = create_mock_context()
            runner_tools = RunnerTools(context=context)
            tool = GetSmartTrainingAdviceTool(runner_tools)
            assert "智能训练建议" in tool.description

    def test_parameters(self) -> None:
        with patch("src.core.storage.StorageManager"):
            context = create_mock_context()
            runner_tools = RunnerTools(context=context)
            tool = GetSmartTrainingAdviceTool(runner_tools)
            params = tool.parameters
            assert "current_vdot" in params["properties"]
            assert "weekly_volume_km" in params["properties"]

    @pytest.mark.asyncio
    async def test_execute_success(self) -> None:
        context, mocks = _create_mock_context_with_v0120()
        runner_tools = RunnerTools(context=context)

        with patch(
            "src.core.plan.smart_advice_engine.SmartAdviceEngine",
            return_value=mocks["advice_engine"],
        ):
            tool = GetSmartTrainingAdviceTool(runner_tools)
            result = await tool.execute(
                current_vdot=42.0,
                weekly_volume_km=35.0,
            )
            assert "success" in result

    @pytest.mark.asyncio
    async def test_execute_with_injury_risk(self) -> None:
        context, mocks = _create_mock_context_with_v0120()
        runner_tools = RunnerTools(context=context)

        with patch(
            "src.core.plan.smart_advice_engine.SmartAdviceEngine",
            return_value=mocks["advice_engine"],
        ):
            tool = GetSmartTrainingAdviceTool(runner_tools)
            result = await tool.execute(
                injury_risk="high",
                weekly_volume_km=50.0,
            )
            assert "success" in result


class TestRunnerToolsV0120:
    """RunnerTools v0.12.0方法测试"""

    def test_evaluate_goal_achievement(self) -> None:
        context, mocks = _create_mock_context_with_v0120()
        runner_tools = RunnerTools(context=context)

        with patch(
            "src.core.plan.goal_prediction_engine.GoalPredictionEngine",
            return_value=mocks["goal_engine"],
        ):
            result = runner_tools.evaluate_goal_achievement(
                goal_type="vdot",
                goal_value=50.0,
                current_vdot=45.0,
            )
            assert result["success"] is True
            assert "data" in result

    def test_create_long_term_plan(self) -> None:
        context, mocks = _create_mock_context_with_v0120()
        runner_tools = RunnerTools(context=context)

        with patch(
            "src.core.plan.long_term_plan_generator.LongTermPlanGenerator",
            return_value=mocks["plan_generator"],
        ):
            result = runner_tools.create_long_term_plan(
                plan_name="半马备赛",
                current_vdot=42.0,
                target_vdot=48.0,
            )
            assert result["success"] is True
            assert "data" in result

    def test_get_smart_training_advice(self) -> None:
        context, mocks = _create_mock_context_with_v0120()
        runner_tools = RunnerTools(context=context)

        with patch(
            "src.core.plan.smart_advice_engine.SmartAdviceEngine",
            return_value=mocks["advice_engine"],
        ):
            result = runner_tools.get_smart_training_advice(
                current_vdot=42.0,
                weekly_volume_km=35.0,
            )
            assert result["success"] is True
            assert "data" in result

    def test_evaluate_goal_achievement_error(self) -> None:
        context, mocks = _create_mock_context_with_v0120()
        runner_tools = RunnerTools(context=context)

        with patch(
            "src.core.plan.goal_prediction_engine.GoalPredictionEngine",
            side_effect=Exception("预测引擎错误"),
        ):
            result = runner_tools.evaluate_goal_achievement(
                goal_type="vdot",
                goal_value=50.0,
                current_vdot=45.0,
            )
            assert result["success"] is False

    def test_create_long_term_plan_error(self) -> None:
        context, mocks = _create_mock_context_with_v0120()
        runner_tools = RunnerTools(context=context)

        with patch(
            "src.core.plan.long_term_plan_generator.LongTermPlanGenerator",
            side_effect=Exception("规划引擎错误"),
        ):
            result = runner_tools.create_long_term_plan(
                plan_name="测试",
                current_vdot=42.0,
            )
            assert result["success"] is False

    def test_get_smart_training_advice_error(self) -> None:
        context, mocks = _create_mock_context_with_v0120()
        runner_tools = RunnerTools(context=context)

        with patch(
            "src.core.plan.smart_advice_engine.SmartAdviceEngine",
            side_effect=Exception("建议引擎错误"),
        ):
            result = runner_tools.get_smart_training_advice(
                current_vdot=42.0,
            )
            assert result["success"] is False
