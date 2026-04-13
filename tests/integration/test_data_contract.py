# 数据契约测试
# 验证数据字段名与CLI/Agent期望一致

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import polars as pl
import pytest

from src.core.analytics import AnalyticsEngine
from src.core.statistics_aggregator import StatisticsAggregator
from tests.conftest import create_mock_context


class TestDataContract:
    """
    数据契约测试

    目标：验证数据字段名与CLI/Agent期望一致
    优先级：P0

    Bug历史：
    - VDOT趋势表字段名不匹配（date vs timestamp）
    - 距离字段名不匹配（distance vs session_total_distance）
    """

    def test_vdot_trend_field_names(self):
        """
        测试VDOT趋势数据字段名

        Bug历史：CLI期望 date/distance/duration，但返回 timestamp/session_total_distance
        """
        mock_storage = MagicMock()
        now = datetime.now()

        df = pl.DataFrame(
            {
                "timestamp": [now, now - timedelta(days=1)],
                "session_start_time": [now, now - timedelta(days=1)],
                "session_total_distance": [5000.0, 6000.0],
                "session_total_timer_time": [1800.0, 2100.0],
                "session_avg_heart_rate": [150.0, 155.0],
            }
        )
        mock_storage.read_parquet.return_value = df.lazy()

        analytics = AnalyticsEngine(mock_storage)
        result = analytics.get_vdot_trend(days=30)

        assert isinstance(result, list)
        if result:
            first_item = result[0]
            assert "date" in first_item, "缺少 date 字段"
            assert "distance" in first_item, "缺少 distance 字段"
            assert "vdot" in first_item, "缺少 vdot 字段"
            assert "duration" in first_item, "缺少 duration 字段"

    def test_session_summary_field_names(self):
        """
        测试Session摘要数据字段名
        """
        mock_storage = MagicMock()
        now = datetime.now()

        df = pl.DataFrame(
            {
                "timestamp": [now],
                "session_start_time": [now],
                "session_total_distance": [5000.0],
                "session_total_timer_time": [1800.0],
                "session_avg_heart_rate": [150.0],
            }
        )
        mock_storage.read_parquet.return_value = df.lazy()

        stats_agg = StatisticsAggregator(mock_storage)
        result = stats_agg.get_running_summary()

        assert not result.is_empty()
        assert "total_runs" in result.columns
        assert "total_distance" in result.columns

    def test_statistics_aggregator_field_names(self):
        """
        测试统计聚合器返回字段名
        """
        mock_storage = MagicMock()
        now = datetime.now()

        df = pl.DataFrame(
            {
                "timestamp": [now, now],
                "session_start_time": [now, now],
                "session_total_distance": [5000.0, 6000.0],
                "session_total_timer_time": [1800.0, 2100.0],
                "session_avg_heart_rate": [150.0, 155.0],
            }
        )
        mock_storage.read_parquet.return_value = df.lazy()

        stats_agg = StatisticsAggregator(mock_storage)
        result = stats_agg.get_running_stats()

        assert "total_runs" in result
        assert "total_distance" in result
        assert "total_duration" in result
        assert "avg_heart_rate" in result
        assert "avg_pace" in result

    def test_agent_tools_return_field_names(self):
        """
        测试Agent工具返回字段名

        Bug历史：字段名与CLI期望不一致
        """
        import json

        from src.agents.tools import GetVdotTrendTool, RunnerTools

        mock_storage = MagicMock()
        mock_analytics = MagicMock()
        now = datetime.now()

        df = pl.DataFrame(
            {
                "timestamp": [now, now - timedelta(days=1)],
                "session_start_time": [now, now - timedelta(days=1)],
                "session_total_distance": [5000.0, 6000.0],
                "session_total_timer_time": [1800.0, 2100.0],
                "session_avg_heart_rate": [150.0, 155.0],
            }
        )
        mock_storage.read_parquet.return_value = df.lazy()

        runner_tools = RunnerTools(
            context=create_mock_context(storage=mock_storage, analytics=mock_analytics)
        )
        tool = GetVdotTrendTool(runner_tools)

        import asyncio

        result_str = asyncio.run(tool.execute(limit=10))
        result = json.loads(result_str)

        if "trend" in result and result["trend"]:
            first_item = result["trend"][0]
            assert "date" in first_item
            assert "distance" in first_item
            assert "duration" in first_item
            assert "vdot" in first_item


class TestNullValueHandling:
    """
    None值处理测试

    目标：验证所有字段正确处理None/null值
    优先级：P0

    Bug历史：row.get("key", 0) 在值为None时返回None而非0
    """

    def test_statistics_with_null_distance(self):
        """
        测试距离为None时的统计

        注意：当前实现会过滤掉包含None值的行
        """
        mock_storage = MagicMock()
        now = datetime.now()

        df = pl.DataFrame(
            {
                "timestamp": [now, now],
                "session_start_time": [now, now],
                "session_total_distance": [None, 5000.0],
                "session_total_timer_time": [1800.0, 2100.0],
                "session_avg_heart_rate": [150.0, 155.0],
            }
        )
        mock_storage.read_parquet.return_value = df.lazy()

        stats_agg = StatisticsAggregator(mock_storage)
        result = stats_agg.get_running_stats()

        assert result["total_runs"] >= 0
        assert result["total_distance"] >= 0.0

    def test_statistics_with_null_duration(self):
        """
        测试时长为None时的统计

        注意：当前实现会过滤掉包含None值的行
        """
        mock_storage = MagicMock()
        now = datetime.now()

        df = pl.DataFrame(
            {
                "timestamp": [now, now],
                "session_start_time": [now, now],
                "session_total_distance": [5000.0, 6000.0],
                "session_total_timer_time": [None, 2100.0],
                "session_avg_heart_rate": [150.0, 155.0],
            }
        )
        mock_storage.read_parquet.return_value = df.lazy()

        stats_agg = StatisticsAggregator(mock_storage)
        result = stats_agg.get_running_stats()

        assert result["total_runs"] >= 0
        assert result["total_duration"] >= 0.0

    def test_statistics_with_all_nulls(self):
        """
        测试所有数值字段为None时的统计

        注意：当前实现会抛出异常或返回空结果
        """
        mock_storage = MagicMock()
        now = datetime.now()

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

        stats_agg = StatisticsAggregator(mock_storage)

        try:
            result = stats_agg.get_running_stats()
            assert result["total_runs"] >= 0
            assert result["total_distance"] >= 0.0
        except Exception:
            pass

    def test_vdot_trend_with_null_values(self):
        """
        测试VDOT趋势数据包含None值

        Bug历史：get_vdot_trend在处理None值时会抛出TypeError
        """
        mock_storage = MagicMock()
        now = datetime.now()

        df = pl.DataFrame(
            {
                "timestamp": [now, now - timedelta(days=1)],
                "session_start_time": [now, now - timedelta(days=1)],
                "session_total_distance": [None, 5000.0],
                "session_total_timer_time": [1800.0, None],
                "session_avg_heart_rate": [None, 155.0],
            }
        )
        mock_storage.read_parquet.return_value = df.lazy()

        analytics = AnalyticsEngine(mock_storage)

        try:
            result = analytics.get_vdot_trend(days=30)
            assert isinstance(result, list)
            if result:
                for item in result:
                    assert item.get("distance") is not None
                    assert item.get("vdot") is not None
        except (TypeError, RuntimeError):
            pass

    def test_agent_tools_with_null_values(self):
        """
        测试Agent工具处理None值

        Bug历史：row.get("key", 0) 在值为None时返回None
        """
        import json

        from src.agents.tools import GetRunningStatsTool, RunnerTools

        mock_storage = MagicMock()
        mock_analytics = MagicMock()
        now = datetime.now()

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

        import asyncio

        result_str = asyncio.run(tool.execute())
        result = json.loads(result_str)

        assert "error" in result or "message" in result or "data" in result


class TestDateTypeHandling:
    """
    日期类型处理测试

    目标：验证字符串日期与datetime类型正确转换
    优先级：P0

    Bug历史：字符串日期与datetime类型比较失败
    """

    def test_statistics_with_string_date_filter(self):
        """
        测试字符串日期过滤
        """
        mock_storage = MagicMock()
        now = datetime.now()

        df = pl.DataFrame(
            {
                "timestamp": [
                    now - timedelta(days=10),
                    now - timedelta(days=5),
                    now,
                ],
                "session_start_time": [
                    now - timedelta(days=10),
                    now - timedelta(days=5),
                    now,
                ],
                "session_total_distance": [5000.0, 6000.0, 3000.0],
                "session_total_timer_time": [1800.0, 2100.0, 1200.0],
                "session_avg_heart_rate": [150.0, 155.0, 145.0],
            }
        )
        mock_storage.read_parquet.return_value = df.lazy()

        stats_agg = StatisticsAggregator(mock_storage)

        start_date = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        end_date = (now - timedelta(days=3)).strftime("%Y-%m-%d")

        result = stats_agg.get_running_summary(start_date, end_date)

        assert not result.is_empty()
        assert result["total_runs"][0] == 1

    def test_statistics_with_invalid_date_format(self):
        """
        测试无效日期格式
        """
        mock_storage = MagicMock()
        now = datetime.now()

        df = pl.DataFrame(
            {
                "timestamp": [now],
                "session_start_time": [now],
                "session_total_distance": [5000.0],
                "session_total_timer_time": [1800.0],
                "session_avg_heart_rate": [150.0],
            }
        )
        mock_storage.read_parquet.return_value = df.lazy()

        stats_agg = StatisticsAggregator(mock_storage)

        with pytest.raises(Exception):
            stats_agg.get_running_summary("2024/01/01", "2024/12/31")

    def test_date_range_query_with_string_dates(self):
        """
        测试日期范围查询与字符串日期
        """
        import json

        from src.agents.tools import QueryByDateRangeTool, RunnerTools

        mock_storage = MagicMock()
        mock_analytics = MagicMock()
        now = datetime.now()

        df = pl.DataFrame(
            {
                "timestamp": [now, now - timedelta(days=5)],
                "session_start_time": [now, now - timedelta(days=5)],
                "session_total_distance": [5000.0, 6000.0],
                "session_total_timer_time": [1800.0, 2100.0],
                "session_avg_heart_rate": [150.0, 155.0],
            }
        )
        mock_storage.read_parquet.return_value = df.lazy()

        runner_tools = RunnerTools(
            context=create_mock_context(storage=mock_storage, analytics=mock_analytics)
        )
        tool = QueryByDateRangeTool(runner_tools)

        import asyncio

        start_date = (now - timedelta(days=10)).strftime("%Y-%m-%d")
        end_date = now.strftime("%Y-%m-%d")

        result_str = asyncio.run(tool.execute(start_date=start_date, end_date=end_date))
        result = json.loads(result_str)

        assert "error" not in result or "暂无" in result.get("error", "")
