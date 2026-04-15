"""ImportService 单元测试"""

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

import polars as pl
import pytest

from src.core.exceptions import ParseError
from src.core.importer import ImportService


class TestScanDirectory:
    """测试扫描目录"""

    def test_scan_directory_with_fit_files(self):
        """测试扫描包含FIT文件的目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            fit_file1 = tmpdir_path / "run1.fit"
            fit_file2 = tmpdir_path / "run2.fit"
            txt_file = tmpdir_path / "readme.txt"

            fit_file1.touch()
            fit_file2.touch()
            txt_file.touch()

            mock_context = Mock()
            importer = ImportService(mock_context)
            result = importer.scan_directory(tmpdir_path)

            assert len(result) == 2
            assert fit_file1 in result
            assert fit_file2 in result
            assert txt_file not in result

    def test_scan_directory_empty(self):
        """测试扫描空目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            mock_context = Mock()
            importer = ImportService(mock_context)
            result = importer.scan_directory(tmpdir_path)

            assert len(result) == 0

    def test_scan_directory_nested(self):
        """测试扫描嵌套目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            nested_dir = tmpdir_path / "2024" / "01"
            nested_dir.mkdir(parents=True)

            fit_file1 = tmpdir_path / "run1.fit"
            fit_file2 = nested_dir / "run2.fit"

            fit_file1.touch()
            fit_file2.touch()

            mock_context = Mock()
            importer = ImportService(mock_context)
            result = importer.scan_directory(tmpdir_path)

            assert len(result) == 2
            assert fit_file1 in result
            assert fit_file2 in result


class TestProcessFile:
    """测试处理单个文件"""

    @pytest.fixture
    def mock_context(self):
        """创建 Mock AppContext"""
        mock_context = Mock()
        mock_context.parser = Mock()
        mock_context.indexer = Mock()
        mock_context.storage = Mock()
        return mock_context

    @pytest.fixture
    def importer(self, mock_context):
        """创建 ImportService 实例"""
        return ImportService(mock_context)

    def test_process_file_success(self, importer, mock_context):
        """测试成功处理文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.fit"
            filepath.touch()

            mock_metadata = {
                "time_created": datetime(2024, 1, 1),
                "serial_number": "12345",
            }
            mock_context.parser.parse_file_metadata.return_value = mock_metadata
            mock_context.indexer.generate_fingerprint.return_value = "abc123"
            mock_context.indexer.exists.return_value = False

            mock_df = pl.DataFrame(
                {
                    "timestamp": [datetime(2024, 1, 1)],
                    "heart_rate": [140],
                }
            )
            mock_context.parser.parse_file.return_value = mock_df
            mock_context.storage.save_to_parquet.return_value = True

            mock_progress = Mock()
            mock_task_id = Mock()

            result = importer.process_file(filepath, mock_progress, mock_task_id)

            assert result["status"] == "added"
            assert result["message"] == "导入成功"
            assert "fingerprint" in result
            mock_context.indexer.add.assert_called_once()

    def test_process_file_parse_metadata_error(self, importer, mock_context):
        """测试解析元数据失败"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.fit"
            filepath.touch()

            mock_context.parser.parse_file_metadata.side_effect = ParseError("解析失败")

            mock_progress = Mock()
            mock_task_id = Mock()

            result = importer.process_file(filepath, mock_progress, mock_task_id)

            assert result["status"] == "error"
            assert "解析元数据失败" in result["message"]

    def test_process_file_no_metadata(self, importer, mock_context):
        """测试无法解析元数据"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.fit"
            filepath.touch()

            mock_context.parser.parse_file_metadata.return_value = {}

            mock_progress = Mock()
            mock_task_id = Mock()

            result = importer.process_file(filepath, mock_progress, mock_task_id)

            assert result["status"] == "skipped"
            assert "无法解析文件元数据" in result["message"]

    def test_process_file_duplicate(self, importer, mock_context):
        """测试重复文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.fit"
            filepath.touch()

            mock_metadata = {
                "time_created": datetime(2024, 1, 1),
                "serial_number": "12345",
            }
            mock_context.parser.parse_file_metadata.return_value = mock_metadata
            mock_context.indexer.generate_fingerprint.return_value = "abc123"
            mock_context.indexer.exists.return_value = True

            mock_progress = Mock()
            mock_task_id = Mock()

            result = importer.process_file(filepath, mock_progress, mock_task_id)

            assert result["status"] == "skipped"
            assert "文件已存在" in result["message"]

    def test_process_file_parse_error(self, importer, mock_context):
        """测试解析文件失败"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.fit"
            filepath.touch()

            mock_metadata = {
                "time_created": datetime(2024, 1, 1),
                "serial_number": "12345",
            }
            mock_context.parser.parse_file_metadata.return_value = mock_metadata
            mock_context.indexer.generate_fingerprint.return_value = "abc123"
            mock_context.indexer.exists.return_value = False
            mock_context.parser.parse_file.return_value = None

            mock_progress = Mock()
            mock_task_id = Mock()

            result = importer.process_file(filepath, mock_progress, mock_task_id)

            assert result["status"] == "skipped"
            assert "解析失败" in result["message"]

    def test_process_file_save_error(self, importer, mock_context):
        """测试保存文件失败"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.fit"
            filepath.touch()

            mock_metadata = {
                "time_created": datetime(2024, 1, 1),
                "serial_number": "12345",
            }
            mock_context.parser.parse_file_metadata.return_value = mock_metadata
            mock_context.indexer.generate_fingerprint.return_value = "abc123"
            mock_context.indexer.exists.return_value = False

            mock_df = pl.DataFrame(
                {
                    "timestamp": [datetime(2024, 1, 1)],
                    "heart_rate": [140],
                }
            )
            mock_context.parser.parse_file.return_value = mock_df
            mock_context.storage.save_to_parquet.return_value = False

            mock_progress = Mock()
            mock_task_id = Mock()

            result = importer.process_file(filepath, mock_progress, mock_task_id)

            assert result["status"] == "skipped"
            assert "保存失败" in result["message"]


class TestImportFile:
    """测试导入单个文件"""

    @pytest.fixture
    def mock_context(self):
        """创建 Mock AppContext"""
        mock_context = Mock()
        mock_context.parser = Mock()
        mock_context.indexer = Mock()
        mock_context.storage = Mock()
        return mock_context

    @pytest.fixture
    def importer(self, mock_context):
        """创建 ImportService 实例"""
        return ImportService(mock_context)

    def test_import_file_success(self, importer, mock_context):
        """测试成功导入文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.fit"
            filepath.touch()

            mock_metadata = {
                "time_created": datetime(2024, 1, 1),
                "serial_number": "12345",
            }
            mock_context.parser.parse_file_metadata.return_value = mock_metadata
            mock_context.indexer.generate_fingerprint.return_value = "abc123"
            mock_context.indexer.exists.return_value = False

            mock_df = pl.DataFrame(
                {
                    "timestamp": [datetime(2024, 1, 1)],
                    "heart_rate": [140],
                }
            )
            mock_context.parser.parse_file.return_value = mock_df
            mock_context.storage.save_to_parquet.return_value = True

            result = importer.import_file(filepath)

            assert result["status"] == "added"
            assert result["message"] == "导入成功"
            assert "fingerprint" in result

    def test_import_file_force(self, importer, mock_context):
        """测试强制导入重复文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.fit"
            filepath.touch()

            mock_metadata = {
                "time_created": datetime(2024, 1, 1),
                "serial_number": "12345",
            }
            mock_context.parser.parse_file_metadata.return_value = mock_metadata
            mock_context.indexer.generate_fingerprint.return_value = "abc123"
            mock_context.indexer.exists.return_value = True

            mock_df = pl.DataFrame(
                {
                    "timestamp": [datetime(2024, 1, 1)],
                    "heart_rate": [140],
                }
            )
            mock_context.parser.parse_file.return_value = mock_df
            mock_context.storage.save_to_parquet.return_value = True

            result = importer.import_file(filepath, force=True)

            assert result["status"] == "added"
            mock_context.indexer.add.assert_called_once()

    def test_import_file_duplicate_skip(self, importer, mock_context):
        """测试跳过重复文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.fit"
            filepath.touch()

            mock_metadata = {
                "time_created": datetime(2024, 1, 1),
                "serial_number": "12345",
            }
            mock_context.parser.parse_file_metadata.return_value = mock_metadata
            mock_context.indexer.generate_fingerprint.return_value = "abc123"
            mock_context.indexer.exists.return_value = True

            result = importer.import_file(filepath, force=False)

            assert result["status"] == "skipped"
            assert "文件已存在" in result["message"]

    def test_import_file_parse_error(self, importer, mock_context):
        """测试解析失败"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.fit"
            filepath.touch()

            mock_context.parser.parse_file_metadata.side_effect = ParseError("解析失败")

            result = importer.import_file(filepath)

            assert result["status"] == "error"
            assert "解析元数据失败" in result["message"]


class TestImportDirectory:
    """测试批量导入目录"""

    @pytest.fixture
    def mock_context(self):
        """创建 Mock AppContext"""
        mock_context = Mock()
        mock_context.parser = Mock()
        mock_context.indexer = Mock()
        mock_context.storage = Mock()
        return mock_context

    @pytest.fixture
    def importer(self, mock_context):
        """创建 ImportService 实例"""
        return ImportService(mock_context)

    def test_import_directory_empty(self, importer):
        """测试导入空目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            result = importer.import_directory(tmpdir_path)

            assert result["total"] == 0
            assert result["added"] == 0
            assert result["skipped"] == 0
            assert result["errors"] == 0

    def test_import_directory_with_files(self, importer, mock_context):
        """测试导入包含文件的目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            fit_file1 = tmpdir_path / "run1.fit"
            fit_file2 = tmpdir_path / "run2.fit"
            fit_file1.touch()
            fit_file2.touch()

            mock_metadata = {
                "time_created": datetime(2024, 1, 1),
                "serial_number": "12345",
            }
            mock_context.parser.parse_file_metadata.return_value = mock_metadata
            mock_context.indexer.generate_fingerprint.return_value = "abc123"
            mock_context.indexer.exists.return_value = False

            mock_df = pl.DataFrame(
                {
                    "timestamp": [datetime(2024, 1, 1)],
                    "heart_rate": [140],
                }
            )
            mock_context.parser.parse_file.return_value = mock_df
            mock_context.storage.save_to_parquet.return_value = True

            result = importer.import_directory(tmpdir_path)

            assert result["total"] == 2
            assert result["added"] == 2
            assert result["skipped"] == 0
            assert result["errors"] == 0

    def test_import_directory_with_duplicates(self, importer, mock_context):
        """测试导入包含重复文件的目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            fit_file1 = tmpdir_path / "run1.fit"
            fit_file2 = tmpdir_path / "run2.fit"
            fit_file1.touch()
            fit_file2.touch()

            mock_metadata = {
                "time_created": datetime(2024, 1, 1),
                "serial_number": "12345",
            }
            mock_context.parser.parse_file_metadata.return_value = mock_metadata
            mock_context.indexer.generate_fingerprint.return_value = "abc123"
            mock_context.indexer.exists.return_value = True

            result = importer.import_directory(tmpdir_path)

            assert result["total"] == 2
            assert result["added"] == 0
            assert result["skipped"] == 2
            assert result["errors"] == 0

    def test_import_directory_with_errors(self, importer, mock_context):
        """测试导入包含错误文件的目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            fit_file1 = tmpdir_path / "run1.fit"
            fit_file2 = tmpdir_path / "run2.fit"
            fit_file1.touch()
            fit_file2.touch()

            mock_context.parser.parse_file_metadata.side_effect = ParseError("解析失败")

            result = importer.import_directory(tmpdir_path)

            assert result["total"] == 2
            assert result["added"] == 0
            assert result["skipped"] == 0
            assert result["errors"] == 2
