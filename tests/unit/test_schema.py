# Schema模块单元测试
# 测试Parquet Schema定义和数据标准化功能

import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

import polars as pl

from src.core.schema import (
    ParquetSchema,
    create_activity_id,
    create_schema_dataframe
)


class TestParquetSchema:
    """测试ParquetSchema类"""

    def test_get_schema(self):
        """测试获取完整Schema"""
        schema = ParquetSchema.get_schema()
        
        assert "activity_id" in schema
        assert "timestamp" in schema
        assert "source_file" in schema
        assert "filename" in schema
        assert "distance" in schema
        assert "duration" in schema
        assert "heart_rate" in schema
        assert "total_distance" in schema
        assert "total_timer_time" in schema
        assert "avg_heart_rate" in schema

    def test_get_required_fields(self):
        """测试获取必填字段"""
        required = ParquetSchema.get_required_fields()
        
        assert "activity_id" in required
        assert "timestamp" in required
        assert "source_file" in required
        assert "filename" in required
        assert "total_distance" in required
        assert "total_timer_time" in required

    def test_get_default_values(self):
        """测试获取默认值"""
        defaults = ParquetSchema.get_default_values()
        
        assert defaults["serial_number"] == "UNKNOWN"
        assert defaults["total_distance"] == 0.0
        assert defaults["record_count"] == 0

    def test_validate_dataframe_success(self):
        """测试验证DataFrame成功"""
        df = pl.DataFrame({
            "activity_id": ["test_123"],
            "timestamp": [datetime(2024, 1, 1, 12, 0, 0)],
            "source_file": ["test.fit"],
            "filename": ["test"],
            "serial_number": ["TEST1000"],
            "total_distance": [5000.0],
            "total_timer_time": [1800],
            "avg_heart_rate": [140],
            "cadence": [180],
            "record_count": [1]
        })
        
        # 先标准化再验证
        normalized_df = ParquetSchema.normalize_dataframe(df)
        result = ParquetSchema.validate_dataframe(normalized_df)
        assert result["valid"] is True

    def test_validate_dataframe_type_mismatch(self):
        """测试验证DataFrame类型不匹配"""
        df = pl.DataFrame({"activity_id": [123], "timestamp": ["2024-01-01"], "source_file": ["test.fit"], "filename": ["test"], "total_distance": [5000.0], "total_timer_time": [1800]})
        
        result = ParquetSchema.validate_dataframe(df)
        assert result["valid"] is False

    def test_normalize_dataframe_add_missing_columns(self):
        """测试标准化DataFrame添加缺失列"""
        df = pl.DataFrame({"activity_id": ["test_123"]})
        
        normalized = ParquetSchema.normalize_dataframe(df)
        
        assert "activity_id" in normalized.columns
        assert "timestamp" in normalized.columns
        assert "source_file" in normalized.columns

    def test_normalize_dataframe_convert_types(self):
        """测试标准化DataFrame转换类型"""
        df = pl.DataFrame({
            "activity_id": ["test_123"],
            "timestamp": ["2024-01-01"],
            "total_distance": ["1000"],
            "total_timer_time": ["3600"]
        })
        
        normalized = ParquetSchema.normalize_dataframe(df)
        
        assert "activity_id" in normalized.columns

    def test_validate_dataframe_empty(self):
        """测试验证空DataFrame"""
        df = pl.DataFrame()
        
        result = ParquetSchema.validate_dataframe(df)
        assert result["valid"] is False  # 空DataFrame缺少必填字段

    def test_validate_dataframe_partial_columns(self):
        """测试验证部分列的DataFrame"""
        df = pl.DataFrame({
            "activity_id": ["test_123"],
            "timestamp": [datetime.now()]
        })
        
        result = ParquetSchema.validate_dataframe(df)
        assert result["valid"] is False  # 缺少必填字段


class TestCreateActivityId:
    """测试create_activity_id函数"""

    def test_create_activity_id_basic(self):
        """测试基本活动ID创建"""
        filename = "test_run"
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        
        activity_id = create_activity_id(filename, timestamp)
        
        assert "test_run" in activity_id
        assert "20240101_120000" in activity_id

    def test_create_activity_id_with_special_chars(self):
        """测试包含特殊字符的文件名"""
        filename = "test-run_2024"
        timestamp = datetime(2024, 6, 15, 8, 30, 45)
        
        activity_id = create_activity_id(filename, timestamp)
        
        assert "test-run_2024" in activity_id
        assert "20240615_083045" in activity_id


class TestCreateSchemaDataFrame:
    """测试create_schema_dataframe函数"""

    def test_create_schema_dataframe_basic(self):
        """测试基本数据创建"""
        metadata = {
            "filename": "test_run",
            "serial_number": "TEST1000",
            "time_created": datetime(2024, 1, 1, 12, 0, 0),
            "total_distance": 5000,
            "total_timer_time": 1800,
            "total_calories": 300,
            "avg_heart_rate": 140,
            "max_heart_rate": 160,
            "record_count": 100
        }
        
        records = [
            {
                "timestamp": datetime(2024, 1, 1, 12, 0, 0),
                "distance": 50.0,
                "duration": 60.0,
                "heart_rate": 140
            }
        ]
        
        df = create_schema_dataframe(metadata, records)
        
        assert isinstance(df, pl.DataFrame)
        assert "activity_id" in df.columns
        assert "filename" in df.columns
        assert "serial_number" in df.columns
        assert len(df) == 1

    def test_create_schema_dataframe_multiple_records(self):
        """测试多条记录创建"""
        metadata = {
            "filename": "test_run",
            "serial_number": "TEST1000",
            "time_created": datetime(2024, 1, 1, 12, 0, 0),
            "total_distance": 10000,
            "total_timer_time": 3600,
            "total_calories": 600,
            "avg_heart_rate": 145,
            "max_heart_rate": 170,
            "record_count": 200
        }
        
        records = [
            {
                "timestamp": datetime(2024, 1, 1, 12, 0, 0),
                "distance": 50.0,
                "duration": 60.0,
                "heart_rate": 140
            },
            {
                "timestamp": datetime(2024, 1, 1, 12, 1, 0),
                "distance": 100.0,
                "duration": 120.0,
                "heart_rate": 145
            }
        ]
        
        df = create_schema_dataframe(metadata, records)
        
        assert len(df) == 2
        assert df.select(pl.col("distance").sum()).item() == 150.0

    def test_create_schema_dataframe_with_missing_fields(self):
        """测试包含缺失字段的数据"""
        metadata = {
            "filename": "test_run",
            "serial_number": "TEST1000",
            "time_created": datetime(2024, 1, 1, 12, 0, 0),
            "total_distance": 5000,
            "total_timer_time": 1800,
            "total_calories": 300
        }
        
        records = [
            {
                "timestamp": datetime(2024, 1, 1, 12, 0, 0),
                "distance": 50.0,
                "duration": 60.0
            }
        ]
        
        df = create_schema_dataframe(metadata, records)
        
        assert isinstance(df, pl.DataFrame)
        assert len(df) == 1

    def test_create_schema_dataframe_empty_records(self):
        """测试空记录列表"""
        metadata = {
            "filename": "test_run",
            "serial_number": "TEST1000",
            "time_created": datetime(2024, 1, 1, 12, 0, 0)
        }
        
        records = []
        
        df = create_schema_dataframe(metadata, records)
        
        assert isinstance(df, pl.DataFrame)
        assert len(df) == 0

    def test_create_schema_dataframe_default_values(self):
        """测试默认值填充"""
        metadata = {
            "filename": "test_run",
            "serial_number": "TEST1000",
            "time_created": datetime(2024, 1, 1, 12, 0, 0)
        }
        
        records = [
            {
                "timestamp": datetime(2024, 1, 1, 12, 0, 0),
                "distance": 50.0,
                "duration": 60.0
            }
        ]
        
        df = create_schema_dataframe(metadata, records)
        
        row = df.row(0, named=True)
        assert row["serial_number"] == "TEST1000"
        assert row["total_distance"] == 0.0
