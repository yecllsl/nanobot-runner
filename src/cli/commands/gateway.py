# Gateway 相关命令
# 包含 gateway 命令

import asyncio
import logging

import typer

from src.cli.common import console
from src.core.logger import get_logger

logger = get_logger(__name__)

app = typer.Typer(help="Gateway 服务命令")


@app.command()
def gateway(
    port: int = typer.Option(18790, "--port", "-p", help="Gateway端口"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="详细输出"),
    logs: bool = typer.Option(False, "--logs", "-l", help="启用日志输出"),
) -> None:
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
    from nanobot.agent import AgentLoop
    from nanobot.bus import MessageBus
    from nanobot.channels.manager import ChannelManager
    from nanobot.cli.commands import _make_provider
    from nanobot.config.loader import load_config
    from nanobot.cron.service import CronService
    from nanobot.heartbeat.service import HeartbeatService
    from nanobot.session.manager import SessionManager
    from nanobot.utils.helpers import sync_workspace_templates

    from src.agents.tools import RunnerTools, create_tools

    if verbose:
        logging.basicConfig(level=logging.DEBUG)

    if logs:
        logging.getLogger("nanobot").setLevel(logging.DEBUG)
        logging.getLogger("src").setLevel(logging.DEBUG)
    else:
        logging.getLogger("nanobot").setLevel(logging.WARNING)
        logging.getLogger("src").setLevel(logging.WARNING)

    config = load_config()
    provider = _make_provider(config)

    context = None
    runner_tools = None
    workspace = None

    try:
        from src.core.context import AppContextFactory

        context = AppContextFactory.create()
        workspace = context.config.base_dir
        runner_tools = RunnerTools(context)
    except Exception:
        console.print("[yellow]警告: 无法初始化存储管理器[/yellow]")
        from pathlib import Path

        workspace = Path.home() / ".nanobot-runner"

    sync_workspace_templates(workspace)

    bus = MessageBus()
    session = SessionManager(bus=bus)

    agent = AgentLoop(
        bus=bus,
        provider=provider,
        workspace=workspace,
    )

    if runner_tools:
        for tool in create_tools(runner_tools):
            agent.tools.register(tool)

    channels = ChannelManager(
        workspace=workspace,
        provider=provider,
        agent=agent,
        session=session,
        bus=bus,
    )

    cron = CronService(workspace=workspace, agent=agent)

    def on_heartbeat_execute():
        console.print("[dim]心跳检测执行中...[/dim]")

    def on_heartbeat_notify(channel: str, chat_id: str, response: str):
        from nanobot.bus import OutboundMessage

        bus.publish_outbound(
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
        console.print(
            f"[green]✓[/green] 已启用通道: {', '.join(channels.enabled_channels)}"
        )
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
