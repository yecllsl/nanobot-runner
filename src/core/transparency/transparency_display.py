# 透明化展示模块
# 提供Rich格式化的决策解释、数据来源、决策路径展示

from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from src.core.transparency.models import (
    DataSource,
    DecisionExplanation,
    DecisionPath,
    DetailLevel,
)


class TransparencyDisplay:
    """透明化展示

    使用Rich库格式化展示AI决策的透明化信息。
    核心接口：
    - display_brief_explanation: 展示简洁版解释
    - display_detailed_explanation: 展示详细版解释
    - display_data_sources: 展示数据来源
    - display_decision_path: 展示决策路径
    """

    def display_brief_explanation(
        self,
        explanation: DecisionExplanation,
    ) -> Panel:
        """展示简洁版解释

        生成包含3-5条关键理由的简洁面板。

        Args:
            explanation: 决策解释

        Returns:
            Panel: Rich Panel组件
        """
        content_parts: list[str] = []

        for i, reason in enumerate(explanation.brief_reasons, 1):
            content_parts.append(f"  {i}. {reason}")

        if explanation.confidence_score >= 0:
            confidence_pct = f"{explanation.confidence_score:.0%}"
            content_parts.append(f"\n  置信度: {confidence_pct}")

        content = "\n".join(content_parts)

        return Panel(
            content,
            title="[bold]决策解释[/bold]",
            subtitle=f"决策ID: {explanation.decision_id}",
            border_style="blue",
        )

    def display_detailed_explanation(
        self,
        explanation: DecisionExplanation,
    ) -> Panel:
        """展示详细版解释

        生成包含完整分析过程的详细面板。

        Args:
            explanation: 决策解释

        Returns:
            Panel: Rich Panel组件
        """
        content_parts: list[str] = []

        content_parts.append(f"决策ID: {explanation.decision_id}")
        content_parts.append(f"置信度: {explanation.confidence_score:.1%}")
        content_parts.append("")

        if explanation.brief_reasons:
            content_parts.append("[bold]关键理由[/bold]")
            for i, reason in enumerate(explanation.brief_reasons, 1):
                content_parts.append(f"  {i}. {reason}")
            content_parts.append("")

        if explanation.detailed_analysis:
            content_parts.append("[bold]详细分析[/bold]")
            content_parts.append(explanation.detailed_analysis)
            content_parts.append("")

        if explanation.data_sources:
            content_parts.append(
                f"[bold]数据来源[/bold] ({len(explanation.data_sources)}个)"
            )
            for ds in explanation.data_sources:
                quality_str = f"{ds.quality_score:.0%}"
                content_parts.append(
                    f"  - {ds.name} ({ds.type.value}, 质量: {quality_str})"
                )
            content_parts.append("")

        if explanation.decision_path.steps:
            content_parts.append(
                f"[bold]决策路径[/bold] ({len(explanation.decision_path.steps)}步, "
                f"耗时: {explanation.decision_path.total_duration_ms}ms)"
            )
            for i, step in enumerate(explanation.decision_path.steps, 1):
                content_parts.append(f"  {i}. {step.name}: {step.description}")

        content = "\n".join(content_parts)

        return Panel(
            content,
            title="[bold]详细决策解释[/bold]",
            border_style="green",
        )

    def display_data_sources(
        self,
        sources: list[DataSource],
    ) -> Table:
        """展示数据来源

        生成数据来源表格。

        Args:
            sources: 数据来源列表

        Returns:
            Table: Rich Table组件
        """
        table = Table(title="数据来源")

        table.add_column("名称", style="cyan")
        table.add_column("类型", style="magenta")
        table.add_column("描述", style="white")
        table.add_column("质量", style="green", justify="right")

        for source in sources:
            quality_str = f"{source.quality_score:.0%}"
            table.add_row(
                source.name,
                source.type.value,
                source.description[:50],
                quality_str,
            )

        return table

    def display_decision_path(
        self,
        path: DecisionPath,
    ) -> str:
        """展示决策路径（Mermaid流程图）

        Args:
            path: 决策路径

        Returns:
            str: Mermaid流程图
        """
        return path.to_mermaid()

    def display_explanation_by_level(
        self,
        explanation: DecisionExplanation,
        detail_level: DetailLevel = DetailLevel.BRIEF,
    ) -> Panel | Table | str:
        """根据详细程度展示解释

        Args:
            explanation: 决策解释
            detail_level: 详细程度

        Returns:
            Panel | Table | str: 展示组件
        """
        if detail_level == DetailLevel.OFF:
            return Panel(
                "透明化展示已关闭",
                title="[bold]决策解释[/bold]",
                border_style="dim",
            )

        if detail_level == DetailLevel.BRIEF:
            return self.display_brief_explanation(explanation)

        return self.display_detailed_explanation(explanation)

    @staticmethod
    def format_confidence(confidence: float) -> Text:
        """格式化置信度显示

        Args:
            confidence: 置信度值

        Returns:
            Text: Rich Text组件
        """
        pct = f"{confidence:.0%}"
        if confidence >= 0.8:
            return Text(pct, style="bold green")
        if confidence >= 0.5:
            return Text(pct, style="yellow")
        return Text(pct, style="bold red")
