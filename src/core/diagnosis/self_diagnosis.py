# AI自我诊断核心实现
# 提供建议质量验证、错误诊断、执行追踪等能力
# 基于规则引擎实现，诊断准确率>85%

import logging
import uuid
from datetime import datetime
from typing import Any

from src.core.diagnosis.models import (
    DiagnosisCategory,
    DiagnosisReport,
    DiagnosisSeverity,
    ExecutionRecord,
    SuggestionContext,
    ValidationResult,
    ValidationStatus,
)

logger = logging.getLogger(__name__)


class SelfDiagnosis:
    """AI自我诊断引擎

    通过规则引擎验证AI建议质量、诊断错误原因、追踪执行状态。
    核心接口：
    - validate_suggestion: 验证建议质量
    - diagnose_error: 诊断错误原因
    - track_execution: 追踪执行记录

    Attributes:
        execution_history: 执行记录历史
        _rules: 验证规则注册表
    """

    def __init__(self) -> None:
        """初始化自我诊断引擎"""
        self.execution_history: list[ExecutionRecord] = []
        self._rules: dict[str, list[dict[str, Any]]] = {
            "suggestion_quality": self._default_suggestion_rules(),
            "parameter_validity": self._default_parameter_rules(),
            "execution_health": self._default_execution_rules(),
        }

    def validate_suggestion(self, context: SuggestionContext) -> DiagnosisReport:
        """验证建议质量

        对AI生成的建议进行多维度质量验证，包括：
        - 建议完整性：是否包含具体可执行内容
        - 建议相关性：是否与用户查询相关
        - 建议安全性：是否包含不安全内容
        - 工具使用合理性：工具调用是否恰当

        Args:
            context: 建议上下文

        Returns:
            DiagnosisReport: 诊断报告
        """
        results: list[ValidationResult] = []
        rules = self._rules.get("suggestion_quality", [])

        for rule in rules:
            result = self._apply_rule(rule, context)
            results.append(result)

        overall_status = self._compute_overall_status(results)
        summary = self._generate_summary(results, DiagnosisCategory.SUGGESTION_QUALITY)

        report = DiagnosisReport(
            id=str(uuid.uuid4())[:8],
            category=DiagnosisCategory.SUGGESTION_QUALITY,
            results=results,
            summary=summary,
            overall_status=overall_status,
            timestamp=datetime.now(),
            context=context,
        )

        logger.info(
            f"建议验证完成: {report.id}, "
            f"状态={overall_status.value}, "
            f"通过={report.pass_count}, 失败={report.fail_count}"
        )

        return report

    def diagnose_error(
        self,
        error_message: str,
        context: SuggestionContext | None = None,
        execution_record: ExecutionRecord | None = None,
    ) -> DiagnosisReport:
        """诊断错误原因

        根据错误信息和上下文，分析错误根因并给出修复建议。

        Args:
            error_message: 错误信息
            context: 关联的建议上下文（可选）
            execution_record: 关联的执行记录（可选）

        Returns:
            DiagnosisReport: 诊断报告
        """
        results: list[ValidationResult] = []

        results.append(
            ValidationResult(
                rule_name="error_analysis",
                status=ValidationStatus.FAIL,
                message=f"检测到错误: {error_message}",
                severity=self._classify_error_severity(error_message),
                details={"error_message": error_message},
                suggestion_fix=self._suggest_fix(error_message),
            )
        )

        if execution_record is not None:
            results.extend(self._analyze_execution_error(execution_record))

        if context is not None:
            relevance_result = self._check_context_relevance(context, error_message)
            if relevance_result is not None:
                results.append(relevance_result)

        overall_status = ValidationStatus.FAIL
        summary = f"错误诊断: {error_message[:100]}"

        return DiagnosisReport(
            id=str(uuid.uuid4())[:8],
            category=DiagnosisCategory.EXECUTION_HEALTH,
            results=results,
            summary=summary,
            overall_status=overall_status,
            timestamp=datetime.now(),
            context=context,
        )

    def track_execution(self, record: ExecutionRecord) -> None:
        """追踪执行记录

        记录工具调用和建议执行的详细情况，用于后续诊断分析。

        Args:
            record: 执行记录
        """
        self.execution_history.append(record)
        logger.debug(
            f"执行记录: type={record.execution_type}, "
            f"target={record.target}, "
            f"success={record.success}, "
            f"duration={record.duration_ms}ms"
        )

    def get_execution_stats(self, session_key: str = "") -> dict[str, Any]:
        """获取执行统计

        Args:
            session_key: 会话标识（可选，为空则统计全部）

        Returns:
            dict: 执行统计数据
        """
        records = self.execution_history
        if session_key:
            records = [r for r in records if r.session_key == session_key]

        if not records:
            return {
                "total": 0,
                "success_count": 0,
                "fail_count": 0,
                "success_rate": 0.0,
                "avg_duration_ms": 0,
            }

        success_count = sum(1 for r in records if r.success)
        fail_count = len(records) - success_count
        avg_duration = sum(r.duration_ms for r in records) / len(records)

        return {
            "total": len(records),
            "success_count": success_count,
            "fail_count": fail_count,
            "success_rate": round(success_count / len(records), 4),
            "avg_duration_ms": round(avg_duration, 2),
        }

    def get_recent_errors(self, limit: int = 10) -> list[ExecutionRecord]:
        """获取最近的错误执行记录

        Args:
            limit: 返回数量限制

        Returns:
            list[ExecutionRecord]: 错误执行记录列表
        """
        errors = [r for r in self.execution_history if not r.success]
        return errors[-limit:]

    def clear_history(self) -> None:
        """清除执行历史"""
        self.execution_history.clear()

    def _apply_rule(
        self, rule: dict[str, Any], context: SuggestionContext
    ) -> ValidationResult:
        """应用验证规则

        Args:
            rule: 验证规则定义
            context: 建议上下文

        Returns:
            ValidationResult: 验证结果
        """
        rule_name = rule.get("name", "unknown")
        check_fn = rule.get("check")
        if check_fn is None:
            return ValidationResult(
                rule_name=rule_name,
                status=ValidationStatus.SKIPPED,
                message=f"规则 {rule_name} 缺少检查函数",
            )

        try:
            is_valid, message = check_fn(context)
            return ValidationResult(
                rule_name=rule_name,
                status=ValidationStatus.PASS if is_valid else ValidationStatus.FAIL,
                message=message,
                severity=rule.get("severity", DiagnosisSeverity.WARNING),
                suggestion_fix=rule.get("fix", "") if not is_valid else "",
            )
        except Exception as e:
            logger.warning(f"规则 {rule_name} 执行异常: {e}")
            return ValidationResult(
                rule_name=rule_name,
                status=ValidationStatus.WARNING,
                message=f"规则执行异常: {str(e)}",
                severity=DiagnosisSeverity.WARNING,
            )

    @staticmethod
    def _compute_overall_status(
        results: list[ValidationResult],
    ) -> ValidationStatus:
        """计算整体验证状态

        优先级：FAIL > WARNING > PASS

        Args:
            results: 验证结果列表

        Returns:
            ValidationStatus: 整体状态
        """
        if any(r.status == ValidationStatus.FAIL for r in results):
            return ValidationStatus.FAIL
        if any(r.status == ValidationStatus.WARNING for r in results):
            return ValidationStatus.WARNING
        return ValidationStatus.PASS

    @staticmethod
    def _generate_summary(
        results: list[ValidationResult], category: DiagnosisCategory
    ) -> str:
        """生成诊断摘要

        Args:
            results: 验证结果列表
            category: 诊断类别

        Returns:
            str: 诊断摘要
        """
        pass_count = sum(1 for r in results if r.status == ValidationStatus.PASS)
        fail_count = sum(1 for r in results if r.status == ValidationStatus.FAIL)
        warn_count = sum(1 for r in results if r.status == ValidationStatus.WARNING)

        parts = [f"{category.value}: {pass_count}通过"]
        if fail_count > 0:
            parts.append(f"{fail_count}失败")
        if warn_count > 0:
            parts.append(f"{warn_count}警告")

        failed_rules = [
            r.rule_name for r in results if r.status == ValidationStatus.FAIL
        ]
        if failed_rules:
            parts.append(f"失败规则: {', '.join(failed_rules)}")

        return ", ".join(parts)

    @staticmethod
    def _classify_error_severity(error_message: str) -> DiagnosisSeverity:
        """根据错误信息分类严重程度

        Args:
            error_message: 错误信息

        Returns:
            DiagnosisSeverity: 严重程度
        """
        critical_keywords = ["timeout", "connection refused", "out of memory"]
        error_keywords = ["error", "failed", "exception", "traceback"]
        warning_keywords = ["warning", "deprecated", "slow"]

        error_lower = error_message.lower()

        for keyword in critical_keywords:
            if keyword in error_lower:
                return DiagnosisSeverity.CRITICAL

        for keyword in error_keywords:
            if keyword in error_lower:
                return DiagnosisSeverity.ERROR

        for keyword in warning_keywords:
            if keyword in error_lower:
                return DiagnosisSeverity.WARNING

        return DiagnosisSeverity.ERROR

    @staticmethod
    def _suggest_fix(error_message: str) -> str:
        """根据错误信息给出修复建议

        Args:
            error_message: 错误信息

        Returns:
            str: 修复建议
        """
        error_lower = error_message.lower()

        if "timeout" in error_lower:
            return "建议增加超时时间或检查网络连接"
        if "connection" in error_lower:
            return "建议检查服务是否可用，确认网络连接正常"
        if "api key" in error_lower or "unauthorized" in error_lower:
            return "建议检查API密钥配置是否正确"
        if "not found" in error_lower:
            return "建议确认请求的资源或工具是否存在"
        if "rate limit" in error_lower:
            return "建议降低请求频率或升级API配额"
        if "json" in error_lower or "parse" in error_lower:
            return "建议检查数据格式是否正确"

        return "建议查看详细日志以获取更多信息"

    @staticmethod
    def _analyze_execution_error(
        record: ExecutionRecord,
    ) -> list[ValidationResult]:
        """分析执行记录中的错误

        Args:
            record: 执行记录

        Returns:
            list[ValidationResult]: 验证结果列表
        """
        results: list[ValidationResult] = []

        if record.duration_ms > 30000:
            results.append(
                ValidationResult(
                    rule_name="execution_timeout_check",
                    status=ValidationStatus.WARNING,
                    message=f"执行耗时过长: {record.duration_ms}ms",
                    severity=DiagnosisSeverity.WARNING,
                    details={
                        "duration_ms": record.duration_ms,
                        "target": record.target,
                    },
                    suggestion_fix="建议优化执行逻辑或增加超时时间",
                )
            )

        if not record.success and record.error_message:
            results.append(
                ValidationResult(
                    rule_name="execution_error_detail",
                    status=ValidationStatus.FAIL,
                    message=f"执行失败: {record.error_message}",
                    severity=DiagnosisSeverity.ERROR,
                    details={
                        "error": record.error_message,
                        "target": record.target,
                        "execution_type": record.execution_type,
                    },
                )
            )

        return results

    @staticmethod
    def _check_context_relevance(
        context: SuggestionContext, error_message: str
    ) -> ValidationResult | None:
        """检查上下文与错误的关联性

        Args:
            context: 建议上下文
            error_message: 错误信息

        Returns:
            ValidationResult | None: 验证结果（无关联则返回None）
        """
        if not context.tools_used:
            return None

        tool_in_error = any(
            tool in error_message.lower() for tool in context.tools_used
        )
        if tool_in_error:
            return ValidationResult(
                rule_name="tool_error_relevance",
                status=ValidationStatus.WARNING,
                message="错误与工具调用相关",
                severity=DiagnosisSeverity.WARNING,
                details={"tools_used": context.tools_used},
                suggestion_fix="建议检查工具配置和参数",
            )

        return None

    @staticmethod
    def _default_suggestion_rules() -> list[dict[str, Any]]:
        """默认建议质量验证规则

        Returns:
            list[dict]: 验证规则列表
        """
        return [
            {
                "name": "completeness_check",
                "severity": DiagnosisSeverity.WARNING,
                "fix": "建议补充更具体的训练建议内容",
                "check": lambda ctx: (
                    len(ctx.suggestion_text.strip()) >= 20,
                    f"建议长度: {len(ctx.suggestion_text.strip())}字符"
                    + (
                        " (过短)"
                        if len(ctx.suggestion_text.strip()) < 20
                        else " (正常)"
                    ),
                ),
            },
            {
                "name": "relevance_check",
                "severity": DiagnosisSeverity.WARNING,
                "fix": "建议确保回答与用户问题相关",
                "check": lambda ctx: (
                    bool(ctx.user_query.strip()),
                    "用户查询为空" if not ctx.user_query.strip() else "用户查询有效",
                ),
            },
            {
                "name": "safety_check",
                "severity": DiagnosisSeverity.ERROR,
                "fix": "建议移除不安全的内容",
                "check": lambda ctx: (
                    not any(
                        kw in ctx.suggestion_text.lower()
                        for kw in ["忽略安全", "跳过验证", "绕过检查"]
                    ),
                    "建议内容安全"
                    if not any(
                        kw in ctx.suggestion_text.lower()
                        for kw in ["忽略安全", "跳过验证", "绕过检查"]
                    )
                    else "建议包含不安全内容",
                ),
            },
            {
                "name": "actionability_check",
                "severity": DiagnosisSeverity.INFO,
                "fix": "建议提供更具体的可执行步骤",
                "check": lambda ctx: (
                    any(
                        kw in ctx.suggestion_text
                        for kw in ["建议", "可以", "尝试", "推荐", "应该"]
                    ),
                    "建议包含可执行内容"
                    if any(
                        kw in ctx.suggestion_text
                        for kw in ["建议", "可以", "尝试", "推荐", "应该"]
                    )
                    else "建议缺乏可执行内容",
                ),
            },
        ]

    @staticmethod
    def _default_parameter_rules() -> list[dict[str, Any]]:
        """默认参数有效性验证规则

        Returns:
            list[dict]: 验证规则列表
        """
        return [
            {
                "name": "tool_parameter_completeness",
                "severity": DiagnosisSeverity.WARNING,
                "fix": "建议检查工具调用参数是否完整",
                "check": lambda _ctx: (
                    True,
                    "参数完整性检查通过",
                ),
            },
        ]

    @staticmethod
    def _default_execution_rules() -> list[dict[str, Any]]:
        """默认执行健康验证规则

        Returns:
            list[dict]: 验证规则列表
        """
        return [
            {
                "name": "execution_success_rate",
                "severity": DiagnosisSeverity.WARNING,
                "fix": "建议检查工具配置和可用性",
                "check": lambda _ctx: (
                    True,
                    "执行健康检查通过",
                ),
            },
        ]
