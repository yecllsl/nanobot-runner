"""WebUI 认证测试

测试 JWT Token 认证机制，包括 Token 签发、验证、过期等场景。
"""

from src.core.webui.auth import create_access_token


class TestAuthentication:
    """认证机制测试"""

    def test_issue_token_without_auth(self, client):
        """POST /api/auth/token 无需认证即可签发 Token"""
        response = client.post("/api/auth/token")
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_access_api_with_valid_token(self, client, auth_headers):
        """使用有效 Token 访问受保护 API 应成功"""
        response = client.get("/api/dashboard", headers=auth_headers)
        assert response.status_code == 200

    def test_access_api_without_token(self, client):
        """无 Token 访问受保护 API 应返回 401"""
        response = client.get("/api/dashboard")
        assert response.status_code == 401

    def test_access_api_with_invalid_token(self, client, invalid_auth_headers):
        """使用无效 Token 访问受保护 API 应返回 401"""
        response = client.get("/api/dashboard", headers=invalid_auth_headers)
        assert response.status_code == 401

    def test_access_api_with_expired_token(self, client):
        """使用过期 Token 访问受保护 API 应返回 401"""
        # 签发一个已过期的 Token（ttl_seconds=0）
        expired_token = create_access_token(secret="e2e-test-secret-key", ttl_seconds=0)
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = client.get("/api/dashboard", headers=headers)
        assert response.status_code == 401

    def test_all_protected_endpoints_require_auth(self, client):
        """所有受保护端点都应要求认证"""
        protected_endpoints = [
            "/api/dashboard",
            "/api/vdot/trend",
            "/api/training-load",
            "/api/training-load/trend",
            "/api/activities",
            "/api/body-signal/daily",
            "/api/body-signal/weekly",
            "/api/body-signal/alerts",
            "/api/plan/list",
            "/api/plan/calendar",
            "/api/evolution/status",
            "/api/evolution/tuning",
            "/api/evolution/reports",
            "/api/settings/profile",
            "/api/settings/system",
        ]

        for endpoint in protected_endpoints:
            response = client.get(endpoint)
            assert response.status_code == 401, f"{endpoint} should require auth"
