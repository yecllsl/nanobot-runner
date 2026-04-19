import json
from pathlib import Path
from unittest.mock import patch

from src.core.config import ConfigManager
from src.core.init.generator import ConfigGenerator
from src.core.init.models import EnvironmentInfo, InitMode, InitResult, ValidationResult
from src.core.init.wizard import InitWizard


class TestInitModels:
    """初始化模块数据结构测试"""

    def test_init_mode_enum(self) -> None:
        assert InitMode.FRESH.value == "fresh"
        assert InitMode.MIGRATE.value == "migrate"

    def test_environment_info(self) -> None:
        info = EnvironmentInfo(
            python_version="3.11.0",
            os_type="Windows",
            os_version="10",
            dependencies={"polars": "0.20.0"},
            missing_dependencies=["questionary"],
        )
        assert info.python_version == "3.11.0"
        assert info.os_type == "Windows"
        assert "questionary" in info.missing_dependencies

    def test_init_result_success(self) -> None:
        result = InitResult(
            success=True,
            config_path=Path("/tmp/config.json"),
            next_steps=["step1"],
        )
        assert result.success is True
        assert result.config_path == Path("/tmp/config.json")
        assert len(result.next_steps) == 1

    def test_init_result_failure(self) -> None:
        result = InitResult(
            success=False,
            errors=["error1"],
        )
        assert result.success is False
        assert "error1" in result.errors

    def test_validation_result_valid(self) -> None:
        result = ValidationResult(is_valid=True)
        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []

    def test_validation_result_invalid(self) -> None:
        result = ValidationResult(
            is_valid=False,
            errors=["missing field"],
            warnings=["optional field"],
        )
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert len(result.warnings) == 1


class TestConfigGenerator:
    """配置文件生成器测试"""

    def test_generate_config_json(self) -> None:
        generator = ConfigGenerator()
        config = {"version": "0.9.4", "data_dir": "/tmp/data"}
        result = generator.generate_config_json(config)

        parsed = json.loads(result)
        assert parsed["version"] == "0.9.4"
        assert parsed["data_dir"] == "/tmp/data"

    def test_generate_env_local_with_api_key(self) -> None:
        generator = ConfigGenerator()
        env_vars = {
            "NANOBOT_LLM_API_KEY": "sk-test",
            "NANOBOT_LLM_PROVIDER": "openai",
            "NANOBOT_LLM_MODEL": "gpt-4o-mini",
        }
        result = generator.generate_env_local(env_vars)

        assert "NANOBOT_LLM_API_KEY=sk-test" in result
        assert "NANOBOT_LLM_PROVIDER=openai" in result

    def test_generate_env_local_with_feishu(self) -> None:
        generator = ConfigGenerator()
        env_vars = {
            "NANOBOT_FEISHU_APP_ID": "cli_test",
            "NANOBOT_FEISHU_APP_SECRET": "secret",
            "NANOBOT_FEISHU_RECEIVE_ID": "user1",
            "NANOBOT_AUTO_PUSH_FEISHU": "true",
        }
        result = generator.generate_env_local(env_vars)

        assert "NANOBOT_FEISHU_APP_ID=cli_test" in result
        assert "飞书通知配置" in result

    def test_write_config_files(self, tmp_path: Path) -> None:
        generator = ConfigGenerator()
        config = {"version": "0.9.4", "data_dir": str(tmp_path / "data")}
        env_vars = {"NANOBOT_LLM_API_KEY": "sk-test"}

        written = generator.write_config_files(tmp_path, config, env_vars)

        assert "config" in written
        assert "env" in written
        assert written["config"].exists()
        assert written["env"].exists()

    def test_write_config_files_creates_template_files(self, tmp_path: Path) -> None:
        generator = ConfigGenerator()
        config = {"version": "0.9.4", "data_dir": str(tmp_path / "data")}

        written = generator.write_config_files(tmp_path, config)

        assert "config" in written
        assert written["config"].exists()

    def test_write_config_files_creates_memory_files(self, tmp_path: Path) -> None:
        generator = ConfigGenerator()
        config = {"version": "0.9.4", "data_dir": str(tmp_path / "data")}

        written = generator.write_config_files(tmp_path, config)

        memory_dir = tmp_path / "memory"
        assert memory_dir.exists()
        assert (memory_dir / "MEMORY.md").exists()
        assert (memory_dir / "history.jsonl").exists()


class TestInitWizard:
    """初始化向导测试"""

    def test_detect_environment(self, tmp_path: Path) -> None:
        with patch.object(Path, "home", return_value=tmp_path):
            config = ConfigManager(allow_default=True)
            wizard = InitWizard(config=config)
            env_info = wizard.detect_environment()

            assert env_info.python_version
            assert env_info.os_type
            assert isinstance(env_info.dependencies, dict)

    def test_create_directories(self, tmp_path: Path) -> None:
        with patch.object(Path, "home", return_value=tmp_path):
            config = ConfigManager(allow_default=True)
            wizard = InitWizard(config=config)
            wizard.create_directories(tmp_path / "workspace")

            assert (tmp_path / "workspace").exists()
            assert (tmp_path / "workspace" / "data").exists()
            assert (tmp_path / "workspace" / "memory").exists()

    def test_validate_config_valid(self, tmp_path: Path) -> None:
        with patch.object(Path, "home", return_value=tmp_path):
            config = ConfigManager(allow_default=True)
            wizard = InitWizard(config=config)

            result = wizard.validate_config(
                {
                    "version": "0.9.4",
                    "data_dir": str(tmp_path / "data"),
                }
            )
            assert result.is_valid is True

    def test_validate_config_missing_version(self, tmp_path: Path) -> None:
        with patch.object(Path, "home", return_value=tmp_path):
            config = ConfigManager(allow_default=True)
            wizard = InitWizard(config=config)

            result = wizard.validate_config({"data_dir": "/tmp/data"})
            assert result.is_valid is False
            assert any("版本号" in e for e in result.errors)

    def test_validate_config_missing_data_dir(self, tmp_path: Path) -> None:
        with patch.object(Path, "home", return_value=tmp_path):
            config = ConfigManager(allow_default=True)
            wizard = InitWizard(config=config)

            result = wizard.validate_config({"version": "0.9.4"})
            assert result.is_valid is False
            assert any("数据目录" in e for e in result.errors)

    def test_is_already_initialized(self, tmp_path: Path) -> None:
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        assert InitWizard._is_already_initialized(workspace) is False

        (workspace / "config.json").write_text("{}", encoding="utf-8")
        assert InitWizard._is_already_initialized(workspace) is True

    def test_run_already_initialized_no_force(self, tmp_path: Path) -> None:
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        (workspace / "config.json").write_text("{}", encoding="utf-8")

        with patch.object(Path, "home", return_value=tmp_path):
            config = ConfigManager(allow_default=True)
            wizard = InitWizard(config=config)

            result = wizard.run(workspace_dir=workspace)
            assert result.success is False
            assert any("已初始化" in e for e in result.errors)
