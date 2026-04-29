# 索引管理器单元测试

import tempfile
from pathlib import Path

from src.core.storage.indexer import IndexManager


class TestIndexManager:
    """IndexManager 单元测试"""

    def test_init(self):
        """测试初始化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_file = Path(tmpdir) / "index.json"
            indexer = IndexManager(index_file=index_file)
            assert indexer.index_file == index_file

    def test_generate_fingerprint(self):
        """测试指纹生成"""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_file = Path(tmpdir) / "index.json"
            indexer = IndexManager(index_file=index_file)

            metadata = {
                "serial_number": "12345",
                "time_created": "2024-01-01",
                "total_distance": 5000,
                "filename": "test.fit",
            }

            fingerprint = indexer.generate_fingerprint(metadata)
            assert fingerprint is not None
            assert len(fingerprint) == 64

    def test_add_and_exists(self):
        """测试添加和检查指纹"""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_file = Path(tmpdir) / "index.json"
            indexer = IndexManager(index_file=index_file)

            fingerprint = "test_fingerprint_123"

            # 添加指纹
            result = indexer.add(fingerprint, {"filename": "test.fit"})
            assert result is True

            # 检查是否存在
            assert indexer.exists(fingerprint) is True

            # 重复添加应失败
            result = indexer.add(fingerprint, {"filename": "test.fit"})
            assert result is False

    def test_remove(self):
        """测试移除指纹"""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_file = Path(tmpdir) / "index.json"
            indexer = IndexManager(index_file=index_file)

            fingerprint = "test_fingerprint_456"
            indexer.add(fingerprint, {"filename": "test.fit"})

            assert indexer.exists(fingerprint) is True

            # 移除指纹
            result = indexer.remove(fingerprint)
            assert result is True

            assert indexer.exists(fingerprint) is False

    def test_get_all_fingerprints(self):
        """测试获取所有指纹"""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_file = Path(tmpdir) / "index.json"
            indexer = IndexManager(index_file=index_file)

            fingerprints = ["fp1", "fp2", "fp3"]
            for fp in fingerprints:
                indexer.add(fp, {"filename": f"test_{fp}.fit"})

            all_fps = indexer.get_all_fingerprints()
            assert len(all_fps) == 3
            assert set(all_fps) == set(fingerprints)

    def test_get_file_info(self):
        """测试获取文件信息"""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_file = Path(tmpdir) / "index.json"
            indexer = IndexManager(index_file=index_file)

            fingerprint = "test_fp_info"
            metadata = {
                "filename": "test.fit",
                "filepath": "/path/to/test.fit",
                "time_created": "2024-01-01",
            }
            indexer.add(fingerprint, metadata)

            info = indexer.get_file_info(fingerprint)
            assert info is not None
            assert info["filename"] == "test.fit"
