from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.config.manager import ConfigManager, ConfigSource


@pytest.fixture(autouse=True)
def reset_config_cache():
    ConfigManager.reset_cache()
    yield
    ConfigManager.reset_cache()


class TestConfigManagerLoadConfigWithDefault:
    def test_load_config_using_default(self, tmp_path):
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager(allow_default=True)
                config = cm.load_config()
                assert config["version"] == "0.9.4"
                assert "data_dir" in config


class TestConfigManagerGetConfigSource:
    def test_config_source_env(self, tmp_path):
        with patch.dict(os.environ, {"NANOBOT_FEISHU_APP_ID": "env_val"}, clear=False):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()
                source = cm.get_config_source("feishu_app_id")
                assert source == ConfigSource.ENV

    def test_config_source_file(self, tmp_path):
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()
                cm.save_config(
                    {
                        "version": "0.1.0",
                        "data_dir": str(tmp_path / "data"),
                        "feishu_app_id": "file_val",
                    }
                )
                source = cm.get_config_source("feishu_app_id")
                assert source == ConfigSource.FILE

    def test_config_source_default(self, tmp_path):
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()
                source = cm.get_config_source("nonexistent_key")
                assert source == ConfigSource.DEFAULT

    def test_config_source_default_mode(self, tmp_path):
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager(allow_default=True)
                source = cm.get_config_source("any_key")
                assert source == ConfigSource.DEFAULT


class TestConfigManagerValidateConsistency:
    def test_no_inconsistencies(self, tmp_path):
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()
                cm.save_config(
                    {
                        "version": "0.1.0",
                        "data_dir": str(tmp_path / "data"),
                    }
                )
                result = cm.validate_config_consistency()
                assert result == []

    def test_with_inconsistencies(self, tmp_path):
        with patch.dict(os.environ, {"NANOBOT_FEISHU_APP_ID": "env_val"}, clear=False):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()
                cm.save_config(
                    {
                        "version": "0.1.0",
                        "data_dir": str(tmp_path / "data"),
                        "feishu_app_id": "file_val",
                    }
                )
                result = cm.validate_config_consistency()
                assert len(result) > 0
                assert result[0]["field"] == "feishu_app_id"

    def test_default_mode_no_inconsistencies(self, tmp_path):
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager(allow_default=True)
                result = cm.validate_config_consistency()
                assert result == []


class TestConfigManagerGetLlmConfig:
    def test_get_llm_config_from_file(self, tmp_path):
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()
                cm.save_config(
                    {
                        "version": "0.1.0",
                        "data_dir": str(tmp_path / "data"),
                        "llm_provider": "openai",
                        "llm_model": "gpt-4",
                        "llm_base_url": "https://api.openai.com",
                    }
                )
                llm = cm.get_llm_config()
                assert llm["provider"] == "openai"
                assert llm["model"] == "gpt-4"
                assert llm["base_url"] == "https://api.openai.com"

    def test_get_llm_config_env_override(self, tmp_path):
        with patch.dict(
            os.environ,
            {"NANOBOT_LLM_PROVIDER": "anthropic", "NANOBOT_LLM_MODEL": "claude-3"},
            clear=False,
        ):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()
                cm.save_config(
                    {
                        "version": "0.1.0",
                        "data_dir": str(tmp_path / "data"),
                        "llm_provider": "openai",
                        "llm_model": "gpt-4",
                    }
                )
                llm = cm.get_llm_config()
                assert llm["provider"] == "anthropic"
                assert llm["model"] == "claude-3"

    def test_get_llm_config_empty(self, tmp_path):
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()
                llm = cm.get_llm_config()
                assert llm["provider"] == ""
                assert llm["model"] == ""


class TestConfigManagerHasLlmConfig:
    def test_has_llm_config_true(self, tmp_path):
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()
                cm.save_config(
                    {
                        "version": "0.1.0",
                        "data_dir": str(tmp_path / "data"),
                        "llm_provider": "openai",
                        "llm_model": "gpt-4",
                    }
                )
                assert cm.has_llm_config() is True

    def test_has_llm_config_false(self, tmp_path):
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()
                assert cm.has_llm_config() is False


class TestConfigManagerSaveLlmConfig:
    def test_save_llm_config(self, tmp_path):
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()
                cm.save_llm_config(
                    provider="openai",
                    model="gpt-4",
                    base_url="https://api.openai.com",
                )
                config = cm.load_config()
                assert config["llm_provider"] == "openai"
                assert config["llm_model"] == "gpt-4"
                assert config["llm_base_url"] == "https://api.openai.com"

    def test_save_llm_config_with_api_key(self, tmp_path):
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()
                with patch("src.core.config.env_manager.EnvManager") as mock_env:
                    mock_instance = MagicMock()
                    mock_env.return_value = mock_instance
                    cm.save_llm_config(
                        provider="openai",
                        model="gpt-4",
                        api_key="sk-test-key",
                    )
                    mock_instance.save_env_file.assert_called_once()

    def test_save_llm_config_remove_base_url(self, tmp_path):
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()
                cm.save_config(
                    {
                        "version": "0.1.0",
                        "data_dir": str(tmp_path / "data"),
                        "llm_provider": "openai",
                        "llm_model": "gpt-4",
                        "llm_base_url": "https://old-url.com",
                    }
                )
                cm.save_llm_config(
                    provider="openai",
                    model="gpt-4",
                    base_url=None,
                )
                config = cm.load_config()
                assert "llm_base_url" not in config


class TestConfigManagerCastEnvValue:
    def test_cast_bool_true(self):
        assert ConfigManager._cast_env_value("auto_push_feishu", "true") is True
        assert ConfigManager._cast_env_value("auto_push_feishu", "1") is True
        assert ConfigManager._cast_env_value("auto_push_feishu", "yes") is True

    def test_cast_bool_false(self):
        assert ConfigManager._cast_env_value("auto_push_feishu", "false") is False
        assert ConfigManager._cast_env_value("auto_push_feishu", "0") is False

    def test_cast_int(self):
        assert ConfigManager._cast_env_value("default_year", "2024") == 2024

    def test_cast_int_invalid(self):
        assert (
            ConfigManager._cast_env_value("default_year", "not_a_number")
            == "not_a_number"
        )

    def test_cast_string(self):
        assert ConfigManager._cast_env_value("feishu_app_id", "test_id") == "test_id"


class TestConfigManagerLoadConfigWithEnvOverride:
    def test_env_override(self, tmp_path):
        with patch.dict(
            os.environ, {"NANOBOT_FEISHU_APP_ID": "env_app_id"}, clear=False
        ):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()
                cm.save_config(
                    {
                        "version": "0.1.0",
                        "data_dir": str(tmp_path / "data"),
                        "feishu_app_id": "file_app_id",
                    }
                )
                config = cm.load_config_with_env_override()
                assert config["feishu_app_id"] == "env_app_id"

    def test_no_env_override(self, tmp_path):
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()
                cm.save_config(
                    {
                        "version": "0.1.0",
                        "data_dir": str(tmp_path / "data"),
                        "feishu_app_id": "file_app_id",
                    }
                )
                config = cm.load_config_with_env_override()
                assert config["feishu_app_id"] == "file_app_id"


class TestConfigManagerGetTypedConfig:
    def test_get_typed_config(self, tmp_path):
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()
                cm.save_config(
                    {
                        "version": "0.1.0",
                        "data_dir": str(tmp_path / "data"),
                    }
                )
                typed = cm.get_typed_config()
                assert typed is not None


class TestConfigManagerDetectConfigFile:
    def test_detect_from_env_file(self, tmp_path):
        config_file = tmp_path / "custom_config.json"
        config_file.write_text('{"version": "0.1.0", "data_dir": "/tmp/data"}')
        with patch.dict(os.environ, {"NANOBOT_CONFIG_FILE": str(config_file)}):
            cm = ConfigManager()
            assert cm.config_file == config_file

    def test_detect_from_env_dir(self, tmp_path):
        config_dir = tmp_path / "config_dir"
        config_dir.mkdir()
        config_file = config_dir / "config.json"
        config_file.write_text('{"version": "0.1.0", "data_dir": "/tmp/data"}')
        with patch.dict(os.environ, {"NANOBOT_CONFIG_DIR": str(config_dir)}):
            cm = ConfigManager()
            assert cm.config_file == config_file

    def test_detect_default_path(self, tmp_path):
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()
                assert cm.config_file == tmp_path / ".nanobot-runner" / "config.json"


class TestConfigManagerSaveConfigValidation:
    def test_save_invalid_config(self, tmp_path):
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()
                with pytest.raises(ValueError, match="配置验证失败"):
                    cm.save_config({"invalid": True})


class TestConfigManagerIsCacheValid:
    def test_cache_valid(self, tmp_path):

        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()
                cm.load_config()
                assert cm._is_cache_valid() is True

    def test_cache_invalid_no_cache(self, tmp_path):
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()
                cm._invalidate_cache()
                assert cm._is_cache_valid() is False
