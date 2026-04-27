# MCP配置辅助模块单元测试
# 测试MCPConfigHelper的配置加载、保存、验证、导入功能

import json
from pathlib import Path

import pytest

from src.core.tools.mcp_config_helper import MCPConfigHelper
from src.core.tools.models import (
    MCPServerConfig,
    MCPTransportType,
    ToolsConfig,
)


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    """创建临时配置目录"""
    return tmp_path


@pytest.fixture
def config_path(config_dir: Path) -> Path:
    """创建临时config.json路径"""
    return config_dir / "config.json"


@pytest.fixture
def helper(config_path: Path) -> MCPConfigHelper:
    """创建MCPConfigHelper实例"""
    return MCPConfigHelper(config_path)


@pytest.fixture
def config_with_stdio_server(config_path: Path) -> Path:
    """创建包含stdio服务器的配置文件"""
    config = {
        "version": "0.13.0",
        "data_dir": "/data",
        "tools": {
            "mcp_servers": {
                "runflow-tools": {
                    "type": "stdio",
                    "command": "python",
                    "args": ["-m", "runflow_mcp_server"],
                    "tool_timeout": 30,
                    "enabled_tools": ["*"],
                }
            }
        },
    }
    config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
    return config_path


@pytest.fixture
def config_with_multiple_servers(config_path: Path) -> Path:
    """创建包含多个服务器的配置文件"""
    config = {
        "version": "0.13.0",
        "data_dir": "/data",
        "tools": {
            "mcp_servers": {
                "local-tools": {
                    "type": "stdio",
                    "command": "python",
                    "args": ["-m", "local_server"],
                },
                "remote-tools": {
                    "type": "sse",
                    "url": "https://example.com/sse",
                },
                "disabled-tools": {
                    "type": "stdio",
                    "command": "node",
                    "args": ["server.js"],
                    "disabled": True,
                },
            }
        },
    }
    config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
    return config_path


class TestMCPConfigHelperLoad:
    """测试配置加载"""

    def test_load_nonexistent_file(self, helper: MCPConfigHelper) -> None:
        result = helper.load_tools_config()
        assert len(result.mcp_servers) == 0

    def test_load_empty_config(
        self, config_path: Path, helper: MCPConfigHelper
    ) -> None:
        config_path.write_text("{}", encoding="utf-8")
        result = helper.load_tools_config()
        assert len(result.mcp_servers) == 0

    def test_load_config_without_tools(
        self, config_path: Path, helper: MCPConfigHelper
    ) -> None:
        config = {"version": "0.13.0", "data_dir": "/data"}
        config_path.write_text(json.dumps(config), encoding="utf-8")
        result = helper.load_tools_config()
        assert len(result.mcp_servers) == 0

    def test_load_config_with_stdio_server(
        self, config_with_stdio_server: Path, helper: MCPConfigHelper
    ) -> None:
        result = helper.load_tools_config()
        assert "runflow-tools" in result.mcp_servers
        server = result.mcp_servers["runflow-tools"]
        assert server.transport_type == MCPTransportType.STDIO
        assert server.command == "python"
        assert server.args == ["-m", "runflow_mcp_server"]

    def test_load_config_with_multiple_servers(
        self, config_with_multiple_servers: Path, helper: MCPConfigHelper
    ) -> None:
        result = helper.load_tools_config()
        assert len(result.mcp_servers) == 3
        assert "local-tools" in result.mcp_servers
        assert "remote-tools" in result.mcp_servers
        assert "disabled-tools" in result.mcp_servers

    def test_load_invalid_json(
        self, config_path: Path, helper: MCPConfigHelper
    ) -> None:
        config_path.write_text("not json", encoding="utf-8")
        result = helper.load_tools_config()
        assert len(result.mcp_servers) == 0

    def test_load_invalid_tools_type(
        self, config_path: Path, helper: MCPConfigHelper
    ) -> None:
        config = {"tools": "not a dict"}
        config_path.write_text(json.dumps(config), encoding="utf-8")
        result = helper.load_tools_config()
        assert len(result.mcp_servers) == 0


class TestMCPConfigHelperSave:
    """测试配置保存"""

    def test_save_to_new_file(self, config_path: Path, helper: MCPConfigHelper) -> None:
        server = MCPServerConfig(
            name="weather",
            transport_type=MCPTransportType.STDIO,
            command="python",
            args=["-m", "weather"],
        )
        tools_config = ToolsConfig(mcp_servers={"weather": server})
        result = helper.save_tools_config(tools_config)
        assert result is True

        saved = json.loads(config_path.read_text(encoding="utf-8"))
        assert "tools" in saved
        assert "weather" in saved["tools"]["mcp_servers"]

    def test_save_preserves_other_fields(
        self, config_path: Path, helper: MCPConfigHelper
    ) -> None:
        existing_config = {"version": "0.13.0", "data_dir": "/data", "custom": "value"}
        config_path.write_text(json.dumps(existing_config), encoding="utf-8")

        tools_config = ToolsConfig()
        helper.save_tools_config(tools_config)

        saved = json.loads(config_path.read_text(encoding="utf-8"))
        assert saved["version"] == "0.13.0"
        assert saved["data_dir"] == "/data"
        assert saved["custom"] == "value"
        assert "tools" in saved

    def test_save_overwrites_tools(
        self, config_with_stdio_server: Path, helper: MCPConfigHelper
    ) -> None:
        new_server = MCPServerConfig(
            name="new-server",
            transport_type=MCPTransportType.SSE,
            url="https://new.example.com/sse",
        )
        tools_config = ToolsConfig(mcp_servers={"new-server": new_server})
        helper.save_tools_config(tools_config)

        saved = json.loads(config_with_stdio_server.read_text(encoding="utf-8"))
        assert "new-server" in saved["tools"]["mcp_servers"]
        assert "runflow-tools" not in saved["tools"]["mcp_servers"]


class TestMCPConfigHelperValidate:
    """测试配置验证"""

    def test_validate_valid_stdio_config(
        self, config_with_stdio_server: Path, helper: MCPConfigHelper
    ) -> None:
        errors = helper.validate_mcp_config()
        assert len(errors) == 0

    def test_validate_missing_command(
        self, config_path: Path, helper: MCPConfigHelper
    ) -> None:
        config = {
            "tools": {
                "mcp_servers": {
                    "bad-server": {"type": "stdio"},
                }
            }
        }
        config_path.write_text(json.dumps(config), encoding="utf-8")
        errors = helper.validate_mcp_config()
        assert any("stdio协议必须配置command字段" in e for e in errors)

    def test_validate_missing_url_sse(
        self, config_path: Path, helper: MCPConfigHelper
    ) -> None:
        config = {
            "tools": {
                "mcp_servers": {
                    "bad-sse": {"type": "sse"},
                }
            }
        }
        config_path.write_text(json.dumps(config), encoding="utf-8")
        errors = helper.validate_mcp_config()
        assert any("sse协议必须配置url字段" in e for e in errors)

    def test_validate_missing_url_streamable_http(
        self, config_path: Path, helper: MCPConfigHelper
    ) -> None:
        config = {
            "tools": {
                "mcp_servers": {
                    "bad-http": {"type": "streamableHttp"},
                }
            }
        }
        config_path.write_text(json.dumps(config), encoding="utf-8")
        errors = helper.validate_mcp_config()
        assert any("streamableHttp协议必须配置url字段" in e for e in errors)

    def test_validate_invalid_timeout(
        self, config_path: Path, helper: MCPConfigHelper
    ) -> None:
        config = {
            "tools": {
                "mcp_servers": {
                    "bad-timeout": {
                        "type": "stdio",
                        "command": "python",
                        "tool_timeout": -1,
                    },
                }
            }
        }
        config_path.write_text(json.dumps(config), encoding="utf-8")
        errors = helper.validate_mcp_config()
        assert any("tool_timeout必须为正整数" in e for e in errors)

    def test_validate_empty_file(self, helper: MCPConfigHelper) -> None:
        errors = helper.validate_mcp_config()
        assert len(errors) == 0


class TestMCPConfigHelperListTools:
    """测试列出MCP工具"""

    def test_list_tools_wildcard(
        self, config_with_stdio_server: Path, helper: MCPConfigHelper
    ) -> None:
        tools = helper.list_mcp_tools()
        assert "mcp_runflow-tools_*" in tools

    def test_list_tools_specific(
        self, config_path: Path, helper: MCPConfigHelper
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
        tools = helper.list_mcp_tools()
        assert "mcp_weather_get_weather" in tools
        assert "mcp_weather_get_forecast" in tools

    def test_list_tools_excludes_disabled(
        self, config_path: Path, helper: MCPConfigHelper
    ) -> None:
        config = {
            "tools": {
                "mcp_servers": {
                    "disabled-server": {
                        "type": "stdio",
                        "command": "python",
                        "disabled": True,
                    }
                }
            }
        }
        config_path.write_text(json.dumps(config), encoding="utf-8")
        tools = helper.list_mcp_tools()
        assert len(tools) == 0

    def test_list_tools_empty_config(self, helper: MCPConfigHelper) -> None:
        tools = helper.list_mcp_tools()
        assert len(tools) == 0


class TestMCPConfigHelperImport:
    """测试Claude Desktop配置导入"""

    def test_import_valid_config(
        self, config_path: Path, helper: MCPConfigHelper, config_dir: Path
    ) -> None:
        claude_config = {
            "mcpServers": {
                "filesystem": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                }
            }
        }
        claude_path = config_dir / "claude_config.json"
        claude_path.write_text(json.dumps(claude_config), encoding="utf-8")

        result = helper.import_claude_desktop_config(claude_path)
        assert result is True

        tools_config = helper.load_tools_config()
        assert "filesystem" in tools_config.mcp_servers
        server = tools_config.mcp_servers["filesystem"]
        assert server.transport_type == MCPTransportType.STDIO
        assert server.command == "npx"

    def test_import_nonexistent_file(self, helper: MCPConfigHelper) -> None:
        result = helper.import_claude_desktop_config(Path("/nonexistent"))
        assert result is False

    def test_import_empty_servers(
        self, config_path: Path, helper: MCPConfigHelper, config_dir: Path
    ) -> None:
        claude_config = {"mcpServers": {}}
        claude_path = config_dir / "claude_config.json"
        claude_path.write_text(json.dumps(claude_config), encoding="utf-8")

        result = helper.import_claude_desktop_config(claude_path)
        assert result is True

    def test_import_merges_with_existing(
        self, config_with_stdio_server: Path, helper: MCPConfigHelper, config_dir: Path
    ) -> None:
        claude_config = {
            "mcpServers": {
                "new-server": {
                    "command": "node",
                    "args": ["server.js"],
                }
            }
        }
        claude_path = config_dir / "claude_config.json"
        claude_path.write_text(json.dumps(claude_config), encoding="utf-8")

        helper.import_claude_desktop_config(claude_path)

        tools_config = helper.load_tools_config()
        assert "runflow-tools" in tools_config.mcp_servers
        assert "new-server" in tools_config.mcp_servers

    def test_import_url_based_server(
        self, config_path: Path, helper: MCPConfigHelper, config_dir: Path
    ) -> None:
        claude_config = {
            "mcpServers": {
                "remote": {
                    "url": "https://example.com/sse",
                }
            }
        }
        claude_path = config_dir / "claude_config.json"
        claude_path.write_text(json.dumps(claude_config), encoding="utf-8")

        helper.import_claude_desktop_config(claude_path)

        tools_config = helper.load_tools_config()
        assert "remote" in tools_config.mcp_servers
        assert tools_config.mcp_servers["remote"].transport_type == MCPTransportType.SSE

    def test_import_http_url_server(
        self, config_path: Path, helper: MCPConfigHelper, config_dir: Path
    ) -> None:
        claude_config = {
            "mcpServers": {
                "http-remote": {
                    "url": "https://example.com/api/mcp",
                }
            }
        }
        claude_path = config_dir / "claude_config.json"
        claude_path.write_text(json.dumps(claude_config), encoding="utf-8")

        helper.import_claude_desktop_config(claude_path)

        tools_config = helper.load_tools_config()
        assert "http-remote" in tools_config.mcp_servers
        assert (
            tools_config.mcp_servers["http-remote"].transport_type
            == MCPTransportType.STREAMABLE_HTTP
        )


class TestMCPConfigHelperAddRemoveUpdate:
    """测试添加、移除、更新服务器配置"""

    def test_add_server(self, config_path: Path, helper: MCPConfigHelper) -> None:
        server = MCPServerConfig(
            name="weather",
            transport_type=MCPTransportType.STDIO,
            command="python",
            args=["-m", "weather"],
        )
        result = helper.add_mcp_server(server)
        assert result is True

        tools_config = helper.load_tools_config()
        assert "weather" in tools_config.mcp_servers

    def test_remove_server(
        self, config_with_stdio_server: Path, helper: MCPConfigHelper
    ) -> None:
        result = helper.remove_mcp_server("runflow-tools")
        assert result is True

        tools_config = helper.load_tools_config()
        assert "runflow-tools" not in tools_config.mcp_servers

    def test_remove_nonexistent_server(self, helper: MCPConfigHelper) -> None:
        result = helper.remove_mcp_server("nonexistent")
        assert result is True

    def test_update_server(
        self, config_with_stdio_server: Path, helper: MCPConfigHelper
    ) -> None:
        result = helper.update_mcp_server("runflow-tools", tool_timeout=60)
        assert result is True

        tools_config = helper.load_tools_config()
        assert tools_config.mcp_servers["runflow-tools"].tool_timeout == 60

    def test_update_nonexistent_server(self, helper: MCPConfigHelper) -> None:
        result = helper.update_mcp_server("nonexistent", tool_timeout=60)
        assert result is False
