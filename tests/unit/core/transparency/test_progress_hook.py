# ProgressDisplayHook单元测试

import time
from unittest.mock import MagicMock

import pytest

from src.core.transparency.progress_hook import ProgressDisplayHook


class TestProgressDisplayHook:
    """ProgressDisplayHook测试类"""

    @pytest.fixture
    def mock_console(self):
        """模拟Rich Console"""
        return MagicMock()

    @pytest.fixture
    def mock_tool_call(self):
        """模拟工具调用"""
        tc = MagicMock()
        tc.name = "test_tool"
        return tc

    @pytest.fixture
    def mock_context(self, mock_tool_call):
        """模拟AgentHookContext"""
        ctx = MagicMock()
        ctx.tool_calls = [mock_tool_call]
        return ctx

    @pytest.mark.asyncio
    async def test_before_execute_tools_records_time(self, mock_console, mock_context):
        """测试工具执行前记录时间"""
        hook = ProgressDisplayHook(console=mock_console)

        await hook.before_execute_tools(mock_context)

        assert "test_tool" in hook.get_pending_tools()
        mock_console.print.assert_called_once_with("🔧 正在调用: test_tool ...")

    @pytest.mark.asyncio
    async def test_before_execute_tools_multiple_tools(self, mock_console):
        """测试多工具调用进度显示"""
        tc1 = MagicMock()
        tc1.name = "tool_a"
        tc2 = MagicMock()
        tc2.name = "tool_b"
        ctx = MagicMock()
        ctx.tool_calls = [tc1, tc2]

        hook = ProgressDisplayHook(console=mock_console)
        await hook.before_execute_tools(ctx)

        assert hook.get_pending_tools().keys() == {"tool_a", "tool_b"}
        assert mock_console.print.call_count == 2

    @pytest.mark.asyncio
    async def test_after_iteration_calculates_elapsed(self, mock_console, mock_context):
        """测试迭代后计算耗时"""
        hook = ProgressDisplayHook(console=mock_console)

        await hook.before_execute_tools(mock_context)
        time.sleep(0.01)  # 短暂等待
        await hook.after_iteration(mock_context)

        # 验证完成消息被打印
        calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("✅ test_tool 完成" in str(call) for call in calls)
        assert hook.get_pending_tools() == {}

    @pytest.mark.asyncio
    async def test_after_iteration_no_pending_tools(self, mock_console):
        """测试无待处理工具时不输出"""
        ctx = MagicMock()
        ctx.tool_calls = []

        hook = ProgressDisplayHook(console=mock_console)
        await hook.after_iteration(ctx)

        mock_console.print.assert_not_called()

    @pytest.mark.asyncio
    async def test_after_iteration_unknown_tool_ignored(self, mock_console):
        """测试未知工具被忽略"""
        tc = MagicMock()
        tc.name = "unknown_tool"
        ctx = MagicMock()
        ctx.tool_calls = [tc]

        hook = ProgressDisplayHook(console=mock_console)
        # 不调用before_execute_tools，直接调用after_iteration
        await hook.after_iteration(ctx)

        mock_console.print.assert_not_called()

    def test_get_pending_tools_returns_copy(self, mock_console):
        """测试获取待处理工具返回副本"""
        hook = ProgressDisplayHook(console=mock_console)
        hook._tool_start_times["tool"] = 123.0

        pending = hook.get_pending_tools()
        pending["new_tool"] = 456.0

        assert "new_tool" not in hook.get_pending_tools()

    def test_reset(self, mock_console):
        """测试重置状态"""
        hook = ProgressDisplayHook(console=mock_console)
        hook._tool_start_times["tool"] = 123.0

        hook.reset()

        assert hook.get_pending_tools() == {}

    @pytest.mark.asyncio
    async def test_before_execute_tools_no_console(self, mock_context):
        """测试无console时不输出"""
        hook = ProgressDisplayHook()

        await hook.before_execute_tools(mock_context)

        assert "test_tool" in hook.get_pending_tools()
