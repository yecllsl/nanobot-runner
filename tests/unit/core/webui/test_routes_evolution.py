"""Evolution API 路由单元测试"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.core.webui.app import create_app


@pytest.fixture
def mock_trigger_result() -> MagicMock:
    """创建Mock触发检查结果"""
    action1 = MagicMock()
    action1.action_type = "retrain_model"
    action1.trigger_reason = "vdot预测误差连续3次>5%"
    action1.created_at = MagicMock(isoformat=lambda: "2026-06-01T10:00:00")
    action1.executed = True

    action2 = MagicMock()
    action2.action_type = "adjust_strategy"
    action2.trigger_reason = "连续2次拒绝推荐"
    action2.created_at = MagicMock(isoformat=lambda: "2026-06-01T11:00:00")
    action2.executed = False

    result = MagicMock()
    result.triggered_actions = [action1, action2]
    return result


@pytest.fixture
def mock_tuning_params() -> MagicMock:
    """创建Mock调优参数"""
    params = MagicMock()
    params.tone_intensity = 0.5
    params.detail_level_score = 0.5
    params.recommendation_aggressiveness = 0.5
    params.data_driven_weight = 0.5
    return params


@pytest.fixture
def mock_report() -> MagicMock:
    """创建Mock进化报告"""
    report = MagicMock()
    report.to_dict.return_value = {
        "report_id": "rpt-001",
        "month": "2026-05",
        "total_decisions": 10,
    }
    return report


@pytest.fixture
def mock_context(
    mock_trigger_result: MagicMock,
    mock_tuning_params: MagicMock,
    mock_report: MagicMock,
) -> MagicMock:
    context = MagicMock()
    context.config.get_webui_config.return_value = {
        "enabled": True,
        "host": "127.0.0.1",
        "port": 8766,
        "cors_origins": [],
        "token_secret": "test-secret",
        "token_ttl_s": 86400,
    }
    # EvolutionEngine 公共方法
    context.evolution_engine.check_triggers.return_value = mock_trigger_result
    context.evolution_engine.get_prompt_tuning_params.return_value = mock_tuning_params
    context.evolution_engine.adjust_prompt_params.return_value = mock_tuning_params
    context.evolution_engine.get_evolution_report.return_value = mock_report
    # EvolutionStore
    context.evolution_engine._store.data_dir = MagicMock()
    return context


@pytest.fixture
def client(mock_context: MagicMock) -> TestClient:
    app = create_app(context=mock_context)
    return TestClient(app)


class TestEvolutionStatusEndpoint:
    """GET /api/evolution/status"""

    def test_status_returns_200(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/evolution/status", headers=auth_headers)
        assert response.status_code == 200

    def test_status_contains_engine_status(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/evolution/status", headers=auth_headers)
        data = response.json()
        assert "engine_status" in data
        assert data["engine_status"] == "running"

    def test_status_contains_trigger_conditions(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/evolution/status", headers=auth_headers)
        data = response.json()
        assert "trigger_conditions" in data
        assert len(data["trigger_conditions"]) == 4

    def test_status_requires_auth(self, client: TestClient) -> None:
        response = client.get("/api/evolution/status")
        assert response.status_code == 401


class TestTuningParamsEndpoint:
    """GET/PUT /api/evolution/tuning"""

    def test_get_tuning_returns_200(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/evolution/tuning", headers=auth_headers)
        assert response.status_code == 200

    def test_get_tuning_returns_params(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/evolution/tuning", headers=auth_headers)
        data = response.json()
        assert "tone" in data
        assert "detail" in data
        assert "aggressive" in data
        assert "data_driven" in data

    def test_put_tuning_returns_200(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.put(
            "/api/evolution/tuning",
            json={"tone": 0.7, "detail": 0.3},
            headers=auth_headers,
        )
        assert response.status_code == 200

    def test_put_tuning_calls_adjust(
        self, client: TestClient, auth_headers: dict[str, str], mock_context: MagicMock
    ) -> None:
        client.put(
            "/api/evolution/tuning",
            json={"tone": 0.7},
            headers=auth_headers,
        )
        mock_context.evolution_engine.adjust_prompt_params.assert_called_once()


class TestEvolutionReportsEndpoint:
    """GET /api/evolution/reports"""

    def test_reports_returns_200(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/evolution/reports", headers=auth_headers)
        assert response.status_code == 200

    def test_reports_contains_available_months(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/evolution/reports", headers=auth_headers)
        data = response.json()
        assert "available_months" in data
        assert "count" in data


class TestEvolutionReportDetailEndpoint:
    """GET /api/evolution/reports/{month}"""

    def test_report_detail_returns_200(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/evolution/reports/2026-05", headers=auth_headers)
        assert response.status_code == 200

    def test_report_detail_invalid_month(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/evolution/reports/invalid", headers=auth_headers)
        assert response.status_code == 400
