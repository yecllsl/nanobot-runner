# 健康Agent工具集成测试
# 验证Agent能够通过自然语言调用健康数据工具

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def config_with_health_tools(tmp_path: Path) -> Path:
    """创建包含健康数据工具配置的config.json"""
    config_path = tmp_path / "config.json"
    config = {
        "version": "0.13.0",
        "data_dir": str(tmp_path / "data"),
        "timezone": "Asia/Shanghai",
        "llm_provider": "openai",
        "llm_model": "gpt-4o-mini",
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


class TestHealthAgentToolIntegration:
    """健康Agent工具集成测试"""

    @pytest.mark.asyncio
    async def test_health_tool_config_loaded(self, config_with_health_tools: Path):
        """测试健康工具配置正确加载"""
        from src.core.tools.mcp_config_helper import MCPConfigHelper

        helper = MCPConfigHelper(config_with_health_tools)
        tools_config = helper.load_tools_config()

        assert tools_config.mcp_servers is not None
        assert "coros" in tools_config.mcp_servers

    @pytest.mark.asyncio
    @patch("nanobot.agent.tools.mcp.connect_mcp_servers", new_callable=AsyncMock)
    async def test_health_tool_connected(
        self, mock_connect, config_with_health_tools: Path
    ):
        """测试健康工具成功连接"""
        from contextlib import AsyncExitStack

        from src.core.tools.mcp_connector import connect_mcp_tools_from_config

        mock_exit_stack = AsyncExitStack()
        mock_connect.return_value = {"coros": mock_exit_stack}

        registry = MagicMock()
        result = await connect_mcp_tools_from_config(config_with_health_tools, registry)

        assert "coros" in result["connected_servers"]
        assert result["failed_servers"] == []

    @pytest.mark.asyncio
    @patch("nanobot.agent.tools.mcp.connect_mcp_servers", new_callable=AsyncMock)
    async def test_health_tool_naming_convention(
        self, mock_connect, config_with_health_tools: Path
    ):
        """测试健康工具命名规范（mcp_coros_*）"""
        from contextlib import AsyncExitStack

        from src.core.tools.mcp_connector import connect_mcp_tools_from_config

        mock_exit_stack = AsyncExitStack()
        mock_connect.return_value = {"coros": mock_exit_stack}

        registry = MagicMock()
        await connect_mcp_tools_from_config(config_with_health_tools, registry)

        mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_tool_connection_failure_handling(
        self, config_with_health_tools: Path
    ):
        """测试健康工具连接失败的优雅降级"""
        with patch("nanobot.agent.tools.mcp.connect_mcp_servers") as mock_connect:
            mock_connect.side_effect = Exception("Connection failed")

            from src.core.tools.mcp_connector import connect_mcp_tools_from_config

            registry = MagicMock()
            result = await connect_mcp_tools_from_config(
                config_with_health_tools, registry
            )

            assert result["connected_servers"] == []
            assert "coros" in result["failed_servers"]

    @pytest.mark.asyncio
    @patch("nanobot.agent.tools.mcp.connect_mcp_servers", new_callable=AsyncMock)
    async def test_health_tool_with_llm_config(
        self, mock_connect, config_with_health_tools: Path
    ):
        """测试健康工具与LLM配置协同"""
        from contextlib import AsyncExitStack

        from src.core.tools.mcp_connector import connect_mcp_tools_from_config

        mock_exit_stack = AsyncExitStack()
        mock_connect.return_value = {"coros": mock_exit_stack}

        registry = MagicMock()
        result = await connect_mcp_tools_from_config(config_with_health_tools, registry)

        assert "coros" in result["connected_servers"]

    @pytest.mark.asyncio
    async def test_health_tool_disabled_server_skipped(self, tmp_path: Path):
        """测试禁用的健康工具服务器被跳过"""
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

        from src.core.tools.mcp_connector import connect_mcp_tools_from_config

        registry = MagicMock()
        result = await connect_mcp_tools_from_config(config_path, registry)

        assert result["connected_servers"] == []
        assert result["failed_servers"] == []

    @pytest.mark.asyncio
    @patch("nanobot.agent.tools.mcp.connect_mcp_servers", new_callable=AsyncMock)
    async def test_health_tool_timeout_configuration(
        self, mock_connect, tmp_path: Path
    ):
        """测试健康工具超时配置正确传递"""
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

        from src.core.tools.mcp_connector import connect_mcp_tools_from_config

        mock_exit_stack = AsyncExitStack()
        mock_connect.return_value = {"coros": mock_exit_stack}

        registry = MagicMock()
        await connect_mcp_tools_from_config(config_path, registry)

        mock_connect.assert_called_once()
        call_args = mock_connect.call_args
        mcp_servers_dict = call_args[0][0]
        assert mcp_servers_dict["coros"].tool_timeout == 60
