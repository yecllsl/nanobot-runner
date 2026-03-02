# 配置管理单元测试
# 测试配置管理器的功能

import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.core.config import ConfigManager, config


class TestConfigManager:
    """测试配置管理器"""

    def test_init(self, tmp_path):
        """测试初始化"""
        with patch.object(Path, 'home', return_value=tmp_path):
            cm = ConfigManager()
            assert cm.base_dir == tmp_path / ".nanobot-runner"
            assert cm.data_dir == cm.base_dir / "data"
            assert cm.config_file == cm.base_dir / "config.json"
            assert cm.index_file == cm.data_dir / "index.json"

    def test_ensure_dirs(self, tmp_path):
        """测试确保目录存在"""
        with patch.object(Path, 'home', return_value=tmp_path):
            cm = ConfigManager()
            assert cm.base_dir.exists()
            assert cm.data_dir.exists()

    def test_ensure_config_default(self, tmp_path):
        """测试创建默认配置"""
        with patch.object(Path, 'home', return_value=tmp_path):
            cm = ConfigManager()
            assert cm.config_file.exists()
            
            with open(cm.config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            assert config_data["version"] == "0.1.0"
            assert "data_dir" in config_data
            assert "auto_push_feishu" in config_data
            assert "feishu_webhook" in config_data

    def test_save_config(self, tmp_path):
        """测试保存配置"""
        with patch.object(Path, 'home', return_value=tmp_path):
            cm = ConfigManager()
            test_config = {
                "version": "0.2.0",
                "custom_key": "custom_value"
            }
            cm.save_config(test_config)
            
            with open(cm.config_file, 'r', encoding='utf-8') as f:
                saved_config = json.load(f)
            
            assert saved_config["version"] == "0.2.0"
            assert saved_config["custom_key"] == "custom_value"

    def test_load_config(self, tmp_path):
        """测试加载配置"""
        with patch.object(Path, 'home', return_value=tmp_path):
            cm = ConfigManager()
            
            # 先保存测试配置
            test_config = {"test_key": "test_value"}
            cm.save_config(test_config)
            
            loaded_config = cm.load_config()
            assert loaded_config["test_key"] == "test_value"

    def test_get_existing_key(self, tmp_path):
        """测试获取存在的配置项"""
        with patch.object(Path, 'home', return_value=tmp_path):
            cm = ConfigManager()
            
            # 设置测试配置
            cm.save_config({"test_key": "test_value"})
            
            value = cm.get("test_key")
            assert value == "test_value"

    def test_get_non_existing_key(self, tmp_path):
        """测试获取不存在的配置项"""
        with patch.object(Path, 'home', return_value=tmp_path):
            cm = ConfigManager()
            
            value = cm.get("non_existing_key")
            assert value is None

    def test_get_with_default(self, tmp_path):
        """测试获取配置项并提供默认值"""
        with patch.object(Path, 'home', return_value=tmp_path):
            cm = ConfigManager()
            
            value = cm.get("non_existing_key", "default_value")
            assert value == "default_value"

    def test_set_config(self, tmp_path):
        """测试设置配置项"""
        with patch.object(Path, 'home', return_value=tmp_path):
            cm = ConfigManager()
            
            cm.set("new_key", "new_value")
            
            loaded_config = cm.load_config()
            assert loaded_config["new_key"] == "new_value"

    def test_singleton_instance(self):
        """测试全局单例实例"""
        assert config is not None
        assert isinstance(config, ConfigManager)
