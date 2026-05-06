from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.core.models.recovery import RecoveryStatus


class DataQuality(Enum):
    """数据质量枚举"""

    SUFFICIENT = "sufficient"
    INSUFFICIENT = "insufficient"
    EMPTY = "empty"


class HRVDataSource(Enum):
    """HRV数据来源枚举"""

    RR_INTERVAL = "rr_interval"
    HR_ESTIMATE = "hr_estimate"


@dataclass(frozen=True)
class RestingHRPoint:
    """静息心率数据点"""

    date: str
    resting_hr: float
    deviation_pct: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "resting_hr": self.resting_hr,
            "deviation_pct": self.deviation_pct,
        }


@dataclass(frozen=True)
class RecoveryPoint:
    """恢复数据点"""

    date: str
    tsb: float
    ctl: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "tsb": self.tsb,
            "ctl": self.ctl,
        }


@dataclass(frozen=True)
class BodySignalAlert:
    """身体信号预警"""

    alert_type: str
    severity: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "alert_type": self.alert_type,
            "severity": self.severity,
            "message": self.message,
            "details": self.details,
        }


@dataclass
class FatigueBreakdown:
    """疲劳度分解"""

    atl_component: float = 0.0
    hr_deviation_component: float = 0.0
    consecutive_component: float = 0.0
    subjective_component: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "atl_component": self.atl_component,
            "hr_deviation_component": self.hr_deviation_component,
            "consecutive_component": self.consecutive_component,
            "subjective_component": self.subjective_component,
        }


@dataclass
class FatigueResult:
    """疲劳度评估结果"""

    fatigue_score: float
    recovery_status: RecoveryStatus
    consecutive_hard_days: int
    breakdown: FatigueBreakdown
    recommendation: str
    data_quality: DataQuality

    def to_dict(self) -> dict[str, Any]:
        return {
            "fatigue_score": self.fatigue_score,
            "recovery_status": self.recovery_status.value,
            "consecutive_hard_days": self.consecutive_hard_days,
            "breakdown": self.breakdown.to_dict(),
            "recommendation": self.recommendation,
            "data_quality": self.data_quality.value,
        }


@dataclass
class RestDayEffect:
    """休息日效果"""

    resting_hr_change_pct: float
    tsb_change: float
    effect_level: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "resting_hr_change_pct": self.resting_hr_change_pct,
            "tsb_change": self.tsb_change,
            "effect_level": self.effect_level,
            "message": self.message,
        }


@dataclass
class RecoveryStatusResult:
    """恢复状态结果"""

    recovery_status: RecoveryStatus
    rest_day_effect: RestDayEffect
    recovery_trend: list[RecoveryPoint]
    data_quality: DataQuality

    def to_dict(self) -> dict[str, Any]:
        return {
            "recovery_status": self.recovery_status.value,
            "rest_day_effect": self.rest_day_effect.to_dict(),
            "recovery_trend": [p.to_dict() for p in self.recovery_trend],
            "data_quality": self.data_quality.value,
        }


@dataclass
class HRVAnalysisResult:
    """HRV分析结果"""

    resting_hr_trend: list[RestingHRPoint]
    data_quality: DataQuality
    data_source: HRVDataSource

    def to_dict(self) -> dict[str, Any]:
        return {
            "resting_hr_trend": [p.to_dict() for p in self.resting_hr_trend],
            "data_quality": self.data_quality.value,
            "data_source": self.data_source.value,
        }


@dataclass
class HRRecoveryResult:
    """心率恢复分析结果"""

    hr_end: float
    hr_recovery_1min: float | None = None
    data_quality: DataQuality = DataQuality.EMPTY

    def to_dict(self) -> dict[str, Any]:
        return {
            "hr_end": self.hr_end,
            "hr_recovery_1min": self.hr_recovery_1min,
            "data_quality": self.data_quality.value,
        }


@dataclass
class HRDriftResult:
    """心率漂移检测结果"""

    drift_rate: float
    data_quality: DataQuality = DataQuality.EMPTY

    def to_dict(self) -> dict[str, Any]:
        return {
            "drift_rate": self.drift_rate,
            "data_quality": self.data_quality.value,
        }


@dataclass
class BodySignalSummary:
    """身体信号摘要"""

    recovery_status: RecoveryStatus
    fatigue_score: float
    data_quality: DataQuality
    daily_summary: str
    training_advice: str
    alerts: list[BodySignalAlert] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "recovery_status": self.recovery_status.value,
            "fatigue_score": self.fatigue_score,
            "data_quality": self.data_quality.value,
            "daily_summary": self.daily_summary,
            "training_advice": self.training_advice,
            "alerts": [a.to_dict() for a in self.alerts],
        }
