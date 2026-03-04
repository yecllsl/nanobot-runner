# 数据导入服务单元测试
# 测试数据导入功能

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os

from src.core.importer import ImportService


class TestImportService:
    """测试导入服务"""

    def test_init(self):
        """测试初始化"""
        service = ImportService()
        assert service is not None
        assert hasattr(service, 'parser')
        assert hasattr(service, 'indexer')
        assert hasattr(service, 'storage')

    def test_scan_directory(self):
        """测试扫描目录"""
        service = ImportService()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试文件
            Path(tmpdir).mkdir(parents=True, exist_ok=True)
            fit_file = Path(tmpdir) / "test.fit"
            fit_file.touch()
            
            # 创建非FIT文件
            txt_file = Path(tmpdir) / "test.txt"
            txt_file.touch()
            
            result = service.scan_directory(Path(tmpdir))
            
            assert len(result) == 1
            assert result[0] == fit_file

    def test_scan_directory_nested(self):
        """测试递归扫描目录"""
        service = ImportService()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建子目录
            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()
            
            # 创建FIT文件
            fit_file1 = Path(tmpdir) / "test1.fit"
            fit_file1.touch()
            fit_file2 = subdir / "test2.fit"
            fit_file2.touch()
            
            result = service.scan_directory(Path(tmpdir))
            
            assert len(result) == 2

    def test_import_file_success(self):
        """测试成功导入单个文件"""
        service = ImportService()
        
        with tempfile.NamedTemporaryFile(suffix='.fit', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            mock_metadata = {
                "serial_number": "12345",
                "time_created": "2024-01-01",
                "total_distance": 5000,
                "filename": temp_path.stem,
                "filepath": str(temp_path)
            }
            
            mock_df = Mock()
            mock_df.select.return_value.row.return_value = [2024]
            
            with patch.object(service.parser, 'parse_file_metadata', return_value=mock_metadata), \
                 patch.object(service.indexer, 'exists', return_value=False), \
                 patch.object(service.parser, 'parse_file', return_value=mock_df), \
                 patch.object(service.storage, 'save_to_parquet', return_value=True), \
                 patch.object(service.indexer, 'add', return_value=None):
                
                result = service.import_file(temp_path)
                
                assert result["status"] == "added"
                assert "导入成功" in result["message"]
        finally:
            os.unlink(temp_path)

    def test_import_file_no_metadata(self):
        """测试无法解析元数据的文件"""
        service = ImportService()
        
        with tempfile.NamedTemporaryFile(suffix='.fit', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            with patch.object(service.parser, 'parse_file_metadata', return_value={}), \
                 patch.object(service.parser, 'parse_file') as mock_parse:
                
                result = service.import_file(temp_path)
                
                assert result["status"] == "error"
                assert "无法解析元数据" in result["message"]
                mock_parse.assert_not_called()
        finally:
            os.unlink(temp_path)

    def test_import_file_duplicate(self):
        """测试重复文件导入"""
        service = ImportService()
        
        with tempfile.NamedTemporaryFile(suffix='.fit', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            mock_metadata = {
                "serial_number": "12345",
                "time_created": "2024-01-01",
                "total_distance": 5000,
                "filename": temp_path.stem,
                "filepath": str(temp_path)
            }
            
            with patch.object(service.parser, 'parse_file_metadata', return_value=mock_metadata), \
                 patch.object(service.indexer, 'exists', return_value=True), \
                 patch.object(service.parser, 'parse_file') as mock_parse, \
                 patch.object(service.storage, 'save_to_parquet') as mock_save:
                
                result = service.import_file(temp_path)
                
                assert result["status"] == "skipped"
                assert "文件已存在" in result["message"]
                mock_parse.assert_not_called()
                mock_save.assert_not_called()
        finally:
            os.unlink(temp_path)

    def test_import_file_parse_error(self):
        """测试解析失败的文件"""
        service = ImportService()
        
        with tempfile.NamedTemporaryFile(suffix='.fit', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            mock_metadata = {
                "serial_number": "12345",
                "time_created": "2024-01-01",
                "total_distance": 5000,
                "filename": temp_path.stem,
                "filepath": str(temp_path)
            }
            
            with patch.object(service.parser, 'parse_file_metadata', return_value=mock_metadata), \
                 patch.object(service.indexer, 'exists', return_value=False), \
                 patch.object(service.parser, 'parse_file', return_value=None):
                
                result = service.import_file(temp_path)
                
                assert result["status"] == "error"
                assert "解析失败" in result["message"]
        finally:
            os.unlink(temp_path)

    def test_import_file_save_error(self):
        """测试保存失败的文件"""
        service = ImportService()
        
        with tempfile.NamedTemporaryFile(suffix='.fit', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            mock_metadata = {
                "serial_number": "12345",
                "time_created": "2024-01-01",
                "total_distance": 5000,
                "filename": temp_path.stem,
                "filepath": str(temp_path)
            }
            
            mock_df = Mock()
            mock_df.select.return_value.row.return_value = [2024]
            
            with patch.object(service.parser, 'parse_file_metadata', return_value=mock_metadata), \
                 patch.object(service.indexer, 'exists', return_value=False), \
                 patch.object(service.parser, 'parse_file', return_value=mock_df), \
                 patch.object(service.storage, 'save_to_parquet', return_value=False), \
                 patch.object(service.indexer, 'add') as mock_add:
                
                result = service.import_file(temp_path)
                
                assert result["status"] == "error"
                assert "保存失败" in result["message"]
                mock_add.assert_not_called()
        finally:
            os.unlink(temp_path)

    def test_import_directory_empty(self):
        """测试空目录导入"""
        service = ImportService()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(service, 'scan_directory', return_value=[]):
                result = service.import_directory(Path(tmpdir))
                
                assert result["total"] == 0
                assert result["added"] == 0
                assert result["skipped"] == 0
                assert result["errors"] == 0

    def test_import_directory_success(self):
        """测试成功导入目录"""
        service = ImportService()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试文件
            fit_file = Path(tmpdir) / "test.fit"
            fit_file.touch()
            
            mock_metadata = {
                "serial_number": "12345",
                "time_created": "2024-01-01",
                "total_distance": 5000,
                "filename": "test",
                "filepath": str(fit_file)
            }
            
            mock_df = Mock()
            mock_df.select.return_value.row.return_value = [2024]
            
            with patch.object(service, 'scan_directory', return_value=[fit_file]), \
                 patch.object(service.parser, 'parse_file_metadata', return_value=mock_metadata), \
                 patch.object(service.indexer, 'exists', return_value=False), \
                 patch.object(service.parser, 'parse_file', return_value=mock_df), \
                 patch.object(service.storage, 'save_to_parquet', return_value=True), \
                 patch.object(service.indexer, 'add', return_value=None):
                
                result = service.import_directory(Path(tmpdir))
                
                assert result["total"] == 1
                assert result["added"] == 1
                assert result["skipped"] == 0
                assert result["errors"] == 0

    def test_import_directory_mixed(self):
        """测试混合状态导入"""
        service = ImportService()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试文件
            fit_file1 = Path(tmpdir) / "test1.fit"
            fit_file1.touch()
            fit_file2 = Path(tmpdir) / "test2.fit"
            fit_file2.touch()
            
            mock_metadata1 = {
                "serial_number": "12345",
                "time_created": "2024-01-01",
                "total_distance": 5000,
                "filename": "test1",
                "filepath": str(fit_file1)
            }
            
            mock_metadata2 = {
                "serial_number": "67890",
                "time_created": "2024-01-02",
                "total_distance": 10000,
                "filename": "test2",
                "filepath": str(fit_file2)
            }
            
            mock_df = Mock()
            mock_df.select.return_value.row.return_value = [2024]
            
            with patch.object(service, 'scan_directory', return_value=[fit_file1, fit_file2]), \
                 patch.object(service.parser, 'parse_file_metadata', side_effect=[mock_metadata1, mock_metadata2]), \
                 patch.object(service.indexer, 'exists', side_effect=[False, True]), \
                 patch.object(service.parser, 'parse_file', return_value=mock_df), \
                 patch.object(service.storage, 'save_to_parquet', return_value=True), \
                 patch.object(service.indexer, 'add', return_value=None):
                
                result = service.import_directory(Path(tmpdir))
                
                assert result["total"] == 2
                assert result["added"] == 1
                assert result["skipped"] == 1
                assert result["errors"] == 0


class TestImportServiceAdvanced:
    """测试导入服务高级功能"""

    def test_process_file_with_progress(self):
        """测试带进度条的文件处理"""
        service = ImportService()
        
        with tempfile.NamedTemporaryFile(suffix='.fit', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            mock_metadata = {
                "serial_number": "12345",
                "time_created": "2024-01-01",
                "total_distance": 5000,
                "filename": temp_path.stem,
                "filepath": str(temp_path)
            }
            
            mock_df = Mock()
            mock_df.select.return_value.row.return_value = [2024]
            
            with patch.object(service.parser, 'parse_file_metadata', return_value=mock_metadata), \
                 patch.object(service.indexer, 'exists', return_value=False), \
                 patch.object(service.parser, 'parse_file', return_value=mock_df), \
                 patch.object(service.storage, 'save_to_parquet', return_value=True), \
                 patch.object(service.indexer, 'add', return_value=None):
                
                from rich.progress import Progress
                progress = Progress()
                task_id = progress.add_task("测试", total=1)
                
                try:
                    result = service.process_file(temp_path, progress, task_id)
                    
                    assert result["status"] == "added"
                finally:
                    progress.stop()
        finally:
            os.unlink(temp_path)

    def test_import_file_with_custom_year(self):
        """测试自定义年份的导入"""
        service = ImportService()
        
        with tempfile.NamedTemporaryFile(suffix='.fit', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            mock_metadata = {
                "serial_number": "12345",
                "time_created": "2023-01-01",
                "total_distance": 5000,
                "filename": temp_path.stem,
                "filepath": str(temp_path)
            }
            
            mock_df = Mock()
            mock_df.select.return_value.row.return_value = [2023]
            
            with patch.object(service.parser, 'parse_file_metadata', return_value=mock_metadata), \
                 patch.object(service.indexer, 'exists', return_value=False), \
                 patch.object(service.parser, 'parse_file', return_value=mock_df), \
                 patch.object(service.storage, 'save_to_parquet') as mock_save, \
                 patch.object(service.indexer, 'add', return_value=None):
                
                service.import_file(temp_path)
                
                mock_save.assert_called_once()
                call_args = mock_save.call_args
                assert call_args[0][1] == 2023
        finally:
            os.unlink(temp_path)

    def test_import_file_fingerprint_generation(self):
        """测试指纹生成"""
        service = ImportService()
        
        with tempfile.NamedTemporaryFile(suffix='.fit', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            mock_metadata = {
                "serial_number": "TEST123",
                "time_created": "2024-01-01",
                "total_distance": 5000,
                "filename": temp_path.stem,
                "filepath": str(temp_path)
            }
            
            mock_df = Mock()
            mock_df.select.return_value.row.return_value = [2024]
            
            with patch.object(service.parser, 'parse_file_metadata', return_value=mock_metadata), \
                 patch.object(service.indexer, 'exists', return_value=False), \
                 patch.object(service.parser, 'parse_file', return_value=mock_df), \
                 patch.object(service.storage, 'save_to_parquet', return_value=True), \
                 patch.object(service.indexer, 'add', return_value=None):
                
                result = service.import_file(temp_path)
                
                assert "fingerprint" in result
                assert len(result["fingerprint"]) == 64
        finally:
            os.unlink(temp_path)

    def test_import_file_error_handling(self):
        """测试错误处理"""
        service = ImportService()
        
        with tempfile.NamedTemporaryFile(suffix='.fit', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            with patch.object(service.parser, 'parse_file_metadata', side_effect=Exception("解析错误")):
                with pytest.raises(Exception):
                    service.import_file(temp_path)
        finally:
            os.unlink(temp_path)

    def test_scan_directory_with_symlink(self):
        """测试带符号链接的目录扫描"""
        service = ImportService()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试文件
            fit_file = Path(tmpdir) / "test.fit"
            fit_file.touch()
            
            # 创建符号链接
            try:
                link_file = Path(tmpdir) / "link.fit"
                link_file.symlink_to(fit_file)
            except (OSError, NotImplementedError):
                # Windows上可能不支持符号链接
                pytest.skip("系统不支持符号链接")
            
            result = service.scan_directory(Path(tmpdir))
            
            # 符号链接也会被扫描到
            assert len(result) >= 1
