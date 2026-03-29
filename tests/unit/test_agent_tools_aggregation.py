"""测试 Agent 工具的统计聚合逻辑

验证 Agent 工具在查询数据时正确使用按会话聚合逻辑
"""
from datetime import datetime, timedelta

import polars as pl
import pytest

from src.agents.tools import RunnerTools
from src.core.storage import StorageManager


class TestAgentToolsAggregation:
    """测试 Agent 工具的聚合逻辑"""

    @pytest.fixture
    def mock_storage(self, tmp_path):
        """创建模拟存储管理器"""
        storage_dir = tmp_path / "data"
        storage_dir.mkdir()
        return StorageManager(storage_dir)

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
            "source_file": ["test1.fit"] * 3600
            + ["test2.fit"] * 1800
            + ["test3.fit"] * 7200,
            "filename": ["test1"] * 3600 + ["test2"] * 1800 + ["test3"] * 7200,
            "activity_id": [1] * 3600 + [2] * 1800 + [3] * 7200,
            "import_timestamp": [datetime.now()] * (3600 + 1800 + 7200),
        }

        return pl.DataFrame(data)

    def test_query_by_date_range_aggregation(self, mock_storage, sample_run_data):
        """测试日期范围查询的聚合逻辑"""
        # 保存数据
        mock_storage.save_to_parquet(sample_run_data, 2024)

        # 创建 RunnerTools
        tools = RunnerTools(storage=mock_storage)

        # 查询所有数据
        results = tools.query_by_date_range("2024-01-01", "2024-01-03")

        # 验证：应该返回 3 次跑步，而不是 12600 个采样点
        assert len(results) == 3, f"应该返回 3 次跑步，但返回了 {len(results)} 条记录"

        # 验证每次跑步的数据
        distances = [r["distance"] for r in results]
        assert 10.0 in distances  # 10 公里
        assert 5.0 in distances  # 5 公里
        assert 21.1 in distances  # 21.1 公里

    def test_query_by_date_range_single_day(self, mock_storage, sample_run_data):
        """测试查询单天的数据"""
        # 保存数据
        mock_storage.save_to_parquet(sample_run_data, 2024)

        # 创建 RunnerTools
        tools = RunnerTools(storage=mock_storage)

        # 只查询第一天
        results = tools.query_by_date_range("2024-01-01", "2024-01-01")

        # 验证：应该返回 1 次跑步
        assert len(results) == 1, f"应该返回 1 次跑步，但返回了 {len(results)} 条记录"
        assert results[0]["distance"] == 10.0

    def test_query_by_distance_aggregation(self, mock_storage, sample_run_data):
        """测试距离查询的聚合逻辑"""
        # 保存数据
        mock_storage.save_to_parquet(sample_run_data, 2024)

        # 创建 RunnerTools
        tools = RunnerTools(storage=mock_storage)

        # 查询距离>=5 公里的跑步
        results = tools.query_by_distance(min_distance=5.0)

        # 验证：应该返回 3 次跑步，而不是 12600 个采样点
        assert len(results) == 3, f"应该返回 3 次跑步，但返回了 {len(results)} 条记录"

        # 验证距离
        distances = [r["distance"] for r in results]
        assert all(d >= 5.0 for d in distances)

    def test_query_by_distance_range(self, mock_storage, sample_run_data):
        """测试距离范围查询"""
        # 保存数据
        mock_storage.save_to_parquet(sample_run_data, 2024)

        # 创建 RunnerTools
        tools = RunnerTools(storage=mock_storage)

        # 查询 5-15 公里之间的跑步
        results = tools.query_by_distance(min_distance=5.0, max_distance=15.0)

        # 验证：应该返回 2 次跑步（5 公里和 10 公里）
        assert len(results) == 2, f"应该返回 2 次跑步，但返回了 {len(results)} 条记录"

        distances = [r["distance"] for r in results]
        assert 5.0 in distances
        assert 10.0 in distances

    def test_get_recent_runs_aggregation(self, mock_storage, sample_run_data):
        """测试最近跑步记录的聚合逻辑"""
        # 保存数据
        mock_storage.save_to_parquet(sample_run_data, 2024)

        # 创建 RunnerTools
        tools = RunnerTools(storage=mock_storage)

        # 获取最近 10 次跑步
        results = tools.get_recent_runs(limit=10)

        # 验证：应该返回 3 次跑步，而不是 12600 个采样点
        assert len(results) == 3, f"应该返回 3 次跑步，但返回了 {len(results)} 条记录"

        # 验证距离
        distances = [r["distance_km"] for r in results]
        assert 10.0 in distances
        assert 5.0 in distances
        assert 21.1 in distances

    def test_sampling_points_not_returned_as_runs(self, mock_storage, sample_run_data):
        """测试采样点不会被作为单独的跑步返回"""
        # 保存数据（12600 个采样点）
        mock_storage.save_to_parquet(sample_run_data, 2024)

        # 创建 RunnerTools
        tools = RunnerTools(storage=mock_storage)

        # 查询所有数据
        results = tools.query_by_date_range("2024-01-01", "2024-01-03")

        # 验证：返回的应该是 3 次跑步，而不是 12600 个采样点
        assert len(results) == 3
        assert len(results) != 12600

    def test_distance_not_duplicated_in_results(self, mock_storage, sample_run_data):
        """测试距离数据不会在结果中重复"""
        # 保存数据
        mock_storage.save_to_parquet(sample_run_data, 2024)

        # 创建 RunnerTools
        tools = RunnerTools(storage=mock_storage)

        # 查询所有数据
        results = tools.query_by_date_range("2024-01-01", "2024-01-03")

        # 验证总距离（应该是 36.1 公里，而不是 12600 * 平均距离）
        total_distance = sum(r["distance"] for r in results)
        assert abs(total_distance - 36.1) < 0.1

    def test_empty_date_range_query(self, mock_storage, sample_run_data):
        """测试空日期范围查询"""
        # 保存数据
        mock_storage.save_to_parquet(sample_run_data, 2024)

        # 创建 RunnerTools
        tools = RunnerTools(storage=mock_storage)

        # 查询不存在的日期范围
        results = tools.query_by_date_range("2020-01-01", "2020-01-01")

        # 验证：应该返回空列表
        assert len(results) == 0

    def test_invalid_date_format(self, mock_storage, sample_run_data):
        """测试无效日期格式处理"""
        # 保存数据
        mock_storage.save_to_parquet(sample_run_data, 2024)

        # 创建 RunnerTools
        tools = RunnerTools(storage=mock_storage)

        # 查询无效日期
        results = tools.query_by_date_range("invalid", "2024-01-01")

        # 验证：应该返回错误信息
        assert len(results) == 1
        assert "error" in results[0]


class TestAgentToolsEdgeCases:
    """测试 Agent 工具的边界情况"""

    @pytest.fixture
    def mock_storage(self, tmp_path):
        """创建模拟存储管理器"""
        storage_dir = tmp_path / "data"
        storage_dir.mkdir()
        return StorageManager(storage_dir)

    def test_single_run_query(self, mock_storage):
        """测试查询单次跑步"""
        # 创建只有 1 次跑步的数据
        timestamps = [
            datetime(2024, 1, 1, 10, 0, 0) + timedelta(seconds=i) for i in range(3600)
        ]

        data = {
            "timestamp": timestamps,
            "heart_rate": [145] * 3600,
            "pace": [500] * 3600,
            "session_start_time": [datetime(2024, 1, 1, 10, 0, 0)] * 3600,
            "session_total_distance": [10000.0] * 3600,
            "session_total_timer_time": [3600.0] * 3600,
            "session_avg_heart_rate": [145] * 3600,
            "source_file": ["test.fit"] * 3600,
            "filename": ["test"] * 3600,
            "activity_id": [1] * 3600,
            "import_timestamp": [datetime.now()] * 3600,
        }

        df = pl.DataFrame(data)
        mock_storage.save_to_parquet(df, 2024)

        # 创建 RunnerTools
        tools = RunnerTools(storage=mock_storage)

        # 查询
        results = tools.query_by_date_range("2024-01-01", "2024-01-01")

        # 验证
        assert len(results) == 1
        assert results[0]["distance"] == 10.0

    def test_no_data_query(self, mock_storage):
        """测试查询空数据"""
        # 创建 RunnerTools
        tools = RunnerTools(storage=mock_storage)

        # 查询
        results = tools.query_by_date_range("2024-01-01", "2024-01-01")

        # 验证
        assert len(results) == 0
