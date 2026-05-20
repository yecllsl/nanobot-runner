# 结果回填收集器
# 负责收集AI决策的实际结果，计算执行忠实度、预测误差、用户反馈等

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from src.core.base.logger import get_logger
from src.core.evolution.config import EvolutionConfig
from src.core.evolution.decision_logger import DecisionLogger
from src.core.evolution.evolution_store import EvolutionStore
from src.core.evolution.models import (
    DecisionLog,
    OutcomeRecord,
    PredictionAccuracyStats,
)
from src.core.plan.ask_user_confirm import ConfirmOption, ConfirmPrompt, ConfirmScenario

if TYPE_CHECKING:
    from src.core.plan.plan_execution_repository import PlanExecutionRepository
    from src.core.plan.plan_manager import PlanManager

logger = get_logger(__name__)


@dataclass(frozen=True)
class PlanExecutionData:
    """计划执行数据（不可变数据类）

    记录训练计划的计划值与实际执行值，用于计算执行忠实度。

    Attributes:
        planned_volume_km: 计划跑量（公里）
        actual_volume_km: 实际跑量（公里）
        planned_duration_min: 计划时长（分钟）
        actual_duration_min: 实际时长（分钟）
        completion_rate: 完成率
    """

    planned_volume_km: float
    actual_volume_km: float
    planned_duration_min: int
    actual_duration_min: int
    completion_rate: float


class PlanExecutionDataAdapter:
    """计划执行数据适配器

    封装PlanManager和PlanExecutionRepository，
    提供统一的计划执行数据查询接口。

    从PlanManager获取计划详情（计划跑量/时长），
    从PlanExecutionRepository获取执行统计（实际跑量/时长/完成率），
    合并为PlanExecutionData供fidelity计算使用。

    Attributes:
        _plan_manager: 计划管理器实例
        _execution_repo: 执行记录仓库实例
    """

    def __init__(
        self, plan_manager: PlanManager, execution_repo: PlanExecutionRepository
    ) -> None:
        """初始化适配器

        Args:
            plan_manager: 计划管理器实例（PlanManager）
            execution_repo: 执行记录仓库实例（PlanExecutionRepository）
        """
        self._plan_manager = plan_manager
        self._execution_repo = execution_repo

    def get_execution_data(self, plan_id: str) -> PlanExecutionData | None:
        """获取计划执行数据

        从PlanManager获取计划详情计算计划跑量/时长，
        从PlanExecutionRepository获取执行统计获取实际值，
        合并为PlanExecutionData。

        Args:
            plan_id: 计划唯一标识

        Returns:
            PlanExecutionData | None: 执行数据，计划不存在返回None
        """
        plan = self._plan_manager.get_plan(plan_id)
        if plan is None:
            return None

        # 从计划详情计算计划跑量和时长
        planned_volume_km = 0.0
        planned_duration_min = 0
        for week in plan.weeks:
            planned_volume_km += week.weekly_distance_km
            planned_duration_min += week.weekly_duration_min

        # 从执行统计获取实际值
        try:
            stats = self._execution_repo.get_plan_execution_stats(plan_id)
            actual_volume_km = stats.total_distance_km
            actual_duration_min = stats.total_duration_min
            completion_rate = stats.completion_rate
        except Exception:
            logger.warning("获取计划执行统计失败: plan_id=%s", plan_id)
            actual_volume_km = 0.0
            actual_duration_min = 0
            completion_rate = 0.0

        return PlanExecutionData(
            planned_volume_km=planned_volume_km,
            actual_volume_km=actual_volume_km,
            planned_duration_min=planned_duration_min,
            actual_duration_min=actual_duration_min,
            completion_rate=completion_rate,
        )


def calculate_fidelity(data: PlanExecutionData) -> float:
    """计算执行忠实度

    公式: fidelity = 1 - (0.55 * |actual_volume - planned_volume|/planned_volume
                          + 0.45 * |actual_duration - planned_duration|/planned_duration)

    结果限制在[0, 1]范围内。计划值为0时返回1.0（无偏差）。

    Args:
        data: 计划执行数据

    Returns:
        float: 执行忠实度，范围[0, 1]
    """
    if data.planned_volume_km == 0 or data.planned_duration_min == 0:
        return 1.0

    volume_deviation = (
        abs(data.actual_volume_km - data.planned_volume_km) / data.planned_volume_km
    )
    duration_deviation = (
        abs(data.actual_duration_min - data.planned_duration_min)
        / data.planned_duration_min
    )
    fidelity = 1.0 - (0.55 * volume_deviation + 0.45 * duration_deviation)
    return max(0.0, min(1.0, fidelity))


def calculate_prediction_error(predicted: float, actual: float) -> tuple[float, str]:
    """计算预测误差和方向

    公式:
        prediction_error = |predicted - actual| / actual * 100
        prediction_direction:
            predicted > actual * 1.05 → "overestimate"
            predicted < actual * 0.95 → "underestimate"
            else → "accurate"

    Args:
        predicted: 预测值
        actual: 实际值

    Returns:
        tuple[float, str]: (预测误差百分比, 预测方向)
    """
    if actual == 0:
        if predicted == 0:
            return 0.0, "accurate"
        return 100.0, "overestimate" if predicted > 0 else "underestimate"

    error = abs(predicted - actual) / actual * 100.0
    if predicted > actual * 1.05:
        direction = "overestimate"
    elif predicted < actual * 0.95:
        direction = "underestimate"
    else:
        direction = "accurate"
    return error, direction


class OutcomeCollector:
    """结果回填收集器

    负责收集AI决策的实际结果，包括：
    - 计划执行忠实度（fidelity）
    - 预测精度（误差和方向）
    - 用户反馈（评分和文本）

    所有结果以OutcomeRecord形式持久化到EvolutionStore。

    Attributes:
        _store: 存储层实例
        _decision_logger: 决策日志记录器
        _plan_adapter: 计划执行数据适配器（可选）
        _config: 模块配置
    """

    def __init__(
        self,
        store: EvolutionStore,
        decision_logger: DecisionLogger,
        plan_adapter: PlanExecutionDataAdapter | None = None,
        config: EvolutionConfig | None = None,
    ) -> None:
        """初始化结果回填收集器

        Args:
            store: 存储层实例
            decision_logger: 决策日志记录器
            plan_adapter: 计划执行数据适配器（可选，无则无法计算fidelity）
            config: 模块配置，为None时使用默认配置
        """
        self._store = store
        self._decision_logger = decision_logger
        self._plan_adapter = plan_adapter
        self._config = config or EvolutionConfig()

    def check_plan_execution(self, decision_id: str) -> OutcomeRecord:
        """通过plan_adapter获取执行数据计算fidelity

        从决策日志中提取plan_id，通过plan_adapter获取执行数据，
        计算执行忠实度并保存为OutcomeRecord。

        若无plan_adapter或无执行数据，fidelity为None。

        Args:
            decision_id: 决策唯一标识

        Returns:
            OutcomeRecord: 包含执行忠实度的结果记录

        Raises:
            ValueError: 决策不存在时抛出
        """
        decision = self._decision_logger.get_decision_by_id(decision_id)
        if decision is None:
            raise ValueError(f"决策不存在: {decision_id}")

        fidelity: float | None = None
        if self._plan_adapter is not None:
            plan_id = self._extract_plan_id(decision)
            if plan_id is not None:
                exec_data = self._plan_adapter.get_execution_data(plan_id)
                if exec_data is not None:
                    fidelity = calculate_fidelity(exec_data)

        outcome = OutcomeRecord(
            outcome_id=f"out_{uuid.uuid4().hex[:12]}",
            decision_id=decision_id,
            outcome_timestamp=datetime.now(),
            actual_vdot=None,
            actual_injury=False,
            execution_fidelity=fidelity,
            user_feedback_score=None,
            user_feedback_text=None,
            prediction_error=None,
            prediction_direction=None,
            session_id=None,
        )
        self._store.save_outcome(outcome)
        logger.info(
            "计划执行检查完成: decision_id=%s, fidelity=%s", decision_id, fidelity
        )
        return outcome

    def check_prediction_accuracy(
        self, decision_id: str, actual_vdot: float
    ) -> tuple[OutcomeRecord, PredictionAccuracyStats]:
        """计算预测误差和方向

        从决策日志的prediction_snapshot中提取预测VDOT，
        与实际VDOT对比计算误差和方向，保存为OutcomeRecord。
        同时返回全局预测精度统计。

        Args:
            decision_id: 决策唯一标识
            actual_vdot: 实际VDOT值

        Returns:
            tuple[OutcomeRecord, PredictionAccuracyStats]: (结果记录, 精度统计)

        Raises:
            ValueError: 决策不存在时抛出
        """
        decision = self._decision_logger.get_decision_by_id(decision_id)
        if decision is None:
            raise ValueError(f"决策不存在: {decision_id}")

        prediction_error: float | None = None
        prediction_direction: str | None = None

        # 从prediction_snapshot中提取预测VDOT
        if decision.prediction_snapshot is not None:
            predicted_vdot = decision.prediction_snapshot.get("predicted_vdot")
            if predicted_vdot is not None:
                prediction_error, prediction_direction = calculate_prediction_error(
                    predicted_vdot, actual_vdot
                )

        outcome = OutcomeRecord(
            outcome_id=f"out_{uuid.uuid4().hex[:12]}",
            decision_id=decision_id,
            outcome_timestamp=datetime.now(),
            actual_vdot=actual_vdot,
            actual_injury=False,
            execution_fidelity=None,
            user_feedback_score=None,
            user_feedback_text=None,
            prediction_error=prediction_error,
            prediction_direction=prediction_direction,
            session_id=None,
        )
        self._store.save_outcome(outcome)

        # 计算全局精度统计
        stats = self._compute_accuracy_stats()
        logger.info(
            "预测精度检查完成: decision_id=%s, error=%s, direction=%s",
            decision_id,
            prediction_error,
            prediction_direction,
        )
        return outcome, stats

    def record_feedback(
        self,
        decision_id: str,
        score: int,
        text: str | None = None,
        accepted: bool | None = None,
    ) -> OutcomeRecord:
        """记录用户反馈

        将用户对决策的评分和文本反馈保存为OutcomeRecord。

        Args:
            decision_id: 决策唯一标识
            score: 用户反馈评分（1-5）
            text: 用户反馈文本（可选）
            accepted: 推荐是否被采纳（可选）

        Returns:
            OutcomeRecord: 包含用户反馈的结果记录

        Raises:
            ValueError: 决策不存在时抛出
        """
        decision = self._decision_logger.get_decision_by_id(decision_id)
        if decision is None:
            raise ValueError(f"决策不存在: {decision_id}")

        outcome = OutcomeRecord(
            outcome_id=f"out_{uuid.uuid4().hex[:12]}",
            decision_id=decision_id,
            outcome_timestamp=datetime.now(),
            actual_vdot=None,
            actual_injury=False,
            execution_fidelity=None,
            user_feedback_score=score,
            user_feedback_text=text,
            prediction_error=None,
            prediction_direction=None,
            session_id=None,
        )
        self._store.save_outcome(outcome)
        logger.info("用户反馈已记录: decision_id=%s, score=%d", decision_id, score)
        return outcome

    def generate_feedback_prompt(self, decision_id: str) -> ConfirmPrompt:
        """生成反馈提示

        根据决策信息生成用户反馈确认提示，使用ConfirmScenario.DECISION_FEEDBACK场景。

        Args:
            decision_id: 决策唯一标识

        Returns:
            ConfirmPrompt: 反馈确认提示

        Raises:
            ValueError: 决策不存在时抛出
        """
        decision = self._decision_logger.get_decision_by_id(decision_id)
        if decision is None:
            raise ValueError(f"决策不存在: {decision_id}")

        recommendation = decision.recommendation_text or "无"
        return ConfirmPrompt(
            scenario=ConfirmScenario.DECISION_FEEDBACK,
            title="决策反馈",
            message=(
                f"请对以下决策进行评分：\n决策ID: {decision_id}\n推荐: {recommendation}"
            ),
            options=[
                ConfirmOption(key="1", label="1分", description="非常不满意", value=1),
                ConfirmOption(key="2", label="2分", description="不满意", value=2),
                ConfirmOption(key="3", label="3分", description="一般", value=3),
                ConfirmOption(key="4", label="4分", description="满意", value=4),
                ConfirmOption(key="5", label="5分", description="非常满意", value=5),
            ],
            default_key="3",
            metadata={"decision_id": decision_id},
        )

    def get_outcome_by_decision_id(self, decision_id: str) -> OutcomeRecord | None:
        """根据决策ID获取结果记录

        查询与指定决策关联的最新结果记录。

        Args:
            decision_id: 决策唯一标识

        Returns:
            OutcomeRecord | None: 结果记录，未找到返回None
        """
        outcomes = self._store.query_outcomes(decision_id=decision_id, limit=1)
        if outcomes:
            return outcomes[0]
        return None

    def _compute_accuracy_stats(self) -> PredictionAccuracyStats:
        """计算全局预测精度统计

        从存储层获取所有决策-结果配对，汇总预测误差和方向统计。

        Returns:
            PredictionAccuracyStats: 预测精度统计
        """
        pairs = self._store.get_decision_outcome_pairs()

        errors: list[float] = []
        overestimate_count = 0
        underestimate_count = 0

        for _, outcome in pairs:
            if outcome.prediction_error is not None:
                errors.append(outcome.prediction_error)
                if outcome.prediction_direction == "overestimate":
                    overestimate_count += 1
                elif outcome.prediction_direction == "underestimate":
                    underestimate_count += 1

        total = len(errors)
        mae = sum(errors) / total if total > 0 else 0.0

        return PredictionAccuracyStats(
            mae=round(mae, 4),
            total_pairs=total,
            overestimate_rate=round(overestimate_count / total, 4)
            if total > 0
            else 0.0,
            underestimate_rate=round(underestimate_count / total, 4)
            if total > 0
            else 0.0,
        )

    def get_decision_outcome_pairs(self) -> list[tuple[DecisionLog, OutcomeRecord]]:
        """获取所有决策-结果配对

        委托EvolutionStore获取决策与对应结果的配对列表。

        Returns:
            list[tuple[DecisionLog, OutcomeRecord]]: 决策-结果配对列表
        """
        return self._store.get_decision_outcome_pairs()

    def get_accuracy_stats(self, days: int = 30) -> PredictionAccuracyStats:
        """获取预测精度统计（公开接口）

        计算全局预测精度统计，包括MAE、高估率、低估率。

        Args:
            days: 统计天数，默认30天（当前为全量统计，后续迭代支持日期过滤）

        Returns:
            PredictionAccuracyStats: 预测精度统计
        """
        return self._compute_accuracy_stats()

    def get_fidelity_stats(self, days: int = 30) -> dict[str, float | int]:
        """获取执行忠实度统计（公开接口）

        从存储层获取结果记录，计算执行忠实度统计。

        Args:
            days: 统计天数，默认30天

        Returns:
            dict: 包含count、avg_fidelity、min_fidelity、max_fidelity的字典
        """
        cutoff = datetime.now().timestamp() - days * 86400
        outcomes = self._store.query_outcomes(limit=10000)

        fidelities: list[float] = []
        for o in outcomes:
            if (
                o.execution_fidelity is not None
                and o.outcome_timestamp.timestamp() >= cutoff
            ):
                fidelities.append(o.execution_fidelity)

        if not fidelities:
            return {
                "count": 0,
                "avg_fidelity": 0.0,
                "min_fidelity": 0.0,
                "max_fidelity": 0.0,
            }

        return {
            "count": len(fidelities),
            "avg_fidelity": round(sum(fidelities) / len(fidelities), 4),
            "min_fidelity": round(min(fidelities), 4),
            "max_fidelity": round(max(fidelities), 4),
        }

    def _extract_plan_id(self, decision: DecisionLog) -> str | None:
        """从决策日志中提取plan_id

        依次从tool_call_chain的args和prediction_snapshot中查找plan_id。

        Args:
            decision: 决策日志对象

        Returns:
            str | None: plan_id，未找到返回None
        """
        # 从tool_call_chain的arguments中提取
        for call in decision.tool_call_chain:
            args = call.get("arguments", {})
            if "plan_id" in args:
                return args["plan_id"]
        # 从prediction_snapshot中提取
        if decision.prediction_snapshot and "plan_id" in decision.prediction_snapshot:
            return decision.prediction_snapshot["plan_id"]
        return None
