# PlanManager单元测试

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.core.models import FitnessLevel, PlanType, TrainingType
from src.core.plan.plan_manager import (
    PlanManager,
    PlanManagerError,
    PlanStatus,
    PlanStatusTransition,
)
from src.core.training_plan import (
    DailyPlan,
    TrainingPlan,
    WeeklySchedule,
)
from tests.conftest import create_mock_context


def create_test_plan(plan_id: str) -> TrainingPlan:
    """创建测试训练计划"""
    daily_plan = DailyPlan(
        date="2026-04-10",
        workout_type=TrainingType.EASY,
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


class TestPlanStatusTransition:
    """测试计划状态转换"""

    def test_draft_can_transition_to_active(self):
        """测试草稿可以转换为激活"""
        assert PlanStatusTransition.can_transition(PlanStatus.DRAFT, PlanStatus.ACTIVE)

    def test_draft_can_transition_to_cancelled(self):
        """测试草稿可以转换为取消"""
        assert PlanStatusTransition.can_transition(
            PlanStatus.DRAFT, PlanStatus.CANCELLED
        )

    def test_active_can_transition_to_paused(self):
        """测试激活可以转换为暂停"""
        assert PlanStatusTransition.can_transition(PlanStatus.ACTIVE, PlanStatus.PAUSED)

    def test_active_can_transition_to_completed(self):
        """测试激活可以转换为完成"""
        assert PlanStatusTransition.can_transition(
            PlanStatus.ACTIVE, PlanStatus.COMPLETED
        )

    def test_active_can_transition_to_cancelled(self):
        """测试激活可以转换为取消"""
        assert PlanStatusTransition.can_transition(
            PlanStatus.ACTIVE, PlanStatus.CANCELLED
        )

    def test_paused_can_transition_to_active(self):
        """测试暂停可以转换为激活"""
        assert PlanStatusTransition.can_transition(PlanStatus.PAUSED, PlanStatus.ACTIVE)

    def test_paused_can_transition_to_cancelled(self):
        """测试暂停可以转换为取消"""
        assert PlanStatusTransition.can_transition(
            PlanStatus.PAUSED, PlanStatus.CANCELLED
        )

    def test_completed_cannot_transition(self):
        """测试完成状态不可转换"""
        assert not PlanStatusTransition.can_transition(
            PlanStatus.COMPLETED, PlanStatus.ACTIVE
        )
        assert not PlanStatusTransition.can_transition(
            PlanStatus.COMPLETED, PlanStatus.PAUSED
        )
        assert not PlanStatusTransition.can_transition(
            PlanStatus.COMPLETED, PlanStatus.CANCELLED
        )

    def test_cancelled_cannot_transition(self):
        """测试取消状态不可转换"""
        assert not PlanStatusTransition.can_transition(
            PlanStatus.CANCELLED, PlanStatus.ACTIVE
        )
        assert not PlanStatusTransition.can_transition(
            PlanStatus.CANCELLED, PlanStatus.PAUSED
        )

    def test_invalid_transition(self):
        """测试无效状态转换"""
        assert not PlanStatusTransition.can_transition(
            PlanStatus.DRAFT, PlanStatus.PAUSED
        )
        assert not PlanStatusTransition.can_transition(
            PlanStatus.DRAFT, PlanStatus.COMPLETED
        )


class TestPlanManagerInit:
    """测试PlanManager初始化"""

    def test_init_with_context(self):
        """测试使用AppContext初始化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            config = MagicMock()
            config.data_dir = data_dir
            context = create_mock_context(config=config)
            manager = PlanManager(context)
            assert manager.data_dir == data_dir
            assert manager.plans_file == data_dir / "training_plans.json"

    def test_init_creates_plans_file(self):
        """测试初始化创建计划文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            config = MagicMock()
            config.data_dir = data_dir
            context = create_mock_context(config=config)
            manager = PlanManager(context)
            assert manager.plans_file.exists()


class TestPlanManagerCreate:
    """测试创建计划"""

    @pytest.fixture
    def manager(self):
        """创建PlanManager实例"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            config = MagicMock()
            config.data_dir = data_dir
            context = create_mock_context(config=config)
            yield PlanManager(context)

    def test_create_plan_success(self, manager):
        """测试成功创建计划"""
        plan = create_test_plan("test_plan_1")
        plan_id = manager.create_plan(plan)

        assert plan_id == "test_plan_1"
        assert "test_plan_1" in manager._plans

    def test_create_plan_without_id(self, manager):
        """测试创建无ID计划"""
        plan = create_test_plan("")
        with pytest.raises(PlanManagerError, match="计划ID不能为空"):
            manager.create_plan(plan)

    def test_create_duplicate_plan(self, manager):
        """测试创建重复计划"""
        plan = create_test_plan("test_plan_1")
        manager.create_plan(plan)

        with pytest.raises(PlanManagerError, match="计划ID已存在"):
            manager.create_plan(plan)

    def test_create_plan_sets_draft_status(self, manager):
        """测试创建计划设置草稿状态"""
        plan = create_test_plan("test_plan_1")
        manager.create_plan(plan)

        status = manager.get_plan_status("test_plan_1")
        assert status == PlanStatus.DRAFT


class TestPlanManagerGet:
    """测试获取计划"""

    @pytest.fixture
    def manager(self):
        """创建PlanManager实例"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            config = MagicMock()
            config.data_dir = data_dir
            context = create_mock_context(config=config)
            yield PlanManager(context)

    def test_get_plan_success(self, manager):
        """测试成功获取计划"""
        plan = create_test_plan("test_plan_1")
        manager.create_plan(plan)

        retrieved = manager.get_plan("test_plan_1")
        assert retrieved is not None
        assert retrieved.plan_id == "test_plan_1"

    def test_get_plan_not_found(self, manager):
        """测试获取不存在的计划"""
        retrieved = manager.get_plan("non_existent")
        assert retrieved is None

    def test_get_plan_status(self, manager):
        """测试获取计划状态"""
        plan = create_test_plan("test_plan_1")
        manager.create_plan(plan)

        status = manager.get_plan_status("test_plan_1")
        assert status == PlanStatus.DRAFT

    def test_get_plan_status_not_found(self, manager):
        """测试获取不存在计划的状态"""
        status = manager.get_plan_status("non_existent")
        assert status is None


class TestPlanManagerUpdate:
    """测试更新计划"""

    @pytest.fixture
    def manager(self):
        """创建PlanManager实例"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            config = MagicMock()
            config.data_dir = data_dir
            context = create_mock_context(config=config)
            yield PlanManager(context)

    def test_update_plan_success(self, manager):
        """测试成功更新计划"""
        plan = create_test_plan("test_plan_1")
        manager.create_plan(plan)

        result = manager.update_plan("test_plan_1", {"goal_distance_km": 15.0})
        assert result is True

        updated = manager.get_plan("test_plan_1")
        assert updated is not None
        assert updated.goal_distance_km == 15.0

    def test_update_plan_not_found(self, manager):
        """测试更新不存在的计划"""
        with pytest.raises(PlanManagerError, match="计划不存在"):
            manager.update_plan("non_existent", {"goal_distance_km": 15.0})

    def test_update_plan_status_valid_transition(self, manager):
        """测试有效状态转换更新"""
        plan = create_test_plan("test_plan_1")
        manager.create_plan(plan)

        result = manager.update_plan("test_plan_1", {"status": "active"})
        assert result is True

        status = manager.get_plan_status("test_plan_1")
        assert status == PlanStatus.ACTIVE

    def test_update_plan_status_invalid_transition(self, manager):
        """测试无效状态转换更新"""
        plan = create_test_plan("test_plan_1")
        manager.create_plan(plan)

        with pytest.raises(PlanManagerError, match="状态转换不合法"):
            manager.update_plan("test_plan_1", {"status": "paused"})

    def test_update_plan_cannot_change_id(self, manager):
        """测试不能修改计划ID"""
        plan = create_test_plan("test_plan_1")
        manager.create_plan(plan)

        manager.update_plan("test_plan_1", {"plan_id": "new_id"})

        assert "test_plan_1" in manager._plans
        assert "new_id" not in manager._plans


class TestPlanManagerCancel:
    """测试取消计划"""

    @pytest.fixture
    def manager(self):
        """创建PlanManager实例"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            config = MagicMock()
            config.data_dir = data_dir
            context = create_mock_context(config=config)
            yield PlanManager(context)

    def test_cancel_plan_success(self, manager):
        """测试成功取消计划"""
        plan = create_test_plan("test_plan_1")
        manager.create_plan(plan)

        result = manager.cancel_plan("test_plan_1", "测试取消")
        assert result is True

        status = manager.get_plan_status("test_plan_1")
        assert status == PlanStatus.CANCELLED

    def test_cancel_plan_not_found(self, manager):
        """测试取消不存在的计划"""
        with pytest.raises(PlanManagerError, match="计划不存在"):
            manager.cancel_plan("non_existent", "测试取消")

    def test_cancel_active_plan(self, manager):
        """测试取消激活的计划"""
        plan = create_test_plan("test_plan_1")
        manager.create_plan(plan)
        manager.update_plan("test_plan_1", {"status": "active"})

        result = manager.cancel_plan("test_plan_1", "测试取消")
        assert result is True

        status = manager.get_plan_status("test_plan_1")
        assert status == PlanStatus.CANCELLED

    def test_cancel_completed_plan(self, manager):
        """测试取消已完成的计划"""
        plan = create_test_plan("test_plan_1")
        manager.create_plan(plan)
        manager.update_plan("test_plan_1", {"status": "active"})
        manager.update_plan("test_plan_1", {"status": "completed"})

        with pytest.raises(PlanManagerError, match="当前状态不允许取消"):
            manager.cancel_plan("test_plan_1", "测试取消")


class TestPlanManagerActivate:
    """测试激活计划"""

    @pytest.fixture
    def manager(self):
        """创建PlanManager实例"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            config = MagicMock()
            config.data_dir = data_dir
            context = create_mock_context(config=config)
            yield PlanManager(context)

    def test_activate_plan_success(self, manager):
        """测试成功激活计划"""
        plan = create_test_plan("test_plan_1")
        manager.create_plan(plan)

        result = manager.activate_plan("test_plan_1")
        assert result is True

        status = manager.get_plan_status("test_plan_1")
        assert status == PlanStatus.ACTIVE

    def test_activate_plan_not_found(self, manager):
        """测试激活不存在的计划"""
        with pytest.raises(PlanManagerError, match="计划不存在"):
            manager.activate_plan("non_existent")

    def test_activate_already_active_plan(self, manager):
        """测试激活已激活的计划"""
        plan = create_test_plan("test_plan_1")
        manager.create_plan(plan)
        manager.activate_plan("test_plan_1")

        with pytest.raises(PlanManagerError, match="当前状态不允许激活"):
            manager.activate_plan("test_plan_1")


class TestPlanManagerPause:
    """测试暂停计划"""

    @pytest.fixture
    def manager(self):
        """创建PlanManager实例"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            config = MagicMock()
            config.data_dir = data_dir
            context = create_mock_context(config=config)
            yield PlanManager(context)

    def test_pause_plan_success(self, manager):
        """测试成功暂停计划"""
        plan = create_test_plan("test_plan_1")
        manager.create_plan(plan)
        manager.activate_plan("test_plan_1")

        result = manager.pause_plan("test_plan_1")
        assert result is True

        status = manager.get_plan_status("test_plan_1")
        assert status == PlanStatus.PAUSED

    def test_pause_plan_not_found(self, manager):
        """测试暂停不存在的计划"""
        with pytest.raises(PlanManagerError, match="计划不存在"):
            manager.pause_plan("non_existent")

    def test_pause_draft_plan(self, manager):
        """测试暂停草稿计划"""
        plan = create_test_plan("test_plan_1")
        manager.create_plan(plan)

        with pytest.raises(PlanManagerError, match="当前状态不允许暂停"):
            manager.pause_plan("test_plan_1")


class TestPlanManagerComplete:
    """测试完成计划"""

    @pytest.fixture
    def manager(self):
        """创建PlanManager实例"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            config = MagicMock()
            config.data_dir = data_dir
            context = create_mock_context(config=config)
            yield PlanManager(context)

    def test_complete_plan_success(self, manager):
        """测试成功完成计划"""
        plan = create_test_plan("test_plan_1")
        manager.create_plan(plan)
        manager.activate_plan("test_plan_1")

        result = manager.complete_plan("test_plan_1")
        assert result is True

        status = manager.get_plan_status("test_plan_1")
        assert status == PlanStatus.COMPLETED

    def test_complete_plan_not_found(self, manager):
        """测试完成不存在的计划"""
        with pytest.raises(PlanManagerError, match="计划不存在"):
            manager.complete_plan("non_existent")

    def test_complete_draft_plan(self, manager):
        """测试完成草稿计划"""
        plan = create_test_plan("test_plan_1")
        manager.create_plan(plan)

        with pytest.raises(PlanManagerError, match="当前状态不允许完成"):
            manager.complete_plan("test_plan_1")


class TestPlanManagerList:
    """测试列出计划"""

    @pytest.fixture
    def manager(self):
        """创建PlanManager实例"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            config = MagicMock()
            config.data_dir = data_dir
            context = create_mock_context(config=config)
            yield PlanManager(context)

    def test_list_plans_empty(self, manager):
        """测试列出空计划列表"""
        plans = manager.list_plans()
        assert len(plans) == 0

    def test_list_plans_all(self, manager):
        """测试列出所有计划"""
        for i in range(5):
            plan = create_test_plan(f"plan_{i}")
            manager.create_plan(plan)

        plans = manager.list_plans()
        assert len(plans) == 5

    def test_list_plans_by_status(self, manager):
        """测试按状态列出计划"""
        for i in range(3):
            plan = create_test_plan(f"plan_{i}")
            manager.create_plan(plan)

        for i in range(3, 5):
            plan = create_test_plan(f"plan_{i}")
            manager.create_plan(plan)
            manager.activate_plan(f"plan_{i}")

        draft_plans = manager.list_plans(status=PlanStatus.DRAFT)
        assert len(draft_plans) == 3

        active_plans = manager.list_plans(status=PlanStatus.ACTIVE)
        assert len(active_plans) == 2

    def test_list_plans_with_limit(self, manager):
        """测试限制返回数量"""
        for i in range(10):
            plan = create_test_plan(f"plan_{i}")
            manager.create_plan(plan)

        plans = manager.list_plans(limit=5)
        assert len(plans) == 5


class TestPlanManagerDelete:
    """测试删除计划"""

    @pytest.fixture
    def manager(self):
        """创建PlanManager实例"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            config = MagicMock()
            config.data_dir = data_dir
            context = create_mock_context(config=config)
            yield PlanManager(context)

    def test_delete_plan_success(self, manager):
        """测试成功删除计划"""
        plan = create_test_plan("test_plan_1")
        manager.create_plan(plan)

        result = manager.delete_plan("test_plan_1")
        assert result is True

        assert "test_plan_1" not in manager._plans

    def test_delete_plan_not_found(self, manager):
        """测试删除不存在的计划"""
        with pytest.raises(PlanManagerError, match="计划不存在"):
            manager.delete_plan("non_existent")


class TestPlanManagerGetActive:
    """测试获取激活计划"""

    @pytest.fixture
    def manager(self):
        """创建PlanManager实例"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            config = MagicMock()
            config.data_dir = data_dir
            context = create_mock_context(config=config)
            yield PlanManager(context)

    def test_get_active_plan_success(self, manager):
        """测试成功获取激活计划"""
        plan = create_test_plan("test_plan_1")
        manager.create_plan(plan)
        manager.activate_plan("test_plan_1")

        active_plan = manager.get_active_plan()
        assert active_plan is not None
        assert active_plan.plan_id == "test_plan_1"

    def test_get_active_plan_none(self, manager):
        """测试无激活计划"""
        plan = create_test_plan("test_plan_1")
        manager.create_plan(plan)

        active_plan = manager.get_active_plan()
        assert active_plan is None

    def test_get_active_plan_multiple(self, manager):
        """测试多个激活计划（返回第一个）"""
        for i in range(3):
            plan = create_test_plan(f"plan_{i}")
            manager.create_plan(plan)
            manager.activate_plan(f"plan_{i}")

        active_plan = manager.get_active_plan()
        assert active_plan is not None
