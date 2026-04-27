# 工具管理器单元测试
# 测试ToolManager的工具列表、状态查询、启用/禁用、发现等功能

import json
from pathlib import Path

import pytest

from src.core.tools.models import (
    MCPServerConfig,
    MCPTransportType,
    ToolStatus,
    ToolType,
)
from src.core.tools.tool_manager import ToolManager


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def config_path(config_dir: Path) -> Path:
    return config_dir / "config.json"


@pytest.fixture
def manager(config_path: Path) -> ToolManager:
    return ToolManager(config_path)


@pytest.fixture
def config_with_servers(config_path: Path) -> Path:
    """创建包含多个服务器的配置文件"""
    config = {
        "version": "0.13.0",
        "data_dir": "/data",
        "tools": {
            "mcp_servers": {
                "weather": {
                    "type": "stdio",
                    "command": "python",
                    "args": ["-m", "weather"],
                    "enabled_tools": ["*"],
                },
                "map": {
                    "type": "stdio",
                    "command": "python",
                    "args": ["-m", "map"],
                    "enabled_tools": ["plan_route", "analyze_route"],
                },
                "disabled-svc": {
                    "type": "stdio",
                    "command": "python",
                    "disabled": True,
                },
                "remote": {
                    "type": "sse",
                    "url": "https://example.com/sse",
                },
            }
        },
    }
    config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
    return config_path


class TestToolManagerListTools:
    """测试列出工具"""

    def test_list_tools_empty(self, manager: ToolManager) -> None:
        tools = manager.list_tools()
        assert len(tools) == 0

    def test_list_tools_with_wildcard_server(
        self, config_with_servers: Path, manager: ToolManager
    ) -> None:
        tools = manager.list_tools()
        weather_tools = [t for t in tools if t.mcp_server_name == "weather"]
        assert len(weather_tools) == 1
        assert weather_tools[0].id == "mcp_weather_*"
        assert weather_tools[0].status == ToolStatus.ENABLED

    def test_list_tools_with_specific_tools(
        self, config_with_servers: Path, manager: ToolManager
    ) -> None:
        tools = manager.list_tools()
        map_tools = [t for t in tools if t.mcp_server_name == "map"]
        assert len(map_tools) == 2
        tool_ids = {t.id for t in map_tools}
        assert "mcp_map_plan_route" in tool_ids
        assert "mcp_map_analyze_route" in tool_ids

    def test_list_tools_disabled_server(
        self, config_with_servers: Path, manager: ToolManager
    ) -> None:
        tools = manager.list_tools()
        disabled_tools = [t for t in tools if t.mcp_server_name == "disabled-svc"]
        assert len(disabled_tools) == 1
        assert disabled_tools[0].status == ToolStatus.DISABLED

    def test_list_tools_cloud_type(
        self, config_with_servers: Path, manager: ToolManager
    ) -> None:
        tools = manager.list_tools()
        remote_tools = [t for t in tools if t.mcp_server_name == "remote"]
        assert len(remote_tools) == 1
        assert remote_tools[0].tool_type == ToolType.CLOUD

    def test_list_tools_local_type(
        self, config_with_servers: Path, manager: ToolManager
    ) -> None:
        tools = manager.list_tools()
        weather_tools = [t for t in tools if t.mcp_server_name == "weather"]
        assert weather_tools[0].tool_type == ToolType.LOCAL


class TestToolManagerGetStatus:
    """测试获取工具状态"""

    def test_get_status_enabled_wildcard(
        self, config_with_servers: Path, manager: ToolManager
    ) -> None:
        status = manager.get_tool_status("mcp_weather_get_weather")
        assert status == ToolStatus.ENABLED

    def test_get_status_enabled_specific(
        self, config_with_servers: Path, manager: ToolManager
    ) -> None:
        status = manager.get_tool_status("mcp_map_plan_route")
        assert status == ToolStatus.ENABLED

    def test_get_status_disabled_server(
        self, config_with_servers: Path, manager: ToolManager
    ) -> None:
        status = manager.get_tool_status("mcp_disabled-svc_some_tool")
        assert status == ToolStatus.DISABLED

    def test_get_status_nonexistent_server(
        self, config_with_servers: Path, manager: ToolManager
    ) -> None:
        status = manager.get_tool_status("mcp_nonexistent_tool")
        assert status == ToolStatus.DISABLED

    def test_get_status_invalid_format(self, manager: ToolManager) -> None:
        status = manager.get_tool_status("invalid_format")
        assert status == ToolStatus.DISABLED

    def test_get_status_specific_tool_not_in_enabled_list(
        self, config_with_servers: Path, manager: ToolManager
    ) -> None:
        status = manager.get_tool_status("mcp_map_unknown_tool")
        assert status == ToolStatus.DISABLED


class TestToolManagerEnableTool:
    """测试启用工具"""

    def test_enable_tool_in_wildcard_server(
        self, config_with_servers: Path, manager: ToolManager
    ) -> None:
        result = manager.enable_tool("mcp_weather_get_weather")
        assert result is True

    def test_enable_tool_adds_to_enabled_list(
        self, config_path: Path, manager: ToolManager
    ) -> None:
        config = {
            "tools": {
                "mcp_servers": {
                    "weather": {
                        "type": "stdio",
                        "command": "python",
                        "enabled_tools": ["get_weather"],
                    }
                }
            }
        }
        config_path.write_text(json.dumps(config), encoding="utf-8")

        result = manager.enable_tool("mcp_weather_get_forecast")
        assert result is True

        status = manager.get_tool_status("mcp_weather_get_forecast")
        assert status == ToolStatus.ENABLED

    def test_enable_tool_also_enables_disabled_server(
        self, config_path: Path, manager: ToolManager
    ) -> None:
        config = {
            "tools": {
                "mcp_servers": {
                    "weather": {
                        "type": "stdio",
                        "command": "python",
                        "disabled": True,
                    }
                }
            }
        }
        config_path.write_text(json.dumps(config), encoding="utf-8")

        result = manager.enable_tool("mcp_weather_get_weather")
        assert result is True

        status = manager.get_tool_status("mcp_weather_get_weather")
        assert status == ToolStatus.ENABLED

    def test_enable_tool_invalid_name(self, manager: ToolManager) -> None:
        result = manager.enable_tool("invalid")
        assert result is False

    def test_enable_tool_nonexistent_server(
        self, config_with_servers: Path, manager: ToolManager
    ) -> None:
        result = manager.enable_tool("mcp_nonexistent_tool")
        assert result is False


class TestToolManagerDisableTool:
    """测试禁用工具"""

    def test_disable_specific_tool(
        self, config_path: Path, manager: ToolManager
    ) -> None:
        config = {
            "tools": {
                "mcp_servers": {
                    "weather": {
                        "type": "stdio",
                        "command": "python",
                        "enabled_tools": ["get_weather", "get_forecast"],
                    }
                }
            }
        }
        config_path.write_text(json.dumps(config), encoding="utf-8")

        result = manager.disable_tool("mcp_weather_get_forecast")
        assert result is True

        status = manager.get_tool_status("mcp_weather_get_forecast")
        assert status == ToolStatus.DISABLED

        status = manager.get_tool_status("mcp_weather_get_weather")
        assert status == ToolStatus.ENABLED

    def test_disable_last_tool_disables_server(
        self, config_path: Path, manager: ToolManager
    ) -> None:
        config = {
            "tools": {
                "mcp_servers": {
                    "weather": {
                        "type": "stdio",
                        "command": "python",
                        "enabled_tools": ["get_weather"],
                    }
                }
            }
        }
        config_path.write_text(json.dumps(config), encoding="utf-8")

        result = manager.disable_tool("mcp_weather_get_weather")
        assert result is True

        server_config = manager.get_server_config("weather")
        assert server_config is not None
        assert server_config.disabled is True

    def test_disable_wildcard_server(
        self, config_with_servers: Path, manager: ToolManager
    ) -> None:
        result = manager.disable_tool("mcp_weather_*")
        assert result is True

        server_config = manager.get_server_config("weather")
        assert server_config is not None
        assert server_config.disabled is True

    def test_disable_tool_invalid_name(self, manager: ToolManager) -> None:
        result = manager.disable_tool("invalid")
        assert result is False


class TestToolManagerDiscoverTools:
    """测试发现工具"""

    def test_discover_only_enabled(
        self, config_with_servers: Path, manager: ToolManager
    ) -> None:
        discovered = manager.discover_tools()
        for tool in discovered:
            assert tool.status == ToolStatus.ENABLED

    def test_discover_excludes_disabled(
        self, config_with_servers: Path, manager: ToolManager
    ) -> None:
        all_tools = manager.list_tools()
        discovered = manager.discover_tools()
        assert len(discovered) < len(all_tools)

    def test_discover_empty(self, manager: ToolManager) -> None:
        discovered = manager.discover_tools()
        assert len(discovered) == 0


class TestToolManagerServerManagement:
    """测试服务器管理"""

    def test_list_servers(
        self, config_with_servers: Path, manager: ToolManager
    ) -> None:
        servers = manager.list_servers()
        assert "weather" in servers
        assert "map" in servers
        assert "disabled-svc" in servers
        assert "remote" in servers

    def test_get_server_config(
        self, config_with_servers: Path, manager: ToolManager
    ) -> None:
        config = manager.get_server_config("weather")
        assert config is not None
        assert config.command == "python"

    def test_get_nonexistent_server_config(self, manager: ToolManager) -> None:
        config = manager.get_server_config("nonexistent")
        assert config is None

    def test_add_server(self, config_path: Path, manager: ToolManager) -> None:
        server = MCPServerConfig(
            name="new-service",
            transport_type=MCPTransportType.STDIO,
            command="python",
            args=["-m", "new_service"],
        )
        result = manager.add_server(server)
        assert result is True
        assert "new-service" in manager.list_servers()

    def test_remove_server(
        self, config_with_servers: Path, manager: ToolManager
    ) -> None:
        result = manager.remove_server("weather")
        assert result is True
        assert "weather" not in manager.list_servers()

    def test_enable_server(
        self, config_with_servers: Path, manager: ToolManager
    ) -> None:
        result = manager.enable_server("disabled-svc")
        assert result is True

        config = manager.get_server_config("disabled-svc")
        assert config is not None
        assert config.disabled is False

    def test_disable_server(
        self, config_with_servers: Path, manager: ToolManager
    ) -> None:
        result = manager.disable_server("weather")
        assert result is True

        config = manager.get_server_config("weather")
        assert config is not None
        assert config.disabled is True


class TestToolManagerValidateConfig:
    """测试配置验证"""

    def test_validate_valid_config(
        self, config_with_servers: Path, manager: ToolManager
    ) -> None:
        errors = manager.validate_config()
        assert len(errors) == 0

    def test_validate_invalid_config(
        self, config_path: Path, manager: ToolManager
    ) -> None:
        config = {
            "tools": {
                "mcp_servers": {
                    "bad": {"type": "stdio"},
                }
            }
        }
        config_path.write_text(json.dumps(config), encoding="utf-8")
        errors = manager.validate_config()
        assert len(errors) > 0


class TestToolManagerExtractNames:
    """测试工具名称解析"""

    def test_extract_server_name_wildcard(
        self, config_with_servers: Path, manager: ToolManager
    ) -> None:
        assert manager._extract_server_name("mcp_weather_*") == "weather"

    def test_extract_server_name_with_known_servers(
        self, config_with_servers: Path, manager: ToolManager
    ) -> None:
        assert manager._extract_server_name("mcp_weather_get_weather") == "weather"
        assert manager._extract_server_name("mcp_map_plan_route") == "map"

    def test_extract_server_name_invalid(self, manager: ToolManager) -> None:
        assert manager._extract_server_name("invalid") is None
        assert manager._extract_server_name("mcp_") is None

    def test_extract_specific_tool(self) -> None:
        assert (
            ToolManager._extract_specific_tool("mcp_weather_get_weather", "weather")
            == "get_weather"
        )
        assert ToolManager._extract_specific_tool("mcp_weather_*", "weather") is None

    def test_extract_specific_tool_no_match(self) -> None:
        assert ToolManager._extract_specific_tool("no_underscore", "weather") is None
