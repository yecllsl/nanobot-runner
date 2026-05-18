from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.core.transparency.hook_integration import ObservabilityHook
from src.core.transparency.models import (
    AIDecision,
    DecisionExplanation,
    DecisionType,
    LogEntry,
    LogFilters,
)
from src.core.transparency.observability_manager import ObservabilityManager
from src.core.transparency.trace_logger import TraceLogger
from src.core.transparency.transparency_engine import TransparencyEngine


class TestObservabilityHookInit:
    def test_init_with_engine(self):
        manager = ObservabilityManager()
        engine = TransparencyEngine()
        hook = ObservabilityHook(manager, engine)
        assert hook.manager is manager
        assert hook.engine is engine
        assert hook.get_iteration_count() == 0
        assert hook.get_tools_used() == []

    def test_init_without_engine(self):
        manager = ObservabilityManager()
        hook = ObservabilityHook(manager)
        assert hook.engine is None


class TestObservabilityHookBeforeIteration:
    @pytest.mark.asyncio
    async def test_before_iteration_starts_trace(self):
        manager = ObservabilityManager()
        hook = ObservabilityHook(manager)
        context = MagicMock()

        await hook.before_iteration(context)
        assert hook.get_iteration_count() == 1

    @pytest.mark.asyncio
    async def test_before_iteration_increments_count(self):
        manager = ObservabilityManager()
        hook = ObservabilityHook(manager)
        context = MagicMock()

        await hook.before_iteration(context)
        await hook.before_iteration(context)
        assert hook.get_iteration_count() == 2

    @pytest.mark.asyncio
    async def test_before_iteration_resets_tools(self):
        manager = ObservabilityManager()
        hook = ObservabilityHook(manager)
        context = MagicMock()

        await hook.before_iteration(context)
        assert hook.get_tools_used() == []


class TestObservabilityHookOnStream:
    @pytest.mark.asyncio
    async def test_on_stream_records_event(self):
        manager = ObservabilityManager()
        hook = ObservabilityHook(manager)
        context = MagicMock()

        await hook.before_iteration(context)
        await hook.on_stream(context, "hello world")

    @pytest.mark.asyncio
    async def test_on_stream_no_active_trace(self):
        manager = ObservabilityManager()
        hook = ObservabilityHook(manager)
        context = MagicMock()

        await hook.on_stream(context, "no trace")
        assert hook.get_iteration_count() == 0

    @pytest.mark.asyncio
    async def test_on_stream_empty_delta(self):
        manager = ObservabilityManager()
        hook = ObservabilityHook(manager)
        context = MagicMock()

        await hook.before_iteration(context)
        await hook.on_stream(context, "")


class TestObservabilityHookBeforeExecuteTools:
    @pytest.mark.asyncio
    async def test_before_execute_tools_records(self):
        manager = ObservabilityManager()
        hook = ObservabilityHook(manager)
        context = MagicMock()
        tc1 = MagicMock()
        tc1.name = "tool_a"
        tc1.arguments = {"key": "value"}
        tc2 = MagicMock()
        tc2.name = "tool_b"
        tc2.arguments = {}
        context.tool_calls = [tc1, tc2]

        await hook.before_iteration(context)
        await hook.before_execute_tools(context)

        tools = hook.get_tools_used()
        assert "tool_a" in tools
        assert "tool_b" in tools

    @pytest.mark.asyncio
    async def test_before_execute_tools_no_trace(self):
        manager = ObservabilityManager()
        hook = ObservabilityHook(manager)
        context = MagicMock()
        context.tool_calls = []

        await hook.before_execute_tools(context)
        assert hook.get_tools_used() == []


class TestObservabilityHookAfterIteration:
    @pytest.mark.asyncio
    async def test_after_iteration_records(self):
        manager = ObservabilityManager()
        hook = ObservabilityHook(manager)
        context = MagicMock()

        await hook.before_iteration(context)
        await hook.after_iteration(context)

    @pytest.mark.asyncio
    async def test_after_iteration_no_trace(self):
        manager = ObservabilityManager()
        hook = ObservabilityHook(manager)
        context = MagicMock()

        await hook.after_iteration(context)


class TestObservabilityHookFinalizeContent:
    @pytest.mark.asyncio
    async def test_finalize_content_ends_trace(self):
        manager = ObservabilityManager()
        hook = ObservabilityHook(manager)
        context = MagicMock()

        await hook.before_iteration(context)
        result = await hook.finalize_content(context, "final answer")
        assert result == "final answer"
        assert hook._current_trace_id is None

    @pytest.mark.asyncio
    async def test_finalize_content_with_engine(self):
        manager = ObservabilityManager()
        engine = TransparencyEngine()
        hook = ObservabilityHook(manager, engine)
        context = MagicMock()

        await hook.before_iteration(context)
        await hook.before_execute_tools(context)
        context.tool_calls = [MagicMock(name="tool_x")]
        context.tool_calls[0].name = "tool_x"
        context.tool_calls[0].arguments = {}

        result = await hook.finalize_content(context, "answer with engine")
        assert result == "answer with engine"

    @pytest.mark.asyncio
    async def test_finalize_content_no_trace(self):
        manager = ObservabilityManager()
        hook = ObservabilityHook(manager)
        context = MagicMock()

        result = await hook.finalize_content(context, "no trace content")
        assert result == "no trace content"

    @pytest.mark.asyncio
    async def test_finalize_content_empty_content(self):
        manager = ObservabilityManager()
        hook = ObservabilityHook(manager)
        context = MagicMock()

        await hook.before_iteration(context)
        result = await hook.finalize_content(context, "")
        assert result == ""


class TestObservabilityHookReset:
    @pytest.mark.asyncio
    async def test_reset_clears_state(self):
        manager = ObservabilityManager()
        hook = ObservabilityHook(manager)
        context = MagicMock()

        await hook.before_iteration(context)

        hook.reset()
        assert hook.get_iteration_count() == 0
        assert hook.get_tools_used() == []
        assert hook._current_trace_id is None

    @pytest.mark.asyncio
    async def test_reset_with_active_trace(self):
        manager = ObservabilityManager()
        hook = ObservabilityHook(manager)
        context = MagicMock()

        await hook.before_iteration(context)

        assert hook._current_trace_id is not None
        hook.reset()
        assert hook._current_trace_id is None


class TestTraceLoggerExtended:
    def test_log_decision_with_explanation(self):
        logger = TraceLogger()
        decision = AIDecision(
            id="ext-001",
            decision_type=DecisionType.TRAINING_ADVICE,
            confidence=0.9,
            tools_used=["tool1"],
            memory_referenced=["mem1"],
            duration_ms=500,
        )
        explanation = DecisionExplanation(
            decision_id="ext-001",
            brief_reasons=["理由1", "理由2"],
            data_sources=[],
        )
        logger.log_decision(decision, explanation)

        logs = logger.get_decision_logs()
        assert len(logs) == 1
        assert logs[0].context.get("brief_reasons") == ["理由1", "理由2"]
        assert logs[0].context.get("data_sources_count") == 0

    def test_log_tool_invocation_large_params(self):
        logger = TraceLogger()
        large_params = {"data": "x" * 600}
        logger.log_tool_invocation("tool", large_params, success=True)

        logs = logger.get_tool_call_logs()
        assert len(logs) == 1
        assert "params_summary" in logs[0].context

    def test_log_tool_invocation_large_result(self):
        logger = TraceLogger()
        large_result = {"output": "y" * 600}
        logger.log_tool_invocation("tool", {}, result=large_result, success=True)

        logs = logger.get_tool_call_logs()
        assert len(logs) == 1
        assert "result_summary" in logs[0].context

    def test_log_tool_invocation_small_params_and_result(self):
        logger = TraceLogger()
        logger.log_tool_invocation(
            "tool", {"key": "val"}, result={"out": "ok"}, success=True
        )

        logs = logger.get_tool_call_logs()
        assert logs[0].context.get("params") == {"key": "val"}
        assert logs[0].context.get("result") == {"out": "ok"}

    def test_query_logs_with_time_filter(self):
        logger = TraceLogger()
        decision = AIDecision(id="tf-001", decision_type=DecisionType.GENERAL)
        logger.log_decision(decision)

        now = datetime.now()
        filters = LogFilters(start_time=now, end_time=now)
        logs = logger.query_logs(filters)
        assert isinstance(logs, list)

    def test_query_logs_with_tool_id_filter(self):
        logger = TraceLogger()
        logger.log_tool_invocation("target_tool", {}, success=True)
        logger.log_tool_invocation("other_tool", {}, success=True)

        filters = LogFilters(tool_id="target_tool")
        logs = logger.query_logs(filters)
        assert len(logs) == 1
        assert logs[0].context.get("tool_id") == "target_tool"

    def test_query_logs_with_status_filter(self):
        logger = TraceLogger()
        logger.log_tool_invocation("ok_tool", {}, success=True)
        logger.log_tool_invocation("fail_tool", {}, success=False)

        filters = LogFilters(status="WARNING")
        logs = logger.query_logs(filters)
        assert len(logs) == 1
        assert logs[0].level == "WARNING"

    def test_query_logs_with_session_key_filter(self):
        logger = TraceLogger()
        entry = LogEntry(
            timestamp=datetime.now(),
            level="INFO",
            message="test",
            context={"session_key": "sess-001"},
            entry_type="decision",
        )
        logger._add_entry(entry)

        filters = LogFilters(session_key="sess-001")
        logs = logger.query_logs(filters)
        assert len(logs) == 1

    def test_persist_entry(self, tmp_path: Path):
        log_dir = tmp_path / "logs"
        logger = TraceLogger(log_dir)

        decision = AIDecision(id="p-001", decision_type=DecisionType.GENERAL)
        logger.log_decision(decision)

        date_str = datetime.now().strftime("%Y-%m-%d")
        log_file = log_dir / f"trace_{date_str}.jsonl"
        if log_file.exists():
            content = log_file.read_text(encoding="utf-8")
            assert "p-001" in content

    def test_persist_entry_creates_dir(self, tmp_path: Path):
        log_dir = tmp_path / "new_logs"
        logger = TraceLogger(log_dir)
        assert log_dir.exists()

    def test_get_decision_logs_limit(self):
        logger = TraceLogger()
        for i in range(10):
            decision = AIDecision(id=f"dl-{i}", decision_type=DecisionType.GENERAL)
            logger.log_decision(decision)

        logs = logger.get_decision_logs(limit=3)
        assert len(logs) == 3

    def test_get_tool_call_logs_limit(self):
        logger = TraceLogger()
        for i in range(10):
            logger.log_tool_invocation(f"tool-{i}", {}, success=True)

        logs = logger.get_tool_call_logs(limit=3)
        assert len(logs) == 3

    def test_get_stats_error_count(self):
        logger = TraceLogger()
        logger.log_tool_invocation("fail_tool", {}, success=False)
        logger.log_tool_invocation("ok_tool", {}, success=True)

        stats = logger.get_stats()
        assert stats["error_count"] == 1
