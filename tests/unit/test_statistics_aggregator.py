# StatisticsAggregator 单元测试
# 测试统计聚合器功能

from datetime import datetime, timedelta
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import polars as pl
import pytest

from src.core.statistics_aggregator import StatisticsAggregator


@pytest.fixture
def mock_storage() -> MagicMock:
    """创建模拟 StorageManager"""
    return MagicMock()


@pytest.fixture
def stats_aggregator(mock_storage: MagicMock) -> StatisticsAggregator:
    """创建 StatisticsAggregator 实例"""
    return StatisticsAggregator(mock_storage)


class TestStatisticsAggregator:
    """StatisticsAggregator 测试类"""

    def test_get_running_summary_empty_storage(
        self, stats_aggregator: StatisticsAggregator, mock_storage: MagicMock
    ) -> None:
        """测试空存储返回空 DataFrame"""
        mock_storage.read_parquet.return_value = pl.LazyFrame()

        result = stats_aggregator.get_running_summary()

        assert result.is_empty()
        mock_storage.read_parquet.assert_called_once()

    def test_get_running_summary_success(
        self, stats_aggregator: StatisticsAggregator, mock_storage: MagicMock
    ) -> None:
        """测试成功获取跑步摘要"""
        now = datetime.now()
        df = pl.DataFrame(
            {
                "timestamp": [now, now, now + timedelta(hours=2)],
                "session_start_time": [now, now, now + timedelta(hours=2)],
                "session_total_distance": [5000.0, 5000.0, 3000.0],
                "session_total_timer_time": [1800.0, 1800.0, 1200.0],
                "session_avg_heart_rate": [150.0, 150.0, 145.0],
            }
        )
        mock_storage.read_parquet.return_value = df.lazy()

        result = stats_aggregator.get_running_summary()

        assert not result.is_empty()
        assert result["total_runs"][0] == 2
        assert result["total_distance"][0] == 8000.0
        assert result["total_timer_time"][0] == 3000.0

    def test_get_running_summary_with_date_filter(
        self, stats_aggregator: StatisticsAggregator, mock_storage: MagicMock
    ) -> None:
        """测试带日期过滤的跑步摘要"""
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

        start_date = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        end_date = (now - timedelta(days=3)).strftime("%Y-%m-%d")

        result = stats_aggregator.get_running_summary(start_date, end_date)

        assert not result.is_empty()
        assert result["total_runs"][0] == 1

    def test_format_duration_success(
        self, stats_aggregator: StatisticsAggregator
    ) -> None:
        """测试时长格式化"""
        assert stats_aggregator._format_duration(3661) == "01:01:01"
        assert stats_aggregator._format_duration(3600) == "01:00:00"
        assert stats_aggregator._format_duration(60) == "00:01:00"
        assert stats_aggregator._format_duration(0) == "00:00:00"

    def test_format_pace_success(self, stats_aggregator: StatisticsAggregator) -> None:
        """测试配速格式化"""
        assert stats_aggregator._format_pace(300) == "5'00\""
        assert stats_aggregator._format_pace(360) == "6'00\""
        assert stats_aggregator._format_pace(0) == "0'00\""
        assert stats_aggregator._format_pace(-10) == "0'00\""

    def test_get_running_stats_empty_storage(
        self, stats_aggregator: StatisticsAggregator, mock_storage: MagicMock
    ) -> None:
        """测试空存储返回默认统计"""
        mock_storage.read_parquet.return_value = pl.LazyFrame()

        result = stats_aggregator.get_running_stats()

        assert result["total_runs"] == 0
        assert result["total_distance"] == 0.0
        assert result["total_duration"] == 0.0
        assert result["avg_heart_rate"] == 0.0

    def test_get_running_stats_success(
        self, stats_aggregator: StatisticsAggregator, mock_storage: MagicMock
    ) -> None:
        """测试成功获取统计数据"""
        now = datetime.now()
        df = pl.DataFrame(
            {
                "timestamp": [now, now, now + timedelta(hours=2)],
                "session_start_time": [now, now, now + timedelta(hours=2)],
                "session_total_distance": [5000.0, 5000.0, 3000.0],
                "session_total_timer_time": [1800.0, 1800.0, 1200.0],
                "session_avg_heart_rate": [150.0, 150.0, 145.0],
            }
        )
        mock_storage.read_parquet.return_value = df.lazy()

        result = stats_aggregator.get_running_stats()

        assert result["total_runs"] == 2
        assert result["total_distance"] == 8.0
        assert result["total_duration"] == round(3000.0 / 3600, 2)
        assert "avg_pace" in result

    def test_get_running_stats_with_year(
        self, stats_aggregator: StatisticsAggregator, mock_storage: MagicMock
    ) -> None:
        """测试按年份获取统计数据"""
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

        result = stats_aggregator.get_running_stats(year=2026)

        assert result["total_runs"] == 1
        mock_storage.read_parquet.assert_called_once_with([2026])

    def test_calculate_avg_pace_from_values_success(
        self, stats_aggregator: StatisticsAggregator
    ) -> None:
        """测试根据距离和时长计算平均配速"""
        assert stats_aggregator._calculate_avg_pace_from_values(5000, 1500) == "5:00"
        assert stats_aggregator._calculate_avg_pace_from_values(10000, 3600) == "6:00"
        assert stats_aggregator._calculate_avg_pace_from_values(0, 100) == "0:00"

    def test_calculate_avg_pace_success(
        self, stats_aggregator: StatisticsAggregator
    ) -> None:
        """测试从 DataFrame 计算平均配速"""
        df = pl.DataFrame(
            {
                "distance": [5000.0, 3000.0],
                "duration": [1500.0, 900.0],
            }
        )

        result = stats_aggregator._calculate_avg_pace(df)

        assert result == "5:00"

    def test_calculate_avg_pace_empty_df(
        self, stats_aggregator: StatisticsAggregator
    ) -> None:
        """测试空 DataFrame 计算配速"""
        df = pl.DataFrame({"distance": [], "duration": []})

        result = stats_aggregator._calculate_avg_pace(df)

        assert result == "0:00"

    def test_get_pace_distribution_empty_storage(
        self, stats_aggregator: StatisticsAggregator, mock_storage: MagicMock
    ) -> None:
        """测试空存储返回空配速分布"""
        mock_storage.read_parquet.return_value = pl.LazyFrame()

        result = stats_aggregator.get_pace_distribution()

        assert result["zones"] == {}
        assert result["trend"] == []
        assert "message" in result

    def test_get_pace_distribution_success(
        self, stats_aggregator: StatisticsAggregator, mock_storage: MagicMock
    ) -> None:
        """测试成功获取配速分布"""
        now = datetime.now()
        df = pl.DataFrame(
            {
                "timestamp": [now, now, now, now],
                "session_start_time": [now, now, now, now],
                "session_total_distance": [5000.0, 5000.0, 5000.0, 5000.0],
                "session_total_timer_time": [1500.0, 1800.0, 2100.0, 2400.0],
            }
        )
        mock_storage.read_parquet.return_value = df.lazy()

        result = stats_aggregator.get_pace_distribution()

        assert "zones" in result
        assert "trend" in result
        assert "total_count" in result
        assert result["total_count"] == 4

    def test_get_pace_distribution_with_year(
        self, stats_aggregator: StatisticsAggregator, mock_storage: MagicMock
    ) -> None:
        """测试按年份获取配速分布"""
        now = datetime.now()
        df = pl.DataFrame(
            {
                "timestamp": [now],
                "session_start_time": [now],
                "session_total_distance": [5000.0],
                "session_total_timer_time": [1800.0],
            }
        )
        mock_storage.read_parquet.return_value = df.lazy()

        result = stats_aggregator.get_pace_distribution(year=2026)

        assert "zones" in result
        mock_storage.read_parquet.assert_called_once_with([2026])

    def test_get_running_summary_runtime_error(
        self, stats_aggregator: StatisticsAggregator, mock_storage: MagicMock
    ) -> None:
        """测试获取跑步摘要时发生运行时错误"""
        mock_storage.read_parquet.side_effect = Exception("读取失败")

        with pytest.raises(RuntimeError, match="获取跑步摘要失败"):
            stats_aggregator.get_running_summary()

    def test_get_running_stats_runtime_error(
        self, stats_aggregator: StatisticsAggregator, mock_storage: MagicMock
    ) -> None:
        """测试获取统计数据时发生运行时错误"""
        mock_storage.read_parquet.side_effect = Exception("读取失败")

        with pytest.raises(RuntimeError, match="获取统计数据失败"):
            stats_aggregator.get_running_stats()

    def test_get_pace_distribution_runtime_error(
        self, stats_aggregator: StatisticsAggregator, mock_storage: MagicMock
    ) -> None:
        """测试获取配速分布时发生运行时错误"""
        mock_storage.read_parquet.side_effect = Exception("读取失败")

        with pytest.raises(RuntimeError, match="配速分布分析失败"):
            stats_aggregator.get_pace_distribution()

    def test_get_running_stats_with_null_heart_rate(
        self, stats_aggregator: StatisticsAggregator, mock_storage: MagicMock
    ) -> None:
        """测试心率数据为空时的统计"""
        now = datetime.now()
        df = pl.DataFrame(
            {
                "timestamp": [now, now],
                "session_start_time": [now, now],
                "session_total_distance": [5000.0, 5000.0],
                "session_total_timer_time": [1800.0, 1800.0],
                "session_avg_heart_rate": [None, None],
            }
        )
        mock_storage.read_parquet.return_value = df.lazy()

        result = stats_aggregator.get_running_stats()

        assert result["avg_heart_rate"] == 0.0

    def test_get_pace_distribution_with_zero_distance(
        self, stats_aggregator: StatisticsAggregator, mock_storage: MagicMock
    ) -> None:
        """测试距离为0时的配速分布"""
        now = datetime.now()
        df = pl.DataFrame(
            {
                "timestamp": [now, now],
                "session_start_time": [now, now],
                "session_total_distance": [0.0, 5000.0],
                "session_total_timer_time": [1800.0, 1800.0],
            }
        )
        mock_storage.read_parquet.return_value = df.lazy()

        result = stats_aggregator.get_pace_distribution()

        assert "zones" in result
        assert result["total_count"] == 1
