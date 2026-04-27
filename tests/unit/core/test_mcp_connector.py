# MCP工具连接器单元测试
# 测试connect_mcp_tools_from_config和load_mcp_servers_config函数

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.tools.mcp_connector import (
    connect_mcp_tools_from_config,
    load_mcp_servers_config,
)


@pytest.fixture
def config_with_weather(tmp_path: Path) -> Path:
    """创建包含天气MCP服务器配置的config.json"""
    config_path = tmp_path / "config.json"
    config = {
        "version": "0.13.0",
        "data_dir": str(tmp_path / "data"),
        "tools": {
            "mcp_servers": {
                "weather": {
                    "type": "stdio",
                    "command": "npx",
                    "args": ["-y", "@dangahagan/weather-mcp"],
                    "tool_timeout": 30,
                    "enabled_tools": ["*"],
                }
            }
        },
    }
    config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
    return config_path


@pytest.fixture
def config_with_disabled_server(tmp_path: Path) -> Path:
    """创建包含已禁用MCP服务器的config.json"""
    config_path = tmp_path / "config.json"
    config = {
        "version": "0.13.0",
        "data_dir": str(tmp_path / "data"),
        "tools": {
            "mcp_servers": {
                "weather": {
                    "type": "stdio",
                    "command": "npx",
                    "args": ["-y", "@dangahagan/weather-mcp"],
                    "disabled": True,
                    "enabled_tools": ["*"],
                }
            }
        },
    }
    config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
    return config_path


@pytest.fixture
def config_without_tools(tmp_path: Path) -> Path:
    """创建不包含工具配置的config.json"""
    config_path = tmp_path / "config.json"
    config = {
        "version": "0.13.0",
        "data_dir": str(tmp_path / "data"),
    }
    config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
    return config_path


class TestLoadMcpServersConfig:
    """测试load_mcp_servers_config函数"""

    def test_load_weather_config(self, config_with_weather: Path):
        """测试加载天气MCP服务器配置"""
        result = load_mcp_servers_config(config_with_weather)

        assert "weather" in result
        weather = result["weather"]
        assert weather.type == "stdio"
        assert weather.command == "npx"
        assert weather.args == ["-y", "@dangahagan/weather-mcp"]

    def test_skip_disabled_server(self, config_with_disabled_server: Path):
        """测试跳过已禁用的MCP服务器"""
        result = load_mcp_servers_config(config_with_disabled_server)
        assert "weather" not in result

    def test_empty_config(self, config_without_tools: Path):
        """测试无工具配置时返回空字典"""
        result = load_mcp_servers_config(config_without_tools)
        assert result == {}

    def test_nonexistent_config(self, tmp_path: Path):
        """测试配置文件不存在时返回空字典"""
        result = load_mcp_servers_config(tmp_path / "nonexistent.json")
        assert result == {}


class TestConnectMcpToolsFromConfig:
    """测试connect_mcp_tools_from_config函数"""

    @pytest.mark.asyncio
    async def test_no_mcp_servers(self, config_without_tools: Path):
        """测试无MCP服务器配置时的处理"""
        registry = MagicMock()
        result = await connect_mcp_tools_from_config(config_without_tools, registry)

        assert result["connected_servers"] == []
        assert result["failed_servers"] == []
        assert result["exit_stacks"] == {}

    @pytest.mark.asyncio
    async def test_all_disabled_servers(self, config_with_disabled_server: Path):
        """测试所有MCP服务器都禁用时的处理"""
        registry = MagicMock()
        result = await connect_mcp_tools_from_config(
            config_with_disabled_server, registry
        )

        assert result["connected_servers"] == []
        assert result["failed_servers"] == []
        assert result["exit_stacks"] == {}

    @pytest.mark.asyncio
    @patch("nanobot.agent.tools.mcp.connect_mcp_servers", new_callable=AsyncMock)
    async def test_successful_connection(self, mock_connect, config_with_weather: Path):
        """测试成功连接MCP服务器"""
        from contextlib import AsyncExitStack

        mock_exit_stack = AsyncExitStack()
        mock_connect.return_value = {"weather": mock_exit_stack}

        registry = MagicMock()
        result = await connect_mcp_tools_from_config(config_with_weather, registry)

        assert "weather" in result["connected_servers"]
        assert result["failed_servers"] == []
        mock_connect.assert_called_once()

        call_args = mock_connect.call_args
        mcp_servers_dict = call_args[0][0]
        assert "weather" in mcp_servers_dict
        assert mcp_servers_dict["weather"].type == "stdio"

    @pytest.mark.asyncio
    @patch("nanobot.agent.tools.mcp.connect_mcp_servers", new_callable=AsyncMock)
    async def test_connection_failure(self, mock_connect, config_with_weather: Path):
        """测试MCP服务器连接失败"""
        mock_connect.side_effect = Exception("Connection failed")

        registry = MagicMock()
        result = await connect_mcp_tools_from_config(config_with_weather, registry)

        assert result["connected_servers"] == []
        assert "weather" in result["failed_servers"]

    @pytest.mark.asyncio
    @patch("nanobot.agent.tools.mcp.connect_mcp_servers", new_callable=AsyncMock)
    async def test_partial_connection_failure(self, mock_connect, tmp_path: Path):
        """测试部分MCP服务器连接失败"""
        from contextlib import AsyncExitStack

        config_path = tmp_path / "config.json"
        config = {
            "version": "0.13.0",
            "data_dir": str(tmp_path / "data"),
            "tools": {
                "mcp_servers": {
                    "weather": {
                        "type": "stdio",
                        "command": "npx",
                        "args": ["-y", "@dangahagan/weather-mcp"],
                        "enabled_tools": ["*"],
                    },
                    "map": {
                        "type": "sse",
                        "url": "https://api.map.com/sse",
                        "enabled_tools": ["*"],
                    },
                }
            },
        }
        config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")

        mock_exit_stack = AsyncExitStack()
        mock_connect.return_value = {"weather": mock_exit_stack}

        registry = MagicMock()
        result = await connect_mcp_tools_from_config(config_path, registry)

        assert "weather" in result["connected_servers"]
        assert "map" in result["failed_servers"]

    @pytest.mark.asyncio
    async def test_nanobot_sdk_not_available(self, config_with_weather: Path):
        """测试nanobot SDK不可用时的降级处理"""
        registry = MagicMock()

        with patch.dict("sys.modules", {"nanobot.agent.tools.mcp": None}):
            result = await connect_mcp_tools_from_config(config_with_weather, registry)

            assert result["connected_servers"] == []
            assert "weather" in result["failed_servers"]
