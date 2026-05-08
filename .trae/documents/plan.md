# CRITICAL-1 修复实施计划：补充 CLI 命令与 Agent 工具

> **目标**: 补充实现缺失的 CLI 命令（status today/weekly、analysis hrv/hr-recovery/fatigue/recovery/compare）和 Agent 工具（6个身体信号工具），使代码与文档一致。
> **架构**: 基于已实现的 `src/core/body_signal/` 核心引擎，补充 CLI 命令层和 Agent 工具层封装。
> **技术栈**: Python 3.11+, Typer, Rich, Polars

---

## 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/cli/commands/status.py` | 新建 | status today / status weekly 命令 |
| `src/cli/commands/analysis.py` | 修改 | 新增 hrv / hr-recovery / fatigue / recovery / compare 子命令 |
| `src/cli/commands/__init__.py` | 修改 | 导出 status_app |
| `src/cli/app.py` | 修改 | 注册 status 命令组 |
| `src/cli/handlers/status_handler.py` | 新建 | status 命令业务逻辑 Handler |
| `src/cli/handlers/analysis_handler.py` | 修改 | 新增身体信号分析方法 |
| `src/agents/tools.py` | 修改 | 新增 6 个身体信号工具类及 RunnerTools 方法 |

---

## Task 1: 新建 `src/cli/handlers/status_handler.py`

**说明**: 封装 `status today` 和 `status weekly` 的业务逻辑，通过 BodySignalEngine 获取身体信号摘要。

```python
# 状态查看 Handler
# 负责今日/本周身体状态的业务逻辑调用

from typing import Any

from src.core.base.context import AppContext, AppContextFactory
from src.core.body_signal import BodySignalEngine
from src.core.body_signal.fatigue_assessor import FatigueAssessor
from src.core.body_signal.hrv_analyzer import HRVAnalyzer
from src.core.body_signal.recovery_monitor import RecoveryMonitor


class StatusHandler:
    """状态查看业务逻辑"""

    def __init__(self, context: AppContext | None = None) -> None:
        if context is None:
            context = AppContextFactory.create()

        self.context = context
        self._engine: BodySignalEngine | None = None

    def _get_engine(self) -> BodySignalEngine:
        """获取或创建 BodySignalEngine 实例"""
        if self._engine is None:
            hrv_analyzer = HRVAnalyzer(session_repo=self.context.session_repo)
            from src.core.calculators.training_load_analyzer import TrainingLoadAnalyzer
            training_load_analyzer = TrainingLoadAnalyzer()
            fatigue_assessor = FatigueAssessor(
                session_repo=self.context.session_repo,
                training_load_analyzer=training_load_analyzer,
            )
            recovery_monitor = RecoveryMonitor(
                session_repo=self.context.session_repo,
                training_load_analyzer=training_load_analyzer,
                hrv_analyzer=hrv_analyzer,
            )
            self._engine = BodySignalEngine(
                hrv_analyzer=hrv_analyzer,
                fatigue_assessor=fatigue_assessor,
                recovery_monitor=recovery_monitor,
            )
        return self._engine

    def get_today_status(self) -> dict[str, Any]:
        """获取今日身体状态"""
        engine = self._get_engine()
        summary = engine.get_daily_summary()
        return summary.to_dict()

    def get_weekly_status(self) -> dict[str, Any]:
        """获取本周身体状态"""
        engine = self._get_engine()
        summary = engine.get_weekly_summary()
        return summary.to_dict()
```

---

## Task 2: 新建 `src/cli/commands/status.py`

**说明**: 实现 `status today` 和 `status weekly` CLI 命令，使用 Rich 格式化输出。

```python
# 状态查看命令
# 包含 today 和 weekly 命令

import typer
from rich.panel import Panel
from rich.table import Table

from src.cli.common import CLIError, console, print_error
from src.cli.handlers.status_handler import StatusHandler

app = typer.Typer(help="身体状态查看命令")


@app.command()
def today() -> None:
    """
    查看今日身体状态

    示例:
        nanobotrun status today
    """
    try:
        handler = StatusHandler()
        result = handler.get_today_status()

        recovery_status = result.get("recovery_status", "未知")
        fatigue_score = result.get("fatigue_score", 0.0)
        data_quality = result.get("data_quality", "empty")
        daily_summary = result.get("daily_summary", "")
        training_advice = result.get("training_advice", "")
        alerts = result.get("alerts", [])

        status_color = {"green": "green", "yellow": "yellow", "red": "red"}.get(
            recovery_status, "white"
        )

        panel_content = (
            f"[bold]恢复状态:[/bold] [{status_color}]{recovery_status}[/{status_color}]\n"
            f"[bold]疲劳度评分:[/bold] {fatigue_score:.1f}/100\n"
            f"[bold]数据质量:[/bold] {data_quality}\n"
            f"[bold]训练建议:[/bold] {training_advice}"
        )

        if alerts:
            panel_content += "\n\n[bold]⚠️ 预警:[/bold]"
            for alert in alerts:
                severity_color = {"critical": "red", "warning": "yellow"}.get(
                    alert.get("severity", ""), "white"
                )
                panel_content += f"\n  [{severity_color}]• {alert.get('message', '')}[/{severity_color}]"

        panel = Panel(
            panel_content,
            title=f"[Body Status] {daily_summary}",
            border_style="blue",
        )
        console.print(panel)

    except Exception as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)


@app.command()
def weekly() -> None:
    """
    查看本周身体状态摘要

    示例:
        nanobotrun status weekly
    """
    try:
        handler = StatusHandler()
        result = handler.get_weekly_status()

        recovery_status = result.get("recovery_status", "未知")
        fatigue_score = result.get("fatigue_score", 0.0)
        data_quality = result.get("data_quality", "empty")
        daily_summary = result.get("daily_summary", "")
        training_advice = result.get("training_advice", "")
        alerts = result.get("alerts", [])

        status_color = {"green": "green", "yellow": "yellow", "red": "red"}.get(
            recovery_status, "white"
        )

        panel_content = (
            f"[bold]恢复状态:[/bold] [{status_color}]{recovery_status}[/{status_color}]\n"
            f"[bold]疲劳度评分:[/bold] {fatigue_score:.1f}/100\n"
            f"[bold]数据质量:[/bold] {data_quality}\n"
            f"[bold]训练建议:[/bold] {training_advice}"
        )

        if alerts:
            panel_content += "\n\n[bold]⚠️ 预警:[/bold]"
            for alert in alerts:
                severity_color = {"critical": "red", "warning": "yellow"}.get(
                    alert.get("severity", ""), "white"
                )
                panel_content += f"\n  [{severity_color}]• {alert.get('message', '')}[/{severity_color}]"

        panel = Panel(
            panel_content,
            title=f"[Body Status] {daily_summary}",
            border_style="blue",
        )
        console.print(panel)

    except Exception as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)
```

---

## Task 3: 修改 `src/cli/handlers/analysis_handler.py`

**说明**: 新增身体信号分析方法（HRV、心率恢复、疲劳度、恢复状态、训练周期对比）。

```python
# 在现有 AnalysisHandler 类中新增以下方法

    def get_hrv_analysis(self, days: int = 30) -> dict[str, Any]:
        """获取HRV分析结果"""
        from src.core.body_signal.hrv_analyzer import HRVAnalyzer
        from src.core.body_signal.models import HRVDataSource

        hrv_analyzer = HRVAnalyzer(session_repo=self.context.session_repo)
        hrv_result = hrv_analyzer.analyze_hrv(days=days)
        hrv_metrics = hrv_analyzer.estimate_hrv_metrics()

        result = hrv_result.to_dict()
        result["estimated_hrv_metrics"] = hrv_metrics
        return result

    def get_hr_recovery(self) -> dict[str, Any]:
        """获取心率恢复分析"""
        from src.core.body_signal.hrv_analyzer import HRVAnalyzer

        hrv_analyzer = HRVAnalyzer(session_repo=self.context.session_repo)
        recovery_result = hrv_analyzer.analyze_hr_recovery()
        return recovery_result.to_dict()

    def get_fatigue_score(self, rpe: int | None = None) -> dict[str, Any]:
        """获取疲劳度评估"""
        from src.core.body_signal.fatigue_assessor import FatigueAssessor
        from src.core.calculators.training_load_analyzer import TrainingLoadAnalyzer

        training_load_analyzer = TrainingLoadAnalyzer()
        fatigue_assessor = FatigueAssessor(
            session_repo=self.context.session_repo,
            training_load_analyzer=training_load_analyzer,
        )
        fatigue_result = fatigue_assessor.assess_fatigue(rpe=rpe)
        return fatigue_result.to_dict()

    def get_recovery_status(self) -> dict[str, Any]:
        """获取恢复状态"""
        from src.core.body_signal.hrv_analyzer import HRVAnalyzer
        from src.core.body_signal.recovery_monitor import RecoveryMonitor
        from src.core.calculators.training_load_analyzer import TrainingLoadAnalyzer

        training_load_analyzer = TrainingLoadAnalyzer()
        hrv_analyzer = HRVAnalyzer(session_repo=self.context.session_repo)
        recovery_monitor = RecoveryMonitor(
            session_repo=self.context.session_repo,
            training_load_analyzer=training_load_analyzer,
            hrv_analyzer=hrv_analyzer,
        )
        recovery_result = recovery_monitor.get_recovery_status()
        return recovery_result.to_dict()

    def compare_training_periods(
        self, period1_days: int = 7, period2_days: int = 7
    ) -> dict[str, Any]:
        """对比两个训练周期的身体信号变化"""
        from src.core.body_signal.hrv_analyzer import HRVAnalyzer
        from src.core.body_signal.recovery_monitor import RecoveryMonitor
        from src.core.calculators.training_load_analyzer import TrainingLoadAnalyzer

        training_load_analyzer = TrainingLoadAnalyzer()
        hrv_analyzer = HRVAnalyzer(session_repo=self.context.session_repo)
        recovery_monitor = RecoveryMonitor(
            session_repo=self.context.session_repo,
            training_load_analyzer=training_load_analyzer,
            hrv_analyzer=hrv_analyzer,
        )

        # 获取最近两个周期的恢复趋势
        trend1 = recovery_monitor.get_recovery_trend(days=period1_days)
        trend2 = recovery_monitor.get_recovery_trend(days=period2_days + period1_days)
        # 取更早的 period2_days 数据
        trend2 = trend2[:-period1_days] if len(trend2) > period1_days else []

        avg_tsb1 = sum(p.tsb for p in trend1) / len(trend1) if trend1 else 0.0
        avg_tsb2 = sum(p.tsb for p in trend2) / len(trend2) if trend2 else 0.0

        hrv1 = hrv_analyzer.analyze_hrv(days=period1_days)
        hrv2 = hrv_analyzer.analyze_hrv(days=period2_days + period1_days)

        return {
            "period1_days": period1_days,
            "period2_days": period2_days,
            "period1": {
                "avg_tsb": round(avg_tsb1, 2),
                "data_points": len(trend1),
                "hrv_data_quality": hrv1.data_quality.value,
            },
            "period2": {
                "avg_tsb": round(avg_tsb2, 2),
                "data_points": len(trend2),
                "hrv_data_quality": hrv2.data_quality.value,
            },
            "tsb_change": round(avg_tsb1 - avg_tsb2, 2),
            "comparison_summary": (
                "近期恢复状态改善" if avg_tsb1 > avg_tsb2 else "近期恢复状态下降"
            ),
        }
```

---

## Task 4: 修改 `src/cli/commands/analysis.py`

**说明**: 在现有 analysis.py 中新增 `hrv`、`hr-recovery`、`fatigue`、`recovery`、`compare` 五个子命令。

```python
# 在现有文件末尾追加以下命令

@app.command()
def hrv(
    days: int = typer.Option(30, "--days", "-d", help="分析天数（7/30/90）"),
) -> None:
    """
    查看HRV（心率变异）分析

    示例:
        nanobotrun analysis hrv
        nanobotrun analysis hrv --days 7
    """
    try:
        handler = AnalysisHandler()
        console.print(f"[bold]HRV分析[/bold] (最近 {days} 天)")

        result = handler.get_hrv_analysis(days=days)

        data_quality = result.get("data_quality", "empty")
        if data_quality == "empty":
            console.print("[yellow]暂无HRV数据[/yellow]")
            console.print("[dim]提示: 需要导入包含心率数据的跑步记录[/dim]")
            return

        trend = result.get("resting_hr_trend", [])
        hrv_metrics = result.get("estimated_hrv_metrics", {})

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("日期", width=12)
        table.add_column("静息心率", width=10)
        table.add_column("偏差", width=10)

        for point in trend[-10:]:
            deviation = point.get("deviation_pct", 0.0)
            deviation_str = f"{deviation:+.1f}%"
            deviation_color = (
                "green" if abs(deviation) < 5 else "yellow" if abs(deviation) < 10 else "red"
            )
            table.add_row(
                point.get("date", "N/A"),
                f"{point.get('resting_hr', 0):.0f} bpm",
                f"[{deviation_color}]{deviation_str}[/{deviation_color}]",
            )

        console.print(table)

        if hrv_metrics:
            rmssd = hrv_metrics.get("estimated_rmssd")
            sdnn = hrv_metrics.get("estimated_sdnn")
            source = hrv_metrics.get("data_source", "未知")
            console.print(f"\n[bold]HRV指标[/bold] (来源: {source})")
            if rmssd:
                console.print(f"  RMSSD: {rmssd:.2f} ms")
            if sdnn:
                console.print(f"  SDNN: {sdnn:.2f} ms")

    except Exception as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)


@app.command(name="hr-recovery")
def hr_recovery() -> None:
    """
    查看心率恢复分析

    示例:
        nanobotrun analysis hr-recovery
    """
    try:
        handler = AnalysisHandler()
        console.print("[bold]心率恢复分析[/bold]")

        result = handler.get_hr_recovery()

        data_quality = result.get("data_quality", "empty")
        if data_quality == "empty":
            console.print("[yellow]暂无心率恢复数据[/yellow]")
            return

        hr_end = result.get("hr_end", 0.0)
        hr_recovery_1min = result.get("hr_recovery_1min")

        panel = Panel(
            f"[bold]训练结束心率:[/bold] {hr_end:.0f} bpm\n"
            + (
                f"[bold]1分钟恢复:[/bold] {hr_recovery_1min:.0f} bpm"
                if hr_recovery_1min
                else "[dim]1分钟恢复数据不可用[/dim]"
            ),
            title="[HR Recovery] 心率恢复",
            border_style="blue",
        )
        console.print(panel)

    except Exception as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)


@app.command()
def fatigue(
    rpe: int | None = typer.Option(None, "--rpe", help="主观疲劳度 (1-10)"),
) -> None:
    """
    查看疲劳度评估

    示例:
        nanobotrun analysis fatigue
        nanobotrun analysis fatigue --rpe 7
    """
    try:
        handler = AnalysisHandler()
        console.print("[bold]疲劳度评估[/bold]")

        result = handler.get_fatigue_score(rpe=rpe)

        data_quality = result.get("data_quality", "empty")
        if data_quality == "empty":
            console.print("[yellow]暂无训练数据[/yellow]")
            console.print("[dim]提示: 需要导入跑步数据后才能评估疲劳度[/dim]")
            return

        fatigue_score = result.get("fatigue_score", 0.0)
        recovery_status = result.get("recovery_status", "未知")
        consecutive_days = result.get("consecutive_hard_days", 0)
        recommendation = result.get("recommendation", "")
        breakdown = result.get("breakdown", {})

        status_color = {"green": "green", "yellow": "yellow", "red": "red"}.get(
            recovery_status, "white"
        )
        score_color = "green" if fatigue_score < 40 else "yellow" if fatigue_score < 70 else "red"

        panel = Panel(
            f"[bold]疲劳度评分:[/bold] [{score_color}]{fatigue_score:.1f}/100[/{score_color}]\n"
            f"[bold]恢复状态:[/bold] [{status_color}]{recovery_status}[/{status_color}]\n"
            f"[bold]连续高强度天数:[/bold] {consecutive_days} 天\n"
            f"[bold]建议:[/bold] {recommendation}\n\n"
            f"[bold]疲劳度分解:[/bold]\n"
            f"  ATL负荷: {breakdown.get('atl_component', 0):.1f}\n"
            f"  心率偏差: {breakdown.get('hr_deviation_component', 0):.1f}\n"
            f"  连续训练: {breakdown.get('consecutive_component', 0):.1f}\n"
            f"  主观疲劳: {breakdown.get('subjective_component', 0):.1f}",
            title="[Fatigue] 疲劳度评估",
            border_style="blue",
        )
        console.print(panel)

    except Exception as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)


@app.command()
def recovery() -> None:
    """
    查看恢复状态

    示例:
        nanobotrun analysis recovery
    """
    try:
        handler = AnalysisHandler()
        console.print("[bold]恢复状态分析[/bold]")

        result = handler.get_recovery_status()

        data_quality = result.get("data_quality", "empty")
        if data_quality == "empty":
            console.print("[yellow]暂无恢复状态数据[/yellow]")
            return

        recovery_status = result.get("recovery_status", "未知")
        rest_day_effect = result.get("rest_day_effect", {})

        status_color = {"green": "green", "yellow": "yellow", "red": "red"}.get(
            recovery_status, "white"
        )

        panel = Panel(
            f"[bold]恢复状态:[/bold] [{status_color}]{recovery_status}[/{status_color}]\n"
            f"[bold]休息日效果:[/bold] {rest_day_effect.get('effect_level', '未知')}\n"
            f"[bold]静息心率变化:[/bold] {rest_day_effect.get('resting_hr_change_pct', 0):+.1f}%\n"
            f"[bold]说明:[/bold] {rest_day_effect.get('message', '')}",
            title="[Recovery] 恢复状态",
            border_style="blue",
        )
        console.print(panel)

    except Exception as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)


@app.command()
def compare(
    period1: int = typer.Option(7, "--period1", "-p1", help="近期周期天数"),
    period2: int = typer.Option(7, "--period2", "-p2", help="对比周期天数"),
) -> None:
    """
    对比两个训练周期的身体信号变化

    示例:
        nanobotrun analysis compare
        nanobotrun analysis compare --period1 7 --period2 14
    """
    try:
        handler = AnalysisHandler()
        console.print(f"[bold]训练周期对比[/bold] (近期 {period1} 天 vs 之前 {period2} 天)")

        result = handler.compare_training_periods(
            period1_days=period1, period2_days=period2
        )

        period1_data = result.get("period1", {})
        period2_data = result.get("period2", {})
        tsb_change = result.get("tsb_change", 0.0)
        summary = result.get("comparison_summary", "")

        change_color = "green" if tsb_change > 0 else "red" if tsb_change < 0 else "white"

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("指标", width=15)
        table.add_column(f"近期 ({period1}天)", width=15)
        table.add_column(f"之前 ({period2}天)", width=15)
        table.add_column("变化", width=12)

        table.add_row(
            "平均TSB",
            f"{period1_data.get('avg_tsb', 0):.1f}",
            f"{period2_data.get('avg_tsb', 0):.1f}",
            f"[{change_color}]{tsb_change:+.1f}[/{change_color}]",
        )
        table.add_row(
            "数据点数",
            str(period1_data.get("data_points", 0)),
            str(period2_data.get("data_points", 0)),
            "--",
        )

        console.print(table)
        console.print(f"\n[bold]总结:[/bold] {summary}")

    except Exception as e:
        print_error(CLIError.storage_error(str(e)))
        raise typer.Exit(1)
```

---

## Task 5: 修改 `src/cli/commands/__init__.py`

**说明**: 导入并导出 `status_app`。

```python
# 在文件顶部新增导入
from src.cli.commands.status import app as status_app

# 在 __all__ 列表中新增
__all__ = [
    # ... 现有项 ...
    "status_app",
]
```

---

## Task 6: 修改 `src/cli/app.py`

**说明**: 注册 status 命令组。

```python
# 在导入列表中新增
from src.cli.commands import status_app

# 在 app.add_typer 调用中新增
app.add_typer(status_app, name="status")
```

---

## Task 7: 修改 `src/agents/tools.py`

**说明**: 在 `RunnerTools` 类中新增 6 个身体信号方法，并创建对应的 6 个 Agent 工具类，最后注册到 `create_tools()` 和 `TOOL_DESCRIPTIONS` 中。

### 7.1 RunnerTools 新增方法

在 `RunnerTools` 类末尾（`ask_rpe_in_cli` 方法之后）新增以下 6 个方法：

```python
    def get_hrv_analysis(self, days: int = 30) -> dict[str, Any]:
        """获取HRV分析结果 - v0.19.0新增"""
        try:
            from src.core.body_signal.hrv_analyzer import HRVAnalyzer

            hrv_analyzer = HRVAnalyzer(session_repo=self.storage)
            hrv_result = hrv_analyzer.analyze_hrv(days=days)
            hrv_metrics = hrv_analyzer.estimate_hrv_metrics()

            result = hrv_result.to_dict()
            result["estimated_hrv_metrics"] = hrv_metrics
            return {"success": True, "data": result}
        except Exception as e:
            logger.error(f"HRV分析失败: {e}")
            return {"success": False, "error": str(e)}

    def get_hr_recovery(self) -> dict[str, Any]:
        """获取心率恢复分析 - v0.19.0新增"""
        try:
            from src.core.body_signal.hrv_analyzer import HRVAnalyzer

            hrv_analyzer = HRVAnalyzer(session_repo=self.storage)
            recovery_result = hrv_analyzer.analyze_hr_recovery()
            return {"success": True, "data": recovery_result.to_dict()}
        except Exception as e:
            logger.error(f"心率恢复分析失败: {e}")
            return {"success": False, "error": str(e)}

    def get_fatigue_score(self, rpe: int | None = None) -> dict[str, Any]:
        """获取疲劳度评估 - v0.19.0新增"""
        try:
            from src.core.body_signal.fatigue_assessor import FatigueAssessor
            from src.core.calculators.training_load_analyzer import TrainingLoadAnalyzer

            training_load_analyzer = TrainingLoadAnalyzer()
            fatigue_assessor = FatigueAssessor(
                session_repo=self.storage,
                training_load_analyzer=training_load_analyzer,
            )
            fatigue_result = fatigue_assessor.assess_fatigue(rpe=rpe)
            return {"success": True, "data": fatigue_result.to_dict()}
        except Exception as e:
            logger.error(f"疲劳度评估失败: {e}")
            return {"success": False, "error": str(e)}

    def get_recovery_status(self) -> dict[str, Any]:
        """获取恢复状态 - v0.19.0新增"""
        try:
            from src.core.body_signal.hrv_analyzer import HRVAnalyzer
            from src.core.body_signal.recovery_monitor import RecoveryMonitor
            from src.core.calculators.training_load_analyzer import TrainingLoadAnalyzer

            training_load_analyzer = TrainingLoadAnalyzer()
            hrv_analyzer = HRVAnalyzer(session_repo=self.storage)
            recovery_monitor = RecoveryMonitor(
                session_repo=self.storage,
                training_load_analyzer=training_load_analyzer,
                hrv_analyzer=hrv_analyzer,
            )
            recovery_result = recovery_monitor.get_recovery_status()
            return {"success": True, "data": recovery_result.to_dict()}
        except Exception as e:
            logger.error(f"恢复状态获取失败: {e}")
            return {"success": False, "error": str(e)}

    def get_body_signal_summary(self, period: str = "daily") -> dict[str, Any]:
        """获取身体信号综合摘要 - v0.19.0新增"""
        try:
            from src.core.body_signal import BodySignalEngine
            from src.core.body_signal.fatigue_assessor import FatigueAssessor
            from src.core.body_signal.hrv_analyzer import HRVAnalyzer
            from src.core.body_signal.recovery_monitor import RecoveryMonitor
            from src.core.calculators.training_load_analyzer import TrainingLoadAnalyzer

            training_load_analyzer = TrainingLoadAnalyzer()
            hrv_analyzer = HRVAnalyzer(session_repo=self.storage)
            fatigue_assessor = FatigueAssessor(
                session_repo=self.storage,
                training_load_analyzer=training_load_analyzer,
            )
            recovery_monitor = RecoveryMonitor(
                session_repo=self.storage,
                training_load_analyzer=training_load_analyzer,
                hrv_analyzer=hrv_analyzer,
            )
            engine = BodySignalEngine(
                hrv_analyzer=hrv_analyzer,
                fatigue_assessor=fatigue_assessor,
                recovery_monitor=recovery_monitor,
            )

            if period == "weekly":
                summary = engine.get_weekly_summary()
            else:
                summary = engine.get_daily_summary()

            return {"success": True, "data": summary.to_dict()}
        except Exception as e:
            logger.error(f"身体信号摘要获取失败: {e}")
            return {"success": False, "error": str(e)}

    def compare_training_periods(
        self, period1_days: int = 7, period2_days: int = 7
    ) -> dict[str, Any]:
        """对比两个训练周期的身体信号变化 - v0.19.0新增"""
        try:
            from src.core.body_signal.hrv_analyzer import HRVAnalyzer
            from src.core.body_signal.recovery_monitor import RecoveryMonitor
            from src.core.calculators.training_load_analyzer import TrainingLoadAnalyzer

            training_load_analyzer = TrainingLoadAnalyzer()
            hrv_analyzer = HRVAnalyzer(session_repo=self.storage)
            recovery_monitor = RecoveryMonitor(
                session_repo=self.storage,
                training_load_analyzer=training_load_analyzer,
                hrv_analyzer=hrv_analyzer,
            )

            trend1 = recovery_monitor.get_recovery_trend(days=period1_days)
            trend2 = recovery_monitor.get_recovery_trend(days=period2_days + period1_days)
            trend2 = trend2[:-period1_days] if len(trend2) > period1_days else []

            avg_tsb1 = sum(p.tsb for p in trend1) / len(trend1) if trend1 else 0.0
            avg_tsb2 = sum(p.tsb for p in trend2) / len(trend2) if trend2 else 0.0

            hrv1 = hrv_analyzer.analyze_hrv(days=period1_days)
            hrv2 = hrv_analyzer.analyze_hrv(days=period2_days + period1_days)

            return {
                "success": True,
                "data": {
                    "period1_days": period1_days,
                    "period2_days": period2_days,
                    "period1": {
                        "avg_tsb": round(avg_tsb1, 2),
                        "data_points": len(trend1),
                        "hrv_data_quality": hrv1.data_quality.value,
                    },
                    "period2": {
                        "avg_tsb": round(avg_tsb2, 2),
                        "data_points": len(trend2),
                        "hrv_data_quality": hrv2.data_quality.value,
                    },
                    "tsb_change": round(avg_tsb1 - avg_tsb2, 2),
                    "comparison_summary": (
                        "近期恢复状态改善" if avg_tsb1 > avg_tsb2 else "近期恢复状态下降"
                    ),
                },
            }
        except Exception as e:
            logger.error(f"训练周期对比失败: {e}")
            return {"success": False, "error": str(e)}
```

### 7.2 新增 6 个 Agent 工具类

在 `ParseUserConfirmTool` 类之后、`SpawnSubagentTool` 类之前插入以下 6 个工具类：

```python
class GetHrvAnalysisTool(BaseTool):
    """获取HRV分析工具 - v0.19.0新增"""

    @property
    def name(self) -> str:
        return "get_hrv_analysis"

    @property
    def description(self) -> str:
        return "获取HRV（心率变异）分析结果，包括静息心率趋势和估算的HRV指标（RMSSD/SDNN）。当用户询问'HRV是多少'、'心率变异分析'、'静息心率趋势'时使用此工具。"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "分析天数（默认30天）",
                    "default": 30,
                }
            },
        }

    async def execute(self, **kwargs: Any) -> str:
        days = kwargs.get("days", 30)
        return self._run_sync(self.runner_tools.get_hrv_analysis, days)


class GetHrRecoveryTool(BaseTool):
    """获取心率恢复分析工具 - v0.19.0新增"""

    @property
    def name(self) -> str:
        return "get_hr_recovery"

    @property
    def description(self) -> str:
        return "获取心率恢复分析结果，评估训练后心率下降速率和心脏恢复能力。当用户询问'心率恢复'、'恢复能力'时使用此工具。"

    @property
    def parameters(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}}

    async def execute(self, **kwargs: Any) -> str:
        return self._run_sync(self.runner_tools.get_hr_recovery)


class GetFatigueScoreTool(BaseTool):
    """获取疲劳度评估工具 - v0.19.0新增"""

    @property
    def name(self) -> str:
        return "get_fatigue_score"

    @property
    def description(self) -> str:
        return "获取疲劳度评估结果，综合训练负荷、心率偏差、连续训练天数等维度计算疲劳度分数。当用户询问'我累不累'、'疲劳度'、'身体状态'时使用此工具。"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "rpe": {
                    "type": "integer",
                    "description": "主观疲劳度 (1-10)，可选",
                }
            },
        }

    async def execute(self, **kwargs: Any) -> str:
        rpe = kwargs.get("rpe")
        return self._run_sync(self.runner_tools.get_fatigue_score, rpe)


class GetRecoveryStatusTool(BaseTool):
    """获取恢复状态工具 - v0.19.0新增"""

    @property
    def name(self) -> str:
        return "get_recovery_status"

    @property
    def description(self) -> str:
        return "获取恢复状态评估，包括TSB变化、休息日效果和恢复趋势。当用户询问'恢复得怎么样'、'今天能训练吗'时使用此工具。"

    @property
    def parameters(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}}

    async def execute(self, **kwargs: Any) -> str:
        return self._run_sync(self.runner_tools.get_recovery_status)


class GetBodySignalSummaryTool(BaseTool):
    """获取身体信号综合摘要工具 - v0.19.0新增"""

    @property
    def name(self) -> str:
        return "get_body_signal_summary"

    @property
    def description(self) -> str:
        return "获取身体信号综合摘要，整合HRV、疲劳度和恢复状态三个维度生成每日或每周摘要。当用户询问'今天状态怎么样'、'身体信号'、'综合状态'时使用此工具。"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "description": "周期类型（daily/weekly，默认daily）",
                    "enum": ["daily", "weekly"],
                    "default": "daily",
                }
            },
        }

    async def execute(self, **kwargs: Any) -> str:
        period = kwargs.get("period", "daily")
        return self._run_sync(self.runner_tools.get_body_signal_summary, period)


class CompareTrainingPeriodsTool(BaseTool):
    """对比训练周期工具 - v0.19.0新增"""

    @property
    def name(self) -> str:
        return "compare_training_periods"

    @property
    def description(self) -> str:
        return "对比两个训练周期的身体信号变化，分析恢复状态趋势。当用户询问'最近状态有没有变好'、'对比上周'、'训练趋势'时使用此工具。"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "period1_days": {
                    "type": "integer",
                    "description": "近期周期天数（默认7天）",
                    "default": 7,
                },
                "period2_days": {
                    "type": "integer",
                    "description": "对比周期天数（默认7天）",
                    "default": 7,
                },
            },
        }

    async def execute(self, **kwargs: Any) -> str:
        period1_days = kwargs.get("period1_days", 7)
        period2_days = kwargs.get("period2_days", 7)
        return self._run_sync(
            self.runner_tools.compare_training_periods, period1_days, period2_days
        )
```

### 7.3 注册到 create_tools()

在 `create_tools()` 函数返回列表中，在 `GetTransparencyInsightTool` 之后添加：

```python
        GetHrvAnalysisTool(runner_tools),
        GetHrRecoveryTool(runner_tools),
        GetFatigueScoreTool(runner_tools),
        GetRecoveryStatusTool(runner_tools),
        GetBodySignalSummaryTool(runner_tools),
        CompareTrainingPeriodsTool(runner_tools),
```

### 7.4 注册到 TOOL_DESCRIPTIONS

在 `TOOL_DESCRIPTIONS` 字典末尾添加：

```python
    "get_hrv_analysis": {
        "description": "获取HRV（心率变异）分析结果，包括静息心率趋势和估算的HRV指标（RMSSD/SDNN）。当用户询问'HRV是多少'、'心率变异分析'时使用此工具。返回JSON格式：{success: true, data: {resting_hr_trend: [{date, resting_hr, deviation_pct}], data_quality, data_source, estimated_hrv_metrics: {estimated_rmssd, estimated_sdnn, data_source}}} 或 {success: false, error: 错误信息}",
        "parameters": {"days": "分析天数（默认30天）"},
    },
    "get_hr_recovery": {
        "description": "获取心率恢复分析结果，评估训练后心率下降速率和心脏恢复能力。当用户询问'心率恢复'、'恢复能力'时使用此工具。返回JSON格式：{success: true, data: {hr_end, hr_recovery_1min, data_quality}} 或 {success: false, error: 错误信息}",
        "parameters": {},
    },
    "get_fatigue_score": {
        "description": "获取疲劳度评估结果，综合训练负荷、心率偏差、连续训练天数等维度计算疲劳度分数。当用户询问'我累不累'、'疲劳度'时使用此工具。返回JSON格式：{success: true, data: {fatigue_score, recovery_status, consecutive_hard_days, breakdown: {atl_component, hr_deviation_component, consecutive_component, subjective_component}, recommendation, data_quality}} 或 {success: false, error: 错误信息}",
        "parameters": {"rpe": "主观疲劳度 (1-10，可选)"},
    },
    "get_recovery_status": {
        "description": "获取恢复状态评估，包括TSB变化、休息日效果和恢复趋势。当用户询问'恢复得怎么样'、'今天能训练吗'时使用此工具。返回JSON格式：{success: true, data: {recovery_status, rest_day_effect: {resting_hr_change_pct, tsb_change, effect_level, message}, recovery_trend: [{date, tsb, ctl}], data_quality}} 或 {success: false, error: 错误信息}",
        "parameters": {},
    },
    "get_body_signal_summary": {
        "description": "获取身体信号综合摘要，整合HRV、疲劳度和恢复状态三个维度生成每日或每周摘要。当用户询问'今天状态怎么样'、'身体信号'、'综合状态'时使用此工具。返回JSON格式：{success: true, data: {recovery_status, fatigue_score, data_quality, daily_summary, training_advice, alerts: [{alert_type, severity, message, details}]}} 或 {success: false, error: 错误信息}",
        "parameters": {"period": "周期类型（daily/weekly，默认daily）"},
    },
    "compare_training_periods": {
        "description": "对比两个训练周期的身体信号变化，分析恢复状态趋势。当用户询问'最近状态有没有变好'、'对比上周'、'训练趋势'时使用此工具。返回JSON格式：{success: true, data: {period1: {avg_tsb, data_points, hrv_data_quality}, period2: {avg_tsb, data_points, hrv_data_quality}, tsb_change, comparison_summary}} 或 {success: false, error: 错误信息}",
        "parameters": {
            "period1_days": "近期周期天数（默认7天）",
            "period2_days": "对比周期天数（默认7天）",
        },
    },
```

---

## Task 8: 运行代码质量检查

```bash
uv run ruff format src/ tests/
uv run ruff check src/ tests/
uv run mypy src/ --ignore-missing-imports
```

---

## 自检清单

- [ ] `status today` 命令可用
- [ ] `status weekly` 命令可用
- [ ] `analysis hrv` 命令可用
- [ ] `analysis hr-recovery` 命令可用
- [ ] `analysis fatigue` 命令可用
- [ ] `analysis recovery` 命令可用
- [ ] `analysis compare` 命令可用
- [ ] `get_hrv_analysis` Agent 工具可用
- [ ] `get_hr_recovery` Agent 工具可用
- [ ] `get_fatigue_score` Agent 工具可用
- [ ] `get_recovery_status` Agent 工具可用
- [ ] `get_body_signal_summary` Agent 工具可用
- [ ] `compare_training_periods` Agent 工具可用
- [ ] ruff format 通过
- [ ] ruff check 通过
- [ ] mypy 通过（或仅存在已有错误）
