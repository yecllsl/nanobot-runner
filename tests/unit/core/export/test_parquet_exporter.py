# Parquet 导出器单元测试
# 测试 format_name、不含 TSS/VDOT 计算字段

from pathlib import Path

from src.core.export.models import ExportConfig, ExportResult
from src.core.export.parquet_exporter import (
    COMPUTED_FIELDS,
    INTERNAL_FIELDS,
    RAW_FIELDS,
    ParquetExporter,
)


class TestParquetExporterFormatName:
    """format_name 测试类"""

    def test_format_name_returns_parquet(self):
        """测试 format_name 返回 'parquet'"""
        exporter = ParquetExporter()
        assert exporter.format_name == "parquet"


class TestParquetExporterFieldFilter:
    """字段过滤测试类"""

    def test_excludes_computed_fields(self, tmp_path):
        """测试不含 TSS/VDOT 计算字段"""
        exporter = ParquetExporter()
        output_path = tmp_path / "test.parquet"
        config = ExportConfig(output_path=output_path)
        data = [
            {
                "timestamp": "2024-01-01",
                "session_total_distance": 5000.0,
                "session_training_stress_score": 85.0,  # 计算字段
                "session_vdot": 45.2,  # 计算字段
            }
        ]
        result = exporter.export(data, config)

        assert result.success is True
        # Parquet 文件已生成
        assert output_path.exists()

    def test_raw_fields_definition(self):
        """测试原始字段定义"""
        assert "timestamp" in RAW_FIELDS
        assert "session_total_distance" in RAW_FIELDS
        assert "session_avg_heart_rate" in RAW_FIELDS

    def test_computed_fields_definition(self):
        """测试计算字段定义"""
        assert "session_training_stress_score" in COMPUTED_FIELDS
        assert "session_vdot" in COMPUTED_FIELDS
        assert "tss" in COMPUTED_FIELDS
        assert "vdot" in COMPUTED_FIELDS
        assert "atl" in COMPUTED_FIELDS
        assert "ctl" in COMPUTED_FIELDS
        assert "tsb" in COMPUTED_FIELDS

    def test_internal_fields_definition(self):
        """测试内部字段定义"""
        assert "sha256" in INTERNAL_FIELDS
        assert "file_hash" in INTERNAL_FIELDS
        assert "fingerprint" in INTERNAL_FIELDS
        assert "_raw_bytes" in INTERNAL_FIELDS

    def test_filter_raw_fields_excludes_computed(self):
        """测试 _filter_raw_fields 排除计算字段"""
        exporter = ParquetExporter()
        data = [
            {
                "timestamp": "2024-01-01",
                "session_total_distance": 5000.0,
                "session_training_stress_score": 85.0,
                "session_vdot": 45.2,
                "sha256": "abc",
            }
        ]
        filtered = exporter._filter_raw_fields(data)
        assert len(filtered) == 1
        assert "timestamp" in filtered[0]
        assert "session_total_distance" in filtered[0]
        assert "session_training_stress_score" not in filtered[0]
        assert "session_vdot" not in filtered[0]
        assert "sha256" not in filtered[0]

    def test_filter_raw_fields_fallback(self):
        """测试过滤后为空时回退保留非黑名单字段"""
        exporter = ParquetExporter()
        data = [
            {
                "custom_field": 123,
                "sha256": "abc",
                "session_vdot": 45.0,
            }
        ]
        filtered = exporter._filter_raw_fields(data)
        assert len(filtered) == 1
        assert "custom_field" in filtered[0]
        assert "sha256" not in filtered[0]
        assert "session_vdot" not in filtered[0]


class TestParquetExporterEmptyData:
    """空数据测试类"""

    def test_empty_data_writes_empty_parquet(self, tmp_path):
        """测试空数据写入空 Parquet 文件"""
        exporter = ParquetExporter()
        output_path = tmp_path / "empty.parquet"
        config = ExportConfig(output_path=output_path)
        result = exporter.export([], config)

        assert result.success is True
        assert result.record_count == 0
        assert output_path.exists()


class TestParquetExporterPathValidation:
    """路径校验测试类"""

    def test_rejects_path_traversal(self):
        """测试路径穿越攻击被拒绝"""
        exporter = ParquetExporter()
        assert exporter.validate_output_path(Path("../secret.parquet")) is False

    def test_accepts_safe_path(self):
        """测试安全路径被接受"""
        exporter = ParquetExporter()
        assert exporter.validate_output_path(Path("./output.parquet")) is True


class TestParquetExporterResult:
    """导出结果测试类"""

    def test_result_type(self, tmp_path):
        """测试返回 ExportResult 类型"""
        exporter = ParquetExporter()
        output_path = tmp_path / "test.parquet"
        config = ExportConfig(output_path=output_path)
        data = [{"timestamp": "2024-01-01", "session_total_distance": 5000.0}]
        result = exporter.export(data, config)
        assert isinstance(result, ExportResult)
        assert result.success is True
        assert result.record_count == 1
