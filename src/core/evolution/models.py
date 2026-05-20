# 决策追踪数据模型
# 定义DecisionLog/OutcomeRecord/PredictionAccuracyStats等核心数据结构

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.core.transparency.models import DecisionType


@dataclass(frozen=True)
class DecisionLog:
    """决策日志（不可变数据类）

    记录一次AI决策的完整信息，包括跑者状态、决策类型、工具调用链、
    预测快照、推荐文本、执行状态等。

    Attributes:
        decision_id: 决策唯一标识
        timestamp: 决策时间
        runner_state: 跑者状态快照（vdot/ctl/atl/tsb/fatigue_score等）
        decision_type: 决策类型（复用transparency模块的DecisionType）
        tool_call_chain: 工具调用链
        prediction_snapshot: 预测快照（可选）
        recommendation_text: 推荐文本（可选）
        execution_status: 执行状态（字符串：pending/executed/skipped/modified/failed）
        recommendation_accepted: 推荐是否被采纳（可选）
        session_key: 会话标识
    """

    decision_id: str
    timestamp: datetime
    runner_state: dict[str, Any]
    decision_type: DecisionType
    tool_call_chain: list[dict[str, Any]]
    prediction_snapshot: dict[str, Any] | None
    recommendation_text: str | None
    execution_status: str
    recommendation_accepted: bool | None
    session_key: str

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "decision_id": self.decision_id,
            "timestamp": self.timestamp.isoformat(),
            "runner_state": self.runner_state,
            "decision_type": self.decision_type.value,
            "tool_call_chain": self.tool_call_chain,
            "prediction_snapshot": self.prediction_snapshot,
            "recommendation_text": self.recommendation_text,
            "execution_status": self.execution_status,
            "recommendation_accepted": self.recommendation_accepted,
            "session_key": self.session_key,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DecisionLog:
        """从字典创建实例"""
        timestamp = data["timestamp"]
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        decision_type = data["decision_type"]
        if isinstance(decision_type, str):
            decision_type = DecisionType(decision_type)
        return cls(
            decision_id=data["decision_id"],
            timestamp=timestamp,
            runner_state=data["runner_state"],
            decision_type=decision_type,
            tool_call_chain=data["tool_call_chain"],
            prediction_snapshot=data.get("prediction_snapshot"),
            recommendation_text=data.get("recommendation_text"),
            execution_status=data["execution_status"],
            recommendation_accepted=data.get("recommendation_accepted"),
            session_key=data.get("session_key", ""),
        )


@dataclass(frozen=True)
class OutcomeRecord:
    """结果回填记录（不可变数据类）

    记录AI决策的实际结果，包括实际VDOT、伤病情况、执行忠实度、
    用户反馈、预测误差等。

    Attributes:
        outcome_id: 结果唯一标识
        decision_id: 关联的决策ID
        outcome_timestamp: 结果时间
        actual_vdot: 实际VDOT（可选）
        actual_injury: 是否发生伤病
        execution_fidelity: 执行忠实度（可选）
        user_feedback_score: 用户反馈评分（可选，1-5）
        user_feedback_text: 用户反馈文本（可选）
        prediction_error: 预测误差（可选）
        prediction_direction: 预测方向（overestimate/underestimate/accurate，非error_direction）
        session_id: 关联的Session ID（可选）
    """

    outcome_id: str
    decision_id: str
    outcome_timestamp: datetime
    actual_vdot: float | None
    actual_injury: bool
    execution_fidelity: float | None
    user_feedback_score: int | None
    user_feedback_text: str | None
    prediction_error: float | None
    prediction_direction: str | None
    session_id: str | None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "outcome_id": self.outcome_id,
            "decision_id": self.decision_id,
            "outcome_timestamp": self.outcome_timestamp.isoformat(),
            "actual_vdot": self.actual_vdot,
            "actual_injury": self.actual_injury,
            "execution_fidelity": self.execution_fidelity,
            "user_feedback_score": self.user_feedback_score,
            "user_feedback_text": self.user_feedback_text,
            "prediction_error": self.prediction_error,
            "prediction_direction": self.prediction_direction,
            "session_id": self.session_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OutcomeRecord:
        """从字典创建实例"""
        timestamp = data["outcome_timestamp"]
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        return cls(
            outcome_id=data["outcome_id"],
            decision_id=data["decision_id"],
            outcome_timestamp=timestamp,
            actual_vdot=data.get("actual_vdot"),
            actual_injury=data.get("actual_injury", False),
            execution_fidelity=data.get("execution_fidelity"),
            user_feedback_score=data.get("user_feedback_score"),
            user_feedback_text=data.get("user_feedback_text"),
            prediction_error=data.get("prediction_error"),
            prediction_direction=data.get("prediction_direction"),
            session_id=data.get("session_id"),
        )


@dataclass
class PredictionAccuracyStats:
    """预测精度统计

    汇总预测准确度统计数据。

    Attributes:
        mae: 平均绝对误差
        total_pairs: 配对总数
        overestimate_rate: 高估率
        underestimate_rate: 低估率
    """

    mae: float
    total_pairs: int
    overestimate_rate: float
    underestimate_rate: float

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "mae": self.mae,
            "total_pairs": self.total_pairs,
            "overestimate_rate": self.overestimate_rate,
            "underestimate_rate": self.underestimate_rate,
        }
