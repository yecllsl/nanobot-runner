# MCP工具连接器模块
# 负责从config.json加载MCP服务器配置并连接到AgentLoop

import logging
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from src.core.tools.models import MCPServerConfig

logger = logging.getLogger(__name__)


def _adapt_for_nanobot(server_config: MCPServerConfig) -> SimpleNamespace:
    """将项目MCPServerConfig转换为nanobot SDK期望的格式

    nanobot SDK期望通过cfg.type访问传输类型，而项目使用transport_type。
    此函数创建SimpleNamespace对象，使nanobot SDK能正确访问配置属性。

    Args:
        server_config: 项目的MCPServerConfig实例

    Returns:
        SimpleNamespace: nanobot SDK兼容的配置对象
    """
    return SimpleNamespace(
        type=server_config.transport_type.value,
        command=server_config.command,
        args=server_config.args,
        env=server_config.env,
        url=server_config.url,
        headers=server_config.headers,
        tool_timeout=server_config.tool_timeout,
        enabled_tools=server_config.enabled_tools,
        disabled=server_config.disabled,
    )


async def connect_mcp_tools_from_config(
    config_path: Path,
    tool_registry: Any,
) -> dict[str, Any]:
    """从config.json加载MCP服务器配置并连接工具到注册表

    读取config.json中的tools.mcp_servers配置，
    调用nanobot SDK的connect_mcp_servers函数连接所有已配置的MCP服务器，
    并将其工具注册到AgentLoop的ToolRegistry中。

    Args:
        config_path: config.json文件路径
        tool_registry: AgentLoop.tools（ToolRegistry实例）

    Returns:
        dict[str, Any]: 连接结果，包含:
            - connected_servers: 成功连接的服务器列表
            - failed_servers: 连接失败的服务器列表
            - exit_stacks: 服务器连接的AsyncExitStack映射（用于清理）
    """
    from src.core.tools.mcp_config_helper import MCPConfigHelper

    config_helper = MCPConfigHelper(config_path)
    tools_config = config_helper.load_tools_config()

    if not tools_config.mcp_servers:
        logger.info("未配置MCP服务器，跳过连接")
        return {
            "connected_servers": [],
            "failed_servers": [],
            "exit_stacks": {},
        }

    mcp_servers_dict: dict[str, Any] = {}
    for name, server_config in tools_config.mcp_servers.items():
        if server_config.disabled:
            logger.info(f"MCP服务器 {name} 已禁用，跳过连接")
            continue
        mcp_servers_dict[name] = _adapt_for_nanobot(server_config)

    if not mcp_servers_dict:
        logger.info("没有已启用的MCP服务器，跳过连接")
        return {
            "connected_servers": [],
            "failed_servers": [],
            "exit_stacks": {},
        }

    try:
        from nanobot.agent.tools.mcp import connect_mcp_servers
    except ImportError:
        logger.warning("nanobot-ai MCP模块不可用，跳过MCP服务器连接")
        return {
            "connected_servers": [],
            "failed_servers": list(mcp_servers_dict.keys()),
            "exit_stacks": {},
        }

    try:
        exit_stacks = await connect_mcp_servers(mcp_servers_dict, tool_registry)
        connected_servers = list(exit_stacks.keys())
        failed_servers = [
            name for name in mcp_servers_dict if name not in connected_servers
        ]

        if connected_servers:
            logger.info(f"已连接MCP服务器: {connected_servers}")
        if failed_servers:
            logger.warning(f"MCP服务器连接失败: {failed_servers}")

        return {
            "connected_servers": connected_servers,
            "failed_servers": failed_servers,
            "exit_stacks": exit_stacks,
        }
    except Exception as e:
        logger.error(f"连接MCP服务器失败: {e}")
        return {
            "connected_servers": [],
            "failed_servers": list(mcp_servers_dict.keys()),
            "exit_stacks": {},
        }


def load_mcp_servers_config(config_path: Path) -> dict[str, Any]:
    """从config.json加载MCP服务器配置字典

    用于传递给nanobot SDK的connect_mcp_servers函数。

    Args:
        config_path: config.json文件路径

    Returns:
        dict[str, Any]: MCP服务器配置字典，格式为 {name: config_dict}
    """
    from src.core.tools.mcp_config_helper import MCPConfigHelper

    config_helper = MCPConfigHelper(config_path)
    tools_config = config_helper.load_tools_config()

    result: dict[str, Any] = {}
    for name, server_config in tools_config.mcp_servers.items():
        if not server_config.disabled:
            result[name] = _adapt_for_nanobot(server_config)

    return result
