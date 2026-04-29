from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Violation:
    rule_id: str
    rule_name: str
    actual_value: float
    limit_value: float
    message: str
    location: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "actual_value": self.actual_value,
            "limit_value": self.limit_value,
            "message": self.message,
            "location": self.location,
        }


@dataclass
class ValidationResult:
    passed: bool
    violations: list[Violation]
    retry_count: int
    action: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "violations": [v.to_dict() for v in self.violations],
            "retry_count": self.retry_count,
            "action": self.action,
        }


@dataclass
class DimensionResult:
    dimension: str
    score: float
    status: str
    details: dict[str, Any]
    recommendations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "score": self.score,
            "status": self.status,
            "details": self.details,
            "recommendations": self.recommendations,
        }


@dataclass
class AnalysisReport:
    overall_score: float
    dimensions: list[DimensionResult]
    recommendations: list[str]
    warnings: list[str]
    disclaimer: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_score": self.overall_score,
            "dimensions": [dim.to_dict() for dim in self.dimensions],
            "recommendations": self.recommendations,
            "warnings": self.warnings,
            "disclaimer": self.disclaimer,
        }


@dataclass
class SyncResult:
    success: bool
    message: str
    event_id: str | None = None
    error: str | None = None
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "message": self.message,
            "event_id": self.event_id,
            "error": self.error,
            "details": self.details,
        }


@dataclass(frozen=True)
class CalendarEventResult:
    success: bool
    event_id: str | None = None
    message: str = ""
    error: str | None = None
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"success": self.success}
        if self.event_id:
            result["event_id"] = self.event_id
        if self.message:
            result["message"] = self.message
        if self.error:
            result["error"] = self.error
        if self.data:
            result["data"] = self.data
        return result


@dataclass
class BatchSyncResult:
    total: int
    success: int
    failed: int
    results: list[SyncResult]

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "success": self.success,
            "failed": self.failed,
            "results": [r.to_dict() for r in self.results],
        }


@dataclass
class WeatherInfo:
    condition: str
    temperature: float
    humidity: float
    wind_speed: float
    alert: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "condition": self.condition,
            "temperature": self.temperature,
            "humidity": self.humidity,
            "wind_speed": self.wind_speed,
            "alert": self.alert,
        }


@dataclass
class NotifyResult:
    sent: bool
    message: str
    skipped: bool
    skip_reason: str | None = None
    weather_info: WeatherInfo | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "sent": self.sent,
            "message": self.message,
            "skipped": self.skipped,
            "skip_reason": self.skip_reason,
            "weather_info": (
                self.weather_info.to_dict() if self.weather_info else None
            ),
        }


@dataclass(frozen=True)
class RunningStats:
    total_runs: int
    total_distance: float
    total_duration: float
    avg_heart_rate: float
    avg_pace: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_runs": self.total_runs,
            "total_distance": self.total_distance,
            "total_duration": self.total_duration,
            "avg_heart_rate": self.avg_heart_rate,
            "avg_pace": self.avg_pace,
        }


@dataclass(frozen=True)
class HRDriftResult:
    drift: float = 0.0
    drift_rate: float = 0.0
    correlation: float = 0.0
    assessment: str = ""
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result = {
            "drift": self.drift,
            "drift_rate": self.drift_rate,
            "correlation": self.correlation,
            "assessment": self.assessment,
        }
        if self.error is not None:
            result["error"] = self.error
        return result


@dataclass(frozen=True)
class HRZoneResult:
    max_hr: int
    zones: list[dict[str, Any]]
    total_time_in_hr: int
    activities_count: int
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_hr": self.max_hr,
            "zones": self.zones,
            "total_time_in_hr": self.total_time_in_hr,
            "activities_count": self.activities_count,
            "message": self.message,
        }


@dataclass(frozen=True)
class ReportData:
    success: bool
    report_type: str | None
    content: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    message: str = ""
    generated_at: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "success": self.success,
            "report_type": self.report_type,
        }
        if self.content:
            result["content"] = self.content
        if self.data:
            result["data"] = self.data
        if self.message:
            result["message"] = self.message
        if self.generated_at:
            result["generated_at"] = self.generated_at
        if self.error:
            result["error"] = self.error
        return result


@dataclass(frozen=True)
class VdotTrendItem:
    date: str
    vdot: float
    distance: float
    duration: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "vdot": self.vdot,
            "distance": self.distance,
            "duration": self.duration,
        }


@dataclass(frozen=True)
class DailyReportData:
    date: str
    greeting: str
    yesterday_run: dict[str, Any] | None
    fitness_status: dict[str, Any]
    training_advice: str
    weekly_plan: list[dict[str, Any]]
    generated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "greeting": self.greeting,
            "yesterday_run": self.yesterday_run,
            "fitness_status": self.fitness_status,
            "training_advice": self.training_advice,
            "weekly_plan": self.weekly_plan,
            "generated_at": self.generated_at,
        }


@dataclass(frozen=True)
class PaceDistributionResult:
    zones: dict[str, dict[str, Any]]
    trend: list[dict[str, Any]]
    total_count: int = 0
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "zones": self.zones,
            "trend": self.trend,
            "total_count": self.total_count,
        }
        if self.message:
            result["message"] = self.message
        return result


@dataclass(frozen=True)
class OperationResult:
    success: bool
    message: str = ""
    error: str = ""
    data: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"success": self.success}
        if self.message:
            result["message"] = self.message
        if self.error:
            result["error"] = self.error
        if self.data:
            result["data"] = self.data
        return result


@dataclass(frozen=True)
class WeeklyReportData:
    type: str = "weekly"
    date_range: str = ""
    greeting: str = ""
    total_runs: int = 0
    total_distance_km: float = 0.0
    total_duration_min: float = 0.0
    total_tss: float = 0.0
    avg_vdot: float = 0.0
    training_load: dict[str, Any] | None = None
    highlights: list[str] | None = None
    concerns: list[str] | None = None
    recommendations: list[str] | None = None
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "type": self.type,
            "date_range": self.date_range,
            "greeting": self.greeting,
            "total_runs": self.total_runs,
            "total_distance_km": self.total_distance_km,
            "total_duration_min": self.total_duration_min,
            "total_tss": self.total_tss,
            "avg_vdot": self.avg_vdot,
        }
        if self.training_load:
            result["training_load"] = self.training_load
        if self.highlights:
            result["highlights"] = self.highlights
        if self.concerns:
            result["concerns"] = self.concerns
        if self.recommendations:
            result["recommendations"] = self.recommendations
        if self.error:
            result["error"] = self.error
        return result


@dataclass(frozen=True)
class MonthlyReportData:
    type: str = "monthly"
    month: str = ""
    greeting: str = ""
    total_runs: int = 0
    total_distance_km: float = 0.0
    total_duration_min: float = 0.0
    total_tss: float = 0.0
    avg_vdot: float = 0.0
    avg_weekly_distance_km: float = 0.0
    avg_weekly_duration_min: float = 0.0
    training_load: dict[str, Any] | None = None
    highlights: list[str] | None = None
    concerns: list[str] | None = None
    recommendations: list[str] | None = None
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "type": self.type,
            "month": self.month,
            "greeting": self.greeting,
            "total_runs": self.total_runs,
            "total_distance_km": self.total_distance_km,
            "total_duration_min": self.total_duration_min,
            "total_tss": self.total_tss,
            "avg_vdot": self.avg_vdot,
            "avg_weekly_distance_km": self.avg_weekly_distance_km,
            "avg_weekly_duration_min": self.avg_weekly_duration_min,
        }
        if self.training_load:
            result["training_load"] = self.training_load
        if self.highlights:
            result["highlights"] = self.highlights
        if self.concerns:
            result["concerns"] = self.concerns
        if self.recommendations:
            result["recommendations"] = self.recommendations
        if self.error:
            result["error"] = self.error
        return result
