# CLI入口模块
# 基于Typer和Rich的本地跑步数据助理

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt

from src.core.config import ConfigManager
from src.core.parser import FitParser
from src.core.storage import StorageManager
from src.core.indexer import IndexManager
from src.core.importer import ImportService

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
    start_date: Optional[str] = typer.Option(None, "--start", "-s", help="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = typer.Option(None, "--end", "-e", help="结束日期 (YYYY-MM-DD)"),
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
    from nanobot.agent import AgentLoop
    from nanobot.agent.tools import Tool, ToolRegistry
    from nanobot.bus import MessageBus
    from nanobot.providers import LiteLLMProvider

    from src.agents.tools import RunnerTools, TOOL_DESCRIPTIONS
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
        storage = StorageManager()
        runner_tools = RunnerTools(storage)

        registry = ToolRegistry()

        for tool_name, tool_desc in TOOL_DESCRIPTIONS.items():
            tool = Tool(
                name=tool_name,
                description=tool_desc.get("description", ""),
                function=getattr(runner_tools, tool_name)
            )
            registry.register(tool)

        workspace = Path.home() / ".nanobot-runner"
        workspace.mkdir(parents=True, exist_ok=True)

        provider = LiteLLMProvider(model="local")

        bus = MessageBus()

        agent = AgentLoop(
            bus=bus,
            provider=provider,
            workspace=workspace,
            max_iterations=20,
            memory_window=10,
        )

        agent.tools = registry

        console.print("[bold green]✓ Agent 已初始化[/bold green]")
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
                    response = agent.chat(user_input)

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


if __name__ == "__main__":
    app()
