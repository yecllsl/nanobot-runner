# 分析相关命令
# 包含 vdot、load 和 hr-drift 命令

from pathlib import Path
from typing import Optional

import typer
from rich.panel import Panel
from rich.table import Table

from src.cli.common import CLIError, console, print_error
from src.cli.handlers.analysis_handler import AnalysisHandler

app = typer.Typer(help="数据分析命令")


@app.command()
def vdot(
    limit: int = typer.Option(10, "--limit", "-n", help="显示最近 N 条记录"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="输出文件路径（JSON）"),
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
