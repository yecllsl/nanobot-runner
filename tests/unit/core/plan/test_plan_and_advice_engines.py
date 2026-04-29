# v0.12.0 规划引擎和建议引擎单元测试
# 覆盖 LongTermPlanGenerator / SmartAdviceEngine


from unittest.mock import MagicMock, patch

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

    def test_generate_plan_skip_training_plans(self) -> None:
        """测试 auto_create_training_plans=False 时跳过创建TrainingPlan"""
        plan = self.generator.generate_plan(
            plan_name="测试计划",
            current_vdot=42.0,
            total_weeks=16,
            auto_create_training_plans=False,
        )
        assert plan.training_plan_ids == []

    def test_generate_plan_training_plan_ids_default_empty(self) -> None:
        """测试默认情况下 training_plan_ids 为空列表（无context时）"""
        plan = self.generator.generate_plan(
            plan_name="测试计划",
            current_vdot=42.0,
            total_weeks=16,
            auto_create_training_plans=False,
        )
        assert isinstance(plan.training_plan_ids, list)
        assert len(plan.training_plan_ids) == 0

    @patch("src.core.base.context.get_context")
    @patch("src.core.training_plan.TrainingPlanEngine")
    def test_create_training_plans_for_cycles_success(
        self, mock_engine_cls, mock_get_context
    ) -> None:
        """测试自动创建TrainingPlan成功"""
        mock_context = MagicMock()
        mock_context.config.user_id = "test_user"
        mock_plan_manager = MagicMock()
        mock_plan_manager.create_plan.return_value = "plan_test_001"
        mock_context.plan_manager = mock_plan_manager
        mock_get_context.return_value = mock_context

        mock_engine = MagicMock()
        mock_plan = MagicMock()
        mock_plan.metadata = None
        mock_engine.generate_plan.return_value = mock_plan
        mock_engine_cls.return_value = mock_engine

        plan = self.generator.generate_plan(
            plan_name="测试计划",
            current_vdot=42.0,
            total_weeks=16,
            auto_create_training_plans=True,
        )

        assert len(plan.training_plan_ids) == 4
        assert all(pid == "plan_test_001" for pid in plan.training_plan_ids)
        assert mock_plan_manager.create_plan.call_count == 4

    @patch("src.core.base.context.get_context")
    @patch("src.core.training_plan.TrainingPlanEngine")
    def test_create_training_plans_partial_failure(
        self, mock_engine_cls, mock_get_context
    ) -> None:
        """测试部分周期创建TrainingPlan失败时降级处理"""
        mock_context = MagicMock()
        mock_context.config.user_id = "test_user"
        mock_plan_manager = MagicMock()
        mock_plan_manager.create_plan.return_value = "plan_test_001"
        mock_context.plan_manager = mock_plan_manager
        mock_get_context.return_value = mock_context

        mock_engine = MagicMock()
        mock_plan = MagicMock()
        mock_plan.metadata = None
        call_count = 0

        def side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise ValueError("模拟生成失败")
            return mock_plan

        mock_engine.generate_plan.side_effect = side_effect
        mock_engine_cls.return_value = mock_engine

        plan = self.generator.generate_plan(
            plan_name="测试计划",
            current_vdot=42.0,
            total_weeks=16,
            auto_create_training_plans=True,
        )

        assert len(plan.training_plan_ids) == 3

    def test_long_term_plan_training_plan_ids_to_dict(self) -> None:
        """测试 LongTermPlan.to_dict 包含 training_plan_ids"""
        plan = self.generator.generate_plan(
            plan_name="测试计划",
            current_vdot=42.0,
            total_weeks=16,
            auto_create_training_plans=False,
        )
        d = plan.to_dict()
        assert "training_plan_ids" in d
        assert d["training_plan_ids"] == []

    def test_long_term_plan_with_custom_training_plan_ids(self) -> None:
        """测试 LongTermPlan 自定义 training_plan_ids"""
        plan = self.generator.generate_plan(
            plan_name="测试计划",
            current_vdot=42.0,
            total_weeks=16,
            auto_create_training_plans=False,
        )
        plan.training_plan_ids = ["plan_001", "plan_002"]
        d = plan.to_dict()
        assert d["training_plan_ids"] == ["plan_001", "plan_002"]

    @patch("src.core.base.context.get_context")
    @patch("src.core.training_plan.TrainingPlanEngine")
    def test_create_training_plans_metadata_set(
        self, mock_engine_cls, mock_get_context
    ) -> None:
        """测试创建的TrainingPlan metadata包含关联信息"""
        mock_context = MagicMock()
        mock_context.config.user_id = "test_user"
        mock_plan_manager = MagicMock()
        mock_plan_manager.create_plan.return_value = "plan_test_001"
        mock_context.plan_manager = mock_plan_manager
        mock_get_context.return_value = mock_context

        mock_engine = MagicMock()
        mock_plan = MagicMock()
        mock_plan.metadata = None
        mock_engine.generate_plan.return_value = mock_plan
        mock_engine_cls.return_value = mock_engine

        self.generator.generate_plan(
            plan_name="春季备赛",
            current_vdot=42.0,
            total_weeks=16,
            auto_create_training_plans=True,
        )

        assert mock_plan.metadata is not None
        assert mock_plan.metadata["long_term_plan_name"] == "春季备赛"
        assert "cycle_type" in mock_plan.metadata
        assert "cycle_index" in mock_plan.metadata


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
