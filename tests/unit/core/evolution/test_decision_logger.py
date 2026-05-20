# DecisionLogger 单元测试
# 覆盖决策日志记录、执行状态更新、历史查询、配置读取等场景

from __future__ import annotations

from datetime import datetime

from src.core.evolution.config import EvolutionConfig
from src.core.evolution.decision_logger import DecisionLogger
from src.core.evolution.evolution_store import EvolutionStore
from src.core.evolution.models import DecisionLog
from src.core.transparency.models import DecisionType


def _make_decision(
    decision_id: str = "dec_001",
    timestamp: datetime | None = None,
    decision_type: DecisionType = DecisionType.TRAINING_ADVICE,
    execution_status: str = "pending",
    session_key: str = "session_001",
) -> DecisionLog:
    """创建测试用DecisionLog辅助函数"""
    return DecisionLog(
        decision_id=decision_id,
        timestamp=timestamp or datetime(2026, 5, 1, 10, 0, 0),
        runner_state={"vdot": 45.0, "ctl": 50.0, "atl": 40.0, "tsb": 10.0},
        decision_type=decision_type,
        tool_call_chain=[{"tool": "suggest_training", "arguments": {}}],
        prediction_snapshot=None,
        recommendation_text="建议轻松跑",
        execution_status=execution_status,
        recommendation_accepted=None,
        session_key=session_key,
    )


class TestLogDecision:
    """决策日志记录"""

    def test_log_decision_returns_decision_id(self, tmp_path):
        """记录决策返回decision_id"""
        store = EvolutionStore(tmp_path)
        decision_logger = DecisionLogger(store)
        decision = _make_decision("dec_001")

        result = decision_logger.log_decision(decision)

        assert result == "dec_001"

    def test_log_decision_persists_to_store(self, tmp_path):
        """记录决策持久化到存储层"""
        store = EvolutionStore(tmp_path)
        decision_logger = DecisionLogger(store)
        decision = _make_decision("dec_001")

        decision_logger.log_decision(decision)

        # 通过新的store实例验证持久化
        store2 = EvolutionStore(tmp_path)
        found = store2.get_decision_by_id("dec_001")
        assert found is not None
        assert found.decision_id == "dec_001"
        assert found.decision_type == DecisionType.TRAINING_ADVICE
        assert found.recommendation_text == "建议轻松跑"


class TestUpdateExecutionStatus:
    """执行状态更新"""

    def test_update_execution_status(self, tmp_path):
        """更新执行状态"""
        store = EvolutionStore(tmp_path)
        decision_logger = DecisionLogger(store)
        decision = _make_decision("dec_001", execution_status="pending")
        decision_logger.log_decision(decision)

        result = decision_logger.update_execution_status(
            "dec_001", "executed", accepted=True
        )

        assert result is True
        updated = decision_logger.get_decision_by_id("dec_001")
        assert updated is not None
        assert updated.execution_status == "executed"
        assert updated.recommendation_accepted is True

    def test_update_status_without_accepted(self, tmp_path):
        """仅更新执行状态，不更新accepted字段"""
        store = EvolutionStore(tmp_path)
        decision_logger = DecisionLogger(store)
        decision = _make_decision("dec_001", execution_status="pending")
        decision_logger.log_decision(decision)

        decision_logger.update_execution_status("dec_001", "skipped")

        updated = decision_logger.get_decision_by_id("dec_001")
        assert updated is not None
        assert updated.execution_status == "skipped"
        # accepted应保持原值（None）
        assert updated.recommendation_accepted is None

    def test_update_nonexistent_decision_returns_false(self, tmp_path):
        """更新不存在的决策返回False"""
        store = EvolutionStore(tmp_path)
        decision_logger = DecisionLogger(store)

        result = decision_logger.update_execution_status("nonexistent_id", "executed")

        assert result is False

    def test_update_preserves_other_fields(self, tmp_path):
        """更新执行状态后其他字段保持不变"""
        store = EvolutionStore(tmp_path)
        decision_logger = DecisionLogger(store)
        decision = _make_decision("dec_001", execution_status="pending")
        decision_logger.log_decision(decision)

        decision_logger.update_execution_status("dec_001", "executed", accepted=False)

        updated = decision_logger.get_decision_by_id("dec_001")
        assert updated is not None
        assert updated.decision_id == "dec_001"
        assert updated.timestamp == decision.timestamp
        assert updated.runner_state == decision.runner_state
        assert updated.decision_type == decision.decision_type
        assert updated.tool_call_chain == decision.tool_call_chain
        assert updated.prediction_snapshot == decision.prediction_snapshot
        assert updated.recommendation_text == decision.recommendation_text
        assert updated.session_key == decision.session_key


class TestGetDecisionHistory:
    """决策历史查询"""

    def test_get_history_by_decision_type(self, tmp_path):
        """按类型获取决策历史"""
        store = EvolutionStore(tmp_path)
        decision_logger = DecisionLogger(store)
        d1 = _make_decision("dec_001", decision_type=DecisionType.TRAINING_ADVICE)
        d2 = _make_decision("dec_002", decision_type=DecisionType.PLAN_ADJUSTMENT)
        d3 = _make_decision("dec_003", decision_type=DecisionType.TRAINING_ADVICE)

        decision_logger.log_decision(d1)
        decision_logger.log_decision(d2)
        decision_logger.log_decision(d3)

        results = decision_logger.get_decision_history(
            decision_type=DecisionType.TRAINING_ADVICE
        )
        assert len(results) == 2
        assert all(r.decision_type == DecisionType.TRAINING_ADVICE for r in results)

    def test_get_history_with_limit(self, tmp_path):
        """按数量限制获取历史"""
        store = EvolutionStore(tmp_path)
        decision_logger = DecisionLogger(store)
        for i in range(5):
            d = _make_decision(
                f"dec_{i:03d}",
                timestamp=datetime(2026, 5, i + 1),
            )
            decision_logger.log_decision(d)

        results = decision_logger.get_decision_history(limit=2)
        assert len(results) == 2


class TestGetDecisionById:
    """根据ID获取决策"""

    def test_get_decision_by_id(self, tmp_path):
        """根据ID获取决策"""
        store = EvolutionStore(tmp_path)
        decision_logger = DecisionLogger(store)
        decision = _make_decision("dec_001")
        decision_logger.log_decision(decision)

        result = decision_logger.get_decision_by_id("dec_001")

        assert result is not None
        assert result.decision_id == "dec_001"
        assert result.decision_type == DecisionType.TRAINING_ADVICE

    def test_get_nonexistent_decision_returns_none(self, tmp_path):
        """获取不存在的决策返回None"""
        store = EvolutionStore(tmp_path)
        decision_logger = DecisionLogger(store)

        result = decision_logger.get_decision_by_id("nonexistent_id")

        assert result is None


class TestRunnerStateFields:
    """跑者状态字段配置"""

    def test_runner_state_fields_from_config(self, tmp_path):
        """从配置获取runner_state_fields"""
        config = EvolutionConfig(runner_state_fields=["vdot", "ctl", "atl"])
        store = EvolutionStore(tmp_path)
        decision_logger = DecisionLogger(store, config=config)

        assert decision_logger.runner_state_fields == ["vdot", "ctl", "atl"]

    def test_default_runner_state_fields(self, tmp_path):
        """默认runner_state_fields"""
        store = EvolutionStore(tmp_path)
        decision_logger = DecisionLogger(store)

        assert decision_logger.runner_state_fields == [
            "vdot",
            "ctl",
            "atl",
            "tsb",
            "fatigue_score",
        ]
