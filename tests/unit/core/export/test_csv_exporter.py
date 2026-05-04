# CSV 导出器单元测试
# 测试 format_name、UTF-8 BOM 编码、字段白名单过滤和路径穿越拒绝

from pathlib import Path

from src.core.export.csv_exporter import (
    CSV_FIELD_BLACKLIST,
    CSV_FIELD_WHITELIST,
    CsvExporter,
)
from src.core.export.models import ExportConfig, ExportResult


class TestCsvExporterFormatName:
    """format_name 测试类"""

    def test_format_name_returns_csv(self):
        """测试 format_name 返回 'csv'"""
        exporter = CsvExporter()
        assert exporter.format_name == "csv"


class TestCsvExporterEncoding:
    """编码测试类"""

    def test_export_uses_utf8_bom(self, tmp_path):
        """测试导出文件使用 UTF-8 BOM 编码"""
        exporter = CsvExporter()
        output_path = tmp_path / "test.csv"
        config = ExportConfig(output_path=output_path, encoding="utf-8-sig")
        # 使用白名单内的字段确保数据不被过滤掉
        data = [{"timestamp": "2024-01-01", "session_total_distance": 5000.0}]
        result = exporter.export(data, config)

        assert result.success is True
        content = output_path.read_bytes()
        # UTF-8 BOM 以 EF BB BF 开头
        assert content.startswith(b"\xef\xbb\xbf")

    def test_export_utf8_content(self, tmp_path):
        """测试中文字符正确写入"""
        exporter = CsvExporter()
        output_path = tmp_path / "test.csv"
        config = ExportConfig(output_path=output_path, encoding="utf-8-sig")
        data = [{"session_start_time": "2024-01-01", "session_total_distance": 5000.0}]
        result = exporter.export(data, config)

        assert result.success is True
        text = output_path.read_text(encoding="utf-8-sig")
        assert "session_start_time" in text
        assert "2024-01-01" in text


class TestCsvExporterFieldFilter:
    """字段白名单过滤测试类"""

    def test_whitelist_filters_fields(self, tmp_path):
        """测试字段白名单过滤正确"""
        exporter = CsvExporter()
        output_path = tmp_path / "test.csv"
        config = ExportConfig(output_path=output_path)
        data = [
            {
                "timestamp": "2024-01-01",
                "session_total_distance": 5000.0,
                "sha256": "abc123",  # 黑名单字段
                "internal_id": "xyz",  # 黑名单字段
            }
        ]
        result = exporter.export(data, config)

        assert result.success is True
        text = output_path.read_text(encoding="utf-8-sig")
        assert "timestamp" in text
        assert "session_total_distance" in text
        assert "sha256" not in text
        assert "internal_id" not in text

    def test_blacklist_fields(self):
        """测试黑名单字段定义"""
        assert "sha256" in CSV_FIELD_BLACKLIST
        assert "file_hash" in CSV_FIELD_BLACKLIST
        assert "fingerprint" in CSV_FIELD_BLACKLIST
        assert "internal_id" in CSV_FIELD_BLACKLIST
        assert "_raw_bytes" in CSV_FIELD_BLACKLIST

    def test_whitelist_fields(self):
        """测试白名单字段定义"""
        assert "timestamp" in CSV_FIELD_WHITELIST
        assert "session_total_distance" in CSV_FIELD_WHITELIST
        assert "session_vdot" in CSV_FIELD_WHITELIST
        assert "session_training_stress_score" in CSV_FIELD_WHITELIST

    def test_empty_data_returns_success(self, tmp_path):
        """测试空数据导出返回成功"""
        exporter = CsvExporter()
        output_path = tmp_path / "empty.csv"
        config = ExportConfig(output_path=output_path)
        result = exporter.export([], config)

        assert result.success is True
        assert result.record_count == 0
        assert result.file_path == output_path


class TestCsvExporterPathValidation:
    """路径校验测试类"""

    def test_rejects_path_traversal(self):
        """测试路径穿越攻击被拒绝"""
        exporter = CsvExporter()
        assert exporter.validate_output_path(Path("../secret.csv")) is False
        assert exporter.validate_output_path(Path("foo/../../bar.csv")) is False

    def test_accepts_safe_path(self):
        """测试安全路径被接受"""
        exporter = CsvExporter()
        assert exporter.validate_output_path(Path("./output.csv")) is True
        assert exporter.validate_output_path(Path("/tmp/output.csv")) is True

    def test_export_with_invalid_path(self, tmp_path):
        """测试导出时无效路径返回失败"""
        exporter = CsvExporter()
        config = ExportConfig(output_path=Path("../invalid.csv"))
        result = exporter.export([{"a": 1}], config)
        assert result.success is False
        assert "路径验证不通过" in result.message


class TestCsvExporterResult:
    """导出结果测试类"""

    def test_result_type(self, tmp_path):
        """测试返回 ExportResult 类型"""
        exporter = CsvExporter()
        output_path = tmp_path / "test.csv"
        config = ExportConfig(output_path=output_path)
        # 使用白名单字段确保记录被保留
        result = exporter.export(
            [{"timestamp": "2024-01-01", "session_total_distance": 5000.0}], config
        )
        assert isinstance(result, ExportResult)
        assert result.success is True
        assert result.record_count == 1
