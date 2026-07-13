"""Hook 生命周期集成测试

验证 AgentHook 子类（RuntimeEventHook）的生命周期回调。
"""

from unittest.mock import MagicMock

import pytest

from src.core.transparency.runtime_event_hook import RuntimeEventHook


@pytest.mark.anyio
async def test_hook_full_lifecycle():
    """测试 Hook 完整生命周期：before_iteration → before_execute_tools → after_iteration"""
    hook = RuntimeEventHook(event_publisher=None)
    events = []
    hook.subscribe(lambda e: events.append(e))

    context = MagicMock()
    context.trace_id = "lifecycle-trace"
    context.tool_calls = [{"name": "some_tool"}]

    await hook.before_iteration(context)
    await hook.before_execute_tools(context)
    await hook.after_iteration(context)

    # 应收到 3 个事件：iteration_start + tool_start + iteration_end
    assert len(events) == 3
    types = [e.type for e in events]
    assert types == ["iteration_start", "tool_start", "iteration_end"]


@pytest.mark.anyio
async def test_hook_with_multiple_tool_calls():
    """测试 Hook 处理多个工具调用"""
    hook = RuntimeEventHook(event_publisher=None)
    events = []
    hook.subscribe(lambda e: events.append(e))

    context = MagicMock()
    context.trace_id = "multi-tool"
    context.tool_calls = [
        {"name": "tool1"},
        {"name": "tool2"},
        {"name": "tool3"},
    ]

    await hook.before_execute_tools(context)

    # 3 个工具调用应产生 3 个 tool_start 事件
    tool_events = [e for e in events if e.type == "tool_start"]
    assert len(tool_events) == 3


@pytest.mark.anyio
async def test_hook_empty_tool_calls():
    """测试 Hook 处理空工具调用列表"""
    hook = RuntimeEventHook(event_publisher=None)
    events = []
    hook.subscribe(lambda e: events.append(e))

    context = MagicMock()
    context.trace_id = "no-tools"
    context.tool_calls = []

    await hook.before_execute_tools(context)

    # 空工具列表不应产生 tool_start 事件
    assert len(events) == 0
