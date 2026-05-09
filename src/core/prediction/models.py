from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.core.body_signal.models import DataQuality


@dataclass(frozen=True)
class VDOTFactor:
    """VDOT影响因子"""

    name: str
    weight: float
    direction: str
    value: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "weight": self.weight,
            "direction": self.direction,
            "value": self.value,
        }


@dataclass(frozen=True)
class MLPredictionInfo:
    """ML预测元信息"""

    model_type: str
    training_samples: int
    feature_count: int
    shap_available: bool
    quantile_models: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_type": self.model_type,
            "training_samples": self.training_samples,
            "feature_count": self.feature_count,
            "shap_available": self.shap_available,
            "quantile_models": self.quantile_models,
        }


@dataclass(frozen=True)
class VDOTPrediction:
    """VDOT趋势预测结果"""

    current_vdot: float
    predicted_vdot: float
    prediction_days: int
    confidence_interval: tuple[float, float]
    confidence: float
    trend_slope: float
    key_factors: list[VDOTFactor]
    data_quality: DataQuality
    prediction_type: str
    model_info: MLPredictionInfo | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_vdot": self.current_vdot,
            "predicted_vdot": self.predicted_vdot,
            "prediction_days": self.prediction_days,
            "confidence_interval": list(self.confidence_interval),
            "confidence": self.confidence,
            "trend_slope": self.trend_slope,
            "key_factors": [f.to_dict() for f in self.key_factors],
            "data_quality": self.data_quality.value,
            "prediction_type": self.prediction_type,
            "model_info": self.model_info.to_dict() if self.model_info else None,
        }


@dataclass(frozen=True)
class PaceSplit:
    """配速分段"""

    segment: str
    pace: str
    pace_seconds: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "segment": self.segment,
            "pace": self.pace,
            "pace_seconds": self.pace_seconds,
        }


@dataclass(frozen=True)
class PaceStrategy:
    """配速策略"""

    strategy_type: str
    splits: list[PaceSplit]

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_type": self.strategy_type,
            "splits": [s.to_dict() for s in self.splits],
        }


@dataclass(frozen=True)
class PersonalizationInfo:
    """个人化信息"""

    runner_type: str
    riegel_exponent: float
    correction_factor: float
    race_samples_count: int
    pre_race_adjustment: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "runner_type": self.runner_type,
            "riegel_exponent": self.riegel_exponent,
            "correction_factor": self.correction_factor,
            "race_samples_count": self.race_samples_count,
            "pre_race_adjustment": self.pre_race_adjustment,
        }


@dataclass(frozen=True)
class RacePredictionResult:
    """比赛成绩预测结果"""

    distance_km: float
    predicted_time: str
    predicted_time_seconds: float
    confidence: float
    best_case: str
    worst_case: str
    predicted_vdot: float
    pace_strategy: PaceStrategy | None
    prediction_type: str
    personalization_info: PersonalizationInfo | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "distance_km": self.distance_km,
            "predicted_time": self.predicted_time,
            "predicted_time_seconds": self.predicted_time_seconds,
            "confidence": self.confidence,
            "best_case": self.best_case,
            "worst_case": self.worst_case,
            "predicted_vdot": self.predicted_vdot,
            "pace_strategy": self.pace_strategy.to_dict()
            if self.pace_strategy
            else None,
            "prediction_type": self.prediction_type,
            "personalization_info": self.personalization_info.to_dict()
            if self.personalization_info
            else None,
        }


@dataclass(frozen=True)
class RiskTimePoint:
    """风险时间点"""

    days_ahead: int
    risk_probability: float
    risk_level: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "days_ahead": self.days_ahead,
            "risk_probability": self.risk_probability,
            "risk_level": self.risk_level,
        }


@dataclass(frozen=True)
class RiskFactor:
    """风险因子"""

    name: str
    contribution: float
    current_value: float
    threshold_value: float
    direction: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "contribution": self.contribution,
            "current_value": self.current_value,
            "threshold_value": self.threshold_value,
            "direction": self.direction,
        }


@dataclass(frozen=True)
class AcuteLoadRisk:
    """急性负荷风险"""

    atl_ctl_ratio: float
    weekly_load_change_pct: float
    risk_contribution: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "atl_ctl_ratio": self.atl_ctl_ratio,
            "weekly_load_change_pct": self.weekly_load_change_pct,
            "risk_contribution": self.risk_contribution,
        }


@dataclass(frozen=True)
class ChronicRisk:
    """慢性风险"""

    tsb_consecutive_low_days: int
    resting_hr_deviation_pct: float
    risk_contribution: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "tsb_consecutive_low_days": self.tsb_consecutive_low_days,
            "resting_hr_deviation_pct": self.resting_hr_deviation_pct,
            "risk_contribution": self.risk_contribution,
        }


@dataclass(frozen=True)
class BodySignalRisk:
    """身体信号风险"""

    fatigue_score: float
    recovery_status: str
    active_alerts: list[str]
    risk_contribution: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "fatigue_score": self.fatigue_score,
            "recovery_status": self.recovery_status,
            "active_alerts": self.active_alerts,
            "risk_contribution": self.risk_contribution,
        }


@dataclass(frozen=True)
class InjuryRiskPrediction:
    """伤病风险预测结果"""

    risk_score: float
    risk_level: str
    risk_timeline: list[RiskTimePoint]
    acute_load_risk: AcuteLoadRisk | None
    chronic_risk: ChronicRisk | None
    body_signal_risk: BodySignalRisk | None
    top_risk_factors: list[RiskFactor] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    data_quality: DataQuality = DataQuality.INSUFFICIENT
    prediction_type: str = "basic"

    def to_dict(self) -> dict[str, Any]:
        return {
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "risk_timeline": [t.to_dict() for t in self.risk_timeline],
            "acute_load_risk": self.acute_load_risk.to_dict()
            if self.acute_load_risk
            else None,
            "chronic_risk": self.chronic_risk.to_dict() if self.chronic_risk else None,
            "body_signal_risk": self.body_signal_risk.to_dict()
            if self.body_signal_risk
            else None,
            "top_risk_factors": [f.to_dict() for f in self.top_risk_factors],
            "recommendations": self.recommendations,
            "data_quality": self.data_quality.value,
            "prediction_type": self.prediction_type,
        }


@dataclass(frozen=True)
class PredictionRecord:
    """预测记录（用于校准和回测）"""

    prediction_date: str
    prediction_type: str
    predicted_value: float
    predicted_unit: str
    actual_value: float | None
    deviation_pct: float | None
    prediction_method: str
    model_version: str
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "prediction_date": self.prediction_date,
            "prediction_type": self.prediction_type,
            "predicted_value": self.predicted_value,
            "predicted_unit": self.predicted_unit,
            "actual_value": self.actual_value,
            "deviation_pct": self.deviation_pct,
            "prediction_method": self.prediction_method,
            "model_version": self.model_version,
            "confidence": self.confidence,
        }


@dataclass(frozen=True)
class TrainingResponse:
    """训练响应预测结果"""

    session_type: str
    duration_min: int
    intensity: str
    predicted_vdot_impact: float
    predicted_fatigue_impact: float
    predicted_recovery_hours: float
    predicted_injury_risk_delta: float
    banister_fitness_delta: float
    banister_fatigue_delta: float
    prediction_type: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_type": self.session_type,
            "duration_min": self.duration_min,
            "intensity": self.intensity,
            "predicted_vdot_impact": self.predicted_vdot_impact,
            "predicted_fatigue_impact": self.predicted_fatigue_impact,
            "predicted_recovery_hours": self.predicted_recovery_hours,
            "predicted_injury_risk_delta": self.predicted_injury_risk_delta,
            "banister_fitness_delta": self.banister_fitness_delta,
            "banister_fatigue_delta": self.banister_fatigue_delta,
            "prediction_type": self.prediction_type,
        }


@dataclass(frozen=True)
class InjuryReportResult:
    """伤病报告结果"""

    injury_id: str
    injury_type: str
    severity: str
    date: str
    label_type: str
    created_at: str
    success: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "injury_id": self.injury_id,
            "injury_type": self.injury_type,
            "severity": self.severity,
            "date": self.date,
            "label_type": self.label_type,
            "created_at": self.created_at,
            "success": self.success,
        }


@dataclass(frozen=True)
class InjuryLabel:
    """伤病标签"""

    injury_id: str
    injury_type: str
    severity: str
    start_date: str
    end_date: str | None
    label_type: str
    affected_sessions: list[str]
    notes: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "injury_id": self.injury_id,
            "injury_type": self.injury_type,
            "severity": self.severity,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "label_type": self.label_type,
            "affected_sessions": self.affected_sessions,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class SufficiencyDimension:
    """数据充足度维度"""

    name: str
    current_value: float
    target_value: float
    is_met: bool
    progress_pct: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "current_value": self.current_value,
            "target_value": self.target_value,
            "is_met": self.is_met,
            "progress_pct": self.progress_pct,
        }


@dataclass(frozen=True)
class DataSufficiencyReport:
    """数据充足度报告"""

    prediction_type: str
    is_sufficient: bool
    overall_progress_pct: float
    dimensions: list[SufficiencyDimension]
    advice: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "prediction_type": self.prediction_type,
            "is_sufficient": self.is_sufficient,
            "overall_progress_pct": self.overall_progress_pct,
            "dimensions": [d.to_dict() for d in self.dimensions],
            "advice": self.advice,
        }


@dataclass(frozen=True)
class PredictionStatusReport:
    """预测状态总览"""

    vdot_status: DataSufficiencyReport
    race_status: DataSufficiencyReport
    injury_status: DataSufficiencyReport
    overall_ready_count: int
    advice: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "vdot_status": self.vdot_status.to_dict(),
            "race_status": self.race_status.to_dict(),
            "injury_status": self.injury_status.to_dict(),
            "overall_ready_count": self.overall_ready_count,
            "advice": self.advice,
        }


@dataclass(frozen=True)
class ModelMetadata:
    """模型元数据"""

    model_type: str
    version: str
    trained_at: str
    training_samples: int
    feature_count: int
    validation_error: float
    model_algorithm: str
    sklearn_version: str
    quantile_models: bool
    ensemble_weights: dict[str, float] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_type": self.model_type,
            "version": self.version,
            "trained_at": self.trained_at,
            "training_samples": self.training_samples,
            "feature_count": self.feature_count,
            "validation_error": self.validation_error,
            "model_algorithm": self.model_algorithm,
            "sklearn_version": self.sklearn_version,
            "quantile_models": self.quantile_models,
            "ensemble_weights": self.ensemble_weights,
        }


@dataclass(frozen=True)
class ModelTrainingResult:
    """模型训练结果"""

    model_type: str
    version: str
    training_samples: int
    validation_error: float
    training_duration_seconds: float
    success: bool
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_type": self.model_type,
            "version": self.version,
            "training_samples": self.training_samples,
            "validation_error": self.validation_error,
            "training_duration_seconds": self.training_duration_seconds,
            "success": self.success,
            "message": self.message,
        }


@dataclass(frozen=True)
class ModelManagementResult:
    """模型管理操作结果"""

    action: str
    model_type: str
    success: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "model_type": self.model_type,
            "success": self.success,
            "message": self.message,
            "details": self.details,
        }


@dataclass(frozen=True)
class ModelStatus:
    """模型状态"""

    model_type: str
    version: str
    trained_at: str
    training_samples: int
    validation_error: float
    is_available: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_type": self.model_type,
            "version": self.version,
            "trained_at": self.trained_at,
            "training_samples": self.training_samples,
            "validation_error": self.validation_error,
            "is_available": self.is_available,
        }
