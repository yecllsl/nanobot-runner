# v0.11.0 Agent工具单元测试
# 覆盖 AdjustPlanTool / GetPlanAdjustmentSuggestionsTool

import json
from unittest.mock import MagicMock, patch

import pytest

from src.agents.tools import (
    AdjustPlanTool,
    GetPlanAdjustmentSuggestionsTool,
    RunnerTools,
)
from src.core.models import PlanExecutionStats
from src.core.plan.plan_adjustment_validator import PlanAdjustmentValidator
from tests.conftest import create_mock_context


def _create_mock_context_with_v0110() -> tuple:
    """创建带v0.11.0扩展组件的Mock上下文"""
    mock_plan_manager = MagicMock()
    mock_execution_repo = MagicMock()
    mock_validator = PlanAdjustmentValidator()

    context = create_mock_context(plan_manager=mock_plan_manager)
    context.set_extension("plan_execution_repo", mock_execution_repo)
    context.set_extension("plan_adjustment_validator", mock_validator)

    return context, {
        "plan_manager": mock_plan_manager,
        "execution_repo": mock_execution_repo,
        "validator": mock_validator,
    }


class TestAdjustPlanTool:
    """AdjustPlanTool 测试"""

    def test_name(self):
        context, _ = _create_mock_context_with_v0110()
        runner_tools = RunnerTools(context=context)
        tool = AdjustPlanTool(runner_tools)
        assert tool.name == "adjust_plan"

    def test_description(self):
        context, _ = _create_mock_context_with_v0110()
        runner_tools = RunnerTools(context=context)
        tool = AdjustPlanTool(runner_tools)
        assert "调整" in tool.description

    def test_parameters_structure(self):
        context, _ = _create_mock_context_with_v0110()
        runner_tools = RunnerTools(context=context)
        tool = AdjustPlanTool(runner_tools)
        params = tool.parameters
        assert "plan_id" in params["properties"]
        assert "adjustment_request" in params["properties"]
        assert "plan_id" in params["required"]
        assert "adjustment_request" in params["required"]

    def test_validate_params_valid(self):
        context, _ = _create_mock_context_with_v0110()
        runner_tools = RunnerTools(context=context)
        tool = AdjustPlanTool(runner_tools)
        errors = tool.validate_params(
            {
                "plan_id": "plan_test",
                "adjustment_request": "减量",
            }
        )
        assert len(errors) == 0

    def test_validate_params_missing_required(self):
        context, _ = _create_mock_context_with_v0110()
        runner_tools = RunnerTools(context=context)
        tool = AdjustPlanTool(runner_tools)
        errors = tool.validate_params({})
        assert len(errors) > 0
        assert any("plan_id" in e for e in errors)
        assert any("adjustment_request" in e for e in errors)

    def test_to_schema(self):
        context, _ = _create_mock_context_with_v0110()
        runner_tools = RunnerTools(context=context)
        tool = AdjustPlanTool(runner_tools)
        schema = tool.to_schema()
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "adjust_plan"
        assert "parameters" in schema["function"]

    @pytest.mark.anyio
    async def test_execute_reduce_volume(self):
        context, mocks = _create_mock_context_with_v0110()
        with patch("src.core.base.context.get_context", return_value=context):
            runner_tools = RunnerTools(context=context)
            tool = AdjustPlanTool(runner_tools)
            result = await tool.execute(
                plan_id="plan_test",
                adjustment_request="减量",
            )
            result_dict = json.loads(result)
            assert result_dict["success"] is True
            assert "adjustment" in result_dict
            assert result_dict["requires_confirmation"] is True

    @pytest.mark.anyio
    async def test_execute_increase_volume(self):
        context, mocks = _create_mock_context_with_v0110()
        with patch("src.core.base.context.get_context", return_value=context):
            runner_tools = RunnerTools(context=context)
            tool = AdjustPlanTool(runner_tools)
            result = await tool.execute(
                plan_id="plan_test",
                adjustment_request="改变训练类型",
                confirmation_required=False,
            )
            result_dict = json.loads(result)
            assert result_dict["success"] is True
            assert result_dict["requires_confirmation"] is False

    @pytest.mark.anyio
    async def test_execute_exception(self):
        context, mocks = _create_mock_context_with_v0110()
        mocks["validator"] = MagicMock()
        mocks["validator"].get_default_adjustment.side_effect = Exception("校验器异常")
        context.set_extension("plan_adjustment_validator", mocks["validator"])

        with patch("src.core.base.context.get_context", return_value=context):
            runner_tools = RunnerTools(context=context)
            tool = AdjustPlanTool(runner_tools)
            result = await tool.execute(
                plan_id="plan_test",
                adjustment_request="减量",
            )
            result_dict = json.loads(result)
            assert "error" in result_dict


class TestGetPlanAdjustmentSuggestionsTool:
    """GetPlanAdjustmentSuggestionsTool 测试"""

    def test_name(self):
        context, _ = _create_mock_context_with_v0110()
        runner_tools = RunnerTools(context=context)
        tool = GetPlanAdjustmentSuggestionsTool(runner_tools)
        assert tool.name == "get_plan_adjustment_suggestions"

    def test_description(self):
        context, _ = _create_mock_context_with_v0110()
        runner_tools = RunnerTools(context=context)
        tool = GetPlanAdjustmentSuggestionsTool(runner_tools)
        assert "建议" in tool.description

    def test_parameters_structure(self):
        context, _ = _create_mock_context_with_v0110()
        runner_tools = RunnerTools(context=context)
        tool = GetPlanAdjustmentSuggestionsTool(runner_tools)
        params = tool.parameters
        assert "plan_id" in params["properties"]
        assert "plan_id" in params["required"]

    def test_validate_params_valid(self):
        context, _ = _create_mock_context_with_v0110()
        runner_tools = RunnerTools(context=context)
        tool = GetPlanAdjustmentSuggestionsTool(runner_tools)
        errors = tool.validate_params({"plan_id": "plan_test"})
        assert len(errors) == 0

    def test_validate_params_missing_required(self):
        context, _ = _create_mock_context_with_v0110()
        runner_tools = RunnerTools(context=context)
        tool = GetPlanAdjustmentSuggestionsTool(runner_tools)
        errors = tool.validate_params({})
        assert len(errors) > 0
        assert any("plan_id" in e for e in errors)

    @pytest.mark.anyio
    async def test_execute_with_low_completion(self):
        context, mocks = _create_mock_context_with_v0110()
        mock_stats = PlanExecutionStats(
            plan_id="plan_test",
            total_planned_days=28,
            completed_days=10,
            completion_rate=0.36,
            avg_effort_score=5.0,
            total_distance_km=80.0,
            total_duration_min=500,
            avg_hr=140,
            avg_hr_drift=2.0,
        )
        mocks["execution_repo"].get_plan_execution_stats.return_value = mock_stats

        with patch("src.core.base.context.get_context", return_value=context):
            runner_tools = RunnerTools(context=context)
            tool = GetPlanAdjustmentSuggestionsTool(runner_tools)
            result = await tool.execute(plan_id="plan_test")
            result_dict = json.loads(result)
            assert result_dict["success"] is True
            assert len(result_dict["suggestions"]) > 0
            assert any(
                "完成率" in s["suggestion_content"] for s in result_dict["suggestions"]
            )

    @pytest.mark.anyio
    async def test_execute_with_high_effort(self):
        context, mocks = _create_mock_context_with_v0110()
        mock_stats = PlanExecutionStats(
            plan_id="plan_test",
            total_planned_days=28,
            completed_days=25,
            completion_rate=0.89,
            avg_effort_score=8.5,
            total_distance_km=200.0,
            total_duration_min=1200,
            avg_hr=160,
            avg_hr_drift=2.0,
        )
        mocks["execution_repo"].get_plan_execution_stats.return_value = mock_stats

        with patch("src.core.base.context.get_context", return_value=context):
            runner_tools = RunnerTools(context=context)
            tool = GetPlanAdjustmentSuggestionsTool(runner_tools)
            result = await tool.execute(plan_id="plan_test")
            result_dict = json.loads(result)
            assert result_dict["success"] is True
            assert any(
                "体感" in s["suggestion_content"] for s in result_dict["suggestions"]
            )

    @pytest.mark.anyio
    async def test_execute_with_good_status(self):
        context, mocks = _create_mock_context_with_v0110()
        mock_stats = PlanExecutionStats(
            plan_id="plan_test",
            total_planned_days=28,
            completed_days=25,
            completion_rate=0.89,
            avg_effort_score=5.0,
            total_distance_km=200.0,
            total_duration_min=1200,
            avg_hr=140,
            avg_hr_drift=2.0,
        )
        mocks["execution_repo"].get_plan_execution_stats.return_value = mock_stats

        with patch("src.core.base.context.get_context", return_value=context):
            runner_tools = RunnerTools(context=context)
            tool = GetPlanAdjustmentSuggestionsTool(runner_tools)
            result = await tool.execute(plan_id="plan_test")
            result_dict = json.loads(result)
            assert result_dict["success"] is True
            assert any(
                "良好" in s["suggestion_content"] for s in result_dict["suggestions"]
            )

    @pytest.mark.anyio
    async def test_execute_exception(self):
        context, mocks = _create_mock_context_with_v0110()
        mocks["execution_repo"].get_plan_execution_stats.side_effect = Exception(
            "计划不存在"
        )

        with patch("src.core.base.context.get_context", return_value=context):
            runner_tools = RunnerTools(context=context)
            tool = GetPlanAdjustmentSuggestionsTool(runner_tools)
            result = await tool.execute(plan_id="plan_unknown")
            result_dict = json.loads(result)
            assert "error" in result_dict


class TestRunnerToolsPlanAdjustment:
    """RunnerTools v0.11.0 方法测试"""

    def test_adjust_plan_success(self):
        context, mocks = _create_mock_context_with_v0110()
        with patch("src.core.base.context.get_context", return_value=context):
            runner_tools = RunnerTools(context=context)
            result = runner_tools.adjust_plan(
                plan_id="plan_test",
                adjustment_request="减量",
            )
            assert result["success"] is True
            assert "adjustment" in result

    def test_adjust_plan_error(self):
        context, mocks = _create_mock_context_with_v0110()
        mocks["validator"] = MagicMock()
        mocks["validator"].get_default_adjustment.side_effect = Exception("异常")
        context.set_extension("plan_adjustment_validator", mocks["validator"])

        with patch("src.core.base.context.get_context", return_value=context):
            runner_tools = RunnerTools(context=context)
            result = runner_tools.adjust_plan(
                plan_id="plan_test",
                adjustment_request="减量",
            )
            assert "error" in result

    def test_get_plan_adjustment_suggestions_success(self):
        context, mocks = _create_mock_context_with_v0110()
        mock_stats = PlanExecutionStats(
            plan_id="plan_test",
            total_planned_days=28,
            completed_days=20,
            completion_rate=0.71,
            avg_effort_score=5.5,
            total_distance_km=150.0,
            total_duration_min=900,
            avg_hr=145,
            avg_hr_drift=2.5,
        )
        mocks["execution_repo"].get_plan_execution_stats.return_value = mock_stats

        with patch("src.core.base.context.get_context", return_value=context):
            runner_tools = RunnerTools(context=context)
            result = runner_tools.get_plan_adjustment_suggestions(plan_id="plan_test")
            assert result["success"] is True
            assert "suggestions" in result

    def test_get_plan_adjustment_suggestions_error(self):
        context, mocks = _create_mock_context_with_v0110()
        mocks["execution_repo"].get_plan_execution_stats.side_effect = Exception("异常")

        with patch("src.core.base.context.get_context", return_value=context):
            runner_tools = RunnerTools(context=context)
            result = runner_tools.get_plan_adjustment_suggestions(plan_id="plan_test")
            assert "error" in result


class TestToolDescriptionsV0110:
    """v0.11.0 TOOL_DESCRIPTIONS 测试"""

    def test_adjust_plan_description_exists(self):
        from src.agents.tools import TOOL_DESCRIPTIONS

        assert "adjust_plan" in TOOL_DESCRIPTIONS
        desc = TOOL_DESCRIPTIONS["adjust_plan"]
        assert "description" in desc
        assert "parameters" in desc
        assert "plan_id" in desc["parameters"]
        assert "adjustment_request" in desc["parameters"]

    def test_get_plan_adjustment_suggestions_description_exists(self):
        from src.agents.tools import TOOL_DESCRIPTIONS

        assert "get_plan_adjustment_suggestions" in TOOL_DESCRIPTIONS
        desc = TOOL_DESCRIPTIONS["get_plan_adjustment_suggestions"]
        assert "description" in desc
        assert "parameters" in desc
        assert "plan_id" in desc["parameters"]
