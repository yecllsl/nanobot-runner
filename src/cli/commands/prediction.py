from __future__ import annotations

import typer
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from src.cli.common import CLIError, console, print_error
from src.cli.handlers.prediction_handler import PredictionHandler

app = typer.Typer(help="ML智能预测命令", no_args_is_help=True)

model_app = typer.Typer(help="预测模型管理", no_args_is_help=True)
app.add_typer(model_app, name="model")


def _format_prediction_type(prediction_type: str, confidence: float) -> str:
    """格式化预测模式标注"""
    if prediction_type == "ml_enhanced":
        level = "高" if confidence >= 0.8 else "中" if confidence >= 0.5 else "低"
        return f"🧠 ML增强预测 | 模型置信度: {level}"
    elif prediction_type == "parametric":
        return "📊 参数化模型预测"
    return "基础预测"


def _format_data_hint(data_quality: str, prediction_type: str) -> str:
    """格式化数据不足提示"""
    if prediction_type != "ml_enhanced" and data_quality in (
        "insufficient",
        "low",
        "unknown",
    ):
        return "\n[dim]💡 当前数据量有限，建议积累更多数据以启用ML增强预测[/dim]"
    return ""


@app.command(name="vdot")
def predict_vdot(
    days: int = typer.Option(30, "--days", "-d", help="预测天数"),
) -> None:
    """VDOT趋势预测

    基于训练数据预测未来VDOT变化趋势。

    Examples:
        nanobotrun predict vdot --days 30
        nanobotrun predict vdot -d 90
    """
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
        type_label = _format_prediction_type(prediction_type, confidence)
        data_hint = _format_data_hint(data_quality, prediction_type)

        panel = Panel(
            f"[bold]当前VDOT:[/bold] {current_vdot:.1f}\n"
            f"[bold]预测VDOT:[/bold] {predicted_vdot:.1f} "
            f"([{diff_color}]{diff:+.1f}[/{diff_color}])\n"
            f"[bold]置信区间:[/bold] [{ci[0]:.1f}, {ci[1]:.1f}]\n"
            f"[bold]置信度:[/bold] {confidence:.0%}\n"
            f"[bold]趋势斜率:[/bold] {trend_slope:+.4f}/天\n"
            f"[bold]预测模式:[/bold] {type_label}\n"
            f"[bold]数据质量:[/bold] {data_quality}"
            f"{data_hint}",
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
    """比赛成绩预测

    基于个人化Riegel公式预测不同距离的比赛完赛时间。

    Examples:
        nanobotrun predict race --distance 42.195
        nanobotrun predict race -D 10 --date 2026-06-01
    """
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
        type_label = _format_prediction_type(prediction_type, confidence)

        panel = Panel(
            f"[bold]预测完赛时间:[/bold] {predicted_time}\n"
            f"[bold]最佳情况:[/bold] {best_case}\n"
            f"[bold]最差情况:[/bold] {worst_case}\n"
            f"[bold]置信度:[/bold] {confidence:.0%}\n"
            f"[bold]对应VDOT:[/bold] {predicted_vdot:.1f}\n"
            f"[bold]预测模式:[/bold] {type_label}",
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
    """伤病风险预测

    综合急性/慢性负荷比、训练单调性、身体信号等评估受伤概率。

    Examples:
        nanobotrun predict injury --days 21
        nanobotrun predict injury -d 7
    """
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
        type_label = _format_prediction_type(prediction_type, risk_score / 100)
        data_hint = _format_data_hint(data_quality, prediction_type)

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
            f"[bold]风险评分:[/bold] "
            f"[{score_color}]{risk_score:.1f}/100[/{score_color}]\n"
            f"[bold]风险等级:[/bold] "
            f"[{level_color}]{risk_level}[/{level_color}]\n"
            f"[bold]预测模式:[/bold] {type_label}\n"
            f"[bold]数据质量:[/bold] {data_quality}"
            f"{factors_text}{recs_text}{data_hint}",
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
    """训练响应预测

    预测单次训练的响应效果，包括VDOT影响、疲劳影响、恢复时间和伤病风险增量。

    Examples:
        nanobotrun predict response --type threshold --duration 60 --intensity high
        nanobotrun predict response -t easy -m 45 -i low
    """
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

        vdot_color = "green" if vdot_impact > 0 else "red"
        risk_color = (
            "green"
            if injury_risk_delta < 0.05
            else "yellow"
            if injury_risk_delta < 0.1
            else "red"
        )

        panel = Panel(
            f"[bold]VDOT影响:[/bold] "
            f"[{vdot_color}]{vdot_impact:+.2f}[/{vdot_color}]\n"
            f"[bold]疲劳影响:[/bold] {fatigue_impact:.1f}\n"
            f"[bold]预计恢复:[/bold] {recovery_hours:.0f}小时\n"
            f"[bold]伤病风险增量:[/bold] "
            f"[{risk_color}]{injury_risk_delta:+.3f}[/{risk_color}]\n"
            f"[bold]Banister体能增量:[/bold] {fitness_delta:+.2f}\n"
            f"[bold]Banister疲劳增量:[/bold] {fatigue_delta:+.2f}\n"
            f"[bold]预测模式:[/bold] 📊 参数化模型预测",
            title="[Training Response] 训练响应预测",
            border_style="blue",
        )
        console.print(panel)

    except Exception as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)


@app.command(name="status")
def prediction_status() -> None:
    """预测数据充足度评估

    检查各预测类型的数据充足度，评估是否具备ML增强预测条件。

    Examples:
        nanobotrun predict status
    """
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
                mode = "🧠 ML增强"
            elif is_sufficient and not model_available:
                mode = "📊 参数化(ML模型未训练)"
            elif progress >= 50:
                mode = "📊 参数化"
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


@model_app.command(name="status")
def model_status(
    model_type: str = typer.Option(
        "all", "--type", "-t", help="模型类型(all/vdot/injury)"
    ),
) -> None:
    """查看模型状态

    查看预测模型的训练状态、版本信息和数据充足度。

    Examples:
        nanobotrun predict model status --type all
        nanobotrun predict model status -t vdot
    """
    try:
        handler = PredictionHandler()

        type_map = {
            "all": ["vdot_predictor", "injury_predictor"],
            "vdot": ["vdot_predictor"],
            "injury": ["injury_predictor"],
        }
        model_types = type_map.get(model_type, [model_type])

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("模型类型", width=18)
        table.add_column("状态", width=10)
        table.add_column("版本", width=10)
        table.add_column("训练时间", width=20)
        table.add_column("训练样本", width=10)
        table.add_column("验证误差", width=10)

        for mt in model_types:
            result = handler.manage_model(action="status", model_type=mt)
            details = result.get("details", {})
            is_available = details.get("is_available", False)
            status_label = (
                "[green]可用[/green]" if is_available else "[yellow]未训练[/yellow]"
            )

            try:
                from src.core.base.context import AppContextFactory

                ctx = AppContextFactory.create()
                engine = ctx.prediction_engine
                if engine and engine._model_manager:
                    st = engine._model_manager.get_model_status(mt)
                    table.add_row(
                        mt,
                        status_label,
                        st.version or "-",
                        st.trained_at or "-",
                        str(st.training_samples) if st.training_samples else "-",
                        f"{st.validation_error:.4f}" if st.validation_error else "-",
                    )
                else:
                    table.add_row(mt, status_label, "-", "-", "-", "-")
            except Exception:
                table.add_row(mt, status_label, "-", "-", "-", "-")

        console.print(table)

    except Exception as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)


@model_app.command(name="train")
def model_train(
    model_type: str = typer.Option(
        "vdot", "--type", "-t", help="模型类型(vdot/injury)"
    ),
) -> None:
    """训练预测模型

    使用当前数据训练或重新训练ML预测模型。

    Examples:
        nanobotrun predict model train --type vdot
        nanobotrun predict model train -t injury
    """
    try:
        handler = PredictionHandler()

        type_map = {
            "vdot": "vdot_predictor",
            "injury": "injury_predictor",
        }
        actual_type = type_map.get(model_type, model_type)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(f"[cyan]训练 {model_type} 模型...", total=None)
            result = handler.manage_model(action="train", model_type=actual_type)
            progress.update(task, completed=1, total=1)

        success = result.get("success", False)
        message = result.get("message", "")

        if success:
            console.print(f"[green]✓[/green] {message}")
        else:
            console.print(f"[red]✗[/red] {message}")

    except Exception as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)


@model_app.command(name="rollback")
def model_rollback(
    model_type: str = typer.Option(
        "vdot", "--type", "-t", help="模型类型(vdot/injury)"
    ),
) -> None:
    """回滚模型到上一版本

    将预测模型回滚到上一个训练版本。

    Examples:
        nanobotrun predict model rollback --type vdot
        nanobotrun predict model rollback -t injury
    """
    try:
        handler = PredictionHandler()

        type_map = {
            "vdot": "vdot_predictor",
            "injury": "injury_predictor",
        }
        actual_type = type_map.get(model_type, model_type)

        result = handler.manage_model(action="rollback", model_type=actual_type)

        success = result.get("success", False)
        message = result.get("message", "")

        if success:
            console.print(f"[green]✓[/green] {message}")
        else:
            console.print(f"[red]✗[/red] {message}")

    except Exception as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)
