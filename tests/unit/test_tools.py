# Agent工具集单元测试

from datetime import datetime
from unittest.mock import MagicMock, patch

import polars as pl
import pytest

from src.agents.tools import (
    TOOL_DESCRIPTIONS,
    BaseTool,
    CalculateVdotForRunTool,
    GetHrDriftAnalysisTool,
    GetRecentRunsTool,
    GetRunningStatsTool,
    GetTrainingLoadTool,
    GetVdotTrendTool,
    QueryByDateRangeTool,
    QueryByDistanceTool,
    RunnerTools,
    create_tools,
)


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
            assert any("missing required field" in e for e in errors)

    def test_validate_params_type_mismatch_string(self):
        """测试参数类型不匹配验证 - string"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = QueryByDateRangeTool(runner_tools)

            errors = tool.validate_params({"start_date": 123, "end_date": 456})

            assert len(errors) > 0
            assert any("must be string" in e for e in errors)

    def test_validate_params_type_mismatch_integer(self):
        """测试参数类型不匹配验证 - integer"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = GetRecentRunsTool(runner_tools)

            errors = tool.validate_params({"limit": "not_an_integer"})

            assert len(errors) > 0
            assert any("must be integer" in e for e in errors)

    def test_validate_params_type_mismatch_number(self):
        """测试参数类型不匹配验证 - number"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = CalculateVdotForRunTool(runner_tools)

            errors = tool.validate_params(
                {"distance_m": "not_a_number", "time_s": "not_a_number"}
            )

            assert len(errors) > 0
            assert any("must be number" in e for e in errors)

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
        with patch("src.core.storage.StorageManager") as MockStorage:
            mock_storage = MagicMock()
            MockStorage.return_value = mock_storage
            mock_storage.read_parquet.return_value.collect.return_value.height = 0

            runner_tools = RunnerTools(storage=mock_storage)
            tool = GetRunningStatsTool(runner_tools)

            result = await tool.execute()

            # 新格式返回 {"success": false, "error": ...}
            assert "success" in result
            assert "error" in result


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
            mock_lf.sort.return_value.limit.return_value.collect.return_value.iter_rows.return_value = (
                []
            )

            runner_tools = RunnerTools(storage=mock_storage)
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
            mock_lf.sort.return_value.limit.return_value.collect.return_value.iter_rows.return_value = (
                []
            )

            runner_tools = RunnerTools(storage=mock_storage)
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

            runner_tools = RunnerTools(storage=mock_storage)
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

            runner_tools = RunnerTools(storage=mock_storage)
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
            mock_lf.filter.return_value.select.return_value.sort.return_value.collect.return_value.iter_rows.return_value = (
                []
            )

            runner_tools = RunnerTools(storage=mock_storage)
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
            mock_lf.filter.return_value.select.return_value.sort.return_value.collect.return_value.iter_rows.return_value = (
                []
            )

            runner_tools = RunnerTools(storage=mock_storage)
            tool = QueryByDistanceTool(runner_tools)

            result = await tool.execute(min_distance=5.0)

            assert isinstance(result, str)


class TestCreateTools:
    """create_tools 函数测试"""

    def test_create_tools_returns_list(self):
        """测试返回工具列表"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tools = create_tools(runner_tools)

            assert isinstance(tools, list)
            assert len(tools) == 10

    def test_create_tools_contains_all_tools(self):
        """测试包含所有工具"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tools = create_tools(runner_tools)

            tool_names = [t.name for t in tools]
            assert "get_running_stats" in tool_names
            assert "get_recent_runs" in tool_names
            assert "calculate_vdot_for_run" in tool_names
            assert "get_vdot_trend" in tool_names
            assert "get_hr_drift_analysis" in tool_names
            assert "get_training_load" in tool_names
            assert "query_by_date_range" in tool_names
            assert "query_by_distance" in tool_names
            assert "update_memory" in tool_names


class TestRunnerTools:
    """RunnerTools 单元测试"""

    def test_init(self):
        """测试初始化"""
        tools = RunnerTools()
        assert tools is not None

    def test_init_with_storage(self):
        """测试使用自定义存储初始化"""
        mock_storage = MagicMock()
        tools = RunnerTools(storage=mock_storage)
        assert tools.storage == mock_storage

    def test_get_running_stats_empty(self):
        """测试空数据统计"""
        with patch("src.core.storage.StorageManager") as MockStorage:
            mock_storage = MagicMock()
            MockStorage.return_value = mock_storage

            tools = RunnerTools(storage=mock_storage)

            # 模拟空数据
            mock_storage.read_parquet.return_value.collect.return_value.height = 0

            result = tools.get_running_stats()

            assert "message" in result

    def test_get_running_stats_with_data(self):
        """测试有数据统计"""
        with patch("src.core.storage.StorageManager") as MockStorage:
            mock_storage = MagicMock()
            MockStorage.return_value = mock_storage

            tools = RunnerTools(storage=mock_storage)

            # 模拟 AnalyticsEngine.get_running_summary 返回有数据
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

            tools = RunnerTools(storage=mock_storage)

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

            tools = RunnerTools(storage=mock_storage)

            # 模拟数据
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

            tools = RunnerTools(storage=mock_storage)

            mock_lf = MagicMock()
            mock_storage.read_parquet.return_value = mock_lf

            # Mock group_by chain
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

    def test_get_vdot_trend_empty(self):
        """测试获取VDOT趋势空数据"""
        with patch("src.core.storage.StorageManager") as MockStorage:
            mock_storage = MagicMock()
            MockStorage.return_value = mock_storage

            mock_lf = MagicMock()
            mock_storage.read_parquet.return_value = mock_lf
            mock_lf.sort.return_value.limit.return_value.collect.return_value.iter_rows.return_value = (
                []
            )

            tools = RunnerTools(storage=mock_storage)

            result = tools.get_vdot_trend(limit=10)

            assert isinstance(result, list)
            assert len(result) == 0

    def test_get_vdot_trend_with_data(self):
        """测试获取VDOT趋势有数据"""
        from datetime import datetime

        with patch("src.core.storage.StorageManager") as MockStorage:
            mock_storage = MagicMock()
            MockStorage.return_value = mock_storage

            mock_df = pl.DataFrame(
                [
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
            )

            mock_lf = MagicMock()
            mock_storage.read_parquet.return_value = mock_lf
            mock_lf.group_by.return_value.agg.return_value.sort.return_value.limit.return_value.collect.return_value = (
                mock_df
            )

            tools = RunnerTools(storage=mock_storage)

            result = tools.get_vdot_trend(limit=10)

            assert isinstance(result, list)
            assert len(result) == 2

    def test_get_hr_drift_analysis_empty(self):
        """测试心率漂移分析空数据"""
        with patch("src.core.storage.StorageManager") as MockStorage:
            mock_storage = MagicMock()
            MockStorage.return_value = mock_storage

            mock_lf = MagicMock()
            mock_storage.read_parquet.return_value = mock_lf
            mock_lf.collect.return_value.height = 0

            tools = RunnerTools(storage=mock_storage)

            result = tools.get_hr_drift_analysis()

            assert "error" in result

    def test_get_hr_drift_analysis_with_data(self):
        """测试心率漂移分析有数据"""
        with patch("src.core.storage.StorageManager") as MockStorage:
            mock_storage = MagicMock()
            MockStorage.return_value = mock_storage

            mock_lf = MagicMock()
            mock_storage.read_parquet.return_value = mock_lf
            mock_df = MagicMock()
            mock_df.height = 1
            mock_df.columns = ["heart_rate"]
            mock_df.select.side_effect = lambda col: MagicMock(
                to_series=lambda: MagicMock(
                    to_list=lambda: [150, 155, 160, 165, 170, 175, 180, 185, 190, 195]
                )
            )
            mock_lf.collect.return_value = mock_df

            tools = RunnerTools(storage=mock_storage)

            # Mock analytics.analyze_hr_drift
            tools.analytics.analyze_hr_drift = MagicMock(return_value={"drift": 0.5})

            result = tools.get_hr_drift_analysis()

            assert "drift" in result

    def test_get_training_load(self):
        """测试获取训练负荷"""
        with patch("src.core.storage.StorageManager") as MockStorage:
            mock_storage = MagicMock()
            MockStorage.return_value = mock_storage

            tools = RunnerTools(storage=mock_storage)
            tools.analytics.get_training_load = MagicMock(
                return_value={"atl": 50, "ctl": 60, "tsb": 10}
            )

            result = tools.get_training_load(days=42)

            assert isinstance(result, dict)
            assert "atl" in result

    def test_query_by_date_range_invalid_format(self):
        """测试按日期范围查询无效格式"""
        with patch("src.core.storage.StorageManager") as MockStorage:
            mock_storage = MagicMock()
            MockStorage.return_value = mock_storage

            tools = RunnerTools(storage=mock_storage)

            result = tools.query_by_date_range("invalid", "invalid")

            assert len(result) == 1
            assert "error" in result[0]

    def test_query_by_date_range_valid(self):
        """测试按日期范围查询有效"""
        with patch("src.core.storage.StorageManager") as MockStorage:
            mock_storage = MagicMock()
            MockStorage.return_value = mock_storage

            mock_lf = MagicMock()
            mock_storage.read_parquet.return_value = mock_lf
            mock_lf.filter.return_value.select.return_value.sort.return_value.collect.return_value.iter_rows.return_value = (
                []
            )

            tools = RunnerTools(storage=mock_storage)

            result = tools.query_by_date_range("2024-01-01", "2024-12-31")

            assert isinstance(result, list)

    def test_query_by_date_range_with_data(self):
        """测试按日期范围查询有数据"""
        with patch("src.core.storage.StorageManager") as MockStorage:
            mock_storage = MagicMock()
            MockStorage.return_value = mock_storage

            mock_lf = MagicMock()
            mock_storage.read_parquet.return_value = mock_lf
            # 模拟 Schema 对象，len() 返回列数
            mock_schema = MagicMock()
            mock_schema.__len__ = MagicMock(return_value=3)  # 3 列
            mock_lf.collect_schema.return_value = mock_schema
            
            # 模拟 group_by().agg().filter().sort().collect() 链式调用
            mock_grouped = MagicMock()
            mock_lf.group_by.return_value = mock_grouped
            
            mock_agged = MagicMock()
            mock_grouped.agg.return_value = mock_agged
            
            mock_filtered = MagicMock()
            mock_agged.filter.return_value = mock_filtered
            
            mock_sorted = MagicMock()
            mock_filtered.sort.return_value = mock_sorted
            
            mock_df = MagicMock()
            mock_df.is_empty.return_value = False
            mock_df.iter_rows.return_value = [
                {
                    "session_start": datetime(2024, 1, 1, 10, 0, 0),
                    "distance": 5000,
                    "duration": 1200,
                    "avg_hr": 150,
                }
            ]
            mock_sorted.collect.return_value = mock_df

            tools = RunnerTools(storage=mock_storage)

            result = tools.query_by_date_range("2024-01-01", "2024-12-31")

            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]["distance"] == 5.0

    def test_query_by_distance_min_only(self):
        """测试按距离查询仅最小值"""
        with patch("src.core.storage.StorageManager") as MockStorage:
            mock_storage = MagicMock()
            MockStorage.return_value = mock_storage

            mock_lf = MagicMock()
            mock_storage.read_parquet.return_value = mock_lf
            mock_lf.filter.return_value.select.return_value.sort.return_value.collect.return_value.iter_rows.return_value = (
                []
            )

            tools = RunnerTools(storage=mock_storage)

            result = tools.query_by_distance(min_distance=5.0)

            assert isinstance(result, list)

    def test_query_by_distance_with_max(self):
        """测试按距离查询有最大值"""
        with patch("src.core.storage.StorageManager") as MockStorage:
            mock_storage = MagicMock()
            MockStorage.return_value = mock_storage

            mock_lf = MagicMock()
            mock_storage.read_parquet.return_value = mock_lf
            mock_lf.filter.return_value.select.return_value.sort.return_value.collect.return_value.iter_rows.return_value = (
                []
            )

            tools = RunnerTools(storage=mock_storage)

            result = tools.query_by_distance(min_distance=5.0, max_distance=10.0)

            assert isinstance(result, list)

    def test_query_by_distance_with_data(self):
        """测试按距离查询有数据"""
        with patch("src.core.storage.StorageManager") as MockStorage:
            mock_storage = MagicMock()
            MockStorage.return_value = mock_storage

            mock_lf = MagicMock()
            mock_storage.read_parquet.return_value = mock_lf
            # 模拟 Schema 对象，len() 返回列数
            mock_schema = MagicMock()
            mock_schema.__len__ = MagicMock(return_value=3)  # 3 列
            mock_lf.collect_schema.return_value = mock_schema
            
            # 模拟 filter().group_by().agg().sort().collect() 链式调用
            mock_filtered = MagicMock()
            mock_lf.filter.return_value = mock_filtered
            
            mock_grouped = MagicMock()
            mock_filtered.group_by.return_value = mock_grouped
            
            mock_agged = MagicMock()
            mock_grouped.agg.return_value = mock_agged
            
            mock_sorted = MagicMock()
            mock_agged.sort.return_value = mock_sorted
            
            mock_df = MagicMock()
            mock_df.is_empty.return_value = False
            mock_df.iter_rows.return_value = [
                {
                    "session_start": datetime(2024, 1, 1, 10, 0, 0),
                    "distance": 5000,
                    "duration": 1200,
                    "avg_hr": 150,
                }
            ]
            mock_sorted.collect.return_value = mock_df

            tools = RunnerTools(storage=mock_storage)

            result = tools.query_by_distance(min_distance=5.0, max_distance=10.0)

            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]["distance"] == 5.0

    def test_tool_descriptions(self):
        """测试工具描述"""
        assert len(TOOL_DESCRIPTIONS) > 0

        # 检查关键工具
        assert "get_running_stats" in TOOL_DESCRIPTIONS
        assert "get_recent_runs" in TOOL_DESCRIPTIONS
        assert "calculate_vdot_for_run" in TOOL_DESCRIPTIONS
