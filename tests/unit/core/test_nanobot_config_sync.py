from pathlib import Path
from unittest.mock import MagicMock, patch

from src.core.nanobot_config_sync import NanobotConfigSync, SyncResult


class TestSyncResult:
    """SyncResult数据类测试"""

    def test_default_values(self) -> None:
        result = SyncResult(success=True)
        assert result.success
        assert result.errors == []
        assert result.warnings == []
        assert result.synced_fields == []

    def test_with_errors(self) -> None:
        result = SyncResult(success=False, errors=["error1"])
        assert not result.success
        assert result.errors == ["error1"]


class TestNanobotConfigSync:
    """NanobotConfigSync测试"""

    def _make_mock_config(self, has_llm: bool = True) -> MagicMock:
        mock = MagicMock()
        mock.has_llm_config.return_value = has_llm
        if has_llm:
            mock.get_llm_config.return_value = {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "api_key": "sk-test",
                "base_url": None,
            }
        return mock

    def test_sync_no_runner_llm_config(self) -> None:
        mock_config = self._make_mock_config(has_llm=False)
        sync = NanobotConfigSync(mock_config)
        result = sync.sync_to_nanobot()

        assert not result.success
        assert "项目配置中未找到LLM配置" in result.errors

    @patch.object(NanobotConfigSync, "_is_nanobot_installed", return_value=False)
    def test_sync_nanobot_not_installed(self, mock_installed: MagicMock) -> None:
        mock_config = self._make_mock_config(has_llm=True)
        sync = NanobotConfigSync(mock_config)
        result = sync.sync_to_nanobot()

        assert not result.success
        assert "nanobot未安装" in result.errors[0]

    @patch.object(NanobotConfigSync, "_is_nanobot_installed", return_value=True)
    @patch.object(NanobotConfigSync, "_save_nanobot_config")
    @patch.object(NanobotConfigSync, "_load_nanobot_config")
    def test_sync_success_new_config(
        self, mock_load: MagicMock, mock_save: MagicMock, mock_installed: MagicMock
    ) -> None:
        mock_load.return_value = {}
        mock_config = self._make_mock_config(has_llm=True)

        sync = NanobotConfigSync(mock_config)
        result = sync.sync_to_nanobot()

        assert result.success
        assert "providers.default" in result.synced_fields
        assert "agents.defaults.model" in result.synced_fields
        mock_save.assert_called_once()

    @patch.object(NanobotConfigSync, "_is_nanobot_installed", return_value=True)
    @patch.object(NanobotConfigSync, "_save_nanobot_config")
    @patch.object(NanobotConfigSync, "_load_nanobot_config")
    def test_sync_merges_with_existing(
        self, mock_load: MagicMock, mock_save: MagicMock, mock_installed: MagicMock
    ) -> None:
        existing = {
            "providers": {"default": "anthropic"},
            "agents": {"defaults": {"model": "old-model"}},
            "custom_field": "preserved",
        }
        mock_load.return_value = existing
        mock_config = self._make_mock_config(has_llm=True)

        sync = NanobotConfigSync(mock_config)
        result = sync.sync_to_nanobot()

        assert result.success
        saved_config = mock_save.call_args[0][0]
        assert saved_config["providers"]["default"] == "openai"
        assert saved_config["agents"]["defaults"]["model"] == "gpt-4o-mini"
        assert saved_config["custom_field"] == "preserved"

    @patch.object(NanobotConfigSync, "_is_nanobot_installed", return_value=True)
    @patch.object(NanobotConfigSync, "_save_nanobot_config")
    @patch.object(NanobotConfigSync, "_load_nanobot_config")
    def test_sync_with_base_url(
        self, mock_load: MagicMock, mock_save: MagicMock, mock_installed: MagicMock
    ) -> None:
        mock_load.return_value = {}
        mock_config = self._make_mock_config(has_llm=True)
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
        assert (
            saved_config["providers"]["openai"]["base_url"] == "https://custom.api.com"
        )

    def test_has_runner_llm_config_exception(self) -> None:
        mock_config = MagicMock()
        mock_config.has_llm_config.side_effect = Exception("error")

        sync = NanobotConfigSync(mock_config)
        assert not sync._has_runner_llm_config()

    @patch.object(NanobotConfigSync, "_is_nanobot_installed", return_value=True)
    @patch.object(NanobotConfigSync, "_save_nanobot_config")
    def test_load_nanobot_config_creates_default(
        self, mock_save: MagicMock, mock_installed: MagicMock
    ) -> None:
        mock_config = self._make_mock_config(has_llm=True)

        sync = NanobotConfigSync(mock_config)

        with patch.object(Path, "exists", return_value=False):
            config = sync._load_nanobot_config()

        assert "providers" in config
        assert "agents" in config

    def test_create_default_nanobot_config(self) -> None:
        mock_config = self._make_mock_config()
        sync = NanobotConfigSync(mock_config)
        config = sync._create_default_nanobot_config()

        assert config["providers"]["default"] == "openai"
        assert config["agents"]["defaults"]["model"] == "gpt-4o-mini"
