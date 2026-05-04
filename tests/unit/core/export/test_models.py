# 导出模块数据模型单元测试
# 测试 ExportConfig / ExportResult 的不可变性和字段默认值

from dataclasses import FrozenInstanceError
from datetime import datetime
from pathlib import Path

import pytest

from src.core.export.models import ExportConfig, ExportResult


class TestExportConfig:
    """ExportConfig 数据模型测试类"""

    def test_create_required(self):
        """测试仅提供必填字段"""
        config = ExportConfig(output_path=Path("/tmp/test.csv"))
        assert config.output_path == Path("/tmp/test.csv")
        assert config.start_date is None
        assert config.end_date is None
        assert config.include_computed_fields is True
        assert config.encoding == "utf-8-sig"

    def test_create_full(self):
        """测试提供全部字段"""
        start = datetime(2024, 1, 1)
        end = datetime(2024, 3, 31)
        config = ExportConfig(
            output_path=Path("/tmp/test.json"),
            start_date=start,
            end_date=end,
            include_computed_fields=False,
            encoding="utf-8",
        )
        assert config.output_path == Path("/tmp/test.json")
        assert config.start_date == start
        assert config.end_date == end
        assert config.include_computed_fields is False
        assert config.encoding == "utf-8"

    def test_frozen_immutable(self):
        """测试 frozen dataclass 不可变性"""
        config = ExportConfig(output_path=Path("/tmp/test.csv"))
        with pytest.raises(FrozenInstanceError):
            config.output_path = Path("/tmp/other.csv")

    def test_default_encoding_utf8_bom(self):
        """测试默认编码为 utf-8-sig（带 BOM）"""
        config = ExportConfig(output_path=Path("test.csv"))
        assert config.encoding == "utf-8-sig"

    def test_default_include_computed_fields_true(self):
        """测试默认包含计算字段为 True"""
        config = ExportConfig(output_path=Path("test.csv"))
        assert config.include_computed_fields is True

    def test_path_type(self):
        """测试 output_path 字段类型为 Path"""
        config = ExportConfig(output_path=Path("test.csv"))
        assert isinstance(config.output_path, Path)


class TestExportResult:
    """ExportResult 数据模型测试类"""

    def test_create_success(self):
        """测试成功结果构造"""
        result = ExportResult(
            success=True,
            record_count=100,
            file_path=Path("/tmp/out.csv"),
            message="导出成功",
            duration_ms=150,
        )
        assert result.success is True
        assert result.record_count == 100
        assert result.file_path == Path("/tmp/out.csv")
        assert result.message == "导出成功"
        assert result.duration_ms == 150

    def test_create_failure(self):
        """测试失败结果构造"""
        result = ExportResult(
            success=False,
            record_count=0,
            file_path=None,
            message="导出失败：路径无效",
            duration_ms=0,
        )
        assert result.success is False
        assert result.record_count == 0
        assert result.file_path is None
        assert result.message == "导出失败：路径无效"
        assert result.duration_ms == 0

    def test_frozen_immutable(self):
        """测试 frozen dataclass 不可变性"""
        result = ExportResult(
            success=True,
            record_count=10,
            file_path=Path("test.csv"),
            message="ok",
            duration_ms=50,
        )
        with pytest.raises(FrozenInstanceError):
            result.success = False

    def test_zero_record_count(self):
        """测试零记录边界场景"""
        result = ExportResult(
            success=True,
            record_count=0,
            file_path=Path("empty.csv"),
            message="空数据导出成功",
            duration_ms=10,
        )
        assert result.record_count == 0
        assert result.success is True
