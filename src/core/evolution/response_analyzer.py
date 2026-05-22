# 训练响应性分析器
# 分析不同训练类型对跑者VDOT变化的响应效果

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from src.core.base.logger import get_logger
from src.core.evolution.config import EvolutionConfig
from src.core.evolution.evolution_store import EvolutionStore
from src.core.evolution.models import (
    DecisionLog,
    OutcomeRecord,
    TrainingResponseReport,
    TrainingTypeResponse,
)

logger = get_logger(__name__)

# 训练类型关键词映射（优先级2：从recommendation_text匹配）
_TRAINING_TYPE_KEYWORDS: dict[str, list[str]] = {
    "interval": ["间歇", "间歇跑", "速度间歇", "亚索800"],
    "threshold": ["阈值", "节奏", "节奏跑", "乳酸阈值"],
    "long": ["长距离", "LSD", "长跑"],
    "recovery": ["恢复", "恢复跑", "排酸跑", "休息"],
    "easy": ["轻松跑", "慢跑"],
}

# 训练类型优先级（冲突解决：高优先级优先）
_TRAINING_TYPE_PRIORITY: dict[str, int] = {
    "interval": 5,
    "threshold": 4,
    "long": 3,
    "recovery": 2,
    "easy": 1,
}


class ResponseAnalyzer:
    """训练响应性分析器

    分析不同训练类型对跑者VDOT变化的响应效果。
    通过DecisionLog/OutcomeRecord配对，推断训练类型，
    计算响应性评分，识别最佳/最差训练类型。
    """

    def __init__(
        self,
        store: EvolutionStore,
        config: EvolutionConfig | None = None,
    ) -> None:
        self._store = store
        self._config = config or EvolutionConfig()

    def analyze(self, months: int = 6) -> TrainingResponseReport:
        """执行训练响应性分析"""
        eligible_pairs = self._get_eligible_pairs(months)
        all_pairs = self._store.get_decision_outcome_pairs(days=months * 30)

        # 按训练类型分组
        type_groups: dict[str, list[tuple[DecisionLog, OutcomeRecord]]] = {}
        for decision, outcome in eligible_pairs:
            training_type = self._infer_training_type(decision)
            if training_type not in type_groups:
                type_groups[training_type] = []
            type_groups[training_type].append((decision, outcome))

        # 计算各类型响应性
        responses: list[TrainingTypeResponse] = []
        for training_type, pairs in type_groups.items():
            vdot_deltas: list[float] = []
            fidelities: list[float] = []
            for decision, outcome in pairs:
                if outcome.actual_vdot is not None:
                    delta = outcome.actual_vdot - decision.runner_state.get("vdot", 0)
                    vdot_deltas.append(delta)
                if outcome.execution_fidelity is not None:
                    fidelities.append(outcome.execution_fidelity)

            avg_vdot_delta = sum(vdot_deltas) / len(vdot_deltas) if vdot_deltas else 0.0
            avg_fidelity = sum(fidelities) / len(fidelities) if fidelities else 0.0
            response_score = self._calculate_response_score(
                avg_vdot_delta, avg_fidelity
            )

            responses.append(
                TrainingTypeResponse(
                    training_type=training_type,
                    sample_count=len(pairs),
                    avg_vdot_delta=round(avg_vdot_delta, 4),
                    avg_fidelity=round(avg_fidelity, 4),
                    response_score=round(response_score, 4),
                )
            )

        # 按response_score排序
        responses.sort(key=lambda r: r.response_score, reverse=True)

        # 判断数据充足性
        min_samples = self._config.response_min_samples_per_type
        data_sufficient = (
            all(r.sample_count >= min_samples for r in responses)
            if responses
            else False
        )

        # 确定最佳/最差类型
        best_type: str | None = None
        worst_type: str | None = None
        sufficient_responses = [r for r in responses if r.sample_count >= min_samples]
        if len(sufficient_responses) >= 2:
            best_type = sufficient_responses[0].training_type
            worst_type = sufficient_responses[-1].training_type
        elif len(sufficient_responses) == 1:
            best_type = sufficient_responses[0].training_type

        profile_summary = self._build_profile_summary(responses)

        report = TrainingResponseReport(
            report_id=f"rpt_{uuid.uuid4().hex[:12]}",
            timestamp=datetime.now(),
            analysis_months=months,
            total_pairs=len(all_pairs),
            eligible_pairs=len(eligible_pairs),
            training_responses=responses,
            best_type=best_type,
            worst_type=worst_type,
            profile_summary=profile_summary,
            data_sufficient=data_sufficient,
        )
        logger.info(
            "训练响应性分析完成: total=%d, eligible=%d, types=%d, sufficient=%s",
            report.total_pairs,
            report.eligible_pairs,
            len(responses),
            data_sufficient,
        )
        return report

    def _get_eligible_pairs(
        self, months: int
    ) -> list[tuple[DecisionLog, OutcomeRecord]]:
        """筛选fidelity>=config.response_min_fidelity的配对"""
        cutoff = datetime.now() - timedelta(days=months * 30)
        all_pairs = self._store.get_decision_outcome_pairs(start_date=cutoff)
        min_fidelity = self._config.response_min_fidelity
        return [
            (d, o)
            for d, o in all_pairs
            if o.execution_fidelity is not None and o.execution_fidelity >= min_fidelity
        ]

    def _infer_training_type(self, decision: DecisionLog) -> str:
        """推断训练类型（三级优先级）

        优先级1: 从tool_call_chain提取
        优先级2: 从recommendation_text关键词匹配
        优先级3: 兜底"unknown"
        """
        # 优先级1: 从tool_call_chain提取
        for call in decision.tool_call_chain:
            if call.get("tool") == "predict_training_response":
                session_type = call.get("arguments", {}).get("session_type", "")
                if session_type in _TRAINING_TYPE_PRIORITY:
                    return session_type

        # 优先级2: 从recommendation_text关键词匹配
        if decision.recommendation_text:
            text = decision.recommendation_text
            matched_types: list[str] = []
            for type_name, keywords in _TRAINING_TYPE_KEYWORDS.items():
                for keyword in keywords:
                    if keyword in text:
                        matched_types.append(type_name)
                        break
            if matched_types:
                matched_types.sort(
                    key=lambda t: _TRAINING_TYPE_PRIORITY[t], reverse=True
                )
                return matched_types[0]

        # 优先级3: 兜底
        return "unknown"

    def _calculate_response_score(
        self, avg_vdot_delta: float, avg_fidelity: float
    ) -> float:
        """计算响应性评分

        response_score = normalize(avg_vdot_delta) * 0.6 + avg_fidelity * 0.4
        normalize: min(avg_vdot_delta / 0.5, 1.0) (0.5/周为满分基准)
        """
        normalized_delta = min(avg_vdot_delta / 0.5, 1.0) if avg_vdot_delta > 0 else 0.0
        return normalized_delta * 0.6 + avg_fidelity * 0.4

    def _build_profile_summary(self, responses: list[TrainingTypeResponse]) -> str:
        """生成画像摘要文本"""
        if not responses:
            return "暂无训练响应数据"
        sorted_responses = sorted(
            responses, key=lambda r: r.response_score, reverse=True
        )
        parts: list[str] = []
        for r in sorted_responses[:3]:
            n = r.sample_count
            parts.append(
                f"{r.training_type}(效果{r.response_score:.0%},样本{n})"
                if n > 0
                else f"{r.training_type}(效果{r.response_score:.0%})"
            )
        return "训练效果排名: " + " > ".join(parts)
