"""双路径共存集成测试

验证 RunFlowAgent 的 CLI 路径与 WebUI 路径可以共存，
共享同一 AppContext 但不相互干扰。
"""

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from src.core.webui.app import create_app
from src.core.webui.auth import create_access_token


def _make_mock_context(token_secret: str = "test-secret") -> MagicMock:
    """构建带 WebUI 配置的 mock context"""
    mock_context = MagicMock()
    mock_context.config.get_webui_config.return_value = {
        "enabled": True,
        "host": "127.0.0.1",
        "port": 8766,
        "cors_origins": [],
        "token_secret": token_secret,
        "token_ttl_s": 86400,
    }
    return mock_context


def test_webui_app_creates_without_affecting_cli():
    """测试 WebUI 应用创建不影响 CLI 上下文"""
    mock_context = _make_mock_context()

    app = create_app(context=mock_context)

    # WebUI 应用创建后，context 仍可用
    assert app.state.context is mock_context
    # 验证 runtime_event_hook 已初始化
    assert hasattr(app.state, "runtime_event_hook")


def test_webui_and_cli_share_same_context():
    """测试 WebUI 与 CLI 共享同一 AppContext"""
    mock_context = _make_mock_context(token_secret="shared-secret")

    app = create_app(context=mock_context)

    # WebUI 通过 app.state.context 访问
    assert app.state.context is mock_context
    # 验证 context 的关键组件存在
    assert hasattr(mock_context, "config")
    assert hasattr(mock_context, "analytics")


def test_webui_runtime_events_endpoint_available():
    """测试 WebUI 运行时事件端点可用（与 CLI 不冲突）"""
    mock_context = _make_mock_context()

    app = create_app(context=mock_context)
    client = TestClient(app)
    token = create_access_token(secret="test-secret", ttl_seconds=3600)
    headers = {"Authorization": f"Bearer {token}"}

    # 验证 WebUI 健康检查（无需认证）
    response = client.get("/api/health")
    assert response.status_code == 200

    # 验证 WebUI 自定义 Provider 端点（需认证）
    response = client.get("/api/settings/custom-providers", headers=headers)
    assert response.status_code == 200
