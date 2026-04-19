# v0.12.0 规划引擎和建议引擎单元测试
# 覆盖 LongTermPlanGenerator / SmartAdviceEngine


from src.core.models import LongTermPlan, SmartTrainingAdvice
from src.core.plan.long_term_plan_generator import LongTermPlanGenerator
from src.core.plan.smart_advice_engine import SmartAdviceEngine


class TestLongTermPlanGenerator:
    """LongTermPlanGenerator 测试"""

    def setup_method(self) -> None:
        self.generator = LongTermPlanGenerator()

    def test_generate_plan_basic(self) -> None:
        plan = self.generator.generate_plan(
            plan_name="半马备赛",
            current_vdot=42.0,
            target_vdot=48.0,
            total_weeks=16,
        )
        assert isinstance(plan, LongTermPlan)
        assert plan.plan_name == "半马备赛"
        assert plan.total_weeks == 16
        assert len(plan.cycles) == 4

    def test_generate_plan_with_target_race(self) -> None:
        plan = self.generator.generate_plan(
            plan_name="全马备赛",
            current_vdot=45.0,
            target_vdot=50.0,
            target_race="北京马拉松",
            target_date="2026-10-15",
            total_weeks=20,
        )
        assert plan.target_race == "北京马拉松"
        assert plan.target_date == "2026-10-15"
        assert plan.has_target_race is True

    def test_generate_plan_cycle_types(self) -> None:
        plan = self.generator.generate_plan(
            plan_name="测试计划",
            current_vdot=40.0,
            total_weeks=12,
        )
        cycle_types = [c.cycle_type for c in plan.cycles]
        assert "base" in cycle_types
        assert "build" in cycle_types
        assert "peak" in cycle_types
        assert "taper" in cycle_types

    def test_generate_plan_volume_range(self) -> None:
        plan = self.generator.generate_plan(
            plan_name="测试计划",
            current_vdot=42.0,
            fitness_level="intermediate",
            total_weeks=16,
        )
        low, high = plan.weekly_volume_range_km
        assert low > 0
        assert high > low

    def test_generate_plan_milestones(self) -> None:
        plan = self.generator.generate_plan(
            plan_name="测试计划",
            current_vdot=42.0,
            target_vdot=48.0,
            total_weeks=16,
        )
        assert len(plan.key_milestones) > 0

    def test_generate_plan_beginner(self) -> None:
        plan = self.generator.generate_plan(
            plan_name="初学者计划",
            current_vdot=30.0,
            fitness_level="beginner",
            total_weeks=12,
        )
        low, high = plan.weekly_volume_range_km
        assert low < 35

    def test_generate_plan_advanced(self) -> None:
        plan = self.generator.generate_plan(
            plan_name="进阶计划",
            current_vdot=55.0,
            fitness_level="advanced",
            total_weeks=16,
        )
        low, high = plan.weekly_volume_range_km
        assert low >= 40

    def test_generate_plan_cycle_goals_with_target(self) -> None:
        plan = self.generator.generate_plan(
            plan_name="测试计划",
            current_vdot=42.0,
            target_vdot=48.0,
            total_weeks=16,
        )
        base_cycle = next(c for c in plan.cycles if c.cycle_type == "base")
        assert "VDOT" in base_cycle.goal

    def test_generate_plan_cycle_goals_without_target(self) -> None:
        plan = self.generator.generate_plan(
            plan_name="测试计划",
            current_vdot=42.0,
            target_vdot=None,
            total_weeks=16,
        )
        base_cycle = next(c for c in plan.cycles if c.cycle_type == "base")
        assert "有氧基础" in base_cycle.goal

    def test_generate_plan_key_workouts(self) -> None:
        plan = self.generator.generate_plan(
            plan_name="测试计划",
            current_vdot=42.0,
            total_weeks=16,
        )
        for cycle in plan.cycles:
            assert len(cycle.key_workouts) > 0

    def test_generate_plan_to_dict(self) -> None:
        plan = self.generator.generate_plan(
            plan_name="测试计划",
            current_vdot=42.0,
            target_vdot=48.0,
            total_weeks=16,
        )
        d = plan.to_dict()
        assert d["plan_name"] == "测试计划"
        assert len(d["cycles"]) == 4

    def test_minimum_weeks(self) -> None:
        plan = self.generator.generate_plan(
            plan_name="短计划",
            current_vdot=42.0,
            total_weeks=4,
        )
        assert plan.total_weeks == 4
        assert len(plan.cycles) >= 2


class TestSmartAdviceEngine:
    """SmartAdviceEngine 测试"""

    def setup_method(self) -> None:
        self.engine = SmartAdviceEngine()

    def test_generate_advice_basic(self) -> None:
        advices = self.engine.generate_advice(
            current_vdot=42.0,
            weekly_volume_km=35.0,
            training_consistency=0.8,
        )
        assert isinstance(advices, list)
        assert len(advices) > 0
        assert all(isinstance(a, SmartTrainingAdvice) for a in advices)

    def test_generate_advice_low_volume(self) -> None:
        advices = self.engine.generate_advice(
            weekly_volume_km=15.0,
        )
        training_advices = [a for a in advices if a.advice_type == "training"]
        assert any("增加周跑量" in a.content for a in training_advices)

    def test_generate_advice_low_consistency(self) -> None:
        advices = self.engine.generate_advice(
            weekly_volume_km=30.0,
            training_consistency=0.3,
        )
        training_advices = [a for a in advices if a.advice_type == "training"]
        assert any("训练规律性" in a.content for a in training_advices)

    def test_generate_advice_high_tsb(self) -> None:
        advices = self.engine.generate_advice(
            tsb=-25.0,
        )
        recovery_advices = [a for a in advices if a.advice_type == "recovery"]
        assert any("减量" in a.content for a in recovery_advices)

    def test_generate_advice_moderate_tsb(self) -> None:
        advices = self.engine.generate_advice(
            tsb=-12.0,
        )
        recovery_advices = [a for a in advices if a.advice_type == "recovery"]
        assert any("恢复" in a.content for a in recovery_advices)

    def test_generate_advice_high_effort(self) -> None:
        advices = self.engine.generate_advice(
            recent_effort_scores=[8, 9, 8],
        )
        recovery_advices = [a for a in advices if a.advice_type == "recovery"]
        assert any("体感" in a.content for a in recovery_advices)

    def test_generate_advice_high_atl_ctl_ratio(self) -> None:
        advices = self.engine.generate_advice(
            ctl=50.0,
            atl=80.0,
        )
        recovery_advices = [a for a in advices if a.advice_type == "recovery"]
        assert any("急性负荷" in a.content for a in recovery_advices)

    def test_generate_advice_nutrition_high_volume(self) -> None:
        advices = self.engine.generate_advice(
            weekly_volume_km=60.0,
        )
        nutrition_advices = [a for a in advices if a.advice_type == "nutrition"]
        assert len(nutrition_advices) > 0

    def test_generate_advice_injury_risk_high(self) -> None:
        advices = self.engine.generate_advice(
            injury_risk="high",
        )
        injury_advices = [a for a in advices if a.advice_type == "injury_prevention"]
        assert any("高风险" in a.context for a in injury_advices)

    def test_generate_advice_injury_risk_medium(self) -> None:
        advices = self.engine.generate_advice(
            injury_risk="medium",
        )
        injury_advices = [a for a in advices if a.advice_type == "injury_prevention"]
        assert any("中等风险" in a.context for a in injury_advices)

    def test_generate_advice_sorted_by_priority(self) -> None:
        advices = self.engine.generate_advice(
            weekly_volume_km=15.0,
            injury_risk="high",
            training_consistency=0.3,
        )
        priorities = [a.priority for a in advices]
        priority_order = {"high": 0, "medium": 1, "low": 2}
        for i in range(len(priorities) - 1):
            assert priority_order[priorities[i]] <= priority_order[priorities[i + 1]]

    def test_generate_advice_5k_goal(self) -> None:
        advices = self.engine.generate_advice(
            goal_type="5k",
            weekly_volume_km=30.0,
        )
        training_advices = [a for a in advices if a.advice_type == "training"]
        assert any("间歇" in a.content for a in training_advices)

    def test_generate_advice_marathon_goal(self) -> None:
        advices = self.engine.generate_advice(
            goal_type="marathon",
            weekly_volume_km=40.0,
        )
        training_advices = [a for a in advices if a.advice_type == "training"]
        assert any(
            "长距离" in a.content or "耐力" in a.content for a in training_advices
        )

    def test_generate_advice_low_vdot(self) -> None:
        advices = self.engine.generate_advice(
            current_vdot=30.0,
            weekly_volume_km=25.0,
        )
        training_advices = [a for a in advices if a.advice_type == "training"]
        assert any("轻松跑" in a.content for a in training_advices)

    def test_generate_advice_high_volume_injury(self) -> None:
        advices = self.engine.generate_advice(
            weekly_volume_km=70.0,
        )
        injury_advices = [a for a in advices if a.advice_type == "injury_prevention"]
        assert any("跑姿" in a.content or "高跑量" in a.context for a in injury_advices)

    def test_advice_to_dict(self) -> None:
        advices = self.engine.generate_advice(
            weekly_volume_km=30.0,
        )
        for advice in advices:
            d = advice.to_dict()
            assert "advice_type" in d
            assert "content" in d
            assert "priority" in d
