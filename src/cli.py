# CLI入口模块
# 基于Typer和Rich的本地跑步数据助理

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt

from src.core.config import ConfigManager
from src.core.importer import ImportService
from src.core.indexer import IndexManager
from src.core.parser import FitParser
from src.core.storage import StorageManager

app = typer.Typer(
    name="nanobotrun",
    help="Nanobot Runner - 本地跑步数据助理",
    add_completion=False,
)

console = Console()


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
        console.print(f"[red]错误：路径不存在: {path}[/red]")
        raise typer.Exit(1)

    try:
        config = ConfigManager()
        storage = StorageManager(config.data_dir)
        indexer = IndexManager(config.index_file)
        parser = FitParser()
        importer = ImportService(parser, storage, indexer)

        if path_obj.is_file():
            console.print(f"[cyan]正在导入文件: {path}[/cyan]")
            result = importer.import_file(path_obj, force=force)
            if result.get("status") == "added":
                console.print(f"[green]✓ 导入成功[/green]")
            elif result.get("status") == "skipped":
                console.print(f"[yellow]文件已存在，跳过导入[/yellow]")
            else:
                console.print(f"[red]导入失败: {result.get('message', '未知错误')}[/red]")
        elif path_obj.is_dir():
            console.print(f"[cyan]正在导入目录: {path}[/cyan]")
            stats = importer.import_directory(path_obj, force=force)
            console.print(f"[green]✓ 导入完成，共 {stats['added']} 个文件新增[/green]")

    except Exception as e:
        console.print(f"[red]导入失败: {str(e)}[/red]")
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
    """
    try:
        config = ConfigManager()
        storage = StorageManager(config.data_dir)

        if year:
            years = [year]
        else:
            years = None

        lf = storage.read_parquet(years=years)
        df = lf.collect()

        if df.is_empty():
            console.print("[yellow]暂无跑步数据[/yellow]")
            return

        from datetime import datetime

        if start_date or end_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None

            if start_dt:
                df = df.filter(df["timestamp"] >= str(start_dt))
            if end_dt:
                df = df.filter(df["timestamp"] <= str(end_dt))

        total_runs = df.height
        total_distance = df["total_distance"].sum()
        total_time = df["total_timer_time"].sum()
        avg_distance = df["total_distance"].mean()
        avg_time = df["total_timer_time"].mean()
        avg_hr = df["avg_heart_rate"].mean()

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

    except Exception as e:
        console.print(f"[red]获取统计失败: {str(e)}[/red]")
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

    console.print("[bold green]🤖 Nanobot Runner Agent[/bold green]")
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

        console.print(f"[bold green]✓ Agent 已初始化[/bold green]")
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

        # 查看状态
        if status:
            schedule_status = service.get_schedule_status()
            if schedule_status.get("configured"):
                state = (
                    "[green]已启用[/green]"
                    if schedule_status.get("enabled")
                    else "[yellow]已禁用[/yellow]"
                )
                console.print(f"[bold]定时推送状态:[/bold] {state}")
                console.print(f"  推送时间: {schedule_status.get('time', 'N/A')}")
                console.print(f"  推送到飞书: {'是' if schedule_status.get('push') else '否'}")
                console.print(f"  年龄设置: {schedule_status.get('age', 30)}")
            else:
                console.print("[yellow]未配置定时推送[/yellow]")
                console.print(
                    "使用 [cyan]nanobotrun report --schedule HH:MM[/cyan] 配置定时推送"
                )
            return

        # 启用/禁用
        if enable is not None:
            result = service.enable_schedule(enabled=enable)
            if result.get("success"):
                console.print(f"[green]{result.get('message')}[/green]")
            else:
                console.print(f"[red]{result.get('error')}[/red]")
                raise typer.Exit(1)
            return

        # 配置定时推送
        if schedule:
            result = service.schedule_report(time_str=schedule, push=push, age=age)
            if result.get("success"):
                console.print(f"[green]{result.get('message')}[/green]")
            else:
                console.print(f"[red]{result.get('error')}[/red]")
                raise typer.Exit(1)
            return

        # 立即生成晨报
        result = service.run_report_now(push=push, age=age)

        if not result.get("success"):
            console.print(f"[red]生成晨报失败: {result.get('error')}[/red]")
            raise typer.Exit(1)

        report_data = result.get("report", {})

        # 显示晨报内容
        _display_report(report_data)

        # 推送结果
        if push:
            push_result = result.get("push_result", {})
            if push_result.get("success"):
                console.print("[green]晨报已推送到飞书[/green]")
            else:
                console.print(f"[red]推送失败: {push_result.get('error')}[/red]")

    except Exception as e:
        console.print(f"[red]操作失败: {str(e)}[/red]")
        raise typer.Exit(1)


def _display_report(report_data: dict):
    """
    在终端显示晨报内容

    Args:
        report_data: 晨报数据
    """
    from rich.panel import Panel
    from rich.table import Table

    # 日期和问候语
    console.print()
    console.print(
        Panel(
            f"[bold]{report_data.get('date', '')}[/bold]\n{report_data.get('greeting', '')}",
            title="☀️ 每日跑步晨报",
            border_style="blue",
        )
    )

    # 昨日训练
    yesterday_run = report_data.get("yesterday_run")
    if yesterday_run:
        table = Table(title="昨日训练", show_header=False)
        table.add_column("指标", style="cyan")
        table.add_column("数值", style="green")
        table.add_row("距离", f"{yesterday_run.get('distance_km', 0)} km")
        table.add_row("时长", f"{yesterday_run.get('duration_min', 0)} 分钟")
        table.add_row("TSS", str(yesterday_run.get("tss", 0)))
        console.print(table)
    else:
        console.print("[dim]昨日无训练记录[/dim]")

    # 体能状态
    fitness = report_data.get("fitness_status", {})
    fitness_table = Table(title="体能状态", show_header=False)
    fitness_table.add_column("指标", style="cyan")
    fitness_table.add_column("数值", style="green")
    fitness_table.add_row("ATL (疲劳)", str(fitness.get("atl", 0)))
    fitness_table.add_row("CTL (体能)", str(fitness.get("ctl", 0)))
    fitness_table.add_row("TSB (状态)", str(fitness.get("tsb", 0)))
    fitness_table.add_row("评估", fitness.get("status", "数据不足"))
    console.print(fitness_table)

    # 训练建议
    console.print(
        Panel(
            report_data.get("training_advice", "暂无建议"),
            title="今日建议",
            border_style="green",
        )
    )

    # 本周计划
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


if __name__ == "__main__":
    app()
