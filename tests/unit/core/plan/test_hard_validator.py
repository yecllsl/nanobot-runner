"""
HardValidator 单元测试
"""

from datetime import datetime, timedelta

from src.core.models import (
    DailyPlan,
    TrainingPlan,
    ValidationResult,
    Violation,
    WeeklySchedule,
)
from src.core.plan.hard_validator import HardValidator


class TestHardValidator:
    """HardValidator 测试类"""

    def setup_method(self):
        """每个测试方法前的设置"""
        self.validator = HardValidator()

    def _create_training_plan(
        self,
        plan_id: str,
        weeks: list[WeeklySchedule],
        goal_distance_km: float = 21.0975,
        goal_date: str = None,
    ) -> TrainingPlan:
        """创建训练计划辅助方法"""
        today = datetime.now()
        if goal_date is None:
            goal_date = (today + timedelta(days=14)).strftime("%Y-%m-%d")

        return TrainingPlan(
            plan_id=plan_id,
            user_id="test_user",
            status="active",
            plan_type="race_preparation",
            goal_distance_km=goal_distance_km,
            goal_date=goal_date,
            start_date=weeks[0].start_date if weeks else today.strftime("%Y-%m-%d"),
            end_date=goal_date,
            target_time="2:00:00",
            weeks=weeks,
            calendar_event_ids={},
            created_at=today.strftime("%Y-%m-%d %H:%M:%S"),
            updated_at=today.strftime("%Y-%m-%d %H:%M:%S"),
        )

    def test_validate_valid_plan(self):
        """测试校验有效计划"""
        plan = self._create_valid_plan()

        result = self.validator.validate(
            plan=plan,
            current_weekly_distance_km=30.0,
            goal_distance_km=21.0975,
        )

        assert isinstance(result, ValidationResult)
        assert result.passed is True
        assert len(result.violations) == 0

    def test_validate_weekly_increase_limit_violation(self):
        """测试周跑量增长限制违规"""
        plan = self._create_plan_with_high_weekly_increase()

        result = self.validator.validate(
            plan=plan,
            current_weekly_distance_km=30.0,
            goal_distance_km=21.0975,
        )

        assert result.passed is False
        assert any(
            v.rule_id == HardValidator.RULE_WEEKLY_INCREASE for v in result.violations
        )

    def test_validate_rest_day_required_violation(self):
        """测试缺少休息日违规"""
        plan = self._create_plan_without_rest_day()

        result = self.validator.validate(
            plan=plan,
            current_weekly_distance_km=30.0,
            goal_distance_km=21.0975,
        )

        assert result.passed is False
        assert any(v.rule_id == HardValidator.RULE_REST_DAY for v in result.violations)

    def test_validate_long_run_ratio_limit_violation(self):
        """测试长距离跑比例限制违规"""
        plan = self._create_plan_with_excessive_long_run()

        result = self.validator.validate(
            plan=plan,
            current_weekly_distance_km=30.0,
            goal_distance_km=21.0975,
        )

        assert result.passed is False
        assert any(
            v.rule_id == HardValidator.RULE_LONG_RUN_RATIO for v in result.violations
        )

    def test_validate_high_intensity_ratio_limit_violation(self):
        """测试高强度训练比例限制违规"""
        plan = self._create_plan_with_excessive_high_intensity()

        result = self.validator.validate(
            plan=plan,
            current_weekly_distance_km=30.0,
            goal_distance_km=21.0975,
        )

        assert result.passed is False
        assert any(
            v.rule_id == HardValidator.RULE_HIGH_INTENSITY_RATIO
            for v in result.violations
        )

    def test_validate_single_run_distance_limit_violation(self):
        """测试单次跑步距离限制违规"""
        plan = self._create_plan_with_excessive_single_run()

        result = self.validator.validate(
            plan=plan,
            current_weekly_distance_km=30.0,
            goal_distance_km=42.195,
        )

        assert result.passed is False
        assert any(
            v.rule_id == HardValidator.RULE_SINGLE_RUN_DISTANCE
            for v in result.violations
        )

    def test_validate_taper_week_reduction_violation(self):
        """测试减量周跑量减少违规"""
        plan = self._create_plan_without_proper_taper()

        result = self.validator.validate(
            plan=plan,
            current_weekly_distance_km=40.0,
            goal_distance_km=42.195,
        )

        assert result.passed is False
        assert any(
            v.rule_id == HardValidator.RULE_TAPER_WEEK for v in result.violations
        )

    def test_validate_multiple_violations(self):
        """测试多个违规"""
        plan = self._create_plan_with_multiple_violations()

        result = self.validator.validate(
            plan=plan,
            current_weekly_distance_km=30.0,
            goal_distance_km=21.0975,
        )

        assert result.passed is False
        assert len(result.violations) >= 2

    def test_validate_empty_plan(self):
        """测试空计划"""
        plan = self._create_training_plan("test_plan", [])

        result = self.validator.validate(
            plan=plan,
            current_weekly_distance_km=30.0,
            goal_distance_km=21.0975,
        )

        assert result.passed is True

    def test_violation_structure(self):
        """测试违规数据结构"""
        plan = self._create_plan_with_high_weekly_increase()

        result = self.validator.validate(
            plan=plan,
            current_weekly_distance_km=30.0,
            goal_distance_km=21.0975,
        )

        assert len(result.violations) > 0
        violation = result.violations[0]
        assert isinstance(violation, Violation)
        assert violation.rule_id is not None
        assert violation.rule_name is not None
        assert violation.message is not None

    def _create_valid_plan(self) -> TrainingPlan:
        """创建有效计划"""
        today = datetime.now()
        week1_start = today + timedelta(days=1)
        week1_end = week1_start + timedelta(days=6)

        daily_plans_week1 = [
            DailyPlan(
                date=(week1_start + timedelta(days=i)).strftime("%Y-%m-%d"),
                workout_type="easy_run" if i % 2 == 0 else "rest",
                distance_km=8.0 if i % 2 == 0 else 0.0,
                duration_min=48 if i % 2 == 0 else 0,
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
            weekly_distance_km=32.0,
            weekly_duration_min=192,
            phase="base",
            focus="建立基础耐力",
        )

        return self._create_training_plan("test_plan_valid", [week1])

    def _create_plan_with_high_weekly_increase(self) -> TrainingPlan:
        """创建周跑量增长过快的计划"""
        today = datetime.now()
        week1_start = today + timedelta(days=1)
        week1_end = week1_start + timedelta(days=6)

        daily_plans_week1 = [
            DailyPlan(
                date=(week1_start + timedelta(days=i)).strftime("%Y-%m-%d"),
                workout_type="easy_run",
                distance_km=10.0,
                duration_min=60,
            )
            for i in range(7)
        ]

        week1 = WeeklySchedule(
            week_number=1,
            start_date=week1_start.strftime("%Y-%m-%d"),
            end_date=week1_end.strftime("%Y-%m-%d"),
            daily_plans=daily_plans_week1,
            weekly_distance_km=70.0,
            weekly_duration_min=420,
            phase="base",
            focus="建立基础耐力",
        )

        return self._create_training_plan("test_plan_high_increase", [week1])

    def _create_plan_without_rest_day(self) -> TrainingPlan:
        """创建缺少休息日的计划"""
        today = datetime.now()
        week1_start = today + timedelta(days=1)
        week1_end = week1_start + timedelta(days=6)

        daily_plans_week1 = [
            DailyPlan(
                date=(week1_start + timedelta(days=i)).strftime("%Y-%m-%d"),
                workout_type="easy_run",
                distance_km=5.0,
                duration_min=30,
            )
            for i in range(7)
        ]

        week1 = WeeklySchedule(
            week_number=1,
            start_date=week1_start.strftime("%Y-%m-%d"),
            end_date=week1_end.strftime("%Y-%m-%d"),
            daily_plans=daily_plans_week1,
            weekly_distance_km=35.0,
            weekly_duration_min=210,
            phase="base",
            focus="建立基础耐力",
        )

        return self._create_training_plan("test_plan_no_rest", [week1])

    def _create_plan_with_excessive_long_run(self) -> TrainingPlan:
        """创建长距离跑比例过高的计划"""
        today = datetime.now()
        week1_start = today + timedelta(days=1)
        week1_end = week1_start + timedelta(days=6)

        daily_plans_week1 = [
            DailyPlan(
                date=(week1_start + timedelta(days=i)).strftime("%Y-%m-%d"),
                workout_type="long" if i == 6 else "easy_run",
                distance_km=25.0 if i == 6 else 5.0,
                duration_min=150 if i == 6 else 30,
            )
            for i in range(7)
        ]

        week1 = WeeklySchedule(
            week_number=1,
            start_date=week1_start.strftime("%Y-%m-%d"),
            end_date=week1_end.strftime("%Y-%m-%d"),
            daily_plans=daily_plans_week1,
            weekly_distance_km=55.0,
            weekly_duration_min=330,
            phase="base",
            focus="建立基础耐力",
        )

        return self._create_training_plan("test_plan_excessive_long_run", [week1])

    def _create_plan_with_excessive_high_intensity(self) -> TrainingPlan:
        """创建高强度训练比例过高的计划"""
        today = datetime.now()
        week1_start = today + timedelta(days=1)
        week1_end = week1_start + timedelta(days=6)

        daily_plans_week1 = [
            DailyPlan(
                date=(week1_start + timedelta(days=i)).strftime("%Y-%m-%d"),
                workout_type="interval" if i % 2 == 0 else "tempo_run",
                distance_km=10.0 if i % 2 == 0 else 8.0,
                duration_min=50 if i % 2 == 0 else 45,
                target_hr_zone=4 if i % 2 == 0 else 3,
            )
            for i in range(7)
        ]

        week1 = WeeklySchedule(
            week_number=1,
            start_date=week1_start.strftime("%Y-%m-%d"),
            end_date=week1_end.strftime("%Y-%m-%d"),
            daily_plans=daily_plans_week1,
            weekly_distance_km=63.0,
            weekly_duration_min=335,
            phase="base",
            focus="建立基础耐力",
        )

        return self._create_training_plan("test_plan_excessive_high_intensity", [week1])

    def _create_plan_with_excessive_single_run(self) -> TrainingPlan:
        """创建单次跑步距离过长的计划"""
        today = datetime.now()
        week1_start = today + timedelta(days=1)
        week1_end = week1_start + timedelta(days=6)

        daily_plans_week1 = [
            DailyPlan(
                date=(week1_start + timedelta(days=i)).strftime("%Y-%m-%d"),
                workout_type="long" if i == 6 else "rest",
                distance_km=60.0 if i == 6 else 0.0,
                duration_min=360 if i == 6 else 0,
            )
            for i in range(7)
        ]

        week1 = WeeklySchedule(
            week_number=1,
            start_date=week1_start.strftime("%Y-%m-%d"),
            end_date=week1_end.strftime("%Y-%m-%d"),
            daily_plans=daily_plans_week1,
            weekly_distance_km=60.0,
            weekly_duration_min=360,
            phase="base",
            focus="建立基础耐力",
        )

        return self._create_training_plan(
            "test_plan_excessive_single_run", [week1], goal_distance_km=42.195
        )

    def _create_plan_without_proper_taper(self) -> TrainingPlan:
        """创建减量周跑量减少不足的计划"""
        today = datetime.now()
        week1_start = today + timedelta(days=1)
        week1_end = week1_start + timedelta(days=6)
        week2_start = week1_end + timedelta(days=1)
        week2_end = week2_start + timedelta(days=6)

        daily_plans_week1 = [
            DailyPlan(
                date=(week1_start + timedelta(days=i)).strftime("%Y-%m-%d"),
                workout_type="easy_run",
                distance_km=10.0,
                duration_min=60,
            )
            for i in range(7)
        ]

        week1 = WeeklySchedule(
            week_number=1,
            start_date=week1_start.strftime("%Y-%m-%d"),
            end_date=week1_end.strftime("%Y-%m-%d"),
            daily_plans=daily_plans_week1,
            weekly_distance_km=70.0,
            weekly_duration_min=420,
            phase="peak",
            focus="峰值训练",
        )

        daily_plans_week2 = [
            DailyPlan(
                date=(week2_start + timedelta(days=i)).strftime("%Y-%m-%d"),
                workout_type="easy_run",
                distance_km=10.0,
                duration_min=60,
            )
            for i in range(7)
        ]

        week2 = WeeklySchedule(
            week_number=2,
            start_date=week2_start.strftime("%Y-%m-%d"),
            end_date=week2_end.strftime("%Y-%m-%d"),
            daily_plans=daily_plans_week2,
            weekly_distance_km=70.0,
            weekly_duration_min=420,
            phase="taper",
            focus="减量调整",
        )

        return self._create_training_plan(
            "test_plan_no_taper", [week1, week2], goal_distance_km=42.195
        )

    def _create_plan_with_multiple_violations(self) -> TrainingPlan:
        """创建包含多个违规的计划"""
        today = datetime.now()
        week1_start = today + timedelta(days=1)
        week1_end = week1_start + timedelta(days=6)

        daily_plans_week1 = [
            DailyPlan(
                date=(week1_start + timedelta(days=i)).strftime("%Y-%m-%d"),
                workout_type="interval",
                distance_km=15.0,
                duration_min=75,
                target_hr_zone=4,
            )
            for i in range(7)
        ]

        week1 = WeeklySchedule(
            week_number=1,
            start_date=week1_start.strftime("%Y-%m-%d"),
            end_date=week1_end.strftime("%Y-%m-%d"),
            daily_plans=daily_plans_week1,
            weekly_distance_km=105.0,
            weekly_duration_min=525,
            phase="base",
            focus="建立基础耐力",
        )

        return self._create_training_plan("test_plan_multiple_violations", [week1])
