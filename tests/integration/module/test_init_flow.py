import json
from pathlib import Path
from unittest.mock import patch

from src.core.config import ConfigManager
from src.core.env_manager import EnvManager
from src.core.init.models import InitMode
from src.core.init.wizard import InitWizard


class TestInitFlowIntegration:
    """初始化流程集成测试：InitWizard → ConfigGenerator → EnvManager"""

    def test_fresh_init_creates_config(self, tmp_path: Path) -> None:
        """全新初始化：创建配置文件"""
        with patch.object(Path, "home", return_value=tmp_path):
            config = ConfigManager(allow_default=True)
            wizard = InitWizard(config=config)

            with patch.object(
                wizard,
                "guide_config",
                return_value={
                    "config": {"version": "0.9.4"},
                    "env_vars": {},
                },
            ):
                result = wizard.run(
                    mode=InitMode.FRESH,
                    force=True,
                    skip_optional=True,
                )

            assert result.success is True
            assert result.config_path is not None

            config_file = Path(result.config_path)
            assert config_file.exists()

            with open(config_file, encoding="utf-8") as f:
                data = json.load(f)
            assert "version" in data
            assert "data_dir" in data

    def test_fresh_init_with_workspace(self, tmp_path: Path) -> None:
        """指定 workspace 目录初始化"""
        workspace = tmp_path / "custom_workspace"

        with patch.object(Path, "home", return_value=tmp_path):
            config = ConfigManager(allow_default=True)
            wizard = InitWizard(config=config)

            with patch.object(
                wizard,
                "guide_config",
                return_value={
                    "config": {"version": "0.9.4"},
                    "env_vars": {},
                },
            ):
                result = wizard.run(
                    mode=InitMode.FRESH,
                    force=True,
                    skip_optional=True,
                    workspace_dir=workspace,
                )

            assert result.success is True

    def test_reinit_without_force_fails(self, tmp_path: Path) -> None:
        """重复初始化（不强制）应失败"""
        config_dir = tmp_path / ".nanobot-runner"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "config.json").write_text(
            json.dumps({"version": "0.9.4", "data_dir": "/tmp/data"}),
            encoding="utf-8",
        )

        with patch.object(Path, "home", return_value=tmp_path):
            config = ConfigManager(allow_default=True)
            wizard = InitWizard(config=config)

            result = wizard.run(
                mode=InitMode.FRESH,
                force=False,
                skip_optional=True,
            )

            assert result.success is False
            assert any("已初始化" in e for e in result.errors)

    def test_env_manager_reads_written_env(self, tmp_path: Path) -> None:
        """EnvManager 写入 .env.local 后能正确读取"""
        env_file = tmp_path / ".env.local"
        env_vars = {
            "NANOBOT_LLM_API_KEY": "sk-test-key",
            "NANOBOT_FEISHU_APP_ID": "cli_test",
        }

        manager = EnvManager(env_file=env_file)
        manager.save_env_file(env_vars)

        assert env_file.exists()

        loaded = manager.load_env()
        assert loaded["NANOBOT_LLM_API_KEY"] == "sk-test-key"
        assert loaded["NANOBOT_FEISHU_APP_ID"] == "cli_test"

    def test_detect_environment(self, tmp_path: Path) -> None:
        """环境检测返回完整信息"""
        with patch.object(Path, "home", return_value=tmp_path):
            config = ConfigManager(allow_default=True)
            wizard = InitWizard(config=config)

            env_info = wizard.detect_environment()
            assert env_info.python_version != ""
            assert env_info.os_type != ""
