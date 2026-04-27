# 技能管理命令
# 提供技能的列表、启用、禁用、导入等管理功能

from pathlib import Path

import typer

from src.cli.common import CLIError, console, print_error

app = typer.Typer(help="技能管理命令")


def _get_workspace_and_config() -> tuple[Path, Path]:
    """获取工作空间和config.json路径

    Returns:
        tuple[Path, Path]: (工作空间路径, config.json路径)
    """
    from src.core.context import AppContextFactory

    context = AppContextFactory.create()
    workspace = context.config.base_dir
    config_path = context.config.config_file
    return workspace, config_path


@app.command("list")
def list_skills() -> None:
    """列出所有可用技能

    显示技能名称、描述、状态等信息。
    """
    from src.core.skills.skill_manager import SkillManager

    try:
        workspace, config_path = _get_workspace_and_config()
        manager = SkillManager(workspace, config_path)
        skills = manager.list_skills()

        if not skills:
            console.print("[yellow]未发现任何技能[/yellow]")
            console.print("[dim]使用 'nanobotrun skill import' 导入自定义技能[/dim]")
            return

        console.print("[bold]可用技能列表[/bold]\n")

        for skill in skills:
            status_icon = "🟢" if skill.is_enabled else "🔴"
            console.print(
                f"  {status_icon} [bold]{skill.name}[/bold] [dim]v{skill.version}[/dim]"
            )
            console.print(f"    [dim]{skill.description}[/dim]")

            if skill.tags:
                tags_str = ", ".join(skill.tags)
                console.print(f"    [dim]标签: {tags_str}[/dim]")

            if skill.enabled_tools:
                tools_str = ", ".join(skill.enabled_tools)
                console.print(f"    [dim]工具: {tools_str}[/dim]")

            console.print()

        enabled_count = sum(1 for s in skills if s.is_enabled)
        disabled_count = len(skills) - enabled_count
        console.print(
            f"[dim]共 {len(skills)} 个技能 "
            f"(启用: {enabled_count}, 禁用: {disabled_count})[/dim]"
        )

    except Exception as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)


@app.command("enable")
def enable_skill(
    name: str = typer.Argument(..., help="技能名称"),
) -> None:
    """启用技能

    示例:
        nanobotrun skill enable weather-assistant
    """
    from src.core.skills.skill_manager import SkillManager

    try:
        workspace, config_path = _get_workspace_and_config()
        manager = SkillManager(workspace, config_path)

        if manager.get_skill(name) is None:
            console.print(f"[yellow]技能 '{name}' 不存在[/yellow]")
            raise typer.Exit(1)

        if manager.enable_skill(name):
            console.print(f"[green]✓[/green] 技能 '{name}' 已启用")
        else:
            console.print(f"[red]✗[/red] 技能 '{name}' 启用失败")
            raise typer.Exit(1)

    except typer.Exit:
        raise
    except Exception as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)


@app.command("disable")
def disable_skill(
    name: str = typer.Argument(..., help="技能名称"),
) -> None:
    """禁用技能

    示例:
        nanobotrun skill disable weather-assistant
    """
    from src.core.skills.skill_manager import SkillManager

    try:
        workspace, config_path = _get_workspace_and_config()
        manager = SkillManager(workspace, config_path)

        if manager.get_skill(name) is None:
            console.print(f"[yellow]技能 '{name}' 不存在[/yellow]")
            raise typer.Exit(1)

        if manager.disable_skill(name):
            console.print(f"[green]✓[/green] 技能 '{name}' 已禁用")
        else:
            console.print(f"[red]✗[/red] 技能 '{name}' 禁用失败")
            raise typer.Exit(1)

    except typer.Exit:
        raise
    except Exception as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)


@app.command("import")
def import_skill(
    skill_path_str: str = typer.Argument(
        ...,
        help="技能目录路径",
    ),
) -> None:
    """导入自定义技能

    从指定目录导入技能到工作空间。

    示例:
        nanobotrun skill import /path/to/skill
    """
    from src.core.skills.skill_manager import SkillManager

    try:
        skill_path = Path(skill_path_str).expanduser().resolve()
        if not skill_path.exists():
            console.print(f"[red]技能目录不存在: {skill_path}[/red]")
            raise typer.Exit(1)

        workspace, config_path = _get_workspace_and_config()
        manager = SkillManager(workspace, config_path)

        if manager.import_skill(skill_path):
            console.print("[green]✓[/green] 技能导入成功")
        else:
            console.print("[red]✗[/red] 技能导入失败")
            raise typer.Exit(1)

    except typer.Exit:
        raise
    except Exception as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)


@app.command("show")
def show_skill(
    name: str = typer.Argument(..., help="技能名称"),
) -> None:
    """显示技能详细信息

    示例:
        nanobotrun skill show weather-assistant
    """
    from src.core.skills.skill_manager import SkillManager

    try:
        workspace, config_path = _get_workspace_and_config()
        manager = SkillManager(workspace, config_path)

        skill = manager.get_skill(name)
        if skill is None:
            console.print(f"[yellow]技能 '{name}' 不存在[/yellow]")
            raise typer.Exit(1)

        console.print(f"[bold]{skill.name}[/bold] v{skill.version}\n")
        console.print(f"[dim]作者: {skill.author}[/dim]")
        console.print(f"[dim]状态: {skill.status.value}[/dim]")

        if skill.path:
            console.print(f"[dim]路径: {skill.path}[/dim]")

        console.print(f"\n{skill.description}")

        if skill.tags:
            console.print(f"\n[bold]标签:[/bold] {', '.join(skill.tags)}")

        if skill.dependencies:
            console.print("\n[bold]依赖:[/bold]")
            for dep in skill.dependencies:
                optional_str = " (可选)" if dep.optional else ""
                version_str = f" v{dep.version}" if dep.version else ""
                console.print(f"  • {dep.name}{version_str}{optional_str}")

        if skill.enabled_tools:
            console.print(
                f"\n[bold]启用的工具:[/bold] {', '.join(skill.enabled_tools)}"
            )

        content = manager.get_skill_content(name)
        if content:
            console.print("\n[bold]技能内容:[/bold]")
            console.print("[dim]" + "─" * 40 + "[/dim]")
            lines = content.split("\n")
            if len(lines) > 20:
                console.print("\n".join(lines[:20]))
                console.print(f"[dim]... (共 {len(lines)} 行)[/dim]")
            else:
                console.print(content)

    except typer.Exit:
        raise
    except Exception as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)
