"""JWT 认证中间件单元测试"""

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from src.core.webui.auth import create_access_token, get_current_user


@pytest.fixture
def secret_key() -> str:
    return "test-secret-for-jwt"


@pytest.fixture
def app(secret_key: str) -> FastAPI:
    """创建带认证依赖的测试应用"""
    app = FastAPI()

    @app.get("/protected")
    async def protected_route(user: str = Depends(get_current_user)):
        return {"user": user}

    @app.post("/auth/token")
    async def login():
        token = create_access_token(
            secret=secret_key,
            ttl_seconds=3600,
        )
        return {"access_token": token, "token_type": "bearer"}

    return app


@pytest.fixture
def client(app: FastAPI, secret_key: str) -> TestClient:
    # 注入 secret_key 到 app.state
    app.state.webui_secret = secret_key
    # 设置全局 app 实例供 get_current_user 使用
    import src.core.webui.app as app_module

    app_module._app_instance = app
    return TestClient(app)


class TestCreateAccessToken:
    def test_create_valid_token(self, secret_key: str) -> None:
        """创建有效的 JWT 令牌"""
        token = create_access_token(secret=secret_key, ttl_seconds=3600)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_token_contains_exp_claim(self, secret_key: str) -> None:
        """令牌包含 exp 过期时间"""
        import jwt

        token = create_access_token(secret=secret_key, ttl_seconds=3600)
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        assert "exp" in payload
        assert "sub" in payload
        assert payload["sub"] == "nanobot-runner"


class TestGetCurrentUser:
    def test_valid_token_returns_user(
        self, client: TestClient, secret_key: str
    ) -> None:
        """有效令牌返回用户信息"""
        token = create_access_token(secret=secret_key, ttl_seconds=3600)
        response = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["user"] == "nanobot-runner"

    def test_missing_token_returns_401(self, client: TestClient) -> None:
        """缺少令牌返回 401"""
        response = client.get("/protected")
        assert response.status_code == 401

    def test_invalid_token_returns_401(self, client: TestClient) -> None:
        """无效令牌返回 401"""
        response = client.get(
            "/protected",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401

    def test_expired_token_returns_401(
        self, client: TestClient, secret_key: str
    ) -> None:
        """过期令牌返回 401"""
        token = create_access_token(secret=secret_key, ttl_seconds=-1)
        response = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401

    def test_token_issue_endpoint(self, client: TestClient) -> None:
        """令牌签发端点返回有效令牌"""
        response = client.post("/auth/token")
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
