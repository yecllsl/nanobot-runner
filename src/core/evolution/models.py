# 决策追踪数据模型
# 定义DecisionLog/OutcomeRecord/PredictionAccuracyStats等核心数据结构

from __future__ import annotations

from dataclasses import dataclass, field
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


@dataclass(frozen=True)
class TrainingTypeResponse:
    """训练类型响应性数据（不可变数据类）

    记录某类训练对跑者VDOT变化的响应效果。

    Attributes:
        training_type: 训练类型（interval/threshold/long/recovery/easy/unknown）
        sample_count: 样本数量
        avg_vdot_delta: 平均VDOT变化量
        avg_fidelity: 平均执行忠实度
        response_score: 综合响应性评分
    """

    training_type: str
    sample_count: int
    avg_vdot_delta: float
    avg_fidelity: float
    response_score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "training_type": self.training_type,
            "sample_count": self.sample_count,
            "avg_vdot_delta": self.avg_vdot_delta,
            "avg_fidelity": self.avg_fidelity,
            "response_score": self.response_score,
        }


@dataclass(frozen=True)
class TrainingResponseReport:
    """训练响应性分析报告（不可变数据类）

    Attributes:
        report_id: 报告唯一标识
        timestamp: 报告生成时间
        analysis_months: 分析月数
        total_pairs: 总决策-结果配对数
        eligible_pairs: 符合条件的配对数
        training_responses: 各训练类型响应数据列表
        best_type: 最佳训练类型（可选）
        worst_type: 最差训练类型（可选）
        profile_summary: 画像摘要文本
        data_sufficient: 数据是否充足
    """

    report_id: str
    timestamp: datetime
    analysis_months: int
    total_pairs: int
    eligible_pairs: int
    training_responses: list[TrainingTypeResponse]
    best_type: str | None
    worst_type: str | None
    profile_summary: str
    data_sufficient: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "timestamp": self.timestamp.isoformat(),
            "analysis_months": self.analysis_months,
            "total_pairs": self.total_pairs,
            "eligible_pairs": self.eligible_pairs,
            "training_responses": [r.to_dict() for r in self.training_responses],
            "best_type": self.best_type,
            "worst_type": self.worst_type,
            "profile_summary": self.profile_summary,
            "data_sufficient": self.data_sufficient,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TrainingResponseReport:
        timestamp = data["timestamp"]
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        responses = [
            TrainingTypeResponse(**r) for r in data.get("training_responses", [])
        ]
        return cls(
            report_id=data["report_id"],
            timestamp=timestamp,
            analysis_months=data["analysis_months"],
            total_pairs=data["total_pairs"],
            eligible_pairs=data["eligible_pairs"],
            training_responses=responses,
            best_type=data.get("best_type"),
            worst_type=data.get("worst_type"),
            profile_summary=data.get("profile_summary", ""),
            data_sufficient=data.get("data_sufficient", False),
        )


@dataclass(frozen=True)
class CalibrationProfile:
    """校准配置（不可变数据类）— 仅scale修正（评审MEDIUM-1整改：无bias字段）

    Attributes:
        model_type: 模型类型（vdot/injury/training_response）
        scale: 缩放因子，默认1.0（无修正）
        last_updated: 最后更新时间
        sample_count: 校准使用的样本数
        mae_before: 校准前MAE（可选）
        mae_after: 校准后MAE（可选）
    """

    model_type: str
    scale: float = 1.0
    last_updated: datetime = field(default_factory=datetime.now)
    sample_count: int = 0
    mae_before: float | None = None
    mae_after: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_type": self.model_type,
            "scale": self.scale,
            "last_updated": self.last_updated.isoformat(),
            "sample_count": self.sample_count,
            "mae_before": self.mae_before,
            "mae_after": self.mae_after,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CalibrationProfile:
        last_updated = data.get("last_updated", datetime.now().isoformat())
        if isinstance(last_updated, str):
            last_updated = datetime.fromisoformat(last_updated)
        return cls(
            model_type=data["model_type"],
            scale=data.get("scale", 1.0),
            last_updated=last_updated,
            sample_count=data.get("sample_count", 0),
            mae_before=data.get("mae_before"),
            mae_after=data.get("mae_after"),
        )

    @classmethod
    def default(cls, model_type: str) -> CalibrationProfile:
        """创建默认校准配置（scale=1.0，无修正）"""
        return cls(
            model_type=model_type,
            scale=1.0,
            last_updated=datetime.now(),
            sample_count=0,
            mae_before=None,
            mae_after=None,
        )


@dataclass(frozen=True)
class CalibrationReport:
    """校准报告（不可变数据类）— 无bias_before/bias_after字段

    Attributes:
        model_type: 模型类型
        timestamp: 校准时间
        direction: 偏差方向（overestimate/underestimate/none）
        magnitude: 偏差幅度
        scale_before: 校准前scale
        scale_after: 校准后scale
        mae_before: 校准前MAE
        mae_after: 校准后MAE
        improvement_pct: 改善百分比
        sample_count: 样本数
    """

    model_type: str
    timestamp: datetime
    direction: str
    magnitude: float
    scale_before: float
    scale_after: float
    mae_before: float
    mae_after: float
    improvement_pct: float
    sample_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_type": self.model_type,
            "timestamp": self.timestamp.isoformat(),
            "direction": self.direction,
            "magnitude": self.magnitude,
            "scale_before": self.scale_before,
            "scale_after": self.scale_after,
            "mae_before": self.mae_before,
            "mae_after": self.mae_after,
            "improvement_pct": self.improvement_pct,
            "sample_count": self.sample_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CalibrationReport:
        timestamp = data["timestamp"]
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        return cls(
            model_type=data["model_type"],
            timestamp=timestamp,
            direction=data["direction"],
            magnitude=data["magnitude"],
            scale_before=data["scale_before"],
            scale_after=data["scale_after"],
            mae_before=data["mae_before"],
            mae_after=data["mae_after"],
            improvement_pct=data["improvement_pct"],
            sample_count=data["sample_count"],
        )


@dataclass(frozen=True)
class ParameterChange:
    """参数变更记录（不可变数据类）

    Attributes:
        name: 参数名称
        old_value: 变更前值
        new_value: 变更后值
        change_pct: 变更百分比
    """

    name: str
    old_value: float
    new_value: float
    change_pct: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "change_pct": self.change_pct,
        }


@dataclass(frozen=True)
class ModelEvolutionResult:
    """模型进化结果（不可变数据类）

    Attributes:
        model_type: 模型类型
        timestamp: 进化时间
        parameter_changes: 参数变更列表
        mae_before: 进化前MAE
        mae_after: 进化后MAE
        improvement_pct: 改善百分比
        calibration_report: 关联的校准报告（可选）
    """

    model_type: str
    timestamp: datetime
    parameter_changes: list[ParameterChange]
    mae_before: float
    mae_after: float
    improvement_pct: float
    calibration_report: CalibrationReport | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_type": self.model_type,
            "timestamp": self.timestamp.isoformat(),
            "parameter_changes": [c.to_dict() for c in self.parameter_changes],
            "mae_before": self.mae_before,
            "mae_after": self.mae_after,
            "improvement_pct": self.improvement_pct,
            "calibration_report": (
                self.calibration_report.to_dict()
                if self.calibration_report is not None
                else None
            ),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModelEvolutionResult:
        timestamp = data["timestamp"]
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        changes = [ParameterChange(**c) for c in data.get("parameter_changes", [])]
        cal_report = None
        if data.get("calibration_report") is not None:
            cal_report = CalibrationReport.from_dict(data["calibration_report"])
        return cls(
            model_type=data["model_type"],
            timestamp=timestamp,
            parameter_changes=changes,
            mae_before=data["mae_before"],
            mae_after=data["mae_after"],
            improvement_pct=data["improvement_pct"],
            calibration_report=cal_report,
        )


# === v0.25 自适应进化数据模型 ===


@dataclass(frozen=True)
class EvolutionAction:
    """进化动作（不可变数据类）

    表示一个待执行的进化动作，由EvolutionController检测触发条件后生成。

    Attributes:
        action_id: 动作唯一标识
        action_type: 动作类型 (retrain_model/adjust_strategy/incremental_learn/generate_report)
        trigger_reason: 触发原因描述
        trigger_condition: 触发条件详情
        target_model_type: 目标模型类型 (vdot/injury/training_response/prompt/all/none)
        priority: 优先级 (high/medium/low)
        created_at: 创建时间
        executed: 是否已执行
        executed_at: 执行时间 (可选)
        execution_result: 执行结果摘要 (可选，str或dict类型)
    """

    action_id: str
    action_type: str
    trigger_reason: str
    trigger_condition: dict[str, Any]
    target_model_type: str
    priority: str
    created_at: datetime
    executed: bool = False
    executed_at: datetime | None = None
    execution_result: str | dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        result: dict[str, Any] = {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "trigger_reason": self.trigger_reason,
            "trigger_condition": self.trigger_condition,
            "target_model_type": self.target_model_type,
            "priority": self.priority,
            "created_at": self.created_at.isoformat(),
            "executed": self.executed,
        }
        if self.executed_at is not None:
            result["executed_at"] = self.executed_at.isoformat()
        if self.execution_result is not None:
            result["execution_result"] = self.execution_result
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvolutionAction:
        """从字典创建实例"""
        created_at = data["created_at"]
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        executed_at = data.get("executed_at")
        if isinstance(executed_at, str):
            executed_at = datetime.fromisoformat(executed_at)
        return cls(
            action_id=data["action_id"],
            action_type=data["action_type"],
            trigger_reason=data["trigger_reason"],
            trigger_condition=data.get("trigger_condition", {}),
            target_model_type=data["target_model_type"],
            priority=data["priority"],
            created_at=created_at,
            executed=data.get("executed", False),
            executed_at=executed_at,
            execution_result=data.get("execution_result"),
        )


@dataclass(frozen=True)
class TriggerCheckResult:
    """触发条件检查结果（不可变数据类）

    Attributes:
        checked_at: 检查时间
        triggered_actions: 触发的进化动作列表
        skipped_conditions: 跳过的条件及原因
    """

    checked_at: datetime
    triggered_actions: list[EvolutionAction]
    skipped_conditions: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "checked_at": self.checked_at.isoformat(),
            "triggered_actions": [a.to_dict() for a in self.triggered_actions],
            "skipped_conditions": self.skipped_conditions,
        }


@dataclass(frozen=True)
class PromptTuningParams:
    """提示调优参数（不可变数据类）

    4维连续参数空间，控制LLM输出风格。
    每个参数范围0.0-1.0，默认0.5（中性）。

    Attributes:
        tone_intensity: 语气强度 (0.0=温和/1.0=严厉)
        detail_level_score: 信息密度 (0.0=简洁/1.0=详细)
        recommendation_aggressiveness: 推荐激进程度 (0.0=保守/1.0=激进)
        data_driven_weight: 数据驱动权重 (0.0=纯经验驱动/1.0=纯数据驱动)
        last_updated: 最后更新时间
        update_count: 累计更新次数
    """

    tone_intensity: float = 0.5
    detail_level_score: float = 0.5
    recommendation_aggressiveness: float = 0.5
    data_driven_weight: float = 0.5
    last_updated: datetime = field(default_factory=datetime.now)
    update_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "tone_intensity": self.tone_intensity,
            "detail_level_score": self.detail_level_score,
            "recommendation_aggressiveness": self.recommendation_aggressiveness,
            "data_driven_weight": self.data_driven_weight,
            "last_updated": self.last_updated.isoformat(),
            "update_count": self.update_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PromptTuningParams:
        """从字典创建实例"""
        last_updated = data.get("last_updated", datetime.now().isoformat())
        if isinstance(last_updated, str):
            last_updated = datetime.fromisoformat(last_updated)
        return cls(
            tone_intensity=data.get("tone_intensity", 0.5),
            detail_level_score=data.get("detail_level_score", 0.5),
            recommendation_aggressiveness=data.get(
                "recommendation_aggressiveness", 0.5
            ),
            data_driven_weight=data.get("data_driven_weight", 0.5),
            last_updated=last_updated,
            update_count=data.get("update_count", 0),
        )

    @classmethod
    def default(cls) -> PromptTuningParams:
        """创建默认提示调优参数（全部0.5，中性）"""
        return cls(
            tone_intensity=0.5,
            detail_level_score=0.5,
            recommendation_aggressiveness=0.5,
            data_driven_weight=0.5,
            last_updated=datetime.now(),
            update_count=0,
        )

    def with_updates(
        self,
        tone: float | None = None,
        detail: float | None = None,
        aggressive: float | None = None,
        data_driven: float | None = None,
    ) -> PromptTuningParams:
        """创建更新后的参数副本（保持不可变性）

        每个参数被clamp到[0.0, 1.0]范围。

        Args:
            tone: 新的语气强度（None保持不变）
            detail: 新的信息密度（None保持不变）
            aggressive: 新的推荐激进程度（None保持不变）
            data_driven: 新的数据驱动权重（None保持不变）

        Returns:
            PromptTuningParams: 更新后的参数副本
        """
        return PromptTuningParams(
            tone_intensity=max(
                0.0, min(1.0, tone if tone is not None else self.tone_intensity)
            ),
            detail_level_score=max(
                0.0, min(1.0, detail if detail is not None else self.detail_level_score)
            ),
            recommendation_aggressiveness=max(
                0.0,
                min(
                    1.0,
                    aggressive
                    if aggressive is not None
                    else self.recommendation_aggressiveness,
                ),
            ),
            data_driven_weight=max(
                0.0,
                min(
                    1.0,
                    data_driven if data_driven is not None else self.data_driven_weight,
                ),
            ),
            last_updated=datetime.now(),
            update_count=self.update_count + 1,
        )
