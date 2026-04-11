"""
测试工具模块

提供测试数据创建的辅助函数
"""

from datetime import datetime, timedelta

from src.core.models import (
    DailyPlan,
    TrainingLoad,
    TrainingPlan,
    UserContext,
    UserPreferences,
    WeeklySchedule,
)
from src.core.profile import RunnerProfile


def create_test_user_context() -> UserContext:
    """创建测试用户上下文"""
    return UserContext(
        profile=RunnerProfile(
            user_id="test_user",
            profile_date=datetime.now(),
            total_activities=100,
            total_distance_km=1500.0,
            total_duration_hours=150.0,
            avg_vdot=45.0,
            max_vdot=48.0,
            weekly_avg_distance_km=30.0,
            weekly_avg_duration_hours=3.5,
            avg_pace_min_per_km=6.0,
            resting_heart_rate=60.0,
            max_heart_rate=190.0,
        ),
        recent_activities=[],
        training_load=TrainingLoad(
            atl=10.0,
            ctl=12.0,
            tsb=-2.0,
            recent_4_weeks_distance_km=120.0,
            last_week_distance_km=35.0,
            avg_weekly_distance_km=30.0,
            longest_run_km=15.0,
            training_frequency=4,
        ),
        preferences=UserPreferences(
            preferred_training_days=["monday", "wednesday", "friday", "sunday"],
            preferred_training_time="morning",
            enable_calendar_sync=True,
        ),
        historical_best_pace_min_per_km=5.5,
    )


def create_test_training_plan(
    plan_id: str = "test_plan",
    goal_distance_km: float = 21.0975,
    goal_date: str | None = None,
    weeks: list[WeeklySchedule] | None = None,
    weekly_distance_km: float = 32.0,
    daily_workout_type: str = "easy_run",
    daily_distance_km: float = 8.0,
) -> TrainingPlan:
    """创建测试训练计划"""
    today = datetime.now()

    if goal_date is None:
        goal_date = (today + timedelta(days=14)).strftime("%Y-%m-%d")

    if weeks is None:
        week1_start = today + timedelta(days=1)
        week1_end = week1_start + timedelta(days=6)

        daily_plans_week1 = [
            DailyPlan(
                date=(week1_start + timedelta(days=i)).strftime("%Y-%m-%d"),
                workout_type=daily_workout_type if i % 2 == 0 else "rest",
                distance_km=daily_distance_km if i % 2 == 0 else 0.0,
                duration_min=int(daily_distance_km * 6) if i % 2 == 0 else 0,
                target_pace_min_per_km=6.0 if i % 2 == 0 else None,
                target_hr_zone=2 if i % 2 == 0 else None,
            )
            for i in range(7)
        ]

        week1 = WeeklySchedule(
            week_number=1,
            start_date=week1_start.strftime("%Y-%m-%d"),
            end_date=week1_end.strftime("%Y-%m-%d"),
            daily_plans=daily_plans_week1,
            weekly_distance_km=weekly_distance_km,
            weekly_duration_min=int(weekly_distance_km * 6),
            phase="base",
            focus="建立基础耐力",
        )
        weeks = [week1]

    return TrainingPlan(
        plan_id=plan_id,
        user_id="test_user",
        status="active",
        plan_type="race_preparation",
        goal_distance_km=goal_distance_km,
        goal_date=goal_date,
        start_date=weeks[0].start_date,
        end_date=goal_date,
        target_time="2:00:00",
        weeks=weeks,
        calendar_event_ids={},
        created_at=today.strftime("%Y-%m-%d %H:%M:%S"),
        updated_at=today.strftime("%Y-%m-%d %H:%M:%S"),
    )
