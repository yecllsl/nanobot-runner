# 分析相关命令
# 包含 vdot、load 和 hr-drift 命令

from pathlib import Path

import typer
from rich.panel import Panel
from rich.table import Table

from src.cli.common import CLIError, console, print_error
from src.cli.handlers.analysis_handler import AnalysisHandler

app = typer.Typer(help="数据分析命令")


@app.command()
def vdot(
    limit: int = typer.Option(10, "--limit", "-n", help="显示最近 N 条记录"),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="输出文件路径（JSON）"
    ),
) -> None:
    """
    查看 VDOT 趋势

    示例:
        nanobotrun vdot
        nanobotrun vdot -n 20
        nanobotrun vdot -o vdot_trend.json

    Args:
        limit: 显示最近 N 条记录
        output: 输出文件路径（JSON）
    """
    import json

    try:
        handler = AnalysisHandler()

        console.print(f"[bold]VDOT趋势分析[/bold] (最近 {limit} 次训练)")

        trend_data = handler.get_vdot_trend(limit=limit)

        if not trend_data:
            console.print("[yellow]暂无VDOT数据[/yellow]")
            console.print("[dim]提示: 需要导入跑步数据后才能计算VDOT[/dim]")
            return

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("日期", width=12)
        table.add_column("距离", width=10)
        table.add_column("时长", width=10)
        table.add_column("VDOT", width=8)
        table.add_column("趋势", width=8)

        prev_vdot = None
        for record in trend_data:
            date_str = record.get("date", "N/A")
            distance = record.get("distance_km", 0)
            duration = record.get("duration", "N/A")
            vdot_value = record.get("vdot", 0)

            if prev_vdot is not None:
                diff = vdot_value - prev_vdot
                if diff > 0:
                    trend = f"[green]↑{diff:.1f}[/green]"
                elif diff < 0:
                    trend = f"[red]↓{abs(diff):.1f}[/red]"
                else:
                    trend = "[dim]→0.0[/dim]"
            else:
                trend = "[dim]--[/dim]"

            table.add_row(
                date_str,
                f"{distance:.2f}km",
                duration,
                f"{vdot_value:.1f}",
                trend,
            )
            prev_vdot = vdot_value

        console.print(table)

        if output:
            with open(output, "w", encoding="utf-8") as f:
                json.dump(trend_data, f, ensure_ascii=False, indent=2)
            console.print(f"\n[green]✓[/green] 数据已保存到: {output}")

    except Exception as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)


@app.command()
def hrv(
    days: int = typer.Option(30, "--days", "-d", help="分析天数（7/30/90）"),
) -> None:
    """
    查看HRV（心率变异）分析

    示例:
        nanobotrun analysis hrv
        nanobotrun analysis hrv --days 7
    """
    try:
        handler = AnalysisHandler()
        console.print(f"[bold]HRV分析[/bold] (最近 {days} 天)")

        result = handler.get_hrv_analysis(days=days)

        data_quality = result.get("data_quality", "empty")
        if data_quality == "empty":
            console.print("[yellow]暂无HRV数据[/yellow]")
            console.print("[dim]提示: 需要导入包含心率数据的跑步记录[/dim]")
            return

        trend = result.get("resting_hr_trend", [])
        hrv_metrics = result.get("estimated_hrv_metrics", {})

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("日期", width=12)
        table.add_column("静息心率", width=10)
        table.add_column("偏差", width=10)

        for point in trend[-10:]:
            deviation = point.get("deviation_pct", 0.0)
            deviation_str = f"{deviation:+.1f}%"
            deviation_color = (
                "green"
                if abs(deviation) < 5
                else "yellow"
                if abs(deviation) < 10
                else "red"
            )
            table.add_row(
                point.get("date", "N/A"),
                f"{point.get('resting_hr', 0):.0f} bpm",
                f"[{deviation_color}]{deviation_str}[/{deviation_color}]",
            )

        console.print(table)

        if hrv_metrics:
            rmssd = hrv_metrics.get("estimated_rmssd")
            sdnn = hrv_metrics.get("estimated_sdnn")
            source = hrv_metrics.get("data_source", "未知")
            console.print(f"\n[bold]HRV指标[/bold] (来源: {source})")
            if rmssd:
                console.print(f"  RMSSD: {rmssd:.2f} ms")
            if sdnn:
                console.print(f"  SDNN: {sdnn:.2f} ms")

    except Exception as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)


@app.command(name="hr-recovery")
def hr_recovery() -> None:
    """
    查看心率恢复分析

    示例:
        nanobotrun analysis hr-recovery
    """
    try:
        handler = AnalysisHandler()
        console.print("[bold]心率恢复分析[/bold]")

        result = handler.get_hr_recovery()

        data_quality = result.get("data_quality", "empty")
        if data_quality == "empty":
            console.print("[yellow]暂无心率恢复数据[/yellow]")
            return

        hr_end = result.get("hr_end", 0.0)
        hr_recovery_1min = result.get("hr_recovery_1min")

        panel = Panel(
            f"[bold]训练结束心率:[/bold] {hr_end:.0f} bpm\n"
            + (
                f"[bold]1分钟恢复:[/bold] {hr_recovery_1min:.0f} bpm"
                if hr_recovery_1min
                else "[dim]1分钟恢复数据不可用[/dim]"
            ),
            title="[HR Recovery] 心率恢复",
            border_style="blue",
        )
        console.print(panel)

    except Exception as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)


@app.command()
def fatigue(
    rpe: int | None = typer.Option(None, "--rpe", help="主观疲劳度 (1-10)"),
) -> None:
    """
    查看疲劳度评估

    示例:
        nanobotrun analysis fatigue
        nanobotrun analysis fatigue --rpe 7
    """
    try:
        handler = AnalysisHandler()
        console.print("[bold]疲劳度评估[/bold]")

        result = handler.get_fatigue_score(rpe=rpe)

        data_quality = result.get("data_quality", "empty")
        if data_quality == "empty":
            console.print("[yellow]暂无训练数据[/yellow]")
            console.print("[dim]提示: 需要导入跑步数据后才能评估疲劳度[/dim]")
            return

        fatigue_score = result.get("fatigue_score", 0.0)
        recovery_status = result.get("recovery_status", "未知")
        consecutive_days = result.get("consecutive_hard_days", 0)
        recommendation = result.get("recommendation", "")
        breakdown = result.get("breakdown", {})

        status_color = {"green": "green", "yellow": "yellow", "red": "red"}.get(
            recovery_status, "white"
        )
        score_color = (
            "green" if fatigue_score < 40 else "yellow" if fatigue_score < 70 else "red"
        )

        panel = Panel(
            f"[bold]疲劳度评分:[/bold] [{score_color}]{fatigue_score:.1f}/100[/{score_color}]\n"
            f"[bold]恢复状态:[/bold] [{status_color}]{recovery_status}[/{status_color}]\n"
            f"[bold]连续高强度天数:[/bold] {consecutive_days} 天\n"
            f"[bold]建议:[/bold] {recommendation}\n\n"
            f"[bold]疲劳度分解:[/bold]\n"
            f"  ATL负荷: {breakdown.get('atl_component', 0):.1f}\n"
            f"  心率偏差: {breakdown.get('hr_deviation_component', 0):.1f}\n"
            f"  连续训练: {breakdown.get('consecutive_component', 0):.1f}\n"
            f"  主观疲劳: {breakdown.get('subjective_component', 0):.1f}",
            title="[Fatigue] 疲劳度评估",
            border_style="blue",
        )
        console.print(panel)

    except Exception as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)


@app.command()
def recovery() -> None:
    """
    查看恢复状态

    示例:
        nanobotrun analysis recovery
    """
    try:
        handler = AnalysisHandler()
        console.print("[bold]恢复状态分析[/bold]")

        result = handler.get_recovery_status()

        data_quality = result.get("data_quality", "empty")
        if data_quality == "empty":
            console.print("[yellow]暂无恢复状态数据[/yellow]")
            return

        recovery_status = result.get("recovery_status", "未知")
        rest_day_effect = result.get("rest_day_effect", {})

        status_color = {"green": "green", "yellow": "yellow", "red": "red"}.get(
            recovery_status, "white"
        )

        panel = Panel(
            f"[bold]恢复状态:[/bold] [{status_color}]{recovery_status}[/{status_color}]\n"
            f"[bold]休息日效果:[/bold] {rest_day_effect.get('effect_level', '未知')}\n"
            f"[bold]静息心率变化:[/bold] {rest_day_effect.get('resting_hr_change_pct', 0):+.1f}%\n"
            f"[bold]说明:[/bold] {rest_day_effect.get('message', '')}",
            title="[Recovery] 恢复状态",
            border_style="blue",
        )
        console.print(panel)

    except Exception as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)


@app.command()
def compare(
    period1: int = typer.Option(7, "--period1", "-p1", help="近期周期天数"),
    period2: int = typer.Option(7, "--period2", "-p2", help="对比周期天数"),
) -> None:
    """
    对比两个训练周期的身体信号变化

    示例:
        nanobotrun analysis compare
        nanobotrun analysis compare --period1 7 --period2 14
    """
    try:
        handler = AnalysisHandler()
        console.print(
            f"[bold]训练周期对比[/bold] (近期 {period1} 天 vs 之前 {period2} 天)"
        )

        result = handler.compare_training_periods(
            period1_days=period1, period2_days=period2
        )

        period1_data = result.get("period1", {})
        period2_data = result.get("period2", {})
        tsb_change = result.get("tsb_change", 0.0)
        summary = result.get("comparison_summary", "")

        change_color = (
            "green" if tsb_change > 0 else "red" if tsb_change < 0 else "white"
        )

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("指标", width=15)
        table.add_column(f"近期 ({period1}天)", width=15)
        table.add_column(f"之前 ({period2}天)", width=15)
        table.add_column("变化", width=12)

        table.add_row(
            "平均TSB",
            f"{period1_data.get('avg_tsb', 0):.1f}",
            f"{period2_data.get('avg_tsb', 0):.1f}",
            f"[{change_color}]{tsb_change:+.1f}[/{change_color}]",
        )
        table.add_row(
            "数据点数",
            str(period1_data.get("data_points", 0)),
            str(period2_data.get("data_points", 0)),
            "--",
        )

        console.print(table)
        console.print(f"\n[bold]总结:[/bold] {summary}")

    except Exception as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)


@app.command(name="load")
def training_load(
    days: int = typer.Option(42, "--days", "-d", help="分析天数"),
) -> None:
    """
    查看训练负荷（ATL/CTL/TSB）

    示例:
        nanobotrun load
        nanobotrun load -d 30

    Args:
        days: 分析天数
    """
    try:
        handler = AnalysisHandler()

        console.print(f"[bold]训练负荷分析[/bold] (最近 {days} 天)")

        load_data = handler.get_training_load(days=days)

        if load_data.get("message"):
            console.print(f"[yellow]{load_data['message']}[/yellow]")
            return

        atl = load_data.get("atl", 0)
        ctl = load_data.get("ctl", 0)
        tsb = load_data.get("tsb", 0)
        status = load_data.get("fitness_status", "未知")
        advice = load_data.get("training_advice", "")

        status_color = "green" if tsb > 0 else "yellow" if tsb > -10 else "red"

        panel = Panel(
            f"[bold]ATL (急性训练负荷):[/bold] {atl:.1f}\n"
            f"[bold]CTL (慢性训练负荷):[/bold] {ctl:.1f}\n"
            f"[bold]TSB (训练压力平衡):[/bold] [{status_color}]{tsb:.1f}[/{status_color}]\n\n"
            f"[bold]体能状态:[/bold] {status}\n"
            f"[bold]训练建议:[/bold] {advice}",
            title="[Training Load] 训练负荷",
            border_style="blue",
        )

        console.print(panel)

    except Exception as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)


@app.command(name="hr-drift")
def hr_drift(
    limit: int = typer.Option(10, "--limit", "-n", help="分析最近 N 次训练"),
) -> None:
    """
    查看心率漂移分析

    示例:
        nanobotrun hr-drift
        nanobotrun hr-drift -n 5

    Args:
        limit: 分析最近 N 次训练
    """
    try:
        handler = AnalysisHandler()

        console.print(f"[bold]心率漂移分析[/bold] (最近 {limit} 次训练)")

        result = handler.get_hr_drift_analysis()

        if result.get("error"):
            console.print(f"[yellow]{result['error']}[/yellow]")
            return

        drift_value = result.get("drift_rate")
        correlation = result.get("correlation")

        if drift_value is None:
            console.print("[yellow]暂无心率漂移数据[/yellow]")
            console.print("[dim]提示: 需要包含心率数据的跑步记录[/dim]")
            return

        drift_color = (
            "green" if drift_value < 5 else "yellow" if drift_value < 10 else "red"
        )
        corr_color = "green" if correlation and correlation < -0.7 else "yellow"

        corr_value = f"{correlation:.3f}" if correlation else "N/A"

        assessment = result.get("assessment", "")

        panel = Panel(
            f"[bold]心率漂移率:[/bold] [{drift_color}]{drift_value:.2f}%[/{drift_color}]\n"
            f"[bold]心率-配速相关性:[/bold] [{corr_color}]{corr_value}[/{corr_color}]\n\n"
            f"[bold]评估:[/bold] {assessment}",
            title="[Heart Rate Drift] 心率漂移",
            border_style="blue",
        )

        console.print(panel)

    except Exception as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)
