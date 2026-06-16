"""WebUI API 端点测试

覆盖所有 13 个 API 端点的基本功能、认证、错误处理。
"""


class TestHealthEndpoint:
    """健康检查端点测试"""

    def test_health_check_returns_ok(self, client):
        """GET /api/health 应返回状态 ok"""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data

    def test_health_check_no_auth_required(self, client):
        """健康检查不需要认证"""
        response = client.get("/api/health")
        assert response.status_code == 200


class TestAuthEndpoint:
    """认证端点测试"""

    def test_issue_token(self, client):
        """POST /api/auth/token 应签发令牌"""
        response = client.post("/api/auth/token")
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"


class TestDashboardAPI:
    """仪表盘 API 测试"""

    def test_get_dashboard_with_auth(self, client, auth_headers):
        """GET /api/dashboard 应返回汇总数据"""
        response = client.get("/api/dashboard", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "training_load" in data
        assert "body_signal" in data

    def test_get_dashboard_without_auth(self, client):
        """GET /api/dashboard 无认证应返回 401"""
        response = client.get("/api/dashboard")
        assert response.status_code == 401

    def test_get_dashboard_invalid_token(self, client, invalid_auth_headers):
        """GET /api/dashboard 无效令牌应返回 401"""
        response = client.get("/api/dashboard", headers=invalid_auth_headers)
        assert response.status_code == 401


class TestVdotAPI:
    """VDOT 趋势 API 测试"""

    def test_get_vdot_trend(self, client, auth_headers):
        """GET /api/vdot/trend 应返回趋势数据"""
        response = client.get("/api/vdot/trend", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "days" in data
        assert "count" in data

    def test_get_vdot_trend_with_days(self, client, auth_headers):
        """GET /api/vdot/trend?days=90 应支持天数参数"""
        response = client.get("/api/vdot/trend?days=90", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["days"] == 90

    def test_get_vdot_trend_invalid_days(self, client, auth_headers):
        """GET /api/vdot/trend?days=0 应返回 422"""
        response = client.get("/api/vdot/trend?days=0", headers=auth_headers)
        assert response.status_code == 422


class TestTrainingLoadAPI:
    """训练负荷 API 测试"""

    def test_get_training_load(self, client, auth_headers):
        """GET /api/training-load 应返回 ATL/CTL/TSB"""
        response = client.get("/api/training-load", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "atl" in data
        assert "ctl" in data
        assert "tsb" in data

    def test_get_training_load_trend(self, client, auth_headers):
        """GET /api/training-load/trend 应返回趋势数据"""
        response = client.get("/api/training-load/trend", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "trend_data" in data


class TestActivitiesAPI:
    """活动列表 API 测试"""

    def test_get_activities(self, client, auth_headers):
        """GET /api/activities 应返回活动列表"""
        response = client.get("/api/activities", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "count" in data

    def test_get_activities_with_limit(self, client, auth_headers):
        """GET /api/activities?limit=10 应支持数量限制"""
        response = client.get("/api/activities?limit=10", headers=auth_headers)
        assert response.status_code == 200

    def test_get_activity_detail_not_found(self, client, auth_headers):
        """GET /api/activities/{id} 不存在的活动应返回 404"""
        response = client.get("/api/activities/nonexistent-id", headers=auth_headers)
        assert response.status_code == 404


class TestBodySignalAPI:
    """身体信号 API 测试"""

    def test_get_daily_summary(self, client, auth_headers):
        """GET /api/body-signal/daily 应返回每日摘要"""
        response = client.get("/api/body-signal/daily", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "recovery_status" in data

    def test_get_weekly_summary(self, client, auth_headers):
        """GET /api/body-signal/weekly 应返回每周摘要"""
        response = client.get("/api/body-signal/weekly", headers=auth_headers)
        assert response.status_code == 200

    def test_get_alerts(self, client, auth_headers):
        """GET /api/body-signal/alerts 应返回预警列表"""
        response = client.get("/api/body-signal/alerts", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "alerts" in data


class TestPlanAPI:
    """训练计划 API 测试"""

    def test_list_plans(self, client, auth_headers):
        """GET /api/plan/list 应返回计划列表"""
        response = client.get("/api/plan/list", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "plans" in data

    def test_get_plan_calendar(self, client, auth_headers):
        """GET /api/plan/calendar 应返回日历数据"""
        response = client.get("/api/plan/calendar", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "days" in data

    def test_get_plan_detail_not_found(self, client, auth_headers):
        """GET /api/plan/{id} 不存在的计划应返回 404"""
        response = client.get("/api/plan/nonexistent-plan", headers=auth_headers)
        assert response.status_code == 404

    def test_get_plan_progress_not_found(self, client, auth_headers):
        """GET /api/plan/progress/{id} 不存在的计划应返回 404"""
        response = client.get(
            "/api/plan/progress/nonexistent-plan", headers=auth_headers
        )
        assert response.status_code == 404


class TestEvolutionAPI:
    """进化引擎 API 测试"""

    def test_get_evolution_status(self, client, auth_headers):
        """GET /api/evolution/status 应返回状态数据"""
        response = client.get("/api/evolution/status", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "engine_status" in data
        assert "trigger_conditions" in data

    def test_get_tuning_params(self, client, auth_headers):
        """GET /api/evolution/tuning 应返回调优参数"""
        response = client.get("/api/evolution/tuning", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "tone" in data
        assert "detail" in data
        assert "aggressive" in data
        assert "data_driven" in data

    def test_update_tuning_params(self, client, auth_headers):
        """PUT /api/evolution/tuning 应更新参数"""
        payload = {"tone": 0.7, "detail": 0.6}
        response = client.put(
            "/api/evolution/tuning", json=payload, headers=auth_headers
        )
        assert response.status_code == 200

    def test_list_reports(self, client, auth_headers):
        """GET /api/evolution/reports 应返回报告列表"""
        response = client.get("/api/evolution/reports", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "available_months" in data

    def test_get_report_invalid_format(self, client, auth_headers):
        """GET /api/evolution/reports/{month} 无效格式应返回 400"""
        response = client.get("/api/evolution/reports/invalid", headers=auth_headers)
        assert response.status_code == 400


class TestSettingsAPI:
    """设置中心 API 测试"""

    def test_get_profile(self, client, auth_headers):
        """GET /api/settings/profile 应返回个人信息"""
        response = client.get("/api/settings/profile", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "nickname" in data
        assert "age" in data

    def test_update_profile(self, client, auth_headers):
        """PUT /api/settings/profile 应更新个人信息"""
        payload = {"nickname": "新昵称"}
        response = client.put(
            "/api/settings/profile", json=payload, headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_get_system_config(self, client, auth_headers):
        """GET /api/settings/system 应返回系统配置"""
        response = client.get("/api/settings/system", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "data_dir" in data
        assert "version" in data
