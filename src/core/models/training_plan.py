from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from src.core.models.user_profile import (
    FitnessLevel,
)


class PlanStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PlanType(StrEnum):
    BASE = "base"
    BUILD = "build"
    PEAK = "peak"
    RACE = "race"
    RECOVERY = "recovery"

    @property
    def label(self) -> str:
        labels = {
            "base": "基础期",
            "build": "进展期",
            "peak": "巅峰期",
            "race": "比赛期",
            "recovery": "恢复期",
        }
        return labels[self.value]


class TrainingType(StrEnum):
    EASY = "easy"
    LONG = "long"
    TEMPO = "tempo"
    INTERVAL = "interval"
    RECOVERY = "recovery"
    REST = "rest"
    CROSS = "cross"

    @property
    def label(self) -> str:
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
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    TRAINING_CYCLE = "training_cycle"


class TrainingPattern(StrEnum):
    REST = "rest"
    LIGHT = "light"
    MODERATE = "moderate"
    INTENSE = "intense"
    EXTREME = "extreme"

    @property
    def label(self) -> str:
        labels = {
            "rest": "休息型",
            "light": "轻松型",
            "moderate": "适度型",
            "intense": "高强度型",
            "extreme": "极限型",
        }
        return labels[self.value]


class InjuryRiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"

    @property
    def label(self) -> str:
        labels = {
            "low": "低",
            "medium": "中",
            "high": "高",
            "very_high": "极高",
        }
        return labels[self.value]


@dataclass
class DailyPlan:
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
class PlanExecutionStats:
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
    workout_type: TrainingType
    avg_completion_rate: float
    avg_effort_score: float
    avg_hr_drift: float
    sample_count: int
    recommendation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "workout_type": self.workout_type.value,
            "avg_completion_rate": round(self.avg_completion_rate, 2),
            "avg_effort_score": round(self.avg_effort_score, 2),
            "avg_hr_drift": round(self.avg_hr_drift, 3),
            "sample_count": self.sample_count,
            "recommendation": self.recommendation,
        }


@dataclass
class PlanAdjustment:
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
        return self.goal_value - self.current_value

    @property
    def achievement_rate(self) -> float:
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
    plan_name: str
    target_race: str | None
    target_date: str | None
    current_vdot: float | None
    target_vdot: float | None
    total_weeks: int
    cycles: list[TrainingCycle]
    weekly_volume_range_km: tuple[float, float]
    key_milestones: list[str]
    training_plan_ids: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.total_weeks < 4:
            raise ValueError(f"total_weeks不能小于4，当前值：{self.total_weeks}")

    @property
    def has_target_race(self) -> bool:
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
            "training_plan_ids": self.training_plan_ids,
        }


@dataclass
class SmartTrainingAdvice:
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
class ScheduleStatus:
    enabled: bool
    configured: bool
    time: str = ""
    push: bool = True
    age: int = 30
    job_id: str = ""
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
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


def create_training_plan_id(user_id: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"plan_{user_id}_{timestamp}"
