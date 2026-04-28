# 工具管理命令
# 提供 MCP 工具的列表、启用、禁用、添加、移除等管理功能

import json
from pathlib import Path

import typer

from src.cli.common import CLIError, console, print_error

app = typer.Typer(help="工具管理命令")


def _get_config_path() -> Path:
    """获取config.json路径

    Returns:
        Path: config.json文件路径
    """
    from src.core.base.context import AppContextFactory

    context = AppContextFactory.create()
    return context.config.config_file


@app.command("list")
def list_tools() -> None:
    """列出所有已配置的工具

    显示MCP服务器及其工具的状态信息。
    """
    from src.core.tools.tool_manager import ToolManager

    try:
        config_path = _get_config_path()
        manager = ToolManager(config_path)
        tools = manager.list_tools()

        if not tools:
            console.print("[yellow]未配置任何工具[/yellow]")
            console.print("[dim]使用 'nanobotrun tools add' 添加MCP工具[/dim]")
            return

        console.print("[bold]已配置工具列表[/bold]\n")

        servers = manager.list_servers()
        for server_name in servers:
            server_config = manager.get_server_config(server_name)
            if server_config is None:
                continue

            status_icon = "🟢" if not server_config.disabled else "🔴"
            transport = server_config.transport_type.value
            console.print(
                f"  {status_icon} [bold]{server_name}[/bold] [dim]({transport})[/dim]"
            )

            if server_config.command:
                cmd_str = server_config.command
                if server_config.args:
                    cmd_str += " " + " ".join(server_config.args)
                console.print(f"    [dim]命令: {cmd_str}[/dim]")
            elif server_config.url:
                console.print(f"    [dim]URL: {server_config.url}[/dim]")

            enabled_str = (
                ", ".join(server_config.enabled_tools)
                if server_config.enabled_tools != ["*"]
                else "全部工具"
            )
            console.print(f"    [dim]启用工具: {enabled_str}[/dim]")
            console.print()

        enabled_count = sum(1 for t in tools if t.status.value == "enabled")
        disabled_count = len(tools) - enabled_count
        console.print(
            f"[dim]共 {len(tools)} 个工具 "
            f"(启用: {enabled_count}, 禁用: {disabled_count})[/dim]"
        )

    except Exception as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)


@app.command("add")
def add_server(
    name: str = typer.Argument(..., help="服务器名称"),
    command: str | None = typer.Option(None, "--command", "-c", help="启动命令"),
    args: str | None = typer.Option(
        None, "--args", "-a", help="命令参数（JSON数组格式）"
    ),
    url: str | None = typer.Option(None, "--url", "-u", help="服务端URL"),
    transport_type: str = typer.Option(
        "stdio", "--type", "-t", help="传输协议类型: stdio/sse/streamableHttp"
    ),
    timeout: int = typer.Option(30, "--timeout", help="工具调用超时时间（秒）"),
    enabled_tools: str | None = typer.Option(
        None, "--enabled-tools", help="启用的工具列表（逗号分隔，*表示全部）"
    ),
) -> None:
    """添加MCP服务器配置

    示例:
        nanobotrun tools add weather --command npx --args '["-y", "@dangahagan/weather-mcp"]'
        nanobotrun tools add weather --command npx --args '["-y", "@dangahagan/weather-mcp"]' --type stdio
    """
    from src.core.tools.models import MCPServerConfig, MCPTransportType
    from src.core.tools.tool_manager import ToolManager

    try:
        config_path = _get_config_path()

        try:
            transport = MCPTransportType(transport_type)
        except ValueError:
            console.print(f"[red]无效的传输协议类型: {transport_type}[/red]")
            console.print("[dim]支持的类型: stdio, sse, streamableHttp[/dim]")
            raise typer.Exit(1)

        parsed_args: list[str] | None = None
        if args:
            try:
                parsed_args = json.loads(args)
                if not isinstance(parsed_args, list):
                    console.print("[red]args参数必须是JSON数组格式[/red]")
                    raise typer.Exit(1)
            except json.JSONDecodeError:
                console.print("[red]args参数JSON解析失败[/red]")
                raise typer.Exit(1)

        parsed_enabled: list[str] = ["*"]
        if enabled_tools:
            parsed_enabled = [t.strip() for t in enabled_tools.split(",")]

        server_config = MCPServerConfig(
            name=name,
            transport_type=transport,
            command=command,
            args=parsed_args,
            url=url,
            tool_timeout=timeout,
            enabled_tools=parsed_enabled,
        )

        manager = ToolManager(config_path)
        if manager.add_server(server_config):
            console.print(f"[green]✓[/green] MCP服务器 '{name}' 添加成功")
        else:
            console.print(f"[red]✗[/red] MCP服务器 '{name}' 添加失败")
            raise typer.Exit(1)

    except typer.Exit:
        raise
    except Exception as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)


@app.command("remove")
def remove_server(
    name: str = typer.Argument(..., help="服务器名称"),
) -> None:
    """移除MCP服务器配置

    示例:
        nanobotrun tools remove weather
    """
    from src.core.tools.tool_manager import ToolManager

    try:
        config_path = _get_config_path()
        manager = ToolManager(config_path)

        if manager.get_server_config(name) is None:
            console.print(f"[yellow]MCP服务器 '{name}' 不存在[/yellow]")
            raise typer.Exit(1)

        if manager.remove_server(name):
            console.print(f"[green]✓[/green] MCP服务器 '{name}' 已移除")
        else:
            console.print(f"[red]✗[/red] MCP服务器 '{name}' 移除失败")
            raise typer.Exit(1)

    except typer.Exit:
        raise
    except Exception as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)


@app.command("enable")
def enable_server(
    name: str = typer.Argument(..., help="服务器名称"),
) -> None:
    """启用MCP服务器

    示例:
        nanobotrun tools enable weather
    """
    from src.core.tools.tool_manager import ToolManager

    try:
        config_path = _get_config_path()
        manager = ToolManager(config_path)

        if manager.get_server_config(name) is None:
            console.print(f"[yellow]MCP服务器 '{name}' 不存在[/yellow]")
            raise typer.Exit(1)

        if manager.enable_server(name):
            console.print(f"[green]✓[/green] MCP服务器 '{name}' 已启用")
        else:
            console.print(f"[red]✗[/red] MCP服务器 '{name}' 启用失败")
            raise typer.Exit(1)

    except typer.Exit:
        raise
    except Exception as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)


@app.command("disable")
def disable_server(
    name: str = typer.Argument(..., help="服务器名称"),
) -> None:
    """禁用MCP服务器

    示例:
        nanobotrun tools disable weather
    """
    from src.core.tools.tool_manager import ToolManager

    try:
        config_path = _get_config_path()
        manager = ToolManager(config_path)

        if manager.get_server_config(name) is None:
            console.print(f"[yellow]MCP服务器 '{name}' 不存在[/yellow]")
            raise typer.Exit(1)

        if manager.disable_server(name):
            console.print(f"[green]✓[/green] MCP服务器 '{name}' 已禁用")
        else:
            console.print(f"[red]✗[/red] MCP服务器 '{name}' 禁用失败")
            raise typer.Exit(1)

    except typer.Exit:
        raise
    except Exception as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)


@app.command("import-claude")
def import_claude_config(
    config_path_str: str = typer.Argument(
        ...,
        help="Claude Desktop配置文件路径",
    ),
) -> None:
    """导入Claude Desktop的MCP配置

    从Claude Desktop的配置文件中导入MCP服务器配置。

    示例:
        nanobotrun tools import-claude ~/Library/Application\\ Support/Claude/claude_desktop_config.json
    """
    from src.core.tools.mcp_config_helper import MCPConfigHelper

    try:
        claude_config_path = Path(config_path_str).expanduser()
        if not claude_config_path.exists():
            console.print(
                f"[red]Claude Desktop配置文件不存在: {claude_config_path}[/red]"
            )
            raise typer.Exit(1)

        config_path = _get_config_path()
        helper = MCPConfigHelper(config_path)

        if helper.import_claude_desktop_config(claude_config_path):
            console.print("[green]✓[/green] Claude Desktop MCP配置导入成功")
        else:
            console.print("[yellow]未导入任何MCP服务器配置[/yellow]")

    except typer.Exit:
        raise
    except Exception as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)


@app.command("validate")
def validate_config() -> None:
    """验证MCP配置有效性

    检查所有MCP服务器配置是否符合规范。
    """
    from src.core.tools.tool_manager import ToolManager

    try:
        config_path = _get_config_path()
        manager = ToolManager(config_path)
        errors = manager.validate_config()

        if not errors:
            console.print("[green]✓[/green] MCP配置验证通过")
        else:
            console.print("[red]✗[/red] MCP配置验证失败:\n")
            for error in errors:
                console.print(f"  • {error}")
            raise typer.Exit(1)

    except typer.Exit:
        raise
    except Exception as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)
