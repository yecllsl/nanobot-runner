# NotifyTool端到端测试

"""
测试NotifyTool与Agent工具集成的端到端流程
"""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.agents.tools import RunnerTools, SendTrainingReminderTool
from src.core.models import DailyPlan, WeatherInfo
from src.core.plan.notify_tool import NotifyTool


class TestNotifyToolE2E:
    """NotifyTool端到端测试"""

    @pytest.fixture
    def mock_storage(self):
        """创建模拟存储管理器"""
        storage = Mock()
        storage.read_parquet = Mock(return_value=Mock())
        return storage

    @pytest.fixture
    def mock_profile_storage(self):
        """创建模拟画像存储管理器"""
        profile_storage = Mock()

        # 创建模拟用户画像
        profile = Mock()
        profile.to_dict = Mock(
            return_value={
                "estimated_vdot": 45.0,
                "weekly_avg_distance": 40.0,
                "age": 30,
                "resting_hr": 60,
                "enable_training_reminder": True,
                "weather_alert_enabled": True,
                "best_pace_min_per_km": 5.5,
            }
        )
        profile_storage.load_profile_json = Mock(return_value=profile)

        return profile_storage

    @pytest.fixture
    def runner_tools(self, mock_storage, mock_profile_storage):
        """创建RunnerTools实例"""
        with patch("src.agents.tools.StorageManager", return_value=mock_storage):
            with patch(
                "src.agents.tools.ProfileStorageManager",
                return_value=mock_profile_storage,
            ):
                tools = RunnerTools()
                tools.profile_storage = mock_profile_storage
                return tools

    def test_send_training_reminder_tool_creation(self, runner_tools):
        """测试工具创建"""
        tool = SendTrainingReminderTool(runner_tools)
        assert tool.name == "send_training_reminder"
        assert "训练提醒" in tool.description

    def test_send_training_reminder_tool_schema(self, runner_tools):
        """测试工具Schema"""
        tool = SendTrainingReminderTool(runner_tools)
        schema = tool.to_schema()

        assert schema["type"] == "function"
        assert schema["function"]["name"] == "send_training_reminder"
        assert "date" in schema["function"]["parameters"]["properties"]
        assert "check_do_not_disturb" in schema["function"]["parameters"]["properties"]

    @pytest.mark.asyncio
    async def test_send_training_reminder_no_profile(self, runner_tools):
        """测试无用户画像情况"""
        runner_tools.profile_storage.load_profile_json = Mock(return_value=None)

        tool = SendTrainingReminderTool(runner_tools)
        result = await tool.execute()

        # 解析JSON字符串
        import json

        result_dict = json.loads(result) if isinstance(result, str) else result
        assert "error" in result_dict
        assert "未找到用户画像" in result_dict["error"]

    @pytest.mark.asyncio
    async def test_send_training_reminder_no_plan(self, runner_tools):
        """测试无训练计划情况"""
        import json

        # Mock get_recent_runs 方法
        runner_tools.get_recent_runs = Mock(return_value=[])

        # Mock get_training_load 方法
        runner_tools.get_training_load = Mock(
            return_value={"atl": 0.0, "ctl": 0.0, "tsb": 0.0}
        )

        with patch("src.core.plan.plan_manager.PlanManager") as mock_plan_manager:
            mock_manager_instance = Mock()
            mock_manager_instance.get_active_plan = Mock(return_value=None)
            mock_plan_manager.return_value = mock_manager_instance

            tool = SendTrainingReminderTool(runner_tools)
            result = await tool.execute()

            # 解析JSON字符串
            result_dict = json.loads(result) if isinstance(result, str) else result
            # 由于 _run_sync 会将包含 message 字段的字典转换为 error 格式
            # 所以这里检查 error 字段
            assert "error" in result_dict
            assert "未找到激活的训练计划" in result_dict["error"]

    @pytest.mark.asyncio
    async def test_send_training_reminder_success(self, runner_tools):
        """测试成功发送提醒"""
        import json

        # Mock get_recent_runs 方法
        runner_tools.get_recent_runs = Mock(return_value=[])

        # Mock get_training_load 方法
        runner_tools.get_training_load = Mock(
            return_value={"atl": 50.0, "ctl": 60.0, "tsb": -10.0}
        )

        # 创建模拟训练计划
        mock_plan = Mock()
        mock_plan.weeks = []

        today = datetime.now().strftime("%Y-%m-%d")
        daily_plan = DailyPlan(
            date=today,
            workout_type="轻松跑",
            distance_km=10.0,
            duration_min=60,
        )

        mock_week = Mock()
        mock_week.daily_plans = [daily_plan]
        mock_plan.weeks = [mock_week]

        # Mock PlanManager
        with patch("src.core.plan.plan_manager.PlanManager") as mock_plan_manager:
            mock_manager_instance = Mock()
            mock_manager_instance.get_active_plan = Mock(return_value=mock_plan)
            mock_plan_manager.return_value = mock_manager_instance

            # Mock NotifyTool
            with patch("src.core.plan.notify_tool.NotifyTool") as mock_notify_tool:
                mock_notify_instance = Mock()
                mock_notify_instance.get_today_plan = Mock(return_value=daily_plan)
                # 修改返回结果，不包含 message 字段，避免被 _run_sync 转换
                mock_notify_instance.send_reminder = Mock(
                    return_value=Mock(
                        to_dict=Mock(
                            return_value={
                                "sent": True,
                                "skipped": False,
                            }
                        )
                    )
                )
                mock_notify_tool.return_value = mock_notify_instance

                tool = SendTrainingReminderTool(runner_tools)
                result = await tool.execute()

                # 解析JSON字符串
                result_dict = json.loads(result) if isinstance(result, str) else result
                assert result_dict.get("sent") is True
                assert result_dict.get("skipped") is False


class TestNotifyToolIntegration:
    """NotifyTool集成测试"""

    def test_notify_tool_with_feishu_bot(self):
        """测试NotifyTool与飞书机器人集成"""
        # 创建模拟飞书机器人
        mock_bot = Mock()
        mock_bot.send_card = Mock(
            return_value={"success": True, "data": {"message_id": "test_id"}}
        )

        # 创建NotifyTool
        notify_tool = NotifyTool(feishu_bot=mock_bot)

        # 验证集成
        assert notify_tool.feishu_bot == mock_bot

    def test_notify_tool_with_weather_service(self):
        """测试NotifyTool与天气服务集成"""
        # 创建模拟天气服务
        mock_weather = Mock()
        mock_weather.get_weather = Mock(
            return_value=WeatherInfo(
                condition="晴",
                temperature=22.0,
                humidity=60.0,
                wind_speed=3.5,
            )
        )

        # 创建NotifyTool
        notify_tool = NotifyTool(weather_service=mock_weather)

        # 验证集成
        assert notify_tool.weather_service == mock_weather

        # 测试获取天气
        weather = notify_tool.weather_service.get_weather()
        assert weather.condition == "晴"
        assert weather.temperature == 22.0

    def test_notify_tool_full_workflow(self):
        """测试NotifyTool完整工作流"""
        # 创建模拟依赖
        mock_bot = Mock()
        mock_bot.send_card = Mock(
            return_value={"success": True, "data": {"message_id": "test_id"}}
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
        # 关键：需要让 check_extreme_weather 返回 False，避免在免打扰检查中再次调用 get_weather
        mock_weather.check_extreme_weather = Mock(return_value=False)

        # 创建NotifyTool
        notify_tool = NotifyTool(feishu_bot=mock_bot, weather_service=mock_weather)

        # 创建测试数据
        daily_plan = DailyPlan(
            date="2026-04-03",
            workout_type="轻松跑",
            distance_km=10.0,
            duration_min=60,
            target_pace_min_per_km=6.0,
            target_hr_zone=2,
        )

        # 创建用户上下文
        from src.core.models import TrainingLoad, UserContext, UserPreferences

        profile = Mock()
        profile.to_dict = Mock(return_value={})

        preferences = UserPreferences(
            enable_training_reminder=True,
            weather_alert_enabled=True,
        )

        training_load = TrainingLoad(atl=50.0, ctl=60.0, tsb=-10.0)

        user_context = UserContext(
            profile=profile,
            recent_activities=[],
            training_load=training_load,
            preferences=preferences,
            historical_best_pace_min_per_km=5.5,
        )

        # 发送提醒（设置 check_do_not_disturb=False 避免在免打扰检查中调用 get_weather）
        result = notify_tool.send_reminder(
            daily_plan, user_context, check_do_not_disturb=False
        )

        # 验证结果
        assert result.sent is True
        assert result.skipped is False
        assert "成功" in result.message

        # 验证飞书机器人被调用
        mock_bot.send_card.assert_called_once()

        # 验证天气服务被调用（只调用1次）
        mock_weather.get_weather.assert_called_once()


class TestNotifyToolPerformance:
    """NotifyTool性能测试"""

    def test_send_reminder_response_time(self):
        """测试发送提醒响应时间"""
        import time

        # 创建模拟依赖
        mock_bot = Mock()
        mock_bot.send_card = Mock(
            return_value={"success": True, "data": {"message_id": "test_id"}}
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

        # 创建NotifyTool
        notify_tool = NotifyTool(feishu_bot=mock_bot, weather_service=mock_weather)

        # 创建测试数据
        daily_plan = DailyPlan(
            date="2026-04-03",
            workout_type="轻松跑",
            distance_km=10.0,
            duration_min=60,
        )

        from src.core.models import TrainingLoad, UserContext, UserPreferences

        profile = Mock()
        profile.to_dict = Mock(return_value={})
        preferences = UserPreferences(enable_training_reminder=True)
        training_load = TrainingLoad(atl=50.0, ctl=60.0, tsb=-10.0)

        user_context = UserContext(
            profile=profile,
            recent_activities=[],
            training_load=training_load,
            preferences=preferences,
            historical_best_pace_min_per_km=5.5,
        )

        # 测试响应时间
        start_time = time.time()
        result = notify_tool.send_reminder(daily_plan, user_context)
        end_time = time.time()

        # 验证响应时间 ≤ 5秒
        response_time = end_time - start_time
        assert response_time < 5.0, f"响应时间 {response_time:.2f}s 超过5秒限制"
        assert result.sent is True

    def test_batch_reminders_performance(self):
        """测试批量发送性能"""
        import time

        # 创建模拟依赖
        mock_bot = Mock()
        mock_bot.send_card = Mock(
            return_value={"success": True, "data": {"message_id": "test_id"}}
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

        # 创建NotifyTool
        notify_tool = NotifyTool(feishu_bot=mock_bot, weather_service=mock_weather)

        # 创建批量测试数据（10条）
        daily_plans = [
            DailyPlan(
                date=f"2026-04-{i:02d}",
                workout_type="轻松跑",
                distance_km=10.0,
                duration_min=60,
            )
            for i in range(1, 11)
        ]

        from src.core.models import TrainingLoad, UserContext, UserPreferences

        profile = Mock()
        profile.to_dict = Mock(return_value={})
        preferences = UserPreferences(enable_training_reminder=True)
        training_load = TrainingLoad(atl=50.0, ctl=60.0, tsb=-10.0)

        user_context = UserContext(
            profile=profile,
            recent_activities=[],
            training_load=training_load,
            preferences=preferences,
            historical_best_pace_min_per_km=5.5,
        )

        # 测试批量发送性能
        start_time = time.time()
        results = notify_tool.send_batch_reminders(daily_plans, user_context)
        end_time = time.time()

        # 验证批量发送时间
        batch_time = end_time - start_time
        assert batch_time < 10.0, f"批量发送时间 {batch_time:.2f}s 超过10秒限制"
        assert len(results) == 10
