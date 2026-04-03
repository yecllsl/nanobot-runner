# E2E测试 - 训练计划端到端流程测试
# Sprint 2 补充测试用例

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.plan.calendar_tool import CalendarTool, SyncMode
from src.core.plan.plan_manager import PlanManager, PlanStatus
from src.core.training_plan import (
    DailyPlan,
    FitnessLevel,
    PlanType,
    TrainingPlan,
    WeeklySchedule,
    WorkoutType,
)
from src.notify.feishu_calendar import SyncResult


def create_e2e_plan(plan_id: str, with_event_id: bool = False) -> TrainingPlan:
    """创建E2E测试训练计划"""
    daily_plans = [
        DailyPlan(
            date=f"2026-04-{10+i:02d}",
            workout_type=WorkoutType.EASY if i % 2 == 0 else WorkoutType.LONG,
            distance_km=5.0 + i,
            duration_min=30 + i * 5,
            event_id=f"event_{i}" if with_event_id else None,
        )
        for i in range(7)
    ]
    week = WeeklySchedule(
        week_number=1,
        start_date="2026-04-10",
        end_date="2026-04-16",
        daily_plans=daily_plans,
    )
    return TrainingPlan(
        plan_id=plan_id,
        user_id="e2e_user",
        plan_type=PlanType.BASE,
        fitness_level=FitnessLevel.INTERMEDIATE,
        start_date="2026-04-10",
        end_date="2026-04-30",
        goal_distance_km=21.1,
        goal_date="2026-04-30",
        weeks=[week],
    )


class TestTrainingPlanE2E:
    """TC-E2E-001: 训练计划完整流程"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def plan_manager(self, temp_dir):
        """创建PlanManager实例"""
        return PlanManager(data_dir=temp_dir)

    @pytest.fixture
    def calendar_tool(self):
        """创建CalendarTool实例"""
        with patch("src.core.plan.calendar_tool.FeishuCalendarSync"):
            return CalendarTool()

    @pytest.mark.asyncio
    async def test_complete_training_plan_flow(self, plan_manager, calendar_tool):
        """TC-E2E-001: 训练计划完整流程（创建→激活→同步→验证）"""
        # 1. 创建训练计划
        plan = create_e2e_plan("e2e_plan_001")
        plan_id = plan_manager.create_plan(plan)
        assert plan_id == "e2e_plan_001"

        # 2. 验证计划已创建
        retrieved_plan = plan_manager.get_plan(plan_id)
        assert retrieved_plan is not None
        assert retrieved_plan.plan_id == "e2e_plan_001"

        # 3. 验证初始状态
        status = plan_manager.get_plan_status(plan_id)
        assert status == PlanStatus.DRAFT

        # 4. 激活计划
        result = plan_manager.activate_plan(plan_id)
        assert result is True
        status = plan_manager.get_plan_status(plan_id)
        assert status == PlanStatus.ACTIVE

        # 5. 同步到日历
        with patch.object(
            calendar_tool._sync_service, "sync_plan", new_callable=AsyncMock
        ) as mock_sync:
            mock_sync.return_value = SyncResult(
                success=True,
                message="同步成功",
                details={"event_ids": [f"event_{i}" for i in range(7)]},
            )

            result = await calendar_tool.sync_plan(plan, SyncMode.CREATE)

            assert result.success is True

        # 6. 验证计划状态
        final_plan = plan_manager.get_plan(plan_id)
        assert final_plan is not None
        assert final_plan.plan_type == PlanType.BASE


class TestPlanAdjustmentE2E:
    """TC-E2E-002: 计划调整流程"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def plan_manager(self, temp_dir):
        """创建PlanManager实例"""
        return PlanManager(data_dir=temp_dir)

    @pytest.fixture
    def calendar_tool(self):
        """创建CalendarTool实例"""
        with patch("src.core.plan.calendar_tool.FeishuCalendarSync"):
            return CalendarTool()

    @pytest.mark.asyncio
    async def test_plan_adjustment_flow(self, plan_manager, calendar_tool):
        """TC-E2E-002: 计划调整流程（调整→更新→验证）"""
        # 1. 创建并激活计划
        plan = create_e2e_plan("e2e_plan_002", with_event_id=True)
        plan_id = plan_manager.create_plan(plan)
        plan_manager.activate_plan(plan_id)

        # 2. 调整计划目标
        updates = {
            "goal_distance_km": 42.195,
            "goal_date": "2026-05-15",
        }
        result = plan_manager.update_plan(plan_id, updates)
        assert result is True

        # 3. 更新日历事件
        with patch.object(
            calendar_tool._sync_service, "update_event", new_callable=AsyncMock
        ) as mock_update:
            mock_update.return_value = SyncResult(success=True, message="更新成功")

            # 更新每个日训练计划
            for week in plan.weeks:
                for daily_plan in week.daily_plans:
                    if daily_plan.event_id:
                        date = datetime.strptime(daily_plan.date, "%Y-%m-%d")
                        result = await calendar_tool.sync_daily_workout(
                            daily_plan, date, SyncMode.UPDATE
                        )
                        assert result.success is True

        # 4. 验证更新结果
        updated_plan = plan_manager.get_plan(plan_id)
        assert updated_plan is not None
        assert updated_plan.goal_distance_km == 42.195


class TestPlanCancellationE2E:
    """TC-E2E-003: 计划取消流程"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def plan_manager(self, temp_dir):
        """创建PlanManager实例"""
        return PlanManager(data_dir=temp_dir)

    @pytest.fixture
    def calendar_tool(self):
        """创建CalendarTool实例"""
        with patch("src.core.plan.calendar_tool.FeishuCalendarSync"):
            return CalendarTool()

    @pytest.mark.asyncio
    async def test_plan_cancellation_flow(self, plan_manager, calendar_tool):
        """TC-E2E-003: 计划取消流程（取消→删除→验证）"""
        # 1. 创建并激活计划
        plan = create_e2e_plan("e2e_plan_003", with_event_id=True)
        plan_id = plan_manager.create_plan(plan)
        plan_manager.activate_plan(plan_id)

        # 2. 取消计划
        reason = "因伤取消训练计划"
        result = plan_manager.cancel_plan(plan_id, reason)
        assert result is True

        # 3. 验证状态
        status = plan_manager.get_plan_status(plan_id)
        assert status == PlanStatus.CANCELLED

        # 4. 删除日历事件
        with patch.object(calendar_tool._sync_service, "_api") as mock_api:
            mock_api.delete_event = AsyncMock()

            result = await calendar_tool.sync_plan(plan, SyncMode.DELETE)

            assert result.success is True

        # 5. 验证计划已取消
        cancelled_plan = plan_manager.get_plan(plan_id)
        assert cancelled_plan is not None
        assert plan_manager.get_plan_status(plan_id) == PlanStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_plan_deletion_after_cancellation(self, plan_manager, calendar_tool):
        """取消后删除计划"""
        # 1. 创建并取消计划
        plan = create_e2e_plan("e2e_plan_004", with_event_id=True)
        plan_id = plan_manager.create_plan(plan)
        plan_manager.cancel_plan(plan_id, "测试取消")

        # 2. 删除计划
        result = plan_manager.delete_plan(plan_id)
        assert result is True

        # 3. 验证计划已删除
        deleted_plan = plan_manager.get_plan(plan_id)
        assert deleted_plan is None

        # 4. 验证计划列表中不存在
        all_plans = plan_manager.list_plans()
        plan_ids = [p.plan_id for p in all_plans]
        assert plan_id not in plan_ids
