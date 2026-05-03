# Cron 定时任务管理命令 - v0.17.0
# 提供训练提醒等定时任务的CLI管理接口

import typer

from src.cli.common import CLIError, console, print_error, print_status

app = typer.Typer(help="定时任务管理命令")


@app.command(name="status")
def cron_status() -> None:
    """查看定时任务状态

    示例：
        nanobotrun cron status
    """
    try:
        from src.core.base.context import get_context
        from src.core.plan.training_reminder_manager import TrainingReminderManager

        context = get_context()
        data_dir = (
            context.config.data_dir if hasattr(context.config, "data_dir") else None
        )

        reminder_manager = TrainingReminderManager(data_dir=data_dir)

        # 显示提醒配置
        schedule = reminder_manager.schedule
        console.print("[bold cyan]训练提醒配置[/bold cyan]")
        console.print(f"  启用状态: {'✅ 已启用' if schedule.enabled else '❌ 已禁用'}")
        console.print(f"  Cron表达式: {schedule.cron_expression}")
        console.print(f"  提前提醒: {schedule.advance_minutes} 分钟")
        console.print(f"  天气检查: {'✅' if schedule.check_weather else '❌'}")
        console.print(
            f"  免打扰时段: {schedule.do_not_disturb_start} - {schedule.do_not_disturb_end}"
        )

        # 显示今日状态
        today_status = reminder_manager.get_today_status()
        console.print("\n[bold cyan]今日提醒状态[/bold cyan]")
        if today_status["has_record"]:
            status_emoji = {
                "sent": "✅",
                "skipped": "⏭️",
                "failed": "❌",
            }.get(today_status["status"], "❓")
            console.print(f"  {status_emoji} 状态: {today_status['status']}")
            console.print(f"  📝 消息: {today_status['message']}")
            if today_status.get("skip_reason"):
                console.print(f"  ⏭️ 跳过原因: {today_status['skip_reason']}")
            if today_status.get("executed_at"):
                console.print(f"  🕐 执行时间: {today_status['executed_at']}")
        else:
            console.print("  ⏳ 今日尚未执行提醒")

        # 显示最近历史
        history = reminder_manager.get_history(days=3)
        if history:
            console.print("\n[bold cyan]最近提醒历史（3天）[/bold cyan]")
            for record in history[:5]:
                status_emoji = {
                    "sent": "✅",
                    "skipped": "⏭️",
                    "failed": "❌",
                }.get(record["status"], "❓")
                console.print(f"  {status_emoji} {record['date']}: {record['message']}")

    except Exception as e:
        print_error(CLIError.execution_record_failed(f"获取状态失败：{e}"))
        raise typer.Exit(1)


@app.command(name="enable")
def enable_reminder(
    cron_expr: str = typer.Option("0 7 * * *", "--cron", "-c", help="Cron表达式"),
    advance_minutes: int = typer.Option(30, "--advance", "-a", help="提前提醒分钟数"),
    check_weather: bool = typer.Option(
        True, "--weather/--no-weather", help="是否检查天气"
    ),
    dnd_start: str = typer.Option("22:00", "--dnd-start", help="免打扰开始时间"),
    dnd_end: str = typer.Option("07:00", "--dnd-end", help="免打扰结束时间"),
) -> None:
    """启用训练提醒

    示例：
        nanobotrun cron enable
        nanobotrun cron enable --cron "0 6 * * *" --advance 60
        nanobotrun cron enable --no-weather --dnd-start 23:00
    """
    try:
        from src.core.base.context import get_context
        from src.core.plan.training_reminder_manager import TrainingReminderManager

        context = get_context()
        data_dir = (
            context.config.data_dir if hasattr(context.config, "data_dir") else None
        )

        reminder_manager = TrainingReminderManager(data_dir=data_dir)

        # 更新配置
        reminder_manager.update_schedule(
            enabled=True,
            cron_expression=cron_expr,
            advance_minutes=advance_minutes,
            check_weather=check_weather,
            do_not_disturb_start=dnd_start,
            do_not_disturb_end=dnd_end,
        )

        print_status("训练提醒已启用", "success")
        console.print(f"  ⏰ Cron: {cron_expr}")
        console.print(f"  ⏱️ 提前: {advance_minutes} 分钟")
        console.print(f"  🌤️ 天气检查: {'开启' if check_weather else '关闭'}")
        console.print(f"  🌙 免打扰: {dnd_start} - {dnd_end}")

        console.print("\n  💡 提示：提醒将在Gateway服务启动后生效")
        console.print("     运行 nanobotrun gateway start 启动服务")

    except Exception as e:
        print_error(CLIError.execution_record_failed(f"启用失败：{e}"))
        raise typer.Exit(1)


@app.command(name="disable")
def disable_reminder() -> None:
    """禁用训练提醒

    示例：
        nanobotrun cron disable
    """
    try:
        from src.core.base.context import get_context
        from src.core.plan.training_reminder_manager import TrainingReminderManager

        context = get_context()
        data_dir = (
            context.config.data_dir if hasattr(context.config, "data_dir") else None
        )

        reminder_manager = TrainingReminderManager(data_dir=data_dir)
        reminder_manager.update_schedule(enabled=False)

        print_status("训练提醒已禁用", "success")

    except Exception as e:
        print_error(CLIError.execution_record_failed(f"禁用失败：{e}"))
        raise typer.Exit(1)


@app.command(name="trigger")
def trigger_reminder(
    force: bool = typer.Option(False, "--force", "-f", help="强制发送，忽略免打扰"),
) -> None:
    """手动触发训练提醒

    示例：
        nanobotrun cron trigger
        nanobotrun cron trigger --force
    """
    try:
        from src.core.base.context import get_context
        from src.core.plan.training_reminder_manager import TrainingReminderManager

        context = get_context()
        data_dir = (
            context.config.data_dir if hasattr(context.config, "data_dir") else None
        )

        reminder_manager = TrainingReminderManager(data_dir=data_dir)

        # 临时修改免打扰设置（如果强制发送）
        original_dnd_start = reminder_manager.schedule.do_not_disturb_start
        original_dnd_end = reminder_manager.schedule.do_not_disturb_end

        if force:
            # 设置一个不可能的免打扰时段来绕过检查
            reminder_manager.schedule.do_not_disturb_start = "00:00"
            reminder_manager.schedule.do_not_disturb_end = "00:01"

        try:
            result = reminder_manager.on_reminder_trigger()

            if result.get("sent"):
                print_status("训练提醒已发送", "success")
                console.print(f"  📝 {result['record']['message']}")
            elif result.get("reason") == "disabled":
                print_status("提醒功能已禁用", "warning")
                console.print("  使用 nanobotrun cron enable 启用提醒")
            elif result.get("reason") == "no_plan":
                print_status("今日无训练计划", "info")
            elif result.get("reason") == "do_not_disturb":
                print_status("免打扰时段，跳过提醒", "info")
                if not force:
                    console.print("  使用 --force 强制发送")
            else:
                print_status(
                    f"提醒未发送: {result.get('reason', '未知原因')}", "warning"
                )

        finally:
            # 恢复原始免打扰设置
            if force:
                reminder_manager.schedule.do_not_disturb_start = original_dnd_start
                reminder_manager.schedule.do_not_disturb_end = original_dnd_end

    except Exception as e:
        print_error(CLIError.execution_record_failed(f"触发失败：{e}"))
        raise typer.Exit(1)


@app.command(name="history")
def show_history(
    days: int = typer.Option(7, "--days", "-d", help="查看最近几天的记录"),
    clear: bool = typer.Option(False, "--clear", help="清理历史记录"),
) -> None:
    """查看或清理提醒历史

    示例：
        nanobotrun cron history
        nanobotrun cron history --days 30
        nanobotrun cron history --clear
    """
    try:
        from src.core.base.context import get_context
        from src.core.plan.training_reminder_manager import TrainingReminderManager

        context = get_context()
        data_dir = (
            context.config.data_dir if hasattr(context.config, "data_dir") else None
        )

        reminder_manager = TrainingReminderManager(data_dir=data_dir)

        if clear:
            removed = reminder_manager.clear_history(days=days)
            print_status(f"已清理 {removed} 条历史记录", "success")
            return

        history = reminder_manager.get_history(days=days)

        if not history:
            console.print(f"[yellow]最近 {days} 天无提醒记录[/yellow]")
            return

        console.print(f"[bold cyan]最近 {days} 天提醒历史[/bold cyan]")
        console.print("=" * 50)

        for record in history:
            status_emoji = {
                "sent": "✅",
                "skipped": "⏭️",
                "failed": "❌",
            }.get(record["status"], "❓")

            console.print(f"\n{status_emoji} {record['date']} - {record['id']}")
            console.print(f"   状态: {record['status']}")
            console.print(f"   消息: {record['message']}")
            if record.get("skip_reason"):
                console.print(f"   跳过原因: {record['skip_reason']}")
            if record.get("executed_at"):
                console.print(f"   执行时间: {record['executed_at']}")

    except Exception as e:
        print_error(CLIError.execution_record_failed(f"获取历史失败：{e}"))
        raise typer.Exit(1)
