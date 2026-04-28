# AI状态洞察看板
# 展示AI进化状态、建议质量、工具可靠性、记忆整理日志

import logging
from typing import Any

from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table

from src.core.transparency.observability_manager import ObservabilityManager
from src.core.transparency.trace_logger import TraceLogger

logger = logging.getLogger(__name__)


class AIStatusDashboard:
    """AI状态洞察看板

    展示AI进化状态、建议质量、工具可靠性、记忆整理日志。
    核心接口：
    - render: 渲染完整看板
    - render_evolution_status: 渲染AI进化状态
    - render_suggestion_quality: 渲染建议质量
    - render_tool_reliability: 渲染工具可靠性
    - render_memory_log: 渲染记忆整理日志
    """

    def __init__(
        self,
        manager: ObservabilityManager | None = None,
        trace_logger: TraceLogger | None = None,
    ) -> None:
        """初始化AI状态洞察看板

        Args:
            manager: 可观测性管理器
            trace_logger: 追踪日志记录器
        """
        self.manager = manager or ObservabilityManager()
        self.trace_logger = trace_logger or TraceLogger()

    def render(self) -> Layout:
        """渲染完整看板

        Returns:
            Layout: Rich Layout组件
        """
        layout = Layout()

        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
        )

        layout["header"].update(
            Panel(
                "[bold]AI 状态洞察看板[/bold]",
                border_style="bright_blue",
            )
        )

        layout["body"].split_row(
            Layout(name="left"),
            Layout(name="right"),
        )

        layout["left"].split_column(
            Layout(name="evolution"),
            Layout(name="suggestion"),
        )

        layout["right"].split_column(
            Layout(name="tools"),
            Layout(name="memory"),
        )

        layout["evolution"].update(self.render_evolution_status())
        layout["suggestion"].update(self.render_suggestion_quality())
        layout["tools"].update(self.render_tool_reliability())
        layout["memory"].update(self.render_memory_log())

        return layout

    def render_evolution_status(self) -> Panel:
        """渲染AI进化状态

        Returns:
            Panel: Rich Panel组件
        """
        metrics = self.manager.get_metrics()
        log_stats = self.trace_logger.get_stats()

        total_decisions = log_stats.get("decision_count", 0)
        total_traces = metrics.total_traces
        success_rate = 0.0
        if total_traces > 0:
            success_rate = metrics.successful_traces / total_traces

        evolution_level = self._calculate_evolution_level(total_decisions)

        content_parts: list[str] = []
        content_parts.append(f"进化等级: {evolution_level}")
        content_parts.append(f"总决策次数: {total_decisions}")
        content_parts.append(f"总追踪次数: {total_traces}")
        content_parts.append(f"成功率: {success_rate:.1%}")

        if metrics.avg_duration_ms > 0:
            content_parts.append(f"平均响应时间: {metrics.avg_duration_ms:.0f}ms")

        content = "\n".join(content_parts)

        return Panel(
            content,
            title="[bold]AI进化状态[/bold]",
            border_style="cyan",
        )

    def render_suggestion_quality(self) -> Panel:
        """渲染建议质量

        Returns:
            Panel: Rich Panel组件
        """
        metrics = self.manager.get_metrics()
        log_stats = self.trace_logger.get_stats()

        tool_success = metrics.tool_success_rate
        error_count = log_stats.get("error_count", 0)
        total = log_stats.get("total_entries", 0)

        quality_score = self._calculate_quality_score(tool_success, error_count, total)

        content_parts: list[str] = []
        content_parts.append(f"建议质量评分: {quality_score:.1f}/10")

        if metrics.tool_call_count > 0:
            content_parts.append(f"工具调用成功率: {tool_success:.1%}")

        content_parts.append(f"错误次数: {error_count}")

        if quality_score >= 8:
            content_parts.append("状态: 优秀")
        elif quality_score >= 6:
            content_parts.append("状态: 良好")
        elif quality_score >= 4:
            content_parts.append("状态: 一般")
        else:
            content_parts.append("状态: 需改进")

        content = "\n".join(content_parts)

        return Panel(
            content,
            title="[bold]建议质量[/bold]",
            border_style="green",
        )

    def render_tool_reliability(self) -> Table:
        """渲染工具可靠性

        Returns:
            Table: Rich Table组件
        """
        table = Table(title="工具可靠性")

        table.add_column("指标", style="cyan")
        table.add_column("值", style="green", justify="right")
        table.add_column("状态", style="bold")

        metrics = self.manager.get_metrics()

        tool_calls = metrics.tool_call_count
        tool_success_rate = metrics.tool_success_rate

        tool_status = (
            "✓"
            if tool_success_rate >= 0.9
            else "⚠"
            if tool_success_rate >= 0.7
            else "✗"
        )

        table.add_row(
            "工具调用次数",
            str(tool_calls),
            "",
        )

        table.add_row(
            "工具成功率",
            f"{tool_success_rate:.1%}",
            tool_status,
        )

        table.add_row(
            "追踪成功率",
            f"{metrics.successful_traces / metrics.total_traces:.1%}"
            if metrics.total_traces > 0
            else "N/A",
            "✓" if metrics.error_rate < 0.1 else "⚠",
        )

        table.add_row(
            "平均耗时",
            f"{metrics.avg_duration_ms:.0f}ms"
            if metrics.avg_duration_ms > 0
            else "N/A",
            "✓" if metrics.avg_duration_ms < 3000 else "⚠",
        )

        return table

    def render_memory_log(self, limit: int = 5) -> Panel:
        """渲染记忆整理日志

        Args:
            limit: 显示条目数

        Returns:
            Panel: Rich Panel组件
        """
        decision_logs = self.trace_logger.get_decision_logs(limit)

        if not decision_logs:
            return Panel(
                "暂无记忆整理日志",
                title="[bold]记忆整理日志[/bold]",
                border_style="yellow",
            )

        content_parts: list[str] = []
        for entry in reversed(decision_logs):
            ts = entry.timestamp.strftime("%H:%M:%S")
            msg = entry.message[:60]
            content_parts.append(f"[{ts}] {msg}")

        content = "\n".join(content_parts)

        return Panel(
            content,
            title="[bold]记忆整理日志[/bold]",
            border_style="yellow",
        )

    def get_dashboard_data(self) -> dict[str, Any]:
        """获取看板数据（JSON格式）

        Returns:
            dict: 看板数据
        """
        metrics = self.manager.get_metrics()
        log_stats = self.trace_logger.get_stats()

        total_decisions = log_stats.get("decision_count", 0)
        evolution_level = self._calculate_evolution_level(total_decisions)
        quality_score = self._calculate_quality_score(
            metrics.tool_success_rate,
            log_stats.get("error_count", 0),
            log_stats.get("total_entries", 0),
        )

        return {
            "evolution": {
                "level": evolution_level,
                "total_decisions": total_decisions,
                "total_traces": metrics.total_traces,
                "success_rate": metrics.successful_traces / metrics.total_traces
                if metrics.total_traces > 0
                else 0.0,
            },
            "suggestion_quality": {
                "score": quality_score,
                "tool_success_rate": metrics.tool_success_rate,
                "error_count": log_stats.get("error_count", 0),
            },
            "tool_reliability": {
                "tool_call_count": metrics.tool_call_count,
                "tool_success_rate": metrics.tool_success_rate,
                "avg_duration_ms": metrics.avg_duration_ms,
            },
            "log_stats": log_stats,
        }

    @staticmethod
    def _calculate_evolution_level(decision_count: int) -> str:
        """计算AI进化等级

        Args:
            decision_count: 决策次数

        Returns:
            str: 进化等级
        """
        if decision_count >= 1000:
            return "专家级"
        if decision_count >= 500:
            return "高级"
        if decision_count >= 100:
            return "中级"
        if decision_count >= 20:
            return "初级"
        return "新手"

    @staticmethod
    def _calculate_quality_score(
        tool_success_rate: float,
        error_count: int,
        total_entries: int,
    ) -> float:
        """计算建议质量评分

        Args:
            tool_success_rate: 工具成功率
            error_count: 错误次数
            total_entries: 总条目数

        Returns:
            float: 质量评分（0-10）
        """
        score = 5.0

        score += tool_success_rate * 3.0

        if total_entries > 0:
            error_rate = error_count / total_entries
            score -= error_rate * 5.0

        return max(0.0, min(10.0, score))
