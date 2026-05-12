from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from src.core.base.exceptions import NanobotRunnerError


class DataQuality(Enum):
    """数据质量枚举"""

    SUFFICIENT = "sufficient"
    INSUFFICIENT = "insufficient"
    EMPTY = "empty"


@dataclass(frozen=True)
class FitnessDimension:
    """体能维度"""

    vdot: float
    vdot_trend: float
    vo2max_estimate: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "vdot": self.vdot,
            "vdot_trend": self.vdot_trend,
            "vo2max_estimate": self.vo2max_estimate,
        }


@dataclass(frozen=True)
class LoadDimension:
    """负荷维度"""

    ctl: float
    atl: float
    tsb: float
    acwr: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "ctl": self.ctl,
            "atl": self.atl,
            "tsb": self.tsb,
            "acwr": self.acwr,
        }


@dataclass(frozen=True)
class BodySignalDimension:
    """身体信号维度"""

    fatigue_score: float
    recovery_status: str
    resting_hr: float | None = None
    hrv_rmssd: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "fatigue_score": self.fatigue_score,
            "recovery_status": self.recovery_status,
            "resting_hr": self.resting_hr,
            "hrv_rmssd": self.hrv_rmssd,
        }


@dataclass(frozen=True)
class RiskDimension:
    """风险维度"""

    injury_risk_7d: float
    injury_risk_28d: float
    overtraining_risk: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "injury_risk_7d": self.injury_risk_7d,
            "injury_risk_28d": self.injury_risk_28d,
            "overtraining_risk": self.overtraining_risk,
        }


@dataclass(frozen=True)
class IntensityDistribution:
    """强度分布"""

    zone1_pct: float
    zone2_pct: float
    zone3_pct: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "zone1_pct": self.zone1_pct,
            "zone2_pct": self.zone2_pct,
            "zone3_pct": self.zone3_pct,
        }


@dataclass(frozen=True)
class TrainingPatternDimension:
    """训练模式维度"""

    weekly_volume_km: float
    intensity_distribution: IntensityDistribution
    long_run_frequency: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "weekly_volume_km": self.weekly_volume_km,
            "intensity_distribution": self.intensity_distribution.to_dict(),
            "long_run_frequency": self.long_run_frequency,
        }


@dataclass(frozen=True)
class RunnerStateVector:
    """跑者状态向量（5维度）"""

    fitness: FitnessDimension
    load: LoadDimension
    body_signal: BodySignalDimension
    risk: RiskDimension
    training_pattern: TrainingPatternDimension
    snapshot_date: str
    data_quality: DataQuality

    def to_dict(self) -> dict[str, Any]:
        return {
            "fitness": self.fitness.to_dict(),
            "load": self.load.to_dict(),
            "body_signal": self.body_signal.to_dict(),
            "risk": self.risk.to_dict(),
            "training_pattern": self.training_pattern.to_dict(),
            "snapshot_date": self.snapshot_date,
            "data_quality": self.data_quality.value,
        }


@dataclass(frozen=True)
class WeeklyPlanSpec:
    """周计划规格"""

    weekly_volume_km: float
    easy_ratio: float
    tempo_ratio: float
    interval_ratio: float
    long_run_km: float
    intensity_multiplier: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "weekly_volume_km": self.weekly_volume_km,
            "easy_ratio": self.easy_ratio,
            "tempo_ratio": self.tempo_ratio,
            "interval_ratio": self.interval_ratio,
            "long_run_km": self.long_run_km,
            "intensity_multiplier": self.intensity_multiplier,
        }


@dataclass(frozen=True)
class HypotheticalPlan:
    """假设训练计划"""

    name: str
    weeks: list[WeeklyPlanSpec]
    source: str = "plan_id"
    plan_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "weeks": [w.to_dict() for w in self.weeks],
            "source": self.source,
            "plan_id": self.plan_id,
        }

    @classmethod
    def from_week_dicts(
        cls,
        name: str,
        weeks: list[dict[str, Any]],
        source: str = "cli",
        plan_id: str = "",
    ) -> HypotheticalPlan:
        """从字典列表构建HypotheticalPlan（CLI/Agent共用）"""
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
        return cls(name=name, weeks=week_specs, source=source, plan_id=plan_id)


@dataclass(frozen=True)
class SimulationWeekSnapshot:
    """推演周快照"""

    week_number: int
    state: RunnerStateVector
    weekly_plan: WeeklyPlanSpec
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "week_number": self.week_number,
            "state": self.state.to_dict(),
            "weekly_plan": self.weekly_plan.to_dict(),
            "confidence": self.confidence,
        }


@dataclass(frozen=True)
class SimulationResult:
    """推演结果"""

    plan_name: str
    initial_state: RunnerStateVector
    final_state: RunnerStateVector
    snapshots: list[SimulationWeekSnapshot]
    total_weeks: int
    prediction_type: str
    vdot_delta: float
    peak_injury_risk: float
    avg_tsb: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_name": self.plan_name,
            "initial_state": self.initial_state.to_dict(),
            "final_state": self.final_state.to_dict(),
            "snapshots": [s.to_dict() for s in self.snapshots],
            "total_weeks": self.total_weeks,
            "prediction_type": self.prediction_type,
            "vdot_delta": self.vdot_delta,
            "peak_injury_risk": self.peak_injury_risk,
            "avg_tsb": self.avg_tsb,
        }


@dataclass(frozen=True)
class PlanComparisonMetrics:
    """计划对比指标"""

    plan_id: str
    plan_name: str
    vdot_delta: float
    peak_injury_risk: float
    avg_tsb: float
    min_recovery_status: str
    recommendation_score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "plan_name": self.plan_name,
            "vdot_delta": self.vdot_delta,
            "peak_injury_risk": self.peak_injury_risk,
            "avg_tsb": self.avg_tsb,
            "min_recovery_status": self.min_recovery_status,
            "recommendation_score": self.recommendation_score,
        }


@dataclass(frozen=True)
class PlanComparison:
    """计划对比结果"""

    plans: list[PlanComparisonMetrics]
    best_plan: PlanComparisonMetrics
    comparison_dimensions: list[str]
    recommendation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "plans": [p.to_dict() for p in self.plans],
            "best_plan": self.best_plan.to_dict(),
            "comparison_dimensions": self.comparison_dimensions,
            "recommendation": self.recommendation,
        }


@dataclass(frozen=True)
class StateVectorCache:
    """状态向量缓存"""

    state: RunnerStateVector
    created_at: str
    ttl_hours: int = 24

    def is_expired(self) -> bool:
        """判断缓存是否过期"""
        try:
            created = datetime.fromisoformat(self.created_at)
            return datetime.now() > created + timedelta(hours=self.ttl_hours)
        except (ValueError, TypeError):
            return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.to_dict(),
            "created_at": self.created_at,
            "ttl_hours": self.ttl_hours,
        }


@dataclass
class TwinEngineError(NanobotRunnerError):
    """数字孪生引擎异常

    注意：未使用 frozen=True，因为基类 NanobotRunnerError 为可变 dataclass，
    Python 不允许从非 frozen dataclass 继承 frozen dataclass。
    若需冻结需同步修改 exceptions.py 中所有异常类，影响范围过大。
    """

    error_code: str = "TWIN_ENGINE_ERROR"
    recovery_suggestion: str | None = None
