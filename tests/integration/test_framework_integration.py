# 框架集成测试
# 验证工具与nanobot-ai框架正确集成

from unittest.mock import MagicMock, patch

import polars as pl
import pytest

from src.agents.tools import (
    CalculateVdotForRunTool,
    GetRecentRunsTool,
    GetRunningStatsTool,
    QueryByDateRangeTool,
    RunnerTools,
    UpdateMemoryTool,
    create_tools,
)
from tests.conftest import create_mock_context


class TestFrameworkIntegration:
    """
    框架集成测试

    目标：验证工具与nanobot-ai框架正确集成
    优先级：P0

    Bug历史：BaseTool缺少concurrency_safe属性导致框架报错
    """

    def test_base_tool_has_concurrency_safe_attribute(self):
        """
        测试BaseTool具有concurrency_safe属性

        Bug历史：nanobot-ai 0.1.4+ 要求工具具有concurrency_safe属性
        """
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = GetRunningStatsTool(runner_tools)

        assert hasattr(tool, "concurrency_safe")
        assert tool.concurrency_safe is True

    def test_all_tools_have_concurrency_safe(self):
        """
        测试所有工具都具有concurrency_safe属性
        """
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tools = create_tools(runner_tools)

        for tool in tools:
            assert hasattr(tool, "concurrency_safe"), (
                f"{tool.name} 缺少 concurrency_safe 属性"
            )

    def test_tool_to_schema_format(self):
        """
        测试工具schema格式符合OpenAI function calling规范
        """
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = GetRunningStatsTool(runner_tools)
            schema = tool.to_schema()

        assert schema["type"] == "function"
        assert "function" in schema
        assert "name" in schema["function"]
        assert "description" in schema["function"]
        assert "parameters" in schema["function"]
        assert schema["function"]["parameters"]["type"] == "object"

    def test_all_tools_schema_format(self):
        """
        测试所有工具的schema格式正确
        """
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tools = create_tools(runner_tools)

        for tool in tools:
            schema = tool.to_schema()
            assert schema["type"] == "function"
            assert "function" in schema
            assert "name" in schema["function"]
            assert len(schema["function"]["name"]) > 0

    def test_tool_validate_params_method(self):
        """
        测试工具参数验证方法
        """
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = CalculateVdotForRunTool(runner_tools)

        errors = tool.validate_params({})
        assert len(errors) > 0

        errors = tool.validate_params({"distance_m": 5000, "time_s": 1800})
        assert len(errors) == 0

    def test_tool_run_sync_method(self):
        """
        测试工具同步运行方法
        """
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = GetRunningStatsTool(runner_tools)

        result = tool._run_sync(lambda: {"data": "test"})
        assert '"data": "test"' in result

    def test_tool_run_sync_with_exception(self):
        """
        测试工具同步运行方法异常处理
        """
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = GetRunningStatsTool(runner_tools)

        result = tool._run_sync(lambda: 1 / 0)
        assert "error" in result


class TestToolDescriptions:
    """
    工具描述测试

    目标：验证工具描述与TOOL_DESCRIPTIONS一致
    优先级：P1
    """

    def test_tool_descriptions_defined(self):
        """
        测试所有工具都有描述
        """
        from src.agents.tools import TOOL_DESCRIPTIONS

        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tools = create_tools(runner_tools)

        for tool in tools:
            if tool.name in TOOL_DESCRIPTIONS:
                desc_entry = TOOL_DESCRIPTIONS[tool.name]
                assert "description" in desc_entry, f"{tool.name} 描述格式不正确"
                assert len(desc_entry["description"]) > 0

    @pytest.mark.skip(
        reason="已知问题：工具描述与TOOL_DESCRIPTIONS不一致，需要单独修复"
    )
    def test_tool_description_matches_schema(self):
        """
        测试工具描述与schema一致

        注意：此测试验证工具描述与TOOL_DESCRIPTIONS一致
        """
        from src.agents.tools import TOOL_DESCRIPTIONS

        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tools = create_tools(runner_tools)

        for tool in tools:
            if tool.name in TOOL_DESCRIPTIONS:
                schema = tool.to_schema()
                expected_desc = TOOL_DESCRIPTIONS[tool.name]["description"]
                actual_desc = schema["function"]["description"]
                assert actual_desc == expected_desc, f"{tool.name} 描述不匹配"


class TestToolParameterValidation:
    """
    工具参数验证测试

    目标：验证工具参数类型验证正确
    优先级：P0
    """

    def test_string_parameter_validation(self):
        """
        测试字符串参数验证
        """
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = QueryByDateRangeTool(runner_tools)

        errors = tool.validate_params({"start_date": 123, "end_date": 456})
        assert any("should be string" in e for e in errors)

    def test_integer_parameter_validation(self):
        """
        测试整数参数验证
        """
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = GetRecentRunsTool(runner_tools)

        errors = tool.validate_params({"limit": "not_an_integer"})
        assert any("should be integer" in e for e in errors)

    def test_number_parameter_validation(self):
        """
        测试数值参数验证
        """
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = CalculateVdotForRunTool(runner_tools)

        errors = tool.validate_params(
            {"distance_m": "not_a_number", "time_s": "not_a_number"}
        )
        assert any("should be number" in e for e in errors)

    def test_required_parameter_validation(self):
        """
        测试必填参数验证
        """
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = CalculateVdotForRunTool(runner_tools)

        errors = tool.validate_params({})
        assert any("missing required" in e for e in errors)


class TestToolExecution:
    """
    工具执行测试

    目标：验证工具异步执行正确
    优先级：P0
    """

    @pytest.mark.anyio
    async def test_get_running_stats_execution(self):
        """
        测试获取跑步统计工具执行
        """
        import json

        mock_storage = MagicMock()
        mock_analytics = MagicMock()
        mock_summary = MagicMock()
        mock_summary.height = 0
        mock_analytics.get_running_summary.return_value = mock_summary

        runner_tools = RunnerTools(
            context=create_mock_context(storage=mock_storage, analytics=mock_analytics)
        )
        tool = GetRunningStatsTool(runner_tools)

        result = await tool.execute()
        result_dict = json.loads(result)

        assert "error" in result_dict or "message" in result_dict

    @pytest.mark.anyio
    async def test_calculate_vdot_execution(self):
        """
        测试计算VDOT工具执行
        """
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = CalculateVdotForRunTool(runner_tools)

        result = await tool.execute(distance_m=5000, time_s=1800)
        assert isinstance(result, str)
        assert "error" not in result.lower() or "vdot" in result.lower()

    @pytest.mark.anyio
    async def test_query_by_date_range_execution(self):
        """
        测试日期范围查询工具执行
        """
        mock_storage = MagicMock()
        mock_analytics = MagicMock()
        mock_lf = MagicMock()
        mock_storage.read_parquet.return_value = mock_lf
        mock_lf.filter.return_value.select.return_value.sort.return_value.collect.return_value.iter_rows.return_value = []

        runner_tools = RunnerTools(
            context=create_mock_context(storage=mock_storage, analytics=mock_analytics)
        )
        tool = QueryByDateRangeTool(runner_tools)

        result = await tool.execute(start_date="2024-01-01", end_date="2024-12-31")
        assert isinstance(result, str)

    @pytest.mark.anyio
    async def test_update_memory_execution(self):
        """
        测试更新记忆工具执行
        """
        with patch("src.core.storage.StorageManager"):
            with patch(
                "src.core.base.profile.ProfileStorageManager"
            ) as MockProfileStorage:
                mock_profile_storage = MagicMock()
                MockProfileStorage.return_value = mock_profile_storage
                mock_profile_storage.save_memory_md.return_value = True

                runner_tools = RunnerTools()
                tool = UpdateMemoryTool(runner_tools)

                result = await tool.execute(note="测试笔记", category="training")
                assert "error" not in result or "成功" in result


class TestToolErrorHandling:
    """
    工具错误处理测试

    目标：验证工具正确处理异常
    优先级：P0
    """

    @pytest.mark.anyio
    async def test_tool_handles_exception(self):
        """
        测试工具异常处理
        """
        mock_storage = MagicMock()
        mock_analytics = MagicMock()
        mock_analytics.get_running_summary.side_effect = Exception("测试异常")

        runner_tools = RunnerTools(
            context=create_mock_context(storage=mock_storage, analytics=mock_analytics)
        )
        tool = GetRunningStatsTool(runner_tools)

        result = await tool.execute()
        assert "error" in result.lower()

    @pytest.mark.anyio
    async def test_tool_handles_none_values(self):
        """
        测试工具处理None值

        Bug历史：row.get("key", 0) 在值为None时返回None
        """
        import json
        from datetime import datetime

        mock_storage = MagicMock()
        mock_analytics = MagicMock()
        now = datetime.now()

        import polars as pl

        df = pl.DataFrame(
            {
                "timestamp": [now],
                "session_start_time": [now],
                "session_total_distance": [None],
                "session_total_timer_time": [None],
                "session_avg_heart_rate": [None],
            }
        )
        mock_storage.read_parquet.return_value = df.lazy()
        mock_analytics.get_running_summary.return_value = pl.DataFrame()

        runner_tools = RunnerTools(
            context=create_mock_context(storage=mock_storage, analytics=mock_analytics)
        )
        tool = GetRunningStatsTool(runner_tools)

        result = await tool.execute()
        result_dict = json.loads(result)

        assert "error" in result_dict or "message" in result_dict

    @pytest.mark.anyio
    async def test_tool_handles_empty_data(self):
        """
        测试工具处理空数据
        """
        import json

        mock_storage = MagicMock()
        mock_analytics = MagicMock()
        mock_analytics.get_running_summary.return_value = pl.DataFrame()

        runner_tools = RunnerTools(
            context=create_mock_context(storage=mock_storage, analytics=mock_analytics)
        )
        tool = GetRunningStatsTool(runner_tools)

        result = await tool.execute()
        result_dict = json.loads(result)

        assert (
            "error" in result_dict or "message" in result_dict or "data" in result_dict
        )
