# 报告服务模块
# 封装晨报、周报、月报生成、推送和定时调度逻辑

from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from nanobot.cron.service import CronService
from nanobot.cron.types import CronSchedule

from src.core.analytics import AnalyticsEngine
from src.core.config import ConfigManager
from src.core.logger import get_logger
from src.core.storage import StorageManager
from src.notify.feishu import FeishuBot

logger = get_logger(__name__)


class ReportType(str, Enum):
    """报告类型枚举"""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ReportService:
    """报告服务，负责生成、推送和定时调度晨报、周报、月报"""

    JOB_NAME_DAILY = "daily_report"
    JOB_NAME_WEEKLY = "weekly_report"
    JOB_NAME_MONTHLY = "monthly_report"

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

        self.cron_store = self.config.cron_store
        self.cron_store.parent.mkdir(parents=True, exist_ok=True)
        self.cron_service = CronService(store_path=self.cron_store)
        logger.debug("ReportService 初始化完成")

    def _get_feishu_bot(self) -> FeishuBot:
        if self.feishu is None:
            # 使用新的应用机器人配置
            self.feishu = FeishuBot(
                app_id=self.config.get("feishu_app_id"),
                app_secret=self.config.get("feishu_app_secret"),
                receive_id=self.config.get("feishu_receive_id"),
                receive_id_type=self.config.get("feishu_receive_id_type", "user_id"),
            )
        return self.feishu

    def generate_report(
        self, report_type: ReportType = ReportType.DAILY, age: int = 30
    ) -> Dict[str, Any]:
        """
        生成报告

        Args:
            report_type: 报告类型 (daily/weekly/monthly)
            age: 年龄参数

        Returns:
            dict: 报告数据
        """
        logger.debug(f"生成{report_type.value}报告，年龄：{age}")

        if report_type == ReportType.DAILY:
            return self.analytics.generate_daily_report(age=age)
        elif report_type == ReportType.WEEKLY:
            return self._generate_weekly_report(age=age)
        elif report_type == ReportType.MONTHLY:
            return self._generate_monthly_report(age=age)
        else:
            raise ValueError(f"不支持的报告类型：{report_type}")

    def _generate_weekly_report(self, age: int = 30) -> Dict[str, Any]:
        """
        生成周报

        Args:
            age: 年龄参数

        Returns:
            dict: 周报数据
        """
        now = datetime.now()
        start_of_week = now - timedelta(days=now.weekday())
        start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)

        # 获取本周训练数据
        end_date = now
        start_date = start_of_week

        try:
            runs = self.storage.query_by_date_range(
                start_date=start_date, end_date=end_date
            )

            # 统计本周数据
            total_runs = len(runs)
            total_distance = sum(run.get("total_distance", 0) for run in runs)
            total_duration = sum(run.get("total_timer_time", 0) for run in runs)
            total_tss = sum(run.get("tss", 0) for run in runs)

            # 计算平均 VDOT
            vdot_values = [run.get("vdot", 0) for run in runs if run.get("vdot")]
            avg_vdot = sum(vdot_values) / len(vdot_values) if vdot_values else 0

            # 获取训练负荷
            training_load = self.analytics.get_training_load(days=7)

            return {
                "type": "weekly",
                "date_range": f"{start_date.strftime('%m.%d')}-{end_date.strftime('%m.%d')}",
                "greeting": f"本周训练总结 ({start_date.strftime('%m.%d')}-{end_date.strftime('%m.%d')})",
                "total_runs": total_runs,
                "total_distance_km": round(total_distance / 1000, 2),
                "total_duration_min": round(total_duration / 60, 1),
                "total_tss": round(total_tss, 1),
                "avg_vdot": round(avg_vdot, 1),
                "training_load": training_load,
                "highlights": self._identify_weekly_highlights(runs),
                "concerns": self._identify_weekly_concerns(runs),
                "recommendations": self._generate_weekly_recommendations(
                    runs, training_load
                ),
            }
        except Exception as e:
            logger.error(f"生成周报失败：{e}", exc_info=True)
            return {
                "type": "weekly",
                "error": f"生成失败：{str(e)}",
            }

    def _generate_monthly_report(self, age: int = 30) -> Dict[str, Any]:
        """
        生成月报

        Args:
            age: 年龄参数

        Returns:
            dict: 月报数据
        """
        now = datetime.now()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # 获取本月训练数据
        end_date = now
        start_date = start_of_month

        try:
            runs = self.storage.query_by_date_range(
                start_date=start_date, end_date=end_date
            )

            # 统计本月数据
            total_runs = len(runs)
            total_distance = sum(run.get("total_distance", 0) for run in runs)
            total_duration = sum(run.get("total_timer_time", 0) for run in runs)
            total_tss = sum(run.get("tss", 0) for run in runs)

            # 计算平均 VDOT
            vdot_values = [run.get("vdot", 0) for run in runs if run.get("vdot")]
            avg_vdot = sum(vdot_values) / len(vdot_values) if vdot_values else 0

            # 计算周均训练量
            weeks_in_month = (now - start_of_month).days / 7 + 1
            avg_weekly_distance = (total_distance / 1000) / weeks_in_month
            avg_weekly_duration = (total_duration / 60) / weeks_in_month

            # 获取训练负荷
            training_load = self.analytics.get_training_load(days=30)

            return {
                "type": "monthly",
                "month": now.strftime("%Y年%m月"),
                "greeting": f"本月训练总结 ({now.strftime('%Y年%m月')})",
                "total_runs": total_runs,
                "total_distance_km": round(total_distance / 1000, 2),
                "total_duration_min": round(total_duration / 60, 1),
                "total_tss": round(total_tss, 1),
                "avg_vdot": round(avg_vdot, 1),
                "avg_weekly_distance_km": round(avg_weekly_distance, 2),
                "avg_weekly_duration_min": round(avg_weekly_duration, 1),
                "training_load": training_load,
                "highlights": self._identify_monthly_highlights(runs),
                "concerns": self._identify_monthly_concerns(runs),
                "recommendations": self._generate_monthly_recommendations(
                    runs, training_load
                ),
            }
        except Exception as e:
            logger.error(f"生成月报失败：{e}", exc_info=True)
            return {
                "type": "monthly",
                "error": f"生成失败：{str(e)}",
            }

    def _identify_weekly_highlights(self, runs: List[Dict]) -> List[str]:
        """识别本周亮点"""
        highlights: List[str] = []
        if not runs:
            return highlights

        # 找出最长距离
        max_distance_run = max(runs, key=lambda x: x.get("total_distance", 0))
        max_distance = max_distance_run.get("total_distance", 0) / 1000
        if max_distance > 0:
            highlights.append(f"最长距离：{max_distance:.2f} km")

        # 找出最高 VDOT
        vdot_runs = [r for r in runs if r.get("vdot")]
        if vdot_runs:
            max_vdot_run = max(vdot_runs, key=lambda x: x.get("vdot", 0))
            highlights.append(f"最高 VDOT: {max_vdot_run.get('vdot', 0):.1f}")

        # 训练频率
        if len(runs) >= 3:
            highlights.append(f"训练频率良好：{len(runs)} 次训练")

        return highlights

    def _identify_weekly_concerns(self, runs: List[Dict]) -> List[str]:
        """识别本周需关注点"""
        concerns = []
        if not runs:
            concerns.append("本周无训练记录")
            return concerns

        # 训练频率过低
        if len(runs) < 2:
            concerns.append("训练频率较低，建议增加训练次数")

        # 检查是否有过度训练
        total_tss = sum(run.get("tss", 0) for run in runs)
        if total_tss > 400:
            concerns.append(f"本周 TSS 较高 ({total_tss:.0f}), 注意恢复")

        return concerns

    def _generate_weekly_recommendations(
        self, runs: List[Dict], training_load: Dict
    ) -> List[str]:
        """生成本周建议"""
        recommendations = []

        # 基于训练负荷给出建议
        ctl = training_load.get("ctl", 0)
        atl = training_load.get("atl", 0)
        tsb = training_load.get("tsb", 0)

        if tsb < -20:
            recommendations.append("疲劳累积较多，建议安排恢复周")
        elif tsb > 30:
            recommendations.append("状态良好，可适当增加训练强度")
        else:
            recommendations.append("保持当前训练节奏")

        if ctl < 50:
            recommendations.append("有氧基础待加强，建议增加 LSD 训练")
        elif ctl > 100:
            recommendations.append("有氧基础良好，可增加间歇训练")

        return recommendations

    def _identify_monthly_highlights(self, runs: List[Dict]) -> List[str]:
        """识别本月亮点"""
        highlights: List[str] = []
        if not runs:
            return highlights

        # 总跑量
        total_distance = sum(run.get("total_distance", 0) for run in runs) / 1000
        if total_distance > 100:
            highlights.append(f"月跑量突破：{total_distance:.1f} km")

        # 训练频率
        if len(runs) >= 12:
            highlights.append(f"训练频率优秀：{len(runs)} 次训练")

        # 找出最长距离
        max_distance_run = max(runs, key=lambda x: x.get("total_distance", 0))
        max_distance = max_distance_run.get("total_distance", 0) / 1000
        if max_distance > 20:
            highlights.append(f"长距离突破：{max_distance:.2f} km")

        return highlights

    def _identify_monthly_concerns(self, runs: List[Dict]) -> List[str]:
        """识别本月需关注点"""
        concerns = []
        if not runs:
            concerns.append("本月无训练记录")
            return concerns

        # 训练频率过低
        if len(runs) < 4:
            concerns.append("训练频率较低，建议增加规律训练")

        # 总 TSS 过高
        total_tss = sum(run.get("tss", 0) for run in runs)
        if total_tss > 1200:
            concerns.append(f"本月 TSS 较高 ({total_tss:.0f}), 注意恢复和营养")

        return concerns

    def _generate_monthly_recommendations(
        self, runs: List[Dict], training_load: Dict
    ) -> List[str]:
        """生成月度建议"""
        recommendations = []

        ctl = training_load.get("ctl", 0)
        tsb = training_load.get("tsb", 0)

        if tsb < -30:
            recommendations.append("月度疲劳累积明显，建议下月初安排恢复周")
        elif tsb > 20:
            recommendations.append("月度状态良好，下月可适当提升训练量")
        else:
            recommendations.append("保持当前训练节奏，循序渐进")

        if ctl < 60:
            recommendations.append("有氧基础建设阶段，建议保持规律有氧训练")
        elif 60 <= ctl <= 100:
            recommendations.append("有氧基础良好，可加入乳酸阈值训练")
        else:
            recommendations.append("有氧基础优秀，可增加高强度间歇训练")

        return recommendations

    def push_report(
        self, report_data: Dict[str, Any], report_type: ReportType = ReportType.DAILY
    ) -> Dict[str, Any]:
        """
        推送报告

        Args:
            report_data: 报告数据
            report_type: 报告类型

        Returns:
            dict: 推送结果
        """
        feishu = self._get_feishu_bot()

        if not feishu.auth.is_configured():
            logger.warning("未配置飞书应用机器人")
            return {"success": False, "error": "未配置飞书应用机器人"}

        if not feishu.receive_id:
            logger.warning("未配置飞书接收者 ID")
            return {"success": False, "error": "未配置飞书接收者 ID"}

        # 根据报告类型格式化内容
        if report_type == ReportType.DAILY:
            content = self._format_report_content(report_data)
            title = "☀️ 每日跑步晨报"
        elif report_type == ReportType.WEEKLY:
            content = self._format_weekly_report_content(report_data)
            title = "📊 每周跑步总结"
        elif report_type == ReportType.MONTHLY:
            content = self._format_monthly_report_content(report_data)
            title = "📈 每月跑步总结"
        else:
            return {
                "success": False,
                "error": f"不支持的报告类型：{report_type}",
            }

        result = feishu.send_card(title, content)

        if "error" in result:
            logger.error(f"推送{report_type.value}报告失败：{result['error']}")
            return {"success": False, "error": result["error"]}

        logger.info(f"{report_type.value}报告推送成功")
        return {"success": True, "message": f"{report_type.value}报告推送成功"}

    def _format_report_content(self, report_data: Dict[str, Any]) -> str:
        """格式化报告内容 (晨报)"""
        lines = []

        lines.append(f"**{report_data.get('date', '')}**")
        lines.append(f"{report_data.get('greeting', '')}")
        lines.append("")

        yesterday_run = report_data.get("yesterday_run")
        if yesterday_run:
            lines.append("**昨日训练**")
            lines.append(f"- 距离：{yesterday_run.get('distance_km', 0)} km")
            lines.append(f"- 时长：{yesterday_run.get('duration_min', 0)} 分钟")
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
        lines.append(f"- 评估：{fitness.get('status', '数据不足')}")
        lines.append("")

        lines.append("**今日建议**")
        lines.append(report_data.get("training_advice", "暂无建议"))

        return "\n".join(lines)

    def _format_weekly_report_content(self, report_data: Dict[str, Any]) -> str:
        """格式化周报内容"""
        lines = []

        lines.append(f"**{report_data.get('greeting', '')}**")
        lines.append("")

        lines.append("**训练统计**")
        lines.append(f"- 训练次数：{report_data.get('total_runs', 0)} 次")
        lines.append(f"- 总距离：{report_data.get('total_distance_km', 0):.2f} km")
        lines.append(f"- 总时长：{report_data.get('total_duration_min', 0):.1f} 分钟")
        lines.append(f"- 总 TSS: {report_data.get('total_tss', 0):.1f}")
        lines.append(f"- 平均 VDOT: {report_data.get('avg_vdot', 0):.1f}")
        lines.append("")

        # 训练亮点
        highlights = report_data.get("highlights", [])
        if highlights:
            lines.append("**✨ 亮点**")
            for h in highlights:
                lines.append(f"- {h}")
            lines.append("")

        # 需关注点
        concerns = report_data.get("concerns", [])
        if concerns:
            lines.append("**⚠️ 需关注**")
            for c in concerns:
                lines.append(f"- {c}")
            lines.append("")

        # 建议
        recommendations = report_data.get("recommendations", [])
        if recommendations:
            lines.append("**💡 建议**")
            for r in recommendations:
                lines.append(f"- {r}")

        return "\n".join(lines)

    def _format_monthly_report_content(self, report_data: Dict[str, Any]) -> str:
        """格式化月报内容"""
        lines = []

        lines.append(f"**{report_data.get('greeting', '')}**")
        lines.append("")

        lines.append("**训练统计**")
        lines.append(f"- 训练次数：{report_data.get('total_runs', 0)} 次")
        lines.append(f"- 总距离：{report_data.get('total_distance_km', 0):.2f} km")
        lines.append(f"- 总时长：{report_data.get('total_duration_min', 0):.1f} 分钟")
        lines.append(f"- 总 TSS: {report_data.get('total_tss', 0):.1f}")
        lines.append(f"- 平均 VDOT: {report_data.get('avg_vdot', 0):.1f}")
        lines.append(f"- 周均距离：{report_data.get('avg_weekly_distance_km', 0):.2f} km")
        lines.append(f"- 周均时长：{report_data.get('avg_weekly_duration_min', 0):.1f} 分钟")
        lines.append("")

        # 训练亮点
        highlights = report_data.get("highlights", [])
        if highlights:
            lines.append("**✨ 亮点**")
            for h in highlights:
                lines.append(f"- {h}")
            lines.append("")

        # 需关注点
        concerns = report_data.get("concerns", [])
        if concerns:
            lines.append("**⚠️ 需关注**")
            for c in concerns:
                lines.append(f"- {c}")
            lines.append("")

        # 建议
        recommendations = report_data.get("recommendations", [])
        if recommendations:
            lines.append("**💡 建议**")
            for r in recommendations:
                lines.append(f"- {r}")

        return "\n".join(lines)

    def _get_job_name(self, report_type: ReportType) -> str:
        """获取任务名称"""
        if report_type == ReportType.DAILY:
            return self.JOB_NAME_DAILY
        elif report_type == ReportType.WEEKLY:
            return self.JOB_NAME_WEEKLY
        elif report_type == ReportType.MONTHLY:
            return self.JOB_NAME_MONTHLY
        else:
            return self.JOB_NAME_DAILY

    def schedule_report(
        self,
        time_str: str,
        push: bool = True,
        age: int = 30,
        report_type: ReportType = ReportType.DAILY,
    ) -> Dict[str, Any]:
        """
        配置定时推送

        Args:
            time_str: 时间字符串 (HH:MM)
            push: 是否推送
            age: 年龄参数
            report_type: 报告类型

        Returns:
            dict: 配置结果
        """
        try:
            hour, minute = map(int, time_str.split(":"))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                logger.error(f"时间格式无效：{time_str}")
                return {"success": False, "error": "时间格式无效"}

            now = datetime.now()
            target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if target_time <= now:
                target_time += timedelta(days=1)

            at_ms = int(target_time.timestamp() * 1000)

            schedule = CronSchedule(kind="at", at_ms=at_ms)

            import json

            message = json.dumps(
                {"push": push, "age": age, "time": time_str, "type": report_type.value}
            )

            # 根据报告类型确定任务名
            job_name = self._get_job_name(report_type)

            existing_jobs = self.cron_service.list_jobs(include_disabled=True)
            for job in existing_jobs:
                if job.name == job_name:
                    self.cron_service.remove_job(job.id)

            self.cron_service.add_job(
                name=job_name,
                schedule=schedule,
                message=message,
                delete_after_run=False,
            )

            # 保存配置
            self.config.set(f"report_schedule_{report_type.value}", time_str)
            self.config.set(f"report_push_{report_type.value}", push)
            self.config.set(f"report_age_{report_type.value}", age)

            logger.info(f"配置定时{report_type.value}推送成功，下次推送时间：{target_time}")
            return {
                "success": True,
                "message": f"已配置定时{report_type.value}推送，下次推送时间：{target_time.strftime('%Y-%m-%d %H:%M')}",
                "next_run": target_time.isoformat(),
            }

        except ValueError as e:
            logger.error(f"时间格式错误：{e}")
            return {"success": False, "error": f"时间格式错误：{e}"}
        except Exception as e:
            logger.error(f"配置定时推送失败：{e}")
            return {"success": False, "error": f"配置失败：{e}"}

    def enable_schedule(
        self, enabled: bool = True, report_type: ReportType = ReportType.DAILY
    ) -> Dict[str, Any]:
        """
        启用/禁用定时推送

        Args:
            enabled: 是否启用
            report_type: 报告类型

        Returns:
            dict: 操作结果
        """
        try:
            jobs = self.cron_service.list_jobs(include_disabled=True)
            job_id = None
            job_name = self._get_job_name(report_type)
            for job in jobs:
                if job.name == job_name:
                    job_id = job.id
                    break

            if not job_id:
                logger.warning(f"未找到定时任务 ({report_type.value})")
                return {
                    "success": False,
                    "error": f"未找到定时任务，请先使用 --schedule 配置 ({report_type.value})",
                }

            self.cron_service.enable_job(job_id, enabled=enabled)

            self.config.set(f"report_enabled_{report_type.value}", enabled)

            status = "已启用" if enabled else "已禁用"
            logger.info(f"定时{report_type.value}推送{status}")
            return {"success": True, "message": f"定时{report_type.value}推送{status}"}

        except Exception as e:
            logger.error(f"操作失败：{e}")
            return {"success": False, "error": f"操作失败：{e}"}

    def get_schedule_status(
        self, report_type: ReportType = ReportType.DAILY
    ) -> Dict[str, Any]:
        """
        获取定时推送状态

        Args:
            report_type: 报告类型

        Returns:
            dict: 状态信息
        """
        try:
            jobs = self.cron_service.list_jobs(include_disabled=True)
            job = None
            job_name = self._get_job_name(report_type)
            for j in jobs:
                if j.name == job_name:
                    job = j
                    break

            if not job:
                logger.debug(f"未配置定时{report_type.value}推送")
                return {
                    "enabled": False,
                    "configured": False,
                    "message": f"未配置定时{report_type.value}推送",
                }

            import json

            try:
                config = json.loads(job.message) if job.message else {}
            except json.JSONDecodeError:
                config = {}

            logger.debug(f"定时{report_type.value}推送状态：enabled={job.enabled}")
            return {
                "enabled": job.enabled,
                "configured": True,
                "time": config.get(
                    "time", self.config.get(f"report_schedule_{report_type.value}")
                ),
                "push": config.get(
                    "push", self.config.get(f"report_push_{report_type.value}", True)
                ),
                "age": config.get(
                    "age", self.config.get(f"report_age_{report_type.value}", 30)
                ),
                "job_id": job.id,
            }

        except Exception as e:
            logger.error(f"获取定时{report_type.value}推送状态失败：{e}")
            return {
                "enabled": False,
                "configured": False,
                "error": str(e),
            }

    async def run_scheduled_report(
        self, report_type: ReportType = ReportType.DAILY
    ) -> bool:
        """
        运行定时推送

        Args:
            report_type: 报告类型

        Returns:
            bool: 是否成功
        """
        try:
            status = self.get_schedule_status(report_type=report_type)
            age = status.get("age", 30)
            push = status.get("push", True)

            report_data = self.generate_report(report_type=report_type, age=age)

            if push:
                result = self.push_report(report_data, report_type=report_type)
                logger.info(
                    f"定时{report_type.value}推送执行完成：success={result.get('success')}"
                )
                return result.get("success", False)

            logger.info(f"定时{report_type.value}推送执行完成（仅生成）")
            return True

        except Exception as e:
            logger.error(f"定时{report_type.value}推送执行失败：{e}")
            return False

    def run_report_now(
        self,
        push: bool = False,
        age: int = 30,
        report_type: ReportType = ReportType.DAILY,
    ) -> Dict[str, Any]:
        """
        立即生成报告

        Args:
            push: 是否推送
            age: 年龄参数
            report_type: 报告类型

        Returns:
            dict: 结果
        """
        try:
            logger.debug(f"立即生成{report_type.value}报告，push={push}, age={age}")
            report_data = self.generate_report(report_type=report_type, age=age)

            result = {
                "success": True,
                "report": report_data,
            }

            if push:
                push_result = self.push_report(report_data, report_type=report_type)
                result["push_result"] = push_result
                logger.info(
                    f"{report_type.value}报告生成并推送完成：success={push_result.get('success')}"
                )

            return result

        except Exception as e:
            logger.error(f"生成{report_type.value}报告失败：{e}")
            return {"success": False, "error": str(e)}
