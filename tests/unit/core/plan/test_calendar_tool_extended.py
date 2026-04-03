# CalendarTool 补充单元测试
# 提高覆盖率至80%以上

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.plan.calendar_tool import (
    BatchSyncResult,
    CalendarTool,
    HealthCheckItem,
    HealthCheckResult,
    OptimisticUpdateContext,
    SyncMode,
)
from src.core.training_plan import (
    DailyPlan,
    FitnessLevel,
    PlanType,
    TrainingPlan,
    WeeklySchedule,
    WorkoutType,
)
from src.notify.feishu_calendar import SyncResult


def create_test_plan(plan_id: str, with_event_id: bool = False) -> TrainingPlan:
    """创建测试训练计划"""
    daily_plan = DailyPlan(
        date="2026-04-10",
        workout_type=WorkoutType.EASY,
        distance_km=5.0,
        duration_min=30,
        event_id="event_123" if with_event_id else None,
    )
    week = WeeklySchedule(
        week_number=1,
        start_date="2026-04-01",
        end_date="2026-04-07",
        daily_plans=[daily_plan],
    )
    return TrainingPlan(
        plan_id=plan_id,
        user_id="test_user",
        plan_type=PlanType.BASE,
        fitness_level=FitnessLevel.INTERMEDIATE,
        start_date="2026-04-01",
        end_date="2026-04-30",
        goal_distance_km=10.0,
        goal_date="2026-04-30",
        weeks=[week],
    )


class TestBatchSyncExtended:
    """批量同步扩展测试"""

    @pytest.fixture
    def calendar_tool(self):
        """创建CalendarTool实例"""
        with patch("src.core.plan.calendar_tool.FeishuCalendarSync"):
            return CalendarTool()

    @pytest.mark.asyncio
    async def test_batch_sync_all_success(self, calendar_tool):
        """TC-M5-010: 批量同步-成功场景"""
        plans = [create_test_plan(f"plan_{i}") for i in range(10)]

        with patch.object(
            calendar_tool, "sync_plan", new_callable=AsyncMock
        ) as mock_sync:
            mock_sync.return_value = MagicMock(
                success=True, details={"event_ids": ["event_1"]}
            )

            result = await calendar_tool.batch_sync(plans, SyncMode.CREATE)

            assert result.success is True
            assert result.total_count == 10
            assert result.synced_count == 10
            assert result.failed_count == 0

    @pytest.mark.asyncio
    async def test_batch_sync_partial_failure(self, calendar_tool):
        """TC-M5-011: 批量同步-部分失败"""
        plans = [create_test_plan(f"plan_{i}") for i in range(10)]

        call_count = 0

        async def mock_sync_func(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 5:
                return MagicMock(success=False, error="同步失败", message="失败")
            return MagicMock(success=True, details={"event_ids": ["event_1"]})

        with patch.object(
            calendar_tool, "sync_plan", new_callable=AsyncMock
        ) as mock_sync:
            mock_sync.side_effect = mock_sync_func

            result = await calendar_tool.batch_sync(plans, SyncMode.CREATE)

            assert result.success is False
            assert result.total_count == 10
            assert result.synced_count == 9
            assert result.failed_count == 1
            assert len(result.errors) == 1

    @pytest.mark.asyncio
    async def test_batch_sync_with_batch_size(self, calendar_tool):
        """TC-M5-012: 批量同步-指定批次大小"""
        plans = [create_test_plan(f"plan_{i}") for i in range(25)]

        with patch.object(
            calendar_tool, "sync_plan", new_callable=AsyncMock
        ) as mock_sync:
            mock_sync.return_value = MagicMock(
                success=True, details={"event_ids": ["event_1"]}
            )

            result = await calendar_tool.batch_sync(
                plans, SyncMode.CREATE, batch_size=10
            )

            assert result.total_count == 25
            assert mock_sync.call_count == 25

    @pytest.mark.asyncio
    async def test_batch_sync_with_exception(self, calendar_tool):
        """批量同步-异常处理"""
        plans = [create_test_plan(f"plan_{i}") for i in range(5)]

        call_count = 0

        async def mock_sync_func(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 3:
                raise Exception("网络异常")
            return MagicMock(success=True, details={"event_ids": ["event_1"]})

        with patch.object(
            calendar_tool, "sync_plan", new_callable=AsyncMock
        ) as mock_sync:
            mock_sync.side_effect = mock_sync_func

            result = await calendar_tool.batch_sync(plans, SyncMode.CREATE)

            assert result.success is False
            assert result.failed_count == 1
            assert len(result.errors) == 1
            assert "网络异常" in result.errors[0]["error"]


class TestOptimisticUpdateExtended:
    """乐观更新扩展测试"""

    @pytest.fixture
    def calendar_tool(self):
        """创建CalendarTool实例"""
        with patch("src.core.plan.calendar_tool.FeishuCalendarSync"):
            return CalendarTool()

    @pytest.mark.asyncio
    async def test_optimistic_update_success(self, calendar_tool):
        """TC-M5-007: 乐观更新-创建上下文"""
        plan = create_test_plan("test_plan")
        daily_plan = DailyPlan(
            date="2026-04-10",
            workout_type=WorkoutType.EASY,
            distance_km=5.0,
            duration_min=30,
        )
        date = datetime.strptime("2026-04-10", "%Y-%m-%d")

        with patch.object(
            calendar_tool._sync_service,
            "sync_daily_workout",
            new_callable=AsyncMock,
        ) as mock_sync:
            mock_sync.return_value = SyncResult(
                success=True, message="同步成功", event_id="real_event_123"
            )

            result = await calendar_tool.optimistic_update(plan, daily_plan, date)

            assert result.success is True
            assert result.event_id == "real_event_123"
            assert daily_plan.event_id == "real_event_123"
            assert len(calendar_tool._optimistic_contexts) == 0

    @pytest.mark.asyncio
    async def test_optimistic_update_rollback(self, calendar_tool):
        """TC-M5-008: 乐观更新-回滚"""
        plan = create_test_plan("test_plan")
        daily_plan = DailyPlan(
            date="2026-04-10",
            workout_type=WorkoutType.EASY,
            distance_km=5.0,
            duration_min=30,
            event_id="original_event",
        )
        date = datetime.strptime("2026-04-10", "%Y-%m-%d")

        with patch.object(
            calendar_tool._sync_service,
            "sync_daily_workout",
            new_callable=AsyncMock,
        ) as mock_sync:
            mock_sync.return_value = SyncResult(
                success=False, message="同步失败", error="网络错误"
            )

            result = await calendar_tool.optimistic_update(plan, daily_plan, date)

            assert result.success is False
            assert "回滚" in result.message
            assert daily_plan.event_id == "original_event"
            assert len(calendar_tool._optimistic_contexts) == 0

    @pytest.mark.asyncio
    async def test_optimistic_update_exception(self, calendar_tool):
        """乐观更新-异常处理"""
        plan = create_test_plan("test_plan")
        daily_plan = DailyPlan(
            date="2026-04-10",
            workout_type=WorkoutType.EASY,
            distance_km=5.0,
            duration_min=30,
        )
        date = datetime.strptime("2026-04-10", "%Y-%m-%d")

        with patch.object(
            calendar_tool._sync_service,
            "sync_daily_workout",
            new_callable=AsyncMock,
        ) as mock_sync:
            mock_sync.side_effect = Exception("API异常")

            result = await calendar_tool.optimistic_update(plan, daily_plan, date)

            assert result.success is False
            assert "异常" in result.message
            assert daily_plan.event_id is None


class TestSyncPlanExtended:
    """同步计划扩展测试"""

    @pytest.fixture
    def calendar_tool(self):
        """创建CalendarTool实例"""
        with patch("src.core.plan.calendar_tool.FeishuCalendarSync"):
            return CalendarTool()

    @pytest.mark.asyncio
    async def test_sync_plan_update_mode(self, calendar_tool):
        """TC-M5-015: 同步计划-UPDATE模式"""
        plan = create_test_plan("test_plan", with_event_id=True)

        with patch.object(
            calendar_tool._sync_service, "_api"
        ) as mock_api, patch.object(
            calendar_tool._sync_service, "update_event", new_callable=AsyncMock
        ) as mock_update:
            mock_api.return_value = MagicMock()
            mock_update.return_value = SyncResult(success=True, message="更新成功")

            result = await calendar_tool.sync_plan(plan, SyncMode.UPDATE)

            assert result.success is True

    @pytest.mark.asyncio
    async def test_sync_plan_delete_mode(self, calendar_tool):
        """TC-M5-016: 同步计划-DELETE模式"""
        plan = create_test_plan("test_plan", with_event_id=True)

        with patch.object(
            calendar_tool._sync_service, "_api"
        ) as mock_api, patch.object(
            calendar_tool._sync_service, "_get_default_calendar_id"
        ) as mock_calendar_id:
            mock_api.delete_event = AsyncMock()
            mock_calendar_id.return_value = "calendar_123"

            result = await calendar_tool.sync_plan(plan, SyncMode.DELETE)

            assert result.success is True

    @pytest.mark.asyncio
    async def test_sync_plan_delete_without_api(self, calendar_tool):
        """同步计划删除-无API"""
        plan = create_test_plan("test_plan", with_event_id=True)

        with patch.object(calendar_tool._sync_service, "_api", None):
            result = await calendar_tool.sync_plan(plan, SyncMode.DELETE)

            assert result.success is False
            assert "未初始化" in result.message

    @pytest.mark.asyncio
    async def test_sync_plan_delete_without_calendar_id(self, calendar_tool):
        """同步计划删除-无日历ID"""
        plan = create_test_plan("test_plan", with_event_id=True)

        with patch.object(
            calendar_tool._sync_service, "_api"
        ) as mock_api, patch.object(
            calendar_tool._sync_service, "_get_default_calendar_id"
        ) as mock_calendar_id:
            mock_api.return_value = MagicMock()
            mock_calendar_id.return_value = None

            result = await calendar_tool.sync_plan(plan, SyncMode.DELETE)

            assert result.success is False
            assert "未指定日历" in result.message


class TestSyncDailyWorkoutExtended:
    """同步单日训练扩展测试"""

    @pytest.fixture
    def calendar_tool(self):
        """创建CalendarTool实例"""
        with patch("src.core.plan.calendar_tool.FeishuCalendarSync"):
            return CalendarTool()

    @pytest.mark.asyncio
    async def test_sync_daily_workout_update_mode(self, calendar_tool):
        """TC-M5-018: 同步单日训练-UPDATE"""
        daily_plan = DailyPlan(
            date="2026-04-10",
            workout_type=WorkoutType.EASY,
            distance_km=5.0,
            duration_min=30,
            event_id="event_123",
        )
        date = datetime.strptime("2026-04-10", "%Y-%m-%d")

        with patch.object(
            calendar_tool._sync_service, "update_event", new_callable=AsyncMock
        ) as mock_update:
            mock_update.return_value = SyncResult(
                success=True, message="更新成功", event_id="event_123"
            )

            result = await calendar_tool.sync_daily_workout(
                daily_plan, date, SyncMode.UPDATE
            )

            assert result.success is True

    @pytest.mark.asyncio
    async def test_sync_daily_workout_delete_mode(self, calendar_tool):
        """TC-M5-019: 同步单日训练-DELETE"""
        daily_plan = DailyPlan(
            date="2026-04-10",
            workout_type=WorkoutType.EASY,
            distance_km=5.0,
            duration_min=30,
            event_id="event_123",
        )
        date = datetime.strptime("2026-04-10", "%Y-%m-%d")

        with patch.object(
            calendar_tool._sync_service, "_api"
        ) as mock_api, patch.object(
            calendar_tool._sync_service, "_get_default_calendar_id"
        ) as mock_calendar_id:
            mock_api.delete_event = AsyncMock()
            mock_calendar_id.return_value = "calendar_123"

            result = await calendar_tool.sync_daily_workout(
                daily_plan, date, SyncMode.DELETE
            )

            assert result.success is True

    @pytest.mark.asyncio
    async def test_sync_daily_workout_delete_without_event_id(self, calendar_tool):
        """同步单日训练删除-无event_id"""
        daily_plan = DailyPlan(
            date="2026-04-10",
            workout_type=WorkoutType.EASY,
            distance_km=5.0,
            duration_min=30,
        )
        date = datetime.strptime("2026-04-10", "%Y-%m-%d")

        result = await calendar_tool.sync_daily_workout(
            daily_plan, date, SyncMode.DELETE
        )

        assert result.success is False
        assert "id" in result.message.lower()


class TestHealthCheckExtended:
    """健康检查扩展测试"""

    @pytest.fixture
    def calendar_tool(self):
        """创建CalendarTool实例"""
        with patch("src.core.plan.calendar_tool.FeishuCalendarSync"):
            return CalendarTool()

    @pytest.mark.asyncio
    async def test_check_network_success(self, calendar_tool):
        """TC-M5-002: 预同步检查-网络检查"""
        with patch("requests.get") as mock_get:
            mock_get.return_value = MagicMock(status_code=200)

            result = await calendar_tool._check_network()

            assert result.healthy is True
            assert result.item == HealthCheckItem.NETWORK

    @pytest.mark.asyncio
    async def test_check_network_failure(self, calendar_tool):
        """网络检查-失败"""
        with patch("requests.get") as mock_get:
            mock_get.side_effect = Exception("网络异常")

            result = await calendar_tool._check_network()

            assert result.healthy is False
            assert "失败" in result.message

    @pytest.mark.asyncio
    async def test_check_token_success(self, calendar_tool):
        """TC-M5-003: 预同步检查-令牌检查"""
        with patch.object(calendar_tool._sync_service, "_api") as mock_api:
            mock_api._get_access_token = MagicMock(return_value="valid_token")

            result = await calendar_tool._check_token()

            assert result.healthy is True
            assert result.item == HealthCheckItem.TOKEN

    @pytest.mark.asyncio
    async def test_check_token_no_api(self, calendar_tool):
        """令牌检查-无API"""
        with patch.object(calendar_tool._sync_service, "_api", None):
            result = await calendar_tool._check_token()

            assert result.healthy is False
            assert "未初始化" in result.message

    @pytest.mark.asyncio
    async def test_check_calendar_permission_success(self, calendar_tool):
        """TC-M5-004: 预同步检查-日历权限"""
        with patch.object(calendar_tool._sync_service, "_api") as mock_api:
            mock_api.get_calendar_list = AsyncMock(
                return_value=[{"calendar_id": "cal_1"}]
            )

            result = await calendar_tool._check_calendar_permission()

            assert result.healthy is True
            assert result.item == HealthCheckItem.CALENDAR_PERMISSION

    @pytest.mark.asyncio
    async def test_check_calendar_permission_no_calendars(self, calendar_tool):
        """日历权限检查-无日历"""
        with patch.object(calendar_tool._sync_service, "_api") as mock_api:
            mock_api.get_calendar_list = AsyncMock(return_value=[])

            result = await calendar_tool._check_calendar_permission()

            assert result.healthy is False
            assert "无可用" in result.message

    @pytest.mark.asyncio
    async def test_check_calendar_id_success(self, calendar_tool):
        """TC-M5-005: 预同步检查-日历ID"""
        with patch.object(
            calendar_tool._sync_service, "_get_default_calendar_id"
        ) as mock_calendar_id:
            mock_calendar_id.return_value = "calendar_123"

            result = await calendar_tool._check_calendar_id()

            assert result.healthy is True
            assert result.item == HealthCheckItem.CALENDAR_ID

    @pytest.mark.asyncio
    async def test_check_calendar_id_not_configured(self, calendar_tool):
        """日历ID检查-未配置"""
        with patch.object(
            calendar_tool._sync_service, "_get_default_calendar_id"
        ) as mock_calendar_id:
            mock_calendar_id.return_value = None

            result = await calendar_tool._check_calendar_id()

            assert result.healthy is False
            assert "未配置" in result.message
