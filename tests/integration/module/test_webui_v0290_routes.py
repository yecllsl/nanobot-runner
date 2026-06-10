"""v0.29.0 WebUI 新路由模块级集成测试

测试目标：
- 验证 plan/evolution/settings 路由在 app 中正确注册
- 验证路由前缀和端点路径可访问
- 验证认证中间件在所有新端点生效

验收标准：
1. 所有新端点返回 200（带认证）或 401（无认证）
2. 路由前缀 /api/plan, /api/evolution, /api/settings 正确
3. 请求/响应数据流转正常
"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.core.webui.app import create_app
from src.core.webui.auth import create_access_token


@pytest.fixture
def mock_trigger_result() -> MagicMock:
    action = MagicMock()
    action.action_type = "retrain_model"
    action.trigger_reason = "vdot预测误差"
    action.created_at = MagicMock(isoformat=lambda: "2026-06-01T10:00:00")
    action.executed = True
    result = MagicMock()
    result.triggered_actions = [action]
    return result


@pytest.fixture
def mock_tuning_params() -> MagicMock:
    params = MagicMock()
    params.tone_intensity = 0.5
    params.detail_level_score = 0.5
    params.recommendation_aggressiveness = 0.5
    params.data_driven_weight = 0.5
    return params


@pytest.fixture
def mock_context(
    mock_trigger_result: MagicMock,
    mock_tuning_params: MagicMock,
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
    context.config.load_config.return_value = {
        "profile": {
            "nickname": "测试跑者",
            "age": 30,
            "gender": "male",
            "max_heart_rate": 190,
            "resting_heart_rate": 60,
        }
    }
    context.config.data_dir = MagicMock()
    context.config.data_dir.__str__ = lambda self: "/data"

    # PlanManager
    context.plan_manager.list_plans.return_value = []
    context.plan_manager.get_plan.return_value = None

    # EvolutionEngine
    context.evolution_engine.check_triggers.return_value = mock_trigger_result
    context.evolution_engine.get_prompt_tuning_params.return_value = mock_tuning_params
    context.evolution_engine.adjust_prompt_params.return_value = mock_tuning_params
    context.evolution_engine._store.data_dir = MagicMock()

    return context


@pytest.fixture
def client(mock_context: MagicMock) -> TestClient:
    app = create_app(context=mock_context)
    return TestClient(app)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    token = create_access_token(secret="test-secret", ttl_seconds=3600)
    return {"Authorization": f"Bearer {token}"}


class TestRouteRegistration:
    """验证所有新路由在 app 中正确注册"""

    def test_plan_list_registered(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/plan/list", headers=auth_headers)
        assert response.status_code == 200

    def test_plan_calendar_registered(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get(
            "/api/plan/calendar?year=2026&month=6", headers=auth_headers
        )
        assert response.status_code == 200

    def test_evolution_status_registered(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/evolution/status", headers=auth_headers)
        assert response.status_code == 200

    def test_evolution_tuning_registered(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/evolution/tuning", headers=auth_headers)
        assert response.status_code == 200

    def test_evolution_reports_registered(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/evolution/reports", headers=auth_headers)
        assert response.status_code == 200

    def test_settings_profile_registered(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/settings/profile", headers=auth_headers)
        assert response.status_code == 200

    def test_settings_system_registered(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/settings/system", headers=auth_headers)
        assert response.status_code == 200


class TestAuthEnforcement:
    """验证所有新端点强制认证"""

    def test_plan_endpoints_require_auth(self, client: TestClient) -> None:
        for path in ["/api/plan/list", "/api/plan/calendar?year=2026&month=6"]:
            assert client.get(path).status_code == 401

    def test_evolution_endpoints_require_auth(self, client: TestClient) -> None:
        for path in [
            "/api/evolution/status",
            "/api/evolution/tuning",
            "/api/evolution/reports",
        ]:
            assert client.get(path).status_code == 401

    def test_settings_endpoints_require_auth(self, client: TestClient) -> None:
        for path in ["/api/settings/profile", "/api/settings/system"]:
            assert client.get(path).status_code == 401


class TestExistingRoutesUnaffected:
    """验证现有路由不受新路由影响"""

    def test_dashboard_still_works(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/dashboard/summary", headers=auth_headers)
        # 可能返回200或500（取决于mock），但不应404
        assert response.status_code != 404

    def test_vdot_still_works(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/vdot/trend?days=30", headers=auth_headers)
        assert response.status_code != 404
