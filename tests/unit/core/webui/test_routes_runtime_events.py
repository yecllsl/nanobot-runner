"""运行时事件 SSE 端点单元测试 (v0.32.0)"""

import asyncio
import contextlib
import json
from typing import Any
from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

from src.core.transparency.runtime_event_hook import RuntimeEvent
from src.core.webui.app import create_app
from src.core.webui.auth import create_access_token


@pytest.fixture
def mock_context() -> MagicMock:
    context = MagicMock()
    context.config.get_webui_config.return_value = {
        "enabled": True,
        "host": "127.0.0.1",
        "port": 8766,
        "cors_origins": [],
        "token_secret": "test-secret",
        "token_ttl_s": 86400,
    }
    return context


@pytest.fixture
def app(mock_context: MagicMock):
    return create_app(context=mock_context)


@pytest.fixture
def client(app) -> TestClient:
    return TestClient(app)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    token = create_access_token(secret="test-secret", ttl_seconds=3600)
    return {"Authorization": f"Bearer {token}"}


def _make_scope(
    headers: dict[str, str], path: str = "/api/runtime-events/stream"
) -> dict[str, Any]:
    """构造 ASGI scope

    使用 spec_version=2.4 让 Starlette 跳过 listen_for_disconnect，
    只运行 stream_response，避免 receive 死循环占用事件循环。
    """
    return {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.4"},
        "http_version": "1.1",
        "method": "GET",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "server": ("test", 80),
        "client": ("127.0.0.1", 123),
        "root_path": "",
    }


async def _run_app_until_started(
    app, scope: dict[str, Any]
) -> tuple[asyncio.Task, list[dict[str, Any]], list[bytes]]:
    """启动 ASGI app task，等待响应头，返回 task 和收到的消息

    注意：调用方负责取消返回的 task（SSE 流不会自行结束）
    """
    received: list[dict[str, Any]] = []
    body_chunks: list[bytes] = []
    started = asyncio.Event()

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        received.append(message)
        if message["type"] == "http.response.start":
            started.set()
        elif message["type"] == "http.response.body":
            body = message.get("body", b"")
            if body:
                body_chunks.append(body)

    task = asyncio.create_task(app(scope, receive, send))
    await asyncio.wait_for(started.wait(), timeout=2.0)
    return task, received, body_chunks


class TestRuntimeEventsEndpoint:
    """运行时事件 SSE 端点测试"""

    def test_stream_requires_auth(self, client: TestClient) -> None:
        """测试 SSE 端点需要认证"""
        response = client.get("/api/runtime-events/stream")
        assert response.status_code == 401

    async def test_stream_returns_sse_content_type(
        self, app, auth_headers: dict[str, str]
    ) -> None:
        """测试 SSE 端点返回正确的 content type"""
        scope = _make_scope(auth_headers)
        task, received, _ = await _run_app_until_started(app, scope)

        start = next(m for m in received if m["type"] == "http.response.start")
        assert start["status"] == 200
        headers = {k.decode(): v.decode() for k, v in start["headers"]}
        assert "text/event-stream" in headers["content-type"]

        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    async def test_stream_has_no_cache_headers(
        self, app, auth_headers: dict[str, str]
    ) -> None:
        """测试 SSE 响应包含 no-cache 头"""
        scope = _make_scope(auth_headers)
        task, received, _ = await _run_app_until_started(app, scope)

        start = next(m for m in received if m["type"] == "http.response.start")
        headers = {k.decode(): v.decode() for k, v in start["headers"]}
        assert headers["cache-control"] == "no-cache"

        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    def test_runtime_event_hook_initialized(self, client: TestClient) -> None:
        """测试 app.state 中 runtime_event_hook 已初始化"""
        assert hasattr(client.app.state, "runtime_event_hook")
        assert client.app.state.runtime_event_hook is not None

    async def test_stream_receives_published_event(
        self, app, auth_headers: dict[str, str]
    ) -> None:
        """测试 SSE 流接收已发布的事件"""
        scope = _make_scope(auth_headers)
        hook = app.state.runtime_event_hook
        task, _, body_chunks = await _run_app_until_started(app, scope)

        # 等待生成器执行到 subscribe + queue.get()
        await asyncio.sleep(0.3)
        # 发布事件（同步调用 callback，将事件放入 asyncio.Queue）
        hook._publish(RuntimeEvent(type="test_event", trace_id="trace-123"))
        # 等待生成器处理事件并 yield
        await asyncio.sleep(0.3)

        all_body = b"".join(body_chunks).decode()
        for line in all_body.split("\n"):
            if line.startswith("data: "):
                data = json.loads(line[6:])
                assert data["type"] == "test_event"
                assert data["trace_id"] == "trace-123"
                break
        else:
            pytest.fail(f"未收到事件，收到的数据: {all_body!r}")

        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    async def test_stream_subscriber_cleanup_on_disconnect(
        self, app, auth_headers: dict[str, str]
    ) -> None:
        """测试断开连接后订阅者被清理"""
        scope = _make_scope(auth_headers)
        hook = app.state.runtime_event_hook
        initial_count = len(hook._subscribers)

        task, _, _ = await _run_app_until_started(app, scope)
        # 确保生成器已执行 subscribe
        await asyncio.sleep(0.1)

        # 取消 task（模拟客户端断开），finally 块清理订阅者
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

        assert len(hook._subscribers) == initial_count
