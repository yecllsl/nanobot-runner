"""AgentLoopAdapter 单元测试

验证适配器正确封装 nanobot AgentLoop 的私有 API 与公开 API。
基于 nanobot 0.2.2 实际调研结果：
- _mcp_stacks 是 dict[str, AsyncExitStack]
- _background_tasks 是 list[asyncio.Task]
- _extra_hooks 是 list[AgentHook]
- stop() 是同步方法
- submit_cron_turn(msg) 接收单个 InboundMessage 参数
- process_direct(content, ...) 返回 OutboundMessage | None
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.agent_loop_adapter import AdapterError, AgentLoopAdapter


@pytest.fixture
def mock_agent_loop():
    """创建模拟的 AgentLoop，属性类型对齐 nanobot 0.2.2 实际实现"""
    loop = MagicMock()
    loop._connect_mcp = AsyncMock()
    loop._mcp_stacks = {}  # 实际为 dict[str, AsyncExitStack]
    loop._background_tasks = []  # 实际为 list[asyncio.Task]
    loop._extra_hooks = []  # 实际为 list[AgentHook]
    loop.close_mcp = AsyncMock()
    loop.process_direct = AsyncMock(return_value="response")
    loop.submit_cron_turn = AsyncMock()
    loop.stop = MagicMock()  # 同步方法
    return loop


@pytest.fixture
def adapter(mock_agent_loop):
    return AgentLoopAdapter(mock_agent_loop)


async def test_connect_mcp(adapter, mock_agent_loop):
    """测试连接 MCP（封装 _connect_mcp 私有方法）"""
    await adapter.connect_mcp()
    mock_agent_loop._connect_mcp.assert_called_once()


async def test_mcp_stacks(adapter):
    """测试获取 MCP 栈（封装 _mcp_stacks 私有属性，类型为 dict）"""
    assert adapter.mcp_stacks == {}


async def test_background_tasks(adapter):
    """测试获取后台任务（封装 _background_tasks 私有属性，类型为 list）"""
    assert adapter.background_tasks == []


async def test_add_hook(adapter, mock_agent_loop):
    """测试添加 Hook（封装 _extra_hooks 追加操作）"""
    hook = MagicMock()
    adapter.add_hook(hook)
    assert hook in mock_agent_loop._extra_hooks


async def test_close_mcp(adapter, mock_agent_loop):
    """测试关闭 MCP（封装 close_mcp 公开方法）"""
    await adapter.close_mcp()
    mock_agent_loop.close_mcp.assert_called_once()


async def test_process_direct(adapter, mock_agent_loop):
    """测试直接处理消息（封装 process_direct 公开方法）"""
    result = await adapter.process_direct("test message")
    assert result == "response"
    mock_agent_loop.process_direct.assert_called_once_with("test message")


async def test_submit_cron_turn(adapter, mock_agent_loop):
    """测试提交 Cron turn（封装 submit_cron_turn 公开方法，接收单个 msg 参数）"""
    msg = MagicMock()
    await adapter.submit_cron_turn(msg)
    mock_agent_loop.submit_cron_turn.assert_called_once_with(msg)


def test_stop(adapter, mock_agent_loop):
    """测试停止 Agent Loop（封装 stop 同步方法）"""
    adapter.stop()
    mock_agent_loop.stop.assert_called_once()


async def test_private_api_unavailable(mock_agent_loop):
    """测试私有 API 不可用时抛出 AdapterError"""
    del mock_agent_loop._mcp_stacks
    adapter = AgentLoopAdapter(mock_agent_loop)
    with pytest.raises(AdapterError):
        _ = adapter.mcp_stacks


async def test_connect_mcp_unavailable(mock_agent_loop):
    """测试 _connect_mcp 不可用时抛出 AdapterError"""
    del mock_agent_loop._connect_mcp
    adapter = AgentLoopAdapter(mock_agent_loop)
    with pytest.raises(AdapterError):
        await adapter.connect_mcp()
