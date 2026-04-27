# 技能管理器单元测试
# 验证技能发现、启用、禁用、导入等功能

import json
from pathlib import Path

import pytest

from src.core.skills.models import SkillDependency, SkillInfo, SkillStatus
from src.core.skills.skill_manager import SkillManager


@pytest.fixture
def temp_workspace(tmp_path: Path) -> tuple[Path, Path]:
    """创建临时工作空间和配置文件"""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    skills_dir = workspace / "skills"
    skills_dir.mkdir()

    config_path = tmp_path / "config.json"
    config = {
        "version": "0.13.0",
        "data_dir": str(workspace / "data"),
        "skills": {"disabled": []},
    }
    config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")

    return workspace, config_path


@pytest.fixture
def sample_skill(temp_workspace: tuple[Path, Path]) -> Path:
    """创建示例技能"""
    workspace, _ = temp_workspace
    skill_dir = workspace / "skills" / "test-skill"
    skill_dir.mkdir()

    skill_content = """---
name: test-skill
description: 测试技能
version: 1.0.0
author: test-author
tags:
  - test
  - demo
dependencies:
  - name: weather
    version: "1.0"
    optional: true
enabled_tools:
  - mcp_weather_get_weather
---

# 测试技能内容

这是一个测试技能的详细说明。
"""
    (skill_dir / "SKILL.md").write_text(skill_content, encoding="utf-8")
    return skill_dir


class TestSkillManager:
    """技能管理器测试"""

    def test_list_skills_empty(self, temp_workspace: tuple[Path, Path]):
        """测试空技能列表"""
        workspace, config_path = temp_workspace
        manager = SkillManager(workspace, config_path)
        skills = manager.list_skills()
        assert skills == []

    def test_list_skills_with_skill(
        self, temp_workspace: tuple[Path, Path], sample_skill: Path
    ):
        """测试列出技能"""
        workspace, config_path = temp_workspace
        manager = SkillManager(workspace, config_path)
        skills = manager.list_skills()

        assert len(skills) == 1
        assert skills[0].name == "test-skill"
        assert skills[0].description == "测试技能"
        assert skills[0].version == "1.0.0"
        assert skills[0].author == "test-author"
        assert skills[0].status == SkillStatus.ENABLED

    def test_get_skill(self, temp_workspace: tuple[Path, Path], sample_skill: Path):
        """测试获取技能"""
        workspace, config_path = temp_workspace
        manager = SkillManager(workspace, config_path)
        skill = manager.get_skill("test-skill")

        assert skill is not None
        assert skill.name == "test-skill"

    def test_get_skill_not_found(self, temp_workspace: tuple[Path, Path]):
        """测试获取不存在的技能"""
        workspace, config_path = temp_workspace
        manager = SkillManager(workspace, config_path)
        skill = manager.get_skill("nonexistent")

        assert skill is None

    def test_enable_skill(self, temp_workspace: tuple[Path, Path], sample_skill: Path):
        """测试启用技能"""
        workspace, config_path = temp_workspace
        manager = SkillManager(workspace, config_path)

        result = manager.enable_skill("test-skill")
        assert result is True

        skill = manager.get_skill("test-skill")
        assert skill is not None
        assert skill.status == SkillStatus.ENABLED

    def test_disable_skill(self, temp_workspace: tuple[Path, Path], sample_skill: Path):
        """测试禁用技能"""
        workspace, config_path = temp_workspace
        manager = SkillManager(workspace, config_path)

        result = manager.disable_skill("test-skill")
        assert result is True

        skill = manager.get_skill("test-skill")
        assert skill is not None
        assert skill.status == SkillStatus.DISABLED

    def test_enable_nonexistent_skill(self, temp_workspace: tuple[Path, Path]):
        """测试启用不存在的技能"""
        workspace, config_path = temp_workspace
        manager = SkillManager(workspace, config_path)

        result = manager.enable_skill("nonexistent")
        assert result is False

    def test_disable_nonexistent_skill(self, temp_workspace: tuple[Path, Path]):
        """测试禁用不存在的技能"""
        workspace, config_path = temp_workspace
        manager = SkillManager(workspace, config_path)

        result = manager.disable_skill("nonexistent")
        assert result is False

    def test_import_skill(self, temp_workspace: tuple[Path, Path], tmp_path: Path):
        """测试导入技能"""
        workspace, config_path = temp_workspace

        external_skill_dir = tmp_path / "external-skill"
        external_skill_dir.mkdir()
        skill_content = """---
name: external-skill
description: 外部技能
---
外部技能内容
"""
        (external_skill_dir / "SKILL.md").write_text(skill_content, encoding="utf-8")

        manager = SkillManager(workspace, config_path)
        result = manager.import_skill(external_skill_dir)

        assert result is True
        skill = manager.get_skill("external-skill")
        assert skill is not None
        assert skill.name == "external-skill"

    def test_import_existing_skill(
        self, temp_workspace: tuple[Path, Path], sample_skill: Path
    ):
        """测试导入已存在的技能"""
        workspace, config_path = temp_workspace
        manager = SkillManager(workspace, config_path)

        result = manager.import_skill(sample_skill)
        assert result is False

    def test_get_skill_content(
        self, temp_workspace: tuple[Path, Path], sample_skill: Path
    ):
        """测试获取技能内容"""
        workspace, config_path = temp_workspace
        manager = SkillManager(workspace, config_path)

        content = manager.get_skill_content("test-skill")
        assert content is not None
        assert "test-skill" in content
        assert "测试技能" in content

    def test_skill_dependencies(
        self, temp_workspace: tuple[Path, Path], sample_skill: Path
    ):
        """测试技能依赖解析"""
        workspace, config_path = temp_workspace
        manager = SkillManager(workspace, config_path)
        skill = manager.get_skill("test-skill")

        assert skill is not None
        assert len(skill.dependencies) == 1
        assert skill.dependencies[0].name == "weather"
        assert skill.dependencies[0].version == "1.0"
        assert skill.dependencies[0].optional is True

    def test_skill_tags(self, temp_workspace: tuple[Path, Path], sample_skill: Path):
        """测试技能标签解析"""
        workspace, config_path = temp_workspace
        manager = SkillManager(workspace, config_path)
        skill = manager.get_skill("test-skill")

        assert skill is not None
        assert "test" in skill.tags
        assert "demo" in skill.tags

    def test_skill_enabled_tools(
        self, temp_workspace: tuple[Path, Path], sample_skill: Path
    ):
        """测试技能启用的工具"""
        workspace, config_path = temp_workspace
        manager = SkillManager(workspace, config_path)
        skill = manager.get_skill("test-skill")

        assert skill is not None
        assert "mcp_weather_get_weather" in skill.enabled_tools


class TestSkillInfo:
    """技能信息测试"""

    def test_skill_info_to_dict(self):
        """测试技能信息转换为字典"""
        skill = SkillInfo(
            name="test",
            description="测试技能",
            version="1.0.0",
            author="test-author",
            status=SkillStatus.ENABLED,
            dependencies=[SkillDependency(name="dep1")],
            tags=["tag1", "tag2"],
            enabled_tools=["tool1"],
        )

        result = skill.to_dict()

        assert result["name"] == "test"
        assert result["description"] == "测试技能"
        assert result["version"] == "1.0.0"
        assert result["status"] == "enabled"
        assert len(result["dependencies"]) == 1
        assert result["tags"] == ["tag1", "tag2"]
        assert result["enabled_tools"] == ["tool1"]

    def test_skill_info_is_enabled(self):
        """测试技能启用状态检查"""
        enabled_skill = SkillInfo(
            name="enabled",
            description="启用的技能",
            status=SkillStatus.ENABLED,
        )
        disabled_skill = SkillInfo(
            name="disabled",
            description="禁用的技能",
            status=SkillStatus.DISABLED,
        )

        assert enabled_skill.is_enabled is True
        assert disabled_skill.is_enabled is False


class TestSkillDependency:
    """技能依赖测试"""

    def test_skill_dependency_defaults(self):
        """测试技能依赖默认值"""
        dep = SkillDependency(name="test-dep")

        assert dep.name == "test-dep"
        assert dep.version is None
        assert dep.optional is False
