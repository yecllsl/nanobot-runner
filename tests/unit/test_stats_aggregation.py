"""测试统计聚合逻辑的正确性

验证按会话聚合统计逻辑，确保不会将采样点数量误认为跑步次数
"""

from datetime import datetime, timedelta

import polars as pl
import pytest

from src.core.analytics import AnalyticsEngine
from src.core.storage import StorageManager


class TestStatsAggregation:
    """测试统计聚合逻辑"""

    @pytest.fixture
    def mock_storage(self, tmp_path):
        """创建模拟存储管理器"""
        storage = StorageManager(tmp_path)
        return storage

    @pytest.fixture
    def sample_run_data(self):
        """创建样本跑步数据（包含多个采样点）"""
        # 模拟一次 60 分钟的跑步，每秒 1 个采样点，共 3600 个采样点
        timestamps = [
            datetime(2024, 1, 1, 10, 0, 0) + timedelta(seconds=i) for i in range(3600)
        ]

        data = {
            "timestamp": timestamps,
            "heart_rate": [140 + i % 10 for i in range(3600)],  # 心率 140-149 波动
            "pace": [500 + i % 20 for i in range(3600)],  # 配速 500-519 秒/公里波动
            "session_start_time": [datetime(2024, 1, 1, 10, 0, 0)] * 3600,
            "session_total_distance": [10000.0] * 3600,  # 10 公里
            "session_total_timer_time": [3600.0] * 3600,  # 60 分钟
            "session_avg_heart_rate": [145] * 3600,
        }

        return pl.DataFrame(data)

    @pytest.fixture
    def multiple_runs_data(self):
        """创建多次跑步的样本数据"""
        # 第一次跑步：3600 个采样点，10 公里，60 分钟
        timestamps1 = [
            datetime(2024, 1, 1, 10, 0, 0) + timedelta(seconds=i) for i in range(3600)
        ]
        # 第二次跑步：1800 个采样点，5 公里，30 分钟
        timestamps2 = [
            datetime(2024, 1, 2, 10, 0, 0) + timedelta(seconds=i) for i in range(1800)
        ]
        # 第三次跑步：7200 个采样点，20 公里，120 分钟
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
                [10000.0] * 3600 + [5000.0] * 1800 + [20000.0] * 7200
            ),
            "session_total_timer_time": (
                [3600.0] * 3600 + [1800.0] * 1800 + [7200.0] * 7200
            ),
            "session_avg_heart_rate": ([145] * 3600 + [150] * 1800 + [140] * 7200),
        }

        return pl.DataFrame(data)

    def test_single_run_aggregation(self, mock_storage, sample_run_data):
        """测试单次跑步的聚合统计"""
        # 保存数据
        mock_storage.save_to_parquet(sample_run_data, 2024)

        # 创建分析引擎
        analytics = AnalyticsEngine(mock_storage)
        summary = analytics.get_running_summary()

        # 验证聚合结果
        assert summary.height == 1, "应该聚合为 1 次跑步"
        assert summary["total_runs"][0] == 1
        assert summary["total_distance"][0] == 10000.0
        assert summary["total_timer_time"][0] == 3600.0
        assert abs(summary["avg_distance"][0] - 10000.0) < 0.01
        assert abs(summary["avg_timer_time"][0] - 3600.0) < 0.01
        assert abs(summary["avg_heart_rate"][0] - 145.0) < 0.01

    def test_multiple_runs_aggregation(self, mock_storage, multiple_runs_data):
        """测试多次跑步的聚合统计"""
        # 保存数据
        mock_storage.save_to_parquet(multiple_runs_data, 2024)

        # 创建分析引擎
        analytics = AnalyticsEngine(mock_storage)
        summary = analytics.get_running_summary()

        # 验证聚合结果
        assert summary.height == 1, "应该聚合为 1 行统计结果"
        assert summary["total_runs"][0] == 3, "应该是 3 次跑步"
        assert summary["total_distance"][0] == 35000.0, "总距离应该是 35 公里"
        assert summary["total_timer_time"][0] == 12600.0, "总时长应该是 12600 秒"
        assert abs(summary["avg_distance"][0] - 11666.67) < 0.01
        assert abs(summary["avg_timer_time"][0] - 4200.0) < 0.01
        assert abs(summary["avg_heart_rate"][0] - 145.0) < 0.01

    def test_empty_data_aggregation(self, mock_storage):
        """测试空数据的聚合统计"""
        analytics = AnalyticsEngine(mock_storage)
        summary = analytics.get_running_summary()

        # 验证空结果
        assert summary.is_empty()

    def test_session_grouping_logic(self, mock_storage, sample_run_data):
        """测试会话分组逻辑的正确性"""
        # 保存数据
        mock_storage.save_to_parquet(sample_run_data, 2024)

        # 手动执行聚合逻辑
        lf = mock_storage.read_parquet()
        session_df = (
            lf.group_by("session_start_time")
            .agg(
                [
                    pl.col("session_total_distance").first().alias("distance"),
                    pl.col("session_total_timer_time").first().alias("duration"),
                    pl.col("session_avg_heart_rate").first().alias("avg_hr"),
                ]
            )
            .collect()
        )

        # 验证聚合后的行数
        assert session_df.height == 1, "应该聚合为 1 行"
        assert session_df["distance"][0] == 10000.0
        assert session_df["duration"][0] == 3600.0
        assert session_df["avg_hr"][0] == 145

    def test_sampling_points_not_counted_as_runs(self, mock_storage, sample_run_data):
        """测试采样点不会被误认为跑步次数"""
        # 保存数据（3600 个采样点）
        mock_storage.save_to_parquet(sample_run_data, 2024)

        # 创建分析引擎
        analytics = AnalyticsEngine(mock_storage)
        summary = analytics.get_running_summary()

        # 验证：跑步次数应该是 1，而不是 3600
        assert summary["total_runs"][0] == 1
        assert summary["total_runs"][0] != 3600

    def test_distance_not_doubly_counted(self, mock_storage, sample_run_data):
        """测试距离不会被重复计算"""
        # 保存数据（3600 个采样点，每个都包含 10 公里的会话数据）
        mock_storage.save_to_parquet(sample_run_data, 2024)

        # 创建分析引擎
        analytics = AnalyticsEngine(mock_storage)
        summary = analytics.get_running_summary()

        # 验证：总距离应该是 10 公里，而不是 3600 * 10 公里
        assert summary["total_distance"][0] == 10000.0
        assert summary["total_distance"][0] != 36000000.0

    def test_time_not_doubly_counted(self, mock_storage, sample_run_data):
        """测试时长不会被重复计算"""
        # 保存数据（3600 个采样点，每个都包含 3600 秒的会话数据）
        mock_storage.save_to_parquet(sample_run_data, 2024)

        # 创建分析引擎
        analytics = AnalyticsEngine(mock_storage)
        summary = analytics.get_running_summary()

        # 验证：总时长应该是 3600 秒，而不是 3600 * 3600 秒
        assert summary["total_timer_time"][0] == 3600.0
        assert summary["total_timer_time"][0] != 12960000.0


class TestStatsAggregationEdgeCases:
    """测试统计聚合的边界情况"""

    @pytest.fixture
    def mock_storage(self, tmp_path):
        """创建模拟存储管理器"""
        storage = StorageManager(tmp_path)
        return storage

    def test_single_sampling_point_run(self, mock_storage):
        """测试只有一个采样点的跑步"""
        # 创建只有 1 个采样点的数据
        data = {
            "timestamp": [datetime(2024, 1, 1, 10, 0, 0)],
            "heart_rate": [145],
            "pace": [500],
            "session_start_time": [datetime(2024, 1, 1, 10, 0, 0)],
            "session_total_distance": [5000.0],
            "session_total_timer_time": [1800.0],
            "session_avg_heart_rate": [150],
        }

        df = pl.DataFrame(data)
        mock_storage.save_to_parquet(df, 2024)

        analytics = AnalyticsEngine(mock_storage)
        summary = analytics.get_running_summary()

        assert summary["total_runs"][0] == 1
        assert summary["total_distance"][0] == 5000.0
        assert summary["total_timer_time"][0] == 1800.0

    def test_same_start_time_different_sessions(self, mock_storage):
        """测试相同开始时间的不同会话（理论上不应该发生）"""
        # 创建两个会话，但开始时间相同（异常情况）
        timestamps1 = [
            datetime(2024, 1, 1, 10, 0, 0) + timedelta(seconds=i) for i in range(100)
        ]
        timestamps2 = [
            datetime(2024, 1, 1, 10, 0, 0) + timedelta(seconds=i)
            for i in range(100, 200)
        ]

        data = {
            "timestamp": timestamps1 + timestamps2,
            "heart_rate": [145] * 200,
            "pace": [500] * 200,
            "session_start_time": [datetime(2024, 1, 1, 10, 0, 0)] * 200,
            "session_total_distance": [5000.0] * 100 + [6000.0] * 100,
            "session_total_timer_time": [1800.0] * 100 + [2000.0] * 100,
            "session_avg_heart_rate": [150] * 200,
        }

        df = pl.DataFrame(data)
        mock_storage.save_to_parquet(df, 2024)

        analytics = AnalyticsEngine(mock_storage)
        summary = analytics.get_running_summary()

        # 由于开始时间相同，会被聚合为一次跑步
        # 取第一个会话的数据
        assert summary["total_runs"][0] == 1
        assert summary["total_distance"][0] == 5000.0  # 取第一个值
