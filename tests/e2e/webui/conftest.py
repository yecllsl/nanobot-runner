"""WebUI E2E 测试配置 (v0.29.0)

提供 API 层和 UI 层测试的公共 fixture。
API 测试使用 FastAPI TestClient + Mock Context（无需运行服务器）。
UI 测试使用 Playwright（需要运行 WebUI 服务器）。
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.core.webui.app import create_app
from src.core.webui.auth import create_access_token


# ============================================================
# API 测试公共 Fixture
# ============================================================


@pytest.fixture
def webui_config() -> dict:
    """WebUI 基础配置"""
    return {
        "enabled": True,
        "host": "127.0.0.1",
        "port": 8766,
        "cors_origins": ["http://127.0.0.1:8765"],
        "token_secret": "e2e-test-secret-key",
        "token_ttl_s": 86400,
    }


@pytest.fixture
def mock_context(webui_config: dict) -> MagicMock:
    """创建完整的 Mock AppContext，覆盖所有 WebUI 路由依赖"""
    context = MagicMock()
    context.config.get_webui_config.return_value = webui_config
    context.config.load_config.return_value = {
        "profile": {
            "nickname": "E2E测试跑者",
            "age": 30,
            "gender": "male",
            "max_heart_rate": 190,
            "resting_heart_rate": 60,
        }
    }
    context.config.data_dir = MagicMock()
    context.config.data_dir.__str__ = lambda self: "/test/data"

    # Analytics
    context.analytics.get_training_load.return_value = {
        "atl": 50.0,
        "ctl": 60.0,
        "tsb": 10.0,
        "fitness_status": "恢复良好",
        "training_advice": "体能充沛",
        "days_analyzed": 42,
        "runs_count": 20,
    }
    context.analytics.get_training_load_trend.return_value = {
        "trend_data": [
            {"date": "2026-06-01", "tss": 85.0, "atl": 48.0, "ctl": 55.0, "tsb": 7.0},
            {"date": "2026-06-02", "tss": 0.0, "atl": 42.0, "ctl": 55.5, "tsb": 13.5},
        ],
        "summary": {
            "current_atl": 50.0,
            "current_ctl": 60.0,
            "current_tsb": 10.0,
            "status": "恢复良好",
            "recommendation": "体能充沛",
        },
        "days_analyzed": 90,
        "total_runs": 20,
    }

    # VDOT
    vdot_item = MagicMock()
    vdot_item.to_dict.return_value = {
        "date": "2026-06-10",
        "vdot": 45.2,
        "distance": 10000.0,
        "duration": 3000.0,
    }
    context.analytics.get_vdot_trend.return_value = [vdot_item]

    # Session
    session = MagicMock()
    session.to_dict.return_value = {
        "timestamp": "2026-06-10T07:00:00",
        "distance_km": 10.0,
        "duration_min": 50.0,
        "avg_pace_sec_km": 300.0,
        "avg_heart_rate": 155.0,
        "distance_m": 10000.0,
        "duration_s": 3000.0,
        "max_heart_rate": 175.0,
        "calories": 650.0,
    }
    context.session_repo.get_recent_sessions.return_value = [session]

    # Body Signal
    body_summary = MagicMock()
    body_summary.to_dict.return_value = {
        "recovery_status": "good",
        "fatigue_score": 20.0,
        "hrv_score": 65.0,
        "data_quality": "sufficient",
        "daily_summary": "今日状态良好",
        "training_advice": "可以进行训练",
        "alerts": [],
    }
    context.body_signal_engine.get_daily_summary.return_value = body_summary

    weekly_summary = MagicMock()
    weekly_summary.to_dict.return_value = {
        "week_start": "2026-06-08",
        "week_end": "2026-06-14",
        "avg_recovery": 72.0,
        "avg_fatigue": 35.0,
        "trend": "stable",
    }
    context.body_signal_engine.get_weekly_summary.return_value = weekly_summary
    context.body_signal_engine.check_alerts.return_value = []

    # Plan Manager
    context.plan_manager.list_plans.return_value = []
    context.plan_manager.get_active_plan.return_value = None
    context.plan_manager.get_plan.return_value = None

    # Evolution Engine
    trigger_result = MagicMock()
    trigger_result.triggered_actions = []
    context.evolution_engine.check_evolution_triggers.return_value = trigger_result
    context.evolution_engine.check_triggers.return_value = trigger_result

    tuning_params = MagicMock()
    tuning_params.tone_intensity = 0.5
    tuning_params.detail_level_score = 0.5
    tuning_params.recommendation_aggressiveness = 0.5
    tuning_params.data_driven_weight = 0.5
    context.evolution_engine.get_prompt_tuning_params.return_value = tuning_params
    context.evolution_engine.adjust_prompt_params.return_value = tuning_params
    context.evolution_engine.get_available_report_months.return_value = []

    context.evolution_engine._store = MagicMock()
    context.evolution_engine._store.data_dir = MagicMock()

    return context


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """有效的认证请求头"""
    token = create_access_token(secret="e2e-test-secret-key", ttl_seconds=3600)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def invalid_auth_headers() -> dict[str, str]:
    """无效的认证请求头"""
    return {"Authorization": "Bearer invalid-token-xxx"}


@pytest.fixture
def client(mock_context: MagicMock) -> TestClient:
    """创建 FastAPI TestClient"""
    app = create_app(context=mock_context)
    return TestClient(app)


# ============================================================
# Playwright UI 测试配置
# ============================================================


# UI 测试的 base_url，需要服务器预先启动
# Gateway 端口 8765 提供前端 SPA 页面
# API 端口 8766 提供后端 API 接口
WEBUI_BASE_URL = "http://127.0.0.1:8766"  # 前端页面（数据可视化SPA）
API_BASE_URL = "http://127.0.0.1:8766"  # 后端 API


@pytest.fixture
def webui_base_url() -> str:
    """WebUI 前端基础 URL（Gateway 端口）"""
    return WEBUI_BASE_URL


@pytest.fixture
def api_base_url() -> str:
    """WebUI API 基础 URL（API 端口）"""
    return API_BASE_URL
