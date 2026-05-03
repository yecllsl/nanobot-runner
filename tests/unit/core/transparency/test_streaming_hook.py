# StreamingHook单元测试

from unittest.mock import MagicMock

import pytest

from src.core.transparency.streaming_hook import StreamingHook


class TestStreamingHook:
    """StreamingHook测试类"""

    @pytest.fixture
    def mock_console(self):
        """模拟Rich Console"""
        return MagicMock()

    @pytest.fixture
    def mock_bus(self):
        """模拟MessageBus"""
        return MagicMock()

    @pytest.fixture
    def mock_context(self):
        """模拟AgentHookContext"""
        return MagicMock()

    def test_wants_streaming_returns_true(self):
        """测试wants_streaming返回True"""
        hook = StreamingHook()
        assert hook.wants_streaming() is True

    @pytest.mark.asyncio
    async def test_on_stream_cli_output(self, mock_console, mock_context):
        """测试CLI通道流式输出"""
        hook = StreamingHook(console=mock_console)

        await hook.on_stream(mock_context, "Hello")

        mock_console.print.assert_called_once_with("Hello", end="")
        assert hook.get_stream_buffer() == "Hello"
        assert hook.is_stream_active() is True

    @pytest.mark.asyncio
    async def test_on_stream_empty_delta_filtered(self, mock_console, mock_context):
        """测试空delta过滤"""
        hook = StreamingHook(console=mock_console)

        await hook.on_stream(mock_context, "")

        mock_console.print.assert_not_called()
        assert hook.is_stream_active() is False

    @pytest.mark.asyncio
    async def test_on_stream_gateway_output(self, mock_bus, mock_context):
        """测试Gateway通道消息推送"""
        hook = StreamingHook(
            bus=mock_bus,
            channel="feishu",
            chat_id="test_chat",
        )

        await hook.on_stream(mock_context, "Hello")

        mock_bus.publish_outbound.assert_called_once()
        call_args = mock_bus.publish_outbound.call_args[0][0]
        assert call_args.channel == "feishu"
        assert call_args.chat_id == "test_chat"
        assert call_args.content == "Hello"
        assert call_args.metadata.get("stream_delta") is True

    @pytest.mark.asyncio
    async def test_on_stream_no_channel_skips_gateway(self, mock_bus, mock_context):
        """测试无channel时不推送Gateway"""
        hook = StreamingHook(bus=mock_bus)

        await hook.on_stream(mock_context, "Hello")

        mock_bus.publish_outbound.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_stream_end(self, mock_console, mock_context):
        """测试流式结束处理"""
        hook = StreamingHook(console=mock_console)

        await hook.on_stream(mock_context, "Hello")
        await hook.on_stream_end(mock_context)

        mock_console.print.assert_called()
        assert hook.is_stream_active() is False
        assert hook.get_stream_buffer() == ""

    @pytest.mark.asyncio
    async def test_on_stream_end_no_active_stream(self, mock_console, mock_context):
        """测试无活动流时结束不输出换行"""
        hook = StreamingHook(console=mock_console)

        await hook.on_stream_end(mock_context)

        mock_console.print.assert_not_called()

    def test_reset(self, mock_console):
        """测试重置状态"""
        hook = StreamingHook(console=mock_console)
        hook._stream_active = True
        hook._stream_buffer = "test"

        hook.reset()

        assert hook.is_stream_active() is False
        assert hook.get_stream_buffer() == ""

    @pytest.mark.asyncio
    async def test_on_stream_gateway_failure_ignored(self, mock_bus, mock_context):
        """测试Gateway推送失败不中断"""
        mock_bus.publish_outbound.side_effect = Exception("推送失败")
        hook = StreamingHook(
            bus=mock_bus,
            channel="feishu",
            chat_id="test_chat",
        )

        # 不应抛出异常
        await hook.on_stream(mock_context, "Hello")

        assert hook.is_stream_active() is True
