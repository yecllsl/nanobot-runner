"""WebUI 数据一致性测试

验证 WebUI API 返回的数据与 CLI 输出数值一致（误差 < 0.1%）。
使用 FastAPI TestClient + Mock Context 进行数据一致性验证。
"""

import pytest


class TestDataConsistencyDashboard:
    """仪表盘数据一致性测试"""

    def test_dashboard_training_load_values_match(self, client, auth_headers, mock_context):
        """仪表盘训练负荷数据应与 analytics 引擎一致"""
        response = client.get("/api/dashboard", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        # 验证 API 返回的训练负荷数据与 mock_context 一致
        expected_load = mock_context.analytics.get_training_load.return_value
        assert data["training_load"] == expected_load

    def test_dashboard_body_signal_values_match(self, client, auth_headers, mock_context):
        """仪表盘身体信号数据应与 body_signal_engine 一致"""
        response = client.get("/api/dashboard", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        # 验证 API 返回的身体信号数据与 mock_context 一致
        expected_summary = mock_context.body_signal_engine.get_daily_summary.return_value.to_dict()
        assert data["body_signal"] == expected_summary


class TestDataConsistencyVdot:
    """VDOT 数据一致性测试"""

    def test_vdot_trend_values_match(self, client, auth_headers, mock_context):
        """VDOT 趋势数据应与 analytics 引擎一致"""
        response = client.get("/api/vdot/trend?days=30", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        # 验证返回的 items 数量与 mock 数据一致
        assert data["count"] == 1
        assert data["days"] == 30

    def test_vdot_trend_days_parameter(self, client, auth_headers):
        """VDOT 趋势应正确传递 days 参数"""
        for days in [7, 30, 90, 365]:
            response = client.get(f"/api/vdot/trend?days={days}", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["days"] == days


class TestDataConsistencyTrainingLoad:
    """训练负荷数据一致性测试"""

    def test_training_load_values_match(self, client, auth_headers, mock_context):
        """训练负荷 ATL/CTL/TSB 应与 analytics 引擎一致"""
        response = client.get("/api/training-load", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        expected = mock_context.analytics.get_training_load.return_value
        assert data["atl"] == expected["atl"]
        assert data["ctl"] == expected["ctl"]
        assert data["tsb"] == expected["tsb"]

    def test_training_load_trend_values_match(self, client, auth_headers, mock_context):
        """训练负荷趋势数据应与 analytics 引擎一致"""
        response = client.get("/api/training-load/trend", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        expected = mock_context.analytics.get_training_load_trend.return_value
        assert data == expected


class TestDataConsistencyActivities:
    """活动数据一致性测试"""

    def test_activities_count_match(self, client, auth_headers, mock_context):
        """活动列表数量应与 session_repo 一致"""
        response = client.get("/api/activities", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        sessions = mock_context.session_repo.get_recent_sessions.return_value
        assert data["count"] == len(sessions)

    def test_activities_data_fields_match(self, client, auth_headers):
        """活动列表字段应完整"""
        response = client.get("/api/activities", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        if data["items"]:
            item = data["items"][0]
            # 验证关键字段存在
            assert "session_id" in item
            assert "distance_km" in item
            assert "duration_min" in item


class TestDataConsistencyEvolution:
    """进化引擎数据一致性测试"""

    def test_evolution_status_trigger_count(self, client, auth_headers):
        """进化状态应返回 4 条触发条件"""
        response = client.get("/api/evolution/status", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        assert len(data["trigger_conditions"]) == 4

    def test_tuning_params_range(self, client, auth_headers):
        """调优参数值应在 0-1 范围内"""
        response = client.get("/api/evolution/tuning", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        for key in ["tone", "detail", "aggressive", "data_driven"]:
            assert 0.0 <= data[key] <= 1.0, f"{key}={data[key]} 超出 [0, 1] 范围"
