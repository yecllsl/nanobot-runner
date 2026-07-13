"""运行时事件订阅 Hook - 订阅 RuntimeEventPublisher

订阅 nanobot 0.2.2 运行时事件（工具调用进度、迭代生命周期等），
转发到 WebUI 和业务模块。支持多订阅者，回调异常静默降级。

基于 nanobot 0.2.2 实际 API：
- AgentHookContext 无 trace_id 属性，使用 getattr 安全访问
- AgentHook 生命周期方法：before_iteration/before_execute_tools/after_iteration
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from nanobot.agent.hook import AgentHook, AgentHookContext

logger = logging.getLogger(__name__)


@dataclass
class RuntimeEvent:
    """运行时事件数据结构

    Attributes:
        type: 事件类型（iteration_start/iteration_end/tool_start）
        trace_id: 追踪标识（从 context 获取，可能为空）
        data: 事件附加数据（如 tool_call 字典）
    """

    type: str
    trace_id: str = ""
    data: Any = field(default=None)


class RuntimeEventHook(AgentHook):
    """订阅运行时事件总线，转发到 WebUI

    作为 AgentHook 子类挂在 AgentLoop 上，在 Hook 生命周期中
    发布运行时事件，支持多订阅者。回调异常静默降级，不影响主流程。
    """

    def __init__(self, event_publisher: Any):
        """初始化 RuntimeEventHook

        Args:
            event_publisher: RuntimeEventPublisher 实例（预留，当前版本通过 subscribe 注册回调）
        """
        self._publisher = event_publisher
        self._subscribers: list[Callable[[RuntimeEvent], None]] = []

    def subscribe(self, callback: Callable[[RuntimeEvent], None]) -> None:
        """订阅运行时事件

        Args:
            callback: 事件回调函数，接收 RuntimeEvent 参数
        """
        self._subscribers.append(callback)

    async def before_iteration(self, context: AgentHookContext) -> None:
        """迭代前发布 iteration_start 事件"""
        event = RuntimeEvent(
            type="iteration_start",
            trace_id=getattr(context, "trace_id", ""),
        )
        self._publish(event)

    async def before_execute_tools(self, context: AgentHookContext) -> None:
        """工具执行前为每个工具调用发布 tool_start 事件"""
        for tool_call in getattr(context, "tool_calls", []):
            event = RuntimeEvent(
                type="tool_start",
                trace_id=getattr(context, "trace_id", ""),
                data=tool_call,
            )
            self._publish(event)

    async def after_iteration(self, context: AgentHookContext) -> None:
        """迭代后发布 iteration_end 事件"""
        event = RuntimeEvent(
            type="iteration_end",
            trace_id=getattr(context, "trace_id", ""),
        )
        self._publish(event)

    def _publish(self, event: RuntimeEvent) -> None:
        """发布事件到所有订阅者

        异常静默降级，不影响主流程。
        """
        for callback in self._subscribers:
            try:
                callback(event)
            except Exception:
                logger.exception("运行时事件订阅回调异常，已静默降级")
