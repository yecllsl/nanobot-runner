# 通知提醒工具
# 通过飞书机器人按时提醒用户执行训练，支持智能免打扰

import logging
from datetime import datetime
from enum import StrEnum
from typing import Any

from src.core.models import DailyPlan, NotifyResult, UserContext, WeatherInfo
from src.notify.feishu import FeishuBot

logger = logging.getLogger(__name__)


class SkipReason(StrEnum):
    """免打扰原因"""

    TRAINING_COMPLETED = "已完成训练"
    LEAVE_OR_BUSINESS_TRIP = "请假/出差"
    EXTREME_WEATHER = "极端天气"
    REST_DAY = "休息日"
    DO_NOT_DISTURB_TIME = "免打扰时段"
    NO_PLAN = "无训练计划"
    DISABLED = "提醒功能已禁用"


class WeatherCondition(StrEnum):
    """天气状况"""

    CLEAR = "晴"
    CLOUDY = "多云"
    RAIN = "雨"
    HEAVY_RAIN = "大雨"
    STORM = "暴风雨"
    SNOW = "雪"
    FOG = "雾"
    EXTREME_HEAT = "高温"
    EXTREME_COLD = "严寒"


class WeatherService:
    """天气服务（Mock 实现）

    生产环境可替换为 OpenWeatherMap 等真实天气 API
    """

    # 极端天气阈值
    EXTREME_HEAT_TEMP = 35.0  # 高温阈值（摄氏度）
    EXTREME_COLD_TEMP = -10.0  # 严寒阈值（摄氏度）
    HEAVY_RAIN_THRESHOLD = 25.0  # 大雨阈值（mm/h）
    STRONG_WIND_SPEED = 15.0  # 强风阈值（m/s）

    def __init__(self, api_key: str | None = None, city: str = "北京"):
        """
        初始化天气服务

        Args:
            api_key: API密钥（Mock模式下可选）
            city: 城市名称
        """
        self.api_key = api_key
        self.city = city

    def get_weather(self, date: str | None = None) -> WeatherInfo:
        """
        获取天气信息

        Args:
            date: 日期（YYYY-MM-DD），不指定则为今天

        Returns:
            WeatherInfo: 天气信息
        """
        # Mock 实现：返回模拟天气数据
        # 生产环境应调用真实天气 API
        logger.info(f"获取天气信息（Mock）：城市={self.city}, 日期={date or '今天'}")

        # 模拟正常天气
        return WeatherInfo(
            condition=WeatherCondition.CLEAR.value,
            temperature=22.0,
            humidity=60.0,
            wind_speed=3.5,
            alert=None,
        )

    def check_extreme_weather(self, weather: WeatherInfo) -> bool:
        """
        检查是否为极端天气

        Args:
            weather: 天气信息

        Returns:
            bool: 是否为极端天气
        """
        # 检查温度
        if weather.temperature >= self.EXTREME_HEAT_TEMP:
            return True
        if weather.temperature <= self.EXTREME_COLD_TEMP:
            return True

        # 检查天气状况
        extreme_conditions = [
            WeatherCondition.HEAVY_RAIN.value,
            WeatherCondition.STORM.value,
            WeatherCondition.EXTREME_HEAT.value,
            WeatherCondition.EXTREME_COLD.value,
        ]
        if weather.condition in extreme_conditions:
            return True

        # 检查风力
        if weather.wind_speed >= self.STRONG_WIND_SPEED:
            return True

        # 检查预警
        return bool(weather.alert)


class NotifyTool:
    """通知提醒工具

    职责：
    1. 通过飞书机器人发送训练提醒
    2. 智能免打扰检查
    3. 天气预警集成
    """

    def __init__(
        self,
        feishu_bot: FeishuBot | None = None,
        weather_service: WeatherService | None = None,
    ):
        """
        初始化通知工具

        Args:
            feishu_bot: 飞书机器人实例
            weather_service: 天气服务实例
        """
        self.feishu_bot = feishu_bot or FeishuBot()
        self.weather_service = weather_service or WeatherService()

    def send_reminder(
        self,
        daily_plan: DailyPlan,
        user_context: UserContext,
        check_do_not_disturb: bool = True,
    ) -> NotifyResult:
        """
        发送训练提醒

        Args:
            daily_plan: 日训练计划
            user_context: 用户上下文
            check_do_not_disturb: 是否检查免打扰规则

        Returns:
            NotifyResult: 通知结果
        """
        logger.info(
            f"准备发送训练提醒：日期={daily_plan.date}, 类型={daily_plan.workout_type}"
        )

        # 检查免打扰规则
        if check_do_not_disturb:
            skip_reason = self._check_do_not_disturb(daily_plan, user_context)
            if skip_reason:
                logger.info(f"跳过提醒：{skip_reason.value}")
                return NotifyResult(
                    sent=False,
                    message=f"跳过提醒：{skip_reason.value}",
                    skipped=True,
                    skip_reason=skip_reason.value,
                )

        # 获取天气信息
        weather_info = self.weather_service.get_weather(daily_plan.date)

        # 构建提醒消息
        message = self._build_reminder_message(daily_plan, weather_info)

        # 发送飞书消息
        try:
            result = self.feishu_bot.send_card(
                title="🏃 训练提醒",
                content=message,
            )

            if result.success:
                logger.info(f"训练提醒发送成功：{daily_plan.date}")
                return NotifyResult(
                    sent=True,
                    message="训练提醒发送成功",
                    skipped=False,
                    weather_info=weather_info,
                )
            else:
                error_msg = result.error or "未知错误"
                logger.error(f"训练提醒发送失败：{error_msg}")
                return NotifyResult(
                    sent=False,
                    message=f"发送失败：{error_msg}",
                    skipped=False,
                    weather_info=weather_info,
                )

        except Exception as e:
            logger.error(f"发送训练提醒异常：{e}", exc_info=True)
            return NotifyResult(
                sent=False,
                message=f"发送异常：{str(e)}",
                skipped=False,
            )

    def _check_do_not_disturb(
        self, daily_plan: DailyPlan, user_context: UserContext
    ) -> SkipReason | None:
        """
        检查免打扰规则

        Args:
            daily_plan: 日训练计划
            user_context: 用户上下文

        Returns:
            Optional[SkipReason]: 免打扰原因，None表示不跳过
        """
        # 规则1：检查提醒功能是否启用
        if not user_context.preferences.enable_training_reminder:
            return SkipReason.DISABLED

        # 规则2：检查是否已完成训练
        if self.check_training_completed(user_context, daily_plan.date):
            return SkipReason.TRAINING_COMPLETED

        # 规则3：检查是否请假/出差
        if self._check_leave_or_business_trip(user_context, daily_plan.date):
            return SkipReason.LEAVE_OR_BUSINESS_TRIP

        # 规则4：检查是否为休息日
        if daily_plan.workout_type == "休息":
            return SkipReason.REST_DAY

        # 规则5：检查是否在免打扰时段
        if self._check_do_not_disturb_time(user_context):
            return SkipReason.DO_NOT_DISTURB_TIME

        # 规则6：检查极端天气
        if user_context.preferences.weather_alert_enabled:
            weather_info = self.weather_service.get_weather(daily_plan.date)
            if self.weather_service.check_extreme_weather(weather_info):
                return SkipReason.EXTREME_WEATHER

        return None

    def check_training_completed(self, user_context: UserContext, date: str) -> bool:
        """
        检查是否已完成训练

        Args:
            user_context: 用户上下文
            date: 日期（YYYY-MM-DD）

        Returns:
            bool: 是否已完成训练
        """
        # 检查最近活动中是否有当天的训练记录
        for activity in user_context.recent_activities:
            if hasattr(activity, "timestamp"):
                activity_date = str(activity.timestamp)[:10]
                if activity_date == date:
                    logger.info(f"检测到当天已完成训练：{date}")
                    return True

        return False

    def _check_leave_or_business_trip(
        self, user_context: UserContext, date: str
    ) -> bool:
        """
        检查是否请假/出差

        Args:
            user_context: 用户上下文
            date: 日期（YYYY-MM-DD）

        Returns:
            bool: 是否请假/出差
        """
        # 从用户画像或配置中检查请假/出差状态
        # 这里简化实现，实际应从 profile 中读取
        profile_dict = (
            user_context.profile.to_dict()
            if hasattr(user_context.profile, "to_dict")
            else {}
        )

        # 检查请假日期列表
        leave_dates = profile_dict.get("leave_dates", [])
        if date in leave_dates:
            logger.info(f"检测到请假日期：{date}")
            return True

        # 检查出差日期列表
        business_trip_dates = profile_dict.get("business_trip_dates", [])
        if date in business_trip_dates:
            logger.info(f"检测到出差日期：{date}")
            return True

        return False

    def _check_do_not_disturb_time(self, user_context: UserContext) -> bool:
        """
        检查是否在免打扰时段

        Args:
            user_context: 用户上下文

        Returns:
            bool: 是否在免打扰时段
        """
        # 获取当前时间
        now = datetime.now()
        current_time = now.strftime("%H:%M")

        # 从用户偏好中获取免打扰时段
        # 这里简化实现，实际应支持配置多个时段

        # 默认免打扰时段：22:00 - 07:00
        do_not_disturb_start = "22:00"
        do_not_disturb_end = "07:00"

        # 检查是否在免打扰时段
        if do_not_disturb_start <= current_time or current_time < do_not_disturb_end:
            logger.info(f"当前时间 {current_time} 在免打扰时段")
            return True

        return False

    def _build_reminder_message(
        self, daily_plan: DailyPlan, weather_info: WeatherInfo
    ) -> str:
        """
        构建提醒消息内容

        Args:
            daily_plan: 日训练计划
            weather_info: 天气信息

        Returns:
            str: 消息内容
        """
        lines = []

        # 训练类型和距离
        lines.append(f"**训练类型**：{daily_plan.workout_type.label}")
        lines.append(f"**训练距离**：{daily_plan.distance_km:.1f} km")
        lines.append(f"**预计时长**：{daily_plan.duration_min} 分钟")

        # 目标配速
        if daily_plan.target_pace_min_per_km:
            pace = daily_plan.target_pace_min_per_km
            pace_str = f"{int(pace)}'{int((pace - int(pace)) * 60):02d}\"/km"
            lines.append(f"**目标配速**：{pace_str}")

        # 目标心率区间
        if daily_plan.target_hr_zone:
            lines.append(f"**目标心率区间**：Zone {daily_plan.target_hr_zone}")

        # 天气信息
        lines.append("")
        lines.append("**天气情况**：")
        lines.append(f"- 天气：{weather_info.condition}")
        lines.append(f"- 温度：{weather_info.temperature:.1f}°C")
        lines.append(f"- 湿度：{weather_info.humidity:.0f}%")
        lines.append(f"- 风速：{weather_info.wind_speed:.1f} m/s")

        # 天气预警
        if weather_info.alert:
            lines.append(f"- ⚠️ 预警：{weather_info.alert}")

        # 训练备注
        if daily_plan.notes:
            lines.append("")
            lines.append(f"**备注**：{daily_plan.notes}")

        return "\n".join(lines)

    def send_batch_reminders(
        self,
        daily_plans: list[DailyPlan],
        user_context: UserContext,
    ) -> list[NotifyResult]:
        """
        批量发送训练提醒

        Args:
            daily_plans: 日训练计划列表
            user_context: 用户上下文

        Returns:
            List[NotifyResult]: 通知结果列表
        """
        results = []

        for daily_plan in daily_plans:
            result = self.send_reminder(daily_plan, user_context)
            results.append(result)

        return results

    def get_today_plan(
        self, user_context: UserContext, plans: list[Any]
    ) -> DailyPlan | None:
        """
        获取今日训练计划

        Args:
            user_context: 用户上下文
            plans: 训练计划列表

        Returns:
            Optional[DailyPlan]: 今日训练计划，无则返回None
        """
        today = datetime.now().strftime("%Y-%m-%d")

        for plan in plans:
            if hasattr(plan, "weeks"):
                for week in plan.weeks:
                    if hasattr(week, "daily_plans"):
                        for daily_plan in week.daily_plans:
                            if daily_plan.date == today:
                                return daily_plan

        return None
