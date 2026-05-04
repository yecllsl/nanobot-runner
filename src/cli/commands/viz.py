# 可视化命令模块
# 提供图表渲染相关的 CLI 命令

from __future__ import annotations

from datetime import datetime

import typer

from src.cli.common import CLIError, console, print_error
from src.cli.handlers.viz_handler import VizHandler
from src.core.base.context import get_context

app = typer.Typer(help="数据可视化命令")

# VDOT 命令支持的 days 参数枚举
VDOT_DAYS_CHOICES = [7, 30, 90, 365]
# 训练负荷命令支持的 days 参数枚举
LOAD_DAYS_CHOICES = [30, 90, 180]


def _validate_days(value: int, choices: list[int]) -> int:
    """验证 days 参数是否在支持的选项中

    Args:
        value: 输入的 days 值
        choices: 支持的选项列表

    Returns:
        验证通过的值

    Raises:
        typer.BadParameter: 当值不在支持列表中时
    """
    if value not in choices:
        raise typer.BadParameter(f"仅支持: {', '.join(map(str, choices))}")
    return value


@app.command()
def vdot(
    days: int = typer.Option(
        30,
        "--days",
        "-d",
        help="统计天数",
    ),
) -> None:
    """渲染 VDOT 趋势图表

    显示最近 N 天的 VDOT 变化趋势折线图。

    示例:
        nanobotrun viz vdot
        nanobotrun viz vdot --days 90

    Args:
        days: 统计天数（7/30/90/365，默认 30）
    """
    days = _validate_days(days, VDOT_DAYS_CHOICES)

    try:
        context = get_context()
        handler = VizHandler(
            chart_renderer=context.chart_renderer,
            analytics=context.analytics,
        )

        console.print(f"[bold]VDOT 趋势图表[/bold] (最近 {days} 天)")
        result = handler.handle_vdot(days)
        console.print(result)

    except Exception as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)


@app.command(name="load")
def training_load(
    days: int = typer.Option(
        90,
        "--days",
        "-d",
        help="统计天数",
    ),
) -> None:
    """渲染训练负荷趋势图表

    显示最近 N 天的 CTL/ATL/TSB 多线折线图。

    示例:
        nanobotrun viz load
        nanobotrun viz load --days 180

    Args:
        days: 统计天数（30/90/180，默认 90）
    """
    days = _validate_days(days, LOAD_DAYS_CHOICES)

    try:
        context = get_context()
        handler = VizHandler(
            chart_renderer=context.chart_renderer,
            analytics=context.analytics,
        )

        console.print(f"[bold]训练负荷趋势图表[/bold] (最近 {days} 天)")
        result = handler.handle_load(days)
        console.print(result)

    except Exception as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)


@app.command(name="hr-zones")
def hr_zones(
    start: datetime = typer.Option(
        ...,  # 必填参数
        "--start",
        "-s",
        help="开始日期（格式: YYYY-MM-DD）",
        formats=["%Y-%m-%d"],
    ),
    end: datetime = typer.Option(
        ...,  # 必填参数
        "--end",
        "-e",
        help="结束日期（格式: YYYY-MM-DD）",
        formats=["%Y-%m-%d"],
    ),
    age: int = typer.Option(
        30,
        "--age",
        "-a",
        help="年龄，用于计算最大心率",
    ),
) -> None:
    """渲染心率区间分布图表

    显示指定日期范围内的心率区间分布堆叠柱状图。

    示例:
        nanobotrun viz hr-zones --start 2024-01-01 --end 2024-01-31 --age 30

    Args:
        start: 开始日期
        end: 结束日期
        age: 年龄（默认 30）
    """
    # 验证年龄范围
    if age <= 0 or age > 120:
        print_error(
            {
                "message": f"年龄参数无效: {age}",
                "suggestion": "年龄必须在 1-120 范围内",
            }
        )
        raise typer.Exit(1)

    # 验证日期范围
    if start > end:
        print_error(
            {
                "message": "开始日期不能晚于结束日期",
                "suggestion": "请检查 --start 和 --end 参数",
            }
        )
        raise typer.Exit(1)

    try:
        context = get_context()
        handler = VizHandler(
            chart_renderer=context.chart_renderer,
            analytics=context.analytics,
        )

        console.print(
            f"[bold]心率区间分布图表[/bold] "
            f"({start.date()} 至 {end.date()}, 年龄: {age})"
        )
        result = handler.handle_hr_zones(start, end, age)
        console.print(result)

    except Exception as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)
