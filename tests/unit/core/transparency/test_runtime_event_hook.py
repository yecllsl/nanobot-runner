"""RuntimeEventHook 单元测试"""

from unittest.mock import MagicMock

import pytest

from src.core.transparency.runtime_event_hook import RuntimeEvent, RuntimeEventHook


@pytest.fixture
def event_hook():
    """创建带 mock publisher 的 RuntimeEventHook"""
    mock_publisher = MagicMock()
    return RuntimeEventHook(event_publisher=mock_publisher)


def test_subscribe(event_hook):
    """测试订阅运行时事件"""
    callback = MagicMock()
    event_hook.subscribe(callback)
    assert callback in event_hook._subscribers


async def test_before_iteration_publish(event_hook):
    """测试迭代前发布事件"""
    callback = MagicMock()
    event_hook.subscribe(callback)

    context = MagicMock()
    context.trace_id = "trace-1"
    await event_hook.before_iteration(context)

    callback.assert_called_once()
    event = callback.call_args[0][0]
    assert event.type == "iteration_start"
    assert event.trace_id == "trace-1"


async def test_before_execute_tools_publish(event_hook):
    """测试工具执行前发布事件"""
    callback = MagicMock()
    event_hook.subscribe(callback)

    context = MagicMock()
    context.trace_id = "trace-1"
    context.tool_calls = [{"name": "test_tool"}]
    await event_hook.before_execute_tools(context)

    callback.assert_called_once()
    event = callback.call_args[0][0]
    assert event.type == "tool_start"


async def test_after_iteration_publish(event_hook):
    """测试迭代后发布事件"""
    callback = MagicMock()
    event_hook.subscribe(callback)

    context = MagicMock()
    context.trace_id = "trace-1"
    await event_hook.after_iteration(context)

    callback.assert_called_once()
    event = callback.call_args[0][0]
    assert event.type == "iteration_end"


async def test_callback_exception_silent_degradation(event_hook):
    """测试回调异常静默降级"""
    bad_callback = MagicMock(side_effect=Exception("callback error"))
    good_callback = MagicMock()
    event_hook.subscribe(bad_callback)
    event_hook.subscribe(good_callback)

    context = MagicMock()
    context.trace_id = "trace-1"
    context.tool_calls = []
    # 不应抛出异常
    await event_hook.before_iteration(context)

    # good_callback 仍应被调用
    good_callback.assert_called_once()


async def test_before_execute_tools_multiple_tools(event_hook):
    """测试多个工具调用时每个都发布事件"""
    callback = MagicMock()
    event_hook.subscribe(callback)

    context = MagicMock()
    context.trace_id = "trace-1"
    context.tool_calls = [{"name": "tool1"}, {"name": "tool2"}, {"name": "tool3"}]
    await event_hook.before_execute_tools(context)

    assert callback.call_count == 3


async def test_before_execute_tools_empty_calls(event_hook):
    """测试空工具调用列表不发布事件"""
    callback = MagicMock()
    event_hook.subscribe(callback)

    context = MagicMock()
    context.trace_id = "trace-1"
    context.tool_calls = []
    await event_hook.before_execute_tools(context)

    callback.assert_not_called()


def test_publish_with_no_subscribers(event_hook):
    """测试无订阅者时发布事件不报错"""
    # 直接调用 _publish，不应抛出异常
    event = RuntimeEvent(type="test", trace_id="t1")
    event_hook._publish(event)


async def test_event_data_carried_in_tool_start(event_hook):
    """测试 tool_start 事件携带 tool_call 数据"""
    callback = MagicMock()
    event_hook.subscribe(callback)

    context = MagicMock()
    context.trace_id = "trace-1"
    tool_call = {"name": "search", "arguments": {"q": "test"}}
    context.tool_calls = [tool_call]
    await event_hook.before_execute_tools(context)

    event = callback.call_args[0][0]
    assert event.data == tool_call
