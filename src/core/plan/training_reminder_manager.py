# 训练提醒管理器 - v0.17.0
# 负责管理定时训练提醒的调度、执行和状态跟踪

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any

from src.core.config import ConfigManager
from src.core.plan.notify_tool import NotifyTool, SkipReason

logger = logging.getLogger(__name__)


class ReminderStatus(StrEnum):
    """提醒任务状态"""

    PENDING = "pending"  # 待执行
    SENT = "sent"  # 已发送
    SKIPPED = "skipped"  # 已跳过
    FAILED = "failed"  # 发送失败


@dataclass
class ReminderRecord:
    """提醒记录"""

    id: str  # 记录ID
    date: str  # 目标日期
    scheduled_time: str  # 计划发送时间
    status: ReminderStatus  # 状态
    message: str = ""  # 结果消息
    skip_reason: str | None = None  # 跳过原因
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    executed_at: str | None = None  # 执行时间


@dataclass
class ReminderSchedule:
    """提醒调度配置"""

    enabled: bool = True  # 是否启用
    cron_expression: str = "0 7 * * *"  # 默认每天早上7点
    advance_minutes: int = 30  # 提前提醒分钟数
    check_weather: bool = True  # 是否检查天气
    do_not_disturb_start: str = "22:00"  # 免打扰开始时间
    do_not_disturb_end: str = "07:00"  # 免打扰结束时间


class TrainingReminderManager:
    """训练提醒管理器

    职责：
    1. 管理提醒调度配置
    2. 执行定时提醒任务（被CronService调用）
    3. 跟踪提醒发送状态
    4. 提供提醒历史查询
    5. 支持智能免打扰判断

    使用方式：
        # 在CronService中注册
        cron_service.register_job(
            name="training_reminder",
            cron_expr="0 7 * * *",
            callback=reminder_manager.on_reminder_trigger,
        )
    """

    # 提醒历史文件
    HISTORY_FILE: str = "reminder_history.json"
    # 最大历史记录数
    MAX_HISTORY: int = 100

    def __init__(
        self,
        notify_tool: NotifyTool | None = None,
        config: ConfigManager | None = None,
        data_dir: Path | None = None,
    ):
        """初始化训练提醒管理器

        Args:
            notify_tool: 通知工具实例
            config: 配置管理器
            data_dir: 数据目录
        """
        self.notify_tool = notify_tool or NotifyTool()
        self.config = config
        self.data_dir = data_dir or self._get_default_data_dir()
        self.history_file = self.data_dir / self.HISTORY_FILE

        # 加载调度配置
        self.schedule = self._load_schedule()

        # 加载历史记录
        self.history: list[ReminderRecord] = self._load_history()

        logger.info("TrainingReminderManager 初始化完成")

    def _get_default_data_dir(self) -> Path:
        """获取默认数据目录"""
        try:
            from src.core.base.context import get_context

            context = get_context()
            if hasattr(context, "config") and hasattr(context.config, "data_dir"):
                return Path(context.config.data_dir)
        except Exception:
            pass

        # 默认目录
        default_dir = Path.home() / ".nanobot-runner"
        default_dir.mkdir(parents=True, exist_ok=True)
        return default_dir

    def _load_schedule(self) -> ReminderSchedule:
        """加载调度配置"""
        if self.config is None:
            return ReminderSchedule()

        try:
            reminder_config = self.config.get("reminder", {})
            return ReminderSchedule(
                enabled=reminder_config.get("enabled", True),
                cron_expression=reminder_config.get("cron", "0 7 * * *"),
                advance_minutes=reminder_config.get("advance_minutes", 30),
                check_weather=reminder_config.get("check_weather", True),
                do_not_disturb_start=reminder_config.get(
                    "do_not_disturb_start", "22:00"
                ),
                do_not_disturb_end=reminder_config.get("do_not_disturb_end", "07:00"),
            )
        except Exception as e:
            logger.warning(f"加载提醒配置失败: {e}，使用默认配置")
            return ReminderSchedule()

    def _load_history(self) -> list[ReminderRecord]:
        """加载历史记录"""
        if not self.history_file.exists():
            return []

        try:
            with open(self.history_file, encoding="utf-8") as f:
                data = json.load(f)

            records = []
            for item in data:
                try:
                    record = ReminderRecord(
                        id=item.get("id", ""),
                        date=item.get("date", ""),
                        scheduled_time=item.get("scheduled_time", ""),
                        status=ReminderStatus(item.get("status", "pending")),
                        message=item.get("message", ""),
                        skip_reason=item.get("skip_reason"),
                        created_at=item.get("created_at", ""),
                        executed_at=item.get("executed_at"),
                    )
                    records.append(record)
                except Exception as e:
                    logger.warning(f"解析历史记录失败: {e}")

            return records
        except Exception as e:
            logger.warning(f"加载提醒历史失败: {e}")
            return []

    def _save_history(self) -> None:
        """保存历史记录"""
        try:
            # 限制历史记录数量
            records = self.history[-self.MAX_HISTORY :]

            data = []
            for record in records:
                data.append(
                    {
                        "id": record.id,
                        "date": record.date,
                        "scheduled_time": record.scheduled_time,
                        "status": record.status.value,
                        "message": record.message,
                        "skip_reason": record.skip_reason,
                        "created_at": record.created_at,
                        "executed_at": record.executed_at,
                    }
                )

            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"保存提醒历史失败: {e}")

    def on_reminder_trigger(self, **kwargs: Any) -> dict[str, Any]:
        """提醒触发回调（供CronService调用）

        这是CronService调用的主入口，执行完整的提醒流程：
        1. 检查提醒功能是否启用
        2. 获取今日训练计划
        3. 判断免打扰规则
        4. 发送提醒
        5. 记录执行结果

        Args:
            **kwargs: CronService传入的参数

        Returns:
            dict: 执行结果
        """
        trigger_time = datetime.now().isoformat()
        record_id = f"reminder_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        logger.info(f"训练提醒触发: {trigger_time}")

        # 1. 检查提醒功能是否启用
        if not self.schedule.enabled:
            logger.info("训练提醒功能已禁用")
            result = self._create_record(
                record_id=record_id,
                status=ReminderStatus.SKIPPED,
                message="提醒功能已禁用",
                skip_reason=SkipReason.DISABLED.value,
            )
            return {
                "success": True,
                "sent": False,
                "reason": "disabled",
                "record": result,
            }

        # 2. 获取今日训练计划
        daily_plan = self._get_today_plan()
        if daily_plan is None:
            logger.info("今日无训练计划")
            result = self._create_record(
                record_id=record_id,
                status=ReminderStatus.SKIPPED,
                message="今日无训练计划",
                skip_reason=SkipReason.NO_PLAN.value,
            )
            return {
                "success": True,
                "sent": False,
                "reason": "no_plan",
                "record": result,
            }

        # 3. 检查免打扰规则
        skip_reason = self._check_do_not_disturb()
        if skip_reason:
            logger.info(f"免打扰规则触发: {skip_reason}")
            result = self._create_record(
                record_id=record_id,
                status=ReminderStatus.SKIPPED,
                message=f"免打扰: {skip_reason}",
                skip_reason=skip_reason,
            )
            return {
                "success": True,
                "sent": False,
                "reason": "do_not_disturb",
                "record": result,
            }

        # 4. 发送提醒
        try:
            notify_result = self._send_reminder(daily_plan)

            if notify_result.sent:
                result = self._create_record(
                    record_id=record_id,
                    status=ReminderStatus.SENT,
                    message="提醒发送成功",
                )
                return {"success": True, "sent": True, "record": result}
            elif notify_result.skipped:
                result = self._create_record(
                    record_id=record_id,
                    status=ReminderStatus.SKIPPED,
                    message=notify_result.message,
                    skip_reason=notify_result.skip_reason,
                )
                return {
                    "success": True,
                    "sent": False,
                    "reason": "skipped",
                    "record": result,
                }
            else:
                result = self._create_record(
                    record_id=record_id,
                    status=ReminderStatus.FAILED,
                    message=notify_result.message,
                )
                return {
                    "success": False,
                    "sent": False,
                    "reason": "failed",
                    "record": result,
                }

        except Exception as e:
            logger.error(f"发送提醒异常: {e}", exc_info=True)
            result = self._create_record(
                record_id=record_id,
                status=ReminderStatus.FAILED,
                message=f"发送异常: {str(e)}",
            )
            return {
                "success": False,
                "sent": False,
                "reason": "exception",
                "record": result,
            }

    def _get_today_plan(self) -> Any | None:
        """获取今日训练计划

        Returns:
            Optional[DailyPlan]: 今日训练计划
        """
        try:
            # 尝试从PlanManager获取今日计划
            from src.core.base.context import get_context

            context = get_context()
            if hasattr(context, "plan_manager"):
                plan_manager = context.plan_manager
                today = datetime.now().strftime("%Y-%m-%d")
                # 获取当前激活的计划
                active_plan = plan_manager.get_active_plan()
                if active_plan:
                    # 查找今日计划
                    for week in active_plan.weeks:
                        for daily_plan in week.daily_plans:
                            if daily_plan.date == today:
                                return daily_plan

            logger.debug("未找到今日训练计划")
            return None

        except Exception as e:
            logger.warning(f"获取今日计划失败: {e}")
            return None

    def _check_do_not_disturb(self) -> str | None:
        """检查免打扰规则

        Returns:
            Optional[str]: 免打扰原因，None表示不跳过
        """
        now = datetime.now()
        current_time = now.strftime("%H:%M")

        # 检查免打扰时段
        dnd_start = self.schedule.do_not_disturb_start
        dnd_end = self.schedule.do_not_disturb_end

        # 处理跨午夜的情况
        if dnd_start <= dnd_end:
            # 不跨午夜（如 10:00 - 12:00）
            if dnd_start <= current_time <= dnd_end:
                return f"免打扰时段 ({dnd_start} - {dnd_end})"
        else:
            # 跨午夜（如 22:00 - 07:00）
            if current_time >= dnd_start or current_time <= dnd_end:
                return f"免打扰时段 ({dnd_start} - {dnd_end})"

        return None

    def _send_reminder(self, daily_plan: Any) -> Any:
        """发送训练提醒

        Args:
            daily_plan: 日训练计划

        Returns:
            NotifyResult: 通知结果
        """
        # 构建简化版的UserContext
        # 实际生产环境应从用户画像获取完整信息
        from src.core.models import (
            TrainingLoad,
            UserContext,
            UserPreferences,
        )

        user_context = UserContext(
            profile={},
            preferences=UserPreferences(
                enable_training_reminder=True,
                weather_alert_enabled=self.schedule.check_weather,
            ),
            recent_activities=[],
            training_load=TrainingLoad(
                atl=0.0,
                ctl=0.0,
                tsb=0.0,
            ),
            historical_best_pace_min_per_km=0.0,
        )

        return self.notify_tool.send_reminder(
            daily_plan=daily_plan,
            user_context=user_context,
            check_do_not_disturb=False,  # 已在前面检查
        )

    def _create_record(
        self,
        record_id: str,
        status: ReminderStatus,
        message: str,
        skip_reason: str | None = None,
    ) -> dict[str, Any]:
        """创建提醒记录

        Args:
            record_id: 记录ID
            status: 状态
            message: 消息
            skip_reason: 跳过原因

        Returns:
            dict: 记录字典
        """
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")

        record = ReminderRecord(
            id=record_id,
            date=today,
            scheduled_time=self.schedule.cron_expression,
            status=status,
            message=message,
            skip_reason=skip_reason,
            executed_at=now.isoformat(),
        )

        # 添加到历史
        self.history.append(record)
        self._save_history()

        return {
            "id": record.id,
            "date": record.date,
            "status": record.status.value,
            "message": record.message,
            "skip_reason": record.skip_reason,
            "executed_at": record.executed_at,
        }

    def get_history(
        self,
        days: int = 7,
        status: ReminderStatus | None = None,
    ) -> list[dict[str, Any]]:
        """获取提醒历史

        Args:
            days: 最近几天
            status: 按状态筛选

        Returns:
            list: 历史记录列表
        """
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        results = []
        for record in reversed(self.history):
            if record.date < cutoff_date:
                continue
            if status and record.status != status:
                continue

            results.append(
                {
                    "id": record.id,
                    "date": record.date,
                    "status": record.status.value,
                    "message": record.message,
                    "skip_reason": record.skip_reason,
                    "executed_at": record.executed_at,
                }
            )

        return results

    def get_today_status(self) -> dict[str, Any]:
        """获取今日提醒状态

        Returns:
            dict: 今日状态
        """
        today = datetime.now().strftime("%Y-%m-%d")

        for record in reversed(self.history):
            if record.date == today:
                return {
                    "has_record": True,
                    "status": record.status.value,
                    "message": record.message,
                    "skip_reason": record.skip_reason,
                    "executed_at": record.executed_at,
                }

        return {
            "has_record": False,
            "status": "none",
            "message": "今日尚未执行提醒",
        }

    def update_schedule(self, **kwargs: Any) -> ReminderSchedule:
        """更新调度配置

        Args:
            **kwargs: 配置项

        Returns:
            ReminderSchedule: 更新后的配置
        """
        if "enabled" in kwargs:
            self.schedule.enabled = kwargs["enabled"]
        if "cron_expression" in kwargs:
            self.schedule.cron_expression = kwargs["cron_expression"]
        if "advance_minutes" in kwargs:
            self.schedule.advance_minutes = kwargs["advance_minutes"]
        if "check_weather" in kwargs:
            self.schedule.check_weather = kwargs["check_weather"]
        if "do_not_disturb_start" in kwargs:
            self.schedule.do_not_disturb_start = kwargs["do_not_disturb_start"]
        if "do_not_disturb_end" in kwargs:
            self.schedule.do_not_disturb_end = kwargs["do_not_disturb_end"]

        logger.info(f"提醒配置已更新: {self.schedule}")
        return self.schedule

    def clear_history(self, days: int = 30) -> int:
        """清理历史记录

        Args:
            days: 保留最近几天的记录

        Returns:
            int: 清理的记录数
        """
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        original_count = len(self.history)
        self.history = [r for r in self.history if r.date >= cutoff_date]
        removed_count = original_count - len(self.history)

        self._save_history()
        logger.info(f"清理了 {removed_count} 条历史记录")

        return removed_count
