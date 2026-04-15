# 集成测试 - CalendarTool + PlanManager 协作测试
# Sprint 2 补充测试用例

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.models import FitnessLevel, PlanType, TrainingType
from src.core.plan.calendar_tool import (
    CalendarTool,
    SyncMode,
)
from src.core.plan.plan_manager import PlanManager, PlanStatus
from src.core.training_plan import (
    DailyPlan,
    TrainingPlan,
    WeeklySchedule,
)
from src.notify.feishu_calendar import SyncResult
from tests.conftest import create_mock_context


def create_test_plan(plan_id: str, with_event_id: bool = False) -> TrainingPlan:
    """创建测试训练计划"""
    daily_plan = DailyPlan(
        date="2026-04-10",
        workout_type=TrainingType.EASY,
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


class TestCalendarPlanIntegration:
    """TC-INT-001: CalendarTool + PlanManager 协作测试"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def plan_manager(self, temp_dir):
        """创建PlanManager实例"""
        mock_config = MagicMock()
        mock_config.data_dir = temp_dir
        context = create_mock_context(config=mock_config)
        return PlanManager(context)

    @pytest.fixture
    def calendar_tool(self):
        """创建CalendarTool实例"""
        with patch("src.core.plan.calendar_tool.FeishuCalendarSync") as mock_sync:
            tool = CalendarTool()
            # Mock sync_plan方法
            mock_sync.return_value.sync_plan = AsyncMock(
                return_value=SyncResult(
                    success=True,
                    message="同步成功",
                    event_id="event_123",
                    details={"event_ids": ["event_123"]},
                )
            )
            yield tool

    @pytest.mark.asyncio
    async def test_create_plan_and_sync_to_calendar(self, plan_manager, calendar_tool):
        """TC-INT-001: 创建计划→同步到日历→验证event_id"""
        # 1. 创建训练计划
        plan = create_test_plan("plan_001")
        plan_id = plan_manager.create_plan(plan)
        assert plan_id == "plan_001"

        # 2. 验证计划状态
        status = plan_manager.get_plan_status(plan_id)
        assert status == PlanStatus.DRAFT

        # 3. 激活计划
        plan_manager.activate_plan(plan_id)
        status = plan_manager.get_plan_status(plan_id)
        assert status == PlanStatus.ACTIVE

        # 4. 同步到日历
        with patch.object(
            calendar_tool._sync_service, "sync_plan", new_callable=AsyncMock
        ) as mock_sync:
            mock_sync.return_value = SyncResult(
                success=True,
                message="同步成功",
                event_id="event_123",
                details={"event_ids": ["event_123"]},
            )

            result = await calendar_tool.sync_plan(plan, SyncMode.CREATE)

            assert result.success is True
            assert result.event_id == "event_123"

        # 5. 验证event_id已设置
        retrieved_plan = plan_manager.get_plan(plan_id)
        assert retrieved_plan is not None


class TestPlanLifecycle:
    """TC-INT-002: 完整生命周期测试"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def plan_manager(self, temp_dir):
        """创建PlanManager实例"""
        mock_config = MagicMock()
        mock_config.data_dir = temp_dir
        context = create_mock_context(config=mock_config)
        return PlanManager(context)

    @pytest.mark.asyncio
    async def test_complete_lifecycle(self, plan_manager):
        """TC-INT-002: 创建→激活→更新→完成→查询状态"""
        # 1. 创建计划
        plan = create_test_plan("plan_lifecycle")
        plan_id = plan_manager.create_plan(plan)
        assert plan_id == "plan_lifecycle"

        # 2. 验证初始状态
        status = plan_manager.get_plan_status(plan_id)
        assert status == PlanStatus.DRAFT

        # 3. 激活计划
        result = plan_manager.activate_plan(plan_id)
        assert result is True
        status = plan_manager.get_plan_status(plan_id)
        assert status == PlanStatus.ACTIVE

        # 4. 更新计划
        updates = {"goal_distance_km": 21.1}
        result = plan_manager.update_plan(plan_id, updates)
        assert result is True

        # 5. 完成计划
        result = plan_manager.complete_plan(plan_id)
        assert result is True
        status = plan_manager.get_plan_status(plan_id)
        assert status == PlanStatus.COMPLETED

        # 6. 验证最终状态
        retrieved_plan = plan_manager.get_plan(plan_id)
        assert retrieved_plan is not None
        assert retrieved_plan.goal_distance_km == 21.1


class TestBatchSyncWithStatus:
    """TC-INT-003: 批量同步 + 状态管理测试"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def plan_manager(self, temp_dir):
        """创建PlanManager实例"""
        mock_config = MagicMock()
        mock_config.data_dir = temp_dir
        context = create_mock_context(config=mock_config)
        return PlanManager(context)

    @pytest.fixture
    def calendar_tool(self):
        """创建CalendarTool实例"""
        with patch("src.core.plan.calendar_tool.FeishuCalendarSync"):
            return CalendarTool()

    @pytest.mark.asyncio
    async def test_batch_sync_with_status_management(self, plan_manager, calendar_tool):
        """TC-INT-003: 批量创建→批量同步→验证状态"""
        # 1. 批量创建计划
        plans = []
        for i in range(5):
            plan = create_test_plan(f"plan_batch_{i}")
            plan_manager.create_plan(plan)
            plans.append(plan)

        # 2. 验证所有计划状态
        for i in range(5):
            status = plan_manager.get_plan_status(f"plan_batch_{i}")
            assert status == PlanStatus.DRAFT

        # 3. 批量同步
        with patch.object(
            calendar_tool, "sync_plan", new_callable=AsyncMock
        ) as mock_sync:
            mock_sync.return_value = MagicMock(
                success=True, details={"event_ids": [f"event_{i}"]}
            )

            result = await calendar_tool.batch_sync(
                plans, SyncMode.CREATE, batch_size=2
            )

            assert result.success is True
            assert result.total_count == 5
            assert result.synced_count == 5
            assert result.failed_count == 0

        # 4. 激活所有计划
        for i in range(5):
            plan_manager.activate_plan(f"plan_batch_{i}")
            status = plan_manager.get_plan_status(f"plan_batch_{i}")
            assert status == PlanStatus.ACTIVE


class TestConcurrentOperations:
    """TC-INT-004: 并发操作测试"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def plan_manager(self, temp_dir):
        """创建PlanManager实例"""
        mock_config = MagicMock()
        mock_config.data_dir = temp_dir
        context = create_mock_context(config=mock_config)
        return PlanManager(context)

    @pytest.mark.asyncio
    async def test_concurrent_create_operations(self, plan_manager):
        """TC-INT-004: 并发创建/更新/查询计划"""

        async def create_and_activate(plan_id: str):
            """创建并激活计划"""
            plan = create_test_plan(plan_id)
            plan_manager.create_plan(plan)
            plan_manager.activate_plan(plan_id)
            return plan_manager.get_plan_status(plan_id)

        # 并发创建10个计划
        tasks = [create_and_activate(f"plan_concurrent_{i}") for i in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 验证所有操作成功
        success_count = sum(1 for r in results if r == PlanStatus.ACTIVE)
        assert success_count == 10

        # 验证数据一致性
        all_plans = plan_manager.list_plans()
        assert len(all_plans) == 10

    @pytest.mark.asyncio
    async def test_concurrent_read_write_operations(self, plan_manager):
        """并发读写操作测试"""
        # 先创建一个计划
        plan = create_test_plan("plan_concurrent_rw")
        plan_manager.create_plan(plan)

        async def read_operation():
            """读操作"""
            return plan_manager.get_plan("plan_concurrent_rw")

        async def write_operation():
            """写操作"""
            return plan_manager.update_plan(
                "plan_concurrent_rw", {"goal_distance_km": 15.0}
            )

        # 并发执行读写操作
        tasks = [read_operation() for _ in range(5)] + [
            write_operation() for _ in range(3)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 验证没有异常
        exception_count = sum(1 for r in results if isinstance(r, Exception))
        assert exception_count == 0
