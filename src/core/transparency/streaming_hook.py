# 流式输出Hook模块
# 实现AgentHook，支持CLI和Gateway双通道流式输出

from __future__ import annotations

import logging

from nanobot.agent.hook import AgentHook, AgentHookContext
from nanobot.bus import MessageBus
from rich.console import Console

logger = logging.getLogger(__name__)


class StreamingHook(AgentHook):
    """流式输出钩子

    继承nanobot-ai的AgentHook，实现流式输出功能。
    支持CLI（Rich Console.print）和Gateway（MessageBus.publish_outbound）双通道输出。
    """

    def __init__(
        self,
        console: Console | None = None,
        bus: MessageBus | None = None,
        channel: str | None = None,
        chat_id: str | None = None,
    ) -> None:
        """初始化流式输出钩子

        Args:
            console: Rich控制台实例（CLI通道）
            bus: 消息总线实例（Gateway通道）
            channel: 通道名称（Gateway通道时使用）
            chat_id: 聊天ID（Gateway通道时使用）
        """
        super().__init__()
        self._console = console
        self._bus = bus
        self._channel = channel
        self._chat_id = chat_id
        self._stream_buffer: str = ""
        self._stream_active: bool = False

    def wants_streaming(self) -> bool:
        """是否支持流式输出

        Returns:
            bool: 始终返回True，表示支持流式输出
        """
        return True

    async def on_stream(self, context: AgentHookContext, delta: str) -> None:
        """流式输出时触发

        将流式输出片段通过CLI或Gateway通道输出。
        过滤空delta，不输出空字符串。

        Args:
            context: Hook上下文
            delta: 流式输出片段
        """
        if not delta:
            return

        self._stream_active = True
        self._stream_buffer += delta

        # CLI通道输出
        if self._console is not None:
            self._console.print(delta, end="")

        # Gateway通道输出
        if self._bus is not None and self._channel and self._chat_id:
            try:
                from nanobot.bus.events import OutboundMessage

                self._bus.publish_outbound(
                    OutboundMessage(
                        channel=self._channel,
                        chat_id=self._chat_id,
                        content=delta,
                        metadata={"stream_delta": True},
                    )
                )
            except Exception as e:
                logger.warning(f"Gateway流式输出失败: {e}")

    async def on_stream_end(self, context: AgentHookContext) -> None:
        """流式输出结束时触发

        输出换行并清理流式状态。

        Args:
            context: Hook上下文
        """
        if self._stream_active and self._console is not None:
            self._console.print()

        self._stream_active = False
        self._stream_buffer = ""

    def get_stream_buffer(self) -> str:
        """获取当前流式输出缓冲区内容

        Returns:
            str: 已缓冲的流式输出内容
        """
        return self._stream_buffer

    def is_stream_active(self) -> bool:
        """检查流式输出是否处于活动状态

        Returns:
            bool: 流式输出是否活动
        """
        return self._stream_active

    def reset(self) -> None:
        """重置流式输出状态"""
        self._stream_buffer = ""
        self._stream_active = False
