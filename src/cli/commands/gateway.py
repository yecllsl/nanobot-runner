# Gateway 相关命令
# 包含 gateway start 命令

import asyncio
import contextlib
import logging
from typing import Any

import typer

from src.cli.common import console
from src.core.base.logger import get_logger

logger = get_logger(__name__)

app = typer.Typer(help="Gateway 服务命令")


def _connect_mcp_tools_sync(context: Any, agent: Any) -> dict[str, Any]:
    """同步方式连接MCP服务器工具到Agent

    在Gateway同步启动流程中调用，通过asyncio.run执行异步连接。

    Args:
        context: 应用上下文
        agent: AgentLoop实例

    Returns:
        dict[str, Any]: MCP连接的exit_stacks映射
    """
    from src.core.tools.mcp_connector import connect_mcp_tools_from_config

    config_path = context.config.config_file
    try:
        result = asyncio.run(connect_mcp_tools_from_config(config_path, agent.tools))
        connected = result.get("connected_servers", [])
        failed = result.get("failed_servers", [])
        if connected:
            logger.info(f"MCP工具已连接: {connected}")
        if failed:
            logger.warning(f"MCP连接失败: {failed}")
        return result.get("exit_stacks", {})
    except Exception as e:
        logger.warning(f"连接MCP工具失败: {e}")
        return {}


def _format_stats(data: dict) -> str:
    """格式化训练统计数据"""
    if "message" in data:
        return data["message"]

    total_runs = data.get("total_runs", 0)
    total_distance = data.get("total_distance", 0.0)
    total_duration = data.get("total_duration", 0.0)
    avg_distance = data.get("avg_distance", 0.0)
    avg_duration = data.get("avg_duration", 0.0)

    hours = int(total_duration // 3600)
    minutes = int((total_duration % 3600) // 60)

    avg_pace = avg_duration / avg_distance / 60 if avg_distance > 0 else 0
    pace_min = int(avg_pace)
    pace_sec = int((avg_pace - pace_min) * 60)

    return (
        f"📊 训练统计\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"🏃 总跑步次数: {total_runs} 次\n"
        f"📏 总距离: {total_distance:.2f} km\n"
        f"⏱️ 总时长: {hours}小时{minutes}分钟\n"
        f"📐 平均距离: {avg_distance:.2f} km\n"
        f"⚡ 平均配速: {pace_min}'{pace_sec:02d}\"/km"
    )


def _format_recent(runs: list[dict]) -> str:
    """格式化最近训练记录"""
    if not runs:
        return "暂无跑步记录"

    lines = ["📋 最近训练记录", "━━━━━━━━━━━━━━━━"]
    for i, run in enumerate(runs, 1):
        date = run.get("timestamp", "N/A")[:10]
        distance = run.get("distance_km", 0)
        duration = run.get("duration", "N/A")
        avg_hr = run.get("avg_hr", "-")

        lines.append(f"{i}. {date} | {distance:.2f}km | {duration} | HR:{avg_hr}")

    return "\n".join(lines)


def _format_vdot(trend: list[dict]) -> str:
    """格式化VDOT趋势"""
    if not trend:
        return "暂无VDOT数据"

    lines = ["📈 VDOT趋势", "━━━━━━━━━━━━━━━━"]
    for item in trend:
        date = item.get("date", "N/A")
        distance = item.get("distance_km", 0)
        duration = item.get("duration", "N/A")
        vdot = item.get("vdot", 0)

        lines.append(f"{date} | {distance:.2f}km | {duration} | VDOT:{vdot:.1f}")

    return "\n".join(lines)


def _format_hr_drift(data: dict) -> str:
    """格式化心率漂移分析"""
    if "error" in data:
        return data["error"]

    correlation = data.get("correlation", 0)
    is_drift = data.get("is_hr_drift", False)
    avg_hr = data.get("avg_hr", 0)
    hr_range = data.get("hr_range", [0, 0])

    status = "⚠️ 存在心率漂移" if is_drift else "✅ 心率稳定"
    drift_indicator = (
        "🔴" if correlation < -0.7 else "🟡" if correlation < -0.5 else "🟢"
    )

    return (
        f"💓 心率漂移分析\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"{drift_indicator} {status}\n"
        f"📊 相关性: {correlation:.3f}\n"
        f"❤️ 平均心率: {avg_hr:.0f} bpm\n"
        f"📈 心率范围: {hr_range[0]:.0f} - {hr_range[1]:.0f} bpm"
    )


def _format_training_load(data: dict) -> str:
    """格式化训练负荷"""
    if "error" in data:
        return data["error"]

    atl = data.get("atl", 0)
    ctl = data.get("ctl", 0)
    tsb = data.get("tsb", 0)

    status = "💪 体能充沛" if tsb > 10 else "⚖️ 训练平衡" if tsb > -10 else "😴 需要休息"

    return (
        f"🏋️ 训练负荷\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"🔥 ATL (急性负荷): {atl:.1f}\n"
        f"💪 CTL (慢性负荷): {ctl:.1f}\n"
        f"⚖️ TSB (训练平衡): {tsb:+.1f}\n"
        f"{status}"
    )


def _register_runner_commands(agent, runner_tools):
    """注册跑步业务命令到 CommandRouter，直接执行不走 LLM"""
    from nanobot.bus.events import OutboundMessage
    from nanobot.command.router import CommandContext

    async def cmd_stats(ctx: CommandContext) -> OutboundMessage:
        data = runner_tools.get_running_stats()
        return OutboundMessage(
            channel=ctx.msg.channel,
            chat_id=ctx.msg.chat_id,
            content=_format_stats(data),
            metadata={**dict(ctx.msg.metadata or {}), "render_as": "text"},
        )

    async def cmd_recent(ctx: CommandContext) -> OutboundMessage:
        args = ctx.args.strip()
        limit = 10
        if args:
            with contextlib.suppress(ValueError):
                limit = int(args.split()[0])
        data = runner_tools.get_recent_runs(limit)
        return OutboundMessage(
            channel=ctx.msg.channel,
            chat_id=ctx.msg.chat_id,
            content=_format_recent(data),
            metadata={**dict(ctx.msg.metadata or {}), "render_as": "text"},
        )

    async def cmd_vdot(ctx: CommandContext) -> OutboundMessage:
        args = ctx.args.strip()
        limit = 20
        if args:
            with contextlib.suppress(ValueError):
                limit = int(args.split()[0])
        data = runner_tools.get_vdot_trend(limit)
        return OutboundMessage(
            channel=ctx.msg.channel,
            chat_id=ctx.msg.chat_id,
            content=_format_vdot(data),
            metadata={**dict(ctx.msg.metadata or {}), "render_as": "text"},
        )

    async def cmd_hr_drift(ctx: CommandContext) -> OutboundMessage:
        args = ctx.args.strip()
        run_id = args.split()[0] if args else None
        data = runner_tools.get_hr_drift_analysis(run_id)
        return OutboundMessage(
            channel=ctx.msg.channel,
            chat_id=ctx.msg.chat_id,
            content=_format_hr_drift(data),
            metadata={**dict(ctx.msg.metadata or {}), "render_as": "text"},
        )

    async def cmd_load(ctx: CommandContext) -> OutboundMessage:
        args = ctx.args.strip()
        days = 42
        if args:
            with contextlib.suppress(ValueError):
                days = int(args.split()[0])
        data = runner_tools.get_training_load(days)
        return OutboundMessage(
            channel=ctx.msg.channel,
            chat_id=ctx.msg.chat_id,
            content=_format_training_load(data),
            metadata={**dict(ctx.msg.metadata or {}), "render_as": "text"},
        )

    agent.commands.exact("/stats", cmd_stats)
    agent.commands.exact("/recent", cmd_recent)
    agent.commands.prefix("/recent ", cmd_recent)
    agent.commands.exact("/vd", cmd_vdot)
    agent.commands.prefix("/vd ", cmd_vdot)
    agent.commands.exact("/vdot", cmd_vdot)
    agent.commands.prefix("/vdot ", cmd_vdot)
    agent.commands.exact("/hr_drift", cmd_hr_drift)
    agent.commands.prefix("/hr_drift ", cmd_hr_drift)
    agent.commands.exact("/load", cmd_load)
    agent.commands.prefix("/load ", cmd_load)


@app.command()
def start(
    port: int = typer.Option(18790, "--port", "-p", help="Gateway端口"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="详细输出"),
    logs: bool = typer.Option(False, "--logs", "-l", help="启用日志输出"),
) -> None:
    """
    启动飞书机器人Gateway服务

    启动后可通过飞书App与"Nanobot-ai助手"机器人交互：

    命令示例（直接执行，响应快）:
        /stats              # 查看训练统计
        /recent 5           # 查看最近5次训练
        /vd                 # 查看VDOT趋势
        /hr_drift           # 查看心率漂移分析
        /load               # 查看训练负荷
        /help               # 显示帮助

    自然语言示例（需要LLM理解，响应较慢）:
        我最近跑得怎么样？
        给我一个训练建议
        我的VDOT是多少？
    """
    from src.agents.tools import RunnerTools, create_tools
    from src.core.base.context import get_context
    from src.core.provider_adapter import RunnerProviderAdapter

    if verbose:
        logging.basicConfig(level=logging.DEBUG)

    if logs:
        logging.getLogger("nanobot").setLevel(logging.DEBUG)
        logging.getLogger("src").setLevel(logging.DEBUG)
    else:
        logging.getLogger("nanobot").setLevel(logging.WARNING)
        logging.getLogger("src").setLevel(logging.WARNING)

    context = None
    runner_tools = None
    workspace = None
    adapter = None

    try:
        context = get_context()
        workspace = context.config.base_dir
        runner_tools = RunnerTools(context)

        if context.config.has_llm_config():
            adapter = RunnerProviderAdapter(context.config)
    except Exception:
        console.print("[yellow]警告: 无法初始化存储管理器[/yellow]")
        from pathlib import Path

        workspace = Path.home() / ".nanobot-runner"

    if not adapter or not adapter.is_available():
        console.print("[red]LLM配置缺失，Gateway服务需要LLM支持[/red]")
        console.print("[yellow]请先运行: nanobotrun init[/yellow]")
        raise typer.Exit(1)

    provider = adapter.get_provider_instance()
    agent_defaults = adapter.get_agent_defaults()

    from nanobot.agent import AgentLoop
    from nanobot.bus import MessageBus
    from nanobot.channels.manager import ChannelManager
    from nanobot.heartbeat.service import HeartbeatService
    from nanobot.utils.helpers import sync_workspace_templates

    sync_workspace_templates(workspace)

    bus = MessageBus()

    agent = AgentLoop(
        bus=bus,
        provider=provider,
        workspace=workspace,
        model=agent_defaults.model,
        max_iterations=agent_defaults.max_tool_iterations,
        context_window_tokens=agent_defaults.context_window_tokens,
        context_block_limit=agent_defaults.context_block_limit,
        max_tool_result_chars=agent_defaults.max_tool_result_chars,
    )

    if runner_tools:
        for tool in create_tools(runner_tools):
            agent.tools.register(tool)
        _register_runner_commands(agent, runner_tools)

    _connect_mcp_tools_sync(context, agent)

    channels = ChannelManager(config=adapter._get_or_create_nanobot_config(), bus=bus)

    # v0.17.0: 使用 GatewayIntegration 集成 Cron + Hook
    from src.core.plan.gateway_integration import GatewayIntegration

    integration = GatewayIntegration(
        workspace=workspace,
        bus=bus,
        console=console,
        data_dir=context.config.data_dir if context else None,
    )

    # 设置Cron服务（包含训练提醒）
    cron = integration.setup_cron_service(auto_register_reminder=True)

    # 设置流式输出Hook
    streaming_hook = integration.setup_streaming_hook()
    if streaming_hook and hasattr(agent, "hooks"):
        agent.hooks.register(streaming_hook)

    def on_heartbeat_execute():
        console.print("[dim]心跳检测执行中...[/dim]")

    def on_heartbeat_notify(channel: str, chat_id: str, response: str):
        from nanobot.bus import OutboundMessage

        bus.publish_outbound(
            OutboundMessage(channel=channel, chat_id=chat_id, content=response)
        )

    hb_interval_s = 300
    hb_enabled = True
    heartbeat = HeartbeatService(
        workspace=workspace,
        provider=provider,
        model=agent.model,
        on_execute=on_heartbeat_execute,
        on_notify=on_heartbeat_notify,
        interval_s=hb_interval_s,
        enabled=hb_enabled,
    )

    if channels.enabled_channels:
        console.print(
            f"[green]✓[/green] 已启用通道: {', '.join(channels.enabled_channels)}"
        )
    else:
        console.print("[yellow]警告: 未启用任何通道[/yellow]")

    # v0.17.0: 显示Cron和提醒状态
    cron_status_info = integration.get_cron_status()
    if cron_status_info.get("enabled"):
        console.print(
            f"[green]✓[/green] 定时任务: {cron_status_info.get('jobs_count', 0)} 个"
        )
        if cron_status_info.get("reminder_job"):
            reminder = cron_status_info["reminder_job"]
            console.print(f"[green]✓[/green] 训练提醒: {reminder['cron']}")
        elif cron_status_info.get("reminder_enabled"):
            console.print("[yellow]! 训练提醒已启用但未注册任务[/yellow]")
    else:
        console.print("[yellow]! Cron服务未启用[/yellow]")

    console.print(f"[green]✓[/green] 心跳检测: 每 {hb_interval_s} 秒")
    console.print()
    console.print("[bold cyan]飞书机器人交互命令：[/bold cyan]")
    console.print("  - /stats - 查看训练统计")
    console.print("  - /recent [数量] - 查看最近训练")
    console.print("  - /vd - 查看VDOT趋势")
    console.print("  - /hr_drift - 查看心率漂移")
    console.print("  - /load - 查看训练负荷")
    console.print("  - /help - 显示帮助")
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
            integration.shutdown()  # v0.17.0: 使用集成器关闭
            agent.stop()
            await channels.stop_all()

    asyncio.run(run())
