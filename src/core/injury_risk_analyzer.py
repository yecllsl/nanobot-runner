# 伤病风险分析器
# 评估跑者的伤病风险，提供预防建议

from dataclasses import dataclass
from typing import Any, Dict, List

from src.core.logger import get_logger
from src.core.user_profile_manager import (
    InjuryRiskLevel,
    RunnerProfile,
    TrainingPattern,
)

logger = get_logger(__name__)


@dataclass
class InjuryRiskResult:
    """伤病风险评估结果"""

    risk_score: float
    risk_level: InjuryRiskLevel
    risk_factors: List[str]
    recommendations: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "risk_score": self.risk_score,
            "risk_level": self.risk_level.value,
            "risk_factors": self.risk_factors,
            "recommendations": self.recommendations,
        }


class InjuryRiskAnalyzer:
    """伤病风险分析器"""

    def calculate_injury_risk(
        self,
        profile: RunnerProfile,
        age: int = 30,
        resting_hr: int = 60,
    ) -> InjuryRiskResult:
        """
        计算伤病风险评分

        风险评估维度：
        1. 训练负荷突变（ATL/CTL 比率）
        2. 训练一致性
        3. 恢复情况（TSB）
        4. 年龄因素
        5. 训练强度

        Args:
            profile: 跑者画像对象
            age: 年龄
            resting_hr: 静息心率

        Returns:
            InjuryRiskResult: 伤病风险评估结果

        Raises:
            ValueError: 当参数无效时
        """
        if age <= 0 or age > 120:
            raise ValueError("年龄必须在 1-120 之间")
        if resting_hr <= 0 or resting_hr > 200:
            raise ValueError("静息心率必须在合理范围内")

        risk_score = 0.0
        risk_factors: List[str] = []
        recommendations: List[str] = []

        risk_score, risk_factors, recommendations = self._evaluate_training_load(
            profile, risk_score, risk_factors, recommendations
        )

        risk_score, risk_factors, recommendations = self._evaluate_consistency(
            profile, risk_score, risk_factors, recommendations
        )

        risk_score, risk_factors, recommendations = self._evaluate_recovery(
            profile, risk_score, risk_factors, recommendations
        )

        risk_score, risk_factors, recommendations = self._evaluate_age(
            age, risk_score, risk_factors, recommendations
        )

        risk_score, risk_factors, recommendations = self._evaluate_intensity(
            profile, risk_score, risk_factors, recommendations
        )

        risk_level = self._determine_risk_level(risk_score, recommendations)

        result = InjuryRiskResult(
            risk_score=round(risk_score, 2),
            risk_level=risk_level,
            risk_factors=risk_factors,
            recommendations=recommendations,
        )

        profile.injury_risk_score = result.risk_score
        profile.injury_risk_level = result.risk_level

        return result

    def _evaluate_training_load(
        self,
        profile: RunnerProfile,
        risk_score: float,
        risk_factors: List[str],
        recommendations: List[str],
    ) -> tuple:
        """评估训练负荷突变"""
        if profile.ctl > 0:
            atl_ctl_ratio = profile.atl / profile.ctl
            if atl_ctl_ratio > 1.5:
                risk_score += 30
                risk_factors.append("训练负荷突增（ATL/CTL > 1.5）")
                recommendations.append("立即降低训练强度，避免过度训练")
            elif atl_ctl_ratio > 1.2:
                risk_score += 15
                risk_factors.append("训练负荷较高（ATL/CTL > 1.2）")
                recommendations.append("注意监控身体反应，适度调整训练")
            elif atl_ctl_ratio < 0.8:
                risk_score += 10
                risk_factors.append("训练量过低，体能可能下降")
                recommendations.append("逐步增加训练量，保持体能")

        return risk_score, risk_factors, recommendations

    def _evaluate_consistency(
        self,
        profile: RunnerProfile,
        risk_score: float,
        risk_factors: List[str],
        recommendations: List[str],
    ) -> tuple:
        """评估训练一致性"""
        if profile.consistency_score < 30:
            risk_score += 25
            risk_factors.append("训练非常不规律")
            recommendations.append("建立规律的训练习惯，避免三天打鱼两天晒网")
        elif profile.consistency_score < 60:
            risk_score += 12
            risk_factors.append("训练不够规律")
            recommendations.append("制定固定训练计划，提高训练一致性")

        return risk_score, risk_factors, recommendations

    def _evaluate_recovery(
        self,
        profile: RunnerProfile,
        risk_score: float,
        risk_factors: List[str],
        recommendations: List[str],
    ) -> tuple:
        """评估恢复情况"""
        if profile.tsb < -20:
            risk_score += 25
            risk_factors.append("疲劳累积严重（TSB < -20）")
            recommendations.append("立即安排休息，至少 2-3 天完全恢复")
        elif profile.tsb < -10:
            risk_score += 12
            risk_factors.append("有一定疲劳累积（TSB < -10）")
            recommendations.append("降低训练强度，增加恢复时间")

        return risk_score, risk_factors, recommendations

    def _evaluate_age(
        self,
        age: int,
        risk_score: float,
        risk_factors: List[str],
        recommendations: List[str],
    ) -> tuple:
        """评估年龄因素"""
        if age > 50:
            risk_score += 10
            risk_factors.append("年龄较大，恢复能力下降")
            recommendations.append("增加热身和拉伸时间，注重恢复")
        elif age > 40:
            risk_score += 5
            risk_factors.append("中年跑者，需注意恢复")
            recommendations.append("保证充足睡眠，适度训练")

        return risk_score, risk_factors, recommendations

    def _evaluate_intensity(
        self,
        profile: RunnerProfile,
        risk_score: float,
        risk_factors: List[str],
        recommendations: List[str],
    ) -> tuple:
        """评估训练强度"""
        if profile.training_pattern in [
            TrainingPattern.INTENSE,
            TrainingPattern.EXTREME,
        ]:
            risk_score += 10
            risk_factors.append("训练强度过高")
            recommendations.append("安排轻松周，降低训练量")

        return risk_score, risk_factors, recommendations

    def _determine_risk_level(
        self, risk_score: float, recommendations: List[str]
    ) -> InjuryRiskLevel:
        """确定风险等级"""
        if risk_score < 30:
            if not recommendations:
                recommendations.append("保持当前训练节奏，注意监控身体状态")
            return InjuryRiskLevel.LOW
        elif risk_score < 60:
            return InjuryRiskLevel.MEDIUM
        else:
            return InjuryRiskLevel.HIGH

    def get_risk_summary(self, profile: RunnerProfile) -> Dict[str, Any]:
        """
        获取风险摘要

        Args:
            profile: 跑者画像对象

        Returns:
            dict: 风险摘要
        """
        return {
            "risk_score": profile.injury_risk_score,
            "risk_level": profile.injury_risk_level.value,
            "atl": profile.atl,
            "ctl": profile.ctl,
            "tsb": profile.tsb,
            "consistency_score": profile.consistency_score,
        }
