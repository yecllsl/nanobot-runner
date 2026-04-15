# NotifyTool单元测试

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from src.core.models import (
    DailyPlan,
    NotifyResult,
    OperationResult,
    TrainingLoad,
    TrainingType,
    UserContext,
    UserPreferences,
    WeatherInfo,
)
from src.core.plan.notify_tool import (
    NotifyTool,
    SkipReason,
    WeatherCondition,
    WeatherService,
)


def create_test_daily_plan(
    date: str = "2026-04-03",
    workout_type: TrainingType = TrainingType.EASY,
    distance_km: float = 10.0,
    duration_min: int = 60,
) -> DailyPlan:
    """创建测试日计划"""
    return DailyPlan(
        date=date,
        workout_type=workout_type,
        distance_km=distance_km,
        duration_min=duration_min,
        target_pace_min_per_km=6.0,
        target_hr_zone=2,
        notes="测试训练",
    )


def create_test_user_context(
    enable_reminder: bool = True,
    weather_alert: bool = True,
    has_activity_today: bool = False,
    leave_dates: list = None,
    business_trip_dates: list = None,
    activity_date: str = None,
) -> UserContext:
    """创建测试用户上下文"""
    # 创建用户画像
    profile = Mock()
    profile_dict = {}
    if leave_dates:
        profile_dict["leave_dates"] = leave_dates
    if business_trip_dates:
        profile_dict["business_trip_dates"] = business_trip_dates
    profile.to_dict = Mock(return_value=profile_dict)

    # 创建最近活动
    recent_activities = []
    if has_activity_today:
        activity = Mock()
        if activity_date:
            activity.timestamp = datetime.strptime(activity_date, "%Y-%m-%d")
        else:
            activity.timestamp = datetime.now()
        recent_activities.append(activity)

    # 创建训练负荷
    training_load = TrainingLoad(
        atl=50.0,
        ctl=60.0,
        tsb=-10.0,
    )

    # 创建用户偏好
    preferences = UserPreferences(
        enable_training_reminder=enable_reminder,
        weather_alert_enabled=weather_alert,
    )

    return UserContext(
        profile=profile,
        recent_activities=recent_activities,
        training_load=training_load,
        preferences=preferences,
        historical_best_pace_min_per_km=5.5,
    )


class TestWeatherService:
    """测试天气服务"""

    def test_get_weather_returns_weather_info(self):
        """测试获取天气信息"""
        service = WeatherService()
        weather = service.get_weather()

        assert isinstance(weather, WeatherInfo)
        assert weather.condition is not None
        assert weather.temperature is not None
        assert weather.humidity is not None
        assert weather.wind_speed is not None

    def test_get_weather_with_date(self):
        """测试指定日期获取天气"""
        service = WeatherService()
        weather = service.get_weather(date="2026-04-03")

        assert isinstance(weather, WeatherInfo)

    def test_check_extreme_weather_normal(self):
        """测试正常天气"""
        service = WeatherService()
        weather = WeatherInfo(
            condition=WeatherCondition.CLEAR.value,
            temperature=22.0,
            humidity=60.0,
            wind_speed=3.5,
        )

        is_extreme = service.check_extreme_weather(weather)
        assert is_extreme is False

    def test_check_extreme_weather_high_temp(self):
        """测试高温天气"""
        service = WeatherService()
        weather = WeatherInfo(
            condition=WeatherCondition.CLEAR.value,
            temperature=36.0,  # 超过35度
            humidity=60.0,
            wind_speed=3.5,
        )

        is_extreme = service.check_extreme_weather(weather)
        assert is_extreme is True

    def test_check_extreme_weather_low_temp(self):
        """测试严寒天气"""
        service = WeatherService()
        weather = WeatherInfo(
            condition=WeatherCondition.CLEAR.value,
            temperature=-15.0,  # 低于-10度
            humidity=60.0,
            wind_speed=3.5,
        )

        is_extreme = service.check_extreme_weather(weather)
        assert is_extreme is True

    def test_check_extreme_weather_storm(self):
        """测试暴风雨天气"""
        service = WeatherService()
        weather = WeatherInfo(
            condition=WeatherCondition.STORM.value,
            temperature=22.0,
            humidity=80.0,
            wind_speed=10.0,
        )

        is_extreme = service.check_extreme_weather(weather)
        assert is_extreme is True

    def test_check_extreme_weather_strong_wind(self):
        """测试强风天气"""
        service = WeatherService()
        weather = WeatherInfo(
            condition=WeatherCondition.CLEAR.value,
            temperature=22.0,
            humidity=60.0,
            wind_speed=16.0,  # 超过15 m/s
        )

        is_extreme = service.check_extreme_weather(weather)
        assert is_extreme is True

    def test_check_extreme_weather_with_alert(self):
        """测试有预警的天气"""
        service = WeatherService()
        weather = WeatherInfo(
            condition=WeatherCondition.RAIN.value,
            temperature=22.0,
            humidity=70.0,
            wind_speed=5.0,
            alert="暴雨黄色预警",
        )

        is_extreme = service.check_extreme_weather(weather)
        assert is_extreme is True


class TestNotifyToolInit:
    """测试NotifyTool初始化"""

    def test_init_default(self):
        """测试默认初始化"""
        tool = NotifyTool()
        assert tool.feishu_bot is not None
        assert tool.weather_service is not None

    def test_init_with_custom_services(self):
        """测试自定义服务初始化"""
        mock_bot = Mock()
        mock_weather = Mock()
        tool = NotifyTool(feishu_bot=mock_bot, weather_service=mock_weather)

        assert tool.feishu_bot == mock_bot
        assert tool.weather_service == mock_weather


class TestNotifyToolSendReminder:
    """测试发送提醒"""

    @pytest.fixture
    def notify_tool(self):
        """创建NotifyTool实例"""
        mock_bot = Mock()
        mock_bot.send_card = Mock(
            return_value=OperationResult(
                success=True, data={"message_id": "test_msg_id"}
            )
        )
        mock_weather = Mock()
        mock_weather.get_weather = Mock(
            return_value=WeatherInfo(
                condition="晴",
                temperature=22.0,
                humidity=60.0,
                wind_speed=3.5,
            )
        )
        mock_weather.check_extreme_weather = Mock(return_value=False)

        return NotifyTool(feishu_bot=mock_bot, weather_service=mock_weather)

    def test_send_reminder_success(self, notify_tool):
        """测试成功发送提醒"""
        daily_plan = create_test_daily_plan()
        user_context = create_test_user_context()

        # Mock时间，避免免打扰时段检查（10:00不在免打扰时段）
        with patch("src.core.plan.notify_tool.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 4, 3, 10, 0, 0)
            mock_datetime.strftime = datetime.strftime

            result = notify_tool.send_reminder(daily_plan, user_context)

        assert isinstance(result, NotifyResult)
        assert result.sent is True
        assert result.skipped is False
        assert "成功" in result.message

    def test_send_reminder_disabled(self, notify_tool):
        """测试提醒功能禁用"""
        daily_plan = create_test_daily_plan()
        user_context = create_test_user_context(enable_reminder=False)

        result = notify_tool.send_reminder(daily_plan, user_context)

        assert result.sent is False
        assert result.skipped is True
        assert result.skip_reason == SkipReason.DISABLED.value

    def test_send_reminder_training_completed(self, notify_tool):
        """测试已完成训练"""
        daily_plan = create_test_daily_plan()
        user_context = create_test_user_context(
            has_activity_today=True, activity_date="2026-04-03"
        )

        result = notify_tool.send_reminder(daily_plan, user_context)

        assert result.sent is False
        assert result.skipped is True
        assert result.skip_reason == SkipReason.TRAINING_COMPLETED.value

    def test_send_reminder_rest_day(self, notify_tool):
        """测试休息日"""
        daily_plan = create_test_daily_plan(workout_type="休息")
        user_context = create_test_user_context()

        result = notify_tool.send_reminder(daily_plan, user_context)

        assert result.sent is False
        assert result.skipped is True
        assert result.skip_reason == SkipReason.REST_DAY.value

    def test_send_reminder_extreme_weather(self, notify_tool):
        """测试极端天气"""
        notify_tool.weather_service.check_extreme_weather = Mock(return_value=True)

        daily_plan = create_test_daily_plan()
        user_context = create_test_user_context()

        # Mock时间，避免免打扰时段检查
        with patch("src.core.plan.notify_tool.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 4, 3, 10, 0, 0)
            mock_datetime.strftime = datetime.strftime

            result = notify_tool.send_reminder(daily_plan, user_context)

        assert result.sent is False
        assert result.skipped is True
        assert result.skip_reason == SkipReason.EXTREME_WEATHER.value

    def test_send_reminder_leave_date(self, notify_tool):
        """测试请假日期"""
        daily_plan = create_test_daily_plan(date="2026-04-03")
        user_context = create_test_user_context(leave_dates=["2026-04-03"])

        result = notify_tool.send_reminder(daily_plan, user_context)

        assert result.sent is False
        assert result.skipped is True
        assert result.skip_reason == SkipReason.LEAVE_OR_BUSINESS_TRIP.value

    def test_send_reminder_business_trip(self, notify_tool):
        """测试出差日期"""
        daily_plan = create_test_daily_plan(date="2026-04-03")
        user_context = create_test_user_context(business_trip_dates=["2026-04-03"])

        result = notify_tool.send_reminder(daily_plan, user_context)

        assert result.sent is False
        assert result.skipped is True
        assert result.skip_reason == SkipReason.LEAVE_OR_BUSINESS_TRIP.value

    def test_send_reminder_send_failure(self, notify_tool):
        """测试发送失败"""
        notify_tool.feishu_bot.send_card = Mock(
            return_value=OperationResult(success=False, error="网络错误")
        )

        daily_plan = create_test_daily_plan()
        user_context = create_test_user_context()

        # Mock时间，避免免打扰时段检查
        with patch("src.core.plan.notify_tool.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 4, 3, 10, 0, 0)
            mock_datetime.strftime = datetime.strftime

            result = notify_tool.send_reminder(daily_plan, user_context)

        assert result.sent is False
        assert result.skipped is False
        assert "失败" in result.message

    def test_send_reminder_exception(self, notify_tool):
        """测试发送异常"""
        notify_tool.feishu_bot.send_card = Mock(side_effect=Exception("测试异常"))

        daily_plan = create_test_daily_plan()
        user_context = create_test_user_context()

        # Mock时间，避免免打扰时段检查
        with patch("src.core.plan.notify_tool.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 4, 3, 10, 0, 0)
            mock_datetime.strftime = datetime.strftime

            result = notify_tool.send_reminder(daily_plan, user_context)

        assert result.sent is False
        assert result.skipped is False
        assert "异常" in result.message

    def test_send_reminder_without_do_not_disturb_check(self, notify_tool):
        """测试跳过免打扰检查"""
        # 设置会触发免打扰的条件
        user_context = create_test_user_context(has_activity_today=True)
        daily_plan = create_test_daily_plan()

        # 不检查免打扰
        result = notify_tool.send_reminder(
            daily_plan, user_context, check_do_not_disturb=False
        )

        # 应该发送成功
        assert result.sent is True
        assert result.skipped is False


class TestNotifyToolCheckTrainingCompleted:
    """测试检查训练完成"""

    @pytest.fixture
    def notify_tool(self):
        """创建NotifyTool实例"""
        return NotifyTool()

    def test_check_training_completed_true(self, notify_tool):
        """测试已完成训练"""
        user_context = create_test_user_context(has_activity_today=True)
        today = datetime.now().strftime("%Y-%m-%d")

        result = notify_tool.check_training_completed(user_context, today)
        assert result is True

    def test_check_training_completed_false(self, notify_tool):
        """测试未完成训练"""
        user_context = create_test_user_context(has_activity_today=False)
        today = datetime.now().strftime("%Y-%m-%d")

        result = notify_tool.check_training_completed(user_context, today)
        assert result is False

    def test_check_training_completed_different_date(self, notify_tool):
        """测试不同日期"""
        user_context = create_test_user_context(has_activity_today=True)

        result = notify_tool.check_training_completed(user_context, "2026-04-01")
        assert result is False


class TestNotifyToolBuildMessage:
    """测试构建消息"""

    @pytest.fixture
    def notify_tool(self):
        """创建NotifyTool实例"""
        return NotifyTool()

    def test_build_reminder_message_basic(self, notify_tool):
        """测试构建基本消息"""
        daily_plan = create_test_daily_plan()
        weather_info = WeatherInfo(
            condition="晴",
            temperature=22.0,
            humidity=60.0,
            wind_speed=3.5,
        )

        message = notify_tool._build_reminder_message(daily_plan, weather_info)

        assert "轻松跑" in message
        assert "10.0 km" in message
        assert "60 分钟" in message
        assert "6'00" in message  # 配速
        assert "Zone 2" in message  # 心率区间
        assert "晴" in message
        assert "22.0°C" in message
        assert "测试训练" in message

    def test_build_reminder_message_with_alert(self, notify_tool):
        """测试构建带预警的消息"""
        daily_plan = create_test_daily_plan()
        weather_info = WeatherInfo(
            condition="雨",
            temperature=18.0,
            humidity=85.0,
            wind_speed=8.0,
            alert="暴雨黄色预警",
        )

        message = notify_tool._build_reminder_message(daily_plan, weather_info)

        assert "暴雨黄色预警" in message
        assert "⚠️" in message


class TestNotifyToolBatchReminders:
    """测试批量发送提醒"""

    @pytest.fixture
    def notify_tool(self):
        """创建NotifyTool实例"""
        mock_bot = Mock()
        mock_bot.send_card = Mock(
            return_value={"success": True, "data": {"message_id": "test_msg_id"}}
        )
        mock_weather = Mock()
        mock_weather.get_weather = Mock(
            return_value=WeatherInfo(
                condition="晴",
                temperature=22.0,
                humidity=60.0,
                wind_speed=3.5,
            )
        )
        mock_weather.check_extreme_weather = Mock(return_value=False)

        return NotifyTool(feishu_bot=mock_bot, weather_service=mock_weather)

    def test_send_batch_reminders(self, notify_tool):
        """测试批量发送提醒"""
        daily_plans = [
            create_test_daily_plan(date="2026-04-03"),
            create_test_daily_plan(date="2026-04-04"),
            create_test_daily_plan(date="2026-04-05"),
        ]
        user_context = create_test_user_context()

        results = notify_tool.send_batch_reminders(daily_plans, user_context)

        assert len(results) == 3
        assert all(isinstance(r, NotifyResult) for r in results)

    def test_send_batch_reminders_with_skip(self, notify_tool):
        """测试批量发送带跳过"""
        daily_plans = [
            create_test_daily_plan(date="2026-04-03"),
            create_test_daily_plan(date="2026-04-04", workout_type="休息"),
            create_test_daily_plan(date="2026-04-05"),
        ]
        user_context = create_test_user_context()

        results = notify_tool.send_batch_reminders(daily_plans, user_context)

        assert len(results) == 3
        assert results[1].skipped is True
        assert results[1].skip_reason == SkipReason.REST_DAY.value


class TestNotifyToolGetTodayPlan:
    """测试获取今日计划"""

    @pytest.fixture
    def notify_tool(self):
        """创建NotifyTool实例"""
        return NotifyTool()

    def test_get_today_plan_found(self, notify_tool):
        """测试找到今日计划"""
        today = datetime.now().strftime("%Y-%m-%d")
        daily_plan = create_test_daily_plan(date=today)

        # 创建模拟计划
        mock_plan = Mock()
        mock_week = Mock()
        mock_week.daily_plans = [daily_plan]
        mock_plan.weeks = [mock_week]

        plans = [mock_plan]
        user_context = create_test_user_context()

        result = notify_tool.get_today_plan(user_context, plans)

        assert result is not None
        assert result.date == today

    def test_get_today_plan_not_found(self, notify_tool):
        """测试未找到今日计划"""
        daily_plan = create_test_daily_plan(date="2026-04-01")

        mock_plan = Mock()
        mock_week = Mock()
        mock_week.daily_plans = [daily_plan]
        mock_plan.weeks = [mock_week]

        plans = [mock_plan]
        user_context = create_test_user_context()

        result = notify_tool.get_today_plan(user_context, plans)

        assert result is None


class TestNotifyToolDoNotDisturbTime:
    """测试免打扰时段检查"""

    @pytest.fixture
    def notify_tool(self):
        """创建NotifyTool实例"""
        return NotifyTool()

    def test_check_do_not_disturb_time_night(self, notify_tool):
        """测试夜间免打扰时段"""
        user_context = create_test_user_context()

        # Mock 当前时间为23:00
        with patch("src.core.plan.notify_tool.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 4, 3, 23, 0, 0)
            result = notify_tool._check_do_not_disturb_time(user_context)
            assert result is True

    def test_check_do_not_disturb_time_early_morning(self, notify_tool):
        """测试清晨免打扰时段"""
        user_context = create_test_user_context()

        # Mock 当前时间为06:00
        with patch("src.core.plan.notify_tool.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 4, 3, 6, 0, 0)
            result = notify_tool._check_do_not_disturb_time(user_context)
            assert result is True

    def test_check_do_not_disturb_time_daytime(self, notify_tool):
        """测试白天非免打扰时段"""
        user_context = create_test_user_context()

        # Mock 当前时间为10:00
        with patch("src.core.plan.notify_tool.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 4, 3, 10, 0, 0)
            result = notify_tool._check_do_not_disturb_time(user_context)
            assert result is False


class TestNotifyToolWeatherAlertDisabled:
    """测试天气预警禁用"""

    @pytest.fixture
    def notify_tool(self):
        """创建NotifyTool实例"""
        mock_bot = Mock()
        mock_bot.send_card = Mock(
            return_value=OperationResult(
                success=True, data={"message_id": "test_msg_id"}
            )
        )
        mock_weather = Mock()
        mock_weather.get_weather = Mock(
            return_value=WeatherInfo(
                condition="暴风雨",
                temperature=22.0,
                humidity=80.0,
                wind_speed=20.0,
            )
        )
        mock_weather.check_extreme_weather = Mock(return_value=True)

        return NotifyTool(feishu_bot=mock_bot, weather_service=mock_weather)

    def test_send_reminder_weather_alert_disabled(self, notify_tool):
        """测试天气预警禁用时不跳过"""
        daily_plan = create_test_daily_plan()
        user_context = create_test_user_context(weather_alert=False)

        # Mock时间，避免免打扰时段检查
        with patch("src.core.plan.notify_tool.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 4, 3, 10, 0, 0)
            mock_datetime.strftime = datetime.strftime

            result = notify_tool.send_reminder(daily_plan, user_context)

        # 天气预警禁用，应该发送成功
        assert result.sent is True
        assert result.skipped is False
