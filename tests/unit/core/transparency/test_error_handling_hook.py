# ErrorHandlingHook单元测试

from unittest.mock import MagicMock

import pytest

from src.core.base.exceptions import ConfigError, LLMError, StorageError
from src.core.transparency.error_classifier import ErrorCategory
from src.core.transparency.error_handling_hook import ErrorHandlingHook


class TestErrorHandlingHook:
    """ErrorHandlingHook测试类"""

    @pytest.fixture
    def mock_console(self):
        """模拟Rich Console"""
        return MagicMock()

    @pytest.fixture
    def mock_obs_manager(self):
        """模拟ObservabilityManager"""
        return MagicMock()

    @pytest.fixture
    def mock_context_no_error(self):
        """模拟无错误的AgentHookContext"""
        ctx = MagicMock()
        ctx.error = None
        return ctx

    @pytest.fixture
    def mock_context_with_error(self):
        """模拟有错误的AgentHookContext"""
        ctx = MagicMock()
        ctx.error = StorageError("存储失败")
        return ctx

    @pytest.mark.asyncio
    async def test_after_iteration_no_error(self, mock_console, mock_context_no_error):
        """测试无错误时不处理"""
        hook = ErrorHandlingHook(console=mock_console)

        await hook.after_iteration(mock_context_no_error)

        mock_console.print.assert_not_called()
        assert hook.get_last_error() is None

    @pytest.mark.asyncio
    async def test_after_iteration_with_error(
        self, mock_console, mock_context_with_error
    ):
        """测试有错误时分类并输出"""
        hook = ErrorHandlingHook(console=mock_console)

        await hook.after_iteration(mock_context_with_error)

        mock_console.print.assert_called()
        last_error = hook.get_last_error()
        assert last_error is not None
        assert last_error.category == ErrorCategory.DATA

    @pytest.mark.asyncio
    async def test_after_iteration_verbose_mode(
        self, mock_console, mock_context_with_error
    ):
        """测试verbose模式显示堆栈"""
        hook = ErrorHandlingHook(console=mock_console, verbose=True)

        await hook.after_iteration(mock_context_with_error)

        # 应输出详细错误信息
        calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("详细错误信息" in str(call) for call in calls)

    @pytest.mark.asyncio
    async def test_after_iteration_non_verbose_mode(
        self, mock_console, mock_context_with_error
    ):
        """测试非verbose模式显示恢复建议"""
        hook = ErrorHandlingHook(console=mock_console, verbose=False)

        await hook.after_iteration(mock_context_with_error)

        calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("💡" in str(call) for call in calls)

    @pytest.mark.asyncio
    async def test_after_iteration_records_to_observability(
        self, mock_console, mock_obs_manager, mock_context_with_error
    ):
        """测试错误记录到ObservabilityManager"""
        hook = ErrorHandlingHook(
            console=mock_console,
            observability_manager=mock_obs_manager,
        )

        await hook.after_iteration(mock_context_with_error)

        mock_obs_manager.record_event.assert_called_once()
        call_args = mock_obs_manager.record_event.call_args[0]
        assert call_args[1] == "error_occurred"
        assert call_args[2]["category"] == "data"

    @pytest.mark.asyncio
    async def test_after_iteration_observability_failure_ignored(
        self, mock_console, mock_obs_manager, mock_context_with_error
    ):
        """测试ObservabilityManager记录失败不中断"""
        mock_obs_manager.record_event.side_effect = Exception("记录失败")
        hook = ErrorHandlingHook(
            console=mock_console,
            observability_manager=mock_obs_manager,
        )

        # 不应抛出异常
        await hook.after_iteration(mock_context_with_error)

        assert hook.get_last_error() is not None

    @pytest.mark.asyncio
    async def test_after_iteration_config_error(self, mock_console):
        """测试ConfigError分类"""
        ctx = MagicMock()
        ctx.error = ConfigError("配置缺失")

        hook = ErrorHandlingHook(console=mock_console)
        await hook.after_iteration(ctx)

        assert hook.get_last_error().category == ErrorCategory.CONFIG

    @pytest.mark.asyncio
    async def test_after_iteration_llm_error(self, mock_console):
        """测试LLMError分类"""
        ctx = MagicMock()
        ctx.error = LLMError("LLM调用失败")

        hook = ErrorHandlingHook(console=mock_console)
        await hook.after_iteration(ctx)

        assert hook.get_last_error().category == ErrorCategory.NETWORK

    def test_reset(self, mock_console):
        """测试重置状态"""
        hook = ErrorHandlingHook(console=mock_console)
        hook._last_error = MagicMock()

        hook.reset()

        assert hook.get_last_error() is None

    @pytest.mark.asyncio
    async def test_after_iteration_no_console(self, mock_context_with_error):
        """测试无console时不输出"""
        hook = ErrorHandlingHook()

        # 不应抛出异常
        await hook.after_iteration(mock_context_with_error)

        assert hook.get_last_error() is not None
