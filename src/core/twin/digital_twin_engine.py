from __future__ import annotations

import logging

from src.core.twin.models import (
    HypotheticalPlan,
    PlanComparison,
    PlanComparisonMetrics,
    RunnerStateVector,
    SimulationResult,
)
from src.core.twin.state_vector_builder import StateVectorBuilder
from src.core.twin.whatif_simulator import WhatIfSimulator

logger = logging.getLogger(__name__)


class DigitalTwinEngine:
    """数字孪生引擎 — 薄编排层

    聚合 StateVectorBuilder + WhatIfSimulator，对外提供三个核心方法：
    - get_current_snapshot(): 获取当前跑者状态快照
    - simulate(): What-If 推演
    - compare_plans(): 多计划对比
    """

    def __init__(self, state_vector_builder: StateVectorBuilder) -> None:
        self._builder = state_vector_builder

    def get_current_snapshot(self) -> RunnerStateVector:
        """获取当前5维跑者状态向量"""
        return self._builder.build()

    def simulate(
        self,
        plan: HypotheticalPlan,
        prediction_type: str = "parametric",
    ) -> SimulationResult:
        """What-If 推演：基于当前状态，推演计划执行后的状态变化"""
        initial_state = self.get_current_snapshot()
        return WhatIfSimulator.simulate(initial_state, plan, prediction_type)

    def compare_plans(
        self,
        plans: list[HypotheticalPlan],
        prediction_type: str = "parametric",
    ) -> PlanComparison:
        """多计划对比：对每个计划执行推演，按综合评分排序"""
        initial_state = self.get_current_snapshot()

        results: list[SimulationResult] = []
        for plan in plans:
            result = WhatIfSimulator.simulate(initial_state, plan, prediction_type)
            results.append(result)

        metrics_list: list[PlanComparisonMetrics] = []
        for plan, result in zip(plans, results):
            score = self._compute_score(result)
            min_recovery = result.final_state.body_signal.recovery_status
            metrics_list.append(
                PlanComparisonMetrics(
                    plan_id=plan.plan_id or "",
                    plan_name=result.plan_name,
                    vdot_delta=result.vdot_delta,
                    peak_injury_risk=result.peak_injury_risk,
                    avg_tsb=result.avg_tsb,
                    min_recovery_status=min_recovery,
                    recommendation_score=score,
                )
            )

        sorted_metrics = sorted(
            metrics_list, key=lambda m: m.recommendation_score, reverse=True
        )
        best = sorted_metrics[0] if sorted_metrics else metrics_list[0]

        return PlanComparison(
            plans=sorted_metrics,
            best_plan=best,
            comparison_dimensions=["vdot_delta", "peak_injury_risk", "avg_tsb"],
            recommendation=f"推荐计划: {best.plan_name} (评分: {best.recommendation_score})",
        )

    @staticmethod
    def _compute_score(result: SimulationResult) -> float:
        """综合评分：VDOT提升 + TSB平衡 - 伤病风险惩罚"""
        vdot_score = result.vdot_delta * 10.0
        tsb_score = max(-result.avg_tsb, 0) * -2.0
        risk_penalty = result.peak_injury_risk * -1.0
        return round(vdot_score + tsb_score + risk_penalty, 2)
