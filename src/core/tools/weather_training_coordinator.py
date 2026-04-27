# 天气+训练协同模块
# 负责整合天气数据和训练数据,生成综合训练建议

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WeatherData:
    """天气数据（不可变数据类）

    Attributes:
        temperature: 温度（摄氏度）
        humidity: 湿度（百分比）
        weather: 天气状况（晴/阴/雨/雪等）
        wind: 风力描述
        location: 位置
        precipitation: 降水概率（百分比）
        uv_index: 紫外线指数
    """

    temperature: float
    humidity: float
    weather: str
    wind: str = "无风"
    location: str = "未知"
    precipitation: float = 0.0
    uv_index: float = 0.0


@dataclass(frozen=True)
class TrainingData:
    """训练数据摘要（不可变数据类）

    Attributes:
        recent_distance_km: 最近一周跑量（公里）
        avg_vdot: 平均VDOT值
        training_load: 训练负荷（CTL）
        recovery_status: 恢复状态
        last_run_date: 最近一次跑步日期
    """

    recent_distance_km: float
    avg_vdot: float | None
    training_load: float | None
    recovery_status: str
    last_run_date: str | None


@dataclass(frozen=True)
class WeatherTrainingAdvice:
    """天气+训练综合建议（不可变数据类）

    Attributes:
        advice_type: 建议类型（training/recovery/nutrition/safety）
        content: 建议内容
        priority: 优先级（high/medium/low）
        reason: 建议原因
        weather_impact: 天气影响说明
        training_impact: 训练影响说明
    """

    advice_type: str
    content: str
    priority: str
    reason: str
    weather_impact: str
    training_impact: str


class WeatherTrainingCoordinator:
    """天气+训练协同协调器

    负责整合天气数据和训练数据,生成综合训练建议。
    支持多种天气场景和训练状态的智能建议生成。

    协调器不直接调用工具,而是接收已获取的数据进行整合分析。
    工具调用由nanobot SDK的Agent自动处理。
    """

    def __init__(self) -> None:
        """初始化协调器"""
        pass

    def generate_advice(
        self, weather_data: WeatherData, training_data: TrainingData
    ) -> list[WeatherTrainingAdvice]:
        """生成综合训练建议

        根据天气数据和训练数据,生成多维度的训练建议。

        Args:
            weather_data: 天气数据
            training_data: 训练数据

        Returns:
            list[WeatherTrainingAdvice]: 综合建议列表
        """
        advices: list[WeatherTrainingAdvice] = []

        # 1. 高温天气建议
        if weather_data.temperature > 30:
            advices.append(
                WeatherTrainingAdvice(
                    advice_type="safety",
                    content="高温天气,建议避开中午时段训练,选择清晨或傍晚",
                    priority="high",
                    reason=f"当前温度{weather_data.temperature}°C,超过30°C高温警戒线",
                    weather_impact="高温会增加脱水和中暑风险",
                    training_impact="心率会偏高,体感评分可能上升",
                )
            )
            advices.append(
                WeatherTrainingAdvice(
                    advice_type="nutrition",
                    content="高温天气需增加补水,建议每15-20分钟补充150-200ml水分",
                    priority="high",
                    reason="高温环境下水分流失加快",
                    weather_impact="高温加速汗液蒸发",
                    training_impact="脱水会影响运动表现和恢复",
                )
            )

        # 2. 低温天气建议
        elif weather_data.temperature < 5:
            advices.append(
                WeatherTrainingAdvice(
                    advice_type="safety",
                    content="低温天气,建议充分热身15-20分钟,穿着保暖装备",
                    priority="high",
                    reason=f"当前温度{weather_data.temperature}°C,低于5°C低温警戒线",
                    weather_impact="低温会增加肌肉拉伤风险",
                    training_impact="肌肉弹性下降,需要更长热身时间",
                )
            )

        # 3. 降雨天气建议
        if weather_data.precipitation > 50:
            advices.append(
                WeatherTrainingAdvice(
                    advice_type="training",
                    content="降雨概率较高,建议选择室内训练或穿戴防雨装备",
                    priority="medium",
                    reason=f"降水概率{weather_data.precipitation}%,超过50%",
                    weather_impact="路面湿滑,能见度降低",
                    training_impact="配速可能受影响,安全风险增加",
                )
            )

        # 4. 高湿度天气建议
        if weather_data.humidity > 80:
            advices.append(
                WeatherTrainingAdvice(
                    advice_type="training",
                    content="湿度较高,体感温度会比实际温度高,建议降低训练强度",
                    priority="medium",
                    reason=f"当前湿度{weather_data.humidity}%,超过80%",
                    weather_impact="高湿度影响汗液蒸发,散热困难",
                    training_impact="心率漂移可能加剧,体感更累",
                )
            )

        # 5. 强风天气建议
        if "大风" in weather_data.wind or "7级" in weather_data.wind:
            advices.append(
                WeatherTrainingAdvice(
                    advice_type="training",
                    content="风力较大,建议选择避风路线或降低配速预期",
                    priority="medium",
                    reason=f"当前风力: {weather_data.wind}",
                    weather_impact="强风增加空气阻力",
                    training_impact="相同配速下心率会偏高",
                )
            )

        # 6. 紫外线强度建议
        if weather_data.uv_index > 6:
            advices.append(
                WeatherTrainingAdvice(
                    advice_type="safety",
                    content="紫外线强度较高,建议涂抹防晒霜,佩戴遮阳帽",
                    priority="low",
                    reason=f"紫外线指数{weather_data.uv_index},超过6(强)",
                    weather_impact="紫外线强会增加皮肤损伤风险",
                    training_impact="长时间暴露可能影响运动表现",
                )
            )

        # 7. 结合训练数据的建议
        if training_data.recent_distance_km > 60 and weather_data.temperature > 25:
            advices.append(
                WeatherTrainingAdvice(
                    advice_type="recovery",
                    content="周跑量较大且气温较高,建议本周增加恢复跑比例",
                    priority="high",
                    reason=f"周跑量{training_data.recent_distance_km}km,温度{weather_data.temperature}°C",
                    weather_impact="高温环境下恢复速度变慢",
                    training_impact="疲劳累积风险增加",
                )
            )

        # 8. 训练负荷建议
        if (
            training_data.training_load is not None
            and training_data.training_load > 50
            and weather_data.temperature > 28
        ):
            advices.append(
                WeatherTrainingAdvice(
                    advice_type="training",
                    content="训练负荷较高且气温偏高,建议今日进行轻松跑或休息",
                    priority="high",
                    reason=f"训练负荷CTL={training_data.training_load},温度{weather_data.temperature}°C",
                    weather_impact="高温会放大训练负荷的影响",
                    training_impact="过度训练风险增加",
                )
            )

        # 9. 恢复状态建议
        if training_data.recovery_status == "疲劳" and weather_data.weather in [
            "雨",
            "雪",
        ]:
            advices.append(
                WeatherTrainingAdvice(
                    advice_type="recovery",
                    content="恢复状态不佳且天气恶劣,建议今日休息或室内交叉训练",
                    priority="high",
                    reason=f"恢复状态: {training_data.recovery_status},天气: {weather_data.weather}",
                    weather_impact="恶劣天气增加训练压力",
                    training_impact="疲劳状态下训练效果不佳",
                )
            )

        # 10. 默认建议（无特殊天气情况）
        if not advices:
            advices.append(
                WeatherTrainingAdvice(
                    advice_type="training",
                    content="天气条件良好,适合按计划训练",
                    priority="low",
                    reason="当前天气条件对训练影响较小",
                    weather_impact="无特殊影响",
                    training_impact="可正常训练",
                )
            )

        return advices

    def analyze_weather_impact(self, weather_data: WeatherData) -> dict[str, Any]:
        """分析天气对训练的影响

        Args:
            weather_data: 天气数据

        Returns:
            dict: 天气影响分析结果
        """
        impact_level = "low"
        impact_factors: list[str] = []

        if weather_data.temperature > 30:
            impact_level = "high"
            impact_factors.append("高温")
        elif weather_data.temperature < 5:
            impact_level = "high"
            impact_factors.append("低温")

        if weather_data.precipitation > 50:
            impact_level = "high" if impact_level == "high" else "medium"
            impact_factors.append("降雨")

        if weather_data.humidity > 80:
            impact_level = "high" if impact_level == "high" else "medium"
            impact_factors.append("高湿度")

        if "大风" in weather_data.wind or "7级" in weather_data.wind:
            impact_level = "high" if impact_level == "high" else "medium"
            impact_factors.append("强风")

        return {
            "impact_level": impact_level,
            "impact_factors": impact_factors,
            "recommendation": self._get_weather_recommendation(impact_level),
        }

    def _get_weather_recommendation(self, impact_level: str) -> str:
        """根据影响等级获取建议

        Args:
            impact_level: 影响等级（low/medium/high）

        Returns:
            str: 建议内容
        """
        recommendations = {
            "low": "天气条件良好,适合正常训练",
            "medium": "天气有一定影响,建议适当调整训练计划",
            "high": "天气影响较大,建议谨慎训练或调整训练方式",
        }
        return recommendations.get(impact_level, "建议根据实际情况调整训练")

    def format_advice_for_display(self, advices: list[WeatherTrainingAdvice]) -> str:
        """格式化建议用于显示

        Args:
            advices: 建议列表

        Returns:
            str: 格式化后的建议文本
        """
        if not advices:
            return "暂无训练建议"

        lines: list[str] = ["## 天气+训练综合建议\n"]

        # 按优先级排序
        priority_order = {"high": 0, "medium": 1, "low": 2}
        sorted_advices = sorted(
            advices, key=lambda x: priority_order.get(x.priority, 3)
        )

        for i, advice in enumerate(sorted_advices, 1):
            priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}
            emoji = priority_emoji.get(advice.priority, "⚪")

            lines.append(f"### {i}. {emoji} {advice.content}")
            lines.append(f"- **类型**: {advice.advice_type}")
            lines.append(f"- **优先级**: {advice.priority}")
            lines.append(f"- **原因**: {advice.reason}")
            lines.append(f"- **天气影响**: {advice.weather_impact}")
            lines.append(f"- **训练影响**: {advice.training_impact}")
            lines.append("")

        return "\n".join(lines)
