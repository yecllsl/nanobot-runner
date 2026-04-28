# 诊断与偏好数据模型
# 定义自我诊断、建议验证、执行追踪等核心数据结构

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class DiagnosisSeverity(Enum):
    """诊断严重程度"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class DiagnosisCategory(Enum):
    """诊断类别"""

    SUGGESTION_QUALITY = "suggestion_quality"
    PARAMETER_VALIDITY = "parameter_validity"
    EXECUTION_HEALTH = "execution_health"
    MEMORY_CONSISTENCY = "memory_consistency"
    TOOL_RELIABILITY = "tool_reliability"


class ValidationStatus(Enum):
    """验证状态"""

    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class SuggestionContext:
    """建议上下文（不可变数据类）

    记录AI建议生成时的上下文信息，用于验证和诊断。

    Attributes:
        user_query: 用户原始查询
        suggestion_text: AI生成的建议文本
        tools_used: 使用的工具列表
        memory_referenced: 引用的记忆内容摘要
        timestamp: 建议生成时间
        session_key: 会话标识
    """

    user_query: str
    suggestion_text: str
    tools_used: list[str] = field(default_factory=list)
    memory_referenced: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    session_key: str = ""


@dataclass(frozen=True)
class ValidationResult:
    """验证结果（不可变数据类）

    单个验证规则的检查结果。

    Attributes:
        rule_name: 验证规则名称
        status: 验证状态
        message: 验证消息
        severity: 严重程度
        details: 详细信息
        suggestion_fix: 修复建议
    """

    rule_name: str
    status: ValidationStatus
    message: str
    severity: DiagnosisSeverity = DiagnosisSeverity.INFO
    details: dict[str, Any] = field(default_factory=dict)
    suggestion_fix: str = ""


@dataclass(frozen=True)
class DiagnosisReport:
    """诊断报告（不可变数据类）

    一次完整诊断的结果汇总。

    Attributes:
        id: 诊断报告唯一标识
        category: 诊断类别
        results: 验证结果列表
        summary: 诊断摘要
        overall_status: 整体状态
        timestamp: 诊断时间
        context: 关联的建议上下文
    """

    id: str
    category: DiagnosisCategory
    results: list[ValidationResult] = field(default_factory=list)
    summary: str = ""
    overall_status: ValidationStatus = ValidationStatus.PASS
    timestamp: datetime = field(default_factory=datetime.now)
    context: SuggestionContext | None = None

    @property
    def has_errors(self) -> bool:
        """是否存在错误级别的诊断结果"""
        return any(
            r.status == ValidationStatus.FAIL or r.severity == DiagnosisSeverity.ERROR
            for r in self.results
        )

    @property
    def has_warnings(self) -> bool:
        """是否存在警告级别的诊断结果"""
        return any(r.severity == DiagnosisSeverity.WARNING for r in self.results)

    @property
    def pass_count(self) -> int:
        """通过的验证数量"""
        return sum(1 for r in self.results if r.status == ValidationStatus.PASS)

    @property
    def fail_count(self) -> int:
        """失败的验证数量"""
        return sum(1 for r in self.results if r.status == ValidationStatus.FAIL)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "category": self.category.value,
            "results": [
                {
                    "rule_name": r.rule_name,
                    "status": r.status.value,
                    "message": r.message,
                    "severity": r.severity.value,
                    "details": r.details,
                    "suggestion_fix": r.suggestion_fix,
                }
                for r in self.results
            ],
            "summary": self.summary,
            "overall_status": self.overall_status.value,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass(frozen=True)
class ExecutionRecord:
    """执行记录（不可变数据类）

    记录一次工具或建议的执行情况，用于追踪和诊断。

    Attributes:
        id: 执行记录唯一标识
        execution_type: 执行类型（tool_call/suggestion/advice）
        target: 执行目标（工具名/建议ID）
        success: 是否成功
        duration_ms: 执行耗时（毫秒）
        error_message: 错误信息
        timestamp: 执行时间
        session_key: 会话标识
        input_data: 输入数据摘要
        output_data: 输出数据摘要
    """

    id: str
    execution_type: str
    target: str
    success: bool
    duration_ms: int = 0
    error_message: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)
    session_key: str = ""
    input_data: dict[str, Any] = field(default_factory=dict)
    output_data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "execution_type": self.execution_type,
            "target": self.target,
            "success": self.success,
            "duration_ms": self.duration_ms,
            "error_message": self.error_message,
            "timestamp": self.timestamp.isoformat(),
            "session_key": self.session_key,
        }
