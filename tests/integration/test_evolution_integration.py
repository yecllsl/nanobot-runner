# 决策追踪模块集成测试
# 测试DecisionLogHook/EvolutionEngine/EvolutionStore/OutcomeCollector的端到端交互
# 使用真实组件，不使用Mock

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from nanobot.agent.hook import AgentHookContext

from src.core.evolution.config import EvolutionConfig
from src.core.evolution.decision_log_hook import DecisionLogHook
from src.core.evolution.decision_logger import DecisionLogger
from src.core.evolution.evolution_engine import EvolutionEngine
from src.core.evolution.evolution_store import EvolutionStore
from src.core.evolution.models import DecisionLog
from src.core.evolution.outcome_collector import (
    OutcomeCollector,
    PlanExecutionData,
    PlanExecutionDataAdapter,
    calculate_fidelity,
)
from src.core.transparency import create_composite_hook
from src.core.transparency.hook_integration import ObservabilityHook
from src.core.transparency.models import DecisionType
from src.core.transparency.observability_manager import ObservabilityManager

# ---------------------------------------------------------------------------
# 辅助函数：同步执行async方法
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    """创建临时数据目录"""
    return tmp_path / "evolution_test"


@pytest.fixture
def evolution_engine(data_dir: Path) -> EvolutionEngine:
    """创建EvolutionEngine实例，使用依赖注入模式"""
    data_dir.mkdir(parents=True, exist_ok=True)
    store = EvolutionStore(data_dir=data_dir)
    config = EvolutionConfig()
    decision_logger = DecisionLogger(store=store, config=config)
    outcome_collector = OutcomeCollector(decision_logger=decision_logger, store=store)
    return EvolutionEngine(
        decision_logger=decision_logger, outcome_collector=outcome_collector
    )


@pytest.fixture
def evolution_store(data_dir: Path) -> EvolutionStore:
    """创建EvolutionStore实例，使用临时数据目录"""
    data_dir.mkdir(parents=True, exist_ok=True)
    return EvolutionStore(data_dir=data_dir)


@pytest.fixture
def decision_logger(evolution_store: EvolutionStore) -> DecisionLogger:
    """创建DecisionLogger实例"""
    return DecisionLogger(store=evolution_store)


@pytest.fixture
def outcome_collector(
    evolution_store: EvolutionStore, decision_logger: DecisionLogger
) -> OutcomeCollector:
    """创建OutcomeCollector实例（无plan_adapter）"""
    return OutcomeCollector(store=evolution_store, decision_logger=decision_logger)


@pytest.fixture
def decision_log_hook(evolution_engine: EvolutionEngine) -> DecisionLogHook:
    """创建DecisionLogHook实例"""
    return DecisionLogHook(
        evolution_engine=evolution_engine, session_key="integration_test"
    )


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


def make_decision_log(
    decision_id: str = "dec_test001",
    decision_type: DecisionType = DecisionType.TRAINING_ADVICE,
    execution_status: str = "pending",
    session_key: str = "integration_test",
    tool_call_chain: list[dict[str, Any]] | None = None,
    prediction_snapshot: dict[str, Any] | None = None,
    recommendation_text: str | None = None,
) -> DecisionLog:
    """创建测试用DecisionLog"""
    return DecisionLog(
        decision_id=decision_id,
        timestamp=datetime.now(),
        runner_state={
            "vdot": None,
            "ctl": None,
            "atl": None,
            "tsb": None,
            "fatigue_score": None,
        },
        decision_type=decision_type,
        tool_call_chain=tool_call_chain or [],
        prediction_snapshot=prediction_snapshot,
        recommendation_text=recommendation_text or "测试推荐文本",
        execution_status=execution_status,
        recommendation_accepted=None,
        session_key=session_key,
    )


# ---------------------------------------------------------------------------
# 场景1: Hook触发到存储落盘端到端流程
# DecisionLogHook.finalize_content -> EvolutionStore.save_decision -> JSONL文件
# ---------------------------------------------------------------------------


class TestHookToStorageEndToEnd:
    """测试DecisionLogHook到JSONL文件落盘的端到端流程"""

    def test_finalize_content_creates_jsonl_file(
        self,
        decision_log_hook: DecisionLogHook,
        evolution_engine: EvolutionEngine,
        data_dir: Path,
        mock_context: MagicMock,
    ) -> None:
        """finalize_content应创建JSONL文件并写入决策日志"""
        # 执行: 触发finalize_content
        content = "以下是训练建议，建议轻松跑5公里"
        result = decision_log_hook.finalize_content(mock_context, content)

        # 验证: content原样返回
        assert result == content

        # 验证: Parquet文件已创建
        decisions_dir = data_dir / "decisions"
        parquet_files = list(decisions_dir.rglob("*.parquet"))
        assert len(parquet_files) >= 1, "应至少创建一个Parquet文件"

        # 验证: 通过Engine查询确认数据完整
        decisions = evolution_engine.get_decision_history(limit=10)
        assert len(decisions) >= 1, "应至少写入一条记录"

        # 验证: 查询结果数据完整
        decision = decisions[0]
        assert decision.decision_id is not None
        assert decision.decision_type == DecisionType.TRAINING_ADVICE
        assert decision.recommendation_text == content
        assert decision.execution_status == "pending"
        assert decision.session_key == "integration_test"

    def test_finalize_content_with_tool_calls_stored(
        self,
        decision_log_hook: DecisionLogHook,
        evolution_engine: EvolutionEngine,
        data_dir: Path,
        mock_context: MagicMock,
    ) -> None:
        """带工具调用的决策应完整存储tool_call_chain"""
        # 准备: 模拟工具调用
        mock_tc = MagicMock()
        mock_tc.name = "generate_training_plan"
        mock_tc.arguments = {"goal": "全马破4"}
        mock_tc.id = "tc_001"
        mock_context.tool_calls = [mock_tc]

        # 执行: 先捕获工具调用，再finalize
        run_async(decision_log_hook.before_iteration(mock_context))
        run_async(decision_log_hook.before_execute_tools(mock_context))
        decision_log_hook.finalize_content(mock_context, "需要调整计划以适应全马目标")

        # 验证: 通过Engine查询确认数据完整
        decisions = evolution_engine.get_decision_history(limit=10)
        assert len(decisions) >= 1
        decision = decisions[0]
        assert decision.decision_type == DecisionType.PLAN_ADJUSTMENT
        assert len(decision.tool_call_chain) == 1
        assert decision.tool_call_chain[0]["name"] == "generate_training_plan"
        assert decision.tool_call_chain[0]["arguments"] == {"goal": "全马破4"}

    def test_multiple_decisions_appended_to_jsonl(
        self,
        decision_log_hook: DecisionLogHook,
        evolution_engine: EvolutionEngine,
        data_dir: Path,
        mock_context: MagicMock,
    ) -> None:
        """多次决策应追加到同一个JSONL文件"""
        # 第一次迭代
        run_async(decision_log_hook.before_iteration(mock_context))
        decision_log_hook.finalize_content(mock_context, "训练建议：轻松跑")

        # 第二次迭代
        run_async(decision_log_hook.before_iteration(mock_context))
        decision_log_hook.finalize_content(mock_context, "恢复建议：休息一天")

        # 验证: 通过Engine查询确认2条记录
        decisions = evolution_engine.get_decision_history(limit=10)
        assert len(decisions) == 2


# ---------------------------------------------------------------------------
# 场景2: DecisionLogHook与ObservabilityHook独立触发无冲突
# 两个Hook同时注册到CompositeHook，各自独立工作
# ---------------------------------------------------------------------------


class TestDecisionLogHookAndObservabilityHookIndependent:
    """测试DecisionLogHook与ObservabilityHook在CompositeHook中独立工作"""

    def test_both_hooks_work_independently(
        self,
        evolution_engine: EvolutionEngine,
        data_dir: Path,
        mock_context: MagicMock,
    ) -> None:
        """DecisionLogHook和ObservabilityHook同时注册时各自独立工作"""
        # 准备: 创建ObservabilityManager
        obs_manager = ObservabilityManager()

        # 准备: 创建组合Hook列表
        hooks = create_composite_hook(
            observability_manager=obs_manager,
            evolution_engine=evolution_engine,
            session_key="integration_test",
        )

        # 找到DecisionLogHook和ObservabilityHook
        decision_hook = None
        obs_hook = None
        for h in hooks:
            if isinstance(h, DecisionLogHook):
                decision_hook = h
            elif isinstance(h, ObservabilityHook):
                obs_hook = h

        assert decision_hook is not None, "应包含DecisionLogHook"
        assert obs_hook is not None, "应包含ObservabilityHook"

        # 执行: 模拟Agent迭代生命周期
        # 1. before_iteration
        run_async(obs_hook.before_iteration(mock_context))
        run_async(decision_hook.before_iteration(mock_context))

        # 2. before_execute_tools
        mock_tc = MagicMock()
        mock_tc.name = "get_vdot"
        mock_tc.arguments = {"days": 30}
        mock_tc.id = "tc_001"
        mock_context.tool_calls = [mock_tc]

        run_async(obs_hook.before_execute_tools(mock_context))
        run_async(decision_hook.before_execute_tools(mock_context))

        # 3. finalize_content
        content = "当前VDOT数据如下，建议轻松跑"
        # ObservabilityHook的finalize_content是async
        run_async(obs_hook.finalize_content(mock_context, content))
        # DecisionLogHook的finalize_content是sync
        decision_hook.finalize_content(mock_context, content)

        # 验证: DecisionLogHook产生了决策日志
        decisions = evolution_engine.get_decision_history(limit=10)
        assert len(decisions) >= 1
        # 内容包含"轻松跑"（TRAINING_ADVICE）和"VDOT"（DATA_QUERY），
        # TRAINING_ADVICE优先级高于DATA_QUERY，推断为TRAINING_ADVICE
        assert decisions[0].decision_type == DecisionType.TRAINING_ADVICE
        assert len(decisions[0].tool_call_chain) == 1

        # 验证: ObservabilityHook产生了追踪记录
        metrics = obs_manager.get_metrics()
        assert metrics.total_traces >= 1
        assert metrics.tool_call_count >= 1

    def test_no_state_interference_between_hooks(
        self,
        evolution_engine: EvolutionEngine,
        data_dir: Path,
        mock_context: MagicMock,
    ) -> None:
        """两个Hook之间不应有状态干扰"""
        obs_manager = ObservabilityManager()
        hooks = create_composite_hook(
            observability_manager=obs_manager,
            evolution_engine=evolution_engine,
            session_key="integration_test",
        )

        decision_hook = next(h for h in hooks if isinstance(h, DecisionLogHook))
        obs_hook = next(h for h in hooks if isinstance(h, ObservabilityHook))

        # 第一次迭代
        run_async(obs_hook.before_iteration(mock_context))
        run_async(decision_hook.before_iteration(mock_context))
        mock_tc = MagicMock()
        mock_tc.name = "get_vdot"
        mock_tc.arguments = {}
        mock_tc.id = "tc_001"
        mock_context.tool_calls = [mock_tc]
        run_async(obs_hook.before_execute_tools(mock_context))
        run_async(decision_hook.before_execute_tools(mock_context))
        run_async(obs_hook.finalize_content(mock_context, "VDOT数据"))
        decision_hook.finalize_content(mock_context, "VDOT数据")

        # 第二次迭代 - 验证状态已重置
        run_async(obs_hook.before_iteration(mock_context))
        run_async(decision_hook.before_iteration(mock_context))

        # DecisionLogHook状态应已重置
        assert decision_hook._tool_call_chain == []
        assert decision_hook._decision_logged is False

        # 两次决策都应被记录
        decisions = evolution_engine.get_decision_history(limit=10)
        # 第一次迭代记录了1条决策，第二次还没finalize所以只有1条
        assert len(decisions) == 1


# ---------------------------------------------------------------------------
# 场景3: check_plan_execution端到端
# DecisionLog -> OutcomeCollector.check_plan_execution -> OutcomeRecord -> EvolutionStore.save_outcome
# ---------------------------------------------------------------------------


class TestCheckPlanExecutionEndToEnd:
    """测试check_plan_execution的端到端流程"""

    def test_check_plan_execution_without_plan_adapter(
        self,
        evolution_engine: EvolutionEngine,
        outcome_collector: OutcomeCollector,
        evolution_store: EvolutionStore,
        data_dir: Path,
    ) -> None:
        """无plan_adapter时，check_plan_execution应创建fidelity为None的OutcomeRecord"""
        # 准备: 创建并记录决策
        decision = make_decision_log(decision_id="dec_plan001")
        evolution_engine.log_decision(decision)

        # 执行: check_plan_execution
        outcome = outcome_collector.check_plan_execution("dec_plan001")

        # 验证: OutcomeRecord已创建
        assert outcome is not None
        assert outcome.decision_id == "dec_plan001"
        assert outcome.execution_fidelity is None  # 无plan_adapter

        # 验证: OutcomeRecord可通过store查询
        outcomes = evolution_store.query_outcomes(decision_id="dec_plan001")
        assert len(outcomes) >= 1, "应创建outcomes记录"
        assert outcomes[0].decision_id == "dec_plan001"
        assert outcomes[0].execution_fidelity is None

    def test_check_plan_execution_with_plan_adapter(
        self,
        evolution_store: EvolutionStore,
        decision_logger: DecisionLogger,
        data_dir: Path,
    ) -> None:
        """有plan_adapter时，check_plan_execution应计算fidelity"""
        # 准备: 创建并记录决策（带plan_id）
        decision = make_decision_log(
            decision_id="dec_plan002",
            tool_call_chain=[
                {"name": "generate_plan", "arguments": {"plan_id": "plan_001"}}
            ],
        )
        decision_logger.log_decision(decision)

        # 准备: 创建PlanExecutionDataAdapter的测试实现
        class TestPlanAdapter(PlanExecutionDataAdapter):
            def __init__(self) -> None:
                super().__init__(plan_manager=None, execution_repo=None)

            def get_execution_data(self, plan_id: str) -> PlanExecutionData | None:
                if plan_id == "plan_001":
                    return PlanExecutionData(
                        planned_volume_km=40.0,
                        actual_volume_km=38.0,
                        planned_duration_min=300,
                        actual_duration_min=290,
                        completion_rate=0.95,
                    )
                return None

        # 创建带plan_adapter的OutcomeCollector
        collector = OutcomeCollector(
            store=evolution_store,
            decision_logger=decision_logger,
            plan_adapter=TestPlanAdapter(),
        )

        # 执行: check_plan_execution
        outcome = collector.check_plan_execution("dec_plan002")

        # 验证: fidelity已计算
        assert outcome is not None
        assert outcome.decision_id == "dec_plan002"
        assert outcome.execution_fidelity is not None
        assert 0.0 <= outcome.execution_fidelity <= 1.0

        # 验证: fidelity值与手动计算一致
        exec_data = PlanExecutionData(
            planned_volume_km=40.0,
            actual_volume_km=38.0,
            planned_duration_min=300,
            actual_duration_min=290,
            completion_rate=0.95,
        )
        expected_fidelity = calculate_fidelity(exec_data)
        assert abs(outcome.execution_fidelity - expected_fidelity) < 0.01

    def test_check_plan_execution_nonexistent_decision_raises(
        self,
        outcome_collector: OutcomeCollector,
    ) -> None:
        """决策不存在时check_plan_execution应抛出ValueError"""
        with pytest.raises(ValueError, match="决策不存在"):
            outcome_collector.check_plan_execution("dec_nonexistent")


# ---------------------------------------------------------------------------
# 场景4: DecisionLog与OutcomeRecord通过decision_id关联
# 创建决策 -> 记录反馈 -> 查询关联
# ---------------------------------------------------------------------------


class TestDecisionOutcomeAssociation:
    """测试DecisionLog与OutcomeRecord通过decision_id关联"""

    def test_decision_outcome_linked_by_decision_id(
        self,
        evolution_engine: EvolutionEngine,
        evolution_store: EvolutionStore,
    ) -> None:
        """决策和结果通过decision_id关联"""
        # 准备: 创建并记录决策
        decision = make_decision_log(
            decision_id="dec_link001",
            decision_type=DecisionType.RECOVERY_SUGGESTION,
            recommendation_text="建议休息一天",
        )
        evolution_engine.log_decision(decision)

        # 执行: 记录用户反馈
        outcome = evolution_engine.record_feedback(
            decision_id="dec_link001",
            score=4,
            text="建议不错，但可以更具体",
            accepted=True,
        )

        # 验证: OutcomeRecord的decision_id与DecisionLog一致
        assert outcome.decision_id == "dec_link001"
        assert outcome.user_feedback_score == 4
        assert outcome.user_feedback_text == "建议不错，但可以更具体"

        # 验证: 通过Store查询关联
        outcomes = evolution_store.query_outcomes(decision_id="dec_link001")
        assert len(outcomes) >= 1
        assert outcomes[0].decision_id == "dec_link001"

        # 验证: 通过Store的get_decision_outcome_pairs获取配对
        pairs = evolution_store.get_decision_outcome_pairs()
        linked = [p for p in pairs if p[0].decision_id == "dec_link001"]
        assert len(linked) >= 1
        decision_log, outcome_record = linked[0]
        assert decision_log.decision_id == outcome_record.decision_id
        assert decision_log.recommendation_text == "建议休息一天"
        assert outcome_record.user_feedback_score == 4

    def test_multiple_outcomes_for_same_decision(
        self,
        evolution_engine: EvolutionEngine,
        evolution_store: EvolutionStore,
    ) -> None:
        """同一决策可以有多条结果记录（反馈+执行检查+预测精度）"""
        # 准备: 创建决策（带prediction_snapshot）
        decision = make_decision_log(
            decision_id="dec_multi001",
            prediction_snapshot={"predicted_vdot": 45.0},
        )
        evolution_engine.log_decision(decision)

        # 执行1: 记录用户反馈
        feedback_outcome = evolution_engine.record_feedback(
            decision_id="dec_multi001",
            score=3,
            text="一般般",
        )

        # 执行2: 检查计划执行
        plan_outcome = evolution_engine.check_plan_execution("dec_multi001")

        # 执行3: 检查预测精度
        accuracy_outcome, stats = evolution_engine.check_prediction_accuracy(
            decision_id="dec_multi001",
            actual_vdot=43.5,
        )

        # 验证: 三条OutcomeRecord都关联到同一decision_id
        outcomes = evolution_store.query_outcomes(decision_id="dec_multi001", limit=10)
        assert len(outcomes) == 3

        for o in outcomes:
            assert o.decision_id == "dec_multi001"

        # 验证: 预测精度结果
        assert accuracy_outcome.prediction_error is not None
        assert accuracy_outcome.prediction_direction is not None
        # predicted=45.0, actual=43.5, 45.0 > 43.5*1.05=45.675? No, 45.0 < 45.675
        # 45.0 < 43.5*0.95=41.325? No, 所以direction应该是accurate
        assert accuracy_outcome.prediction_direction == "accurate"

    def test_decision_without_outcome(
        self,
        evolution_engine: EvolutionEngine,
        evolution_store: EvolutionStore,
    ) -> None:
        """只有决策没有结果时，get_decision_outcome_pairs不应返回该决策"""
        # 准备: 创建决策但不记录结果
        decision = make_decision_log(decision_id="dec_no_outcome")
        evolution_engine.log_decision(decision)

        # 验证: 决策存在
        found = evolution_engine.get_decision_history(limit=10)
        assert any(d.decision_id == "dec_no_outcome" for d in found)

        # 验证: 无配对结果
        pairs = evolution_store.get_decision_outcome_pairs()
        linked = [p for p in pairs if p[0].decision_id == "dec_no_outcome"]
        assert len(linked) == 0


# ---------------------------------------------------------------------------
# 场景5: EvolutionEngine全流程
# log_decision -> record_feedback -> get_decision_history -> get_evolution_status
# ---------------------------------------------------------------------------


class TestEvolutionEngineFullFlow:
    """测试EvolutionEngine全流程"""

    def test_full_lifecycle(
        self,
        evolution_engine: EvolutionEngine,
        data_dir: Path,
    ) -> None:
        """完整生命周期: log_decision -> record_feedback -> get_decision_history -> get_evolution_status"""
        # 1. 记录决策
        decision1 = make_decision_log(
            decision_id="dec_flow001",
            decision_type=DecisionType.TRAINING_ADVICE,
            recommendation_text="建议轻松跑5公里",
        )
        decision_id_1 = evolution_engine.log_decision(decision1)
        assert decision_id_1 == "dec_flow001"

        decision2 = make_decision_log(
            decision_id="dec_flow002",
            decision_type=DecisionType.RECOVERY_SUGGESTION,
            recommendation_text="建议休息恢复",
        )
        decision_id_2 = evolution_engine.log_decision(decision2)
        assert decision_id_2 == "dec_flow002"

        # 2. 记录反馈
        outcome1 = evolution_engine.record_feedback(
            decision_id="dec_flow001",
            score=5,
            text="很好的建议",
            accepted=True,
        )
        assert outcome1.user_feedback_score == 5
        assert outcome1.user_feedback_text == "很好的建议"

        outcome2 = evolution_engine.record_feedback(
            decision_id="dec_flow002",
            score=2,
            text="不太需要休息",
            accepted=False,
        )
        assert outcome2.user_feedback_score == 2

        # 3. 查询决策历史
        history = evolution_engine.get_decision_history(limit=10)
        assert len(history) == 2
        # 按时间倒序
        assert history[0].decision_id in ("dec_flow001", "dec_flow002")
        assert history[1].decision_id in ("dec_flow001", "dec_flow002")

        # 按决策类型过滤
        training_decisions = evolution_engine.get_decision_history(
            decision_type=DecisionType.TRAINING_ADVICE
        )
        assert len(training_decisions) == 1
        assert training_decisions[0].decision_id == "dec_flow001"

        # 4. 获取进化状态
        status = evolution_engine.get_evolution_status()
        assert status["total_decisions"] == 2
        assert "status_distribution" in status
        assert "type_distribution" in status
        assert status["status_distribution"]["pending"] == 2
        assert status["type_distribution"]["training_advice"] == 1
        assert status["type_distribution"]["recovery_suggestion"] == 1

    def test_full_flow_with_prediction_accuracy(
        self,
        evolution_engine: EvolutionEngine,
        data_dir: Path,
    ) -> None:
        """完整流程包含预测精度检查"""
        # 1. 记录带预测快照的决策
        decision = make_decision_log(
            decision_id="dec_pred001",
            prediction_snapshot={"predicted_vdot": 50.0},
        )
        evolution_engine.log_decision(decision)

        # 2. 检查预测精度
        outcome, stats = evolution_engine.check_prediction_accuracy(
            decision_id="dec_pred001",
            actual_vdot=46.0,
        )

        # 验证: 预测误差已计算
        assert outcome.prediction_error is not None
        assert outcome.prediction_error > 0
        # predicted=50.0, actual=46.0, 50.0 > 46.0*1.05=48.3 → overestimate
        assert outcome.prediction_direction == "overestimate"
        assert outcome.actual_vdot == 46.0

        # 验证: 精度统计
        assert stats.total_pairs >= 1
        assert stats.mae > 0

    def test_full_flow_with_check_plan_execution(
        self,
        evolution_engine: EvolutionEngine,
        data_dir: Path,
    ) -> None:
        """完整流程包含计划执行检查"""
        # 1. 记录决策
        decision = make_decision_log(
            decision_id="dec_exec001",
            tool_call_chain=[
                {"name": "generate_plan", "args": {"plan_id": "plan_exec"}}
            ],
        )
        evolution_engine.log_decision(decision)

        # 2. 检查计划执行（无plan_adapter，fidelity为None）
        outcome = evolution_engine.check_plan_execution("dec_exec001")

        assert outcome.decision_id == "dec_exec001"
        assert outcome.execution_fidelity is None

    def test_generate_feedback_prompt(
        self,
        evolution_engine: EvolutionEngine,
    ) -> None:
        """生成反馈提示应返回有效的ConfirmPrompt"""
        # 准备: 记录决策
        decision = make_decision_log(
            decision_id="dec_prompt001",
            recommendation_text="建议轻松跑5公里",
        )
        evolution_engine.log_decision(decision)

        # 执行: 生成反馈提示
        prompt = evolution_engine.generate_feedback_prompt("dec_prompt001")

        # 验证: 提示内容
        assert prompt.title == "决策反馈"
        assert "dec_prompt001" in prompt.message
        assert "建议轻松跑5公里" in prompt.message
        assert len(prompt.options) == 5  # 1-5分

    def test_decision_history_with_date_filter(
        self,
        evolution_engine: EvolutionEngine,
    ) -> None:
        """决策历史查询支持日期过滤"""
        # 记录决策
        decision = make_decision_log(decision_id="dec_date001")
        evolution_engine.log_decision(decision)

        # 使用当前时间范围查询
        now = datetime.now()
        from datetime import timedelta

        # 宽范围查询应能找到
        history = evolution_engine.get_decision_history(
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=1),
        )
        assert len(history) >= 1

        # 窄范围查询（未来）应找不到
        future_history = evolution_engine.get_decision_history(
            start_date=now + timedelta(days=365),
        )
        assert len(future_history) == 0
