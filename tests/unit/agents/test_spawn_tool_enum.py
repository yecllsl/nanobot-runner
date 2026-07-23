"""SpawnSubagentTool 枚举扩展测试"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.agents.tools import TOOL_DESCRIPTIONS
from src.agents.tools_twin import SpawnSubagentTool


class TestSpawnSubagentToolEnum:
    """SpawnSubagentTool.parameters 应包含 4 个角色"""

    @pytest.fixture
    def tool(self):
        runner_tools = MagicMock()
        return SpawnSubagentTool(runner_tools)

    def test_enum_contains_coach(self, tool: SpawnSubagentTool):
        enum_values = tool.parameters["properties"]["subagent_type"]["enum"]
        assert "coach" in enum_values

    def test_enum_contains_injury_prevention(self, tool: SpawnSubagentTool):
        enum_values = tool.parameters["properties"]["subagent_type"]["enum"]
        assert "injury_prevention" in enum_values

    def test_enum_contains_legacy_types(self, tool: SpawnSubagentTool):
        """旧角色应保留"""
        enum_values = tool.parameters["properties"]["subagent_type"]["enum"]
        assert "data_analyst" in enum_values
        assert "report_writer" in enum_values

    def test_enum_has_four_types(self, tool: SpawnSubagentTool):
        enum_values = tool.parameters["properties"]["subagent_type"]["enum"]
        assert len(enum_values) == 4


class TestToolDescriptions:
    """TOOL_DESCRIPTIONS 应更新描述"""

    def test_description_mentions_coach(self):
        desc = TOOL_DESCRIPTIONS["spawn_subagent"]["description"]
        assert "教练" in desc or "coach" in desc

    def test_description_mentions_injury(self):
        desc = TOOL_DESCRIPTIONS["spawn_subagent"]["description"]
        assert "伤病" in desc or "injury" in desc

    def test_parameters_subagent_type_mentions_coach(self):
        params = TOOL_DESCRIPTIONS["spawn_subagent"]["parameters"]
        assert "教练" in params["subagent_type"] or "coach" in params["subagent_type"]
