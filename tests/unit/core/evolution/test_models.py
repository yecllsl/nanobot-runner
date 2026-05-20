from __future__ import annotations

from datetime import datetime

import pytest

from src.core.evolution.models import (
    DecisionLog,
    OutcomeRecord,
    PredictionAccuracyStats,
)
from src.core.transparency.models import DecisionType


class TestDecisionLog:
    """DecisionLog 数据模型测试"""

    def test_create_decision_log_with_required_fields(self):
        """测试创建DecisionLog（仅必填字段）"""
        log = DecisionLog(
            decision_id="dec_001",
            timestamp=datetime(2026, 5, 1, 10, 0, 0),
            runner_state={
                "vdot": 45.0,
                "ctl": 50.0,
                "atl": 40.0,
                "tsb": 10.0,
                "fatigue_score": 3.0,
            },
            decision_type=DecisionType.PLAN_ADJUSTMENT,
            tool_call_chain=[
                {"tool": "generate_training_plan", "arguments": {"goal": "全马破4"}}
            ],
            prediction_snapshot=None,
            recommendation_text="建议执行5周训练计划",
            execution_status="pending",
            recommendation_accepted=None,
            session_key="session_001",
        )
        assert log.decision_id == "dec_001"
        assert log.decision_type == DecisionType.PLAN_ADJUSTMENT
        assert log.execution_status == "pending"
        assert log.prediction_snapshot is None
        assert log.recommendation_accepted is None

    def test_decision_log_is_frozen(self):
        """测试DecisionLog不可变"""
        log = DecisionLog(
            decision_id="dec_002",
            timestamp=datetime(2026, 5, 1, 10, 0, 0),
            runner_state={"vdot": 45.0},
            decision_type=DecisionType.TRAINING_ADVICE,
            tool_call_chain=[],
            prediction_snapshot=None,
            recommendation_text=None,
            execution_status="pending",
            recommendation_accepted=None,
            session_key="",
        )
        with pytest.raises(AttributeError):
            log.decision_id = "dec_003"  # type: ignore[misc]

    def test_decision_log_to_dict(self):
        """测试DecisionLog序列化为字典"""
        log = DecisionLog(
            decision_id="dec_004",
            timestamp=datetime(2026, 5, 1, 10, 0, 0),
            runner_state={"vdot": 45.0},
            decision_type=DecisionType.RECOVERY_SUGGESTION,
            tool_call_chain=[{"tool": "suggest_recovery", "arguments": {}}],
            prediction_snapshot={"predicted_vdot": 46.0},
            recommendation_text="建议休息",
            execution_status="executed",
            recommendation_accepted=True,
            session_key="session_002",
        )
        d = log.to_dict()
        assert d["decision_id"] == "dec_004"
        assert d["decision_type"] == "recovery_suggestion"
        assert d["execution_status"] == "executed"
        assert d["prediction_snapshot"] == {"predicted_vdot": 46.0}
        assert d["recommendation_accepted"] is True

    def test_decision_log_from_dict(self):
        """测试DecisionLog从字典反序列化"""
        data = {
            "decision_id": "dec_005",
            "timestamp": "2026-05-01T10:00:00",
            "runner_state": {"vdot": 45.0},
            "decision_type": "plan_adjustment",
            "tool_call_chain": [],
            "prediction_snapshot": None,
            "recommendation_text": None,
            "execution_status": "pending",
            "recommendation_accepted": None,
            "session_key": "",
        }
        log = DecisionLog.from_dict(data)
        assert log.decision_id == "dec_005"
        assert log.decision_type == DecisionType.PLAN_ADJUSTMENT
        assert log.execution_status == "pending"

    def test_execution_status_string_values(self):
        """测试execution_status使用字符串而非枚举"""
        valid_statuses = ["pending", "executed", "skipped", "modified", "failed"]
        for status in valid_statuses:
            log = DecisionLog(
                decision_id=f"dec_status_{status}",
                timestamp=datetime(2026, 5, 1, 10, 0, 0),
                runner_state={"vdot": 45.0},
                decision_type=DecisionType.GENERAL,
                tool_call_chain=[],
                prediction_snapshot=None,
                recommendation_text=None,
                execution_status=status,
                recommendation_accepted=None,
                session_key="",
            )
            assert log.execution_status == status


class TestOutcomeRecord:
    """OutcomeRecord 数据模型测试"""

    def test_create_outcome_record_with_required_fields(self):
        """测试创建OutcomeRecord（仅必填字段）"""
        record = OutcomeRecord(
            outcome_id="out_001",
            decision_id="dec_001",
            outcome_timestamp=datetime(2026, 5, 2, 8, 0, 0),
            actual_vdot=None,
            actual_injury=False,
            execution_fidelity=None,
            user_feedback_score=None,
            user_feedback_text=None,
            prediction_error=None,
            prediction_direction=None,
            session_id=None,
        )
        assert record.outcome_id == "out_001"
        assert record.decision_id == "dec_001"
        assert record.actual_vdot is None
        assert record.actual_injury is False

    def test_outcome_record_is_frozen(self):
        """测试OutcomeRecord不可变"""
        record = OutcomeRecord(
            outcome_id="out_002",
            decision_id="dec_002",
            outcome_timestamp=datetime(2026, 5, 2, 8, 0, 0),
            actual_vdot=None,
            actual_injury=False,
            execution_fidelity=None,
            user_feedback_score=None,
            user_feedback_text=None,
            prediction_error=None,
            prediction_direction=None,
            session_id=None,
        )
        with pytest.raises(AttributeError):
            record.outcome_id = "out_003"  # type: ignore[misc]

    def test_outcome_record_to_dict(self):
        """测试OutcomeRecord序列化为字典"""
        record = OutcomeRecord(
            outcome_id="out_003",
            decision_id="dec_003",
            outcome_timestamp=datetime(2026, 5, 2, 8, 0, 0),
            actual_vdot=46.0,
            actual_injury=False,
            execution_fidelity=0.85,
            user_feedback_score=4,
            user_feedback_text="很好",
            prediction_error=0.03,
            prediction_direction="overestimate",
            session_id="session_001",
        )
        d = record.to_dict()
        assert d["outcome_id"] == "out_003"
        assert d["prediction_direction"] == "overestimate"
        assert d["execution_fidelity"] == 0.85
        assert "error_direction" not in d

    def test_outcome_record_from_dict(self):
        """测试OutcomeRecord从字典反序列化"""
        data = {
            "outcome_id": "out_004",
            "decision_id": "dec_004",
            "outcome_timestamp": "2026-05-02T08:00:00",
            "actual_vdot": 46.0,
            "actual_injury": False,
            "execution_fidelity": 0.85,
            "user_feedback_score": 4,
            "user_feedback_text": "很好",
            "prediction_error": 0.03,
            "prediction_direction": "overestimate",
            "session_id": "session_001",
        }
        record = OutcomeRecord.from_dict(data)
        assert record.outcome_id == "out_004"
        assert record.prediction_direction == "overestimate"

    def test_prediction_direction_field_name_not_error_direction(self):
        """测试字段名为prediction_direction而非error_direction（评审遗留NP-03）"""
        record = OutcomeRecord(
            outcome_id="out_005",
            decision_id="dec_005",
            outcome_timestamp=datetime(2026, 5, 2, 8, 0, 0),
            actual_vdot=None,
            actual_injury=False,
            execution_fidelity=None,
            user_feedback_score=None,
            user_feedback_text=None,
            prediction_error=0.05,
            prediction_direction="underestimate",
            session_id=None,
        )
        assert hasattr(record, "prediction_direction")
        assert not hasattr(record, "error_direction")
        d = record.to_dict()
        assert "prediction_direction" in d
        assert "error_direction" not in d


class TestPredictionAccuracyStats:
    """PredictionAccuracyStats 数据模型测试"""

    def test_create_prediction_accuracy_stats(self):
        """测试创建PredictionAccuracyStats"""
        stats = PredictionAccuracyStats(
            mae=0.04,
            total_pairs=10,
            overestimate_rate=0.6,
            underestimate_rate=0.4,
        )
        assert stats.mae == 0.04
        assert stats.total_pairs == 10
        assert stats.overestimate_rate == 0.6
        assert stats.underestimate_rate == 0.4

    def test_prediction_accuracy_stats_to_dict(self):
        """测试PredictionAccuracyStats序列化"""
        stats = PredictionAccuracyStats(
            mae=0.04,
            total_pairs=10,
            overestimate_rate=0.6,
            underestimate_rate=0.4,
        )
        d = stats.to_dict()
        assert d["mae"] == 0.04
        assert d["total_pairs"] == 10
        assert d["overestimate_rate"] == 0.6
        assert d["underestimate_rate"] == 0.4
