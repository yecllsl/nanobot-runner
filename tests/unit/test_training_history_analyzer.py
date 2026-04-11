# TrainingHistoryAnalyzer 单元测试

from datetime import datetime
from unittest.mock import MagicMock

import polars as pl
import pytest

from src.core.training_history_analyzer import TrainingHistoryAnalyzer
from src.core.user_profile_manager import RunnerProfile


@pytest.fixture
def mock_storage() -> MagicMock:
    """创建模拟 StorageManager"""
    return MagicMock()


@pytest.fixture
def history_analyzer(mock_storage: MagicMock) -> TrainingHistoryAnalyzer:
    """创建 TrainingHistoryAnalyzer 实例"""
    return TrainingHistoryAnalyzer(mock_storage)


@pytest.fixture
def sample_profile() -> RunnerProfile:
    """创建示例画像"""
    return RunnerProfile(user_id="test_user", profile_date=datetime.now())


class TestTrainingHistoryAnalyzer:
    """TrainingHistoryAnalyzer 测试类"""

    def test_analyze_running_time_preference_morning(
        self, history_analyzer: TrainingHistoryAnalyzer
    ) -> None:
        """测试早晨跑步偏好"""
        timestamps = pl.Series(
            [
                datetime(2026, 1, 1, 22, 0, 0),
                datetime(2026, 1, 2, 23, 0, 0),
                datetime(2026, 1, 3, 0, 0, 0),
            ]
        )

        result = history_analyzer.analyze_running_time_preference(timestamps)

        assert result == "morning"

    def test_analyze_running_time_preference_afternoon(
        self, history_analyzer: TrainingHistoryAnalyzer
    ) -> None:
        """测试下午跑步偏好"""
        timestamps = pl.Series(
            [
                datetime(2026, 1, 1, 6, 0, 0),
                datetime(2026, 1, 2, 7, 0, 0),
                datetime(2026, 1, 3, 8, 0, 0),
            ]
        )

        result = history_analyzer.analyze_running_time_preference(timestamps)

        assert result == "afternoon"

    def test_analyze_running_time_preference_evening(
        self, history_analyzer: TrainingHistoryAnalyzer
    ) -> None:
        """测试晚上跑步偏好"""
        timestamps = pl.Series(
            [
                datetime(2026, 1, 1, 11, 0, 0),
                datetime(2026, 1, 2, 12, 0, 0),
                datetime(2026, 1, 3, 13, 0, 0),
            ]
        )

        result = history_analyzer.analyze_running_time_preference(timestamps)

        assert result == "evening"

    def test_calculate_consistency_score_empty_df(
        self, history_analyzer: TrainingHistoryAnalyzer
    ) -> None:
        """测试空数据的一致性评分"""
        df = pl.DataFrame()

        result = history_analyzer.calculate_consistency_score(df, 30)

        assert result == 0.0

    def test_calculate_consistency_score_low_runs(
        self, history_analyzer: TrainingHistoryAnalyzer
    ) -> None:
        """测试低频训练的一致性评分"""
        df = pl.DataFrame(
            {
                "timestamp": [
                    datetime(2026, 1, 1, 8, 0, 0),
                    datetime(2026, 1, 15, 8, 0, 0),
                ]
            }
        )

        result = history_analyzer.calculate_consistency_score(df, 30)

        assert 0 <= result <= 100

    def test_calculate_consistency_score_regular_runs(
        self, history_analyzer: TrainingHistoryAnalyzer
    ) -> None:
        """测试规律训练的一致性评分"""
        timestamps = [datetime(2026, 1, i, 8, 0, 0) for i in range(1, 22, 3)]
        df = pl.DataFrame({"timestamp": timestamps})

        result = history_analyzer.calculate_consistency_score(df, 30)

        assert result > 50

    def test_calculate_data_quality_empty(
        self, history_analyzer: TrainingHistoryAnalyzer, sample_profile: RunnerProfile
    ) -> None:
        """测试空数据的质量评分"""
        lf = pl.DataFrame().lazy()

        history_analyzer.calculate_data_quality(lf, sample_profile)

        assert sample_profile.data_quality_score == 0.0

    def test_calculate_data_quality_full_data(
        self, history_analyzer: TrainingHistoryAnalyzer, sample_profile: RunnerProfile
    ) -> None:
        """测试完整数据的质量评分"""
        df = pl.DataFrame(
            {
                "timestamp": [datetime(2026, 1, i, 8, 0, 0) for i in range(1, 15)],
                "total_distance": [5000.0] * 14,
                "avg_heart_rate": [150] * 14,
            }
        )
        lf = df.lazy()

        history_analyzer.calculate_data_quality(lf, sample_profile)

        assert sample_profile.data_quality_score > 80

    def test_calculate_data_quality_partial_data(
        self, history_analyzer: TrainingHistoryAnalyzer, sample_profile: RunnerProfile
    ) -> None:
        """测试部分数据的质量评分"""
        df = pl.DataFrame(
            {
                "timestamp": [datetime(2026, 1, i, 8, 0, 0) for i in range(1, 8)],
                "total_distance": [5000.0] * 7,
                "avg_heart_rate": [None, 150, None, 140, None, 145, None],
            }
        )
        lf = df.lazy()

        history_analyzer.calculate_data_quality(lf, sample_profile)

        assert 0 < sample_profile.data_quality_score < 100

    def test_get_training_summary_empty(
        self, history_analyzer: TrainingHistoryAnalyzer, mock_storage: MagicMock
    ) -> None:
        """测试空数据的训练摘要"""
        mock_storage.read_parquet.return_value = pl.DataFrame().lazy()

        result = history_analyzer.get_training_summary()

        assert result["total_runs"] == 0

    def test_get_training_summary_with_data(
        self, history_analyzer: TrainingHistoryAnalyzer, mock_storage: MagicMock
    ) -> None:
        """测试有数据的训练摘要"""
        df = pl.DataFrame(
            {
                "timestamp": [datetime(2026, 1, i, 8, 0, 0) for i in range(1, 8)],
                "total_distance": [5000.0] * 7,
                "total_timer_time": [1800.0] * 7,
            }
        )
        mock_storage.read_parquet.return_value = df.lazy()

        result = history_analyzer.get_training_summary()

        assert result["total_runs"] == 7
        assert result["total_distance_km"] == 35.0
        assert result["total_duration_hours"] == 3.5

    def test_analyze_weekly_pattern_empty(
        self, history_analyzer: TrainingHistoryAnalyzer
    ) -> None:
        """测试空数据的每周模式"""
        df = pl.DataFrame()

        result = history_analyzer.analyze_weekly_pattern(df)

        assert result == {}

    def test_analyze_weekly_pattern_with_data(
        self, history_analyzer: TrainingHistoryAnalyzer
    ) -> None:
        """测试有数据的每周模式"""
        df = pl.DataFrame(
            {
                "timestamp": [
                    datetime(2026, 1, 5, 8, 0, 0),
                    datetime(2026, 1, 7, 8, 0, 0),
                    datetime(2026, 1, 6, 8, 0, 0),
                ]
            }
        )

        result = history_analyzer.analyze_weekly_pattern(df)

        assert len(result) > 0

    def test_get_recent_activities_empty(
        self, history_analyzer: TrainingHistoryAnalyzer, mock_storage: MagicMock
    ) -> None:
        """测试空数据的最近活动"""
        mock_storage.read_parquet.return_value = pl.DataFrame().lazy()

        result = history_analyzer.get_recent_activities()

        assert result == []

    def test_get_recent_activities_with_data(
        self, history_analyzer: TrainingHistoryAnalyzer, mock_storage: MagicMock
    ) -> None:
        """测试有数据的最近活动"""
        df = pl.DataFrame(
            {
                "timestamp": [datetime(2026, 1, i, 8, 0, 0) for i in range(1, 8)],
                "total_distance": [5000.0] * 7,
                "total_timer_time": [1800.0] * 7,
                "avg_heart_rate": [150] * 7,
            }
        )
        mock_storage.read_parquet.return_value = df.lazy()

        result = history_analyzer.get_recent_activities(limit=5)

        assert len(result) == 5
        assert "timestamp" in result[0]
        assert "distance_km" in result[0]

    def test_get_recent_activities_with_exception(
        self, history_analyzer: TrainingHistoryAnalyzer, mock_storage: MagicMock
    ) -> None:
        """测试异常情况下的最近活动"""
        mock_storage.read_parquet.side_effect = Exception("读取失败")

        result = history_analyzer.get_recent_activities()

        assert result == []

    def test_analyze_running_time_preference_with_exception(
        self, history_analyzer: TrainingHistoryAnalyzer
    ) -> None:
        """测试异常情况下的时间偏好分析"""
        timestamps = pl.Series([None, None])

        result = history_analyzer.analyze_running_time_preference(timestamps)

        assert result == "morning"

    def test_calculate_consistency_score_with_single_run(
        self, history_analyzer: TrainingHistoryAnalyzer
    ) -> None:
        """测试单次训练的一致性评分"""
        df = pl.DataFrame({"timestamp": [datetime(2026, 1, 1, 8, 0, 0)]})

        result = history_analyzer.calculate_consistency_score(df, 30)

        assert 0 <= result <= 100
