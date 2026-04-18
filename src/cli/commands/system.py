# 系统相关命令
# 包含 version、init、migrate、validate 命令

from pathlib import Path

import typer

from src.cli.common import console

app = typer.Typer(help="系统管理命令")


@app.command()
def version() -> None:
    """显示版本信息"""
    from src import __version__

    console.print(f"[bold]Nanobot Runner[/bold] v{__version__}")


@app.command()
def init(
    force: bool = typer.Option(False, "--force", "-f", help="强制覆盖现有配置"),
    skip_optional: bool = typer.Option(False, "--skip-optional", help="跳过可选配置项"),
    workspace: str | None = typer.Option(
        None, "--workspace", "-w", help="指定 workspace 目录路径"
    ),
) -> None:
    """初始化工作区

    引导用户完成首次配置，创建目录结构和配置文件。
    支持首次安装和升级迁移两种场景。
    """
    from src.core.config import ConfigManager
    from src.core.init.models import InitMode
    from src.core.init.wizard import InitWizard

    config = ConfigManager(allow_default=True)
    wizard = InitWizard(config=config)

    workspace_dir = Path(workspace) if workspace else None

    console.print("[bold]Nanobot Runner 初始化向导[/bold]\n")

    env_info = wizard.detect_environment()
    console.print(
        f"[dim]Python {env_info.python_version} | {env_info.os_type} {env_info.os_version}[/dim]"
    )

    if env_info.missing_dependencies:
        console.print(
            f"[yellow]缺少依赖: {', '.join(env_info.missing_dependencies)}[/yellow]"
        )

    version_info = None
    try:
        from src.core.migrate.engine import MigrationEngine

        engine = MigrationEngine(config=config)
        version_info = engine.detect_old_version()
    except Exception:
        pass

    if version_info:
        console.print(f"\n[yellow]检测到旧版本: v{version_info.version}[/yellow]")
        console.print("[dim]将执行升级迁移[/dim]\n")
        mode = InitMode.MIGRATE
    else:
        mode = InitMode.FRESH

    result = wizard.run(
        mode=mode,
        force=force,
        skip_optional=skip_optional,
        workspace_dir=workspace_dir,
    )

    if result.success:
        console.print("\n[bold green]✓ 初始化完成！[/bold green]")
        if result.config_path:
            console.print(f"配置文件: [cyan]{result.config_path}[/cyan]")
        if result.env_path:
            console.print(f"环境变量: [cyan]{result.env_path}[/cyan]")

        if result.warnings:
            console.print("\n[yellow]警告:[/yellow]")
            for w in result.warnings:
                console.print(f"  [yellow]![/yellow] {w}")

        if result.next_steps:
            console.print("\n[bold]下一步:[/bold]")
            for step in result.next_steps:
                console.print(f"  {step}")
    else:
        console.print("\n[bold red]✗ 初始化失败[/bold red]")
        for err in result.errors:
            console.print(f"  [red]✗[/red] {err}")
        raise typer.Exit(code=1)


@app.command()
def migrate(
    auto: bool = typer.Option(False, "--auto", "-a", help="自动模式，跳过确认"),
    no_backup: bool = typer.Option(False, "--no-backup", help="跳过备份"),
) -> None:
    """迁移旧版本数据

    从旧版本（v0.8.x 或 v0.9.x）迁移配置和数据到当前版本。
    """
    from src.core.config import ConfigManager
    from src.core.migrate.engine import MigrationEngine

    config = ConfigManager(allow_default=True)
    engine = MigrationEngine(config=config)

    version_info = engine.detect_old_version()
    if version_info is None:
        console.print("[green]当前已是最新版本，无需迁移[/green]")
        return

    console.print(f"[bold]检测到旧版本: v{version_info.version}[/bold]")
    console.print(f"  配置路径: [dim]{version_info.config_path}[/dim]")
    console.print(f"  数据路径: [dim]{version_info.data_path}[/dim]")
    console.print(f"  包含数据: {'是' if version_info.has_data else '否'}")

    if not auto:
        confirm = typer.confirm("\n确认执行迁移？")
        if not confirm:
            console.print("[dim]迁移已取消[/dim]")
            return

    if not no_backup:
        console.print("\n[dim]创建备份...[/dim]")
        try:
            backup_info = engine.create_backup()
            console.print(f"[green]✓[/green] 备份已创建: {backup_info.backup_path}")
        except Exception as e:
            console.print(f"[yellow]![/yellow] 备份失败: {e}")
            if not auto and not typer.confirm("备份失败，是否继续迁移？"):
                return

    console.print("\n[dim]执行迁移...[/dim]")
    result = engine.migrate(auto=auto)

    if result.success:
        console.print("\n[bold green]✓ 迁移完成[/bold green]")
        console.print(f"  迁移文件: {result.migrated_files}")
        console.print(f"  耗时: {result.elapsed_time:.2f}s")

        if result.warnings:
            console.print("\n[yellow]警告:[/yellow]")
            for w in result.warnings:
                console.print(f"  [yellow]![/yellow] {w}")
    else:
        console.print("\n[bold red]✗ 迁移失败[/bold red]")
        for err in result.errors:
            console.print(f"  [red]✗[/red] {err}")
        raise typer.Exit(code=1)


@app.command()
def validate(
    connectivity: bool = typer.Option(
        False, "--connectivity", "-c", help="测试 API 连通性"
    ),
) -> None:
    """验证配置完整性

    检查配置文件的格式、完整性、有效性和一致性。
    """
    from src.core.config import ConfigManager
    from src.core.validate.validator import ConfigValidator

    config = ConfigManager(allow_default=True)
    validator = ConfigValidator(config=config)

    console.print("[bold]配置验证[/bold]\n")

    report = validator.validate_all()

    if report.is_valid:
        console.print("[bold green]✓ 配置验证通过[/bold green]")
    else:
        console.print("[bold red]✗ 配置验证失败[/bold red]")

    if report.errors:
        console.print(f"\n[red]错误 ({len(report.errors)}):[/red]")
        for err in report.errors:
            console.print(f"  [red]✗[/red] [{err.field}] {err.message}")
            if err.suggestion:
                console.print(f"    [dim]建议: {err.suggestion}[/dim]")

    if report.warnings:
        console.print(f"\n[yellow]警告 ({len(report.warnings)}):[/yellow]")
        for warn in report.warnings:
            console.print(f"  [yellow]![/yellow] [{warn.field}] {warn.message}")
            if warn.suggestion:
                console.print(f"    [dim]建议: {warn.suggestion}[/dim]")

    if report.summary:
        console.print(f"\n[dim]耗时: {report.elapsed_time:.3f}s[/dim]")

    if connectivity:
        console.print("\n[bold]API 连通性测试[/bold]")
        result = validator.test_api_connectivity()
        if result.is_connected:
            console.print(
                f"  [green]✓[/green] {result.provider} 连接正常 ({result.response_time:.2f}s)"
            )
        else:
            console.print(
                f"  [red]✗[/red] {result.provider} 连接失败: {result.error_message}"
            )

    if not report.is_valid:
        raise typer.Exit(code=1)
