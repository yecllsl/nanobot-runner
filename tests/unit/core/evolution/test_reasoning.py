# 推理可见化单元测试
# 测试DecisionLogHook的emit_reasoning/emit_reasoning_end/_build_reasoning_snapshot
# v0.26: 适配nanobot-ai 0.2.0推理可见化回调（ADR-013）

from __future__ import annotations

import asyncio
import shutil
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from nanobot.agent.hook import AgentHookContext

from src.core.evolution.decision_log_hook import DecisionLogHook
from src.core.evolution.decision_logger import DecisionLogger
from src.core.evolution.evolution_engine import EvolutionEngine
from src.core.evolution.evolution_store import EvolutionStore
from src.core.evolution.outcome_collector import OutcomeCollector


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
    store = EvolutionStore(temp_dir)
    decision_logger = DecisionLogger(store)
    outcome_collector = OutcomeCollector(store, decision_logger)
    return EvolutionEngine(
        decision_logger=decision_logger,
        outcome_collector=outcome_collector,
    )


@pytest.fixture
def hook(engine: EvolutionEngine) -> DecisionLogHook:
    """创建DecisionLogHook实例"""
    return DecisionLogHook(evolution_engine=engine, session_key="test_reasoning")


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
    ctx.metadata = {}
    return ctx


class TestReasoningVisualization:
    """推理可见化测试"""

    def test_emit_reasoning_appends_to_buffer(
        self, hook: DecisionLogHook, mock_context: MagicMock
    ) -> None:
        """emit_reasoning 应将推理片段追加到缓冲区"""
        hook.emit_reasoning(mock_context, "分析用户VDOT趋势...")
        hook.emit_reasoning(mock_context, "VDOT呈上升趋势，建议增加训练量")
        assert len(hook._reasoning_buffer) == 2
        assert hook._reasoning_buffer[0] == "分析用户VDOT趋势..."
        assert hook._reasoning_buffer[1] == "VDOT呈上升趋势，建议增加训练量"

    def test_emit_reasoning_end_marks_completion(
        self, hook: DecisionLogHook, mock_context: MagicMock
    ) -> None:
        """emit_reasoning_end 应标记推理结束"""
        hook.emit_reasoning(mock_context, "推理片段")
        hook.emit_reasoning_end(mock_context)
        assert hook._reasoning_complete is True

    def test_finalize_content_includes_reasoning_snapshot(
        self, hook: DecisionLogHook, engine: EvolutionEngine, mock_context: MagicMock
    ) -> None:
        """finalize_content 应将推理缓冲区写入 DecisionLog 上下文快照"""
        hook.emit_reasoning(mock_context, "第一步推理")
        hook.emit_reasoning(mock_context, "第二步推理")
        hook.emit_reasoning_end(mock_context)

        hook.finalize_content(mock_context, "以下是训练建议")

        decisions = engine.get_decision_history(limit=10)
        assert len(decisions) >= 1
        snapshot = decisions[0].prediction_snapshot
        assert snapshot is not None
        assert "reasoning" in snapshot
        assert snapshot["reasoning"] == "第一步推理\n第二步推理"

    def test_finalize_content_without_reasoning(
        self, hook: DecisionLogHook, engine: EvolutionEngine, mock_context: MagicMock
    ) -> None:
        """无推理时 prediction_snapshot 保持 None"""
        hook.finalize_content(mock_context, "以下是训练建议")

        decisions = engine.get_decision_history(limit=10)
        assert len(decisions) >= 1
        assert decisions[0].prediction_snapshot is None

    def test_reasoning_buffer_cleared_after_finalize(
        self, hook: DecisionLogHook, engine: EvolutionEngine, mock_context: MagicMock
    ) -> None:
        """finalize_content 后推理缓冲区应被清空"""
        hook.emit_reasoning(mock_context, "推理内容")
        hook.emit_reasoning_end(mock_context)
        hook.finalize_content(mock_context, "训练建议")

        assert hook._reasoning_buffer == []
        assert hook._reasoning_complete is False

    def test_before_iteration_resets_reasoning_state(
        self, hook: DecisionLogHook, mock_context: MagicMock
    ) -> None:
        """before_iteration 应重置推理状态"""
        hook.emit_reasoning(mock_context, "推理")
        hook.emit_reasoning_end(mock_context)

        run_async(hook.before_iteration(mock_context))

        assert hook._reasoning_buffer == []
        assert hook._reasoning_complete is False
