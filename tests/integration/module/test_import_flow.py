# 模块集成测试：导入流程

import tempfile
import pytest
from pathlib import Path

from src.core.importer import ImportService
from src.core.storage import StorageManager
from src.core.indexer import IndexManager


class TestImportIntegration:
    """导入流程集成测试"""
    
    def test_full_import_flow(self):
        """测试完整导入流程"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "data"
            data_dir.mkdir()
            
            # 初始化服务
            service = ImportService()
            service.storage = StorageManager(data_dir=data_dir)
            service.indexer = IndexManager(index_file=data_dir / "index.json")
            
            # 模拟导入流程
            metadata = {
                "serial_number": "12345",
                "time_created": "2024-01-01",
                "total_distance": 5000,
                "filename": "test.fit"
            }
            
            # 生成指纹
            fingerprint = service.indexer.generate_fingerprint(metadata)
            
            # 检查不存在
            assert not service.indexer.exists(fingerprint)
            
            # 添加指纹
            result = service.indexer.add(fingerprint, metadata)
            assert result is True
            
            # 检查存在
            assert service.indexer.exists(fingerprint)
            
            # 重复添加应失败
            result = service.indexer.add(fingerprint, metadata)
            assert result is False
    
    def test_storage_and_indexer_integration(self):
        """测试存储和索引器集成"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "data"
            data_dir.mkdir()
            
            storage = StorageManager(data_dir=data_dir)
            indexer = IndexManager(index_file=data_dir / "index.json")
            
            import polars as pl
            from datetime import datetime
            
            # 创建测试数据
            test_data = pl.DataFrame({
                "activity_id": ["test_001"],
                "timestamp": [datetime(2024, 1, 1)],
                "distance": [5000.0],
                "duration": [1800],
                "heart_rate": [140]
            })
            
            # 保存数据
            storage.save_to_parquet(test_data, 2024)
            
            # 生成并添加指纹
            metadata = {
                "serial_number": "12345",
                "time_created": "2024-01-01",
                "total_distance": 5000,
                "filename": "test.fit"
            }
            fingerprint = indexer.generate_fingerprint(metadata)
            indexer.add(fingerprint, metadata)
            
            # 验证数据
            stats = storage.get_stats()
            assert stats["total_records"] == 1
            
            # 验证索引
            assert indexer.exists(fingerprint)
