from __future__ import annotations

import typer
from rich.panel import Panel
from rich.table import Table

from src.cli.common import CLIError, console, print_error
from src.cli.handlers.prediction_handler import PredictionHandler

app = typer.Typer(help="ML智能预测命令")


@app.command(name="vdot")
def predict_vdot(
    days: int = typer.Option(30, "--days", "-d", help="预测天数"),
) -> None:
    """VDOT趋势预测"""
    try:
        handler = PredictionHandler()
        console.print(f"[bold]VDOT趋势预测[/bold] (未来 {days} 天)")

        result = handler.predict_vdot_trend(days=days)

        current_vdot = result.get("current_vdot", 0)
        predicted_vdot = result.get("predicted_vdot", 0)
        confidence = result.get("confidence", 0)
        ci = result.get("confidence_interval", (0, 0))
        trend_slope = result.get("trend_slope", 0)
        prediction_type = result.get("prediction_type", "basic")
        data_quality = result.get("data_quality", "unknown")

        diff = predicted_vdot - current_vdot
        diff_color = "green" if diff > 0 else "red" if diff < 0 else "white"

        panel = Panel(
            f"[bold]当前VDOT:[/bold] {current_vdot:.1f}\n"
            f"[bold]预测VDOT:[/bold] {predicted_vdot:.1f} ([{diff_color}]{diff:+.1f}[/{diff_color}])\n"
            f"[bold]置信区间:[/bold] [{ci[0]:.1f}, {ci[1]:.1f}]\n"
            f"[bold]置信度:[/bold] {confidence:.0%}\n"
            f"[bold]趋势斜率:[/bold] {trend_slope:+.4f}/天\n"
            f"[bold]预测模式:[/bold] {prediction_type}\n"
            f"[bold]数据质量:[/bold] {data_quality}",
            title="[VDOT Prediction] VDOT趋势预测",
            border_style="blue",
        )
        console.print(panel)

    except Exception as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)


@app.command(name="race")
def predict_race(
    distance: float = typer.Option(42.195, "--distance", "-D", help="比赛距离(km)"),
    race_date: str | None = typer.Option(None, "--date", help="比赛日期(YYYY-MM-DD)"),
) -> None:
    """比赛成绩预测"""
    try:
        handler = PredictionHandler()
        distance_label = f"{distance:.1f}km"
        console.print(f"[bold]比赛成绩预测[/bold] ({distance_label})")

        result = handler.predict_race_result(distance_km=distance, race_date=race_date)

        predicted_time = result.get("predicted_time", "N/A")
        confidence = result.get("confidence", 0)
        best_case = result.get("best_case", "N/A")
        worst_case = result.get("worst_case", "N/A")
        predicted_vdot = result.get("predicted_vdot", 0)
        prediction_type = result.get("prediction_type", "basic")

        panel = Panel(
            f"[bold]预测完赛时间:[/bold] {predicted_time}\n"
            f"[bold]最佳情况:[/bold] {best_case}\n"
            f"[bold]最差情况:[/bold] {worst_case}\n"
            f"[bold]置信度:[/bold] {confidence:.0%}\n"
            f"[bold]对应VDOT:[/bold] {predicted_vdot:.1f}\n"
            f"[bold]预测模式:[/bold] {prediction_type}",
            title="[Race Prediction] 比赛成绩预测",
            border_style="blue",
        )
        console.print(panel)

    except Exception as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)


@app.command(name="injury")
def predict_injury(
    days: int = typer.Option(21, "--days", "-d", help="预测天数"),
) -> None:
    """伤病风险预测"""
    try:
        handler = PredictionHandler()
        console.print(f"[bold]伤病风险预测[/bold] (未来 {days} 天)")

        result = handler.predict_injury_risk(days=days)

        risk_score = result.get("risk_score", 0)
        risk_level = result.get("risk_level", "unknown")
        prediction_type = result.get("prediction_type", "basic")
        data_quality = result.get("data_quality", "unknown")
        recommendations = result.get("recommendations", [])
        top_factors = result.get("top_risk_factors", [])

        level_color = {"low": "green", "medium": "yellow", "high": "red"}.get(
            risk_level, "white"
        )
        score_color = (
            "green" if risk_score < 30 else "yellow" if risk_score < 60 else "red"
        )

        factors_text = ""
        if top_factors:
            factors_text = "\n[bold]主要风险因子:[/bold]"
            for f in top_factors[:3]:
                name = f.get("name", "")
                contribution = f.get("contribution", 0)
                factors_text += f"\n  - {name}: 贡献度 {contribution:.0%}"

        recs_text = ""
        if recommendations:
            recs_text = "\n\n[bold]建议:[/bold]"
            for r in recommendations[:3]:
                recs_text += f"\n  - {r}"

        panel = Panel(
            f"[bold]风险评分:[/bold] [{score_color}]{risk_score:.1f}/100[/{score_color}]\n"
            f"[bold]风险等级:[/bold] [{level_color}]{risk_level}[/{level_color}]\n"
            f"[bold]预测模式:[/bold] {prediction_type}\n"
            f"[bold]数据质量:[/bold] {data_quality}"
            f"{factors_text}{recs_text}",
            title="[Injury Prediction] 伤病风险预测",
            border_style="blue",
        )
        console.print(panel)

    except Exception as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)


@app.command(name="response")
def predict_response(
    session_type: str = typer.Option(
        "easy", "--type", "-t", help="训练类型(easy/threshold/interval/recovery)"
    ),
    duration: int = typer.Option(60, "--duration", "-m", help="训练时长(分钟)"),
    intensity: str = typer.Option(
        "moderate", "--intensity", "-i", help="强度(low/moderate/high)"
    ),
) -> None:
    """训练响应预测"""
    try:
        handler = PredictionHandler()
        console.print(
            f"[bold]训练响应预测[/bold] ({session_type}, {duration}min, {intensity})"
        )

        result = handler.predict_training_response(
            session_type=session_type,
            duration_min=duration,
            intensity=intensity,
        )

        vdot_impact = result.get("predicted_vdot_impact", 0)
        fatigue_impact = result.get("predicted_fatigue_impact", 0)
        recovery_hours = result.get("predicted_recovery_hours", 0)
        injury_risk_delta = result.get("predicted_injury_risk_delta", 0)
        fitness_delta = result.get("banister_fitness_delta", 0)
        fatigue_delta = result.get("banister_fatigue_delta", 0)
        prediction_type = result.get("prediction_type", "parametric")

        vdot_color = "green" if vdot_impact > 0 else "red"
        risk_color = (
            "green"
            if injury_risk_delta < 0.05
            else "yellow"
            if injury_risk_delta < 0.1
            else "red"
        )

        panel = Panel(
            f"[bold]VDOT影响:[/bold] [{vdot_color}]{vdot_impact:+.2f}[/{vdot_color}]\n"
            f"[bold]疲劳影响:[/bold] {fatigue_impact:.1f}\n"
            f"[bold]预计恢复:[/bold] {recovery_hours:.0f}小时\n"
            f"[bold]伤病风险增量:[/bold] [{risk_color}]{injury_risk_delta:+.3f}[/{risk_color}]\n"
            f"[bold]Banister体能增量:[/bold] {fitness_delta:+.2f}\n"
            f"[bold]Banister疲劳增量:[/bold] {fatigue_delta:+.2f}\n"
            f"[bold]预测模式:[/bold] {prediction_type}",
            title="[Training Response] 训练响应预测",
            border_style="blue",
        )
        console.print(panel)

    except Exception as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)


@app.command(name="status")
def prediction_status() -> None:
    """预测数据充足度评估"""
    try:
        handler = PredictionHandler()
        console.print("[bold]预测数据充足度评估[/bold]")

        result = handler.check_prediction_status()

        vdot_status = result.get("vdot_status", {})
        race_status = result.get("race_status", {})
        injury_status = result.get("injury_status", {})
        ready_count = result.get("overall_ready_count", 0)
        advice = result.get("advice", [])

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("预测类型", width=12)
        table.add_column("数据充足", width=10)
        table.add_column("进度", width=10)
        table.add_column("预测模式", width=25)

        model_status_map: dict[str, bool] = {}
        try:
            from src.core.base.context import AppContextFactory

            ctx = AppContextFactory.create()
            engine = ctx.prediction_engine
            if engine is not None and engine._model_manager is not None:
                for mt in ("vdot_predictor", "injury_predictor"):
                    st = engine._model_manager.get_model_status(mt)
                    model_status_map[mt] = st.is_available
        except Exception:
            pass

        for name, status, model_key in [
            ("VDOT", vdot_status, "vdot_predictor"),
            ("比赛", race_status, None),
            ("伤病", injury_status, "injury_predictor"),
        ]:
            is_sufficient = status.get("is_sufficient", False)
            progress = status.get("overall_progress_pct", 0)
            model_available = (
                model_status_map.get(model_key, False) if model_key else True
            )

            if is_sufficient and model_available:
                mode = "ML增强"
            elif is_sufficient and not model_available:
                mode = "参数化(ML模型未训练)"
            elif progress >= 50:
                mode = "参数化"
            else:
                mode = "基础"

            suff_label = "[green]是[/green]" if is_sufficient else "[yellow]否[/yellow]"
            table.add_row(name, suff_label, f"{progress:.0f}%", mode)

        console.print(table)
        console.print(f"\n[bold]就绪预测数:[/bold] {ready_count}/3")

        if advice:
            console.print("\n[bold]建议:[/bold]")
            for a in advice:
                console.print(f"  - {a}")

    except Exception as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)


@app.command(name="model")
def manage_model(
    action: str = typer.Argument("status", help="操作(status/train)"),
    model_type: str = typer.Argument("vdot_predictor", help="模型类型"),
) -> None:
    """模型管理"""
    try:
        handler = PredictionHandler()
        console.print(f"[bold]模型管理[/bold] ({action} - {model_type})")

        result = handler.manage_model(action=action, model_type=model_type)

        success = result.get("success", False)
        message = result.get("message", "")

        if success:
            console.print(f"[green]✓[/green] {message}")
        else:
            console.print(f"[red]✗[/red] {message}")

    except Exception as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)
