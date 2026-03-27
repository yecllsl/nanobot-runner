# CLI 入口模块
# 基于 Typer 和 Rich 的本地跑步数据助理

from pathlib import Path
from typing import Optional

import polars as pl
import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from src.core.config import ConfigManager
from src.core.importer import ImportService
from src.core.indexer import IndexManager
from src.core.parser import FitParser
from src.core.profile import ProfileEngine, ProfileStorageManager
from src.core.storage import StorageManager

app = typer.Typer(
    name="nanobotrun",
    help="Nanobot Runner - 本地跑步数据助理",
    add_completion=False,
)

profile_app = typer.Typer(help="用户画像管理")
app.add_typer(profile_app, name="profile")

console = Console()


class CLIError:
    """CLI错误消息和恢复建议"""

    @staticmethod
    def path_not_found(path: str) -> dict:
        return {
            "message": f"路径不存在: {path}",
            "suggestion": "请检查路径是否正确，或使用绝对路径",
        }

    @staticmethod
    def import_failed(error: str) -> dict:
        return {
            "message": f"导入失败: {error}",
            "suggestion": "请确保文件是有效的FIT格式，或使用 --force 参数强制导入",
        }

    @staticmethod
    def config_missing(key: str) -> dict:
        return {
            "message": f"缺少配置: {key}",
            "suggestion": f"请运行 'nanobotrun config --set {key}' 进行配置",
        }

    @staticmethod
    def storage_error(error: str) -> dict:
        return {
            "message": f"存储错误: {error}",
            "suggestion": "请检查数据目录权限，或运行 'nanobotrun import' 导入数据",
        }

    @staticmethod
    def schedule_not_found() -> dict:
        return {
            "message": "未找到定时任务",
            "suggestion": "请先使用 'nanobotrun report --schedule HH:MM' 配置定时推送",
        }

    @staticmethod
    def push_failed(error: str) -> dict:
        return {
            "message": f"推送失败: {error}",
            "suggestion": "请检查飞书 Webhook 配置，或运行 'nanobotrun config --show' 查看当前配置",
        }


def print_error(error_info: dict) -> None:
    """打印带恢复建议的错误消息"""
    console.print(f"[red bold]错误:[/red bold] {error_info['message']}")
    console.print(f"[yellow]建议:[/yellow] {error_info['suggestion']}")


def print_status(message: str, status: str = "info") -> None:
    """打印带状态颜色的消息"""
    colors = {
        "success": "green",
        "error": "red",
        "warning": "yellow",
        "info": "cyan",
    }
    color = colors.get(status, "white")
    console.print(f"[{color}]{message}[/{color}]")


@app.command()
def import_data(
    path: str = typer.Argument(..., help="FIT文件或目录路径"),
    force: bool = typer.Option(False, "--force", "-f", help="强制导入，跳过去重"),
):
    """
    导入FIT文件数据
    """
    path_obj = Path(path)

    if not path_obj.exists():
        print_error(CLIError.path_not_found(path))
        raise typer.Exit(1)

    try:
        config = ConfigManager()
        storage = StorageManager(config.data_dir)
        indexer = IndexManager(config.index_file)
        parser = FitParser()
        importer = ImportService(parser, storage, indexer)

        if path_obj.is_file():
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                progress.add_task(f"正在导入文件: {path_obj.name}", total=None)
                result = importer.import_file(path_obj, force=force)

            if result.get("status") == "added":
                print_status("[OK] 导入成功", "success")
            elif result.get("status") == "skipped":
                print_status("文件已存在，跳过导入（使用 --force 强制导入）", "warning")
            else:
                print_error(CLIError.import_failed(result.get("message", "未知错误")))
                raise typer.Exit(1)

        elif path_obj.is_dir():
            fit_files = list(path_obj.glob("*.fit"))
            if not fit_files:
                print_status(f"目录中没有找到FIT文件: {path}", "warning")
                return

            with Progress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeElapsedColumn(),
            ) as progress:
                task = progress.add_task("导入进度", total=len(fit_files))

                stats = {"added": 0, "skipped": 0, "failed": 0}

                for fit_file in fit_files:
                    progress.update(task, description=f"处理: {fit_file.name}")
                    result = importer.import_file(fit_file, force=force)

                    if result.get("status") == "added":
                        stats["added"] += 1
                    elif result.get("status") == "skipped":
                        stats["skipped"] += 1
                    else:
                        stats["failed"] += 1

                    progress.advance(task)

            console.print()
            print_status(
                f"[OK] 导入完成: 新增 {stats['added']} 个，跳过 {stats['skipped']} 个", "success"
            )
            if stats["failed"] > 0:
                print_status(f"  失败 {stats['failed']} 个文件", "warning")

    except PermissionError:
        print_error(CLIError.storage_error("权限不足，无法写入数据目录"))
        raise typer.Exit(1)
    except Exception as e:
        print_error(CLIError.import_failed(str(e)))
        raise typer.Exit(1)


@app.command()
def stats(
    year: Optional[int] = typer.Option(None, "--year", "-y", help="指定年份"),
    start_date: Optional[str] = typer.Option(
        None, "--start", "-s", help="开始日期 (YYYY-MM-DD)"
    ),
    end_date: Optional[str] = typer.Option(
        None, "--end", "-e", help="结束日期 (YYYY-MM-DD)"
    ),
):
    """
    查看跑步统计信息
    
    数据模型说明：
    - 存储的数据包含两类字段：
      1. 过程数据（record）：timestamp, heart_rate, pace 等，每秒采样一次
      2. 会话数据（session）：session_total_distance, session_total_timer_time 等，每次跑步一条
    - 每个采样点都包含会话数据字段，因此需要按 session_start_time 聚合统计
    - 直接统计行数会将采样点数量误认为跑步次数
    """
    try:
        config = ConfigManager()
        storage = StorageManager(config.data_dir)

        if year:
            years = [year]
        else:
            years = None

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task("正在加载统计数据", total=None)
            lf = storage.read_parquet(years=years)
            df = lf.collect()

        if df.is_empty():
            print_status("暂无跑步数据", "warning")
            console.print("[dim]提示: 使用 'nanobotrun import <路径>' 导入FIT文件[/dim]")
            return

        from datetime import datetime

        if start_date or end_date:
            try:
                start_dt = (
                    datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
                )
                end_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None
            except ValueError:
                print_error(
                    {
                        "message": "日期格式无效",
                        "suggestion": "请使用 YYYY-MM-DD 格式，例如: 2024-01-01",
                    }
                )
                raise typer.Exit(1)

            if start_dt:
                df = df.filter(df["timestamp"] >= str(start_dt))
            if end_dt:
                df = df.filter(df["timestamp"] <= str(end_dt))

        # 按会话聚合统计（避免重复计算采样点数据）
        session_df = df.group_by("session_start_time").agg([
            pl.col("session_total_distance").first().alias("distance"),
            pl.col("session_total_timer_time").first().alias("duration"),
            pl.col("session_avg_heart_rate").first().alias("avg_hr"),
        ])

        total_runs = session_df.height
        total_distance = session_df["distance"].sum()
        total_time = session_df["duration"].sum()
        avg_distance = session_df["distance"].mean()
        avg_time = session_df["duration"].mean()
        avg_hr = session_df["avg_hr"].mean()

        from src.cli_formatter import format_stats_panel

        stats_data = {
            "总跑步次数": total_runs,
            "总距离": total_distance,
            "总时长": total_time,
            "平均距离": avg_distance,
            "平均时长": avg_time,
            "平均心率": avg_hr,
        }

        console.print(format_stats_panel(stats_data))

    except FileNotFoundError:
        print_error(CLIError.storage_error("数据文件不存在"))
        raise typer.Exit(1)
    except Exception as e:
        print_error(
            {
                "message": f"获取统计失败: {str(e)}",
                "suggestion": "请检查数据文件是否损坏，或重新导入数据",
            }
        )
        raise typer.Exit(1)


@app.command()
def chat():
    """
    启动自然语言交互模式
    """
    import asyncio

    asyncio.run(_run_chat())


async def _run_chat():
    from nanobot.agent import AgentLoop
    from nanobot.agent.tools import ToolRegistry
    from nanobot.bus import MessageBus

    from src.agents.tools import RunnerTools, create_tools
    from src.cli_formatter import format_agent_response

    console.print("[bold green][Bot] Nanobot Runner Agent[/bold green]")
    console.print("[dim]基于 nanobot 的本地跑步数据助理[/dim]")
    console.print("=" * 60)
    console.print()
    console.print("[bold cyan]可用命令：[/bold cyan]")
    console.print("  • 查询统计数据（如：我跑了多少次）")
    console.print("  • 查询跑步记录（如：上周跑了多少）")
    console.print("  • VDOT分析（如：我的跑力值趋势）")
    console.print("  • 心率分析（如：心率漂移情况）")
    console.print("  • 输入 [bold]exit[/bold] 或 [bold]q[/bold] 退出")
    console.print()

    try:
        from nanobot.cli.commands import _make_provider
        from nanobot.config.loader import load_config

        config = load_config()
        agent_defaults = config.agents.defaults

        provider = _make_provider(config)

        storage = StorageManager()
        runner_tools = RunnerTools(storage)

        registry = ToolRegistry()

        for tool in create_tools(runner_tools):
            registry.register(tool)

        workspace = Path.home() / ".nanobot-runner"
        workspace.mkdir(parents=True, exist_ok=True)

        bus = MessageBus()

        agent = AgentLoop(
            bus=bus,
            provider=provider,
            workspace=workspace,
            model=agent_defaults.model,
            max_iterations=agent_defaults.max_tool_iterations,
            memory_window=agent_defaults.memory_window,
        )

        agent.tools = registry

        console.print(f"[bold green][OK] Agent 已初始化[/bold green]")
        console.print(f"[dim]模型: {agent_defaults.model}[/dim]")
        console.print()

        while True:
            try:
                user_input = Prompt.ask("\n[bold cyan]您[/bold cyan]")

                if user_input.lower() in ["exit", "quit", "q"]:
                    console.print("[yellow]再见！祝您跑步愉快！[/yellow]")
                    break

                if not user_input.strip():
                    continue

                with console.status("[bold green]思考中...", spinner="dots"):
                    response = await agent.process_direct(user_input)

                console.print()
                format_agent_response(response)

            except KeyboardInterrupt:
                console.print("\n[yellow]检测到中断，已退出[/yellow]")
                break
            except Exception as e:
                console.print(f"[red]错误：{str(e)}[/red]")

    except Exception as e:
        console.print(f"[red]Agent初始化失败：{str(e)}[/red]")
        console.print("[yellow]请确保已正确配置本地模型[/yellow]")


@app.command()
def version():
    """
    显示版本信息
    """
    from . import __version__

    console.print(f"[bold]Nanobot Runner[/bold] v{__version__}")


@app.command()
def vdot(
    limit: int = typer.Option(10, "--limit", "-n", help="显示最近N条记录"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="输出文件路径（JSON）"),
):
    """
    查看VDOT趋势

    示例:
        nanobotrun vdot
        nanobotrun vdot -n 20
        nanobotrun vdot -o vdot_trend.json
    """
    import json

    from src.agents.tools import RunnerTools

    try:
        storage = StorageManager()
        tools = RunnerTools(storage)

        console.print(f"[bold]VDOT趋势分析[/bold] (最近 {limit} 次训练)")

        trend_data = tools.get_vdot_trend(limit=limit)

        if not trend_data:
            console.print("[yellow]暂无VDOT数据[/yellow]")
            console.print("[dim]提示: 需要导入跑步数据后才能计算VDOT[/dim]")
            return

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("日期", width=12)
        table.add_column("距离(km)", justify="right")
        table.add_column("VDOT", justify="right", style="yellow")

        for item in trend_data:
            distance_km = item.get("distance", 0) / 1000
            table.add_row(
                item.get("timestamp", "N/A")[:10],
                f"{distance_km:.2f}",
                f"{item.get('vdot', 0):.1f}",
            )

        console.print(table)

        if trend_data:
            vdot_values = [
                item.get("vdot", 0) for item in trend_data if item.get("vdot")
            ]
            if vdot_values:
                avg_vdot = sum(vdot_values) / len(vdot_values)
                max_vdot = max(vdot_values)
                min_vdot = min(vdot_values)
                console.print(
                    f"\n[dim]统计: 平均VDOT {avg_vdot:.1f} | 最高 {max_vdot:.1f} | 最低 {min_vdot:.1f}[/dim]"
                )

        if output:
            with open(output, "w", encoding="utf-8") as f:
                json.dump(trend_data, f, ensure_ascii=False, indent=2)
            console.print(f"\n[green]✓[/green] 数据已保存到: [cyan]{output}[/cyan]")

    except Exception as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)


@app.command(name="load")
def training_load(
    days: int = typer.Option(42, "--days", "-d", help="分析天数"),
):
    """
    查看训练负荷（ATL/CTL/TSB）

    示例:
        nanobotrun load
        nanobotrun load -d 30
    """
    from src.core.analytics import AnalyticsEngine

    try:
        storage = StorageManager()
        engine = AnalyticsEngine(storage)

        console.print(f"[bold]训练负荷分析[/bold] (最近 {days} 天)")

        load_data = engine.get_training_load(days=days)

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

        console.print(
            f"\n[dim]分析天数: {load_data.get('days_analyzed', days)} | 跑步次数: {load_data.get('runs_count', 0)}[/dim]"
        )

    except Exception as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)


@app.command()
def recent(
    limit: int = typer.Option(10, "--limit", "-n", help="显示最近N次训练"),
):
    """
    查看最近训练记录

    示例:
        nanobotrun recent
        nanobotrun recent -n 5
    """
    from src.agents.tools import RunnerTools

    try:
        storage = StorageManager()
        tools = RunnerTools(storage)

        console.print(f"[bold]最近 {limit} 次训练记录[/bold]")

        runs = tools.get_recent_runs(limit=limit)

        if not runs:
            console.print("[yellow]暂无训练记录[/yellow]")
            console.print("[dim]提示: 使用 'nanobotrun import <路径>' 导入FIT文件[/dim]")
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


@app.command(name="hr-drift")
def hr_drift(
    limit: int = typer.Option(10, "--limit", "-n", help="分析最近N次训练"),
):
    """
    查看心率漂移分析

    示例:
        nanobotrun hr-drift
        nanobotrun hr-drift -n 5
    """
    from src.agents.tools import RunnerTools

    try:
        storage = StorageManager()
        tools = RunnerTools(storage)

        console.print(f"[bold]心率漂移分析[/bold] (最近 {limit} 次训练)")

        result = tools.get_hr_drift_analysis()

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
            f"[bold]心率漂移:[/bold] [{drift_color}]{drift_value:.1f}%[/{drift_color}]\n"
            f"[bold]相关性:[/bold] [{corr_color}]{corr_value}[/{corr_color}]\n"
            f"[bold]评估:[/bold] {assessment}\n\n"
            f"[dim]心率漂移 < 5%: 有氧基础良好[/dim]\n"
            f"[dim]心率漂移 5-10%: 需要加强有氧训练[/dim]\n"
            f"[dim]心率漂移 > 10%: 有氧能力不足[/dim]",
            title="[HR Drift] 心率漂移分析",
            border_style="blue",
        )
        console.print(panel)

    except Exception as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)


@app.command()
def memory(
    action: str = typer.Argument(..., help="操作：show/edit/clear"),
):
    """
    管理 Agent 记忆

    示例:
        nanobotrun memory show
        nanobotrun memory edit
        nanobotrun memory clear
    """
    from src.core.profile import ProfileStorageManager

    try:
        profile_storage = ProfileStorageManager()
        memory_file = profile_storage.memory_md_path

        if action == "show":
            if not memory_file.exists():
                console.print("[yellow]记忆文件不存在[/yellow]")
                return

            with open(memory_file, encoding="utf-8") as f:
                content = f.read()

            console.print(f"[bold]Agent 记忆:[/bold] {memory_file}")
            console.print(content)

        elif action == "clear":
            if not memory_file.exists():
                console.print("[yellow]记忆文件不存在[/yellow]")
                return

            from rich.prompt import Confirm

            if Confirm.ask("[red]确定要清空记忆文件吗？此操作不可恢复[/red]"):
                with open(memory_file, "w", encoding="utf-8") as f:
                    f.write("# Agent 记忆\n\n")
                console.print("[green]✓[/green] 记忆文件已清空")

        else:
            console.print("[red]未知操作[/red]")
            console.print("[dim]可用操作：show, edit, clear[/dim]")
            raise typer.Exit(1)

    except Exception as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)


@app.command()
def init():
    """
    初始化工作区

    将 ~/.nanobot-runner/ 作为 nanobot-ai 的 workspace 进行初始化，
    创建必要的目录结构和模板文件。
    """
    from nanobot.utils.helpers import sync_workspace_templates

    config = ConfigManager()
    workspace = config.data_dir.parent

    console.print(f"[bold]初始化工作区:[/bold] {workspace}")

    if not workspace.exists():
        workspace.mkdir(parents=True, exist_ok=True)
        console.print(f"[green]✓[/green] 创建工作区目录")

    data_dir = config.data_dir
    if not data_dir.exists():
        data_dir.mkdir(parents=True, exist_ok=True)
        console.print(f"[green]✓[/green] 创建数据目录: {data_dir}")

    added = sync_workspace_templates(workspace)
    if added:
        console.print("[green]✓[/green] 同步模板文件:")
        for name in added:
            console.print(f"  [dim]{name}[/dim]")
    else:
        console.print("[dim]模板文件已是最新[/dim]")

    console.print(f"\n[bold green]工作区初始化完成！[/bold green]")
    console.print(f"工作区路径: [cyan]{workspace}[/cyan]")
    console.print(f"数据路径: [cyan]{data_dir}[/cyan]")
    console.print("\n下一步:")
    console.print("  1. 导入数据: [cyan]nanobotrun import-data <FIT文件路径>[/cyan]")
    console.print("  2. 查看统计: [cyan]nanobotrun stats[/cyan]")
    console.print("  3. 查看画像: [cyan]nanobotrun profile show[/cyan]")


plan_app = typer.Typer(help="训练计划管理")
app.add_typer(plan_app, name="plan")


@plan_app.command("generate")
def generate_plan(
    goal_distance: float = typer.Option(
        ..., "--goal-distance", "-d", help="目标比赛距离（公里）"
    ),
    goal_date: str = typer.Option(..., "--goal-date", "-t", help="目标比赛日期（YYYY-MM-DD）"),
    current_vdot: Optional[float] = typer.Option(
        None, "--vdot", "-v", help="当前VDOT（可选，默认从画像获取）"
    ),
    weekly_volume: Optional[float] = typer.Option(
        None, "--volume", help="当前周跑量（公里，可选）"
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="输出文件路径（JSON格式）"
    ),
):
    """
    生成个性化训练计划

    基于用户画像和历史数据，生成科学的训练计划。

    示例:
        nanobotrun plan generate --goal-distance 21.0975 --goal-date 2026-06-01
        nanobotrun plan generate -d 42.195 -t 2026-10-15 -v 45.0
    """
    import json

    from src.core.analytics import AnalyticsEngine
    from src.core.profile import ProfileStorageManager
    from src.core.training_plan import TrainingPlanEngine

    try:
        storage = StorageManager()
        analytics = AnalyticsEngine(storage)
        profile_storage = ProfileStorageManager()
        engine = TrainingPlanEngine()

        profile = profile_storage.load_profile_json()
        if not profile:
            console.print("[red]错误: 未找到用户画像[/red]")
            console.print("请先运行 [cyan]nanobotrun import[/cyan] 导入数据")
            raise typer.Exit(1)

        profile_dict = profile.to_dict()
        vdot = current_vdot or profile_dict.get("estimated_vdot", 35.0)
        volume = weekly_volume or profile_dict.get("weekly_avg_distance", 30.0)
        age = profile_dict.get("age", 30)
        resting_hr = profile_dict.get("resting_hr", 60)

        console.print(f"[bold]生成训练计划[/bold]")
        console.print(f"  目标距离: [cyan]{goal_distance} km[/cyan]")
        console.print(f"  目标日期: [cyan]{goal_date}[/cyan]")
        console.print(f"  当前VDOT: [yellow]{vdot}[/yellow]")
        console.print(f"  周跑量: [yellow]{volume:.1f} km[/yellow]")

        plan = engine.generate_plan(
            user_id="default",
            goal_distance_km=goal_distance,
            goal_date=goal_date,
            current_vdot=vdot,
            current_weekly_distance_km=volume,
            age=age,
            resting_hr=resting_hr,
        )

        console.print(f"\n[bold green]训练计划生成成功！[/bold green]")
        console.print(f"  体能水平: [yellow]{plan.fitness_level.value}[/yellow]")
        console.print(f"  训练周数: [yellow]{len(plan.weeks)} 周[/yellow]")

        total_distance = sum(ws.weekly_distance_km for ws in plan.weeks)
        console.print(f"  总跑量: [yellow]{total_distance:.1f} km[/yellow]")

        console.print(f"\n[bold]训练计划概览:[/bold]")
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("周次", style="dim", width=6)
        table.add_column("日期范围", width=22)
        table.add_column("周跑量(km)", justify="right")
        table.add_column("重点", style="green")

        for ws in plan.weeks[:8]:
            table.add_row(
                f"第{ws.week_number}周",
                f"{ws.start_date} ~ {ws.end_date}",
                f"{ws.weekly_distance_km:.1f}",
                ws.focus or "-",
            )

        if len(plan.weeks) > 8:
            table.add_row("...", "...", "...", "...")

        console.print(table)

        if output:
            plan_dict = plan.to_dict()
            with open(output, "w", encoding="utf-8") as f:
                json.dump(plan_dict, f, ensure_ascii=False, indent=2)
            console.print(f"\n[green]✓[/green] 计划已保存到: [cyan]{output}[/cyan]")

    except ValueError as e:
        print_error(CLIError.config_missing(str(e)))
        raise typer.Exit(1)
    except Exception as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)


@plan_app.command("show")
def show_plan(
    plan_file: Path = typer.Argument(..., help="训练计划文件路径（JSON）"),
    week: Optional[int] = typer.Option(None, "--week", "-w", help="显示指定周的计划"),
):
    """
    显示训练计划详情

    示例:
        nanobotrun plan show plan.json
        nanobotrun plan show plan.json --week 4
    """
    import json

    if not plan_file.exists():
        print_error(CLIError.path_not_found(str(plan_file)))
        raise typer.Exit(1)

    try:
        with open(plan_file, encoding="utf-8") as f:
            plan_data = json.load(f)

        console.print(
            f"[bold]训练计划: {plan_data.get('goal_distance_km', '未知')}km比赛[/bold]"
        )
        console.print(f"  目标日期: [cyan]{plan_data.get('goal_date', '未知')}[/cyan]")
        console.print(
            f"  体能水平: [yellow]{plan_data.get('fitness_level', 'N/A')}[/yellow]"
        )

        weeks = plan_data.get("weeks", [])

        if week:
            if week < 1 or week > len(weeks):
                console.print(f"[red]无效的周次: {week}[/red]")
                raise typer.Exit(1)

            ws = weeks[week - 1]
            console.print(f"\n[bold]第{week}周详情:[/bold]")
            console.print(f"  日期: {ws.get('start_date')} ~ {ws.get('end_date')}")
            console.print(f"  周跑量: {ws.get('weekly_distance_km', 0):.1f} km")
            console.print(f"  重点: {ws.get('focus', '-')}")

            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("日期", width=12)
            table.add_column("训练类型", width=10)
            table.add_column("距离(km)", justify="right")
            table.add_column("时长(分)", justify="right")
            table.add_column("说明")

            for dp in ws.get("daily_plans", []):
                table.add_row(
                    dp.get("date", "-"),
                    dp.get("workout_type", "-"),
                    f"{dp.get('distance_km', 0):.1f}",
                    str(dp.get("duration_min", 0)),
                    dp.get("notes", "-"),
                )

            console.print(table)
        else:
            console.print(f"\n[bold]计划概览 ({len(weeks)}周):[/bold]")

            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("周次", style="dim", width=6)
            table.add_column("日期范围", width=22)
            table.add_column("周跑量(km)", justify="right")
            table.add_column("重点", style="green")

            for ws in weeks:
                table.add_row(
                    f"第{ws.get('week_number', 0)}周",
                    f"{ws.get('start_date')} ~ {ws.get('end_date')}",
                    f"{ws.get('weekly_distance_km', 0):.1f}",
                    ws.get("focus", "-"),
                )

            console.print(table)

    except json.JSONDecodeError:
        print_error(CLIError.storage_error("无效的JSON文件"))
        raise typer.Exit(1)
    except Exception as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)


@app.command()
def gateway(
    port: int = typer.Option(18790, "--port", "-p", help="Gateway端口"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="详细输出"),
):
    """
    启动飞书机器人Gateway服务

    启动后可通过飞书App与"Nanobot-ai助手"机器人交互：

    命令示例:
        /stats              # 查看训练统计
        /recent 5           # 查看最近5次训练
        /vd                 # 查看VDOT趋势
        /help               # 显示帮助

    自然语言示例:
        我最近跑得怎么样？
        给我一个训练建议
        我的VDOT是多少？
    """
    import asyncio

    from nanobot.agent import AgentLoop
    from nanobot.agent.tools import ToolRegistry
    from nanobot.bus import MessageBus
    from nanobot.channels.manager import ChannelManager
    from nanobot.cli.commands import _make_provider
    from nanobot.config.loader import get_data_dir, load_config
    from nanobot.cron.service import CronService
    from nanobot.cron.types import CronJob
    from nanobot.heartbeat.service import HeartbeatService
    from nanobot.session.manager import SessionManager
    from nanobot.utils.helpers import sync_workspace_templates

    from src.agents.tools import RunnerTools, create_tools

    if verbose:
        import logging

        logging.basicConfig(level=logging.DEBUG)

    console.print("[bold green]🐈 Nanobot Runner Gateway[/bold green]")
    console.print(f"[dim]启动 Gateway 服务，端口: {port}[/dim]")
    console.print("=" * 60)

    config = load_config()
    workspace = Path.home() / ".nanobot-runner"
    workspace.mkdir(parents=True, exist_ok=True)

    sync_workspace_templates(workspace)

    config.agents.defaults.workspace = str(workspace)

    bus = MessageBus()
    provider = _make_provider(config)
    session_manager = SessionManager(workspace)

    cron_store_path = get_data_dir() / "cron" / "jobs.json"
    cron = CronService(cron_store_path)

    storage = StorageManager()
    runner_tools = RunnerTools(storage)

    registry = ToolRegistry()
    for tool in create_tools(runner_tools):
        registry.register(tool)

    agent = AgentLoop(
        bus=bus,
        provider=provider,
        workspace=workspace,
        model=config.agents.defaults.model,
        temperature=config.agents.defaults.temperature,
        max_tokens=config.agents.defaults.max_tokens,
        max_iterations=config.agents.defaults.max_tool_iterations,
        memory_window=config.agents.defaults.memory_window,
        reasoning_effort=config.agents.defaults.reasoning_effort,
        cron_service=cron,
        restrict_to_workspace=config.tools.restrict_to_workspace,
        session_manager=session_manager,
        mcp_servers=config.tools.mcp_servers,
        channels_config=config.channels,
    )

    agent.tools = registry

    async def on_cron_job(job: CronJob) -> str | None:
        response = await agent.process_direct(
            job.payload.message,
            session_key=f"cron:{job.id}",
            channel=job.payload.channel or "cli",
            chat_id=job.payload.to or "direct",
        )
        if job.payload.deliver and job.payload.to:
            from nanobot.bus.events import OutboundMessage

            await bus.publish_outbound(
                OutboundMessage(
                    channel=job.payload.channel or "cli",
                    chat_id=job.payload.to,
                    content=response or "",
                )
            )
        return response

    cron.on_job = on_cron_job

    channels = ChannelManager(config, bus)

    def _pick_heartbeat_target() -> tuple[str, str]:
        enabled = set(channels.enabled_channels)
        for item in session_manager.list_sessions():
            key = item.get("key") or ""
            if ":" not in key:
                continue
            channel, chat_id = key.split(":", 1)
            if channel in {"cli", "system"}:
                continue
            if channel in enabled and chat_id:
                return channel, chat_id
        return "cli", "direct"

    async def on_heartbeat_execute(tasks: str) -> str:
        channel, chat_id = _pick_heartbeat_target()

        async def _silent(*_args, **_kwargs):
            pass

        return await agent.process_direct(
            tasks,
            session_key="heartbeat",
            channel=channel,
            chat_id=chat_id,
            on_progress=_silent,
        )

    async def on_heartbeat_notify(response: str) -> None:
        from nanobot.bus.events import OutboundMessage

        channel, chat_id = _pick_heartbeat_target()
        if channel == "cli":
            return
        await bus.publish_outbound(
            OutboundMessage(channel=channel, chat_id=chat_id, content=response)
        )

    hb_cfg = config.gateway.heartbeat
    heartbeat = HeartbeatService(
        workspace=workspace,
        provider=provider,
        model=agent.model,
        on_execute=on_heartbeat_execute,
        on_notify=on_heartbeat_notify,
        interval_s=hb_cfg.interval_s,
        enabled=hb_cfg.enabled,
    )

    if channels.enabled_channels:
        console.print(f"[green]✓[/green] 已启用通道: {', '.join(channels.enabled_channels)}")
    else:
        console.print("[yellow]警告: 未启用任何通道[/yellow]")

    cron_status = cron.status()
    if cron_status["jobs"] > 0:
        console.print(f"[green]✓[/green] 定时任务: {cron_status['jobs']} 个")

    console.print(f"[green]✓[/green] 心跳检测: 每 {hb_cfg.interval_s} 秒")
    console.print()
    console.print("[bold cyan]飞书机器人交互命令：[/bold cyan]")
    console.print("  • /stats - 查看训练统计")
    console.print("  • /recent [数量] - 查看最近训练")
    console.print("  • /vd - 查看VDOT趋势")
    console.print("  • /hr_drift - 查看心率漂移")
    console.print("  • /help - 显示帮助")
    console.print()
    console.print("[bold green]Gateway 服务已启动，按 Ctrl+C 停止[/bold green]")

    async def run():
        try:
            await cron.start()
            await heartbeat.start()
            await asyncio.gather(
                agent.run(),
                channels.start_all(),
            )
        except KeyboardInterrupt:
            console.print("\n[yellow]正在关闭...[/yellow]")
        finally:
            await agent.close_mcp()
            heartbeat.stop()
            cron.stop()
            agent.stop()
            await channels.stop_all()

    asyncio.run(run())


@app.command()
def report(
    push: bool = typer.Option(False, "--push", "-p", help="推送到飞书"),
    schedule: Optional[str] = typer.Option(
        None, "--schedule", "-s", help="配置定时推送时间 (HH:MM)"
    ),
    enable: Optional[bool] = typer.Option(None, "--enable/--disable", help="启用/禁用定时推送"),
    status: bool = typer.Option(False, "--status", help="查看定时推送状态"),
    age: int = typer.Option(30, "--age", "-a", help="年龄（用于计算最大心率）"),
):
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
    from src.core.report_service import ReportService

    try:
        service = ReportService()

        if status:
            schedule_status = service.get_schedule_status()
            if schedule_status.get("configured"):
                state_color = "green" if schedule_status.get("enabled") else "yellow"
                state_text = "已启用" if schedule_status.get("enabled") else "已禁用"
                console.print(
                    f"[bold]定时推送状态:[/bold] [{state_color}]{state_text}[/{state_color}]"
                )
                console.print(
                    f"  推送时间: [cyan]{schedule_status.get('time', 'N/A')}[/cyan]"
                )
                console.print(
                    f"  推送到飞书: {'[green]是[/green]' if schedule_status.get('push') else '[dim]否[/dim]'}"
                )
                console.print(
                    f"  年龄设置: [cyan]{schedule_status.get('age', 30)}[/cyan] 岁"
                )
            else:
                print_status("未配置定时推送", "warning")
                console.print(
                    "[dim]使用 'nanobotrun report --schedule HH:MM' 配置定时推送[/dim]"
                )
            return

        if enable is not None:
            result = service.enable_schedule(enabled=enable)
            if result.get("success"):
                print_status(result.get("message", ""), "success")
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

            if result.get("success"):
                print_status(result.get("message", ""), "success")
            else:
                print_error(
                    {
                        "message": result.get("error", "配置失败"),
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
            result = service.run_report_now(push=push, age=age)

        if not result.get("success"):
            print_error(
                {
                    "message": f"生成晨报失败: {result.get('error', '未知错误')}",
                    "suggestion": "请检查是否有跑步数据，或使用 'nanobotrun import' 导入数据",
                }
            )
            raise typer.Exit(1)

        report_data = result.get("report", {})

        _display_report(report_data)

        if push:
            push_result = result.get("push_result", {})
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


def _display_report(report_data: dict):
    """
    在终端显示晨报内容

    Args:
        report_data: 晨报数据
    """
    from rich.panel import Panel
    from rich.table import Table

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
        "green" if "良好" in status_text else "yellow" if "注意" in status_text else "red"
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


@profile_app.command("show")
def profile_show(
    days: int = typer.Option(90, "--days", "-d", help="分析天数"),
    age: int = typer.Option(30, "--age", "-a", help="年龄（用于计算最大心率）"),
    resting_hr: int = typer.Option(60, "--resting-hr", "-r", help="静息心率"),
    rebuild: bool = typer.Option(False, "--rebuild", help="重新构建画像"),
):
    """
    显示用户画像信息

    包含：平均 VDOT、健身水平、训练模式、受伤风险评估等
    """
    from rich.panel import Panel
    from rich.table import Table

    try:
        config = ConfigManager()
        storage = StorageManager(config.data_dir)
        profile_storage = ProfileStorageManager()
        profile = None

        if rebuild:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                progress.add_task("正在构建用户画像...", total=None)
                engine = ProfileEngine(storage)
                profile = engine.build_profile(
                    user_id="default_user",
                    days=days,
                    age=age,
                    resting_hr=resting_hr,
                )
                profile_storage.save_profile_json(profile)
        else:
            profile = profile_storage.load_profile_json()

            if profile is None:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    transient=True,
                ) as progress:
                    progress.add_task("首次运行，正在构建用户画像...", total=None)
                    engine = ProfileEngine(storage)
                    profile = engine.build_profile(
                        user_id="default_user",
                        days=days,
                        age=age,
                        resting_hr=resting_hr,
                    )
                    profile_storage.save_profile_json(profile)

        if profile is None or profile.total_activities == 0:
            console.print(
                Panel(
                    "[yellow]暂无跑步数据[/yellow]\n\n" "使用 'nanobotrun import <路径>' 导入FIT文件",
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
        training_table.add_row("周平均时长", f"{profile.weekly_avg_duration_hours:.2f} 小时")
        training_table.add_row("训练模式", f"[bold]{profile.training_pattern.value}[/bold]")
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

        load_table.add_row("ATL (疲劳)", f"[{atl_color}]{profile.atl:.2f}[/{atl_color}]")
        load_table.add_row("CTL (体能)", f"[{ctl_color}]{profile.ctl:.2f}[/{ctl_color}]")
        load_table.add_row("TSB (状态)", f"[{tsb_color}]{profile.tsb:.2f}[/{tsb_color}]")
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


if __name__ == "__main__":
    app()
