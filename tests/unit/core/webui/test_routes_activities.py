"""活动列表与详情 API 路由单元测试"""

import hashlib
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.core.webui.app import create_app
from src.core.webui.auth import create_access_token


def _compute_session_id(timestamp: str) -> str:
    """辅助函数：计算 session_id"""
    return hashlib.sha256(timestamp.encode("utf-8")).hexdigest()


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
    # 模拟 SessionDetail 对象
    session1 = MagicMock()
    session1.to_dict.return_value = {
        "timestamp": "2024-01-20T07:30:00",
        "distance_km": 8.02,
        "duration_min": 42.5,
        "avg_pace_sec_km": 319.4,
        "avg_heart_rate": 155.0,
        "distance_m": 8020.0,
        "duration_s": 2550.0,
        "max_heart_rate": 175.0,
        "calories": 520.0,
    }
    session2 = MagicMock()
    session2.to_dict.return_value = {
        "timestamp": "2024-01-18T06:00:00",
        "distance_km": 5.01,
        "duration_min": 28.3,
        "avg_pace_sec_km": 338.7,
        "avg_heart_rate": 148.0,
        "distance_m": 5010.0,
        "duration_s": 1698.0,
        "max_heart_rate": 168.0,
        "calories": 340.0,
    }
    context.session_repo.get_recent_sessions.return_value = [session1, session2]
    return context


@pytest.fixture
def client(mock_context: MagicMock) -> TestClient:
    app = create_app(context=mock_context)
    return TestClient(app)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    token = create_access_token(secret="test-secret", ttl_seconds=3600)
    return {"Authorization": f"Bearer {token}"}


class TestActivitiesListEndpoint:
    def test_returns_200(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/activities", headers=auth_headers)
        assert response.status_code == 200

    def test_returns_list(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/activities", headers=auth_headers)
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == 2
        assert data["items"][0]["distance_km"] == 8.02

    def test_items_contain_session_id(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/activities", headers=auth_headers)
        data = response.json()
        # 每个活动应包含 session_id 字段
        for item in data["items"]:
            assert "session_id" in item
            assert len(item["session_id"]) == 64  # SHA256 hex 长度

    def test_with_limit_param(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/activities?limit=5", headers=auth_headers)
        assert response.status_code == 200

    def test_requires_auth(self, client: TestClient) -> None:
        response = client.get("/api/activities")
        assert response.status_code == 401


class TestActivityDetailEndpoint:
    def test_returns_200_with_valid_id(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """有效ID返回200"""
        # 使用 fixture 中 session1 的 timestamp 计算 session_id
        valid_id = _compute_session_id("2024-01-20T07:30:00")
        response = client.get(f"/api/activities/{valid_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["distance_km"] == 8.02

    def test_returns_404_with_invalid_id(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """无效ID返回404"""
        # 使用一个不存在的 session_id
        invalid_id = _compute_session_id("nonexistent-timestamp")
        response = client.get(f"/api/activities/{invalid_id}", headers=auth_headers)
        assert response.status_code == 404

    def test_detail_requires_auth(self, client: TestClient) -> None:
        """详情端点需要认证"""
        response = client.get("/api/activities/someid")
        assert response.status_code == 401
