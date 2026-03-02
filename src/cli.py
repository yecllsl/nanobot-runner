# CLI入口
# 命令行界面主程序

import typer
from rich.console import Console
from rich.table import Table
from pathlib import Path

from src.core.importer import ImportService
from src.core.storage import StorageManager

app = typer.Typer(
    name="nanobotrun",
    help="Nanobot Runner - 桌面端私人AI跑步助理",
    no_args_is_help=True
)

console = Console()
import_service = ImportService()
storage_manager = StorageManager()


@app.command()
def import_data(
    path: str = typer.Argument(..., help="FIT文件或目录路径"),
    force: bool = typer.Option(False, "--force", "-f", help="强制导入（跳过去重）")
):
    """
    导入FIT文件或目录
    """
    filepath = Path(path)
    
    if not filepath.exists():
        console.print(f"[red]错误: 路径不存在: {path}[/red]")
        raise typer.Exit(code=1)
    
    if filepath.is_file():
        if filepath.suffix != ".fit":
            console.print("[red]错误: 只支持.fit格式文件[/red]")
            raise typer.Exit(code=1)
        
        import_service.import_file(filepath)
    elif filepath.is_dir():
        import_service.import_directory(filepath)
    else:
        console.print("[red]错误: 无效的路径[/red]")
        raise typer.Exit(code=1)


@app.command()
def stats():
    """
    查看本地数据统计
    """
    stats = storage_manager.get_stats()
    
    table = Table(title="本地数据统计")
    table.add_column("指标", style="cyan")
    table.add_column("值", style="magenta")
    
    table.add_row("总记录数", str(stats.get("total_records", 0)))
    
    time_range = stats.get("time_range")
    if time_range:
        table.add_row("时间范围", f"{time_range.get('start', 'N/A')} ~ {time_range.get('end', 'N/A')}")
    
    years = stats.get("years", [])
    table.add_row("年份", ", ".join(str(y) for y in years) if years else "N/A")
    
    console.print(table)


@app.command()
def chat():
    """
    启动自然语言交互模式
    """
    console.print("[bold]正在启动Agent交互模式...[/bold]")
    console.print("请输入您的问题，输入 'exit' 退出")
    console.print("=" * 50)
    
    # TODO: 集成 nanobot-ai Agent
    console.print("[yellow]注意: Agent功能待实现[/yellow]")


@app.command()
def version():
    """
    显示版本信息
    """
    from . import __version__
    console.print(f"[bold]Nanobot Runner[/bold] v{__version__}")


if __name__ == "__main__":
    app()
