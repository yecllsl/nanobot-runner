# Sprint 3 E2E测试 - 地图和健康数据工具
# 验证Agent能够通过自然语言调用地图和健康数据MCP工具

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def config_with_all_sprint3_tools(tmp_path: Path) -> Path:
    """创建包含Sprint 3所有MCP工具配置的config.json"""
    config_path = tmp_path / "config.json"
    config = {
        "version": "0.13.0",
        "data_dir": str(tmp_path / "data"),
        "timezone": "Asia/Shanghai",
        "llm_provider": "openai",
        "llm_model": "gpt-4o-mini",
        "tools": {
            "mcp_servers": {
                "weather": {
                    "type": "stdio",
                    "command": "npx",
                    "args": ["-y", "@dangahagan/weather-mcp"],
                    "tool_timeout": 30,
                    "enabled_tools": ["*"],
                },
                "osm": {
                    "type": "stdio",
                    "command": "uvx",
                    "args": ["osm-mcp-server"],
                    "tool_timeout": 30,
                    "enabled_tools": ["*"],
                },
                "coros": {
                    "type": "stdio",
                    "command": "npx",
                    "args": ["-y", "coros-cli", "mcp"],
                    "tool_timeout": 30,
                    "enabled_tools": ["*"],
                },
            }
        },
    }
    config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
    return config_path


class TestSprint3E2EIntegration:
    """Sprint 3 E2E集成测试"""

    @pytest.mark.asyncio
    @patch("nanobot.agent.tools.mcp.connect_mcp_servers", new_callable=AsyncMock)
    async def test_all_sprint3_tools_connected(
        self, mock_connect, config_with_all_sprint3_tools: Path
    ):
        """测试Sprint 3所有工具成功连接"""
        from contextlib import AsyncExitStack

        from src.core.tools.mcp_connector import connect_mcp_tools_from_config

        mock_exit_stack = AsyncExitStack()
        mock_connect.return_value = {
            "weather": mock_exit_stack,
            "osm": mock_exit_stack,
            "coros": mock_exit_stack,
        }

        registry = MagicMock()
        result = await connect_mcp_tools_from_config(
            config_with_all_sprint3_tools, registry
        )

        assert "weather" in result["connected_servers"]
        assert "osm" in result["connected_servers"]
        assert "coros" in result["connected_servers"]
        assert result["failed_servers"] == []

    @pytest.mark.asyncio
    @patch("nanobot.agent.tools.mcp.connect_mcp_servers", new_callable=AsyncMock)
    async def test_map_tool_integration_with_weather(
        self, mock_connect, config_with_all_sprint3_tools: Path
    ):
        """测试地图工具与天气工具的协同"""
        from contextlib import AsyncExitStack

        from src.core.tools.mcp_connector import connect_mcp_tools_from_config

        mock_exit_stack = AsyncExitStack()
        mock_connect.return_value = {
            "weather": mock_exit_stack,
            "osm": mock_exit_stack,
            "coros": mock_exit_stack,
        }

        registry = MagicMock()
        result = await connect_mcp_tools_from_config(
            config_with_all_sprint3_tools, registry
        )

        assert len(result["connected_servers"]) == 3

    @pytest.mark.asyncio
    @patch("nanobot.agent.tools.mcp.connect_mcp_servers", new_callable=AsyncMock)
    async def test_health_tool_data_sync_capability(
        self, mock_connect, config_with_all_sprint3_tools: Path
    ):
        """测试健康数据工具的数据同步能力"""
        from contextlib import AsyncExitStack

        from src.core.tools.mcp_connector import connect_mcp_tools_from_config

        mock_exit_stack = AsyncExitStack()
        mock_connect.return_value = {
            "weather": mock_exit_stack,
            "osm": mock_exit_stack,
            "coros": mock_exit_stack,
        }

        registry = MagicMock()
        result = await connect_mcp_tools_from_config(
            config_with_all_sprint3_tools, registry
        )

        assert "coros" in result["connected_servers"]

    @pytest.mark.asyncio
    @patch("nanobot.agent.tools.mcp.connect_mcp_servers", new_callable=AsyncMock)
    async def test_partial_tool_failure_handling(self, mock_connect, tmp_path: Path):
        """测试部分工具连接失败的处理"""
        from contextlib import AsyncExitStack

        from src.core.tools.mcp_connector import connect_mcp_tools_from_config

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
                    "osm": {
                        "type": "stdio",
                        "command": "uvx",
                        "args": ["osm-mcp-server"],
                        "enabled_tools": ["*"],
                    },
                    "coros": {
                        "type": "stdio",
                        "command": "npx",
                        "args": ["-y", "coros-cli", "mcp"],
                        "enabled_tools": ["*"],
                    },
                }
            },
        }
        config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")

        mock_exit_stack = AsyncExitStack()
        mock_connect.return_value = {
            "weather": mock_exit_stack,
            "coros": mock_exit_stack,
        }

        registry = MagicMock()
        result = await connect_mcp_tools_from_config(config_path, registry)

        assert "weather" in result["connected_servers"]
        assert "coros" in result["connected_servers"]
        assert "osm" in result["failed_servers"]

    @pytest.mark.asyncio
    @patch("nanobot.agent.tools.mcp.connect_mcp_servers", new_callable=AsyncMock)
    async def test_tool_timeout_consistency(
        self, mock_connect, config_with_all_sprint3_tools: Path
    ):
        """测试所有工具超时配置一致性"""
        from contextlib import AsyncExitStack

        from src.core.tools.mcp_connector import connect_mcp_tools_from_config

        mock_exit_stack = AsyncExitStack()
        mock_connect.return_value = {
            "weather": mock_exit_stack,
            "osm": mock_exit_stack,
            "coros": mock_exit_stack,
        }

        registry = MagicMock()
        await connect_mcp_tools_from_config(config_with_all_sprint3_tools, registry)

        mock_connect.assert_called_once()
        call_args = mock_connect.call_args
        mcp_servers_dict = call_args[0][0]

        assert mcp_servers_dict["weather"].tool_timeout == 30
        assert mcp_servers_dict["osm"].tool_timeout == 30
        assert mcp_servers_dict["coros"].tool_timeout == 30

    @pytest.mark.asyncio
    @patch("nanobot.agent.tools.mcp.connect_mcp_servers", new_callable=AsyncMock)
    async def test_disabled_tools_not_connected(self, mock_connect, tmp_path: Path):
        """测试禁用的工具不会被连接"""
        from contextlib import AsyncExitStack

        from src.core.tools.mcp_connector import connect_mcp_tools_from_config

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
                    "osm": {
                        "type": "stdio",
                        "command": "uvx",
                        "args": ["osm-mcp-server"],
                        "disabled": True,
                        "enabled_tools": ["*"],
                    },
                    "coros": {
                        "type": "stdio",
                        "command": "npx",
                        "args": ["-y", "coros-cli", "mcp"],
                        "enabled_tools": ["*"],
                    },
                }
            },
        }
        config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")

        mock_exit_stack = AsyncExitStack()
        mock_connect.return_value = {
            "weather": mock_exit_stack,
            "coros": mock_exit_stack,
        }

        registry = MagicMock()
        result = await connect_mcp_tools_from_config(config_path, registry)

        assert "weather" in result["connected_servers"]
        assert "coros" in result["connected_servers"]
        assert "osm" not in result["connected_servers"]
        assert "osm" not in result["failed_servers"]
