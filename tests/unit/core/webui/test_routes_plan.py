"""Plan API 路由单元测试"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.core.webui.app import create_app


@pytest.fixture
def mock_plan() -> MagicMock:
    """创建Mock训练计划对象"""
    day1 = MagicMock()
    day1.date = "2026-06-01"
    day1.workout_type = MagicMock(value="easy", label="轻松跑")
    day1.distance_km = 8.0
    day1.target_pace_min_per_km = 6.0
    day1.duration_min = 48
    day1.completed = True
    day1.notes = "测试备注"
    day1.actual_distance_km = 8.2
    day1.actual_duration_min = 50
    day1.actual_avg_hr = 145

    day2 = MagicMock()
    day2.date = "2026-06-02"
    day2.workout_type = MagicMock(value="rest", label="休息")
    day2.distance_km = 0.0
    day2.target_pace_min_per_km = 0.0
    day2.duration_min = 0
    day2.completed = False
    day2.notes = ""
    day2.actual_distance_km = None
    day2.actual_duration_min = None
    day2.actual_avg_hr = None

    week = MagicMock()
    week.week_number = 1
    week.daily_plans = [day1, day2]

    plan = MagicMock()
    plan.plan_id = "plan-001"
    plan.plan_type = MagicMock(label="全马")
    plan.goal_date = "2026-09-01"
    plan.status = MagicMock(value="active")
    plan.start_date = "2026-06-01"
    plan.end_date = "2026-08-31"
    plan.weeks = [week]
    plan.updated_at = MagicMock(isoformat=lambda: "2026-06-01T00:00:00")
    plan.created_at = "2026-06-01T00:00:00"
    plan.to_dict.return_value = {
        "plan_id": "plan-001",
        "plan_type": "marathon",
        "goal_date": "2026-09-01",
        "status": "active",
        "weeks": [],
    }
    return plan


@pytest.fixture
def mock_context(mock_plan: MagicMock) -> MagicMock:
    context = MagicMock()
    context.config.get_webui_config.return_value = {
        "enabled": True,
        "host": "127.0.0.1",
        "port": 8766,
        "cors_origins": [],
        "token_secret": "test-secret",
        "token_ttl_s": 86400,
    }
    context.plan_manager.list_plans.return_value = [mock_plan]
    context.plan_manager.get_active_plan.return_value = mock_plan
    context.plan_manager.get_plan.return_value = mock_plan
    context.plan_manager.record_execution.return_value = {
        "success": True,
        "message": "已记录2026-06-01的执行反馈",
        "plan_id": "plan-001",
        "date": "2026-06-01",
    }
    return context


@pytest.fixture
def client(mock_context: MagicMock) -> TestClient:
    app = create_app(context=mock_context)
    return TestClient(app)


class TestPlanListEndpoint:
    """GET /api/plan/list"""

    def test_list_plans_returns_200(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/plan/list", headers=auth_headers)
        assert response.status_code == 200

    def test_list_plans_returns_plans_array(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/plan/list", headers=auth_headers)
        data = response.json()
        assert "plans" in data
        assert len(data["plans"]) == 1
        assert data["plans"][0]["plan_id"] == "plan-001"

    def test_list_plans_with_status_filter(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/plan/list?status=active", headers=auth_headers)
        assert response.status_code == 200

    def test_list_plans_requires_auth(self, client: TestClient) -> None:
        response = client.get("/api/plan/list")
        assert response.status_code == 401


class TestPlanCalendarEndpoint:
    """GET /api/plan/calendar"""

    def test_calendar_returns_200(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/plan/calendar", headers=auth_headers)
        assert response.status_code == 200

    def test_calendar_with_active_plan(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/plan/calendar", headers=auth_headers)
        data = response.json()
        assert data["plan_id"] == "plan-001"
        assert "days" in data
        assert len(data["days"]) == 2

    def test_calendar_no_active_plan(
        self, client: TestClient, auth_headers: dict[str, str], mock_context: MagicMock
    ) -> None:
        mock_context.plan_manager.get_active_plan.return_value = None
        response = client.get("/api/plan/calendar", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["plan_id"] is None
        assert data["days"] == []


class TestPlanDetailEndpoint:
    """GET /api/plan/{plan_id}"""

    def test_plan_detail_returns_200(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/plan/plan-001", headers=auth_headers)
        assert response.status_code == 200

    def test_plan_not_found(
        self, client: TestClient, auth_headers: dict[str, str], mock_context: MagicMock
    ) -> None:
        mock_context.plan_manager.get_plan.return_value = None
        response = client.get("/api/plan/nonexistent", headers=auth_headers)
        assert response.status_code == 404


class TestPlanProgressEndpoint:
    """GET /api/plan/progress/{plan_id}"""

    def test_progress_returns_200(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/plan/progress/plan-001", headers=auth_headers)
        assert response.status_code == 200

    def test_progress_contains_completion_rate(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/plan/progress/plan-001", headers=auth_headers)
        data = response.json()
        assert "completion_rate" in data
        assert "total_days" in data
        assert "completed_days" in data
        assert "weekly_summary" in data

    def test_progress_plan_not_found(
        self, client: TestClient, auth_headers: dict[str, str], mock_context: MagicMock
    ) -> None:
        mock_context.plan_manager.get_plan.return_value = None
        response = client.get("/api/plan/progress/nonexistent", headers=auth_headers)
        assert response.status_code == 404


class TestDailyPlanUpdateEndpoint:
    """PUT /api/plan/daily/{plan_id}/{date}"""

    def test_update_daily_plan_returns_200(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.put(
            "/api/plan/daily/plan-001/2026-06-01",
            json={
                "completion_rate": 0.8,
                "effort_score": 7,
                "notes": "感觉不错",
                "actual_distance_km": 8.2,
                "actual_duration_min": 50,
                "actual_avg_hr": 145,
            },
            headers=auth_headers,
        )
        assert response.status_code == 200

    def test_update_daily_plan_record_called(
        self, client: TestClient, auth_headers: dict[str, str], mock_context: MagicMock
    ) -> None:
        client.put(
            "/api/plan/daily/plan-001/2026-06-01",
            json={"completion_rate": 1.0, "effort_score": 5, "notes": "完成"},
            headers=auth_headers,
        )
        mock_context.plan_manager.record_execution.assert_called_once()

    def test_update_daily_plan_error_returns_400(
        self, client: TestClient, auth_headers: dict[str, str], mock_context: MagicMock
    ) -> None:
        mock_context.plan_manager.record_execution.side_effect = ValueError("参数无效")
        response = client.put(
            "/api/plan/daily/plan-001/2026-06-01",
            json={"completion_rate": 1.0},
            headers=auth_headers,
        )
        assert response.status_code == 400
