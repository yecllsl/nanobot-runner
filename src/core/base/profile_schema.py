# 跑者画像数据结构定义
# RunnerProfile 数据类 — 唯一真实来源 (Single Source of Truth)
# 本模块从 profile.py 拆分而来 (Task 20)

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.core.models import FitnessLevel, InjuryRiskLevel, TrainingPattern


@dataclass
class RunnerProfile:
    """跑者画像数据结构"""

    # 基本信息
    user_id: str
    profile_date: datetime
    total_activities: int = 0
    total_distance_km: float = 0.0
    total_duration_hours: float = 0.0

    # 体能指标
    avg_vdot: float = 0.0
    max_vdot: float = 0.0
    fitness_level: FitnessLevel = FitnessLevel.BEGINNER

    # 训练模式指标
    weekly_avg_distance_km: float = 0.0
    weekly_avg_duration_hours: float = 0.0
    training_pattern: TrainingPattern = TrainingPattern.REST

    # 心率指标
    avg_heart_rate: float | None = None
    max_heart_rate: float | None = None
    resting_heart_rate: float | None = None

    # 伤病风险
    injury_risk_level: InjuryRiskLevel = InjuryRiskLevel.LOW
    injury_risk_score: float = 0.0

    # 训练负荷
    atl: float = 0.0  # 急性训练负荷
    ctl: float = 0.0  # 慢性训练负荷
    tsb: float = 0.0  # 训练压力平衡

    # 其他指标
    avg_pace_min_per_km: float = 0.0
    favorite_running_time: str = "morning"  # morning, afternoon, evening
    consistency_score: float = 0.0  # 训练一致性评分 (0-100)

    # 元数据
    data_quality_score: float = 0.0  # 数据质量评分 (0-100)
    analysis_period_days: int = 0
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "user_id": self.user_id,
            "profile_date": self.profile_date.isoformat(),
            "total_activities": self.total_activities,
            "total_distance_km": round(self.total_distance_km, 2),
            "total_duration_hours": round(self.total_duration_hours, 2),
            "avg_vdot": round(self.avg_vdot, 2),
            "max_vdot": round(self.max_vdot, 2),
            "fitness_level": self.fitness_level.value,
            "weekly_avg_distance_km": round(self.weekly_avg_distance_km, 2),
            "weekly_avg_duration_hours": round(self.weekly_avg_duration_hours, 2),
            "training_pattern": self.training_pattern.value,
            "avg_heart_rate": self.avg_heart_rate,
            "max_heart_rate": self.max_heart_rate,
            "resting_heart_rate": self.resting_heart_rate,
            "injury_risk_level": self.injury_risk_level.value,
            "injury_risk_score": round(self.injury_risk_score, 2),
            "atl": round(self.atl, 2),
            "ctl": round(self.ctl, 2),
            "tsb": round(self.tsb, 2),
            "avg_pace_min_per_km": round(self.avg_pace_min_per_km, 2),
            "favorite_running_time": self.favorite_running_time,
            "consistency_score": round(self.consistency_score, 2),
            "data_quality_score": round(self.data_quality_score, 2),
            "analysis_period_days": self.analysis_period_days,
            "notes": self.notes,
        }
