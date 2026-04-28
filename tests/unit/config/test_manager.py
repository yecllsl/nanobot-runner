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

                assert config_data["version"] == "0.9.4"
                assert "data_dir" in config_data
                assert "auto_push_feishu" in config_data
                assert "feishu_app_id" in config_data

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

    def test_migrate_old_cron_config(self, tmp_path):
        """测试迁移旧的定时任务配置"""
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                old_cron_dir = tmp_path / ".nanobot" / "cron"
                old_cron_dir.mkdir(parents=True, exist_ok=True)

                old_cron_store = old_cron_dir / "jobs.json"
                old_jobs = {"jobs": [{"id": "test1", "name": "test_job"}]}
                with open(old_cron_store, "w", encoding="utf-8") as f:
                    json.dump(old_jobs, f)

                cm = ConfigManager()

                new_cron_store = cm.cron_store
                assert new_cron_store.exists()

                with open(new_cron_store, encoding="utf-8") as f:
                    migrated_jobs = json.load(f)

                assert migrated_jobs["jobs"][0]["id"] == "test1"
                assert migrated_jobs["jobs"][0]["name"] == "test_job"

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
