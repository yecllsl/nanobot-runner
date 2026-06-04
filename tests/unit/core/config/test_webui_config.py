"""WebUI 配置读取单元测试"""

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from src.core.config.manager import ConfigManager


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    """创建包含 webui 配置的临时目录"""
    config_data = {
        "version": "0.28.0",
        "data_dir": str(tmp_path / "data"),
        "webui": {
            "enabled": True,
            "host": "0.0.0.0",
            "port": 9090,
            "cors_origins": ["http://localhost:3000"],
            "token_secret": "test-secret-key",
            "token_ttl_s": 3600,
        },
    }
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config_data), encoding="utf-8")
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return tmp_path


class TestGetWebuiConfig:
    def test_returns_webui_config_from_file(self, config_dir: Path) -> None:
        """从配置文件读取 webui 配置"""
        with patch.dict(os.environ, {"NANOBOT_CONFIG_DIR": str(config_dir)}):
            ConfigManager.reset_cache()
            mgr = ConfigManager()
            result = mgr.get_webui_config()

        assert result["enabled"] is True
        assert result["host"] == "0.0.0.0"
        assert result["port"] == 9090
        assert result["cors_origins"] == ["http://localhost:3000"]
        assert result["token_secret"] == "test-secret-key"
        assert result["token_ttl_s"] == 3600

    def test_returns_empty_dict_when_no_webui_section(self, tmp_path: Path) -> None:
        """配置文件无 webui 节时返回含默认值的 dict"""
        config_data = {
            "version": "0.28.0",
            "data_dir": str(tmp_path / "data"),
        }
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config_data), encoding="utf-8")
        (tmp_path / "data").mkdir()

        with patch.dict(os.environ, {"NANOBOT_CONFIG_DIR": str(tmp_path)}):
            ConfigManager.reset_cache()
            mgr = ConfigManager()
            result = mgr.get_webui_config()

        assert result["enabled"] is False
        assert result["host"] == "127.0.0.1"
        assert result["port"] == 8766

    def test_env_override_port(self, config_dir: Path) -> None:
        """环境变量覆盖 webui.port"""
        with patch.dict(
            os.environ,
            {
                "NANOBOT_CONFIG_DIR": str(config_dir),
                "NANOBOT_WEBUI_PORT": "9999",
            },
        ):
            ConfigManager.reset_cache()
            mgr = ConfigManager()
            result = mgr.get_webui_config()

        assert result["port"] == 9999

    def test_env_override_enabled(self, config_dir: Path) -> None:
        """环境变量覆盖 webui.enabled"""
        with patch.dict(
            os.environ,
            {
                "NANOBOT_CONFIG_DIR": str(config_dir),
                "NANOBOT_WEBUI_ENABLED": "false",
            },
        ):
            ConfigManager.reset_cache()
            mgr = ConfigManager()
            result = mgr.get_webui_config()

        assert result["enabled"] is False

    def test_defaults_when_missing_fields(self, tmp_path: Path) -> None:
        """webui 配置节存在但字段缺失时使用默认值"""
        config_data = {
            "version": "0.28.0",
            "data_dir": str(tmp_path / "data"),
            "webui": {"enabled": True},
        }
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config_data), encoding="utf-8")
        (tmp_path / "data").mkdir()

        with patch.dict(os.environ, {"NANOBOT_CONFIG_DIR": str(tmp_path)}):
            ConfigManager.reset_cache()
            mgr = ConfigManager()
            result = mgr.get_webui_config()

        assert result["enabled"] is True
        assert result["host"] == "127.0.0.1"
        assert result["port"] == 8766
