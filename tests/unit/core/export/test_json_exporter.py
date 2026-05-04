# JSON 导出器单元测试
# 测试 format_name、元数据包含、标准 JSON 格式

import json
from pathlib import Path

from src.core.export.json_exporter import JsonExporter
from src.core.export.models import ExportConfig, ExportResult


class TestJsonExporterFormatName:
    """format_name 测试类"""

    def test_format_name_returns_json(self):
        """测试 format_name 返回 'json'"""
        exporter = JsonExporter()
        assert exporter.format_name == "json"


class TestJsonExporterMetadata:
    """元数据测试类"""

    def test_export_contains_metadata(self, tmp_path):
        """测试导出包含元数据（导出时间、记录数）"""
        exporter = JsonExporter()
        output_path = tmp_path / "test.json"
        config = ExportConfig(output_path=output_path)
        data = [
            {"timestamp": "2024-01-01", "distance": 5000.0},
            {"timestamp": "2024-01-02", "distance": 8000.0},
        ]
        result = exporter.export(data, config)

        assert result.success is True
        assert result.record_count == 2

        content = json.loads(output_path.read_text(encoding="utf-8"))
        assert "metadata" in content
        assert "data" in content
        assert content["metadata"]["record_count"] == 2
        assert "export_time" in content["metadata"]
        assert content["metadata"]["format_version"] == "1.0"
        assert content["metadata"]["source"] == "nanobot-runner"

    def test_export_empty_data_metadata(self, tmp_path):
        """测试空数据也包含元数据"""
        exporter = JsonExporter()
        output_path = tmp_path / "empty.json"
        config = ExportConfig(output_path=output_path)
        result = exporter.export([], config)

        assert result.success is True
        assert result.record_count == 0

        content = json.loads(output_path.read_text(encoding="utf-8"))
        assert content["metadata"]["record_count"] == 0
        assert content["data"] == []


class TestJsonExporterFormat:
    """JSON 格式测试类"""

    def test_standard_json_format(self, tmp_path):
        """测试符合标准 JSON 格式"""
        exporter = JsonExporter()
        output_path = tmp_path / "test.json"
        config = ExportConfig(output_path=output_path)
        data = [{"name": "run1", "value": 100}]
        result = exporter.export(data, config)

        assert result.success is True
        raw_text = output_path.read_text(encoding="utf-8")
        # 验证是合法 JSON
        parsed = json.loads(raw_text)
        assert isinstance(parsed, dict)
        assert isinstance(parsed["data"], list)

    def test_pretty_print_indent(self, tmp_path):
        """测试格式化缩进输出"""
        exporter = JsonExporter()
        output_path = tmp_path / "test.json"
        config = ExportConfig(output_path=output_path)
        data = [{"a": 1}]
        exporter.export(data, config)

        raw_text = output_path.read_text(encoding="utf-8")
        # 验证存在 2 空格缩进
        assert '  "metadata"' in raw_text or '  "data"' in raw_text

    def test_unicode_support(self, tmp_path):
        """测试 Unicode 字符正确编码"""
        exporter = JsonExporter()
        output_path = tmp_path / "test.json"
        config = ExportConfig(output_path=output_path)
        data = [{"notes": "晨跑测试"}]
        exporter.export(data, config)

        content = json.loads(output_path.read_text(encoding="utf-8"))
        assert content["data"][0]["notes"] == "晨跑测试"

    def test_no_bom(self, tmp_path):
        """测试 JSON 文件不含 BOM"""
        exporter = JsonExporter()
        output_path = tmp_path / "test.json"
        config = ExportConfig(output_path=output_path, encoding="utf-8-sig")
        data = [{"a": 1}]
        exporter.export(data, config)

        raw_bytes = output_path.read_bytes()
        # JSON 不应以 BOM 开头
        assert not raw_bytes.startswith(b"\xef\xbb\xbf")


class TestJsonExporterPathValidation:
    """路径校验测试类"""

    def test_rejects_path_traversal(self):
        """测试路径穿越攻击被拒绝"""
        exporter = JsonExporter()
        assert exporter.validate_output_path(Path("../secret.json")) is False

    def test_accepts_safe_path(self):
        """测试安全路径被接受"""
        exporter = JsonExporter()
        assert exporter.validate_output_path(Path("./output.json")) is True

    def test_rejects_unresolvable_path(self):
        """测试无法解析的路径被拒绝"""
        exporter = JsonExporter()
        assert exporter.validate_output_path(Path("\x00invalid.json")) is False

    def test_parent_dir_not_exists_accepted(self):
        """测试父目录不存在时路径仍被接受（导出时会自动创建）"""
        exporter = JsonExporter()
        assert exporter.validate_output_path(Path("./nonexist/output.json")) is True

    def test_rejects_no_write_permission(self, tmp_path):
        """测试父目录无写权限时路径被拒绝"""
        exporter = JsonExporter()
        import os
        import stat

        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()
        if os.name == "posix":
            os.chmod(str(readonly_dir), stat.S_IRUSR | stat.S_IXUSR)
            try:
                assert (
                    exporter.validate_output_path(readonly_dir / "output.json") is False
                )
            finally:
                os.chmod(str(readonly_dir), stat.S_IRWXU)
        else:
            # Windows 下 os.access 行为不同，仅验证不抛异常
            result = exporter.validate_output_path(readonly_dir / "output.json")
            assert isinstance(result, bool)


class TestJsonExporterResult:
    """导出结果测试类"""

    def test_result_type(self, tmp_path):
        """测试返回 ExportResult 类型"""
        exporter = JsonExporter()
        output_path = tmp_path / "test.json"
        config = ExportConfig(output_path=output_path)
        result = exporter.export([{"a": 1}], config)
        assert isinstance(result, ExportResult)
        assert result.success is True

    def test_export_with_invalid_path(self):
        """测试导出时无效路径返回失败结果"""
        exporter = JsonExporter()
        config = ExportConfig(output_path=Path("../invalid.json"))
        result = exporter.export([{"a": 1}], config)
        assert result.success is False
        assert "路径验证不通过" in result.message

    def test_empty_data_json_structure(self, tmp_path):
        """测试空数据导出的 JSON 结构完整性"""
        exporter = JsonExporter()
        output_path = tmp_path / "empty.json"
        config = ExportConfig(output_path=output_path)
        result = exporter.export([], config)

        assert result.success is True
        content = json.loads(output_path.read_text(encoding="utf-8"))
        assert "metadata" in content
        assert "data" in content
        assert content["data"] == []
        assert content["metadata"]["record_count"] == 0
        assert "export_time" in content["metadata"]
        assert "format_version" in content["metadata"]

    def test_export_creates_parent_directory(self, tmp_path):
        """测试导出时自动创建父目录"""
        exporter = JsonExporter()
        output_path = tmp_path / "subdir" / "nested" / "test.json"
        config = ExportConfig(output_path=output_path)
        data = [{"timestamp": "2024-01-01", "distance": 5000.0}]
        result = exporter.export(data, config)

        assert result.success is True
        assert output_path.exists()
