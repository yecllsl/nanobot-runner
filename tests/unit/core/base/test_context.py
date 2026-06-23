# AppContext 单元测试
# 覆盖 context.py 的 lazy property 缓存、get/set_extension、工厂方法、全局上下文管理

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from src.core.base.context import (
    AppContext,
    AppContextFactory,
    get_context,
    reset_context,
    set_context,
)


def _make_mock_context() -> AppContext:
    """创建全 Mock 依赖的 AppContext"""
    config = MagicMock()
    config.data_dir = Path(tempfile.mkdtemp())
    config.base_dir = Path(tempfile.mkdtemp())
    config.index_file = config.data_dir / "index.json"
    config.cron_store = config.data_dir / "cron"

    return AppContext(
        config=config,
        storage=MagicMock(),
        indexer=MagicMock(),
        parser=MagicMock(),
        importer=MagicMock(),
        analytics=MagicMock(),
        profile_engine=MagicMock(),
        profile_storage=MagicMock(),
        session_repo=MagicMock(),
        report_service=MagicMock(),
        plan_manager=MagicMock(),
    )


class TestAppContextExtensions:
    """覆盖 get_extension/set_extension 方法"""

    def test_get_extension_not_found(self):
        ctx = _make_mock_context()
        assert ctx.get_extension("nonexistent") is None

    def test_set_and_get_extension(self):
        ctx = _make_mock_context()
        mock_obj = MagicMock()
        ctx.set_extension("test_key", mock_obj)
        assert ctx.get_extension("test_key") is mock_obj

    def test_set_extension_overwrite(self):
        ctx = _make_mock_context()
        obj1 = MagicMock()
        obj2 = MagicMock()
        ctx.set_extension("key", obj1)
        ctx.set_extension("key", obj2)
        assert ctx.get_extension("key") is obj2


class TestAppContextLazyPropertyCaching:
    """覆盖 lazy property 缓存逻辑：已设置 extension 时直接返回"""

    def test_plan_adjustment_validator_cached(self):
        """覆盖 lines 131-137: 已缓存时直接返回"""
        ctx = _make_mock_context()
        mock_validator = MagicMock()
        ctx.set_extension("plan_adjustment_validator", mock_validator)
        assert ctx.plan_adjustment_validator is mock_validator

    def test_prompt_template_engine_cached(self):
        """覆盖 lines 142-148: 已缓存时直接返回"""
        ctx = _make_mock_context()
        mock_engine = MagicMock()
        ctx.set_extension("prompt_template_engine", mock_engine)
        assert ctx.prompt_template_engine is mock_engine

    def test_goal_prediction_engine_cached(self):
        """覆盖 lines 167-173: 已缓存时直接返回"""
        ctx = _make_mock_context()
        mock_engine = MagicMock()
        ctx.set_extension("goal_prediction_engine", mock_engine)
        assert ctx.goal_prediction_engine is mock_engine

    def test_long_term_plan_generator_cached(self):
        """覆盖 lines 178-184: 已缓存时直接返回"""
        ctx = _make_mock_context()
        mock_gen = MagicMock()
        ctx.set_extension("long_term_plan_generator", mock_gen)
        assert ctx.long_term_plan_generator is mock_gen

    def test_smart_advice_engine_cached(self):
        """覆盖 lines 187-195: 已缓存时直接返回"""
        ctx = _make_mock_context()
        mock_engine = MagicMock()
        ctx.set_extension("smart_advice_engine", mock_engine)
        assert ctx.smart_advice_engine is mock_engine

    def test_ask_user_confirm_manager_cached(self):
        """覆盖 lines 238-244: 已缓存时直接返回"""
        ctx = _make_mock_context()
        mock_mgr = MagicMock()
        ctx.set_extension("ask_user_confirm_manager", mock_mgr)
        assert ctx.ask_user_confirm_manager is mock_mgr

    def test_chart_renderer_cached(self):
        """覆盖 lines 249-255: 已缓存时直接返回"""
        ctx = _make_mock_context()
        mock_renderer = MagicMock()
        ctx.set_extension("chart_renderer", mock_renderer)
        assert ctx.chart_renderer is mock_renderer

    def test_export_engine_cached(self):
        """覆盖 lines 260-266: 已缓存时直接返回"""
        ctx = _make_mock_context()
        mock_engine = MagicMock()
        ctx.set_extension("export_engine", mock_engine)
        assert ctx.export_engine is mock_engine

    def test_training_load_analyzer_cached(self):
        """覆盖 lines 305-313: 已缓存时直接返回"""
        ctx = _make_mock_context()
        mock_analyzer = MagicMock()
        ctx.set_extension("training_load_analyzer", mock_analyzer)
        assert ctx.training_load_analyzer is mock_analyzer

    def test_vdot_calculator_cached(self):
        """覆盖 lines 316-324: 已缓存时直接返回"""
        ctx = _make_mock_context()
        mock_calc = MagicMock()
        ctx.set_extension("vdot_calculator", mock_calc)
        assert ctx.vdot_calculator is mock_calc

    def test_race_prediction_engine_cached(self):
        """覆盖 lines 327-335: 已缓存时直接返回"""
        ctx = _make_mock_context()
        mock_engine = MagicMock()
        ctx.set_extension("race_prediction_engine", mock_engine)
        assert ctx.race_prediction_engine is mock_engine

    def test_injury_risk_analyzer_cached(self):
        """覆盖 lines 338-346: 已缓存时直接返回"""
        ctx = _make_mock_context()
        mock_analyzer = MagicMock()
        ctx.set_extension("injury_risk_analyzer", mock_analyzer)
        assert ctx.injury_risk_analyzer is mock_analyzer

    def test_plan_execution_repo_cached(self):
        """覆盖 lines 109-115: 已缓存时直接返回"""
        ctx = _make_mock_context()
        mock_repo = MagicMock()
        ctx.set_extension("plan_execution_repo", mock_repo)
        assert ctx.plan_execution_repo is mock_repo

    def test_training_response_analyzer_cached(self):
        """覆盖 lines 120-126: 已缓存时直接返回"""
        ctx = _make_mock_context()
        mock_analyzer = MagicMock()
        ctx.set_extension("training_response_analyzer", mock_analyzer)
        assert ctx.training_response_analyzer is mock_analyzer

    def test_prompt_tuner_cached(self):
        """覆盖 lines 541-544: 已缓存时直接返回"""
        ctx = _make_mock_context()
        mock_tuner = MagicMock()
        mock_engine = MagicMock()
        mock_engine._prompt_tuner = mock_tuner
        ctx.set_extension("evolution_engine", mock_engine)
        assert ctx.prompt_tuner is mock_tuner

    def test_prompt_tuner_no_engine(self):
        """覆盖 line 544: evolution_engine 没有 _prompt_tuner"""
        ctx = _make_mock_context()
        mock_engine = MagicMock(spec=[])
        ctx.set_extension("evolution_engine", mock_engine)
        assert ctx.prompt_tuner is None

    def test_prompt_tuner_params_with_tuner(self):
        """覆盖 lines 549-552: 有 tuner 时返回参数"""
        ctx = _make_mock_context()
        mock_tuner = MagicMock()
        mock_tuner.get_params.return_value = {"tone": 0.7}
        mock_engine = MagicMock()
        mock_engine._prompt_tuner = mock_tuner
        ctx.set_extension("evolution_engine", mock_engine)
        assert ctx.prompt_tuner_params == {"tone": 0.7}

    def test_prompt_tuner_params_no_tuner(self):
        """覆盖 line 552: 无 tuner 时返回 None"""
        ctx = _make_mock_context()
        mock_engine = MagicMock(spec=[])
        ctx.set_extension("evolution_engine", mock_engine)
        assert ctx.prompt_tuner_params is None


class TestAppContextLazyPropertyCreation:
    """覆盖 lazy property 首次创建逻辑（无缓存时）"""

    def test_plan_adjustment_validator_created(self):
        """覆盖 lines 131-137: 首次创建 PlanAdjustmentValidator"""
        ctx = _make_mock_context()
        validator = ctx.plan_adjustment_validator
        assert validator is not None
        # 验证已缓存
        assert ctx.get_extension("plan_adjustment_validator") is validator

    def test_prompt_template_engine_created(self):
        """覆盖 lines 142-148: 首次创建 PromptTemplateEngine"""
        ctx = _make_mock_context()
        engine = ctx.prompt_template_engine
        assert engine is not None
        assert ctx.get_extension("prompt_template_engine") is engine

    def test_goal_prediction_engine_created(self):
        """覆盖 lines 167-173: 首次创建 GoalPredictionEngine"""
        ctx = _make_mock_context()
        engine = ctx.goal_prediction_engine
        assert engine is not None
        assert ctx.get_extension("goal_prediction_engine") is engine

    def test_long_term_plan_generator_created(self):
        """覆盖 lines 178-184: 首次创建 LongTermPlanGenerator"""
        ctx = _make_mock_context()
        gen = ctx.long_term_plan_generator
        assert gen is not None
        assert ctx.get_extension("long_term_plan_generator") is gen

    def test_smart_advice_engine_created(self):
        """覆盖 lines 187-195: 首次创建 SmartAdviceEngine"""
        ctx = _make_mock_context()
        engine = ctx.smart_advice_engine
        assert engine is not None
        assert ctx.get_extension("smart_advice_engine") is engine

    def test_ask_user_confirm_manager_created(self):
        """覆盖 lines 238-244: 首次创建 AskUserConfirmManager"""
        ctx = _make_mock_context()
        mgr = ctx.ask_user_confirm_manager
        assert mgr is not None
        assert ctx.get_extension("ask_user_confirm_manager") is mgr

    def test_chart_renderer_created(self):
        """覆盖 lines 249-255: 首次创建 PlotextRenderer"""
        ctx = _make_mock_context()
        renderer = ctx.chart_renderer
        assert renderer is not None
        assert ctx.get_extension("chart_renderer") is renderer

    def test_export_engine_created(self):
        """覆盖 lines 260-266: 首次创建 ExportEngine"""
        ctx = _make_mock_context()
        engine = ctx.export_engine
        assert engine is not None
        assert ctx.get_extension("export_engine") is engine

    def test_training_load_analyzer_created(self):
        """覆盖 lines 305-313: 首次创建 TrainingLoadAnalyzer"""
        ctx = _make_mock_context()
        analyzer = ctx.training_load_analyzer
        assert analyzer is not None
        assert ctx.get_extension("training_load_analyzer") is analyzer

    def test_vdot_calculator_created(self):
        """覆盖 lines 316-324: 首次创建 VDOTCalculator"""
        ctx = _make_mock_context()
        calc = ctx.vdot_calculator
        assert calc is not None
        assert ctx.get_extension("vdot_calculator") is calc

    def test_race_prediction_engine_created(self):
        """覆盖 lines 327-335: 首次创建 RacePredictionEngine"""
        ctx = _make_mock_context()
        engine = ctx.race_prediction_engine
        assert engine is not None
        assert ctx.get_extension("race_prediction_engine") is engine

    def test_injury_risk_analyzer_created(self):
        """覆盖 lines 338-346: 首次创建 InjuryRiskAnalyzer"""
        ctx = _make_mock_context()
        analyzer = ctx.injury_risk_analyzer
        assert analyzer is not None
        assert ctx.get_extension("injury_risk_analyzer") is analyzer

    def test_plan_execution_repo_created(self):
        """覆盖 lines 109-115: 首次创建 PlanExecutionRepository"""
        ctx = _make_mock_context()
        repo = ctx.plan_execution_repo
        assert repo is not None
        assert ctx.get_extension("plan_execution_repo") is repo

    def test_training_response_analyzer_created(self):
        """覆盖 lines 120-126: 首次创建 TrainingResponseAnalyzer"""
        ctx = _make_mock_context()
        analyzer = ctx.training_response_analyzer
        assert analyzer is not None
        assert ctx.get_extension("training_response_analyzer") is analyzer

    def test_plan_modification_dialog_manager_created(self):
        """覆盖 lines 153-162: 首次创建 PlanModificationDialogManager"""
        ctx = _make_mock_context()
        mgr = ctx.plan_modification_dialog_manager
        assert mgr is not None
        assert ctx.get_extension("plan_modification_dialog_manager") is mgr

    def test_training_reminder_manager_created(self):
        """覆盖 lines 200-206: 首次创建 TrainingReminderManager"""
        ctx = _make_mock_context()
        mgr = ctx.training_reminder_manager
        assert mgr is not None
        assert ctx.get_extension("training_reminder_manager") is mgr

    def test_cron_callback_handler_created(self):
        """覆盖 lines 211-219: 首次创建 CronCallbackHandler"""
        ctx = _make_mock_context()
        handler = ctx.cron_callback_handler
        assert handler is not None
        assert ctx.get_extension("cron_callback_handler") is handler

    def test_gateway_integration_created(self):
        """覆盖 lines 224-233: 首次创建 GatewayIntegration"""
        ctx = _make_mock_context()
        integration = ctx.gateway_integration
        assert integration is not None
        assert ctx.get_extension("gateway_integration") is integration


class TestAppContextFactoryCreateForTesting:
    """覆盖 line 719: create_for_testing 委托给 create"""

    def test_create_for_testing_returns_context(self):
        """create_for_testing 应返回 AppContext 实例"""
        ctx = AppContextFactory.create_for_testing(allow_default=True)
        assert isinstance(ctx, AppContext)
        assert ctx.config is not None


class TestGlobalContextManagement:
    """覆盖 lines 750-775: get_context/set_context/reset_context"""

    def setup_method(self):
        """每个测试前重置全局上下文"""
        reset_context()

    def teardown_method(self):
        """每个测试后重置全局上下文"""
        reset_context()

    def test_set_and_get_context(self):
        """覆盖 line 765: set_context 设置后 get_context 返回"""
        mock_ctx = _make_mock_context()
        set_context(mock_ctx)
        assert get_context() is mock_ctx

    def test_reset_context(self):
        """覆盖 line 775: reset_context 后 get_context 创建新实例"""
        mock_ctx = _make_mock_context()
        set_context(mock_ctx)
        reset_context()
        # 重置后 get_context 会创建新实例（需要 allow_default）
        # 但这会触发真实的 AppContextFactory.create()，可能失败
        # 所以只验证 reset 后全局上下文为 None
        from src.core.base.context import _global_context

        assert _global_context is None
