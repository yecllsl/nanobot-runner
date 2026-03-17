# Rich格式化输出模块
# 为CLI和Agent交互提供统一的格式化输出

from typing import Any, Dict, List, Optional, Union

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


def format_duration(seconds: int) -> str:
    """
    格式化时长为人类可读格式

    Args:
        seconds: 秒数

    Returns:
        str: 格式化后的时长字符串
    """
    if seconds < 60:
        return f"{seconds}秒"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}分{secs}秒"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours}小时{minutes}分{secs}秒"


def format_pace(seconds_per_km: float) -> str:
    """
    格式化配速为人类可读格式

    Args:
        seconds_per_km: 每公里秒数

    Returns:
        str: 格式化后的配速字符串
    """
    if seconds_per_km <= 0:
        return "N/A"

    minutes = int(seconds_per_km // 60)
    seconds = int(seconds_per_km % 60)
    return f"{minutes}'{seconds:02d}\""


def format_distance(meters: float) -> str:
    """
    格式化距离为人类可读格式

    Args:
        meters: 米

    Returns:
        str: 格式化后的距离字符串
    """
    if meters < 1000:
        return f"{meters:.0f}米"
    else:
        return f"{meters / 1000:.2f}公里"


def format_stats_panel(data: Dict[str, Any]) -> Panel:
    """
    将统计数据格式化为Rich面板

    Args:
        data: 统计数据字典

    Returns:
        Panel: Rich面板对象
    """
    lines = []

    for key, value in data.items():
        if isinstance(value, (int, float)):
            if "distance" in key.lower():
                display_value = format_distance(value)
            elif "time" in key.lower() or "duration" in key.lower():
                display_value = format_duration(value)
            elif "pace" in key.lower():
                display_value = format_pace(value)
            else:
                display_value = (
                    f"{value:.2f}" if isinstance(value, float) else str(value)
                )
        else:
            display_value = str(value)

        lines.append(f"  {key}: [bold]{display_value}[/bold]")

    content = "\n".join(lines)
    return Panel(content, title="[Stats] 统计信息", border_style="cyan")


def format_error(message: str) -> Panel:
    """
    格式化错误消息

    Args:
        message: 错误消息

    Returns:
        Panel: Rich面板对象
    """
    return Panel(f"[red]{message}[/red]", title="[Error] 错误", border_style="red")


def format_success(message: str) -> Panel:
    """
    格式化成功消息

    Args:
        message: 成功消息

    Returns:
        Panel: Rich面板对象
    """
    return Panel(
        f"[green]{message}[/green]", title="[Success] 成功", border_style="green"
    )


def format_warning(message: str) -> Panel:
    """
    格式化警告消息

    Args:
        message: 警告消息

    Returns:
        Panel: Rich面板对象
    """
    return Panel(
        f"[yellow]{message}[/yellow]", title="[Warning] 警告", border_style="yellow"
    )


def format_runs_table(runs: List[Dict[str, Any]]) -> Table:
    """
    将跑步记录格式化为Rich表格

    Args:
        runs: 跑步记录列表

    Returns:
        Table: Rich表格对象
    """
    table = Table(title="[Run] 跑步记录", show_header=True, header_style="bold magenta")

    table.add_column("日期", style="cyan", width=12)
    table.add_column("距离", style="green", width=10, justify="right")
    table.add_column("用时", style="yellow", width=10, justify="right")
    table.add_column("心率", style="red", width=8, justify="right")
    table.add_column("配速", style="blue", width=10, justify="right")

    for run in runs:
        if isinstance(run, dict):
            if "error" in run:
                table.add_row(
                    run.get("timestamp", "N/A")[:10] if run.get("timestamp") else "N/A",
                    "-",
                    "-",
                    "-",
                    "-",
                )
                continue

            distance = run.get("distance", 0)
            duration = run.get("duration", 0)
            heart_rate = run.get("heart_rate", "N/A")
            pace = run.get("pace", "N/A")

            table.add_row(
                run.get("timestamp", "N/A")[:10] if run.get("timestamp") else "N/A",
                f"{distance:.2f} km" if distance else "-",
                _format_duration(duration) if duration else "-",
                f"{heart_rate} bpm" if heart_rate != "N/A" else "-",
                _format_pace(pace) if pace != "N/A" else "-",
            )

    return table


def _format_duration(seconds: Union[int, float]) -> str:
    """内部函数：格式化时长"""
    if seconds is None:
        return "-"
    try:
        secs = int(seconds)
        return format_duration(secs)
    except (ValueError, TypeError):
        return "-"


def _format_pace(pace: Union[int, float, str]) -> str:
    """内部函数：格式化配速"""
    if pace is None or pace == "N/A":
        return "-"
    try:
        return format_pace(float(pace))
    except (ValueError, TypeError):
        return "-"


def format_vdot_trend(vdot_data: List[Dict[str, Any]]) -> Table:
    """
    将VDOT趋势数据格式化为Rich表格

    Args:
        vdot_data: VDOT数据列表

    Returns:
        Table: Rich表格对象
    """
    table = Table(title="[Trend] VDOT趋势", show_header=True, header_style="bold magenta")

    table.add_column("日期", style="cyan", width=12)
    table.add_column("VDOT", style="green", width=10, justify="right")
    table.add_column("距离", style="blue", width=10, justify="right")
    table.add_column("用时", style="yellow", width=10, justify="right")

    for item in vdot_data:
        if isinstance(item, dict):
            table.add_row(
                item.get("date", "N/A")[:10] if item.get("date") else "N/A",
                f"{item.get('vdot', 0):.1f}" if item.get("vdot") else "-",
                f"{item.get('distance', 0) / 1000:.2f} km"
                if item.get("distance")
                else "-",
                format_duration(item.get("duration", 0))
                if item.get("duration")
                else "-",
            )

    return table


def format_agent_response(response: Any) -> None:
    """
    格式化Agent回复并输出到控制台

    Args:
        response: Agent回复内容
    """
    if isinstance(response, dict):
        if "error" in response:
            console.print(format_error(response["error"]))
            return

        if "message" in response:
            console.print(
                Panel(f"[yellow]{response['message']}[/yellow]", border_style="yellow")
            )
            return

        console.print(format_stats_panel(response))
    elif isinstance(response, list):
        if not response:
            console.print("[yellow]暂无数据[/yellow]")
            return

        if response and isinstance(response[0], dict):
            if "distance" in response[0] or "duration" in response[0]:
                console.print(format_runs_table(response))
            elif "vdot" in response[0]:
                console.print(format_vdot_trend(response))
            else:
                for item in response:
                    console.print(item)
    else:
        console.print(response)
