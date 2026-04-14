# StatisticsAggregator单元测试
# 测试统计数据聚合器的核心功能

from datetime import datetime, timedelta
from unittest.mock import Mock

import polars as pl
import pytest

from src.core.statistics_aggregator import StatisticsAggregator


class TestGetRunningSummary:
    """get_running_summary方法测试"""

    @pytest.fixture
    def mock_storage(self):
        """创建mock StorageManager"""
        mock_storage = Mock()
        now = datetime.now()
        mock_storage.read_parquet.return_value = pl.LazyFrame(
            {
                "timestamp": [now - timedelta(days=i) for i in range(10)],
                "session_start_time": [f"session_{i}" for i in range(10)],
                "session_total_distance": [5000.0] * 10,
                "session_total_timer_time": [1800.0] * 10,
                "session_avg_heart_rate": [150.0] * 10,
            }
        )
        return mock_storage

    @pytest.fixture
    def aggregator(self, mock_storage):
        """创建StatisticsAggregator实例"""
        return StatisticsAggregator(mock_storage)

    def test_get_running_summary_basic(self, aggregator):
        """测试基本跑步摘要"""
        result = aggregator.get_running_summary()

        assert result.height == 1
        assert result["total_runs"][0] == 10
        assert result["total_distance"][0] == 50000.0
        assert result["total_timer_time"][0] == 18000.0

    def test_get_running_summary_with_date_range(self, aggregator, mock_storage):
        """测试日期范围过滤"""
        now = datetime.now()
        mock_storage.read_parquet.return_value = pl.LazyFrame(
            {
                "timestamp": [
                    now - timedelta(days=30),
                    now - timedelta(days=20),
                    now - timedelta(days=10),
                    now,
                ],
                "session_start_time": ["s1", "s2", "s3", "s4"],
                "session_total_distance": [5000.0] * 4,
                "session_total_timer_time": [1800.0] * 4,
                "session_avg_heart_rate": [150.0] * 4,
            }
        )

        start_date = (now - timedelta(days=15)).strftime("%Y-%m-%d")
        end_date = (now - timedelta(days=5)).strftime("%Y-%m-%d")

        result = aggregator.get_running_summary(
            start_date=start_date, end_date=end_date
        )

        assert result.height == 1
        assert result["total_runs"][0] == 1

    def test_get_running_summary_empty(self):
        """测试空数据"""
        mock_storage = Mock()
        mock_storage.read_parquet.return_value = pl.LazyFrame()
        aggregator = StatisticsAggregator(mock_storage)

        result = aggregator.get_running_summary()

        assert result.height == 0

    def test_get_running_summary_error(self):
        """测试错误处理"""
        mock_storage = Mock()
        mock_storage.read_parquet.side_effect = Exception("读取失败")
        aggregator = StatisticsAggregator(mock_storage)

        with pytest.raises(RuntimeError, match="获取跑步摘要失败"):
            aggregator.get_running_summary()


class TestGetRunningStats:
    """get_running_stats方法测试"""

    @pytest.fixture
    def mock_storage(self):
        """创建mock StorageManager"""
        mock_storage = Mock()
        now = datetime.now()
        mock_storage.read_parquet.return_value = pl.LazyFrame(
            {
                "session_start_time": [f"session_{i}" for i in range(10)],
                "session_total_distance": [5000.0] * 10,
                "session_total_timer_time": [1800.0] * 10,
                "session_avg_heart_rate": [150.0] * 10,
            }
        )
        return mock_storage

    @pytest.fixture
    def aggregator(self, mock_storage):
        """创建StatisticsAggregator实例"""
        return StatisticsAggregator(mock_storage)

    def test_get_running_stats_basic(self, aggregator):
        """测试基本统计数据"""
        stats = aggregator.get_running_stats()

        assert stats.total_runs == 10
        assert stats.total_distance == 50.0
        assert stats.total_duration == 5.0
        assert stats.avg_heart_rate == 150.0

    def test_get_running_stats_with_year(self, aggregator, mock_storage):
        """测试指定年份统计"""
        stats = aggregator.get_running_stats(year=2024)

        mock_storage.read_parquet.assert_called_once()
        assert stats.total_runs == 10

    def test_get_running_stats_empty(self):
        """测试空数据"""
        mock_storage = Mock()
        mock_storage.read_parquet.return_value = pl.LazyFrame()
        aggregator = StatisticsAggregator(mock_storage)

        stats = aggregator.get_running_stats()

        assert stats.total_runs == 0
        assert stats.total_distance == 0.0
        assert stats.total_duration == 0.0

    def test_get_running_stats_error(self):
        """测试错误处理"""
        mock_storage = Mock()
        mock_storage.read_parquet.side_effect = Exception("读取失败")
        aggregator = StatisticsAggregator(mock_storage)

        with pytest.raises(RuntimeError, match="获取统计数据失败"):
            aggregator.get_running_stats()


class TestGetPaceDistribution:
    """get_pace_distribution方法测试"""

    @pytest.fixture
    def mock_storage(self):
        """创建mock StorageManager"""
        mock_storage = Mock()
        return mock_storage

    @pytest.fixture
    def aggregator(self, mock_storage):
        """创建StatisticsAggregator实例"""
        return StatisticsAggregator(mock_storage)

    def test_get_pace_distribution_basic(self, aggregator, mock_storage):
        """测试基本配速分布"""
        mock_storage.read_parquet.return_value = pl.LazyFrame(
            {
                "session_total_distance": [5000.0] * 10,
                "session_total_timer_time": [1500.0] * 10,
            }
        )

        result = aggregator.get_pace_distribution()

        assert hasattr(result, "zones")
        assert hasattr(result, "trend")
        assert hasattr(result, "total_count")

    def test_get_pace_distribution_with_year(self, aggregator, mock_storage):
        """测试指定年份配速分布"""
        mock_storage.read_parquet.return_value = pl.LazyFrame(
            {
                "session_total_distance": [5000.0] * 10,
                "session_total_timer_time": [1500.0] * 10,
            }
        )

        result = aggregator.get_pace_distribution(year=2024)

        mock_storage.read_parquet.assert_called_once()
        assert hasattr(result, "zones")

    def test_get_pace_distribution_empty(self):
        """测试空数据"""
        mock_storage = Mock()
        mock_storage.read_parquet.return_value = pl.LazyFrame()
        aggregator = StatisticsAggregator(mock_storage)

        result = aggregator.get_pace_distribution()

        assert result.zones == {}
        assert hasattr(result, "message")

    def test_get_pace_distribution_error(self):
        """测试错误处理"""
        mock_storage = Mock()
        mock_storage.read_parquet.side_effect = Exception("读取失败")
        aggregator = StatisticsAggregator(mock_storage)

        with pytest.raises(RuntimeError, match="配速分布分析失败"):
            aggregator.get_pace_distribution()


class TestFormatDuration:
    """_format_duration方法测试"""

    @pytest.fixture
    def aggregator(self):
        """创建StatisticsAggregator实例"""
        mock_storage = Mock()
        return StatisticsAggregator(mock_storage)

    def test_format_duration_hours(self, aggregator):
        """测试小时格式化"""
        assert aggregator._format_duration(3661.0) == "01:01:01"
        assert aggregator._format_duration(7200.0) == "02:00:00"

    def test_format_duration_minutes(self, aggregator):
        """测试分钟格式化"""
        assert aggregator._format_duration(1800.0) == "00:30:00"
        assert aggregator._format_duration(900.0) == "00:15:00"

    def test_format_duration_zero(self, aggregator):
        """测试零时长"""
        assert aggregator._format_duration(0.0) == "00:00:00"

    def test_format_duration_error(self, aggregator):
        """测试错误处理"""
        assert aggregator._format_duration(None) == "00:00:00"


class TestFormatPace:
    """_format_pace方法测试"""

    @pytest.fixture
    def aggregator(self):
        """创建StatisticsAggregator实例"""
        mock_storage = Mock()
        return StatisticsAggregator(mock_storage)

    def test_format_pace_basic(self, aggregator):
        """测试基本配速格式化"""
        assert aggregator._format_pace(300.0) == "5'00\""
        assert aggregator._format_pace(360.0) == "6'00\""

    def test_format_pace_with_seconds(self, aggregator):
        """测试带秒的配速格式化"""
        assert aggregator._format_pace(330.0) == "5'30\""
        assert aggregator._format_pace(345.0) == "5'45\""

    def test_format_pace_zero(self, aggregator):
        """测试零配速"""
        assert aggregator._format_pace(0.0) == "0'00\""

    def test_format_pace_none(self, aggregator):
        """测试None配速"""
        assert aggregator._format_pace(None) == "0'00\""

    def test_format_pace_negative(self, aggregator):
        """测试负配速"""
        assert aggregator._format_pace(-10.0) == "0'00\""


class TestCalculateAvgPaceFromValues:
    """_calculate_avg_pace_from_values方法测试"""

    @pytest.fixture
    def aggregator(self):
        """创建StatisticsAggregator实例"""
        mock_storage = Mock()
        return StatisticsAggregator(mock_storage)

    def test_calculate_avg_pace_basic(self, aggregator):
        """测试基本平均配速计算"""
        pace = aggregator._calculate_avg_pace_from_values(5000.0, 1500.0)

        assert pace == "5:00"

    def test_calculate_avg_pace_with_seconds(self, aggregator):
        """测试带秒的平均配速"""
        pace = aggregator._calculate_avg_pace_from_values(5000.0, 1650.0)

        assert pace == "5:30"

    def test_calculate_avg_pace_zero_distance(self, aggregator):
        """测试零距离"""
        pace = aggregator._calculate_avg_pace_from_values(0.0, 1500.0)

        assert pace == "0:00"

    def test_calculate_avg_pace_error(self, aggregator):
        """测试错误处理"""
        pace = aggregator._calculate_avg_pace_from_values(None, None)

        assert pace == "0:00"


class TestCalculateAvgPace:
    """_calculate_avg_pace方法测试"""

    @pytest.fixture
    def aggregator(self):
        """创建StatisticsAggregator实例"""
        mock_storage = Mock()
        return StatisticsAggregator(mock_storage)

    def test_calculate_avg_pace_from_df(self, aggregator):
        """测试从DataFrame计算平均配速"""
        df = pl.DataFrame({"distance": [5000.0, 5000.0], "duration": [1500.0, 1500.0]})

        pace = aggregator._calculate_avg_pace(df)

        assert pace == "5:00"

    def test_calculate_avg_pace_empty_df(self, aggregator):
        """测试空DataFrame"""
        df = pl.DataFrame({"distance": [], "duration": []})

        pace = aggregator._calculate_avg_pace(df)

        assert pace == "0:00"

    def test_calculate_avg_pace_zero_distance(self, aggregator):
        """测试零距离"""
        df = pl.DataFrame({"distance": [0.0], "duration": [1500.0]})

        pace = aggregator._calculate_avg_pace(df)

        assert pace == "0:00"


class TestIntegration:
    """集成测试"""

    @pytest.fixture
    def mock_storage(self):
        """创建mock StorageManager"""
        mock_storage = Mock()
        now = datetime.now()
        mock_storage.read_parquet.return_value = pl.LazyFrame(
            {
                "timestamp": [now - timedelta(days=i) for i in range(30)],
                "session_start_time": [f"session_{i}" for i in range(30)],
                "session_total_distance": [5000.0] * 30,
                "session_total_timer_time": [1500.0] * 30,
                "session_avg_heart_rate": [150.0] * 30,
            }
        )
        return mock_storage

    @pytest.fixture
    def aggregator(self, mock_storage):
        """创建StatisticsAggregator实例"""
        return StatisticsAggregator(mock_storage)

    def test_full_statistics_workflow(self, aggregator):
        """测试完整统计流程"""
        summary = aggregator.get_running_summary()
        stats = aggregator.get_running_stats()
        pace_dist = aggregator.get_pace_distribution()

        assert summary.height == 1
        assert stats.total_runs == 30
        assert hasattr(pace_dist, "zones")

    def test_year_filtering(self, aggregator, mock_storage):
        """测试年份过滤"""
        stats_2024 = aggregator.get_running_stats(year=2024)
        pace_2024 = aggregator.get_pace_distribution(year=2024)

        assert stats_2024.total_runs == 30
        assert hasattr(pace_2024, "zones")
