# Gateway 相关命令
# 包含 gateway start 命令

import asyncio
import contextlib
import logging
from typing import Any

import typer

from src.cli.common import console
from src.core.base.exceptions import NanobotRunnerError
from src.core.base.logger import get_logger

logger = get_logger(__name__)

app = typer.Typer(help="Gateway 服务命令")


# ponytail: 全局 asyncio 异常处理器，防止 WebSocket 客户端断开等预期内异常级联崩溃
def _asyncio_exception_handler(
    loop: asyncio.AbstractEventLoop, context: dict[str, Any]
) -> None:
    """全局 asyncio 异常处理器

    仅记录异常日志，不中断事件循环。避免 WebSocket 客户端连接断开时
    (ConnectionClosedError) 级联崩溃整个 Gateway 服务。
    """
    exc = context.get("exception")
    message = context.get("message", "")
    if exc and "ConnectionClosedError" in type(exc).__name__:
        logger.debug(f"WebSocket 客户端连接断开（预期内）: {exc}")
    else:
        logger.warning(f"asyncio 异常: {message}", exc_info=exc)


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

    async def cmd_restart(ctx: CommandContext) -> OutboundMessage:
        """重启 Runner Gateway 服务

        覆盖 nanobot 默认的 /restart 命令，使用正确的启动命令。
        """
        import asyncio
        import os
        import sys

        from nanobot.utils.restart import set_restart_notice_to_env

        # 保存重启通知，以便重启后恢复会话
        set_restart_notice_to_env(
            channel=ctx.msg.channel,
            chat_id=ctx.msg.chat_id,
            metadata=dict(ctx.msg.metadata or {}),
        )

        async def _do_restart():
            await asyncio.sleep(1)
            # Runner 的正确启动命令：uv run nanobotrun gateway start --webui
            # 重启时保留原有参数
            new_argv = [
                sys.executable,
                "-m",
                "src.cli.app",
                "gateway",
                "start",
                "--webui",
            ]
            os.execv(sys.executable, new_argv)

        asyncio.create_task(_do_restart())
        return OutboundMessage(
            channel=ctx.msg.channel,
            chat_id=ctx.msg.chat_id,
            content="正在重启 Runner Gateway...",
            metadata={**dict(ctx.msg.metadata or {}), "render_as": "text"},
        )

    # 注册业务命令
    agent.commands.exact("/stats", cmd_stats)
    agent.commands.prefix("/recent ", cmd_recent)
    agent.commands.exact("/vd", cmd_vdot)
    agent.commands.prefix("/vd ", cmd_vdot)
    agent.commands.exact("/vdot", cmd_vdot)
    agent.commands.prefix("/vdot ", cmd_vdot)
    agent.commands.exact("/hr_drift", cmd_hr_drift)
    agent.commands.prefix("/hr_drift ", cmd_hr_drift)
    agent.commands.exact("/load", cmd_load)
    agent.commands.prefix("/load ", cmd_load)

    # 注册重启命令（覆盖 nanobot 默认）
    agent.commands.priority("/restart", cmd_restart)


def _setup_gateway_logging(verbose: bool, logs: bool) -> None:
    """配置Gateway日志级别"""
    if verbose:
        logging.basicConfig(level=logging.DEBUG)

    if logs:
        logging.getLogger("nanobot").setLevel(logging.DEBUG)
        logging.getLogger("src").setLevel(logging.DEBUG)
    else:
        logging.getLogger("nanobot").setLevel(logging.WARNING)
        logging.getLogger("src").setLevel(logging.WARNING)


def _init_gateway_context(
    webui: bool,
) -> tuple[Any, Any, Any, Any]:
    """初始化应用上下文、RunnerTools和Provider适配器

    Returns:
        (context, runner_tools, workspace, adapter) 元组
    """
    from pathlib import Path

    from src.agents.tools import RunnerTools
    from src.core.base.context import get_context
    from src.core.provider_adapter import RunnerProviderAdapter

    context = None
    runner_tools = None
    workspace = None
    adapter = None

    try:
        context = get_context()
        workspace = context.config.base_dir
        runner_tools = RunnerTools(context)

        if context.config.has_llm_config():
            adapter = RunnerProviderAdapter(context.config, webui_enabled=webui)
            # v0.32.0: 直接指向用户维护的 nanobot_config.json，
            # 不再调用 save_nanobot_config() 自动生成
            from nanobot.config.loader import set_config_path

            nanobot_config_path = context.config.get_nanobot_config_path()
            if nanobot_config_path.exists():
                set_config_path(nanobot_config_path)
    except NanobotRunnerError:
        console.print("[yellow]警告: 无法初始化存储管理器[/yellow]")
        workspace = Path.home() / ".nanobot-runner"

    return context, runner_tools, workspace, adapter


def _create_gateway_agent(
    bus: Any,
    provider: Any,
    agent_defaults: Any,
    workspace: Any,
    runner_tools: Any,
    mcp_servers: dict[str, Any] | None = None,
) -> Any:
    """创建 AgentLoop 实例并注册工具与命令

    Args:
        mcp_servers: MCP服务器配置，传入后由 AgentLoopAdapter.connect_mcp() 统一连接，
            确保 connect/close 在同一 task，避免 anyio cancel scope 跨 task 报错

    Returns:
        AgentLoop 实例
    """
    from nanobot.agent import AgentLoop

    agent = AgentLoop(
        bus=bus,
        provider=provider,
        workspace=workspace,
        model=agent_defaults.model,
        max_iterations=agent_defaults.max_tool_iterations,
        context_window_tokens=agent_defaults.context_window_tokens,
        context_block_limit=agent_defaults.context_block_limit,
        max_tool_result_chars=agent_defaults.max_tool_result_chars,
        timezone=getattr(agent_defaults, "timezone", None),
        mcp_servers=mcp_servers or {},
    )

    if runner_tools:
        from src.agents.tools import create_tools

        for tool in create_tools(runner_tools):
            agent.tools.register(tool)
        _register_runner_commands(agent, runner_tools)

    return agent


def _create_runtime_model_callback(adapter: Any, agent: Any) -> Any:
    """创建运行时模型名称回调函数

    使 WebUI 显示实际使用的模型名称。获取失败时静默回退到 agent.model，
    属信息性操作，不阻塞主流程。

    Returns:
        返回当前实际使用的模型名称的回调函数
    """

    def get_runtime_model_name():
        """返回当前实际使用的模型名称"""
        try:
            # 优先从adapter获取实际配置的模型
            if adapter and hasattr(adapter, "config"):
                return adapter.config.llm_model
        except Exception as e:
            # 信息性操作，失败时回退到agent.model，不阻塞主流程
            logger.debug(f"获取运行时模型名称失败，回退到agent.model: {e}")
        # 回退到agent的模型
        return agent.model if agent else None

    return get_runtime_model_name


def _setup_fastapi_server(context: Any, webui: bool) -> Any:
    """创建 WebUI FastAPI 后端服务器

    Returns:
        FastAPI 服务器实例，未启用时返回 None
    """
    if not webui or context is None:
        return None

    # v0.32.0: WebUI REST API 配置使用默认值（nanobot_config.json 无 webui 节）
    webui_config = {
        "host": "127.0.0.1",
        "port": 8766,
    }
    from src.core.webui.app import create_server

    fastapi_server = create_server(context)
    api_host = webui_config.get("host", "127.0.0.1")
    api_port = webui_config.get("port", 8766)
    console.print(
        f"[green][OK][/green] WebUI API: http://{api_host}:{api_port}/api/docs"
    )
    return fastapi_server


def _setup_gateway_integration(workspace: Any, bus: Any, context: Any) -> Any:
    """创建并返回 GatewayIntegration 实例"""
    from src.core.plan.gateway_integration import GatewayIntegration

    # 读取配置文件中的时区，传递给 Cron 任务，避免回退到系统时区（UTC）
    timezone = context.config.get("timezone") if context else None

    return GatewayIntegration(
        workspace=workspace,
        bus=bus,
        console=console,
        data_dir=context.config.data_dir if context else None,
        timezone=timezone,
    )


def _register_heartbeat_cron(cron: Any, timezone: str | None = None) -> int:
    """注册心跳Cron任务

    v0.30.0: HeartbeatService 在 nanobot-ai 0.2.1 中已移除，
    改用 CronService 注册心跳任务。

    Args:
        cron: CronService 实例
        timezone: 配置文件中的时区（如 "Asia/Shanghai"），传入后 Cron 任务按此时区调度

    Returns:
        心跳间隔分钟数
    """
    from nanobot.cron.types import CronSchedule

    hb_interval_s = 300
    hb_enabled = True
    hb_interval_minutes = max(1, hb_interval_s // 60)  # Cron 最小粒度为分钟

    if hb_enabled:
        try:
            cron.add_job(
                name="heartbeat",
                schedule=CronSchedule(
                    kind="cron",
                    expr=f"*/{hb_interval_minutes} * * * *",
                    tz=timezone,
                ),
                message="心跳检测",
            )
            logger.info(f"心跳Cron任务已注册: 每 {hb_interval_minutes} 分钟")
        except Exception as e:
            logger.warning(f"注册心跳Cron任务失败: {e}")

    return hb_interval_minutes


def _display_channel_status(channels: Any, context: Any) -> None:
    """显示通道启用状态和WebUI访问信息"""
    if not channels.enabled_channels:
        console.print("[yellow]警告: 未启用任何通道[/yellow]")
        return

    console.print(
        f"[green][OK][/green] 已启用通道: {', '.join(channels.enabled_channels)}"
    )
    # v0.27.0: WebSocket 通道启用时，显示 WebUI 访问地址与安全提示
    if "websocket" in channels.enabled_channels and context is not None:
        ws_config = (
            context.config.load_nanobot_config()
            .get("channels", {})
            .get("websocket", {})
        )
        ws_host = ws_config.get("host", "127.0.0.1")
        ws_port = ws_config.get("port", 8765)
        console.print(f"[green][OK][/green] WebUI 访问地址: http://{ws_host}:{ws_port}")
        # Token 获取方式提示
        if ws_config.get("websocket_requires_token", True):
            token_path = ws_config.get("token_issue_path") or "/token"
            console.print(
                f"[dim]  Token获取: curl http://{ws_host}:{ws_port}{token_path}[/dim]"
            )
        # 非本地绑定时显示安全警告
        if ws_host not in ("127.0.0.1", "localhost"):
            console.print(
                "[yellow]⚠ 安全警告: WebUI 绑定到非本地地址，请确保网络环境安全[/yellow]"
            )
            console.print(
                "[dim]  建议设置 websocket_requires_token=true 并配置强密钥[/dim]"
            )


def _display_cron_status(integration: Any) -> None:
    """显示Cron服务和训练提醒状态"""
    cron_status_info = integration.get_cron_status()
    if cron_status_info.get("enabled"):
        console.print(
            f"[green][OK][/green] 定时任务: {cron_status_info.get('jobs_count', 0)} 个"
        )
        if cron_status_info.get("reminder_job"):
            reminder = cron_status_info["reminder_job"]
            console.print(f"[green][OK][/green] 训练提醒: {reminder['cron']}")
        elif cron_status_info.get("reminder_enabled"):
            console.print("[yellow]! 训练提醒已启用但未注册任务[/yellow]")
    else:
        console.print("[yellow]! Cron服务未启用[/yellow]")


def _display_gateway_commands_info() -> None:
    """显示飞书机器人交互命令帮助"""
    console.print()
    console.print("[bold cyan]飞书机器人交互命令：[/bold cyan]")
    console.print("  - /stats - 查看训练统计")
    console.print("  - /recent [数量] - 查看最近训练")
    console.print("  - /vd - 查看VDOT趋势")
    console.print("  - /hr_drift - 查看心率漂移")
    console.print("  - /load - 查看训练负荷")
    console.print("  - /help - 显示帮助")


def _display_webui_info(
    webui: bool, channels: Any, context: Any, fastapi_server: Any
) -> None:
    """显示WebUI交互信息区块（仅在 WebSocket 通道启用时显示）"""
    if (
        not webui
        or not channels.enabled_channels
        or "websocket" not in channels.enabled_channels
        or context is None
    ):
        return

    ws_config = (
        context.config.load_nanobot_config().get("channels", {}).get("websocket", {})
    )
    ws_host = ws_config.get("host", "127.0.0.1")
    ws_port = ws_config.get("port", 8765)
    token_path = ws_config.get("token_issue_path") or "/token"
    console.print()
    console.print("[bold cyan]WebUI 交互：[/bold cyan]")
    console.print(f"  - 浏览器访问: http://{ws_host}:{ws_port}")
    if ws_config.get("websocket_requires_token", True):
        console.print(f"  - 获取Token: curl http://{ws_host}:{ws_port}{token_path}")

    # v0.28.0: WebUI API 文档
    if fastapi_server is not None:
        webui_config = {"host": "127.0.0.1", "port": 8766}
        api_host = webui_config.get("host", "127.0.0.1")
        api_port = webui_config.get("port", 8766)
        console.print(f"  - API文档: http://{api_host}:{api_port}/api/docs")


async def _run_gateway(
    agent: Any,
    channels: Any,
    cron: Any,
    fastapi_server: Any,
    integration: Any,
    mcp_context: Any | None,
    agent_adapter: Any,
) -> None:
    """运行Gateway服务的异步主循环

    MCP 连接通过 agent_adapter 封装私有 API，断开通过 agent.close_mcp()，
    均在同一 task 内完成，避免 anyio cancel scope 跨 task 报错。
    退出时按顺序优雅关闭：uvicorn → 通道 → 心跳 → MCP。
    """
    try:
        # 通过 agent_adapter.connect_mcp() 连接，确保与 close_mcp() 在同一 task
        if mcp_context is not None:
            await agent_adapter.connect_mcp()
            mcp_connected = list(agent_adapter.mcp_stacks.keys())
            if mcp_connected:
                logger.info(f"MCP工具已连接: {mcp_connected}")

        await cron.start()

        if fastapi_server is not None:
            webui_task = asyncio.create_task(fastapi_server.serve())
        else:
            webui_task = None

        results = await asyncio.gather(
            agent.run(),
            channels.start_all(),
            return_exceptions=True,
        )
        for i, r in enumerate(results):
            if isinstance(r, Exception) and not isinstance(r, KeyboardInterrupt):
                logger.warning(f"服务任务异常退出: {r}")
    except KeyboardInterrupt:
        console.print("\n[yellow]正在关闭...[/yellow]")
    finally:
        # 按顺序优雅关闭：uvicorn → 通道 → 心跳 → MCP
        if fastapi_server is not None:
            fastapi_server.should_exit = True
        if webui_task is not None and not webui_task.done():
            webui_task.cancel()
        await channels.stop_all()
        integration.shutdown()
        agent.stop()
        # MCP 关闭加超时，防止 anyio cancel scope 清理卡住
        try:
            await asyncio.wait_for(agent.close_mcp(), timeout=5.0)
        except (
            TimeoutError,
            RuntimeError,
            BaseExceptionGroup,
            asyncio.CancelledError,
        ) as e:
            logger.debug(f"MCP关闭时异常（可忽略）: {e}")


@app.command()
def start(
    port: int = typer.Option(18790, "--port", "-p", help="Gateway端口"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="详细输出"),
    logs: bool = typer.Option(False, "--logs", "-l", help="启用日志输出"),
    webui: bool = typer.Option(False, "--webui", help="启用WebUI（WebSocket通道）"),
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

    WebUI模式:
        使用 --webui 标志启用WebSocket通道，可通过浏览器访问WebUI界面。
    """
    # 1. 日志配置
    _setup_gateway_logging(verbose, logs)

    # 2. 上下文初始化
    context, runner_tools, workspace, adapter = _init_gateway_context(webui)

    # 3. LLM配置检查
    if not adapter or not adapter.is_available():
        console.print("[red]LLM配置缺失，Gateway服务需要LLM支持[/red]")
        console.print("[yellow]请先运行: nanobotrun init[/yellow]")
        raise typer.Exit(1)

    provider = adapter.get_provider_instance()
    agent_defaults = adapter.get_agent_defaults()

    # 4. 工作区模板同步
    from nanobot.utils.helpers import sync_workspace_templates

    sync_workspace_templates(workspace)

    # 5. 创建消息总线和Agent
    from nanobot.bus import MessageBus

    bus = MessageBus()

    # 加载 MCP 配置，传入 AgentLoop 由 AgentLoopAdapter 统一连接
    # 确保 connect/close 在同一 task，避免 anyio cancel scope 跨 task 报错
    mcp_servers: dict[str, Any] = {}
    if context:
        from src.core.tools.mcp_connector import load_mcp_servers_config

        mcp_servers = load_mcp_servers_config(context.config.get_nanobot_config_path())

    agent = _create_gateway_agent(
        bus, provider, agent_defaults, workspace, runner_tools, mcp_servers
    )

    # v0.32.0: 通过 AgentLoopAdapter 封装 AgentLoop 私有 API，隔离 nanobot 版本变更风险
    from src.core.agent_loop_adapter import AgentLoopAdapter

    agent_adapter = AgentLoopAdapter(agent)

    # MCP 连接/断开均在 _run_gateway 内通过 agent_adapter 完成
    mcp_context = agent if mcp_servers else None

    # 6. 创建 SessionManager 和通道管理器
    from nanobot.channels.manager import ChannelManager
    from nanobot.session.manager import SessionManager

    session_manager = SessionManager(workspace=workspace)
    get_runtime_model_name = _create_runtime_model_callback(adapter, agent)

    # v0.32.0: ChannelManager 直接从 nanobot_config.json 加载 Config 对象
    from nanobot.config.loader import load_config as load_nanobot_config_obj

    nanobot_config_path = context.config.get_nanobot_config_path()
    try:
        nanobot_cfg = load_nanobot_config_obj(nanobot_config_path)
    except ValueError as e:
        console.print(f"[red]错误: nanobot_config.json 格式无效: {e}[/red]")
        raise typer.Exit(1)
    channels = ChannelManager(
        config=nanobot_cfg,
        bus=bus,
        session_manager=session_manager,
        webui_runtime_model_name=get_runtime_model_name,
    )

    # 7. WebUI FastAPI 后端（--webui 标志即为启动条件）
    fastapi_server = _setup_fastapi_server(context, webui)

    # 8. Gateway集成（Cron + Hook）
    integration = _setup_gateway_integration(workspace, bus, context)
    cron = integration.setup_cron_service(auto_register_reminder=True)

    # 设置流式输出Hook（通过 AgentLoopAdapter 封装私有 API）
    streaming_hook = integration.setup_streaming_hook()
    if streaming_hook:
        agent_adapter.add_hook(streaming_hook)

    # 9. 心跳Cron任务（v0.30.0: 改用 CronService）
    hb_timezone = context.config.get("timezone") if context else None
    hb_interval_minutes = _register_heartbeat_cron(cron, timezone=hb_timezone)

    # 10. 显示启动状态信息
    _display_channel_status(channels, context)
    _display_cron_status(integration)
    console.print(
        f"[green][OK][/green] 心跳检测: 每 {hb_interval_minutes} 分钟 (CronService)"
    )
    _display_gateway_commands_info()
    _display_webui_info(webui, channels, context, fastapi_server)

    console.print()
    console.print("[bold green]Gateway 服务已启动，按 Ctrl+C 停止[/bold green]")

    # 11. 运行Gateway服务
    # 设置全局 asyncio 异常处理器，防止 WebSocket 客户端断开等异常级联崩溃
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.set_exception_handler(_asyncio_exception_handler)
    try:
        loop.run_until_complete(
            _run_gateway(
                agent,
                channels,
                cron,
                fastapi_server,
                integration,
                mcp_context,
                agent_adapter,
            )
        )
    finally:
        loop.close()
