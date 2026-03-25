# 训练计划引擎单元测试
# 测试 TrainingPlanEngine 的所有核心功能

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from src.core.training_plan import (
    PHASE_CONFIG,
    DailyPlan,
    FitnessLevel,
    PlanType,
    TrainingPlan,
    TrainingPlanEngine,
    WeeklySchedule,
    WorkoutType,
)


class TestDailyPlan:
    """测试 DailyPlan 数据类"""

    def test_create_daily_plan(self):
        """测试创建单日训练计划"""
        plan = DailyPlan(
            date="2024-01-15",
            workout_type=WorkoutType.EASY,
            distance_km=5.0,
            duration_min=30,
            target_pace_min_per_km=6.0,
            target_hr_zone=2,
            notes="轻松有氧跑",
        )

        assert plan.date == "2024-01-15"
        assert plan.workout_type == WorkoutType.EASY
        assert plan.distance_km == 5.0
        assert plan.duration_min == 30
        assert plan.target_pace_min_per_km == 6.0
        assert plan.target_hr_zone == 2
        assert plan.notes == "轻松有氧跑"
        assert not plan.completed

    def test_daily_plan_to_dict(self):
        """测试转换为字典"""
        plan = DailyPlan(
            date="2024-01-15",
            workout_type=WorkoutType.TEMPO,
            distance_km=8.5,
            duration_min=40,
            target_pace_min_per_km=4.5,
            target_hr_zone=3,
            notes="节奏跑训练",
            completed=True,
            actual_distance_km=8.2,
            actual_duration_min=38,
            actual_avg_hr=165,
            rpe=7,
            hr_drift=3.5,
        )

        result = plan.to_dict()

        assert result["date"] == "2024-01-15"
        assert result["workout_type"] == "节奏跑"
        assert result["distance_km"] == 8.5
        assert result["duration_min"] == 40
        assert result["target_pace_min_per_km"] == 4.5
        assert result["target_hr_zone"] == 3
        assert result["completed"] is True
        assert result["actual_distance_km"] == 8.2
        assert result["actual_avg_hr"] == 165
        assert result["rpe"] == 7
        assert result["hr_drift"] == 3.5

    def test_daily_plan_to_dict_rounding(self):
        """测试字典转换的数值舍入"""
        plan = DailyPlan(
            date="2024-01-15",
            workout_type=WorkoutType.EASY,
            distance_km=5.123456,
            duration_min=30,
            target_pace_min_per_km=6.789,
            hr_drift=2.3456,
        )

        result = plan.to_dict()

        assert result["distance_km"] == 5.12
        assert result["target_pace_min_per_km"] == 6.79
        assert result["hr_drift"] == 2.35

    def test_daily_plan_optional_fields(self):
        """测试可选字段"""
        plan = DailyPlan(
            date="2024-01-15",
            workout_type=WorkoutType.REST,
            distance_km=0.0,
            duration_min=0,
        )

        assert plan.target_pace_min_per_km is None
        assert plan.target_hr_zone is None
        assert plan.actual_distance_km is None
        assert plan.rpe is None


class TestWeeklySchedule:
    """测试 WeeklySchedule 数据类"""

    def test_create_weekly_schedule(self):
        """测试创建周计划"""
        schedule = WeeklySchedule(
            week_number=1,
            start_date="2024-01-15",
            end_date="2024-01-21",
            focus="基础期第一周",
        )

        assert schedule.week_number == 1
        assert schedule.start_date == "2024-01-15"
        assert schedule.end_date == "2024-01-21"
        assert schedule.focus == "基础期第一周"
        assert len(schedule.daily_plans) == 0
        assert schedule.weekly_distance_km == 0.0
        assert schedule.weekly_duration_min == 0

    def test_weekly_schedule_with_daily_plans(self):
        """测试带每日计划的周计划"""
        schedule = WeeklySchedule(
            week_number=2,
            start_date="2024-01-22",
            end_date="2024-01-28",
        )

        # 添加每日计划
        schedule.daily_plans.append(
            DailyPlan(
                date="2024-01-22",
                workout_type=WorkoutType.EASY,
                distance_km=5.0,
                duration_min=30,
            )
        )
        schedule.daily_plans.append(
            DailyPlan(
                date="2024-01-23",
                workout_type=WorkoutType.LONG,
                distance_km=10.0,
                duration_min=60,
            )
        )

        # 更新周统计
        schedule.weekly_distance_km = sum(
            day.distance_km for day in schedule.daily_plans
        )
        schedule.weekly_duration_min = sum(
            day.duration_min for day in schedule.daily_plans
        )

        assert len(schedule.daily_plans) == 2
        assert schedule.weekly_distance_km == 15.0
        assert schedule.weekly_duration_min == 90

    def test_weekly_schedule_to_dict(self):
        """测试转换为字典"""
        schedule = WeeklySchedule(
            week_number=1,
            start_date="2024-01-15",
            end_date="2024-01-21",
            weekly_distance_km=50.0,
            weekly_duration_min=300,
            focus="基础期",
            notes="逐步增加跑量",
        )

        result = schedule.to_dict()

        assert result["week_number"] == 1
        assert result["weekly_distance_km"] == 50.0
        assert result["weekly_duration_min"] == 300
        assert result["focus"] == "基础期"
        assert result["notes"] == "逐步增加跑量"
        assert isinstance(result["daily_plans"], list)


class TestTrainingPlan:
    """测试 TrainingPlan 数据类"""

    def test_create_training_plan(self):
        """测试创建训练计划"""
        plan = TrainingPlan(
            plan_id="plan_001",
            user_id="user_123",
            plan_type=PlanType.BASE,
            fitness_level=FitnessLevel.INTERMEDIATE,
            start_date="2024-01-15",
            end_date="2024-03-15",
            goal_distance_km=21.0975,
            goal_date="2024-03-24",
        )

        assert plan.plan_id == "plan_001"
        assert plan.user_id == "user_123"
        assert plan.plan_type == PlanType.BASE
        assert plan.fitness_level == FitnessLevel.INTERMEDIATE
        assert plan.goal_distance_km == 21.0975
        assert len(plan.weeks) == 0

    def test_training_plan_to_dict(self):
        """测试转换为字典"""
        plan = TrainingPlan(
            plan_id="plan_001",
            user_id="user_123",
            plan_type=PlanType.BUILD,
            fitness_level=FitnessLevel.ADVANCED,
            start_date="2024-01-15",
            end_date="2024-04-15",
            goal_distance_km=42.195,
            goal_date="2024-04-21",
            notes="全马训练计划",
        )

        result = plan.to_dict()

        assert result["plan_id"] == "plan_001"
        assert result["plan_type"] == "进展期"
        assert result["fitness_level"] == "进阶"
        assert result["goal_distance_km"] == 42.20
        assert result["notes"] == "全马训练计划"
        assert "created_at" in result
        assert "updated_at" in result


class TestFitnessLevel:
    """测试 FitnessLevel 枚举"""

    def test_fitness_level_values(self):
        """测试体能水平枚举值"""
        assert FitnessLevel.BEGINNER.value == "初学者"
        assert FitnessLevel.INTERMEDIATE.value == "中级"
        assert FitnessLevel.ADVANCED.value == "进阶"
        assert FitnessLevel.ELITE.value == "精英"


class TestPlanType:
    """测试 PlanType 枚举"""

    def test_plan_type_values(self):
        """测试计划类型枚举值"""
        assert PlanType.BASE.value == "基础期"
        assert PlanType.BUILD.value == "进展期"
        assert PlanType.PEAK.value == "巅峰期"
        assert PlanType.RACE.value == "比赛期"
        assert PlanType.RECOVERY.value == "恢复期"


class TestWorkoutType:
    """测试 WorkoutType 枚举"""

    def test_workout_type_values(self):
        """测试训练类型枚举值"""
        assert WorkoutType.EASY.value == "轻松跑"
        assert WorkoutType.LONG.value == "长距离跑"
        assert WorkoutType.TEMPO.value == "节奏跑"
        assert WorkoutType.INTERVAL.value == "间歇跑"
        assert WorkoutType.RECOVERY.value == "恢复跑"
        assert WorkoutType.REST.value == "休息"
        assert WorkoutType.CROSS.value == "交叉训练"


class TestPhaseConfig:
    """测试 PHASE_CONFIG 配置"""

    def test_phase_config_structure(self):
        """测试阶段配置结构"""
        for plan_type, config in PHASE_CONFIG.items():
            assert "duration_weeks" in config
            assert "easy_ratio" in config
            assert "intensity_multiplier" in config
            assert "weekly_increase" in config

            # 验证比例总和约为 1
            total_ratio = (
                config.get("easy_ratio", 0)
                + config.get("long_ratio", 0)
                + config.get("tempo_ratio", 0)
                + config.get("interval_ratio", 0)
                + config.get("cross_ratio", 0)
            )
            assert 0.9 <= total_ratio <= 1.1  # 允许 10% 误差

    def test_base_phase_config(self):
        """测试基础期配置"""
        config = PHASE_CONFIG[PlanType.BASE]
        assert config["duration_weeks"] == 4
        assert config["easy_ratio"] == 0.80
        assert config["intensity_multiplier"] == 0.7
        assert config["weekly_increase"] == 0.10


class TestTrainingPlanEngine:
    """测试 TrainingPlanEngine 类"""

    @pytest.fixture
    def engine(self):
        """创建 TrainingPlanEngine 实例"""
        return TrainingPlanEngine()

    def test_init(self, engine):
        """测试初始化"""
        assert engine is not None

    def test_get_phase_config_by_fitness_level_beginner(self, engine):
        """测试初学者阶段配置"""
        config = engine.get_phase_config_by_fitness_level(
            PlanType.BASE, FitnessLevel.BEGINNER
        )

        assert (
            config["intensity_multiplier"]
            < PHASE_CONFIG[PlanType.BASE]["intensity_multiplier"]
        )
        assert config["easy_ratio"] > PHASE_CONFIG[PlanType.BASE]["easy_ratio"]
        assert (
            config["weekly_increase"] < PHASE_CONFIG[PlanType.BASE]["weekly_increase"]
        )

    def test_get_phase_config_by_fitness_level_intermediate(self, engine):
        """测试中级阶段配置（标准配置）"""
        config = engine.get_phase_config_by_fitness_level(
            PlanType.BASE, FitnessLevel.INTERMEDIATE
        )

        # 中级应该保持标准配置
        assert (
            config["intensity_multiplier"]
            == PHASE_CONFIG[PlanType.BASE]["intensity_multiplier"]
        )
        assert config["easy_ratio"] == PHASE_CONFIG[PlanType.BASE]["easy_ratio"]

    def test_get_phase_config_by_fitness_level_advanced(self, engine):
        """测试进阶阶段配置"""
        config = engine.get_phase_config_by_fitness_level(
            PlanType.BUILD, FitnessLevel.ADVANCED
        )

        assert (
            config["intensity_multiplier"]
            > PHASE_CONFIG[PlanType.BUILD]["intensity_multiplier"]
        )
        assert config.get("interval_ratio", 0) > PHASE_CONFIG[PlanType.BUILD].get(
            "interval_ratio", 0
        )

    def test_get_phase_config_by_fitness_level_elite(self, engine):
        """测试精英阶段配置"""
        config = engine.get_phase_config_by_fitness_level(
            PlanType.PEAK, FitnessLevel.ELITE
        )

        assert (
            config["intensity_multiplier"]
            > PHASE_CONFIG[PlanType.PEAK]["intensity_multiplier"]
        )
        assert config.get("interval_ratio", 0) > PHASE_CONFIG[PlanType.PEAK].get(
            "interval_ratio", 0
        )

    def test_determine_fitness_level(self, engine):
        """测试体能水平判定"""
        assert engine._determine_fitness_level(25) == FitnessLevel.BEGINNER
        assert engine._determine_fitness_level(35) == FitnessLevel.INTERMEDIATE
        assert engine._determine_fitness_level(50) == FitnessLevel.ADVANCED
        assert engine._determine_fitness_level(65) == FitnessLevel.ELITE

    def test_determine_fitness_level_boundaries(self, engine):
        """测试体能水平判定边界值"""
        assert engine._determine_fitness_level(29.9) == FitnessLevel.BEGINNER
        assert engine._determine_fitness_level(30) == FitnessLevel.INTERMEDIATE
        assert engine._determine_fitness_level(44.9) == FitnessLevel.INTERMEDIATE
        assert engine._determine_fitness_level(45) == FitnessLevel.ADVANCED
        assert engine._determine_fitness_level(59.9) == FitnessLevel.ADVANCED
        assert engine._determine_fitness_level(60) == FitnessLevel.ELITE

    def test_allocate_phases_short_distance(self, engine):
        """测试短距离阶段分配"""
        phases = engine._allocate_phases(total_weeks=8, goal_distance_km=5)

        assert len(phases) >= 2
        # 短距离应该包含基础期和比赛期
        phase_types = [p[0] for p in phases]
        assert PlanType.BASE in phase_types
        assert PlanType.RACE in phase_types

    def test_allocate_phases_half_marathon(self, engine):
        """测试半马阶段分配"""
        phases = engine._allocate_phases(total_weeks=12, goal_distance_km=21)

        assert len(phases) >= 3
        # 半马应该包含基础期、进展期、巅峰期和比赛期
        phase_types = [p[0] for p in phases]
        assert PlanType.BASE in phase_types
        assert PlanType.BUILD in phase_types
        assert PlanType.RACE in phase_types

    def test_allocate_phases_full_marathon(self, engine):
        """测试全马阶段分配"""
        phases = engine._allocate_phases(total_weeks=16, goal_distance_km=42)

        assert len(phases) >= 4
        # 全马应该包含所有阶段
        phase_types = [p[0] for p in phases]
        assert PlanType.BASE in phase_types
        assert PlanType.BUILD in phase_types
        assert PlanType.PEAK in phase_types
        assert PlanType.RACE in phase_types

    def test_calculate_target_pace(self, engine):
        """测试目标配速计算"""
        # VDOT 越高，配速越快
        pace_vdot40 = engine._calculate_target_pace(40, WorkoutType.EASY)
        pace_vdot50 = engine._calculate_target_pace(50, WorkoutType.EASY)

        assert pace_vdot40 > pace_vdot50  # VDOT 低配速慢
        assert 3.0 <= pace_vdot40 <= 8.0  # 在合理范围内
        assert 3.0 <= pace_vdot50 <= 8.0

    def test_calculate_target_pace_workout_types(self, engine):
        """测试不同训练类型的目标配速"""
        vdot = 45

        easy_pace = engine._calculate_target_pace(vdot, WorkoutType.EASY)
        tempo_pace = engine._calculate_target_pace(vdot, WorkoutType.TEMPO)
        interval_pace = engine._calculate_target_pace(vdot, WorkoutType.INTERVAL)

        # 轻松跑最慢，间歇跑最快
        assert easy_pace > tempo_pace > interval_pace

    def test_generate_weekly_schedule(self, engine):
        """测试周计划生成"""
        schedule = engine._generate_weekly_schedule(
            week_number=1,
            start_date="2024-01-15",
            end_date="2024-01-21",
            weekly_distance_km=40.0,
            phase_config=PHASE_CONFIG[PlanType.BASE],
            fitness_level=FitnessLevel.INTERMEDIATE,
            current_vdot=40,
        )

        assert schedule.week_number == 1
        assert len(schedule.daily_plans) == 7
        assert schedule.weekly_distance_km > 0
        assert schedule.weekly_duration_min > 0

        # 应该包含休息日
        rest_days = [
            day for day in schedule.daily_plans if day.workout_type == WorkoutType.REST
        ]
        assert len(rest_days) >= 1

    def test_generate_plan_success(self, engine):
        """测试成功生成训练计划"""
        future_date = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")

        plan = engine.generate_plan(
            user_id="test_user",
            goal_distance_km=21.0975,
            goal_date=future_date,
            current_vdot=40,
            current_weekly_distance_km=30,
            age=30,
            resting_hr=60,
        )

        assert plan.user_id == "test_user"
        assert plan.goal_distance_km == 21.0975
        assert len(plan.weeks) > 0
        assert plan.fitness_level == FitnessLevel.INTERMEDIATE
        assert "VDOT" in plan.notes

    def test_generate_plan_invalid_goal_distance(self, engine):
        """测试无效目标距离"""
        future_date = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")

        with pytest.raises(ValueError, match="目标距离必须为正数"):
            engine.generate_plan(
                user_id="test_user",
                goal_distance_km=0,
                goal_date=future_date,
                current_vdot=40,
                current_weekly_distance_km=30,
            )

    def test_generate_plan_invalid_goal_date(self, engine):
        """测试无效目标日期"""
        past_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        with pytest.raises(ValueError, match="目标日期必须晚于今天"):
            engine.generate_plan(
                user_id="test_user",
                goal_distance_km=21,
                goal_date=past_date,
                current_vdot=40,
                current_weekly_distance_km=30,
            )

    def test_generate_plan_invalid_vdot(self, engine):
        """测试无效 VDOT 值"""
        future_date = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")

        with pytest.raises(ValueError, match="VDOT 值必须为正数"):
            engine.generate_plan(
                user_id="test_user",
                goal_distance_km=21,
                goal_date=future_date,
                current_vdot=0,
                current_weekly_distance_km=30,
            )

    def test_generate_plan_invalid_age(self, engine):
        """测试无效年龄"""
        future_date = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")

        with pytest.raises(ValueError, match="年龄必须在 1-120 之间"):
            engine.generate_plan(
                user_id="test_user",
                goal_distance_km=21,
                goal_date=future_date,
                current_vdot=40,
                current_weekly_distance_km=30,
                age=0,
            )

    def test_generate_plan_insufficient_weeks(self, engine):
        """测试训练时间不足"""
        near_date = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")

        with pytest.raises(ValueError, match="训练时间至少需要 4 周"):
            engine.generate_plan(
                user_id="test_user",
                goal_distance_km=21,
                goal_date=near_date,
                current_vdot=40,
                current_weekly_distance_km=30,
            )

    def test_adjust_plan_hr_drift_high(self, engine):
        """测试心率漂移高时的计划调整"""
        future_date = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")
        plan = engine.generate_plan(
            user_id="test_user",
            goal_distance_km=21,
            goal_date=future_date,
            current_vdot=40,
            current_weekly_distance_km=30,
        )

        original_distance = plan.weeks[0].weekly_distance_km

        # 心率漂移>10%，应该大幅降低训练负荷
        adjusted_plan = engine.adjust_plan(plan=plan, week_number=1, hr_drift=12.5)

        adjusted_distance = adjusted_plan.weeks[0].weekly_distance_km
        assert adjusted_distance < original_distance
        assert "心率漂移" in adjusted_plan.weeks[0].notes

    def test_adjust_plan_rpe_high(self, engine):
        """测试主观疲劳度高时的计划调整"""
        future_date = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")
        plan = engine.generate_plan(
            user_id="test_user",
            goal_distance_km=21,
            goal_date=future_date,
            current_vdot=40,
            current_weekly_distance_km=30,
        )

        original_distance = plan.weeks[0].weekly_distance_km

        # RPE>=8，应该降低训练量
        adjusted_plan = engine.adjust_plan(plan=plan, week_number=1, rpe=8)

        adjusted_distance = adjusted_plan.weeks[0].weekly_distance_km
        assert adjusted_distance < original_distance
        assert "主观疲劳度" in adjusted_plan.weeks[0].notes

    def test_adjust_plan_combined_factors(self, engine):
        """测试多因素组合调整"""
        future_date = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")
        plan = engine.generate_plan(
            user_id="test_user",
            goal_distance_km=21,
            goal_date=future_date,
            current_vdot=40,
            current_weekly_distance_km=30,
        )

        original_distance = plan.weeks[0].weekly_distance_km

        # 心率漂移 + 高 RPE
        adjusted_plan = engine.adjust_plan(
            plan=plan, week_number=1, hr_drift=7.5, rpe=7
        )

        adjusted_distance = adjusted_plan.weeks[0].weekly_distance_km
        assert adjusted_distance < original_distance
        assert "心率漂移" in adjusted_plan.weeks[0].notes
        assert "主观疲劳度" in adjusted_plan.weeks[0].notes

    def test_adjust_plan_invalid_week(self, engine):
        """测试无效周数"""
        future_date = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")
        plan = engine.generate_plan(
            user_id="test_user",
            goal_distance_km=21,
            goal_date=future_date,
            current_vdot=40,
            current_weekly_distance_km=30,
        )

        with pytest.raises(ValueError, match="周数必须在"):
            engine.adjust_plan(plan=plan, week_number=0)

        with pytest.raises(ValueError, match="周数必须在"):
            engine.adjust_plan(plan=plan, week_number=len(plan.weeks) + 1)

    def test_adjust_plan_invalid_hr_drift(self, engine):
        """测试无效心率漂移值"""
        future_date = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")
        plan = engine.generate_plan(
            user_id="test_user",
            goal_distance_km=21,
            goal_date=future_date,
            current_vdot=40,
            current_weekly_distance_km=30,
        )

        with pytest.raises(ValueError, match="心率漂移值异常"):
            engine.adjust_plan(plan=plan, week_number=1, hr_drift=60)

    def test_adjust_plan_invalid_rpe(self, engine):
        """测试无效 RPE 值"""
        future_date = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")
        plan = engine.generate_plan(
            user_id="test_user",
            goal_distance_km=21,
            goal_date=future_date,
            current_vdot=40,
            current_weekly_distance_km=30,
        )

        with pytest.raises(ValueError, match="主观疲劳度必须在 1-10 之间"):
            engine.adjust_plan(plan=plan, week_number=1, rpe=11)

    def test_get_daily_workout_success(self, engine):
        """测试成功获取当日训练"""
        future_date = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")
        plan = engine.generate_plan(
            user_id="test_user",
            goal_distance_km=21,
            goal_date=future_date,
            current_vdot=40,
            current_weekly_distance_km=30,
        )

        # 获取第一周第一天的训练
        first_day_date = plan.weeks[0].daily_plans[0].date
        daily_plan = engine.get_daily_workout(plan=plan, target_date=first_day_date)

        assert daily_plan is not None
        assert daily_plan.date == first_day_date
        assert daily_plan.workout_type is not None

    def test_get_daily_workout_today(self, engine):
        """测试获取今日训练"""
        future_date = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")
        plan = engine.generate_plan(
            user_id="test_user",
            goal_distance_km=21,
            goal_date=future_date,
            current_vdot=40,
            current_weekly_distance_km=30,
        )

        # 不指定日期，应该返回今日训练
        daily_plan = engine.get_daily_workout(plan=plan)

        # 今日应该在第一周
        if daily_plan:
            assert daily_plan.date == datetime.now().strftime("%Y-%m-%d")

    def test_get_daily_workout_not_found(self, engine):
        """测试未找到训练计划"""
        future_date = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")
        plan = engine.generate_plan(
            user_id="test_user",
            goal_distance_km=21,
            goal_date=future_date,
            current_vdot=40,
            current_weekly_distance_km=30,
        )

        # 查询计划外的日期
        past_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
        daily_plan = engine.get_daily_workout(plan=plan, target_date=past_date)

        assert daily_plan is None

    def test_get_daily_workout_invalid_date(self, engine):
        """测试无效日期格式"""
        future_date = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")
        plan = engine.generate_plan(
            user_id="test_user",
            goal_distance_km=21,
            goal_date=future_date,
            current_vdot=40,
            current_weekly_distance_km=30,
        )

        with pytest.raises(ValueError, match="日期格式无效"):
            engine.get_daily_workout(plan=plan, target_date="2024/01/15")

    def test_get_plan_summary(self, engine):
        """测试获取计划摘要"""
        future_date = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")
        plan = engine.generate_plan(
            user_id="test_user",
            goal_distance_km=21,
            goal_date=future_date,
            current_vdot=40,
            current_weekly_distance_km=30,
        )

        summary = engine.get_plan_summary(plan)

        assert summary["plan_id"] == plan.plan_id
        assert summary["user_id"] == plan.user_id
        assert summary["duration_weeks"] == len(plan.weeks)
        assert summary["total_distance_km"] > 0
        assert summary["total_duration_hours"] > 0
        assert "workout_distribution" in summary
        assert isinstance(summary["workout_distribution"], dict)


class TestTrainingPlanIntegration:
    """训练计划引擎集成测试"""

    @pytest.fixture
    def engine(self):
        """创建 TrainingPlanEngine 实例"""
        return TrainingPlanEngine()

    def test_full_workflow_generate_and_adjust(self, engine):
        """测试完整工作流：生成→调整→获取"""
        # 1. 生成计划
        future_date = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")
        plan = engine.generate_plan(
            user_id="test_user",
            goal_distance_km=21.0975,
            goal_date=future_date,
            current_vdot=42,
            current_weekly_distance_km=35,
            age=28,
            resting_hr=58,
        )

        assert len(plan.weeks) > 0
        assert plan.fitness_level == FitnessLevel.INTERMEDIATE

        # 保存原始跑量（adjust_plan 会修改原对象）
        original_distance = plan.weeks[0].weekly_distance_km

        # 2. 调整第一周计划（模拟心率漂移和高 RPE）
        adjusted_plan = engine.adjust_plan(
            plan=plan, week_number=1, hr_drift=6.5, rpe=7
        )

        assert adjusted_plan.updated_at >= plan.created_at
        # 调整后跑量应该减少（hr_drift=6.5% 触发 15% 减少，rpe=7 触发 15% 减少，总共约 28% 减少）
        assert adjusted_plan.weeks[0].weekly_distance_km < original_distance

        # 3. 获取当日训练
        first_day_date = adjusted_plan.weeks[0].daily_plans[0].date
        daily_workout = engine.get_daily_workout(
            plan=adjusted_plan, target_date=first_day_date
        )

        assert daily_workout is not None
        assert daily_workout.workout_type is not None

        # 4. 获取计划摘要
        summary = engine.get_plan_summary(adjusted_plan)

        assert summary["duration_weeks"] == len(adjusted_plan.weeks)
        # goal_distance_km 会被四舍五入到 2 位小数
        assert abs(summary["goal_distance_km"] - 21.0975) < 0.01

    def test_different_fitness_levels(self, engine):
        """测试不同体能水平的计划生成"""
        future_date = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")

        # 初学者
        beginner_plan = engine.generate_plan(
            user_id="beginner",
            goal_distance_km=10,
            goal_date=future_date,
            current_vdot=25,
            current_weekly_distance_km=15,
        )

        # 精英
        elite_plan = engine.generate_plan(
            user_id="elite",
            goal_distance_km=42,
            goal_date=future_date,
            current_vdot=65,
            current_weekly_distance_km=80,
        )

        # 精英的总跑量应该更高
        beginner_total = sum(week.weekly_distance_km for week in beginner_plan.weeks)
        elite_total = sum(week.weekly_distance_km for week in elite_plan.weeks)

        assert elite_total > beginner_total

        # 初学者应该有更高的轻松跑比例
        beginner_config = engine.get_phase_config_by_fitness_level(
            PlanType.BASE, FitnessLevel.BEGINNER
        )
        elite_config = engine.get_phase_config_by_fitness_level(
            PlanType.BASE, FitnessLevel.ELITE
        )

        assert beginner_config["easy_ratio"] > elite_config["easy_ratio"]

    def test_different_goal_distances(self, engine):
        """测试不同目标距离的计划生成"""
        future_date = (datetime.now() + timedelta(days=120)).strftime("%Y-%m-%d")

        # 5km 计划
        plan_5k = engine.generate_plan(
            user_id="user_5k",
            goal_distance_km=5,
            goal_date=future_date,
            current_vdot=40,
            current_weekly_distance_km=20,
        )

        # 全马计划
        plan_42k = engine.generate_plan(
            user_id="user_42k",
            goal_distance_km=42.195,
            goal_date=future_date,
            current_vdot=45,
            current_weekly_distance_km=50,
        )

        # 全马计划应该更长
        assert len(plan_42k.weeks) >= len(plan_5k.weeks)

        # 全马的总跑量应该更高
        total_5k = sum(week.weekly_distance_km for week in plan_5k.weeks)
        total_42k = sum(week.weekly_distance_km for week in plan_42k.weeks)

        assert total_42k > total_5k

    def test_plan_serialization(self, engine):
        """测试计划序列化"""
        future_date = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")
        plan = engine.generate_plan(
            user_id="test_user",
            goal_distance_km=21,
            goal_date=future_date,
            current_vdot=40,
            current_weekly_distance_km=30,
        )

        # 转换为字典
        plan_dict = plan.to_dict()

        # 验证关键字段
        assert "plan_id" in plan_dict
        assert "user_id" in plan_dict
        assert "weeks" in plan_dict
        assert isinstance(plan_dict["weeks"], list)

        # 验证周计划
        if plan_dict["weeks"]:
            week_dict = plan_dict["weeks"][0]
            assert "week_number" in week_dict
            assert "daily_plans" in week_dict
            assert isinstance(week_dict["daily_plans"], list)

            # 验证每日计划
            if week_dict["daily_plans"]:
                day_dict = week_dict["daily_plans"][0]
                assert "date" in day_dict
                assert "workout_type" in day_dict
                assert "distance_km" in day_dict
