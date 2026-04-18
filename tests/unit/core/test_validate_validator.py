import json
from pathlib import Path
from unittest.mock import patch

from src.core.config import ConfigManager
from src.core.validate.models import (
    ConnectivityResult,
    ErrorLevel,
    ValidationError,
    ValidationReport,
)
from src.core.validate.validator import ConfigValidator


class TestValidationModels:
    """验证模块数据结构测试"""

    def test_error_level_enum(self) -> None:
        assert ErrorLevel.ERROR.value == "error"
        assert ErrorLevel.WARNING.value == "warning"
        assert ErrorLevel.INFO.value == "info"

    def test_validation_error(self) -> None:
        err = ValidationError(
            level=ErrorLevel.ERROR,
            field="version",
            message="缺少版本号",
            suggestion="添加 version 字段",
        )
        assert err.level == ErrorLevel.ERROR
        assert err.field == "version"
        assert err.suggestion == "添加 version 字段"

    def test_validation_report_valid(self) -> None:
        report = ValidationReport(is_valid=True)
        assert report.is_valid is True
        assert report.errors == []

    def test_validation_report_invalid(self) -> None:
        report = ValidationReport(
            is_valid=False,
            errors=[
                ValidationError(level=ErrorLevel.ERROR, field="test", message="err")
            ],
        )
        assert report.is_valid is False
        assert len(report.errors) == 1

    def test_connectivity_result(self) -> None:
        result = ConnectivityResult(
            provider="openai", is_connected=True, response_time=0.5
        )
        assert result.provider == "openai"
        assert result.is_connected is True
        assert result.response_time == 0.5


class TestConfigValidator:
    """配置验证器测试"""

    def test_validate_format_no_config(self, tmp_path: Path) -> None:
        with patch.object(Path, "home", return_value=tmp_path):
            config = ConfigManager(allow_default=True)
            validator = ConfigValidator(config=config)

            errors = validator.validate_format()
            assert len(errors) == 0 or any("不存在" in e.message for e in errors)

    def test_validate_format_invalid_json(self, tmp_path: Path) -> None:
        config_dir = tmp_path / ".nanobot-runner"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "config.json").write_text("invalid json{{{", encoding="utf-8")

        with patch.object(Path, "home", return_value=tmp_path):
            config = ConfigManager(allow_default=True)
            validator = ConfigValidator(config=config)

            errors = validator.validate_format()
            assert any(e.level == ErrorLevel.ERROR for e in errors)

    def test_validate_completeness_missing_required(self, tmp_path: Path) -> None:
        with patch.object(Path, "home", return_value=tmp_path):
            config = ConfigManager(allow_default=True)
            validator = ConfigValidator(config=config)

            with patch.object(config, "load_config", return_value={}):
                errors = validator.validate_completeness()
                error_fields = [e.field for e in errors if e.level == ErrorLevel.ERROR]
                assert "version" in error_fields
                assert "data_dir" in error_fields

    def test_validate_completeness_missing_optional(self, tmp_path: Path) -> None:
        with patch.object(Path, "home", return_value=tmp_path):
            config = ConfigManager(allow_default=True)
            validator = ConfigValidator(config=config)

            with patch.object(
                config,
                "load_config",
                return_value={"version": "0.9.4", "data_dir": "/tmp/data"},
            ):
                errors = validator.validate_completeness()
                warning_fields = [
                    e.field for e in errors if e.level == ErrorLevel.WARNING
                ]
                assert "llm_provider" in warning_fields or "llm_model" in warning_fields

    def test_validate_validity_bad_version_format(self, tmp_path: Path) -> None:
        with patch.object(Path, "home", return_value=tmp_path):
            config = ConfigManager(allow_default=True)
            validator = ConfigValidator(config=config)

            with patch.object(
                config,
                "load_config",
                return_value={"version": "abc", "data_dir": "/tmp/data"},
            ):
                errors = validator.validate_validity()
                assert any(e.field == "version" for e in errors)

    def test_validate_validity_data_dir_not_directory(self, tmp_path: Path) -> None:
        existing_file = tmp_path / "not_a_dir"
        existing_file.write_text("file", encoding="utf-8")

        with patch.object(Path, "home", return_value=tmp_path):
            config = ConfigManager(allow_default=True)
            validator = ConfigValidator(config=config)

            with patch.object(
                config,
                "load_config",
                return_value={"version": "0.9.4", "data_dir": str(existing_file)},
            ):
                errors = validator.validate_validity()
                assert any(e.field == "data_dir" for e in errors)

    def test_validate_all(self, tmp_path: Path) -> None:
        config_dir = tmp_path / ".nanobot-runner"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "config.json").write_text(
            json.dumps({"version": "0.9.4", "data_dir": "/tmp/data"}),
            encoding="utf-8",
        )

        with patch.object(Path, "home", return_value=tmp_path):
            config = ConfigManager(allow_default=True)
            validator = ConfigValidator(config=config)

            report = validator.validate_all()
            assert isinstance(report, ValidationReport)

    def test_test_api_connectivity_no_key(self, tmp_path: Path) -> None:
        config_dir = tmp_path / ".nanobot-runner"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "config.json").write_text(
            json.dumps({"version": "0.9.4", "data_dir": "/tmp/data"}),
            encoding="utf-8",
        )

        with patch.object(Path, "home", return_value=tmp_path):
            config = ConfigManager(allow_default=True)
            validator = ConfigValidator(config=config)

            result = validator.test_api_connectivity()
            assert result.is_connected is False
