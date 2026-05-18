import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.core.skills.models import SkillInfo, SkillStatus
from src.core.skills.skill_manager import SkillManager


@pytest.fixture
def temp_workspace(tmp_path: Path) -> tuple[Path, Path]:
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
def skill_with_front_matter(temp_workspace: tuple[Path, Path]) -> Path:
    workspace, _ = temp_workspace
    skill_dir = workspace / "skills" / "yaml-skill"
    skill_dir.mkdir()
    content = """---
name: yaml-skill
description: YAML格式技能
version: 2.0.0
author: yaml-author
tags:
  - yaml
dependencies:
  - dep-string
  - name: dep-dict
    version: "1.5"
    optional: true
enabled_tools:
  - tool_a
  - tool_b
---

# YAML技能内容
"""
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
    return skill_dir


@pytest.fixture
def skill_without_front_matter(temp_workspace: tuple[Path, Path]) -> Path:
    workspace, _ = temp_workspace
    skill_dir = workspace / "skills" / "plain-skill"
    skill_dir.mkdir()
    content = """# 纯文本技能描述

这是没有front matter的技能文件。
"""
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
    return skill_dir


class TestSkillManagerListSkills:
    def test_list_skills_no_skills_dir(self, tmp_path: Path):
        workspace = tmp_path / "no_skills_ws"
        workspace.mkdir()
        config_path = tmp_path / "config.json"
        config_path.write_text("{}", encoding="utf-8")
        manager = SkillManager(workspace, config_path)
        assert manager.list_skills() == []

    def test_list_skills_dir_with_files(self, temp_workspace: tuple[Path, Path]):
        workspace, config_path = temp_workspace
        (workspace / "skills" / "not_a_dir.txt").write_text("ignore", encoding="utf-8")
        manager = SkillManager(workspace, config_path)
        assert manager.list_skills() == []

    def test_list_skills_dir_without_skill_file(
        self, temp_workspace: tuple[Path, Path]
    ):
        workspace, config_path = temp_workspace
        empty_dir = workspace / "skills" / "empty-skill"
        empty_dir.mkdir()
        manager = SkillManager(workspace, config_path)
        assert manager.list_skills() == []

    def test_list_skills_disabled(self, temp_workspace: tuple[Path, Path]):
        workspace, config_path = temp_workspace
        skill_dir = workspace / "skills" / "disabled-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: disabled-skill\ndescription: 被禁用\n---\n内容",
            encoding="utf-8",
        )

        config = json.loads(config_path.read_text(encoding="utf-8"))
        config["skills"]["disabled"] = ["disabled-skill"]
        config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")

        manager = SkillManager(workspace, config_path)
        skills = manager.list_skills()
        assert len(skills) == 1
        assert skills[0].status == SkillStatus.DISABLED

    def test_list_skills_parse_error(self, temp_workspace: tuple[Path, Path]):
        workspace, config_path = temp_workspace
        skill_dir = workspace / "skills" / "bad-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_bytes(b"\xff\xfe Invalid UTF-8")
        manager = SkillManager(workspace, config_path)
        skills = manager.list_skills()
        assert skills == []


class TestSkillManagerEnableDisable:
    def test_enable_already_enabled(
        self, temp_workspace: tuple[Path, Path], skill_with_front_matter: Path
    ):
        workspace, config_path = temp_workspace
        manager = SkillManager(workspace, config_path)
        result = manager.enable_skill("yaml-skill")
        assert result is True

    def test_disable_already_disabled(self, temp_workspace: tuple[Path, Path]):
        workspace, config_path = temp_workspace
        skill_dir = workspace / "skills" / "d-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: d-skill\ndescription: desc\n---\n内容",
            encoding="utf-8",
        )
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config["skills"]["disabled"] = ["d-skill"]
        config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")

        manager = SkillManager(workspace, config_path)
        result = manager.disable_skill("d-skill")
        assert result is True

    def test_enable_skill_removes_from_disabled(
        self, temp_workspace: tuple[Path, Path]
    ):
        workspace, config_path = temp_workspace
        skill_dir = workspace / "skills" / "toggle-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: toggle-skill\ndescription: desc\n---\n内容",
            encoding="utf-8",
        )

        config = json.loads(config_path.read_text(encoding="utf-8"))
        config["skills"]["disabled"] = ["toggle-skill"]
        config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")

        manager = SkillManager(workspace, config_path)
        result = manager.enable_skill("toggle-skill")
        assert result is True

        config_after = json.loads(config_path.read_text(encoding="utf-8"))
        assert "toggle-skill" not in config_after["skills"]["disabled"]

    def test_disable_skill_adds_to_disabled(
        self, temp_workspace: tuple[Path, Path], skill_with_front_matter: Path
    ):
        workspace, config_path = temp_workspace
        manager = SkillManager(workspace, config_path)
        result = manager.disable_skill("yaml-skill")
        assert result is True

        config_after = json.loads(config_path.read_text(encoding="utf-8"))
        assert "yaml-skill" in config_after["skills"]["disabled"]

    def test_enable_skill_config_write_error(
        self, temp_workspace: tuple[Path, Path], skill_with_front_matter: Path
    ):
        workspace, config_path = temp_workspace
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config["skills"]["disabled"] = ["yaml-skill"]
        config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")

        manager = SkillManager(workspace, config_path)
        with patch("json.dump", side_effect=PermissionError("no write")):
            result = manager.enable_skill("yaml-skill")
        assert result is False

    def test_disable_skill_config_write_error(
        self, temp_workspace: tuple[Path, Path], skill_with_front_matter: Path
    ):
        workspace, config_path = temp_workspace
        manager = SkillManager(workspace, config_path)
        with patch("json.dump", side_effect=PermissionError("no write")):
            result = manager.disable_skill("yaml-skill")
        assert result is False


class TestSkillManagerImportSkill:
    def test_import_nonexistent_path(self, temp_workspace: tuple[Path, Path]):
        workspace, config_path = temp_workspace
        manager = SkillManager(workspace, config_path)
        result = manager.import_skill(Path("/nonexistent/path"))
        assert result is False

    def test_import_path_without_skill_file(
        self, temp_workspace: tuple[Path, Path], tmp_path: Path
    ):
        workspace, config_path = temp_workspace
        ext_dir = tmp_path / "no-skill-file"
        ext_dir.mkdir()
        manager = SkillManager(workspace, config_path)
        result = manager.import_skill(ext_dir)
        assert result is False

    def test_import_skill_creates_skills_dir(self, tmp_path: Path):
        workspace = tmp_path / "ws"
        workspace.mkdir()
        config_path = tmp_path / "config.json"
        config_path.write_text("{}", encoding="utf-8")

        ext_dir = tmp_path / "ext-skill"
        ext_dir.mkdir()
        (ext_dir / "SKILL.md").write_text(
            "---\nname: ext-skill\ndescription: ext\n---\n内容",
            encoding="utf-8",
        )

        manager = SkillManager(workspace, config_path)
        result = manager.import_skill(ext_dir)
        assert result is True
        assert (workspace / "skills" / "ext-skill").exists()

    def test_import_skill_copy_error(
        self, temp_workspace: tuple[Path, Path], tmp_path: Path
    ):
        workspace, config_path = temp_workspace
        ext_dir = tmp_path / "fail-skill"
        ext_dir.mkdir()
        (ext_dir / "SKILL.md").write_text(
            "---\nname: fail-skill\ndescription: fail\n---\n内容",
            encoding="utf-8",
        )

        manager = SkillManager(workspace, config_path)
        with patch("shutil.copytree", side_effect=OSError("copy failed")):
            result = manager.import_skill(ext_dir)
        assert result is False


class TestSkillManagerGetContent:
    def test_get_content_nonexistent_skill(self, temp_workspace: tuple[Path, Path]):
        workspace, config_path = temp_workspace
        manager = SkillManager(workspace, config_path)
        assert manager.get_skill_content("nonexistent") is None

    def test_get_content_skill_no_path(self, temp_workspace: tuple[Path, Path]):
        workspace, config_path = temp_workspace
        manager = SkillManager(workspace, config_path)
        with patch.object(
            manager,
            "get_skill",
            return_value=SkillInfo(name="x", description="x", path=None),
        ):
            assert manager.get_skill_content("x") is None

    def test_get_content_skill_file_missing(self, temp_workspace: tuple[Path, Path]):
        workspace, config_path = temp_workspace
        skill_dir = workspace / "skills" / "no-file-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: no-file-skill\ndescription: desc\n---\n内容",
            encoding="utf-8",
        )
        manager = SkillManager(workspace, config_path)
        skill = manager.get_skill("no-file-skill")
        assert skill is not None
        (skill_dir / "SKILL.md").unlink()
        assert manager.get_skill_content("no-file-skill") is None

    def test_get_content_read_error(
        self, temp_workspace: tuple[Path, Path], skill_with_front_matter: Path
    ):
        workspace, config_path = temp_workspace
        manager = SkillManager(workspace, config_path)
        with patch.object(Path, "read_text", side_effect=OSError("read error")):
            result = manager.get_skill_content("yaml-skill")
        assert result is None


class TestSkillManagerParseContent:
    def test_parse_front_matter_with_string_deps(
        self, temp_workspace: tuple[Path, Path], skill_with_front_matter: Path
    ):
        workspace, config_path = temp_workspace
        manager = SkillManager(workspace, config_path)
        skill = manager.get_skill("yaml-skill")
        assert skill is not None
        dep_names = [d.name for d in skill.dependencies]
        assert "dep-string" in dep_names
        assert "dep-dict" in dep_names

    def test_parse_plain_content(
        self, temp_workspace: tuple[Path, Path], skill_without_front_matter: Path
    ):
        workspace, config_path = temp_workspace
        manager = SkillManager(workspace, config_path)
        skill = manager.get_skill("plain-skill")
        assert skill is not None
        assert skill.description == "纯文本技能描述"
        assert skill.version == "1.0.0"
        assert skill.author == "unknown"

    def test_parse_invalid_yaml_front_matter(self, temp_workspace: tuple[Path, Path]):
        workspace, config_path = temp_workspace
        skill_dir = workspace / "skills" / "bad-yaml"
        skill_dir.mkdir()
        content = "---\ninvalid: [yaml: content\n---\n# 标题\n内容"
        (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")

        manager = SkillManager(workspace, config_path)
        skill = manager.get_skill("bad-yaml")
        assert skill is not None
        assert skill.name == "bad-yaml"

    def test_parse_front_matter_non_dict(self, temp_workspace: tuple[Path, Path]):
        workspace, config_path = temp_workspace
        skill_dir = workspace / "skills" / "list-fm"
        skill_dir.mkdir()
        content = "---\n- item1\n- item2\n---\n# 标题\n内容"
        (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")

        manager = SkillManager(workspace, config_path)
        skill = manager.get_skill("list-fm")
        assert skill is not None
        assert skill.name == "list-fm"


class TestLoadDisabledSkills:
    def test_load_disabled_no_config_file(self, tmp_path: Path):
        workspace = tmp_path / "ws"
        workspace.mkdir()
        config_path = tmp_path / "missing_config.json"
        manager = SkillManager(workspace, config_path)
        assert manager._load_disabled_skills() == []

    def test_load_disabled_invalid_json(self, tmp_path: Path):
        workspace = tmp_path / "ws"
        workspace.mkdir()
        config_path = tmp_path / "bad_config.json"
        config_path.write_text("not valid json", encoding="utf-8")
        manager = SkillManager(workspace, config_path)
        assert manager._load_disabled_skills() == []

    def test_load_disabled_no_skills_key(self, tmp_path: Path):
        workspace = tmp_path / "ws"
        workspace.mkdir()
        config_path = tmp_path / "config.json"
        config_path.write_text('{"version": "1.0"}', encoding="utf-8")
        manager = SkillManager(workspace, config_path)
        assert manager._load_disabled_skills() == []
