# AI决策透明化引擎
# 提供决策解释生成、数据来源追溯、决策路径可视化等能力

import logging
from typing import Any

from src.core.transparency.models import (
    AIDecision,
    DataSource,
    DataSourceType,
    DecisionExplanation,
    DecisionPath,
    DecisionStep,
    DetailLevel,
)

logger = logging.getLogger(__name__)


class TransparencyEngine:
    """AI决策透明化引擎

    生成决策解释、追溯数据来源、可视化决策路径。
    核心接口：
    - generate_explanation: 生成决策解释
    - trace_data_sources: 追溯数据来源
    - visualize_decision_path: 可视化决策路径
    """

    def __init__(self) -> None:
        """初始化透明化引擎"""
        self._decision_store: dict[str, AIDecision] = {}

    def generate_explanation(
        self,
        decision: AIDecision,
        detail_level: DetailLevel = DetailLevel.BRIEF,
    ) -> DecisionExplanation:
        """生成决策解释

        根据决策信息和详细程度，生成简洁版或详细版的解释。

        Args:
            decision: AI决策
            detail_level: 详细程度

        Returns:
            DecisionExplanation: 决策解释
        """
        self._decision_store[decision.id] = decision

        data_sources = self.trace_data_sources(decision.id)
        decision_path = self.visualize_decision_path(decision)
        brief_reasons = self._generate_brief_reasons(decision)
        detailed_analysis = self._generate_detailed_analysis(decision)

        explanation = DecisionExplanation(
            decision_id=decision.id,
            brief_reasons=brief_reasons,
            detailed_analysis=detailed_analysis,
            data_sources=data_sources,
            decision_path=decision_path,
            confidence_score=decision.confidence,
        )

        logger.info(
            f"决策解释已生成: decision_id={decision.id}, "
            f"detail_level={detail_level.value}, "
            f"reasons_count={len(brief_reasons)}"
        )

        return explanation

    def trace_data_sources(self, decision_id: str) -> list[DataSource]:
        """追溯数据来源

        根据决策ID，分析该决策使用的数据来源。

        Args:
            decision_id: 决策ID

        Returns:
            list[DataSource]: 数据来源列表
        """
        decision = self._decision_store.get(decision_id)
        if decision is None:
            logger.warning(f"决策不存在: {decision_id}")
            return []

        sources: list[DataSource] = []

        if decision.input_data:
            sources.extend(self._extract_data_sources(decision.input_data))

        for tool_name in decision.tools_used:
            sources.append(
                DataSource(
                    type=DataSourceType.EXTERNAL_TOOL,
                    name=tool_name,
                    description=f"外部工具: {tool_name}",
                    timestamp=decision.timestamp,
                    quality_score=0.9,
                )
            )

        for memory_ref in decision.memory_referenced:
            sources.append(
                DataSource(
                    type=DataSourceType.MEMORY,
                    name=memory_ref,
                    description=f"记忆引用: {memory_ref}",
                    timestamp=decision.timestamp,
                    quality_score=0.8,
                )
            )

        if decision.input_data.get("user_query"):
            sources.append(
                DataSource(
                    type=DataSourceType.USER_PROFILE,
                    name="用户输入",
                    description="用户原始查询",
                    timestamp=decision.timestamp,
                    quality_score=1.0,
                )
            )

        return sources

    def visualize_decision_path(self, decision: AIDecision) -> DecisionPath:
        """可视化决策路径

        根据决策信息，构建决策路径步骤。

        Args:
            decision: AI决策

        Returns:
            DecisionPath: 决策路径
        """
        steps: list[DecisionStep] = []

        steps.append(
            DecisionStep(
                name="接收用户请求",
                description=f"用户查询: {decision.input_data.get('user_query', '未知')}",
                step_type="reasoning",
            )
        )

        if decision.memory_referenced:
            steps.append(
                DecisionStep(
                    name="检索记忆",
                    description=f"引用了 {len(decision.memory_referenced)} 条记忆",
                    output_data={"memory_count": len(decision.memory_referenced)},
                    step_type="memory_lookup",
                )
            )

        for tool_name in decision.tools_used:
            steps.append(
                DecisionStep(
                    name=f"调用工具: {tool_name}",
                    description=f"使用 {tool_name} 获取数据",
                    step_type="tool_call",
                )
            )

        steps.append(
            DecisionStep(
                name="推理决策",
                description="基于收集的信息进行推理",
                duration_ms=decision.duration_ms,
                step_type="reasoning",
            )
        )

        steps.append(
            DecisionStep(
                name="生成响应",
                description="生成最终回复",
                step_type="reasoning",
            )
        )

        return DecisionPath(
            steps=steps,
            total_duration_ms=decision.duration_ms,
        )

    def get_decision(self, decision_id: str) -> AIDecision | None:
        """获取已存储的决策

        Args:
            decision_id: 决策ID

        Returns:
            AIDecision | None: 决策实例，不存在则返回None
        """
        return self._decision_store.get(decision_id)

    def clear_store(self) -> None:
        """清除决策存储"""
        self._decision_store.clear()

    def _generate_brief_reasons(self, decision: AIDecision) -> list[str]:
        """生成简洁版关键理由

        Args:
            decision: AI决策

        Returns:
            list[str]: 3-5条关键理由
        """
        reasons: list[str] = []

        if decision.reasoning:
            sentences = decision.reasoning.replace("。", "。\n").split("\n")
            for sentence in sentences:
                stripped = sentence.strip()
                if stripped and len(reasons) < 5:
                    reasons.append(stripped)

        if decision.tools_used:
            tools_str = "、".join(decision.tools_used[:3])
            reasons.append(f"参考了工具数据: {tools_str}")

        if decision.memory_referenced:
            reasons.append(f"结合了 {len(decision.memory_referenced)} 条历史记忆")

        if decision.confidence >= 0.8:
            reasons.append("决策置信度较高")
        elif decision.confidence < 0.5:
            reasons.append("决策置信度较低，建议谨慎参考")

        if not reasons:
            reasons.append("基于现有信息综合分析")

        return reasons[:5]

    def _generate_detailed_analysis(self, decision: AIDecision) -> str:
        """生成详细版完整分析

        Args:
            decision: AI决策

        Returns:
            str: 完整分析文本
        """
        parts: list[str] = []

        parts.append(f"## 决策类型: {decision.decision_type.value}")
        parts.append(f"## 置信度: {decision.confidence:.1%}")
        parts.append("")

        if decision.reasoning:
            parts.append("### 推理过程")
            parts.append(decision.reasoning)
            parts.append("")

        if decision.tools_used:
            parts.append("### 使用的工具")
            for tool in decision.tools_used:
                parts.append(f"- {tool}")
            parts.append("")

        if decision.memory_referenced:
            parts.append("### 引用的记忆")
            for mem in decision.memory_referenced:
                parts.append(f"- {mem}")
            parts.append("")

        if decision.input_data:
            parts.append("### 输入数据")
            for key, value in decision.input_data.items():
                value_str = str(value)
                if len(value_str) > 200:
                    value_str = value_str[:200] + "..."
                parts.append(f"- **{key}**: {value_str}")
            parts.append("")

        if decision.output_data:
            parts.append("### 输出数据")
            for key, value in decision.output_data.items():
                value_str = str(value)
                if len(value_str) > 200:
                    value_str = value_str[:200] + "..."
                parts.append(f"- **{key}**: {value_str}")

        return "\n".join(parts)

    @staticmethod
    def _extract_data_sources(input_data: dict[str, Any]) -> list[DataSource]:
        """从输入数据中提取数据来源

        Args:
            input_data: 输入数据字典

        Returns:
            list[DataSource]: 数据来源列表
        """
        sources: list[DataSource] = []

        if "training_data" in input_data:
            sources.append(
                DataSource(
                    type=DataSourceType.TRAINING_DATA,
                    name="训练数据",
                    description="用户历史训练数据",
                    quality_score=0.95,
                )
            )

        if "user_profile" in input_data:
            sources.append(
                DataSource(
                    type=DataSourceType.USER_PROFILE,
                    name="用户画像",
                    description="用户偏好和设置",
                    quality_score=0.9,
                )
            )

        if "weather_data" in input_data:
            sources.append(
                DataSource(
                    type=DataSourceType.EXTERNAL_TOOL,
                    name="天气数据",
                    description="实时天气信息",
                    quality_score=0.85,
                )
            )

        return sources
