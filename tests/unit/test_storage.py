# 存储管理器单元测试

import tempfile
import pytest
from pathlib import Path
from datetime import datetime

import polars as pl

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
            test_data = pl.DataFrame({
                "activity_id": ["test_001"],
                "timestamp": [datetime(2024, 1, 1)],
                "distance": [5000.0],
                "duration": [1800],
                "heart_rate": [140]
            })
            
            # 保存
            result = manager.save_to_parquet(test_data, 2024)
            assert result is True
            
            # 读取
            lf = manager.read_parquet(years=[2024])
            df = lf.collect()
            
            assert df.height == 1
            assert set(df.columns) == {"activity_id", "timestamp", "distance", "duration", "heart_rate"}
    
    def test_append_to_existing_file(self):
        """测试追加到现有文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))
            
            # 第一次保存
            data1 = pl.DataFrame({
                "activity_id": ["test_001"],
                "timestamp": [datetime(2024, 1, 1)],
                "distance": [5000.0],
                "duration": [1800],
                "heart_rate": [140]
            })
            manager.save_to_parquet(data1, 2024)
            
            # 第二次追加
            data2 = pl.DataFrame({
                "activity_id": ["test_002"],
                "timestamp": [datetime(2024, 1, 2)],
                "distance": [10000.0],
                "duration": [3600],
                "heart_rate": [150]
            })
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
            test_data = pl.DataFrame({
                "activity_id": ["test_001", "test_002"],
                "timestamp": [datetime(2024, 1, 1), datetime(2024, 2, 1)],
                "distance": [5000.0, 10000.0],
                "duration": [1800, 3600],
                "heart_rate": [140, 150]
            })
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
