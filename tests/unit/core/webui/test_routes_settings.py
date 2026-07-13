"""Settings API 路由单元测试"""

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
    return context


@pytest.fixture
def client(mock_context: MagicMock) -> TestClient:
    app = create_app(context=mock_context)
    return TestClient(app)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    token = create_access_token(secret="test-secret", ttl_seconds=3600)
    return {"Authorization": f"Bearer {token}"}


class TestProfileEndpoint:
    """GET/PUT /api/settings/profile"""

    def test_get_profile_returns_200(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/settings/profile", headers=auth_headers)
        assert response.status_code == 200

    def test_get_profile_contains_fields(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/settings/profile", headers=auth_headers)
        data = response.json()
        assert "nickname" in data
        assert "age" in data
        assert "gender" in data
        assert "max_heart_rate" in data
        assert "resting_heart_rate" in data

    def test_put_profile_returns_200(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.put(
            "/api/settings/profile",
            json={"nickname": "新名字", "age": 31},
            headers=auth_headers,
        )
        assert response.status_code == 200

    def test_put_profile_calls_save(
        self, client: TestClient, auth_headers: dict[str, str], mock_context: MagicMock
    ) -> None:
        client.put(
            "/api/settings/profile",
            json={"nickname": "新名字"},
            headers=auth_headers,
        )
        mock_context.config.save_config.assert_called_once()

    def test_profile_requires_auth(self, client: TestClient) -> None:
        response = client.get("/api/settings/profile")
        assert response.status_code == 401


class TestSystemConfigEndpoint:
    """GET /api/settings/system"""

    def test_system_config_returns_200(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/settings/system", headers=auth_headers)
        assert response.status_code == 200

    def test_system_config_contains_fields(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/settings/system", headers=auth_headers)
        data = response.json()
        assert "data_dir" in data
        assert "version" in data
        assert "webui_enabled" in data
        assert "webui_port" in data

    def test_system_config_requires_auth(self, client: TestClient) -> None:
        response = client.get("/api/settings/system")
        assert response.status_code == 401


class TestCustomProviderEndpoint:
    """GET/POST /api/settings/custom-providers"""

    @pytest.fixture(autouse=True)
    def _clear_custom_providers(self):
        """每个测试前后清理 DynamicProviderRegistry 类级状态"""
        from src.core.provider_adapter import DynamicProviderRegistry

        DynamicProviderRegistry._custom_providers.clear()
        DynamicProviderRegistry._provider_metadata.clear()
        yield
        DynamicProviderRegistry._custom_providers.clear()
        DynamicProviderRegistry._provider_metadata.clear()

    def test_list_empty_returns_200(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/settings/custom-providers", headers=auth_headers)
        assert response.status_code == 200
        assert "providers" in response.json()

    def test_add_provider_returns_success(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.post(
            "/api/settings/custom-providers",
            json={
                "name": "test-custom-provider",
                "api_base": "https://api.example.com/v1",
                "api_key": "sk-test",
                "default_model": "gpt-4",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_add_provider_appears_in_list(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        client.post(
            "/api/settings/custom-providers",
            json={
                "name": "test-list-provider",
                "api_base": "https://api.example.com/v1",
                "api_key": "sk-test",
                "default_model": "gpt-4",
            },
            headers=auth_headers,
        )
        response = client.get("/api/settings/custom-providers", headers=auth_headers)
        assert "test-list-provider" in response.json()["providers"]

    def test_add_builtin_name_conflict_returns_failure(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """名称与内置 Provider 冲突时返回 success=False"""
        response = client.post(
            "/api/settings/custom-providers",
            json={
                "name": "openai",  # 内置名称
                "api_base": "https://api.example.com/v1",
                "api_key": "sk-test",
                "default_model": "gpt-4",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False

    def test_add_invalid_payload_returns_422(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """缺少必填字段时返回 422"""
        response = client.post(
            "/api/settings/custom-providers",
            json={"name": "incomplete"},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_list_requires_auth(self, client: TestClient) -> None:
        response = client.get("/api/settings/custom-providers")
        assert response.status_code == 401

    def test_add_requires_auth(self, client: TestClient) -> None:
        response = client.post(
            "/api/settings/custom-providers",
            json={
                "name": "no-auth",
                "api_base": "https://api.example.com/v1",
                "api_key": "sk-test",
                "default_model": "gpt-4",
            },
        )
        assert response.status_code == 401
