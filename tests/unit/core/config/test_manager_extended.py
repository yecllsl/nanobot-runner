from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

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
                assert config["version"] == "0.32.0"
                assert "data_dir" in config


class TestConfigManagerGetConfigSource:
    # ponytail: 移除了 test_config_source_env — ENV_KEY_MAPPING 已清空，ENV 源检测不再可用

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

    # ponytail: 移除了 test_with_inconsistencies — validate_config_consistency 已简化为始终返回 []

    def test_default_mode_no_inconsistencies(self, tmp_path):
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager(allow_default=True)
                result = cm.validate_config_consistency()
                assert result == []


# ponytail: 移除了 TestConfigManagerGetLlmConfig — get_llm_config() 已删除，LLM 配置迁移至 nanobot_config.json
# ponytail: 移除了 TestConfigManagerSaveLlmConfig — save_llm_config() 已删除，LLM 配置迁移至 nanobot_config.json


class TestConfigManagerHasLlmConfig:
    def test_has_llm_config_true(self, tmp_path):
        """has_llm_config 从 nanobot_config.json 读取 providers.default.apiKey"""
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()
                cm.save_config(
                    {
                        "version": "0.1.0",
                        "data_dir": str(tmp_path / "data"),
                    }
                )
                # 写入 nanobot_config.json，包含有效 provider 配置
                nano_config = {
                    "providers": {
                        "default": "openai",
                        "openai": {"apiKey": "sk-test-key"},
                    }
                }
                cm.get_nanobot_config_path().write_text(
                    json.dumps(nano_config), encoding="utf-8"
                )
                assert cm.has_llm_config() is True

    def test_has_llm_config_false(self, tmp_path):
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()
                assert cm.has_llm_config() is False


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
    # ponytail: 移除了 test_env_override — ENV_KEY_MAPPING 已清空，环境变量不再覆盖非敏感字段

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
