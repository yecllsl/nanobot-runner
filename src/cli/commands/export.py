# 导出命令模块
# 提供数据导出相关的 CLI 命令

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import typer

from src.cli.common import CLIError, console, print_error, print_status
from src.cli.handlers.export_handler import ExportHandler
from src.core.base.context import get_context
from src.core.export.models import ExportConfig, ExportResult

app = typer.Typer(help="数据导出命令")

# 支持的导出格式
SESSION_FORMAT_CHOICES = ["csv", "json", "parquet"]
SUMMARY_FORMAT_CHOICES = ["csv", "json"]
PERIOD_CHOICES = ["weekly", "monthly", "yearly"]


def _print_export_result(result: ExportResult) -> None:
    """打印导出结果

    Args:
        result: 导出结果
    """
    if result.success:
        print_status(
            f"导出成功: {result.record_count} 条记录 -> {result.file_path} "
            f"(耗时: {result.duration_ms}ms)",
            status="success",
        )
        if result.message:
            console.print(f"[dim]{result.message}[/dim]")
    else:
        print_error(
            {
                "message": f"导出失败: {result.message}",
                "suggestion": "请检查输出路径、格式参数是否正确，或查看日志获取详细信息",
            }
        )


@app.command()
def sessions(
    output: Path = typer.Option(
        ...,  # 必填参数
        "--output",
        "-o",
        help="输出文件路径",
    ),
    start: datetime | None = typer.Option(
        None,
        "--start",
        "-s",
        help="开始日期（格式: YYYY-MM-DD）",
        formats=["%Y-%m-%d"],
    ),
    end: datetime | None = typer.Option(
        None,
        "--end",
        "-e",
        help="结束日期（格式: YYYY-MM-DD）",
        formats=["%Y-%m-%d"],
    ),
    format_name: str = typer.Option(
        "csv",
        "--format",
        "-f",
        help="导出格式（csv/json/parquet）",
    ),
) -> None:
    """导出跑步活动数据

    将指定日期范围内的跑步活动数据导出为指定格式。

    示例:
        nanobotrun export sessions -o ./runs.csv
        nanobotrun export sessions -o ./runs.json --format json --start 2024-01-01 --end 2024-03-31
        nanobotrun export sessions -o ./runs.parquet --format parquet

    Args:
        output: 输出文件路径（必填）
        start: 开始日期（可选）
        end: 结束日期（可选）
        format_name: 导出格式（默认 csv）
    """
    # 验证格式
    if format_name.lower() not in SESSION_FORMAT_CHOICES:
        print_error(
            {
                "message": f"不支持的导出格式: '{format_name}'",
                "suggestion": f"支持的格式: {', '.join(SESSION_FORMAT_CHOICES)}",
            }
        )
        raise typer.Exit(1)

    # 验证日期范围
    if start and end and start > end:
        print_error(
            {
                "message": "开始日期不能晚于结束日期",
                "suggestion": "请检查 --start 和 --end 参数",
            }
        )
        raise typer.Exit(1)

    try:
        context = get_context()
        handler = ExportHandler(export_engine=context.export_engine)

        config = ExportConfig(
            output_path=output,
            start_date=start,
            end_date=end,
            include_computed_fields=True,
        )

        console.print(f"[bold]导出活动数据[/bold] -> {output} ({format_name})")
        if start or end:
            date_range = (
                f"{start.date() if start else '最早'} ~ {end.date() if end else '最新'}"
            )
            console.print(f"[dim]日期范围: {date_range}[/dim]")

        result = handler.handle_export_sessions(config, format_name.lower())
        _print_export_result(result)

        if not result.success:
            raise typer.Exit(1)

    except Exception as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)


@app.command()
def summary(
    output: Path = typer.Option(
        ...,  # 必填参数
        "--output",
        "-o",
        help="输出文件路径",
    ),
    period: str = typer.Option(
        "monthly",
        "--period",
        "-p",
        help="汇总周期（weekly/monthly/yearly）",
    ),
    format_name: str = typer.Option(
        "csv",
        "--format",
        "-f",
        help="导出格式（csv/json）",
    ),
    start: datetime | None = typer.Option(
        None,
        "--start",
        "-s",
        help="开始日期（格式: YYYY-MM-DD）",
        formats=["%Y-%m-%d"],
    ),
    end: datetime | None = typer.Option(
        None,
        "--end",
        "-e",
        help="结束日期（格式: YYYY-MM-DD）",
        formats=["%Y-%m-%d"],
    ),
) -> None:
    """导出跑步摘要数据

    按指定周期（周/月/年）汇总数据后导出。

    示例:
        nanobotrun export summary -o ./summary.csv
        nanobotrun export summary -o ./summary.json --format json --period weekly
        nanobotrun export summary -o ./yearly.csv --period yearly --start 2024-01-01 --end 2024-12-31

    Args:
        output: 输出文件路径（必填）
        period: 汇总周期（默认 monthly）
        format_name: 导出格式（默认 csv）
        start: 开始日期（可选）
        end: 结束日期（可选）
    """
    # 验证格式
    if format_name.lower() not in SUMMARY_FORMAT_CHOICES:
        print_error(
            {
                "message": f"不支持的导出格式: '{format_name}'",
                "suggestion": f"支持的格式: {', '.join(SUMMARY_FORMAT_CHOICES)}",
            }
        )
        raise typer.Exit(1)

    # 验证周期
    if period.lower() not in PERIOD_CHOICES:
        print_error(
            {
                "message": f"不支持的汇总周期: '{period}'",
                "suggestion": f"支持的周期: {', '.join(PERIOD_CHOICES)}",
            }
        )
        raise typer.Exit(1)

    # 验证日期范围
    if start and end and start > end:
        print_error(
            {
                "message": "开始日期不能晚于结束日期",
                "suggestion": "请检查 --start 和 --end 参数",
            }
        )
        raise typer.Exit(1)

    try:
        context = get_context()
        handler = ExportHandler(export_engine=context.export_engine)

        config = ExportConfig(
            output_path=output,
            start_date=start,
            end_date=end,
            include_computed_fields=True,
        )

        console.print(
            f"[bold]导出摘要数据[/bold] -> {output} ({period}, {format_name})"
        )
        if start or end:
            date_range = (
                f"{start.date() if start else '最早'} ~ {end.date() if end else '最新'}"
            )
            console.print(f"[dim]日期范围: {date_range}[/dim]")

        result = handler.handle_export_summary(
            config, period.lower(), format_name.lower()
        )
        _print_export_result(result)

        if not result.success:
            raise typer.Exit(1)

    except Exception as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)
