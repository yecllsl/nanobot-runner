# 透明化数据模型
# 定义AI决策透明化、可观测性、追踪日志等核心数据结构

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class DetailLevel(Enum):
    """展示详细程度"""

    BRIEF = "brief"
    DETAILED = "detailed"
    OFF = "off"


class DecisionType(Enum):
    """决策类型"""

    TRAINING_ADVICE = "training_advice"
    PLAN_ADJUSTMENT = "plan_adjustment"
    RECOVERY_SUGGESTION = "recovery_suggestion"
    WEATHER_ADVICE = "weather_advice"
    DATA_QUERY = "data_query"
    GENERAL = "general"


class DataSourceType(Enum):
    """数据来源类型"""

    TRAINING_DATA = "training_data"
    USER_PROFILE = "user_profile"
    EXTERNAL_TOOL = "external_tool"
    MEMORY = "memory"
    KNOWLEDGE_BASE = "knowledge_base"


class TraceStatus(Enum):
    """追踪状态"""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class AIDecision:
    """AI决策（不可变数据类）

    记录一次AI决策的完整信息，包括输入、输出、推理过程等。

    Attributes:
        id: 决策唯一标识
        decision_type: 决策类型
        input_data: 输入数据
        output_data: 输出数据
        reasoning: 推理过程描述
        confidence: 置信度（0.0-1.0）
        timestamp: 决策时间
        session_key: 会话标识
        tools_used: 使用的工具列表
        memory_referenced: 引用的记忆内容
        duration_ms: 决策耗时（毫秒）
    """

    id: str
    decision_type: DecisionType
    input_data: dict[str, Any] = field(default_factory=dict)
    output_data: dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""
    confidence: float = 0.5
    timestamp: datetime = field(default_factory=datetime.now)
    session_key: str = ""
    tools_used: list[str] = field(default_factory=list)
    memory_referenced: list[str] = field(default_factory=list)
    duration_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "decision_type": self.decision_type.value,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "session_key": self.session_key,
            "tools_used": self.tools_used,
            "memory_referenced": self.memory_referenced,
            "duration_ms": self.duration_ms,
        }


@dataclass(frozen=True)
class DataSource:
    """数据来源（不可变数据类）

    描述AI决策使用的数据来源信息。

    Attributes:
        type: 数据来源类型
        name: 来源名称
        description: 来源描述
        timestamp: 数据时间戳
        quality_score: 数据质量评分（0.0-1.0）
        details: 详细信息
    """

    type: DataSourceType
    name: str
    description: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    quality_score: float = 1.0
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "type": self.type.value,
            "name": self.name,
            "description": self.description,
            "timestamp": self.timestamp.isoformat(),
            "quality_score": self.quality_score,
            "details": self.details,
        }


@dataclass(frozen=True)
class DecisionStep:
    """决策步骤（不可变数据类）

    记录AI决策过程中的单个步骤。

    Attributes:
        name: 步骤名称
        description: 步骤描述
        input_data: 输入数据摘要
        output_data: 输出数据摘要
        duration_ms: 步骤耗时（毫秒）
        step_type: 步骤类型（reasoning/tool_call/memory_lookup）
    """

    name: str
    description: str
    input_data: dict[str, Any] = field(default_factory=dict)
    output_data: dict[str, Any] = field(default_factory=dict)
    duration_ms: int = 0
    step_type: str = "reasoning"

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "name": self.name,
            "description": self.description,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "duration_ms": self.duration_ms,
            "step_type": self.step_type,
        }


@dataclass(frozen=True)
class DecisionPath:
    """决策路径（不可变数据类）

    记录AI决策的完整路径，包含所有步骤。

    Attributes:
        steps: 决策步骤列表
        total_duration_ms: 总耗时（毫秒）
    """

    steps: list[DecisionStep] = field(default_factory=list)
    total_duration_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "steps": [s.to_dict() for s in self.steps],
            "total_duration_ms": self.total_duration_ms,
        }

    def to_mermaid(self) -> str:
        """生成Mermaid流程图

        Returns:
            str: Mermaid格式的流程图
        """
        if not self.steps:
            return "graph LR\n    A[开始] --> B[结束]"

        lines = ["graph LR"]
        for i, step in enumerate(self.steps):
            node_id = chr(65 + i)
            label = step.name.replace('"', "'")
            lines.append(f'    {node_id}["{label}"]')
            if i > 0:
                prev_id = chr(64 + i)
                lines.append(f"    {prev_id} --> {node_id}")

        return "\n".join(lines)


@dataclass(frozen=True)
class DecisionExplanation:
    """决策解释（不可变数据类）

    AI决策的完整解释，包含简洁版和详细版。

    Attributes:
        decision_id: 关联的决策ID
        brief_reasons: 简洁版关键理由（3-5条）
        detailed_analysis: 详细版完整分析
        data_sources: 数据来源列表
        decision_path: 决策路径
        confidence_score: 置信度评分
    """

    decision_id: str
    brief_reasons: list[str] = field(default_factory=list)
    detailed_analysis: str = ""
    data_sources: list[DataSource] = field(default_factory=list)
    decision_path: DecisionPath = field(default_factory=DecisionPath)
    confidence_score: float = 0.5

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "decision_id": self.decision_id,
            "brief_reasons": self.brief_reasons,
            "detailed_analysis": self.detailed_analysis,
            "data_sources": [ds.to_dict() for ds in self.data_sources],
            "decision_path": self.decision_path.to_dict(),
            "confidence_score": self.confidence_score,
        }


@dataclass(frozen=True)
class TraceEvent:
    """追踪事件（不可变数据类）

    记录追踪过程中的单个事件。

    Attributes:
        timestamp: 事件时间戳
        name: 事件名称
        data: 事件数据
    """

    timestamp: datetime = field(default_factory=datetime.now)
    name: str = ""
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "name": self.name,
            "data": self.data,
        }


@dataclass(frozen=True)
class TraceReport:
    """追踪报告（不可变数据类）

    一次完整追踪的结果报告。

    Attributes:
        trace_id: 追踪唯一标识
        operation_name: 操作名称
        start_time: 开始时间
        end_time: 结束时间
        duration_ms: 持续时间（毫秒）
        status: 追踪状态
        events: 事件列表
        tags: 标签
    """

    trace_id: str
    operation_name: str
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime = field(default_factory=datetime.now)
    duration_ms: int = 0
    status: TraceStatus = TraceStatus.COMPLETED
    events: list[TraceEvent] = field(default_factory=list)
    tags: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "trace_id": self.trace_id,
            "operation_name": self.operation_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration_ms": self.duration_ms,
            "status": self.status.value,
            "events": [e.to_dict() for e in self.events],
            "tags": self.tags,
        }


@dataclass(frozen=True)
class ObservabilityMetrics:
    """可观测性指标（不可变数据类）

    汇总可观测性统计数据。

    Attributes:
        total_traces: 总追踪数
        successful_traces: 成功追踪数
        failed_traces: 失败追踪数
        avg_duration_ms: 平均耗时（毫秒）
        error_rate: 错误率
        tool_call_count: 工具调用次数
        tool_success_rate: 工具调用成功率
    """

    total_traces: int = 0
    successful_traces: int = 0
    failed_traces: int = 0
    avg_duration_ms: float = 0.0
    error_rate: float = 0.0
    tool_call_count: int = 0
    tool_success_rate: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "total_traces": self.total_traces,
            "successful_traces": self.successful_traces,
            "failed_traces": self.failed_traces,
            "avg_duration_ms": round(self.avg_duration_ms, 2),
            "error_rate": round(self.error_rate, 4),
            "tool_call_count": self.tool_call_count,
            "tool_success_rate": round(self.tool_success_rate, 4),
        }


@dataclass(frozen=True)
class LogFilters:
    """日志过滤条件（不可变数据类）

    Attributes:
        start_time: 开始时间（可选）
        end_time: 结束时间（可选）
        decision_type: 决策类型（可选）
        tool_id: 工具ID（可选）
        status: 状态过滤（可选）
        session_key: 会话标识（可选）
        limit: 返回数量限制
    """

    start_time: datetime | None = None
    end_time: datetime | None = None
    decision_type: str | None = None
    tool_id: str | None = None
    status: str | None = None
    session_key: str | None = None
    limit: int = 100


@dataclass(frozen=True)
class LogEntry:
    """日志条目（不可变数据类）

    Attributes:
        timestamp: 日志时间戳
        level: 日志级别
        message: 日志消息
        context: 上下文数据
        trace_id: 关联的追踪ID
        entry_type: 条目类型（decision/tool_call/trace）
    """

    timestamp: datetime = field(default_factory=datetime.now)
    level: str = "INFO"
    message: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    trace_id: str | None = None
    entry_type: str = "decision"

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level,
            "message": self.message,
            "context": self.context,
            "trace_id": self.trace_id,
            "entry_type": self.entry_type,
        }


@dataclass(frozen=True)
class TransparencySettings:
    """透明度设置（不可变数据类）

    用户可配置的透明度参数。

    Attributes:
        detail_level: 展示详细程度
        show_data_sources: 是否展示数据来源
        show_decision_path: 是否展示决策路径
        show_confidence: 是否展示置信度
        auto_explain: 是否自动解释决策
    """

    detail_level: DetailLevel = DetailLevel.BRIEF
    show_data_sources: bool = True
    show_decision_path: bool = False
    show_confidence: bool = True
    auto_explain: bool = True

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "detail_level": self.detail_level.value,
            "show_data_sources": self.show_data_sources,
            "show_decision_path": self.show_decision_path,
            "show_confidence": self.show_confidence,
            "auto_explain": self.auto_explain,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TransparencySettings":
        """从字典创建实例

        Args:
            data: 设置字典

        Returns:
            TransparencySettings: 透明度设置实例
        """
        detail_str = data.get("detail_level", "brief")
        try:
            detail_level = DetailLevel(detail_str)
        except ValueError:
            detail_level = DetailLevel.BRIEF

        return cls(
            detail_level=detail_level,
            show_data_sources=data.get("show_data_sources", True),
            show_decision_path=data.get("show_decision_path", False),
            show_confidence=data.get("show_confidence", True),
            auto_explain=data.get("auto_explain", True),
        )

    @classmethod
    def default(cls) -> "TransparencySettings":
        """创建默认设置

        Returns:
            TransparencySettings: 默认设置实例
        """
        return cls()
