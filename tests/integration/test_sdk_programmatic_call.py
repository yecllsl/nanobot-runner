"""SDK 编程式调用集成测试

验证 SDKAdapter 封装 Nanobot SDK 的调用链路。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.sdk_adapter import SDKAdapter, SDKUnavailableError


@pytest.mark.anyio
async def test_sdk_query_full_flow():
    """测试 SDK query 完整调用链路"""
    mock_result = MagicMock()
    mock_result.content = "Hello from SDK"

    mock_sdk = AsyncMock()
    mock_sdk.run = AsyncMock(return_value=mock_result)
    mock_sdk.__aenter__ = AsyncMock(return_value=mock_sdk)
    mock_sdk.__aexit__ = AsyncMock(return_value=None)

    with patch("src.core.sdk_adapter.Nanobot") as mock_nanobot_class:
        mock_nanobot_class.from_config.return_value = mock_sdk
        adapter = SDKAdapter()
        result = await adapter.query("test message", session_key="test:session")

    assert result == "Hello from SDK"
    mock_sdk.run.assert_called_once_with("test message", session_key="test:session")


@pytest.mark.anyio
async def test_sdk_stream_query_full_flow():
    """测试 SDK stream_query 流式调用链路"""

    async def mock_stream(*args, **kwargs):
        yield MagicMock(delta="Hello ")
        yield MagicMock(delta="World")

    mock_sdk = AsyncMock()
    mock_sdk.stream = mock_stream
    mock_sdk.__aenter__ = AsyncMock(return_value=mock_sdk)
    mock_sdk.__aexit__ = AsyncMock(return_value=None)

    with patch("src.core.sdk_adapter.Nanobot") as mock_nanobot_class:
        mock_nanobot_class.from_config.return_value = mock_sdk
        adapter = SDKAdapter()
        chunks = []
        async for chunk in adapter.stream_query("test", session_key="test:session"):
            chunks.append(chunk)

    assert chunks == ["Hello ", "World"]


@pytest.mark.anyio
async def test_sdk_query_failure_raises_sdk_unavailable():
    """测试 SDK 调用失败抛出 SDKUnavailableError"""
    with patch("src.core.sdk_adapter.Nanobot") as mock_nanobot_class:
        mock_nanobot_class.from_config.side_effect = RuntimeError("config not found")
        adapter = SDKAdapter()
        with pytest.raises(SDKUnavailableError, match="SDK 模式不可用"):
            await adapter.query("test")
