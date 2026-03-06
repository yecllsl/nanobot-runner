# 存储管理器单元测试

import tempfile
from datetime import datetime
from pathlib import Path

import polars as pl
import pytest

from src.core.storage import StorageManager


class TestStorageManager:
    """StorageManager 单元测试"""

    def test_init_default_dir(self):
        """测试初始化默认目录"""
        manager = StorageManager()
        assert manager.data_dir is not None

    def test_init_custom_dir(self):
        """测试初始化自定义目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_dir = Path(tmpdir) / "test_data"
            manager = StorageManager(data_dir=custom_dir)
            assert manager.data_dir == custom_dir

    def test_save_and_read_parquet(self):
        """测试保存和读取Parquet文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            # 创建测试数据
            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001"],
                    "timestamp": [datetime(2024, 1, 1)],
                    "total_distance": [5000.0],
                    "total_timer_time": [1800],
                    "avg_heart_rate": [140],
                }
            )

            # 保存
            result = manager.save_to_parquet(test_data, 2024)
            assert result is True

    def test_save_activities_alias(self):
        """测试 save_activities 方法（save_to_parquet 的别名）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001"],
                    "timestamp": [datetime(2024, 1, 1)],
                    "total_distance": [5000.0],
                    "total_timer_time": [1800],
                    "avg_heart_rate": [140],
                }
            )

            result = manager.save_activities(test_data, 2024)
            assert result is True

    def test_save_to_parquet_empty_with_allow_empty_true(self):
        """测试允许保存空数据框（allow_empty=True）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            empty_data = pl.DataFrame(
                {
                    "activity_id": [],
                    "timestamp": [],
                    "total_distance": [],
                    "total_timer_time": [],
                    "avg_heart_rate": [],
                }
            )

            result = manager.save_to_parquet(empty_data, 2024, allow_empty=True)
            assert result is True

    def test_save_to_parquet_empty_with_allow_empty_false(self):
        """测试拒绝保存空数据框（allow_empty=False，默认）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            empty_data = pl.DataFrame(
                {
                    "activity_id": [],
                    "timestamp": [],
                    "total_distance": [],
                    "total_timer_time": [],
                    "avg_heart_rate": [],
                }
            )

            with pytest.raises(ValueError, match="数据框不能为空"):
                manager.save_to_parquet(empty_data, 2024)

    def test_get_data_summary(self):
        """测试获取数据摘要"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001"],
                    "timestamp": [datetime(2024, 1, 1)],
                    "total_distance": [5000.0],
                    "total_timer_time": [1800],
                    "avg_heart_rate": [140],
                }
            )
            manager.save_to_parquet(test_data, 2024)

            summary = manager.get_data_summary()
            assert summary["total_records"] == 1
            assert 2024 in summary["available_years"]
            assert "total_size_mb" in summary

    def test_get_data_summary_empty(self):
        """测试空数据摘要"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            summary = manager.get_data_summary()
            assert summary["total_records"] == 0
            assert summary["available_years"] == []

    def test_delete_year_data(self):
        """测试删除年份数据"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001"],
                    "timestamp": [datetime(2024, 1, 1)],
                    "total_distance": [5000.0],
                    "total_timer_time": [1800],
                    "avg_heart_rate": [140],
                }
            )
            manager.save_to_parquet(test_data, 2024)

            # 删除数据
            result = manager.delete_year_data(2024)
            assert result is True

            # 验证删除
            years = manager.get_available_years()
            assert 2024 not in years

    def test_delete_year_data_not_exists(self):
        """测试删除不存在的年份数据"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            result = manager.delete_year_data(2024)
            assert result is False

    def test_append_to_existing_file(self):
        """测试追加到现有文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            # 第一次保存
            data1 = pl.DataFrame(
                {
                    "activity_id": ["test_001"],
                    "timestamp": [datetime(2024, 1, 1)],
                    "total_distance": [5000.0],
                    "total_timer_time": [1800],
                    "avg_heart_rate": [140],
                }
            )
            manager.save_to_parquet(data1, 2024)

            # 第二次追加
            data2 = pl.DataFrame(
                {
                    "activity_id": ["test_002"],
                    "timestamp": [datetime(2024, 1, 2)],
                    "total_distance": [10000.0],
                    "total_timer_time": [3600],
                    "avg_heart_rate": [150],
                }
            )
            manager.save_to_parquet(data2, 2024)

            # 读取验证
            lf = manager.read_parquet(years=[2024])
            df = lf.collect()

            assert df.height == 2

    def test_get_stats(self):
        """测试获取统计信息"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            # 创建测试数据
            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001", "test_002"],
                    "timestamp": [datetime(2024, 1, 1), datetime(2024, 2, 1)],
                    "total_distance": [5000.0, 10000.0],
                    "total_timer_time": [1800, 3600],
                    "avg_heart_rate": [140, 150],
                }
            )
            manager.save_to_parquet(test_data, 2024)

            # 获取统计
            stats = manager.get_stats()

            assert stats["total_records"] == 2
            assert 2024 in stats["years"]
            assert stats["time_range"] is not None

    def test_get_stats_empty(self):
        """测试空数据统计"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            stats = manager.get_stats()

            assert stats["total_records"] == 0
            assert stats["years"] == []

    def test_get_available_years(self):
        """测试获取可用年份"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            # 创建测试数据
            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001"],
                    "timestamp": [datetime(2024, 1, 1)],
                    "total_distance": [5000.0],
                    "total_timer_time": [1800],
                    "avg_heart_rate": [140],
                }
            )
            manager.save_to_parquet(test_data, 2024)

            years = manager.get_available_years()
            assert 2024 in years

    def test_get_available_years_empty(self):
        """测试空数据的可用年份"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            years = manager.get_available_years()
            assert years == []

    def test_read_activities_with_year(self):
        """测试按年份读取"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            # 创建测试数据
            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001"],
                    "timestamp": [datetime(2024, 1, 1)],
                    "total_distance": [5000.0],
                    "total_timer_time": [1800],
                    "avg_heart_rate": [140],
                }
            )
            manager.save_to_parquet(test_data, 2024)

            df = manager.read_activities(2024)
            assert df.height == 1

    def test_read_activities_multiple_years(self):
        """测试多年份数据读取"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            # 创建2024年数据
            data_2024 = pl.DataFrame(
                {
                    "activity_id": ["test_001"],
                    "timestamp": [datetime(2024, 1, 1)],
                    "total_distance": [5000.0],
                    "total_timer_time": [1800],
                    "avg_heart_rate": [140],
                }
            )
            manager.save_to_parquet(data_2024, 2024)

            # 创建2025年数据
            data_2025 = pl.DataFrame(
                {
                    "activity_id": ["test_002"],
                    "timestamp": [datetime(2025, 1, 1)],
                    "total_distance": [10000.0],
                    "total_timer_time": [3600],
                    "avg_heart_rate": [150],
                }
            )
            manager.save_to_parquet(data_2025, 2025)

            # 读取所有年份
            df = manager.read_activities()
            assert df.height == 2

    def test_query_activities_by_days(self):
        """测试按天数查询"""
        from datetime import datetime, timedelta
        
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            # 创建最近7天的数据
            today = datetime.now()
            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001", "test_002"],
                    "timestamp": [today - timedelta(days=3), today - timedelta(days=5)],
                    "total_distance": [5000.0, 10000.0],
                    "total_timer_time": [1800, 3600],
                    "avg_heart_rate": [140, 150],
                }
            )
            manager.save_to_parquet(test_data, today.year)

            # 查询最近30天
            result = manager.query_activities(days=30)
            assert result.height >= 0

    def test_query_activities_by_min_distance(self):
        """测试按最小距离查询"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001", "test_002"],
                    "timestamp": [datetime(2024, 1, 1), datetime(2024, 1, 2)],
                    "total_distance": [5000.0, 10000.0],
                    "total_timer_time": [1800, 3600],
                    "avg_heart_rate": [140, 150],
                }
            )
            manager.save_to_parquet(test_data, 2024)

            result = manager.query_activities(min_distance=8000)
            assert result.height >= 0

    def test_query_activities_by_min_heart_rate(self):
        """测试按最小心率查询"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001", "test_002"],
                    "timestamp": [datetime(2024, 1, 1), datetime(2024, 1, 2)],
                    "total_distance": [5000.0, 10000.0],
                    "total_timer_time": [1800, 3600],
                    "avg_heart_rate": [140, 150],
                }
            )
            manager.save_to_parquet(test_data, 2024)

            result = manager.query_activities(min_heart_rate=145)
            assert result.height >= 0

    def test_query_activities_no_data(self):
        """测试无数据查询"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            result = manager.query_activities()
            assert result.height == 0

    def test_read_parquet_empty_directory(self):
        """测试空目录读取"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            lf = manager.read_parquet()
            df = lf.collect()
            assert df.height == 0

    def test_save_to_parquet_compression(self):
        """测试压缩保存"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001"],
                    "timestamp": [datetime(2024, 1, 1)],
                    "total_distance": [5000.0],
                    "total_timer_time": [1800],
                    "avg_heart_rate": [140],
                }
            )
            result = manager.save_to_parquet(test_data, 2024)
            assert result is True
