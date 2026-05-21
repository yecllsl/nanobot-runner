# AppContext evolution_engine 扩展属性单元测试 - v0.23.0
# 测试决策追踪引擎的懒加载、缓存行为和依赖注入构造

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.base.context import AppContext
from src.core.evolution.decision_logger import DecisionLogger
from src.core.evolution.evolution_engine import EvolutionEngine
from src.core.evolution.outcome_collector import OutcomeCollector


@pytest.fixture
def mock_context():
    """创建Mock上下文"""
    config = MagicMock()
    config.data_dir = Path(tempfile.mkdtemp())

    context = AppContext(
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

    yield context

    # 清理临时目录
    import shutil

    shutil.rmtree(config.data_dir, ignore_errors=True)


class TestEvolutionEngineExtension:
    """AppContext evolution_engine 扩展属性测试"""

    def test_evolution_engine_returns_instance(self, mock_context):
        """evolution_engine属性应返回EvolutionEngine实例"""
        engine = mock_context.evolution_engine

        assert isinstance(engine, EvolutionEngine)

    def test_evolution_engine_caching(self, mock_context):
        """evolution_engine属性应缓存同一实例"""
        engine1 = mock_context.evolution_engine
        engine2 = mock_context.evolution_engine

        # 多次访问返回同一实例
        assert engine1 is engine2

        # 扩展存储中也应存在
        assert mock_context.get_extension("evolution_engine") is engine1

    def test_evolution_engine_lazy_load(self, mock_context):
        """evolution_engine应延迟加载，初始状态为None"""
        # 初始状态应为None
        assert mock_context.get_extension("evolution_engine") is None

        # 访问属性后应自动创建
        engine = mock_context.evolution_engine
        assert engine is not None
        assert mock_context.get_extension("evolution_engine") is engine

    def test_evolution_engine_manual_override(self, mock_context):
        """手动设置的evolution_engine实例应被优先返回"""
        custom_engine = MagicMock(spec=EvolutionEngine)
        mock_context.set_extension("evolution_engine", custom_engine)

        engine = mock_context.evolution_engine
        assert engine is custom_engine

    def test_evolution_engine_dependency_injection(self, mock_context):
        """验证EvolutionEngine使用依赖注入构造：decision_logger和outcome_collector由外部构建"""
        engine = mock_context.evolution_engine

        # 验证子组件类型正确
        assert isinstance(engine.decision_logger, DecisionLogger)
        assert isinstance(engine.outcome_collector, OutcomeCollector)

    def test_evolution_engine_shared_store(self, mock_context):
        """验证decision_logger和outcome_collector共享同一EvolutionStore实例"""
        engine = mock_context.evolution_engine

        # 通过decision_logger写入决策
        from datetime import datetime

        from src.core.evolution.models import DecisionLog
        from src.core.transparency.models import DecisionType

        decision = DecisionLog(
            decision_id="dec_shared_test",
            timestamp=datetime(2026, 5, 20, 10, 0, 0),
            runner_state={"vdot": 45.0},
            decision_type=DecisionType.TRAINING_ADVICE,
            tool_call_chain=[],
            prediction_snapshot=None,
            recommendation_text="测试共享store",
            execution_status="pending",
            recommendation_accepted=None,
            session_key="test",
        )
        engine.log_decision(decision)

        # 通过outcome_collector可查询到关联结果（共享store验证）
        outcome = engine.check_plan_execution("dec_shared_test")
        assert outcome.decision_id == "dec_shared_test"

    def test_evolution_engine_with_mocked_sub_components(self, mock_context):
        """通过mock验证EvolutionEngine构造时子组件正确注入"""
        with patch("src.core.evolution.evolution_engine.EvolutionEngine") as MockEngine:
            mock_instance = MagicMock()
            MockEngine.return_value = mock_instance

            engine = mock_context.evolution_engine

            assert engine is mock_instance
            # 验证EvolutionEngine使用依赖注入构造
            MockEngine.assert_called_once()
            call_kwargs = MockEngine.call_args
            # 构造参数应包含decision_logger和outcome_collector
            assert "decision_logger" in call_kwargs.kwargs
            assert "outcome_collector" in call_kwargs.kwargs


class TestEvolutionEngineV024Extension:
    """AppContext evolution_engine v0.24组件注入测试"""

    def test_v024_components_injected(self, mock_context):
        """v0.24组件应被注入到EvolutionEngine"""
        from src.core.evolution.calibration_engine import CalibrationEngine
        from src.core.evolution.model_evolver import ModelEvolver
        from src.core.evolution.response_analyzer import ResponseAnalyzer

        engine = mock_context.evolution_engine

        assert isinstance(engine._response_analyzer, ResponseAnalyzer)
        assert isinstance(engine._calibration_engine, CalibrationEngine)
        assert isinstance(engine._model_evolver, ModelEvolver)

    def test_v024_methods_callable(self, mock_context):
        """v0.24方法应可正常调用"""
        engine = mock_context.evolution_engine

        # analyze_training_response 不应抛RuntimeError
        report = engine.analyze_training_response(months=6)
        assert report is not None

        # apply_calibration_to_prediction 不应抛RuntimeError
        corrected = engine.apply_calibration_to_prediction("vdot", 46.0)
        assert corrected == 46.0  # 默认scale=1.0

    def test_v024_components_share_store(self, mock_context):
        """v0.24组件应与v0.23组件共享同一EvolutionStore"""
        engine = mock_context.evolution_engine

        store_v023 = engine.decision_logger._store
        store_v024 = engine._calibration_engine._store
        assert store_v023 is store_v024

    def test_get_evolution_status_includes_calibration(self, mock_context):
        """get_evolution_status应包含calibration_status"""
        engine = mock_context.evolution_engine
        status = engine.get_evolution_status()
        assert "calibration_status" in status
