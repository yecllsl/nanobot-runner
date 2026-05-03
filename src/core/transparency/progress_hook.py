# 进度显示Hook模块
# 显示工具调用开始和耗时

from __future__ import annotations

import logging
import time

from nanobot.agent.hook import AgentHook, AgentHookContext
from rich.console import Console

logger = logging.getLogger(__name__)


class ProgressDisplayHook(AgentHook):
    """进度显示钩子

    在before_execute_tools显示工具调用开始，
    在after_iteration显示工具调用耗时。
    """

    def __init__(self, console: Console | None = None) -> None:
        """初始化进度显示钩子

        Args:
            console: Rich控制台实例
        """
        super().__init__()
        self._console = console
        self._tool_start_times: dict[str, float] = {}

    async def before_execute_tools(self, context: AgentHookContext) -> None:
        """工具执行前记录开始时间并显示进度

        遍历context.tool_calls，记录time.monotonic()到_tool_start_times，
        显示格式: "🔧 正在调用: {tool_name} ..."

        Args:
            context: Hook上下文
        """
        for tc in context.tool_calls:
            tool_name = tc.name
            self._tool_start_times[tool_name] = time.monotonic()

            if self._console is not None:
                self._console.print(f"🔧 正在调用: {tool_name} ...")

            logger.debug(f"工具调用开始: {tool_name}")

    async def after_iteration(self, context: AgentHookContext) -> None:
        """迭代后计算耗时并显示完成状态

        计算耗时并清除_tool_start_times条目，
        显示格式: "✅ {tool_name} 完成，耗时 {elapsed}s"

        Args:
            context: Hook上下文
        """
        current_time = time.monotonic()
        completed_tools: list[str] = []

        # 获取当前迭代中调用的工具
        for tc in context.tool_calls:
            tool_name = tc.name
            if tool_name in self._tool_start_times:
                start_time = self._tool_start_times[tool_name]
                elapsed = current_time - start_time

                if self._console is not None:
                    self._console.print(f"✅ {tool_name} 完成，耗时 {elapsed:.2f}s")

                logger.debug(f"工具调用完成: {tool_name}, 耗时={elapsed:.2f}s")
                completed_tools.append(tool_name)

        # 清除已完成的工具计时
        for tool_name in completed_tools:
            del self._tool_start_times[tool_name]

    def get_pending_tools(self) -> dict[str, float]:
        """获取正在进行的工具调用及其开始时间

        Returns:
            dict[str, float]: 工具名称到开始时间的映射
        """
        return self._tool_start_times.copy()

    def reset(self) -> None:
        """重置进度显示状态"""
        self._tool_start_times.clear()
