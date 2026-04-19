"""
训练计划功能数据模型

定义训练计划制定与飞书日历同步功能所需的所有数据模型。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, StrEnum
from typing import Any


class PlanStatus(StrEnum):
    """训练计划状态"""

    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class FitnessLevel(StrEnum):
    """体能水平"""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    ELITE = "elite"

    @property
    def label(self) -> str:
        """中文标签"""
        labels = {
            "beginner": "初学者",
            "intermediate": "中级",
            "advanced": "进阶",
            "elite": "精英",
        }
        return labels[self.value]


class PlanType(StrEnum):
    """训练计划类型"""

    BASE = "base"
    BUILD = "build"
    PEAK = "peak"
    RACE = "race"
    RECOVERY = "recovery"

    @property
    def label(self) -> str:
        """中文标签"""
        labels = {
            "base": "基础期",
            "build": "进展期",
            "peak": "巅峰期",
            "race": "比赛期",
            "recovery": "恢复期",
        }
        return labels[self.value]


class TrainingType(StrEnum):
    """训练类型"""

    EASY = "easy"
    LONG = "long"
    TEMPO = "tempo"
    INTERVAL = "interval"
    RECOVERY = "recovery"
    REST = "rest"
    CROSS = "cross"

    @property
    def label(self) -> str:
        """中文标签"""
        labels = {
            "easy": "轻松跑",
            "long": "长距离跑",
            "tempo": "节奏跑",
            "interval": "间歇跑",
            "recovery": "恢复跑",
            "rest": "休息",
            "cross": "交叉训练",
        }
        return labels[self.value]


class ReportType(StrEnum):
    """报告类型"""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    TRAINING_CYCLE = "training_cycle"


class TrainingPattern(StrEnum):
    """训练模式"""

    REST = "rest"
    LIGHT = "light"
    MODERATE = "moderate"
    INTENSE = "intense"
    EXTREME = "extreme"

    @property
    def label(self) -> str:
        """中文标签"""
        labels = {
            "rest": "休息型",
            "light": "轻松型",
            "moderate": "适度型",
            "intense": "高强度型",
            "extreme": "极限型",
        }
        return labels[self.value]


class InjuryRiskLevel(StrEnum):
    """伤病风险等级"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"

    @property
    def label(self) -> str:
        """中文标签"""
        labels = {
            "low": "低",
            "medium": "中",
            "high": "高",
            "very_high": "极高",
        }
        return labels[self.value]


class DimensionType(Enum):
    """分析维度类型"""

    FITNESS_MATCH = "体能匹配度"
    LOAD_PROGRESSION = "负荷递进性"
    INJURY_RISK = "伤病风险"
    GOAL_ACHIEVABILITY = "目标可达性"


class DimensionStatus(Enum):
    """维度状态"""

    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"


@dataclass
class UserPreferences:
    """用户偏好"""

    preferred_training_days: list[str] = field(default_factory=list)
    preferred_training_time: str = "morning"
    max_weekly_distance_km: float | None = None
    min_recovery_days_per_week: int = 2
    enable_calendar_sync: bool = True
    enable_training_reminder: bool = True
    reminder_time: str = "07:00"
    weather_alert_enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "preferred_training_days": self.preferred_training_days,
            "preferred_training_time": self.preferred_training_time,
            "max_weekly_distance_km": self.max_weekly_distance_km,
            "min_recovery_days_per_week": self.min_recovery_days_per_week,
            "enable_calendar_sync": self.enable_calendar_sync,
            "enable_training_reminder": self.enable_training_reminder,
            "reminder_time": self.reminder_time,
            "weather_alert_enabled": self.weather_alert_enabled,
        }


@dataclass
class TrainingLoad:
    """训练负荷"""

    atl: float
    ctl: float
    tsb: float
    recent_4_weeks_distance_km: float = 0.0
    last_week_distance_km: float = 0.0
    avg_weekly_distance_km: float = 0.0
    longest_run_km: float = 0.0
    training_frequency: int = 0

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "atl": self.atl,
            "ctl": self.ctl,
            "tsb": self.tsb,
            "recent_4_weeks_distance_km": self.recent_4_weeks_distance_km,
            "last_week_distance_km": self.last_week_distance_km,
            "avg_weekly_distance_km": self.avg_weekly_distance_km,
            "longest_run_km": self.longest_run_km,
            "training_frequency": self.training_frequency,
        }


@dataclass
class UserContext:
    """用户上下文"""

    profile: Any
    recent_activities: list[Any]
    training_load: TrainingLoad
    preferences: UserPreferences
    historical_best_pace_min_per_km: float

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "profile": self.profile.to_dict()
            if hasattr(self.profile, "to_dict")
            else {},
            "recent_activities": [
                act.to_dict() if hasattr(act, "to_dict") else {}
                for act in self.recent_activities
            ],
            "training_load": (
                self.training_load.to_dict()
                if hasattr(self.training_load, "to_dict")
                else {}
            ),
            "preferences": self.preferences.to_dict(),
            "historical_best_pace_min_per_km": self.historical_best_pace_min_per_km,
        }


@dataclass
class DailyPlan:
    """日计划 - v0.10.0扩展"""

    date: str
    workout_type: TrainingType
    distance_km: float
    duration_min: int
    target_pace_min_per_km: float | None = None
    target_hr_zone: int | None = None
    notes: str = ""
    completed: bool = False
    actual_distance_km: float | None = None
    actual_duration_min: int | None = None
    actual_avg_hr: int | None = None
    rpe: int | None = None
    hr_drift: float | None = None
    event_id: str | None = None
    completion_rate: float | None = None
    effort_score: int | None = None
    feedback_notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "date": self.date,
            "workout_type": self.workout_type.value,
            "distance_km": round(self.distance_km, 2),
            "duration_min": self.duration_min,
            "target_pace_min_per_km": (
                round(self.target_pace_min_per_km, 2)
                if self.target_pace_min_per_km
                else None
            ),
            "target_hr_zone": self.target_hr_zone,
            "notes": self.notes,
            "completed": self.completed,
            "actual_distance_km": (
                round(self.actual_distance_km, 2) if self.actual_distance_km else None
            ),
            "actual_duration_min": self.actual_duration_min,
            "actual_avg_hr": self.actual_avg_hr,
            "rpe": self.rpe,
            "hr_drift": round(self.hr_drift, 2) if self.hr_drift else None,
            "event_id": self.event_id,
            "completion_rate": (
                round(self.completion_rate, 2) if self.completion_rate else None
            ),
            "effort_score": self.effort_score,
            "feedback_notes": self.feedback_notes,
        }


@dataclass
class WeeklySchedule:
    """周计划"""

    week_number: int
    start_date: str
    end_date: str
    daily_plans: list[DailyPlan] = field(default_factory=list)
    weekly_distance_km: float = 0.0
    weekly_duration_min: int = 0
    phase: str = ""
    focus: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "week_number": self.week_number,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "daily_plans": [plan.to_dict() for plan in self.daily_plans],
            "weekly_distance_km": round(self.weekly_distance_km, 2),
            "weekly_duration_min": self.weekly_duration_min,
            "phase": self.phase,
            "focus": self.focus,
            "notes": self.notes,
        }


@dataclass
class TrainingPlan:
    """训练计划"""

    plan_id: str
    user_id: str
    plan_type: PlanType
    fitness_level: FitnessLevel
    start_date: str
    end_date: str
    goal_distance_km: float
    goal_date: str
    weeks: list[WeeklySchedule] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    notes: str = ""
    status: PlanStatus = PlanStatus.DRAFT
    target_time: str | None = None
    calendar_event_ids: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "plan_id": self.plan_id,
            "user_id": self.user_id,
            "plan_type": self.plan_type.value,
            "fitness_level": self.fitness_level.value,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "goal_distance_km": round(self.goal_distance_km, 2),
            "goal_date": self.goal_date,
            "weeks": [week.to_dict() for week in self.weeks],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "notes": self.notes,
            "status": self.status.value,
            "target_time": self.target_time,
            "calendar_event_ids": self.calendar_event_ids,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TrainingPlan:
        """从字典创建训练计划"""
        weeks = []
        for week_data in data.get("weeks", []):
            daily_plans = []
            for day_data in week_data.get("daily_plans", []):
                daily_plan = DailyPlan(
                    date=day_data["date"],
                    workout_type=TrainingType(day_data["workout_type"]),
                    distance_km=day_data["distance_km"],
                    duration_min=day_data["duration_min"],
                    target_pace_min_per_km=day_data.get("target_pace_min_per_km"),
                    target_hr_zone=day_data.get("target_hr_zone"),
                    notes=day_data.get("notes", ""),
                    completed=day_data.get("completed", False),
                    actual_distance_km=day_data.get("actual_distance_km"),
                    actual_duration_min=day_data.get("actual_duration_min"),
                    actual_avg_hr=day_data.get("actual_avg_hr"),
                    rpe=day_data.get("rpe"),
                    hr_drift=day_data.get("hr_drift"),
                    event_id=day_data.get("event_id"),
                    completion_rate=day_data.get("completion_rate"),
                    effort_score=day_data.get("effort_score"),
                    feedback_notes=day_data.get("feedback_notes", ""),
                )
                daily_plans.append(daily_plan)

            week = WeeklySchedule(
                week_number=week_data["week_number"],
                start_date=week_data["start_date"],
                end_date=week_data["end_date"],
                daily_plans=daily_plans,
                weekly_distance_km=week_data.get("weekly_distance_km", 0.0),
                weekly_duration_min=week_data.get("weekly_duration_min", 0),
                phase=week_data.get("phase", ""),
                focus=week_data.get("focus", ""),
                notes=week_data.get("notes", ""),
            )
            weeks.append(week)

        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now()

        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        elif updated_at is None:
            updated_at = datetime.now()

        return cls(
            plan_id=data["plan_id"],
            user_id=data["user_id"],
            plan_type=PlanType(data["plan_type"]),
            fitness_level=FitnessLevel(data["fitness_level"]),
            start_date=data["start_date"],
            end_date=data["end_date"],
            goal_distance_km=data["goal_distance_km"],
            goal_date=data["goal_date"],
            weeks=weeks,
            created_at=created_at,
            updated_at=updated_at,
            notes=data.get("notes", ""),
            status=PlanStatus(data.get("status", "draft")),
            target_time=data.get("target_time"),
            calendar_event_ids=data.get("calendar_event_ids", {}),
            metadata=data.get("metadata"),
        )


@dataclass
class Violation:
    """违规项"""

    rule_id: str
    rule_name: str
    actual_value: float
    limit_value: float
    message: str
    location: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
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
    """校验结果"""

    passed: bool
    violations: list[Violation]
    retry_count: int
    action: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "passed": self.passed,
            "violations": [v.to_dict() for v in self.violations],
            "retry_count": self.retry_count,
            "action": self.action,
        }


@dataclass
class DimensionResult:
    """维度分析结果"""

    dimension: str
    score: float
    status: str
    details: dict[str, Any]
    recommendations: list[str]

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "dimension": self.dimension,
            "score": self.score,
            "status": self.status,
            "details": self.details,
            "recommendations": self.recommendations,
        }


@dataclass
class AnalysisReport:
    """分析报告"""

    overall_score: float
    dimensions: list[DimensionResult]
    recommendations: list[str]
    warnings: list[str]
    disclaimer: str

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "overall_score": self.overall_score,
            "dimensions": [dim.to_dict() for dim in self.dimensions],
            "recommendations": self.recommendations,
            "warnings": self.warnings,
            "disclaimer": self.disclaimer,
        }


@dataclass
class SyncResult:
    """同步结果"""

    success: bool
    message: str
    event_id: str | None = None
    error: str | None = None
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "success": self.success,
            "message": self.message,
            "event_id": self.event_id,
            "error": self.error,
            "details": self.details,
        }


@dataclass(frozen=True)
class CalendarEventResult:
    """日历事件操作结果"""

    success: bool
    event_id: str | None = None
    message: str = ""
    error: str | None = None
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
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
    """批量同步结果"""

    total: int
    success: int
    failed: int
    results: list[SyncResult]

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "total": self.total,
            "success": self.success,
            "failed": self.failed,
            "results": [r.to_dict() for r in self.results],
        }


@dataclass
class WeatherInfo:
    """天气信息"""

    condition: str
    temperature: float
    humidity: float
    wind_speed: float
    alert: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "condition": self.condition,
            "temperature": self.temperature,
            "humidity": self.humidity,
            "wind_speed": self.wind_speed,
            "alert": self.alert,
        }


@dataclass
class NotifyResult:
    """通知结果"""

    sent: bool
    message: str
    skipped: bool
    skip_reason: str | None = None
    weather_info: WeatherInfo | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "sent": self.sent,
            "message": self.message,
            "skipped": self.skipped,
            "skip_reason": self.skip_reason,
            "weather_info": (
                self.weather_info.to_dict() if self.weather_info else None
            ),
        }


@dataclass
class PlanExecutionStats:
    """计划执行统计 - v0.10.0新增"""

    plan_id: str
    total_planned_days: int
    completed_days: int
    completion_rate: float
    avg_effort_score: float
    total_distance_km: float
    total_duration_min: int
    avg_hr: int | None
    avg_hr_drift: float | None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "plan_id": self.plan_id,
            "total_planned_days": self.total_planned_days,
            "completed_days": self.completed_days,
            "completion_rate": round(self.completion_rate, 2),
            "avg_effort_score": round(self.avg_effort_score, 2),
            "total_distance_km": round(self.total_distance_km, 2),
            "total_duration_min": self.total_duration_min,
            "avg_hr": self.avg_hr,
            "avg_hr_drift": (
                round(self.avg_hr_drift, 3) if self.avg_hr_drift else None
            ),
        }


@dataclass
class TrainingResponsePattern:
    """训练响应模式 - v0.10.0新增"""

    workout_type: TrainingType
    avg_completion_rate: float
    avg_effort_score: float
    avg_hr_drift: float
    sample_count: int
    recommendation: str

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "workout_type": self.workout_type.value,
            "avg_completion_rate": round(self.avg_completion_rate, 2),
            "avg_effort_score": round(self.avg_effort_score, 2),
            "avg_hr_drift": round(self.avg_hr_drift, 3),
            "sample_count": self.sample_count,
            "recommendation": self.recommendation,
        }


def create_training_plan_id(user_id: str) -> str:
    """
    生成训练计划ID

    Args:
        user_id: 用户ID

    Returns:
        str: 训练计划ID
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"plan_{user_id}_{timestamp}"


def create_default_user_preferences() -> UserPreferences:
    """
    创建默认用户偏好

    Returns:
        UserPreferences: 默认用户偏好
    """
    return UserPreferences(
        preferred_training_days=["周一", "周三", "周五", "周日"],
        preferred_training_time="morning",
        max_weekly_distance_km=None,
        min_recovery_days_per_week=2,
        enable_calendar_sync=True,
        enable_training_reminder=True,
        reminder_time="07:00",
        weather_alert_enabled=True,
    )


@dataclass(frozen=True)
class RunningStats:
    """跑步统计数据"""

    total_runs: int
    total_distance: float
    total_duration: float
    avg_heart_rate: float
    avg_pace: str

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "total_runs": self.total_runs,
            "total_distance": self.total_distance,
            "total_duration": self.total_duration,
            "avg_heart_rate": self.avg_heart_rate,
            "avg_pace": self.avg_pace,
        }


@dataclass(frozen=True)
class HRDriftResult:
    """心率漂移分析结果"""

    drift: float = 0.0
    drift_rate: float = 0.0
    correlation: float = 0.0
    assessment: str = ""
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
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
    """心率区间分析结果"""

    max_hr: int
    zones: list[dict[str, Any]]
    total_time_in_hr: int
    activities_count: int
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "max_hr": self.max_hr,
            "zones": self.zones,
            "total_time_in_hr": self.total_time_in_hr,
            "activities_count": self.activities_count,
            "message": self.message,
        }


@dataclass(frozen=True)
class ReportData:
    """报告数据"""

    success: bool
    report_type: str | None
    content: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    message: str = ""
    generated_at: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
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
    """VDOT趋势数据项"""

    date: str
    vdot: float
    distance: float
    duration: float

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "date": self.date,
            "vdot": self.vdot,
            "distance": self.distance,
            "duration": self.duration,
        }


@dataclass(frozen=True)
class DailyReportData:
    """每日晨报数据"""

    date: str
    greeting: str
    yesterday_run: dict[str, Any] | None
    fitness_status: dict[str, Any]
    training_advice: str
    weekly_plan: list[dict[str, Any]]
    generated_at: str

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
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
    """配速分布分析结果"""

    zones: dict[str, dict[str, Any]]
    trend: list[dict[str, Any]]
    total_count: int = 0
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        result: dict[str, Any] = {
            "zones": self.zones,
            "trend": self.trend,
            "total_count": self.total_count,
        }
        if self.message:
            result["message"] = self.message
        return result


@dataclass
class PlanAdjustment:
    """计划调整 - v0.11.0新增"""

    adjustment_type: str
    original_value: Any
    adjusted_value: Any
    reason: str
    confidence: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence必须在0.0-1.0之间，当前值：{self.confidence}")
        valid_types = {"volume", "intensity", "type", "date"}
        if self.adjustment_type not in valid_types:
            raise ValueError(
                f"adjustment_type必须是{valid_types}之一，当前值：{self.adjustment_type}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "adjustment_type": self.adjustment_type,
            "original_value": self.original_value,
            "adjusted_value": self.adjusted_value,
            "reason": self.reason,
            "confidence": round(self.confidence, 2),
        }


@dataclass
class PlanSuggestion:
    """计划调整建议 - v0.11.0新增"""

    suggestion_type: str
    suggestion_content: str
    priority: str
    context: str
    confidence: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence必须在0.0-1.0之间，当前值：{self.confidence}")
        valid_priorities = {"high", "medium", "low"}
        if self.priority not in valid_priorities:
            raise ValueError(
                f"priority必须是{valid_priorities}之一，当前值：{self.priority}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "suggestion_type": self.suggestion_type,
            "suggestion_content": self.suggestion_content,
            "priority": self.priority,
            "context": self.context,
            "confidence": round(self.confidence, 2),
        }


@dataclass
class GoalAchievementEvaluation:
    """目标达成评估 - v0.12.0新增"""

    goal_type: str
    goal_value: float
    current_value: float
    achievement_probability: float
    key_risks: list[str]
    improvement_suggestions: list[str]
    estimated_weeks_to_achieve: int | None
    confidence: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.achievement_probability <= 1.0:
            raise ValueError(
                f"achievement_probability必须在0.0-1.0之间，当前值：{self.achievement_probability}"
            )
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence必须在0.0-1.0之间，当前值：{self.confidence}")

    @property
    def gap(self) -> float:
        """目标差距"""
        return self.goal_value - self.current_value

    @property
    def achievement_rate(self) -> float:
        """当前达成率"""
        if self.goal_value == 0:
            return 0.0
        return min(self.current_value / self.goal_value, 1.0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal_type": self.goal_type,
            "goal_value": self.goal_value,
            "current_value": self.current_value,
            "achievement_probability": round(self.achievement_probability, 2),
            "key_risks": self.key_risks,
            "improvement_suggestions": self.improvement_suggestions,
            "estimated_weeks_to_achieve": self.estimated_weeks_to_achieve,
            "confidence": round(self.confidence, 2),
            "gap": round(self.gap, 2),
            "achievement_rate": round(self.achievement_rate, 2),
        }


@dataclass
class TrainingCycle:
    """训练周期"""

    cycle_type: str
    start_date: str
    end_date: str
    weekly_volume_km: float
    key_workouts: list[str]
    goal: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "cycle_type": self.cycle_type,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "weekly_volume_km": self.weekly_volume_km,
            "key_workouts": self.key_workouts,
            "goal": self.goal,
        }


@dataclass
class LongTermPlan:
    """长期训练规划 - v0.12.0新增"""

    plan_name: str
    target_race: str | None
    target_date: str | None
    current_vdot: float | None
    target_vdot: float | None
    total_weeks: int
    cycles: list[TrainingCycle]
    weekly_volume_range_km: tuple[float, float]
    key_milestones: list[str]

    def __post_init__(self) -> None:
        if self.total_weeks < 4:
            raise ValueError(f"total_weeks不能小于4，当前值：{self.total_weeks}")

    @property
    def has_target_race(self) -> bool:
        """是否有目标比赛"""
        return self.target_race is not None and self.target_date is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_name": self.plan_name,
            "target_race": self.target_race,
            "target_date": self.target_date,
            "current_vdot": self.current_vdot,
            "target_vdot": self.target_vdot,
            "total_weeks": self.total_weeks,
            "cycles": [c.to_dict() for c in self.cycles],
            "weekly_volume_range_km": list(self.weekly_volume_range_km),
            "key_milestones": self.key_milestones,
            "has_target_race": self.has_target_race,
        }


@dataclass
class SmartTrainingAdvice:
    """智能训练建议 - v0.12.0新增"""

    advice_type: str
    content: str
    priority: str
    context: str
    confidence: float
    related_metrics: list[str]

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence必须在0.0-1.0之间，当前值：{self.confidence}")
        valid_types = {"training", "recovery", "nutrition", "injury_prevention"}
        if self.advice_type not in valid_types:
            raise ValueError(
                f"advice_type必须是{valid_types}之一，当前值：{self.advice_type}"
            )
        valid_priorities = {"high", "medium", "low"}
        if self.priority not in valid_priorities:
            raise ValueError(
                f"priority必须是{valid_priorities}之一，当前值：{self.priority}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "advice_type": self.advice_type,
            "content": self.content,
            "priority": self.priority,
            "context": self.context,
            "confidence": round(self.confidence, 2),
            "related_metrics": self.related_metrics,
        }


@dataclass(frozen=True)
class OperationResult:
    """通用操作结果"""

    success: bool
    message: str = ""
    error: str = ""
    data: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
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
    """周报数据"""

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
        """转换为字典"""
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
    """月报数据"""

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
        """转换为字典"""
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


@dataclass(frozen=True)
class ScheduleStatus:
    """定时推送状态"""

    enabled: bool
    configured: bool
    time: str = ""
    push: bool = True
    age: int = 30
    job_id: str = ""
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        result: dict[str, Any] = {
            "enabled": self.enabled,
            "configured": self.configured,
        }
        if self.time:
            result["time"] = self.time
        if self.push:
            result["push"] = self.push
        if self.age:
            result["age"] = self.age
        if self.job_id:
            result["job_id"] = self.job_id
        if self.message:
            result["message"] = self.message
        return result
