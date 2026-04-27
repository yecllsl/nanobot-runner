# 工具管理器模块
# 负责工具配置管理和状态监控
# 注意：工具调用由nanobot SDK的Nanobot.from_config()和bot.run()自动处理

import logging
from pathlib import Path
from typing import Any

from src.core.tools.mcp_config_helper import MCPConfigHelper
from src.core.tools.models import (
    MCPServerConfig,
    ToolInfo,
    ToolStatus,
    ToolType,
)

logger = logging.getLogger(__name__)


class ToolManager:
    """工具管理器

    负责工具配置管理和状态监控。
    注意：工具调用由nanobot SDK的Nanobot.from_config()和bot.run()自动处理。

    ToolManager的核心职责是配置管理而非工具调用：
    - 列出/发现可用工具
    - 启用/禁用工具（更新config.json）
    - 查询工具状态
    - 管理MCP服务器配置

    Attributes:
        config_path: config.json文件路径
        config_helper: MCP配置辅助类实例
    """

    def __init__(self, config_path: Path) -> None:
        """初始化工具管理器

        Args:
            config_path: config.json路径
        """
        self.config_path = config_path
        self.config_helper = MCPConfigHelper(config_path)

    def list_tools(self) -> list[ToolInfo]:
        """列出所有可用工具

        从config.json中读取MCP服务器配置，生成工具信息列表。
        对于enabled_tools为["*"]的服务器，生成一个通配符工具条目。

        Returns:
            list[ToolInfo]: 工具信息列表
        """
        tools_config = self.config_helper.load_tools_config()
        tools: list[ToolInfo] = []

        for server_name, server_config in tools_config.mcp_servers.items():
            server_tools = self._build_tools_from_server(server_name, server_config)
            tools.extend(server_tools)

        return tools

    def get_tool_status(self, tool_name: str) -> ToolStatus:
        """获取工具状态

        根据工具名称判断其当前状态。
        支持精确匹配和通配符匹配（mcp_{server}_*格式）。

        Args:
            tool_name: 工具名称，格式为 mcp_{server_name}_{tool_name}

        Returns:
            ToolStatus: 工具状态
        """
        tools_config = self.config_helper.load_tools_config()
        server_name = self._extract_server_name(tool_name)

        if server_name is None:
            return ToolStatus.DISABLED

        server_config = tools_config.mcp_servers.get(server_name)
        if server_config is None:
            return ToolStatus.DISABLED

        if server_config.disabled:
            return ToolStatus.DISABLED

        specific_tool = self._extract_specific_tool(tool_name, server_name)
        if (
            specific_tool is not None
            and server_config.enabled_tools != ["*"]
            and specific_tool not in server_config.enabled_tools
        ):
            return ToolStatus.DISABLED

        return ToolStatus.ENABLED

    def enable_tool(self, tool_name: str) -> bool:
        """启用工具

        将指定工具添加到对应MCP服务器的enabled_tools列表中。
        如果服务器当前disabled=True，则同时启用服务器。

        Args:
            tool_name: 工具名称，格式为 mcp_{server_name}_{tool_name}

        Returns:
            bool: 是否启用成功
        """
        server_name = self._extract_server_name(tool_name)
        if server_name is None:
            logger.warning(f"无法解析工具名称: {tool_name}")
            return False

        tools_config = self.config_helper.load_tools_config()
        server_config = tools_config.mcp_servers.get(server_name)

        if server_config is None:
            logger.warning(f"MCP服务器不存在: {server_name}")
            return False

        specific_tool = self._extract_specific_tool(tool_name, server_name)
        update_kwargs: dict[str, Any] = {}

        if server_config.disabled:
            update_kwargs["disabled"] = False

        if specific_tool is not None and server_config.enabled_tools != ["*"]:
            new_enabled = list(server_config.enabled_tools)
            if specific_tool not in new_enabled:
                new_enabled.append(specific_tool)
            update_kwargs["enabled_tools"] = new_enabled

        if update_kwargs:
            return self.config_helper.update_mcp_server(server_name, **update_kwargs)

        return True

    def disable_tool(self, tool_name: str) -> bool:
        """禁用工具

        将指定工具从对应MCP服务器的enabled_tools列表中移除。
        如果移除后enabled_tools为空，则禁用整个服务器。

        Args:
            tool_name: 工具名称，格式为 mcp_{server_name}_{tool_name}

        Returns:
            bool: 是否禁用成功
        """
        server_name = self._extract_server_name(tool_name)
        if server_name is None:
            logger.warning(f"无法解析工具名称: {tool_name}")
            return False

        tools_config = self.config_helper.load_tools_config()
        server_config = tools_config.mcp_servers.get(server_name)

        if server_config is None:
            logger.warning(f"MCP服务器不存在: {server_name}")
            return False

        specific_tool = self._extract_specific_tool(tool_name, server_name)
        update_kwargs: dict[str, Any] = {}

        if specific_tool is None or server_config.enabled_tools == ["*"]:
            update_kwargs["disabled"] = True
        else:
            new_enabled = [t for t in server_config.enabled_tools if t != specific_tool]
            if not new_enabled:
                update_kwargs["disabled"] = True
                update_kwargs["enabled_tools"] = []
            else:
                update_kwargs["enabled_tools"] = new_enabled

        if update_kwargs:
            return self.config_helper.update_mcp_server(server_name, **update_kwargs)

        return True

    def discover_tools(self) -> list[ToolInfo]:
        """发现可用工具

        扫描所有已配置的MCP服务器，返回所有可用的工具信息。
        与list_tools的区别：discover_tools只返回已启用的工具。

        Returns:
            list[ToolInfo]: 可用工具信息列表
        """
        all_tools = self.list_tools()
        return [t for t in all_tools if t.status == ToolStatus.ENABLED]

    def get_server_config(self, server_name: str) -> MCPServerConfig | None:
        """获取指定MCP服务器的配置

        Args:
            server_name: 服务器名称

        Returns:
            MCPServerConfig | None: 服务器配置，不存在返回None
        """
        tools_config = self.config_helper.load_tools_config()
        return tools_config.mcp_servers.get(server_name)

    def list_servers(self) -> list[str]:
        """列出所有已配置的MCP服务器名称

        Returns:
            list[str]: 服务器名称列表
        """
        tools_config = self.config_helper.load_tools_config()
        return list(tools_config.mcp_servers.keys())

    def enable_server(self, server_name: str) -> bool:
        """启用MCP服务器

        Args:
            server_name: 服务器名称

        Returns:
            bool: 是否启用成功
        """
        return self.config_helper.update_mcp_server(server_name, disabled=False)

    def disable_server(self, server_name: str) -> bool:
        """禁用MCP服务器

        Args:
            server_name: 服务器名称

        Returns:
            bool: 是否禁用成功
        """
        return self.config_helper.update_mcp_server(server_name, disabled=True)

    def add_server(self, server_config: MCPServerConfig) -> bool:
        """添加MCP服务器

        Args:
            server_config: 服务器配置

        Returns:
            bool: 是否添加成功
        """
        return self.config_helper.add_mcp_server(server_config)

    def remove_server(self, server_name: str) -> bool:
        """移除MCP服务器

        Args:
            server_name: 服务器名称

        Returns:
            bool: 是否移除成功
        """
        return self.config_helper.remove_mcp_server(server_name)

    def validate_config(self) -> list[str]:
        """验证工具配置有效性

        Returns:
            list[str]: 错误信息列表，空列表表示验证通过
        """
        return self.config_helper.validate_mcp_config()

    @staticmethod
    def _build_tools_from_server(
        server_name: str, server_config: MCPServerConfig
    ) -> list[ToolInfo]:
        """从MCP服务器配置构建工具信息列表

        Args:
            server_name: 服务器名称
            server_config: 服务器配置

        Returns:
            list[ToolInfo]: 工具信息列表
        """
        tools: list[ToolInfo] = []
        status = ToolStatus.DISABLED if server_config.disabled else ToolStatus.ENABLED
        tool_type = ToolType.LOCAL

        if server_config.transport_type.value in ("sse", "streamableHttp"):
            tool_type = ToolType.CLOUD

        if server_config.enabled_tools == ["*"]:
            tool_info = ToolInfo(
                id=f"mcp_{server_name}_*",
                name=f"{server_name} (全部工具)",
                description=f"MCP服务器 {server_name} 的全部工具",
                tool_type=tool_type,
                status=status,
                mcp_server_name=server_name,
            )
            tools.append(tool_info)
        else:
            for tool_name in server_config.enabled_tools:
                tool_info = ToolInfo(
                    id=f"mcp_{server_name}_{tool_name}",
                    name=tool_name,
                    description=f"MCP服务器 {server_name} 的 {tool_name} 工具",
                    tool_type=tool_type,
                    status=status,
                    mcp_server_name=server_name,
                )
                tools.append(tool_info)

        return tools

    def _extract_server_name(self, tool_name: str) -> str | None:
        """从工具名称中提取MCP服务器名称

        工具名称格式为 mcp_{server_name}_{tool_name}，
        由于server_name和tool_name都可能包含下划线，
        需要基于已知的服务器名称进行匹配。

        Args:
            tool_name: 工具名称

        Returns:
            str | None: 服务器名称，解析失败返回None
        """
        if not tool_name.startswith("mcp_"):
            return None

        rest = tool_name[4:]
        if not rest:
            return None

        if rest.endswith("_*"):
            return rest[:-2]

        tools_config = self.config_helper.load_tools_config()
        for server_name in tools_config.mcp_servers:
            prefix = f"mcp_{server_name}_"
            if tool_name.startswith(prefix):
                return server_name

        return None

    @staticmethod
    def _extract_specific_tool(tool_name: str, server_name: str) -> str | None:
        """从工具名称中提取具体工具名

        基于已知的服务器名称，从工具全名中提取工具名部分。

        Args:
            tool_name: 工具名称，格式为 mcp_{server_name}_{tool_name}
            server_name: 已知的服务器名称

        Returns:
            str | None: 具体工具名，通配符格式返回None
        """
        if tool_name.endswith("_*"):
            return None

        prefix = f"mcp_{server_name}_"
        if tool_name.startswith(prefix):
            return tool_name[len(prefix) :]

        return None
