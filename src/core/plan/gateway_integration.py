# Gateway Hook + Cron 集成模块 - v0.17.0
# 将训练提醒、流式输出等Hook集成到Gateway服务

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from nanobot.bus import MessageBus
from nanobot.cron.service import CronService
from rich.console import Console

from src.core.plan.cron_callback import CronCallbackHandler
from src.core.plan.training_reminder_manager import TrainingReminderManager
from src.core.transparency.streaming_hook import StreamingHook

logger = logging.getLogger(__name__)


class GatewayIntegration:
    """Gateway服务集成器

    负责将训练提醒、流式输出等组件集成到Gateway服务中。
    提供统一的初始化和配置接口。

    使用方式：
        integration = GatewayIntegration(workspace, bus)
        integration.setup_cron_service()  # 设置Cron服务
        integration.setup_streaming_hook()  # 设置流式输出
    """

    def __init__(
        self,
        workspace: Path,
        bus: MessageBus | None = None,
        console: Console | None = None,
        data_dir: Path | None = None,
    ) -> None:
        """初始化Gateway集成器

        Args:
            workspace: Gateway工作目录
            bus: 消息总线实例
            console: Rich控制台实例
            data_dir: 数据目录，默认使用workspace/data
        """
        self.workspace = workspace
        self.bus = bus
        self.console = console
        self.data_dir = data_dir or workspace / "data"

        # 组件实例
        self.reminder_manager: TrainingReminderManager | None = None
        self.cron_callback: CronCallbackHandler | None = None
        self.cron_service: CronService | None = None
        self.streaming_hook: StreamingHook | None = None

    def setup_cron_service(
        self,
        store_path: Path | None = None,
        auto_register_reminder: bool = True,
    ) -> CronService:
        """设置Cron服务并集成训练提醒

        Args:
            store_path: Cron存储路径，默认使用workspace/cron.json
            auto_register_reminder: 是否自动注册训练提醒任务

        Returns:
            CronService: 配置好的Cron服务实例
        """
        store_path = store_path or self.workspace / "cron.json"

        # 创建训练提醒管理器
        self.reminder_manager = TrainingReminderManager(data_dir=self.data_dir)

        # 创建Cron回调处理器
        self.cron_callback = CronCallbackHandler(
            reminder_manager=self.reminder_manager,
        )

        # 创建Cron服务
        self.cron_service = CronService(
            store_path=store_path,
            on_job=self.cron_callback.on_job,
        )

        # 自动注册训练提醒任务
        if auto_register_reminder and self.reminder_manager.schedule.enabled:
            self._register_training_reminder_job()

        logger.info(f"Cron服务已设置: {store_path}")
        return self.cron_service

    def _register_training_reminder_job(self) -> None:
        """注册训练提醒定时任务"""
        if self.cron_service is None:
            logger.warning("Cron服务未初始化，无法注册提醒任务")
            return

        try:
            # 检查是否已存在训练提醒任务
            existing = self.cron_service.list_jobs()
            has_reminder = any(
                job.name == CronCallbackHandler.TRAINING_REMINDER_JOB
                for job in existing
            )

            if has_reminder:
                logger.info("训练提醒任务已存在，跳过注册")
                return

            # 注册新的训练提醒任务
            assert self.reminder_manager is not None
            schedule = self.reminder_manager.schedule
            self.cron_service.register_job(
                name=CronCallbackHandler.TRAINING_REMINDER_JOB,
                cron_expr=schedule.cron_expression,
                metadata={
                    "type": "training_reminder",
                    "advance_minutes": schedule.advance_minutes,
                    "check_weather": schedule.check_weather,
                },
            )

            logger.info(f"训练提醒任务已注册: {schedule.cron_expression}")

        except Exception as e:
            logger.error(f"注册训练提醒任务失败: {e}", exc_info=True)

    def setup_streaming_hook(
        self,
        channel: str | None = None,
        chat_id: str | None = None,
    ) -> StreamingHook:
        """设置流式输出Hook

        配置双通道流式输出：CLI控制台 + Gateway消息总线。

        Args:
            channel: Gateway通道名称
            chat_id: 聊天ID

        Returns:
            StreamingHook: 配置好的流式输出钩子
        """
        self.streaming_hook = StreamingHook(
            console=self.console,
            bus=self.bus,
            channel=channel,
            chat_id=chat_id,
        )

        logger.info("流式输出Hook已设置")
        return self.streaming_hook

    def get_hooks(self) -> list[Any]:
        """获取所有已配置的Hook

        Returns:
            list[Any]: Hook实例列表
        """
        hooks = []

        if self.streaming_hook is not None:
            hooks.append(self.streaming_hook)

        return hooks

    def get_cron_status(self) -> dict[str, Any]:
        """获取Cron服务状态

        Returns:
            dict: 包含任务数量、提醒状态等信息
        """
        if self.cron_service is None:
            return {"enabled": False, "message": "Cron服务未初始化"}

        try:
            status = self.cron_service.status()
            jobs = self.cron_service.list_jobs()

            reminder_job = None
            for job in jobs:
                if job.name == CronCallbackHandler.TRAINING_REMINDER_JOB:
                    reminder_job = {
                        "id": job.id,
                        "name": job.name,
                        "cron": job.cron_expr,
                        "enabled": job.enabled,
                    }
                    break

            return {
                "enabled": True,
                "jobs_count": status.get("jobs", 0),
                "reminder_job": reminder_job,
                "reminder_enabled": (
                    self.reminder_manager.schedule.enabled
                    if self.reminder_manager
                    else False
                ),
            }

        except Exception as e:
            logger.error(f"获取Cron状态失败: {e}")
            return {"enabled": True, "error": str(e)}

    def shutdown(self) -> None:
        """关闭所有集成组件"""
        if self.cron_service is not None:
            try:
                self.cron_service.stop()
                logger.info("Cron服务已停止")
            except Exception as e:
                logger.warning(f"停止Cron服务异常: {e}")

        self.reminder_manager = None
        self.cron_callback = None
        self.cron_service = None
        self.streaming_hook = None
