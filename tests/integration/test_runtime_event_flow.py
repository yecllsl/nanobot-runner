"""运行时事件订阅集成测试

验证 RuntimeEventHook 订阅 Agent 运行时事件的完整流程。
"""

from unittest.mock import MagicMock

import pytest

from src.core.transparency.runtime_event_hook import RuntimeEvent, RuntimeEventHook


@pytest.mark.anyio
async def test_event_subscription_full_flow():
    """测试事件订阅完整流程：subscribe → publish → receive"""
    hook = RuntimeEventHook(event_publisher=None)
    received_events: list[RuntimeEvent] = []
    hook.subscribe(lambda event: received_events.append(event))

    context = MagicMock()
    context.trace_id = "trace-123"
    context.tool_calls = []

    await hook.before_iteration(context)
    assert len(received_events) == 1
    assert received_events[0].type == "iteration_start"
    assert received_events[0].trace_id == "trace-123"


@pytest.mark.anyio
async def test_tool_events_flow():
    """测试工具事件流：before_execute_tools → after_iteration"""
    hook = RuntimeEventHook(event_publisher=None)
    events: list[RuntimeEvent] = []
    hook.subscribe(lambda e: events.append(e))

    context = MagicMock()
    context.trace_id = "trace-456"
    context.tool_calls = [{"name": "read_file", "args": {"path": "/tmp/test"}}]

    await hook.before_execute_tools(context)
    await hook.after_iteration(context)

    # 应收到：1 个 tool_start + 1 个 iteration_end
    assert len(events) == 2
    assert events[0].type == "tool_start"
    assert events[0].data == {"name": "read_file", "args": {"path": "/tmp/test"}}
    assert events[1].type == "iteration_end"


def test_multiple_subscribers():
    """测试多个订阅者同时接收事件"""
    hook = RuntimeEventHook(event_publisher=None)
    events_a: list[RuntimeEvent] = []
    events_b: list[RuntimeEvent] = []
    hook.subscribe(lambda e: events_a.append(e))
    hook.subscribe(lambda e: events_b.append(e))

    hook._publish(RuntimeEvent(type="test", trace_id="t1"))

    assert len(events_a) == 1
    assert len(events_b) == 1
    assert events_a[0].type == "test"


def test_subscriber_exception_does_not_block_others():
    """测试一个订阅者异常不影响其他订阅者"""
    hook = RuntimeEventHook(event_publisher=None)
    received: list[RuntimeEvent] = []

    def bad_callback(event: RuntimeEvent) -> None:
        raise ValueError("subscriber failed")

    hook.subscribe(bad_callback)
    hook.subscribe(lambda e: received.append(e))

    hook._publish(RuntimeEvent(type="test"))

    # 第二个订阅者仍应收到事件
    assert len(received) == 1
