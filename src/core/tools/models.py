# 工具生态数据模型
# 定义工具信息、状态、类型等核心数据结构

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ToolType(Enum):
    """工具类型"""

    LOCAL = "local"
    CLOUD = "cloud"
    HYBRID = "hybrid"


class ToolStatus(Enum):
    """工具状态"""

    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"
    INSTALLING = "installing"


class MCPTransportType(Enum):
    """MCP传输协议类型"""

    STDIO = "stdio"
    SSE = "sse"
    STREAMABLE_HTTP = "streamableHttp"


@dataclass(frozen=True)
class ToolInfo:
    """工具信息（不可变数据类）

    描述一个工具的元数据，包括名称、描述、类型、状态等。

    Attributes:
        id: 工具唯一标识，格式为 mcp_{server_name}_{tool_name}
        name: 工具显示名称
        description: 工具功能描述
        tool_type: 工具类型（本地/云端/混合）
        status: 工具当前状态
        version: 工具版本号
        author: 工具作者
        homepage: 工具主页URL
        config_schema: 工具配置的JSON Schema
        privacy_policy: 隐私政策说明
        mcp_server_name: 所属MCP服务器名称
    """

    id: str
    name: str
    description: str
    tool_type: ToolType
    status: ToolStatus
    version: str = "0.1.0"
    author: str = ""
    homepage: str | None = None
    config_schema: dict[str, Any] | None = None
    privacy_policy: str | None = None
    mcp_server_name: str | None = None


@dataclass(frozen=True)
class MCPServerConfig:
    """MCP服务器配置（不可变数据类）

    描述一个MCP服务器的连接配置，支持stdio/sse/streamableHttp三种传输协议。

    Attributes:
        name: 服务器名称
        transport_type: 传输协议类型
        command: stdio模式下的启动命令
        args: stdio模式下的命令参数
        env: 环境变量配置
        url: sse/streamableHttp模式下的服务端URL
        headers: streamableHttp模式下的请求头
        tool_timeout: 工具调用超时时间（秒）
        enabled_tools: 启用的工具列表，["*"]表示全部启用
        disabled: 是否禁用此服务器
    """

    name: str
    transport_type: MCPTransportType
    command: str | None = None
    args: list[str] | None = None
    env: dict[str, str] | None = None
    url: str | None = None
    headers: dict[str, str] | None = None
    tool_timeout: int = 30
    enabled_tools: list[str] = field(default_factory=lambda: ["*"])
    disabled: bool = False

    def to_config_dict(self) -> dict[str, Any]:
        """转换为config.json中的配置字典格式

        Returns:
            dict: 符合MCP标准规范的配置字典
        """
        config: dict[str, Any] = {"type": self.transport_type.value}

        if self.transport_type == MCPTransportType.STDIO:
            if self.command is not None:
                config["command"] = self.command
            if self.args is not None:
                config["args"] = self.args
            if self.env is not None:
                config["env"] = self.env
        elif self.transport_type in (
            MCPTransportType.SSE,
            MCPTransportType.STREAMABLE_HTTP,
        ):
            if self.url is not None:
                config["url"] = self.url
            if self.headers is not None:
                config["headers"] = self.headers

        if self.tool_timeout != 30:
            config["tool_timeout"] = self.tool_timeout
        if self.enabled_tools != ["*"]:
            config["enabled_tools"] = self.enabled_tools
        if self.disabled:
            config["disabled"] = True

        return config

    @classmethod
    def from_config_dict(cls, name: str, config: dict[str, Any]) -> "MCPServerConfig":
        """从config.json中的配置字典创建实例

        Args:
            name: 服务器名称
            config: 配置字典

        Returns:
            MCPServerConfig: 服务器配置实例

        Raises:
            ValueError: 传输协议类型无效时抛出
        """
        transport_str = config.get("type", "stdio")
        try:
            transport_type = MCPTransportType(transport_str)
        except ValueError:
            raise ValueError(
                f"无效的MCP传输协议类型: '{transport_str}'，"
                f"支持的类型: {[t.value for t in MCPTransportType]}"
            )

        return cls(
            name=name,
            transport_type=transport_type,
            command=config.get("command"),
            args=config.get("args"),
            env=config.get("env"),
            url=config.get("url"),
            headers=config.get("headers"),
            tool_timeout=config.get("tool_timeout", 30),
            enabled_tools=config.get("enabled_tools", ["*"]),
            disabled=config.get("disabled", False),
        )


@dataclass(frozen=True)
class ToolResult:
    """工具调用结果（不可变数据类）

    Attributes:
        success: 调用是否成功
        data: 返回数据
        error: 错误信息（调用失败时）
        duration_ms: 调用耗时（毫秒）
    """

    success: bool
    data: Any = None
    error: str | None = None
    duration_ms: int = 0


@dataclass(frozen=True)
class ToolsConfig:
    """工具生态全局配置（不可变数据类）

    存储在config.json的"tools"字段下。

    Attributes:
        mcp_servers: MCP服务器配置映射，key为服务器名称
    """

    mcp_servers: dict[str, MCPServerConfig] = field(default_factory=dict)

    def to_config_dict(self) -> dict[str, Any]:
        """转换为config.json中的配置字典格式

        Returns:
            dict: 工具配置字典
        """
        servers: dict[str, Any] = {}
        for name, server_config in self.mcp_servers.items():
            servers[name] = server_config.to_config_dict()
        return {"mcp_servers": servers}

    @classmethod
    def from_config_dict(cls, config: dict[str, Any]) -> "ToolsConfig":
        """从config.json中的配置字典创建实例

        Args:
            config: 工具配置字典，应包含"mcp_servers"字段

        Returns:
            ToolsConfig: 工具配置实例
        """
        mcp_servers: dict[str, MCPServerConfig] = {}
        servers_config = config.get("mcp_servers", {})

        for name, server_config in servers_config.items():
            if isinstance(server_config, dict):
                mcp_servers[name] = MCPServerConfig.from_config_dict(
                    name, server_config
                )

        return cls(mcp_servers=mcp_servers)
