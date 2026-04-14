"""
PlanAnalyzer 单元测试
"""

from datetime import datetime, timedelta

import pytest

from src.core.exceptions import ValidationError
from src.core.models import (
    AnalysisReport,
    DailyPlan,
    DimensionResult,
    FitnessLevel,
    TrainingLoad,
    TrainingPlan,
    UserContext,
    UserPreferences,
    WeeklySchedule,
)
from src.core.plan.plan_analyzer import PlanAnalyzer
from src.core.profile import RunnerProfile


class TestPlanAnalyzer:
    """PlanAnalyzer 测试类"""

    def setup_method(self):
        """每个测试方法前的设置"""
        self.analyzer = PlanAnalyzer()

        self.user_context = UserContext(
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

    def _create_training_plan(
        self,
        plan_id: str,
        weeks: list[WeeklySchedule],
        goal_distance_km: float = 21.0975,
        goal_date: str = None,
        target_time: str = "2:00:00",
    ) -> TrainingPlan:
        """创建训练计划辅助方法"""
        today = datetime.now()
        if goal_date is None:
            goal_date = (today + timedelta(days=14)).strftime("%Y-%m-%d")

        return TrainingPlan(
            plan_id=plan_id,
            user_id="test_user",
            plan_type="race_preparation",
            fitness_level=FitnessLevel.INTERMEDIATE,
            goal_distance_km=goal_distance_km,
            goal_date=goal_date,
            start_date=weeks[0].start_date if weeks else today.strftime("%Y-%m-%d"),
            end_date=goal_date,
            weeks=weeks,
            target_time=target_time,
            calendar_event_ids={},
        )

    def test_analyze_valid_plan(self):
        """测试分析有效计划"""
        plan = self._create_valid_plan()

        report = self.analyzer.analyze(
            plan=plan,
            user_context=self.user_context,
        )

        assert isinstance(report, AnalysisReport)
        assert 0 <= report.overall_score <= 100
        assert len(report.dimensions) == 4
        assert len(report.dimensions[0].details) > 0
        assert report.disclaimer is not None

    def test_analyze_fitness_match_dimension(self):
        """测试体能匹配维度分析"""
        plan = self._create_valid_plan()

        report = self.analyzer.analyze(
            plan=plan,
            user_context=self.user_context,
        )

        fitness_dim = next(
            (
                d
                for d in report.dimensions
                if d.dimension == PlanAnalyzer.DIMENSION_FITNESS
            ),
            None,
        )

        assert fitness_dim is not None
        assert 0 <= fitness_dim.score <= 100
        assert isinstance(fitness_dim.details, dict)

    def test_analyze_load_progression_dimension(self):
        """测试负荷递进维度分析"""
        plan = self._create_valid_plan()

        report = self.analyzer.analyze(
            plan=plan,
            user_context=self.user_context,
        )

        load_dim = next(
            (
                d
                for d in report.dimensions
                if d.dimension == PlanAnalyzer.DIMENSION_LOAD
            ),
            None,
        )

        assert load_dim is not None
        assert 0 <= load_dim.score <= 100
        assert isinstance(load_dim.details, dict)

    def test_analyze_injury_risk_dimension(self):
        """测试伤病风险维度分析"""
        plan = self._create_valid_plan()

        report = self.analyzer.analyze(
            plan=plan,
            user_context=self.user_context,
        )

        injury_dim = next(
            (
                d
                for d in report.dimensions
                if d.dimension == PlanAnalyzer.DIMENSION_INJURY
            ),
            None,
        )

        assert injury_dim is not None
        assert 0 <= injury_dim.score <= 100
        assert isinstance(injury_dim.details, dict)

    def test_analyze_goal_achievability_dimension(self):
        """测试目标可达性维度分析"""
        plan = self._create_valid_plan()

        report = self.analyzer.analyze(
            plan=plan,
            user_context=self.user_context,
        )

        goal_dim = next(
            (
                d
                for d in report.dimensions
                if d.dimension == PlanAnalyzer.DIMENSION_GOAL
            ),
            None,
        )

        assert goal_dim is not None
        assert 0 <= goal_dim.score <= 100
        assert isinstance(goal_dim.details, dict)

    def test_analyze_plan_with_high_injury_risk(self):
        """测试分析高伤病风险计划"""
        plan = self._create_high_risk_plan()

        report = self.analyzer.analyze(
            plan=plan,
            user_context=self.user_context,
        )

        assert len(report.warnings) > 0
        assert any(
            "跑量" in warning or "训练" in warning for warning in report.warnings
        )

    def test_analyze_plan_with_unrealistic_goal(self):
        """测试分析目标不切实际的计划"""
        plan = self._create_unrealistic_goal_plan()

        report = self.analyzer.analyze(
            plan=plan,
            user_context=self.user_context,
        )

        goal_dim = next(
            (
                d
                for d in report.dimensions
                if d.dimension == PlanAnalyzer.DIMENSION_GOAL
            ),
            None,
        )

        assert goal_dim is not None
        assert goal_dim.score < 60

    def test_analyze_empty_plan(self):
        """测试分析空计划"""
        plan = self._create_training_plan("test_plan", [])

        with pytest.raises(ValidationError, match="训练计划不能为空"):
            self.analyzer.analyze(
                plan=plan,
                user_context=self.user_context,
            )

    def test_analyze_generates_recommendations(self):
        """测试生成改进建议"""
        plan = self._create_valid_plan()

        report = self.analyzer.analyze(
            plan=plan,
            user_context=self.user_context,
        )

        assert isinstance(report.recommendations, list)

    def test_analyze_generates_warnings(self):
        """测试生成风险警告"""
        plan = self._create_high_risk_plan()

        report = self.analyzer.analyze(
            plan=plan,
            user_context=self.user_context,
        )

        assert isinstance(report.warnings, list)
        assert len(report.warnings) > 0

    def test_analyze_includes_disclaimer(self):
        """测试包含医疗免责声明"""
        plan = self._create_valid_plan()

        report = self.analyzer.analyze(
            plan=plan,
            user_context=self.user_context,
        )

        assert report.disclaimer is not None
        assert (
            "免责声明" in report.disclaimer or "disclaimer" in report.disclaimer.lower()
        )

    def test_dimension_result_structure(self):
        """测试维度结果数据结构"""
        plan = self._create_valid_plan()

        report = self.analyzer.analyze(
            plan=plan,
            user_context=self.user_context,
        )

        for dimension in report.dimensions:
            assert isinstance(dimension, DimensionResult)
            assert dimension.dimension is not None
            assert 0 <= dimension.score <= 100
            assert isinstance(dimension.recommendations, list)

    def test_analyze_with_different_user_profiles(self):
        """测试不同用户画像的分析结果"""
        plan = self._create_valid_plan()

        beginner_context = UserContext(
            profile=RunnerProfile(
                user_id="beginner_user",
                profile_date=datetime.now(),
                total_activities=20,
                total_distance_km=100.0,
                total_duration_hours=12.0,
                avg_vdot=35.0,
                max_vdot=38.0,
                weekly_avg_distance_km=10.0,
                weekly_avg_duration_hours=1.5,
                avg_pace_min_per_km=7.5,
                resting_heart_rate=70.0,
                max_heart_rate=195.0,
            ),
            recent_activities=[],
            training_load=TrainingLoad(
                atl=5.0,
                ctl=6.0,
                tsb=-1.0,
                recent_4_weeks_distance_km=40.0,
                last_week_distance_km=10.0,
                avg_weekly_distance_km=10.0,
                longest_run_km=5.0,
                training_frequency=2,
            ),
            preferences=UserPreferences(
                preferred_training_days=["tuesday", "thursday", "saturday"],
                preferred_training_time="evening",
                enable_calendar_sync=True,
            ),
            historical_best_pace_min_per_km=7.0,
        )

        report = self.analyzer.analyze(
            plan=plan,
            user_context=beginner_context,
        )

        assert isinstance(report, AnalysisReport)
        assert report.overall_score is not None

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

    def _create_high_risk_plan(self) -> TrainingPlan:
        """创建高伤病风险计划"""
        today = datetime.now()
        week1_start = today + timedelta(days=1)
        week1_end = week1_start + timedelta(days=6)

        daily_plans_week1 = [
            DailyPlan(
                date=(week1_start + timedelta(days=i)).strftime("%Y-%m-%d"),
                workout_type="interval",
                distance_km=12.0,
                duration_min=60,
                target_hr_zone=4,
            )
            for i in range(7)
        ]

        week1 = WeeklySchedule(
            week_number=1,
            start_date=week1_start.strftime("%Y-%m-%d"),
            end_date=week1_end.strftime("%Y-%m-%d"),
            daily_plans=daily_plans_week1,
            weekly_distance_km=84.0,
            weekly_duration_min=420,
            phase="base",
            focus="高强度训练",
        )

        return self._create_training_plan("test_plan_high_risk", [week1])

    def _create_unrealistic_goal_plan(self) -> TrainingPlan:
        """创建目标不切实际的计划"""
        today = datetime.now()
        week1_start = today + timedelta(days=1)
        week1_end = week1_start + timedelta(days=6)

        daily_plans_week1 = [
            DailyPlan(
                date=(week1_start + timedelta(days=i)).strftime("%Y-%m-%d"),
                workout_type="easy_run" if i % 2 == 0 else "rest",
                distance_km=5.0 if i % 2 == 0 else 0.0,
                duration_min=30 if i % 2 == 0 else 0,
            )
            for i in range(7)
        ]

        week1 = WeeklySchedule(
            week_number=1,
            start_date=week1_start.strftime("%Y-%m-%d"),
            end_date=week1_end.strftime("%Y-%m-%d"),
            daily_plans=daily_plans_week1,
            weekly_distance_km=20.0,
            weekly_duration_min=120,
            phase="base",
            focus="建立基础耐力",
        )

        return self._create_training_plan(
            "test_plan_unrealistic",
            [week1],
            goal_distance_km=42.195,
            target_time="3:00:00",
        )
