# CLI 流式输出集成测试 - v0.17.0

from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from src.cli.streaming import CLIStreamingManager, stream_agent_response
from src.core.transparency.streaming_hook import StreamingHook


class TestCLIStreamingManager:
    """CLIStreamingManager 测试"""

    def test_init_default(self):
        """测试默认初始化"""
        manager = CLIStreamingManager()
        assert manager._show_spinner is True
        assert manager._render_markdown is True
        assert manager._stream_buffer == ""
        assert manager._stream_active is False

    def test_init_custom(self):
        """测试自定义初始化"""
        console = Console()
        manager = CLIStreamingManager(
            console=console,
            show_spinner=False,
            render_markdown=False,
        )
        assert manager._console == console
        assert manager._show_spinner is False
        assert manager._render_markdown is False

    def test_context_manager(self):
        """测试上下文管理器"""
        manager = CLIStreamingManager(show_spinner=False)

        with manager as m:
            assert m is manager
            assert manager._live is None

    def test_context_manager_with_spinner(self):
        """测试带spinner的上下文管理器"""
        manager = CLIStreamingManager(show_spinner=True)

        with patch("src.cli.streaming.Live") as MockLive:
            mock_live = MagicMock()
            MockLive.return_value = mock_live

            with manager as m:
                assert m is manager
                MockLive.assert_called_once()
                mock_live.start.assert_called_once()

            mock_live.stop.assert_called_once()

    def test_create_hook(self):
        """测试创建Hook"""
        console = Console()
        manager = CLIStreamingManager(console=console)

        hook = manager.create_hook()
        assert isinstance(hook, StreamingHook)

    def test_on_delta(self):
        """测试处理流式片段"""
        manager = CLIStreamingManager(show_spinner=False)

        manager.on_delta("Hello")
        assert manager._stream_buffer == "Hello"
        assert manager._stream_active is True

        manager.on_delta(" World")
        assert manager._stream_buffer == "Hello World"

    def test_on_delta_empty(self):
        """测试处理空片段"""
        manager = CLIStreamingManager(show_spinner=False)

        manager.on_delta("")
        assert manager._stream_buffer == ""
        assert manager._stream_active is False

    def test_on_complete(self):
        """测试完成处理"""
        manager = CLIStreamingManager(show_spinner=False)

        manager.on_delta("Test content")
        manager.on_complete()

        assert manager._stream_buffer == ""
        assert manager._stream_active is False

    def test_on_complete_with_text(self):
        """测试带文本的完成处理"""
        manager = CLIStreamingManager(show_spinner=False)

        manager.on_complete("Final text")
        assert manager._stream_buffer == ""

    def test_get_buffer(self):
        """测试获取缓冲区"""
        manager = CLIStreamingManager(show_spinner=False)

        manager.on_delta("Buffer content")
        assert manager.get_buffer() == "Buffer content"

    def test_is_active(self):
        """测试活动状态检查"""
        manager = CLIStreamingManager(show_spinner=False)

        assert manager.is_active() is False
        manager.on_delta("content")
        assert manager.is_active() is True
        manager.on_complete()
        assert manager.is_active() is False


class TestStreamAgentResponse:
    """stream_agent_response 便捷函数测试"""

    def test_stream_with_string_result(self):
        """测试字符串结果"""
        agent = MagicMock()
        agent.run.return_value = "Agent response"

        with patch("src.cli.streaming.CLIStreamingManager") as MockManager:
            mock_manager = MagicMock()
            mock_manager.create_hook.return_value = MagicMock()
            MockManager.return_value.__enter__ = MagicMock(return_value=mock_manager)
            MockManager.return_value.__exit__ = MagicMock(return_value=False)

            result = stream_agent_response(agent)

            assert result == "Agent response"
            agent.run.assert_called_once()

    def test_stream_with_object_result(self):
        """测试对象结果"""
        agent = MagicMock()
        result_obj = MagicMock()
        result_obj.content = "Object content"
        agent.run.return_value = result_obj

        with patch("src.cli.streaming.CLIStreamingManager") as MockManager:
            mock_manager = MagicMock()
            mock_manager.create_hook.return_value = MagicMock()
            MockManager.return_value.__enter__ = MagicMock(return_value=mock_manager)
            MockManager.return_value.__exit__ = MagicMock(return_value=False)

            result = stream_agent_response(agent)

            assert result == "Object content"

    def test_stream_exception(self):
        """测试异常处理"""
        agent = MagicMock()
        agent.run.side_effect = Exception("Test error")

        with patch("src.cli.streaming.CLIStreamingManager") as MockManager:
            mock_manager = MagicMock()
            mock_manager.create_hook.return_value = MagicMock()
            MockManager.return_value.__enter__ = MagicMock(return_value=mock_manager)
            MockManager.return_value.__exit__ = MagicMock(return_value=False)

            with pytest.raises(Exception, match="Test error"):
                stream_agent_response(agent)

            mock_manager.on_complete.assert_called_once()
