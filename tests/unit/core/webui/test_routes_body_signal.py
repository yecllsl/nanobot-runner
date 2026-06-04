"""身体信号 API 路由单元测试"""

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
    daily_summary = MagicMock()
    daily_summary.to_dict.return_value = {
        "recovery_status": "good",
        "fatigue_score": 25.0,
        "data_quality": "sufficient",
        "daily_summary": "今日状态良好",
        "training_advice": "建议进行中等强度训练",
        "alerts": [
            {
                "alert_type": "high_fatigue",
                "severity": "warning",
                "message": "连续高强度训练3天",
            }
        ],
    }
    context.body_signal_engine.get_daily_summary.return_value = daily_summary

    weekly_summary = MagicMock()
    weekly_summary.to_dict.return_value = {
        "recovery_status": "good",
        "fatigue_score": 30.0,
        "data_quality": "sufficient",
        "daily_summary": "本周训练负荷适中",
        "training_advice": "保持当前训练节奏",
        "alerts": [],
    }
    context.body_signal_engine.get_weekly_summary.return_value = weekly_summary

    alert = MagicMock()
    alert.to_dict.return_value = {
        "alert_type": "high_fatigue",
        "severity": "warning",
        "message": "连续高强度训练3天",
    }
    context.body_signal_engine.check_alerts.return_value = [alert]
    return context


@pytest.fixture
def client(mock_context: MagicMock) -> TestClient:
    app = create_app(context=mock_context)
    return TestClient(app)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    token = create_access_token(secret="test-secret", ttl_seconds=3600)
    return {"Authorization": f"Bearer {token}"}


class TestBodySignalDailyEndpoint:
    def test_returns_200(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/body-signal/daily", headers=auth_headers)
        assert response.status_code == 200

    def test_contains_fields(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/body-signal/daily", headers=auth_headers)
        data = response.json()
        assert data["recovery_status"] == "good"
        assert data["fatigue_score"] == 25.0


class TestBodySignalWeeklyEndpoint:
    def test_returns_200(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/body-signal/weekly", headers=auth_headers)
        assert response.status_code == 200


class TestBodySignalAlertsEndpoint:
    def test_returns_200(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/body-signal/alerts", headers=auth_headers)
        assert response.status_code == 200

    def test_returns_alerts_list(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/body-signal/alerts", headers=auth_headers)
        data = response.json()
        assert "alerts" in data
        assert len(data["alerts"]) == 1


class TestBodySignalAuthRequired:
    def test_daily_requires_auth(self, client: TestClient) -> None:
        assert client.get("/api/body-signal/daily").status_code == 401

    def test_weekly_requires_auth(self, client: TestClient) -> None:
        assert client.get("/api/body-signal/weekly").status_code == 401

    def test_alerts_requires_auth(self, client: TestClient) -> None:
        assert client.get("/api/body-signal/alerts").status_code == 401
