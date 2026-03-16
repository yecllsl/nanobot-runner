# 晨报服务模块
# 封装晨报生成、推送和定时调度逻辑

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from nanobot.cron.service import CronService
from nanobot.cron.types import CronSchedule

from src.core.analytics import AnalyticsEngine
from src.core.config import ConfigManager
from src.core.storage import StorageManager
from src.notify.feishu import FeishuBot


class ReportService:
    """晨报服务，负责生成、推送和定时调度"""

    JOB_NAME = "daily_report"  # 定时任务名称

    def __init__(
        self,
        config: Optional[ConfigManager] = None,
        storage: Optional[StorageManager] = None,
        analytics: Optional[AnalyticsEngine] = None,
        feishu: Optional[FeishuBot] = None,
    ):
        """
        初始化晨报服务

        Args:
            config: 配置管理器
            storage: 存储管理器
            analytics: 分析引擎
            feishu: 飞书机器人
        """
        self.config = config or ConfigManager()
        self.storage = storage or StorageManager(self.config.data_dir)
        self.analytics = analytics or AnalyticsEngine(self.storage)
        self.feishu = feishu

        # 初始化 CronService
        self.cron_store = self.config.base_dir / "cron"
        self.cron_store.mkdir(parents=True, exist_ok=True)
        self.cron_service = CronService(store_path=self.cron_store)

    def _get_feishu_bot(self) -> FeishuBot:
        """获取飞书机器人实例"""
        if self.feishu is None:
            self.feishu = FeishuBot()
        return self.feishu

    def generate_report(self, age: int = 30) -> Dict[str, Any]:
        """
        生成晨报内容

        Args:
            age: 年龄，用于计算最大心率

        Returns:
            Dict[str, Any]: 晨报数据
        """
        return self.analytics.generate_daily_report(age=age)

    def push_report(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        推送晨报到飞书

        Args:
            report_data: 晨报数据

        Returns:
            Dict[str, Any]: 推送结果
        """
        feishu = self._get_feishu_bot()

        # 检查是否配置了 Webhook
        if not feishu.webhook:
            return {"success": False, "error": "未配置飞书 Webhook"}

        # 格式化晨报内容
        content = self._format_report_content(report_data)

        # 发送卡片消息
        result = feishu.send_card("☀️ 每日跑步晨报", content)

        if "error" in result:
            return {"success": False, "error": result["error"]}

        return {"success": True, "message": "晨报推送成功"}

    def _format_report_content(self, report_data: Dict[str, Any]) -> str:
        """
        格式化晨报内容为飞书卡片格式

        Args:
            report_data: 晨报数据

        Returns:
            str: 格式化后的内容
        """
        lines = []

        # 日期和问候语
        lines.append(f"**{report_data.get('date', '')}**")
        lines.append(f"{report_data.get('greeting', '')}")
        lines.append("")

        # 昨日训练
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

        # 体能状态
        fitness = report_data.get("fitness_status", {})
        lines.append("**体能状态**")
        lines.append(f"- ATL (疲劳): {fitness.get('atl', 0)}")
        lines.append(f"- CTL (体能): {fitness.get('ctl', 0)}")
        lines.append(f"- TSB (状态): {fitness.get('tsb', 0)}")
        lines.append(f"- 评估: {fitness.get('status', '数据不足')}")
        lines.append("")

        # 训练建议
        lines.append("**今日建议**")
        lines.append(report_data.get("training_advice", "暂无建议"))

        return "\n".join(lines)

    def schedule_report(
        self, time_str: str, push: bool = True, age: int = 30
    ) -> Dict[str, Any]:
        """
        配置定时推送

        Args:
            time_str: 推送时间，格式 HH:MM（如 07:00）
            push: 是否推送到飞书
            age: 年龄

        Returns:
            Dict[str, Any]: 配置结果
        """
        try:
            # 解析时间
            hour, minute = map(int, time_str.split(":"))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                return {"success": False, "error": "时间格式无效"}

            # 计算下次推送时间（今天的指定时间，如果已过则明天）
            now = datetime.now()
            target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if target_time <= now:
                target_time += timedelta(days=1)

            # 转换为毫秒时间戳
            at_ms = int(target_time.timestamp() * 1000)

            # 创建定时任务
            schedule = CronSchedule(kind="at", at_ms=at_ms)

            # 构建任务消息（存储推送配置）
            import json

            message = json.dumps({"push": push, "age": age, "time": time_str})

            # 检查是否已存在同名任务
            existing_jobs = self.cron_service.list_jobs(include_disabled=True)
            for job in existing_jobs:
                if job.name == self.JOB_NAME:
                    # 删除旧任务
                    self.cron_service.remove_job(job.id)

            # 添加新任务
            self.cron_service.add_job(
                name=self.JOB_NAME,
                schedule=schedule,
                message=message,
                delete_after_run=False,
            )

            # 保存配置到 config
            self.config.set("report_schedule", time_str)
            self.config.set("report_push", push)
            self.config.set("report_age", age)

            return {
                "success": True,
                "message": f"已配置定时推送，下次推送时间: {target_time.strftime('%Y-%m-%d %H:%M')}",
                "next_run": target_time.isoformat(),
            }

        except ValueError as e:
            return {"success": False, "error": f"时间格式错误: {e}"}
        except Exception as e:
            return {"success": False, "error": f"配置失败: {e}"}

    def enable_schedule(self, enabled: bool = True) -> Dict[str, Any]:
        """
        启用或禁用定时推送

        Args:
            enabled: True 启用，False 禁用

        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 查找任务
            jobs = self.cron_service.list_jobs(include_disabled=True)
            job_id = None
            for job in jobs:
                if job.name == self.JOB_NAME:
                    job_id = job.id
                    break

            if not job_id:
                return {
                    "success": False,
                    "error": "未找到定时任务，请先使用 --schedule 配置",
                }

            # 启用/禁用任务
            self.cron_service.enable_job(job_id, enabled=enabled)

            # 更新配置
            self.config.set("report_enabled", enabled)

            status = "已启用" if enabled else "已禁用"
            return {"success": True, "message": f"定时推送{status}"}

        except Exception as e:
            return {"success": False, "error": f"操作失败: {e}"}

    def get_schedule_status(self) -> Dict[str, Any]:
        """
        获取定时推送状态

        Returns:
            Dict[str, Any]: 状态信息
        """
        try:
            jobs = self.cron_service.list_jobs(include_disabled=True)
            job = None
            for j in jobs:
                if j.name == self.JOB_NAME:
                    job = j
                    break

            if not job:
                return {
                    "enabled": False,
                    "configured": False,
                    "message": "未配置定时推送",
                }

            # 解析任务配置
            import json

            try:
                config = json.loads(job.message) if job.message else {}
            except json.JSONDecodeError:
                config = {}

            return {
                "enabled": job.enabled,
                "configured": True,
                "time": config.get("time", self.config.get("report_schedule")),
                "push": config.get("push", self.config.get("report_push", True)),
                "age": config.get("age", self.config.get("report_age", 30)),
                "job_id": job.id,
            }

        except Exception as e:
            return {"enabled": False, "configured": False, "error": str(e)}

    async def run_scheduled_report(self) -> bool:
        """
        执行定时推送任务（由 CronService 调用）

        Returns:
            bool: 是否成功
        """
        try:
            # 获取配置
            status = self.get_schedule_status()
            age = status.get("age", 30)
            push = status.get("push", True)

            # 生成晨报
            report_data = self.generate_report(age=age)

            # 推送
            if push:
                result = self.push_report(report_data)
                return result.get("success", False)

            return True

        except Exception:
            return False

    def run_report_now(self, push: bool = False, age: int = 30) -> Dict[str, Any]:
        """
        立即生成并推送晨报

        Args:
            push: 是否推送到飞书
            age: 年龄

        Returns:
            Dict[str, Any]: 执行结果
        """
        try:
            # 生成晨报
            report_data = self.generate_report(age=age)

            result = {
                "success": True,
                "report": report_data,
            }

            # 推送到飞书
            if push:
                push_result = self.push_report(report_data)
                result["push_result"] = push_result

            return result

        except Exception as e:
            return {"success": False, "error": str(e)}
