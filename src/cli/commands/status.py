# 状态查看命令
# 包含 today 和 weekly 命令

import typer
from rich.panel import Panel

from src.cli.common import CLIError, console, print_error
from src.core.base.context import get_context
from src.core.base.exceptions import NanobotRunnerError

app = typer.Typer(help="身体状态查看命令")


@app.command()
def today() -> None:
    """
    查看今日身体状态

    示例:
        nanobotrun status today
    """
    try:
        context = get_context()
        result = context.body_signal_engine.get_daily_summary().to_dict()

        recovery_status = result.get("recovery_status", "未知")
        fatigue_score = result.get("fatigue_score", 0.0)
        data_quality = result.get("data_quality", "empty")
        daily_summary = result.get("daily_summary", "")
        training_advice = result.get("training_advice", "")
        alerts = result.get("alerts", [])

        status_color = {"green": "green", "yellow": "yellow", "red": "red"}.get(
            recovery_status, "white"
        )

        panel_content = (
            f"[bold]恢复状态:[/bold] [{status_color}]{recovery_status}[/{status_color}]\n"
            f"[bold]疲劳度评分:[/bold] {fatigue_score:.1f}/100\n"
            f"[bold]数据质量:[/bold] {data_quality}\n"
            f"[bold]训练建议:[/bold] {training_advice}"
        )

        if alerts:
            panel_content += "\n\n[bold]预警:[/bold]"
            for alert in alerts:
                severity_color = {"critical": "red", "warning": "yellow"}.get(
                    alert.get("severity", ""), "white"
                )
                panel_content += f"\n  [{severity_color}]• {alert.get('message', '')}[/{severity_color}]"

        panel = Panel(
            panel_content,
            title=f"[Body Status] {daily_summary}",
            border_style="blue",
        )
        console.print(panel)

    except NanobotRunnerError as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)


@app.command()
def weekly() -> None:
    """
    查看本周身体状态摘要

    示例:
        nanobotrun status weekly
    """
    try:
        context = get_context()
        result = context.body_signal_engine.get_weekly_summary().to_dict()

        recovery_status = result.get("recovery_status", "未知")
        fatigue_score = result.get("fatigue_score", 0.0)
        data_quality = result.get("data_quality", "empty")
        daily_summary = result.get("daily_summary", "")
        training_advice = result.get("training_advice", "")
        alerts = result.get("alerts", [])

        status_color = {"green": "green", "yellow": "yellow", "red": "red"}.get(
            recovery_status, "white"
        )

        panel_content = (
            f"[bold]恢复状态:[/bold] [{status_color}]{recovery_status}[/{status_color}]\n"
            f"[bold]疲劳度评分:[/bold] {fatigue_score:.1f}/100\n"
            f"[bold]数据质量:[/bold] {data_quality}\n"
            f"[bold]训练建议:[/bold] {training_advice}"
        )

        if alerts:
            panel_content += "\n\n[bold]预警:[/bold]"
            for alert in alerts:
                severity_color = {"critical": "red", "warning": "yellow"}.get(
                    alert.get("severity", ""), "white"
                )
                panel_content += f"\n  [{severity_color}]• {alert.get('message', '')}[/{severity_color}]"

        panel = Panel(
            panel_content,
            title=f"[Body Status] {daily_summary}",
            border_style="blue",
        )
        console.print(panel)

    except NanobotRunnerError as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)
