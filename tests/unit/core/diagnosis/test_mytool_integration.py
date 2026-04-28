# MyTool集成单元测试

import json
from pathlib import Path

from src.core.diagnosis.mytool_integration import MyToolIntegration


class TestMyToolIntegration:
    """MyToolIntegration 测试"""

    def test_enable_self_reflection(self, tmp_path: Path):
        config_path = tmp_path / "config.json"
        config_path.write_text("{}", encoding="utf-8")
        mytool = MyToolIntegration(config_path)

        result = mytool.enable_self_reflection()
        assert result is True

        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
        assert config["tools"]["my"]["enable"] is True
        assert config["tools"]["my"]["allow_set"] is True

    def test_enable_parameter_tuning(self, tmp_path: Path):
        config_path = tmp_path / "config.json"
        config_path.write_text("{}", encoding="utf-8")
        mytool = MyToolIntegration(config_path)

        result = mytool.enable_parameter_tuning()
        assert result is True

        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
        assert config["tools"]["my"]["allow_set"] is True

    def test_disable_self_reflection(self, tmp_path: Path):
        config_path = tmp_path / "config.json"
        config_path.write_text(
            json.dumps({"tools": {"my": {"enable": True, "allow_set": True}}}),
            encoding="utf-8",
        )
        mytool = MyToolIntegration(config_path)

        result = mytool.disable_self_reflection()
        assert result is True

        report = mytool.get_reflection_report()
        assert report["self_reflection_enabled"] is False

    def test_disable_parameter_tuning(self, tmp_path: Path):
        config_path = tmp_path / "config.json"
        config_path.write_text(
            json.dumps({"tools": {"my": {"enable": True, "allow_set": True}}}),
            encoding="utf-8",
        )
        mytool = MyToolIntegration(config_path)

        result = mytool.disable_parameter_tuning()
        assert result is True

        report = mytool.get_reflection_report()
        assert report["parameter_tuning_enabled"] is False

    def test_is_enabled(self, tmp_path: Path):
        config_path = tmp_path / "config.json"
        config_path.write_text("{}", encoding="utf-8")
        mytool = MyToolIntegration(config_path)

        assert mytool.is_enabled() is False

        mytool.enable_self_reflection()
        assert mytool.is_enabled() is True

    def test_is_parameter_tuning_enabled(self, tmp_path: Path):
        config_path = tmp_path / "config.json"
        config_path.write_text("{}", encoding="utf-8")
        mytool = MyToolIntegration(config_path)

        assert mytool.is_parameter_tuning_enabled() is False

        mytool.enable_parameter_tuning()
        assert mytool.is_parameter_tuning_enabled() is True

    def test_get_reflection_report(self, tmp_path: Path):
        config_path = tmp_path / "config.json"
        config_path.write_text("{}", encoding="utf-8")
        mytool = MyToolIntegration(config_path)

        mytool.enable_self_reflection()
        report = mytool.get_reflection_report()

        assert report["self_reflection_enabled"] is True
        assert "capabilities" in report
        assert len(report["capabilities"]) > 0

    def test_config_file_nonexistent(self, tmp_path: Path):
        config_path = tmp_path / "nonexistent" / "config.json"
        mytool = MyToolIntegration(config_path)

        result = mytool.enable_self_reflection()
        assert result is True
        assert config_path.exists()

    def test_preserve_existing_config(self, tmp_path: Path):
        config_path = tmp_path / "config.json"
        existing_config = {
            "model": "gpt-4",
            "tools": {"weather": {"enable": True}},
        }
        config_path.write_text(json.dumps(existing_config), encoding="utf-8")
        mytool = MyToolIntegration(config_path)

        mytool.enable_self_reflection()

        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
        assert config["model"] == "gpt-4"
        assert config["tools"]["weather"]["enable"] is True
        assert config["tools"]["my"]["enable"] is True
