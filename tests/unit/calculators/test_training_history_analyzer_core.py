# TrainingHistoryAnalyzer单元测试
# 测试训练历史分析器的核心功能

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import polars as pl
import pytest

from src.core.calculators.training_history_analyzer import TrainingHistoryAnalyzer
from src.core.user_profile_manager import RunnerProfile


class TestAnalyzeRunningTimePreference:
    """跑步时间偏好分析测试"""

    @pytest.fixture
    def analyzer(self):
        """创建TrainingHistoryAnalyzer实例"""
        mock_storage = Mock()
        return TrainingHistoryAnalyzer(mock_storage)

    def test_morning_preference(self, analyzer):
        """测试晨跑偏好"""
        utc = UTC
        timestamps = pl.Series(
            [
                datetime(2024, 1, 1, 0, 0, tzinfo=utc),
                datetime(2024, 1, 2, 1, 0, tzinfo=utc),
                datetime(2024, 1, 3, 2, 0, tzinfo=utc),
            ]
        )

        result = analyzer.analyze_running_time_preference(timestamps)

        assert result == "morning"

    def test_afternoon_preference(self, analyzer):
        """测试下午跑偏好"""
        utc = UTC
        timestamps = pl.Series(
            [
                datetime(2024, 1, 1, 6, 0, tzinfo=utc),
                datetime(2024, 1, 2, 7, 0, tzinfo=utc),
                datetime(2024, 1, 3, 8, 0, tzinfo=utc),
            ]
        )

        result = analyzer.analyze_running_time_preference(timestamps)

        assert result == "afternoon"

    def test_evening_preference(self, analyzer):
        """测试夜跑偏好"""
        utc = UTC
        timestamps = pl.Series(
            [
                datetime(2024, 1, 1, 14, 0, tzinfo=utc),
                datetime(2024, 1, 2, 15, 0, tzinfo=utc),
                datetime(2024, 1, 3, 16, 0, tzinfo=utc),
            ]
        )

        result = analyzer.analyze_running_time_preference(timestamps)

        assert result == "evening"

    def test_empty_timestamps(self, analyzer):
        """测试空时间戳"""
        timestamps = pl.Series([], dtype=pl.Datetime)

        result = analyzer.analyze_running_time_preference(timestamps)

        assert result == "morning"


class TestCalculateConsistencyScore:
    """训练一致性评分测试"""

    @pytest.fixture
    def analyzer(self):
        """创建TrainingHistoryAnalyzer实例"""
        mock_storage = Mock()
        return TrainingHistoryAnalyzer(mock_storage)

    def test_empty_dataframe(self, analyzer):
        """测试空数据"""
        df = pl.DataFrame()
        score = analyzer.calculate_consistency_score(df, 30)

        assert score == 0.0

    def test_single_run(self, analyzer):
        """测试单次跑步"""
        df = pl.DataFrame({"timestamp": [datetime.now()]})
        score = analyzer.calculate_consistency_score(df, 30)

        assert 0 <= score <= 100

    def test_regular_training(self, analyzer):
        """测试规律训练"""
        now = datetime.now()
        timestamps = [now - timedelta(days=i) for i in range(10)]
        df = pl.DataFrame({"timestamp": timestamps})
        score = analyzer.calculate_consistency_score(df, 30)

        assert score > 0

    def test_high_frequency_training(self, analyzer):
        """测试高频训练"""
        now = datetime.now()
        timestamps = [now - timedelta(days=i * 0.5) for i in range(20)]
        df = pl.DataFrame({"timestamp": timestamps})
        score = analyzer.calculate_consistency_score(df, 30)

        assert score > 60


class TestCalculateRegularityScore:
    """规律性评分测试"""

    @pytest.fixture
    def analyzer(self):
        """创建TrainingHistoryAnalyzer实例"""
        mock_storage = Mock()
        return TrainingHistoryAnalyzer(mock_storage)

    def test_single_run(self, analyzer):
        """测试单次跑步"""
        df = pl.DataFrame({"timestamp": [datetime.now()]})
        score = analyzer._calculate_regularity_score(df, 1)

        assert score == 0.0

    def test_irregular_training(self, analyzer):
        """测试不规律训练"""
        now = datetime.now()
        timestamps = [
            now - timedelta(days=1),
            now - timedelta(days=5),
            now - timedelta(days=15),
        ]
        df = pl.DataFrame({"timestamp": timestamps})
        score = analyzer._calculate_regularity_score(df, 3)

        assert 0 <= score <= 40

    def test_regular_training(self, analyzer):
        """测试规律训练"""
        now = datetime.now()
        timestamps = [now - timedelta(days=i) for i in range(10)]
        df = pl.DataFrame({"timestamp": timestamps})
        score = analyzer._calculate_regularity_score(df, 10)

        assert score > 30


class TestCalculateDataQuality:
    """数据质量评分测试"""

    @pytest.fixture
    def analyzer(self):
        """创建TrainingHistoryAnalyzer实例"""
        mock_storage = Mock()
        return TrainingHistoryAnalyzer(mock_storage)

    def test_empty_data(self, analyzer):
        """测试空数据"""
        lf = pl.LazyFrame()
        profile = RunnerProfile(user_id="test_user", profile_date=datetime(2024, 1, 1))

        analyzer.calculate_data_quality(lf, profile)

        assert profile.data_quality_score == 0.0

    def test_complete_data(self, analyzer):
        """测试完整数据"""
        lf = pl.LazyFrame(
            {
                "timestamp": [datetime.now()] * 15,
                "total_distance": [5000.0] * 15,
                "total_timer_time": [1800.0] * 15,
                "avg_heart_rate": [150.0] * 15,
            }
        )
        profile = RunnerProfile(user_id="test_user", profile_date=datetime(2024, 1, 1))

        analyzer.calculate_data_quality(lf, profile)

        assert profile.data_quality_score >= 80

    def test_partial_data(self, analyzer):
        """测试部分数据"""
        lf = pl.LazyFrame(
            {
                "timestamp": [datetime.now()] * 10,
                "total_distance": [5000.0] * 10,
                "total_timer_time": [1800.0] * 10,
                "avg_heart_rate": [None] * 10,
            }
        )
        profile = RunnerProfile(user_id="test_user", profile_date=datetime(2024, 1, 1))

        analyzer.calculate_data_quality(lf, profile)

        assert 0 <= profile.data_quality_score <= 100

    def test_minimal_data(self, analyzer):
        """测试最少数据"""
        lf = pl.LazyFrame(
            {
                "timestamp": [datetime.now()] * 3,
                "total_distance": [5000.0] * 3,
                "total_timer_time": [1800.0] * 3,
            }
        )
        profile = RunnerProfile(user_id="test_user", profile_date=datetime(2024, 1, 1))

        analyzer.calculate_data_quality(lf, profile)

        assert 0 <= profile.data_quality_score < 100


class TestGetTrainingSummary:
    """训练摘要测试"""

    @pytest.fixture
    def analyzer(self):
        """创建TrainingHistoryAnalyzer实例"""
        mock_storage = Mock()
        mock_storage.read_parquet.return_value = pl.LazyFrame(
            {
                "timestamp": [datetime.now()] * 10,
                "total_distance": [5000.0] * 10,
                "total_timer_time": [1800.0] * 10,
            }
        )
        return TrainingHistoryAnalyzer(mock_storage)

    def test_get_training_summary_with_data(self, analyzer):
        """测试有数据的训练摘要"""
        summary = analyzer.get_training_summary()

        assert summary["total_runs"] == 10
        assert summary["total_distance_km"] == 50.0
        assert summary["total_duration_hours"] == 5.0

    def test_get_training_summary_empty(self):
        """测试空数据的训练摘要"""
        mock_storage = Mock()
        mock_storage.read_parquet.return_value = pl.LazyFrame()
        analyzer = TrainingHistoryAnalyzer(mock_storage)

        summary = analyzer.get_training_summary()

        assert summary["total_runs"] == 0
        assert "message" in summary

    def test_get_training_summary_error(self):
        """测试错误的训练摘要"""
        mock_storage = Mock()
        mock_storage.read_parquet.side_effect = Exception("读取失败")
        analyzer = TrainingHistoryAnalyzer(mock_storage)

        summary = analyzer.get_training_summary()

        assert summary["total_runs"] == 0
        assert "message" in summary


class TestAnalyzeWeeklyPattern:
    """每周训练模式分析测试"""

    @pytest.fixture
    def analyzer(self):
        """创建TrainingHistoryAnalyzer实例"""
        mock_storage = Mock()
        return TrainingHistoryAnalyzer(mock_storage)

    def test_weekly_pattern_with_data(self, analyzer):
        """测试有数据的每周模式"""
        now = datetime.now()
        timestamps = [now - timedelta(days=i) for i in range(7)]
        df = pl.DataFrame({"timestamp": timestamps})

        result = analyzer.analyze_weekly_pattern(df)

        assert isinstance(result, dict)
        assert len(result) > 0

    def test_weekly_pattern_empty(self, analyzer):
        """测试空数据的每周模式"""
        df = pl.DataFrame()
        result = analyzer.analyze_weekly_pattern(df)

        assert result == {}

    def test_weekly_pattern_no_timestamp(self, analyzer):
        """测试无时间戳的每周模式"""
        df = pl.DataFrame({"distance": [5000.0] * 5})
        result = analyzer.analyze_weekly_pattern(df)

        assert result == {}


class TestGetRecentActivities:
    """获取最近活动测试"""

    @pytest.fixture
    def analyzer(self):
        """创建TrainingHistoryAnalyzer实例"""
        mock_storage = Mock()
        now = datetime.now()
        mock_storage.read_parquet.return_value = pl.LazyFrame(
            {
                "timestamp": [now - timedelta(days=i) for i in range(20)],
                "total_distance": [5000.0] * 20,
                "total_timer_time": [1800.0] * 20,
                "avg_heart_rate": [150.0] * 20,
            }
        )
        return TrainingHistoryAnalyzer(mock_storage)

    def test_get_recent_activities_default_limit(self, analyzer):
        """测试默认限制获取最近活动"""
        activities = analyzer.get_recent_activities()

        assert len(activities) == 10
        assert all("timestamp" in act for act in activities)
        assert all("distance_km" in act for act in activities)
        assert all("duration_min" in act for act in activities)

    def test_get_recent_activities_custom_limit(self, analyzer):
        """测试自定义限制获取最近活动"""
        activities = analyzer.get_recent_activities(limit=5)

        assert len(activities) == 5

    def test_get_recent_activities_empty(self):
        """测试空数据的最近活动"""
        mock_storage = Mock()
        mock_storage.read_parquet.return_value = pl.LazyFrame()
        analyzer = TrainingHistoryAnalyzer(mock_storage)

        activities = analyzer.get_recent_activities()

        assert activities == []

    def test_get_recent_activities_error(self):
        """测试错误的最近活动"""
        mock_storage = Mock()
        mock_storage.read_parquet.side_effect = Exception("读取失败")
        analyzer = TrainingHistoryAnalyzer(mock_storage)

        activities = analyzer.get_recent_activities()

        assert activities == []


class TestIntegration:
    """集成测试"""

    @pytest.fixture
    def analyzer(self):
        """创建TrainingHistoryAnalyzer实例"""
        mock_storage = Mock()
        now = datetime.now()
        mock_storage.read_parquet.return_value = pl.LazyFrame(
            {
                "timestamp": [now - timedelta(days=i) for i in range(30)],
                "total_distance": [5000.0] * 30,
                "total_timer_time": [1800.0] * 30,
                "avg_heart_rate": [150.0] * 30,
            }
        )
        return TrainingHistoryAnalyzer(mock_storage)

    def test_full_analysis_workflow(self, analyzer):
        """测试完整分析流程"""
        summary = analyzer.get_training_summary()
        activities = analyzer.get_recent_activities(limit=5)

        assert summary["total_runs"] == 30
        assert len(activities) == 5

    def test_data_quality_with_real_data(self, analyzer):
        """测试真实数据的质量评估"""
        lf = analyzer.storage.read_parquet()
        profile = RunnerProfile(user_id="test_user", profile_date=datetime(2024, 1, 1))

        analyzer.calculate_data_quality(lf, profile)

        assert profile.data_quality_score >= 80
