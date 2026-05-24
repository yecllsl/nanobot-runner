# DecisionLogHook - AI决策日志Hook
# 直接继承AgentHook（非ObservabilityHook），独立注册避免状态竞争
# 在Agent迭代生命周期中自动捕获工具调用链并创建决策日志

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from nanobot.agent.hook import AgentHook, AgentHookContext

from src.core.base.logger import get_logger
from src.core.evolution.models import DecisionLog
from src.core.transparency.models import DecisionType

if TYPE_CHECKING:
    from src.core.twin.digital_twin_engine import DigitalTwinEngine

logger = get_logger(__name__)

# 决策类型关键词映射（按优先级从高到低排列）
_DECISION_TYPE_KEYWORDS: list[tuple[DecisionType, list[str]]] = [
    (DecisionType.PLAN_ADJUSTMENT, ["调整计划", "修改计划", "计划调整"]),
    (DecisionType.RECOVERY_SUGGESTION, ["恢复", "休息", "疲劳"]),
    (
        DecisionType.TRAINING_ADVICE,
        ["训练建议", "轻松跑", "间歇跑", "节奏跑", "长距离"],
    ),
    (DecisionType.WEATHER_ADVICE, ["天气", "下雨", "高温", "室内训练"]),
    (DecisionType.DATA_QUERY, ["VDOT", "CTL", "ATL", "TSB", "数据", "统计"]),
]

# 决策类型优先级列表
_TYPE_PRIORITY: list[DecisionType] = [
    DecisionType.PLAN_ADJUSTMENT,
    DecisionType.RECOVERY_SUGGESTION,
    DecisionType.TRAINING_ADVICE,
    DecisionType.WEATHER_ADVICE,
    DecisionType.DATA_QUERY,
    DecisionType.GENERAL,
]


class DecisionLogHook(AgentHook):
    """AI决策日志Hook

    直接继承AgentHook（非ObservabilityHook），作为独立Hook注册，
    避免与ObservabilityHook的finalize_content产生状态竞争。

    在Agent迭代生命周期中：
    - before_iteration: 重置状态
    - before_execute_tools: 捕获工具调用到_tool_call_chain
    - finalize_content: 根据content关键词推断决策类型，创建DecisionLog

    Args:
        evolution_engine: 进化引擎实例，用于调用log_decision
        twin_engine: 数字孪生引擎实例，用于获取跑者状态快照
        session_key: 会话标识（可选）
    """

    def __init__(
        self,
        evolution_engine: Any,
        twin_engine: DigitalTwinEngine | None = None,
        session_key: str = "",
    ) -> None:
        """初始化决策日志Hook

        Args:
            evolution_engine: 进化引擎实例，需提供decision_logger属性和log_decision方法
            twin_engine: 数字孪生引擎实例，用于获取跑者状态快照（可选）
            session_key: 会话标识，用于关联决策日志
        """
        super().__init__()
        self._evolution_engine = evolution_engine
        self._twin_engine = twin_engine
        self._session_key = session_key
        self._tool_call_chain: list[dict[str, Any]] = []
        self._decision_logged: bool = False
        self._current_goal_state: str | None = None

    async def before_iteration(self, context: AgentHookContext) -> None:
        """迭代开始前重置状态

        Args:
            context: Hook上下文
        """
        self._tool_call_chain = []
        self._decision_logged = False
        self._current_goal_state = None

    async def before_execute_tools(self, context: AgentHookContext) -> None:
        """工具执行前捕获工具调用到_tool_call_chain

        Args:
            context: Hook上下文，包含tool_calls属性
        """
        if not context.tool_calls:
            return

        for tc in context.tool_calls:
            tool_name = getattr(tc, "name", "")
            tool_args = getattr(tc, "arguments", {})
            tool_id = getattr(tc, "id", "")
            self._tool_call_chain.append(
                {
                    "id": tool_id,
                    "name": tool_name,
                    "arguments": tool_args,
                }
            )

    def finalize_content(
        self, context: AgentHookContext, content: str | None
    ) -> str | None:
        """内容生成完成后创建DecisionLog（同步方法）

        根据content关键词推断决策类型，构建DecisionLog并调用
        evolution_engine.log_decision持久化。runner_state字段
        从DigitalTwinEngine获取实际值。

        Args:
            context: Hook上下文
            content: Agent最终输出的内容

        Returns:
            str | None: 原样返回content，不修改输出
        """
        if self._decision_logged:
            return content

        if content is None:
            return content

        self._decision_logged = True

        # v0.26: 从 context.metadata 读取 GoalState
        metadata = getattr(context, "metadata", None)
        goal_state = self.goal_state_raw(metadata)
        if goal_state is not None:
            self._current_goal_state = goal_state

        decision_type = self._infer_decision_type(content)
        runner_state = self._build_runner_state()

        decision = DecisionLog(
            decision_id=f"dec_{uuid.uuid4().hex[:8]}",
            timestamp=datetime.now(),
            runner_state=runner_state,
            decision_type=decision_type,
            tool_call_chain=self._tool_call_chain,
            prediction_snapshot=None,
            recommendation_text=content[:500] if content else None,
            execution_status="pending",
            recommendation_accepted=None,
            session_key=self._session_key,
            goal_state=self._current_goal_state,
        )

        try:
            self._evolution_engine.log_decision(decision)
            logger.debug(
                "决策日志已记录: decision_id=%s, type=%s",
                decision.decision_id,
                decision_type.value,
            )
        except Exception as e:
            logger.warning("决策日志记录失败: %s", e)

        return content

    def after_iteration(self, context: Any) -> None:
        """Agent迭代完成后回调（v0.26扩展：读取GoalState + 触发进化检查）"""
        # v0.26: 读取 GoalState
        metadata = getattr(context, "metadata", None)
        goal_state = self.goal_state_raw(metadata)
        if goal_state is not None:
            self._current_goal_state = goal_state

        if not self._decision_logged:
            return

        # v0.25: 触发进化检查
        try:
            result = self._evolution_engine.check_evolution_triggers()
            if result.triggered_actions:
                # 异步执行进化动作（daemon线程，不阻塞主流程）
                import threading

                def _execute_actions() -> None:
                    for action in result.triggered_actions:
                        try:
                            self._evolution_engine.execute_evolution_action(action)
                        except Exception as e:
                            logger.error("异步执行进化动作失败: %s", e)

                thread = threading.Thread(
                    target=_execute_actions,
                    daemon=True,
                    name="evolution-action-executor",
                )
                thread.start()
        except RuntimeError:
            # v0.25组件未注入，graceful降级
            pass
        except Exception as e:
            logger.warning("进化触发检查异常（不影响主流程）: %s", e)

    @staticmethod
    def goal_state_raw(metadata: dict[str, Any] | None) -> str | None:
        """从 context.metadata 提取当前活跃目标

        Args:
            metadata: AgentHookContext.metadata 字典

        Returns:
            str | None: 目标字符串，无目标时返回 None
        """
        if metadata is None:
            return None
        return metadata.get("goal_state")

    def _infer_decision_type(self, content: str) -> DecisionType:
        """根据content关键词推断决策类型

        Args:
            content: Agent输出的文本内容

        Returns:
            DecisionType: 推断出的决策类型，无匹配时返回GENERAL
        """
        found_types: set[DecisionType] = set()
        for decision_type, keywords in _DECISION_TYPE_KEYWORDS:
            for keyword in keywords:
                if keyword in content:
                    found_types.add(decision_type)
                    break

        for dt in _TYPE_PRIORITY:
            if dt in found_types:
                return dt

        return DecisionType.GENERAL

    def _build_runner_state(self) -> dict[str, Any]:
        """构建跑者状态快照

        优先从DigitalTwinEngine获取实际跑者状态向量，
        将5维状态展平为runner_state字典。
        若twin_engine未注入或获取失败，回退到字段名列表+None值。

        Returns:
            dict[str, Any]: 跑者状态字典
        """
        if self._twin_engine is not None:
            try:
                snapshot = self._twin_engine.get_current_snapshot()
                return {
                    "vdot": snapshot.fitness.vdot,
                    "vdot_trend": snapshot.fitness.vdot_trend,
                    "ctl": snapshot.load.ctl,
                    "atl": snapshot.load.atl,
                    "tsb": snapshot.load.tsb,
                    "acwr": snapshot.load.acwr,
                    "fatigue_score": snapshot.body_signal.fatigue_score,
                    "recovery_status": snapshot.body_signal.recovery_status,
                    "injury_risk_7d": snapshot.risk.injury_risk_7d,
                    "injury_risk_28d": snapshot.risk.injury_risk_28d,
                    "overtraining_risk": snapshot.risk.overtraining_risk,
                    "weekly_volume_km": snapshot.training_pattern.weekly_volume_km,
                    "long_run_frequency": snapshot.training_pattern.long_run_frequency,
                    "snapshot_date": snapshot.snapshot_date,
                    "data_quality": snapshot.data_quality.value,
                }
            except Exception as e:
                logger.warning("从DigitalTwinEngine获取状态快照失败: %s", e)

        # 回退: 从配置获取字段名列表，值设为None
        state: dict[str, Any] = {}
        try:
            if hasattr(self._evolution_engine, "decision_logger"):
                fields = self._evolution_engine.decision_logger.runner_state_fields
                for field_name in fields:
                    state[field_name] = None
        except Exception as e:
            logger.warning("获取runner_state字段列表失败: %s", e)
        return state
