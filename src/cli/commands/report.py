# 报告和画像相关命令
# 包含 report 和 profile 命令


from pathlib import Path
from typing import Any, cast

import typer
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from src.cli.common import CLIError, console, print_error, print_status
from src.core.models import MonthlyReportData, ReportType, WeeklyReportData

app = typer.Typer(help="报告和画像命令")
profile_app = typer.Typer(help="用户画像管理")
app.add_typer(profile_app, name="profile")


@app.command()
def report(
    push: bool = typer.Option(False, "--push", "-p", help="推送到飞书"),
    schedule: str | None = typer.Option(
        None, "--schedule", "-s", help="配置定时推送时间 (HH:MM)"
    ),
    enable: bool | None = typer.Option(
        None, "--enable/--disable", help="启用/禁用定时推送"
    ),
    status: bool = typer.Option(False, "--status", help="查看定时推送状态"),
    age: int = typer.Option(30, "--age", "-a", help="年龄（用于计算最大心率）"),
) -> None:
    """
    生成并推送每日晨报

    示例:
        nanobotrun report              # 生成晨报
        nanobotrun report --push       # 生成并推送到飞书
        nanobotrun report --schedule 07:00  # 配置每天 07:00 推送
        nanobotrun report --enable     # 启用定时推送
        nanobotrun report --disable    # 禁用定时推送
        nanobotrun report --status     # 查看定时推送状态
    """
    from src.core.base.context import get_context

    try:
        service = get_context().report_service

        if status:
            schedule_status = service.get_schedule_status()
            if schedule_status.configured:
                state_color = "green" if schedule_status.enabled else "yellow"
                state_text = "已启用" if schedule_status.enabled else "已禁用"
                console.print(
                    f"[bold]定时推送状态:[/bold] [{state_color}]{state_text}[/{state_color}]"
                )
                console.print(
                    f"  推送时间: [cyan]{schedule_status.time or 'N/A'}[/cyan]"
                )
                console.print(
                    f"  推送到飞书: {'[green]是[/green]' if schedule_status.push else '[dim]否[/dim]'}"
                )
                console.print(f"  年龄设置: [cyan]{schedule_status.age}[/cyan] 岁")
            else:
                print_status("未配置定时推送", "warning")
                console.print(
                    "[dim]使用 'nanobotrun report --schedule HH:MM' 配置定时推送[/dim]"
                )
            return

        if enable is not None:
            result = service.enable_schedule(enabled=enable)
            if result.success:
                print_status(result.message or "", "success")
            else:
                print_error(CLIError.schedule_not_found())
                raise typer.Exit(1)
            return

        if schedule:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                progress.add_task("正在配置定时推送", total=None)
                result = service.schedule_report(time_str=schedule, push=push, age=age)

            if result.success:
                print_status(result.message or "", "success")
            else:
                print_error(
                    {
                        "message": result.error or "配置失败",
                        "suggestion": "请确保时间格式为 HH:MM，例如: 07:00",
                    }
                )
                raise typer.Exit(1)
            return

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task("正在生成晨报", total=None)
            report_result = service.run_report_now(push=push, age=age)

        if not report_result.get("success"):
            print_error(
                {
                    "message": f"生成晨报失败: {report_result.get('error', '未知错误')}",
                    "suggestion": "请检查是否有跑步数据，或使用 'nanobotrun data import <路径>' 导入数据",
                }
            )
            raise typer.Exit(1)

        report_data = report_result.get("report", {})

        _display_report(report_data)

        if push:
            push_result = report_result.get("push_result", {})
            if push_result.get("success"):
                print_status("晨报已推送到飞书", "success")
            else:
                print_error(CLIError.push_failed(push_result.get("error", "未知错误")))

    except PermissionError:
        print_error(CLIError.storage_error("权限不足，无法访问配置文件"))
        raise typer.Exit(1)
    except Exception as e:
        print_error(
            {
                "message": f"操作失败: {str(e)}",
                "suggestion": "请检查配置和数据文件是否正常",
            }
        )
        raise typer.Exit(1)


@app.command()
def weekly(
    push: bool = typer.Option(False, "--push", "-p", help="推送到飞书"),
    age: int = typer.Option(30, "--age", "-a", help="年龄（用于计算最大心率）"),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="保存报告到指定目录"
    ),
) -> None:
    """
    生成周报

    示例:
        nanobotrun report weekly              # 生成周报
        nanobotrun report weekly --push       # 生成并推送到飞书
        nanobotrun report weekly --output ./reports  # 生成周报并保存到文件
    """
    from src.core.base.context import get_context

    try:
        service = get_context().report_service

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task("正在生成周报", total=None)
            result = service.generate_report(report_type=ReportType.WEEKLY, age=age)

        if not result:
            print_error(
                {
                    "message": "生成周报失败",
                    "suggestion": "请检查是否有跑步数据，或使用 'nanobotrun data import <路径>' 导入数据",
                }
            )
            raise typer.Exit(1)

        _display_weekly_report(
            cast(
                WeeklyReportData | dict[str, Any],
                result.to_dict() if hasattr(result, "to_dict") else result,
            )
        )

        if output:
            _save_report_to_file(ReportType.WEEKLY, age, output)

        if push:
            push_result = service.push_report(result, report_type=ReportType.WEEKLY)
            if push_result.success:
                print_status("周报已推送到飞书", "success")
            else:
                print_error(CLIError.push_failed(push_result.error or "未知错误"))

    except Exception as e:
        print_error(
            {
                "message": f"操作失败: {str(e)}",
                "suggestion": "请检查配置和数据文件是否正常",
            }
        )
        raise typer.Exit(1)


@app.command()
def monthly(
    push: bool = typer.Option(False, "--push", "-p", help="推送到飞书"),
    age: int = typer.Option(30, "--age", "-a", help="年龄（用于计算最大心率）"),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="保存报告到指定目录"
    ),
) -> None:
    """
    生成月报

    示例:
        nanobotrun report monthly              # 生成月报
        nanobotrun report monthly --push       # 生成并推送到飞书
        nanobotrun report monthly --output ./reports  # 生成月报并保存到文件
    """
    from src.core.base.context import get_context

    try:
        service = get_context().report_service

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task("正在生成月报", total=None)
            result = service.generate_report(report_type=ReportType.MONTHLY, age=age)

        if not result:
            print_error(
                {
                    "message": "生成月报失败",
                    "suggestion": "请检查是否有跑步数据，或使用 'nanobotrun data import <路径>' 导入数据",
                }
            )
            raise typer.Exit(1)

        _display_monthly_report(
            cast(
                MonthlyReportData | dict[str, Any],
                result.to_dict() if hasattr(result, "to_dict") else result,
            )
        )

        if output:
            _save_report_to_file(ReportType.MONTHLY, age, output)

        if push:
            push_result = service.push_report(result, report_type=ReportType.MONTHLY)
            if push_result.success:
                print_status("月报已推送到飞书", "success")
            else:
                print_error(CLIError.push_failed(push_result.error or "未知错误"))

    except Exception as e:
        print_error(
            {
                "message": f"操作失败: {str(e)}",
                "suggestion": "请检查配置和数据文件是否正常",
            }
        )
        raise typer.Exit(1)


def _save_report_to_file(report_type: ReportType, age: int, output_dir: Path) -> None:
    """使用ReportGenerator生成Markdown报告并保存到文件"""
    from src.core.base.context import get_context
    from src.core.report_generator import ReportGenerator

    try:
        context = get_context()
        generator = ReportGenerator(context)

        report_result = generator.generate_report(report_type=report_type, age=age)

        if not report_result.success:
            print_error(
                {
                    "message": f"保存报告失败: {report_result.error}",
                    "suggestion": "请检查数据文件是否正常",
                }
            )
            return

        save_result = generator.save_report(
            report_content=report_result.content,
            report_type=report_type,
            output_dir=output_dir,
        )

        if save_result.get("success"):
            print_status(
                f"报告已保存至 {save_result.get('file_path', output_dir)}", "success"
            )
        else:
            print_error(
                {
                    "message": f"保存报告失败: {save_result.get('error', '未知错误')}",
                    "suggestion": "请检查输出目录是否有写入权限",
                }
            )

    except Exception as e:
        print_error(
            {
                "message": f"保存报告失败: {str(e)}",
                "suggestion": "请检查输出目录路径是否正确",
            }
        )


def _display_report(report_data: dict) -> None:
    """
    在终端显示晨报内容

    Args:
        report_data: 晨报数据
    """
    console.print()
    console.print(
        Panel(
            f"[bold]{report_data.get('date', '')}[/bold]\n{report_data.get('greeting', '')}",
            title="[Morning] 每日跑步晨报",
            border_style="blue",
        )
    )

    yesterday_run = report_data.get("yesterday_run")
    if yesterday_run:
        table = Table(title="昨日训练", show_header=False)
        table.add_column("指标", style="cyan")
        table.add_column("数值", style="green")
        table.add_row("距离", f"{yesterday_run.get('distance_km', 0)} km")
        table.add_row("时长", f"{yesterday_run.get('duration_min', 0)} 分钟")
        tss = yesterday_run.get("tss", 0)
        tss_color = "green" if tss < 100 else "yellow" if tss < 150 else "red"
        table.add_row("TSS", f"[{tss_color}]{tss}[/{tss_color}]")
        console.print(table)
    else:
        console.print("[dim]昨日无训练记录[/dim]")

    fitness = report_data.get("fitness_status", {})
    fitness_table = Table(title="体能状态", show_header=False)
    fitness_table.add_column("指标", style="cyan")
    fitness_table.add_column("数值", style="green")

    atl = fitness.get("atl", 0)
    ctl = fitness.get("ctl", 0)
    tsb = fitness.get("tsb", 0)

    atl_color = "green" if atl < 50 else "yellow" if atl < 100 else "red"
    ctl_color = "green" if ctl < 50 else "yellow" if ctl < 100 else "red"
    tsb_color = "green" if tsb > 0 else "yellow" if tsb > -20 else "red"

    fitness_table.add_row("ATL (疲劳)", f"[{atl_color}]{atl}[/{atl_color}]")
    fitness_table.add_row("CTL (体能)", f"[{ctl_color}]{ctl}[/{ctl_color}]")
    fitness_table.add_row("TSB (状态)", f"[{tsb_color}]{tsb}[/{tsb_color}]")

    status_text = fitness.get("status", "数据不足")
    status_color = (
        "green"
        if "良好" in status_text
        else "yellow"
        if "注意" in status_text
        else "red"
    )
    fitness_table.add_row("评估", f"[{status_color}]{status_text}[/{status_color}]")
    console.print(fitness_table)

    training_advice = report_data.get("training_advice", "暂无建议")
    advice_border = (
        "green" if "轻松" in training_advice or "休息" in training_advice else "yellow"
    )
    console.print(
        Panel(
            training_advice,
            title="今日建议",
            border_style=advice_border,
        )
    )

    weekly_plan = report_data.get("weekly_plan", [])
    if weekly_plan:
        plan_table = Table(title="本周计划")
        plan_table.add_column("日期", style="cyan")
        plan_table.add_column("计划", style="green")
        for day_plan in weekly_plan:
            day_str = day_plan.get("day", "")
            date_str = day_plan.get("date", "")
            plan_str = day_plan.get("plan", "")
            is_today = day_plan.get("is_today", False)

            if is_today:
                plan_table.add_row(
                    f"[bold]{day_str} {date_str}[/bold] (今天)",
                    f"[bold]{plan_str}[/bold]",
                )
            else:
                plan_table.add_row(f"{day_str} {date_str}", plan_str)
        console.print(plan_table)


def _display_weekly_report(report_data: WeeklyReportData | dict[str, Any]) -> None:
    """
    在终端显示周报内容

    Args:
        report_data: 周报数据
    """
    # 转换 dataclass 为字典
    if isinstance(report_data, WeeklyReportData):
        report_dict = report_data.to_dict()
    else:
        report_dict = report_data

    if "error" in report_dict:
        print_error(
            {
                "message": report_dict["error"],
                "suggestion": "请检查是否有跑步数据",
            }
        )
        return

    console.print()
    console.print(
        Panel(
            f"[bold]{report_dict.get('date_range', '')}[/bold]\n{report_dict.get('greeting', '')}",
            title="[Weekly] 周报",
            border_style="blue",
        )
    )

    summary_table = Table(title="本周训练统计", show_header=False)
    summary_table.add_column("指标", style="cyan")
    summary_table.add_column("数值", style="green")
    summary_table.add_row("总次数", str(report_dict.get("total_runs", 0)))
    summary_table.add_row("总距离", f"{report_dict.get('total_distance_km', 0)} km")
    summary_table.add_row("总时长", f"{report_dict.get('total_duration_min', 0)} 分钟")
    summary_table.add_row("总TSS", f"{report_dict.get('total_tss', 0)}")
    summary_table.add_row("平均VDOT", f"{report_dict.get('avg_vdot', 0)}")
    console.print(summary_table)

    training_load = report_dict.get("training_load", {})
    if training_load:
        load_table = Table(title="训练负荷", show_header=False)
        load_table.add_column("指标", style="cyan")
        load_table.add_column("数值", style="green")

        atl = training_load.get("atl", 0)
        ctl = training_load.get("ctl", 0)
        tsb = training_load.get("tsb", 0)

        atl_color = "green" if atl < 50 else "yellow" if atl < 100 else "red"
        ctl_color = "green" if ctl < 50 else "yellow" if ctl < 100 else "red"
        tsb_color = "green" if tsb > 0 else "yellow" if tsb > -20 else "red"

        load_table.add_row("ATL (疲劳)", f"[{atl_color}]{atl}[/{atl_color}]")
        load_table.add_row("CTL (体能)", f"[{ctl_color}]{ctl}[/{ctl_color}]")
        load_table.add_row("TSB (状态)", f"[{tsb_color}]{tsb}[/{tsb_color}]")
        console.print(load_table)

    highlights = report_dict.get("highlights", [])
    if highlights:
        console.print(
            Panel(
                "\n".join(f"- {h}" for h in highlights),
                title="本周亮点",
                border_style="green",
            )
        )

    concerns = report_dict.get("concerns", [])
    if concerns:
        console.print(
            Panel(
                "\n".join(f"- {c}" for c in concerns),
                title="需要关注",
                border_style="yellow",
            )
        )

    recommendations = report_dict.get("recommendations", [])
    if recommendations:
        console.print(
            Panel(
                "\n".join(f"- {r}" for r in recommendations),
                title="下周建议",
                border_style="blue",
            )
        )


def _display_monthly_report(report_data: MonthlyReportData | dict[str, Any]) -> None:
    """
    在终端显示月报内容

    Args:
        report_data: 月报数据
    """
    # 转换 dataclass 为字典
    if isinstance(report_data, MonthlyReportData):
        report_dict = report_data.to_dict()
    else:
        report_dict = report_data

    if "error" in report_dict:
        print_error(
            {
                "message": report_dict["error"],
                "suggestion": "请检查是否有跑步数据",
            }
        )
        return

    console.print()
    console.print(
        Panel(
            f"[bold]{report_dict.get('date_range', '')}[/bold]\n{report_dict.get('greeting', '')}",
            title="[Monthly] 月报",
            border_style="blue",
        )
    )

    summary_table = Table(title="本月训练统计", show_header=False)
    summary_table.add_column("指标", style="cyan")
    summary_table.add_column("数值", style="green")
    summary_table.add_row("总次数", str(report_dict.get("total_runs", 0)))
    summary_table.add_row("总距离", f"{report_dict.get('total_distance_km', 0)} km")
    summary_table.add_row("总时长", f"{report_dict.get('total_duration_min', 0)} 分钟")
    summary_table.add_row("总TSS", f"{report_dict.get('total_tss', 0)}")
    summary_table.add_row("平均VDOT", f"{report_dict.get('avg_vdot', 0)}")
    console.print(summary_table)

    training_load = report_dict.get("training_load", {})
    if training_load:
        load_table = Table(title="训练负荷", show_header=False)
        load_table.add_column("指标", style="cyan")
        load_table.add_column("数值", style="green")

        atl = training_load.get("atl", 0)
        ctl = training_load.get("ctl", 0)
        tsb = training_load.get("tsb", 0)

        atl_color = "green" if atl < 50 else "yellow" if atl < 100 else "red"
        ctl_color = "green" if ctl < 50 else "yellow" if ctl < 100 else "red"
        tsb_color = "green" if tsb > 0 else "yellow" if tsb > -20 else "red"

        load_table.add_row("ATL (疲劳)", f"[{atl_color}]{atl}[/{atl_color}]")
        load_table.add_row("CTL (体能)", f"[{ctl_color}]{ctl}[/{ctl_color}]")
        load_table.add_row("TSB (状态)", f"[{tsb_color}]{tsb}[/{tsb_color}]")
        console.print(load_table)

    highlights = report_dict.get("highlights", [])
    if highlights:
        console.print(
            Panel(
                "\n".join(f"- {h}" for h in highlights),
                title="本月亮点",
                border_style="green",
            )
        )

    concerns = report_dict.get("concerns", [])
    if concerns:
        console.print(
            Panel(
                "\n".join(f"- {c}" for c in concerns),
                title="需要关注",
                border_style="yellow",
            )
        )

    recommendations = report_dict.get("recommendations", [])
    if recommendations:
        console.print(
            Panel(
                "\n".join(f"- {r}" for r in recommendations),
                title="下月建议",
                border_style="blue",
            )
        )


@profile_app.command("show")
def profile_show(
    days: int = typer.Option(90, "--days", "-d", help="分析天数"),
    age: int = typer.Option(30, "--age", "-a", help="年龄（用于计算最大心率）"),
    resting_hr: int = typer.Option(60, "--resting-hr", "-r", help="静息心率"),
    rebuild: bool = typer.Option(False, "--rebuild", help="重新构建画像"),
) -> None:
    """
    显示用户画像信息

    包含：平均 VDOT、健身水平、训练模式、受伤风险评估等
    """
    from src.core.base.context import AppContextFactory

    try:
        context = AppContextFactory.create()
        profile = None

        if rebuild:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                progress.add_task("正在构建用户画像...", total=None)
                profile = context.profile_engine.build_profile(
                    user_id="default_user",
                    days=days,
                    age=age,
                    resting_hr=resting_hr,
                )
                context.profile_storage.save_profile_json(profile)
        else:
            profile = context.profile_storage.load_profile_json()

            if profile is None:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    transient=True,
                ) as progress:
                    progress.add_task("首次运行，正在构建用户画像...", total=None)
                    profile = context.profile_engine.build_profile(
                        user_id="default_user",
                        days=days,
                        age=age,
                        resting_hr=resting_hr,
                    )
                    context.profile_storage.save_profile_json(profile)

        if profile is None or profile.total_activities == 0:
            console.print(
                Panel(
                    "[yellow]暂无跑步数据[/yellow]\n\n"
                    "使用 'nanobotrun data import <路径>' 导入FIT文件",
                    title="用户画像",
                    border_style="yellow",
                )
            )
            return

        console.print()
        console.print(
            Panel(
                f"[bold]用户 ID:[/bold] {profile.user_id}\n"
                f"[bold]画像日期:[/bold] {profile.profile_date.strftime('%Y-%m-%d %H:%M')}\n"
                f"[bold]分析周期:[/bold] {profile.analysis_period_days} 天",
                title="[Profile] 用户画像",
                border_style="blue",
            )
        )

        basic_table = Table(title="基础统计", show_header=False)
        basic_table.add_column("指标", style="cyan")
        basic_table.add_column("数值", style="green")
        basic_table.add_row("总活动次数", str(profile.total_activities))
        basic_table.add_row("总跑量", f"{profile.total_distance_km:.2f} km")
        basic_table.add_row("总时长", f"{profile.total_duration_hours:.2f} 小时")
        basic_table.add_row("平均配速", f"{profile.avg_pace_min_per_km:.2f} min/km")
        console.print(basic_table)

        fitness_table = Table(title="体能指标", show_header=False)
        fitness_table.add_column("指标", style="cyan")
        fitness_table.add_column("数值", style="green")

        vdot_color = (
            "green"
            if profile.avg_vdot >= 45
            else "yellow"
            if profile.avg_vdot >= 30
            else "red"
        )
        fitness_table.add_row(
            "平均 VDOT", f"[{vdot_color}]{profile.avg_vdot:.2f}[/{vdot_color}]"
        )
        fitness_table.add_row("最大 VDOT", f"{profile.max_vdot:.2f}")
        fitness_table.add_row("体能水平", f"[bold]{profile.fitness_level.value}[/bold]")
        console.print(fitness_table)

        training_table = Table(title="训练模式", show_header=False)
        training_table.add_column("指标", style="cyan")
        training_table.add_column("数值", style="green")
        training_table.add_row("周平均跑量", f"{profile.weekly_avg_distance_km:.2f} km")
        training_table.add_row(
            "周平均时长", f"{profile.weekly_avg_duration_hours:.2f} 小时"
        )
        training_table.add_row(
            "训练模式", f"[bold]{profile.training_pattern.value}[/bold]"
        )
        training_table.add_row("训练一致性", f"{profile.consistency_score:.1f}/100")
        console.print(training_table)

        load_table = Table(title="训练负荷", show_header=False)
        load_table.add_column("指标", style="cyan")
        load_table.add_column("数值", style="green")

        atl_color = (
            "green" if profile.atl < 50 else "yellow" if profile.atl < 100 else "red"
        )
        ctl_color = (
            "green" if profile.ctl < 50 else "yellow" if profile.ctl < 100 else "red"
        )
        tsb_color = (
            "green" if profile.tsb > 0 else "yellow" if profile.tsb > -20 else "red"
        )

        load_table.add_row(
            "ATL (疲劳)", f"[{atl_color}]{profile.atl:.2f}[/{atl_color}]"
        )
        load_table.add_row(
            "CTL (体能)", f"[{ctl_color}]{profile.ctl:.2f}[/{ctl_color}]"
        )
        load_table.add_row(
            "TSB (状态)", f"[{tsb_color}]{profile.tsb:.2f}[/{tsb_color}]"
        )
        console.print(load_table)

        risk_color = (
            "green"
            if profile.injury_risk_level.value == "低"
            else "yellow"
            if profile.injury_risk_level.value == "中"
            else "red"
        )
        console.print(
            Panel(
                f"[bold]伤病风险等级:[/bold] [{risk_color}]{profile.injury_risk_level.value}[/{risk_color}]\n"
                f"[bold]风险评分:[/bold] {profile.injury_risk_score:.1f}",
                title="伤病风险评估",
                border_style=risk_color,
            )
        )

        if (
            profile.avg_heart_rate
            or profile.max_heart_rate
            or profile.resting_heart_rate
        ):
            hr_table = Table(title="心率指标", show_header=False)
            hr_table.add_column("指标", style="cyan")
            hr_table.add_column("数值", style="green")
            if profile.avg_heart_rate:
                hr_table.add_row("平均心率", f"{profile.avg_heart_rate:.1f} bpm")
            if profile.max_heart_rate:
                hr_table.add_row("最大心率", f"{profile.max_heart_rate:.1f} bpm")
            if profile.resting_heart_rate:
                hr_table.add_row("静息心率", f"{profile.resting_heart_rate:.1f} bpm")
            console.print(hr_table)

        console.print(
            Panel(
                f"[bold]数据质量评分:[/bold] {profile.data_quality_score:.1f}/100\n"
                f"[bold]偏好训练时间:[/bold] {profile.favorite_running_time}",
                title="其他信息",
                border_style="dim",
            )
        )

    except Exception as e:
        print_error(
            {
                "message": f"获取用户画像失败: {str(e)}",
                "suggestion": "请确保已导入跑步数据，或使用 --rebuild 重新构建画像",
            }
        )
        raise typer.Exit(1)
