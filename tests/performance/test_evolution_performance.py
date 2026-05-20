# 决策追踪模块性能测试
# 验证DecisionLogHook和EvolutionStore各操作的性能阈值
# 使用time.perf_counter()高精度计时

from __future__ import annotations

import asyncio
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from nanobot.agent.hook import AgentHookContext

from src.core.evolution.config import EvolutionConfig
from src.core.evolution.decision_log_hook import DecisionLogHook
from src.core.evolution.decision_logger import DecisionLogger
from src.core.evolution.evolution_engine import EvolutionEngine
from src.core.evolution.evolution_store import EvolutionStore
from src.core.evolution.models import DecisionLog
from src.core.evolution.outcome_collector import OutcomeCollector
from src.core.transparency.models import DecisionType

# ---------------------------------------------------------------------------
# 辅助函数
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


def _make_mock_context(tool_calls: list[Any] | None = None) -> MagicMock:
    """创建模拟的AgentHookContext"""
    ctx = MagicMock(spec=AgentHookContext)
    ctx.iteration = 1
    ctx.messages = []
    ctx.tool_calls = tool_calls or []
    ctx.tool_results = []
    ctx.final_content = None
    ctx.error = None
    return ctx


def _make_mock_tool_call(
    name: str = "get_vdot", arguments: dict | None = None
) -> MagicMock:
    """创建模拟的工具调用对象"""
    tc = MagicMock()
    tc.name = name
    tc.arguments = arguments or {}
    tc.id = f"tc_{uuid.uuid4().hex[:8]}"
    return tc


def _make_engine(data_dir: Path) -> EvolutionEngine:
    """创建测试用的EvolutionEngine（依赖注入模式）"""
    store = EvolutionStore(data_dir=data_dir)
    config = EvolutionConfig()
    decision_logger = DecisionLogger(store=store, config=config)
    outcome_collector = OutcomeCollector(decision_logger=decision_logger, store=store)
    return EvolutionEngine(
        decision_logger=decision_logger, outcome_collector=outcome_collector
    )


def _make_decision_log(
    timestamp: datetime, session_key: str = "perf_test"
) -> DecisionLog:
    """创建测试用DecisionLog"""
    return DecisionLog(
        decision_id=f"dec_{uuid.uuid4().hex[:8]}",
        timestamp=timestamp,
        runner_state={
            "vdot": None,
            "ctl": None,
            "atl": None,
            "tsb": None,
            "fatigue_score": None,
        },
        decision_type=DecisionType.TRAINING_ADVICE,
        tool_call_chain=[{"id": "tc_001", "name": "get_vdot", "arguments": {}}],
        prediction_snapshot=None,
        recommendation_text="建议进行轻松跑训练",
        execution_status="pending",
        recommendation_accepted=None,
        session_key=session_key,
    )


# ---------------------------------------------------------------------------
# 性能阈值常量（单位：秒）
# ---------------------------------------------------------------------------

# Hook方法延迟阈值
BEFORE_ITERATION_THRESHOLD = 0.050  # <50ms
BEFORE_EXECUTE_TOOLS_THRESHOLD = 0.010  # <10ms
FINALIZE_CONTENT_THRESHOLD = 0.100  # <100ms（含log_decision同步写入）

# 同步写入延迟阈值
SAVE_DECISION_THRESHOLD = 0.050  # <50ms

# 1年范围查询阈值
QUERY_ONE_YEAR_THRESHOLD = 2.0  # <2秒

# Hook开销对比阈值
HOOK_OVERHEAD_THRESHOLD = 0.100  # <100ms差异

# 迭代次数
ITERATIONS = 100


# ---------------------------------------------------------------------------
# 测试类
# ---------------------------------------------------------------------------


class TestBeforeIterationPerformance:
    """before_iteration性能测试"""

    def test_before_iteration_average_latency(self, tmp_path: Path) -> None:
        """before_iteration平均延迟应小于50ms

        创建DecisionLogHook，调用before_iteration 100次，
        测量平均耗时并断言小于阈值。
        """
        engine = _make_engine(data_dir=tmp_path)
        hook = DecisionLogHook(evolution_engine=engine, session_key="perf_test")
        mock_context = _make_mock_context()

        # 预热：消除首次调用的冷启动影响
        for _ in range(5):
            run_async(hook.before_iteration(mock_context))

        # 正式测量
        latencies: list[float] = []
        for _ in range(ITERATIONS):
            start = time.perf_counter()
            run_async(hook.before_iteration(mock_context))
            elapsed = time.perf_counter() - start
            latencies.append(elapsed)

        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)

        print(f"before_iteration 平均延迟: {avg_latency * 1000:.3f}ms")
        print(f"before_iteration 最大延迟: {max_latency * 1000:.3f}ms")

        assert avg_latency < BEFORE_ITERATION_THRESHOLD, (
            f"before_iteration平均延迟 {avg_latency * 1000:.3f}ms "
            f"超过阈值 {BEFORE_ITERATION_THRESHOLD * 1000:.1f}ms"
        )


class TestBeforeExecuteToolsPerformance:
    """before_execute_tools性能测试"""

    def test_before_execute_tools_average_latency(self, tmp_path: Path) -> None:
        """before_execute_tools平均延迟应小于10ms

        创建DecisionLogHook，调用before_execute_tools 100次，
        测量平均耗时并断言小于阈值。
        """
        engine = _make_engine(data_dir=tmp_path)
        hook = DecisionLogHook(evolution_engine=engine, session_key="perf_test")

        # 模拟3个工具调用
        tool_calls = [
            _make_mock_tool_call("get_vdot", {"days": 30}),
            _make_mock_tool_call("get_training_load", {}),
            _make_mock_tool_call("generate_training_plan", {"goal": "全马破4"}),
        ]
        mock_context = _make_mock_context(tool_calls=tool_calls)

        # 预热
        for _ in range(5):
            run_async(hook.before_iteration(mock_context))
            run_async(hook.before_execute_tools(mock_context))

        # 正式测量
        latencies: list[float] = []
        for _ in range(ITERATIONS):
            # 每次迭代前重置状态
            run_async(hook.before_iteration(mock_context))

            start = time.perf_counter()
            run_async(hook.before_execute_tools(mock_context))
            elapsed = time.perf_counter() - start
            latencies.append(elapsed)

        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)

        print(f"before_execute_tools 平均延迟: {avg_latency * 1000:.3f}ms")
        print(f"before_execute_tools 最大延迟: {max_latency * 1000:.3f}ms")

        assert avg_latency < BEFORE_EXECUTE_TOOLS_THRESHOLD, (
            f"before_execute_tools平均延迟 {avg_latency * 1000:.3f}ms "
            f"超过阈值 {BEFORE_EXECUTE_TOOLS_THRESHOLD * 1000:.1f}ms"
        )


class TestFinalizeContentPerformance:
    """finalize_content性能测试"""

    def test_finalize_content_average_latency(self, tmp_path: Path) -> None:
        """finalize_content平均延迟应小于100ms（含log_decision同步写入）

        创建DecisionLogHook，调用finalize_content 100次，
        测量平均耗时并断言小于阈值。
        """
        engine = _make_engine(data_dir=tmp_path)
        hook = DecisionLogHook(evolution_engine=engine, session_key="perf_test")
        mock_context = _make_mock_context()

        # 预热
        for _ in range(5):
            run_async(hook.before_iteration(mock_context))
            hook.finalize_content(mock_context, "建议进行轻松跑训练")

        # 正式测量
        latencies: list[float] = []
        for _ in range(ITERATIONS):
            # 每次迭代前重置状态（模拟真实迭代周期）
            run_async(hook.before_iteration(mock_context))

            start = time.perf_counter()
            hook.finalize_content(mock_context, "建议进行轻松跑训练")
            elapsed = time.perf_counter() - start
            latencies.append(elapsed)

        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)

        print(f"finalize_content 平均延迟: {avg_latency * 1000:.3f}ms")
        print(f"finalize_content 最大延迟: {max_latency * 1000:.3f}ms")

        assert avg_latency < FINALIZE_CONTENT_THRESHOLD, (
            f"finalize_content平均延迟 {avg_latency * 1000:.3f}ms "
            f"超过阈值 {FINALIZE_CONTENT_THRESHOLD * 1000:.1f}ms"
        )


class TestSaveDecisionPerformance:
    """EvolutionStore.save_decision同步写入性能测试"""

    def test_save_decision_average_latency(self, tmp_path: Path) -> None:
        """save_decision平均延迟应小于50ms

        调用EvolutionStore.save_decision 100次，
        测量平均耗时并断言小于阈值。
        """
        store = EvolutionStore(data_dir=tmp_path)

        # 预热：首次写入需创建目录
        warmup_decision = _make_decision_log(datetime.now())
        store.save_decision(warmup_decision)

        # 正式测量
        latencies: list[float] = []
        base_time = datetime.now()

        for i in range(ITERATIONS):
            decision = _make_decision_log(
                timestamp=base_time + timedelta(seconds=i),
                session_key=f"perf_test_{i}",
            )

            start = time.perf_counter()
            store.save_decision(decision)
            elapsed = time.perf_counter() - start
            latencies.append(elapsed)

        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)

        print(f"save_decision 平均延迟: {avg_latency * 1000:.3f}ms")
        print(f"save_decision 最大延迟: {max_latency * 1000:.3f}ms")

        assert avg_latency < SAVE_DECISION_THRESHOLD, (
            f"save_decision平均延迟 {avg_latency * 1000:.3f}ms "
            f"超过阈值 {SAVE_DECISION_THRESHOLD * 1000:.1f}ms"
        )


class TestQueryOneYearPerformance:
    """1年范围查询性能测试"""

    def test_query_one_year_range(self, tmp_path: Path) -> None:
        """1年范围查询应小于2秒

        插入365条决策记录（每天1条），查询1年范围，
        测量耗时并断言小于阈值。
        """
        store = EvolutionStore(data_dir=tmp_path)

        # 插入365条决策记录（每天1条，跨12个月分片）
        base_date = datetime(2025, 1, 1)
        for i in range(365):
            decision = _make_decision_log(
                timestamp=base_date + timedelta(days=i),
                session_key=f"perf_test_{i}",
            )
            store.save_decision(decision)

        # 预热查询
        store.query_decisions(
            start_date=base_date,
            end_date=base_date + timedelta(days=365),
            limit=365,
        )

        # 正式测量
        start = time.perf_counter()
        results = store.query_decisions(
            start_date=base_date,
            end_date=base_date + timedelta(days=365),
            limit=365,
        )
        elapsed = time.perf_counter() - start

        print(f"1年范围查询耗时: {elapsed:.3f}秒")
        print(f"查询结果数量: {len(results)}")

        assert elapsed < QUERY_ONE_YEAR_THRESHOLD, (
            f"1年范围查询耗时 {elapsed:.3f}秒 超过阈值 {QUERY_ONE_YEAR_THRESHOLD:.1f}秒"
        )
        assert len(results) == 365, f"预期365条结果，实际{len(results)}条"


class TestHookOverheadComparison:
    """Hook开销对比测试"""

    def test_finalize_content_hook_overhead(self, tmp_path: Path) -> None:
        """有/无DecisionLogHook时finalize_content耗时差异应小于100ms

        对比两种场景下finalize_content的耗时差异：
        1. 有DecisionLogHook：完整执行决策类型推断、DecisionLog创建、log_decision持久化
        2. 无DecisionLogHook：仅执行一个空操作finalize_content（基线）

        差异应小于100ms，说明Hook引入的开销在可接受范围内。
        """
        engine = _make_engine(data_dir=tmp_path)
        hook = DecisionLogHook(evolution_engine=engine, session_key="perf_test")
        mock_context = _make_mock_context()

        # ---- 场景1：有DecisionLogHook ----
        # 预热
        for _ in range(5):
            run_async(hook.before_iteration(mock_context))
            hook.finalize_content(mock_context, "建议进行轻松跑训练")

        # 正式测量
        latencies_with_hook: list[float] = []
        for _ in range(ITERATIONS):
            run_async(hook.before_iteration(mock_context))

            start = time.perf_counter()
            hook.finalize_content(mock_context, "建议进行轻松跑训练")
            elapsed = time.perf_counter() - start
            latencies_with_hook.append(elapsed)

        avg_with_hook = sum(latencies_with_hook) / len(latencies_with_hook)

        # ---- 场景2：无DecisionLogHook（基线） ----
        # 模拟一个最小化的finalize_content操作：仅返回content
        # 这代表了没有Hook时的开销基线

        def baseline_finalize(content: str | None) -> str | None:
            """基线finalize_content：仅返回content，无任何处理"""
            return content

        # 预热
        for _ in range(5):
            baseline_finalize("建议进行轻松跑训练")

        # 正式测量
        latencies_baseline: list[float] = []
        for _ in range(ITERATIONS):
            start = time.perf_counter()
            baseline_finalize("建议进行轻松跑训练")
            elapsed = time.perf_counter() - start
            latencies_baseline.append(elapsed)

        avg_baseline = sum(latencies_baseline) / len(latencies_baseline)

        # 计算Hook引入的开销
        overhead = avg_with_hook - avg_baseline

        print(f"有Hook的finalize_content平均延迟: {avg_with_hook * 1000:.3f}ms")
        print(f"无Hook基线平均延迟: {avg_baseline * 1000:.3f}ms")
        print(f"Hook引入的开销: {overhead * 1000:.3f}ms")

        assert overhead < HOOK_OVERHEAD_THRESHOLD, (
            f"Hook开销 {overhead * 1000:.3f}ms "
            f"超过阈值 {HOOK_OVERHEAD_THRESHOLD * 1000:.1f}ms"
        )
