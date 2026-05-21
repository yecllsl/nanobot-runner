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


@app.command(name="calibrate")
def run_calibration(
    model_type: str = typer.Option(
        "vdot",
        "--model",
        "-m",
        help="模型类型 (vdot/injury/training_response)",
    ),
) -> None:
    """执行预测校准

    基于预测-实际配对数据，检测模型偏差方向和幅度，通过EMA更新scale因子。

    Examples:
        nanobotrun evolution calibrate
        nanobotrun evolution calibrate --model injury
    """
    try:
        handler = EvolutionHandler()
        result = handler.run_calibration(model_type=model_type)

        direction = result.get("direction", "none")
        magnitude = result.get("magnitude", 0.0)
        scale_before = result.get("scale_before", 1.0)
        scale_after = result.get("scale_after", 1.0)
        mae_before = result.get("mae_before", 0.0)
        mae_after = result.get("mae_after", 0.0)
        improvement = result.get("improvement_pct", 0.0)

        # 偏差方向可视化
        direction_labels = {
            "overestimate": "[red]高估[/red]",
            "underestimate": "[yellow]低估[/yellow]",
            "none": "[green]准确[/green]",
        }
        direction_text = direction_labels.get(direction, direction)

        # 改善方向
        if improvement > 0:
            improvement_text = f"[green]{improvement:.1f}%[/green]"
        else:
            improvement_text = f"[dim]{improvement:.1f}%[/dim]"

        console.print(
            Panel(
                f"[bold]模型类型:[/bold] {model_type}\n\n"
                f"[bold]偏差方向:[/bold] {direction_text}\n"
                f"[bold]偏差幅度:[/bold] {magnitude:.1%}\n\n"
                f"[bold]Scale修正:[/bold] {scale_before:.4f} → {scale_after:.4f}\n"
                f"[bold]MAE:[/bold] {mae_before:.4f} → {mae_after:.4f}\n"
                f"[bold]改善幅度:[/bold] {improvement_text}\n"
                f"[bold]样本数:[/bold] {result.get('sample_count', 0)}",
                title="[Evolution] 预测校准报告",
                border_style="cyan",
            )
        )

    except ValueError as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)
    except NanobotRunnerError as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)


@app.command(name="response")
def analyze_training_response(
    months: int = typer.Option(6, "--months", "-m", help="分析月数"),
) -> None:
    """分析训练响应性

    分析不同训练类型对跑者VDOT变化的响应效果，识别最佳/最差训练类型。

    Examples:
        nanobotrun evolution response
        nanobotrun evolution response --months 12
    """
    try:
        handler = EvolutionHandler()
        result = handler.analyze_training_response(months=months)

        total_pairs = result.get("total_pairs", 0)
        eligible_pairs = result.get("eligible_pairs", 0)
        responses = result.get("training_responses", [])
        best_type = result.get("best_type")
        worst_type = result.get("worst_type")
        data_sufficient = result.get("data_sufficient", False)

        # 数据充足性
        sufficient_text = (
            "[green]充足[/green]" if data_sufficient else "[yellow]不足[/yellow]"
        )

        # 训练类型响应表格
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("训练类型", width=15)
        table.add_column("样本数", width=10)
        table.add_column("平均VDOT变化", width=15)
        table.add_column("平均忠实度", width=12)
        table.add_column("响应性评分", width=12)

        for r in responses:
            training_type = r.get("training_type", "")
            sample_count = r.get("sample_count", 0)
            avg_delta = r.get("avg_vdot_delta", 0.0)
            avg_fidelity = r.get("avg_fidelity", 0.0)
            response_score = r.get("response_score", 0.0)

            # 评分颜色
            if response_score >= 0.7:
                score_color = "green"
            elif response_score >= 0.4:
                score_color = "yellow"
            else:
                score_color = "red"

            table.add_row(
                training_type,
                str(sample_count),
                f"{avg_delta:+.4f}",
                f"{avg_fidelity:.1%}",
                f"[{score_color}]{response_score:.1%}[/{score_color}]",
            )

        console.print(
            Panel(
                f"[bold]分析周期:[/bold] 最近{months}个月\n"
                f"[bold]总配对数:[/bold] {total_pairs}\n"
                f"[bold]合格配对数:[/bold] {eligible_pairs}\n"
                f"[bold]数据充足性:[/bold] {sufficient_text}\n"
                f"[bold]最佳训练类型:[/bold] {best_type or 'N/A'}\n"
                f"[bold]最差训练类型:[/bold] {worst_type or 'N/A'}",
                title="[Evolution] 训练响应性分析",
                border_style="cyan",
            )
        )
        if responses:
            console.print(table)

    except NanobotRunnerError as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)


@app.command(name="calibration-status")
def get_calibration_status(
    model_type: str = typer.Option(
        "",
        "--model",
        "-m",
        help="模型类型 (vdot/injury/training_response)，空则显示全部",
    ),
) -> None:
    """查看校准状态

    展示预测校准的当前状态，包括scale因子、样本数、MAE等。

    Examples:
        nanobotrun evolution calibration-status
        nanobotrun evolution calibration-status --model vdot
    """
    try:
        handler = EvolutionHandler()
        result = handler.get_calibration_status(model_type=model_type or None)

        if "model_type" in result:
            # 单个模型状态
            _print_calibration_profile(result)
        else:
            # 所有模型状态
            for mt, profile_data in result.items():
                console.print(f"\n[bold]{mt}[/bold]")
                _print_calibration_profile(profile_data)

    except NanobotRunnerError as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)


def _print_calibration_profile(data: dict) -> None:
    """格式化输出单个校准配置"""
    scale = data.get("scale", 1.0)
    sample_count = data.get("sample_count", 0)
    mae_before = data.get("mae_before")
    mae_after = data.get("mae_after")
    last_updated = data.get("last_updated", "")

    # Scale方向
    if scale < 1.0:
        scale_text = f"[red]{scale:.4f} (高估修正)[/red]"
    elif scale > 1.0:
        scale_text = f"[yellow]{scale:.4f} (低估修正)[/yellow]"
    else:
        scale_text = f"[green]{scale:.4f} (无修正)[/green]"

    lines = [
        f"  Scale: {scale_text}",
        f"  样本数: {sample_count}",
    ]
    if mae_before is not None:
        lines.append(f"  校准前MAE: {mae_before:.4f}")
    if mae_after is not None:
        lines.append(f"  校准后MAE: {mae_after:.4f}")
    if last_updated:
        lines.append(f"  最后更新: {last_updated}")

    console.print("\n".join(lines))
