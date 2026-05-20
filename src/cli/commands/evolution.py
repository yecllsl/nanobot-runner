# 决策追踪CLI命令组
# 提供决策历史查询、反馈记录、精度统计、忠实度统计、状态查看等命令

from __future__ import annotations

import typer
from rich.panel import Panel
from rich.table import Table

from src.cli.common import CLIError, console, print_error
from src.cli.handlers.evolution_handler import EvolutionHandler
from src.core.base.exceptions import NanobotRunnerError

app = typer.Typer(help="决策追踪命令", no_args_is_help=True)


@app.command(name="history")
def get_history(
    start_date: str = typer.Option("", "--start", "-s", help="起始日期 (YYYY-MM-DD)"),
    end_date: str = typer.Option("", "--end", "-e", help="结束日期 (YYYY-MM-DD)"),
    decision_type: str = typer.Option(
        "",
        "--type",
        "-t",
        help="决策类型过滤 (training_advice/plan_adjustment/recovery_suggestion/weather_advice/data_query/general)",
    ),
) -> None:
    """查看决策历史记录

    按时间范围和决策类型查询AI决策历史，以表格形式展示。

    Examples:
        nanobotrun evolution history
        nanobotrun evolution history --start 2024-01-01 --end 2024-12-31
        nanobotrun evolution history --type training_advice
    """
    try:
        handler = EvolutionHandler()
        result = handler.get_history(
            start_date=start_date or None,
            end_date=end_date or None,
            decision_type=decision_type or None,
        )

        if not result:
            console.print("[yellow]暂无决策历史记录[/yellow]")
            return

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("决策ID", width=20)
        table.add_column("时间", width=20)
        table.add_column("类型", width=22)
        table.add_column("执行状态", width=12)
        table.add_column("推荐摘要", width=30)

        for d in result:
            # 格式化时间
            ts = d.get("timestamp", "")
            if isinstance(ts, str) and "T" in ts:
                ts = ts[:19].replace("T", " ")

            # 推荐摘要截断
            recommendation = d.get("recommendation_text") or ""
            if len(recommendation) > 28:
                recommendation = recommendation[:25] + "..."

            # 执行状态颜色
            status = d.get("execution_status", "unknown")
            status_color = {
                "pending": "yellow",
                "executed": "green",
                "skipped": "dim",
                "modified": "cyan",
                "failed": "red",
            }.get(status, "white")

            table.add_row(
                d.get("decision_id", "")[:20],
                ts,
                d.get("decision_type", ""),
                f"[{status_color}]{status}[/{status_color}]",
                recommendation,
            )

        console.print(table)
        console.print(f"\n共 [bold]{len(result)}[/bold] 条决策记录")

    except ValueError as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)
    except NanobotRunnerError as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)


@app.command(name="feedback")
def record_feedback(
    decision_id: str = typer.Argument(help="决策唯一标识"),
    score: int = typer.Option(..., "--score", "-s", help="反馈评分 (1-5)"),
    text: str = typer.Option("", "--text", "-t", help="反馈文本"),
    accepted: bool = typer.Option(False, "--accepted", "-a", help="推荐是否被采纳"),
) -> None:
    """记录决策反馈

    对指定决策记录用户反馈评分和文本。

    Examples:
        nanobotrun evolution feedback dec_abc123 --score 4
        nanobotrun evolution feedback dec_abc123 --score 5 --text "非常好" --accepted
    """
    try:
        # 评分范围校验
        if score < 1 or score > 5:
            print_error(CLIError.storage_error("评分必须在1-5之间"))
            raise typer.Exit(1)

        handler = EvolutionHandler()
        handler.record_feedback(
            decision_id=decision_id,
            score=score,
            text=text or None,
            accepted=accepted if accepted else None,
        )

        # 评分可视化
        stars = "*" * score + "-" * (5 - score)
        accepted_text = "[green]已采纳[/green]" if accepted else ""

        console.print(
            Panel(
                f"[bold]决策ID:[/bold] {decision_id}\n"
                f"[bold]评分:[/bold] [{stars}] {score}/5\n"
                f"[bold]反馈:[/bold] {text or '无'}\n"
                f"[bold]采纳:[/bold] {accepted_text or '未标记'}",
                title="[Evolution] 反馈已记录",
                border_style="green",
            )
        )

    except ValueError as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)
    except NanobotRunnerError as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)


@app.command(name="accuracy")
def get_accuracy(
    days: int = typer.Option(30, "--days", "-d", help="统计天数"),
) -> None:
    """查看预测精度统计

    展示AI预测的准确度统计，包括平均绝对误差、高估率、低估率等。

    Examples:
        nanobotrun evolution accuracy
        nanobotrun evolution accuracy --days 90
    """
    try:
        handler = EvolutionHandler()
        result = handler.get_accuracy(days=days)

        mae = result.get("mae", 0.0)
        total = result.get("total_pairs", 0)
        over_rate = result.get("overestimate_rate", 0.0)
        under_rate = result.get("underestimate_rate", 0.0)

        # 精度等级判定
        if mae <= 2.0:
            level = "[green]优秀[/green]"
        elif mae <= 5.0:
            level = "[yellow]良好[/yellow]"
        else:
            level = "[red]需改进[/red]"

        console.print(
            Panel(
                f"[bold]统计周期:[/bold] 最近{days}天\n\n"
                f"[bold]平均绝对误差(MAE):[/bold] {mae:.2f}% {level}\n"
                f"[bold]配对总数:[/bold] {total}\n\n"
                f"[bold]高估率:[/bold] {over_rate:.1%}\n"
                f"[bold]低估率:[/bold] {under_rate:.1%}\n"
                f"[bold]准确率:[/bold] {max(0, 1 - over_rate - under_rate):.1%}",
                title="[Evolution] 预测精度统计",
                border_style="cyan",
            )
        )

    except NanobotRunnerError as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)


@app.command(name="fidelity")
def get_fidelity(
    days: int = typer.Option(30, "--days", "-d", help="统计天数"),
) -> None:
    """查看执行忠实度统计

    展示训练计划执行忠实度统计，反映跑者按计划执行的程度。

    Examples:
        nanobotrun evolution fidelity
        nanobotrun evolution fidelity --days 90
    """
    try:
        handler = EvolutionHandler()
        result = handler.get_fidelity(days=days)

        count = result.get("count", 0)
        avg = result.get("avg_fidelity", 0.0)
        min_val = result.get("min_fidelity", 0.0)
        max_val = result.get("max_fidelity", 0.0)

        if count == 0:
            console.print("[yellow]暂无执行忠实度数据[/yellow]")
            return

        # 忠实度等级判定
        if avg >= 0.8:
            level = "[green]优秀[/green]"
        elif avg >= 0.6:
            level = "[yellow]良好[/yellow]"
        else:
            level = "[red]需改进[/red]"

        console.print(
            Panel(
                f"[bold]统计周期:[/bold] 最近{days}天\n\n"
                f"[bold]平均忠实度:[/bold] {avg:.1%} {level}\n"
                f"[bold]最低忠实度:[/bold] {min_val:.1%}\n"
                f"[bold]最高忠实度:[/bold] {max_val:.1%}\n"
                f"[bold]样本数:[/bold] {count}",
                title="[Evolution] 执行忠实度统计",
                border_style="cyan",
            )
        )

    except NanobotRunnerError as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)


@app.command(name="status")
def get_status() -> None:
    """查看决策追踪整体状态

    展示决策追踪模块的整体运行状态，包括总决策数、状态分布、类型分布等。

    Examples:
        nanobotrun evolution status
    """
    try:
        handler = EvolutionHandler()
        result = handler.get_status()

        total = result.get("total_decisions", 0)
        status_dist = result.get("status_distribution", {})
        type_dist = result.get("type_distribution", {})

        # 状态分布格式化
        status_lines = []
        status_labels = {
            "pending": "待执行",
            "executed": "已执行",
            "skipped": "已跳过",
            "modified": "已修改",
            "failed": "执行失败",
        }
        for status, count in status_dist.items():
            label = status_labels.get(status, status)
            status_lines.append(f"  {label}: {count}")

        # 类型分布格式化
        type_lines = []
        type_labels = {
            "training_advice": "训练建议",
            "plan_adjustment": "计划调整",
            "recovery_suggestion": "恢复建议",
            "weather_advice": "天气建议",
            "data_query": "数据查询",
            "general": "通用",
        }
        for dtype, count in type_dist.items():
            label = type_labels.get(dtype, dtype)
            type_lines.append(f"  {label}: {count}")

        status_text = "\n".join(status_lines) if status_lines else "  暂无数据"
        type_text = "\n".join(type_lines) if type_lines else "  暂无数据"

        console.print(
            Panel(
                f"[bold]总决策数:[/bold] {total}\n\n"
                f"[bold]执行状态分布:[/bold]\n{status_text}\n\n"
                f"[bold]决策类型分布:[/bold]\n{type_text}",
                title="[Evolution] 决策追踪状态",
                border_style="cyan",
            )
        )

    except NanobotRunnerError as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)
