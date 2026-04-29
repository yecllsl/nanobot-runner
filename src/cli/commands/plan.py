# 计划执行反馈相关命令
# v0.10.0新增：plan log / plan stats
# v0.11.0新增：plan adjust / plan suggest
# v0.12.0新增：plan evaluate / plan long-term / plan advice

import typer

from src.cli.common import CLIError, console, print_error, print_status

app = typer.Typer(help="训练计划执行反馈命令")


@app.command(name="create")
def create_plan(
    goal_distance_km: float = typer.Argument(..., help="目标距离（公里）"),
    goal_date: str = typer.Argument(..., help="目标日期（YYYY-MM-DD）"),
    current_vdot: float = typer.Option(..., "--vdot", "-v", help="当前VDOT值"),
    current_weekly_distance_km: float = typer.Option(
        30.0, "--volume", help="当前周跑量（公里）"
    ),
    age: int = typer.Option(30, "--age", "-a", help="年龄"),
    resting_hr: int = typer.Option(60, "--rhr", help="静息心率"),
) -> None:
    """创建训练计划

    示例：
        nanobotrun plan create 42.195 2026-06-15 --vdot 42.0 --volume 35
        nanobotrun plan create 21.1 2026-05-01 -v 40.0 --volume 30
    """
    from src.core.base.context import get_context
    from src.core.training_plan import TrainingPlanEngine

    try:
        context = get_context()
        engine = TrainingPlanEngine()

        plan = engine.generate_plan(
            user_id=context.config.user_id,
            goal_distance_km=goal_distance_km,
            goal_date=goal_date,
            current_vdot=current_vdot,
            current_weekly_distance_km=current_weekly_distance_km,
            age=age,
            resting_hr=resting_hr,
        )

        plan_id = context.plan_manager.create_plan(plan)

        print_status("[OK] 训练计划创建成功", "success")
        console.print(f"  计划ID: {plan_id}")
        console.print(f"  目标: {goal_distance_km}km @ {goal_date}")
        console.print(f"  总周数: {len(plan.weeks)}")
        console.print(f"  计划类型: {plan.plan_type.label}")
        console.print(f"  体能水平: {plan.fitness_level.label}")

        console.print("\n  💡 使用以下命令记录训练反馈：")
        console.print(
            f"    nanobotrun plan log {plan_id} <日期> --completion 0.8 --effort 6"
        )

    except Exception as e:
        print_error(CLIError.execution_record_failed(f"创建失败：{e}"))
        raise typer.Exit(1)


@app.command(name="log")
def log_execution(
    plan_id: str = typer.Argument(..., help="训练计划ID"),
    date: str = typer.Argument(..., help="日期（YYYY-MM-DD）"),
    completion_rate: float | None = typer.Option(
        None, "--completion", "-c", help="完成度（0.0-1.0）"
    ),
    effort_score: int | None = typer.Option(
        None, "--effort", "-e", help="体感评分（1-10）"
    ),
    notes: str = typer.Option("", "--notes", "-n", help="反馈备注"),
    distance: float | None = typer.Option(
        None, "--distance", "-d", help="实际距离（公里）"
    ),
    duration: int | None = typer.Option(None, "--duration", help="实际时长（分钟）"),
    avg_hr: int | None = typer.Option(None, "--hr", help="实际平均心率"),
) -> None:
    """记录训练计划执行反馈

    示例：
        nanobotrun plan log plan_20240101 2024-01-15 --completion 0.8 --effort 6
        nanobotrun plan log plan_20240101 2024-01-15 -c 1.0 -e 4 -n "轻松完成"
    """
    try:
        from src.core.base.context import get_context

        context = get_context()
        plan_manager = context.plan_manager

        result = plan_manager.record_execution(
            plan_id=plan_id,
            date=date,
            completion_rate=completion_rate,
            effort_score=effort_score,
            notes=notes,
            actual_distance_km=distance,
            actual_duration_min=duration,
            actual_avg_hr=avg_hr,
        )

        if result.get("success"):
            print_status(f"[OK] {result.get('message', '记录成功')}", "success")
            if completion_rate is not None:
                console.print(f"  完成度: {completion_rate:.0%}")
            if effort_score is not None:
                console.print(f"  体感评分: {effort_score}/10")
            if notes:
                console.print(f"  备注: {notes}")
        else:
            print_error(
                CLIError.execution_record_failed(result.get("message", "未知错误"))
            )
            raise typer.Exit(1)

    except Exception as e:
        if "计划不存在" in str(e) or "日期不存在" in str(e):
            print_error(CLIError.execution_record_failed(str(e)))
        else:
            print_error(CLIError.execution_record_failed(f"记录失败：{e}"))
        raise typer.Exit(1)


@app.command(name="stats")
def get_stats(
    plan_id: str = typer.Argument(..., help="训练计划ID"),
) -> None:
    """查看训练计划执行统计

    示例：
        nanobotrun plan stats plan_20240101
    """
    try:
        from src.core.base.context import get_context

        context = get_context()
        execution_repo = context.plan_execution_repo

        stats = execution_repo.get_plan_execution_stats(plan_id)

        console.print("\n[bold]训练计划执行统计[/bold]")
        console.print(f"  计划ID: {stats.plan_id}")
        console.print(f"  计划天数: {stats.total_planned_days}")
        console.print(f"  完成天数: {stats.completed_days}")
        console.print(f"  完成率: {stats.completion_rate:.1%}")
        console.print(f"  平均体感: {stats.avg_effort_score:.1f}/10")
        console.print(f"  总距离: {stats.total_distance_km:.1f}km")
        console.print(f"  总时长: {stats.total_duration_min}分钟")

        if stats.avg_hr is not None:
            console.print(f"  平均心率: {stats.avg_hr}bpm")
        if stats.avg_hr_drift is not None:
            console.print(f"  平均心率漂移: {stats.avg_hr_drift:.3f}")

    except Exception as e:
        print_error(CLIError.execution_record_failed(f"查询失败：{e}"))
        raise typer.Exit(1)


@app.command(name="adjust")
def adjust_plan(
    plan_id: str = typer.Argument(..., help="训练计划ID"),
    request: str = typer.Argument(
        ..., help="调整请求（自然语言），如'减量20%'、'增加间歇跑'"
    ),
    confirm: bool = typer.Option(
        True, "--confirm/--no-confirm", help="是否需要确认后再执行调整"
    ),
) -> None:
    """调整训练计划

    示例：
        nanobotrun plan adjust plan_20240101 "减量20%"
        nanobotrun plan adjust plan_20240101 "增加间歇跑" --no-confirm
    """
    try:
        from src.core.base.context import get_context

        context = get_context()
        runner_tools = (
            context.runner_tools if hasattr(context, "runner_tools") else None
        )

        from src.agents.tools import RunnerTools

        if runner_tools is None:
            runner_tools = RunnerTools(context=context)

        result = runner_tools.adjust_plan(
            plan_id=plan_id,
            adjustment_request=request,
            confirmation_required=confirm,
        )

        if result.get("success"):
            console.print("\n[bold]训练计划调整[/bold]")
            console.print(f"  计划ID: {plan_id}")
            console.print(f"  调整请求: {request}")

            adjustment = result.get("adjustment", {})
            if adjustment:
                console.print(f"  调整类型: {adjustment.get('adjustment_type', 'N/A')}")
                console.print(f"  调整描述: {adjustment.get('description', 'N/A')}")
                if adjustment.get("adjusted_value") is not None:
                    console.print(f"  调整值: {adjustment.get('adjusted_value')}")

            if result.get("requires_confirmation"):
                console.print("\n[yellow]⚠ 需要确认后才会执行调整[/yellow]")
            else:
                print_status("[OK] 调整已执行", "success")
        else:
            violations = result.get("violations", [])
            print_error(
                CLIError.execution_record_failed(result.get("error", "调整失败"))
            )
            if violations:
                console.print("[red]违规项：[/red]")
                for v in violations:
                    console.print(f"  - {v}")
            raise typer.Exit(1)

    except typer.Exit:
        raise
    except Exception as e:
        print_error(CLIError.execution_record_failed(f"调整失败：{e}"))
        raise typer.Exit(1)


@app.command(name="suggest")
def get_suggestions(
    plan_id: str = typer.Argument(..., help="训练计划ID"),
) -> None:
    """获取训练计划调整建议

    示例：
        nanobotrun plan suggest plan_20240101
    """
    try:
        from src.core.base.context import get_context

        context = get_context()
        runner_tools = (
            context.runner_tools if hasattr(context, "runner_tools") else None
        )

        from src.agents.tools import RunnerTools

        if runner_tools is None:
            runner_tools = RunnerTools(context=context)

        result = runner_tools.get_plan_adjustment_suggestions(plan_id=plan_id)

        if result.get("success"):
            console.print("\n[bold]训练计划调整建议[/bold]")
            console.print(f"  计划ID: {plan_id}")

            suggestions = result.get("suggestions", [])
            if suggestions:
                for i, s in enumerate(suggestions, 1):
                    priority = s.get("priority", "low")
                    confidence = s.get("confidence", 0)
                    content = s.get("suggestion_content", "")

                    priority_color = {
                        "high": "red",
                        "medium": "yellow",
                        "low": "green",
                    }.get(priority, "white")

                    console.print(
                        f"\n  [{priority_color}]● 优先级: {priority}[/{priority_color}]"
                    )
                    console.print(f"  建议: {content}")
                    console.print(f"  置信度: {confidence:.0%}")
            else:
                console.print("  暂无建议")
        else:
            print_error(
                CLIError.execution_record_failed(result.get("error", "获取建议失败"))
            )
            raise typer.Exit(1)

    except typer.Exit:
        raise
    except Exception as e:
        print_error(CLIError.execution_record_failed(f"获取建议失败：{e}"))
        raise typer.Exit(1)


@app.command(name="evaluate")
def evaluate_goal(
    goal_type: str = typer.Argument(
        ..., help="目标类型（vdot/5k/10k/half_marathon/marathon）"
    ),
    goal_value: float = typer.Argument(..., help="目标值（VDOT值或秒数）"),
    current_vdot: float = typer.Option(..., "--vdot", "-v", help="当前VDOT值"),
    weeks: int | None = typer.Option(None, "--weeks", "-w", help="可用训练周数"),
) -> None:
    """评估目标达成概率（v0.12.0新增）"""
    from src.core.base.context import get_context

    try:
        context = get_context()
        engine = context.goal_prediction_engine
        evaluation = engine.evaluate_goal(
            goal_type=goal_type,
            goal_value=goal_value,
            current_vdot=current_vdot,
            weeks_available=weeks,
        )

        print_status(f"🎯 目标评估：{goal_type} = {goal_value}")
        console.print(f"  当前水平：{evaluation.current_value}")
        console.print(f"  目标差距：{evaluation.gap:.2f}")
        console.print(f"  达成概率：{evaluation.achievement_probability:.0%}")
        console.print(f"  置信度：{evaluation.confidence:.0%}")
        if evaluation.estimated_weeks_to_achieve:
            console.print(f"  预计所需周数：{evaluation.estimated_weeks_to_achieve}")

        if evaluation.key_risks:
            console.print("\n  ⚠️ 关键风险：")
            for risk in evaluation.key_risks:
                console.print(f"    - {risk}")

        if evaluation.improvement_suggestions:
            console.print("\n  💡 改进建议：")
            for suggestion in evaluation.improvement_suggestions:
                console.print(f"    - {suggestion}")

    except typer.Exit:
        raise
    except Exception as e:
        print_error(CLIError.execution_record_failed(f"目标评估失败：{e}"))
        raise typer.Exit(1)


@app.command(name="long-term")
def create_long_term_plan(
    plan_name: str = typer.Argument(..., help="计划名称"),
    current_vdot: float = typer.Option(..., "--vdot", "-v", help="当前VDOT值"),
    target_vdot: float | None = typer.Option(None, "--target", "-t", help="目标VDOT值"),
    target_race: str | None = typer.Option(None, "--race", "-r", help="目标赛事"),
    target_date: str | None = typer.Option(
        None, "--date", "-d", help="目标日期(YYYY-MM-DD)"
    ),
    total_weeks: int = typer.Option(16, "--weeks", "-w", help="总训练周数"),
    fitness_level: str = typer.Option(
        "intermediate",
        "--level",
        "-l",
        help="体能水平(beginner/intermediate/advanced/elite)",
    ),
    skip_training_plans: bool = typer.Option(
        False, "--skip-plans", help="跳过自动创建训练计划"
    ),
) -> None:
    """创建长期训练规划（v0.12.0新增）"""
    from src.core.base.context import get_context

    try:
        context = get_context()
        generator = context.long_term_plan_generator
        plan = generator.generate_plan(
            plan_name=plan_name,
            current_vdot=current_vdot,
            target_vdot=target_vdot,
            target_race=target_race,
            target_date=target_date,
            total_weeks=total_weeks,
            fitness_level=fitness_level,
            auto_create_training_plans=not skip_training_plans,
        )

        print_status(f"📋 长期训练规划：{plan.plan_name}")
        console.print(f"  当前VDOT：{plan.current_vdot}")
        if plan.target_vdot:
            console.print(f"  目标VDOT：{plan.target_vdot}")
        if plan.has_target_race:
            console.print(f"  目标赛事：{plan.target_race} ({plan.target_date})")
        console.print(f"  总周数：{plan.total_weeks}")
        console.print(
            f"  周跑量范围：{plan.weekly_volume_range_km[0]:.0f}-{plan.weekly_volume_range_km[1]:.0f}km"
        )

        if plan.cycles:
            console.print("\n  📅 训练周期：")
            for cycle in plan.cycles:
                console.print(
                    f"    {cycle.cycle_type}: {cycle.start_date} ~ {cycle.end_date} "
                    f"({cycle.weekly_volume_km:.0f}km/周) - {cycle.goal}"
                )

        if plan.key_milestones:
            console.print("\n  🏆 关键里程碑：")
            for milestone in plan.key_milestones:
                console.print(f"    - {milestone}")

        if plan.training_plan_ids:
            console.print("\n  📝 关联训练计划：")
            for i, tp_id in enumerate(plan.training_plan_ids):
                cycle = plan.cycles[i] if i < len(plan.cycles) else None
                cycle_type = cycle.cycle_type if cycle else "unknown"
                console.print(f"    [{cycle_type}] {tp_id}")

            console.print("\n  💡 使用以下命令记录训练反馈：")
            console.print(
                "    nanobotrun plan log <plan_id> <日期> --completion 0.8 --effort 6"
            )

    except typer.Exit:
        raise
    except Exception as e:
        print_error(CLIError.execution_record_failed(f"创建长期规划失败：{e}"))
        raise typer.Exit(1)


@app.command(name="advice")
def get_training_advice(
    current_vdot: float | None = typer.Option(None, "--vdot", "-v", help="当前VDOT值"),
    weekly_volume: float | None = typer.Option(None, "--volume", help="周跑量(公里)"),
    consistency: float | None = typer.Option(
        None, "--consistency", help="训练一致性(0-1)"
    ),
    injury_risk: str = typer.Option("low", "--risk", help="伤病风险(low/medium/high)"),
    goal_type: str | None = typer.Option(None, "--goal", "-g", help="目标类型"),
) -> None:
    """获取智能训练建议（v0.12.0新增）"""
    from src.core.base.context import get_context

    try:
        context = get_context()
        engine = context.smart_advice_engine
        advices = engine.generate_advice(
            current_vdot=current_vdot,
            weekly_volume_km=weekly_volume or 0.0,
            training_consistency=consistency or 1.0,
            injury_risk=injury_risk,
            goal_type=goal_type,
        )

        print_status(f"💡 智能训练建议（共{len(advices)}条）")

        priority_icons = {"high": "🔴", "medium": "🟡", "low": "🟢"}
        type_labels = {
            "training": "训练",
            "recovery": "恢复",
            "nutrition": "营养",
            "injury_prevention": "伤病预防",
        }

        for advice in advices:
            icon = priority_icons.get(advice.priority, "⚪")
            label = type_labels.get(advice.advice_type, advice.advice_type)
            console.print(f"\n  {icon} [{label}] {advice.content}")
            console.print(
                f"    优先级：{advice.priority} | 置信度：{advice.confidence:.0%}"
            )
            if advice.context:
                console.print(f"    背景：{advice.context}")

    except typer.Exit:
        raise
    except Exception as e:
        print_error(CLIError.execution_record_failed(f"获取训练建议失败：{e}"))
        raise typer.Exit(1)
