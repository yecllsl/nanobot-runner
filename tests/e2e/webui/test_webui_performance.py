"""WebUI 性能测试

测试 WebUI 页面加载性能、API 响应时间、图表渲染时间。
使用 FastAPI TestClient 进行 API 性能测试（无需运行服务器）。
"""

import time


class TestAPIResponseTime:
    """API 响应时间测试"""

    def test_health_api_response_time(self, client):
        """GET /api/health 响应时间应 < 200ms"""
        start = time.perf_counter()
        response = client.get("/api/health")
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert response.status_code == 200
        assert elapsed_ms < 200, f"响应时间 {elapsed_ms:.0f}ms 超过 200ms 阈值"

    def test_dashboard_api_response_time(self, client, auth_headers):
        """GET /api/dashboard 响应时间应 < 500ms"""
        start = time.perf_counter()
        response = client.get("/api/dashboard", headers=auth_headers)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert response.status_code == 200
        assert elapsed_ms < 500, f"响应时间 {elapsed_ms:.0f}ms 超过 500ms 阈值"

    def test_vdot_api_response_time(self, client, auth_headers):
        """GET /api/vdot/trend 响应时间应 < 500ms"""
        start = time.perf_counter()
        response = client.get("/api/vdot/trend", headers=auth_headers)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert response.status_code == 200
        assert elapsed_ms < 500, f"响应时间 {elapsed_ms:.0f}ms 超过 500ms 阈值"

    def test_training_load_api_response_time(self, client, auth_headers):
        """GET /api/training-load 响应时间应 < 500ms"""
        start = time.perf_counter()
        response = client.get("/api/training-load", headers=auth_headers)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert response.status_code == 200
        assert elapsed_ms < 500, f"响应时间 {elapsed_ms:.0f}ms 超过 500ms 阈值"

    def test_activities_api_response_time(self, client, auth_headers):
        """GET /api/activities 响应时间应 < 500ms"""
        start = time.perf_counter()
        response = client.get("/api/activities", headers=auth_headers)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert response.status_code == 200
        assert elapsed_ms < 500, f"响应时间 {elapsed_ms:.0f}ms 超过 500ms 阈值"

    def test_body_signal_api_response_time(self, client, auth_headers):
        """GET /api/body-signal/daily 响应时间应 < 500ms"""
        start = time.perf_counter()
        response = client.get("/api/body-signal/daily", headers=auth_headers)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert response.status_code == 200
        assert elapsed_ms < 500, f"响应时间 {elapsed_ms:.0f}ms 超过 500ms 阈值"

    def test_evolution_status_api_response_time(self, client, auth_headers):
        """GET /api/evolution/status 响应时间应 < 500ms"""
        start = time.perf_counter()
        response = client.get("/api/evolution/status", headers=auth_headers)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert response.status_code == 200
        assert elapsed_ms < 500, f"响应时间 {elapsed_ms:.0f}ms 超过 500ms 阈值"

    def test_settings_profile_api_response_time(self, client, auth_headers):
        """GET /api/settings/profile 响应时间应 < 500ms"""
        start = time.perf_counter()
        response = client.get("/api/settings/profile", headers=auth_headers)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert response.status_code == 200
        assert elapsed_ms < 500, f"响应时间 {elapsed_ms:.0f}ms 超过 500ms 阈值"
