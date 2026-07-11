"""HeartbeatTaskManager 单元测试

覆盖任务注册、注销、执行、状态查询等场景。
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.core.base.exceptions import NanobotRunnerError
from src.core.plan.heartbeat_tasks import (
    HeartbeatTask,
    HeartbeatTaskManager,
    HeartbeatTaskType,
    TaskPriority,
    create_data_sync_task,
    create_health_check_task,
    create_training_status_task,
)


def _make_task(
    name: str = "test_task",
    task_type: HeartbeatTaskType = HeartbeatTaskType.HEALTH_CHECK,
    priority: TaskPriority = TaskPriority.NORMAL,
    interval_seconds: int = 60,
    enabled: bool = True,
    handler=None,
) -> HeartbeatTask:
    """创建测试用心跳任务"""
    return HeartbeatTask(
        name=name,
        task_type=task_type,
        priority=priority,
        interval_seconds=interval_seconds,
        enabled=enabled,
        handler=handler or (lambda: {"ok": True}),
    )


class TestHeartbeatTaskManagerRegister:
    """任务注册与注销"""

    def test_register_task(self):
        manager = HeartbeatTaskManager()
        task = _make_task("task1")
        manager.register_task(task)
        assert "task1" in manager
        assert manager.task_count == 1

    def test_unregister_task_success(self):
        manager = HeartbeatTaskManager()
        manager.register_task(_make_task("task1"))
        assert manager.unregister_task("task1") is True
        assert "task1" not in manager
        assert manager.task_count == 0

    def test_unregister_nonexistent_returns_false(self):
        manager = HeartbeatTaskManager()
        assert manager.unregister_task("nonexistent") is False


class TestHeartbeatTaskManagerQuery:
    """任务查询"""

    def test_get_task_returns_task(self):
        manager = HeartbeatTaskManager()
        task = _make_task("task1")
        manager.register_task(task)
        assert manager.get_task("task1") is task

    def test_get_task_nonexistent_returns_none(self):
        manager = HeartbeatTaskManager()
        assert manager.get_task("nonexistent") is None

    def test_get_enabled_tasks_filters_disabled(self):
        manager = HeartbeatTaskManager()
        manager.register_task(_make_task("enabled_task", enabled=True))
        manager.register_task(_make_task("disabled_task", enabled=False))
        enabled = manager.get_enabled_tasks()
        assert len(enabled) == 1
        assert enabled[0].name == "enabled_task"

    def test_get_tasks_by_type(self):
        manager = HeartbeatTaskManager()
        manager.register_task(
            _make_task("health_task", task_type=HeartbeatTaskType.HEALTH_CHECK)
        )
        manager.register_task(
            _make_task("sync_task", task_type=HeartbeatTaskType.DATA_SYNC)
        )
        health_tasks = manager.get_tasks_by_type(HeartbeatTaskType.HEALTH_CHECK)
        assert len(health_tasks) == 1
        assert health_tasks[0].name == "health_task"

    def test_get_tasks_by_priority(self):
        manager = HeartbeatTaskManager()
        manager.register_task(_make_task("high", priority=TaskPriority.HIGH))
        manager.register_task(_make_task("normal", priority=TaskPriority.NORMAL))
        high_tasks = manager.get_tasks_by_priority(TaskPriority.HIGH)
        assert len(high_tasks) == 1
        assert high_tasks[0].name == "high"


class TestHeartbeatTaskManagerToggle:
    """任务启用/禁用与间隔更新"""

    def test_enable_task(self):
        manager = HeartbeatTaskManager()
        manager.register_task(_make_task("task1", enabled=False))
        assert manager.enable_task("task1") is True
        assert manager.get_task("task1").enabled is True

    def test_enable_nonexistent_returns_false(self):
        manager = HeartbeatTaskManager()
        assert manager.enable_task("nonexistent") is False

    def test_disable_task(self):
        manager = HeartbeatTaskManager()
        manager.register_task(_make_task("task1", enabled=True))
        assert manager.disable_task("task1") is True
        assert manager.get_task("task1").enabled is False

    def test_disable_nonexistent_returns_false(self):
        manager = HeartbeatTaskManager()
        assert manager.disable_task("nonexistent") is False

    def test_update_interval(self):
        manager = HeartbeatTaskManager()
        manager.register_task(_make_task("task1", interval_seconds=60))
        assert manager.update_interval("task1", 120) is True
        assert manager.get_task("task1").interval_seconds == 120

    def test_update_interval_nonexistent_returns_false(self):
        manager = HeartbeatTaskManager()
        assert manager.update_interval("nonexistent", 120) is False


class TestHeartbeatTaskManagerExecute:
    """任务执行"""

    def test_execute_task_calls_handler(self):
        manager = HeartbeatTaskManager()
        handler = MagicMock(return_value={"result": "ok"})
        manager.register_task(_make_task("task1", handler=handler))
        result = manager.execute_task("task1")
        assert result == {"result": "ok"}
        handler.assert_called_once()

    def test_execute_nonexistent_raises_key_error(self):
        manager = HeartbeatTaskManager()
        with pytest.raises(KeyError, match="任务不存在"):
            manager.execute_task("nonexistent")

    def test_execute_disabled_task_returns_none(self):
        manager = HeartbeatTaskManager()
        handler = MagicMock()
        manager.register_task(_make_task("task1", enabled=False, handler=handler))
        result = manager.execute_task("task1")
        assert result is None
        handler.assert_not_called()

    def test_execute_task_propagates_nanobot_error(self):
        manager = HeartbeatTaskManager()

        def failing_handler():
            raise NanobotRunnerError("task failed")

        manager.register_task(_make_task("task1", handler=failing_handler))
        with pytest.raises(NanobotRunnerError, match="task failed"):
            manager.execute_task("task1")

    def test_execute_all_ready_runs_due_tasks(self):
        manager = HeartbeatTaskManager()
        handler = MagicMock(return_value="done")
        manager.register_task(_make_task("task1", interval_seconds=0, handler=handler))
        results = manager.execute_all_ready()
        assert "task1" in results
        assert results["task1"] == "done"

    def test_execute_all_ready_skips_disabled(self):
        manager = HeartbeatTaskManager()
        handler = MagicMock(return_value="done")
        manager.register_task(
            _make_task("disabled", enabled=False, interval_seconds=0, handler=handler)
        )
        results = manager.execute_all_ready()
        assert "disabled" not in results

    def test_execute_all_ready_captures_errors(self):
        manager = HeartbeatTaskManager()

        def failing_handler():
            raise NanobotRunnerError("failed")

        manager.register_task(
            _make_task("task1", interval_seconds=0, handler=failing_handler)
        )
        results = manager.execute_all_ready()
        assert "task1" in results
        assert isinstance(results["task1"], NanobotRunnerError)


class TestHeartbeatTaskManagerStatus:
    """任务状态查询"""

    def test_get_task_status(self):
        manager = HeartbeatTaskManager()
        manager.register_task(_make_task("task1"))
        status = manager.get_task_status("task1")
        assert status is not None
        assert status["name"] == "task1"
        assert status["enabled"] is True
        assert status["type"] == "health_check"

    def test_get_task_status_nonexistent_returns_none(self):
        manager = HeartbeatTaskManager()
        assert manager.get_task_status("nonexistent") is None

    def test_get_all_status(self):
        manager = HeartbeatTaskManager()
        manager.register_task(_make_task("task1"))
        manager.register_task(_make_task("task2"))
        statuses = manager.get_all_status()
        assert len(statuses) == 2

    def test_enabled_count_property(self):
        manager = HeartbeatTaskManager()
        manager.register_task(_make_task("enabled", enabled=True))
        manager.register_task(_make_task("disabled", enabled=False))
        assert manager.enabled_count == 1

    def test_len_dunder(self):
        manager = HeartbeatTaskManager()
        manager.register_task(_make_task("task1"))
        manager.register_task(_make_task("task2"))
        assert len(manager) == 2


class TestHeartbeatTaskFactories:
    """预定义任务工厂函数"""

    def test_create_health_check_task_default(self):
        task = create_health_check_task()
        assert task.name == "health_check"
        assert task.task_type == HeartbeatTaskType.HEALTH_CHECK
        assert task.priority == TaskPriority.HIGH
        assert task.enabled is True
        # 默认 handler 应可执行
        result = task.handler()
        assert "status" in result

    def test_create_health_check_task_custom_handler(self):
        custom = MagicMock(return_value="custom")
        task = create_health_check_task(handler=custom)
        assert task.handler is custom

    def test_create_training_status_task_default(self):
        task = create_training_status_task()
        assert task.name == "training_status"
        assert task.task_type == HeartbeatTaskType.TRAINING_STATUS
        assert task.priority == TaskPriority.NORMAL
        result = task.handler()
        assert "training_status" in result

    def test_create_training_status_task_custom_handler(self):
        custom = MagicMock(return_value="custom")
        task = create_training_status_task(handler=custom)
        assert task.handler is custom

    def test_create_data_sync_task_default(self):
        task = create_data_sync_task()
        assert task.name == "data_sync"
        assert task.task_type == HeartbeatTaskType.DATA_SYNC
        assert task.priority == TaskPriority.LOW
        result = task.handler()
        assert "sync_status" in result

    def test_create_data_sync_task_custom_handler(self):
        custom = MagicMock(return_value="custom")
        task = create_data_sync_task(handler=custom)
        assert task.handler is custom
