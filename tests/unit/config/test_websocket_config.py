# WebSocket 配置读取单元测试
# 测试 ConfigManager.get_websocket_config() 的配置文件读取、环境变量覆盖、类型转换等场景

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from src.core.config.manager import ConfigManager


@pytest.fixture(autouse=True)
def reset_config_cache():
    """每个测试前重置 ConfigManager 缓存"""
    ConfigManager.reset_cache()
    yield
    ConfigManager.reset_cache()


class TestGetWebsocketConfig:
    """测试 ConfigManager.get_websocket_config()"""

    def _create_cm_with_config(self, tmp_path, config_data):
        """辅助方法：创建 ConfigManager 并写入指定配置

        Args:
            tmp_path: 临时目录
            config_data: 要写入的完整配置字典

        Returns:
            ConfigManager: 初始化完成的配置管理器实例
        """
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()
                cm.save_config(config_data)
                return cm

    # ---- 配置文件读取场景 ----

    def test_config_section_exists_with_values(self, tmp_path):
        """测试 websocket 配置节存在时正确读取所有值"""
        ws_config = {
            "enabled": True,
            "host": "192.168.1.100",
            "port": 9090,
            "token": "my-secret-token",
            "token_issue_secret": "my-signing-secret",
        }
        config_data = {
            "version": "0.9.4",
            "data_dir": str(tmp_path / "data"),
            "websocket": ws_config,
        }
        cm = self._create_cm_with_config(tmp_path, config_data)

        result = cm.get_websocket_config()

        assert result == ws_config
        assert result["enabled"] is True
        assert result["host"] == "192.168.1.100"
        assert result["port"] == 9090
        assert result["token"] == "my-secret-token"
        assert result["token_issue_secret"] == "my-signing-secret"

    def test_config_section_not_exists(self, tmp_path):
        """测试 websocket 配置节不存在时返回空 dict"""
        config_data = {
            "version": "0.9.4",
            "data_dir": str(tmp_path / "data"),
        }
        cm = self._create_cm_with_config(tmp_path, config_data)

        result = cm.get_websocket_config()

        assert result == {}

    def test_config_section_is_not_dict(self, tmp_path):
        """测试 websocket 配置节为非 dict 类型时返回空 dict"""
        # websocket 节为字符串 — mock load_config 绕过 Schema 验证
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()
                with patch.object(
                    cm,
                    "load_config",
                    return_value={
                        "version": "0.9.4",
                        "data_dir": str(tmp_path / "data"),
                        "websocket": "not_a_dict",
                    },
                ):
                    result = cm.get_websocket_config()
                    assert result == {}

    def test_config_section_is_list(self, tmp_path):
        """测试 websocket 配置节为列表类型时返回空 dict"""
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()
                with patch.object(
                    cm,
                    "load_config",
                    return_value={
                        "version": "0.9.4",
                        "data_dir": str(tmp_path / "data"),
                        "websocket": [1, 2, 3],
                    },
                ):
                    result = cm.get_websocket_config()
                    assert result == {}

    def test_config_section_is_none(self, tmp_path):
        """测试 websocket 配置节为 None 时返回空 dict"""
        config_data = {
            "version": "0.9.4",
            "data_dir": str(tmp_path / "data"),
            "websocket": None,
        }
        cm = self._create_cm_with_config(tmp_path, config_data)

        result = cm.get_websocket_config()

        assert result == {}

    def test_config_section_is_empty_dict(self, tmp_path):
        """测试 websocket 配置节为空 dict 时返回空 dict"""
        config_data = {
            "version": "0.9.4",
            "data_dir": str(tmp_path / "data"),
            "websocket": {},
        }
        cm = self._create_cm_with_config(tmp_path, config_data)

        result = cm.get_websocket_config()

        assert result == {}

    def test_partial_websocket_config(self, tmp_path):
        """测试 websocket 配置节只有部分字段时正确读取"""
        config_data = {
            "version": "0.9.4",
            "data_dir": str(tmp_path / "data"),
            "websocket": {
                "enabled": False,
                "host": "localhost",
            },
        }
        cm = self._create_cm_with_config(tmp_path, config_data)

        result = cm.get_websocket_config()

        # 只返回配置文件中存在的字段
        assert result == {"enabled": False, "host": "localhost"}
        assert "port" not in result
        assert "token" not in result
        assert "token_issue_secret" not in result

    def test_websocket_config_with_extra_fields(self, tmp_path):
        """测试 websocket 配置节包含额外字段时也一并返回"""
        config_data = {
            "version": "0.9.4",
            "data_dir": str(tmp_path / "data"),
            "websocket": {
                "enabled": True,
                "host": "0.0.0.0",
                "port": 8080,
                "custom_field": "custom_value",
            },
        }
        cm = self._create_cm_with_config(tmp_path, config_data)

        result = cm.get_websocket_config()

        assert result["custom_field"] == "custom_value"

    def test_returns_shallow_copy(self, tmp_path):
        """测试返回的是浅拷贝，修改返回值不影响原始配置"""
        config_data = {
            "version": "0.9.4",
            "data_dir": str(tmp_path / "data"),
            "websocket": {
                "enabled": True,
                "host": "localhost",
                "port": 8080,
            },
        }
        cm = self._create_cm_with_config(tmp_path, config_data)

        result = cm.get_websocket_config()
        result["enabled"] = False
        result["host"] = "modified"

        # 重新获取，应仍是原始值
        result2 = cm.get_websocket_config()
        assert result2["enabled"] is True
        assert result2["host"] == "localhost"

    # ---- 环境变量覆盖场景 ----

    def test_env_enabled_true(self, tmp_path):
        """测试 NANOBOT_WS_ENABLED=true 覆盖 enabled 为 True"""
        config_data = {
            "version": "0.9.4",
            "data_dir": str(tmp_path / "data"),
            "websocket": {"enabled": False},
        }
        with patch.dict(os.environ, {"NANOBOT_WS_ENABLED": "true"}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()
                cm.save_config(config_data)

                result = cm.get_websocket_config()

                assert result["enabled"] is True

    def test_env_enabled_yes(self, tmp_path):
        """测试 NANOBOT_WS_ENABLED=yes 覆盖 enabled 为 True"""
        config_data = {
            "version": "0.9.4",
            "data_dir": str(tmp_path / "data"),
            "websocket": {"enabled": False},
        }
        with patch.dict(os.environ, {"NANOBOT_WS_ENABLED": "yes"}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()
                cm.save_config(config_data)

                result = cm.get_websocket_config()

                assert result["enabled"] is True

    def test_env_enabled_one(self, tmp_path):
        """测试 NANOBOT_WS_ENABLED=1 覆盖 enabled 为 True"""
        config_data = {
            "version": "0.9.4",
            "data_dir": str(tmp_path / "data"),
            "websocket": {"enabled": False},
        }
        with patch.dict(os.environ, {"NANOBOT_WS_ENABLED": "1"}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()
                cm.save_config(config_data)

                result = cm.get_websocket_config()

                assert result["enabled"] is True

    def test_env_enabled_false(self, tmp_path):
        """测试 NANOBOT_WS_ENABLED=false 覆盖 enabled 为 False"""
        config_data = {
            "version": "0.9.4",
            "data_dir": str(tmp_path / "data"),
            "websocket": {"enabled": True},
        }
        with patch.dict(os.environ, {"NANOBOT_WS_ENABLED": "false"}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()
                cm.save_config(config_data)

                result = cm.get_websocket_config()

                assert result["enabled"] is False

    def test_env_enabled_case_insensitive(self, tmp_path):
        """测试 NANOBOT_WS_ENABLED 大写值也能正确转换"""
        config_data = {
            "version": "0.9.4",
            "data_dir": str(tmp_path / "data"),
            "websocket": {"enabled": False},
        }
        with patch.dict(os.environ, {"NANOBOT_WS_ENABLED": "TRUE"}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()
                cm.save_config(config_data)

                result = cm.get_websocket_config()

                assert result["enabled"] is True

    def test_env_host_override(self, tmp_path):
        """测试 NANOBOT_WS_HOST 覆盖 host"""
        config_data = {
            "version": "0.9.4",
            "data_dir": str(tmp_path / "data"),
            "websocket": {"host": "localhost"},
        }
        with patch.dict(os.environ, {"NANOBOT_WS_HOST": "10.0.0.1"}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()
                cm.save_config(config_data)

                result = cm.get_websocket_config()

                assert result["host"] == "10.0.0.1"

    def test_env_port_override(self, tmp_path):
        """测试 NANOBOT_WS_PORT 覆盖 port（整数类型转换）"""
        config_data = {
            "version": "0.9.4",
            "data_dir": str(tmp_path / "data"),
            "websocket": {"port": 8080},
        }
        with patch.dict(os.environ, {"NANOBOT_WS_PORT": "9090"}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()
                cm.save_config(config_data)

                result = cm.get_websocket_config()

                assert result["port"] == 9090
                assert isinstance(result["port"], int)

    def test_env_port_invalid_value(self, tmp_path):
        """测试 NANOBOT_WS_PORT 非数字值时保留原始字符串"""
        config_data = {
            "version": "0.9.4",
            "data_dir": str(tmp_path / "data"),
            "websocket": {"port": 8080},
        }
        with patch.dict(os.environ, {"NANOBOT_WS_PORT": "abc"}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()
                cm.save_config(config_data)

                result = cm.get_websocket_config()

                # int() 转换失败时回退为原始字符串
                assert result["port"] == "abc"

    def test_env_token_override(self, tmp_path):
        """测试 NANOBOT_WS_TOKEN 覆盖 token"""
        config_data = {
            "version": "0.9.4",
            "data_dir": str(tmp_path / "data"),
            "websocket": {"token": "old-token"},
        }
        with patch.dict(
            os.environ, {"NANOBOT_WS_TOKEN": "new-token-from-env"}, clear=True
        ):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()
                cm.save_config(config_data)

                result = cm.get_websocket_config()

                assert result["token"] == "new-token-from-env"

    def test_env_token_secret_override(self, tmp_path):
        """测试 NANOBOT_WS_TOKEN_SECRET 覆盖 token_issue_secret"""
        config_data = {
            "version": "0.9.4",
            "data_dir": str(tmp_path / "data"),
            "websocket": {"token_issue_secret": "old-secret"},
        }
        with patch.dict(
            os.environ,
            {"NANOBOT_WS_TOKEN_SECRET": "new-secret-from-env"},
            clear=True,
        ):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()
                cm.save_config(config_data)

                result = cm.get_websocket_config()

                assert result["token_issue_secret"] == "new-secret-from-env"

    def test_env_override_without_config_section(self, tmp_path):
        """测试配置文件无 websocket 节时，环境变量仍可生效"""
        config_data = {
            "version": "0.9.4",
            "data_dir": str(tmp_path / "data"),
        }
        with patch.dict(
            os.environ,
            {
                "NANOBOT_WS_ENABLED": "true",
                "NANOBOT_WS_HOST": "0.0.0.0",
                "NANOBOT_WS_PORT": "3000",
            },
            clear=True,
        ):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()
                cm.save_config(config_data)

                result = cm.get_websocket_config()

                assert result["enabled"] is True
                assert result["host"] == "0.0.0.0"
                assert result["port"] == 3000

    def test_all_env_vars_override_simultaneously(self, tmp_path):
        """测试所有 WebSocket 环境变量同时覆盖"""
        config_data = {
            "version": "0.9.4",
            "data_dir": str(tmp_path / "data"),
            "websocket": {
                "enabled": False,
                "host": "localhost",
                "port": 8080,
                "token": "file-token",
                "token_issue_secret": "file-secret",
            },
        }
        with patch.dict(
            os.environ,
            {
                "NANOBOT_WS_ENABLED": "true",
                "NANOBOT_WS_HOST": "10.20.30.40",
                "NANOBOT_WS_PORT": "9999",
                "NANOBOT_WS_TOKEN": "env-token",
                "NANOBOT_WS_TOKEN_SECRET": "env-secret",
            },
            clear=True,
        ):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()
                cm.save_config(config_data)

                result = cm.get_websocket_config()

                assert result["enabled"] is True
                assert result["host"] == "10.20.30.40"
                assert result["port"] == 9999
                assert result["token"] == "env-token"
                assert result["token_issue_secret"] == "env-secret"

    def test_env_override_priority_over_config(self, tmp_path):
        """测试环境变量优先级高于配置文件"""
        config_data = {
            "version": "0.9.4",
            "data_dir": str(tmp_path / "data"),
            "websocket": {
                "enabled": True,
                "host": "config-host",
                "port": 5000,
            },
        }
        with patch.dict(
            os.environ,
            {
                "NANOBOT_WS_HOST": "env-host",
                "NANOBOT_WS_PORT": "6000",
            },
            clear=True,
        ):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()
                cm.save_config(config_data)

                result = cm.get_websocket_config()

                # 环境变量覆盖的值
                assert result["host"] == "env-host"
                assert result["port"] == 6000
                # 配置文件的值（无对应环境变量）
                assert result["enabled"] is True

    # ---- 默认值场景 ----

    def test_no_websocket_config_no_env(self, tmp_path):
        """测试无配置节且无环境变量时返回空 dict（无默认值填充）"""
        config_data = {
            "version": "0.9.4",
            "data_dir": str(tmp_path / "data"),
        }
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()
                cm.save_config(config_data)

                result = cm.get_websocket_config()

                # get_websocket_config 不填充默认值，只返回配置文件+环境变量的合并结果
                assert result == {}

    def test_partial_config_no_env_returns_only_configured(self, tmp_path):
        """测试部分配置且无环境变量时只返回已配置的字段"""
        config_data = {
            "version": "0.9.4",
            "data_dir": str(tmp_path / "data"),
            "websocket": {
                "host": "0.0.0.0",
                "port": 3000,
            },
        }
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()
                cm.save_config(config_data)

                result = cm.get_websocket_config()

                # 只返回配置文件中存在的字段，不填充默认值
                assert result == {"host": "0.0.0.0", "port": 3000}
                assert "enabled" not in result
                assert "token" not in result
                assert "token_issue_secret" not in result

    def test_env_adds_field_to_partial_config(self, tmp_path):
        """测试环境变量为部分配置添加新字段"""
        config_data = {
            "version": "0.9.4",
            "data_dir": str(tmp_path / "data"),
            "websocket": {
                "host": "localhost",
                "port": 8080,
            },
        }
        with patch.dict(
            os.environ,
            {
                "NANOBOT_WS_ENABLED": "true",
                "NANOBOT_WS_TOKEN": "env-token",
            },
            clear=True,
        ):
            with patch.object(Path, "home", return_value=tmp_path):
                cm = ConfigManager()
                cm.save_config(config_data)

                result = cm.get_websocket_config()

                # 配置文件的值
                assert result["host"] == "localhost"
                assert result["port"] == 8080
                # 环境变量新增的字段
                assert result["enabled"] is True
                assert result["token"] == "env-token"
