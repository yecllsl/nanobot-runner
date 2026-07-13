"""SDKAdapter 单元测试"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.sdk_adapter import SDKAdapter, SDKUnavailableError


@pytest.fixture
def sdk_adapter():
    """创建 SDKAdapter 实例"""
    return SDKAdapter(workspace=None)


async def test_create_session_success(sdk_adapter):
    """测试创建 SDK 会话成功"""
    with patch("src.core.sdk_adapter.Nanobot") as mock_nanobot_cls:
        mock_instance = MagicMock()
        mock_nanobot_cls.from_config.return_value = mock_instance

        session = await sdk_adapter.create_session("session-1")

        assert session is mock_instance
        mock_nanobot_cls.from_config.assert_called_once_with(workspace=None)


async def test_create_session_with_workspace():
    """测试带 workspace 创建会话"""
    with patch("src.core.sdk_adapter.Nanobot") as mock_nanobot_cls:
        mock_instance = MagicMock()
        mock_nanobot_cls.from_config.return_value = mock_instance

        adapter = SDKAdapter(workspace="/tmp/test")
        await adapter.create_session()

        mock_nanobot_cls.from_config.assert_called_once_with(workspace="/tmp/test")


async def test_create_session_failure_raises_sdk_unavailable():
    """测试 SDK 创建失败抛出 SDKUnavailableError"""
    with patch("src.core.sdk_adapter.Nanobot") as mock_nanobot_cls:
        mock_nanobot_cls.from_config.side_effect = RuntimeError("config not found")

        adapter = SDKAdapter()
        with pytest.raises(SDKUnavailableError, match="SDK 模式不可用"):
            await adapter.create_session()


async def test_stream_query_yields_deltas(sdk_adapter):
    """测试流式查询输出 delta 片段"""
    with patch("src.core.sdk_adapter.Nanobot") as mock_nanobot_cls:
        mock_instance = AsyncMock()
        mock_instance.__aenter__.return_value = mock_instance
        mock_instance.__aexit__.return_value = None

        # 构造 mock stream 事件
        async def mock_stream(message, **kwargs):
            for delta in ["chunk1", "chunk2"]:
                event = MagicMock()
                event.delta = delta
                yield event

        mock_instance.stream = mock_stream
        mock_nanobot_cls.from_config.return_value = mock_instance

        chunks = []
        async for chunk in sdk_adapter.stream_query("test", "session-1"):
            chunks.append(chunk)

        assert chunks == ["chunk1", "chunk2"]


async def test_stream_query_skips_empty_delta(sdk_adapter):
    """测试流式查询跳过空 delta 事件"""
    with patch("src.core.sdk_adapter.Nanobot") as mock_nanobot_cls:
        mock_instance = AsyncMock()
        mock_instance.__aenter__.return_value = mock_instance
        mock_instance.__aexit__.return_value = None

        async def mock_stream(message, **kwargs):
            for delta in ["text", "", "more", ""]:
                event = MagicMock()
                event.delta = delta
                yield event

        mock_instance.stream = mock_stream
        mock_nanobot_cls.from_config.return_value = mock_instance

        chunks = []
        async for chunk in sdk_adapter.stream_query("test"):
            chunks.append(chunk)

        assert chunks == ["text", "more"]


async def test_query_returns_content(sdk_adapter):
    """测试非流式查询返回完整内容"""
    with patch("src.core.sdk_adapter.Nanobot") as mock_nanobot_cls:
        mock_instance = AsyncMock()
        mock_instance.__aenter__.return_value = mock_instance
        mock_instance.__aexit__.return_value = None

        mock_result = MagicMock()
        mock_result.content = "完整响应"
        mock_instance.run = AsyncMock(return_value=mock_result)
        mock_nanobot_cls.from_config.return_value = mock_instance

        result = await sdk_adapter.query("test", "session-1")

        assert result == "完整响应"
        mock_instance.run.assert_called_once_with("test", session_key="session-1")


async def test_query_returns_empty_string_for_none_content(sdk_adapter):
    """测试 RunResult.content 为 None 时返回空字符串"""
    with patch("src.core.sdk_adapter.Nanobot") as mock_nanobot_cls:
        mock_instance = AsyncMock()
        mock_instance.__aenter__.return_value = mock_instance
        mock_instance.__aexit__.return_value = None

        mock_result = MagicMock()
        mock_result.content = None
        mock_instance.run = AsyncMock(return_value=mock_result)
        mock_nanobot_cls.from_config.return_value = mock_instance

        result = await sdk_adapter.query("test")

        assert result == ""


async def test_query_sdk_unavailable_raises_error(sdk_adapter):
    """测试 SDK 不可用时抛出 SDKUnavailableError"""
    with patch("src.core.sdk_adapter.Nanobot") as mock_nanobot_cls:
        mock_nanobot_cls.from_config.side_effect = Exception("SDK unavailable")

        with pytest.raises(SDKUnavailableError):
            await sdk_adapter.query("test", "session-1")


async def test_stream_query_sdk_unavailable_raises_error(sdk_adapter):
    """测试流式查询 SDK 不可用时抛出 SDKUnavailableError"""
    with patch("src.core.sdk_adapter.Nanobot") as mock_nanobot_cls:
        mock_nanobot_cls.from_config.side_effect = Exception("SDK unavailable")

        with pytest.raises(SDKUnavailableError):
            async for _ in sdk_adapter.stream_query("test", "session-1"):
                pass


async def test_stream_query_runtime_error_raises_sdk_unavailable(sdk_adapter):
    """测试流式查询运行时错误转为 SDKUnavailableError"""
    with patch("src.core.sdk_adapter.Nanobot") as mock_nanobot_cls:
        mock_instance = AsyncMock()
        mock_instance.__aenter__.return_value = mock_instance
        mock_instance.__aexit__.return_value = None
        mock_instance.stream.side_effect = RuntimeError("stream failed")
        mock_nanobot_cls.from_config.return_value = mock_instance

        with pytest.raises(SDKUnavailableError, match="SDK 模式不可用"):
            async for _ in sdk_adapter.stream_query("test"):
                pass


async def test_query_runtime_error_raises_sdk_unavailable(sdk_adapter):
    """测试非流式查询运行时错误转为 SDKUnavailableError"""
    with patch("src.core.sdk_adapter.Nanobot") as mock_nanobot_cls:
        mock_instance = AsyncMock()
        mock_instance.__aenter__.return_value = mock_instance
        mock_instance.__aexit__.return_value = None
        mock_instance.run.side_effect = RuntimeError("run failed")
        mock_nanobot_cls.from_config.return_value = mock_instance

        with pytest.raises(SDKUnavailableError, match="SDK 模式不可用"):
            await sdk_adapter.query("test")
