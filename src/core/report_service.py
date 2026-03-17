# 晨报服务模块
# 封装晨报生成、推送和定时调度逻辑

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from nanobot.cron.service import CronService
from nanobot.cron.types import CronSchedule

from src.core.analytics import AnalyticsEngine
from src.core.config import ConfigManager
from src.core.logger import get_logger
from src.core.storage import StorageManager
from src.notify.feishu import FeishuBot

logger = get_logger(__name__)


class ReportService:
    """晨报服务，负责生成、推送和定时调度"""

    JOB_NAME = "daily_report"

    def __init__(
        self,
        config: Optional[ConfigManager] = None,
        storage: Optional[StorageManager] = None,
        analytics: Optional[AnalyticsEngine] = None,
        feishu: Optional[FeishuBot] = None,
    ):
        self.config = config or ConfigManager()
        self.storage = storage or StorageManager(self.config.data_dir)
        self.analytics = analytics or AnalyticsEngine(self.storage)
        self.feishu = feishu

        self.cron_store = self.config.base_dir / "cron"
        self.cron_store.mkdir(parents=True, exist_ok=True)
        self.cron_service = CronService(store_path=self.cron_store)
        logger.debug("ReportService 初始化完成")

    def _get_feishu_bot(self) -> FeishuBot:
        if self.feishu is None:
            self.feishu = FeishuBot()
        return self.feishu

    def generate_report(self, age: int = 30) -> Dict[str, Any]:
        logger.debug(f"生成晨报, 年龄: {age}")
        return self.analytics.generate_daily_report(age=age)

    def push_report(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        feishu = self._get_feishu_bot()

        if not feishu.webhook:
            logger.warning("未配置飞书 Webhook")
            return {"success": False, "error": "未配置飞书 Webhook"}

        content = self._format_report_content(report_data)

        result = feishu.send_card("☀️ 每日跑步晨报", content)

        if "error" in result:
            logger.error(f"推送晨报失败: {result['error']}")
            return {"success": False, "error": result["error"]}

        logger.info("晨报推送成功")
        return {"success": True, "message": "晨报推送成功"}

    def _format_report_content(self, report_data: Dict[str, Any]) -> str:
        lines = []

        lines.append(f"**{report_data.get('date', '')}**")
        lines.append(f"{report_data.get('greeting', '')}")
        lines.append("")

        yesterday_run = report_data.get("yesterday_run")
        if yesterday_run:
            lines.append("**昨日训练**")
            lines.append(f"- 距离: {yesterday_run.get('distance_km', 0)} km")
            lines.append(f"- 时长: {yesterday_run.get('duration_min', 0)} 分钟")
            lines.append(f"- TSS: {yesterday_run.get('tss', 0)}")
            lines.append("")
        else:
            lines.append("**昨日训练**: 无")
            lines.append("")

        fitness = report_data.get("fitness_status", {})
        lines.append("**体能状态**")
        lines.append(f"- ATL (疲劳): {fitness.get('atl', 0)}")
        lines.append(f"- CTL (体能): {fitness.get('ctl', 0)}")
        lines.append(f"- TSB (状态): {fitness.get('tsb', 0)}")
        lines.append(f"- 评估: {fitness.get('status', '数据不足')}")
        lines.append("")

        lines.append("**今日建议**")
        lines.append(report_data.get("training_advice", "暂无建议"))

        return "\n".join(lines)

    def schedule_report(
        self, time_str: str, push: bool = True, age: int = 30
    ) -> Dict[str, Any]:
        try:
            hour, minute = map(int, time_str.split(":"))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                logger.error(f"时间格式无效: {time_str}")
                return {"success": False, "error": "时间格式无效"}

            now = datetime.now()
            target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if target_time <= now:
                target_time += timedelta(days=1)

            at_ms = int(target_time.timestamp() * 1000)

            schedule = CronSchedule(kind="at", at_ms=at_ms)

            import json

            message = json.dumps({"push": push, "age": age, "time": time_str})

            existing_jobs = self.cron_service.list_jobs(include_disabled=True)
            for job in existing_jobs:
                if job.name == self.JOB_NAME:
                    self.cron_service.remove_job(job.id)

            self.cron_service.add_job(
                name=self.JOB_NAME,
                schedule=schedule,
                message=message,
                delete_after_run=False,
            )

            self.config.set("report_schedule", time_str)
            self.config.set("report_push", push)
            self.config.set("report_age", age)

            logger.info(f"配置定时推送成功，下次推送时间: {target_time}")
            return {
                "success": True,
                "message": f"已配置定时推送，下次推送时间: {target_time.strftime('%Y-%m-%d %H:%M')}",
                "next_run": target_time.isoformat(),
            }

        except ValueError as e:
            logger.error(f"时间格式错误: {e}")
            return {"success": False, "error": f"时间格式错误: {e}"}
        except Exception as e:
            logger.error(f"配置定时推送失败: {e}")
            return {"success": False, "error": f"配置失败: {e}"}

    def enable_schedule(self, enabled: bool = True) -> Dict[str, Any]:
        try:
            jobs = self.cron_service.list_jobs(include_disabled=True)
            job_id = None
            for job in jobs:
                if job.name == self.JOB_NAME:
                    job_id = job.id
                    break

            if not job_id:
                logger.warning("未找到定时任务")
                return {
                    "success": False,
                    "error": "未找到定时任务，请先使用 --schedule 配置",
                }

            self.cron_service.enable_job(job_id, enabled=enabled)

            self.config.set("report_enabled", enabled)

            status = "已启用" if enabled else "已禁用"
            logger.info(f"定时推送{status}")
            return {"success": True, "message": f"定时推送{status}"}

        except Exception as e:
            logger.error(f"操作失败: {e}")
            return {"success": False, "error": f"操作失败: {e}"}

    def get_schedule_status(self) -> Dict[str, Any]:
        try:
            jobs = self.cron_service.list_jobs(include_disabled=True)
            job = None
            for j in jobs:
                if j.name == self.JOB_NAME:
                    job = j
                    break

            if not job:
                logger.debug("未配置定时推送")
                return {
                    "enabled": False,
                    "configured": False,
                    "message": "未配置定时推送",
                }

            import json

            try:
                config = json.loads(job.message) if job.message else {}
            except json.JSONDecodeError:
                config = {}

            logger.debug(f"定时推送状态: enabled={job.enabled}")
            return {
                "enabled": job.enabled,
                "configured": True,
                "time": config.get("time", self.config.get("report_schedule")),
                "push": config.get("push", self.config.get("report_push", True)),
                "age": config.get("age", self.config.get("report_age", 30)),
                "job_id": job.id,
            }

        except Exception as e:
            logger.error(f"获取定时推送状态失败: {e}")
            return {"enabled": False, "configured": False, "error": str(e)}

    async def run_scheduled_report(self) -> bool:
        try:
            status = self.get_schedule_status()
            age = status.get("age", 30)
            push = status.get("push", True)

            report_data = self.generate_report(age=age)

            if push:
                result = self.push_report(report_data)
                logger.info(f"定时推送执行完成: success={result.get('success')}")
                return result.get("success", False)

            logger.info("定时推送执行完成（仅生成）")
            return True

        except Exception as e:
            logger.error(f"定时推送执行失败: {e}")
            return False

    def run_report_now(self, push: bool = False, age: int = 30) -> Dict[str, Any]:
        try:
            logger.debug(f"立即生成晨报, push={push}, age={age}")
            report_data = self.generate_report(age=age)

            result = {
                "success": True,
                "report": report_data,
            }

            if push:
                push_result = self.push_report(report_data)
                result["push_result"] = push_result
                logger.info(f"晨报生成并推送完成: success={push_result.get('success')}")

            return result

        except Exception as e:
            logger.error(f"生成晨报失败: {e}")
            return {"success": False, "error": str(e)}
