from __future__ import annotations

import logging

from src.core.prediction.baselines.banister_ir import BanisterIRModel
from src.core.prediction.models import TrainingResponse

logger = logging.getLogger(__name__)

INTENSITY_MULTIPLIERS = {
    "low": 0.6,
    "moderate": 0.75,
    "high": 0.9,
    "very_high": 1.05,
}

SESSION_TYPE_TSS_PER_MIN = {
    "easy": 0.5,
    "recovery": 0.4,
    "tempo": 0.8,
    "threshold": 0.9,
    "interval": 1.1,
    "long": 0.65,
    "race": 1.2,
}

RECOVERY_HOURS_BASE = {
    "easy": 8.0,
    "recovery": 6.0,
    "tempo": 24.0,
    "threshold": 36.0,
    "interval": 48.0,
    "long": 30.0,
    "race": 72.0,
}


class TrainingResponsePredictor:
    """训练响应预测

    基于Banister IR模型预测训练对VDOT/疲劳/恢复的影响
    """

    def __init__(
        self,
        banister_model: BanisterIRModel | None = None,
        base_vdot: float = 45.0,
    ) -> None:
        self._banister_model = banister_model or BanisterIRModel()
        self._base_vdot = base_vdot

    def predict(
        self,
        session_type: str,
        duration_min: int,
        intensity: str,
    ) -> TrainingResponse:
        """预测训练响应"""
        tss = self._estimate_tss(session_type, duration_min, intensity)
        recovery_hours = self._estimate_recovery(session_type, intensity, tss)
        vdot_impact = self._estimate_vdot_impact(tss)
        fatigue_impact = self._estimate_fatigue_impact(tss, intensity)
        injury_risk_delta = self._estimate_injury_risk_delta(intensity, tss)
        fitness_delta, fatigue_delta = self._estimate_banister_deltas(tss)

        return TrainingResponse(
            session_type=session_type,
            duration_min=duration_min,
            intensity=intensity,
            predicted_vdot_impact=round(vdot_impact, 2),
            predicted_fatigue_impact=round(fatigue_impact, 1),
            predicted_recovery_hours=round(recovery_hours, 1),
            predicted_injury_risk_delta=round(injury_risk_delta, 3),
            banister_fitness_delta=round(fitness_delta, 2),
            banister_fatigue_delta=round(fatigue_delta, 2),
            prediction_type="parametric",
        )

    def _estimate_tss(
        self, session_type: str, duration_min: int, intensity: str
    ) -> float:
        """估算TSS"""
        tss_per_min = SESSION_TYPE_TSS_PER_MIN.get(session_type, 0.7)
        intensity_mult = INTENSITY_MULTIPLIERS.get(intensity, 0.75)
        return tss_per_min * duration_min * intensity_mult

    def _estimate_recovery(
        self, session_type: str, intensity: str, tss: float
    ) -> float:
        """估算恢复时间"""
        base_hours = RECOVERY_HOURS_BASE.get(session_type, 24.0)
        intensity_mult = INTENSITY_MULTIPLIERS.get(intensity, 0.75)
        return base_hours * intensity_mult

    def _estimate_vdot_impact(self, tss: float) -> float:
        """估算VDOT影响"""
        return self._banister_model.k1 * tss * 0.1

    def _estimate_fatigue_impact(self, tss: float, intensity: str) -> float:
        """估算疲劳影响"""
        intensity_mult = INTENSITY_MULTIPLIERS.get(intensity, 0.75)
        return self._banister_model.k2 * tss * intensity_mult * 10

    def _estimate_injury_risk_delta(self, intensity: str, tss: float) -> float:
        """估算伤病风险增量"""
        intensity_mult = INTENSITY_MULTIPLIERS.get(intensity, 0.75)
        return min(0.3, tss * intensity_mult * 0.001)

    def _estimate_banister_deltas(self, tss: float) -> tuple[float, float]:
        """估算Banister适应/疲劳增量"""
        import numpy as np

        stress = np.array([tss])
        fitness_delta = self._banister_model.k1 * float(
            np.sum(stress * np.exp(-np.arange(1) / self._banister_model.tau_fitness))
        )
        fatigue_delta = self._banister_model.k2 * float(
            np.sum(stress * np.exp(-np.arange(1) / self._banister_model.tau_fatigue))
        )
        return fitness_delta, fatigue_delta
