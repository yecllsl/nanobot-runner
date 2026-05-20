# EvolutionEngine 单元测试
# 覆盖薄编排层的全部委托方法和get_evolution_status统计方法
# 适配依赖注入构造函数: EvolutionEngine(decision_logger, outcome_collector)

from __future__ import annotations

from datetime import datetime

import pytest

from src.core.evolution.decision_logger import DecisionLogger
from src.core.evolution.evolution_engine import EvolutionEngine
from src.core.evolution.evolution_store import EvolutionStore
from src.core.evolution.models import (
    DecisionLog,
    OutcomeRecord,
    PredictionAccuracyStats,
)
from src.core.evolution.outcome_collector import OutcomeCollector
from src.core.plan.ask_user_confirm import ConfirmPrompt
from src.core.transparency.models import DecisionType


def _make_decision(
    decision_id: str = "dec_001",
    timestamp: datetime | None = None,
    decision_type: DecisionType = DecisionType.TRAINING_ADVICE,
    execution_status: str = "pending",
    prediction_snapshot: dict | None = None,
    recommendation_text: str | None = "建议轻松跑",
    session_key: str = "session_001",
) -> DecisionLog:
    """创建测试用DecisionLog辅助函数"""
    return DecisionLog(
        decision_id=decision_id,
        timestamp=timestamp or datetime(2026, 5, 1, 10, 0, 0),
        runner_state={"vdot": 45.0, "ctl": 50.0, "atl": 40.0, "tsb": 10.0},
        decision_type=decision_type,
        tool_call_chain=[{"tool": "suggest_training", "arguments": {}}],
        prediction_snapshot=prediction_snapshot,
        recommendation_text=recommendation_text,
        execution_status=execution_status,
        recommendation_accepted=None,
        session_key=session_key,
    )


def _make_engine(tmp_path, plan_adapter=None) -> EvolutionEngine:
    """创建测试用EvolutionEngine辅助函数（依赖注入模式）

    创建共享EvolutionStore实例，构建DecisionLogger和OutcomeCollector
    后注入EvolutionEngine，与context.py中的创建逻辑一致。

    Args:
        tmp_path: 临时目录路径
        plan_adapter: 计划执行数据适配器（可选）

    Returns:
        EvolutionEngine: 测试用引擎实例
    """
    store = EvolutionStore(tmp_path)
    decision_logger = DecisionLogger(store)
    outcome_collector = OutcomeCollector(
        store, decision_logger, plan_adapter=plan_adapter
    )
    return EvolutionEngine(
        decision_logger=decision_logger,
        outcome_collector=outcome_collector,
    )


class TestLogDecision:
    """决策日志记录"""

    def test_log_decision_returns_decision_id(self, tmp_path):
        """记录决策返回decision_id"""
        engine = _make_engine(tmp_path)
        decision = _make_decision("dec_001")

        result = engine.log_decision(decision)

        assert result == "dec_001"

    def test_log_decision_persists_via_store(self, tmp_path):
        """记录决策通过共享store持久化"""
        engine = _make_engine(tmp_path)
        decision = _make_decision("dec_001")
        engine.log_decision(decision)

        found = engine.decision_logger.get_decision_by_id("dec_001")
        assert found is not None
        assert found.decision_id == "dec_001"


class TestCheckPlanExecution:
    """计划执行忠实度检查"""

    def test_check_plan_execution_without_adapter(self, tmp_path):
        """无plan_adapter时fidelity为None"""
        engine = _make_engine(tmp_path)
        decision = _make_decision("dec_001")
        engine.log_decision(decision)

        outcome = engine.check_plan_execution("dec_001")

        assert isinstance(outcome, OutcomeRecord)
        assert outcome.decision_id == "dec_001"
        assert outcome.execution_fidelity is None

    def test_check_plan_execution_nonexistent_decision(self, tmp_path):
        """检查不存在的决策抛出ValueError"""
        engine = _make_engine(tmp_path)

        with pytest.raises(ValueError, match="决策不存在"):
            engine.check_plan_execution("nonexistent_id")


class TestCheckPredictionAccuracy:
    """预测精度检查"""

    def test_check_prediction_accuracy_returns_tuple(self, tmp_path):
        """检查预测精度返回tuple(OutcomeRecord, PredictionAccuracyStats)"""
        engine = _make_engine(tmp_path)
        decision = _make_decision(
            "dec_001",
            prediction_snapshot={"predicted_vdot": 46.0},
        )
        engine.log_decision(decision)

        result = engine.check_prediction_accuracy("dec_001", actual_vdot=45.0)

        assert isinstance(result, tuple)
        assert len(result) == 2
        outcome, stats = result
        assert isinstance(outcome, OutcomeRecord)
        assert isinstance(stats, PredictionAccuracyStats)
        assert outcome.decision_id == "dec_001"
        assert outcome.actual_vdot == 45.0
        assert outcome.prediction_error is not None
        assert outcome.prediction_error > 0

    def test_check_prediction_accuracy_no_snapshot(self, tmp_path):
        """无prediction_snapshot时误差为None"""
        engine = _make_engine(tmp_path)
        decision = _make_decision("dec_001", prediction_snapshot=None)
        engine.log_decision(decision)

        outcome, stats = engine.check_prediction_accuracy("dec_001", actual_vdot=45.0)

        assert outcome.prediction_error is None
        assert outcome.prediction_direction is None
        assert outcome.actual_vdot == 45.0

    def test_check_prediction_accuracy_nonexistent_decision(self, tmp_path):
        """检查不存在的决策抛出ValueError"""
        engine = _make_engine(tmp_path)

        with pytest.raises(ValueError, match="决策不存在"):
            engine.check_prediction_accuracy("nonexistent_id", actual_vdot=45.0)


class TestRecordFeedback:
    """用户反馈记录"""

    def test_record_feedback(self, tmp_path):
        """记录用户反馈"""
        engine = _make_engine(tmp_path)
        decision = _make_decision("dec_001")
        engine.log_decision(decision)

        outcome = engine.record_feedback(
            "dec_001", score=4, text="很有帮助", accepted=True
        )

        assert isinstance(outcome, OutcomeRecord)
        assert outcome.decision_id == "dec_001"
        assert outcome.user_feedback_score == 4
        assert outcome.user_feedback_text == "很有帮助"

    def test_record_feedback_without_text(self, tmp_path):
        """仅记录评分，无文本"""
        engine = _make_engine(tmp_path)
        decision = _make_decision("dec_001")
        engine.log_decision(decision)

        outcome = engine.record_feedback("dec_001", score=3)

        assert outcome.user_feedback_score == 3
        assert outcome.user_feedback_text is None

    def test_record_feedback_nonexistent_decision(self, tmp_path):
        """对不存在的决策记录反馈抛出ValueError"""
        engine = _make_engine(tmp_path)

        with pytest.raises(ValueError, match="决策不存在"):
            engine.record_feedback("nonexistent_id", score=3)


class TestGetDecisionHistory:
    """决策历史查询"""

    def test_get_decision_history(self, tmp_path):
        """获取全部决策历史"""
        engine = _make_engine(tmp_path)
        d1 = _make_decision("dec_001", decision_type=DecisionType.TRAINING_ADVICE)
        d2 = _make_decision("dec_002", decision_type=DecisionType.PLAN_ADJUSTMENT)
        engine.log_decision(d1)
        engine.log_decision(d2)

        results = engine.get_decision_history()

        assert len(results) == 2

    def test_get_decision_history_by_type(self, tmp_path):
        """按类型过滤决策历史"""
        engine = _make_engine(tmp_path)
        d1 = _make_decision("dec_001", decision_type=DecisionType.TRAINING_ADVICE)
        d2 = _make_decision("dec_002", decision_type=DecisionType.PLAN_ADJUSTMENT)
        engine.log_decision(d1)
        engine.log_decision(d2)

        results = engine.get_decision_history(
            decision_type=DecisionType.TRAINING_ADVICE
        )

        assert len(results) == 1
        assert results[0].decision_type == DecisionType.TRAINING_ADVICE

    def test_get_decision_history_with_limit(self, tmp_path):
        """按数量限制获取历史"""
        engine = _make_engine(tmp_path)
        for i in range(5):
            d = _make_decision(f"dec_{i:03d}", timestamp=datetime(2026, 5, i + 1))
            engine.log_decision(d)

        results = engine.get_decision_history(limit=2)
        assert len(results) == 2


class TestGetEvolutionStatus:
    """决策追踪整体状态"""

    def test_empty_status(self, tmp_path):
        """无决策时状态统计"""
        engine = _make_engine(tmp_path)

        status = engine.get_evolution_status()

        assert status["total_decisions"] == 0
        assert status["status_distribution"] == {}
        assert status["type_distribution"] == {}
        assert status["outcome_fill_rate"] == 0.0
        assert status["avg_fidelity"] == 0.0
        assert status["avg_prediction_error"] == 0.0
        assert status["feedback_collection_rate"] == 0.0

    def test_status_with_decisions(self, tmp_path):
        """有决策时状态统计"""
        engine = _make_engine(tmp_path)
        d1 = _make_decision(
            "dec_001",
            execution_status="pending",
            decision_type=DecisionType.TRAINING_ADVICE,
        )
        d2 = _make_decision(
            "dec_002",
            execution_status="executed",
            decision_type=DecisionType.TRAINING_ADVICE,
        )
        d3 = _make_decision(
            "dec_003",
            execution_status="pending",
            decision_type=DecisionType.PLAN_ADJUSTMENT,
        )
        engine.log_decision(d1)
        engine.log_decision(d2)
        engine.log_decision(d3)

        status = engine.get_evolution_status()

        assert status["total_decisions"] == 3
        assert status["status_distribution"]["pending"] == 2
        assert status["status_distribution"]["executed"] == 1
        assert status["type_distribution"]["training_advice"] == 2
        assert status["type_distribution"]["plan_adjustment"] == 1
        assert "outcome_fill_rate" in status
        assert "avg_fidelity" in status
        assert "avg_prediction_error" in status
        assert "feedback_collection_rate" in status


class TestGenerateFeedbackPrompt:
    """反馈提示生成"""

    def test_generate_feedback_prompt(self, tmp_path):
        """生成反馈提示"""
        engine = _make_engine(tmp_path)
        decision = _make_decision("dec_001", recommendation_text="建议轻松跑")
        engine.log_decision(decision)

        prompt = engine.generate_feedback_prompt("dec_001")

        assert isinstance(prompt, ConfirmPrompt)
        assert "dec_001" in prompt.message
        assert "建议轻松跑" in prompt.message
        assert len(prompt.options) == 5

    def test_generate_feedback_prompt_nonexistent_decision(self, tmp_path):
        """对不存在的决策生成提示抛出ValueError"""
        engine = _make_engine(tmp_path)

        with pytest.raises(ValueError, match="决策不存在"):
            engine.generate_feedback_prompt("nonexistent_id")


class TestProperties:
    """属性访问"""

    def test_decision_logger_property(self, tmp_path):
        """decision_logger属性只读访问"""
        engine = _make_engine(tmp_path)

        assert engine.decision_logger is not None
        assert isinstance(engine.decision_logger, DecisionLogger)

    def test_outcome_collector_property(self, tmp_path):
        """outcome_collector属性只读访问"""
        engine = _make_engine(tmp_path)

        assert engine.outcome_collector is not None
        assert isinstance(engine.outcome_collector, OutcomeCollector)

    def test_shared_store_between_logger_and_collector(self, tmp_path):
        """decision_logger和outcome_collector共享同一store实例"""
        engine = _make_engine(tmp_path)

        decision = _make_decision("dec_shared")
        engine.log_decision(decision)

        outcome = engine.check_plan_execution("dec_shared")
        assert outcome.decision_id == "dec_shared"

    def test_dependency_injection_constructor(self, tmp_path):
        """依赖注入构造函数：外部构建子组件后注入"""
        store = EvolutionStore(tmp_path)
        logger = DecisionLogger(store)
        collector = OutcomeCollector(store, logger)

        engine = EvolutionEngine(
            decision_logger=logger,
            outcome_collector=collector,
        )

        assert engine.decision_logger is logger
        assert engine.outcome_collector is collector
