from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, StrEnum
from typing import Any


class FitnessLevel(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    ELITE = "elite"

    @property
    def label(self) -> str:
        labels = {
            "beginner": "初学者",
            "intermediate": "中级",
            "advanced": "进阶",
            "elite": "精英",
        }
        return labels[self.value]


class DimensionType(Enum):
    FITNESS_MATCH = "体能匹配度"
    LOAD_PROGRESSION = "负荷递进性"
    INJURY_RISK = "伤病风险"
    GOAL_ACHIEVABILITY = "目标可达性"


class DimensionStatus(Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"


@dataclass
class UserPreferences:
    preferred_training_days: list[str] = field(default_factory=list)
    preferred_training_time: str = "morning"
    max_weekly_distance_km: float | None = None
    min_recovery_days_per_week: int = 2
    enable_calendar_sync: bool = True
    enable_training_reminder: bool = True
    reminder_time: str = "07:00"
    weather_alert_enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
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
    atl: float
    ctl: float
    tsb: float
    recent_4_weeks_distance_km: float = 0.0
    last_week_distance_km: float = 0.0
    avg_weekly_distance_km: float = 0.0
    longest_run_km: float = 0.0
    training_frequency: int = 0

    def to_dict(self) -> dict[str, Any]:
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
    profile: Any
    recent_activities: list[Any]
    training_load: TrainingLoad
    preferences: UserPreferences
    historical_best_pace_min_per_km: float

    def to_dict(self) -> dict[str, Any]:
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


def create_default_user_preferences() -> UserPreferences:
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
