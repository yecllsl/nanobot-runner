"""_prepare_subagent_context 新角色分支单元测试"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.agents.tools import RunnerTools


@pytest.fixture
def runner_tools():
    """构造带 mock 依赖的 RunnerTools"""
    with patch.object(RunnerTools, "__init__", lambda self, ctx=None: None):
        tools = RunnerTools()
        tools._context = MagicMock()
        tools._runner_config = MagicMock()
        tools._runner_config.base_dir = MagicMock()
        tools._runner_config.base_dir.__truediv__ = MagicMock(return_value=MagicMock())
        # mock 业务方法
        tools.get_vdot_trend = MagicMock(return_value={"vdot": 45.2})
        tools.get_training_load = MagicMock(return_value={"atl": 50, "ctl": 60})
        tools.get_recent_runs = MagicMock(return_value=[{"distance_km": 10}])
        tools.predict_injury_risk = MagicMock(
            return_value={"success": True, "data": {"risk_level": "low"}}
        )
        tools.get_hrv_analysis = MagicMock(return_value={"rmssd": 35.0})
        tools.get_fatigue_score = MagicMock(return_value={"score": 3})
        tools.get_recovery_status = MagicMock(return_value={"status": "good"})
        tools.get_hr_drift_analysis = MagicMock(return_value={"drift": 5.0})
        # report_writer 向后兼容分支会调用 get_running_stats（访问 self.analytics）
        tools.get_running_stats = MagicMock(return_value={"total_runs": 0})
        tools._load_subagent_memory = MagicMock(return_value={"user_goal": "marathon"})
        tools._get_plan_status_safe = MagicMock(return_value={"plan_id": "p1"})
        return tools


class TestPrepareCoachContext:
    """教练角色预查询测试"""

    def test_coach_context_contains_vdot(self, runner_tools: RunnerTools):
        ctx = runner_tools._prepare_subagent_context(
            subagent_type="coach", user_request="分析训练"
        )
        assert "vdot_trend" in ctx
        assert ctx["vdot_trend"] == {"vdot": 45.2}

    def test_coach_context_contains_training_load(self, runner_tools: RunnerTools):
        ctx = runner_tools._prepare_subagent_context(
            subagent_type="coach", user_request="分析训练"
        )
        assert "training_load" in ctx

    def test_coach_context_contains_recent_runs(self, runner_tools: RunnerTools):
        ctx = runner_tools._prepare_subagent_context(
            subagent_type="coach", user_request="分析训练"
        )
        assert "recent_runs" in ctx

    def test_coach_context_contains_plan_status(self, runner_tools: RunnerTools):
        ctx = runner_tools._prepare_subagent_context(
            subagent_type="coach", user_request="分析训练"
        )
        assert ctx["plan_status"] == {"plan_id": "p1"}

    def test_coach_context_contains_memory(self, runner_tools: RunnerTools):
        ctx = runner_tools._prepare_subagent_context(
            subagent_type="coach", user_request="分析训练"
        )
        assert ctx["memory"] == {"user_goal": "marathon"}

    def test_coach_context_contains_user_request(self, runner_tools: RunnerTools):
        ctx = runner_tools._prepare_subagent_context(
            subagent_type="coach", user_request="帮我安排下周训练"
        )
        assert ctx["user_request"] == "帮我安排下周训练"


class TestPrepareInjuryContext:
    """伤病预防师角色预查询测试"""

    def test_injury_context_contains_injury_risk(self, runner_tools: RunnerTools):
        ctx = runner_tools._prepare_subagent_context(
            subagent_type="injury_prevention", user_request="膝盖不舒服"
        )
        assert "injury_risk" in ctx
        assert ctx["injury_risk"]["success"] is True

    def test_injury_context_contains_hrv(self, runner_tools: RunnerTools):
        ctx = runner_tools._prepare_subagent_context(
            subagent_type="injury_prevention", user_request="评估"
        )
        assert "hrv_analysis" in ctx

    def test_injury_context_contains_fatigue(self, runner_tools: RunnerTools):
        ctx = runner_tools._prepare_subagent_context(
            subagent_type="injury_prevention", user_request="评估"
        )
        assert "fatigue" in ctx

    def test_injury_context_contains_recovery(self, runner_tools: RunnerTools):
        ctx = runner_tools._prepare_subagent_context(
            subagent_type="injury_prevention", user_request="评估"
        )
        assert "recovery" in ctx

    def test_injury_context_contains_hr_drift(self, runner_tools: RunnerTools):
        ctx = runner_tools._prepare_subagent_context(
            subagent_type="injury_prevention", user_request="评估"
        )
        assert "hr_drift" in ctx

    def test_injury_context_contains_memory(self, runner_tools: RunnerTools):
        ctx = runner_tools._prepare_subagent_context(
            subagent_type="injury_prevention", user_request="评估"
        )
        assert "memory" in ctx

    def test_injury_context_contains_training_load(self, runner_tools: RunnerTools):
        ctx = runner_tools._prepare_subagent_context(
            subagent_type="injury_prevention", user_request="评估"
        )
        assert "training_load" in ctx


class TestPrepareContextBackwardCompat:
    """旧角色（data_analyst/report_writer）向后兼容测试"""

    def test_data_analyst_still_works(self, runner_tools: RunnerTools):
        """data_analyst 分支应保持原有行为"""
        ctx = runner_tools._prepare_subagent_context(
            subagent_type="data_analyst", user_request="分析"
        )
        # data_analyst 原本就查询 vdot_trend 和 training_load
        assert "vdot_trend" in ctx
        assert "training_load" in ctx

    def test_report_writer_still_works(self, runner_tools: RunnerTools):
        """report_writer 分支应保持原有行为"""
        ctx = runner_tools._prepare_subagent_context(
            subagent_type="report_writer", user_request="周报"
        )
        assert "running_stats" in ctx or "recent_runs" in ctx
