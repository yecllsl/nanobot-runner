from pathlib import Path
from unittest.mock import MagicMock, patch

from src.core.init.migrate import ConfigMigrator, MigrationResult
from src.core.init.models import InitMode
from src.core.init.wizard import InitWizard


class TestConfigMigrator:
    """ConfigMigrator测试"""

    def _make_mock_config(self) -> MagicMock:
        mock = MagicMock()
        mock.config_file = Path("/tmp/test_config.json")
        mock.base_dir = Path("/tmp/test_runner")
        mock._get_default_config.return_value = {
            "version": "0.9.5",
            "data_dir": "/tmp/test_runner/data",
        }
        return mock

    def test_migrate_no_nanobot_config(self) -> None:
        mock_config = self._make_mock_config()
        migrator = ConfigMigrator(mock_config)

        with patch.object(Path, "exists", return_value=False):
            result = migrator.migrate_from_nanobot()

        assert not result.success
        assert "nanobot配置文件不存在" in result.errors[0]

    @patch.object(ConfigMigrator, "_load_nanobot_config")
    def test_migrate_empty_config(self, mock_load: MagicMock) -> None:
        mock_load.return_value = {}
        mock_config = self._make_mock_config()
        migrator = ConfigMigrator(mock_config)

        result = migrator.migrate_from_nanobot()
        assert not result.success
        assert "没有可迁移的LLM配置" in result.errors[0]

    @patch.object(ConfigMigrator, "_load_nanobot_config")
    def test_migrate_llm_config(self, mock_load: MagicMock) -> None:
        mock_load.return_value = {
            "providers": {
                "default": "openai",
                "openai": {
                    "api_key": "sk-test-key",
                    "base_url": "https://api.openai.com",
                },
            },
            "agents": {
                "defaults": {
                    "model": "gpt-4o-mini",
                },
            },
        }
        mock_config = self._make_mock_config()
        migrator = ConfigMigrator(mock_config)

        result = migrator.migrate_from_nanobot()
        assert result.success
        assert "llm_provider" in result.migrated_fields
        assert "llm_model" in result.migrated_fields
        assert "llm_api_key" in result.migrated_fields
        assert "llm_base_url" in result.migrated_fields

    @patch.object(ConfigMigrator, "_load_nanobot_config")
    def test_migrate_api_key_from_env(self, mock_load: MagicMock) -> None:
        mock_load.return_value = {
            "providers": {
                "default": "openai",
                "openai": {
                    "api_key_env": "NANOBOT_LLM_API_KEY",
                },
            },
            "agents": {
                "defaults": {
                    "model": "gpt-4o-mini",
                },
            },
        }
        mock_config = self._make_mock_config()
        migrator = ConfigMigrator(mock_config)

        with patch.dict("os.environ", {"NANOBOT_LLM_API_KEY": "sk-env-key"}):
            result = migrator.migrate_from_nanobot()

        assert result.success
        assert "llm_api_key" in result.migrated_fields

    @patch.object(ConfigMigrator, "_load_nanobot_config")
    def test_migrate_no_api_key_warning(self, mock_load: MagicMock) -> None:
        mock_load.return_value = {
            "providers": {
                "default": "openai",
                "openai": {},
            },
            "agents": {
                "defaults": {
                    "model": "gpt-4o-mini",
                },
            },
        }
        mock_config = self._make_mock_config()
        migrator = ConfigMigrator(mock_config)

        result = migrator.migrate_from_nanobot()
        assert result.success
        assert "llm_provider" in result.migrated_fields
        assert "llm_model" in result.migrated_fields


class TestMigrationResult:
    """MigrationResult数据类测试"""

    def test_default_values(self) -> None:
        result = MigrationResult(success=True)
        assert result.success
        assert result.errors == []
        assert result.warnings == []
        assert result.migrated_fields == []
        assert result.config_path is None
        assert result.env_path is None


class TestInitWizardMigrateMode:
    """InitWizard迁移模式测试"""

    def _make_wizard(self) -> InitWizard:
        mock_config = MagicMock()
        mock_config.base_dir = Path("/tmp/test_runner")
        mock_config.has_llm_config.return_value = True
        return InitWizard(config=mock_config)

    @patch.object(InitWizard, "_is_already_initialized", return_value=False)
    @patch.object(InitWizard, "_sync_to_nanobot")
    @patch("src.core.init.migrate.ConfigMigrator")
    def test_migrate_mode_success(
        self, mock_migrator_cls: MagicMock, mock_sync: MagicMock, mock_init: MagicMock
    ) -> None:
        mock_migrator = MagicMock()
        mock_migrator.migrate_from_nanobot.return_value = MigrationResult(
            success=True,
            migrated_fields=["llm_provider", "llm_model"],
            config_path=Path("/tmp/config.json"),
            env_path=Path("/tmp/.env.local"),
        )
        mock_migrator_cls.return_value = mock_migrator

        wizard = self._make_wizard()
        result = wizard.run(mode=InitMode.MIGRATE)

        assert result.success
        assert result.config_path == Path("/tmp/config.json")
        mock_sync.assert_called_once()

    @patch.object(InitWizard, "_is_already_initialized", return_value=True)
    def test_migrate_mode_already_initialized_no_force(
        self, mock_init: MagicMock
    ) -> None:
        wizard = self._make_wizard()
        result = wizard.run(mode=InitMode.MIGRATE, force=False)

        assert not result.success
        assert "已初始化" in result.errors[0]

    @patch.object(InitWizard, "_is_already_initialized", return_value=False)
    @patch("src.core.init.migrate.ConfigMigrator")
    def test_migrate_mode_failure(
        self, mock_migrator_cls: MagicMock, mock_init: MagicMock
    ) -> None:
        mock_migrator = MagicMock()
        mock_migrator.migrate_from_nanobot.return_value = MigrationResult(
            success=False,
            errors=["nanobot配置文件不存在"],
        )
        mock_migrator_cls.return_value = mock_migrator

        wizard = self._make_wizard()
        result = wizard.run(mode=InitMode.MIGRATE)

        assert not result.success
        assert "nanobot配置文件不存在" in result.errors


class TestInitWizardAgentMode:
    """InitWizard agent_mode参数测试"""

    def _make_wizard(self) -> InitWizard:
        mock_config = MagicMock()
        mock_config.base_dir = Path("/tmp/test_runner")
        return InitWizard(config=mock_config)

    @patch.object(InitWizard, "_is_already_initialized", return_value=False)
    @patch.object(InitWizard, "_sync_to_nanobot")
    @patch.object(InitWizard, "guide_config")
    @patch.object(InitWizard, "validate_config")
    @patch.object(InitWizard, "generate_config_files")
    @patch.object(InitWizard, "detect_environment")
    def test_data_mode_no_llm(
        self,
        mock_detect: MagicMock,
        mock_generate: MagicMock,
        mock_validate: MagicMock,
        mock_guide: MagicMock,
        mock_sync: MagicMock,
        mock_init: MagicMock,
    ) -> None:
        mock_detect.return_value = MagicMock(missing_dependencies=[])
        mock_guide.return_value = {
            "config": {"version": "0.9.5", "data_dir": "/tmp/data"},
            "env_vars": {},
        }
        mock_validate.return_value = MagicMock(is_valid=True, errors=[], warnings=[])
        mock_generate.return_value = {
            "config": Path("/tmp/config.json"),
        }

        wizard = self._make_wizard()
        result = wizard.run(agent_mode=False)

        assert result.success
        mock_guide.assert_called_once_with(skip_optional=False, agent_mode=False)
        mock_sync.assert_not_called()
        assert "Agent聊天" not in " ".join(result.next_steps)

    @patch.object(InitWizard, "_is_already_initialized", return_value=False)
    @patch.object(InitWizard, "_sync_to_nanobot")
    @patch.object(InitWizard, "guide_config")
    @patch.object(InitWizard, "validate_config")
    @patch.object(InitWizard, "generate_config_files")
    @patch.object(InitWizard, "detect_environment")
    def test_agent_mode_with_llm(
        self,
        mock_detect: MagicMock,
        mock_generate: MagicMock,
        mock_validate: MagicMock,
        mock_guide: MagicMock,
        mock_sync: MagicMock,
        mock_init: MagicMock,
    ) -> None:
        mock_detect.return_value = MagicMock(missing_dependencies=[])
        mock_guide.return_value = {
            "config": {
                "version": "0.9.5",
                "data_dir": "/tmp/data",
                "llm_provider": "openai",
                "llm_model": "gpt-4o-mini",
            },
            "env_vars": {"NANOBOT_LLM_API_KEY": "sk-test"},
        }
        mock_validate.return_value = MagicMock(is_valid=True, errors=[], warnings=[])
        mock_generate.return_value = {
            "config": Path("/tmp/config.json"),
        }

        wizard = self._make_wizard()
        result = wizard.run(agent_mode=True)

        assert result.success
        mock_guide.assert_called_once_with(skip_optional=False, agent_mode=True)
        mock_sync.assert_called_once()
        assert "Agent聊天" in " ".join(result.next_steps)
