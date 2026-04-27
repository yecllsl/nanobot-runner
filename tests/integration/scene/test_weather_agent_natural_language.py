# Agent自然语言调用天气工具的E2E测试
# 验证Agent能够通过自然语言调用天气MCP工具

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def config_with_weather_and_llm(tmp_path: Path) -> Path:
    """创建包含天气MCP服务器和LLM配置的config.json"""
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
                }
            }
        },
    }
    config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
    return config_path


@pytest.fixture
def mock_llm_response_for_weather():
    """模拟LLM对天气查询的响应"""
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": "call_123",
                "type": "function",
                "function": {
                    "name": "mcp_weather_get_weather",
                    "arguments": '{"location": "Beijing"}',
                },
            }
        ],
    }


@pytest.fixture
def mock_weather_tool_result():
    """模拟天气工具的返回结果"""
    return {
        "temperature": 25,
        "humidity": 60,
        "weather": "晴",
        "wind": "东南风3级",
        "location": "Beijing",
    }


class TestAgentNaturalLanguageWeatherQuery:
    """Agent自然语言查询天气的E2E测试"""

    @pytest.mark.asyncio
    @patch("nanobot.agent.tools.mcp.connect_mcp_servers", new_callable=AsyncMock)
    async def test_agent_calls_weather_tool_via_natural_language(
        self,
        mock_connect,
        config_with_weather_and_llm: Path,
        mock_llm_response_for_weather: dict,
        mock_weather_tool_result: dict,
    ):
        """测试Agent通过自然语言调用天气工具"""
        from contextlib import AsyncExitStack

        from src.core.tools.mcp_connector import connect_mcp_tools_from_config

        mock_exit_stack = AsyncExitStack()
        mock_connect.return_value = {"weather": mock_exit_stack}

        registry = MagicMock()
        result = await connect_mcp_tools_from_config(
            config_with_weather_and_llm, registry
        )

        assert "weather" in result["connected_servers"]
        assert result["failed_servers"] == []

    @pytest.mark.asyncio
    @patch("nanobot.agent.tools.mcp.connect_mcp_servers", new_callable=AsyncMock)
    async def test_weather_tool_naming_convention_in_tool_calls(
        self, mock_connect, config_with_weather_and_llm: Path
    ):
        """测试天气工具在工具调用中的命名规范"""
        from contextlib import AsyncExitStack

        from src.core.tools.mcp_connector import connect_mcp_tools_from_config

        mock_exit_stack = AsyncExitStack()
        mock_connect.return_value = {"weather": mock_exit_stack}

        registry = MagicMock()
        await connect_mcp_tools_from_config(config_with_weather_and_llm, registry)

        mock_connect.assert_called_once()
        call_args = mock_connect.call_args
        mcp_servers_dict = call_args[0][0]
        assert "weather" in mcp_servers_dict

    @pytest.mark.asyncio
    @patch("nanobot.agent.tools.mcp.connect_mcp_servers", new_callable=AsyncMock)
    async def test_agent_handles_weather_tool_error_gracefully(
        self, mock_connect, config_with_weather_and_llm: Path
    ):
        """测试Agent优雅处理天气工具错误"""
        from src.core.tools.mcp_connector import connect_mcp_tools_from_config

        mock_connect.side_effect = Exception("Weather service unavailable")

        registry = MagicMock()
        result = await connect_mcp_tools_from_config(
            config_with_weather_and_llm, registry
        )

        assert result["connected_servers"] == []
        assert "weather" in result["failed_servers"]

    @pytest.mark.asyncio
    @patch("nanobot.agent.tools.mcp.connect_mcp_servers", new_callable=AsyncMock)
    async def test_agent_weather_query_with_location_parameter(
        self, mock_connect, config_with_weather_and_llm: Path
    ):
        """测试Agent查询天气时传递位置参数"""
        from contextlib import AsyncExitStack

        from src.core.tools.mcp_connector import connect_mcp_tools_from_config

        mock_exit_stack = AsyncExitStack()
        mock_connect.return_value = {"weather": mock_exit_stack}

        registry = MagicMock()
        await connect_mcp_tools_from_config(config_with_weather_and_llm, registry)

        mock_connect.assert_called_once()

    @pytest.mark.asyncio
    @patch("nanobot.agent.tools.mcp.connect_mcp_servers", new_callable=AsyncMock)
    async def test_multiple_weather_queries_in_session(
        self, mock_connect, config_with_weather_and_llm: Path
    ):
        """测试同一会话中多次查询天气"""
        from contextlib import AsyncExitStack

        from src.core.tools.mcp_connector import connect_mcp_tools_from_config

        mock_exit_stack = AsyncExitStack()
        mock_connect.return_value = {"weather": mock_exit_stack}

        registry = MagicMock()
        result = await connect_mcp_tools_from_config(
            config_with_weather_and_llm, registry
        )

        assert "weather" in result["connected_servers"]
        assert "weather" in result["exit_stacks"]

    @pytest.mark.asyncio
    @patch("nanobot.agent.tools.mcp.connect_mcp_servers", new_callable=AsyncMock)
    async def test_weather_tool_timeout_handling(self, mock_connect, tmp_path: Path):
        """测试天气工具超时处理"""
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
                        "tool_timeout": 5,
                        "enabled_tools": ["*"],
                    }
                }
            },
        }
        config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")

        mock_exit_stack = AsyncExitStack()
        mock_connect.return_value = {"weather": mock_exit_stack}

        registry = MagicMock()
        await connect_mcp_tools_from_config(config_path, registry)

        mock_connect.assert_called_once()
        call_args = mock_connect.call_args
        mcp_servers_dict = call_args[0][0]
        assert mcp_servers_dict["weather"].tool_timeout == 5

    @pytest.mark.asyncio
    @patch("nanobot.agent.tools.mcp.connect_mcp_servers", new_callable=AsyncMock)
    async def test_weather_tool_with_enabled_tools_filter(
        self, mock_connect, tmp_path: Path
    ):
        """测试天气工具启用特定工具过滤"""
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
                        "enabled_tools": ["get_weather", "get_forecast"],
                    }
                }
            },
        }
        config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")

        mock_exit_stack = AsyncExitStack()
        mock_connect.return_value = {"weather": mock_exit_stack}

        registry = MagicMock()
        await connect_mcp_tools_from_config(config_path, registry)

        mock_connect.assert_called_once()
        call_args = mock_connect.call_args
        mcp_servers_dict = call_args[0][0]
        assert mcp_servers_dict["weather"].enabled_tools == [
            "get_weather",
            "get_forecast",
        ]
