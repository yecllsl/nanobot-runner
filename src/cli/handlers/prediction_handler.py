from __future__ import annotations

from typing import Any

from src.core.base.context import AppContext, AppContextFactory


class PredictionHandler:
    """预测业务逻辑"""

    def __init__(self, context: AppContext | None = None) -> None:
        if context is None:
            context = AppContextFactory.create()
        self.context = context

    def _get_engine(self) -> Any:
        engine = self.context.prediction_engine
        if engine is None:
            raise RuntimeError("预测引擎未初始化，请先运行 nanobotrun system init")
        return engine

    def predict_vdot_trend(self, days: int = 30) -> dict[str, Any]:
        """VDOT趋势预测"""
        engine = self._get_engine()
        result = engine.predict_vdot_trend(days=days)
        return result.to_dict()

    def predict_race_result(
        self, distance_km: float, race_date: str | None = None
    ) -> dict[str, Any]:
        """比赛成绩预测"""
        engine = self._get_engine()
        result = engine.predict_race_result(
            distance_km=distance_km, race_date=race_date
        )
        return result.to_dict()

    def predict_injury_risk(self, days: int = 21) -> dict[str, Any]:
        """伤病风险预测"""
        engine = self._get_engine()
        result = engine.predict_injury_risk(days=days)
        return result.to_dict()

    def predict_training_response(
        self,
        session_type: str,
        duration_min: int,
        intensity: str,
    ) -> dict[str, Any]:
        """训练响应预测"""
        engine = self._get_engine()
        result = engine.predict_training_response(
            session_type=session_type,
            duration_min=duration_min,
            intensity=intensity,
        )
        return result.to_dict()

    def report_injury(
        self,
        injury_type: str,
        severity: str,
        date: str,
    ) -> dict[str, Any]:
        """伤病报告提交"""
        engine = self._get_engine()
        result = engine.report_injury(
            injury_type=injury_type,
            severity=severity,
            date=date,
        )
        return result.to_dict()

    def check_prediction_status(self) -> dict[str, Any]:
        """数据充足度评估"""
        engine = self._get_engine()
        result = engine.check_prediction_status()
        return result.to_dict()

    def manage_model(self, action: str, model_type: str) -> dict[str, Any]:
        """模型管理"""
        engine = self._get_engine()
        result = engine.manage_model(action=action, model_type=model_type)
        return result.to_dict()
