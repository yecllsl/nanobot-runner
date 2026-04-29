"""
目标达成预测引擎 - v0.12.0

基于VDOT趋势、训练负荷和执行反馈，预测目标达成概率
"""

import logging
from typing import Any

from src.core.calculators.race_prediction import RacePredictionEngine
from src.core.models import GoalAchievementEvaluation

logger = logging.getLogger(__name__)


class GoalPredictionEngine:
    """目标达成预测引擎

    基于当前体能水平、训练趋势和目标差距，预测目标达成概率。
    复用RacePredictionEngine的VDOT趋势预测和置信度计算能力。
    """

    VDOT_WEEKLY_IMPROVEMENT_RATE = 0.3
    VDOT_MAX_WEEKLY_IMPROVEMENT = 0.5
    MIN_DATA_POINTS_FOR_PREDICTION = 2

    def __init__(self, race_engine: RacePredictionEngine | None = None) -> None:
        self._race_engine = race_engine or RacePredictionEngine()

    def evaluate_goal(
        self,
        goal_type: str,
        goal_value: float,
        current_vdot: float,
        vdot_trend: list[float] | None = None,
        weekly_volume_km: float = 0.0,
        training_consistency: float = 1.0,
        weeks_available: int | None = None,
    ) -> GoalAchievementEvaluation:
        """评估目标达成概率

        Args:
            goal_type: 目标类型（vdot/5k/10k/half_marathon/marathon）
            goal_value: 目标值（VDOT值或秒数）
            current_vdot: 当前VDOT值
            vdot_trend: VDOT趋势列表
            weekly_volume_km: 周跑量（公里）
            training_consistency: 训练一致性(0-1)
            weeks_available: 可用周数

        Returns:
            GoalAchievementEvaluation: 目标达成评估
        """
        current_value = self._resolve_current_value(goal_type, current_vdot)
        achievement_probability = self._calculate_achievement_probability(
            goal_type=goal_type,
            goal_value=goal_value,
            current_value=current_value,
            current_vdot=current_vdot,
            vdot_trend=vdot_trend,
            weekly_volume_km=weekly_volume_km,
            training_consistency=training_consistency,
            weeks_available=weeks_available,
        )
        key_risks = self._identify_key_risks(
            goal_type=goal_type,
            goal_value=goal_value,
            current_value=current_value,
            current_vdot=current_vdot,
            weekly_volume_km=weekly_volume_km,
            training_consistency=training_consistency,
        )
        improvement_suggestions = self._generate_improvement_suggestions(
            goal_type=goal_type,
            goal_value=goal_value,
            current_value=current_value,
            key_risks=key_risks,
            weekly_volume_km=weekly_volume_km,
        )
        estimated_weeks = self._estimate_weeks_to_achieve(
            goal_type=goal_type,
            goal_value=goal_value,
            current_value=current_value,
            current_vdot=current_vdot,
            vdot_trend=vdot_trend,
            weekly_volume_km=weekly_volume_km,
            training_consistency=training_consistency,
        )
        confidence = self._calculate_confidence(
            vdot_trend=vdot_trend,
            training_consistency=training_consistency,
        )

        return GoalAchievementEvaluation(
            goal_type=goal_type,
            goal_value=goal_value,
            current_value=current_value,
            achievement_probability=achievement_probability,
            key_risks=key_risks,
            improvement_suggestions=improvement_suggestions,
            estimated_weeks_to_achieve=estimated_weeks,
            confidence=confidence,
        )

    def _resolve_current_value(self, goal_type: str, current_vdot: float) -> float:
        """根据目标类型解析当前值"""
        if goal_type == "vdot":
            return current_vdot

        distance_map: dict[str, float] = {
            "5k": 5.0,
            "10k": 10.0,
            "half_marathon": 21.0975,
            "marathon": 42.195,
        }
        distance_km = distance_map.get(goal_type)
        if distance_km is None:
            return current_vdot

        try:
            predicted_time = self._race_engine.vdot_to_time(current_vdot, distance_km)
            return predicted_time
        except (ValueError, ZeroDivisionError):
            return current_vdot

    def _calculate_achievement_probability(
        self,
        goal_type: str,
        goal_value: float,
        current_value: float,
        current_vdot: float,
        vdot_trend: list[float] | None,
        weekly_volume_km: float,
        training_consistency: float,
        weeks_available: int | None,
    ) -> float:
        """计算目标达成概率"""
        if goal_type == "vdot":
            gap = goal_value - current_vdot
        else:
            gap = current_value - goal_value

        if gap <= 0:
            return 1.0

        trend_slope = self._calculate_trend_slope(vdot_trend)

        if goal_type == "vdot":
            weekly_improvement = max(trend_slope, self.VDOT_WEEKLY_IMPROVEMENT_RATE)
        else:
            weekly_improvement = max(
                trend_slope * current_value * 0.01,
                current_value * 0.005,
            )

        effective_improvement = weekly_improvement * training_consistency

        if weekly_volume_km < 20:
            effective_improvement *= 0.7
        elif weekly_volume_km > 80:
            effective_improvement *= 0.9

        if weeks_available is not None and weeks_available > 0:
            total_improvement = effective_improvement * weeks_available
            if goal_type == "vdot":
                probability = min(1.0, total_improvement / gap) if gap > 0 else 1.0
            else:
                probability = min(1.0, total_improvement / gap) if gap > 0 else 1.0
        else:
            estimated_weeks = (
                gap / effective_improvement if effective_improvement > 0 else 999
            )
            probability = max(0.0, 1.0 - (estimated_weeks / 52.0))

        return max(0.0, min(1.0, probability))

    def _calculate_trend_slope(self, vdot_trend: list[float] | None) -> float:
        """计算VDOT趋势斜率"""
        if not vdot_trend or len(vdot_trend) < self.MIN_DATA_POINTS_FOR_PREDICTION:
            return 0.0

        n = len(vdot_trend)
        x_mean = (n - 1) / 2.0
        y_mean = sum(vdot_trend) / n

        numerator = sum((i - x_mean) * (vdot_trend[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return 0.0

        slope = numerator / denominator
        return max(0.0, min(self.VDOT_MAX_WEEKLY_IMPROVEMENT, slope))

    def _identify_key_risks(
        self,
        goal_type: str,
        goal_value: float,
        current_value: float,
        current_vdot: float,
        weekly_volume_km: float,
        training_consistency: float,
    ) -> list[str]:
        """识别关键风险"""
        risks: list[str] = []

        if goal_type == "vdot":
            gap = goal_value - current_vdot
            if gap > 10:
                risks.append("目标VDOT差距过大（>10），达成难度极高")
            elif gap > 5:
                risks.append("目标VDOT差距较大（5-10），需要系统性训练")
        else:
            if current_value > 0 and goal_value > 0:
                gap_pct = abs(current_value - goal_value) / current_value
                if gap_pct > 0.2:
                    risks.append("目标时间差距超过20%，需要长期训练")

        if weekly_volume_km < 20:
            risks.append("周跑量不足（<20km），影响有氧基础发展")
        elif weekly_volume_km > 80:
            risks.append("周跑量偏高（>80km），注意伤病风险")

        if training_consistency < 0.5:
            risks.append("训练一致性低（<50%），影响训练效果累积")

        if current_vdot < 30:
            risks.append("当前VDOT较低，建议先建立有氧基础")

        if not risks:
            risks.append("暂无明显风险")

        return risks

    def _generate_improvement_suggestions(
        self,
        goal_type: str,
        goal_value: float,
        current_value: float,
        key_risks: list[str],
        weekly_volume_km: float,
    ) -> list[str]:
        """生成改进建议"""
        suggestions: list[str] = []

        if goal_type == "vdot":
            gap = goal_value - current_value
            if gap > 5:
                suggestions.append("建议分阶段设定目标，先提升至中间VDOT值")
            suggestions.append("增加间歇训练和阈值跑，提升VDOT")
        else:
            suggestions.append("保持规律训练，逐步提升训练强度")

        if weekly_volume_km < 30:
            suggestions.append("逐步增加周跑量至30-50km")
        elif weekly_volume_km < 50:
            suggestions.append("维持当前跑量，注重训练质量")

        suggestions.append("确保每周至少一次长距离跑")

        if any("伤病" in r for r in key_risks):
            suggestions.append("增加力量训练和拉伸，预防伤病")

        return suggestions[:5]

    def _estimate_weeks_to_achieve(
        self,
        goal_type: str,
        goal_value: float,
        current_value: float,
        current_vdot: float,
        vdot_trend: list[float] | None,
        weekly_volume_km: float,
        training_consistency: float,
    ) -> int | None:
        """估算达成目标所需周数"""
        if goal_type == "vdot":
            gap = goal_value - current_vdot
        else:
            gap = current_value - goal_value

        if gap <= 0:
            return 0

        trend_slope = self._calculate_trend_slope(vdot_trend)

        if goal_type == "vdot":
            weekly_improvement = max(trend_slope, self.VDOT_WEEKLY_IMPROVEMENT_RATE)
        else:
            weekly_improvement = max(
                trend_slope * current_value * 0.01,
                current_value * 0.005,
            )

        effective_improvement = weekly_improvement * training_consistency

        if weekly_volume_km < 20:
            effective_improvement *= 0.7

        if effective_improvement <= 0:
            return None

        weeks = int(gap / effective_improvement) + 1
        return max(4, min(104, weeks))

    def _calculate_confidence(
        self,
        vdot_trend: list[float] | None,
        training_consistency: float,
    ) -> float:
        """计算预测置信度"""
        try:
            trend_confidence = self._race_engine.calculate_confidence(
                vdot_trend=vdot_trend or [],
                training_consistency=training_consistency,
            )
        except Exception:
            trend_confidence = 0.5

        data_confidence = 0.3
        if vdot_trend and len(vdot_trend) >= 4:
            data_confidence = 0.8
        elif vdot_trend and len(vdot_trend) >= 2:
            data_confidence = 0.5

        confidence = trend_confidence * 0.6 + data_confidence * 0.4
        return max(0.0, min(1.0, confidence))


class PredictionEvaluator:
    """预测评估器

    评估预测准确性，计算误差指标，提供预测质量统计。
    """

    def evaluate_prediction_accuracy(
        self,
        predicted_value: float,
        actual_value: float,
    ) -> dict[str, float]:
        """评估单次预测准确性

        Args:
            predicted_value: 预测值
            actual_value: 实际值

        Returns:
            dict: 误差指标
        """
        if actual_value == 0:
            return {
                "absolute_error": abs(predicted_value),
                "relative_error_pct": 0.0,
                "is_accurate": False,
            }

        absolute_error = abs(predicted_value - actual_value)
        relative_error = (absolute_error / abs(actual_value)) * 100

        return {
            "absolute_error": round(absolute_error, 2),
            "relative_error_pct": round(relative_error, 2),
            "is_accurate": relative_error < 5.0,
        }

    def evaluate_batch(
        self,
        predictions: list[float],
        actuals: list[float],
    ) -> dict[str, Any]:
        """批量评估预测准确性

        Args:
            predictions: 预测值列表
            actuals: 实际值列表

        Returns:
            dict: 批量评估结果
        """
        if len(predictions) != len(actuals):
            raise ValueError("预测值和实际值列表长度不一致")

        if not predictions:
            return {
                "count": 0,
                "mean_absolute_error": 0.0,
                "mean_relative_error_pct": 0.0,
                "accuracy_rate": 0.0,
            }

        errors = []
        for pred, actual in zip(predictions, actuals):
            error = self.evaluate_prediction_accuracy(pred, actual)
            errors.append(error)

        mae = sum(e["absolute_error"] for e in errors) / len(errors)
        mre = sum(e["relative_error_pct"] for e in errors) / len(errors)
        accurate_count = sum(1 for e in errors if e["is_accurate"])

        return {
            "count": len(errors),
            "mean_absolute_error": round(mae, 2),
            "mean_relative_error_pct": round(mre, 2),
            "accuracy_rate": round(accurate_count / len(errors), 2),
        }

    def calculate_prediction_metrics(
        self,
        vdot_predictions: list[float],
        vdot_actuals: list[float],
    ) -> dict[str, Any]:
        """计算VDOT预测指标

        Args:
            vdot_predictions: VDOT预测值列表
            vdot_actuals: VDOT实际值列表

        Returns:
            dict: 预测指标
        """
        batch_result = self.evaluate_batch(vdot_predictions, vdot_actuals)

        if not vdot_predictions:
            return {**batch_result, "vdot_bias": 0.0}

        biases = [p - a for p, a in zip(vdot_predictions, vdot_actuals)]
        mean_bias = sum(biases) / len(biases)

        return {
            **batch_result,
            "vdot_bias": round(mean_bias, 2),
            "bias_direction": "overestimate" if mean_bias > 0 else "underestimate",
        }
