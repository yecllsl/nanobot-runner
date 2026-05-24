# Model Presets 管理命令
# 提供模型预设的查看功能

from __future__ import annotations

import typer
from rich.table import Table

from src.cli.common import CLIError, console, print_error
from src.cli.handlers.model_handler import ModelHandler
from src.core.base.exceptions import NanobotRunnerError

app = typer.Typer(help="Model Presets 管理", no_args_is_help=True)


@app.command(name="list")
def list_presets() -> None:
    """查看 Model Presets 列表

    展示当前配置的所有模型预设，包括名称、Provider、模型等信息。

    Examples:
        nanobotrun model list
    """
    try:
        handler = ModelHandler()
        presets = handler.list_presets()

        if not presets:
            console.print("[yellow]暂无 Model Presets 配置[/yellow]")
            console.print(
                "[dim]在 config.json 中添加 model_presets 字段以配置预设[/dim]"
            )
            return

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("预设名称", width=15)
        table.add_column("Provider", width=15)
        table.add_column("模型", width=30)
        table.add_column("Temperature", width=12)

        for preset in presets:
            temp = preset.get("temperature")
            temp_str = f"{temp}" if temp is not None else "-"
            table.add_row(
                preset["name"],
                preset["provider"],
                preset["model"],
                temp_str,
            )

        console.print(table)
        console.print(f"\n共 [bold]{len(presets)}[/bold] 个预设")
        console.print(
            "[dim]切换预设: 在飞书/WebUI 中使用 /model <preset_name> 命令[/dim]"
        )

    except NanobotRunnerError as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)
