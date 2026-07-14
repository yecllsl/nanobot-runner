# 配置管理单元测试
# 测试配置管理器的功能

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from src.core.config.manager import ConfigManager, config


@pytest.fixture(autouse=True)
def reset_config_cache():
    """每个测试前重置 ConfigManager 缓存"""
    ConfigManager.reset_cache()
    yield
    ConfigManager.reset_cache()


class TestConfigManager:
    """测试配置管理器"""

    def test_init(self, tmp_path):
        """测试初始化"""
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()
                assert cm.base_dir == tmp_path / ".nanobot-runner"
                assert cm.data_dir == cm.base_dir / "data"
                assert cm.config_file == cm.base_dir / "config.json"
                assert cm.index_file == cm.data_dir / "index.json"
                assert cm.cron_dir == cm.base_dir / "cron"
                assert cm.cron_store == cm.cron_dir / "jobs.json"

    def test_ensure_dirs(self, tmp_path):
        """测试确保目录存在"""
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()
                assert cm.base_dir.exists()
                assert cm.data_dir.exists()
                assert cm.cron_dir.exists()

    def test_ensure_config_default(self, tmp_path):
        """测试创建默认配置"""
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()
                assert cm.config_file.exists()

                with open(cm.config_file, encoding="utf-8") as f:
                    config_data = json.load(f)

                assert config_data["version"] == "0.32.0"
                assert "data_dir" in config_data
                assert "auto_push_feishu" in config_data
                assert "timezone" in config_data

    def test_allow_default_does_not_auto_create_config(self, tmp_path):
        """测试 allow_default=True 时不自动创建配置文件

        修复：初始化向导场景下，ConfigManager(allow_default=True) 不应
        自动创建 config.json，否则会导致 _is_already_initialized() 误判。
        """
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager(allow_default=True)
                # allow_default=True 时不应自动创建配置文件
                assert not cm.config_file.exists()
                # 但 base_dir 等属性应正确设置
                assert cm.base_dir == tmp_path / ".nanobot-runner"

    def test_save_config(self, tmp_path):
        """测试保存配置"""
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()
                test_config = {
                    "version": "0.2.0",
                    "data_dir": str(tmp_path / "data"),
                    "custom_key": "custom_value",
                }
                cm.save_config(test_config)

                with open(cm.config_file, encoding="utf-8") as f:
                    saved_config = json.load(f)

                assert saved_config["version"] == "0.2.0"
                assert saved_config["data_dir"] == str(tmp_path / "data")
                assert saved_config["custom_key"] == "custom_value"

    def test_load_config(self, tmp_path):
        """测试加载配置"""
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()

                # 先保存测试配置
                test_config = {
                    "version": "0.1.0",
                    "data_dir": str(tmp_path / "data"),
                    "test_key": "test_value",
                }
                cm.save_config(test_config)

                loaded_config = cm.load_config()
                assert loaded_config["test_key"] == "test_value"

    def test_get_existing_key(self, tmp_path):
        """测试获取存在的配置项"""
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()

                # 设置测试配置
                cm.save_config(
                    {
                        "version": "0.1.0",
                        "data_dir": str(tmp_path / "data"),
                        "test_key": "test_value",
                    }
                )

                value = cm.get("test_key")
                assert value == "test_value"

    def test_get_non_existing_key(self, tmp_path):
        """测试获取不存在的配置项"""
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()

                value = cm.get("non_existing_key")
                assert value is None

    def test_get_with_default(self, tmp_path):
        """测试获取配置项并提供默认值"""
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()

                value = cm.get("non_existing_key", "default_value")
                assert value == "default_value"

    def test_set_config(self, tmp_path):
        """测试设置配置项"""
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()

                cm.set("new_key", "new_value")

                loaded_config = cm.load_config()
                assert loaded_config["new_key"] == "new_value"

    def test_singleton_instance(self):
        """测试全局单例实例"""
        assert config is not None
        assert isinstance(config, ConfigManager)

    def test_cache_mechanism(self, tmp_path):
        """测试配置缓存机制"""
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()

                cm._invalidate_cache()

                config1 = cm.load_config()
                config2 = cm.load_config()

                assert config1 == config2
                assert ConfigManager._cache is not None

    def test_cache_invalidation_on_save(self, tmp_path):
        """测试保存配置时缓存失效"""
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()

                cm.load_config()
                assert ConfigManager._cache is not None

                cm.save_config(
                    {
                        "version": "0.1.0",
                        "data_dir": str(tmp_path / "data"),
                        "new_key": "new_value",
                    }
                )

                assert ConfigManager._cache is None

    def test_cache_invalidation_manual(self, tmp_path):
        """测试手动清除缓存"""
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()

                cm.load_config()
                assert ConfigManager._cache is not None

                cm._invalidate_cache()
                assert ConfigManager._cache is None

    def test_reload_config(self, tmp_path):
        """测试强制重新加载配置"""
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()

                config1 = cm.load_config()

                with open(cm.config_file, encoding="utf-8") as f:
                    raw_config = json.load(f)
                raw_config["manual_key"] = "manual_value"
                with open(cm.config_file, "w", encoding="utf-8") as f:
                    json.dump(raw_config, f)

                config2 = cm.reload_config()

                assert "manual_key" in config2
                assert config2["manual_key"] == "manual_value"

    def test_load_config_without_cache(self, tmp_path):
        """测试不使用缓存加载配置"""
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()

                cm._invalidate_cache()

                config1 = cm.load_config(use_cache=False)
                assert ConfigManager._cache is not None

                config2 = cm.load_config(use_cache=False)
                assert config1 == config2

    def test_cache_ttl_expiration(self, tmp_path):
        """测试缓存 TTL 过期"""
        import time

        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()

                original_ttl = ConfigManager._cache_ttl
                ConfigManager._cache_ttl = 0.1

                try:
                    cm._invalidate_cache()
                    cm.load_config()

                    time.sleep(0.15)

                    assert not cm._is_cache_valid()
                finally:
                    ConfigManager._cache_ttl = original_ttl

    def test_cache_file_modification_detection(self, tmp_path):
        """测试文件修改检测"""
        import time

        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()

                cm._invalidate_cache()
                cm.load_config()

                time.sleep(0.01)

                with open(cm.config_file, "w", encoding="utf-8") as f:
                    json.dump(
                        {
                            "version": "0.1.0",
                            "data_dir": str(tmp_path / "data"),
                            "modified": True,
                        },
                        f,
                    )

                assert not cm._is_cache_valid()


class TestNanobotConfigLoading:
    """测试 nanobot_config.json 读取功能（v0.32.0）"""

    def test_get_nanobot_config_path(self, tmp_path):
        """测试获取 nanobot_config.json 路径"""
        with patch.dict(os.environ, {"NANOBOT_CONFIG_DIR": str(tmp_path)}):
            ConfigManager.reset_cache()
            cm = ConfigManager(allow_default=True)
            assert cm.get_nanobot_config_path() == tmp_path / "nanobot_config.json"

    def test_load_nanobot_config_not_exists(self, tmp_path):
        """nanobot_config.json 不存在时返回空 dict"""
        with patch.dict(os.environ, {"NANOBOT_CONFIG_DIR": str(tmp_path)}):
            ConfigManager.reset_cache()
            cm = ConfigManager(allow_default=True)
            result = cm.load_nanobot_config()
            assert result == {}

    def test_load_nanobot_config_exists(self, tmp_path):
        """nanobot_config.json 存在时返回配置字典"""
        nano_config = {
            "providers": {
                "default": "custom",
                "custom": {"apiKey": "sk-test", "apiBase": "https://api.test.com/v1"},
            },
            "agents": {"defaults": {"model": "test-model"}},
        }
        nano_path = tmp_path / "nanobot_config.json"
        nano_path.write_text(json.dumps(nano_config), encoding="utf-8")

        with patch.dict(os.environ, {"NANOBOT_CONFIG_DIR": str(tmp_path)}):
            ConfigManager.reset_cache()
            cm = ConfigManager(allow_default=True)
            result = cm.load_nanobot_config()
            assert result["providers"]["default"] == "custom"
            assert result["agents"]["defaults"]["model"] == "test-model"

    def test_has_llm_config_true(self, tmp_path):
        """nanobot_config.json 有有效 provider+apiKey 时 has_llm_config 返回 True"""
        nano_config = {
            "providers": {
                "default": "custom",
                "custom": {"apiKey": "sk-test", "apiBase": "https://api.test.com/v1"},
            },
        }
        nano_path = tmp_path / "nanobot_config.json"
        nano_path.write_text(json.dumps(nano_config), encoding="utf-8")

        with patch.dict(os.environ, {"NANOBOT_CONFIG_DIR": str(tmp_path)}):
            ConfigManager.reset_cache()
            cm = ConfigManager(allow_default=True)
            assert cm.has_llm_config() is True

    def test_has_llm_config_false_no_file(self, tmp_path):
        """nanobot_config.json 不存在时 has_llm_config 返回 False"""
        with patch.dict(os.environ, {"NANOBOT_CONFIG_DIR": str(tmp_path)}):
            ConfigManager.reset_cache()
            cm = ConfigManager(allow_default=True)
            assert cm.has_llm_config() is False

    def test_has_llm_config_false_no_api_key(self, tmp_path):
        """provider 存在但 apiKey 为空时 has_llm_config 返回 False"""
        nano_config = {
            "providers": {
                "default": "custom",
                "custom": {"apiKey": "", "apiBase": "https://api.test.com/v1"},
            },
        }
        nano_path = tmp_path / "nanobot_config.json"
        nano_path.write_text(json.dumps(nano_config), encoding="utf-8")

        with patch.dict(os.environ, {"NANOBOT_CONFIG_DIR": str(tmp_path)}):
            ConfigManager.reset_cache()
            cm = ConfigManager(allow_default=True)
            assert cm.has_llm_config() is False

    def test_resolve_webui_dist_returns_path_or_none(self, tmp_path):
        """resolve_webui_dist 返回 Path 或 None"""
        with patch.dict(os.environ, {"NANOBOT_CONFIG_DIR": str(tmp_path)}):
            ConfigManager.reset_cache()
            cm = ConfigManager(allow_default=True)
            result = cm.resolve_webui_dist()
            assert result is None or isinstance(result, Path)


class TestLegacyFieldsWarning:
    """测试旧版 config.json 字段检测（规格 7.3 向后兼容）"""

    def test_check_legacy_fields_returns_list(self, tmp_path):
        """config.json 含 llm_provider 等旧字段时返回字段列表"""
        config_data = {
            "version": "0.32.0",
            "data_dir": str(tmp_path / "data"),
            "llm_provider": "openai",
            "llm_model": "gpt-4o-mini",
        }
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config_data), encoding="utf-8")
        (tmp_path / "data").mkdir()

        with patch.dict(os.environ, {"NANOBOT_CONFIG_DIR": str(tmp_path)}):
            ConfigManager.reset_cache()
            cm = ConfigManager(allow_default=True)
            legacy = cm.check_legacy_fields()

        assert "llm_provider" in legacy
        assert "llm_model" in legacy

    def test_check_legacy_fields_empty_when_clean(self, tmp_path):
        """config.json 无旧字段时返回空列表"""
        config_data = {
            "version": "0.32.0",
            "data_dir": str(tmp_path / "data"),
        }
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config_data), encoding="utf-8")
        (tmp_path / "data").mkdir()

        with patch.dict(os.environ, {"NANOBOT_CONFIG_DIR": str(tmp_path)}):
            ConfigManager.reset_cache()
            cm = ConfigManager(allow_default=True)
            assert cm.check_legacy_fields() == []
