"""Dashboard API 路由单元测试"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.core.webui.app import create_app


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
    context.analytics.get_training_load.return_value = {
        "atl": 45.0,
        "ctl": 55.0,
        "tsb": 10.0,
        "fitness_status": "恢复良好",
        "training_advice": "当前体能充沛",
        "days_analyzed": 42,
        "runs_count": 15,
    }
    context.analytics.get_vdot_trend.return_value = []
    context.session_repo.get_recent_sessions.return_value = []
    context.body_signal_engine.get_daily_summary.return_value = MagicMock(
        to_dict=lambda: {
            "recovery_status": "good",
            "fatigue_score": 20.0,
            "data_quality": "sufficient",
            "daily_summary": "今日状态良好",
            "training_advice": "可以进行训练",
            "alerts": [],
        }
    )
    return context


@pytest.fixture
def client(mock_context: MagicMock) -> TestClient:
    app = create_app(context=mock_context)
    return TestClient(app)


class TestDashboardEndpoint:
    def test_get_dashboard_returns_200(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/dashboard", headers=auth_headers)
        assert response.status_code == 200

    def test_dashboard_contains_training_load(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/dashboard", headers=auth_headers)
        data = response.json()
        assert "training_load" in data
        assert data["training_load"]["atl"] == 45.0

    def test_dashboard_contains_body_signal(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/dashboard", headers=auth_headers)
        data = response.json()
        assert "body_signal" in data
        assert data["body_signal"]["fatigue_score"] == 20.0

    def test_dashboard_requires_auth(self, client: TestClient) -> None:
        response = client.get("/api/dashboard")
        assert response.status_code == 401
