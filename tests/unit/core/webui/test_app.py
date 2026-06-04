"""FastAPI 应用工厂单元测试"""

from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.core.webui.app import create_app, get_app


def _make_mock_context() -> MagicMock:
    context = MagicMock()
    context.config.get_webui_config.return_value = {
        "enabled": True,
        "host": "127.0.0.1",
        "port": 8766,
        "cors_origins": ["http://localhost:8765"],
        "token_secret": "test-secret",
        "token_ttl_s": 86400,
    }
    return context


class TestCreateApp:
    def test_create_app_returns_fastapi_instance(self) -> None:
        """create_app 返回 FastAPI 实例"""
        mock_context = _make_mock_context()
        app = create_app(context=mock_context)
        assert isinstance(app, FastAPI)

    def test_health_check_endpoint(self) -> None:
        """健康检查端点返回 200"""
        mock_context = _make_mock_context()
        app = create_app(context=mock_context)
        client = TestClient(app)
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data

    def test_token_issue_endpoint(self) -> None:
        """令牌签发端点可用"""
        mock_context = _make_mock_context()
        app = create_app(context=mock_context)
        client = TestClient(app)
        response = client.post("/api/auth/token")
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_cors_middleware_configured(self) -> None:
        """CORS 中间件已配置"""
        mock_context = _make_mock_context()
        app = create_app(context=mock_context)
        # 验证 CORS 中间件已添加
        middleware_types = [
            type(m.cls).__name__ if hasattr(m, "cls") else type(m).__name__
            for m in app.user_middleware
        ]
        assert any("CORS" in str(m) for m in middleware_types) or any(
            "CORS" in str(m) for m in app.user_middleware
        )


class TestGetApp:
    def test_get_app_returns_none_before_create(self) -> None:
        """创建前 get_app 返回 None"""
        import src.core.webui.app as app_module

        app_module._app_instance = None
        assert get_app() is None
