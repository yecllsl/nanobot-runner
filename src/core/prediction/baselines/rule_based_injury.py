from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class RuleBasedInjuryBaseline:
    """基于规则的伤病风险基线评估

    使用ACWR、训练单调性、连续高强度天数、静息心率偏差
    四个维度进行规则化评分，不依赖ML模型。
    """

    ACWR_THRESHOLDS = (1.3, 1.5, 2.0)
    MONOTONY_THRESHOLDS = (1.5, 2.0, 2.5)
    CONSECUTIVE_THRESHOLDS = (2, 3, 5)
    HR_DEVIATION_THRESHOLDS = (5.0, 10.0, 15.0)

    def assess(
        self,
        acwr: float,
        training_monotony: float,
        consecutive_hard_days: int,
        resting_hr_deviation_pct: float,
    ) -> dict[str, Any]:
        """评估伤病风险"""
        scores: dict[str, float] = {}
        risk_factors: list[str] = []

        acwr_score = self._score_dimension(acwr, self.ACWR_THRESHOLDS)
        scores["acwr"] = acwr_score
        if acwr >= self.ACWR_THRESHOLDS[1]:
            risk_factors.append("acwr")

        monotony_score = self._score_dimension(
            training_monotony, self.MONOTONY_THRESHOLDS
        )
        scores["training_monotony"] = monotony_score
        if training_monotony >= self.MONOTONY_THRESHOLDS[1]:
            risk_factors.append("training_monotony")

        consecutive_score = self._score_dimension(
            float(consecutive_hard_days), self.CONSECUTIVE_THRESHOLDS
        )
        scores["consecutive_hard_days"] = consecutive_score
        if consecutive_hard_days >= self.CONSECUTIVE_THRESHOLDS[1]:
            risk_factors.append("consecutive_hard_days")

        hr_score = self._score_dimension(
            resting_hr_deviation_pct, self.HR_DEVIATION_THRESHOLDS
        )
        scores["resting_hr_deviation"] = hr_score
        if resting_hr_deviation_pct >= self.HR_DEVIATION_THRESHOLDS[1]:
            risk_factors.append("resting_hr_deviation")

        total_score = sum(scores.values()) / len(scores)

        risk_level = self._score_to_level(total_score)

        return {
            "risk_level": risk_level,
            "risk_score": round(total_score, 1),
            "risk_factors": risk_factors,
            "dimension_scores": scores,
            "advice": self._generate_advice(risk_level, risk_factors),
        }

    def _score_dimension(
        self, value: float, thresholds: tuple[float, float, float]
    ) -> float:
        """根据阈值计算0-100分"""
        low, medium, high = thresholds
        if value < low:
            return min(25.0, max(0.0, value / low * 25.0))
        elif value < medium:
            return 25.0 + (value - low) / (medium - low) * 25.0
        elif value < high:
            return 50.0 + (value - medium) / (high - medium) * 25.0
        else:
            return min(100.0, 75.0 + (value - high) / high * 25.0)

    def _score_to_level(self, score: float) -> str:
        """分数转风险等级"""
        if score < 25:
            return "low"
        elif score < 75:
            return "medium"
        else:
            return "high"

    def _generate_advice(self, risk_level: str, risk_factors: list[str]) -> str:
        """生成建议"""
        if risk_level == "low":
            return "训练负荷合理，继续保持当前节奏"
        elif risk_level == "medium":
            factors_text = "、".join(risk_factors) if risk_factors else "综合因素"
            return f"注意{factors_text}，建议适当降低训练强度"
        else:
            return "伤病风险较高，强烈建议休息或仅进行低强度恢复训练"
