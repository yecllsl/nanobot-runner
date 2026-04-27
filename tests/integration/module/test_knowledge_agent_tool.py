# 知识库Agent工具集成测试
# 验证Agent能够通过技能加载训练知识库

import json
from pathlib import Path

import pytest

from src.core.skills.models import SkillStatus
from src.core.skills.skill_manager import SkillManager


@pytest.fixture
def temp_workspace_with_skill(tmp_path: Path) -> tuple[Path, Path]:
    """创建包含训练知识库技能的临时工作空间"""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    skills_dir = workspace / "skills"
    skills_dir.mkdir()

    training_skill_dir = skills_dir / "training-knowledge"
    training_skill_dir.mkdir()

    skill_content = """---
name: training-knowledge
description: 训练知识库技能
version: 1.0.0
author: nanobot-runner
tags:
  - training
  - knowledge
---

# 训练知识库

VDOT训练体系、训练负荷管理、心率训练等知识。
"""
    (training_skill_dir / "SKILL.md").write_text(skill_content, encoding="utf-8")

    config_path = tmp_path / "config.json"
    config = {
        "version": "0.13.0",
        "data_dir": str(workspace / "data"),
        "skills": {"disabled": []},
    }
    config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")

    return workspace, config_path


class TestKnowledgeAgentToolIntegration:
    """知识库Agent工具集成测试"""

    def test_training_knowledge_skill_loaded(
        self, temp_workspace_with_skill: tuple[Path, Path]
    ):
        """测试训练知识库技能正确加载"""
        workspace, config_path = temp_workspace_with_skill
        manager = SkillManager(workspace, config_path)
        skills = manager.list_skills()

        assert len(skills) == 1
        assert skills[0].name == "training-knowledge"
        assert skills[0].status == SkillStatus.ENABLED

    def test_training_knowledge_skill_content(
        self, temp_workspace_with_skill: tuple[Path, Path]
    ):
        """测试训练知识库技能内容获取"""
        workspace, config_path = temp_workspace_with_skill
        manager = SkillManager(workspace, config_path)

        content = manager.get_skill_content("training-knowledge")
        assert content is not None
        assert "VDOT" in content
        assert "训练负荷" in content

    def test_training_knowledge_skill_tags(
        self, temp_workspace_with_skill: tuple[Path, Path]
    ):
        """测试训练知识库技能标签"""
        workspace, config_path = temp_workspace_with_skill
        manager = SkillManager(workspace, config_path)
        skill = manager.get_skill("training-knowledge")

        assert skill is not None
        assert "training" in skill.tags
        assert "knowledge" in skill.tags

    def test_training_knowledge_skill_disable(
        self, temp_workspace_with_skill: tuple[Path, Path]
    ):
        """测试禁用训练知识库技能"""
        workspace, config_path = temp_workspace_with_skill
        manager = SkillManager(workspace, config_path)

        result = manager.disable_skill("training-knowledge")
        assert result is True

        skill = manager.get_skill("training-knowledge")
        assert skill is not None
        assert skill.status == SkillStatus.DISABLED

    def test_training_knowledge_skill_enable(
        self, temp_workspace_with_skill: tuple[Path, Path]
    ):
        """测试启用训练知识库技能"""
        workspace, config_path = temp_workspace_with_skill
        manager = SkillManager(workspace, config_path)

        manager.disable_skill("training-knowledge")
        result = manager.enable_skill("training-knowledge")
        assert result is True

        skill = manager.get_skill("training-knowledge")
        assert skill is not None
        assert skill.status == SkillStatus.ENABLED

    def test_knowledge_skill_with_tools_config(
        self, temp_workspace_with_skill: tuple[Path, Path]
    ):
        """测试知识库技能与工具配置协同"""
        workspace, config_path = temp_workspace_with_skill
        manager = SkillManager(workspace, config_path)
        skill = manager.get_skill("training-knowledge")

        assert skill is not None
        assert skill.enabled_tools == []

    def test_knowledge_skill_to_dict(
        self, temp_workspace_with_skill: tuple[Path, Path]
    ):
        """测试知识库技能转换为字典"""
        workspace, config_path = temp_workspace_with_skill
        manager = SkillManager(workspace, config_path)
        skill = manager.get_skill("training-knowledge")

        assert skill is not None
        skill_dict = skill.to_dict()

        assert skill_dict["name"] == "training-knowledge"
        assert skill_dict["description"] == "训练知识库技能"
        assert skill_dict["version"] == "1.0.0"
        assert skill_dict["status"] == "enabled"

    def test_multiple_skills_management(
        self, temp_workspace_with_skill: tuple[Path, Path]
    ):
        """测试多个技能管理"""
        workspace, config_path = temp_workspace_with_skill

        another_skill_dir = workspace / "skills" / "another-skill"
        another_skill_dir.mkdir()
        skill_content = """---
name: another-skill
description: 另一个技能
---
内容
"""
        (another_skill_dir / "SKILL.md").write_text(skill_content, encoding="utf-8")

        manager = SkillManager(workspace, config_path)
        skills = manager.list_skills()

        assert len(skills) == 2
        skill_names = [s.name for s in skills]
        assert "training-knowledge" in skill_names
        assert "another-skill" in skill_names
