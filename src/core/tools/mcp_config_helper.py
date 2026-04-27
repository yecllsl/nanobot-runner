# MCP配置辅助模块
# 负责MCP服务器配置的管理、验证和导入
# 注意：不负责工具调用，工具调用由nanobot SDK自动处理

import json
import logging
from pathlib import Path
from typing import Any

from src.core.tools.models import MCPServerConfig, MCPTransportType, ToolsConfig

logger = logging.getLogger(__name__)


class MCPConfigHelper:
    """MCP配置辅助类

    负责MCP服务器配置的管理和验证。
    注意：不负责工具调用，工具调用由nanobot SDK的Nanobot.from_config()自动处理。

    Attributes:
        config_path: config.json文件路径
    """

    def __init__(self, config_path: Path) -> None:
        """初始化配置辅助类

        Args:
            config_path: config.json路径
        """
        self.config_path = config_path

    def load_tools_config(self) -> ToolsConfig:
        """加载工具配置

        从config.json中读取tools字段，解析为ToolsConfig实例。

        Returns:
            ToolsConfig: 工具配置实例，配置文件不存在或无tools字段时返回空配置
        """
        if not self.config_path.exists():
            logger.debug(f"配置文件不存在: {self.config_path}")
            return ToolsConfig()

        try:
            with open(self.config_path, encoding="utf-8") as f:
                config = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"读取配置文件失败: {e}")
            return ToolsConfig()

        tools_section = config.get("tools", {})
        if not isinstance(tools_section, dict):
            logger.warning("配置文件中tools字段格式错误，应为字典类型")
            return ToolsConfig()

        return ToolsConfig.from_config_dict(tools_section)

    def save_tools_config(self, tools_config: ToolsConfig) -> bool:
        """保存工具配置到config.json

        将ToolsConfig实例序列化并写入config.json的tools字段。
        保留config.json中其他字段不变。

        Args:
            tools_config: 工具配置实例

        Returns:
            bool: 是否保存成功
        """
        try:
            config: dict[str, Any] = {}
            if self.config_path.exists():
                with open(self.config_path, encoding="utf-8") as f:
                    config = json.load(f)

            config["tools"] = tools_config.to_config_dict()

            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            logger.info(f"工具配置已保存到: {self.config_path}")
            return True
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"保存工具配置失败: {e}")
            return False

    def validate_mcp_config(self) -> list[str]:
        """验证MCP配置有效性

        检查所有MCP服务器配置是否符合规范：
        - stdio协议必须有command字段
        - sse协议必须有url字段
        - streamableHttp协议必须有url字段
        - enabled_tools必须为列表
        - tool_timeout必须为正整数

        Returns:
            list[str]: 错误信息列表，空列表表示验证通过
        """
        errors: list[str] = []
        tools_config = self.load_tools_config()

        for name, server_config in tools_config.mcp_servers.items():
            prefix = f"服务器[{name}]"

            if (
                server_config.transport_type == MCPTransportType.STDIO
                and not server_config.command
            ):
                errors.append(f"{prefix}: stdio协议必须配置command字段")
            elif (
                server_config.transport_type == MCPTransportType.SSE
                and not server_config.url
            ):
                errors.append(f"{prefix}: sse协议必须配置url字段")
            elif (
                server_config.transport_type == MCPTransportType.STREAMABLE_HTTP
                and not server_config.url
            ):
                errors.append(f"{prefix}: streamableHttp协议必须配置url字段")

            if not isinstance(server_config.enabled_tools, list):
                errors.append(f"{prefix}: enabled_tools必须为列表")
            elif not server_config.enabled_tools:
                errors.append(f"{prefix}: enabled_tools不能为空")

            if server_config.tool_timeout <= 0:
                errors.append(f"{prefix}: tool_timeout必须为正整数")

        return errors

    def list_mcp_tools(self) -> list[str]:
        """列出已配置的MCP工具名称

        根据mcp_servers配置和enabled_tools规则，生成工具名称列表。
        工具命名格式为 mcp_{server_name}_{tool_name}。

        当enabled_tools为["*"]时，无法确定具体工具名称，
        返回服务器级别的标识 mcp_{server_name}_*。

        Returns:
            list[str]: 工具名称列表
        """
        tools_config = self.load_tools_config()
        tool_names: list[str] = []

        for name, server_config in tools_config.mcp_servers.items():
            if server_config.disabled:
                continue

            if server_config.enabled_tools == ["*"]:
                tool_names.append(f"mcp_{name}_*")
            else:
                for tool_name in server_config.enabled_tools:
                    tool_names.append(f"mcp_{name}_{tool_name}")

        return tool_names

    def import_claude_desktop_config(self, claude_config_path: Path) -> bool:
        """导入Claude Desktop的MCP配置

        读取Claude Desktop的配置文件，提取mcpServers字段，
        转换为本项目兼容的mcp_servers格式并合并到现有配置中。

        Claude Desktop配置格式:
        {
            "mcpServers": {
                "server-name": {
                    "command": "...",
                    "args": [...],
                    "env": {...}
                }
            }
        }

        Args:
            claude_config_path: Claude Desktop配置文件路径

        Returns:
            bool: 是否导入成功
        """
        if not claude_config_path.exists():
            logger.warning(f"Claude Desktop配置文件不存在: {claude_config_path}")
            return False

        try:
            with open(claude_config_path, encoding="utf-8") as f:
                claude_config = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"读取Claude Desktop配置失败: {e}")
            return False

        mcp_servers = claude_config.get("mcpServers", {})
        if not isinstance(mcp_servers, dict):
            logger.warning("Claude Desktop配置中mcpServers字段格式错误")
            return False

        if not mcp_servers:
            logger.info("Claude Desktop配置中没有MCP服务器")
            return True

        tools_config = self.load_tools_config()
        imported_count = 0

        for name, server_config in mcp_servers.items():
            if not isinstance(server_config, dict):
                logger.warning(f"跳过无效的服务器配置: {name}")
                continue

            converted = self._convert_claude_server_config(name, server_config)
            if converted is not None:
                tools_config.mcp_servers[name] = converted
                imported_count += 1
                logger.info(f"已导入MCP服务器: {name}")

        if imported_count > 0:
            success = self.save_tools_config(tools_config)
            if success:
                logger.info(f"成功导入 {imported_count} 个MCP服务器配置")
            return success

        logger.info("没有可导入的MCP服务器配置")
        return True

    @staticmethod
    def _convert_claude_server_config(
        name: str, server_config: dict[str, Any]
    ) -> MCPServerConfig | None:
        """将Claude Desktop的服务器配置转换为本项目格式

        Claude Desktop的stdio服务器配置通常包含command和args字段，
        需要转换为本项目的MCPServerConfig格式。

        Args:
            name: 服务器名称
            server_config: Claude Desktop格式的服务器配置

        Returns:
            MCPServerConfig | None: 转换后的配置，转换失败返回None
        """
        if "command" in server_config:
            return MCPServerConfig(
                name=name,
                transport_type=MCPTransportType.STDIO,
                command=server_config.get("command"),
                args=server_config.get("args"),
                env=server_config.get("env"),
                tool_timeout=server_config.get("tool_timeout", 30),
                enabled_tools=server_config.get("enabled_tools", ["*"]),
                disabled=server_config.get("disabled", False),
            )

        if "url" in server_config:
            url = server_config["url"]
            if url.endswith("/sse"):
                transport_type = MCPTransportType.SSE
            else:
                transport_type = MCPTransportType.STREAMABLE_HTTP

            return MCPServerConfig(
                name=name,
                transport_type=transport_type,
                url=url,
                headers=server_config.get("headers"),
                tool_timeout=server_config.get("tool_timeout", 30),
                enabled_tools=server_config.get("enabled_tools", ["*"]),
                disabled=server_config.get("disabled", False),
            )

        logger.warning(f"无法识别的服务器配置格式: {name}")
        return None

    def add_mcp_server(self, server_config: MCPServerConfig) -> bool:
        """添加MCP服务器配置

        Args:
            server_config: MCP服务器配置

        Returns:
            bool: 是否添加成功
        """
        tools_config = self.load_tools_config()
        tools_config.mcp_servers[server_config.name] = server_config
        return self.save_tools_config(tools_config)

    def remove_mcp_server(self, server_name: str) -> bool:
        """移除MCP服务器配置

        Args:
            server_name: 服务器名称

        Returns:
            bool: 是否移除成功（服务器不存在也返回True）
        """
        tools_config = self.load_tools_config()
        if server_name in tools_config.mcp_servers:
            del tools_config.mcp_servers[server_name]
            return self.save_tools_config(tools_config)
        return True

    def update_mcp_server(self, server_name: str, **kwargs: Any) -> bool:
        """更新MCP服务器配置

        根据关键字参数更新指定服务器的配置项。

        Args:
            server_name: 服务器名称
            **kwargs: 要更新的配置项

        Returns:
            bool: 是否更新成功
        """
        tools_config = self.load_tools_config()

        if server_name not in tools_config.mcp_servers:
            logger.warning(f"MCP服务器不存在: {server_name}")
            return False

        old_config = tools_config.mcp_servers[server_name]
        old_dict: dict[str, Any] = {
            "name": old_config.name,
            "transport_type": old_config.transport_type,
            "command": old_config.command,
            "args": old_config.args,
            "env": old_config.env,
            "url": old_config.url,
            "headers": old_config.headers,
            "tool_timeout": old_config.tool_timeout,
            "enabled_tools": old_config.enabled_tools,
            "disabled": old_config.disabled,
        }
        old_dict.update(kwargs)

        try:
            new_config = MCPServerConfig(**old_dict)
        except (TypeError, ValueError) as e:
            logger.error(f"更新MCP服务器配置失败: {e}")
            return False

        tools_config.mcp_servers[server_name] = new_config
        return self.save_tools_config(tools_config)
