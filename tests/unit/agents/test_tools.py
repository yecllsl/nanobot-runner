# Agent工具集单元测试

from datetime import datetime
from unittest.mock import MagicMock, patch

import polars as pl
import pytest

from src.agents.tools import (
    TOOL_DESCRIPTIONS,
    CalculateVdotForRunTool,
    GetHrDriftAnalysisTool,
    GetRecentRunsTool,
    GetRunningStatsTool,
    GetTrainingLoadTool,
    GetVdotTrendTool,
    QueryByDateRangeTool,
    QueryByDistanceTool,
    RunnerTools,
    UpdateMemoryTool,
    create_tools,
)
from tests.conftest import create_mock_context


class TestBaseTool:
    """BaseTool 基类测试"""

    def test_to_schema(self):
        """测试转换为 OpenAI function schema 格式"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = GetRunningStatsTool(runner_tools)

            schema = tool.to_schema()

            assert schema["type"] == "function"
            assert schema["function"]["name"] == "get_running_stats"
            assert "description" in schema["function"]
            assert "parameters" in schema["function"]

    def test_validate_params_missing_required(self):
        """测试缺少必填参数验证"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = CalculateVdotForRunTool(runner_tools)

            errors = tool.validate_params({})

            assert len(errors) > 0
            assert any("missing required" in e for e in errors)

    def test_validate_params_type_mismatch_string(self):
        """测试参数类型不匹配验证 - string"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = QueryByDateRangeTool(runner_tools)

            errors = tool.validate_params({"start_date": 123, "end_date": 456})

            assert len(errors) > 0
            assert any("should be string" in e for e in errors)

    def test_validate_params_type_mismatch_integer(self):
        """测试参数类型不匹配验证 - integer"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = GetRecentRunsTool(runner_tools)

            errors = tool.validate_params({"limit": "not_an_integer"})

            assert len(errors) > 0
            assert any("should be integer" in e for e in errors)

    def test_validate_params_type_mismatch_number(self):
        """测试参数类型不匹配验证 - number"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = CalculateVdotForRunTool(runner_tools)

            errors = tool.validate_params(
                {"distance_m": "not_a_number", "time_s": "not_a_number"}
            )

            assert len(errors) > 0
            assert any("should be number" in e for e in errors)

    def test_validate_params_valid(self):
        """测试有效参数验证"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = CalculateVdotForRunTool(runner_tools)

            errors = tool.validate_params({"distance_m": 5000, "time_s": 1200})

            assert len(errors) == 0

    def test_run_sync_success(self):
        """测试同步调用成功"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = GetRunningStatsTool(runner_tools)

            def mock_func():
                return {"data": "test"}

            result = tool._run_sync(mock_func)
            assert '"data": "test"' in result

    def test_run_sync_exception(self):
        """测试同步调用异常"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = GetRunningStatsTool(runner_tools)

            def mock_func():
                raise ValueError("test error")

            result = tool._run_sync(mock_func)
            assert "error" in result


class TestGetRunningStatsTool:
    """GetRunningStatsTool 测试"""

    def test_name(self):
        """测试工具名称"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = GetRunningStatsTool(runner_tools)
            assert tool.name == "get_running_stats"

    def test_description(self):
        """测试工具描述"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = GetRunningStatsTool(runner_tools)
            assert "跑步统计" in tool.description

    def test_parameters(self):
        """测试参数定义"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = GetRunningStatsTool(runner_tools)
            assert tool.parameters["type"] == "object"
            assert "start_date" in tool.parameters["properties"]
            assert "end_date" in tool.parameters["properties"]

    @pytest.mark.anyio
    async def test_execute(self):
        """测试异步执行"""
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

        assert "error" in result_dict
        assert "暂无跑步数据" in result_dict["error"]


class TestGetRecentRunsTool:
    """GetRecentRunsTool 测试"""

    def test_name(self):
        """测试工具名称"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = GetRecentRunsTool(runner_tools)
            assert tool.name == "get_recent_runs"

    def test_parameters(self):
        """测试参数定义"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = GetRecentRunsTool(runner_tools)
            assert "limit" in tool.parameters["properties"]

    @pytest.mark.anyio
    async def test_execute(self):
        """测试异步执行"""
        with patch("src.core.storage.StorageManager") as MockStorage:
            mock_storage = MagicMock()
            MockStorage.return_value = mock_storage

            mock_lf = MagicMock()
            mock_storage.read_parquet.return_value = mock_lf
            mock_lf.sort.return_value.limit.return_value.collect.return_value.iter_rows.return_value = []

            runner_tools = RunnerTools(
                context=create_mock_context(storage=mock_storage)
            )
            tool = GetRecentRunsTool(runner_tools)

            result = await tool.execute(limit=5)

            assert isinstance(result, str)


class TestCalculateVdotForRunTool:
    """CalculateVdotForRunTool 测试"""

    def test_name(self):
        """测试工具名称"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = CalculateVdotForRunTool(runner_tools)
            assert tool.name == "calculate_vdot_for_run"

    def test_parameters_required(self):
        """测试必填参数"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = CalculateVdotForRunTool(runner_tools)
            assert "distance_m" in tool.parameters["required"]
            assert "time_s" in tool.parameters["required"]

    @pytest.mark.anyio
    async def test_execute(self):
        """测试异步执行"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = CalculateVdotForRunTool(runner_tools)

            result = await tool.execute(distance_m=5000, time_s=1200)

            assert isinstance(result, str)


class TestGetVdotTrendTool:
    """GetVdotTrendTool 测试"""

    def test_name(self):
        """测试工具名称"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = GetVdotTrendTool(runner_tools)
            assert tool.name == "get_vdot_trend"

    @pytest.mark.anyio
    async def test_execute(self):
        """测试异步执行"""
        with patch("src.core.storage.StorageManager") as MockStorage:
            mock_storage = MagicMock()
            MockStorage.return_value = mock_storage

            mock_lf = MagicMock()
            mock_storage.read_parquet.return_value = mock_lf
            mock_lf.sort.return_value.limit.return_value.collect.return_value.iter_rows.return_value = []

            runner_tools = RunnerTools(
                context=create_mock_context(storage=mock_storage)
            )
            tool = GetVdotTrendTool(runner_tools)

            result = await tool.execute(limit=10)

            assert isinstance(result, str)


class TestGetHrDriftAnalysisTool:
    """GetHrDriftAnalysisTool 测试"""

    def test_name(self):
        """测试工具名称"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = GetHrDriftAnalysisTool(runner_tools)
            assert tool.name == "get_hr_drift_analysis"

    @pytest.mark.anyio
    async def test_execute_empty_data(self):
        """测试空数据执行"""
        with patch("src.core.storage.StorageManager") as MockStorage:
            mock_storage = MagicMock()
            MockStorage.return_value = mock_storage

            mock_lf = MagicMock()
            mock_storage.read_parquet.return_value = mock_lf
            mock_lf.collect.return_value.height = 0

            runner_tools = RunnerTools(
                context=create_mock_context(storage=mock_storage)
            )
            tool = GetHrDriftAnalysisTool(runner_tools)

            result = await tool.execute()

            assert "error" in result


class TestGetTrainingLoadTool:
    """GetTrainingLoadTool 测试"""

    def test_name(self):
        """测试工具名称"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = GetTrainingLoadTool(runner_tools)
            assert tool.name == "get_training_load"

    @pytest.mark.anyio
    async def test_execute(self):
        """测试异步执行"""
        with patch("src.core.storage.StorageManager") as MockStorage:
            mock_storage = MagicMock()
            MockStorage.return_value = mock_storage

            runner_tools = RunnerTools(
                context=create_mock_context(storage=mock_storage)
            )
            tool = GetTrainingLoadTool(runner_tools)

            result = await tool.execute(days=42)

            assert isinstance(result, str)


class TestQueryByDateRangeTool:
    """QueryByDateRangeTool 测试"""

    def test_name(self):
        """测试工具名称"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = QueryByDateRangeTool(runner_tools)
            assert tool.name == "query_by_date_range"

    def test_parameters_required(self):
        """测试必填参数"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = QueryByDateRangeTool(runner_tools)
            assert "start_date" in tool.parameters["required"]
            assert "end_date" in tool.parameters["required"]

    @pytest.mark.anyio
    async def test_execute(self):
        """测试异步执行"""
        with patch("src.core.storage.StorageManager") as MockStorage:
            mock_storage = MagicMock()
            MockStorage.return_value = mock_storage

            mock_lf = MagicMock()
            mock_storage.read_parquet.return_value = mock_lf
            mock_lf.filter.return_value.select.return_value.sort.return_value.collect.return_value.iter_rows.return_value = []

            runner_tools = RunnerTools(
                context=create_mock_context(storage=mock_storage)
            )
            tool = QueryByDateRangeTool(runner_tools)

            result = await tool.execute(start_date="2024-01-01", end_date="2024-12-31")

            assert isinstance(result, str)


class TestQueryByDistanceTool:
    """QueryByDistanceTool 测试"""

    def test_name(self):
        """测试工具名称"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = QueryByDistanceTool(runner_tools)
            assert tool.name == "query_by_distance"

    def test_parameters_required(self):
        """测试必填参数"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = QueryByDistanceTool(runner_tools)
            assert "min_distance" in tool.parameters["required"]

    @pytest.mark.anyio
    async def test_execute(self):
        """测试异步执行"""
        with patch("src.core.storage.StorageManager") as MockStorage:
            mock_storage = MagicMock()
            MockStorage.return_value = mock_storage

            mock_lf = MagicMock()
            mock_storage.read_parquet.return_value = mock_lf
            mock_lf.filter.return_value.select.return_value.sort.return_value.collect.return_value.iter_rows.return_value = []

            runner_tools = RunnerTools(
                context=create_mock_context(storage=mock_storage)
            )
            tool = QueryByDistanceTool(runner_tools)

            result = await tool.execute(min_distance=5.0)

            assert isinstance(result, str)


class TestUpdateMemoryTool:
    """UpdateMemoryTool 测试"""

    def test_name(self):
        """测试工具名称"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = UpdateMemoryTool(runner_tools)
            assert tool.name == "update_memory"

    def test_description(self):
        """测试工具描述"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = UpdateMemoryTool(runner_tools)
            assert "记忆" in tool.description or "Memory" in tool.description

    def test_parameters(self):
        """测试参数定义"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = UpdateMemoryTool(runner_tools)
            assert tool.parameters["type"] == "object"
            assert "note" in tool.parameters["properties"]
            assert "category" in tool.parameters["properties"]
            assert "note" in tool.parameters["required"]
            assert "category" not in tool.parameters.get("required", [])

    def test_parameters_category_enum(self):
        """测试分类参数枚举值"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = UpdateMemoryTool(runner_tools)
            category_schema = tool.parameters["properties"]["category"]
            assert "enum" in category_schema
            assert category_schema["enum"] == [
                "training",
                "preference",
                "injury",
                "other",
            ]
            assert category_schema.get("default") == "other"

    @pytest.mark.anyio
    async def test_execute_success(self):
        """测试执行成功"""
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

    @pytest.mark.anyio
    async def test_execute_empty_note(self):
        """测试空笔记内容"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = UpdateMemoryTool(runner_tools)

            result = await tool.execute(note="")

            assert "error" in result
            assert "空" in result

    @pytest.mark.anyio
    async def test_execute_invalid_category(self):
        """测试无效分类"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = UpdateMemoryTool(runner_tools)

            result = await tool.execute(note="测试", category="invalid")

            assert "error" in result
            assert "无效" in result or "invalid" in result

    @pytest.mark.anyio
    async def test_execute_default_category(self):
        """测试默认分类"""
        with patch("src.core.storage.StorageManager"):
            with patch(
                "src.core.base.profile.ProfileStorageManager"
            ) as MockProfileStorage:
                mock_profile_storage = MagicMock()
                MockProfileStorage.return_value = mock_profile_storage
                mock_profile_storage.save_memory_md.return_value = True

                runner_tools = RunnerTools()
                tool = UpdateMemoryTool(runner_tools)

                result = await tool.execute(note="测试笔记")

                assert isinstance(result, str)

    @pytest.mark.anyio
    async def test_execute_save_failure(self):
        """测试保存失败"""
        mock_profile_storage = MagicMock()
        mock_profile_storage.save_memory_md.return_value = False

        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            runner_tools.profile_storage = mock_profile_storage
            tool = UpdateMemoryTool(runner_tools)

            result = await tool.execute(note="测试笔记")

            assert "error" in result


class TestCreateTools:
    """create_tools 函数测试"""

    def test_create_tools_returns_list(self):
        """测试返回工具列表"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tools = create_tools(runner_tools)

            assert isinstance(tools, list)
            assert len(tools) == 28

    def test_create_tools_contains_all_tools(self):
        """测试包含所有工具"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tools = create_tools(runner_tools)

            expected_names = [
                "get_running_stats",
                "get_recent_runs",
                "calculate_vdot_for_run",
                "get_vdot_trend",
                "get_hr_drift_analysis",
                "get_training_load",
                "query_by_date_range",
                "query_by_distance",
                "update_memory",
                "get_weather_training_advice",
                "diagnose_suggestion",
                "diagnose_error",
                "get_personalized_suggestion",
                "record_feedback",
                "get_user_preferences",
                "update_user_preferences",
            ]

            tool_names = [t.name for t in tools]
            for expected_name in expected_names:
                assert expected_name in tool_names


class TestRunnerTools:
    """RunnerTools 单元测试"""

    def test_init(self):
        """测试初始化"""
        tools = RunnerTools()
        assert tools is not None

    def test_init_with_storage(self):
        """测试使用自定义存储初始化"""
        mock_storage = MagicMock()
        tools = RunnerTools(context=create_mock_context(storage=mock_storage))
        assert tools.storage == mock_storage

    def test_get_running_stats_empty(self):
        """测试空数据统计"""
        mock_storage = MagicMock()
        mock_analytics = MagicMock()
        mock_analytics.get_running_summary.return_value = pl.DataFrame()

        tools = RunnerTools(
            context=create_mock_context(storage=mock_storage, analytics=mock_analytics)
        )

        result = tools.get_running_stats()

        assert "message" in result

    def test_get_running_stats_with_data(self):
        """测试有数据统计"""
        with patch("src.core.storage.StorageManager") as MockStorage:
            mock_storage = MagicMock()
            MockStorage.return_value = mock_storage

            tools = RunnerTools(context=create_mock_context(storage=mock_storage))

            mock_summary = MagicMock()
            mock_summary.height = 1
            mock_summary.row.return_value = (10, 50000, 3600, 5.0, 360, 10.0, 150)
            tools.analytics.get_running_summary = MagicMock(return_value=mock_summary)

            result = tools.get_running_stats()

            assert "total_runs" in result
            assert result["total_runs"] == 10

    def test_get_running_stats_with_date_range(self):
        """测试带日期范围统计"""
        with patch("src.core.storage.StorageManager") as MockStorage:
            mock_storage = MagicMock()
            MockStorage.return_value = mock_storage

            tools = RunnerTools(context=create_mock_context(storage=mock_storage))

            mock_summary = MagicMock()
            mock_summary.height = 1
            mock_summary.row.return_value = (5, 25000, 1800, 5.0, 360, 5.0, 145)
            tools.analytics.get_running_summary = MagicMock(return_value=mock_summary)

            result = tools.get_running_stats(
                start_date="2024-01-01", end_date="2024-12-31"
            )

            assert "total_runs" in result

    def test_get_recent_runs(self):
        """测试获取最近跑步记录"""
        with patch("src.core.storage.StorageManager") as MockStorage:
            mock_storage = MagicMock()
            MockStorage.return_value = mock_storage

            tools = RunnerTools(context=create_mock_context(storage=mock_storage))

            mock_lf = MagicMock()
            mock_storage.read_parquet.return_value = mock_lf

            mock_df = MagicMock()
            mock_df.sort.return_value = mock_df
            mock_df.limit.return_value = mock_df
            mock_df.collect.return_value = mock_df
            mock_df.iter_rows.return_value = []

            result = tools.get_recent_runs(limit=5)

            assert isinstance(result, list)

    def test_get_recent_runs_with_data(self):
        """测试获取最近跑步记录有数据"""
        with patch("src.core.storage.StorageManager") as MockStorage:
            mock_storage = MagicMock()
            MockStorage.return_value = mock_storage

            tools = RunnerTools(context=create_mock_context(storage=mock_storage))

            mock_lf = MagicMock()
            mock_storage.read_parquet.return_value = mock_lf

            mock_grouped = MagicMock()
            mock_agg = MagicMock()
            mock_sorted = MagicMock()
            mock_limited = MagicMock()
            mock_df = MagicMock()
            mock_lf.group_by.return_value = mock_grouped
            mock_grouped.agg.return_value = mock_agg
            mock_agg.sort.return_value = mock_sorted
            mock_sorted.limit.return_value = mock_limited
            mock_limited.collect.return_value = mock_df
            mock_df.iter_rows.return_value = [
                {
                    "timestamp": "2024-01-01",
                    "distance": 5000,
                    "duration": 1200,
                    "avg_hr": 150,
                }
            ]

            result = tools.get_recent_runs(limit=5)

            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]["distance_km"] == 5.0

    def test_calculate_vdot_for_run(self):
        """测试计算VDOT"""
        tools = RunnerTools()

        vdot = tools.calculate_vdot_for_run(5000, 1200)

        assert vdot > 0
        assert vdot < 100

    def test_calculate_vdot_zero_distance(self):
        """测试VDOT计算零距离返回 0"""
        tools = RunnerTools()

        vdot = tools.calculate_vdot_for_run(0, 1800)

        assert vdot == 0.0

    def test_calculate_vdot_zero_time(self):
        """测试VDOT计算零时间返回 0"""
        tools = RunnerTools()

        vdot = tools.calculate_vdot_for_run(5000, 0)

        assert vdot == 0.0

    def test_get_vdot_trend_empty(self):
        """测试获取VDOT趋势空数据"""
        with patch("src.core.storage.StorageManager") as MockStorage:
            mock_storage = MagicMock()
            MockStorage.return_value = mock_storage

            mock_lf = MagicMock()
            mock_storage.read_parquet.return_value = mock_lf
            mock_lf.sort.return_value.limit.return_value.collect.return_value.iter_rows.return_value = []

            tools = RunnerTools(context=create_mock_context(storage=mock_storage))

            result = tools.get_vdot_trend(limit=10)

            assert isinstance(result, list)
            assert len(result) == 0

    def test_get_vdot_trend_with_data(self):
        """测试获取VDOT趋势有数据"""
        with patch("src.core.storage.StorageManager") as MockStorage:
            mock_storage = MagicMock()
            MockStorage.return_value = mock_storage

            mock_lf = MagicMock()
            mock_storage.read_parquet.return_value = mock_lf

            mock_grouped = MagicMock()
            mock_agg = MagicMock()
            mock_sorted = MagicMock()
            mock_limited = MagicMock()
            mock_df = MagicMock()

            mock_lf.group_by.return_value = mock_grouped
            mock_grouped.agg.return_value = mock_agg
            mock_agg.sort.return_value = mock_sorted
            mock_sorted.limit.return_value = mock_limited
            mock_limited.collect.return_value = mock_df
            mock_df.iter_rows.return_value = [
                {
                    "timestamp": datetime(2024, 1, 1),
                    "distance": 5000.0,
                    "duration": 1200.0,
                },
                {
                    "timestamp": datetime(2024, 1, 2),
                    "distance": 10000.0,
                    "duration": 2400.0,
                },
            ]

            tools = RunnerTools(context=create_mock_context(storage=mock_storage))

            result = tools.get_vdot_trend(limit=10)

            assert isinstance(result, list)

    def test_query_by_date_range_invalid_format(self):
        """测试无效日期格式"""
        tools = RunnerTools()

        result = tools.query_by_date_range("invalid", "2024-12-31")

        assert isinstance(result, list)
        assert "error" in result[0]

    def test_query_by_date_range_empty_result(self):
        """测试日期范围查询无结果"""
        mock_storage = MagicMock()
        mock_lf = MagicMock()
        mock_storage.read_parquet.return_value = mock_lf

        mock_df = MagicMock()
        mock_df.filter.return_value = mock_df
        mock_df.select.return_value = mock_df
        mock_df.sort.return_value = mock_df
        mock_df.collect.return_value = mock_df
        mock_df.iter_rows.return_value = []

        tools = RunnerTools(context=create_mock_context(storage=mock_storage))
        result = tools.query_by_date_range("2025-01-01", "2025-12-31")

        assert isinstance(result, list)
        assert len(result) == 0

    def test_query_by_distance_no_upper_limit(self):
        """测试无上限距离查询"""
        mock_storage = MagicMock()
        mock_lf = MagicMock()
        mock_storage.read_parquet.return_value = mock_lf

        mock_df = MagicMock()
        mock_df.filter.return_value = mock_df
        mock_df.select.return_value = mock_df
        mock_df.sort.return_value = mock_df
        mock_df.collect.return_value = mock_df
        mock_df.iter_rows.return_value = [
            {
                "timestamp": datetime(2024, 1, 15),
                "total_distance": 15000,
                "total_timer_time": 3600,
                "avg_heart_rate": 140,
                "avg_pace": 240,
            }
        ]

        tools = RunnerTools(context=create_mock_context(storage=mock_storage))
        result = tools.query_by_distance(min_distance=10)

        assert isinstance(result, list)

    def test_query_by_distance_with_upper_limit(self):
        """测试有上限距离查询"""
        mock_storage = MagicMock()
        mock_lf = MagicMock()
        mock_storage.read_parquet.return_value = mock_lf

        mock_df = MagicMock()
        mock_df.filter.return_value = mock_df
        mock_df.select.return_value = mock_df
        mock_df.sort.return_value = mock_df
        mock_df.collect.return_value = mock_df
        mock_df.iter_rows.return_value = [
            {
                "timestamp": datetime(2024, 1, 15),
                "total_distance": 8000,
                "total_timer_time": 2400,
                "avg_heart_rate": 145,
                "avg_pace": 300,
            }
        ]

        tools = RunnerTools(context=create_mock_context(storage=mock_storage))
        result = tools.query_by_distance(min_distance=5, max_distance=10)

        assert isinstance(result, list)

    def test_query_by_distance_empty_result(self):
        """测试距离查询无结果"""
        mock_storage = MagicMock()
        mock_lf = MagicMock()
        mock_storage.read_parquet.return_value = mock_lf

        mock_df = MagicMock()
        mock_df.filter.return_value = mock_df
        mock_df.select.return_value = mock_df
        mock_df.sort.return_value = mock_df
        mock_df.collect.return_value = mock_df
        mock_df.iter_rows.return_value = []

        tools = RunnerTools(context=create_mock_context(storage=mock_storage))
        result = tools.query_by_distance(min_distance=100)

        assert isinstance(result, list)
        assert len(result) == 0

    def test_get_training_load(self):
        """测试训练负荷查询"""
        mock_storage = MagicMock()
        mock_lf = MagicMock()
        mock_storage.read_parquet.return_value = mock_lf

        mock_df = MagicMock()
        mock_df.is_empty.return_value = True
        mock_lf.filter.return_value.collect.return_value = mock_df

        mock_engine = MagicMock()
        mock_engine.get_training_load.return_value = {
            "atl": 50.0,
            "ctl": 60.0,
            "tsb": 10.0,
        }

        tools = RunnerTools(
            context=create_mock_context(storage=mock_storage, analytics=mock_engine)
        )
        result = tools.get_training_load(days=30)

        assert isinstance(result, dict)

    def test_update_memory_success(self):
        """测试更新记忆成功"""
        with patch("src.core.storage.StorageManager"):
            with patch(
                "src.core.base.profile.ProfileStorageManager"
            ) as MockProfileStorage:
                mock_profile_storage = MagicMock()
                MockProfileStorage.return_value = mock_profile_storage
                mock_profile_storage.save_memory_md.return_value = True

                runner_tools = RunnerTools()
                result = runner_tools.update_memory("测试笔记", "training")

                assert result["success"] is True
                assert "message" in result
                assert "note" in result

    def test_update_memory_empty_note(self):
        """测试空笔记"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            result = runner_tools.update_memory("")

            assert "error" in result
            assert "空" in result["error"]

    def test_update_memory_whitespace_note(self):
        """测试空白字符笔记"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            result = runner_tools.update_memory("   ")

            assert "error" in result

    def test_update_memory_invalid_category(self):
        """测试无效分类"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            result = runner_tools.update_memory("测试", "invalid_category")

            assert "error" in result
            assert "无效" in result["error"]

    def test_update_memory_default_category(self):
        """测试默认分类"""
        with patch("src.core.storage.StorageManager"):
            with patch(
                "src.core.base.profile.ProfileStorageManager"
            ) as MockProfileStorage:
                mock_profile_storage = MagicMock()
                MockProfileStorage.return_value = mock_profile_storage
                mock_profile_storage.save_memory_md.return_value = True

                runner_tools = RunnerTools()
                result = runner_tools.update_memory("测试笔记")

                assert result["success"] is True

    def test_update_memory_all_categories(self):
        """测试所有有效分类"""
        categories = ["training", "preference", "injury", "other"]

        for category in categories:
            with (
                patch("src.core.storage.StorageManager"),
                patch(
                    "src.core.base.profile.ProfileStorageManager"
                ) as MockProfileStorage,
            ):
                mock_profile_storage = MagicMock()
                MockProfileStorage.return_value = mock_profile_storage
                mock_profile_storage.save_memory_md.return_value = True

                runner_tools = RunnerTools()
                result = runner_tools.update_memory("测试笔记", category)

                assert result["success"] is True

    def test_update_memory_exception_handling(self):
        """测试异常处理"""
        with patch("src.core.storage.StorageManager"):
            with patch(
                "src.core.base.profile.ProfileStorageManager"
            ) as MockProfileStorage:
                mock_profile_storage = MagicMock()
                MockProfileStorage.return_value = mock_profile_storage
                mock_profile_storage.save_memory_md.side_effect = Exception("测试异常")

                runner_tools = RunnerTools()
                result = runner_tools.update_memory("测试笔记")

                assert "error" in result or "success" in result

    def test_update_memory_formats_note(self):
        """测试笔记格式化"""
        with patch("src.core.storage.StorageManager"):
            with patch(
                "src.core.base.profile.ProfileStorageManager"
            ) as MockProfileStorage:
                mock_profile_storage = MagicMock()
                MockProfileStorage.return_value = mock_profile_storage
                mock_profile_storage.save_memory_md.return_value = True

                runner_tools = RunnerTools()
                result = runner_tools.update_memory("测试笔记", "training")

                assert "note" in result
                assert "[训练]" in result["note"]


class TestToolDescriptions:
    """工具描述测试"""

    def test_all_tools_have_descriptions(self):
        """测试所有工具都有描述"""
        expected_tools = [
            "get_running_stats",
            "get_recent_runs",
            "calculate_vdot_for_run",
            "get_vdot_trend",
            "get_hr_drift_analysis",
            "get_training_load",
            "query_by_date_range",
            "query_by_distance",
            "update_memory",
        ]

        for tool_name in expected_tools:
            assert tool_name in TOOL_DESCRIPTIONS

    def test_tool_has_description_field(self):
        """测试工具描述包含description字段"""
        for _tool_name, tool_info in TOOL_DESCRIPTIONS.items():
            assert "description" in tool_info

    def test_tool_has_parameters(self):
        """测试工具描述包含parameters字段"""
        for _tool_name, tool_info in TOOL_DESCRIPTIONS.items():
            assert "parameters" in tool_info

    def test_update_memory_in_descriptions(self):
        """测试 update_memory 在描述字典中"""
        assert "update_memory" in TOOL_DESCRIPTIONS

    def test_update_memory_has_description(self):
        """测试 update_memory 有 description 字段"""
        assert "description" in TOOL_DESCRIPTIONS["update_memory"]

    def test_update_memory_has_parameters(self):
        """测试 update_memory 有 parameters 字段"""
        assert "parameters" in TOOL_DESCRIPTIONS["update_memory"]

    def test_update_memory_parameters(self):
        """测试 update_memory 参数定义"""
        update_memory_desc = TOOL_DESCRIPTIONS["update_memory"]
        params = update_memory_desc["parameters"]
        assert "note" in params
        assert "category" in params


class TestBaseToolValidateParamsExtended:
    """BaseTool 参数验证扩展测试"""

    def test_validate_params_update_memory_required(self):
        """测试 UpdateMemoryTool 必填参数验证"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = UpdateMemoryTool(runner_tools)

            errors = tool.validate_params({})

            assert len(errors) > 0
            assert any("missing required" in e for e in errors)

    def test_validate_params_update_memory_valid(self):
        """测试 UpdateMemoryTool 有效参数"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = UpdateMemoryTool(runner_tools)

            errors = tool.validate_params({"note": "测试笔记", "category": "training"})

            assert len(errors) == 0

    def test_validate_params_update_memory_optional_category(self):
        """测试 UpdateMemoryTool 可选分类参数"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = UpdateMemoryTool(runner_tools)

            errors = tool.validate_params({"note": "测试笔记"})

            assert len(errors) == 0


class TestUpdateMemoryToolSchema:
    """UpdateMemoryTool schema 测试"""

    def test_to_schema_format(self):
        """测试转换为 OpenAI function schema 格式"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = UpdateMemoryTool(runner_tools)

            schema = tool.to_schema()

            assert schema["type"] == "function"
            assert "function" in schema
            assert schema["function"]["name"] == "update_memory"
            assert "description" in schema["function"]
            assert "parameters" in schema["function"]

    def test_schema_parameters_structure(self):
        """测试 schema 参数结构"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = UpdateMemoryTool(runner_tools)

            schema = tool.to_schema()
            params = schema["function"]["parameters"]

            assert params["type"] == "object"
            assert "properties" in params
            assert "note" in params["properties"]
            assert "category" in params["properties"]
