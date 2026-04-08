"""
训练计划功能数据模型

定义训练计划制定与飞书日历同步功能所需的所有数据模型。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class PlanStatus(Enum):
    """训练计划状态"""

    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TrainingType(Enum):
    """训练类型"""

    EASY_RUN = "轻松跑"
    TEMPO_RUN = "节奏跑"
    INTERVAL = "间歇跑"
    LONG_RUN = "长距离跑"
    RECOVERY = "恢复跑"
    REST = "休息"


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

    preferred_training_days: List[str] = field(default_factory=list)
    preferred_training_time: str = "morning"
    max_weekly_distance_km: Optional[float] = None
    min_recovery_days_per_week: int = 2
    enable_calendar_sync: bool = True
    enable_training_reminder: bool = True
    reminder_time: str = "07:00"
    weather_alert_enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
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

    def to_dict(self) -> Dict[str, Any]:
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
    recent_activities: List[Any]
    training_load: TrainingLoad
    preferences: UserPreferences
    historical_best_pace_min_per_km: float

    def to_dict(self) -> Dict[str, Any]:
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
    """日计划"""

    date: str
    workout_type: str
    distance_km: float
    duration_min: int
    target_pace_min_per_km: Optional[float] = None
    target_hr_zone: Optional[int] = None
    notes: Optional[str] = None
    completed: bool = False
    calendar_event_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "date": self.date,
            "workout_type": self.workout_type,
            "distance_km": self.distance_km,
            "duration_min": self.duration_min,
            "target_pace_min_per_km": self.target_pace_min_per_km,
            "target_hr_zone": self.target_hr_zone,
            "notes": self.notes,
            "completed": self.completed,
            "calendar_event_id": self.calendar_event_id,
        }


@dataclass
class WeeklySchedule:
    """周计划"""

    week_number: int
    start_date: str
    end_date: str
    daily_plans: List[DailyPlan]
    weekly_distance_km: float
    weekly_duration_min: int
    phase: str
    focus: str = ""
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "week_number": self.week_number,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "daily_plans": [plan.to_dict() for plan in self.daily_plans],
            "weekly_distance_km": self.weekly_distance_km,
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
    status: str
    plan_type: str
    start_date: str
    end_date: str
    goal_distance_km: float
    goal_date: str
    target_time: str
    weeks: List[WeeklySchedule]
    calendar_event_ids: Dict[str, str]
    created_at: str
    updated_at: str
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "plan_id": self.plan_id,
            "user_id": self.user_id,
            "status": self.status,
            "plan_type": self.plan_type,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "goal_distance_km": self.goal_distance_km,
            "goal_date": self.goal_date,
            "target_time": self.target_time,
            "weeks": [week.to_dict() for week in self.weeks],
            "calendar_event_ids": self.calendar_event_ids,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }


@dataclass
class Violation:
    """违规项"""

    rule_id: str
    rule_name: str
    actual_value: float
    limit_value: float
    message: str
    location: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
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
    violations: List[Violation]
    retry_count: int
    action: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
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
    details: Dict[str, Any]
    recommendations: List[str]

    def to_dict(self) -> Dict[str, Any]:
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
    dimensions: List[DimensionResult]
    recommendations: List[str]
    warnings: List[str]
    disclaimer: str

    def to_dict(self) -> Dict[str, Any]:
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
    event_id: Optional[str] = None
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "success": self.success,
            "message": self.message,
            "event_id": self.event_id,
            "error": self.error,
            "details": self.details,
        }


@dataclass
class BatchSyncResult:
    """批量同步结果"""

    total: int
    success: int
    failed: int
    results: List[SyncResult]

    def to_dict(self) -> Dict[str, Any]:
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
    alert: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
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
    skip_reason: Optional[str] = None
    weather_info: Optional[WeatherInfo] = None

    def to_dict(self) -> Dict[str, Any]:
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
