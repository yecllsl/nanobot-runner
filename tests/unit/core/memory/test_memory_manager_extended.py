from __future__ import annotations

from pathlib import Path

from src.core.memory.memory_manager import MemoryManager
from src.core.personality.models import Personality


class TestMemoryManagerReadWrite:
    def test_read_memory_empty(self, tmp_path):
        mm = MemoryManager(tmp_path)
        assert mm.read_memory() == ""

    def test_write_and_read_memory(self, tmp_path):
        mm = MemoryManager(tmp_path)
        mm.write_memory("test content")
        assert mm.read_memory() == "test content"

    def test_read_memory_exception(self, tmp_path):
        mm = MemoryManager(tmp_path)
        mm.memory_file = tmp_path / "nonexistent" / "MEMORY.md"
        assert mm.read_memory() == ""

    def test_write_memory_creates_dir(self, tmp_path):
        workspace = tmp_path / "new_workspace"
        mm = MemoryManager(workspace)
        mm.write_memory("test")
        assert mm.read_memory() == "test"

    def test_read_user_profile_empty(self, tmp_path):
        mm = MemoryManager(tmp_path)
        assert mm.read_user_profile() == ""

    def test_write_and_read_user_profile(self, tmp_path):
        mm = MemoryManager(tmp_path)
        mm.write_user_profile("user profile content")
        assert mm.read_user_profile() == "user profile content"


class TestMemoryManagerPersonality:
    def test_read_personality_default(self, tmp_path):
        mm = MemoryManager(tmp_path)
        personality = mm.read_personality()
        assert isinstance(personality, Personality)

    def test_write_and_read_personality(self, tmp_path):
        mm = MemoryManager(tmp_path)
        personality = Personality.default()
        mm.write_personality(personality)
        loaded = mm.read_personality()
        assert isinstance(loaded, Personality)

    def test_read_personality_invalid_json(self, tmp_path):
        mm = MemoryManager(tmp_path)
        mm.personality_file.write_text("invalid json", encoding="utf-8")
        personality = mm.read_personality()
        assert isinstance(personality, Personality)


class TestMemoryManagerSavePreference:
    def test_save_preference_new_section(self, tmp_path):
        mm = MemoryManager(tmp_path)
        mm.write_memory("# Project Memory\n\nSome content\n")
        result = mm.save_preference_to_memory({"theme": "dark", "language": "zh"})
        assert result is True
        content = mm.read_memory()
        assert "## 用户偏好" in content
        assert "theme: dark" in content
        assert "language: zh" in content

    def test_save_preference_update_existing(self, tmp_path):
        mm = MemoryManager(tmp_path)
        mm.write_memory(
            "# Project Memory\n\n## 用户偏好\n\n- theme: light\n\n## Other\n"
        )
        result = mm.save_preference_to_memory({"theme": "dark"})
        assert result is True
        content = mm.read_memory()
        assert "theme: dark" in content
        assert "## Other" in content

    def test_save_preference_no_existing_section_at_end(self, tmp_path):
        mm = MemoryManager(tmp_path)
        mm.write_memory("# Project Memory\n\n## 用户偏好\n\n- theme: light\n")
        result = mm.save_preference_to_memory({"theme": "dark"})
        assert result is True
        content = mm.read_memory()
        assert "theme: dark" in content


class TestMemoryManagerLoadPreference:
    def test_load_preference_empty(self, tmp_path):
        mm = MemoryManager(tmp_path)
        prefs = mm.load_preference_from_memory()
        assert prefs == {}

    def test_load_preference_no_section(self, tmp_path):
        mm = MemoryManager(tmp_path)
        mm.write_memory("# Project Memory\n\nSome content\n")
        prefs = mm.load_preference_from_memory()
        assert prefs == {}

    def test_load_preference_with_data(self, tmp_path):
        mm = MemoryManager(tmp_path)
        mm.write_memory(
            "# Project Memory\n\n## 用户偏好\n\n- theme: dark\n- language: zh\n\n## Other\n"
        )
        prefs = mm.load_preference_from_memory()
        assert prefs["theme"] == "dark"
        assert prefs["language"] == "zh"

    def test_load_preference_no_next_section(self, tmp_path):
        mm = MemoryManager(tmp_path)
        mm.write_memory("## 用户偏好\n\n- theme: dark\n")
        prefs = mm.load_preference_from_memory()
        assert prefs["theme"] == "dark"


class TestMemoryManagerUpdateContext:
    def test_update_context_new_section(self, tmp_path):
        mm = MemoryManager(tmp_path)
        mm.write_memory("# Project Memory\n")
        result = mm.update_memory_context("current_goal", "马拉松破4")
        assert result is True
        content = mm.read_memory()
        assert "## 上下文信息" in content
        assert "current_goal: 马拉松破4" in content

    def test_update_context_existing_key(self, tmp_path):
        mm = MemoryManager(tmp_path)
        mm.write_memory(
            "# Project Memory\n\n## 上下文信息\n\n- current_goal: 半马破2\n\n## Other\n"
        )
        result = mm.update_memory_context("current_goal", "全马破4")
        assert result is True
        content = mm.read_memory()
        assert "current_goal: 全马破4" in content

    def test_update_context_new_key_in_section(self, tmp_path):
        mm = MemoryManager(tmp_path)
        mm.write_memory(
            "# Project Memory\n\n## 上下文信息\n\n- current_goal: 马拉松破4\n\n## Other\n"
        )
        result = mm.update_memory_context("race_date", "2026-12-01")
        assert result is True
        content = mm.read_memory()
        assert "race_date: 2026-12-01" in content


class TestMemoryManagerBackup:
    def test_create_backup(self, tmp_path):
        mm = MemoryManager(tmp_path)
        mm.write_memory("test memory")
        mm.write_user_profile("test user")
        backup_path = mm.create_backup()
        assert backup_path != ""
        assert Path(backup_path).exists()

    def test_create_backup_with_personality(self, tmp_path):
        mm = MemoryManager(tmp_path)
        mm.write_memory("test memory")
        personality = Personality.default()
        mm.write_personality(personality)
        backup_path = mm.create_backup()
        assert backup_path != ""

    def test_restore_backup(self, tmp_path):
        mm = MemoryManager(tmp_path)
        mm.write_memory("original memory")
        backup_path = mm.create_backup()
        mm.write_memory("modified memory")
        result = mm.restore_backup(Path(backup_path))
        assert result is True
        assert mm.read_memory() == "original memory"

    def test_restore_backup_nonexistent(self, tmp_path):
        mm = MemoryManager(tmp_path)
        result = mm.restore_backup(tmp_path / "nonexistent")
        assert result is False


class TestMemoryManagerListVersions:
    def test_list_versions_empty(self, tmp_path):
        mm = MemoryManager(tmp_path)
        versions = mm.list_versions()
        assert versions == []

    def test_list_versions_with_backup(self, tmp_path):
        mm = MemoryManager(tmp_path)
        mm.write_memory("test")
        mm.create_backup()
        versions = mm.list_versions()
        assert len(versions) == 1

    def test_list_versions_invalid_version_file(self, tmp_path):
        mm = MemoryManager(tmp_path)
        version_dir = tmp_path / ".memory_versions" / "v_invalid"
        version_dir.mkdir(parents=True)
        (version_dir / "version.json").write_text("invalid json", encoding="utf-8")
        versions = mm.list_versions()
        assert versions == []


class TestMemoryManagerGetStats:
    def test_get_stats_empty(self, tmp_path):
        mm = MemoryManager(tmp_path)
        stats = mm.get_memory_stats()
        assert stats["memory_exists"] is False
        assert stats["user_profile_exists"] is False
        assert stats["version_count"] == 0

    def test_get_stats_with_data(self, tmp_path):
        mm = MemoryManager(tmp_path)
        mm.write_memory("test content")
        stats = mm.get_memory_stats()
        assert stats["memory_exists"] is True
        assert stats["memory_size"] > 0


class TestMemoryManagerComputeHash:
    def test_compute_hash_existing_file(self, tmp_path):
        mm = MemoryManager(tmp_path)
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello", encoding="utf-8")
        h = MemoryManager._compute_file_hash(test_file)
        assert len(h) == 16

    def test_compute_hash_nonexistent_file(self, tmp_path):
        h = MemoryManager._compute_file_hash(tmp_path / "nonexistent.txt")
        assert h == ""
