"""RunnerTools 记忆加载与计划状态查询单元测试"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.agents.tools import RunnerTools


class TestLoadSubagentMemory:
    """_load_subagent_memory 方法测试"""

    def test_load_memory_missing_file_returns_empty(self, tmp_path: Path):
        """记忆文件不存在时返回空 dict"""
        with patch.object(RunnerTools, "__init__", lambda self, ctx=None: None):
            tools = RunnerTools()
            tools._runner_config = MagicMock()
            tools._runner_config.base_dir = tmp_path
            result = tools._load_subagent_memory("coach")
        assert result == {}

    def test_load_memory_valid_json_returns_dict(self, tmp_path: Path):
        """有效 JSON 文件返回解析后的 dict"""
        memory_dir = tmp_path / "memory" / "subagents"
        memory_dir.mkdir(parents=True)
        (memory_dir / "coach.json").write_text(
            json.dumps({"user_goal": "全马破4"}, ensure_ascii=False),
            encoding="utf-8",
        )
        with patch.object(RunnerTools, "__init__", lambda self, ctx=None: None):
            tools = RunnerTools()
            tools._runner_config = MagicMock()
            tools._runner_config.base_dir = tmp_path
            result = tools._load_subagent_memory("coach")
        assert result == {"user_goal": "全马破4"}

    def test_load_memory_corrupt_json_returns_empty(self, tmp_path: Path):
        """损坏的 JSON 返回空 dict"""
        memory_dir = tmp_path / "memory" / "subagents"
        memory_dir.mkdir(parents=True)
        (memory_dir / "coach.json").write_text("{invalid json", encoding="utf-8")
        with patch.object(RunnerTools, "__init__", lambda self, ctx=None: None):
            tools = RunnerTools()
            tools._runner_config = MagicMock()
            tools._runner_config.base_dir = tmp_path
            result = tools._load_subagent_memory("coach")
        assert result == {}

    def test_load_memory_unknown_role_returns_empty(self, tmp_path: Path):
        """未知角色返回空 dict"""
        with patch.object(RunnerTools, "__init__", lambda self, ctx=None: None):
            tools = RunnerTools()
            tools._runner_config = MagicMock()
            tools._runner_config.base_dir = tmp_path
            result = tools._load_subagent_memory("unknown_role")
        assert result == {}


class TestGetPlanStatusSafe:
    """_get_plan_status_safe 方法测试"""

    def test_get_plan_status_no_plan_manager_returns_none(self):
        """无 plan_manager 时返回 None"""
        with patch.object(RunnerTools, "__init__", lambda self, ctx=None: None):
            tools = RunnerTools()
            tools._context = MagicMock()
            tools._context.plan_manager = None
            result = tools._get_plan_status_safe()
        assert result is None

    def test_get_plan_status_exception_returns_none(self):
        """plan_manager 抛异常时返回 None"""
        with patch.object(RunnerTools, "__init__", lambda self, ctx=None: None):
            tools = RunnerTools()
            tools._context = MagicMock()
            tools._context.plan_manager = MagicMock()
            tools._context.plan_manager.list_plans.side_effect = Exception("db error")
            result = tools._get_plan_status_safe()
        assert result is None


class TestGetInjuryRiskSafe:
    """_get_injury_risk_safe 方法测试（spec 验收标准 #4）"""

    def test_get_injury_risk_safe_success(self):
        """predictor 正常时返回预测结果"""
        with patch.object(RunnerTools, "__init__", lambda self, ctx=None: None):
            tools = RunnerTools()
            tools.predict_injury_risk = MagicMock(
                return_value={
                    "success": True,
                    "data": {"risk_level": "low", "score": 0.2},
                }
            )
            result = tools._get_injury_risk_safe(days=21)
        assert result == {"success": True, "data": {"risk_level": "low", "score": 0.2}}

    def test_get_injury_risk_safe_fallback(self):
        """predictor 抛异常时返回 error dict 而非抛异常（spec §6 / 验收标准 #4）"""
        with patch.object(RunnerTools, "__init__", lambda self, ctx=None: None):
            tools = RunnerTools()
            tools.predict_injury_risk = MagicMock(side_effect=Exception("model error"))
            result = tools._get_injury_risk_safe(days=21)
        assert "error" in result
        assert result["fallback"] == "rule_baseline"
