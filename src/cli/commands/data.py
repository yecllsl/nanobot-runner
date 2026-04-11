# 数据相关命令
# 包含 import-data 和 stats 命令

from pathlib import Path

import typer

from src.cli.common import CLIError, console, print_error, print_status
from src.cli.handlers.data_handler import DataHandler

app = typer.Typer(help="数据管理命令")


@app.command()
def import_data(
    path: str = typer.Argument(..., help="FIT 文件或目录路径"),
    force: bool = typer.Option(False, "--force", "-f", help="强制导入，跳过去重"),
) -> None:
    """
    导入 FIT 文件数据

    Args:
        path: FIT 文件或目录路径
        force: 是否强制导入，跳过重复检查
    """
    path_obj = Path(path)

    if not path_obj.exists():
        print_error(CLIError.path_not_found(path))
        raise typer.Exit(1)

    try:
        handler = DataHandler()

        if path_obj.is_file():
            result = handler.import_file(path_obj, force=force)

            if result.get("status") == "added":
                print_status("[OK] 导入成功", "success")
            elif result.get("status") == "skipped":
                print_status("文件已存在，跳过导入（使用 --force 强制导入）", "warning")
            else:
                print_error(CLIError.import_failed(result.get("message", "未知错误")))
                raise typer.Exit(1)

        elif path_obj.is_dir():
            success_count, skip_count, errors = handler.import_directory(
                path_obj, force=force
            )

            console.print("\n[bold]导入完成:[/bold]")
            console.print(f"  [green]成功:[/green] {success_count} 个文件")
            console.print(f"  [yellow]跳过:[/yellow] {skip_count} 个文件")

            if errors:
                console.print(f"  [red]失败:[/red] {len(errors)} 个文件")
                for error in errors[:5]:
                    console.print(f"    [dim]{error}[/dim]")
                if len(errors) > 5:
                    console.print(f"    [dim]... 还有 {len(errors) - 5} 个错误[/dim]")

        else:
            print_error(CLIError.path_not_found(path))
            raise typer.Exit(1)

    except Exception as e:
        print_error(CLIError.import_failed(str(e)))
        raise typer.Exit(1)


@app.command()
def stats(
    year: int | None = typer.Option(None, "--year", "-y", help="指定年份"),
    start_date: str | None = typer.Option(
        None, "--start", "-s", help="开始日期 (YYYY-MM-DD)"
    ),
    end_date: str | None = typer.Option(
        None, "--end", "-e", help="结束日期 (YYYY-MM-DD)"
    ),
) -> None:
    """
    查看跑步统计信息

    数据模型说明：
    - 存储的数据包含两类字段：
      1. 过程数据（record）：timestamp, heart_rate, pace 等，每秒采样一次
      2. 会话数据（session）：session_total_distance, session_total_timer_time 等，每次跑步一条
    - 每个采样点都包含会话数据字段，因此需要按 session_start_time 聚合统计
    - 直接统计行数会将采样点数量误认为跑步次数

    Args:
        year: 指定年份
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
    """
    from rich.progress import Progress, SpinnerColumn, TextColumn

    try:
        handler = DataHandler()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task("正在加载统计数据", total=None)
            df = handler.get_stats(year=year, start_date=start_date, end_date=end_date)

        if df.is_empty():
            console.print("[yellow]暂无数据[/yellow]")
            console.print("[dim]提示: 请先使用 'nanobotrun import-data' 导入数据[/dim]")
            return

        import polars as pl

        from src.cli.formatter import format_stats_panel

        session_df = df.group_by("session_start_time").agg(
            [
                pl.col("session_total_distance").first().alias("distance"),
                pl.col("session_total_timer_time").first().alias("duration"),
                pl.col("session_avg_heart_rate").first().alias("avg_hr"),
            ]
        )

        total_runs = session_df.height
        total_distance = session_df["distance"].sum()
        total_time = session_df["duration"].sum()
        avg_distance = session_df["distance"].mean()
        avg_time = session_df["duration"].mean()
        avg_hr = session_df["avg_hr"].mean()

        stats_data = {
            "总跑步次数": total_runs,
            "总距离": total_distance,
            "总时长": total_time,
            "平均距离": avg_distance,
            "平均时长": avg_time,
            "平均心率": avg_hr,
        }

        console.print(format_stats_panel(stats_data))

    except Exception as e:
        print_error(
            {
                "message": f"获取统计失败: {str(e)}",
                "suggestion": "请检查数据文件是否损坏，或重新导入数据",
            }
        )
        raise typer.Exit(1)


@app.command()
def recent(
    limit: int = typer.Option(10, "--limit", "-n", help="显示最近 N 次训练"),
) -> None:
    """
    查看最近训练记录

    示例:
        nanobotrun data recent
        nanobotrun data recent -n 5

    Args:
        limit: 显示最近 N 次训练
    """
    from rich.table import Table

    try:
        handler = DataHandler()

        console.print(f"[bold]最近 {limit} 次训练记录[/bold]")

        runs = handler.get_recent_runs(limit=limit)

        if not runs:
            console.print("[yellow]暂无训练记录[/yellow]")
            console.print(
                "[dim]提示: 使用 'nanobotrun data import-data <路径>' 导入FIT文件[/dim]"
            )
            return

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("日期", width=12)
        table.add_column("距离(km)", justify="right")
        table.add_column("时长", justify="right")
        table.add_column("配速", justify="right")
        table.add_column("平均心率", justify="right")

        for run in runs:
            timestamp = run.get("timestamp", "N/A")
            if len(timestamp) > 10:
                timestamp = timestamp[:10]

            duration_min = run.get("duration_min", 0)
            hours = int(duration_min // 60)
            minutes = int(duration_min % 60)
            duration_str = f"{hours}:{minutes:02d}" if hours > 0 else f"{minutes}分"

            pace_sec = run.get("avg_pace_sec_km")
            if pace_sec:
                pace_min = int(pace_sec // 60)
                pace_sec_remainder = int(pace_sec % 60)
                pace_str = f"{pace_min}'{pace_sec_remainder:02d}\""
            else:
                pace_str = "-"

            table.add_row(
                timestamp,
                f"{run.get('distance_km', 0):.2f}",
                duration_str,
                pace_str,
                str(run.get("avg_heart_rate", "-") or "-"),
            )

        console.print(table)

    except Exception as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)
