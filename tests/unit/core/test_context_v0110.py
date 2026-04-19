# v0.11.0 依赖注入单元测试
# 覆盖 AppContext v0.11.0 扩展属性: plan_adjustment_validator / prompt_template_engine

from unittest.mock import MagicMock

from src.core.plan.plan_adjustment_validator import PlanAdjustmentValidator
from src.core.plan.prompt_template_engine import PromptTemplateEngine
from tests.conftest import create_mock_context


class TestAppContextPlanAdjustmentValidator:
    """AppContext plan_adjustment_validator 属性测试"""

    def test_plan_adjustment_validator_lazy_init(self):
        """测试 plan_adjustment_validator 延迟初始化"""
        context = create_mock_context()

        validator = context.plan_adjustment_validator
        assert validator is not None
        assert isinstance(validator, PlanAdjustmentValidator)

    def test_plan_adjustment_validator_cached(self):
        """测试 plan_adjustment_validator 缓存机制"""
        context = create_mock_context()

        validator1 = context.plan_adjustment_validator
        validator2 = context.plan_adjustment_validator
        assert validator1 is validator2

    def test_plan_adjustment_validator_stored_in_extensions(self):
        """测试 plan_adjustment_validator 存储在扩展字典中"""
        context = create_mock_context()

        validator = context.plan_adjustment_validator
        assert context.get_extension("plan_adjustment_validator") is validator

    def test_plan_adjustment_validator_custom_injection(self):
        """测试 plan_adjustment_validator 自定义注入"""
        context = create_mock_context()
        custom_validator = MagicMock(spec=PlanAdjustmentValidator)

        context.set_extension("plan_adjustment_validator", custom_validator)
        assert context.plan_adjustment_validator is custom_validator


class TestAppContextPromptTemplateEngine:
    """AppContext prompt_template_engine 属性测试"""

    def test_prompt_template_engine_lazy_init(self):
        """测试 prompt_template_engine 延迟初始化"""
        context = create_mock_context()

        engine = context.prompt_template_engine
        assert engine is not None
        assert isinstance(engine, PromptTemplateEngine)

    def test_prompt_template_engine_cached(self):
        """测试 prompt_template_engine 缓存机制"""
        context = create_mock_context()

        engine1 = context.prompt_template_engine
        engine2 = context.prompt_template_engine
        assert engine1 is engine2

    def test_prompt_template_engine_stored_in_extensions(self):
        """测试 prompt_template_engine 存储在扩展字典中"""
        context = create_mock_context()

        engine = context.prompt_template_engine
        assert context.get_extension("prompt_template_engine") is engine

    def test_prompt_template_engine_custom_injection(self):
        """测试 prompt_template_engine 自定义注入"""
        context = create_mock_context()
        custom_engine = MagicMock(spec=PromptTemplateEngine)

        context.set_extension("prompt_template_engine", custom_engine)
        assert context.prompt_template_engine is custom_engine


class TestAppContextV0110Integration:
    """v0.11.0 依赖注入集成测试"""

    def test_all_v0110_extensions_independent(self):
        """测试所有v0.11.0扩展组件互相独立"""
        context = create_mock_context()

        validator = context.plan_adjustment_validator
        engine = context.prompt_template_engine

        assert validator is not engine
        assert isinstance(validator, PlanAdjustmentValidator)
        assert isinstance(engine, PromptTemplateEngine)

    def test_v010_and_v0110_extensions_coexist(self):
        """测试v0.10.0和v0.11.0扩展组件共存"""
        context = create_mock_context()

        from src.core.plan.plan_execution_repository import PlanExecutionRepository
        from src.core.plan.training_response_analyzer import TrainingResponseAnalyzer

        repo = context.plan_execution_repo
        analyzer = context.training_response_analyzer
        validator = context.plan_adjustment_validator
        engine = context.prompt_template_engine

        assert isinstance(repo, PlanExecutionRepository)
        assert isinstance(analyzer, TrainingResponseAnalyzer)
        assert isinstance(validator, PlanAdjustmentValidator)
        assert isinstance(engine, PromptTemplateEngine)

    def test_reset_extension_allows_reinit(self):
        """测试重置扩展后可重新初始化"""
        context = create_mock_context()

        validator1 = context.plan_adjustment_validator
        context.set_extension("plan_adjustment_validator", None)
        validator2 = context.plan_adjustment_validator

        assert validator1 is not validator2
        assert isinstance(validator2, PlanAdjustmentValidator)
