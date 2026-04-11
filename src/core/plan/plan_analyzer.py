"""
计划分析器模块

负责从多个维度分析训练计划的合理性，生成分析报告
"""

from typing import Any

from src.core.exceptions import ValidationError
from src.core.logger import get_logger
from src.core.models import AnalysisReport, DimensionResult, TrainingPlan, UserContext

logger = get_logger(__name__)


class PlanAnalyzer:
    """
    训练计划分析器

    从体能匹配、负荷递进、伤病风险、目标可达性四个维度分析计划合理性
    """

    DIMENSION_FITNESS = "fitness_match"
    DIMENSION_LOAD = "load_progression"
    DIMENSION_INJURY = "injury_risk"
    DIMENSION_GOAL = "goal_achievability"

    def __init__(self) -> None:
        """初始化计划分析器"""
        pass

    def _infer_experience_level(self, profile: Any) -> str:
        """
        根据用户画像推断经验水平

        Args:
            profile: 用户画像

        Returns:
            str: 经验水平（beginner/intermediate/advanced）
        """
        if profile.total_activities < 50 or profile.total_distance_km < 500:
            return "beginner"
        elif profile.total_activities >= 200 and profile.total_distance_km >= 2000:
            return "advanced"
        else:
            return "intermediate"

    def _get_status(self, score: float) -> str:
        """
        根据分数获取状态

        Args:
            score: 分数（0-100）

        Returns:
            str: 状态（excellent/good/fair/poor）
        """
        if score >= 80:
            return "excellent"
        elif score >= 60:
            return "good"
        elif score >= 40:
            return "fair"
        else:
            return "poor"

    def analyze(
        self,
        plan: TrainingPlan,
        user_context: UserContext,
    ) -> AnalysisReport:
        """
        分析训练计划的合理性

        Args:
            plan: 训练计划
            user_context: 用户上下文

        Returns:
            AnalysisReport: 分析报告，包含各维度评分、总体评分、改进建议和风险警告

        Raises:
            ValidationError: 参数验证失败
        """
        if not plan.weeks:
            raise ValidationError("训练计划不能为空")

        logger.info(f"开始分析训练计划: plan_id={plan.plan_id}")

        dimensions: list[DimensionResult] = []

        dimensions.append(self._analyze_fitness_match(plan, user_context))
        dimensions.append(self._analyze_load_progression(plan, user_context))
        dimensions.append(self._analyze_injury_risk(plan, user_context))
        dimensions.append(self._analyze_goal_achievability(plan, user_context))

        overall_score = sum(dim.score for dim in dimensions) / len(dimensions)

        recommendations = self._generate_recommendations(dimensions, plan, user_context)
        warnings = self._generate_warnings(dimensions, plan, user_context)

        disclaimer = self._generate_disclaimer()

        report = AnalysisReport(
            overall_score=round(overall_score, 2),
            dimensions=dimensions,
            recommendations=recommendations,
            warnings=warnings,
            disclaimer=disclaimer,
        )

        logger.info(
            f"训练计划分析完成: 总体评分={report.overall_score}, "
            f"维度数={len(dimensions)}, 建议数={len(recommendations)}, "
            f"警告数={len(warnings)}"
        )

        return report

    def _analyze_fitness_match(
        self,
        plan: TrainingPlan,
        user_context: UserContext,
    ) -> DimensionResult:
        """
        分析体能匹配度

        Args:
            plan: 训练计划
            user_context: 用户上下文

        Returns:
            DimensionResult: 体能匹配度分析结果
        """
        profile = user_context.profile
        training_load = user_context.training_load

        score = 100.0
        issues: list[str] = []

        avg_weekly_distance = sum(week.weekly_distance_km for week in plan.weeks) / len(
            plan.weeks
        )

        if avg_weekly_distance > training_load.avg_weekly_distance_km * 1.5:
            score -= 20
            issues.append(
                f"平均周跑量{avg_weekly_distance:.1f}km显著高于当前水平{training_load.avg_weekly_distance_km:.1f}km"
            )

        first_week_distance = plan.weeks[0].weekly_distance_km
        if first_week_distance > training_load.last_week_distance_km * 1.3:
            score -= 15
            issues.append(f"首周跑量{first_week_distance:.1f}km相比当前跑量增长过快")

        high_intensity_count = 0
        for week in plan.weeks:
            for day in week.daily_plans:
                if day.workout_type in ["interval", "tempo"]:
                    high_intensity_count += 1

        experience_level = self._infer_experience_level(profile)
        if experience_level == "beginner" and high_intensity_count > len(plan.weeks):
            score -= 15
            issues.append("初学者高强度训练频率过高")

        score = max(0, score)

        status = self._get_status(score)
        recommendations = self._generate_fitness_suggestions(issues)

        return DimensionResult(
            dimension=self.DIMENSION_FITNESS,
            score=score,
            status=status,
            details={"issues": issues},
            recommendations=recommendations,
        )

    def _analyze_load_progression(
        self,
        plan: TrainingPlan,
        user_context: UserContext,
    ) -> DimensionResult:
        """
        分析负荷递进合理性

        Args:
            plan: 训练计划
            user_context: 用户上下文

        Returns:
            DimensionResult: 负荷递进分析结果
        """
        score = 100.0
        issues: list[str] = []

        distances = [week.weekly_distance_km for week in plan.weeks]

        for i in range(1, len(distances)):
            if distances[i - 1] > 0:
                increase_rate = (distances[i] - distances[i - 1]) / distances[i - 1]
                if increase_rate > 0.10:
                    score -= 10
                    issues.append(
                        f"第{i + 1}周跑量增长{increase_rate * 100:.1f}%，超过10%安全线"
                    )

        has_recovery_week = False
        for i in range(2, len(plan.weeks)):
            if distances[i] < distances[i - 1] * 0.8:
                has_recovery_week = True
                break

        if len(plan.weeks) >= 4 and not has_recovery_week:
            score -= 10
            issues.append("连续训练超过4周未安排减量恢复周")

        if distances:
            peak_distance = max(distances)
            taper_distance = distances[-1]
            if peak_distance > 0:
                taper_ratio = (peak_distance - taper_distance) / peak_distance
                if taper_ratio < 0.4:
                    score -= 15
                    issues.append("赛前减量不足，建议减少40-60%跑量")

        score = max(0, score)

        status = self._get_status(score)
        recommendations = self._generate_load_suggestions(issues)

        return DimensionResult(
            dimension=self.DIMENSION_LOAD,
            score=score,
            status=status,
            details={"issues": issues},
            recommendations=recommendations,
        )

    def _analyze_injury_risk(
        self,
        plan: TrainingPlan,
        user_context: UserContext,
    ) -> DimensionResult:
        """
        分析伤病风险

        Args:
            plan: 训练计划
            user_context: 用户上下文

        Returns:
            DimensionResult: 伤病风险分析结果
        """
        profile = user_context.profile
        training_load = user_context.training_load

        score = 100.0
        issues: list[str] = []

        consecutive_days = 0
        max_consecutive = 0
        for week in plan.weeks:
            for day in week.daily_plans:
                if day.workout_type != "rest":
                    consecutive_days += 1
                    max_consecutive = max(max_consecutive, consecutive_days)
                else:
                    consecutive_days = 0

        if max_consecutive > 5:
            score -= 20
            issues.append(f"连续训练天数达到{max_consecutive}天，伤病风险较高")

        long_run_count = 0
        experience_level = self._infer_experience_level(profile)
        for week in plan.weeks:
            for day in week.daily_plans:
                if day.workout_type == "long":
                    long_run_count += 1
                    if day.distance_km > 30 and experience_level == "beginner":
                        score -= 25
                        issues.append(f"初学者长距离跑{day.distance_km:.1f}km风险极高")

        if hasattr(profile, "age") and profile.age and profile.age > 50:
            high_intensity_count = sum(
                1
                for week in plan.weeks
                for day in week.daily_plans
                if day.workout_type in ["interval", "tempo"]
            )
            if high_intensity_count > len(plan.weeks) * 1.5:
                score -= 15
                issues.append("50岁以上跑者高强度训练频率过高")

        score = max(0, score)

        status = self._get_status(score)
        recommendations = self._generate_injury_suggestions(issues)

        return DimensionResult(
            dimension=self.DIMENSION_INJURY,
            score=score,
            status=status,
            details={"issues": issues},
            recommendations=recommendations,
        )

    def _analyze_goal_achievability(
        self,
        plan: TrainingPlan,
        user_context: UserContext,
    ) -> DimensionResult:
        """
        分析目标可达性

        Args:
            plan: 训练计划
            user_context: 用户上下文

        Returns:
            DimensionResult: 目标可达性分析结果
        """
        profile = user_context.profile
        training_load = user_context.training_load

        score = 100.0
        issues: list[str] = []

        total_weeks = len(plan.weeks)
        if plan.goal_distance_km >= 42 and total_weeks < 12:
            score -= 30
            issues.append(f"全马训练周期仅{total_weeks}周，建议至少12周")
        elif plan.goal_distance_km >= 21 and total_weeks < 8:
            score -= 25
            issues.append(f"半马训练周期仅{total_weeks}周，建议至少8周")

        if plan.weeks:
            peak_distance = max(week.weekly_distance_km for week in plan.weeks)
            if plan.goal_distance_km >= 42 and peak_distance < 60:
                score -= 20
                issues.append(
                    f"全马目标峰值周跑量{peak_distance:.1f}km不足，建议至少60km"
                )
            elif plan.goal_distance_km >= 21 and peak_distance < 40:
                score -= 15
                issues.append(
                    f"半马目标峰值周跑量{peak_distance:.1f}km不足，建议至少40km"
                )

        long_runs = [
            day.distance_km
            for week in plan.weeks
            for day in week.daily_plans
            if day.workout_type == "long"
        ]
        if long_runs:
            max_long_run = max(long_runs)
            if plan.goal_distance_km >= 42 and max_long_run < 32:
                score -= 15
                issues.append(
                    f"全马目标最长训练跑{max_long_run:.1f}km不足，建议至少32km"
                )
            elif plan.goal_distance_km >= 21 and max_long_run < 16:
                score -= 10
                issues.append(
                    f"半马目标最长训练跑{max_long_run:.1f}km不足，建议至少16km"
                )

        score = max(0, score)

        status = self._get_status(score)
        recommendations = self._generate_goal_suggestions(issues)

        return DimensionResult(
            dimension=self.DIMENSION_GOAL,
            score=score,
            status=status,
            details={"issues": issues},
            recommendations=recommendations,
        )

    def _generate_recommendations(
        self,
        dimensions: list[DimensionResult],
        plan: TrainingPlan,
        user_context: UserContext,
    ) -> list[str]:
        """
        生成改进建议

        Args:
            dimensions: 各维度分析结果
            plan: 训练计划
            user_context: 用户上下文

        Returns:
            List[str]: 改进建议列表
        """
        suggestions: list[str] = []

        for dim in dimensions:
            if dim.score < 70:
                suggestions.extend(dim.recommendations)

        if not suggestions:
            suggestions.append("训练计划整体合理，建议严格执行并注意身体反馈")

        return suggestions

    def _generate_warnings(
        self,
        dimensions: list[DimensionResult],
        plan: TrainingPlan,
        user_context: UserContext,
    ) -> list[str]:
        """
        生成风险警告

        Args:
            dimensions: 各维度分析结果
            plan: 训练计划
            user_context: 用户上下文

        Returns:
            List[str]: 风险警告列表
        """
        warnings: list[str] = []

        for dim in dimensions:
            if dim.score < 80:
                issues = dim.details.get("issues", [])
                warnings.extend(issues)

        if (
            hasattr(user_context.profile, "age")
            and user_context.profile.age
            and user_context.profile.age > 50
        ):
            warnings.append("50岁以上跑者建议定期体检，关注心血管健康")

        return warnings

    def _generate_disclaimer(self) -> str:
        """
        生成医疗免责声明

        Returns:
            str: 医疗免责声明
        """
        return (
            "⚠️ **医疗免责声明**\n\n"
            "本训练计划由AI生成，仅供参考，不构成医疗建议。在开始任何训练计划前，请：\n\n"
            "1. 咨询专业医生，确保身体状况适合跑步训练\n"
            "2. 如有心脏病、高血压、关节疾病等健康问题，请遵医嘱\n"
            "3. 训练过程中如出现胸痛、呼吸困难、头晕等症状，请立即停止并就医\n"
            "4. 建议定期进行体检，监控身体健康状况\n\n"
            "执行本训练计划的风险由用户自行承担，AI系统不承担任何责任。"
        )

    def _generate_fitness_suggestions(self, issues: list[str]) -> list[str]:
        """生成体能匹配度改进建议"""
        suggestions = []
        for issue in issues:
            if "平均周跑量" in issue:
                suggestions.append("建议降低平均周跑量，逐步适应训练强度")
            elif "首周跑量" in issue:
                suggestions.append("建议首周跑量与当前跑量持平或略低")
            elif "初学者" in issue:
                suggestions.append("初学者建议减少高强度训练，以轻松跑为主")
        return suggestions

    def _generate_load_suggestions(self, issues: list[str]) -> list[str]:
        """生成负荷递进改进建议"""
        suggestions = []
        for issue in issues:
            if "增长" in issue:
                suggestions.append("建议控制周跑量增长在10%以内")
            elif "恢复周" in issue:
                suggestions.append("建议每3-4周安排一次减量恢复周")
            elif "减量" in issue:
                suggestions.append("建议赛前一周减少40-60%跑量")
        return suggestions

    def _generate_injury_suggestions(self, issues: list[str]) -> list[str]:
        """生成伤病风险改进建议"""
        suggestions = []
        for issue in issues:
            if "连续训练" in issue:
                suggestions.append("建议增加休息日，避免连续高强度训练")
            elif "初学者长距离" in issue:
                suggestions.append("初学者建议长距离跑不超过25km")
            elif "50岁以上" in issue:
                suggestions.append("建议降低高强度训练频率，增加交叉训练")
        return suggestions

    def _generate_goal_suggestions(self, issues: list[str]) -> list[str]:
        """生成目标可达性改进建议"""
        suggestions = []
        for issue in issues:
            if "训练周期" in issue:
                suggestions.append("建议延长训练周期，确保充分准备")
            elif "峰值周跑量" in issue:
                suggestions.append("建议逐步增加峰值周跑量")
            elif "最长训练跑" in issue:
                suggestions.append("建议增加长距离训练跑的距离")
        return suggestions
