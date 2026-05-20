# 决策追踪引擎（薄编排层）
# 委托DecisionLogger和OutcomeCollector完成决策记录与结果回填
# 提供统一的对外接口，降低上层调用方的依赖复杂度

from __future__ import annotations

from typing import Any

from src.core.base.logger import get_logger
from src.core.evolution.decision_logger import DecisionLogger
from src.core.evolution.models import (
    DecisionLog,
    OutcomeRecord,
    PredictionAccuracyStats,
)
from src.core.evolution.outcome_collector import OutcomeCollector
from src.core.plan.ask_user_confirm import ConfirmPrompt

logger = get_logger(__name__)


class EvolutionEngine:
    """决策追踪引擎（薄编排层）

    作为决策追踪模块的统一入口，接收外部注入的DecisionLogger和
    OutcomeCollector实例，委托完成具体业务逻辑。
    上层调用方只需依赖Engine即可完成决策记录、结果回填、反馈收集等操作。

    采用依赖注入模式（与架构设计Section 8.2.5一致），
    子组件由外部构建后注入，提高可测试性和灵活性。

    Attributes:
        decision_logger: 决策日志记录器（只读）
        outcome_collector: 结果回填收集器（只读）
    """

    def __init__(
        self,
        decision_logger: DecisionLogger,
        outcome_collector: OutcomeCollector,
    ) -> None:
        """初始化决策追踪引擎

        接收外部构建的子组件实例，遵循依赖注入原则。

        Args:
            decision_logger: 决策日志记录器实例
            outcome_collector: 结果回填收集器实例
        """
        self._decision_logger = decision_logger
        self._outcome_collector = outcome_collector

    @property
    def decision_logger(self) -> DecisionLogger:
        """获取决策日志记录器（只读）"""
        return self._decision_logger

    @property
    def outcome_collector(self) -> OutcomeCollector:
        """获取结果回填收集器（只读）"""
        return self._outcome_collector

    def log_decision(self, decision: DecisionLog) -> str:
        """记录决策日志

        委托DecisionLogger.log_decision完成决策持久化。

        Args:
            decision: 决策日志对象

        Returns:
            str: 决策唯一标识decision_id
        """
        return self._decision_logger.log_decision(decision)

    def check_plan_execution(self, decision_id: str) -> OutcomeRecord:
        """检查计划执行忠实度

        委托OutcomeCollector.check_plan_execution计算执行忠实度。

        Args:
            decision_id: 决策唯一标识

        Returns:
            OutcomeRecord: 包含执行忠实度的结果记录
        """
        return self._outcome_collector.check_plan_execution(decision_id)

    def check_prediction_accuracy(
        self, decision_id: str, actual_vdot: float
    ) -> tuple[OutcomeRecord, PredictionAccuracyStats]:
        """检查预测精度

        委托OutcomeCollector.check_prediction_accuracy计算预测误差和全局统计。

        Args:
            decision_id: 决策唯一标识
            actual_vdot: 实际VDOT值

        Returns:
            tuple[OutcomeRecord, PredictionAccuracyStats]: (结果记录, 精度统计)
        """
        return self._outcome_collector.check_prediction_accuracy(
            decision_id, actual_vdot
        )

    def record_feedback(
        self,
        decision_id: str,
        score: int,
        text: str | None = None,
        accepted: bool | None = None,
    ) -> OutcomeRecord:
        """记录用户反馈

        委托OutcomeCollector.record_feedback保存用户评分和文本反馈。

        Args:
            decision_id: 决策唯一标识
            score: 用户反馈评分（1-5）
            text: 用户反馈文本（可选）
            accepted: 推荐是否被采纳（可选）

        Returns:
            OutcomeRecord: 包含用户反馈的结果记录
        """
        return self._outcome_collector.record_feedback(
            decision_id, score, text=text, accepted=accepted
        )

    def get_decision_history(
        self,
        start_date: Any = None,
        end_date: Any = None,
        decision_type: Any = None,
        limit: int = 100,
    ) -> list[DecisionLog]:
        """获取决策历史记录

        委托DecisionLogger.get_decision_history按条件查询。

        Args:
            start_date: 起始日期过滤（可选）
            end_date: 结束日期过滤（可选）
            decision_type: 决策类型过滤（可选）
            limit: 返回数量限制，默认100

        Returns:
            list[DecisionLog]: 符合条件的决策日志列表
        """
        return self._decision_logger.get_decision_history(
            start_date=start_date,
            end_date=end_date,
            decision_type=decision_type,
            limit=limit,
        )

    def get_evolution_status(self) -> dict[str, Any]:
        """获取决策追踪整体状态

        汇总总决策数、执行状态分布、决策类型分布、回填率、
        平均忠实度、平均预测误差、反馈收集率等统计信息。

        Returns:
            dict[str, Any]: 包含total_decisions、status_distribution、
                type_distribution、outcome_fill_rate、avg_fidelity、
                avg_prediction_error、feedback_collection_rate的字典
        """
        all_decisions = self._decision_logger.get_decision_history(limit=10000)

        status_dist: dict[str, int] = {}
        for d in all_decisions:
            status = d.execution_status
            status_dist[status] = status_dist.get(status, 0) + 1

        type_dist: dict[str, int] = {}
        for d in all_decisions:
            dtype = d.decision_type.value
            type_dist[dtype] = type_dist.get(dtype, 0) + 1

        # 计算回填率、平均忠实度、平均预测误差、反馈收集率
        pairs = self._outcome_collector.get_decision_outcome_pairs()
        total_decisions = len(all_decisions)

        outcome_fill_rate = len(pairs) / total_decisions if total_decisions > 0 else 0.0

        fidelities = [
            p[1].execution_fidelity
            for p in pairs
            if p[1].execution_fidelity is not None
        ]
        avg_fidelity = sum(fidelities) / len(fidelities) if fidelities else 0.0

        prediction_errors = [
            p[1].prediction_error for p in pairs if p[1].prediction_error is not None
        ]
        avg_prediction_error = (
            sum(prediction_errors) / len(prediction_errors)
            if prediction_errors
            else 0.0
        )

        feedback_scores = [
            p[1].user_feedback_score
            for p in pairs
            if p[1].user_feedback_score is not None
        ]
        feedback_collection_rate = (
            len(feedback_scores) / total_decisions if total_decisions > 0 else 0.0
        )

        return {
            "total_decisions": total_decisions,
            "status_distribution": status_dist,
            "type_distribution": type_dist,
            "outcome_fill_rate": round(outcome_fill_rate, 4),
            "avg_fidelity": round(avg_fidelity, 4),
            "avg_prediction_error": round(avg_prediction_error, 4),
            "feedback_collection_rate": round(feedback_collection_rate, 4),
        }

    def generate_feedback_prompt(self, decision_id: str) -> ConfirmPrompt:
        """生成反馈提示

        委托OutcomeCollector.generate_feedback_prompt生成用户反馈确认提示。

        Args:
            decision_id: 决策唯一标识

        Returns:
            ConfirmPrompt: 反馈确认提示
        """
        return self._outcome_collector.generate_feedback_prompt(decision_id)
