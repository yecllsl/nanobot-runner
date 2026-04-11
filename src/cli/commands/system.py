# 系统相关命令
# 包含 version 和 init 命令

import typer

from src.cli.common import console

app = typer.Typer(help="系统管理命令")


@app.command()
def version() -> None:
    """
    显示版本信息
    """
    from src import __version__

    console.print(f"[bold]Nanobot Runner[/bold] v{__version__}")


@app.command()
def init() -> None:
    """
    初始化工作区

    将 ~/.nanobot-runner/ 作为 nanobot-ai 的 workspace 进行初始化，
    创建必要的目录结构和模板文件。
    """
    from nanobot.utils.helpers import sync_workspace_templates

    from src.core.context import AppContextFactory

    context = AppContextFactory.create()
    workspace = context.config.data_dir.parent

    console.print(f"[bold]初始化工作区:[/bold] {workspace}")

    if not workspace.exists():
        workspace.mkdir(parents=True, exist_ok=True)
        console.print("[green]✓[/green] 创建工作区目录")

    data_dir = context.config.data_dir
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

    console.print("\n[bold green]工作区初始化完成！[/bold green]")
    console.print(f"工作区路径: [cyan]{workspace}[/cyan]")
    console.print(f"数据路径: [cyan]{data_dir}[/cyan]")
    console.print("\n下一步:")
    console.print("  1. 导入数据: [cyan]nanobotrun import-data <FIT文件路径>[/cyan]")
    console.print("  2. 查看统计: [cyan]nanobotrun stats[/cyan]")
    console.print("  3. 查看画像: [cyan]nanobotrun profile show[/cyan]")
