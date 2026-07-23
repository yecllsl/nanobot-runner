"""_invoke_subagent valid_types 扩展测试"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.agents.tools import RunnerTools


@pytest.fixture
def runner_tools():
    with patch.object(RunnerTools, "__init__", lambda self, ctx=None: None):
        tools = RunnerTools()
        return tools


class TestInvokeSubagentValidTypes:
    """_invoke_subagent 应接受新角色类型"""

    def test_coach_is_valid_type(self, runner_tools: RunnerTools):
        result = runner_tools._invoke_subagent("coach", "task content")
        assert result["status"] != "error"
        assert result["subagent_type"] == "coach"

    def test_injury_prevention_is_valid_type(self, runner_tools: RunnerTools):
        result = runner_tools._invoke_subagent("injury_prevention", "task content")
        assert result["status"] != "error"
        assert result["subagent_type"] == "injury_prevention"

    def test_unknown_type_returns_error(self, runner_tools: RunnerTools):
        result = runner_tools._invoke_subagent("unknown", "task content")
        assert result["status"] == "error"


class TestSpawnSubagentUsesRoleBuildTask:
    """spawn_subagent 对新角色应使用 ROLES[type].build_task"""

    def test_spawn_coach_uses_role_prompt(self, runner_tools: RunnerTools):
        """coach 角色的 task 应包含教练 prompt"""
        with (
            patch.object(runner_tools, "_prepare_subagent_context") as mock_ctx,
            patch.object(runner_tools, "_invoke_subagent") as mock_invoke,
        ):
            mock_ctx.return_value = {"vdot": 45.2}
            mock_invoke.return_value = {"status": "ready_to_spawn"}
            runner_tools.spawn_subagent(subagent_type="coach", user_request="分析训练")
        # 验证 _invoke_subagent 被调用时 task 包含教练 prompt
        call_args = mock_invoke.call_args
        task = call_args.kwargs.get("task") or call_args.args[1]
        assert "教练" in task
        assert "VDOT" in task

    def test_spawn_injury_uses_role_prompt(self, runner_tools: RunnerTools):
        """injury_prevention 角色的 task 应包含伤病预防师 prompt"""
        with (
            patch.object(runner_tools, "_prepare_subagent_context") as mock_ctx,
            patch.object(runner_tools, "_invoke_subagent") as mock_invoke,
        ):
            mock_ctx.return_value = {"risk": "low"}
            mock_invoke.return_value = {"status": "ready_to_spawn"}
            runner_tools.spawn_subagent(
                subagent_type="injury_prevention", user_request="评估风险"
            )
        call_args = mock_invoke.call_args
        task = call_args.kwargs.get("task") or call_args.args[1]
        assert "伤病预防师" in task or "伤病" in task
