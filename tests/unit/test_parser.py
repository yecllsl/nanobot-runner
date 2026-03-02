# FIT文件解析器单元测试
# 测试FIT文件解析功能

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os

import polars as pl

from src.core.parser import FitParser


class MockFitMessage:
    """Mock FIT消息"""
    def __init__(self, name, data_list):
        self.name = name
        self._data_list = data_list
    
    def __iter__(self):
        return iter(self._data_list)


class MockFitData:
    """Mock FIT数据"""
    def __init__(self, name, value):
        self.name = name
        self.value = value


class TestFitParser:
    """测试FIT解析器"""

    def test_init(self):
        """测试初始化"""
        parser = FitParser()
        assert parser is not None

    def test_parse_file_success(self):
        """测试成功解析FIT文件"""
        parser = FitParser()
        
        # Mock fitparse.FitFile
        mock_record = MockFitMessage("record", [
            MockFitData("timestamp", "2024-01-01"),
            MockFitData("distance", 5000.0),
            MockFitData("duration", 1800),
            MockFitData("heart_rate", 140)
        ])
        
        mock_session = MockFitMessage("session", [
            MockFitData("total_distance", 5000.0),
            MockFitData("total_elapsed_time", 1800)
        ])
        
        mock_fit_file = Mock()
        mock_fit_file.get_messages.side_effect = lambda msg_type: {
            "record": [mock_record],
            "session": [mock_session]
        }.get(msg_type, [])
        
        with patch('fitparse.FitFile', return_value=mock_fit_file):
            with tempfile.NamedTemporaryFile(suffix='.fit', delete=False) as f:
                temp_path = Path(f.name)
            
            try:
                result = parser.parse_file(temp_path)
                
                assert result is not None
                assert isinstance(result, pl.DataFrame)
                assert result.height == 1
                assert "source_file" in result.columns
                assert "filename" in result.columns
            finally:
                os.unlink(temp_path)

    def test_parse_file_no_records(self):
        """测试没有记录数据的FIT文件"""
        parser = FitParser()
        
        mock_fit_file = Mock()
        mock_fit_file.get_messages.return_value = []
        
        with patch('fitparse.FitFile', return_value=mock_fit_file):
            with tempfile.NamedTemporaryFile(suffix='.fit', delete=False) as f:
                temp_path = Path(f.name)
            
            try:
                result = parser.parse_file(temp_path)
                
                assert result is None
            finally:
                os.unlink(temp_path)

    def test_parse_file_fit_parse_error(self):
        """测试FIT解析错误"""
        parser = FitParser()
        
        with patch('fitparse.FitFile', side_effect=Exception("Parse error")):
            with tempfile.NamedTemporaryFile(suffix='.fit', delete=False) as f:
                temp_path = Path(f.name)
            
            try:
                result = parser.parse_file(temp_path)
                
                assert result is None
            finally:
                os.unlink(temp_path)

    def test_parse_file_generic_error(self):
        """测试通用错误"""
        parser = FitParser()
        
        with patch('fitparse.FitFile', side_effect=Exception("Unknown error")):
            with tempfile.NamedTemporaryFile(suffix='.fit', delete=False) as f:
                temp_path = Path(f.name)
            
            try:
                result = parser.parse_file(temp_path)
                
                assert result is None
            finally:
                os.unlink(temp_path)

    def test_parse_file_metadata_success(self):
        """测试成功解析元数据"""
        parser = FitParser()
        
        mock_file_id = MockFitMessage("file_id", [
            MockFitData("serial_number", "12345"),
            MockFitData("time_created", "2024-01-01"),
            MockFitData("total_distance", 5000)
        ])
        
        mock_fit_file = Mock()
        mock_fit_file.get_messages.side_effect = lambda msg_type: {
            "file_id": [mock_file_id]
        }.get(msg_type, [])
        
        with patch('fitparse.FitFile', return_value=mock_fit_file):
            with tempfile.NamedTemporaryFile(suffix='.fit', delete=False) as f:
                temp_path = Path(f.name)
            
            try:
                result = parser.parse_file_metadata(temp_path)
                
                assert result["serial_number"] == "12345"
                assert result["time_created"] == "2024-01-01"
                assert result["total_distance"] == 5000
                assert result["filename"] == temp_path.stem
                assert result["filepath"] == str(temp_path)
            finally:
                os.unlink(temp_path)

    def test_parse_file_metadata_missing_fields(self):
        """测试缺少字段的元数据解析"""
        parser = FitParser()
        
        mock_file_id = MockFitMessage("file_id", [
            MockFitData("serial_number", "12345")
        ])
        
        mock_fit_file = Mock()
        mock_fit_file.get_messages.side_effect = lambda msg_type: {
            "file_id": [mock_file_id]
        }.get(msg_type, [])
        
        with patch('fitparse.FitFile', return_value=mock_fit_file):
            with tempfile.NamedTemporaryFile(suffix='.fit', delete=False) as f:
                temp_path = Path(f.name)
            
            try:
                result = parser.parse_file_metadata(temp_path)
                
                assert result["serial_number"] == "12345"
                assert result["time_created"] is None
                assert result["total_distance"] is None
            finally:
                os.unlink(temp_path)

    def test_parse_file_metadata_error(self):
        """测试元数据解析错误"""
        parser = FitParser()
        
        with patch('fitparse.FitFile', side_effect=Exception("Parse error")):
            with tempfile.NamedTemporaryFile(suffix='.fit', delete=False) as f:
                temp_path = Path(f.name)
            
            try:
                result = parser.parse_file_metadata(temp_path)
                
                # 错误时应返回默认值
                assert result is not None
                assert result["filepath"] == str(temp_path)
            finally:
                os.unlink(temp_path)
