import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from src.core.config import ConfigManager
from src.core.validate.models import (
    ConnectivityResult,
    ErrorLevel,
    ValidationError,
    ValidationReport,
)
from src.core.validate.validator import ConfigValidator


@pytest.fixture(autouse=True)
def reset_config_cache():
    """每个测试前重置 ConfigManager 缓存"""
    ConfigManager.reset_cache()
    yield
    ConfigManager.reset_cache()


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
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                config = ConfigManager(allow_default=True)
                validator = ConfigValidator(config=config)

                errors = validator.validate_format()
                assert len(errors) == 0 or any("不存在" in e.message for e in errors)

    def test_validate_format_invalid_json(self, tmp_path: Path) -> None:
        config_dir = tmp_path / ".nanobot-runner"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "config.json").write_text("invalid json{{{", encoding="utf-8")

        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                config = ConfigManager(allow_default=True)
                validator = ConfigValidator(config=config)

                errors = validator.validate_format()
                assert any(e.level == ErrorLevel.ERROR for e in errors)

    def test_validate_completeness_missing_required(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                config = ConfigManager(allow_default=True)
                validator = ConfigValidator(config=config)

                with patch.object(config, "load_config", return_value={}):
                    errors = validator.validate_completeness()
                    error_fields = [
                        e.field for e in errors if e.level == ErrorLevel.ERROR
                    ]
                    assert "version" in error_fields
                    assert "data_dir" in error_fields

    def test_validate_completeness_missing_optional(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {}, clear=True):
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
                    assert (
                        "llm_provider" in warning_fields
                        or "llm_model" in warning_fields
                    )

    def test_validate_validity_bad_version_format(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {}, clear=True):
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

        with patch.dict(os.environ, {}, clear=True):
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

        with patch.dict(os.environ, {}, clear=True):
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

        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                config = ConfigManager(allow_default=True)
                validator = ConfigValidator(config=config)

                result = validator.test_api_connectivity()
                assert result.is_connected is False

    def test_validate_format_config_not_dict(self, tmp_path: Path) -> None:
        config_dir = tmp_path / ".nanobot-runner"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "config.json").write_text('"not a dict"', encoding="utf-8")

        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                config = ConfigManager(allow_default=True)
                validator = ConfigValidator(config=config)

                errors = validator.validate_format()
                assert any("根元素必须是对象" in e.message for e in errors)

    def test_validate_format_os_error(self, tmp_path: Path) -> None:
        config_dir = tmp_path / ".nanobot-runner"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "config.json"
        config_file.write_text("{}", encoding="utf-8")

        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                config = ConfigManager(allow_default=True)
                validator = ConfigValidator(config=config)

                with patch("builtins.open", side_effect=OSError("permission denied")):
                    errors = validator.validate_format()
                    assert any("文件读取失败" in e.message for e in errors)

    def test_validate_completeness_load_config_exception(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                config = ConfigManager(allow_default=True)
                validator = ConfigValidator(config=config)

                with patch.object(config, "load_config", side_effect=Exception("fail")):
                    errors = validator.validate_completeness()
                    assert errors == []

    def test_validate_validity_load_config_exception(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                config = ConfigManager(allow_default=True)
                validator = ConfigValidator(config=config)

                with patch.object(config, "load_config", side_effect=Exception("fail")):
                    errors = validator.validate_validity()
                    assert errors == []

    def test_validate_consistency_with_inconsistencies(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                config = ConfigManager(allow_default=True)
                validator = ConfigValidator(config=config)

                with patch.object(
                    config,
                    "validate_config_consistency",
                    return_value=[
                        {
                            "field": "llm_provider",
                            "env_value": "anthropic",
                            "file_value": "openai",
                        }
                    ],
                ):
                    warnings = validator.validate_consistency()
                    assert len(warnings) == 1
                    assert warnings[0].field == "llm_provider"

    def test_test_api_connectivity_load_config_exception(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                config = ConfigManager(allow_default=True)
                validator = ConfigValidator(config=config)

                with patch.object(config, "load_config", side_effect=Exception("fail")):
                    result = validator.test_api_connectivity()
                    assert result.is_connected is False
                    assert "无法加载配置" in result.error_message

    def test_test_api_connectivity_with_provider(self, tmp_path: Path) -> None:
        config_dir = tmp_path / ".nanobot-runner"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "config.json").write_text(
            json.dumps({"version": "0.9.4", "data_dir": "/tmp/data"}),
            encoding="utf-8",
        )

        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                config = ConfigManager(allow_default=True)
                validator = ConfigValidator(config=config)

                with patch.object(
                    validator.env_manager, "get_env", return_value="sk-test-key"
                ):
                    result = validator.test_api_connectivity(provider="anthropic")
                    assert result.provider == "anthropic"
                    assert result.is_connected is True

    def test_test_api_connectivity_openai_mock(self, tmp_path: Path) -> None:
        config_dir = tmp_path / ".nanobot-runner"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "config.json").write_text(
            json.dumps({"version": "0.9.4", "data_dir": "/tmp/data"}),
            encoding="utf-8",
        )

        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                config = ConfigManager(allow_default=True)
                validator = ConfigValidator(config=config)

                with patch.object(
                    validator.env_manager, "get_env", return_value="sk-test-key"
                ):
                    with patch("urllib.request.urlopen") as mock_urlopen:
                        from unittest.mock import Mock

                        mock_resp = Mock()
                        mock_resp.read.return_value = b'{"data": []}'
                        mock_resp.__enter__ = Mock(return_value=mock_resp)
                        mock_resp.__exit__ = Mock(return_value=False)
                        mock_urlopen.return_value = mock_resp

                        result = validator.test_api_connectivity(provider="openai")
                        assert result.is_connected is True

    def test_test_api_connectivity_openai_error(self, tmp_path: Path) -> None:
        config_dir = tmp_path / ".nanobot-runner"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "config.json").write_text(
            json.dumps({"version": "0.9.4", "data_dir": "/tmp/data"}),
            encoding="utf-8",
        )

        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                config = ConfigManager(allow_default=True)
                validator = ConfigValidator(config=config)

                with patch.object(
                    validator.env_manager, "get_env", return_value="sk-test-key"
                ):
                    with patch(
                        "urllib.request.urlopen",
                        side_effect=Exception("connection failed"),
                    ):
                        result = validator.test_api_connectivity(provider="openai")
                        assert result.is_connected is False
                        assert "connection failed" in result.error_message
