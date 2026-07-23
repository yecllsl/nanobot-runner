"""spawn_subagent 新角色集成测试

验证从 spawn_subagent 入口到 _invoke_subagent 的完整调用链，
Mock 到 SubagentManager.spawn 边界（不实际调用 nanobot 底座）。
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.agents.tools import RunnerTools


@pytest.fixture
def runner_tools_with_mocks():
    """构造完整 mock 的 RunnerTools，业务方法返回固定数据"""
    with patch.object(RunnerTools, "__init__", lambda self, ctx=None: None):
        tools = RunnerTools()
        tools._context = MagicMock()
        tools._runner_config = MagicMock()
        tools._runner_config.base_dir = MagicMock()
        # 业务方法 mock
        tools.get_vdot_trend = MagicMock(return_value={"vdot": 45.2, "trend": "up"})
        tools.get_training_load = MagicMock(
            return_value={"atl": 50, "ctl": 60, "tsb": 10}
        )
        tools.get_recent_runs = MagicMock(
            return_value=[{"distance_km": 10, "duration_min": 50}]
        )
        tools.predict_injury_risk = MagicMock(
            return_value={"success": True, "data": {"risk_level": "low", "score": 0.2}}
        )
        tools.get_hrv_analysis = MagicMock(
            return_value={"rmssd": 35.0, "trend": "stable"}
        )
        tools.get_fatigue_score = MagicMock(return_value={"score": 3, "level": "low"})
        tools.get_recovery_status = MagicMock(
            return_value={"status": "good", "readiness": 85}
        )
        tools.get_hr_drift_analysis = MagicMock(return_value={"drift_percent": 5.0})
        # report_writer 分支调用 self.get_running_stats()（src/agents/tools.py:1692），
        # 真实方法依赖 self.analytics（被 no-op __init__ 跳过），不 mock 会抛 AttributeError 逃出 try/except
        tools.get_running_stats = MagicMock(return_value={"total_runs": 0})
        tools._load_subagent_memory = MagicMock(return_value={"user_goal": "marathon"})
        tools._get_plan_status_safe = MagicMock(return_value={"plan_id": "plan_001"})
        return tools


class TestSpawnCoachIntegration:
    """教练角色端到端集成测试"""

    def test_spawn_coach_returns_success(self, runner_tools_with_mocks: RunnerTools):
        result = runner_tools_with_mocks.spawn_subagent(
            subagent_type="coach", user_request="帮我分析近期训练"
        )
        assert result["success"] is True
        assert result["data"]["subagent_type"] == "coach"
        assert "result" in result["data"]

    def test_spawn_coach_task_contains_coach_prompt(
        self, runner_tools_with_mocks: RunnerTools
    ):
        result = runner_tools_with_mocks.spawn_subagent(
            subagent_type="coach", user_request="分析训练"
        )
        task_preview = result["data"].get("task_preview", "")
        assert "教练" in task_preview or "教练" in str(result["data"])

    def test_spawn_coach_task_contains_vdot_data(
        self, runner_tools_with_mocks: RunnerTools
    ):
        """task 应包含预查询的 VDOT 数据"""
        result = runner_tools_with_mocks.spawn_subagent(
            subagent_type="coach", user_request="分析训练"
        )
        # task_preview 或 result 应包含 vdot 数据
        data_str = str(result["data"])
        assert "45.2" in data_str or "vdot" in data_str.lower()

    def test_spawn_coach_context_size_under_8000(
        self, runner_tools_with_mocks: RunnerTools
    ):
        """上下文大小应小于 8000 字符"""
        result = runner_tools_with_mocks.spawn_subagent(
            subagent_type="coach", user_request="分析训练"
        )
        assert result["data"]["context_size"] <= 8000


class TestSpawnInjuryPreventionIntegration:
    """伤病预防师角色端到端集成测试"""

    def test_spawn_injury_returns_success(self, runner_tools_with_mocks: RunnerTools):
        result = runner_tools_with_mocks.spawn_subagent(
            subagent_type="injury_prevention", user_request="评估伤病风险"
        )
        assert result["success"] is True
        assert result["data"]["subagent_type"] == "injury_prevention"

    def test_spawn_injury_task_contains_risk_data(
        self, runner_tools_with_mocks: RunnerTools
    ):
        """task 应包含伤病风险预测数据"""
        result = runner_tools_with_mocks.spawn_subagent(
            subagent_type="injury_prevention", user_request="评估风险"
        )
        data_str = str(result["data"])
        assert "risk_level" in data_str or "low" in data_str

    def test_spawn_injury_task_contains_injury_prompt(
        self, runner_tools_with_mocks: RunnerTools
    ):
        result = runner_tools_with_mocks.spawn_subagent(
            subagent_type="injury_prevention", user_request="评估风险"
        )
        task_preview = result["data"].get("task_preview", "")
        assert "伤病" in task_preview or "伤病" in str(result["data"])


class TestSpawnUnknownRoleIntegration:
    """未知角色应返回 error"""

    def test_spawn_unknown_returns_error(self, runner_tools_with_mocks: RunnerTools):
        result = runner_tools_with_mocks.spawn_subagent(
            subagent_type="unknown_role", user_request="请求"
        )
        # 未知角色走 _invoke_subagent 的 error 分支
        # spawn_subagent 仍返回 success=True（因为预查询成功），
        # 但 result 中会包含 error 状态
        # 检查 _invoke_subagent 返回的 status
        invoke_result = result["data"]["result"]
        assert invoke_result["status"] == "error"


class TestSpawnBackwardCompatIntegration:
    """旧角色向后兼容"""

    def test_spawn_data_analyst_still_works(self, runner_tools_with_mocks: RunnerTools):
        result = runner_tools_with_mocks.spawn_subagent(
            subagent_type="data_analyst", user_request="分析数据"
        )
        assert result["success"] is True
        assert result["data"]["subagent_type"] == "data_analyst"

    def test_spawn_report_writer_still_works(
        self, runner_tools_with_mocks: RunnerTools
    ):
        result = runner_tools_with_mocks.spawn_subagent(
            subagent_type="report_writer", user_request="生成周报", report_type="weekly"
        )
        assert result["success"] is True
        assert result["data"]["subagent_type"] == "report_writer"
