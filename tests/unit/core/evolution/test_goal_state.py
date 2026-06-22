# GoalState 集成测试
# 测试 DecisionLogHook 从 context.metadata 读取 goal_state 并写入 DecisionLog

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
    dir_path = Path(tempfile.mkdtemp())
    yield dir_path
    if dir_path.exists():
        shutil.rmtree(dir_path)


@pytest.fixture
def engine(temp_dir: Path) -> EvolutionEngine:
    store = EvolutionStore(temp_dir)
    decision_logger = DecisionLogger(store)
    outcome_collector = OutcomeCollector(store, decision_logger)
    return EvolutionEngine(
        decision_logger=decision_logger,
        outcome_collector=outcome_collector,
    )


@pytest.fixture
def hook(engine: EvolutionEngine) -> DecisionLogHook:
    return DecisionLogHook(evolution_engine=engine, session_key="test_goal_state")


@pytest.fixture
def mock_context() -> MagicMock:
    ctx = MagicMock(spec=AgentHookContext)
    ctx.iteration = 1
    ctx.messages = []
    ctx.tool_calls = []
    ctx.tool_results = []
    ctx.final_content = None
    ctx.error = None
    ctx.metadata = {}
    return ctx


class TestGoalStateIntegration:
    """GoalState 集成测试"""

    def test_after_iteration_reads_goal_state_from_metadata(
        self, hook: DecisionLogHook, engine: EvolutionEngine, mock_context: MagicMock
    ) -> None:
        """after_iteration 应从 context.metadata 读取 goal_state"""
        mock_context.metadata = {"goal_state": "全马破4"}
        hook.finalize_content(mock_context, "以下是训练建议")
        run_async(hook.after_iteration(mock_context))

        decisions = engine.get_decision_history(limit=10)
        assert len(decisions) >= 1
        assert decisions[0].goal_state == "全马破4"

    def test_after_iteration_no_goal_state_in_metadata(
        self, hook: DecisionLogHook, engine: EvolutionEngine, mock_context: MagicMock
    ) -> None:
        """metadata 中无 goal_state 时 DecisionLog.goal_state 应为 None"""
        mock_context.metadata = {}
        hook.finalize_content(mock_context, "以下是训练建议")
        run_async(hook.after_iteration(mock_context))

        decisions = engine.get_decision_history(limit=10)
        assert len(decisions) >= 1
        assert decisions[0].goal_state is None

    def test_goal_state_raw_helper(self, hook: DecisionLogHook) -> None:
        """goal_state_raw 辅助方法应正确提取 metadata 中的 goal_state"""
        metadata = {"goal_state": "半马PB130"}
        result = hook.goal_state_raw(metadata)
        assert result == "半马PB130"

    def test_goal_state_raw_empty_metadata(self, hook: DecisionLogHook) -> None:
        """goal_state_raw 在 metadata 为空时返回 None"""
        result = hook.goal_state_raw({})
        assert result is None

    def test_goal_state_raw_none_metadata(self, hook: DecisionLogHook) -> None:
        """goal_state_raw 在 metadata 为 None 时返回 None"""
        result = hook.goal_state_raw(None)
        assert result is None
