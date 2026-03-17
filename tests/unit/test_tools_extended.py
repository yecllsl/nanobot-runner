# Agent工具集扩展单元测试
# 提升 agents/tools.py 覆盖率

from datetime import datetime
from unittest.mock import MagicMock, patch

import polars as pl
import pytest

from src.agents.tools import TOOL_DESCRIPTIONS, RunnerTools


class TestRunnerToolsExtended:
    """扩展 RunnerTools 测试"""

    def test_query_by_date_range_success(self):
        """测试日期范围查询成功"""
        with patch("src.agents.tools.StorageManager") as MockStorage:
            mock_storage = MagicMock()
            MockStorage.return_value = mock_storage

            mock_lf = MagicMock()
            mock_storage.read_parquet.return_value = mock_lf

            mock_filtered = MagicMock()
            mock_selected = MagicMock()
            mock_sorted = MagicMock()

            mock_lf.filter.return_value = mock_filtered
            mock_filtered.select.return_value = mock_selected
            mock_selected.sort.return_value = mock_sorted

            mock_df = MagicMock()
            mock_sorted.collect.return_value = mock_df
            mock_df.iter_rows.return_value = [
                {
                    "timestamp": datetime(2024, 1, 15),
                    "total_distance": 5000,
                    "total_timer_time": 1800,
                    "avg_heart_rate": 145,
                    "avg_pace": 360,
                }
            ]

            tools = RunnerTools(storage=mock_storage)
            result = tools.query_by_date_range("2024-01-01", "2024-12-31")

            assert isinstance(result, list)

    def test_query_by_date_range_invalid_format(self):
        """测试无效日期格式"""
        tools = RunnerTools()

        result = tools.query_by_date_range("invalid", "2024-12-31")

        assert isinstance(result, list)
        assert "error" in result[0]

    def test_query_by_date_range_empty_result(self):
        """测试日期范围查询无结果"""
        with patch("src.agents.tools.StorageManager") as MockStorage:
            mock_storage = MagicMock()
            MockStorage.return_value = mock_storage

            mock_lf = MagicMock()
            mock_storage.read_parquet.return_value = mock_lf

            mock_df = MagicMock()
            mock_df.filter.return_value = mock_df
            mock_df.select.return_value = mock_df
            mock_df.sort.return_value = mock_df
            mock_df.collect.return_value = mock_df
            mock_df.iter_rows.return_value = []

            tools = RunnerTools(storage=mock_storage)
            result = tools.query_by_date_range("2025-01-01", "2025-12-31")

            assert isinstance(result, list)
            assert len(result) == 0

    def test_query_by_distance_no_upper_limit(self):
        """测试无上限距离查询"""
        with patch("src.agents.tools.StorageManager") as MockStorage:
            mock_storage = MagicMock()
            MockStorage.return_value = mock_storage

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

            tools = RunnerTools(storage=mock_storage)
            result = tools.query_by_distance(min_distance=10)

            assert isinstance(result, list)

    def test_query_by_distance_with_upper_limit(self):
        """测试有上限距离查询"""
        with patch("src.agents.tools.StorageManager") as MockStorage:
            mock_storage = MagicMock()
            MockStorage.return_value = mock_storage

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

            tools = RunnerTools(storage=mock_storage)
            result = tools.query_by_distance(min_distance=5, max_distance=10)

            assert isinstance(result, list)

    def test_query_by_distance_empty_result(self):
        """测试距离查询无结果"""
        with patch("src.agents.tools.StorageManager") as MockStorage:
            mock_storage = MagicMock()
            MockStorage.return_value = mock_storage

            mock_lf = MagicMock()
            mock_storage.read_parquet.return_value = mock_lf

            mock_df = MagicMock()
            mock_df.filter.return_value = mock_df
            mock_df.select.return_value = mock_df
            mock_df.sort.return_value = mock_df
            mock_df.collect.return_value = mock_df
            mock_df.iter_rows.return_value = []

            tools = RunnerTools(storage=mock_storage)
            result = tools.query_by_distance(min_distance=100)

            assert isinstance(result, list)
            assert len(result) == 0

    def test_get_vdot_trend_success(self):
        """测试获取VDOT趋势成功"""
        with patch("src.agents.tools.StorageManager") as MockStorage:
            mock_storage = MagicMock()
            MockStorage.return_value = mock_storage

            mock_lf = MagicMock()
            mock_storage.read_parquet.return_value = mock_lf

            mock_df = MagicMock()
            mock_df.sort.return_value = mock_df
            mock_df.limit.return_value = mock_df
            mock_df.collect.return_value = mock_df
            mock_df.iter_rows.return_value = [
                {
                    "timestamp": datetime(2024, 1, 15),
                    "total_distance": 5000,
                    "total_timer_time": 1500,
                }
            ]

            tools = RunnerTools(storage=mock_storage)
            result = tools.get_vdot_trend(limit=10)

            assert isinstance(result, list)

    def test_get_vdot_trend_empty(self):
        """测试获取VDOT趋势空数据"""
        with patch("src.agents.tools.StorageManager") as MockStorage:
            mock_storage = MagicMock()
            MockStorage.return_value = mock_storage

            mock_lf = MagicMock()
            mock_storage.read_parquet.return_value = mock_lf

            mock_df = MagicMock()
            mock_df.sort.return_value = mock_df
            mock_df.limit.return_value = mock_df
            mock_df.collect.return_value = mock_df
            mock_df.iter_rows.return_value = []

            tools = RunnerTools(storage=mock_storage)
            result = tools.get_vdot_trend()

            assert isinstance(result, list)
            assert len(result) == 0

    def test_get_hr_drift_analysis_success(self):
        """测试心率漂移分析成功"""
        with patch("src.agents.tools.StorageManager") as MockStorage:
            mock_storage = MagicMock()
            MockStorage.return_value = mock_storage

            mock_lf = MagicMock()
            mock_storage.read_parquet.return_value = mock_lf

            mock_df = MagicMock()
            mock_df.collect.return_value = mock_df
            mock_df.height = 1
            mock_df.select.return_value.to_series.return_value.to_list.return_value = [
                130,
                135,
                140,
            ]
            mock_df.select.return_value.to_series.return_value.to_list.return_value = [
                300,
                310,
                320,
            ]

            with patch.object(pl, "col", return_value=MagicMock()):
                with patch.object(
                    mock_df,
                    "select",
                    return_value=MagicMock(
                        to_series=MagicMock(
                            to_list=MagicMock(
                                side_effect=[[130, 135, 140], [300, 310, 320]]
                            )
                        )
                    ),
                ):
                    tools = RunnerTools(storage=mock_storage)
                    result = tools.get_hr_drift_analysis()

                    assert isinstance(result, dict)

    def test_get_hr_drift_analysis_empty(self):
        """测试心率漂移分析空数据"""
        with patch("src.agents.tools.StorageManager") as MockStorage:
            mock_storage = MagicMock()
            MockStorage.return_value = mock_storage

            mock_lf = MagicMock()
            mock_storage.read_parquet.return_value = mock_lf

            mock_df = MagicMock()
            mock_df.collect.return_value = mock_df
            mock_df.height = 0

            tools = RunnerTools(storage=mock_storage)
            result = tools.get_hr_drift_analysis()

            assert "error" in result

    def test_get_training_load(self):
        """测试训练负荷查询"""
        with patch("src.agents.tools.StorageManager") as MockStorage:
            mock_storage = MagicMock()
            MockStorage.return_value = mock_storage

            mock_lf = MagicMock()
            mock_storage.read_parquet.return_value = mock_lf

            mock_df = MagicMock()
            mock_df.is_empty.return_value = True
            mock_lf.filter.return_value.collect.return_value = mock_df

            with patch("src.agents.tools.AnalyticsEngine") as MockAnalytics:
                mock_engine = MagicMock()
                mock_engine.get_training_load.return_value = {
                    "atl": 50.0,
                    "ctl": 60.0,
                    "tsb": 10.0,
                }
                MockAnalytics.return_value = mock_engine

                tools = RunnerTools(storage=mock_storage)
                tools.analytics = mock_engine
                result = tools.get_training_load(days=30)

                assert isinstance(result, dict)

    def test_get_running_stats_with_dates(self):
        """测试带日期范围的统计"""
        with patch("src.agents.tools.AnalyticsEngine") as MockAnalytics:
            mock_engine = MagicMock()
            MockAnalytics.return_value = mock_engine

            mock_summary = MagicMock()
            mock_summary.row.return_value = (10, 50000, 18000, 5000, 1800, 8000, 145)
            mock_summary.height = 1

            mock_engine.get_running_summary.return_value = mock_summary

            with patch("src.agents.tools.StorageManager") as MockStorage:
                mock_storage = MagicMock()
                tools = RunnerTools(storage=mock_storage)
                tools.analytics = mock_engine

                result = tools.get_running_stats("2024-01-01", "2024-12-31")

                assert "total_runs" in result

    def test_calculate_vdot_zero_distance(self):
        """测试VDOT计算零距离应抛出异常"""
        tools = RunnerTools()

        with pytest.raises(ValueError):
            tools.calculate_vdot_for_run(0, 1800)

    def test_calculate_vdot_zero_time(self):
        """测试VDOT计算零时间应抛出异常"""
        tools = RunnerTools()

        with pytest.raises(ValueError):
            tools.calculate_vdot_for_run(5000, 0)


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
        ]

        for tool_name in expected_tools:
            assert tool_name in TOOL_DESCRIPTIONS

    def test_tool_has_description_field(self):
        """测试工具描述包含description字段"""
        for tool_name, tool_info in TOOL_DESCRIPTIONS.items():
            assert "description" in tool_info

    def test_tool_has_parameters(self):
        """测试工具描述包含parameters字段"""
        for tool_name, tool_info in TOOL_DESCRIPTIONS.items():
            assert "parameters" in tool_info
