# CLI App 入口
# 组合所有命令模块

import typer

from src.cli.commands import (
    agent_app,
    analysis_app,
    data_app,
    gateway_app,
    plan_app,
    preference_app,
    report_app,
    skill_app,
    system_app,
    tools_app,
    transparency_app,
)

app = typer.Typer(
    name="nanobotrun",
    help="Nanobot Runner - 本地跑步数据助理",
    add_completion=False,
)

app.add_typer(data_app, name="data")
app.add_typer(analysis_app, name="analysis")
app.add_typer(agent_app, name="agent")
app.add_typer(report_app, name="report")
app.add_typer(system_app, name="system")
app.add_typer(gateway_app, name="gateway")
app.add_typer(plan_app, name="plan")
app.add_typer(tools_app, name="tools")
app.add_typer(skill_app, name="skill")
app.add_typer(preference_app, name="preference")
app.add_typer(transparency_app, name="transparency")

if __name__ == "__main__":
    app()
