# 训练响应分析器
# 分析用户对不同训练类型的响应模式，识别适应性差异

from typing import Any

from src.core.base.logger import get_logger
from src.core.models import (
    PlanExecutionStats,
    TrainingResponsePattern,
)
from src.core.plan.plan_execution_repository import PlanExecutionRepository

logger = get_logger(__name__)


class TrainingResponseAnalyzer:
    """训练响应分析器

    分析用户对不同训练类型的响应模式，识别适应性差异，
    为智能调整层(v0.11.0)提供数据支撑。
    """

    def __init__(self, execution_repo: PlanExecutionRepository) -> None:
        """初始化训练响应分析器

        Args:
            execution_repo: 计划执行仓储
        """
        self.execution_repo = execution_repo

    def analyze_plan_response(self, plan_id: str) -> dict[str, Any]:
        """分析计划整体执行响应

        综合评估计划执行情况和训练响应模式，输出分析结论。

        Args:
            plan_id: 计划ID

        Returns:
            dict: 分析结果，包含success/data/message
        """
        try:
            stats = self.execution_repo.get_plan_execution_stats(plan_id)
            patterns = self.execution_repo.get_training_response_patterns(plan_id)

            overall_assessment = self._assess_overall(stats, patterns)
            weak_types = self._identify_weak_types(patterns)
            strong_types = self._identify_strong_types(patterns)

            return {
                "success": True,
                "data": {
                    "plan_id": plan_id,
                    "stats": stats.to_dict(),
                    "patterns": [p.to_dict() for p in patterns],
                    "overall_assessment": overall_assessment,
                    "weak_types": weak_types,
                    "strong_types": strong_types,
                },
                "message": "训练响应分析完成",
            }
        except Exception as e:
            logger.error(f"训练响应分析失败：{e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"训练响应分析失败：{e}",
            }

    def _assess_overall(
        self,
        stats: PlanExecutionStats,
        patterns: list[TrainingResponsePattern],
    ) -> str:
        """评估整体训练响应

        Args:
            stats: 执行统计
            patterns: 训练响应模式

        Returns:
            str: 整体评估结论
        """
        if stats.total_planned_days == 0:
            return "计划尚未开始执行"

        if stats.completion_rate >= 0.9 and stats.avg_effort_score <= 5:
            return "训练适应良好，可考虑逐步增加训练量"
        elif stats.completion_rate >= 0.7:
            if stats.avg_effort_score >= 7:
                return "训练完成率尚可，但体感偏累，建议关注恢复"
            return "训练完成率良好，继续保持当前节奏"
        elif stats.completion_rate >= 0.5:
            return "训练完成率一般，建议适当降低训练强度"
        else:
            return "训练完成率偏低，建议重新评估训练计划合理性"

    def _identify_weak_types(
        self, patterns: list[TrainingResponsePattern]
    ) -> list[dict[str, Any]]:
        """识别适应性较差的训练类型

        Args:
            patterns: 训练响应模式

        Returns:
            list: 适应性较差的训练类型列表
        """
        weak = []
        for p in patterns:
            if p.avg_completion_rate < 0.6 or p.avg_effort_score >= 8:
                weak.append(
                    {
                        "workout_type": p.workout_type.value,
                        "avg_completion_rate": p.avg_completion_rate,
                        "avg_effort_score": p.avg_effort_score,
                        "recommendation": p.recommendation,
                    }
                )
        return weak

    def _identify_strong_types(
        self, patterns: list[TrainingResponsePattern]
    ) -> list[dict[str, Any]]:
        """识别适应性较好的训练类型

        Args:
            patterns: 训练响应模式

        Returns:
            list: 适应性较好的训练类型列表
        """
        strong = []
        for p in patterns:
            if p.avg_completion_rate >= 0.85 and p.avg_effort_score <= 6:
                strong.append(
                    {
                        "workout_type": p.workout_type.value,
                        "avg_completion_rate": p.avg_completion_rate,
                        "avg_effort_score": p.avg_effort_score,
                        "recommendation": p.recommendation,
                    }
                )
        return strong
