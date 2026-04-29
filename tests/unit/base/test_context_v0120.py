# v0.12.0 依赖注入层单元测试
# 验证AppContext中v0.12.0组件的懒加载和缓存

from unittest.mock import MagicMock, patch

from tests.conftest import create_mock_context


class TestAppContextV0120:
    """AppContext v0.12.0扩展测试"""

    def test_goal_prediction_engine_property(self) -> None:
        context = create_mock_context()
        with patch(
            "src.core.plan.goal_prediction_engine.GoalPredictionEngine"
        ) as mock_cls:
            mock_instance = MagicMock()
            mock_cls.return_value = mock_instance
            engine = context.goal_prediction_engine
            assert engine is mock_instance

    def test_goal_prediction_engine_cached(self) -> None:
        context = create_mock_context()
        with patch(
            "src.core.plan.goal_prediction_engine.GoalPredictionEngine"
        ) as mock_cls:
            mock_instance = MagicMock()
            mock_cls.return_value = mock_instance
            engine1 = context.goal_prediction_engine
            engine2 = context.goal_prediction_engine
            assert engine1 is engine2
            assert mock_cls.call_count == 1

    def test_long_term_plan_generator_property(self) -> None:
        context = create_mock_context()
        with patch(
            "src.core.plan.long_term_plan_generator.LongTermPlanGenerator"
        ) as mock_cls:
            mock_instance = MagicMock()
            mock_cls.return_value = mock_instance
            generator = context.long_term_plan_generator
            assert generator is mock_instance

    def test_long_term_plan_generator_cached(self) -> None:
        context = create_mock_context()
        with patch(
            "src.core.plan.long_term_plan_generator.LongTermPlanGenerator"
        ) as mock_cls:
            mock_instance = MagicMock()
            mock_cls.return_value = mock_instance
            gen1 = context.long_term_plan_generator
            gen2 = context.long_term_plan_generator
            assert gen1 is gen2
            assert mock_cls.call_count == 1

    def test_smart_advice_engine_property(self) -> None:
        context = create_mock_context()
        with patch("src.core.plan.smart_advice_engine.SmartAdviceEngine") as mock_cls:
            mock_instance = MagicMock()
            mock_cls.return_value = mock_instance
            engine = context.smart_advice_engine
            assert engine is mock_instance

    def test_smart_advice_engine_cached(self) -> None:
        context = create_mock_context()
        with patch("src.core.plan.smart_advice_engine.SmartAdviceEngine") as mock_cls:
            mock_instance = MagicMock()
            mock_cls.return_value = mock_instance
            engine1 = context.smart_advice_engine
            engine2 = context.smart_advice_engine
            assert engine1 is engine2
            assert mock_cls.call_count == 1

    def test_all_v0120_properties_independent(self) -> None:
        context = create_mock_context()
        with (
            patch(
                "src.core.plan.goal_prediction_engine.GoalPredictionEngine"
            ) as mock_goal,
            patch(
                "src.core.plan.long_term_plan_generator.LongTermPlanGenerator"
            ) as mock_plan,
            patch("src.core.plan.smart_advice_engine.SmartAdviceEngine") as mock_advice,
        ):
            mock_goal.return_value = MagicMock(name="goal_engine")
            mock_plan.return_value = MagicMock(name="plan_generator")
            mock_advice.return_value = MagicMock(name="advice_engine")

            goal = context.goal_prediction_engine
            plan = context.long_term_plan_generator
            advice = context.smart_advice_engine

            assert goal is not plan
            assert plan is not advice
            assert goal is not advice
