from pathlib import Path
from unittest.mock import MagicMock, patch

from src.core.config.sync import NanobotConfigSync
from src.core.init.migrate import ConfigMigrator


class TestMigrationIntegration:
    """迁移流程集成测试

    验证从nanobot配置 → ConfigMigrator → 项目配置 → NanobotConfigSync → nanobot配置
    的完整迁移和同步链路。
    """

    def _make_mock_config(self) -> MagicMock:
        mock = MagicMock()
        mock.config_file = Path("/tmp/test_config.json")
        mock.base_dir = Path("/tmp/test_runner")
        mock._get_default_config.return_value = {
            "version": "0.9.5",
            "data_dir": "/tmp/test_runner/data",
        }
        mock.has_llm_config.return_value = True
        mock.get_llm_config.return_value = {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "api_key": "sk-test",
            "base_url": None,
        }
        return mock

    @patch.object(ConfigMigrator, "_load_nanobot_config")
    def test_migrate_then_sync_roundtrip(self, mock_load: MagicMock) -> None:
        """验证迁移后同步的完整链路"""
        nanobot_config = {
            "providers": {
                "default": "openai",
                "openai": {
                    "api_key": "sk-original",
                    "base_url": "https://api.openai.com",
                },
            },
            "agents": {
                "defaults": {
                    "model": "gpt-4o",
                },
            },
        }
        mock_load.return_value = nanobot_config

        mock_config = self._make_mock_config()
        migrator = ConfigMigrator(mock_config)
        migrate_result = migrator.migrate_from_nanobot()

        assert migrate_result.success
        assert "llm_provider" in migrate_result.migrated_fields
        assert "llm_model" in migrate_result.migrated_fields
        assert "llm_api_key" in migrate_result.migrated_fields
        assert "llm_base_url" in migrate_result.migrated_fields

        sync = NanobotConfigSync(mock_config)
        with (
            patch.object(sync, "_is_nanobot_installed", return_value=True),
            patch.object(sync, "_load_nanobot_config", return_value={}),
            patch.object(sync, "_save_nanobot_config"),
        ):
            sync_result = sync.sync_to_nanobot()

        assert sync_result.success
        assert "providers.default" in sync_result.synced_fields
        assert "agents.defaults.model" in sync_result.synced_fields

    @patch.object(ConfigMigrator, "_load_nanobot_config")
    def test_migrate_preserves_non_llm_fields(self, mock_load: MagicMock) -> None:
        """验证迁移时保留nanobot配置中的非LLM字段"""
        nanobot_config = {
            "providers": {
                "default": "openai",
                "openai": {"api_key": "sk-test"},
            },
            "agents": {
                "defaults": {"model": "gpt-4o-mini"},
            },
            "gateway": {
                "heartbeat": {"interval_s": 300, "enabled": True},
            },
            "custom_field": "should_be_preserved",
        }
        mock_load.return_value = nanobot_config

        mock_config = self._make_mock_config()

        sync = NanobotConfigSync(mock_config)
        with (
            patch.object(sync, "_is_nanobot_installed", return_value=True),
            patch.object(sync, "_load_nanobot_config", return_value=nanobot_config),
            patch.object(sync, "_save_nanobot_config") as mock_save,
        ):
            sync_result = sync.sync_to_nanobot()

        assert sync_result.success
        saved_config = mock_save.call_args[0][0]
        assert saved_config["custom_field"] == "should_be_preserved"
        assert saved_config["gateway"]["heartbeat"]["interval_s"] == 300

    @patch.object(ConfigMigrator, "_load_nanobot_config")
    def test_migrate_anthropic_provider(self, mock_load: MagicMock) -> None:
        """验证Anthropic Provider的迁移链路"""
        nanobot_config = {
            "providers": {
                "default": "anthropic",
                "anthropic": {
                    "api_key": "sk-ant-test",
                    "base_url": "https://api.anthropic.com",
                },
            },
            "agents": {
                "defaults": {"model": "claude-3-haiku-20240307"},
            },
        }
        mock_load.return_value = nanobot_config

        mock_config = self._make_mock_config()
        mock_config.get_llm_config.return_value = {
            "provider": "anthropic",
            "model": "claude-3-haiku-20240307",
            "api_key": "sk-ant-test",
            "base_url": "https://api.anthropic.com",
        }

        migrator = ConfigMigrator(mock_config)
        result = migrator.migrate_from_nanobot()

        assert result.success
        assert "llm_provider" in result.migrated_fields
        assert "llm_model" in result.migrated_fields

    def test_sync_no_runner_config(self) -> None:
        """验证项目配置缺失时同步失败但不影响项目功能"""
        mock_config = MagicMock()
        mock_config.has_llm_config.return_value = False

        sync = NanobotConfigSync(mock_config)
        result = sync.sync_to_nanobot()

        assert not result.success
        assert "项目配置中未找到LLM配置" in result.errors

    @patch.object(NanobotConfigSync, "_is_nanobot_installed", return_value=True)
    @patch.object(NanobotConfigSync, "_save_nanobot_config")
    @patch.object(NanobotConfigSync, "_load_nanobot_config")
    def test_sync_updates_provider_config(
        self, mock_load: MagicMock, mock_save: MagicMock, mock_installed: MagicMock
    ) -> None:
        """验证同步更新Provider配置"""
        existing = {
            "providers": {
                "default": "old_provider",
                "old_provider": {"api_key_env": "OLD_KEY"},
            },
            "agents": {"defaults": {"model": "old-model"}},
        }
        mock_load.return_value = existing

        mock_config = self._make_mock_config()
        mock_config.get_llm_config.return_value = {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "api_key": "sk-test",
            "base_url": "https://custom.api.com",
        }

        sync = NanobotConfigSync(mock_config)
        result = sync.sync_to_nanobot()

        assert result.success
        saved_config = mock_save.call_args[0][0]
        assert saved_config["providers"]["default"] == "openai"
        assert (
            saved_config["providers"]["openai"]["base_url"] == "https://custom.api.com"
        )
        assert saved_config["agents"]["defaults"]["model"] == "gpt-4o-mini"
