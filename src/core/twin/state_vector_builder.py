from __future__ import annotations

import logging
from datetime import date
from typing import Any

from src.core.twin.models import (
    BodySignalDimension,
    DataQuality,
    FitnessDimension,
    IntensityDistribution,
    LoadDimension,
    RiskDimension,
    RunnerStateVector,
    TrainingPatternDimension,
)

logger = logging.getLogger(__name__)


def dim_is_default(dim: Any) -> bool:
    """检查维度是否为零值默认维度"""
    if isinstance(dim, FitnessDimension):
        return dim.vdot == 0.0 and dim.vdot_trend == 0.0
    if isinstance(dim, LoadDimension):
        return dim.ctl == 0.0 and dim.atl == 0.0
    if isinstance(dim, BodySignalDimension):
        return dim.fatigue_score == 0.0
    if isinstance(dim, RiskDimension):
        return dim.injury_risk_7d == 0.0 and dim.injury_risk_28d == 0.0
    if isinstance(dim, TrainingPatternDimension):
        return dim.weekly_volume_km == 0.0
    return False


class StateVectorBuilder:
    """5维度跑者状态向量构建器

    聚合 PredictionEngine、BodySignalEngine、TrainingLoadAnalyzer、SessionRepository
    四个依赖，构建 RunnerStateVector。每个维度独立 try/except，失败时返回零值默认维度。
    """

    def __init__(
        self,
        prediction_engine: Any = None,
        body_signal_engine: Any = None,
        training_load_analyzer: Any = None,
        session_repo: Any = None,
    ) -> None:
        self._prediction_engine = prediction_engine
        self._body_signal_engine = body_signal_engine
        self._training_load_analyzer = training_load_analyzer
        self._session_repo = session_repo

    def build(self) -> RunnerStateVector:
        """构建5维度跑者状态向量"""
        fitness = self.build_fitness()
        load = self.build_load()
        body_signal = self.build_body_signal()
        risk = self.build_risk()
        training_pattern = self.build_training_pattern()

        default_count = sum(
            1
            for dim in [fitness, load, body_signal, risk, training_pattern]
            if dim_is_default(dim)
        )

        if default_count >= 3:
            data_quality = DataQuality.EMPTY
        elif default_count >= 1:
            data_quality = DataQuality.INSUFFICIENT
        else:
            data_quality = DataQuality.SUFFICIENT

        return RunnerStateVector(
            fitness=fitness,
            load=load,
            body_signal=body_signal,
            risk=risk,
            training_pattern=training_pattern,
            snapshot_date=date.today().isoformat(),
            data_quality=data_quality,
        )

    def build_fitness(self) -> FitnessDimension:
        """构建体能维度：调用 predict_vdot_trend(days=30)"""
        try:
            result = self._prediction_engine.predict_vdot_trend(days=30)
            data = result.to_dict() if hasattr(result, "to_dict") else result
            return FitnessDimension(
                vdot=float(data.get("current_vdot", 0.0)),
                vdot_trend=float(data.get("trend_slope", 0.0)),
                vo2max_estimate=None,
            )
        except Exception as e:
            logger.warning(f"构建体能维度失败: {e}")
            return FitnessDimension(vdot=0.0, vdot_trend=0.0)

    def build_load(self) -> LoadDimension:
        """构建负荷维度：调用 calculate_atl/ctl"""
        try:
            result = self._training_load_analyzer.calculate_atl_ctl([])
            atl = float(result.get("atl", 0.0))
            ctl = float(result.get("ctl", 0.0))
            tsb = ctl - atl
            acwr = atl / ctl if ctl > 0 else 0.0
            return LoadDimension(
                ctl=round(ctl, 2),
                atl=round(atl, 2),
                tsb=round(tsb, 2),
                acwr=round(acwr, 2),
            )
        except Exception as e:
            logger.warning(f"构建负荷维度失败: {e}")
            return LoadDimension(ctl=0.0, atl=0.0, tsb=0.0, acwr=0.0)

    def build_body_signal(self) -> BodySignalDimension:
        """构建身体信号维度：调用 get_daily_summary()"""
        try:
            result = self._body_signal_engine.get_daily_summary()
            data = result.to_dict() if hasattr(result, "to_dict") else result
            return BodySignalDimension(
                fatigue_score=float(data.get("fatigue_score", 0.0)),
                recovery_status=str(data.get("recovery_status", "unknown")),
                resting_hr=None,
                hrv_rmssd=None,
            )
        except Exception as e:
            logger.warning(f"构建身体信号维度失败: {e}")
            return BodySignalDimension(fatigue_score=0.0, recovery_status="unknown")

    def build_risk(self) -> RiskDimension:
        """构建风险维度：调用 predict_injury_risk(days=28)"""
        try:
            result = self._prediction_engine.predict_injury_risk(days=28)
            data = result.to_dict() if hasattr(result, "to_dict") else result
            timeline = data.get("risk_timeline", [])
            risk_7d = 0.0
            risk_28d = 0.0
            for point in timeline:
                days_ahead = point.get("days_ahead", 0)
                prob = point.get("risk_probability", 0.0)
                if days_ahead <= 7:
                    risk_7d = prob * 100
                if days_ahead <= 28:
                    risk_28d = prob * 100
            overtraining_risk = "low"
            if risk_28d > 30:
                overtraining_risk = "high"
            elif risk_28d > 15:
                overtraining_risk = "medium"
            return RiskDimension(
                injury_risk_7d=round(risk_7d, 2),
                injury_risk_28d=round(risk_28d, 2),
                overtraining_risk=overtraining_risk,
            )
        except Exception as e:
            logger.warning(f"构建风险维度失败: {e}")
            return RiskDimension(
                injury_risk_7d=0.0, injury_risk_28d=0.0, overtraining_risk="low"
            )

    def build_training_pattern(self) -> TrainingPatternDimension:
        """构建训练模式维度：调用 get_recent_sessions(days=28)"""
        try:
            sessions = self._session_repo.get_recent_sessions(limit=28)
            total_distance_km = 0.0
            for s in sessions:
                dist = getattr(s, "distance_m", 0) or 0
                total_distance_km += dist / 1000.0
            weekly_volume = total_distance_km / 4.0 if total_distance_km > 0 else 0.0
            return TrainingPatternDimension(
                weekly_volume_km=round(weekly_volume, 2),
                intensity_distribution=IntensityDistribution(
                    zone1_pct=80.0, zone2_pct=15.0, zone3_pct=5.0
                ),
                long_run_frequency=1,
            )
        except Exception as e:
            logger.warning(f"构建训练模式维度失败: {e}")
            return TrainingPatternDimension(
                weekly_volume_km=0.0,
                intensity_distribution=IntensityDistribution(
                    zone1_pct=0.0, zone2_pct=0.0, zone3_pct=0.0
                ),
                long_run_frequency=0,
            )
