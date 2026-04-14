"""
硬性规则校验器模块

负责校验LLM生成的训练计划是否符合硬性规则，防止反人类计划
"""

from datetime import datetime
from typing import Any

from src.core.logger import get_logger
from src.core.models import TrainingPlan, ValidationResult, Violation

logger = get_logger(__name__)


class HardValidator:
    """
    硬性规则校验器

    实现PRD中定义的6条硬性校验规则
    """

    RULE_WEEKLY_INCREASE = "weekly_increase_limit"
    RULE_REST_DAY = "rest_day_required"
    RULE_LONG_RUN_RATIO = "long_run_ratio_limit"
    RULE_HIGH_INTENSITY_RATIO = "high_intensity_ratio_limit"
    RULE_SINGLE_RUN_DISTANCE = "single_run_distance_limit"
    RULE_TAPER_WEEK = "taper_week_reduction"

    def __init__(self) -> None:
        """初始化硬性规则校验器"""
        self.rules = {
            self.RULE_WEEKLY_INCREASE: self._validate_weekly_increase,
            self.RULE_REST_DAY: self._validate_rest_day,
            self.RULE_LONG_RUN_RATIO: self._validate_long_run_ratio,
            self.RULE_HIGH_INTENSITY_RATIO: self._validate_high_intensity_ratio,
            self.RULE_SINGLE_RUN_DISTANCE: self._validate_single_run_distance,
            self.RULE_TAPER_WEEK: self._validate_taper_week,
        }

    def validate(
        self,
        plan: TrainingPlan,
        current_weekly_distance_km: float,
        goal_distance_km: float,
    ) -> ValidationResult:
        """
        校验训练计划是否符合所有硬性规则

        Args:
            plan: 训练计划
            current_weekly_distance_km: 当前周跑量
            goal_distance_km: 目标距离

        Returns:
            ValidationResult: 校验结果，包含是否通过、违规项和建议
        """
        logger.info(f"开始校验训练计划: plan_id={plan.plan_id}")

        violations: list[Violation] = []

        for rule_name, rule_func in self.rules.items():
            try:
                result = rule_func(plan, current_weekly_distance_km, goal_distance_km)
                if not result.passed:
                    violations.extend(result.violations)
            except Exception as e:
                logger.error(f"规则{rule_name}校验失败: {e}")
                violations.append(
                    Violation(
                        rule_id=rule_name,
                        rule_name=rule_name,
                        actual_value=0.0,
                        limit_value=0.0,
                        message=f"规则校验异常: {str(e)}",
                        location=None,
                    )
                )

        passed = len(violations) == 0
        action = "retry" if not passed else None

        logger.info(f"训练计划校验完成: 通过={passed}, 违规数={len(violations)}")

        return ValidationResult(
            passed=passed,
            violations=violations,
            retry_count=0,
            action=action,
        )

    def _validate_weekly_increase(
        self,
        plan: TrainingPlan,
        current_weekly_distance_km: float,
        goal_distance_km: float,
    ) -> ValidationResult:
        """
        规则1: 周跑量增长不超过10%

        Args:
            plan: 训练计划
            current_weekly_distance_km: 当前周跑量
            goal_distance_km: 目标距离

        Returns:
            ValidationResult: 校验结果
        """
        errors = []
        prev_distance = current_weekly_distance_km

        for week in plan.weeks:
            if prev_distance > 0:
                increase_rate = (
                    week.weekly_distance_km - prev_distance
                ) / prev_distance
                if increase_rate > 0.10:
                    errors.append(
                        {
                            "week_number": week.week_number,
                            "prev_distance": round(prev_distance, 2),
                            "current_distance": round(week.weekly_distance_km, 2),
                            "increase_rate": round(increase_rate * 100, 2),
                        }
                    )
            prev_distance = week.weekly_distance_km

        if errors:
            violation = Violation(
                rule_id=self.RULE_WEEKLY_INCREASE,
                rule_name="周跑量增长限制",
                actual_value=errors[0]["increase_rate"],
                limit_value=10.0,
                message=f"第{errors[0]['week_number']}周跑量增长{errors[0]['increase_rate']}%，超过10%限制",
                location=f"第{errors[0]['week_number']}周",
            )
            return ValidationResult(
                passed=False,
                violations=[violation],
                retry_count=0,
                action="retry",
            )

        return ValidationResult(passed=True, violations=[], retry_count=0, action=None)

    def _validate_rest_day(
        self,
        plan: TrainingPlan,
        current_weekly_distance_km: float,
        goal_distance_km: float,
    ) -> ValidationResult:
        """
        规则2: 每周至少安排1天完全休息

        Args:
            plan: 训练计划
            current_weekly_distance_km: 当前周跑量
            goal_distance_km: 目标距离

        Returns:
            ValidationResult: 校验结果
        """
        errors = []

        for week in plan.weeks:
            rest_days = sum(1 for day in week.daily_plans if day.workout_type == "rest")
            if rest_days < 1:
                errors.append(
                    {
                        "week_number": week.week_number,
                        "rest_days": rest_days,
                    }
                )

        if errors:
            violation = Violation(
                rule_id=self.RULE_REST_DAY,
                rule_name="休息日要求",
                actual_value=0.0,
                limit_value=1.0,
                message=f"第{errors[0]['week_number']}周没有安排休息日",
                location=f"第{errors[0]['week_number']}周",
            )
            return ValidationResult(
                passed=False,
                violations=[violation],
                retry_count=0,
                action="retry",
            )

        return ValidationResult(passed=True, violations=[], retry_count=0, action=None)

    def _validate_long_run_ratio(
        self,
        plan: TrainingPlan,
        current_weekly_distance_km: float,
        goal_distance_km: float,
    ) -> ValidationResult:
        """
        规则3: 长距离跑不超过周跑量的30%

        Args:
            plan: 训练计划
            current_weekly_distance_km: 当前周跑量
            goal_distance_km: 目标距离

        Returns:
            ValidationResult: 校验结果
        """
        errors = []

        for week in plan.weeks:
            long_run_distance = max(
                (
                    day.distance_km
                    for day in week.daily_plans
                    if day.workout_type == "long"
                ),
                default=0.0,
            )
            if week.weekly_distance_km > 0:
                ratio = long_run_distance / week.weekly_distance_km
                if ratio > 0.30:
                    errors.append(
                        {
                            "week_number": week.week_number,
                            "long_run_distance": round(long_run_distance, 2),
                            "weekly_distance": round(week.weekly_distance_km, 2),
                            "ratio": round(ratio * 100, 2),
                        }
                    )

        if errors:
            violation = Violation(
                rule_id=self.RULE_LONG_RUN_RATIO,
                rule_name="长距离跑占比限制",
                actual_value=errors[0]["ratio"],
                limit_value=30.0,
                message=f"第{errors[0]['week_number']}周长距离跑占比{errors[0]['ratio']}%，超过30%限制",
                location=f"第{errors[0]['week_number']}周",
            )
            return ValidationResult(
                passed=False,
                violations=[violation],
                retry_count=0,
                action="retry",
            )

        return ValidationResult(passed=True, violations=[], retry_count=0, action=None)

    def _validate_high_intensity_ratio(
        self,
        plan: TrainingPlan,
        current_weekly_distance_km: float,
        goal_distance_km: float,
    ) -> ValidationResult:
        """
        规则4: 高强度训练（间歇/节奏）不超过周跑量的20%

        Args:
            plan: 训练计划
            current_weekly_distance_km: 当前周跑量
            goal_distance_km: 目标距离

        Returns:
            ValidationResult: 校验结果
        """
        errors = []
        high_intensity_types = {"interval", "tempo"}

        for week in plan.weeks:
            high_intensity_distance = sum(
                day.distance_km
                for day in week.daily_plans
                if day.workout_type in high_intensity_types
            )
            if week.weekly_distance_km > 0:
                ratio = high_intensity_distance / week.weekly_distance_km
                if ratio > 0.20:
                    errors.append(
                        {
                            "week_number": week.week_number,
                            "high_intensity_distance": round(
                                high_intensity_distance, 2
                            ),
                            "weekly_distance": round(week.weekly_distance_km, 2),
                            "ratio": round(ratio * 100, 2),
                        }
                    )

        if errors:
            violation = Violation(
                rule_id=self.RULE_HIGH_INTENSITY_RATIO,
                rule_name="高强度训练占比限制",
                actual_value=errors[0]["ratio"],
                limit_value=20.0,
                message=f"第{errors[0]['week_number']}周高强度训练占比{errors[0]['ratio']}%，超过20%限制",
                location=f"第{errors[0]['week_number']}周",
            )
            return ValidationResult(
                passed=False,
                violations=[violation],
                retry_count=0,
                action="retry",
            )

        return ValidationResult(passed=True, violations=[], retry_count=0, action=None)

    def _validate_single_run_distance(
        self,
        plan: TrainingPlan,
        current_weekly_distance_km: float,
        goal_distance_km: float,
    ) -> ValidationResult:
        """
        规则5: 单次最长距离不超过目标距离的120%

        Args:
            plan: 训练计划
            current_weekly_distance_km: 当前周跑量
            goal_distance_km: 目标距离

        Returns:
            ValidationResult: 校验结果
        """
        max_distance = goal_distance_km * 1.20
        errors: list[dict[str, Any]] = []

        for week in plan.weeks:
            for day in week.daily_plans:
                if day.distance_km > max_distance:
                    errors.append(
                        {
                            "week_number": week.week_number,
                            "date": day.date,
                            "distance": round(day.distance_km, 2),
                            "max_allowed": round(max_distance, 2),
                        }
                    )

        if errors:
            violation = Violation(
                rule_id=self.RULE_SINGLE_RUN_DISTANCE,
                rule_name="单次跑步距离限制",
                actual_value=float(errors[0]["distance"]),
                limit_value=float(errors[0]["max_allowed"]),
                message=f"第{errors[0]['week_number']}周{errors[0]['date']}的单次距离{errors[0]['distance']}km，超过最大限制{errors[0]['max_allowed']}km",
                location=f"第{errors[0]['week_number']}周{errors[0]['date']}",
            )
            return ValidationResult(
                passed=False,
                violations=[violation],
                retry_count=0,
                action="retry",
            )

        return ValidationResult(passed=True, violations=[], retry_count=0, action=None)

    def _validate_taper_week(
        self,
        plan: TrainingPlan,
        current_weekly_distance_km: float,
        goal_distance_km: float,
    ) -> ValidationResult:
        """
        规则6: 比赛前一周跑量减少40-60%

        Args:
            plan: 训练计划
            current_weekly_distance_km: 当前周跑量
            goal_distance_km: 目标距离

        Returns:
            ValidationResult: 校验结果
        """
        if not plan.weeks or len(plan.weeks) < 2:
            return ValidationResult(
                passed=True, violations=[], retry_count=0, action=None
            )

        goal_date = datetime.strptime(plan.goal_date, "%Y-%m-%d")
        last_week = plan.weeks[-1]
        last_week_end = datetime.strptime(last_week.end_date, "%Y-%m-%d")

        days_to_goal = (goal_date - last_week_end).days

        if 0 <= days_to_goal <= 7:
            peak_weekly_distance = max(
                (week.weekly_distance_km for week in plan.weeks[:-1]),
                default=0.0,
            )
            if peak_weekly_distance > 0:
                reduction_rate = (
                    peak_weekly_distance - last_week.weekly_distance_km
                ) / peak_weekly_distance

                if reduction_rate < 0.40:
                    violation = Violation(
                        rule_id=self.RULE_TAPER_WEEK,
                        rule_name="赛前减量要求",
                        actual_value=round(reduction_rate * 100, 2),
                        limit_value=40.0,
                        message=f"比赛周跑量仅减少{round(reduction_rate * 100, 2)}%，低于40%的最低减量要求",
                        location="比赛周",
                    )
                    return ValidationResult(
                        passed=False,
                        violations=[violation],
                        retry_count=0,
                        action="retry",
                    )

        return ValidationResult(passed=True, violations=[], retry_count=0, action=None)
