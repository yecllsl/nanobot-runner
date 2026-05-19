from __future__ import annotations

import json

import typer
from rich.panel import Panel
from rich.table import Table

from src.cli.common import CLIError, console, print_error
from src.cli.handlers.twin_handler import TwinHandler
from src.core.base.exceptions import NanobotRunnerError

app = typer.Typer(help="数字孪生引擎命令", no_args_is_help=True)


@app.command(name="snapshot")
def get_snapshot() -> None:
    """获取当前跑者状态快照

    展示5维度跑者状态向量：体能、负荷、身体信号、风险、训练模式。

    Examples:
        nanobotrun twin snapshot
    """
    try:
        handler = TwinHandler()
        result = handler.get_snapshot()

        fitness = result.get("fitness", {})
        load = result.get("load", {})
        body_signal = result.get("body_signal", {})
        risk = result.get("risk", {})
        training_pattern = result.get("training_pattern", {})
        data_quality = result.get("data_quality", "unknown")

        panel = Panel(
            f"[bold]体能维度[/bold]\n"
            f"  VDOT: {fitness.get('vdot', 0):.1f} | 趋势: {fitness.get('vdot_trend', 0):+.4f}\n\n"
            f"[bold]负荷维度[/bold]\n"
            f"  CTL: {load.get('ctl', 0):.1f} | ATL: {load.get('atl', 0):.1f} | "
            f"TSB: {load.get('tsb', 0):+.1f} | ACWR: {load.get('acwr', 0):.2f}\n\n"
            f"[bold]身体信号[/bold]\n"
            f"  疲劳度: {body_signal.get('fatigue_score', 0):.1f} | "
            f"恢复状态: {body_signal.get('recovery_status', 'unknown')}\n\n"
            f"[bold]风险维度[/bold]\n"
            f"  7日伤病风险: {risk.get('injury_risk_7d', 0):.1f}% | "
            f"28日伤病风险: {risk.get('injury_risk_28d', 0):.1f}% | "
            f"过度训练: {risk.get('overtraining_risk', 'unknown')}\n\n"
            f"[bold]训练模式[/bold]\n"
            f"  周跑量: {training_pattern.get('weekly_volume_km', 0):.1f}km | "
            f"长跑频次: {training_pattern.get('long_run_frequency', 0)}次/周\n\n"
            f"[bold]数据质量:[/bold] {data_quality}",
            title="[Digital Twin] 跑者状态快照",
            border_style="cyan",
        )
        console.print(panel)

    except NanobotRunnerError as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)


@app.command(name="simulate")
def simulate(
    plan_id: str = typer.Option("", "--plan-id", "-p", help="系统训练计划ID"),
    plan_name: str = typer.Option(
        "自定义计划", "--name", "-n", help="计划名称(手动模式)"
    ),
    weeks_json: str = typer.Option(
        "",
        "--weeks",
        "-w",
        help="周计划JSON数组(手动模式)",
    ),
    prediction_type: str = typer.Option(
        "parametric", "--type", "-t", help="预测模式(basic/parametric/ml_enhanced)"
    ),
) -> None:
    """What-If 推演

    基于当前状态推演训练计划执行后的变化。
    支持两种输入方式：--plan-id 引用系统计划，或 --name + --weeks 手动构建。

    Examples:
        nanobotrun twin simulate --plan-id plan_001
        nanobotrun twin simulate --name "破4计划" --weeks '[{"weekly_volume_km":50,"easy_ratio":0.7,"tempo_ratio":0.15,"interval_ratio":0.15,"long_run_km":25}]'
    """
    try:
        handler = TwinHandler()

        if plan_id:
            result = handler.simulate_by_plan_id(
                plan_id=plan_id,
                prediction_type=prediction_type,
            )
            display_name = plan_id
        elif weeks_json:
            weeks = json.loads(weeks_json)
            result = handler.simulate(
                plan_name=plan_name,
                weeks=weeks,
                prediction_type=prediction_type,
            )
            display_name = plan_name
        else:
            print_error(CLIError.storage_error("请提供 --plan-id 或 --weeks 参数"))
            raise typer.Exit(1)

        snapshots = result.get("snapshots", [])
        vdot_delta = result.get("vdot_delta", 0)
        peak_injury_risk = result.get("peak_injury_risk", 0)
        avg_tsb = result.get("avg_tsb", 0)

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("周", width=4)
        table.add_column("VDOT", width=8)
        table.add_column("CTL", width=8)
        table.add_column("ATL", width=8)
        table.add_column("TSB", width=8)
        table.add_column("ACWR", width=8)
        table.add_column("疲劳", width=8)
        table.add_column("7日风险%", width=10)
        table.add_column("置信度", width=8)

        for s in snapshots:
            state = s.get("state", {})
            load = state.get("load", {})
            fitness = state.get("fitness", {})
            body_signal = state.get("body_signal", {})
            risk = state.get("risk", {})
            confidence = s.get("confidence", 0)

            tsb = load.get("tsb", 0)
            tsb_style = "green" if tsb > 10 else "yellow" if tsb > 0 else "red"

            table.add_row(
                str(s.get("week_number", "")),
                f"{fitness.get('vdot', 0):.1f}",
                f"{load.get('ctl', 0):.1f}",
                f"{load.get('atl', 0):.1f}",
                f"[{tsb_style}]{tsb:+.1f}[/{tsb_style}]",
                f"{load.get('acwr', 0):.2f}",
                f"{body_signal.get('fatigue_score', 0):.1f}",
                f"{risk.get('injury_risk_7d', 0):.1f}",
                f"{confidence:.0%}",
            )

        console.print(table)

        vdot_color = "green" if vdot_delta > 0 else "red"
        risk_color = (
            "green"
            if peak_injury_risk < 15
            else "yellow"
            if peak_injury_risk < 30
            else "red"
        )

        summary = Panel(
            f"[bold]VDOT变化:[/bold] [{vdot_color}]{vdot_delta:+.2f}[/{vdot_color}]\n"
            f"[bold]峰值伤病风险:[/bold] [{risk_color}]{peak_injury_risk:.1f}%[/{risk_color}]\n"
            f"[bold]平均TSB:[/bold] {avg_tsb:+.1f}\n"
            f"[bold]预测模式:[/bold] {prediction_type}",
            title=f"[Simulation] {display_name}",
            border_style="cyan",
        )
        console.print(summary)

    except json.JSONDecodeError:
        print_error(CLIError.storage_error("weeks JSON格式错误，请检查输入"))
        raise typer.Exit(1)
    except NanobotRunnerError as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)


@app.command(name="compare")
def compare_plans(
    plan_ids: str = typer.Option(
        "", "--plan-ids", "-p", help="系统训练计划ID列表，逗号分隔(2-5个)"
    ),
    plans_json: str = typer.Option(
        "",
        "--plans",
        help='计划列表JSON，格式: [{"name":"A","weeks":[...]}, {"name":"B","weeks":[...]}]',
    ),
    prediction_type: str = typer.Option(
        "parametric", "--type", "-t", help="预测模式(basic/parametric/ml_enhanced)"
    ),
) -> None:
    """多计划对比

    对比多个训练计划的推演结果，推荐最优方案。
    支持两种输入方式：--plan-ids 引用系统计划，或 --plans 手动构建。

    Examples:
        nanobotrun twin compare --plan-ids plan_001,plan_002,plan_003
        nanobotrun twin compare --plans '[{"name":"保守","weeks":[{"weekly_volume_km":30,"easy_ratio":0.8,"tempo_ratio":0.1,"interval_ratio":0.1,"long_run_km":15}]},{"name":"激进","weeks":[{"weekly_volume_km":60,"easy_ratio":0.6,"tempo_ratio":0.2,"interval_ratio":0.2,"long_run_km":30}]}]'
    """
    try:
        handler = TwinHandler()

        if plan_ids:
            id_list = [pid.strip() for pid in plan_ids.split(",") if pid.strip()]
            result = handler.compare_plans_by_ids(
                plan_ids=id_list,
                prediction_type=prediction_type,
            )
        elif plans_json:
            plans = json.loads(plans_json)
            result = handler.compare_plans(plans=plans, prediction_type=prediction_type)
        else:
            print_error(CLIError.storage_error("请提供 --plan-ids 或 --plans 参数"))
            raise typer.Exit(1)

        metrics = result.get("plans", [])
        best_plan = result.get("best_plan", {})
        recommendation = result.get("recommendation", "")

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("计划", width=12)
        table.add_column("VDOT变化", width=10)
        table.add_column("峰值风险%", width=12)
        table.add_column("平均TSB", width=10)
        table.add_column("恢复状态", width=10)
        table.add_column("评分", width=8)

        for m in metrics:
            is_best = m.get("plan_name") == best_plan.get("plan_name")
            prefix = "★ " if is_best else "  "
            score = m.get("recommendation_score", 0)
            score_color = "green" if score > 0 else "red"

            table.add_row(
                f"{prefix}{m.get('plan_name', '')}",
                f"{m.get('vdot_delta', 0):+.2f}",
                f"{m.get('peak_injury_risk', 0):.1f}",
                f"{m.get('avg_tsb', 0):+.1f}",
                f"{m.get('min_recovery_status', '')}",
                f"[{score_color}]{score:.1f}[/{score_color}]",
            )

        console.print(table)
        console.print(f"\n[bold green]{recommendation}[/bold green]")

    except json.JSONDecodeError:
        print_error(CLIError.storage_error("plans JSON格式错误，请检查输入"))
        raise typer.Exit(1)
    except NanobotRunnerError as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)
