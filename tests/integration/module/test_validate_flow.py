import json
from pathlib import Path
from unittest.mock import patch

from src.core.config.env_manager import EnvManager
from src.core.config.manager import ConfigManager
from src.core.validate.models import ErrorLevel, ValidationReport
from src.core.validate.validator import ConfigValidator


class TestValidateFlowIntegration:
    """验证流程集成测试：ConfigValidator → EnvManager → ConfigManager"""

    def test_validate_valid_config(self, tmp_path: Path) -> None:
        """验证合法配置"""
        config_dir = tmp_path / ".nanobot-runner"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "config.json").write_text(
            json.dumps(
                {
                    "version": "0.9.4",
                    "data_dir": str(tmp_path / "data"),
                    "llm_provider": "openai",
                    "llm_model": "gpt-4o-mini",
                }
            ),
            encoding="utf-8",
        )

        with patch.object(Path, "home", return_value=tmp_path):
            config = ConfigManager(allow_default=True)
            validator = ConfigValidator(config=config)

            report = validator.validate_all()
            assert isinstance(report, ValidationReport)

    def test_validate_missing_required_fields(self, tmp_path: Path) -> None:
        """验证缺少必填字段"""
        with patch.object(Path, "home", return_value=tmp_path):
            config = ConfigManager(allow_default=True)
            validator = ConfigValidator(config=config)

            with patch.object(config, "load_config", return_value={}):
                errors = validator.validate_completeness()
                error_fields = [e.field for e in errors if e.level == ErrorLevel.ERROR]
                assert "version" in error_fields
                assert "data_dir" in error_fields

    def test_validate_invalid_version_format(self, tmp_path: Path) -> None:
        """验证版本号格式错误"""
        with patch.object(Path, "home", return_value=tmp_path):
            config = ConfigManager(allow_default=True)
            validator = ConfigValidator(config=config)

            with patch.object(
                config,
                "load_config",
                return_value={"version": "not-a-version", "data_dir": "/tmp/data"},
            ):
                errors = validator.validate_validity()
                assert any(e.field == "version" for e in errors)

    def test_validate_data_dir_is_file(self, tmp_path: Path) -> None:
        """验证 data_dir 指向文件而非目录"""
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

    def test_env_manager_template_generation(self, tmp_path: Path) -> None:
        """EnvManager 模板生成与验证联动"""
        env_file = tmp_path / ".env.local"
        manager = EnvManager(env_file=env_file)

        template = manager.generate_env_template()
        assert "NANOBOT_LLM_API_KEY" in template

        env_vars = {"NANOBOT_LLM_API_KEY": "sk-test"}
        manager.save_env_file(env_vars)

        loaded = manager.load_env()
        assert loaded["NANOBOT_LLM_API_KEY"] == "sk-test"

    def test_full_validate_flow(self, tmp_path: Path) -> None:
        """完整验证流程"""
        config_dir = tmp_path / ".nanobot-runner"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "config.json").write_text(
            json.dumps({"version": "0.9.4", "data_dir": str(tmp_path / "data")}),
            encoding="utf-8",
        )

        with patch.object(Path, "home", return_value=tmp_path):
            config = ConfigManager(allow_default=True)
            validator = ConfigValidator(config=config)

            report = validator.validate_all()
            assert isinstance(report, ValidationReport)

            if not report.is_valid:
                for err in report.errors:
                    if err.suggestion:
                        assert len(err.suggestion) > 0
