"""
测试 Agent 工具的聚合逻辑

验证 Agent 工具在查询数据时正确使用按会话聚合逻辑
"""
from datetime import datetime, timedelta

import polars as pl
import pytest

from src.agents.tools import RunnerTools
from src.core.analytics import AnalyticsEngine
from src.core.storage import StorageManager
from tests.conftest import create_mock_context


class TestAgentToolsAggregation:
    """测试 Agent 工具的聚合逻辑"""

    @pytest.fixture
    def mock_storage(self, tmp_path):
        """创建模拟存储管理器"""
        storage_dir = tmp_path / "data"
        storage_dir.mkdir()
        return StorageManager(storage_dir)

    @pytest.fixture
    def mock_analytics(self, mock_storage):
        """创建模拟分析引擎"""
        return AnalyticsEngine(mock_storage)

    @pytest.fixture
    def sample_run_data(self):
        """创建样本跑步数据（包含多个采样点）"""
        # 创建 3 次跑步的数据
        # 第一次：10 公里，60 分钟，3600 个采样点
        timestamps1 = [
            datetime(2024, 1, 1, 10, 0, 0) + timedelta(seconds=i) for i in range(3600)
        ]
        # 第二次：5 公里，30 分钟，1800 个采样点
        timestamps2 = [
            datetime(2024, 1, 2, 10, 0, 0) + timedelta(seconds=i) for i in range(1800)
        ]
        # 第三次：21.1 公里，120 分钟，7200 个采样点
        timestamps3 = [
            datetime(2024, 1, 3, 10, 0, 0) + timedelta(seconds=i) for i in range(7200)
        ]

        data = {
            "timestamp": timestamps1 + timestamps2 + timestamps3,
            "heart_rate": [145] * (3600 + 1800 + 7200),
            "pace": [500] * (3600 + 1800 + 7200),
            "session_start_time": (
                [datetime(2024, 1, 1, 10, 0, 0)] * 3600
                + [datetime(2024, 1, 2, 10, 0, 0)] * 1800
                + [datetime(2024, 1, 3, 10, 0, 0)] * 7200
            ),
            "session_total_distance": (
                [10000.0] * 3600 + [5000.0] * 1800 + [21100.0] * 7200
            ),
            "session_total_timer_time": (
                [3600.0] * 3600 + [1800.0] * 1800 + [7200.0] * 7200
            ),
            "session_avg_heart_rate": ([145] * 3600 + [150] * 1800 + [140] * 7200),
        }

        return pl.DataFrame(data)

    def test_get_running_stats_with_aggregation(
        self, mock_storage, mock_analytics, sample_run_data
    ):
        """测试获取跑步统计时正确聚合"""
        mock_storage.save_to_parquet(sample_run_data, year=2024)

        tools = RunnerTools(
            context=create_mock_context(storage=mock_storage, analytics=mock_analytics)
        )
        stats = tools.get_running_stats()

        assert stats["total_runs"] == 3
        assert stats["total_distance"] == 36100.0
        assert stats["total_duration"] == 12600.0

    def test_get_recent_runs_with_aggregation(
        self, mock_storage, mock_analytics, sample_run_data
    ):
        """测试获取最近跑步记录时正确聚合"""
        mock_storage.save_to_parquet(sample_run_data, year=2024)

        tools = RunnerTools(
            context=create_mock_context(storage=mock_storage, analytics=mock_analytics)
        )
        runs = tools.get_recent_runs(limit=10)

        assert len(runs) == 3
        assert runs[0]["distance_km"] == 21.1
        assert runs[1]["distance_km"] == 5.0
        assert runs[2]["distance_km"] == 10.0

    def test_get_vdot_trend_with_aggregation(
        self, mock_storage, mock_analytics, sample_run_data
    ):
        """测试获取 VDOT 趋势时正确聚合"""
        mock_storage.save_to_parquet(sample_run_data, year=2024)

        tools = RunnerTools(
            context=create_mock_context(storage=mock_storage, analytics=mock_analytics)
        )
        trend = tools.get_vdot_trend(limit=10)

        assert len(trend) == 3

    def test_get_training_load_with_aggregation(
        self, mock_storage, mock_analytics, sample_run_data
    ):
        """测试获取训练负荷时正确聚合"""
        mock_storage.save_to_parquet(sample_run_data, year=2024)

        tools = RunnerTools(
            context=create_mock_context(storage=mock_storage, analytics=mock_analytics)
        )
        load = tools.get_training_load(days=42)

        assert "atl" in load
        assert "ctl" in load
        assert "tsb" in load

    def test_get_hr_drift_analysis_with_aggregation(
        self, mock_storage, mock_analytics, sample_run_data
    ):
        """测试获取心率漂移分析时正确聚合"""
        mock_storage.save_to_parquet(sample_run_data, year=2024)

        tools = RunnerTools(
            context=create_mock_context(storage=mock_storage, analytics=mock_analytics)
        )
        drift = tools.get_hr_drift_analysis()

        assert "trend" in drift or "error" in drift

    def test_query_by_date_range_with_aggregation(
        self, mock_storage, mock_analytics, sample_run_data
    ):
        """测试按日期范围查询时正确聚合"""
        mock_storage.save_to_parquet(sample_run_data, year=2024)

        tools = RunnerTools(
            context=create_mock_context(storage=mock_storage, analytics=mock_analytics)
        )
        runs = tools.query_by_date_range(start_date="2024-01-01", end_date="2024-01-02")

        assert len(runs) == 2

    def test_query_by_distance_with_aggregation(
        self, mock_storage, mock_analytics, sample_run_data
    ):
        """测试按距离查询时正确聚合"""
        mock_storage.save_to_parquet(sample_run_data, year=2024)

        tools = RunnerTools(
            context=create_mock_context(storage=mock_storage, analytics=mock_analytics)
        )
        runs = tools.query_by_distance(min_distance=5.0)

        assert len(runs) == 3

    def test_empty_data_handling(self, mock_storage, mock_analytics):
        """测试空数据处理"""
        tools = RunnerTools(
            context=create_mock_context(storage=mock_storage, analytics=mock_analytics)
        )
        stats = tools.get_running_stats()

        assert "message" in stats
        assert "暂无跑步数据" in stats["message"]

    def test_single_run_data(self, mock_storage, mock_analytics):
        """测试单次跑步数据"""
        data = pl.DataFrame(
            {
                "timestamp": [datetime(2024, 1, 1, 10, 0, 0)],
                "heart_rate": [145],
                "pace": [500],
                "session_start_time": [datetime(2024, 1, 1, 10, 0, 0)],
                "session_total_distance": [10000.0],
                "session_total_timer_time": [3600.0],
                "session_avg_heart_rate": [145],
            }
        )

        mock_storage.save_to_parquet(data, year=2024)

        tools = RunnerTools(
            context=create_mock_context(storage=mock_storage, analytics=mock_analytics)
        )
        stats = tools.get_running_stats()

        assert stats["total_runs"] == 1
        assert stats["total_distance"] == 10000.0

    def test_multiple_runs_same_day(self, mock_storage, mock_analytics):
        """测试同一天多次跑步"""
        timestamps = [
            datetime(2024, 1, 1, 10, 0, 0),
            datetime(2024, 1, 1, 14, 0, 0),
        ]

        data = pl.DataFrame(
            {
                "timestamp": timestamps,
                "heart_rate": [145, 150],
                "pace": [500, 480],
                "session_start_time": timestamps,
                "session_total_distance": [5000.0, 3000.0],
                "session_total_timer_time": [1800.0, 1200.0],
                "session_avg_heart_rate": [145, 150],
            }
        )

        mock_storage.save_to_parquet(data, year=2024)

        tools = RunnerTools(
            context=create_mock_context(storage=mock_storage, analytics=mock_analytics)
        )
        stats = tools.get_running_stats()

        assert stats["total_runs"] == 2
        assert stats["total_distance"] == 8000.0
