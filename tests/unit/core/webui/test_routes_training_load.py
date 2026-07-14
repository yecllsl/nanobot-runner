"""训练负荷 API 路由单元测试"""

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
        "atl": 50.0,
        "ctl": 60.0,
        "tsb": 10.0,
        "fitness_status": "恢复良好",
        "training_advice": "体能充沛",
        "days_analyzed": 42,
        "runs_count": 20,
    }
    context.analytics.get_training_load_trend.return_value = {
        "trend_data": [
            {
                "date": "2024-01-15",
                "tss": 85.0,
                "atl": 48.0,
                "ctl": 55.0,
                "tsb": 7.0,
            },
            {
                "date": "2024-01-16",
                "tss": 0.0,
                "atl": 42.0,
                "ctl": 55.5,
                "tsb": 13.5,
            },
        ],
        "summary": {
            "current_atl": 50.0,
            "current_ctl": 60.0,
            "current_tsb": 10.0,
            "status": "恢复良好",
            "recommendation": "体能充沛",
        },
        "days_analyzed": 42,
        "total_runs": 20,
    }
    return context


@pytest.fixture
def client(mock_context: MagicMock) -> TestClient:
    app = create_app(context=mock_context)
    return TestClient(app)


class TestTrainingLoadEndpoint:
    def test_returns_200(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/training-load", headers=auth_headers)
        assert response.status_code == 200

    def test_contains_atl_ctl_tsb(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/training-load", headers=auth_headers)
        data = response.json()
        assert data["atl"] == 50.0
        assert data["ctl"] == 60.0
        assert data["tsb"] == 10.0

    def test_requires_auth(self, client: TestClient) -> None:
        response = client.get("/api/training-load")
        assert response.status_code == 401


class TestTrainingLoadTrendEndpoint:
    def test_returns_200(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/training-load/trend", headers=auth_headers)
        assert response.status_code == 200

    def test_contains_trend_data(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/training-load/trend", headers=auth_headers)
        data = response.json()
        assert "trend_data" in data
        assert "summary" in data
