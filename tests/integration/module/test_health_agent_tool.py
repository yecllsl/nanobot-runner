# 健康数据同步MCP工具集成测试
# 验证Agent能够通过自然语言调用健康数据MCP工具

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.tools.mcp_connector import connect_mcp_tools_from_config


@pytest.fixture
def config_with_coros_mcp(tmp_path: Path) -> Path:
    """创建包含COROS健康数据MCP服务器配置的config.json"""
    config_path = tmp_path / "config.json"
    config = {
        "version": "0.13.0",
        "data_dir": str(tmp_path / "data"),
        "timezone": "Asia/Shanghai",
        "tools": {
            "mcp_servers": {
                "coros": {
                    "type": "stdio",
                    "command": "npx",
                    "args": ["-y", "coros-cli", "mcp"],
                    "tool_timeout": 30,
                    "enabled_tools": ["*"],
                }
            }
        },
    }
    config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
    return config_path


class TestHealthDataMCPToolIntegration:
    """健康数据MCP工具集成测试"""

    @pytest.mark.asyncio
    async def test_coros_mcp_config_loaded_correctly(self, config_with_coros_mcp: Path):
        """测试COROS健康数据MCP配置正确加载"""
        from src.core.tools.mcp_config_helper import MCPConfigHelper

        helper = MCPConfigHelper(config_with_coros_mcp)
        tools_config = helper.load_tools_config()

        assert tools_config.mcp_servers is not None
        assert "coros" in tools_config.mcp_servers

        coros_config = tools_config.mcp_servers["coros"]
        assert coros_config.command == "npx"
        assert coros_config.args == ["-y", "coros-cli", "mcp"]
        assert coros_config.transport_type.value == "stdio"
        assert coros_config.tool_timeout == 30

    @pytest.mark.asyncio
    @patch("nanobot.agent.tools.mcp.connect_mcp_servers", new_callable=AsyncMock)
    async def test_coros_mcp_server_connected(
        self, mock_connect, config_with_coros_mcp: Path
    ):
        """测试COROS健康数据MCP服务器成功连接"""
        from contextlib import AsyncExitStack

        mock_exit_stack = AsyncExitStack()
        mock_connect.return_value = {"coros": mock_exit_stack}

        registry = MagicMock()
        result = await connect_mcp_tools_from_config(config_with_coros_mcp, registry)

        assert "coros" in result["connected_servers"]
        assert result["failed_servers"] == []
        assert "coros" in result["exit_stacks"]

        mock_connect.assert_called_once()
        call_args = mock_connect.call_args
        mcp_servers_dict = call_args[0][0]
        assert "coros" in mcp_servers_dict

    @pytest.mark.asyncio
    @patch("nanobot.agent.tools.mcp.connect_mcp_servers", new_callable=AsyncMock)
    async def test_coros_tool_registered_to_agent(
        self, mock_connect, config_with_coros_mcp: Path
    ):
        """测试健康数据工具注册到Agent"""
        from contextlib import AsyncExitStack

        mock_exit_stack = AsyncExitStack()
        mock_connect.return_value = {"coros": mock_exit_stack}

        registry = MagicMock()
        await connect_mcp_tools_from_config(config_with_coros_mcp, registry)

        mock_connect.assert_called_once()
        call_args = mock_connect.call_args
        tool_registry = call_args[0][1]
        assert tool_registry == registry

    @pytest.mark.asyncio
    @patch("nanobot.agent.tools.mcp.connect_mcp_servers", new_callable=AsyncMock)
    async def test_coros_tool_naming_convention(
        self, mock_connect, config_with_coros_mcp: Path
    ):
        """测试健康数据工具命名规范（mcp_coros_*）"""
        from contextlib import AsyncExitStack

        mock_exit_stack = AsyncExitStack()
        mock_connect.return_value = {"coros": mock_exit_stack}

        registry = MagicMock()
        await connect_mcp_tools_from_config(config_with_coros_mcp, registry)

        mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_coros_mcp_connection_failure_handling(
        self, config_with_coros_mcp: Path
    ):
        """测试健康数据MCP连接失败的优雅降级"""
        with patch("nanobot.agent.tools.mcp.connect_mcp_servers") as mock_connect:
            mock_connect.side_effect = Exception("Connection failed")

            registry = MagicMock()
            result = await connect_mcp_tools_from_config(
                config_with_coros_mcp, registry
            )

            assert result["connected_servers"] == []
            assert "coros" in result["failed_servers"]
            assert result["exit_stacks"] == {}

    @pytest.mark.asyncio
    async def test_coros_mcp_disabled_server_skipped(self, tmp_path: Path):
        """测试禁用的健康数据MCP服务器被跳过"""
        config_path = tmp_path / "config.json"
        config = {
            "version": "0.13.0",
            "data_dir": str(tmp_path / "data"),
            "tools": {
                "mcp_servers": {
                    "coros": {
                        "type": "stdio",
                        "command": "npx",
                        "args": ["-y", "coros-cli", "mcp"],
                        "disabled": True,
                        "enabled_tools": ["*"],
                    }
                }
            },
        }
        config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")

        registry = MagicMock()
        result = await connect_mcp_tools_from_config(config_path, registry)

        assert result["connected_servers"] == []
        assert result["failed_servers"] == []
        assert result["exit_stacks"] == {}

    @pytest.mark.asyncio
    @patch("nanobot.agent.tools.mcp.connect_mcp_servers", new_callable=AsyncMock)
    async def test_coros_tool_timeout_configuration(self, mock_connect, tmp_path: Path):
        """测试健康数据工具超时配置正确传递"""
        from contextlib import AsyncExitStack

        config_path = tmp_path / "config.json"
        config = {
            "version": "0.13.0",
            "data_dir": str(tmp_path / "data"),
            "tools": {
                "mcp_servers": {
                    "coros": {
                        "type": "stdio",
                        "command": "npx",
                        "args": ["-y", "coros-cli", "mcp"],
                        "tool_timeout": 60,
                        "enabled_tools": ["*"],
                    }
                }
            },
        }
        config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")

        mock_exit_stack = AsyncExitStack()
        mock_connect.return_value = {"coros": mock_exit_stack}

        registry = MagicMock()
        await connect_mcp_tools_from_config(config_path, registry)

        mock_connect.assert_called_once()
        call_args = mock_connect.call_args
        mcp_servers_dict = call_args[0][0]
        assert mcp_servers_dict["coros"].tool_timeout == 60

    @pytest.mark.asyncio
    @patch("nanobot.agent.tools.mcp.connect_mcp_servers", new_callable=AsyncMock)
    async def test_multiple_health_tools_integration(
        self, mock_connect, tmp_path: Path
    ):
        """测试多个健康数据工具同时集成"""
        from contextlib import AsyncExitStack

        config_path = tmp_path / "config.json"
        config = {
            "version": "0.13.0",
            "data_dir": str(tmp_path / "data"),
            "tools": {
                "mcp_servers": {
                    "coros": {
                        "type": "stdio",
                        "command": "npx",
                        "args": ["-y", "coros-cli", "mcp"],
                        "enabled_tools": ["*"],
                    },
                    "health_sync": {
                        "type": "stdio",
                        "command": "uvx",
                        "args": ["health-sync-mcp"],
                        "enabled_tools": ["*"],
                    },
                }
            },
        }
        config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")

        mock_exit_stack = AsyncExitStack()
        mock_connect.return_value = {
            "coros": mock_exit_stack,
            "health_sync": mock_exit_stack,
        }

        registry = MagicMock()
        result = await connect_mcp_tools_from_config(config_path, registry)

        assert "coros" in result["connected_servers"]
        assert "health_sync" in result["connected_servers"]
        assert result["failed_servers"] == []
