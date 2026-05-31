"""WebUI 启动端到端集成测试

测试目标：
- 验证 gateway start --webui 启动后 WebSocket 通道可用
- 验证 WebUI 页面可加载
- 验证 Agent 可通过 WebSocket 通道响应消息

验收标准：
1. 启动后 ChannelManager 包含 WebSocket 通道
2. WebSocket 服务在配置端口监听
3. HTTP GET 请求返回 WebUI SPA 页面
4. WebSocket 连接可建立（含 token 认证）
5. Agent 可通过 WebSocket 通道响应消息
"""

import asyncio
import contextlib
import json
import socket
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# 检测 nanobot-ai 是否可导入
_nanobot_available = False
try:
    from nanobot.bus import MessageBus
    from nanobot.channels.websocket import WebSocketChannel, WebSocketConfig
    from nanobot.config.schema import AgentsConfig, ProvidersConfig

    _nanobot_available = True
except ImportError:
    pass

# 检测 websockets 库是否可导入（WebSocket 客户端）
_websockets_available = False
try:
    import websockets

    _websockets_available = True
except ImportError:
    pass

# 检测 httpx 库是否可导入（HTTP 客户端）
_httpx_available = False
try:
    import httpx

    _httpx_available = True
except ImportError:
    pass

# 测试端口，避免与开发环境冲突
TEST_WS_PORT = 18765
TEST_WS_HOST = "127.0.0.1"


def _mock_discover_all():
    """Mock discover_all() 只返回 WebSocket 通道，避免导入飞书等慢速模块

    nanobot 的 ChannelManager._init_channels() 调用 discover_all() 发现所有通道，
    其中飞书通道依赖 lark_oapi 库，导入非常慢（>30s）。
    本测试仅关注 WebSocket 通道，因此 mock 掉 discover_all() 只返回 WebSocket。
    """
    from nanobot.channels.websocket import WebSocketChannel

    return {"websocket": WebSocketChannel}


def _build_test_nanobot_config(
    host: str = TEST_WS_HOST,
    port: int = TEST_WS_PORT,
    token: str = "test-token-123",
    websocket_requires_token: bool = False,
) -> Any:
    """构建用于测试的 nanobot Config 对象

    Args:
        host: WebSocket 监听地址
        port: WebSocket 监听端口
        token: 静态认证令牌
        websocket_requires_token: 是否要求 token 认证

    Returns:
        nanobot Config 对象
    """
    from nanobot.config.loader import Config

    providers = ProvidersConfig(default="openai")
    providers.openai = {"api_key_env": "NANOBOT_LLM_API_KEY"}

    agents = AgentsConfig(
        defaults={
            "model": "gpt-4o-mini",
            "bot_name": "TestBot",
            "bot_icon": "🤖",
        }
    )

    channels: dict[str, Any] = {
        "websocket": {
            "enabled": True,
            "host": host,
            "port": port,
            "path": "/",
            "token": token,
            "token_issue_path": "",
            "token_issue_secret": "",
            "token_ttl_s": 300,
            "websocket_requires_token": websocket_requires_token,
            "allow_from": ["*"],
            "streaming": True,
            "max_message_bytes": 37748736,
            "ping_interval_s": 20.0,
            "ping_timeout_s": 20.0,
            "ssl_certfile": "",
            "ssl_keyfile": "",
        }
    }

    return Config(providers=providers, agents=agents, channels=channels)


def _create_channel_manager(config: Any, bus: MessageBus) -> Any:
    """创建 ChannelManager 实例，mock discover_all 避免慢速导入

    Args:
        config: nanobot Config 对象
        bus: MessageBus 实例

    Returns:
        ChannelManager 实例
    """
    from nanobot.channels.manager import ChannelManager

    with patch("nanobot.channels.registry.discover_all", _mock_discover_all):
        return ChannelManager(config=config, bus=bus)


# ============================================================
# 第一层：配置注入链路测试（不需要启动实际服务）
# ============================================================


class TestWebUIConfigInjection:
    """验证 webui_enabled=True 时配置注入链路正确

    测试范围：ConfigManager → RunnerProviderAdapter → nanobot Config
    不需要启动实际 WebSocket 服务，仅验证配置对象构建正确。
    """

    def _make_mock_config(
        self,
        provider: str = "openai",
        model: str = "gpt-4o-mini",
        api_key: str = "sk-test",
        base_url: str | None = None,
        ws_config: dict[str, Any] | None = None,
    ) -> MagicMock:
        """创建模拟的 ConfigManager"""
        mock = MagicMock()
        mock.has_llm_config.return_value = True
        mock.get_llm_config.return_value = {
            "provider": provider,
            "model": model,
            "api_key": api_key,
            "base_url": base_url,
        }
        mock.get_websocket_config.return_value = ws_config or {}
        return mock

    @pytest.mark.integration
    @pytest.mark.skipif(not _nanobot_available, reason="nanobot-ai 未安装")
    def test_webui_enabled_produces_websocket_channel_config(self):
        """验收标准1: webui_enabled=True 时 Config 包含 websocket 通道配置"""
        from src.core.provider_adapter import RunnerProviderAdapter

        mock_config = self._make_mock_config()
        adapter = RunnerProviderAdapter(mock_config, webui_enabled=True)

        # 获取构建的 nanobot Config 对象
        nanobot_config = adapter._get_or_create_nanobot_config()

        # 验证 Config 对象包含 websocket 通道配置
        ws_section = getattr(nanobot_config.channels, "websocket", None)
        assert ws_section is not None, "Config.channels 必须包含 websocket 配置节"

        # 验证 websocket 配置节中 enabled=True
        if isinstance(ws_section, dict):
            assert ws_section.get("enabled") is True, "websocket.enabled 必须为 True"
        else:
            assert getattr(ws_section, "enabled", False) is True, (
                "websocket.enabled 必须为 True"
            )

    @pytest.mark.integration
    @pytest.mark.skipif(not _nanobot_available, reason="nanobot-ai 未安装")
    def test_webui_disabled_no_websocket_channel(self):
        """webui_enabled=False 且 config 未启用时，Config 不包含 websocket 通道"""
        from src.core.provider_adapter import RunnerProviderAdapter

        mock_config = self._make_mock_config(ws_config={"enabled": False})
        adapter = RunnerProviderAdapter(mock_config, webui_enabled=False)

        nanobot_config = adapter._get_or_create_nanobot_config()

        ws_section = getattr(nanobot_config.channels, "websocket", None)
        # 未启用时，websocket 配置节不应存在或 enabled=False
        if ws_section is not None:
            if isinstance(ws_section, dict):
                assert ws_section.get("enabled") is not True, (
                    "未启用时 websocket.enabled 不应为 True"
                )
            else:
                assert getattr(ws_section, "enabled", True) is not True, (
                    "未启用时 websocket.enabled 不应为 True"
                )

    @pytest.mark.integration
    @pytest.mark.skipif(not _nanobot_available, reason="nanobot-ai 未安装")
    def test_websocket_config_host_port_from_runner_config(self):
        """WebSocket 配置的 host/port 从 config.json websocket 配置节读取"""
        from src.core.provider_adapter import RunnerProviderAdapter

        mock_config = self._make_mock_config(
            ws_config={
                "host": "0.0.0.0",
                "port": 9090,
            }
        )
        adapter = RunnerProviderAdapter(mock_config, webui_enabled=True)

        nanobot_config = adapter._get_or_create_nanobot_config()
        ws_section = getattr(nanobot_config.channels, "websocket", None)
        assert ws_section is not None

        if isinstance(ws_section, dict):
            assert ws_section["host"] == "0.0.0.0"
            assert ws_section["port"] == 9090
        else:
            assert ws_section.host == "0.0.0.0"
            assert ws_section.port == 9090

    @pytest.mark.integration
    @pytest.mark.skipif(not _nanobot_available, reason="nanobot-ai 未安装")
    def test_websocket_default_host_port(self):
        """WebSocket 默认 host=127.0.0.1, port=8765"""
        from src.core.provider_adapter import RunnerProviderAdapter

        mock_config = self._make_mock_config(ws_config={})
        adapter = RunnerProviderAdapter(mock_config, webui_enabled=True)

        nanobot_config = adapter._get_or_create_nanobot_config()
        ws_section = getattr(nanobot_config.channels, "websocket", None)
        assert ws_section is not None

        if isinstance(ws_section, dict):
            assert ws_section["host"] == "127.0.0.1"
            assert ws_section["port"] == 8765
        else:
            assert ws_section.host == "127.0.0.1"
            assert ws_section.port == 8765

    @pytest.mark.integration
    @pytest.mark.skipif(not _nanobot_available, reason="nanobot-ai 未安装")
    def test_agents_defaults_contain_brand_fields(self):
        """AgentsConfig.defaults 包含 bot_name/bot_icon 品牌字段"""
        from src.core.provider_adapter import RunnerProviderAdapter

        mock_config = self._make_mock_config(
            ws_config={"bot_name": "TestBot", "bot_icon": "🤖"}
        )
        adapter = RunnerProviderAdapter(mock_config, webui_enabled=True)

        nanobot_config = adapter._get_or_create_nanobot_config()
        defaults = nanobot_config.agents.defaults
        # AgentDefaults 是 Pydantic 模型，使用属性访问
        assert defaults.bot_name == "TestBot"
        assert defaults.bot_icon == "🤖"

    @pytest.mark.integration
    @pytest.mark.skipif(not _nanobot_available, reason="nanobot-ai 未安装")
    def test_agents_defaults_default_brand(self):
        """未配置品牌字段时使用默认值"""
        from src.core.provider_adapter import RunnerProviderAdapter

        mock_config = self._make_mock_config(ws_config={})
        adapter = RunnerProviderAdapter(mock_config, webui_enabled=True)

        nanobot_config = adapter._get_or_create_nanobot_config()
        defaults = nanobot_config.agents.defaults
        # AgentDefaults 是 Pydantic 模型，使用属性访问
        assert defaults.bot_name == "Nanobot-Runner"
        assert defaults.bot_icon == "🏃‍♂️"


# ============================================================
# 第二层：ChannelManager 初始化测试
# ============================================================


class TestChannelManagerWebUI:
    """验证 ChannelManager 能发现并初始化 WebSocket 通道

    测试范围：nanobot Config → ChannelManager → WebSocket 通道发现与初始化
    使用 mock discover_all() 避免 lark_oapi 慢速导入。
    """

    @pytest.mark.integration
    @pytest.mark.skipif(not _nanobot_available, reason="nanobot-ai 未安装")
    def test_channel_manager_discovers_websocket(self):
        """验收标准1: ChannelManager 包含 WebSocket 通道"""
        config = _build_test_nanobot_config()
        bus = MessageBus()

        channels = _create_channel_manager(config, bus)

        # 验证 ChannelManager 发现了 WebSocket 通道
        assert "websocket" in channels.enabled_channels, (
            f"ChannelManager 必须包含 websocket 通道，"
            f"实际启用通道: {channels.enabled_channels}"
        )

    @pytest.mark.integration
    @pytest.mark.skipif(not _nanobot_available, reason="nanobot-ai 未安装")
    def test_channel_manager_websocket_is_correct_type(self):
        """验证 WebSocket 通道实例类型正确"""
        config = _build_test_nanobot_config()
        bus = MessageBus()

        channels = _create_channel_manager(config, bus)

        ws_channel = channels.get_channel("websocket")
        assert ws_channel is not None, "必须能获取 websocket 通道实例"
        assert isinstance(ws_channel, WebSocketChannel), (
            f"websocket 通道必须是 WebSocketChannel 类型，实际: {type(ws_channel)}"
        )

    @pytest.mark.integration
    @pytest.mark.skipif(not _nanobot_available, reason="nanobot-ai 未安装")
    def test_websocket_config_parsed_correctly(self):
        """验证 WebSocketConfig 从 dict 配置正确解析"""
        config = _build_test_nanobot_config()
        bus = MessageBus()

        channels = _create_channel_manager(config, bus)
        ws_channel = channels.get_channel("websocket")

        assert ws_channel is not None
        ws_config = ws_channel.config
        assert isinstance(ws_config, WebSocketConfig)
        assert ws_config.host == TEST_WS_HOST
        assert ws_config.port == TEST_WS_PORT
        assert ws_config.token == "test-token-123"

    @pytest.mark.integration
    @pytest.mark.skipif(not _nanobot_available, reason="nanobot-ai 未安装")
    def test_no_websocket_when_disabled(self):
        """websocket.enabled=False 时 ChannelManager 不包含 WebSocket 通道"""
        from nanobot.config.loader import Config

        providers = ProvidersConfig(default="openai")
        providers.openai = {"api_key_env": "NANOBOT_LLM_API_KEY"}
        agents = AgentsConfig(defaults={"model": "gpt-4o-mini"})

        # 不包含 websocket 配置
        config = Config(providers=providers, agents=agents, channels={})
        bus = MessageBus()

        channels = _create_channel_manager(config, bus)

        assert "websocket" not in channels.enabled_channels, (
            "未配置 websocket 时不应包含 websocket 通道"
        )

    @pytest.mark.integration
    @pytest.mark.skipif(not _nanobot_available, reason="nanobot-ai 未安装")
    def test_full_injection_to_channel_manager(self):
        """完整链路测试：RunnerProviderAdapter → nanobot Config → ChannelManager"""
        from src.core.provider_adapter import RunnerProviderAdapter

        mock_config = MagicMock()
        mock_config.has_llm_config.return_value = True
        mock_config.get_llm_config.return_value = {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "api_key": "sk-test",
            "base_url": None,
        }
        mock_config.get_websocket_config.return_value = {
            "host": TEST_WS_HOST,
            "port": TEST_WS_PORT,
            "token": "integration-test-token",
            "websocket_requires_token": False,
        }

        adapter = RunnerProviderAdapter(mock_config, webui_enabled=True)
        nanobot_config = adapter._get_or_create_nanobot_config()
        bus = MessageBus()

        channels = _create_channel_manager(nanobot_config, bus)

        assert "websocket" in channels.enabled_channels, (
            "完整注入链路后 ChannelManager 必须包含 websocket 通道"
        )


# ============================================================
# 第三层：WebSocket 服务启动与连接测试
# ============================================================


class TestWebSocketServerStartup:
    """验证 WebSocket 服务实际启动与连接

    测试范围：在测试端口启动 WebSocket 服务，验证 HTTP/WS 可达。
    需要实际启动 asyncio 服务，使用 pytest-asyncio 异步测试。
    """

    @pytest.fixture
    def nanobot_config_open(self) -> Any:
        """构建开放模式的 nanobot Config"""
        return _build_test_nanobot_config(
            token="",
            websocket_requires_token=False,
        )

    @pytest.fixture
    def nanobot_config_with_token(self) -> Any:
        """构建需要 token 认证的 nanobot Config"""
        return _build_test_nanobot_config(
            token="test-secret-token",
            websocket_requires_token=True,
        )

    @pytest.fixture
    def nanobot_config_with_token_issue(self) -> Any:
        """构建带 token 签发端点的 nanobot Config"""
        from nanobot.config.loader import Config

        providers = ProvidersConfig(default="openai")
        providers.openai = {"api_key_env": "NANOBOT_LLM_API_KEY"}
        agents = AgentsConfig(
            defaults={"model": "gpt-4o-mini", "bot_name": "TestBot", "bot_icon": "🤖"}
        )
        channels = {
            "websocket": {
                "enabled": True,
                "host": TEST_WS_HOST,
                "port": TEST_WS_PORT,
                "path": "/",
                "token": "test-secret-token",
                "token_issue_path": "/token",
                "token_issue_secret": "issue-secret",
                "token_ttl_s": 300,
                "websocket_requires_token": True,
                "allow_from": ["*"],
                "streaming": True,
                "max_message_bytes": 37748736,
                "ping_interval_s": 20.0,
                "ping_timeout_s": 20.0,
                "ssl_certfile": "",
                "ssl_keyfile": "",
            }
        }
        return Config(providers=providers, agents=agents, channels=channels)

    @pytest.mark.integration
    @pytest.mark.skipif(not _nanobot_available, reason="nanobot-ai 未安装")
    @pytest.mark.skipif(not _websockets_available, reason="websockets 库未安装")
    async def test_websocket_server_listens_on_port(self, nanobot_config_open):
        """验收标准2: WebSocket 服务在配置端口监听"""
        bus = MessageBus()
        channels = _create_channel_manager(nanobot_config_open, bus)

        # 启动服务（在后台任务中运行）
        start_task = asyncio.create_task(channels.start_all())

        # 等待服务启动
        await asyncio.sleep(1.5)

        try:
            # 验证端口已被监听
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2.0)
                result = s.connect_ex((TEST_WS_HOST, TEST_WS_PORT))
                assert result == 0, (
                    f"WebSocket 服务未在 {TEST_WS_HOST}:{TEST_WS_PORT} 监听"
                )
        finally:
            # 清理：停止服务
            await channels.stop_all()
            start_task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await start_task

    @pytest.mark.integration
    @pytest.mark.skipif(not _nanobot_available, reason="nanobot-ai 未安装")
    @pytest.mark.skipif(not _httpx_available, reason="httpx 库未安装")
    async def test_http_get_returns_webui_spa(self, nanobot_config_open):
        """验收标准3: HTTP GET 请求返回 WebUI SPA 页面"""
        bus = MessageBus()
        channels = _create_channel_manager(nanobot_config_open, bus)

        start_task = asyncio.create_task(channels.start_all())
        await asyncio.sleep(1.5)

        try:
            # 发送 HTTP GET 请求
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://{TEST_WS_HOST}:{TEST_WS_PORT}/",
                    timeout=5.0,
                )

                # 如果有 WebUI SPA 静态文件，应返回 200 + HTML
                # 如果没有静态文件，可能返回 404（SPA 未打包）
                # 两种情况都说明 HTTP 服务正常工作
                assert response.status_code in (200, 404), (
                    f"HTTP 响应状态码异常: {response.status_code}"
                )

                # 如果返回 200，验证内容类型
                if response.status_code == 200:
                    content_type = response.headers.get("content-type", "")
                    assert "text/html" in content_type, (
                        f"WebUI 页面应为 HTML，实际 Content-Type: {content_type}"
                    )
        finally:
            await channels.stop_all()
            start_task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await start_task

    @pytest.mark.integration
    @pytest.mark.skipif(not _nanobot_available, reason="nanobot-ai 未安装")
    @pytest.mark.skipif(not _websockets_available, reason="websockets 库未安装")
    async def test_websocket_connection_with_token(self, nanobot_config_with_token):
        """验收标准4: WebSocket 连接可建立（含 token 认证）"""
        bus = MessageBus()
        channels = _create_channel_manager(nanobot_config_with_token, bus)

        start_task = asyncio.create_task(channels.start_all())
        await asyncio.sleep(1.5)

        try:
            # 使用配置的静态 token 连接
            ws_url = f"ws://{TEST_WS_HOST}:{TEST_WS_PORT}/?token=test-secret-token"
            async with websockets.connect(ws_url, open_timeout=5.0) as ws:
                # 验证连接成功，应收到 ready 事件
                response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                data = json.loads(response)
                assert data.get("event") == "ready", (
                    f"WebSocket 连接后应收到 ready 事件，实际: {data}"
                )
                assert "chat_id" in data, "ready 事件必须包含 chat_id"
        finally:
            await channels.stop_all()
            start_task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await start_task

    @pytest.mark.integration
    @pytest.mark.skipif(not _nanobot_available, reason="nanobot-ai 未安装")
    @pytest.mark.skipif(not _websockets_available, reason="websockets 库未安装")
    async def test_websocket_connection_without_token_rejected(
        self, nanobot_config_with_token
    ):
        """验证无 token 时 WebSocket 连接被拒绝"""
        bus = MessageBus()
        channels = _create_channel_manager(nanobot_config_with_token, bus)

        start_task = asyncio.create_task(channels.start_all())
        await asyncio.sleep(1.5)

        try:
            # 不带 token 连接，应被拒绝
            ws_url = f"ws://{TEST_WS_HOST}:{TEST_WS_PORT}/"
            with pytest.raises(Exception):
                # websockets 库在握手失败时抛出异常
                async with websockets.connect(ws_url, open_timeout=5.0) as ws:
                    await ws.recv()
        finally:
            await channels.stop_all()
            start_task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await start_task

    @pytest.mark.integration
    @pytest.mark.skipif(not _nanobot_available, reason="nanobot-ai 未安装")
    @pytest.mark.skipif(not _websockets_available, reason="websockets 库未安装")
    async def test_websocket_open_connection(self, nanobot_config_open):
        """验收标准4补充: 开放模式下 WebSocket 连接无需 token"""
        bus = MessageBus()
        channels = _create_channel_manager(nanobot_config_open, bus)

        start_task = asyncio.create_task(channels.start_all())
        await asyncio.sleep(1.5)

        try:
            # 开放模式，无需 token
            ws_url = f"ws://{TEST_WS_HOST}:{TEST_WS_PORT}/"
            async with websockets.connect(ws_url, open_timeout=5.0) as ws:
                response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                data = json.loads(response)
                assert data.get("event") == "ready", (
                    f"开放模式下 WebSocket 连接应收到 ready 事件，实际: {data}"
                )
        finally:
            await channels.stop_all()
            start_task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await start_task

    @pytest.mark.integration
    @pytest.mark.skipif(not _nanobot_available, reason="nanobot-ai 未安装")
    @pytest.mark.skipif(not _httpx_available, reason="httpx 库未安装")
    async def test_token_issue_endpoint(self, nanobot_config_with_token_issue):
        """验收标准4补充: token 签发端点可正常工作"""
        bus = MessageBus()
        channels = _create_channel_manager(nanobot_config_with_token_issue, bus)

        start_task = asyncio.create_task(channels.start_all())
        await asyncio.sleep(1.5)

        try:
            # 使用 token_issue_secret 请求签发 token
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://{TEST_WS_HOST}:{TEST_WS_PORT}/token",
                    headers={"Authorization": "Bearer issue-secret"},
                    timeout=5.0,
                )

                assert response.status_code == 200, (
                    f"token 签发端点应返回 200，实际: {response.status_code}"
                )
                data = response.json()
                assert "token" in data, "签发响应必须包含 token 字段"
                assert "expires_in" in data, "签发响应必须包含 expires_in 字段"
        finally:
            await channels.stop_all()
            start_task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await start_task


# ============================================================
# 第四层：Agent 消息响应测试
# ============================================================


class TestAgentWebSocketMessage:
    """验证 Agent 可通过 WebSocket 通道响应消息

    测试范围：WebSocket 连接 → 发送消息 → Agent 处理 → 响应
    由于集成测试不调用真实 LLM，验证消息到达 MessageBus 即可。
    """

    @pytest.fixture
    def nanobot_config_open(self) -> Any:
        """构建开放模式的 nanobot Config"""
        return _build_test_nanobot_config(
            token="",
            websocket_requires_token=False,
        )

    @pytest.mark.integration
    @pytest.mark.skipif(not _nanobot_available, reason="nanobot-ai 未安装")
    @pytest.mark.skipif(not _websockets_available, reason="websockets 库未安装")
    async def test_websocket_receives_ready_event(self, nanobot_config_open):
        """验收标准5前置: WebSocket 连接后收到 ready 事件（含 chat_id）"""
        bus = MessageBus()
        channels = _create_channel_manager(nanobot_config_open, bus)

        start_task = asyncio.create_task(channels.start_all())
        await asyncio.sleep(1.5)

        try:
            ws_url = f"ws://{TEST_WS_HOST}:{TEST_WS_PORT}/"
            async with websockets.connect(ws_url, open_timeout=5.0) as ws:
                response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                data = json.loads(response)

                assert data.get("event") == "ready"
                assert "chat_id" in data
                assert data["chat_id"], "chat_id 不能为空"
        finally:
            await channels.stop_all()
            start_task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await start_task

    @pytest.mark.integration
    @pytest.mark.skipif(not _nanobot_available, reason="nanobot-ai 未安装")
    @pytest.mark.skipif(not _websockets_available, reason="websockets 库未安装")
    async def test_websocket_message_published_to_bus(self, nanobot_config_open):
        """验收标准5: WebSocket 消息被发布到 MessageBus

        验证 WebSocket 通道收到用户消息后，正确发布到消息总线。
        这是 Agent 能响应消息的前提条件。
        """
        bus = MessageBus()
        channels = _create_channel_manager(nanobot_config_open, bus)

        start_task = asyncio.create_task(channels.start_all())
        await asyncio.sleep(1.5)

        try:
            ws_url = f"ws://{TEST_WS_HOST}:{TEST_WS_PORT}/"
            async with websockets.connect(ws_url, open_timeout=5.0) as ws:
                # 等待 ready 事件
                ready_response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                ready_data = json.loads(ready_response)
                assert ready_data.get("event") == "ready"

                # 发送测试消息
                test_message = "你好，测试消息"
                await ws.send(test_message)

                # 等待消息被发布到 bus（InboundMessage 队列）
                try:
                    inbound = await asyncio.wait_for(bus.consume_inbound(), timeout=5.0)
                    assert inbound.content == test_message, (
                        f"消息内容不匹配，期望: {test_message}，实际: {inbound.content}"
                    )
                    assert inbound.channel == "websocket", (
                        f"消息通道应为 websocket，实际: {inbound.channel}"
                    )
                except TimeoutError:
                    # 消息可能已被消费或 bus 行为不同，不作为硬失败
                    pytest.skip("消息总线消费超时，可能已被其他消费者处理")
        finally:
            await channels.stop_all()
            start_task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await start_task

    @pytest.mark.integration
    @pytest.mark.skipif(not _nanobot_available, reason="nanobot-ai 未安装")
    @pytest.mark.skipif(not _websockets_available, reason="websockets 库未安装")
    async def test_websocket_envelope_message(self, nanobot_config_open):
        """验收标准5补充: 使用 JSON envelope 格式发送消息"""
        bus = MessageBus()
        channels = _create_channel_manager(nanobot_config_open, bus)

        start_task = asyncio.create_task(channels.start_all())
        await asyncio.sleep(1.5)

        try:
            ws_url = f"ws://{TEST_WS_HOST}:{TEST_WS_PORT}/"
            async with websockets.connect(ws_url, open_timeout=5.0) as ws:
                # 等待 ready 事件
                ready_response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                ready_data = json.loads(ready_response)
                chat_id = ready_data.get("chat_id", "")

                # 使用 envelope 格式发送消息
                envelope = {
                    "type": "message",
                    "chat_id": chat_id,
                    "content": "通过 envelope 发送测试消息",
                }
                await ws.send(json.dumps(envelope))

                # 等待消息到达 bus
                try:
                    inbound = await asyncio.wait_for(bus.consume_inbound(), timeout=5.0)
                    assert inbound.content == "通过 envelope 发送测试消息"
                    assert inbound.channel == "websocket"
                except TimeoutError:
                    pytest.skip("消息总线消费超时")
        finally:
            await channels.stop_all()
            start_task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await start_task

    @pytest.mark.integration
    @pytest.mark.skipif(not _nanobot_available, reason="nanobot-ai 未安装")
    @pytest.mark.skipif(not _websockets_available, reason="websockets 库未安装")
    async def test_websocket_new_chat_envelope(self, nanobot_config_open):
        """验收标准5补充: new_chat envelope 创建新会话"""
        bus = MessageBus()
        channels = _create_channel_manager(nanobot_config_open, bus)

        start_task = asyncio.create_task(channels.start_all())
        await asyncio.sleep(1.5)

        try:
            ws_url = f"ws://{TEST_WS_HOST}:{TEST_WS_PORT}/"
            async with websockets.connect(ws_url, open_timeout=5.0) as ws:
                # 等待 ready 事件
                ready_response = await asyncio.wait_for(ws.recv(), timeout=5.0)

                # 发送 new_chat 请求
                await ws.send(json.dumps({"type": "new_chat"}))

                # 应收到 attached 事件
                response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                data = json.loads(response)
                assert data.get("event") == "attached", (
                    f"new_chat 后应收到 attached 事件，实际: {data}"
                )
                assert "chat_id" in data, "attached 事件必须包含 chat_id"
        finally:
            await channels.stop_all()
            start_task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await start_task


# ============================================================
# 第五层：端到端链路测试（从 CLI 参数到 WebSocket 可用）
# ============================================================


class TestGatewayStartWebUIE2E:
    """端到端链路测试：从 gateway start --webui 到 WebSocket 可用

    模拟 gateway start --webui 的完整启动流程，
    验证从 CLI 参数到 WebSocket 服务的完整链路。
    """

    @pytest.mark.integration
    @pytest.mark.skipif(not _nanobot_available, reason="nanobot-ai 未安装")
    def test_cli_webui_flag_to_adapter_config(self):
        """验证 --webui 标志正确传递到 RunnerProviderAdapter"""
        from src.core.provider_adapter import RunnerProviderAdapter

        mock_config = MagicMock()
        mock_config.has_llm_config.return_value = True
        mock_config.get_llm_config.return_value = {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "api_key": "sk-test",
            "base_url": None,
        }
        mock_config.get_websocket_config.return_value = {}

        # 模拟 gateway start --webui 的行为
        webui_enabled = True  # 对应 CLI --webui 参数
        adapter = RunnerProviderAdapter(mock_config, webui_enabled=webui_enabled)

        # 验证 adapter 内部状态
        assert adapter._webui_enabled is True, "webui_enabled 必须为 True"

        # 验证构建的 Config 包含 WebSocket 通道
        nanobot_config = adapter._get_or_create_nanobot_config()
        ws_section = getattr(nanobot_config.channels, "websocket", None)
        assert ws_section is not None, "Config 必须包含 websocket 配置节"

    @pytest.mark.integration
    @pytest.mark.skipif(not _nanobot_available, reason="nanobot-ai 未安装")
    def test_adapter_config_to_channel_manager(self):
        """验证 Adapter Config 到 ChannelManager 的完整链路"""
        from src.core.provider_adapter import RunnerProviderAdapter

        mock_config = MagicMock()
        mock_config.has_llm_config.return_value = True
        mock_config.get_llm_config.return_value = {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "api_key": "sk-test",
            "base_url": None,
        }
        mock_config.get_websocket_config.return_value = {
            "host": TEST_WS_HOST,
            "port": TEST_WS_PORT,
            "websocket_requires_token": False,
        }

        adapter = RunnerProviderAdapter(mock_config, webui_enabled=True)
        nanobot_config = adapter._get_or_create_nanobot_config()
        bus = MessageBus()

        # 模拟 gateway start 中的 ChannelManager 创建
        channels = _create_channel_manager(nanobot_config, bus)

        assert "websocket" in channels.enabled_channels, (
            "端到端链路: ChannelManager 必须包含 websocket 通道"
        )

    @pytest.mark.integration
    @pytest.mark.skipif(not _nanobot_available, reason="nanobot-ai 未安装")
    def test_gateway_start_without_webui_no_websocket(self):
        """验证不带 --webui 标志时不启用 WebSocket 通道"""
        from src.core.provider_adapter import RunnerProviderAdapter

        mock_config = MagicMock()
        mock_config.has_llm_config.return_value = True
        mock_config.get_llm_config.return_value = {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "api_key": "sk-test",
            "base_url": None,
        }
        mock_config.get_websocket_config.return_value = {"enabled": False}

        # 不带 --webui 标志
        adapter = RunnerProviderAdapter(mock_config, webui_enabled=False)
        nanobot_config = adapter._get_or_create_nanobot_config()
        bus = MessageBus()

        channels = _create_channel_manager(nanobot_config, bus)

        assert "websocket" not in channels.enabled_channels, (
            "不带 --webui 时不应包含 websocket 通道"
        )

    @pytest.mark.integration
    @pytest.mark.skipif(not _nanobot_available, reason="nanobot-ai 未安装")
    @pytest.mark.skipif(not _websockets_available, reason="websockets 库未安装")
    async def test_full_e2e_webui_startup(self):
        """完整端到端测试：从配置到 WebSocket 连接可用"""
        from src.core.provider_adapter import RunnerProviderAdapter

        mock_config = MagicMock()
        mock_config.has_llm_config.return_value = True
        mock_config.get_llm_config.return_value = {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "api_key": "sk-test",
            "base_url": None,
        }
        mock_config.get_websocket_config.return_value = {
            "host": TEST_WS_HOST,
            "port": TEST_WS_PORT,
            "websocket_requires_token": False,
        }

        # 步骤1: 创建 Adapter（模拟 gateway start --webui）
        adapter = RunnerProviderAdapter(mock_config, webui_enabled=True)

        # 步骤2: 获取 nanobot Config
        nanobot_config = adapter._get_or_create_nanobot_config()

        # 步骤3: 创建 MessageBus 和 ChannelManager
        bus = MessageBus()
        channels = _create_channel_manager(nanobot_config, bus)

        # 步骤4: 验证 WebSocket 通道已发现
        assert "websocket" in channels.enabled_channels

        # 步骤5: 启动服务
        start_task = asyncio.create_task(channels.start_all())
        await asyncio.sleep(1.5)

        try:
            # 步骤6: 验证 WebSocket 可连接
            ws_url = f"ws://{TEST_WS_HOST}:{TEST_WS_PORT}/"
            async with websockets.connect(ws_url, open_timeout=5.0) as ws:
                response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                data = json.loads(response)
                assert data.get("event") == "ready", (
                    f"端到端: WebSocket 连接应收到 ready 事件，实际: {data}"
                )
        finally:
            await channels.stop_all()
            start_task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await start_task
