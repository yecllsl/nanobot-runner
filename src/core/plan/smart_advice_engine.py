"""
智能训练建议引擎 - v0.12.0

基于训练数据、执行反馈和体能状态，生成个性化训练/恢复/营养/伤病预防建议
"""

import logging

from src.core.models import SmartTrainingAdvice

logger = logging.getLogger(__name__)


class SmartAdviceEngine:
    """智能训练建议引擎

    根据用户训练数据、执行反馈和体能状态，生成多维度个性化建议。
    支持四种建议类型：训练(training)、恢复(recovery)、营养(nutrition)、伤病预防(injury_prevention)。
    """

    def generate_advice(
        self,
        current_vdot: float | None = None,
        weekly_volume_km: float = 0.0,
        training_consistency: float = 1.0,
        ctl: float | None = None,
        atl: float | None = None,
        tsb: float | None = None,
        injury_risk: str = "low",
        recent_effort_scores: list[int] | None = None,
        goal_type: str | None = None,
    ) -> list[SmartTrainingAdvice]:
        """生成智能训练建议

        Args:
            current_vdot: 当前VDOT
            weekly_volume_km: 周跑量
            training_consistency: 训练一致性(0-1)
            ctl: 慢性训练负荷
            atl: 急性训练负荷
            tsb: 训练压力平衡
            injury_risk: 伤病风险(low/medium/high)
            recent_effort_scores: 近期体感评分列表
            goal_type: 目标类型

        Returns:
            list[SmartTrainingAdvice]: 建议列表
        """
        advices: list[SmartTrainingAdvice] = []

        advices.extend(
            self._generate_training_advice(
                current_vdot=current_vdot,
                weekly_volume_km=weekly_volume_km,
                training_consistency=training_consistency,
                goal_type=goal_type,
            )
        )

        advices.extend(
            self._generate_recovery_advice(
                ctl=ctl,
                atl=atl,
                tsb=tsb,
                recent_effort_scores=recent_effort_scores,
            )
        )

        advices.extend(
            self._generate_nutrition_advice(
                weekly_volume_km=weekly_volume_km,
                recent_effort_scores=recent_effort_scores,
            )
        )

        advices.extend(
            self._generate_injury_prevention_advice(
                weekly_volume_km=weekly_volume_km,
                injury_risk=injury_risk,
                training_consistency=training_consistency,
            )
        )

        advices.sort(key=lambda a: {"high": 0, "medium": 1, "low": 2}[a.priority])

        return advices

    def _generate_training_advice(
        self,
        current_vdot: float | None,
        weekly_volume_km: float,
        training_consistency: float,
        goal_type: str | None,
    ) -> list[SmartTrainingAdvice]:
        """生成训练建议"""
        advices: list[SmartTrainingAdvice] = []

        if weekly_volume_km < 20:
            advices.append(
                SmartTrainingAdvice(
                    advice_type="training",
                    content="逐步增加周跑量至30km以上，建立有氧基础",
                    priority="high",
                    context=f"当前周跑量{weekly_volume_km}km，低于基础训练量",
                    confidence=0.85,
                    related_metrics=["weekly_volume"],
                )
            )
        elif weekly_volume_km < 40:
            advices.append(
                SmartTrainingAdvice(
                    advice_type="training",
                    content="维持当前跑量，增加一次间歇训练提升速度",
                    priority="medium",
                    context=f"当前周跑量{weekly_volume_km}km，可增加训练质量",
                    confidence=0.75,
                    related_metrics=["weekly_volume", "interval_frequency"],
                )
            )

        if training_consistency < 0.5:
            advices.append(
                SmartTrainingAdvice(
                    advice_type="training",
                    content="提高训练规律性，确保每周至少3次训练",
                    priority="high",
                    context=f"训练一致性仅{training_consistency:.0%}，影响训练效果",
                    confidence=0.90,
                    related_metrics=["training_consistency"],
                )
            )

        if current_vdot and current_vdot < 35:
            advices.append(
                SmartTrainingAdvice(
                    advice_type="training",
                    content="以轻松跑为主，每周一次长距离跑，逐步提升有氧能力",
                    priority="medium",
                    context=f"当前VDOT {current_vdot:.1f}，处于初级水平",
                    confidence=0.80,
                    related_metrics=["vdot", "easy_run_ratio"],
                )
            )

        if goal_type in ("5k", "10k"):
            advices.append(
                SmartTrainingAdvice(
                    advice_type="training",
                    content="增加间歇训练和速度训练，提升短距离表现",
                    priority="medium",
                    context=f"目标为{goal_type}比赛，需要速度能力",
                    confidence=0.70,
                    related_metrics=["interval_pace", "vdot"],
                )
            )
        elif goal_type in ("half_marathon", "marathon"):
            advices.append(
                SmartTrainingAdvice(
                    advice_type="training",
                    content="增加长距离跑和阈值跑，提升耐力表现",
                    priority="medium",
                    context="目标为长距离比赛，需要耐力基础",
                    confidence=0.75,
                    related_metrics=["long_run_distance", "threshold_pace"],
                )
            )

        return advices

    def _generate_recovery_advice(
        self,
        ctl: float | None,
        atl: float | None,
        tsb: float | None,
        recent_effort_scores: list[int] | None,
    ) -> list[SmartTrainingAdvice]:
        """生成恢复建议"""
        advices: list[SmartTrainingAdvice] = []

        if tsb is not None and tsb < -20:
            advices.append(
                SmartTrainingAdvice(
                    advice_type="recovery",
                    content="训练压力过大，建议安排减量周，降低训练强度",
                    priority="high",
                    context=f"TSB为{tsb:.0f}，处于过度训练风险区",
                    confidence=0.85,
                    related_metrics=["tsb", "atl", "ctl"],
                )
            )
        elif tsb is not None and tsb < -10:
            advices.append(
                SmartTrainingAdvice(
                    advice_type="recovery",
                    content="注意恢复，确保每周至少2个恢复日",
                    priority="medium",
                    context=f"TSB为{tsb:.0f}，训练负荷偏高",
                    confidence=0.75,
                    related_metrics=["tsb"],
                )
            )

        if recent_effort_scores and len(recent_effort_scores) >= 3:
            avg_effort = sum(recent_effort_scores) / len(recent_effort_scores)
            if avg_effort > 7:
                advices.append(
                    SmartTrainingAdvice(
                        advice_type="recovery",
                        content="近期体感偏累，建议降低训练强度或增加恢复日",
                        priority="high",
                        context=f"近{len(recent_effort_scores)}次训练平均体感{avg_effort:.1f}/10",
                        confidence=0.80,
                        related_metrics=["effort_score"],
                    )
                )

        if ctl is not None and atl is not None:
            ratio = atl / ctl if ctl > 0 else 0
            if ratio > 1.5:
                advices.append(
                    SmartTrainingAdvice(
                        advice_type="recovery",
                        content="急性负荷过高，需要降低训练量让身体适应",
                        priority="high",
                        context=f"ATL/CTL比值{ratio:.1f}，超过安全阈值1.5",
                        confidence=0.85,
                        related_metrics=["atl", "ctl"],
                    )
                )

        return advices

    def _generate_nutrition_advice(
        self,
        weekly_volume_km: float,
        recent_effort_scores: list[int] | None,
    ) -> list[SmartTrainingAdvice]:
        """生成营养建议"""
        advices: list[SmartTrainingAdvice] = []

        if weekly_volume_km > 50:
            advices.append(
                SmartTrainingAdvice(
                    advice_type="nutrition",
                    content="增加碳水化合物摄入，确保长距离跑前充分储备糖原",
                    priority="medium",
                    context=f"周跑量{weekly_volume_km}km，能量消耗较大",
                    confidence=0.70,
                    related_metrics=["weekly_volume"],
                )
            )

        if weekly_volume_km > 30:
            advices.append(
                SmartTrainingAdvice(
                    advice_type="nutrition",
                    content="训练后30分钟内补充蛋白质和碳水，促进恢复",
                    priority="low",
                    context="规律训练需要及时营养补充",
                    confidence=0.65,
                    related_metrics=["weekly_volume"],
                )
            )

        return advices

    def _generate_injury_prevention_advice(
        self,
        weekly_volume_km: float,
        injury_risk: str,
        training_consistency: float,
    ) -> list[SmartTrainingAdvice]:
        """生成伤病预防建议"""
        advices: list[SmartTrainingAdvice] = []

        if injury_risk == "high":
            advices.append(
                SmartTrainingAdvice(
                    advice_type="injury_prevention",
                    content="当前伤病风险高，建议降低跑量并增加力量训练",
                    priority="high",
                    context="伤病风险评估为高风险",
                    confidence=0.85,
                    related_metrics=["injury_risk", "weekly_volume"],
                )
            )
        elif injury_risk == "medium":
            advices.append(
                SmartTrainingAdvice(
                    advice_type="injury_prevention",
                    content="注意身体信号，每周安排2次力量训练预防伤病",
                    priority="medium",
                    context="伤病风险评估为中等风险",
                    confidence=0.75,
                    related_metrics=["injury_risk"],
                )
            )

        if weekly_volume_km > 60:
            advices.append(
                SmartTrainingAdvice(
                    advice_type="injury_prevention",
                    content="高跑量下注意跑姿和路面选择，避免连续硬地训练",
                    priority="medium",
                    context=f"周跑量{weekly_volume_km}km，属于高跑量",
                    confidence=0.70,
                    related_metrics=["weekly_volume"],
                )
            )

        if training_consistency > 0.9 and weekly_volume_km > 40:
            advices.append(
                SmartTrainingAdvice(
                    advice_type="injury_prevention",
                    content="训练规律性好但跑量偏高，建议每4周安排一个减量周",
                    priority="low",
                    context="持续高负荷训练需要周期性减量",
                    confidence=0.65,
                    related_metrics=["training_consistency", "weekly_volume"],
                )
            )

        return advices
