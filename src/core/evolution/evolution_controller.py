# 进化控制器
# 实现4条触发规则与动作执行（persist-first语义）
# 触发规则: VDOT误差/连续拒绝/新数据积累/月度复盘
# 动作类型: retrain_model/adjust_strategy/incremental_learn/generate_report

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import replace
from datetime import datetime
from typing import Any, Protocol

from src.core.evolution.config import EvolutionConfig
from src.core.evolution.models import (
    EvolutionAction,
    IncrementalLearnResult,
    TriggerCheckResult,
)

logger = logging.getLogger(__name__)

# 触发规则常量
_VDOT_ERROR_THRESHOLD = 0.05  # VDOT误差阈值5%
_VDOT_ERROR_MIN_COUNT = 3  # 连续3次误差超阈值触发
_REJECTION_MIN_COUNT = 2  # 连续2次拒绝触发
_NEW_DATA_THRESHOLD = 50  # 新数据积累50条触发


class _ModelEvolver(Protocol):
    """模型进化器协议（用于类型标注）"""

    def evolve_model(self, model_type: str) -> Any: ...

    def apply_params_to_instance(self, model_type: str) -> None: ...


class _PromptTuner(Protocol):
    """提示调优器协议（用于类型标注）"""

    def auto_adjust_on_rejection(self) -> Any: ...

    def get_params(self) -> Any: ...


class _EvolutionReporter(Protocol):
    """进化报告器协议（用于类型标注）"""

    def generate_report(self) -> Any: ...


class _CalibrationEngine(Protocol):
    """校准引擎协议（用于类型标注）"""

    def run_calibration(self, model_type: str) -> Any: ...


class _Store(Protocol):
    """存储层协议（用于类型标注）"""

    def get_prediction_actual_pairs(
        self, model_type: str, min_count: int = 10, days: int = 90
    ) -> list[tuple[float, float]]: ...

    def get_decision_outcome_pairs(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        days: int = 90,
    ) -> list[tuple[Any, Any]]: ...

    def count_decisions(self) -> int: ...

    def load_trigger_state(self, key: str) -> Any | None: ...

    def save_trigger_state(self, key: str, value: Any) -> None: ...

    def save_model_params(self, model_type: str, params: dict[str, Any]) -> None: ...


class EvolutionController:
    """进化控制器

    实现4条触发规则与动作执行（persist-first语义）:
    1. VDOT预测误差连续3次>5% → retrain_model
    2. 连续2次拒绝推荐 → adjust_strategy
    3. 新数据积累>=50条 → incremental_learn
    4. 当月未生成报告 → generate_report

    persist-first语义: retrain_model和incremental_learn动作
    先持久化参数到磁盘，持久化成功后才修改运行时实例属性。
    持久化失败时仅记录日志，不修改实例属性。

    Attributes:
        store: 决策追踪存储层
        calibration_engine: 校准引擎
        model_evolver: 模型进化器
        prompt_tuner: 提示调优器
        evolution_reporter: 进化报告器
        config: 进化配置
    """

    def __init__(
        self,
        store: _Store,
        calibration_engine: _CalibrationEngine,
        model_evolver: _ModelEvolver,
        prompt_tuner: _PromptTuner,
        evolution_reporter: _EvolutionReporter,
        config: EvolutionConfig,
    ) -> None:
        """初始化进化控制器

        Args:
            store: 决策追踪存储层
            calibration_engine: 校准引擎
            model_evolver: 模型进化器
            prompt_tuner: 提示调优器
            evolution_reporter: 进化报告器
            config: 进化配置
        """
        self._store = store
        self._calibration_engine = calibration_engine
        self._model_evolver = model_evolver
        self._prompt_tuner = prompt_tuner
        self._evolution_reporter = evolution_reporter
        self._config = config

    def check_triggers(self) -> TriggerCheckResult:
        """检查所有触发条件，返回触发结果

        依次执行4条触发规则检查，收集触发的动作和跳过的条件。
        性能预算: <50ms，超时记录警告日志。

        Returns:
            TriggerCheckResult: 触发条件检查结果
        """
        start_ms = time.monotonic()

        triggered_actions: list[EvolutionAction] = []
        skipped_conditions: list[dict[str, Any]] = []

        # 1. VDOT误差触发
        vdot_action = self._check_vdot_error_trigger(skipped_conditions)
        if vdot_action is not None:
            triggered_actions.append(vdot_action)

        # 2. 连续拒绝触发
        rejection_action = self._check_rejection_trigger(skipped_conditions)
        if rejection_action is not None:
            triggered_actions.append(rejection_action)

        # 3. 新数据积累触发
        new_data_action = self._check_new_data_trigger(skipped_conditions)
        if new_data_action is not None:
            triggered_actions.append(new_data_action)

        # 4. 月度复盘触发
        monthly_action = self._check_monthly_review_trigger(skipped_conditions)
        if monthly_action is not None:
            triggered_actions.append(monthly_action)

        # 性能监控
        elapsed_ms = (time.monotonic() - start_ms) * 1000
        if elapsed_ms > 50:
            logger.warning("check_triggers()耗时%.1fms超过50ms预算", elapsed_ms)

        return TriggerCheckResult(
            checked_at=datetime.now(),
            triggered_actions=triggered_actions,
            skipped_conditions=skipped_conditions,
        )

    def _check_vdot_error_trigger(
        self, skipped_conditions: list[dict[str, Any]]
    ) -> EvolutionAction | None:
        """检查VDOT预测误差触发条件

        连续3次VDOT预测误差>5%时触发retrain_model动作。
        使用get_prediction_actual_pairs("vdot", min_count=3, days=90)获取数据。

        Args:
            skipped_conditions: 跳过条件列表（就地追加）

        Returns:
            EvolutionAction | None: 触发的动作，未触发返回None
        """
        pairs = self._store.get_prediction_actual_pairs(
            "vdot", min_count=_VDOT_ERROR_MIN_COUNT, days=90
        )

        if len(pairs) < _VDOT_ERROR_MIN_COUNT:
            skipped_conditions.append(
                {
                    "rule": "vdot_error",
                    "reason": f"预测-实际配对数不足: {len(pairs)} < {_VDOT_ERROR_MIN_COUNT}",
                }
            )
            return None

        # 检查最近3次误差是否全部>5%
        recent_pairs = pairs[-_VDOT_ERROR_MIN_COUNT:]
        all_exceed = all(
            abs(predicted - actual) / max(abs(actual), 1e-9) > _VDOT_ERROR_THRESHOLD
            for predicted, actual in recent_pairs
        )

        if not all_exceed:
            skipped_conditions.append(
                {
                    "rule": "vdot_error",
                    "reason": "最近3次VDOT误差未全部超过5%阈值",
                }
            )
            return None

        return EvolutionAction(
            action_id=f"vdot_err_{uuid.uuid4().hex[:8]}",
            action_type="retrain_model",
            trigger_reason=f"VDOT预测误差连续{_VDOT_ERROR_MIN_COUNT}次>{_VDOT_ERROR_THRESHOLD * 100:.0f}%",
            trigger_condition={
                "recent_errors": [
                    abs(p - a) / max(abs(a), 1e-9) for p, a in recent_pairs
                ],
            },
            target_model_type="vdot",
            priority="high",
            created_at=datetime.now(),
        )

    def _check_rejection_trigger(
        self, skipped_conditions: list[dict[str, Any]]
    ) -> EvolutionAction | None:
        """检查连续拒绝触发条件

        连续2次推荐被拒绝时触发adjust_strategy动作。
        使用get_decision_outcome_pairs(days=90)获取数据。

        Args:
            skipped_conditions: 跳过条件列表（就地追加）

        Returns:
            EvolutionAction | None: 触发的动作，未触发返回None
        """
        pairs = self._store.get_decision_outcome_pairs(days=90)

        if len(pairs) < _REJECTION_MIN_COUNT:
            skipped_conditions.append(
                {
                    "rule": "rejection",
                    "reason": f"决策-结果配对数不足: {len(pairs)} < {_REJECTION_MIN_COUNT}",
                }
            )
            return None

        # 检查最近2次是否全部被拒绝
        recent_pairs = pairs[:_REJECTION_MIN_COUNT]
        all_rejected = all(
            getattr(outcome, "recommendation_accepted", None) is False
            for _, outcome in recent_pairs
        )

        if not all_rejected:
            skipped_conditions.append(
                {
                    "rule": "rejection",
                    "reason": "最近2次推荐未全部被拒绝",
                }
            )
            return None

        return EvolutionAction(
            action_id=f"rej_{uuid.uuid4().hex[:8]}",
            action_type="adjust_strategy",
            trigger_reason=f"连续{_REJECTION_MIN_COUNT}次拒绝推荐",
            trigger_condition={
                "rejection_count": _REJECTION_MIN_COUNT,
            },
            target_model_type="prompt",
            priority="medium",
            created_at=datetime.now(),
        )

    def _check_new_data_trigger(
        self, skipped_conditions: list[dict[str, Any]]
    ) -> EvolutionAction | None:
        """检查新数据积累触发条件

        新数据积累>=50条时触发incremental_learn动作。
        使用count_decisions()与_load_last_incremental_count()计算差值。

        Args:
            skipped_conditions: 跳过条件列表（就地追加）

        Returns:
            EvolutionAction | None: 触发的动作，未触发返回None
        """
        current_count = self._store.count_decisions()
        last_count = self._load_last_incremental_count()
        diff = current_count - last_count

        if diff < _NEW_DATA_THRESHOLD:
            skipped_conditions.append(
                {
                    "rule": "new_data",
                    "reason": f"新数据积累不足: {diff} < {_NEW_DATA_THRESHOLD} (当前{current_count}, 上次{last_count})",
                }
            )
            return None

        return EvolutionAction(
            action_id=f"inc_learn_{uuid.uuid4().hex[:8]}",
            action_type="incremental_learn",
            trigger_reason=f"新数据积累{diff}条>={_NEW_DATA_THRESHOLD}条",
            trigger_condition={
                "current_count": current_count,
                "last_count": last_count,
                "diff": diff,
            },
            target_model_type="all",
            priority="medium",
            created_at=datetime.now(),
        )

    def _check_monthly_review_trigger(
        self, skipped_conditions: list[dict[str, Any]]
    ) -> EvolutionAction | None:
        """检查月度复盘触发条件

        当月未生成报告时触发generate_report动作。
        检查trigger_state中last_monthly_report是否等于当前月份。

        Args:
            skipped_conditions: 跳过条件列表（就地追加）

        Returns:
            EvolutionAction | None: 触发的动作，未触发返回None
        """
        current_month = datetime.now().strftime("%Y-%m")
        last_report_month = self._store.load_trigger_state("last_monthly_report")

        if last_report_month == current_month:
            skipped_conditions.append(
                {
                    "rule": "monthly_review",
                    "reason": f"当月已生成报告: {current_month}",
                }
            )
            return None

        return EvolutionAction(
            action_id=f"monthly_{uuid.uuid4().hex[:8]}",
            action_type="generate_report",
            trigger_reason="月度复盘",
            trigger_condition={
                "current_month": current_month,
                "last_report_month": last_report_month,
            },
            target_model_type="none",
            priority="low",
            created_at=datetime.now(),
        )

    def execute_action(self, action: EvolutionAction) -> EvolutionAction:
        """执行进化动作（persist-first语义）

        根据动作类型分发到对应的执行方法。
        retrain_model和incremental_learn遵循persist-first语义:
        先持久化参数到磁盘，成功后才修改运行时实例属性。

        Args:
            action: 待执行的进化动作

        Returns:
            EvolutionAction: 执行后的动作（包含执行结果）
        """
        dispatch = {
            "retrain_model": self._execute_retrain_model,
            "adjust_strategy": self._execute_adjust_strategy,
            "incremental_learn": self._execute_incremental_learn,
            "generate_report": self._execute_generate_report,
        }

        executor = dispatch.get(action.action_type)
        if executor is None:
            logger.error("未知的动作类型: %s", action.action_type)
            return replace(
                action,
                executed=True,
                executed_at=datetime.now(),
                execution_result=f"未知动作类型: {action.action_type}",
            )

        return executor(action)

    def execute_pending_actions(
        self, actions: list[EvolutionAction]
    ) -> list[EvolutionAction]:
        """执行所有未执行的动作

        Args:
            actions: 动作列表

        Returns:
            list[EvolutionAction]: 执行后的动作列表
        """
        results: list[EvolutionAction] = []
        for action in actions:
            if action.executed:
                results.append(action)
            else:
                results.append(self.execute_action(action))
        return results

    def _execute_retrain_model(self, action: EvolutionAction) -> EvolutionAction:
        """执行retrain_model动作（persist-first语义）

        1. 调用model_evolver.evolve_model()获取进化结果
        2. 先持久化参数到磁盘（store.save_model_params）
        3. 持久化成功后才修改运行时实例属性（model_evolver.apply_params_to_instance）
        4. 持久化失败时不修改实例属性，记录失败信息

        Args:
            action: retrain_model动作

        Returns:
            EvolutionAction: 执行后的动作
        """
        model_type = action.target_model_type
        try:
            result = self._model_evolver.evolve_model(model_type)
        except Exception as exc:
            logger.error("模型进化失败: model_type=%s, error=%s", model_type, exc)
            return replace(
                action,
                executed=True,
                executed_at=datetime.now(),
                execution_result=f"模型进化失败: {exc}",
            )

        # persist-first: 先持久化
        try:
            params_dict: dict[str, Any] = {}
            if hasattr(result, "_raw_param_changes"):
                params_dict = dict(result._raw_param_changes)
            elif hasattr(result, "parameter_changes"):
                params_dict = {c.name: c.new_value for c in result.parameter_changes}

            if params_dict:
                self._store.save_model_params(model_type, params_dict)
        except Exception as exc:
            # 持久化失败，不修改实例属性
            logger.error(
                "持久化失败，不修改实例属性: model_type=%s, error=%s",
                model_type,
                exc,
            )
            return replace(
                action,
                executed=True,
                executed_at=datetime.now(),
                execution_result=f"持久化失败: {exc}",
            )

        # 持久化成功，修改运行时实例属性
        self._model_evolver.apply_params_to_instance(model_type)

        return replace(
            action,
            executed=True,
            executed_at=datetime.now(),
            execution_result={
                "mae_before": getattr(result, "mae_before", None),
                "mae_after": getattr(result, "mae_after", None),
                "persisted": True,
            },
        )

    def _execute_adjust_strategy(self, action: EvolutionAction) -> EvolutionAction:
        """执行adjust_strategy动作

        调用prompt_tuner.auto_adjust_on_rejection()调整提示策略。

        Args:
            action: adjust_strategy动作

        Returns:
            EvolutionAction: 执行后的动作
        """
        try:
            new_params = self._prompt_tuner.auto_adjust_on_rejection()
            params_info = (
                new_params.to_dict()
                if hasattr(new_params, "to_dict")
                else str(new_params)
            )
        except Exception as exc:
            logger.error("策略调整失败: error=%s", exc)
            return replace(
                action,
                executed=True,
                executed_at=datetime.now(),
                execution_result=f"策略调整失败: {exc}",
            )

        return replace(
            action,
            executed=True,
            executed_at=datetime.now(),
            execution_result={"new_params": params_info},
        )

    def _execute_incremental_learn(self, action: EvolutionAction) -> EvolutionAction:
        """执行incremental_learn动作（persist-first语义，H-02整改：结构化部分失败追踪）

        对所有模型类型依次执行增量学习:
        1. 调用model_evolver.evolve_model()获取进化结果
        2. 先持久化参数（persist-first）
        3. 持久化成功后修改运行时实例属性
        4. 使用IncrementalLearnResult记录每个模型的结果（含部分失败）
        5. 完成后更新trigger_state中的last_incremental_count

        Args:
            action: incremental_learn动作

        Returns:
            EvolutionAction: 执行后的动作
        """
        model_types = ["vdot", "injury", "training_response"]
        results: dict[str, dict[str, Any]] = {}

        for model_type in model_types:
            try:
                result = self._model_evolver.evolve_model(model_type)

                # persist-first: 先持久化
                params_dict: dict[str, Any] = {}
                if hasattr(result, "_raw_param_changes"):
                    params_dict = dict(result._raw_param_changes)
                elif hasattr(result, "parameter_changes"):
                    params_dict = {
                        c.name: c.new_value for c in result.parameter_changes
                    }

                if params_dict:
                    try:
                        self._store.save_model_params(model_type, params_dict)
                        # 持久化成功，修改运行时实例属性
                        self._model_evolver.apply_params_to_instance(model_type)
                    except Exception as exc:
                        logger.error(
                            "增量学习持久化失败: model_type=%s, error=%s",
                            model_type,
                            exc,
                        )
                        learn_result = IncrementalLearnResult(
                            model_type=model_type,
                            success=False,
                            mae_before=None,
                            mae_after=None,
                            error=f"持久化失败: {exc}",
                        )
                        results[model_type] = learn_result.to_dict()
                        continue

                # 进化成功
                learn_result = IncrementalLearnResult(
                    model_type=model_type,
                    success=True,
                    mae_before=getattr(result, "mae_before", None),
                    mae_after=getattr(result, "mae_after", None),
                    error=None,
                )
                results[model_type] = learn_result.to_dict()
            except ValueError as exc:
                # 数据不足，记录为失败并跳过
                logger.warning(
                    "增量学习数据不足跳过: model_type=%s, error=%s",
                    model_type,
                    exc,
                )
                learn_result = IncrementalLearnResult(
                    model_type=model_type,
                    success=False,
                    mae_before=None,
                    mae_after=None,
                    error="数据不足跳过",
                )
                results[model_type] = learn_result.to_dict()
            except Exception as exc:
                logger.error("增量学习失败: model_type=%s, error=%s", model_type, exc)
                learn_result = IncrementalLearnResult(
                    model_type=model_type,
                    success=False,
                    mae_before=None,
                    mae_after=None,
                    error=str(exc),
                )
                results[model_type] = learn_result.to_dict()

        # 更新trigger_state
        current_count = self._store.count_decisions()
        self._store.save_trigger_state("last_incremental_count", current_count)

        return replace(
            action,
            executed=True,
            executed_at=datetime.now(),
            execution_result=results,
        )

    def _execute_generate_report(self, action: EvolutionAction) -> EvolutionAction:
        """执行generate_report动作

        调用evolution_reporter.generate_report()生成月度报告，
        并更新trigger_state中的last_monthly_report。

        Args:
            action: generate_report动作

        Returns:
            EvolutionAction: 执行后的动作
        """
        try:
            report = self._evolution_reporter.generate_report()
            report_month = getattr(report, "month", datetime.now().strftime("%Y-%m"))
            # 更新trigger_state，标记当月已生成报告
            self._store.save_trigger_state("last_monthly_report", report_month)
        except Exception as exc:
            logger.error("报告生成失败: error=%s", exc)
            return replace(
                action,
                executed=True,
                executed_at=datetime.now(),
                execution_result=f"报告生成失败: {exc}",
            )

        return replace(
            action,
            executed=True,
            executed_at=datetime.now(),
            execution_result={"month": report_month},
        )

    def _load_last_incremental_count(self) -> int:
        """从trigger_state加载上次增量学习的决策计数

        首次调用（无存储值）或存储值非int时返回0。

        Returns:
            int: 上次增量学习时的决策计数
        """
        value = self._store.load_trigger_state("last_incremental_count")
        if value is None:
            return 0
        if isinstance(value, int):
            return value
        # 非int值（如字符串等），返回0
        return 0
