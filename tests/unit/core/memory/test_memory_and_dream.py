# 记忆管理与Dream集成单元测试

from datetime import datetime
from pathlib import Path

from src.core.memory.dream_integration import DreamIntegration
from src.core.memory.memory_manager import MemoryManager
from src.core.memory.models import MemoryVersion
from src.core.personality.models import Personality


class TestMemoryManager:
    """MemoryManager 测试"""

    def test_read_memory_nonexistent(self, tmp_path: Path):
        manager = MemoryManager(tmp_path)
        assert manager.read_memory() == ""

    def test_write_and_read_memory(self, tmp_path: Path):
        manager = MemoryManager(tmp_path)
        manager.write_memory("测试记忆内容")
        content = manager.read_memory()
        assert content == "测试记忆内容"

    def test_read_user_profile_nonexistent(self, tmp_path: Path):
        manager = MemoryManager(tmp_path)
        assert manager.read_user_profile() == ""

    def test_write_and_read_user_profile(self, tmp_path: Path):
        manager = MemoryManager(tmp_path)
        manager.write_user_profile("用户画像内容")
        content = manager.read_user_profile()
        assert content == "用户画像内容"

    def test_read_personality_nonexistent(self, tmp_path: Path):
        manager = MemoryManager(tmp_path)
        personality = manager.read_personality()
        assert personality.communication_style == "encouraging"

    def test_write_and_read_personality(self, tmp_path: Path):
        manager = MemoryManager(tmp_path)
        personality = Personality(
            communication_style="analytical",
            empathy_level=0.9,
        )
        manager.write_personality(personality)
        loaded = manager.read_personality()
        assert loaded.communication_style == "analytical"
        assert loaded.empathy_level == 0.9

    def test_save_preference_to_memory(self, tmp_path: Path):
        manager = MemoryManager(tmp_path)
        manager.write_memory("# 项目记忆\n\n一些内容\n")

        result = manager.save_preference_to_memory(
            {"training_time": "evening", "communication_style": "brief"}
        )
        assert result is True

        content = manager.read_memory()
        assert "## 用户偏好" in content
        assert "training_time: evening" in content

    def test_save_preference_update_existing(self, tmp_path: Path):
        manager = MemoryManager(tmp_path)
        manager.write_memory(
            "# 项目记忆\n\n## 用户偏好\n\n- training_time: morning\n\n## 其他\n"
        )

        manager.save_preference_to_memory({"training_time": "evening"})

        content = manager.read_memory()
        assert "## 用户偏好" in content

    def test_load_preference_from_memory(self, tmp_path: Path):
        manager = MemoryManager(tmp_path)
        manager.write_memory(
            "# 项目记忆\n\n## 用户偏好\n\n- training_time: evening\n- communication_style: brief\n"
        )

        prefs = manager.load_preference_from_memory()
        assert prefs.get("training_time") == "evening"
        assert prefs.get("communication_style") == "brief"

    def test_load_preference_from_empty_memory(self, tmp_path: Path):
        manager = MemoryManager(tmp_path)
        prefs = manager.load_preference_from_memory()
        assert prefs == {}

    def test_update_memory_context(self, tmp_path: Path):
        manager = MemoryManager(tmp_path)
        manager.write_memory("# 项目记忆\n")

        result = manager.update_memory_context("last_run_date", "2026-01-01")
        assert result is True

        content = manager.read_memory()
        assert "last_run_date: 2026-01-01" in content

    def test_create_backup(self, tmp_path: Path):
        manager = MemoryManager(tmp_path)
        manager.write_memory("记忆内容")
        manager.write_user_profile("用户画像")

        backup_path = manager.create_backup()
        assert backup_path != ""
        assert Path(backup_path).exists()

    def test_restore_backup(self, tmp_path: Path):
        manager = MemoryManager(tmp_path)
        manager.write_memory("原始记忆")
        manager.write_user_profile("原始画像")

        backup_path = manager.create_backup()

        manager.write_memory("修改后的记忆")
        assert manager.read_memory() == "修改后的记忆"

        result = manager.restore_backup(Path(backup_path))
        assert result is True
        assert manager.read_memory() == "原始记忆"

    def test_list_versions(self, tmp_path: Path):
        manager = MemoryManager(tmp_path)
        manager.write_memory("内容")

        manager.create_backup()
        versions = manager.list_versions()
        assert len(versions) == 1
        assert versions[0].version.startswith("v_")

    def test_get_memory_stats(self, tmp_path: Path):
        manager = MemoryManager(tmp_path)
        stats = manager.get_memory_stats()
        assert stats["memory_exists"] is False
        assert stats["version_count"] == 0

        manager.write_memory("内容")
        stats = manager.get_memory_stats()
        assert stats["memory_exists"] is True
        assert stats["memory_size"] > 0

    def test_consecutive_backup_different_versions(self, tmp_path: Path):
        """BUG-v0.14.0-001回归测试：连续调用create_backup()应产生不同版本号"""
        manager = MemoryManager(tmp_path)
        manager.write_memory("内容1")

        backup_path1 = manager.create_backup()
        manager.write_memory("内容2")
        backup_path2 = manager.create_backup()

        assert backup_path1 != ""
        assert backup_path2 != ""
        assert backup_path1 != backup_path2

        versions = manager.list_versions()
        assert len(versions) == 2
        assert versions[0].version != versions[1].version


class TestMemoryVersion:
    """MemoryVersion 数据模型测试"""

    def test_create_version(self):
        version = MemoryVersion(
            version="v_20260101_120000",
            timestamp=datetime(2026, 1, 1, 12, 0, 0),
            memory_hash="abc123",
            user_hash="def456",
        )
        assert version.version == "v_20260101_120000"
        assert version.memory_hash == "abc123"

    def test_to_dict(self):
        version = MemoryVersion(
            version="v_test",
            timestamp=datetime(2026, 1, 1),
            memory_hash="hash1",
            user_hash="hash2",
        )
        d = version.to_dict()
        assert d["version"] == "v_test"
        assert d["memory_hash"] == "hash1"


class TestDreamIntegration:
    """DreamIntegration 测试"""

    def test_get_default_config(self, tmp_path: Path):
        config_path = tmp_path / "config.json"
        dream = DreamIntegration(config_path)

        config = dream.get_dream_config()
        assert config["enabled"] is True
        assert config["frequency"] == "daily"
        assert config["auto_archive"] is True

    def test_update_dream_config(self, tmp_path: Path):
        config_path = tmp_path / "config.json"
        config_path.write_text("{}", encoding="utf-8")
        dream = DreamIntegration(config_path)

        result = dream.update_dream_config(frequency="weekly", auto_archive=False)
        assert result is True

        config = dream.get_dream_config()
        assert config["frequency"] == "weekly"
        assert config["auto_archive"] is False

    def test_set_invalid_frequency(self, tmp_path: Path):
        config_path = tmp_path / "config.json"
        config_path.write_text("{}", encoding="utf-8")
        dream = DreamIntegration(config_path)

        result = dream.set_frequency("invalid")
        assert result is False

    def test_enable_auto_archive(self, tmp_path: Path):
        config_path = tmp_path / "config.json"
        config_path.write_text("{}", encoding="utf-8")
        dream = DreamIntegration(config_path)

        result = dream.enable_auto_archive()
        assert result is True

        status = dream.get_dream_status()
        assert status["auto_archive"] is True

    def test_disable_auto_archive(self, tmp_path: Path):
        config_path = tmp_path / "config.json"
        config_path.write_text("{}", encoding="utf-8")
        dream = DreamIntegration(config_path)

        dream.disable_auto_archive()
        status = dream.get_dream_status()
        assert status["auto_archive"] is False

    def test_trigger_dream_disabled(self, tmp_path: Path):
        config_path = tmp_path / "config.json"
        config_path.write_text("{}", encoding="utf-8")
        dream = DreamIntegration(config_path)
        dream.update_dream_config(enabled=False)

        result = dream.trigger_dream()
        assert result["success"] is False

    def test_trigger_dream_enabled(self, tmp_path: Path):
        config_path = tmp_path / "config.json"
        config_path.write_text("{}", encoding="utf-8")
        dream = DreamIntegration(config_path)
        dream.update_dream_config(enabled=True)

        result = dream.trigger_dream()
        assert result["success"] is True

    def test_get_dream_status(self, tmp_path: Path):
        config_path = tmp_path / "config.json"
        config_path.write_text("{}", encoding="utf-8")
        dream = DreamIntegration(config_path, workspace=tmp_path)

        status = dream.get_dream_status()
        assert "enabled" in status
        assert "frequency" in status
        assert "auto_archive" in status

    def test_enable_auto_extract_preferences(self, tmp_path: Path):
        config_path = tmp_path / "config.json"
        config_path.write_text("{}", encoding="utf-8")
        dream = DreamIntegration(config_path)

        result = dream.enable_auto_extract_preferences()
        assert result is True
