# 训练洞察报告
# 提供训练模式分析、恢复状态趋势、AI建议效果、个性化进化报告

import logging
from datetime import datetime
from typing import Any

from rich.panel import Panel
from rich.table import Table

from src.core.transparency.observability_manager import ObservabilityManager
from src.core.transparency.trace_logger import TraceLogger

logger = logging.getLogger(__name__)


class TrainingInsightReport:
    """训练洞察报告

    提供训练模式分析、恢复状态趋势、AI建议效果、个性化进化报告。
    核心接口：
    - generate_report: 生成完整洞察报告
    - analyze_training_patterns: 分析训练模式
    - analyze_recovery_trend: 分析恢复状态趋势
    - evaluate_ai_advice_effect: 评估AI建议效果
    - generate_evolution_report: 生成个性化进化报告
    """

    def __init__(
        self,
        manager: ObservabilityManager | None = None,
        trace_logger: TraceLogger | None = None,
    ) -> None:
        """初始化训练洞察报告

        Args:
            manager: 可观测性管理器
            trace_logger: 追踪日志记录器
        """
        self.manager = manager or ObservabilityManager()
        self.trace_logger = trace_logger or TraceLogger()

    def generate_report(self) -> dict[str, Any]:
        """生成完整洞察报告

        Returns:
            dict: 洞察报告数据
        """
        return {
            "generated_at": datetime.now().isoformat(),
            "training_patterns": self.analyze_training_patterns(),
            "recovery_trend": self.analyze_recovery_trend(),
            "ai_advice_effect": self.evaluate_ai_advice_effect(),
            "evolution_report": self.generate_evolution_report(),
        }

    def render_report(self) -> Panel:
        """渲染洞察报告

        Returns:
            Panel: Rich Panel组件
        """
        report = self.generate_report()

        content_parts: list[str] = []
        content_parts.append(f"报告生成时间: {report['generated_at']}")
        content_parts.append("")

        patterns = report["training_patterns"]
        content_parts.append("[bold]训练模式分析[/bold]")
        content_parts.append(f"  总决策次数: {patterns['total_decisions']}")
        content_parts.append(f"  工具调用次数: {patterns['tool_calls']}")
        content_parts.append(f"  训练相关决策: {patterns['training_related']}")
        content_parts.append("")

        recovery = report["recovery_trend"]
        content_parts.append("[bold]恢复状态趋势[/bold]")
        content_parts.append(f"  追踪成功率: {recovery['trace_success_rate']:.1%}")
        content_parts.append(f"  平均响应时间: {recovery['avg_duration_ms']:.0f}ms")
        content_parts.append(f"  错误率: {recovery['error_rate']:.1%}")
        content_parts.append("")

        advice = report["ai_advice_effect"]
        content_parts.append("[bold]AI建议效果[/bold]")
        content_parts.append(f"  建议质量评分: {advice['quality_score']:.1f}/10")
        content_parts.append(f"  工具成功率: {advice['tool_success_rate']:.1%}")
        content_parts.append("")

        evolution = report["evolution_report"]
        content_parts.append("[bold]个性化进化报告[/bold]")
        content_parts.append(f"  进化等级: {evolution['level']}")
        content_parts.append(f"  经验值: {evolution['experience']}")
        content_parts.append(f"  下级所需: {evolution['next_level_requirement']}")

        content = "\n".join(content_parts)

        return Panel(
            content,
            title="[bold]训练洞察报告[/bold]",
            border_style="magenta",
        )

    def analyze_training_patterns(self) -> dict[str, Any]:
        """分析训练模式

        Returns:
            dict: 训练模式分析结果
        """
        log_stats = self.trace_logger.get_stats()
        metrics = self.manager.get_metrics()

        decision_logs = self.trace_logger.get_decision_logs(50)

        training_related = 0
        for entry in decision_logs:
            decision_type = entry.context.get("decision_type", "")
            if decision_type in (
                "training_plan",
                "pace_guidance",
                "recovery_advice",
            ):
                training_related += 1

        return {
            "total_decisions": log_stats.get("decision_count", 0),
            "tool_calls": metrics.tool_call_count,
            "training_related": training_related,
            "tool_success_rate": metrics.tool_success_rate,
        }

    def analyze_recovery_trend(self) -> dict[str, Any]:
        """分析恢复状态趋势

        Returns:
            dict: 恢复状态趋势分析结果
        """
        metrics = self.manager.get_metrics()

        trace_success_rate = 0.0
        if metrics.total_traces > 0:
            trace_success_rate = metrics.successful_traces / metrics.total_traces

        return {
            "trace_success_rate": trace_success_rate,
            "avg_duration_ms": metrics.avg_duration_ms,
            "error_rate": metrics.error_rate,
            "failed_traces": metrics.failed_traces,
        }

    def evaluate_ai_advice_effect(self) -> dict[str, Any]:
        """评估AI建议效果

        Returns:
            dict: AI建议效果评估结果
        """
        metrics = self.manager.get_metrics()
        log_stats = self.trace_logger.get_stats()

        quality_score = 5.0
        quality_score += metrics.tool_success_rate * 3.0

        total = log_stats.get("total_entries", 0)
        errors = log_stats.get("error_count", 0)
        if total > 0:
            quality_score -= (errors / total) * 5.0

        quality_score = max(0.0, min(10.0, quality_score))

        return {
            "quality_score": quality_score,
            "tool_success_rate": metrics.tool_success_rate,
            "total_decisions": log_stats.get("decision_count", 0),
            "error_count": errors,
        }

    def generate_evolution_report(self) -> dict[str, Any]:
        """生成个性化进化报告

        Returns:
            dict: 个性化进化报告
        """
        log_stats = self.trace_logger.get_stats()
        total_decisions = log_stats.get("decision_count", 0)

        level = self._calculate_level(total_decisions)
        experience = total_decisions
        next_level_req = self._get_next_level_requirement(total_decisions)

        return {
            "level": level,
            "experience": experience,
            "next_level_requirement": next_level_req,
            "total_traces": self.manager.get_metrics().total_traces,
            "tool_mastery": self._calculate_tool_mastery(),
        }

    def render_training_patterns_table(self) -> Table:
        """渲染训练模式分析表格

        Returns:
            Table: Rich Table组件
        """
        patterns = self.analyze_training_patterns()

        table = Table(title="训练模式分析")

        table.add_column("指标", style="cyan")
        table.add_column("值", style="green", justify="right")

        table.add_row("总决策次数", str(patterns["total_decisions"]))
        table.add_row("工具调用次数", str(patterns["tool_calls"]))
        table.add_row("训练相关决策", str(patterns["training_related"]))
        table.add_row("工具成功率", f"{patterns['tool_success_rate']:.1%}")

        return table

    @staticmethod
    def _calculate_level(decision_count: int) -> str:
        """计算进化等级

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
    def _get_next_level_requirement(decision_count: int) -> str:
        """获取下一级所需经验

        Args:
            decision_count: 决策次数

        Returns:
            str: 下一级需求描述
        """
        if decision_count >= 1000:
            return "已达最高等级"
        if decision_count >= 500:
            return f"再积累 {1000 - decision_count} 次决策可达专家级"
        if decision_count >= 100:
            return f"再积累 {500 - decision_count} 次决策可达高级"
        if decision_count >= 20:
            return f"再积累 {100 - decision_count} 次决策可达中级"
        return f"再积累 {20 - decision_count} 次决策可达初级"

    def _calculate_tool_mastery(self) -> dict[str, float]:
        """计算工具掌握度

        Returns:
            dict: 工具掌握度
        """
        tool_logs = self.trace_logger.get_tool_call_logs(100)

        tool_counts: dict[str, int] = {}
        for entry in tool_logs:
            tool_id = entry.context.get("tool_id", "unknown")
            tool_counts[tool_id] = tool_counts.get(tool_id, 0) + 1

        mastery: dict[str, float] = {}
        for tool_id, count in tool_counts.items():
            mastery[tool_id] = min(1.0, count / 20.0)

        return mastery
