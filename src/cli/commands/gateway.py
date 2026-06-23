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


async def _connect_mcp_tools_async(context: Any, agent: Any) -> dict[str, Any]:
    """异步方式连接MCP服务器工具到Agent

    在 run() 异步函数内调用，使用独立 task 执行 MCP 连接，
    隔离 anyio cancel scope 对主事件循环中其他 task 的影响。

    MCP stdio_client 使用 anyio 的 TaskGroup 和 cancel scope，
    当 stdio 传输的异步生成器清理时，cancel scope 会尝试取消
    同一 scope 下的所有 asyncio task（包括 uvicorn 等），
    导致服务意外崩溃。通过在独立 task 中执行连接，
    将 anyio cancel scope 的作用域限制在该 task 内。

    Args:
        context: 应用上下文
        agent: AgentLoop实例

    Returns:
        dict[str, Any]: MCP连接的exit_stacks映射
    """
    from src.core.tools.mcp_connector import connect_mcp_tools_from_config

    config_path = context.config.config_file

    async def _do_connect() -> dict[str, Any]:
        try:
            return await connect_mcp_tools_from_config(config_path, agent.tools)
        except NanobotRunnerError as e:
            logger.warning(f"连接MCP工具失败: {e}")
            return {"connected_servers": [], "failed_servers": [], "exit_stacks": {}}

    # 在独立 task 中执行连接，隔离 anyio cancel scope
    result = await asyncio.create_task(_do_connect())

    connected = result.get("connected_servers", [])
    failed = result.get("failed_servers", [])
    if connected:
        logger.info(f"MCP工具已连接: {connected}")
    if failed:
        logger.warning(f"MCP连接失败: {failed}")
    return result.get("exit_stacks", {})


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
            # v0.27.0: 传入 webui_enabled 标志，启用 WebSocket 通道
            adapter = RunnerProviderAdapter(context.config, webui_enabled=webui)
    except NanobotRunnerError:
        console.print("[yellow]警告: 无法初始化存储管理器[/yellow]")
        workspace = Path.home() / ".nanobot-runner"

    return context, runner_tools, workspace, adapter


def _setup_webui_branding() -> None:
    """配置自定义 WebUI 品牌路径

    通过 monkey-patch 覆盖默认的 WebUI 静态文件路径，
    优先使用项目自定义的 webui/dist 目录。
    """
    from pathlib import Path

    import nanobot.channels.manager as manager_module

    def _custom_webui_dist():
        """返回项目自定义的 WebUI dist 目录"""
        # 优先使用项目自定义的 webui 目录
        custom_dist = Path(__file__).resolve().parent.parent.parent / "webui" / "dist"
        if custom_dist.is_dir() and (custom_dist / "index.html").exists():
            return custom_dist
        # 回退到 nanobot 默认目录
        try:
            import nanobot.web as web_pkg

            default_dist = Path(web_pkg.__file__).resolve().parent / "dist"
            return default_dist if default_dist.is_dir() else None
        except ImportError:
            return None

    # 保存原始函数并替换
    manager_module._default_webui_dist = _custom_webui_dist


def _create_gateway_agent(
    bus: Any,
    provider: Any,
    agent_defaults: Any,
    workspace: Any,
    runner_tools: Any,
) -> Any:
    """创建 AgentLoop 实例并注册工具与命令

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

    webui_config = context.config.get_webui_config()
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

    return GatewayIntegration(
        workspace=workspace,
        bus=bus,
        console=console,
        data_dir=context.config.data_dir if context else None,
    )


def _register_heartbeat_cron(cron: Any) -> int:
    """注册心跳Cron任务

    v0.30.0: HeartbeatService 在 nanobot-ai 0.2.1 中已移除，
    改用 CronService 注册心跳任务。

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
                    kind="cron", expr=f"*/{hb_interval_minutes} * * * *"
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
        ws_config = context.config.get_websocket_config()
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

    ws_config = context.config.get_websocket_config()
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
        webui_config = context.config.get_webui_config()
        api_host = webui_config.get("host", "127.0.0.1")
        api_port = webui_config.get("port", 8766)
        console.print(f"  - API文档: http://{api_host}:{api_port}/api/docs")


async def _run_gateway(
    agent: Any,
    channels: Any,
    cron: Any,
    fastapi_server: Any,
    integration: Any,
    mcp_context: tuple | None,
) -> None:
    """运行Gateway服务的异步主循环

    按顺序启动各组件，使用 return_exceptions 防止 MCP cancel scope 异常级联。
    退出时按顺序优雅关闭：先停 uvicorn → 停通道 → 停心跳 → 关闭 MCP。
    """
    try:
        # 在同一事件循环内连接MCP工具，避免跨事件循环的cancel scope冲突
        if mcp_context is not None:
            await _connect_mcp_tools_async(mcp_context[0], mcp_context[1])

        await cron.start()

        # 将 uvicorn 放在独立 task 中运行，隔离 anyio cancel scope 的影响
        # MCP stdio_client 使用 anyio TaskGroup，清理时 cancel scope 会取消
        # 同一 scope 下的 asyncio task，导致 uvicorn 等服务被意外取消
        if fastapi_server is not None:
            webui_task = asyncio.create_task(fastapi_server.serve())
        else:
            webui_task = None

        # agent.run() 和 channels.start_all() 使用 return_exceptions
        # 防止 MCP cancel scope 异常级联
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
        # 按顺序优雅关闭：先停 uvicorn → 停通道 → 停心跳 → 关闭 MCP
        if fastapi_server is not None:
            fastapi_server.should_exit = True
        if webui_task is not None and not webui_task.done():
            webui_task.cancel()
        await channels.stop_all()
        integration.shutdown()
        agent.stop()
        # MCP 关闭可能产生 cancel scope 冲突，隔离异常避免影响其他清理
        try:
            await agent.close_mcp()
        except (RuntimeError, BaseExceptionGroup, asyncio.CancelledError) as e:
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

    # 4. 工作区模板同步与WebUI品牌配置
    from nanobot.utils.helpers import sync_workspace_templates

    sync_workspace_templates(workspace)
    _setup_webui_branding()

    # 5. 创建消息总线和Agent
    from nanobot.bus import MessageBus

    bus = MessageBus()
    agent = _create_gateway_agent(
        bus, provider, agent_defaults, workspace, runner_tools
    )

    # MCP工具连接移至 run() 异步函数内，避免 asyncio.run() 跨事件循环导致
    # stdio_client cancel scope 冲突 (RuntimeError: Attempted to exit cancel scope
    # in a different task than it was entered in)
    mcp_context = (context, agent) if context else None

    # 6. 创建 SessionManager 和通道管理器
    from nanobot.channels.manager import ChannelManager
    from nanobot.session.manager import SessionManager

    session_manager = SessionManager(workspace=workspace)
    get_runtime_model_name = _create_runtime_model_callback(adapter, agent)

    channels = ChannelManager(
        config=adapter._get_or_create_nanobot_config(),
        bus=bus,
        session_manager=session_manager,
        webui_runtime_model_name=get_runtime_model_name,
    )

    # 7. WebUI FastAPI 后端（--webui 标志即为启动条件）
    fastapi_server = _setup_fastapi_server(context, webui)

    # 8. Gateway集成（Cron + Hook）
    integration = _setup_gateway_integration(workspace, bus, context)
    cron = integration.setup_cron_service(auto_register_reminder=True)

    # 设置流式输出Hook
    # v0.30.0: nanobot-ai 0.2.1 中 AgentLoop 无公开 hooks 属性
    # 改用 _extra_hooks 列表直接追加
    streaming_hook = integration.setup_streaming_hook()
    if streaming_hook:
        agent._extra_hooks.append(streaming_hook)

    # 9. 心跳Cron任务（v0.30.0: 改用 CronService）
    hb_interval_minutes = _register_heartbeat_cron(cron)

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
    asyncio.run(
        _run_gateway(agent, channels, cron, fastapi_server, integration, mcp_context)
    )
