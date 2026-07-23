"""subagent_roles 模块单元测试"""

from __future__ import annotations

from src.agents.subagent_roles import (
    COACH_PROMPT,
    INJURY_PROMPT,
    ROLES,
    SubagentRole,
)


class TestSubagentRole:
    """SubagentRole 数据类测试"""

    def test_role_build_task_contains_prompt(self):
        """build_task 输出应包含角色 prompt 片段"""
        role = ROLES["coach"]
        task = role.build_task("帮我分析训练", {"vdot": 45.2})
        assert "教练" in task
        assert COACH_PROMPT.split("\n")[0] in task

    def test_role_build_task_contains_user_request(self):
        """build_task 输出应包含用户请求"""
        role = ROLES["injury_prevention"]
        task = role.build_task("膝盖不舒服", {"risk": "low"})
        assert "膝盖不舒服" in task

    def test_role_build_task_contains_context_separator(self):
        """build_task 输出应包含数据上下文分隔符"""
        role = ROLES["coach"]
        task = role.build_task("请求", {"data": 1})
        assert "---数据上下文---" in task
        assert "---数据上下文结束---" in task

    def test_role_build_task_under_8000(self):
        """正常数据量下 task 应小于 8000 字符"""
        role = ROLES["coach"]
        normal_context = {"vdot": 45.2, "load": {"atl": 50, "ctl": 60}}
        task = role.build_task("分析训练", normal_context)
        assert len(task) < 8000

    def test_role_build_task_serializes_dict(self):
        """build_task 应将 dict 序列化为 JSON"""
        role = ROLES["coach"]
        task = role.build_task("请求", {"key": "值"})
        assert '"key"' in task
        assert "值" in task


class TestRolesRegistry:
    """ROLES 注册表测试"""

    def test_roles_registry_contains_coach(self):
        assert "coach" in ROLES
        assert isinstance(ROLES["coach"], SubagentRole)

    def test_roles_registry_contains_injury_prevention(self):
        assert "injury_prevention" in ROLES
        assert isinstance(ROLES["injury_prevention"], SubagentRole)

    def test_coach_role_name_matches_key(self):
        assert ROLES["coach"].name == "coach"

    def test_injury_role_name_matches_key(self):
        assert ROLES["injury_prevention"].name == "injury_prevention"

    def test_coach_prompt_mentions_vdot(self):
        """教练 prompt 应提及 VDOT（核心数据源）"""
        assert "VDOT" in COACH_PROMPT

    def test_injury_prompt_mentions_risk(self):
        """伤病预防师 prompt 应提及风险预测"""
        assert "风险" in INJURY_PROMPT or "伤病" in INJURY_PROMPT

    def test_roles_count_is_two(self):
        """MVP 阶段 ROLES 仅含 2 个新角色（不包含旧 data_analyst/report_writer）"""
        assert len(ROLES) == 2
