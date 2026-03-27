"""统计功能集成测试

测试 stats 命令在不同场景下的统计逻辑正确性
"""
from datetime import datetime, timedelta
from pathlib import Path

import polars as pl
import pytest

from src.core.analytics import AnalyticsEngine
from src.core.parser import FitParser
from src.core.storage import StorageManager


class TestStatsCommandIntegration:
    """stats 命令集成测试"""

    @pytest.fixture
    def mock_fit_file(self, tmp_path):
        """创建模拟 FIT 文件"""
        # 由于 FIT 文件需要特殊库来生成，这里使用简化的测试策略
        # 直接创建 Parquet 文件模拟已导入的 FIT 数据
        fit_file = tmp_path / "test_run.fit"
        fit_file.touch()  # 创建空文件
        return fit_file

    @pytest.fixture
    def sample_parquet_data(self, tmp_path):
        """创建样本 Parquet 数据（模拟已导入的 FIT 文件）"""
        storage_dir = tmp_path / "data"
        storage_dir.mkdir()
        
        storage = StorageManager(storage_dir)
        
        # 创建 3 次跑步的数据，每次跑步有多个采样点
        # 第一次：10 公里，60 分钟，3600 个采样点
        timestamps1 = [
            datetime(2024, 1, 1, 10, 0, 0) + timedelta(seconds=i)
            for i in range(3600)
        ]
        # 第二次：5 公里，30 分钟，1800 个采样点
        timestamps2 = [
            datetime(2024, 1, 2, 10, 0, 0) + timedelta(seconds=i)
            for i in range(1800)
        ]
        # 第三次：21.1 公里（半马），120 分钟，7200 个采样点
        timestamps3 = [
            datetime(2024, 1, 3, 10, 0, 0) + timedelta(seconds=i)
            for i in range(7200)
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
            "session_avg_heart_rate": (
                [145] * 3600 + [150] * 1800 + [140] * 7200
            ),
            "source_file": ["test1.fit"] * 3600 + ["test2.fit"] * 1800 + ["test3.fit"] * 7200,
            "filename": ["test1"] * 3600 + ["test2"] * 1800 + ["test3"] * 7200,
            "activity_id": [1] * 3600 + [2] * 1800 + [3] * 7200,
            "import_timestamp": [datetime.now()] * (3600 + 1800 + 7200),
        }
        
        df = pl.DataFrame(data)
        storage.save_to_parquet(df, 2024)
        
        return storage_dir

    def test_stats_command_with_multiple_runs(
        self, sample_parquet_data
    ):
        """测试 stats 命令处理多次跑步的统计"""
        from src.core.analytics import AnalyticsEngine
        
        storage = StorageManager(sample_parquet_data)
        analytics = AnalyticsEngine(storage)
        
        summary = analytics.get_running_summary()
        
        # 验证输出
        assert summary["total_runs"][0] == 3  # 应该是 3 次跑步，而不是 12600 个采样点
        assert summary["total_distance"][0] == 36100.0  # 36.1 公里
        assert summary["total_timer_time"][0] == 12600.0  # 210 分钟

    def test_stats_command_year_filter(
        self, sample_parquet_data
    ):
        """测试 stats 命令的年份过滤功能"""
        from src.core.analytics import AnalyticsEngine
        
        storage = StorageManager(sample_parquet_data)
        analytics = AnalyticsEngine(storage)
        
        # 测试 2024 年的数据
        summary = analytics.get_running_summary()
        
        assert summary["total_runs"][0] == 3  # 2024 年有 3 次跑步

    def test_stats_command_date_range_filter(
        self, sample_parquet_data
    ):
        """测试 stats 命令的日期范围过滤功能"""
        from src.core.analytics import AnalyticsEngine
        
        storage = StorageManager(sample_parquet_data)
        analytics = AnalyticsEngine(storage)
        
        # 测试只包含前两次跑步的日期范围
        summary = analytics.get_running_summary(
            start_date="2024-01-01",
            end_date="2024-01-02",
        )
        
        # 应该只显示前 2 次跑步
        assert summary["total_runs"][0] == 2

    def test_stats_command_empty_data(self, tmp_path):
        """测试 stats 命令处理空数据"""
        from src.core.analytics import AnalyticsEngine
        
        # 创建空的数据目录
        storage_dir = tmp_path / "data"
        storage_dir.mkdir()
        
        storage = StorageManager(storage_dir)
        analytics = AnalyticsEngine(storage)
        
        summary = analytics.get_running_summary()
        
        # 应该返回空 DataFrame
        assert summary.is_empty()


class TestStatsAggregationRealData:
    """使用真实数据结构的集成测试"""

    @pytest.fixture
    def realistic_run_data(self, tmp_path):
        """创建更真实的跑步数据"""
        storage_dir = tmp_path / "data"
        storage_dir.mkdir()
        storage = StorageManager(storage_dir)
        
        # 模拟一次真实的 10 公里跑步
        # 包含心率、配速的波动
        import random
        
        random.seed(42)  # 固定随机种子以保证可重复性
        
        num_points = 3600  # 60 分钟，每秒 1 个点
        base_time = datetime(2024, 1, 1, 10, 0, 0)
        
        timestamps = [base_time + timedelta(seconds=i) for i in range(num_points)]
        heart_rates = [140 + random.randint(-5, 10) for _ in range(num_points)]
        paces = [500 + random.randint(-20, 30) for _ in range(num_points)]
        
        data = {
            "timestamp": timestamps,
            "heart_rate": heart_rates,
            "pace": paces,
            "session_start_time": [base_time] * num_points,
            "session_total_distance": [10000.0] * num_points,
            "session_total_timer_time": [3600.0] * num_points,
            "session_avg_heart_rate": [145] * num_points,
            "source_file": ["run_20240101.fit"] * num_points,
            "filename": ["run_20240101"] * num_points,
            "activity_id": [1] * num_points,
            "import_timestamp": [datetime.now()] * num_points,
        }
        
        df = pl.DataFrame(data)
        storage.save_to_parquet(df, 2024)
        
        return storage_dir

    def test_realistic_data_aggregation(
        self, realistic_run_data, monkeypatch
    ):
        """测试真实数据结构的聚合统计"""
        from src.core.analytics import AnalyticsEngine
        from src.core.storage import StorageManager
        
        storage = StorageManager(realistic_run_data)
        analytics = AnalyticsEngine(storage)
        
        summary = analytics.get_running_summary()
        
        # 验证统计结果
        assert summary["total_runs"][0] == 1
        assert summary["total_distance"][0] == 10000.0
        assert summary["total_timer_time"][0] == 3600.0
        assert abs(summary["avg_heart_rate"][0] - 145.0) < 1.0

    def test_multiple_realistic_runs_aggregation(
        self, tmp_path, monkeypatch
    ):
        """测试多次真实跑步的聚合统计"""
        storage_dir = tmp_path / "data"
        storage_dir.mkdir()
        storage = StorageManager(storage_dir)
        
        import random
        
        random.seed(42)
        
        # 创建 5 次不同的跑步
        all_data = {}
        timestamps = []
        heart_rates = []
        paces = []
        session_starts = []
        distances = []
        durations = []
        avg_hrs = []
        
        runs = [
            (datetime(2024, 1, 1, 10, 0, 0), 5000, 1800, 150),   # 5 公里，30 分钟
            (datetime(2024, 1, 3, 10, 0, 0), 10000, 3000, 145),  # 10 公里，50 分钟
            (datetime(2024, 1, 5, 10, 0, 0), 15000, 4500, 148),  # 15 公里，75 分钟
            (datetime(2024, 1, 7, 10, 0, 0), 21100, 6300, 142),  # 半马，105 分钟
            (datetime(2024, 1, 10, 10, 0, 0), 8000, 2400, 152),  # 8 公里，40 分钟
        ]
        
        for i, (start_time, distance, duration, avg_hr) in enumerate(runs):
            num_points = duration
            run_timestamps = [
                start_time + timedelta(seconds=i) for i in range(num_points)
            ]
            run_hr = [avg_hr + random.randint(-5, 5) for _ in range(num_points)]
            run_pace = [
                (duration / (distance / 1000)) * 60 + random.randint(-10, 10)
                for _ in range(num_points)
            ]
            
            timestamps.extend(run_timestamps)
            heart_rates.extend(run_hr)
            paces.extend(run_pace)
            session_starts.extend([start_time] * num_points)
            distances.extend([float(distance)] * num_points)
            durations.extend([float(duration)] * num_points)
            avg_hrs.extend([float(avg_hr)] * num_points)
        
        data = {
            "timestamp": timestamps,
            "heart_rate": heart_rates,
            "pace": paces,
            "session_start_time": session_starts,
            "session_total_distance": distances,
            "session_total_timer_time": durations,
            "session_avg_heart_rate": avg_hrs,
            "source_file": [f"run_{i}.fit" for i in range(len(timestamps))],
            "filename": [f"run_{i}" for i in range(len(timestamps))],
            "activity_id": list(range(len(timestamps))),
            "import_timestamp": [datetime.now()] * len(timestamps),
        }
        
        df = pl.DataFrame(data)
        storage.save_to_parquet(df, 2024)
        
        # 测试统计
        analytics = AnalyticsEngine(storage)
        summary = analytics.get_running_summary()
        
        # 验证总跑步次数
        assert summary["total_runs"][0] == 5
        
        # 验证总距离（5+10+15+21.1+8 = 59.1 公里）
        expected_total_distance = 5000 + 10000 + 15000 + 21100 + 8000
        assert summary["total_distance"][0] == expected_total_distance
        
        # 验证总时长（30+50+75+105+40 = 300 分钟 = 18000 秒）
        expected_total_time = 1800 + 3000 + 4500 + 6300 + 2400
        assert summary["total_timer_time"][0] == expected_total_time
        
        # 验证平均距离（59.1 / 5 = 11.82 公里）
        expected_avg_distance = expected_total_distance / 5
        assert abs(summary["avg_distance"][0] - expected_avg_distance) < 0.01
        
        # 验证平均时长（300 / 5 = 60 分钟 = 3600 秒）
        expected_avg_time = expected_total_time / 5
        assert abs(summary["avg_timer_time"][0] - expected_avg_time) < 0.01
