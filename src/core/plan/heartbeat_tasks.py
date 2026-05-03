# Heartbeat 任务扩展模块 - v0.17.0
# 扩展心跳服务，支持训练状态检查、数据同步等任务

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class HeartbeatTaskType(Enum):
    """心跳任务类型枚举"""

    HEALTH_CHECK = "health_check"  # 健康检查
    DATA_SYNC = "data_sync"  # 数据同步
    TRAINING_STATUS = "training_status"  # 训练状态检查
    PLAN_REMINDER = "plan_reminder"  # 计划提醒
    SYSTEM_CLEANUP = "system_cleanup"  # 系统清理


class TaskPriority(Enum):
    """任务优先级枚举"""

    HIGH = 1
    NORMAL = 2
    LOW = 3


@dataclass
class HeartbeatTask:
    """心跳任务数据类

    Attributes:
        name: 任务名称
        task_type: 任务类型
        priority: 任务优先级
        interval_seconds: 执行间隔（秒）
        enabled: 是否启用
        handler: 任务处理函数
    """

    name: str
    task_type: HeartbeatTaskType
    priority: TaskPriority
    interval_seconds: int
    enabled: bool
    handler: Callable[..., Any]


class HeartbeatTaskManager:
    """心跳任务管理器

    管理所有心跳任务，支持动态添加、移除和配置任务。

    使用方式：
        manager = HeartbeatTaskManager()
        manager.register_task(health_check_task)
        tasks = manager.get_ready_tasks()
    """

    def __init__(self) -> None:
        """初始化任务管理器"""
        self._tasks: dict[str, HeartbeatTask] = {}
        self._last_execution: dict[str, float] = {}

    def register_task(self, task: HeartbeatTask) -> None:
        """注册任务

        Args:
            task: 心跳任务
        """
        self._tasks[task.name] = task
        logger.info(f"心跳任务已注册: {task.name} ({task.task_type.value})")

    def unregister_task(self, name: str) -> bool:
        """注销任务

        Args:
            name: 任务名称

        Returns:
            bool: 是否成功注销
        """
        if name in self._tasks:
            del self._tasks[name]
            self._last_execution.pop(name, None)
            logger.info(f"心跳任务已注销: {name}")
            return True
        return False

    def get_task(self, name: str) -> HeartbeatTask | None:
        """获取任务

        Args:
            name: 任务名称

        Returns:
            HeartbeatTask | None: 任务实例
        """
        return self._tasks.get(name)

    def get_enabled_tasks(self) -> list[HeartbeatTask]:
        """获取启用的任务

        Returns:
            list[HeartbeatTask]: 启用的任务列表
        """
        return [task for task in self._tasks.values() if task.enabled]

    def get_tasks_by_type(
        self,
        task_type: HeartbeatTaskType,
    ) -> list[HeartbeatTask]:
        """获取指定类型的任务

        Args:
            task_type: 任务类型

        Returns:
            list[HeartbeatTask]: 该类型的任务列表
        """
        return [task for task in self._tasks.values() if task.task_type == task_type]

    def get_tasks_by_priority(
        self,
        priority: TaskPriority,
    ) -> list[HeartbeatTask]:
        """获取指定优先级的任务

        Args:
            priority: 任务优先级

        Returns:
            list[HeartbeatTask]: 该优先级的任务列表
        """
        return [task for task in self._tasks.values() if task.priority == priority]

    def enable_task(self, name: str) -> bool:
        """启用任务

        Args:
            name: 任务名称

        Returns:
            bool: 是否成功启用
        """
        if name in self._tasks:
            self._tasks[name].enabled = True
            logger.info(f"心跳任务已启用: {name}")
            return True
        return False

    def disable_task(self, name: str) -> bool:
        """禁用任务

        Args:
            name: 任务名称

        Returns:
            bool: 是否成功禁用
        """
        if name in self._tasks:
            self._tasks[name].enabled = False
            logger.info(f"心跳任务已禁用: {name}")
            return True
        return False

    def update_interval(self, name: str, interval_seconds: int) -> bool:
        """更新任务执行间隔

        Args:
            name: 任务名称
            interval_seconds: 新的间隔（秒）

        Returns:
            bool: 是否成功更新
        """
        if name in self._tasks:
            self._tasks[name].interval_seconds = interval_seconds
            logger.info(f"任务 {name} 间隔已更新: {interval_seconds}s")
            return True
        return False

    def execute_task(self, name: str) -> Any:
        """执行指定任务

        Args:
            name: 任务名称

        Returns:
            任务执行结果

        Raises:
            KeyError: 任务不存在时抛出
        """
        if name not in self._tasks:
            raise KeyError(f"任务不存在: {name}")

        task = self._tasks[name]
        if not task.enabled:
            logger.warning(f"任务已禁用，跳过执行: {name}")
            return None

        try:
            logger.debug(f"执行任务: {name}")
            result = task.handler()
            self._last_execution[name] = __import__("time").time()
            return result
        except Exception as e:
            logger.error(f"任务执行失败: {name} - {e}")
            raise

    def execute_all_ready(self) -> dict[str, Any]:
        """执行所有就绪的任务

        Returns:
            dict[str, Any]: 任务执行结果
        """
        import time

        results = {}
        current_time = time.time()

        for name, task in self._tasks.items():
            if not task.enabled:
                continue

            last_run = self._last_execution.get(name, 0)
            if current_time - last_run >= task.interval_seconds:
                try:
                    result = self.execute_task(name)
                    results[name] = result
                except Exception as e:
                    results[name] = e

        return results

    def get_task_status(self, name: str) -> dict[str, Any] | None:
        """获取任务状态

        Args:
            name: 任务名称

        Returns:
            dict | None: 任务状态信息
        """
        if name not in self._tasks:
            return None

        task = self._tasks[name]
        return {
            "name": task.name,
            "type": task.task_type.value,
            "priority": task.priority.name,
            "enabled": task.enabled,
            "interval_seconds": task.interval_seconds,
            "last_execution": self._last_execution.get(name),
        }

    def get_all_status(self) -> list[dict[str, Any]]:
        """获取所有任务状态

        Returns:
            list[dict]: 所有任务状态
        """
        return [
            status
            for name in self._tasks
            if (status := self.get_task_status(name)) is not None
        ]

    @property
    def task_count(self) -> int:
        """任务总数"""
        return len(self._tasks)

    @property
    def enabled_count(self) -> int:
        """启用的任务数"""
        return sum(1 for t in self._tasks.values() if t.enabled)

    def __contains__(self, name: str) -> bool:
        """检查是否包含指定任务"""
        return name in self._tasks

    def __len__(self) -> int:
        """任务数量"""
        return len(self._tasks)


# 预定义任务工厂


def create_health_check_task(
    handler: Callable[..., Any] | None = None,
) -> HeartbeatTask:
    """创建健康检查任务

    Args:
        handler: 自定义处理函数

    Returns:
        HeartbeatTask: 健康检查任务
    """

    def default_handler() -> dict[str, Any]:
        return {"status": "healthy", "timestamp": __import__("time").time()}

    return HeartbeatTask(
        name="health_check",
        task_type=HeartbeatTaskType.HEALTH_CHECK,
        priority=TaskPriority.HIGH,
        interval_seconds=300,  # 5分钟
        enabled=True,
        handler=handler or default_handler,
    )


def create_training_status_task(
    handler: Callable[..., Any] | None = None,
) -> HeartbeatTask:
    """创建训练状态检查任务

    Args:
        handler: 自定义处理函数

    Returns:
        HeartbeatTask: 训练状态检查任务
    """

    def default_handler() -> dict[str, Any]:
        return {"training_status": "checked", "timestamp": __import__("time").time()}

    return HeartbeatTask(
        name="training_status",
        task_type=HeartbeatTaskType.TRAINING_STATUS,
        priority=TaskPriority.NORMAL,
        interval_seconds=3600,  # 1小时
        enabled=True,
        handler=handler or default_handler,
    )


def create_data_sync_task(
    handler: Callable[..., Any] | None = None,
) -> HeartbeatTask:
    """创建数据同步任务

    Args:
        handler: 自定义处理函数

    Returns:
        HeartbeatTask: 数据同步任务
    """

    def default_handler() -> dict[str, Any]:
        return {"sync_status": "completed", "timestamp": __import__("time").time()}

    return HeartbeatTask(
        name="data_sync",
        task_type=HeartbeatTaskType.DATA_SYNC,
        priority=TaskPriority.LOW,
        interval_seconds=86400,  # 1天
        enabled=True,
        handler=handler or default_handler,
    )
