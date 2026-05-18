from __future__ import annotations

import logging
from datetime import date
from typing import TYPE_CHECKING

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

if TYPE_CHECKING:
    from src.core.analysis.body_signals import BodySignalEngine
    from src.core.prediction.prediction_engine import PredictionEngine
    from src.core.storage.session_repository import SessionRepository
    from src.core.training.training_load import TrainingLoadAnalyzer

logger = logging.getLogger(__name__)

Dimension = (
    FitnessDimension
    | LoadDimension
    | BodySignalDimension
    | RiskDimension
    | TrainingPatternDimension
)


def dim_is_default(dim: Dimension) -> bool:
    """检查维度是否为零值默认维度

    当某个维度的关键字段均为零值时，判定为默认维度。
    用于计算数据质量等级：默认维度数 >= 3 → EMPTY, >= 1 → INSUFFICIENT。

    Args:
        dim: 5维度状态向量的任一维度实例

    Returns:
        bool: True 表示该维度为零值默认维度
    """
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
        prediction_engine: PredictionEngine | None = None,
        body_signal_engine: BodySignalEngine | None = None,
        training_load_analyzer: TrainingLoadAnalyzer | None = None,
        session_repo: SessionRepository | None = None,
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

        dims: list[Dimension] = [fitness, load, body_signal, risk, training_pattern]
        default_count = sum(1 for dim in dims if dim_is_default(dim))

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
        if self._prediction_engine is None:
            return FitnessDimension(vdot=0.0, vdot_trend=0.0)
        try:
            result = self._prediction_engine.predict_vdot_trend(days=30)
            data = result.to_dict() if hasattr(result, "to_dict") else result
            if not isinstance(data, dict):
                data = {"current_vdot": 0.0, "trend_slope": 0.0}
            return FitnessDimension(
                vdot=float(data.get("current_vdot", 0.0)),
                vdot_trend=float(data.get("trend_slope", 0.0)),
                vo2max_estimate=None,
            )
        except (AttributeError, ValueError, TypeError, KeyError) as e:
            logger.warning(f"构建体能维度失败: {e}")
            return FitnessDimension(vdot=0.0, vdot_trend=0.0)
        except Exception as e:
            logger.error(f"构建体能维度发生意外错误: {e}", exc_info=True)
            return FitnessDimension(vdot=0.0, vdot_trend=0.0)

    def build_load(self) -> LoadDimension:
        """构建负荷维度：从session_repo读取数据，调用TrainingLoadAnalyzer计算CTL/ATL"""
        if self._training_load_analyzer is None:
            return LoadDimension(ctl=0.0, atl=0.0, tsb=0.0, acwr=0.0)
        try:
            if self._session_repo is not None:
                df = self._session_repo.storage.read_parquet().collect()
                result = (
                    self._training_load_analyzer.calculate_training_load_from_dataframe(
                        df
                    )
                )
                atl = float(result.get("atl", 0.0))
                ctl = float(result.get("ctl", 0.0))
            else:
                result = self._training_load_analyzer.calculate_atl_ctl([])
                if not isinstance(result, dict):
                    return LoadDimension(ctl=0.0, atl=0.0, tsb=0.0, acwr=0.0)
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
        except (
            AttributeError,
            ValueError,
            TypeError,
            KeyError,
            ZeroDivisionError,
        ) as e:
            logger.warning(f"构建负荷维度失败: {e}")
            return LoadDimension(ctl=0.0, atl=0.0, tsb=0.0, acwr=0.0)
        except Exception as e:
            logger.error(f"构建负荷维度发生意外错误: {e}", exc_info=True)
            return LoadDimension(ctl=0.0, atl=0.0, tsb=0.0, acwr=0.0)

    def build_body_signal(self) -> BodySignalDimension:
        """构建身体信号维度：调用 get_daily_summary()"""
        if self._body_signal_engine is None:
            return BodySignalDimension(fatigue_score=0.0, recovery_status="unknown")
        try:
            result = self._body_signal_engine.get_daily_summary()
            data = result.to_dict() if hasattr(result, "to_dict") else result
            if not isinstance(data, dict):
                return BodySignalDimension(fatigue_score=0.0, recovery_status="unknown")
            return BodySignalDimension(
                fatigue_score=float(data.get("fatigue_score", 0.0)),
                recovery_status=str(data.get("recovery_status", "unknown")),
                resting_hr=None,
                hrv_rmssd=None,
            )
        except (AttributeError, ValueError, TypeError, KeyError) as e:
            logger.warning(f"构建身体信号维度失败: {e}")
            return BodySignalDimension(fatigue_score=0.0, recovery_status="unknown")
        except Exception as e:
            logger.error(f"构建身体信号维度发生意外错误: {e}", exc_info=True)
            return BodySignalDimension(fatigue_score=0.0, recovery_status="unknown")

    def build_risk(self) -> RiskDimension:
        """构建风险维度：调用 predict_injury_risk(days=28)"""
        if self._prediction_engine is None:
            return RiskDimension(
                injury_risk_7d=0.0, injury_risk_28d=0.0, overtraining_risk="low"
            )
        try:
            result = self._prediction_engine.predict_injury_risk(days=28)
            data = result.to_dict() if hasattr(result, "to_dict") else result
            if not isinstance(data, dict):
                return RiskDimension(
                    injury_risk_7d=0.0,
                    injury_risk_28d=0.0,
                    overtraining_risk="low",
                )
            timeline = data.get("risk_timeline", [])
            risk_7d = 0.0
            risk_28d = 0.0
            for point in timeline:
                if not isinstance(point, dict):
                    continue
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
        except (AttributeError, ValueError, TypeError, KeyError) as e:
            logger.warning(f"构建风险维度失败: {e}")
            return RiskDimension(
                injury_risk_7d=0.0, injury_risk_28d=0.0, overtraining_risk="low"
            )
        except Exception as e:
            logger.error(f"构建风险维度发生意外错误: {e}", exc_info=True)
            return RiskDimension(
                injury_risk_7d=0.0, injury_risk_28d=0.0, overtraining_risk="low"
            )

    def build_training_pattern(self) -> TrainingPatternDimension:
        """构建训练模式维度：调用 get_recent_sessions(days=28)"""
        if self._session_repo is None:
            return TrainingPatternDimension(
                weekly_volume_km=0.0,
                intensity_distribution=IntensityDistribution(
                    zone1_pct=0.0, zone2_pct=0.0, zone3_pct=0.0
                ),
                long_run_frequency=0,
            )
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
        except (AttributeError, ValueError, TypeError, KeyError) as e:
            logger.warning(f"构建训练模式维度失败: {e}")
            return TrainingPatternDimension(
                weekly_volume_km=0.0,
                intensity_distribution=IntensityDistribution(
                    zone1_pct=0.0, zone2_pct=0.0, zone3_pct=0.0
                ),
                long_run_frequency=0,
            )
        except Exception as e:
            logger.error(f"构建训练模式维度发生意外错误: {e}", exc_info=True)
            return TrainingPatternDimension(
                weekly_volume_km=0.0,
                intensity_distribution=IntensityDistribution(
                    zone1_pct=0.0, zone2_pct=0.0, zone3_pct=0.0
                ),
                long_run_frequency=0,
            )
