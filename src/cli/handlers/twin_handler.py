from __future__ import annotations

from typing import Any

from src.core.base.context import AppContext, AppContextFactory
from src.core.twin.models import HypotheticalPlan, WeeklyPlanSpec


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
        """What-If 推演"""
        engine = self._get_engine()
        plan = self._build_plan(plan_name, weeks)
        result = engine.simulate(plan, prediction_type=prediction_type)
        return result.to_dict()

    def compare_plans(
        self,
        plans: list[dict[str, Any]],
        prediction_type: str = "parametric",
    ) -> dict[str, Any]:
        """多计划对比"""
        engine = self._get_engine()
        hypothetical_plans = [self._build_plan(p["name"], p["weeks"]) for p in plans]
        result = engine.compare_plans(
            hypothetical_plans, prediction_type=prediction_type
        )
        return result.to_dict()

    @staticmethod
    def _build_plan(name: str, weeks: list[dict[str, Any]]) -> HypotheticalPlan:
        """从字典构建 HypotheticalPlan"""
        week_specs = []
        for w in weeks:
            week_specs.append(
                WeeklyPlanSpec(
                    weekly_volume_km=float(w.get("weekly_volume_km", 0)),
                    easy_ratio=float(w.get("easy_ratio", 0.7)),
                    tempo_ratio=float(w.get("tempo_ratio", 0.15)),
                    interval_ratio=float(w.get("interval_ratio", 0.15)),
                    long_run_km=float(w.get("long_run_km", 0)),
                    intensity_multiplier=float(w.get("intensity_multiplier", 1.0)),
                )
            )
        return HypotheticalPlan(
            name=name,
            weeks=week_specs,
            source="cli",
            plan_id="",
        )
