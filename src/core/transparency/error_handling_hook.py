# 错误处理Hook模块
# 捕获工具执行错误，调用ErrorClassifier分类并输出友好提示

from __future__ import annotations

import logging
import traceback

from nanobot.agent.hook import AgentHook, AgentHookContext
from rich.console import Console

from src.core.transparency.error_classifier import ErrorClassifier, FriendlyError
from src.core.transparency.observability_manager import ObservabilityManager

logger = logging.getLogger(__name__)


class ErrorHandlingHook(AgentHook):
    """错误处理钩子

    继承nanobot-ai的AgentHook，通过after_iteration捕获工具执行错误，
    调用ErrorClassifier分类并输出友好提示。
    """

    def __init__(
        self,
        console: Console | None = None,
        observability_manager: ObservabilityManager | None = None,
        verbose: bool = False,
    ) -> None:
        """初始化错误处理钩子

        Args:
            console: Rich控制台实例
            observability_manager: 可观测性管理器
            verbose: 是否显示详细堆栈信息
        """
        super().__init__()
        self._console = console
        self._observability_manager = observability_manager
        self._verbose = verbose
        self._last_error: FriendlyError | None = None

    async def after_iteration(self, context: AgentHookContext) -> None:
        """迭代后触发错误处理

        检查context.error非空时触发错误处理，
        调用ErrorClassifier分类并输出友好提示。
        不吞没异常，保留原始异常信息。

        Args:
            context: Hook上下文
        """
        if not context.error:
            return

        original_error = context.error
        friendly_error = ErrorClassifier.classify(original_error)
        self._last_error = friendly_error

        # 记录错误上下文到ObservabilityManager
        if self._observability_manager is not None:
            try:
                trace_id = getattr(context, "trace_id", None) or "error_trace"
                self._observability_manager.record_event(
                    trace_id,
                    "error_occurred",
                    {
                        "category": friendly_error.category.value,
                        "message": friendly_error.friendly_message,
                        "original_error": str(original_error),
                    },
                )
            except Exception as e:
                logger.warning(f"记录错误到ObservabilityManager失败: {e}")

        # 输出错误信息
        if self._console is not None:
            self._console.print()
            self._console.print(
                f"[bold red]⚠️ {friendly_error.friendly_message}[/bold red]"
            )

            if self._verbose:
                self._console.print("[dim]详细错误信息:[/dim]")
                tb = traceback.format_exception(
                    type(original_error),
                    original_error,
                    original_error.__traceback__,
                )
                self._console.print("".join(tb))
            else:
                self._console.print(
                    f"[yellow]💡 {friendly_error.recovery_suggestion}[/yellow]"
                )

            self._console.print()

        logger.warning(
            f"错误处理: category={friendly_error.category.value}, "
            f"message={friendly_error.friendly_message}, "
            f"original={original_error}"
        )

    def get_last_error(self) -> FriendlyError | None:
        """获取最后一次处理的错误

        Returns:
            FriendlyError | None: 最后一次友好错误信息
        """
        return self._last_error

    def reset(self) -> None:
        """重置错误处理状态"""
        self._last_error = None
