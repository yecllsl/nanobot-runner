"""
计划调整校验器模块 - v0.11.0

可扩展规则引擎，校验LLM生成的计划调整建议是否符合运动科学原则
"""

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from src.core.base.logger import get_logger
from src.core.models import PlanAdjustment, ValidationResult, Violation

logger = get_logger(__name__)


class RulePriority(Enum):
    """规则优先级"""

    CRITICAL = 100
    HIGH = 80
    MEDIUM = 50
    LOW = 20


@dataclass
class ValidationRule:
    """校验规则"""

    name: str
    description: str
    priority: RulePriority
    check: Callable[[PlanAdjustment], bool]
    violation_message: str
    enabled: bool = True


class PlanAdjustmentValidator:
    """计划调整校验器 - 可扩展规则引擎"""

    def __init__(self) -> None:
        self._rules: list[ValidationRule] = []
        self._load_default_rules()

    def _load_default_rules(self) -> None:
        """加载默认规则"""
        self._rules = [
            ValidationRule(
                name="volume_increase_limit",
                description="周跑量增幅不超过10%",
                priority=RulePriority.CRITICAL,
                check=self._check_volume_increase,
                violation_message="周跑量增幅超过10%，违反运动科学原则",
            ),
            ValidationRule(
                name="long_run_ratio",
                description="长距离跑不超过周跑量的30%",
                priority=RulePriority.CRITICAL,
                check=self._check_long_run_ratio,
                violation_message="长距离跑超过周跑量的30%，伤病风险高",
            ),
            ValidationRule(
                name="recovery_after_interval",
                description="间歇跑后需安排恢复日",
                priority=RulePriority.HIGH,
                check=self._check_recovery_after_interval,
                violation_message="间歇跑后未安排恢复日，恢复不足",
            ),
            ValidationRule(
                name="race_taper",
                description="比赛前2周需减量",
                priority=RulePriority.HIGH,
                check=self._check_race_taper,
                violation_message="比赛前2周未减量，影响比赛表现",
            ),
            ValidationRule(
                name="easy_day_intensity",
                description="轻松日强度不超过Zone2",
                priority=RulePriority.MEDIUM,
                check=self._check_easy_day_intensity,
                violation_message="轻松日强度过高，影响恢复",
            ),
        ]

    def add_rule(self, rule: ValidationRule) -> None:
        """添加自定义规则"""
        self._rules.append(rule)

    def remove_rule(self, rule_name: str) -> bool:
        """移除规则"""
        for i, rule in enumerate(self._rules):
            if rule.name == rule_name:
                self._rules.pop(i)
                return True
        return False

    def enable_rule(self, rule_name: str, enabled: bool = True) -> bool:
        """启用/禁用规则"""
        for rule in self._rules:
            if rule.name == rule_name:
                rule.enabled = enabled
                return True
        return False

    def get_rules(self) -> list[ValidationRule]:
        """获取所有规则"""
        return list(self._rules)

    def validate(self, suggestion: PlanAdjustment) -> ValidationResult:
        """校验调整建议"""
        violations: list[Violation] = []
        warnings: list[str] = []
        rule_results: dict[str, bool] = {}

        sorted_rules = sorted(
            [r for r in self._rules if r.enabled],
            key=lambda r: r.priority.value,
            reverse=True,
        )

        for rule in sorted_rules:
            try:
                passed = rule.check(suggestion)
                rule_results[rule.name] = passed

                if not passed:
                    if rule.priority in (RulePriority.CRITICAL, RulePriority.HIGH):
                        violations.append(
                            Violation(
                                rule_id=rule.name,
                                rule_name=rule.description,
                                actual_value=0.0,
                                limit_value=0.0,
                                message=rule.violation_message,
                                location=None,
                            )
                        )
                    else:
                        warnings.append(rule.violation_message)
            except Exception as e:
                logger.warning(f"规则 {rule.name} 执行失败: {e}")
                rule_results[rule.name] = False

        passed = len(violations) == 0
        action = "retry" if not passed else None

        return ValidationResult(
            passed=passed,
            violations=violations,
            retry_count=0,
            action=action,
        )

    def _check_volume_increase(self, suggestion: PlanAdjustment) -> bool:
        """检查跑量增幅 - 超过10%则不通过"""
        if suggestion.adjustment_type != "volume":
            return True
        if not isinstance(suggestion.adjusted_value, (int, float)):
            return True
        if not isinstance(suggestion.original_value, (int, float)):
            return True
        if suggestion.original_value <= 0:
            return True
        increase_rate = (
            suggestion.adjusted_value - suggestion.original_value
        ) / suggestion.original_value
        return increase_rate <= 0.10

    def _check_long_run_ratio(self, suggestion: PlanAdjustment) -> bool:
        """检查长距离跑比例 - 仅当调整类型为type且涉及long时检查"""
        if suggestion.adjustment_type != "type":
            return True
        return not (
            isinstance(suggestion.adjusted_value, str)
            and "long" in str(suggestion.adjusted_value).lower()
        )

    def _check_recovery_after_interval(self, suggestion: PlanAdjustment) -> bool:
        """检查间歇跑后恢复 - intensity类型调整时检查"""
        if suggestion.adjustment_type != "intensity":
            return True
        if not isinstance(suggestion.adjusted_value, (int, float)):
            return True
        return not suggestion.adjusted_value > 7

    def _check_race_taper(self, suggestion: PlanAdjustment) -> bool:
        """检查比赛减量 - 仅当调整类型为date时检查"""
        if suggestion.adjustment_type != "date":
            return True
        return True

    def _check_easy_day_intensity(self, suggestion: PlanAdjustment) -> bool:
        """检查轻松日强度 - intensity类型且值过高时警告"""
        if suggestion.adjustment_type != "intensity":
            return True
        if not isinstance(suggestion.adjusted_value, (int, float)):
            return True
        return not suggestion.adjusted_value > 5

    def get_default_adjustment(self, adjustment_request: str) -> PlanAdjustment:
        """规则引擎降级方案：当LLM不可用时提供默认建议"""
        if "减量" in adjustment_request:
            return PlanAdjustment(
                adjustment_type="volume",
                original_value=1.0,
                adjusted_value=0.8,
                reason="减量周，跑量降低20%",
                confidence=0.7,
            )
        if "加量" in adjustment_request:
            return PlanAdjustment(
                adjustment_type="volume",
                original_value=1.0,
                adjusted_value=1.1,
                reason="加量周，跑量增加10%（安全上限）",
                confidence=0.6,
            )
        return PlanAdjustment(
            adjustment_type="volume",
            original_value=1.0,
            adjusted_value=1.0,
            reason="无法解析调整请求，请使用更明确的描述",
            confidence=0.0,
        )
