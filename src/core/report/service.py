# 报告服务模块
# 封装晨报、周报、月报生成、推送和定时调度逻辑

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from nanobot.cron.service import CronService
from nanobot.cron.types import CronSchedule

from src.core.base.logger import get_logger
from src.core.models import (
    DailyReportData,
    MonthlyReportData,
    OperationResult,
    ReportType,
    ScheduleStatus,
    WeeklyReportData,
)
from src.core.visualization.models import ChartConfig, ChartData, DataSeries
from src.notify.feishu import FeishuBot

if TYPE_CHECKING:
    from rich.console import Console

    from src.core.base.context import AppContext

logger = get_logger(__name__)


class ReportService:
    """报告服务，负责生成、推送和定时调度晨报、周报、月报"""

    JOB_NAME_DAILY = "daily_report"
    JOB_NAME_WEEKLY = "weekly_report"
    JOB_NAME_MONTHLY = "monthly_report"

    def __init__(self, context: "AppContext") -> None:
        """
        初始化报告服务

        Args:
            context: AppContext 实例
        """
        self.context = context
        self.config = context.config
        self.storage = context.storage
        self.analytics = context.analytics
        self.feishu: FeishuBot | None = None

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
    ) -> DailyReportData | WeeklyReportData | MonthlyReportData:
        """
        生成报告

        Args:
            report_type: 报告类型 (daily/weekly/monthly)
            age: 年龄参数

        Returns:
            DailyReportData | WeeklyReportData | MonthlyReportData: 报告数据
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

    def _generate_weekly_report(self, age: int = 30) -> WeeklyReportData:
        """
        生成周报

        Args:
            age: 年龄参数

        Returns:
            WeeklyReportData: 周报数据
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

            total_runs = len(runs)
            total_distance = 0.0
            total_duration = 0.0
            total_tss = 0.0
            vdot_values: list[float] = []

            for run in runs:
                distance = run.get("session_total_distance") or run.get(
                    "total_distance", 0
                )
                duration = run.get("session_total_timer_time") or run.get(
                    "total_timer_time", 0
                )
                total_distance += distance
                total_duration += duration

                tss = self.analytics.calculate_tss_for_run(
                    distance_m=distance,
                    duration_s=duration,
                    avg_heart_rate=run.get("session_avg_heart_rate")
                    or run.get("avg_heart_rate"),
                )
                total_tss += tss

                if distance >= 1500 and duration > 0:
                    vdot = self.analytics.calculate_vdot(distance, duration)
                    if vdot > 0:
                        vdot_values.append(vdot)

            avg_vdot = sum(vdot_values) / len(vdot_values) if vdot_values else 0

            training_load = self.analytics.get_training_load(days=7)

            return WeeklyReportData(
                type="weekly",
                date_range=f"{start_date.strftime('%m.%d')}-{end_date.strftime('%m.%d')}",
                greeting=f"本周训练总结 ({start_date.strftime('%m.%d')}-{end_date.strftime('%m.%d')})",
                total_runs=total_runs,
                total_distance_km=round(total_distance / 1000, 2),
                total_duration_min=round(total_duration / 60, 1),
                total_tss=round(total_tss, 1),
                avg_vdot=round(avg_vdot, 1),
                training_load=training_load,
                highlights=self._identify_weekly_highlights(runs, total_distance),
                concerns=self._identify_weekly_concerns(runs, total_tss),
                recommendations=self._generate_weekly_recommendations(
                    runs, training_load
                ),
            )
        except Exception as e:
            logger.error(f"生成周报失败：{e}", exc_info=True)
            return WeeklyReportData(
                type="weekly",
                error=f"生成失败：{str(e)}",
            )

    def _generate_monthly_report(self, age: int = 30) -> MonthlyReportData:
        """
        生成月报

        Args:
            age: 年龄参数

        Returns:
            MonthlyReportData: 月报数据
        """
        now = datetime.now()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        end_date = now
        start_date = start_of_month

        try:
            runs = self.storage.query_by_date_range(
                start_date=start_date, end_date=end_date
            )

            total_runs = len(runs)
            total_distance = 0.0
            total_duration = 0.0
            total_tss = 0.0
            vdot_values: list[float] = []
            max_distance = 0.0

            for run in runs:
                distance = run.get("session_total_distance") or run.get(
                    "total_distance", 0
                )
                duration = run.get("session_total_timer_time") or run.get(
                    "total_timer_time", 0
                )
                total_distance += distance
                total_duration += duration
                max_distance = max(max_distance, distance)

                tss = self.analytics.calculate_tss_for_run(
                    distance_m=distance,
                    duration_s=duration,
                    avg_heart_rate=run.get("session_avg_heart_rate")
                    or run.get("avg_heart_rate"),
                )
                total_tss += tss

                if distance >= 1500 and duration > 0:
                    vdot = self.analytics.calculate_vdot(distance, duration)
                    if vdot > 0:
                        vdot_values.append(vdot)

            avg_vdot = sum(vdot_values) / len(vdot_values) if vdot_values else 0

            weeks_in_month = max(1, (now - start_of_month).days / 7)
            avg_weekly_distance = (total_distance / 1000) / weeks_in_month
            avg_weekly_duration = (total_duration / 60) / weeks_in_month

            training_load = self.analytics.get_training_load(days=30)

            return MonthlyReportData(
                type="monthly",
                month=now.strftime("%Y年%m月"),
                greeting=f"本月训练总结 ({now.strftime('%Y年%m月')})",
                total_runs=total_runs,
                total_distance_km=round(total_distance / 1000, 2),
                total_duration_min=round(total_duration / 60, 1),
                total_tss=round(total_tss, 1),
                avg_vdot=round(avg_vdot, 1),
                avg_weekly_distance_km=round(avg_weekly_distance, 2),
                avg_weekly_duration_min=round(avg_weekly_duration, 1),
                training_load=training_load,
                highlights=self._identify_monthly_highlights(
                    runs, total_distance, max_distance
                ),
                concerns=self._identify_monthly_concerns(runs, total_tss),
                recommendations=self._generate_monthly_recommendations(
                    runs, training_load
                ),
            )
        except Exception as e:
            logger.error(f"生成月报失败：{e}", exc_info=True)
            return MonthlyReportData(
                type="monthly",
                error=f"生成失败：{str(e)}",
            )

    def _identify_weekly_highlights(
        self, runs: list[dict], total_distance: float
    ) -> list[str]:
        """识别本周亮点"""
        highlights: list[str] = []
        if not runs:
            return highlights

        max_distance = 0.0
        max_vdot = 0.0

        for run in runs:
            distance = run.get("session_total_distance") or run.get("total_distance", 0)
            duration = run.get("session_total_timer_time") or run.get(
                "total_timer_time", 0
            )
            max_distance = max(max_distance, distance)

            if distance >= 1500 and duration > 0:
                vdot = self.analytics.calculate_vdot(distance, duration)
                if vdot > 0:
                    max_vdot = max(max_vdot, vdot)

        if max_distance > 0:
            highlights.append(f"最长距离：{max_distance / 1000:.2f} km")

        if max_vdot > 0:
            highlights.append(f"最高 VDOT: {max_vdot:.1f}")

        if len(runs) >= 3:
            highlights.append(f"训练频率良好：{len(runs)} 次训练")

        return highlights

    def _identify_weekly_concerns(
        self, runs: list[dict], total_tss: float
    ) -> list[str]:
        """识别本周需关注点"""
        concerns = []
        if not runs:
            concerns.append("本周无训练记录")
            return concerns

        if len(runs) < 2:
            concerns.append("训练频率较低，建议增加训练次数")

        if total_tss > 400:
            concerns.append(f"本周 TSS 较高 ({total_tss:.0f}), 注意恢复")

        return concerns

    def _generate_weekly_recommendations(
        self, runs: list[dict], training_load: dict
    ) -> list[str]:
        """生成本周建议"""
        recommendations = []

        # 基于训练负荷给出建议
        ctl = training_load.get("ctl", 0)
        training_load.get("atl", 0)
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

    def _identify_monthly_highlights(
        self, runs: list[dict], total_distance: float, max_distance: float
    ) -> list[str]:
        """识别本月亮点"""
        highlights: list[str] = []
        if not runs:
            return highlights

        total_distance_km = total_distance / 1000
        if total_distance_km > 100:
            highlights.append(f"月跑量突破：{total_distance_km:.1f} km")

        if len(runs) >= 12:
            highlights.append(f"训练频率优秀：{len(runs)} 次训练")

        max_distance_km = max_distance / 1000
        if max_distance_km > 20:
            highlights.append(f"长距离突破：{max_distance_km:.2f} km")

        return highlights

    def _identify_monthly_concerns(
        self, runs: list[dict], total_tss: float
    ) -> list[str]:
        """识别本月需关注点"""
        concerns = []
        if not runs:
            concerns.append("本月无训练记录")
            return concerns

        if len(runs) < 4:
            concerns.append("训练频率较低，建议增加规律训练")

        if total_tss > 1200:
            concerns.append(f"本月 TSS 较高 ({total_tss:.0f}), 注意恢复和营养")

        return concerns

    def _generate_monthly_recommendations(
        self, runs: list[dict], training_load: dict
    ) -> list[str]:
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
        self,
        report_data: DailyReportData
        | WeeklyReportData
        | MonthlyReportData
        | dict[str, Any],
        report_type: ReportType = ReportType.DAILY,
    ) -> OperationResult:
        """
        推送报告

        Args:
            report_data: 报告数据
            report_type: 报告类型

        Returns:
            OperationResult: 推送结果
        """
        # 转换 dataclass 为字典
        if hasattr(report_data, "to_dict"):
            report_dict = report_data.to_dict()
        else:
            report_dict = report_data

        feishu = self._get_feishu_bot()

        if not feishu.auth.is_configured():
            logger.warning("未配置飞书应用机器人")
            return OperationResult(success=False, error="未配置飞书应用机器人")

        if not feishu.receive_id:
            logger.warning("未配置飞书接收者 ID")
            return OperationResult(success=False, error="未配置飞书接收者 ID")

        # 根据报告类型格式化内容
        if report_type == ReportType.DAILY:
            content = self._format_report_content(report_dict)
            title = "☀️ 每日跑步晨报"
        elif report_type == ReportType.WEEKLY:
            content = self._format_weekly_report_content(report_dict)
            title = "📊 每周跑步总结"
        elif report_type == ReportType.MONTHLY:
            content = self._format_monthly_report_content(report_dict)
            title = "📈 每月跑步总结"
        else:
            return OperationResult(
                success=False, error=f"不支持的报告类型：{report_type}"
            )

        result = feishu.send_card(title, content)

        if not result.success:
            logger.error(f"推送{report_type.value}报告失败：{result.error}")
            return OperationResult(success=False, error=result.error)

        logger.info(f"{report_type.value}报告推送成功")
        return OperationResult(success=True, message=f"{report_type.value}报告推送成功")

    def _format_report_content(self, report_data: dict[str, Any]) -> str:
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

    def _format_weekly_report_content(self, report_data: dict[str, Any]) -> str:
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

    def _format_monthly_report_content(self, report_data: dict[str, Any]) -> str:
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
        lines.append(
            f"- 周均距离：{report_data.get('avg_weekly_distance_km', 0):.2f} km"
        )
        lines.append(
            f"- 周均时长：{report_data.get('avg_weekly_duration_min', 0):.1f} 分钟"
        )
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

    def _generate_report_with_charts(
        self,
        report_data: DailyReportData | WeeklyReportData | MonthlyReportData,
        report_type: ReportType,
        console: "Console",
    ) -> None:
        """
        生成带图表的报告输出

        先输出文字报告（复用现有逻辑），再追加图表。
        仅对 WeeklyReportData/MonthlyReportData 渲染图表，DailyReportData 跳过。
        图表渲染失败时静默降级，不抛出异常。

        Args:
            report_data: 报告数据
            report_type: 报告类型
            console: Rich Console 实例
        """
        # 输出文字报告
        report_dict = report_data.to_dict()
        if report_type == ReportType.DAILY:
            content = self._format_report_content(report_dict)
        elif report_type == ReportType.WEEKLY:
            content = self._format_weekly_report_content(report_dict)
        elif report_type == ReportType.MONTHLY:
            content = self._format_monthly_report_content(report_dict)
        else:
            content = str(report_dict)

        console.print(content)

        # 日报跳过图表渲染
        if report_type == ReportType.DAILY:
            return

        # 周报/月报追加图表
        try:
            if isinstance(report_data, WeeklyReportData | MonthlyReportData):
                self._render_and_append_charts(report_data, console)
        except Exception as e:
            logger.warning(f"图表渲染失败，已静默降级：{e}")

    def _render_and_append_charts(
        self,
        report_data: WeeklyReportData | MonthlyReportData,
        console: "Console",
    ) -> None:
        """
        根据报告类型渲染对应图表

        周报：VDOT趋势小图 + 训练负荷状态图
        月报：跑量趋势小图 + 心率区间分布图

        Args:
            report_data: 周报或月报数据
            console: Rich Console 实例
        """
        from src.core.visualization.plotext_renderer import PlotextRenderer

        renderer = PlotextRenderer()
        config = ChartConfig(width=80, height=12, show_legend=True, theme="default")

        if isinstance(report_data, WeeklyReportData):
            # 周报：VDOT趋势 + 训练负荷
            vdot_chart = self._build_vdot_chart(report_data)
            if vdot_chart.series and any(s.values for s in vdot_chart.series):
                try:
                    chart_str = renderer.render_line_chart(vdot_chart, config)
                    console.print("\n[bold]VDOT 趋势[/bold]")
                    console.print(chart_str)
                except Exception as e:
                    logger.warning(f"VDOT图表渲染失败：{e}")

            load_chart = self._build_load_chart(report_data)
            if load_chart.series and any(s.values for s in load_chart.series):
                try:
                    chart_str = renderer.render_multi_line_chart(load_chart, config)
                    console.print("\n[bold]训练负荷状态[/bold]")
                    console.print(chart_str)
                except Exception as e:
                    logger.warning(f"训练负荷图表渲染失败：{e}")

        elif isinstance(report_data, MonthlyReportData):
            # 月报：跑量趋势 + 心率区间
            volume_chart = self._build_volume_chart(report_data)
            if volume_chart.series and any(s.values for s in volume_chart.series):
                try:
                    chart_str = renderer.render_bar_chart(volume_chart, config)
                    console.print("\n[bold]跑量趋势[/bold]")
                    console.print(chart_str)
                except Exception as e:
                    logger.warning(f"跑量图表渲染失败：{e}")

            hr_chart = self._build_hr_zones_chart(report_data)
            if hr_chart.series and any(s.values for s in hr_chart.series):
                try:
                    chart_str = renderer.render_stacked_bar_chart(hr_chart, config)
                    console.print("\n[bold]心率区间分布[/bold]")
                    console.print(chart_str)
                except Exception as e:
                    logger.warning(f"心率区间图表渲染失败：{e}")

    def _build_vdot_chart(
        self, report_data: WeeklyReportData | MonthlyReportData
    ) -> ChartData:
        """
        从报告数据构建VDOT趋势ChartData

        通过查询报告时间范围内的原始数据，提取每次有效跑步的VDOT值。

        Args:
            report_data: 报告数据

        Returns:
            ChartData: VDOT趋势图表数据
        """
        now = datetime.now()
        if isinstance(report_data, WeeklyReportData):
            start_date = now - timedelta(days=now.weekday())
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now
        else:
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = now

        try:
            runs = self.storage.query_by_date_range(
                start_date=start_date, end_date=end_date
            )
            labels: list[str] = []
            values: list[float] = []

            for run in runs:
                distance = run.get("session_total_distance") or run.get(
                    "total_distance", 0
                )
                duration = run.get("session_total_timer_time") or run.get(
                    "total_timer_time", 0
                )
                if distance >= 1500 and duration > 0:
                    vdot = self.analytics.calculate_vdot(distance, duration)
                    if vdot > 0:
                        start_time = run.get("session_start_time")
                        if start_time:
                            if isinstance(start_time, datetime):
                                labels.append(start_time.strftime("%m-%d"))
                            else:
                                labels.append(str(start_time)[:5])
                        else:
                            labels.append(f"R{len(labels) + 1}")
                        values.append(round(vdot, 1))

            return ChartData(
                title="VDOT 趋势",
                x_label="日期",
                y_label="VDOT",
                series=[
                    DataSeries(name="VDOT", labels=labels, values=values, color="blue")
                ],
            )
        except Exception as e:
            logger.warning(f"构建VDOT图表数据失败：{e}")
            return ChartData(title="VDOT 趋势", x_label="", y_label="", series=[])

    def _build_load_chart(
        self, report_data: WeeklyReportData | MonthlyReportData
    ) -> ChartData:
        """
        从报告数据构建训练负荷ChartData

        调用 analytics.get_training_load_trend 获取 CTL/ATL/TSB 趋势。

        Args:
            report_data: 报告数据

        Returns:
            ChartData: 训练负荷图表数据
        """
        days = 7 if isinstance(report_data, WeeklyReportData) else 30
        try:
            trend_result = self.analytics.get_training_load_trend(days=days)
            trend_data = (
                trend_result.get("trend_data", [])
                if isinstance(trend_result, dict)
                else []
            )

            if not trend_data:
                return ChartData(title="训练负荷", x_label="", y_label="", series=[])

            labels = [item.get("date", "") for item in trend_data]
            ctl_values = [item.get("ctl", 0.0) for item in trend_data]
            atl_values = [item.get("atl", 0.0) for item in trend_data]
            tsb_values = [item.get("tsb", 0.0) for item in trend_data]

            return ChartData(
                title="训练负荷状态",
                x_label="日期",
                y_label="负荷",
                series=[
                    DataSeries(
                        name="CTL", labels=labels, values=ctl_values, color="blue"
                    ),
                    DataSeries(
                        name="ATL", labels=labels, values=atl_values, color="red"
                    ),
                    DataSeries(
                        name="TSB", labels=labels, values=tsb_values, color="green"
                    ),
                ],
            )
        except Exception as e:
            logger.warning(f"构建训练负荷图表数据失败：{e}")
            return ChartData(title="训练负荷", x_label="", y_label="", series=[])

    def _build_volume_chart(self, report_data: MonthlyReportData) -> ChartData:
        """
        从报告数据构建跑量趋势ChartData

        按日聚合距离，构建柱状图数据。

        Args:
            report_data: 月报数据

        Returns:
            ChartData: 跑量趋势图表数据
        """
        now = datetime.now()
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = now

        try:
            runs = self.storage.query_by_date_range(
                start_date=start_date, end_date=end_date
            )
            from collections import defaultdict

            daily_distance: dict[str, float] = defaultdict(float)
            for run in runs:
                distance = run.get("session_total_distance") or run.get(
                    "total_distance", 0
                )
                start_time = run.get("session_start_time")
                if start_time:
                    if isinstance(start_time, datetime):
                        day_key = start_time.strftime("%m-%d")
                    else:
                        day_key = str(start_time)[:10]
                else:
                    continue
                daily_distance[day_key] += distance / 1000  # 转换为km

            sorted_days = sorted(daily_distance.keys())
            labels = sorted_days
            values = [round(daily_distance[d], 2) for d in sorted_days]

            return ChartData(
                title="跑量趋势",
                x_label="日期",
                y_label="距离 (km)",
                series=[
                    DataSeries(name="跑量", labels=labels, values=values, color="cyan")
                ],
            )
        except Exception as e:
            logger.warning(f"构建跑量图表数据失败：{e}")
            return ChartData(title="跑量趋势", x_label="", y_label="", series=[])

    def _build_hr_zones_chart(self, report_data: MonthlyReportData) -> ChartData:
        """
        从报告数据构建心率区间ChartData

        使用简单区间模型统计各区间时间占比。

        Args:
            report_data: 月报数据

        Returns:
            ChartData: 心率区间分布图表数据
        """
        now = datetime.now()
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = now

        try:
            runs = self.storage.query_by_date_range(
                start_date=start_date, end_date=end_date
            )
            zone_times: dict[str, float] = {
                "Z1": 0.0,
                "Z2": 0.0,
                "Z3": 0.0,
                "Z4": 0.0,
                "Z5": 0.0,
            }
            zone_colors = {
                "Z1": "blue",
                "Z2": "green",
                "Z3": "yellow",
                "Z4": "orange",
                "Z5": "red",
            }

            for run in runs:
                avg_hr = run.get("session_avg_heart_rate") or run.get(
                    "avg_heart_rate", 0
                )
                duration = run.get("session_total_timer_time") or run.get(
                    "total_timer_time", 0
                )
                if avg_hr <= 0 or duration <= 0:
                    continue

                # 使用简单的心率区间模型（基于最大心率估算）
                max_hr_est = 220 - 30  # 默认年龄30岁估算最大心率
                hr_percent = avg_hr / max_hr_est

                if hr_percent < 0.6:
                    zone = "Z1"
                elif hr_percent < 0.7:
                    zone = "Z2"
                elif hr_percent < 0.8:
                    zone = "Z3"
                elif hr_percent < 0.9:
                    zone = "Z4"
                else:
                    zone = "Z5"

                zone_times[zone] += duration / 60  # 转换为分钟

            if sum(zone_times.values()) == 0:
                return ChartData(
                    title="心率区间分布", x_label="", y_label="", series=[]
                )

            labels = list(zone_times.keys())
            series = [
                DataSeries(
                    name=zone,
                    labels=labels,
                    values=[zone_times[zone]],
                    color=zone_colors.get(zone),
                )
                for zone in labels
                if zone_times[zone] > 0
            ]

            return ChartData(
                title="心率区间分布",
                x_label="区间",
                y_label="时间 (分钟)",
                series=series,
            )
        except Exception as e:
            logger.warning(f"构建心率区间图表数据失败：{e}")
            return ChartData(title="心率区间分布", x_label="", y_label="", series=[])

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
    ) -> OperationResult:
        """
        配置定时推送

        Args:
            time_str: 时间字符串 (HH:MM)
            push: 是否推送
            age: 年龄参数
            report_type: 报告类型

        Returns:
            OperationResult: 配置结果
        """
        try:
            hour, minute = map(int, time_str.split(":"))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                logger.error(f"时间格式无效：{time_str}")
                return OperationResult(success=False, error="时间格式无效")

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

            logger.info(
                f"配置定时{report_type.value}推送成功，下次推送时间：{target_time}"
            )
            return OperationResult(
                success=True,
                message=f"已配置定时{report_type.value}推送，下次推送时间：{target_time.strftime('%Y-%m-%d %H:%M')}",
                data={"next_run": target_time.isoformat()},
            )

        except ValueError as e:
            logger.error(f"时间格式错误：{e}")
            return OperationResult(success=False, error=f"时间格式错误：{e}")
        except Exception as e:
            logger.error(f"配置定时推送失败：{e}")
            return OperationResult(success=False, error=f"配置失败：{e}")

    def enable_schedule(
        self, enabled: bool = True, report_type: ReportType = ReportType.DAILY
    ) -> OperationResult:
        """
        启用/禁用定时推送

        Args:
            enabled: 是否启用
            report_type: 报告类型

        Returns:
            OperationResult: 操作结果
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
                return OperationResult(
                    success=False,
                    error=f"未找到定时任务，请先使用 --schedule 配置 ({report_type.value})",
                )

            self.cron_service.enable_job(job_id, enabled=enabled)

            self.config.set(f"report_enabled_{report_type.value}", enabled)

            status = "已启用" if enabled else "已禁用"
            logger.info(f"定时{report_type.value}推送{status}")
            return OperationResult(
                success=True, message=f"定时{report_type.value}推送{status}"
            )

        except Exception as e:
            logger.error(f"操作失败：{e}")
            return OperationResult(success=False, error=f"操作失败：{e}")

    def get_schedule_status(
        self, report_type: ReportType = ReportType.DAILY
    ) -> ScheduleStatus:
        """
        获取定时推送状态

        Args:
            report_type: 报告类型

        Returns:
            ScheduleStatus: 状态信息
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
                return ScheduleStatus(
                    enabled=False,
                    configured=False,
                    message=f"未配置定时{report_type.value}推送",
                )

            import json

            try:
                config = json.loads(job.message) if job.message else {}
            except json.JSONDecodeError:
                config = {}

            logger.debug(f"定时{report_type.value}推送状态：enabled={job.enabled}")
            return ScheduleStatus(
                enabled=job.enabled,
                configured=True,
                time=config.get(
                    "time", self.config.get(f"report_schedule_{report_type.value}")
                ),
                push=config.get(
                    "push", self.config.get(f"report_push_{report_type.value}", True)
                ),
                age=config.get(
                    "age", self.config.get(f"report_age_{report_type.value}", 30)
                ),
                job_id=job.id,
            )

        except Exception as e:
            logger.error(f"获取定时{report_type.value}推送状态失败：{e}")
            return ScheduleStatus(
                enabled=False,
                configured=False,
                message=str(e),
            )

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
            age = status.age
            push = status.push

            report_data = self.generate_report(report_type=report_type, age=age)

            if push:
                result = self.push_report(report_data, report_type=report_type)
                logger.info(
                    f"定时{report_type.value}推送执行完成：success={result.success}"
                )
                return result.success

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
    ) -> dict[str, Any]:
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

            # 转换 dataclass 为字典
            report_dict: dict[str, Any]
            if hasattr(report_data, "to_dict"):
                report_dict = report_data.to_dict()
            else:
                report_dict = report_data  # type: ignore[assignment]

            result = {
                "success": True,
                "report": report_dict,
            }

            if push:
                push_result = self.push_report(report_data, report_type=report_type)
                result["push_result"] = push_result.to_dict()
                logger.info(
                    f"{report_type.value}报告生成并推送完成：success={push_result.success}"
                )

            return result

        except Exception as e:
            logger.error(f"生成{report_type.value}报告失败：{e}")
            return {"success": False, "error": str(e)}
