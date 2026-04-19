# v0.10.0 Agent工具单元测试
# 覆盖 RecordPlanExecutionTool / GetPlanExecutionStatsTool / AnalyzeTrainingResponseTool

import json
from unittest.mock import MagicMock, patch

import pytest

from src.agents.tools import (
    AnalyzeTrainingResponseTool,
    GetPlanExecutionStatsTool,
    RecordPlanExecutionTool,
    RunnerTools,
)
from src.core.models import (
    PlanExecutionStats,
)
from tests.conftest import create_mock_context


def _create_mock_context_with_extensions() -> tuple:
    """创建带扩展组件的Mock上下文"""
    mock_plan_manager = MagicMock()
    mock_execution_repo = MagicMock()
    mock_analyzer = MagicMock()

    context = create_mock_context(plan_manager=mock_plan_manager)
    context.set_extension("plan_execution_repo", mock_execution_repo)
    context.set_extension("training_response_analyzer", mock_analyzer)

    return context, {
        "plan_manager": mock_plan_manager,
        "execution_repo": mock_execution_repo,
        "analyzer": mock_analyzer,
    }


class TestRecordPlanExecutionTool:
    """RecordPlanExecutionTool 单元测试"""

    def test_name(self):
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = RecordPlanExecutionTool(runner_tools)
            assert tool.name == "record_plan_execution"

    def test_description(self):
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = RecordPlanExecutionTool(runner_tools)
            assert "记录" in tool.description
            assert "训练计划执行反馈" in tool.description

    def test_parameters_structure(self):
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = RecordPlanExecutionTool(runner_tools)
            params = tool.parameters

            assert params["type"] == "object"
            assert "plan_id" in params["properties"]
            assert "date" in params["properties"]
            assert "plan_id" in params["required"]
            assert "date" in params["required"]

    def test_parameters_optional_fields(self):
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = RecordPlanExecutionTool(runner_tools)
            params = tool.parameters

            assert "completion_rate" in params["properties"]
            assert "effort_score" in params["properties"]
            assert "notes" in params["properties"]
            assert "actual_distance_km" in params["properties"]
            assert "actual_duration_min" in params["properties"]
            assert "actual_avg_hr" in params["properties"]

            required = params.get("required", [])
            assert "completion_rate" not in required
            assert "effort_score" not in required

    @pytest.mark.anyio
    async def test_execute_success(self):
        context, mocks = _create_mock_context_with_extensions()
        mocks["plan_manager"].record_execution.return_value = {
            "success": True,
            "message": "已记录2026-04-20的执行反馈",
            "plan_id": "plan_test",
            "date": "2026-04-20",
        }

        with patch("src.core.context.get_context", return_value=context):
            runner_tools = RunnerTools(context=context)
            tool = RecordPlanExecutionTool(runner_tools)
            result = await tool.execute(
                plan_id="plan_test",
                date="2026-04-20",
                completion_rate=0.8,
                effort_score=6,
            )

            result_dict = json.loads(result)
            assert "plan_test" in str(result_dict)

    @pytest.mark.anyio
    async def test_execute_plan_not_found(self):
        context, mocks = _create_mock_context_with_extensions()
        mocks["plan_manager"].record_execution.side_effect = Exception(
            "计划不存在：plan_unknown"
        )

        with patch("src.core.context.get_context", return_value=context):
            runner_tools = RunnerTools(context=context)
            tool = RecordPlanExecutionTool(runner_tools)
            result = await tool.execute(
                plan_id="plan_unknown",
                date="2026-04-20",
            )

            result_dict = json.loads(result)
            assert "error" in result_dict

    @pytest.mark.anyio
    async def test_execute_invalid_completion_rate(self):
        context, mocks = _create_mock_context_with_extensions()
        mocks["plan_manager"].record_execution.side_effect = Exception(
            "完成度必须在0.0-1.0之间"
        )

        with patch("src.core.context.get_context", return_value=context):
            runner_tools = RunnerTools(context=context)
            tool = RecordPlanExecutionTool(runner_tools)
            result = await tool.execute(
                plan_id="plan_test",
                date="2026-04-20",
                completion_rate=1.5,
            )

            result_dict = json.loads(result)
            assert "error" in result_dict

    @pytest.mark.anyio
    async def test_execute_invalid_effort_score(self):
        context, mocks = _create_mock_context_with_extensions()
        mocks["plan_manager"].record_execution.side_effect = Exception(
            "体感评分必须在1-10之间"
        )

        with patch("src.core.context.get_context", return_value=context):
            runner_tools = RunnerTools(context=context)
            tool = RecordPlanExecutionTool(runner_tools)
            result = await tool.execute(
                plan_id="plan_test",
                date="2026-04-20",
                effort_score=15,
            )

            result_dict = json.loads(result)
            assert "error" in result_dict

    def test_to_schema(self):
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = RecordPlanExecutionTool(runner_tools)
            schema = tool.to_schema()

            assert schema["type"] == "function"
            assert schema["function"]["name"] == "record_plan_execution"
            assert "description" in schema["function"]
            assert "parameters" in schema["function"]

    def test_validate_params_missing_required(self):
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = RecordPlanExecutionTool(runner_tools)

            errors = tool.validate_params({})
            assert len(errors) > 0
            assert any("plan_id" in e for e in errors)
            assert any("date" in e for e in errors)

    def test_validate_params_valid(self):
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = RecordPlanExecutionTool(runner_tools)

            errors = tool.validate_params(
                {
                    "plan_id": "plan_test",
                    "date": "2026-04-20",
                }
            )
            assert len(errors) == 0


class TestGetPlanExecutionStatsTool:
    """GetPlanExecutionStatsTool 单元测试"""

    def test_name(self):
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = GetPlanExecutionStatsTool(runner_tools)
            assert tool.name == "get_plan_execution_stats"

    def test_description(self):
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = GetPlanExecutionStatsTool(runner_tools)
            assert "执行统计" in tool.description

    def test_parameters_structure(self):
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = GetPlanExecutionStatsTool(runner_tools)
            params = tool.parameters

            assert params["type"] == "object"
            assert "plan_id" in params["properties"]
            assert "plan_id" in params["required"]

    @pytest.mark.anyio
    async def test_execute_success(self):
        context, mocks = _create_mock_context_with_extensions()
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

        with patch("src.core.context.get_context", return_value=context):
            runner_tools = RunnerTools(context=context)
            tool = GetPlanExecutionStatsTool(runner_tools)
            result = await tool.execute(plan_id="plan_test")

            result_dict = json.loads(result)
            assert result_dict["plan_id"] == "plan_test"
            assert result_dict["total_planned_days"] == 28
            assert result_dict["completed_days"] == 20

    @pytest.mark.anyio
    async def test_execute_plan_not_found(self):
        context, mocks = _create_mock_context_with_extensions()
        mocks["execution_repo"].get_plan_execution_stats.side_effect = Exception(
            "计划不存在：plan_unknown"
        )

        with patch("src.core.context.get_context", return_value=context):
            runner_tools = RunnerTools(context=context)
            tool = GetPlanExecutionStatsTool(runner_tools)
            result = await tool.execute(plan_id="plan_unknown")

            result_dict = json.loads(result)
            assert "error" in result_dict

    @pytest.mark.anyio
    async def test_execute_empty_plan(self):
        context, mocks = _create_mock_context_with_extensions()
        mock_stats = PlanExecutionStats(
            plan_id="plan_empty",
            total_planned_days=0,
            completed_days=0,
            completion_rate=0.0,
            avg_effort_score=0.0,
            total_distance_km=0.0,
            total_duration_min=0,
            avg_hr=None,
            avg_hr_drift=None,
        )
        mocks["execution_repo"].get_plan_execution_stats.return_value = mock_stats

        with patch("src.core.context.get_context", return_value=context):
            runner_tools = RunnerTools(context=context)
            tool = GetPlanExecutionStatsTool(runner_tools)
            result = await tool.execute(plan_id="plan_empty")

            result_dict = json.loads(result)
            assert result_dict["plan_id"] == "plan_empty"
            assert result_dict["total_planned_days"] == 0

    def test_to_schema(self):
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = GetPlanExecutionStatsTool(runner_tools)
            schema = tool.to_schema()

            assert schema["type"] == "function"
            assert schema["function"]["name"] == "get_plan_execution_stats"

    def test_validate_params_missing_required(self):
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = GetPlanExecutionStatsTool(runner_tools)

            errors = tool.validate_params({})
            assert len(errors) > 0
            assert any("plan_id" in e for e in errors)

    def test_validate_params_valid(self):
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = GetPlanExecutionStatsTool(runner_tools)

            errors = tool.validate_params({"plan_id": "plan_test"})
            assert len(errors) == 0


class TestAnalyzeTrainingResponseTool:
    """AnalyzeTrainingResponseTool 单元测试"""

    def test_name(self):
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = AnalyzeTrainingResponseTool(runner_tools)
            assert tool.name == "analyze_training_response"

    def test_description(self):
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = AnalyzeTrainingResponseTool(runner_tools)
            assert "训练响应" in tool.description or "适应" in tool.description

    def test_parameters_structure(self):
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = AnalyzeTrainingResponseTool(runner_tools)
            params = tool.parameters

            assert params["type"] == "object"
            assert "plan_id" in params["properties"]
            assert "plan_id" in params["required"]

    @pytest.mark.anyio
    async def test_execute_success(self):
        context, mocks = _create_mock_context_with_extensions()
        mocks["analyzer"].analyze_plan_response.return_value = {
            "success": True,
            "data": {
                "plan_id": "plan_test",
                "stats": {
                    "plan_id": "plan_test",
                    "total_planned_days": 28,
                    "completed_days": 20,
                    "completion_rate": 0.71,
                },
                "patterns": [],
                "overall_assessment": "训练完成率良好",
                "weak_types": [],
                "strong_types": [],
            },
            "message": "训练响应分析完成",
        }

        with patch("src.core.context.get_context", return_value=context):
            runner_tools = RunnerTools(context=context)
            tool = AnalyzeTrainingResponseTool(runner_tools)
            result = await tool.execute(plan_id="plan_test")

            result_dict = json.loads(result)
            assert "plan_test" in str(result_dict)

    @pytest.mark.anyio
    async def test_execute_plan_not_found(self):
        context, mocks = _create_mock_context_with_extensions()
        mocks["analyzer"].analyze_plan_response.return_value = {
            "success": False,
            "error": "计划不存在：plan_unknown",
            "message": "训练响应分析失败：计划不存在：plan_unknown",
        }

        with patch("src.core.context.get_context", return_value=context):
            runner_tools = RunnerTools(context=context)
            tool = AnalyzeTrainingResponseTool(runner_tools)
            result = await tool.execute(plan_id="plan_unknown")

            result_dict = json.loads(result)
            assert "error" in result_dict

    @pytest.mark.anyio
    async def test_execute_exception(self):
        context, mocks = _create_mock_context_with_extensions()
        mocks["analyzer"].analyze_plan_response.side_effect = Exception("分析失败")

        with patch("src.core.context.get_context", return_value=context):
            runner_tools = RunnerTools(context=context)
            tool = AnalyzeTrainingResponseTool(runner_tools)
            result = await tool.execute(plan_id="plan_test")

            result_dict = json.loads(result)
            assert "error" in result_dict

    def test_to_schema(self):
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = AnalyzeTrainingResponseTool(runner_tools)
            schema = tool.to_schema()

            assert schema["type"] == "function"
            assert schema["function"]["name"] == "analyze_training_response"

    def test_validate_params_missing_required(self):
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = AnalyzeTrainingResponseTool(runner_tools)

            errors = tool.validate_params({})
            assert len(errors) > 0
            assert any("plan_id" in e for e in errors)

    def test_validate_params_valid(self):
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = AnalyzeTrainingResponseTool(runner_tools)

            errors = tool.validate_params({"plan_id": "plan_test"})
            assert len(errors) == 0


class TestRunnerToolsPlanExecution:
    """RunnerTools 计划执行相关方法测试"""

    def test_record_plan_execution_success(self):
        context, mocks = _create_mock_context_with_extensions()
        mocks["plan_manager"].record_execution.return_value = {
            "success": True,
            "message": "已记录2026-04-20的执行反馈",
            "plan_id": "plan_test",
            "date": "2026-04-20",
        }

        with patch("src.core.context.get_context", return_value=context):
            runner_tools = RunnerTools(context=context)
            result = runner_tools.record_plan_execution(
                plan_id="plan_test",
                date="2026-04-20",
                completion_rate=0.8,
                effort_score=6,
            )

            assert "plan_test" in str(result)

    def test_record_plan_execution_error(self):
        context, mocks = _create_mock_context_with_extensions()
        mocks["plan_manager"].record_execution.side_effect = Exception("计划不存在")

        with patch("src.core.context.get_context", return_value=context):
            runner_tools = RunnerTools(context=context)
            result = runner_tools.record_plan_execution(
                plan_id="plan_unknown",
                date="2026-04-20",
            )

            assert "error" in result

    def test_get_plan_execution_stats_success(self):
        context, mocks = _create_mock_context_with_extensions()
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

        with patch("src.core.context.get_context", return_value=context):
            runner_tools = RunnerTools(context=context)
            result = runner_tools.get_plan_execution_stats(plan_id="plan_test")

            assert result["plan_id"] == "plan_test"
            assert result["completion_rate"] == 0.71

    def test_get_plan_execution_stats_error(self):
        context, mocks = _create_mock_context_with_extensions()
        mocks["execution_repo"].get_plan_execution_stats.side_effect = Exception(
            "计划不存在"
        )

        with patch("src.core.context.get_context", return_value=context):
            runner_tools = RunnerTools(context=context)
            result = runner_tools.get_plan_execution_stats(plan_id="plan_unknown")

            assert "error" in result

    def test_analyze_training_response_success(self):
        context, mocks = _create_mock_context_with_extensions()
        mocks["analyzer"].analyze_plan_response.return_value = {
            "success": True,
            "data": {"plan_id": "plan_test"},
            "message": "训练响应分析完成",
        }

        with patch("src.core.context.get_context", return_value=context):
            runner_tools = RunnerTools(context=context)
            result = runner_tools.analyze_training_response(plan_id="plan_test")

            assert "plan_test" in str(result)

    def test_analyze_training_response_error(self):
        context, mocks = _create_mock_context_with_extensions()
        mocks["analyzer"].analyze_plan_response.side_effect = Exception("分析失败")

        with patch("src.core.context.get_context", return_value=context):
            runner_tools = RunnerTools(context=context)
            result = runner_tools.analyze_training_response(plan_id="plan_test")

            assert "error" in result


class TestToolDescriptionsV010:
    """v0.10.0 TOOL_DESCRIPTIONS 测试"""

    def test_record_plan_execution_description_exists(self):
        from src.agents.tools import TOOL_DESCRIPTIONS

        assert "record_plan_execution" in TOOL_DESCRIPTIONS
        desc = TOOL_DESCRIPTIONS["record_plan_execution"]
        assert "description" in desc
        assert "parameters" in desc
        assert "plan_id" in desc["parameters"]
        assert "date" in desc["parameters"]

    def test_get_plan_execution_stats_description_exists(self):
        from src.agents.tools import TOOL_DESCRIPTIONS

        assert "get_plan_execution_stats" in TOOL_DESCRIPTIONS
        desc = TOOL_DESCRIPTIONS["get_plan_execution_stats"]
        assert "description" in desc
        assert "parameters" in desc
        assert "plan_id" in desc["parameters"]

    def test_analyze_training_response_description_exists(self):
        from src.agents.tools import TOOL_DESCRIPTIONS

        assert "analyze_training_response" in TOOL_DESCRIPTIONS
        desc = TOOL_DESCRIPTIONS["analyze_training_response"]
        assert "description" in desc
        assert "parameters" in desc
        assert "plan_id" in desc["parameters"]
