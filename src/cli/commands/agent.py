# Agent 相关命令
# 包含 chat 和 memory 命令

import contextlib
from typing import Any

import typer

from src.cli.common import CLIError, console, print_error

app = typer.Typer(help="Agent 交互命令")


async def _connect_mcp_tools(context: Any, agent: Any) -> dict[str, Any]:
    """连接MCP服务器工具到Agent

    从config.json读取MCP服务器配置，连接并注册工具。

    Args:
        context: 应用上下文
        agent: AgentLoop实例

    Returns:
        dict[str, Any]: 连接结果
    """
    from src.core.tools.mcp_connector import connect_mcp_tools_from_config

    config_path = context.config.config_file
    try:
        return await connect_mcp_tools_from_config(config_path, agent.tools)
    except Exception as e:
        import logging

        logging.getLogger(__name__).warning(f"连接MCP工具失败: {e}")
        return {"connected_servers": [], "failed_servers": [], "exit_stacks": {}}


@app.command()
def chat() -> None:
    """
    启动自然语言交互模式
    """
    import asyncio

    asyncio.run(_run_chat())


async def _run_chat() -> None:
    """异步聊天循环函数"""
    from rich.prompt import Prompt

    from src.agents.tools import RunnerTools, create_tools
    from src.cli.formatter import format_agent_response
    from src.core.context import get_context
    from src.core.provider_adapter import RunnerProviderAdapter

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
        context = get_context()

        if not context.config.has_llm_config():
            console.print("[red]LLM配置缺失，请先运行: nanobotrun init[/red]")
            return

        adapter = RunnerProviderAdapter(context.config)

        if not adapter.is_available():
            console.print("[red]LLM Provider不可用，请检查配置[/red]")
            return

        provider_instance = adapter.get_provider_instance()
        agent_defaults = adapter.get_agent_defaults()
        llm_config = adapter.get_llm_config()

        from nanobot.agent import AgentLoop
        from nanobot.bus import MessageBus

        workspace = context.config.base_dir
        runner_tools = RunnerTools(context)

        bus = MessageBus()
        agent = AgentLoop(
            bus=bus,
            provider=provider_instance,
            workspace=workspace,
            model=agent_defaults.model,
            max_iterations=agent_defaults.max_tool_iterations,
            context_window_tokens=agent_defaults.context_window_tokens,
            context_block_limit=agent_defaults.context_block_limit,
            max_tool_result_chars=agent_defaults.max_tool_result_chars,
        )

        for tool in create_tools(runner_tools):
            agent.tools.register(tool)

        mcp_result = await _connect_mcp_tools(context, agent)
        mcp_connected = mcp_result.get("connected_servers", [])
        mcp_failed = mcp_result.get("failed_servers", [])

        console.print("[bold green][OK] Agent 已初始化[/bold green]")
        console.print(f"[dim]模型: {llm_config.model}[/dim]")
        if mcp_connected:
            console.print(f"[dim]MCP工具: {', '.join(mcp_connected)}[/dim]")
        if mcp_failed:
            console.print(f"[yellow]MCP连接失败: {', '.join(mcp_failed)}[/yellow]")
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
    finally:
        with contextlib.suppress(Exception):
            adapter.close()


@app.command()
def memory(
    action: str = typer.Argument(..., help="操作：show/edit/clear"),
) -> None:
    """
    管理 Agent 记忆

    示例:
        nanobotrun memory show
        nanobotrun memory edit
        nanobotrun memory clear

    Args:
        action: 操作类型 (show/edit/clear)
    """
    from src.core.context import AppContextFactory

    try:
        context = AppContextFactory.create()
        memory_file = context.profile_storage.memory_md_path

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
                console.print("[dim]操作已取消[/dim]")

        elif action == "edit":
            if not memory_file.exists():
                console.print("[yellow]记忆文件不存在[/yellow]")
                return

            import subprocess

            editor = None
            for ed in ["code", "vim", "nano", "notepad"]:
                try:
                    subprocess.run([ed, "--version"], capture_output=True)
                    editor = ed
                    break
                except (FileNotFoundError, OSError):
                    continue

            if editor:
                console.print(f"[dim]使用 {editor} 打开记忆文件...[/dim]")
                subprocess.run([editor, str(memory_file)])
            else:
                console.print("[yellow]未找到可用的编辑器[/yellow]")
                console.print(f"[dim]请手动编辑: {memory_file}[/dim]")

        else:
            console.print(f"[red]未知操作: {action}[/red]")
            console.print("[dim]可用操作: show, edit, clear[/dim]")

    except Exception as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)
