"""AgentLoop 适配器 - 封装私有 API 调用

隔离 nanobot 版本变更风险，为业务模块提供稳定接口。
所有 _ 前缀的私有 API 调用必须通过本 Adapter。

基于 nanobot 0.2.2 实际 API 调研：
- _connect_mcp: async 方法
- _mcp_stacks: dict[str, AsyncExitStack] 实例属性
- _background_tasks: list[asyncio.Task] 实例属性
- _extra_hooks: list[AgentHook] 实例属性
- close_mcp: async 公开方法
- process_direct: async 公开方法，返回 OutboundMessage | None
- submit_cron_turn: async 公开方法，接收单个 InboundMessage 参数
- stop: 同步公开方法
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class AdapterError(Exception):
    """Adapter 操作失败异常（私有 API 不可用时抛出）"""


class AgentLoopAdapter:
    """封装 AgentLoop 私有 API，提供稳定接口

    所有 _ 前缀的私有 API 调用通过本类封装，捕获 AttributeError 转为 AdapterError，
    便于上层统一处理 nanobot 版本变更风险。
    """

    def __init__(self, agent_loop: Any):
        self._loop = agent_loop

    async def connect_mcp(self) -> None:
        """连接 MCP 服务器（封装 _connect_mcp）"""
        try:
            await self._loop._connect_mcp()
        except AttributeError as e:
            raise AdapterError(f"AgentLoop._connect_mcp 不可用: {e}") from e

    @property
    def mcp_stacks(self) -> dict[str, Any]:
        """MCP 栈（封装 _mcp_stacks，类型为 dict）"""
        try:
            return self._loop._mcp_stacks
        except AttributeError as e:
            raise AdapterError(f"AgentLoop._mcp_stacks 不可用: {e}") from e

    @property
    def background_tasks(self) -> list[Any]:
        """后台任务列表（封装 _background_tasks，类型为 list）"""
        try:
            return self._loop._background_tasks
        except AttributeError as e:
            raise AdapterError(f"AgentLoop._background_tasks 不可用: {e}") from e

    def add_hook(self, hook: Any) -> None:
        """添加 Hook（封装 _extra_hooks 追加）"""
        try:
            self._loop._extra_hooks.append(hook)
        except AttributeError as e:
            raise AdapterError(f"AgentLoop._extra_hooks 不可用: {e}") from e

    async def close_mcp(self) -> None:
        """关闭 MCP 连接（封装 close_mcp 公开方法）"""
        await self._loop.close_mcp()

    async def process_direct(self, content: str, **kwargs: Any) -> Any:
        """直接处理消息（封装 process_direct 公开方法）

        Args:
            content: 消息文本内容
            **kwargs: 透传给 AgentLoop.process_direct 的可选参数
                      (session_key, channel, chat_id, sender_id, media, etc.)

        Returns:
            OutboundMessage | None
        """
        return await self._loop.process_direct(content, **kwargs)

    async def submit_cron_turn(self, msg: Any) -> Any:
        """提交 Cron turn（封装 submit_cron_turn 公开方法）

        Args:
            msg: InboundMessage 实例

        Returns:
            OutboundMessage | None
        """
        await self._loop.submit_cron_turn(msg)

    def stop(self) -> None:
        """停止 Agent Loop（封装 stop 同步方法）"""
        self._loop.stop()
