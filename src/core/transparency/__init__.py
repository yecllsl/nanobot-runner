# 透明化模块
# 提供AI决策透明化、可观测性、追踪日志等能力

from typing import Any

from nanobot.agent.hook import AgentHook

from src.core.transparency.error_classifier import (
    ErrorCategory,
    ErrorClassifier,
    FriendlyError,
)
from src.core.transparency.error_handling_hook import ErrorHandlingHook
from src.core.transparency.hook_integration import HookIntegration, ObservabilityHook
from src.core.transparency.models import (
    AIDecision,
    DataSource,
    DataSourceType,
    DecisionExplanation,
    DecisionPath,
    DecisionStep,
    DecisionType,
    DetailLevel,
    LogEntry,
    LogFilters,
    ObservabilityMetrics,
    TraceEvent,
    TraceReport,
    TraceStatus,
    TransparencySettings,
)
from src.core.transparency.observability_manager import ObservabilityManager
from src.core.transparency.progress_hook import ProgressDisplayHook
from src.core.transparency.streaming_hook import StreamingHook
from src.core.transparency.trace_logger import TraceLogger
from src.core.transparency.transparency_display import TransparencyDisplay
from src.core.transparency.transparency_engine import TransparencyEngine

__all__ = [
    "AIDecision",
    "DataSource",
    "DataSourceType",
    "DecisionExplanation",
    "DecisionPath",
    "DecisionStep",
    "DecisionType",
    "DetailLevel",
    "ErrorCategory",
    "ErrorClassifier",
    "ErrorHandlingHook",
    "FriendlyError",
    "HookIntegration",
    "LogEntry",
    "LogFilters",
    "ObservabilityHook",
    "ObservabilityManager",
    "ObservabilityMetrics",
    "ProgressDisplayHook",
    "StreamingHook",
    "TraceEvent",
    "TraceLogger",
    "TraceReport",
    "TraceStatus",
    "TransparencyDisplay",
    "TransparencyEngine",
    "TransparencySettings",
]


def create_composite_hook(
    console: Any | None = None,
    bus: Any | None = None,
    observability_manager: ObservabilityManager | None = None,
    engine: TransparencyEngine | None = None,
    channel: str | None = None,
    chat_id: str | None = None,
    verbose: bool = False,
) -> list[AgentHook]:
    """创建组合Hook列表

    工厂函数，统一创建并注册所有Hook。
    Hook注册顺序: StreamingHook -> ErrorHandlingHook -> ProgressDisplayHook -> ObservabilityHook

    Args:
        console: Rich控制台实例
        bus: 消息总线实例
        observability_manager: 可观测性管理器
        engine: 透明化引擎
        channel: 通道名称
        chat_id: 聊天ID
        verbose: 是否显示详细错误信息

    Returns:
        list[AgentHook]: Hook实例列表
    """
    hooks: list[AgentHook] = []

    # 1. StreamingHook - 流式输出
    hooks.append(
        StreamingHook(
            console=console,
            bus=bus,
            channel=channel,
            chat_id=chat_id,
        )
    )

    # 2. ErrorHandlingHook - 错误处理
    hooks.append(
        ErrorHandlingHook(
            console=console,
            observability_manager=observability_manager,
            verbose=verbose,
        )
    )

    # 3. ProgressDisplayHook - 进度显示
    hooks.append(ProgressDisplayHook(console=console))

    # 4. ObservabilityHook - 可观测性
    if observability_manager is not None:
        hooks.append(
            ObservabilityHook(
                manager=observability_manager,
                engine=engine,
            )
        )

    return hooks
