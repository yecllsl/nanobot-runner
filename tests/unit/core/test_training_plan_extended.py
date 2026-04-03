# TrainingPlan 数据模型补充测试
# 提高覆盖率至80%以上

from datetime import datetime

import pytest

from src.core.training_plan import (
    DailyPlan,
    FitnessLevel,
    PlanType,
    TrainingPlan,
    WeeklySchedule,
    WorkoutType,
)


class TestDailyPlanExtended:
    """DailyPlan 扩展测试"""

    def test_daily_plan_with_all_optional_fields(self):
        """测试所有可选字段"""
        plan = DailyPlan(
            date="2026-04-10",
            workout_type=WorkoutType.EASY,
            distance_km=10.5,
            duration_min=60,
            target_pace_min_per_km=5.5,
            target_hr_zone=3,
            notes="测试训练",
            completed=True,
            actual_distance_km=10.3,
            actual_duration_min=58,
            actual_avg_hr=165,
            rpe=7,
            hr_drift=2.5,
            event_id="event_123",
        )

        assert plan.date == "2026-04-10"
        assert plan.workout_type == WorkoutType.EASY
        assert plan.distance_km == 10.5
        assert plan.duration_min == 60
        assert plan.target_pace_min_per_km == 5.5
        assert plan.target_hr_zone == 3
        assert plan.notes == "测试训练"
        assert plan.completed is True
        assert plan.actual_distance_km == 10.3
        assert plan.actual_duration_min == 58
        assert plan.actual_avg_hr == 165
        assert plan.rpe == 7
        assert plan.hr_drift == 2.5
        assert plan.event_id == "event_123"

    def test_daily_plan_to_dict_with_none_values(self):
        """测试包含None值的字典转换"""
        plan = DailyPlan(
            date="2026-04-10",
            workout_type=WorkoutType.EASY,
            distance_km=5.0,
            duration_min=30,
        )

        result = plan.to_dict()

        assert result["target_pace_min_per_km"] is None
        assert result["target_hr_zone"] is None
        assert result["actual_distance_km"] is None
        assert result["actual_duration_min"] is None
        assert result["actual_avg_hr"] is None
        assert result["rpe"] is None
        assert result["hr_drift"] is None
        assert result["event_id"] is None

    def test_daily_plan_all_workout_types(self):
        """测试所有训练类型"""
        workout_types = [
            WorkoutType.EASY,
            WorkoutType.LONG,
            WorkoutType.TEMPO,
            WorkoutType.INTERVAL,
            WorkoutType.RECOVERY,
            WorkoutType.REST,
            WorkoutType.CROSS,
        ]

        for workout_type in workout_types:
            plan = DailyPlan(
                date="2026-04-10",
                workout_type=workout_type,
                distance_km=5.0,
                duration_min=30,
            )
            assert plan.workout_type == workout_type


class TestWeeklyScheduleExtended:
    """WeeklySchedule 扩展测试"""

    def test_weekly_schedule_creation(self):
        """测试周计划创建"""
        daily_plans = [
            DailyPlan(
                date=f"2026-04-{10+i:02d}",
                workout_type=WorkoutType.EASY,
                distance_km=5.0,
                duration_min=30,
            )
            for i in range(7)
        ]

        week = WeeklySchedule(
            week_number=1,
            start_date="2026-04-10",
            end_date="2026-04-16",
            daily_plans=daily_plans,
            weekly_distance_km=35.0,
            weekly_duration_min=210,
            focus="有氧基础",
            notes="第一周训练",
        )

        assert week.week_number == 1
        assert week.start_date == "2026-04-10"
        assert week.end_date == "2026-04-16"
        assert len(week.daily_plans) == 7
        assert week.weekly_distance_km == 35.0
        assert week.weekly_duration_min == 210
        assert week.focus == "有氧基础"
        assert week.notes == "第一周训练"

    def test_weekly_schedule_to_dict(self):
        """测试周计划字典转换"""
        daily_plans = [
            DailyPlan(
                date="2026-04-10",
                workout_type=WorkoutType.EASY,
                distance_km=5.0,
                duration_min=30,
            )
        ]

        week = WeeklySchedule(
            week_number=1,
            start_date="2026-04-10",
            end_date="2026-04-16",
            daily_plans=daily_plans,
            weekly_distance_km=35.123,
            weekly_duration_min=210,
            focus="有氧基础",
            notes="第一周训练",
        )

        result = week.to_dict()

        assert result["week_number"] == 1
        assert result["start_date"] == "2026-04-10"
        assert result["end_date"] == "2026-04-16"
        assert len(result["daily_plans"]) == 1
        assert result["weekly_distance_km"] == 35.12  # 四舍五入
        assert result["weekly_duration_min"] == 210
        assert result["focus"] == "有氧基础"
        assert result["notes"] == "第一周训练"


class TestTrainingPlanExtended:
    """TrainingPlan 扩展测试"""

    def test_training_plan_creation(self):
        """测试训练计划创建"""
        daily_plan = DailyPlan(
            date="2026-04-10",
            workout_type=WorkoutType.EASY,
            distance_km=5.0,
            duration_min=30,
        )
        week = WeeklySchedule(
            week_number=1,
            start_date="2026-04-10",
            end_date="2026-04-16",
            daily_plans=[daily_plan],
        )

        plan = TrainingPlan(
            plan_id="plan_001",
            user_id="user_001",
            plan_type=PlanType.BASE,
            fitness_level=FitnessLevel.INTERMEDIATE,
            start_date="2026-04-10",
            end_date="2026-04-30",
            goal_distance_km=21.1,
            goal_date="2026-04-30",
            weeks=[week],
            notes="半马训练计划",
        )

        assert plan.plan_id == "plan_001"
        assert plan.user_id == "user_001"
        assert plan.plan_type == PlanType.BASE
        assert plan.fitness_level == FitnessLevel.INTERMEDIATE
        assert plan.start_date == "2026-04-10"
        assert plan.end_date == "2026-04-30"
        assert plan.goal_distance_km == 21.1
        assert plan.goal_date == "2026-04-30"
        assert len(plan.weeks) == 1
        assert plan.notes == "半马训练计划"

    def test_training_plan_to_dict(self):
        """测试训练计划字典转换"""
        daily_plan = DailyPlan(
            date="2026-04-10",
            workout_type=WorkoutType.EASY,
            distance_km=5.0,
            duration_min=30,
        )
        week = WeeklySchedule(
            week_number=1,
            start_date="2026-04-10",
            end_date="2026-04-16",
            daily_plans=[daily_plan],
        )

        plan = TrainingPlan(
            plan_id="plan_001",
            user_id="user_001",
            plan_type=PlanType.BASE,
            fitness_level=FitnessLevel.INTERMEDIATE,
            start_date="2026-04-10",
            end_date="2026-04-30",
            goal_distance_km=21.195,
            goal_date="2026-04-30",
            weeks=[week],
            notes="半马训练计划",
        )

        result = plan.to_dict()

        assert result["plan_id"] == "plan_001"
        assert result["user_id"] == "user_001"
        assert result["plan_type"] == "基础期"
        assert result["fitness_level"] == "中级"
        assert result["start_date"] == "2026-04-10"
        assert result["end_date"] == "2026-04-30"
        assert result["goal_distance_km"] == 21.2  # 四舍五入
        assert result["goal_date"] == "2026-04-30"
        assert len(result["weeks"]) == 1
        assert result["notes"] == "半马训练计划"
        assert "created_at" in result
        assert "updated_at" in result

    def test_training_plan_from_dict(self):
        """测试从字典创建训练计划"""
        data = {
            "plan_id": "plan_001",
            "user_id": "user_001",
            "plan_type": "基础期",
            "fitness_level": "中级",
            "start_date": "2026-04-10",
            "end_date": "2026-04-30",
            "goal_distance_km": 21.1,
            "goal_date": "2026-04-30",
            "weeks": [
                {
                    "week_number": 1,
                    "start_date": "2026-04-10",
                    "end_date": "2026-04-16",
                    "daily_plans": [
                        {
                            "date": "2026-04-10",
                            "workout_type": "轻松跑",
                            "distance_km": 5.0,
                            "duration_min": 30,
                            "target_pace_min_per_km": 6.0,
                            "target_hr_zone": 2,
                            "notes": "轻松跑",
                            "completed": False,
                            "actual_distance_km": None,
                            "actual_duration_min": None,
                            "actual_avg_hr": None,
                            "rpe": None,
                            "hr_drift": None,
                            "event_id": "event_123",
                        }
                    ],
                    "weekly_distance_km": 35.0,
                    "weekly_duration_min": 210,
                    "focus": "有氧基础",
                    "notes": "第一周",
                }
            ],
            "created_at": "2026-04-01T10:00:00",
            "updated_at": "2026-04-01T10:00:00",
            "notes": "半马训练计划",
        }

        plan = TrainingPlan.from_dict(data)

        assert plan.plan_id == "plan_001"
        assert plan.user_id == "user_001"
        assert plan.plan_type == PlanType.BASE
        assert plan.fitness_level == FitnessLevel.INTERMEDIATE
        assert plan.start_date == "2026-04-10"
        assert plan.end_date == "2026-04-30"
        assert plan.goal_distance_km == 21.1
        assert plan.goal_date == "2026-04-30"
        assert len(plan.weeks) == 1
        assert len(plan.weeks[0].daily_plans) == 1
        assert plan.weeks[0].daily_plans[0].event_id == "event_123"
        assert plan.notes == "半马训练计划"

    def test_training_plan_from_dict_without_timestamps(self):
        """测试从字典创建-无时间戳"""
        data = {
            "plan_id": "plan_001",
            "user_id": "user_001",
            "plan_type": "基础期",
            "fitness_level": "中级",
            "start_date": "2026-04-10",
            "end_date": "2026-04-30",
            "goal_distance_km": 21.1,
            "goal_date": "2026-04-30",
            "weeks": [],
        }

        plan = TrainingPlan.from_dict(data)

        assert plan.plan_id == "plan_001"
        assert isinstance(plan.created_at, datetime)
        assert isinstance(plan.updated_at, datetime)

    def test_training_plan_all_plan_types(self):
        """测试所有计划类型"""
        plan_types = [
            PlanType.BASE,
            PlanType.BUILD,
            PlanType.PEAK,
            PlanType.RACE,
            PlanType.RECOVERY,
        ]

        for plan_type in plan_types:
            plan = TrainingPlan(
                plan_id=f"plan_{plan_type.value}",
                user_id="user_001",
                plan_type=plan_type,
                fitness_level=FitnessLevel.INTERMEDIATE,
                start_date="2026-04-10",
                end_date="2026-04-30",
                goal_distance_km=21.1,
                goal_date="2026-04-30",
            )
            assert plan.plan_type == plan_type

    def test_training_plan_all_fitness_levels(self):
        """测试所有体能水平"""
        fitness_levels = [
            FitnessLevel.BEGINNER,
            FitnessLevel.INTERMEDIATE,
            FitnessLevel.ADVANCED,
            FitnessLevel.ELITE,
        ]

        for fitness_level in fitness_levels:
            plan = TrainingPlan(
                plan_id=f"plan_{fitness_level.value}",
                user_id="user_001",
                plan_type=PlanType.BASE,
                fitness_level=fitness_level,
                start_date="2026-04-10",
                end_date="2026-04-30",
                goal_distance_km=21.1,
                goal_date="2026-04-30",
            )
            assert plan.fitness_level == fitness_level


class TestTrainingPlanSerialization:
    """训练计划序列化测试"""

    def test_serialization_roundtrip(self):
        """测试序列化往返"""
        daily_plan = DailyPlan(
            date="2026-04-10",
            workout_type=WorkoutType.EASY,
            distance_km=5.5,
            duration_min=35,
            target_pace_min_per_km=5.5,
            target_hr_zone=3,
            notes="测试训练",
            completed=True,
            actual_distance_km=5.3,
            actual_duration_min=33,
            actual_avg_hr=160,
            rpe=6,
            hr_drift=2.1,
            event_id="event_123",
        )
        week = WeeklySchedule(
            week_number=1,
            start_date="2026-04-10",
            end_date="2026-04-16",
            daily_plans=[daily_plan],
            weekly_distance_km=35.5,
            weekly_duration_min=210,
            focus="有氧基础",
            notes="第一周",
        )

        original_plan = TrainingPlan(
            plan_id="plan_001",
            user_id="user_001",
            plan_type=PlanType.BASE,
            fitness_level=FitnessLevel.INTERMEDIATE,
            start_date="2026-04-10",
            end_date="2026-04-30",
            goal_distance_km=21.1,
            goal_date="2026-04-30",
            weeks=[week],
            notes="半马训练计划",
        )

        # 序列化
        plan_dict = original_plan.to_dict()

        # 反序列化
        restored_plan = TrainingPlan.from_dict(plan_dict)

        # 验证
        assert restored_plan.plan_id == original_plan.plan_id
        assert restored_plan.user_id == original_plan.user_id
        assert restored_plan.plan_type == original_plan.plan_type
        assert restored_plan.fitness_level == original_plan.fitness_level
        assert restored_plan.start_date == original_plan.start_date
        assert restored_plan.end_date == original_plan.end_date
        assert restored_plan.goal_distance_km == original_plan.goal_distance_km
        assert restored_plan.goal_date == original_plan.goal_date
        assert len(restored_plan.weeks) == len(original_plan.weeks)
        assert restored_plan.notes == original_plan.notes

        # 验证日计划
        original_daily = original_plan.weeks[0].daily_plans[0]
        restored_daily = restored_plan.weeks[0].daily_plans[0]
        assert restored_daily.date == original_daily.date
        assert restored_daily.workout_type == original_daily.workout_type
        assert restored_daily.distance_km == original_daily.distance_km
        assert restored_daily.duration_min == original_daily.duration_min
        assert restored_daily.event_id == original_daily.event_id
