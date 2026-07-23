"""UpdateSubagentMemoryTool 工具测试"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.agents.tools import RunnerTools, UpdateSubagentMemoryTool


@pytest.fixture
def tool_and_tools(tmp_path: Path):
    """构造工具实例和 mock RunnerTools"""
    with patch.object(RunnerTools, "__init__", lambda self, ctx=None: None):
        runner_tools = RunnerTools()
        runner_tools._runner_config = MagicMock()
        runner_tools._runner_config.base_dir = tmp_path
        runner_tools._load_subagent_memory = MagicMock(return_value={})
        tool = UpdateSubagentMemoryTool(runner_tools)
        return tool, runner_tools


class TestUpdateSubagentMemoryTool:
    """update_subagent_memory 工具测试"""

    def test_tool_name(self, tool_and_tools):
        tool, _ = tool_and_tools
        assert tool.name == "update_subagent_memory"

    def test_update_memory_writes_json(self, tool_and_tools, tmp_path: Path):
        """更新记忆应写入 JSON 文件"""
        tool, runner_tools = tool_and_tools
        runner_tools._load_subagent_memory.return_value = {"existing": "data"}

        result = tool.runner_tools._update_subagent_memory(
            role="coach", key="user_goal", value="全马破4"
        )

        memory_file = tmp_path / "memory" / "subagents" / "coach.json"
        assert memory_file.exists()
        saved = json.loads(memory_file.read_text(encoding="utf-8"))
        assert saved["existing"] == "data"
        assert saved["user_goal"] == "全马破4"

    def test_update_memory_returns_success(self, tool_and_tools):
        """更新记忆返回 success=True"""
        tool, runner_tools = tool_and_tools
        result = tool.runner_tools._update_subagent_memory(
            role="coach", key="user_goal", value="marathon"
        )
        assert result["success"] is True

    def test_update_memory_unknown_role_still_writes(
        self, tool_and_tools, tmp_path: Path
    ):
        """未知角色也应能写入（不限制角色名，宽容）"""
        tool, runner_tools = tool_and_tools
        result = tool.runner_tools._update_subagent_memory(
            role="custom_role", key="k", value="v"
        )
        assert result["success"] is True
        assert (tmp_path / "memory" / "subagents" / "custom_role.json").exists()
