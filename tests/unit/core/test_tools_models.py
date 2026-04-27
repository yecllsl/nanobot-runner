# 工具生态数据模型单元测试
# 测试ToolInfo/ToolStatus/ToolType/MCPServerConfig/ToolsConfig等数据模型

import pytest

from src.core.tools.models import (
    MCPServerConfig,
    MCPTransportType,
    ToolInfo,
    ToolResult,
    ToolsConfig,
    ToolStatus,
    ToolType,
)


class TestToolType:
    """测试ToolType枚举"""

    def test_enum_values(self):
        assert ToolType.LOCAL.value == "local"
        assert ToolType.CLOUD.value == "cloud"
        assert ToolType.HYBRID.value == "hybrid"

    def test_from_value(self):
        assert ToolType("local") == ToolType.LOCAL
        assert ToolType("cloud") == ToolType.CLOUD

    def test_invalid_value(self):
        with pytest.raises(ValueError):
            ToolType("invalid")


class TestToolStatus:
    """测试ToolStatus枚举"""

    def test_enum_values(self):
        assert ToolStatus.ENABLED.value == "enabled"
        assert ToolStatus.DISABLED.value == "disabled"
        assert ToolStatus.ERROR.value == "error"
        assert ToolStatus.INSTALLING.value == "installing"


class TestMCPTransportType:
    """测试MCPTransportType枚举"""

    def test_enum_values(self):
        assert MCPTransportType.STDIO.value == "stdio"
        assert MCPTransportType.SSE.value == "sse"
        assert MCPTransportType.STREAMABLE_HTTP.value == "streamableHttp"

    def test_invalid_value(self):
        with pytest.raises(ValueError):
            MCPTransportType("invalid")


class TestToolInfo:
    """测试ToolInfo不可变数据类"""

    def test_create_minimal(self):
        info = ToolInfo(
            id="mcp_weather_get_weather",
            name="get_weather",
            description="获取天气数据",
            tool_type=ToolType.CLOUD,
            status=ToolStatus.ENABLED,
        )
        assert info.id == "mcp_weather_get_weather"
        assert info.name == "get_weather"
        assert info.tool_type == ToolType.CLOUD
        assert info.status == ToolStatus.ENABLED
        assert info.version == "0.1.0"
        assert info.author == ""
        assert info.homepage is None
        assert info.config_schema is None
        assert info.privacy_policy is None
        assert info.mcp_server_name is None

    def test_create_full(self):
        info = ToolInfo(
            id="mcp_weather_get_weather",
            name="get_weather",
            description="获取天气数据",
            tool_type=ToolType.CLOUD,
            status=ToolStatus.ENABLED,
            version="1.0.0",
            author="test",
            homepage="https://example.com",
            config_schema={"type": "object"},
            privacy_policy="No data collection",
            mcp_server_name="weather",
        )
        assert info.version == "1.0.0"
        assert info.author == "test"
        assert info.homepage == "https://example.com"
        assert info.mcp_server_name == "weather"

    def test_frozen(self):
        info = ToolInfo(
            id="test",
            name="test",
            description="test",
            tool_type=ToolType.LOCAL,
            status=ToolStatus.ENABLED,
        )
        with pytest.raises(AttributeError):
            info.name = "changed"


class TestMCPServerConfig:
    """测试MCPServerConfig不可变数据类"""

    def test_create_stdio_server(self):
        config = MCPServerConfig(
            name="runflow-tools",
            transport_type=MCPTransportType.STDIO,
            command="python",
            args=["-m", "runflow_mcp_server"],
        )
        assert config.name == "runflow-tools"
        assert config.transport_type == MCPTransportType.STDIO
        assert config.command == "python"
        assert config.args == ["-m", "runflow_mcp_server"]
        assert config.tool_timeout == 30
        assert config.enabled_tools == ["*"]
        assert config.disabled is False

    def test_create_sse_server(self):
        config = MCPServerConfig(
            name="remote-tools",
            transport_type=MCPTransportType.SSE,
            url="https://example.com/sse",
        )
        assert config.url == "https://example.com/sse"
        assert config.command is None

    def test_create_streamable_http_server(self):
        config = MCPServerConfig(
            name="http-tools",
            transport_type=MCPTransportType.STREAMABLE_HTTP,
            url="https://example.com/api",
            headers={"Authorization": "Bearer token"},
        )
        assert config.headers == {"Authorization": "Bearer token"}

    def test_frozen(self):
        config = MCPServerConfig(
            name="test",
            transport_type=MCPTransportType.STDIO,
            command="python",
        )
        with pytest.raises(AttributeError):
            config.name = "changed"

    def test_to_config_dict_stdio(self):
        config = MCPServerConfig(
            name="runflow-tools",
            transport_type=MCPTransportType.STDIO,
            command="python",
            args=["-m", "server"],
            env={"API_KEY": "xxx"},
        )
        result = config.to_config_dict()
        assert result["type"] == "stdio"
        assert result["command"] == "python"
        assert result["args"] == ["-m", "server"]
        assert result["env"] == {"API_KEY": "xxx"}

    def test_to_config_dict_sse(self):
        config = MCPServerConfig(
            name="remote",
            transport_type=MCPTransportType.SSE,
            url="https://example.com/sse",
        )
        result = config.to_config_dict()
        assert result["type"] == "sse"
        assert result["url"] == "https://example.com/sse"
        assert "command" not in result

    def test_to_config_dict_omits_defaults(self):
        config = MCPServerConfig(
            name="test",
            transport_type=MCPTransportType.STDIO,
            command="python",
        )
        result = config.to_config_dict()
        assert "tool_timeout" not in result
        assert "enabled_tools" not in result
        assert "disabled" not in result

    def test_to_config_dict_includes_non_defaults(self):
        config = MCPServerConfig(
            name="test",
            transport_type=MCPTransportType.STDIO,
            command="python",
            tool_timeout=60,
            enabled_tools=["tool1", "tool2"],
            disabled=True,
        )
        result = config.to_config_dict()
        assert result["tool_timeout"] == 60
        assert result["enabled_tools"] == ["tool1", "tool2"]
        assert result["disabled"] is True

    def test_from_config_dict_stdio(self):
        config_dict = {
            "type": "stdio",
            "command": "python",
            "args": ["-m", "server"],
            "env": {"KEY": "value"},
        }
        config = MCPServerConfig.from_config_dict("test", config_dict)
        assert config.name == "test"
        assert config.transport_type == MCPTransportType.STDIO
        assert config.command == "python"
        assert config.args == ["-m", "server"]
        assert config.env == {"KEY": "value"}

    def test_from_config_dict_sse(self):
        config_dict = {
            "type": "sse",
            "url": "https://example.com/sse",
        }
        config = MCPServerConfig.from_config_dict("remote", config_dict)
        assert config.transport_type == MCPTransportType.SSE
        assert config.url == "https://example.com/sse"

    def test_from_config_dict_invalid_type(self):
        config_dict = {"type": "invalid"}
        with pytest.raises(ValueError, match="无效的MCP传输协议类型"):
            MCPServerConfig.from_config_dict("test", config_dict)

    def test_roundtrip_stdio(self):
        original = MCPServerConfig(
            name="test",
            transport_type=MCPTransportType.STDIO,
            command="python",
            args=["-m", "server"],
            tool_timeout=60,
        )
        config_dict = original.to_config_dict()
        restored = MCPServerConfig.from_config_dict("test", config_dict)
        assert restored.name == original.name
        assert restored.transport_type == original.transport_type
        assert restored.command == original.command
        assert restored.args == original.args
        assert restored.tool_timeout == original.tool_timeout


class TestToolResult:
    """测试ToolResult不可变数据类"""

    def test_success_result(self):
        result = ToolResult(success=True, data={"temp": 25})
        assert result.success is True
        assert result.data == {"temp": 25}
        assert result.error is None
        assert result.duration_ms == 0

    def test_error_result(self):
        result = ToolResult(success=False, error="Connection failed")
        assert result.success is False
        assert result.error == "Connection failed"
        assert result.data is None

    def test_with_duration(self):
        result = ToolResult(success=True, data="ok", duration_ms=150)
        assert result.duration_ms == 150

    def test_frozen(self):
        result = ToolResult(success=True)
        with pytest.raises(AttributeError):
            result.success = False


class TestToolsConfig:
    """测试ToolsConfig不可变数据类"""

    def test_empty_config(self):
        config = ToolsConfig()
        assert len(config.mcp_servers) == 0

    def test_config_with_servers(self):
        server = MCPServerConfig(
            name="weather",
            transport_type=MCPTransportType.STDIO,
            command="python",
        )
        config = ToolsConfig(mcp_servers={"weather": server})
        assert "weather" in config.mcp_servers

    def test_to_config_dict_empty(self):
        config = ToolsConfig()
        result = config.to_config_dict()
        assert result == {"mcp_servers": {}}

    def test_to_config_dict_with_servers(self):
        server = MCPServerConfig(
            name="weather",
            transport_type=MCPTransportType.STDIO,
            command="python",
            args=["-m", "weather"],
        )
        config = ToolsConfig(mcp_servers={"weather": server})
        result = config.to_config_dict()
        assert "mcp_servers" in result
        assert "weather" in result["mcp_servers"]
        assert result["mcp_servers"]["weather"]["type"] == "stdio"

    def test_from_config_dict_empty(self):
        config = ToolsConfig.from_config_dict({})
        assert len(config.mcp_servers) == 0

    def test_from_config_dict_with_servers(self):
        config_dict = {
            "mcp_servers": {
                "weather": {
                    "type": "stdio",
                    "command": "python",
                    "args": ["-m", "weather"],
                }
            }
        }
        config = ToolsConfig.from_config_dict(config_dict)
        assert "weather" in config.mcp_servers
        assert config.mcp_servers["weather"].command == "python"

    def test_from_config_dict_ignores_invalid_server(self):
        config_dict = {
            "mcp_servers": {
                "valid": {"type": "stdio", "command": "python"},
                "invalid": "not a dict",
            }
        }
        config = ToolsConfig.from_config_dict(config_dict)
        assert "valid" in config.mcp_servers
        assert "invalid" not in config.mcp_servers

    def test_roundtrip(self):
        server1 = MCPServerConfig(
            name="weather",
            transport_type=MCPTransportType.STDIO,
            command="python",
            args=["-m", "weather"],
        )
        server2 = MCPServerConfig(
            name="remote",
            transport_type=MCPTransportType.SSE,
            url="https://example.com/sse",
        )
        original = ToolsConfig(mcp_servers={"weather": server1, "remote": server2})
        config_dict = original.to_config_dict()
        restored = ToolsConfig.from_config_dict(config_dict)
        assert set(restored.mcp_servers.keys()) == {"weather", "remote"}
        assert restored.mcp_servers["weather"].command == "python"
        assert restored.mcp_servers["remote"].url == "https://example.com/sse"
