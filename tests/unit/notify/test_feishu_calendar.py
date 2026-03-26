# 飞书日历同步服务单元测试

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.training_plan import (
    DailyPlan,
    FitnessLevel,
    PlanType,
    TrainingPlan,
    WeeklySchedule,
    WorkoutType,
)
from src.notify.feishu_calendar import (
    CalendarEventCreateRequest,
    CalendarSyncConfig,
    FeishuCalendarAPI,
    FeishuCalendarSync,
    SyncResult,
)


class TestCalendarSyncConfig:
    """测试 CalendarSyncConfig 配置类"""

    def test_default_config(self):
        """测试默认配置"""
        config = CalendarSyncConfig()
        assert config.enabled is True
        assert config.calendar_id is None
        assert config.reminder_minutes == 60
        assert config.sync_completed is False
        assert config.include_description is True
        assert config.app_id is None
        assert config.app_secret is None

    def test_custom_config(self):
        """测试自定义配置"""
        config = CalendarSyncConfig(
            enabled=False,
            calendar_id="test_calendar_id",
            reminder_minutes=30,
            sync_completed=True,
            include_description=False,
            app_id="test_app_id",
            app_secret="test_app_secret",
        )
        assert config.enabled is False
        assert config.calendar_id == "test_calendar_id"
        assert config.reminder_minutes == 30
        assert config.sync_completed is True
        assert config.include_description is False
        assert config.app_id == "test_app_id"
        assert config.app_secret == "test_app_secret"


class TestSyncResult:
    """测试 SyncResult 同步结果类"""

    def test_success_result(self):
        """测试成功结果"""
        result = SyncResult(
            success=True,
            message="同步成功",
            event_id="event_123",
            details={"count": 1},
        )
        assert result.success is True
        assert result.message == "同步成功"
        assert result.event_id == "event_123"
        assert result.error is None
        assert result.details == {"count": 1}

    def test_error_result(self):
        """测试错误结果"""
        result = SyncResult(
            success=False,
            message="同步失败",
            error="网络错误",
        )
        assert result.success is False
        assert result.message == "同步失败"
        assert result.event_id is None
        assert result.error == "网络错误"
        assert result.details is None


class TestCalendarEventCreateRequest:
    """测试 CalendarEventCreateRequest 事件创建请求类"""

    def test_create_request(self):
        """测试创建事件请求"""
        start_time = datetime(2024, 1, 1, 6, 0)
        end_time = datetime(2024, 1, 1, 7, 0)
        request = CalendarEventCreateRequest(
            summary="🏃 轻松跑 - 10 公里",
            start_time=start_time,
            end_time=end_time,
            description="训练说明",
            reminders=[{"method": "app_push", "minutes": 60}],
        )
        assert request.summary == "🏃 轻松跑 - 10 公里"
        assert request.start_time == start_time
        assert request.end_time == end_time
        assert request.description == "训练说明"
        assert len(request.reminders) == 1


class TestFeishuCalendarAPI:
    """测试 FeishuCalendarAPI 日历 API 封装类"""

    @pytest.fixture
    def mock_config(self):
        """模拟配置"""
        return {
            "app_id": "test_app_id",
            "app_secret": "test_app_secret",
        }

    @pytest.fixture
    def api(self, mock_config):
        """创建 API 实例"""
        return FeishuCalendarAPI(
            mock_config["app_id"],
            mock_config["app_secret"],
        )

    def test_init(self, api, mock_config):
        """测试初始化"""
        assert api.app_id == mock_config["app_id"]
        assert api.app_secret == mock_config["app_secret"]
        assert api._access_token is None
        assert api._token_expire_time is None

    @patch("src.notify.feishu_calendar.requests.post")
    def test_get_access_token_success(self, mock_post, api):
        """测试成功获取访问令牌"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "tenant_access_token": "test_token",
        }
        mock_post.return_value = mock_response

        token = api._get_access_token()

        assert token == "test_token"
        assert api._access_token == "test_token"
        assert api._token_expire_time is not None

    @patch("src.notify.feishu_calendar.requests.post")
    def test_get_access_token_failure(self, mock_post, api):
        """测试获取访问令牌失败"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 99991661,
            "msg": "app_access_token_invalid",
        }
        mock_post.return_value = mock_response

        with pytest.raises(RuntimeError, match="获取飞书访问令牌失败"):
            api._get_access_token()

    @patch("src.notify.feishu_calendar.requests.post")
    def test_get_access_token_cached(self, mock_post, api):
        """测试使用缓存的访问令牌"""
        # 先获取一次令牌
        api._access_token = "cached_token"
        import time

        # 设置一个未来的过期时间
        api._token_expire_time = time.time() + 3600

        token = api._get_access_token()

        assert token == "cached_token"
        mock_post.assert_not_called()

    @patch("src.notify.feishu_calendar.FeishuCalendarAPI._get_headers")
    @patch("src.notify.feishu_calendar.requests.request")
    def test_create_event(self, mock_request, mock_get_headers, api):
        """测试创建日历事件"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {"event_id": "test_event_id"},
        }
        mock_request.return_value = mock_response
        mock_get_headers.return_value = {"Authorization": "Bearer test_token"}

        event = CalendarEventCreateRequest(
            summary="测试事件",
            start_time=datetime(2024, 1, 1, 6, 0),
            end_time=datetime(2024, 1, 1, 7, 0),
            description="测试描述",
            reminders=[{"method": "app_push", "minutes": 60}],
        )

        result = asyncio.run(api.create_event("calendar_id", event))

        assert result == {"event_id": "test_event_id"}
        mock_request.assert_called_once()

    @patch("src.notify.feishu_calendar.FeishuCalendarAPI._get_headers")
    @patch("src.notify.feishu_calendar.requests.request")
    def test_update_event(self, mock_request, mock_get_headers, api):
        """测试更新日历事件"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {"event_id": "test_event_id"},
        }
        mock_request.return_value = mock_response
        # Mock _get_headers 返回包含 Content-Type 的完整 headers
        mock_get_headers.return_value = {
            "Authorization": "Bearer test_token",
            "Content-Type": "application/json",
        }

        update_data = {"summary": "更新后的标题"}

        result = asyncio.run(api.update_event("calendar_id", "event_id", update_data))

        assert result == {"event_id": "test_event_id"}
        mock_request.assert_called_once_with(
            "PATCH",
            "https://open.feishu.cn/open-apis/calendar/v4/calendars/calendar_id/events/event_id",
            params=None,
            json=update_data,
            headers={
                "Authorization": "Bearer test_token",
                "Content-Type": "application/json",
            },
            timeout=10,
        )

    @patch("src.notify.feishu_calendar.FeishuCalendarAPI._get_headers")
    @patch("src.notify.feishu_calendar.requests.request")
    def test_delete_event(self, mock_request, mock_get_headers, api):
        """测试删除日历事件"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {},
        }
        mock_request.return_value = mock_response
        mock_get_headers.return_value = {"Authorization": "Bearer test_token"}

        result = asyncio.run(api.delete_event("calendar_id", "event_id"))

        assert result == {}
        mock_request.assert_called_once()

    @patch("src.notify.feishu_calendar.FeishuCalendarAPI._get_headers")
    @patch("src.notify.feishu_calendar.requests.request")
    def test_get_event(self, mock_request, mock_get_headers, api):
        """测试获取日历事件"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {"event_id": "test_event_id", "summary": "测试事件"},
        }
        mock_request.return_value = mock_response
        mock_get_headers.return_value = {"Authorization": "Bearer test_token"}

        result = asyncio.run(api.get_event("calendar_id", "event_id"))

        assert result == {"event_id": "test_event_id", "summary": "测试事件"}
        mock_request.assert_called_once()

    @patch("src.notify.feishu_calendar.FeishuCalendarAPI._get_headers")
    @patch("src.notify.feishu_calendar.requests.request")
    def test_get_calendar_list(self, mock_request, mock_get_headers, api):
        """测试获取日历列表"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "items": [
                    {"calendar_id": "cal1", "summary": "日历 1"},
                    {"calendar_id": "cal2", "summary": "日历 2"},
                ]
            },
        }
        mock_request.return_value = mock_response
        mock_get_headers.return_value = {"Authorization": "Bearer test_token"}

        result = asyncio.run(api.get_calendar_list())

        assert len(result) == 2
        assert result[0]["calendar_id"] == "cal1"
        assert result[1]["calendar_id"] == "cal2"


class TestFeishuCalendarSync:
    """测试 FeishuCalendarSync 日历同步服务类"""

    @pytest.fixture
    def mock_config(self):
        """模拟配置"""
        return CalendarSyncConfig(
            enabled=True,
            calendar_id="test_calendar_id",
            reminder_minutes=60,
            sync_completed=False,
            include_description=True,
            app_id="test_app_id",
            app_secret="test_app_secret",
        )

    @pytest.fixture
    def mock_api(self):
        """创建 Mock API 实例"""
        mock_api_instance = MagicMock()
        mock_api_instance.create_event = AsyncMock()
        mock_api_instance.update_event = AsyncMock()
        mock_api_instance.delete_event = AsyncMock()
        mock_api_instance.get_event = AsyncMock()
        mock_api_instance.get_calendar_list = AsyncMock()
        return mock_api_instance

    @pytest.fixture
    def sync_service(self, mock_config, mock_api):
        """创建同步服务实例"""
        with patch(
            "src.notify.feishu_calendar.FeishuCalendarAPI", return_value=mock_api
        ):
            service = FeishuCalendarSync(mock_config)
            # 确保 service._api 使用的是我们的 mock 对象
            service._api = mock_api
            return service

    @pytest.fixture
    def sample_training_plan(self):
        """样本训练计划"""
        today = datetime.now()
        plan = TrainingPlan(
            plan_id="test_plan",
            user_id="test_user",
            plan_type=PlanType.BASE,
            fitness_level=FitnessLevel.INTERMEDIATE,
            start_date=today.strftime("%Y-%m-%d"),
            end_date=(today + timedelta(weeks=4)).strftime("%Y-%m-%d"),
            goal_distance_km=21.1,
            goal_date=(today + timedelta(weeks=12)).strftime("%Y-%m-%d"),
        )

        # 添加一周计划
        week = WeeklySchedule(
            week_number=1,
            start_date=today.strftime("%Y-%m-%d"),
            end_date=(today + timedelta(days=6)).strftime("%Y-%m-%d"),
        )

        # 添加每日计划（全部使用未来日期）
        for i in range(7):
            day_date = today + timedelta(days=i + 1)  # 从明天开始
            if i == 0:  # 周一休息
                daily_plan = DailyPlan(
                    date=day_date.strftime("%Y-%m-%d"),
                    workout_type=WorkoutType.REST,
                    distance_km=0.0,
                    duration_min=0,
                    notes="休息日",
                )
            else:
                daily_plan = DailyPlan(
                    date=day_date.strftime("%Y-%m-%d"),
                    workout_type=WorkoutType.EASY,
                    distance_km=5.0 + i,
                    duration_min=30 + i * 5,
                    target_hr_zone=2,
                    notes=f"第{i + 1}天训练",
                )
            week.daily_plans.append(daily_plan)

        plan.weeks.append(week)
        return plan

    def test_init_with_config(self, mock_config):
        """测试使用自定义配置初始化"""
        with patch("src.notify.feishu_calendar.FeishuCalendarAPI"):
            service = FeishuCalendarSync(mock_config)
            assert service.config.enabled is True
            assert service.config.calendar_id == "test_calendar_id"
            assert service._api is not None

    def test_init_without_api_credentials(self):
        """测试无 API 凭证初始化"""
        config = CalendarSyncConfig(
            enabled=True,
            app_id=None,
            app_secret=None,
        )
        with patch("src.notify.feishu_calendar.logger") as mock_logger:
            service = FeishuCalendarSync(config)
            assert service._api is None
            mock_logger.warning.assert_called_with("未配置飞书日历 API 凭证")

    def test_build_calendar_event(self, sync_service):
        """测试构建日历事件"""
        daily_plan = DailyPlan(
            date="2024-01-01",
            workout_type=WorkoutType.EASY,
            distance_km=10.0,
            duration_min=60,
            target_hr_zone=2,
            notes="轻松有氧跑",
        )
        date = datetime(2024, 1, 1)

        event = sync_service.build_calendar_event(daily_plan, date)

        assert "🏃" in event.summary
        assert "轻松跑" in event.summary
        assert "10.00" in event.summary and "公里" in event.summary
        assert event.start_time.hour == 6
        assert event.start_time.minute == 0
        assert event.end_time.hour == 7
        assert event.end_time.minute == 0
        assert event.description is not None
        assert "训练类型：轻松跑" in event.description
        assert "目标距离：10.0 km" in event.description
        assert "目标时长：60 分钟" in event.description
        assert len(event.reminders) == 1
        assert event.reminders[0]["minutes"] == 60

    def test_build_calendar_event_no_description(self):
        """测试构建不包含描述的事件"""
        config = CalendarSyncConfig(
            enabled=True,
            include_description=False,
            app_id="test_app_id",
            app_secret="test_app_secret",
        )
        with patch("src.notify.feishu_calendar.FeishuCalendarAPI"):
            service = FeishuCalendarSync(config)

        daily_plan = DailyPlan(
            date="2024-01-01",
            workout_type=WorkoutType.EASY,
            distance_km=10.0,
            duration_min=60,
        )
        date = datetime(2024, 1, 1)

        event = service.build_calendar_event(daily_plan, date)

        assert event.description is None

    def test_build_calendar_event_no_reminder(self):
        """测试构建不包含提醒的事件"""
        config = CalendarSyncConfig(
            enabled=True,
            reminder_minutes=0,
            app_id="test_app_id",
            app_secret="test_app_secret",
        )
        with patch("src.notify.feishu_calendar.FeishuCalendarAPI"):
            service = FeishuCalendarSync(config)

        daily_plan = DailyPlan(
            date="2024-01-01",
            workout_type=WorkoutType.EASY,
            distance_km=10.0,
            duration_min=60,
        )
        date = datetime(2024, 1, 1)

        event = service.build_calendar_event(daily_plan, date)

        assert len(event.reminders) == 0

    def test_sync_plan_success(
        self,
        mock_api,
        sync_service,
        sample_training_plan,
    ):
        """测试成功同步训练计划"""
        # 设置 AsyncMock 的返回值
        mock_api.create_event.return_value = {"event_id": "event_123"}

        result = asyncio.run(sync_service.sync_plan(sample_training_plan))

        assert result.success is True
        assert "成功同步" in result.message
        assert result.details is not None
        assert result.details.get("synced_count", 0) > 0
        assert mock_api.create_event.call_count > 0

    def test_sync_plan_disabled(self):
        """测试同步功能未启用"""
        config = CalendarSyncConfig(enabled=False)
        with patch("src.notify.feishu_calendar.FeishuCalendarAPI"):
            service = FeishuCalendarSync(config)

        plan = TrainingPlan(
            plan_id="test",
            user_id="test",
            plan_type=PlanType.BASE,
            fitness_level=FitnessLevel.INTERMEDIATE,
            start_date="2024-01-01",
            end_date="2024-04-01",
            goal_distance_km=21.1,
            goal_date="2024-04-01",
        )

        result = asyncio.run(service.sync_plan(plan))

        assert result.success is False
        assert "未启用" in result.message

    def test_sync_plan_no_api(self):
        """测试 API 未初始化"""
        config = CalendarSyncConfig(
            enabled=True,
            app_id=None,
            app_secret=None,
        )
        service = FeishuCalendarSync(config)

        plan = TrainingPlan(
            plan_id="test",
            user_id="test",
            plan_type=PlanType.BASE,
            fitness_level=FitnessLevel.INTERMEDIATE,
            start_date="2024-01-01",
            end_date="2024-04-01",
            goal_distance_km=21.1,
            goal_date="2024-04-01",
        )

        result = asyncio.run(service.sync_plan(plan))

        assert result.success is False
        assert "未初始化" in result.message

    def test_sync_daily_workout_success(self, mock_api, sync_service):
        """测试成功同步单日训练"""
        # 设置 AsyncMock 的返回值
        mock_api.create_event.return_value = {"event_id": "event_123"}

        daily_plan = DailyPlan(
            date="2024-01-01",
            workout_type=WorkoutType.EASY,
            distance_km=10.0,
            duration_min=60,
        )
        date = datetime(2024, 1, 1)

        result = asyncio.run(sync_service.sync_daily_workout(daily_plan, date))

        assert result.success is True
        assert result.event_id is not None
        assert "已同步" in result.message
        mock_api.create_event.assert_called_once()

    def test_sync_daily_workout_disabled(self, sync_service):
        """测试单日训练同步功能未启用"""
        sync_service.config.enabled = False

        daily_plan = DailyPlan(
            date="2024-01-01",
            workout_type=WorkoutType.EASY,
            distance_km=10.0,
            duration_min=60,
        )
        date = datetime(2024, 1, 1)

        result = asyncio.run(sync_service.sync_daily_workout(daily_plan, date))

        assert result.success is False
        assert "未启用" in result.message

    def test_update_event_success(self, mock_api, sync_service):
        """测试成功更新事件"""
        mock_api.update_event.return_value = {"event_id": "event_123"}

        daily_plan = DailyPlan(
            date="2024-01-01",
            workout_type=WorkoutType.EASY,
            distance_km=10.0,
            duration_min=60,
        )
        date = datetime(2024, 1, 1)

        result = asyncio.run(sync_service.update_event("event_123", daily_plan, date))

        assert result.success is True
        assert result.event_id == "event_123"
        assert "已更新" in result.message
        mock_api.update_event.assert_called_once()

    def test_delete_event_success(self, mock_api, sync_service):
        """测试成功删除事件"""
        mock_api.delete_event.return_value = {}

        result = asyncio.run(sync_service.delete_event("event_123"))

        assert result.success is True
        assert result.event_id == "event_123"
        assert "已删除" in result.message
        mock_api.delete_event.assert_called_once()

    def test_check_conflicts_no_api(self, sync_service):
        """测试无 API 时检测冲突"""
        sync_service._api = None

        date = datetime(2024, 1, 1)
        time_range = (6, 8)

        result = asyncio.run(sync_service.check_conflicts(date, time_range))

        assert result == []

    def test_get_default_calendar_id_from_config(self, sync_service):
        """测试从配置获取默认日历 ID"""
        calendar_id = sync_service._get_default_calendar_id()
        assert calendar_id == "test_calendar_id"


class TestIntegration:
    """集成测试"""

    def test_full_sync_workflow(self):
        """测试完整同步流程"""
        # 创建配置
        config = CalendarSyncConfig(
            enabled=True,
            calendar_id="test_calendar",
            app_id="test_app_id",
            app_secret="test_app_secret",
        )

        # 创建同步服务
        with patch("src.notify.feishu_calendar.FeishuCalendarAPI") as MockAPI:
            mock_api_instance = MagicMock()
            MockAPI.return_value = mock_api_instance
            mock_api_instance.create_event = AsyncMock(
                return_value={"event_id": "event_123"}
            )

            service = FeishuCalendarSync(config)

            # 创建训练计划
            today = datetime.now()
            plan = TrainingPlan(
                plan_id="test_plan",
                user_id="test_user",
                plan_type=PlanType.BASE,
                fitness_level=FitnessLevel.INTERMEDIATE,
                start_date=today.strftime("%Y-%m-%d"),
                end_date=(today + timedelta(weeks=4)).strftime("%Y-%m-%d"),
                goal_distance_km=21.1,
                goal_date=(today + timedelta(weeks=12)).strftime("%Y-%m-%d"),
            )

            week = WeeklySchedule(
                week_number=1,
                start_date=today.strftime("%Y-%m-%d"),
                end_date=(today + timedelta(days=6)).strftime("%Y-%m-%d"),
            )

            # 添加训练日（跳过休息日）
            for i in range(1, 7):
                day_date = today + timedelta(days=i)
                daily_plan = DailyPlan(
                    date=day_date.strftime("%Y-%m-%d"),
                    workout_type=WorkoutType.EASY,
                    distance_km=5.0 + i,
                    duration_min=30 + i * 5,
                )
                week.daily_plans.append(daily_plan)

            plan.weeks.append(week)

            # 执行同步
            result = asyncio.run(service.sync_plan(plan))

            # 验证结果
            assert result.success is True
            assert result.details is not None
            assert result.details.get("synced_count", 0) > 0

            # 验证 API 调用
            assert mock_api_instance.create_event.call_count > 0


if __name__ == "__main__":
    pytest.main(
        [
            __file__,
            "-v",
            "--cov=src.notify.feishu_calendar",
            "--cov-report=term-missing",
        ]
    )
