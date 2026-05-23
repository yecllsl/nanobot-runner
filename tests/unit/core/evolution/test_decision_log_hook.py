# DecisionLogHook单元测试
# 测试继承关系、状态管理、决策类型推断、决策日志创建等场景
# 适配依赖注入构造函数和TwinEngine注入

from __future__ import annotations

import asyncio
import inspect
import shutil
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from nanobot.agent.hook import AgentHook, AgentHookContext

from src.core.evolution.decision_log_hook import DecisionLogHook
from src.core.evolution.decision_logger import DecisionLogger
from src.core.evolution.evolution_engine import EvolutionEngine
from src.core.evolution.evolution_store import EvolutionStore
from src.core.evolution.outcome_collector import OutcomeCollector
from src.core.transparency.models import DecisionType


def run_async(coro: Any) -> Any:
    """同步执行协程，兼容Windows的ProactorEventLoop"""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result()
    else:
        return asyncio.run(coro)


def _make_engine(tmp_path: Path) -> EvolutionEngine:
    """创建测试用EvolutionEngine（依赖注入模式）"""
    store = EvolutionStore(tmp_path)
    decision_logger = DecisionLogger(store)
    outcome_collector = OutcomeCollector(store, decision_logger)
    return EvolutionEngine(
        decision_logger=decision_logger,
        outcome_collector=outcome_collector,
    )


@pytest.fixture
def temp_dir() -> Path:
    """创建临时目录，测试结束后清理"""
    dir_path = Path(tempfile.mkdtemp())
    yield dir_path
    if dir_path.exists():
        shutil.rmtree(dir_path)


@pytest.fixture
def engine(temp_dir: Path) -> EvolutionEngine:
    """创建EvolutionEngine实例（依赖注入模式）"""
    return _make_engine(temp_dir)


@pytest.fixture
def hook(engine: EvolutionEngine) -> DecisionLogHook:
    """创建DecisionLogHook实例（无TwinEngine，回退到字段名列表+None值）"""
    return DecisionLogHook(evolution_engine=engine, session_key="test_session")


@pytest.fixture
def mock_context() -> MagicMock:
    """创建模拟的AgentHookContext"""
    ctx = MagicMock(spec=AgentHookContext)
    ctx.iteration = 1
    ctx.messages = []
    ctx.tool_calls = []
    ctx.tool_results = []
    ctx.final_content = None
    ctx.error = None
    return ctx


class TestDecisionLogHookInheritance:
    """测试DecisionLogHook继承关系"""

    def test_inherits_agent_hook(self, hook: DecisionLogHook) -> None:
        """DecisionLogHook应直接继承AgentHook"""
        assert isinstance(hook, AgentHook)

    def test_finalize_content_is_sync(self, hook: DecisionLogHook) -> None:
        """finalize_content应为同步方法，不是协程函数"""
        assert not inspect.iscoroutinefunction(hook.finalize_content)

    def test_before_iteration_is_async(self, hook: DecisionLogHook) -> None:
        """before_iteration应为异步方法"""
        assert inspect.iscoroutinefunction(hook.before_iteration)

    def test_before_execute_tools_is_async(self, hook: DecisionLogHook) -> None:
        """before_execute_tools应为异步方法"""
        assert inspect.iscoroutinefunction(hook.before_execute_tools)


class TestDecisionLogHookStateManagement:
    """测试DecisionLogHook状态管理"""

    def test_before_iteration_resets_state(
        self, hook: DecisionLogHook, mock_context: MagicMock
    ) -> None:
        """before_iteration应重置_tool_call_chain和_decision_logged"""
        hook._tool_call_chain = [{"name": "some_tool", "arguments": {}}]
        hook._decision_logged = True

        run_async(hook.before_iteration(mock_context))

        assert hook._tool_call_chain == []
        assert hook._decision_logged is False

    def test_before_execute_tools_captures_tool_call(
        self, hook: DecisionLogHook, mock_context: MagicMock
    ) -> None:
        """before_execute_tools应捕获工具调用到_tool_call_chain"""
        mock_tc = MagicMock()
        mock_tc.name = "generate_training_plan"
        mock_tc.arguments = {"goal": "全马破4"}
        mock_tc.id = "tc_001"
        mock_context.tool_calls = [mock_tc]

        run_async(hook.before_execute_tools(mock_context))

        assert len(hook._tool_call_chain) == 1
        assert hook._tool_call_chain[0]["name"] == "generate_training_plan"
        assert hook._tool_call_chain[0]["arguments"] == {"goal": "全马破4"}
        assert hook._tool_call_chain[0]["id"] == "tc_001"

    def test_before_execute_tools_no_tool_calls(
        self, hook: DecisionLogHook, mock_context: MagicMock
    ) -> None:
        """tool_calls为空时不应追加任何内容"""
        mock_context.tool_calls = []
        run_async(hook.before_execute_tools(mock_context))
        assert hook._tool_call_chain == []

    def test_before_execute_tools_multiple_tool_calls(
        self, hook: DecisionLogHook, mock_context: MagicMock
    ) -> None:
        """多次工具调用应累积到_tool_call_chain"""
        mock_tc1 = MagicMock()
        mock_tc1.name = "get_vdot"
        mock_tc1.arguments = {}
        mock_tc1.id = "tc_001"
        mock_context.tool_calls = [mock_tc1]
        run_async(hook.before_execute_tools(mock_context))

        mock_tc2 = MagicMock()
        mock_tc2.name = "generate_training_plan"
        mock_tc2.arguments = {"goal": "半马PB"}
        mock_tc2.id = "tc_002"
        mock_context.tool_calls = [mock_tc2]
        run_async(hook.before_execute_tools(mock_context))

        assert len(hook._tool_call_chain) == 2
        assert hook._tool_call_chain[0]["name"] == "get_vdot"
        assert hook._tool_call_chain[1]["name"] == "generate_training_plan"


class TestDecisionTypeInference:
    """测试决策类型推断逻辑"""

    def test_infer_training_advice(self, hook: DecisionLogHook) -> None:
        """包含训练建议关键词应推断为TRAINING_ADVICE"""
        result = hook._infer_decision_type("以下是训练建议")
        assert result == DecisionType.TRAINING_ADVICE

    def test_infer_training_advice_easy_run(self, hook: DecisionLogHook) -> None:
        """包含轻松跑关键词应推断为TRAINING_ADVICE"""
        result = hook._infer_decision_type("今天适合轻松跑")
        assert result == DecisionType.TRAINING_ADVICE

    def test_infer_training_advice_interval(self, hook: DecisionLogHook) -> None:
        """包含间歇跑关键词应推断为TRAINING_ADVICE"""
        result = hook._infer_decision_type("今天适合间歇跑训练")
        assert result == DecisionType.TRAINING_ADVICE

    def test_infer_training_advice_tempo(self, hook: DecisionLogHook) -> None:
        """包含节奏跑关键词应推断为TRAINING_ADVICE"""
        result = hook._infer_decision_type("建议节奏跑5公里")
        assert result == DecisionType.TRAINING_ADVICE

    def test_infer_training_advice_long_distance(self, hook: DecisionLogHook) -> None:
        """包含长距离关键词应推断为TRAINING_ADVICE"""
        result = hook._infer_decision_type("周末安排长距离拉练")
        assert result == DecisionType.TRAINING_ADVICE

    def test_infer_plan_adjustment_highest_priority(
        self, hook: DecisionLogHook
    ) -> None:
        """PLAN_ADJUSTMENT优先级最高，即使包含其他类型关键词"""
        result = hook._infer_decision_type("需要调整计划，建议轻松跑")
        assert result == DecisionType.PLAN_ADJUSTMENT

    def test_infer_plan_adjustment_modify(self, hook: DecisionLogHook) -> None:
        """包含修改计划关键词应推断为PLAN_ADJUSTMENT"""
        result = hook._infer_decision_type("建议修改计划以适应恢复期")
        assert result == DecisionType.PLAN_ADJUSTMENT

    def test_infer_plan_adjustment_reorder(self, hook: DecisionLogHook) -> None:
        """包含计划调整关键词应推断为PLAN_ADJUSTMENT"""
        result = hook._infer_decision_type("计划调整：本周减少跑量")
        assert result == DecisionType.PLAN_ADJUSTMENT

    def test_infer_recovery_suggestion(self, hook: DecisionLogHook) -> None:
        """包含恢复关键词应推断为RECOVERY_SUGGESTION"""
        result = hook._infer_decision_type("建议休息一天进行恢复")
        assert result == DecisionType.RECOVERY_SUGGESTION

    def test_infer_recovery_suggestion_fatigue(self, hook: DecisionLogHook) -> None:
        """包含疲劳关键词应推断为RECOVERY_SUGGESTION"""
        result = hook._infer_decision_type("检测到疲劳累积，建议减量")
        assert result == DecisionType.RECOVERY_SUGGESTION

    def test_infer_recovery_suggestion_rest(self, hook: DecisionLogHook) -> None:
        """包含休息关键词应推断为RECOVERY_SUGGESTION"""
        result = hook._infer_decision_type("今天应该休息")
        assert result == DecisionType.RECOVERY_SUGGESTION

    def test_infer_weather_advice(self, hook: DecisionLogHook) -> None:
        """包含天气关键词应推断为WEATHER_ADVICE"""
        result = hook._infer_decision_type("今天天气不好，注意安全")
        assert result == DecisionType.WEATHER_ADVICE

    def test_infer_weather_advice_rain(self, hook: DecisionLogHook) -> None:
        """包含下雨关键词应推断为WEATHER_ADVICE"""
        result = hook._infer_decision_type("明天下雨，注意安全")
        assert result == DecisionType.WEATHER_ADVICE

    def test_infer_weather_advice_hot(self, hook: DecisionLogHook) -> None:
        """包含高温关键词应推断为WEATHER_ADVICE"""
        result = hook._infer_decision_type("高温预警，减少户外运动")
        assert result == DecisionType.WEATHER_ADVICE

    def test_infer_weather_advice_indoor(self, hook: DecisionLogHook) -> None:
        """包含室内训练关键词应推断为WEATHER_ADVICE"""
        result = hook._infer_decision_type("建议改为室内训练")
        assert result == DecisionType.WEATHER_ADVICE

    def test_infer_data_query_vdot(self, hook: DecisionLogHook) -> None:
        """包含VDOT关键词应推断为DATA_QUERY"""
        result = hook._infer_decision_type("当前VDOT为45.2")
        assert result == DecisionType.DATA_QUERY

    def test_infer_data_query_ctl(self, hook: DecisionLogHook) -> None:
        """包含CTL关键词应推断为DATA_QUERY"""
        result = hook._infer_decision_type("CTL为65，ATL为50")
        assert result == DecisionType.DATA_QUERY

    def test_infer_data_query_tsb(self, hook: DecisionLogHook) -> None:
        """包含TSB关键词应推断为DATA_QUERY"""
        result = hook._infer_decision_type("TSB为+15，体能充沛")
        assert result == DecisionType.DATA_QUERY

    def test_infer_data_query_stats(self, hook: DecisionLogHook) -> None:
        """包含统计关键词应推断为DATA_QUERY"""
        result = hook._infer_decision_type("本月统计数据显示跑量增加")
        assert result == DecisionType.DATA_QUERY

    def test_infer_data_query_data(self, hook: DecisionLogHook) -> None:
        """包含数据关键词应推断为DATA_QUERY"""
        result = hook._infer_decision_type("查看近期数据趋势")
        assert result == DecisionType.DATA_QUERY

    def test_infer_general_when_no_match(self, hook: DecisionLogHook) -> None:
        """无匹配关键词应推断为GENERAL"""
        result = hook._infer_decision_type("你好，有什么可以帮助你的？")
        assert result == DecisionType.GENERAL

    def test_priority_plan_over_recovery(self, hook: DecisionLogHook) -> None:
        """PLAN_ADJUSTMENT优先级高于RECOVERY_SUGGESTION"""
        result = hook._infer_decision_type("需要调整计划，注意恢复")
        assert result == DecisionType.PLAN_ADJUSTMENT

    def test_priority_recovery_over_training(self, hook: DecisionLogHook) -> None:
        """RECOVERY_SUGGESTION优先级高于TRAINING_ADVICE"""
        result = hook._infer_decision_type("疲劳累积，建议轻松跑")
        assert result == DecisionType.RECOVERY_SUGGESTION

    def test_priority_training_over_weather(self, hook: DecisionLogHook) -> None:
        """TRAINING_ADVICE优先级高于WEATHER_ADVICE"""
        result = hook._infer_decision_type("训练建议：高温天注意补水")
        assert result == DecisionType.TRAINING_ADVICE

    def test_priority_weather_over_data_query(self, hook: DecisionLogHook) -> None:
        """WEATHER_ADVICE优先级高于DATA_QUERY"""
        result = hook._infer_decision_type("天气数据表明适合跑步")
        assert result == DecisionType.WEATHER_ADVICE


class TestFinalizeContent:
    """测试finalize_content创建决策日志"""

    def test_finalize_content_creates_decision_log(
        self, hook: DecisionLogHook, engine: EvolutionEngine, mock_context: MagicMock
    ) -> None:
        """finalize_content应创建决策日志并持久化"""
        result = hook.finalize_content(mock_context, "以下是训练建议")

        assert result == "以下是训练建议"

        decisions = engine.get_decision_history(limit=10)
        assert len(decisions) >= 1

        decision = decisions[0]
        assert decision.decision_type == DecisionType.TRAINING_ADVICE
        assert decision.recommendation_text == "以下是训练建议"
        assert decision.execution_status == "pending"
        assert decision.session_key == "test_session"

    def test_finalize_content_with_tool_calls(
        self, hook: DecisionLogHook, engine: EvolutionEngine, mock_context: MagicMock
    ) -> None:
        """带工具调用的决策日志应包含tool_call_chain"""
        mock_tc = MagicMock()
        mock_tc.name = "get_vdot"
        mock_tc.arguments = {"days": 30}
        mock_tc.id = "tc_001"
        mock_context.tool_calls = [mock_tc]

        run_async(hook.before_execute_tools(mock_context))

        result = hook.finalize_content(mock_context, "当前VDOT数据如下")

        assert result == "当前VDOT数据如下"
        decisions = engine.get_decision_history(limit=10)
        assert len(decisions) >= 1
        assert len(decisions[0].tool_call_chain) == 1
        assert decisions[0].tool_call_chain[0]["name"] == "get_vdot"

    def test_finalize_content_none_content_no_log(
        self, hook: DecisionLogHook, engine: EvolutionEngine, mock_context: MagicMock
    ) -> None:
        """None内容不应创建决策日志"""
        result = hook.finalize_content(mock_context, None)

        assert result is None
        decisions = engine.get_decision_history(limit=10)
        assert len(decisions) == 0

    def test_finalize_content_returns_content_unchanged(
        self, hook: DecisionLogHook, mock_context: MagicMock
    ) -> None:
        """finalize_content应原样返回content"""
        content = "建议进行间歇跑训练"
        result = hook.finalize_content(mock_context, content)
        assert result == content

    def test_finalize_content_prevents_duplicate_logging(
        self, hook: DecisionLogHook, engine: EvolutionEngine, mock_context: MagicMock
    ) -> None:
        """防重复机制：多次调用finalize_content只记录一条决策"""
        hook.finalize_content(mock_context, "以下是训练建议")
        hook.finalize_content(mock_context, "再次训练建议")

        decisions = engine.get_decision_history(limit=10)
        assert len(decisions) == 1

    def test_finalize_content_runner_state_fallback_when_no_twin(
        self, hook: DecisionLogHook, engine: EvolutionEngine, mock_context: MagicMock
    ) -> None:
        """无TwinEngine时runner_state回退为字段名+None值"""
        hook.finalize_content(mock_context, "以下是训练建议")

        decisions = engine.get_decision_history(limit=10)
        assert len(decisions) >= 1
        runner_state = decisions[0].runner_state
        for field_name, value in runner_state.items():
            assert value is None, f"字段{field_name}的值应为None，实际为{value}"

    def test_finalize_content_runner_state_has_expected_fields(
        self, hook: DecisionLogHook, engine: EvolutionEngine, mock_context: MagicMock
    ) -> None:
        """runner_state应包含配置中定义的字段"""
        hook.finalize_content(mock_context, "以下是训练建议")

        decisions = engine.get_decision_history(limit=10)
        assert len(decisions) >= 1
        runner_state = decisions[0].runner_state
        expected_fields = ["vdot", "ctl", "atl", "tsb", "fatigue_score"]
        for field_name in expected_fields:
            assert field_name in runner_state, f"缺少字段{field_name}"

    def test_finalize_content_with_twin_engine(
        self, engine: EvolutionEngine, mock_context: MagicMock
    ) -> None:
        """注入TwinEngine时runner_state应包含实际值"""
        mock_twin = MagicMock()
        mock_snapshot = MagicMock()
        mock_snapshot.fitness.vdot = 45.2
        mock_snapshot.fitness.vdot_trend = "improving"
        mock_snapshot.load.ctl = 55.0
        mock_snapshot.load.atl = 42.0
        mock_snapshot.load.tsb = 13.0
        mock_snapshot.load.acwr = 0.76
        mock_snapshot.body_signal.fatigue_score = 3.5
        mock_snapshot.body_signal.recovery_status = "good"
        mock_snapshot.risk.injury_risk_7d = 0.12
        mock_snapshot.risk.injury_risk_28d = 0.08
        mock_snapshot.risk.overtraining_risk = "low"
        mock_snapshot.training_pattern.weekly_volume_km = 35.0
        mock_snapshot.training_pattern.long_run_frequency = 1.0
        mock_snapshot.snapshot_date = "2026-05-20"
        mock_snapshot.data_quality.value = "good"
        mock_twin.get_current_snapshot.return_value = mock_snapshot

        hook_with_twin = DecisionLogHook(
            evolution_engine=engine,
            twin_engine=mock_twin,
            session_key="test_twin",
        )

        hook_with_twin.finalize_content(mock_context, "以下是训练建议")

        decisions = engine.get_decision_history(limit=10)
        assert len(decisions) >= 1
        runner_state = decisions[0].runner_state
        assert runner_state["vdot"] == 45.2
        assert runner_state["ctl"] == 55.0
        assert runner_state["atl"] == 42.0
        assert runner_state["tsb"] == 13.0
        assert runner_state["fatigue_score"] == 3.5

    def test_finalize_content_twin_engine_failure_fallback(
        self, engine: EvolutionEngine, mock_context: MagicMock
    ) -> None:
        """TwinEngine获取失败时回退为字段名+None值"""
        mock_twin = MagicMock()
        mock_twin.get_current_snapshot.side_effect = RuntimeError("引擎未初始化")

        hook_with_twin = DecisionLogHook(
            evolution_engine=engine,
            twin_engine=mock_twin,
            session_key="test_twin_fail",
        )

        hook_with_twin.finalize_content(mock_context, "以下是训练建议")

        decisions = engine.get_decision_history(limit=10)
        assert len(decisions) >= 1
        runner_state = decisions[0].runner_state
        for field_name, value in runner_state.items():
            assert value is None, f"字段{field_name}的值应为None，实际为{value}"

    def test_finalize_content_truncates_long_recommendation(
        self, hook: DecisionLogHook, engine: EvolutionEngine, mock_context: MagicMock
    ) -> None:
        """recommendation_text应截断到500字符"""
        long_content = "训练建议" + "x" * 600
        hook.finalize_content(mock_context, long_content)

        decisions = engine.get_decision_history(limit=10)
        assert len(decisions) >= 1
        assert decisions[0].recommendation_text is not None
        assert len(decisions[0].recommendation_text) <= 500

    def test_finalize_content_log_decision_failure_handled(
        self, hook: DecisionLogHook, mock_context: MagicMock
    ) -> None:
        """log_decision抛异常时不应影响finalize_content返回"""
        hook._evolution_engine = MagicMock()
        hook._evolution_engine.log_decision.side_effect = RuntimeError("写入失败")
        hook._evolution_engine.decision_logger.runner_state_fields = ["vdot"]

        result = hook.finalize_content(mock_context, "以下是训练建议")

        assert result == "以下是训练建议"


class TestDecisionLogHookLifecycle:
    """测试DecisionLogHook完整生命周期"""

    def test_full_lifecycle(
        self, hook: DecisionLogHook, engine: EvolutionEngine, mock_context: MagicMock
    ) -> None:
        """完整生命周期：before_iteration -> before_execute_tools -> finalize_content"""
        run_async(hook.before_iteration(mock_context))
        assert hook._tool_call_chain == []
        assert hook._decision_logged is False

        mock_tc = MagicMock()
        mock_tc.name = "generate_training_plan"
        mock_tc.arguments = {"goal": "全马破4"}
        mock_tc.id = "tc_001"
        mock_context.tool_calls = [mock_tc]
        run_async(hook.before_execute_tools(mock_context))
        assert len(hook._tool_call_chain) == 1

        result = hook.finalize_content(mock_context, "需要调整计划以适应全马目标")
        assert result == "需要调整计划以适应全马目标"

        decisions = engine.get_decision_history(limit=10)
        assert len(decisions) == 1
        decision = decisions[0]
        assert decision.decision_type == DecisionType.PLAN_ADJUSTMENT
        assert len(decision.tool_call_chain) == 1
        assert decision.tool_call_chain[0]["name"] == "generate_training_plan"

    def test_multiple_iterations(
        self, hook: DecisionLogHook, engine: EvolutionEngine, mock_context: MagicMock
    ) -> None:
        """多次迭代应记录多条决策"""
        # 第一次迭代
        run_async(hook.before_iteration(mock_context))
        hook.finalize_content(mock_context, "建议轻松跑")

        # 第二次迭代
        run_async(hook.before_iteration(mock_context))
        hook.finalize_content(mock_context, "需要调整计划")

        decisions = engine.get_decision_history(limit=10)
        assert len(decisions) == 2


class TestDecisionLogHookV025Integration:
    """DecisionLogHook v0.25编排层一致性测试（H-01整改）"""

    def test_hook_holds_evolution_engine_reference(self) -> None:
        """DecisionLogHook应持有EvolutionEngine引用（非EvolutionController）"""
        from src.core.evolution.decision_log_hook import DecisionLogHook

        mock_engine = MagicMock()
        hook = DecisionLogHook(
            evolution_engine=mock_engine,
        )
        assert hook._evolution_engine is mock_engine

    def test_after_iteration_calls_engine_check_evolution_triggers(self) -> None:
        """after_iteration应调用EvolutionEngine.check_evolution_triggers()"""
        from datetime import datetime

        from src.core.evolution.decision_log_hook import DecisionLogHook
        from src.core.evolution.models import TriggerCheckResult

        mock_engine = MagicMock()
        mock_engine.check_evolution_triggers.return_value = TriggerCheckResult(
            checked_at=datetime.now(),
            triggered_actions=[],
            skipped_conditions=[],
        )
        hook = DecisionLogHook(evolution_engine=mock_engine)
        hook._decision_logged = True

        hook.after_iteration(MagicMock())
        mock_engine.check_evolution_triggers.assert_called_once()

    def test_after_iteration_triggers_async_execution_via_engine(self) -> None:
        """after_iteration应通过EvolutionEngine.execute_evolution_action()异步执行"""
        import time
        from datetime import datetime

        from src.core.evolution.decision_log_hook import DecisionLogHook
        from src.core.evolution.models import EvolutionAction, TriggerCheckResult

        action = EvolutionAction(
            action_id="async_test_001",
            action_type="retrain_model",
            trigger_reason="VDOT误差",
            trigger_condition={},
            target_model_type="vdot",
            priority="high",
            created_at=datetime.now(),
        )
        mock_engine = MagicMock()
        mock_engine.check_evolution_triggers.return_value = TriggerCheckResult(
            checked_at=datetime.now(),
            triggered_actions=[action],
            skipped_conditions=[],
        )
        hook = DecisionLogHook(evolution_engine=mock_engine)
        hook._decision_logged = True

        hook.after_iteration(MagicMock())

        # 等待daemon线程执行
        time.sleep(0.5)

        mock_engine.execute_evolution_action.assert_called()

    def test_v025_component_not_injected_graceful_degradation(self) -> None:
        """v0.25组件未注入时after_iteration不报错"""
        from src.core.evolution.decision_log_hook import DecisionLogHook

        mock_engine = MagicMock()
        mock_engine.check_evolution_triggers.side_effect = RuntimeError(
            "请先初始化v0.25组件"
        )
        hook = DecisionLogHook(evolution_engine=mock_engine)
        hook._decision_logged = True

        # 不应抛出异常
        hook.after_iteration(MagicMock())
