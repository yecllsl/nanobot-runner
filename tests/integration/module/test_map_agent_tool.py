# 地图服务MCP工具集成测试
# 验证Agent能够通过自然语言调用地图MCP工具

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.tools.mcp_connector import connect_mcp_tools_from_config


@pytest.fixture
def config_with_osm_mcp(tmp_path: Path) -> Path:
    """创建包含OSM地图MCP服务器配置的config.json"""
    config_path = tmp_path / "config.json"
    config = {
        "version": "0.13.0",
        "data_dir": str(tmp_path / "data"),
        "timezone": "Asia/Shanghai",
        "tools": {
            "mcp_servers": {
                "osm": {
                    "type": "stdio",
                    "command": "uvx",
                    "args": ["osm-mcp-server"],
                    "tool_timeout": 30,
                    "enabled_tools": ["*"],
                }
            }
        },
    }
    config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
    return config_path


class TestMapMCPToolIntegration:
    """地图MCP工具集成测试"""

    @pytest.mark.asyncio
    async def test_osm_mcp_config_loaded_correctly(self, config_with_osm_mcp: Path):
        """测试OSM地图MCP配置正确加载"""
        from src.core.tools.mcp_config_helper import MCPConfigHelper

        helper = MCPConfigHelper(config_with_osm_mcp)
        tools_config = helper.load_tools_config()

        assert tools_config.mcp_servers is not None
        assert "osm" in tools_config.mcp_servers

        osm_config = tools_config.mcp_servers["osm"]
        assert osm_config.command == "uvx"
        assert osm_config.args == ["osm-mcp-server"]
        assert osm_config.transport_type.value == "stdio"
        assert osm_config.tool_timeout == 30

    @pytest.mark.asyncio
    @patch("nanobot.agent.tools.mcp.connect_mcp_servers", new_callable=AsyncMock)
    async def test_osm_mcp_server_connected(
        self, mock_connect, config_with_osm_mcp: Path
    ):
        """测试OSM地图MCP服务器成功连接"""
        from contextlib import AsyncExitStack

        mock_exit_stack = AsyncExitStack()
        mock_connect.return_value = {"osm": mock_exit_stack}

        registry = MagicMock()
        result = await connect_mcp_tools_from_config(config_with_osm_mcp, registry)

        assert "osm" in result["connected_servers"]
        assert result["failed_servers"] == []
        assert "osm" in result["exit_stacks"]

        mock_connect.assert_called_once()
        call_args = mock_connect.call_args
        mcp_servers_dict = call_args[0][0]
        assert "osm" in mcp_servers_dict

    @pytest.mark.asyncio
    @patch("nanobot.agent.tools.mcp.connect_mcp_servers", new_callable=AsyncMock)
    async def test_osm_tool_registered_to_agent(
        self, mock_connect, config_with_osm_mcp: Path
    ):
        """测试地图工具注册到Agent"""
        from contextlib import AsyncExitStack

        mock_exit_stack = AsyncExitStack()
        mock_connect.return_value = {"osm": mock_exit_stack}

        registry = MagicMock()
        await connect_mcp_tools_from_config(config_with_osm_mcp, registry)

        mock_connect.assert_called_once()
        call_args = mock_connect.call_args
        tool_registry = call_args[0][1]
        assert tool_registry == registry

    @pytest.mark.asyncio
    @patch("nanobot.agent.tools.mcp.connect_mcp_servers", new_callable=AsyncMock)
    async def test_osm_tool_naming_convention(
        self, mock_connect, config_with_osm_mcp: Path
    ):
        """测试地图工具命名规范（mcp_osm_*）"""
        from contextlib import AsyncExitStack

        mock_exit_stack = AsyncExitStack()
        mock_connect.return_value = {"osm": mock_exit_stack}

        registry = MagicMock()
        await connect_mcp_tools_from_config(config_with_osm_mcp, registry)

        mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_osm_mcp_connection_failure_handling(self, config_with_osm_mcp: Path):
        """测试地图MCP连接失败的优雅降级"""
        with patch("nanobot.agent.tools.mcp.connect_mcp_servers") as mock_connect:
            mock_connect.side_effect = Exception("Connection failed")

            registry = MagicMock()
            result = await connect_mcp_tools_from_config(config_with_osm_mcp, registry)

            assert result["connected_servers"] == []
            assert "osm" in result["failed_servers"]
            assert result["exit_stacks"] == {}

    @pytest.mark.asyncio
    async def test_osm_mcp_disabled_server_skipped(self, tmp_path: Path):
        """测试禁用的地图MCP服务器被跳过"""
        config_path = tmp_path / "config.json"
        config = {
            "version": "0.13.0",
            "data_dir": str(tmp_path / "data"),
            "tools": {
                "mcp_servers": {
                    "osm": {
                        "type": "stdio",
                        "command": "uvx",
                        "args": ["osm-mcp-server"],
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
    async def test_osm_tool_timeout_configuration(self, mock_connect, tmp_path: Path):
        """测试地图工具超时配置正确传递"""
        from contextlib import AsyncExitStack

        config_path = tmp_path / "config.json"
        config = {
            "version": "0.13.0",
            "data_dir": str(tmp_path / "data"),
            "tools": {
                "mcp_servers": {
                    "osm": {
                        "type": "stdio",
                        "command": "uvx",
                        "args": ["osm-mcp-server"],
                        "tool_timeout": 60,
                        "enabled_tools": ["*"],
                    }
                }
            },
        }
        config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")

        mock_exit_stack = AsyncExitStack()
        mock_connect.return_value = {"osm": mock_exit_stack}

        registry = MagicMock()
        await connect_mcp_tools_from_config(config_path, registry)

        mock_connect.assert_called_once()
        call_args = mock_connect.call_args
        mcp_servers_dict = call_args[0][0]
        assert mcp_servers_dict["osm"].tool_timeout == 60
