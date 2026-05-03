# 可观测性Hook集成
# 基于nanobot-ai AgentHook实现决策追踪和工具调用监控

import logging
from datetime import datetime
from typing import Any

from nanobot.agent.hook import AgentHook, AgentHookContext

from src.core.transparency.models import (
    AIDecision,
    DecisionType,
)
from src.core.transparency.observability_manager import ObservabilityManager
from src.core.transparency.transparency_engine import TransparencyEngine

logger = logging.getLogger(__name__)


class ObservabilityHook(AgentHook):
    """可观测性钩子

    继承nanobot-ai的AgentHook，在Agent迭代和工具调用时
    自动记录追踪数据，实现全链路可观测性。
    """

    def __init__(
        self,
        manager: ObservabilityManager,
        engine: TransparencyEngine | None = None,
    ) -> None:
        """初始化可观测性钩子

        Args:
            manager: 可观测性管理器
            engine: 透明化引擎（可选）
        """
        super().__init__()
        self.manager = manager
        self.engine = engine
        self._current_trace_id: str | None = None
        self._iteration_count: int = 0
        self._tools_in_iteration: list[str] = []

    async def before_iteration(self, context: AgentHookContext) -> None:
        """迭代前记录

        在Agent每次LLM调用前触发，开始新的追踪。

        Args:
            context: Hook上下文
        """
        self._iteration_count += 1
        self._tools_in_iteration = []

        if self._current_trace_id is None:
            self._current_trace_id = self.manager.start_trace(
                operation_name="agent_iteration",
                tags={"iteration": str(self._iteration_count)},
            )

        self.manager.record_event(
            self._current_trace_id,
            "iteration_start",
            {"iteration": self._iteration_count},
        )

        logger.debug(
            f"迭代开始: trace_id={self._current_trace_id}, "
            f"iteration={self._iteration_count}"
        )

    async def on_stream(self, context: AgentHookContext, delta: str) -> None:
        """流式输出时触发

        记录流式事件到ObservabilityManager，事件类型为stream_delta，
        包含delta内容和迭代序号。

        Args:
            context: Hook上下文
            delta: 流式输出片段
        """
        if self._current_trace_id is not None:
            self.manager.record_event(
                self._current_trace_id,
                "stream_delta",
                {
                    "iteration": self._iteration_count,
                    "delta_length": len(delta),
                    "delta_preview": delta[:100] if delta else "",
                },
            )

    async def before_execute_tools(self, context: AgentHookContext) -> None:
        """工具执行前记录

        在Agent执行工具调用前触发，记录工具调用信息。

        Args:
            context: Hook上下文
        """
        if self._current_trace_id is None:
            return

        for tc in context.tool_calls:
            self._tools_in_iteration.append(tc.name)
            self.manager.record_event(
                self._current_trace_id,
                "tool_call",
                {
                    "tool_name": tc.name,
                    "arguments": str(tc.arguments)[:500],
                    "success": True,
                },
            )

        logger.debug(
            f"工具调用: trace_id={self._current_trace_id}, "
            f"tools={[tc.name for tc in context.tool_calls]}"
        )

    async def after_iteration(self, context: AgentHookContext) -> None:
        """迭代后记录

        在Agent每次迭代完成后触发。

        Args:
            context: Hook上下文
        """
        if self._current_trace_id is not None:
            self.manager.record_event(
                self._current_trace_id,
                "iteration_end",
                {"iteration": self._iteration_count},
            )

        logger.debug(
            f"迭代结束: trace_id={self._current_trace_id}, "
            f"iteration={self._iteration_count}"
        )

    async def finalize_content(self, context: AgentHookContext, content: str) -> str:
        """最终输出处理

        在Agent生成最终回复后触发，结束追踪并记录决策。

        Args:
            context: Hook上下文
            content: 最终内容

        Returns:
            str: 处理后的内容（原样返回）
        """
        if self._current_trace_id is not None:
            self.manager.record_event(
                self._current_trace_id,
                "finalize",
                {"content_length": len(content)},
            )

            self.manager.end_trace(self._current_trace_id, status="completed")

            if self.engine is not None:
                decision = AIDecision(
                    id=self._current_trace_id,
                    decision_type=DecisionType.GENERAL,
                    reasoning=content[:500] if content else "",
                    confidence=0.7,
                    timestamp=datetime.now(),
                    tools_used=self._tools_in_iteration,
                )
                self.engine.generate_explanation(decision)

            self._current_trace_id = None

        return content

    def get_iteration_count(self) -> int:
        """获取迭代计数

        Returns:
            int: 迭代次数
        """
        return self._iteration_count

    def get_tools_used(self) -> list[str]:
        """获取使用的工具列表

        Returns:
            list[str]: 工具名称列表
        """
        return self._tools_in_iteration.copy()

    def reset(self) -> None:
        """重置钩子状态"""
        self._iteration_count = 0
        self._tools_in_iteration = []
        if self._current_trace_id is not None:
            self.manager.end_trace(self._current_trace_id, status="failed")
            self._current_trace_id = None


class HookIntegration:
    """Hook系统集成

    提供Hook注册和管理功能，支持决策前/后钩子和工具调用钩子。
    """

    def __init__(
        self,
        manager: ObservabilityManager,
        engine: TransparencyEngine | None = None,
    ) -> None:
        """初始化Hook集成

        Args:
            manager: 可观测性管理器
            engine: 透明化引擎（可选）
        """
        self.manager = manager
        self.engine = engine
        self._hooks: list[ObservabilityHook] = []

    def create_hook(self) -> ObservabilityHook:
        """创建可观测性钩子

        Returns:
            ObservabilityHook: 钩子实例
        """
        hook = ObservabilityHook(
            manager=self.manager,
            engine=self.engine,
        )
        self._hooks.append(hook)
        return hook

    def register_pre_decision_hook(
        self,
        hook_func: Any,
    ) -> None:
        """注册决策前钩子

        Args:
            hook_func: 钩子函数，接收AIDecision参数
        """
        self._pre_decision_hooks.append(hook_func)

    def register_post_decision_hook(
        self,
        hook_func: Any,
    ) -> None:
        """注册决策后钩子

        Args:
            hook_func: 钩子函数，接收AIDecision和DecisionExplanation参数
        """
        self._post_decision_hooks.append(hook_func)

    def register_tool_invocation_hook(
        self,
        hook_func: Any,
    ) -> None:
        """注册工具调用钩子

        Args:
            hook_func: 钩子函数，接收tool_id、params、result参数
        """
        self._tool_invocation_hooks.append(hook_func)

    def get_hooks(self) -> list[ObservabilityHook]:
        """获取所有已创建的钩子

        Returns:
            list[ObservabilityHook]: 钩子列表
        """
        return self._hooks.copy()

    @property
    def _pre_decision_hooks(self) -> list[Any]:
        if not hasattr(self, "__pre_decision_hooks"):
            self.__pre_decision_hooks: list[Any] = []
        return self.__pre_decision_hooks

    @property
    def _post_decision_hooks(self) -> list[Any]:
        if not hasattr(self, "__post_decision_hooks"):
            self.__post_decision_hooks: list[Any] = []
        return self.__post_decision_hooks

    @property
    def _tool_invocation_hooks(self) -> list[Any]:
        if not hasattr(self, "__tool_invocation_hooks"):
            self.__tool_invocation_hooks: list[Any] = []
        return self.__tool_invocation_hooks
