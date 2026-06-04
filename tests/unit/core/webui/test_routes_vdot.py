"""VDOT 趋势 API 路由单元测试"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

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
    # 模拟 VdotTrendItem 对象
    item1 = MagicMock()
    item1.to_dict.return_value = {
        "date": "2024-01-15",
        "vdot": 42.5,
        "distance": 5000.0,
        "duration": 1500.0,
    }
    item2 = MagicMock()
    item2.to_dict.return_value = {
        "date": "2024-01-20",
        "vdot": 43.1,
        "distance": 8000.0,
        "duration": 2400.0,
    }
    context.analytics.get_vdot_trend.return_value = [item1, item2]
    return context


@pytest.fixture
def client(mock_context: MagicMock) -> TestClient:
    app = create_app(context=mock_context)
    return TestClient(app)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    token = create_access_token(secret="test-secret", ttl_seconds=3600)
    return {"Authorization": f"Bearer {token}"}


class TestVdotTrendEndpoint:
    def test_get_vdot_trend_returns_200(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/vdot/trend", headers=auth_headers)
        assert response.status_code == 200

    def test_vdot_trend_returns_list(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/vdot/trend", headers=auth_headers)
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == 2
        assert data["items"][0]["vdot"] == 42.5

    def test_vdot_trend_with_days_param(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/vdot/trend?days=90", headers=auth_headers)
        assert response.status_code == 200

    def test_vdot_trend_requires_auth(self, client: TestClient) -> None:
        response = client.get("/api/vdot/trend")
        assert response.status_code == 401
