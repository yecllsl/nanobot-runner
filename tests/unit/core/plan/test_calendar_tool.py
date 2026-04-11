# CalendarTool单元测试

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.plan.calendar_tool import (
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
from src.notify.feishu_calendar import CalendarSyncConfig


def create_test_plan(plan_id: str) -> TrainingPlan:
    """创建测试训练计划"""
    daily_plan = DailyPlan(
        date="2026-04-10",
        workout_type=WorkoutType.EASY,
        distance_km=5.0,
        duration_min=30,
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


class TestCalendarToolInit:
    """测试CalendarTool初始化"""

    def test_init_with_config(self):
        """测试使用配置初始化"""
        config = CalendarSyncConfig(
            enabled=True,
            calendar_id="test_calendar_id",
            app_id="test_app_id",
            app_secret="test_app_secret",
        )
        tool = CalendarTool(config)
        assert tool._sync_service.config.enabled is True
        assert tool._sync_service.config.calendar_id == "test_calendar_id"

    def test_init_without_config(self):
        """测试不指定配置初始化"""
        with patch("src.core.plan.calendar_tool.FeishuCalendarSync"):
            tool = CalendarTool()
            assert tool is not None


class TestPreSyncCheck:
    """测试预同步检查"""

    @pytest.fixture
    def calendar_tool(self):
        """创建CalendarTool实例"""
        with patch("src.core.plan.calendar_tool.FeishuCalendarSync"):
            return CalendarTool()

    @pytest.mark.asyncio
    async def test_pre_sync_check_all(self, calendar_tool):
        """测试完整健康检查"""
        with (
            patch.object(
                calendar_tool, "_check_network", new_callable=AsyncMock
            ) as mock_network,
            patch.object(
                calendar_tool, "_check_token", new_callable=AsyncMock
            ) as mock_token,
            patch.object(
                calendar_tool, "_check_calendar_permission", new_callable=AsyncMock
            ) as mock_permission,
            patch.object(
                calendar_tool, "_check_calendar_id", new_callable=AsyncMock
            ) as mock_id,
        ):
            mock_network.return_value = HealthCheckResult(
                healthy=True, item=HealthCheckItem.NETWORK, message="网络正常"
            )
            mock_token.return_value = HealthCheckResult(
                healthy=True, item=HealthCheckItem.TOKEN, message="令牌有效"
            )
            mock_permission.return_value = HealthCheckResult(
                healthy=True,
                item=HealthCheckItem.CALENDAR_PERMISSION,
                message="权限正常",
            )
            mock_id.return_value = HealthCheckResult(
                healthy=True, item=HealthCheckItem.CALENDAR_ID, message="日历ID已配置"
            )

            results = await calendar_tool.pre_sync_check()

            assert len(results) == 4
            assert all(r.healthy for r in results)

    @pytest.mark.asyncio
    async def test_pre_sync_check_specific_items(self, calendar_tool):
        """测试指定检查项"""
        with patch.object(
            calendar_tool, "_check_network", new_callable=AsyncMock
        ) as mock_network:
            mock_network.return_value = HealthCheckResult(
                healthy=True, item=HealthCheckItem.NETWORK, message="网络正常"
            )

            results = await calendar_tool.pre_sync_check([HealthCheckItem.NETWORK])

            assert len(results) == 1
            assert results[0].item == HealthCheckItem.NETWORK


class TestOptimisticUpdate:
    """测试乐观更新"""

    @pytest.fixture
    def calendar_tool(self):
        """创建CalendarTool实例"""
        with patch("src.core.plan.calendar_tool.FeishuCalendarSync"):
            return CalendarTool()

    def test_optimistic_context_creation(self, calendar_tool):
        """测试乐观更新上下文创建"""
        daily_plan = DailyPlan(
            date="2026-04-10",
            workout_type=WorkoutType.EASY,
            distance_km=5.0,
            duration_min=30,
        )

        context = OptimisticUpdateContext(
            plan_id="test_plan",
            event_id="temp_123",
            daily_plan=daily_plan,
            date=datetime.now(),
            rollback_data={"original_event_id": None},
        )

        assert context.plan_id == "test_plan"
        assert context.event_id == "temp_123"

    def test_rollback_data_storage(self, calendar_tool):
        """测试回滚数据存储"""
        daily_plan = DailyPlan(
            date="2026-04-10",
            workout_type=WorkoutType.EASY,
            distance_km=5.0,
            duration_min=30,
            event_id="original_event",
        )

        context = OptimisticUpdateContext(
            plan_id="test_plan",
            event_id="temp_123",
            daily_plan=daily_plan,
            date=datetime.now(),
            rollback_data={"original_event_id": "original_event"},
        )

        calendar_tool._optimistic_contexts["temp_123"] = context

        assert "temp_123" in calendar_tool._optimistic_contexts
        assert (
            calendar_tool._optimistic_contexts["temp_123"].rollback_data[
                "original_event_id"
            ]
            == "original_event"
        )


class TestBatchSync:
    """测试批量同步"""

    @pytest.fixture
    def calendar_tool(self):
        """创建CalendarTool实例"""
        with patch("src.core.plan.calendar_tool.FeishuCalendarSync"):
            return CalendarTool()

    @pytest.mark.asyncio
    async def test_batch_sync_empty_list(self, calendar_tool):
        """测试空列表批量同步"""
        result = await calendar_tool.batch_sync([], SyncMode.CREATE)

        assert result.success is True
        assert result.total_count == 0
        assert result.synced_count == 0
        assert result.failed_count == 0

    @pytest.mark.asyncio
    async def test_batch_sync_with_batch_size(self, calendar_tool):
        """测试指定批次大小的批量同步"""
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


class TestSyncModes:
    """测试同步模式"""

    @pytest.fixture
    def calendar_tool(self):
        """创建CalendarTool实例"""
        with patch("src.core.plan.calendar_tool.FeishuCalendarSync"):
            return CalendarTool()

    @pytest.mark.asyncio
    async def test_sync_plan_create_mode(self, calendar_tool):
        """测试创建模式同步"""
        plan = create_test_plan("test_plan")

        with patch.object(
            calendar_tool._sync_service, "sync_plan", new_callable=AsyncMock
        ) as mock_sync:
            mock_sync.return_value = MagicMock(success=True, message="同步成功")

            result = await calendar_tool.sync_plan(plan, SyncMode.CREATE)

            assert result.success is True

    @pytest.mark.asyncio
    async def test_sync_plan_invalid_mode(self, calendar_tool):
        """测试无效同步模式"""
        plan = create_test_plan("test_plan")

        result = await calendar_tool.sync_plan(plan, "invalid_mode")

        assert result.success is False
        assert "不支持" in result.message


class TestSyncDailyWorkout:
    """测试单日训练同步"""

    @pytest.fixture
    def calendar_tool(self):
        """创建CalendarTool实例"""
        with patch("src.core.plan.calendar_tool.FeishuCalendarSync"):
            return CalendarTool()

    @pytest.mark.asyncio
    async def test_sync_daily_workout_create(self, calendar_tool):
        """测试创建单日训练"""
        daily_plan = DailyPlan(
            date="2026-04-10",
            workout_type=WorkoutType.EASY,
            distance_km=5.0,
            duration_min=30,
        )
        date = datetime.strptime("2026-04-10", "%Y-%m-%d")

        with patch.object(
            calendar_tool._sync_service, "sync_daily_workout", new_callable=AsyncMock
        ) as mock_sync:
            mock_sync.return_value = MagicMock(
                success=True, message="同步成功", event_id="event_123"
            )

            result = await calendar_tool.sync_daily_workout(
                daily_plan, date, SyncMode.CREATE
            )

            assert result.success is True

    @pytest.mark.asyncio
    async def test_sync_daily_workout_update_without_event_id(self, calendar_tool):
        """测试更新模式下无event_id"""
        daily_plan = DailyPlan(
            date="2026-04-10",
            workout_type=WorkoutType.EASY,
            distance_km=5.0,
            duration_min=30,
        )
        date = datetime.strptime("2026-04-10", "%Y-%m-%d")

        result = await calendar_tool.sync_daily_workout(
            daily_plan, date, SyncMode.UPDATE
        )

        assert result.success is False
        assert "id" in result.message.lower()
