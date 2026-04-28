# 透明化相关命令
# 包含 transparency show/settings 命令

import typer

from src.cli.common import console

app = typer.Typer(help="AI透明化与可观测性命令")


@app.command()
def show(
    decision_id: str | None = typer.Option(
        None, "--decision-id", "-d", help="指定决策ID查看详情"
    ),
    detail_level: str = typer.Option(
        "brief", "--level", "-l", help="详细程度: brief/detailed"
    ),
    limit: int = typer.Option(10, "--limit", "-n", help="显示最近决策数量"),
) -> None:
    """展示AI决策透明化信息

    查看AI决策解释、数据来源、决策路径等透明化信息。
    """
    from rich.panel import Panel

    from src.core.transparency import (
        DetailLevel,
        TraceLogger,
        TransparencyDisplay,
        TransparencyEngine,
    )

    engine = TransparencyEngine()
    trace_logger = TraceLogger()
    display = TransparencyDisplay()

    if decision_id:
        decision = engine.get_decision(decision_id)
        if decision is None:
            console.print(f"[red]决策不存在: {decision_id}[/red]")
            raise typer.Exit(code=1)

        level = (
            DetailLevel.DETAILED if detail_level == "detailed" else DetailLevel.BRIEF
        )
        explanation = engine.generate_explanation(decision, level)
        panel = display.display_explanation_by_level(explanation, level)
        console.print(panel)

        if explanation.data_sources:
            table = display.display_data_sources(explanation.data_sources)
            console.print(table)

        if detail_level == "detailed" and explanation.decision_path.steps:
            mermaid = display.display_decision_path(explanation.decision_path)
            console.print(Panel(mermaid, title="决策路径", border_style="blue"))
    else:
        decision_logs = trace_logger.get_decision_logs(limit)
        if not decision_logs:
            console.print("[dim]暂无决策记录[/dim]")
            return

        console.print(f"[bold]最近 {len(decision_logs)} 条决策记录[/bold]\n")

        for entry in reversed(decision_logs):
            ts = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            decision_type = entry.context.get("decision_type", "unknown")
            confidence = entry.context.get("confidence", 0)
            tools = entry.context.get("tools_used", [])

            console.print(
                f"[cyan]{ts}[/cyan] | "
                f"类型: [green]{decision_type}[/green] | "
                f"置信度: [yellow]{confidence:.0%}[/yellow] | "
                f"工具: {', '.join(tools) if tools else '无'}"
            )


@app.command()
def settings(
    detail_level: str | None = typer.Option(
        None, "--level", "-l", help="设置默认详细程度: off/brief/detailed"
    ),
    show_data_sources: bool | None = typer.Option(
        None, "--data-sources", help="是否展示数据来源"
    ),
    reset: bool = typer.Option(False, "--reset", help="重置为默认设置"),
) -> None:
    """查看或修改透明化设置

    管理AI决策透明化的展示级别和可观测性配置。
    """
    from src.core.transparency import DetailLevel, TransparencySettings

    current = TransparencySettings.default()

    if reset:
        current = TransparencySettings.default()
        console.print("[green]✓ 已重置为默认设置[/green]")
    elif detail_level is not None or show_data_sources is not None:
        if detail_level is not None:
            valid_levels = {"off", "brief", "detailed"}
            if detail_level not in valid_levels:
                console.print(f"[red]无效的详细程度: {detail_level}[/red]")
                console.print(f"可选值: {', '.join(valid_levels)}")
                raise typer.Exit(code=1)
            level = DetailLevel(detail_level)
            current = TransparencySettings(
                detail_level=level,
                show_data_sources=show_data_sources
                if show_data_sources is not None
                else current.show_data_sources,
            )

        console.print("[green]✓ 设置已更新[/green]")

    console.print("\n[bold]透明化设置[/bold]")
    console.print(f"  详细程度: [cyan]{current.detail_level.value}[/cyan]")
    console.print(
        f"  展示数据来源: [cyan]{'是' if current.show_data_sources else '否'}[/cyan]"
    )


@app.command()
def dashboard() -> None:
    """展示AI状态洞察看板

    显示AI进化状态、建议质量、工具可靠性等洞察信息。
    """
    from src.core.transparency import ObservabilityManager, TraceLogger
    from src.core.transparency.ai_status_dashboard import AIStatusDashboard

    manager = ObservabilityManager()
    trace_logger = TraceLogger()
    dashboard_ui = AIStatusDashboard(manager=manager, trace_logger=trace_logger)

    layout = dashboard_ui.render()
    console.print(layout)

    data = dashboard_ui.get_dashboard_data()
    console.print(f"\n[dim]进化等级: {data['evolution']['level']}[/dim]")
    console.print(f"[dim]建议质量: {data['suggestion_quality']['score']:.1f}/10[/dim]")


@app.command()
def insight() -> None:
    """展示训练洞察报告

    显示训练模式分析、恢复状态趋势、AI建议效果等洞察信息。
    """
    from src.core.transparency import ObservabilityManager, TraceLogger
    from src.core.transparency.training_insight_report import TrainingInsightReport

    manager = ObservabilityManager()
    trace_logger = TraceLogger()
    report = TrainingInsightReport(manager=manager, trace_logger=trace_logger)

    panel = report.render_report()
    console.print(panel)
