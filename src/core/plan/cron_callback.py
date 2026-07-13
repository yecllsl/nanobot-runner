# Cron 回调处理模块 - v0.17.0
# 处理 CronService 的 on_job 回调，支持训练提醒等定时任务

import logging
from typing import Any

from nanobot.cron.session_delivery import origin_delivery_context
from nanobot.cron.types import CronJob

from src.core.base.exceptions import NanobotRunnerError
from src.core.plan.training_reminder_manager import TrainingReminderManager

logger = logging.getLogger(__name__)


class CronCallbackHandler:
    """Cron 回调处理器

    处理 CronService 的 on_job 回调，根据任务类型分发到不同的处理器。

    支持的任务类型：
    - training_reminder: 训练提醒任务
    - heartbeat: 心跳检测任务 (v0.30.0)
    - system_event: 系统事件（受保护，不可删除）
    - agent_turn: 默认的Agent轮询任务

    使用方式：
        # 在 Gateway 启动时注册
        reminder_manager = TrainingReminderManager()
        callback_handler = CronCallbackHandler(reminder_manager)

        cron = CronService(
            store_path=workspace / "cron.json",
            on_job=callback_handler.on_job,
        )
    """

    # 系统任务名称前缀
    SYSTEM_JOB_PREFIX: str = "system_"
    # 训练提醒任务名称
    TRAINING_REMINDER_JOB: str = "training_reminder"
    # 心跳检测任务名称 (v0.30.0)
    HEARTBEAT_JOB: str = "heartbeat"

    def __init__(
        self,
        reminder_manager: TrainingReminderManager | None = None,
    ):
        """初始化回调处理器

        Args:
            reminder_manager: 训练提醒管理器实例
        """
        self.reminder_manager = reminder_manager

        logger.info("CronCallbackHandler 初始化完成")

    async def on_job(self, job: CronJob) -> str | None:
        """CronService on_job 回调入口

        根据任务名称分发到对应的处理器。

        Args:
            job: CronJob 实例

        Returns:
            Optional[str]: 处理结果消息，None表示无需返回
        """
        logger.info("Cron任务执行: %s (%s)", job.name, job.id)

        try:
            # 根据任务名称分发
            if job.name == self.TRAINING_REMINDER_JOB:
                return await self._handle_training_reminder(job)
            elif job.name == self.HEARTBEAT_JOB:
                return await self._handle_heartbeat(job)
            elif job.name.startswith(self.SYSTEM_JOB_PREFIX):
                return await self._handle_system_event(job)
            else:
                # 默认处理：记录日志
                return await self._handle_default(job)

        except NanobotRunnerError as e:
            logger.error("Cron任务处理异常: %s - %s", job.name, e, exc_info=True)
            raise  # 抛出异常让 CronService 记录错误状态

    async def _handle_training_reminder(self, job: CronJob) -> str | None:
        """处理训练提醒任务

        Args:
            job: CronJob 实例

        Returns:
            Optional[str]: 处理结果
        """
        if self.reminder_manager is None:
            logger.warning("训练提醒管理器未初始化，跳过任务")
            return "提醒管理器未初始化"

        # 调用 TrainingReminderManager 的触发方法
        result = self.reminder_manager.on_reminder_trigger()

        if result.get("sent"):
            logger.info("训练提醒发送成功: %s", result.get("record", {}).get("id"))
            return f"训练提醒已发送: {result['record']['message']}"
        elif result.get("reason") == "disabled":
            logger.info("训练提醒功能已禁用")
            return "提醒功能已禁用"
        elif result.get("reason") == "no_plan":
            logger.info("今日无训练计划")
            return "今日无训练计划"
        elif result.get("reason") == "do_not_disturb":
            logger.info("免打扰时段，跳过提醒")
            return "免打扰时段"
        else:
            logger.warning("训练提醒未发送: %s", result.get("reason"))
            return f"提醒未发送: {result.get('reason', '未知原因')}"

    async def _handle_system_event(self, job: CronJob) -> str | None:
        """处理系统事件任务

        Args:
            job: CronJob 实例

        Returns:
            Optional[str]: 处理结果
        """
        logger.debug("系统事件任务: %s", job.name)
        # 系统事件通常由其他组件处理
        # 这里仅记录日志
        return f"系统事件已处理: {job.name}"

    async def _handle_heartbeat(self, job: CronJob) -> str | None:
        """处理心跳检测任务 (v0.30.0)

        替代原 HeartbeatService，由 CronService 统一调度。

        Args:
            job: CronJob 实例

        Returns:
            Optional[str]: 处理结果
        """
        logger.debug("心跳检测执行中")
        return "心跳检测完成"

    def _resolve_delivery_context(
        self, job: CronJob
    ) -> tuple[str, str, dict[str, Any]] | None:
        """解析 CronJob 的投递上下文

        使用 nanobot 0.2.2 的 origin_delivery_context 函数提取
        (channel, chat_id, metadata)。如果 job 没有投递上下文，返回 None。

        Args:
            job: CronJob 实例

        Returns:
            tuple[channel, chat_id, metadata] | None
        """
        try:
            return origin_delivery_context(job)
        except ValueError:
            # job 没有 origin delivery context，这是正常的
            return None

    async def _handle_default(self, job: CronJob) -> str | None:
        """默认任务处理

        对于 agent_turn 类型的任务，提取会话信息并记录。
        使用 nanobot 0.2.2 的 origin_delivery_context 解析投递上下文。

        Args:
            job: CronJob 实例

        Returns:
            Optional[str]: 处理结果
        """
        session_key = getattr(job.payload, "session_key", None) if job.payload else None
        delivery_ctx = self._resolve_delivery_context(job)

        if delivery_ctx is not None:
            channel, chat_id, metadata = delivery_ctx
            logger.debug(
                "会话绑定任务: %s, session=%s, channel=%s, chat_id=%s",
                job.name,
                session_key or "unknown",
                channel,
                chat_id,
            )
            return f"任务已记录: {job.name} (session={session_key or 'unknown'}, channel={channel})"

        # ponytail: 移除了未使用的 msg 变量；新增 session_key 存在但无 delivery context 的分支
        if session_key is not None:
            logger.debug(
                "会话任务(无投递上下文): %s, session=%s",
                job.name,
                session_key,
            )
            return f"任务已记录: {job.name} (session={session_key})"

        logger.debug("默认任务处理: %s", job.name)
        if job.payload and job.payload.message:
            return f"任务已记录: {job.name} - {job.payload.message[:50]}"
        return f"任务已记录: {job.name}"

    def create_training_reminder_job(
        self,
        cron_expr: str = "0 7 * * *",
        tz: str | None = None,
    ) -> dict[str, Any]:
        """创建训练提醒 CronJob 配置

        Args:
            cron_expr: Cron 表达式，默认每天早上7点
            tz: 时区

        Returns:
            dict: CronJob 配置字典
        """
        from nanobot.cron.types import CronSchedule

        schedule = CronSchedule(
            kind="cron",
            expr=cron_expr,
            tz=tz,
        )

        return {
            "id": self.TRAINING_REMINDER_JOB,
            "name": self.TRAINING_REMINDER_JOB,
            "enabled": True,
            "schedule": {
                "kind": schedule.kind,
                "expr": schedule.expr,
                "tz": schedule.tz,
            },
            "payload": {
                "kind": "system_event",
                "message": "训练提醒",
            },
        }
