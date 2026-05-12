from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING

from src.core.twin.models import (
    BodySignalDimension,
    FitnessDimension,
    HypotheticalPlan,
    IntensityDistribution,
    LoadDimension,
    RiskDimension,
    RunnerStateVector,
    SimulationResult,
    SimulationWeekSnapshot,
    TrainingPatternDimension,
    WeeklyPlanSpec,
)

if TYPE_CHECKING:
    from src.core.prediction.baselines.banister_ir import BanisterIRModel
    from src.core.prediction.prediction_engine import PredictionEngine

logger = logging.getLogger(__name__)

AVG_PACE_MIN_PER_KM = 6.0

DECAY_RATES: dict[str, float] = {
    "ml_enhanced": 0.05,
    "parametric": 0.08,
    "basic": 0.12,
}

INITIAL_CONFIDENCE: dict[str, float] = {
    "ml_enhanced": 0.95,
    "parametric": 0.85,
    "basic": 0.70,
}

TSS_INTENSITY_FACTORS: dict[str, float] = {
    "easy": 0.5,
    "tempo": 0.8,
    "interval": 1.1,
    "long": 0.65,
}

ATL_TIME_CONSTANT = 7.0
CTL_TIME_CONSTANT = 42.0


class WhatIfSimulator:
    """What-If 逐周推演器

    支持三种预测模式的逐周推演，每步更新CTL/ATL/VDOT等指标，
    置信度按指数衰减。

    依赖注入（架构7.5.3节）：
    - banister_model: BanisterIRModel，用于L2参数化推演
    - prediction_engine: PredictionEngine，用于L1 ML增强推演
    """

    def __init__(
        self,
        banister_model: BanisterIRModel | None = None,
        prediction_engine: PredictionEngine | None = None,
    ) -> None:
        self._banister_model = banister_model
        self._prediction_engine = prediction_engine

    @staticmethod
    def estimate_weekly_tss(week_plan: WeeklyPlanSpec) -> float:
        """按强度分布估算周TSS

        TSS = Σ(各强度距离 × IF² × 100 / 3600 × 配速系数)
        """
        if week_plan.weekly_volume_km <= 0:
            return 0.0

        easy_km = week_plan.weekly_volume_km * week_plan.easy_ratio
        tempo_km = week_plan.weekly_volume_km * week_plan.tempo_ratio
        interval_km = week_plan.weekly_volume_km * week_plan.interval_ratio
        long_km = week_plan.long_run_km

        pace_factor = AVG_PACE_MIN_PER_KM * 60.0

        easy_tss = (
            (easy_km * pace_factor / 3600) * (TSS_INTENSITY_FACTORS["easy"] ** 2) * 100
        )
        tempo_tss = (
            (tempo_km * pace_factor / 3600)
            * (TSS_INTENSITY_FACTORS["tempo"] ** 2)
            * 100
        )
        interval_tss = (
            (interval_km * pace_factor / 3600)
            * (TSS_INTENSITY_FACTORS["interval"] ** 2)
            * 100
        )
        long_tss = (
            (long_km * pace_factor / 3600) * (TSS_INTENSITY_FACTORS["long"] ** 2) * 100
        )

        total_tss = (
            easy_tss + tempo_tss + interval_tss + long_tss
        ) * week_plan.intensity_multiplier
        return round(total_tss, 2)

    def simulate_week(
        self,
        current_state: RunnerStateVector,
        week_plan: WeeklyPlanSpec,
        prediction_type: str,
    ) -> RunnerStateVector:
        """推演一周：CTL/ATL EWMA更新、VDOT增量估算、疲劳度累加"""
        weekly_tss = WhatIfSimulator.estimate_weekly_tss(week_plan)

        alpha_atl = 1.0 - math.exp(-1.0 / ATL_TIME_CONSTANT)
        alpha_ctl = 1.0 - math.exp(-1.0 / CTL_TIME_CONSTANT)

        new_atl = alpha_atl * weekly_tss + (1.0 - alpha_atl) * current_state.load.atl
        new_ctl = alpha_ctl * weekly_tss + (1.0 - alpha_ctl) * current_state.load.ctl
        new_tsb = new_ctl - new_atl
        new_acwr = new_atl / new_ctl if new_ctl > 0 else 0.0

        vdot_delta = self._estimate_vdot_delta(
            weekly_tss,
            current_state.load.ctl,
            prediction_type,
            current_state.fitness.vdot_trend,
        )
        new_vdot = current_state.fitness.vdot + vdot_delta

        fatigue_increment = min(weekly_tss / 100.0, 5.0)
        new_fatigue = min(
            current_state.body_signal.fatigue_score + fatigue_increment, 10.0
        )

        if new_tsb > 10:
            recovery_status = "good"
        elif new_tsb > 0:
            recovery_status = "moderate"
        elif new_tsb > -10:
            recovery_status = "fatigued"
        else:
            recovery_status = "overtrained"

        injury_risk_delta = 0.0
        if new_acwr > 1.3:
            injury_risk_delta = (new_acwr - 1.3) * 15.0

        new_risk_7d = min(current_state.risk.injury_risk_7d + injury_risk_delta, 100.0)
        new_risk_28d = min(
            current_state.risk.injury_risk_28d + injury_risk_delta * 0.5, 100.0
        )

        overtraining_risk = "low"
        if new_risk_28d > 30:
            overtraining_risk = "high"
        elif new_risk_28d > 15:
            overtraining_risk = "medium"

        return RunnerStateVector(
            fitness=FitnessDimension(
                vdot=round(new_vdot, 2), vdot_trend=current_state.fitness.vdot_trend
            ),
            load=LoadDimension(
                ctl=round(new_ctl, 2),
                atl=round(new_atl, 2),
                tsb=round(new_tsb, 2),
                acwr=round(new_acwr, 2),
            ),
            body_signal=BodySignalDimension(
                fatigue_score=round(new_fatigue, 2),
                recovery_status=recovery_status,
            ),
            risk=RiskDimension(
                injury_risk_7d=round(new_risk_7d, 2),
                injury_risk_28d=round(new_risk_28d, 2),
                overtraining_risk=overtraining_risk,
            ),
            training_pattern=TrainingPatternDimension(
                weekly_volume_km=week_plan.weekly_volume_km,
                intensity_distribution=IntensityDistribution(
                    zone1_pct=week_plan.easy_ratio * 100,
                    zone2_pct=(week_plan.tempo_ratio + week_plan.interval_ratio)
                    * 100
                    / 2,
                    zone3_pct=week_plan.interval_ratio * 100,
                ),
                long_run_frequency=1 if week_plan.long_run_km > 0 else 0,
            ),
            snapshot_date=current_state.snapshot_date,
            data_quality=current_state.data_quality,
        )

    def simulate(
        self,
        initial_state: RunnerStateVector,
        plan: HypotheticalPlan,
        prediction_type: str,
    ) -> SimulationResult:
        """逐周循环推演，每步 confidence *= (1-decay_rate)"""
        decay_rate = DECAY_RATES.get(prediction_type, DECAY_RATES["basic"])
        initial_confidence = INITIAL_CONFIDENCE.get(
            prediction_type, INITIAL_CONFIDENCE["basic"]
        )

        current_state = initial_state
        snapshots: list[SimulationWeekSnapshot] = []
        confidence = initial_confidence
        peak_injury_risk = 0.0
        tsb_sum = 0.0

        for i, week_plan in enumerate(plan.weeks):
            current_state = self.simulate_week(
                current_state, week_plan, prediction_type
            )
            confidence *= 1.0 - decay_rate

            snapshots.append(
                SimulationWeekSnapshot(
                    week_number=i + 1,
                    state=current_state,
                    weekly_plan=week_plan,
                    confidence=round(confidence, 4),
                )
            )

            peak_injury_risk = max(peak_injury_risk, current_state.risk.injury_risk_28d)
            tsb_sum += current_state.load.tsb

        total_weeks = len(plan.weeks)
        avg_tsb = tsb_sum / total_weeks if total_weeks > 0 else 0.0
        vdot_delta = current_state.fitness.vdot - initial_state.fitness.vdot

        return SimulationResult(
            plan_name=plan.name,
            initial_state=initial_state,
            final_state=current_state,
            snapshots=snapshots,
            total_weeks=total_weeks,
            prediction_type=prediction_type,
            vdot_delta=round(vdot_delta, 2),
            peak_injury_risk=round(peak_injury_risk, 2),
            avg_tsb=round(avg_tsb, 2),
        )

    def _estimate_vdot_delta(
        self,
        weekly_tss: float,
        current_ctl: float,
        prediction_type: str,
        trend_slope: float = 0.0,
    ) -> float:
        """估算VDOT增量

        L1 ML增强：调用PredictionEngine获取趋势修正
        L2 参数化：调用BanisterIRModel计算fitness/fatigue差分
        L3 基础：简化stress_ratio公式
        """
        if prediction_type == "ml_enhanced":
            if self._prediction_engine is not None and trend_slope != 0.0:
                try:
                    result = self._prediction_engine.predict_vdot_trend(days=7)
                    if hasattr(result, "trend_slope"):
                        return float(result.trend_slope) * 7.0
                except Exception as e:
                    logger.debug(f"ML增强VDOT预测失败，降级: {e}")
            if trend_slope != 0.0:
                return trend_slope * 7.0

        if prediction_type == "parametric" and self._banister_model is not None:
            try:
                import numpy as np

                avg_daily_tss = weekly_tss / 7.0
                stress_array = np.full(7, avg_daily_tss)
                predicted = self._banister_model.predict(
                    stress_array, base_vdot=0.0, days_ahead=0
                )
                return float(predicted) * 0.1
            except Exception as e:
                logger.debug(f"Banister IR模型预测失败，降级: {e}")

        if current_ctl <= 0:
            return 0.0

        stress_ratio = weekly_tss / current_ctl
        if stress_ratio > 1.0:
            delta = (stress_ratio - 1.0) * 0.1
        else:
            delta = -(1.0 - stress_ratio) * 0.05

        if prediction_type == "basic":
            delta *= 0.7

        return delta
