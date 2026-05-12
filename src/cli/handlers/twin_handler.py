from __future__ import annotations

from typing import Any

from src.core.base.context import AppContext, AppContextFactory
from src.core.twin.models import HypotheticalPlan


class TwinHandler:
    """数字孪生业务逻辑层"""

    def __init__(self, context: AppContext | None = None) -> None:
        if context is None:
            context = AppContextFactory.create()
        self.context = context

    def _get_engine(self) -> Any:
        engine = self.context.digital_twin_engine
        if engine is None:
            raise RuntimeError("数字孪生引擎未初始化，请先运行 nanobotrun system init")
        return engine

    def get_snapshot(self) -> dict[str, Any]:
        """获取当前跑者状态快照"""
        engine = self._get_engine()
        result = engine.get_current_snapshot()
        return result.to_dict()

    def simulate(
        self,
        plan_name: str,
        weeks: list[dict[str, Any]],
        prediction_type: str = "parametric",
    ) -> dict[str, Any]:
        """What-If 推演（手动构建计划）"""
        engine = self._get_engine()
        plan = HypotheticalPlan.from_week_dicts(plan_name, weeks, source="cli")
        result = engine.simulate(plan, prediction_type=prediction_type)
        return result.to_dict()

    def simulate_by_plan_id(
        self,
        plan_id: str,
        prediction_type: str = "parametric",
    ) -> dict[str, Any]:
        """What-If 推演（系统计划引用）"""
        engine = self._get_engine()
        plan = engine.load_plan(plan_id)
        result = engine.simulate(plan, prediction_type=prediction_type)
        return result.to_dict()

    def compare_plans(
        self,
        plans: list[dict[str, Any]],
        prediction_type: str = "parametric",
    ) -> dict[str, Any]:
        """多计划对比（手动构建计划）"""
        engine = self._get_engine()
        hypothetical_plans = [
            HypotheticalPlan.from_week_dicts(p["name"], p["weeks"], source="cli")
            for p in plans
        ]
        result = engine.compare_plans(
            hypothetical_plans, prediction_type=prediction_type
        )
        return result.to_dict()

    def compare_plans_by_ids(
        self,
        plan_ids: list[str],
        prediction_type: str = "parametric",
    ) -> dict[str, Any]:
        """多计划对比（系统计划引用）"""
        engine = self._get_engine()
        result = engine.compare_plans_by_ids(plan_ids, prediction_type=prediction_type)
        return result.to_dict()
