from pathlib import Path

from src.core.backup_manager import BackupManager


class TestBackupManager:
    """备份管理器单元测试"""

    def test_init_default(self) -> None:
        manager = BackupManager()
        assert manager.backup_base_dir == Path.home() / ".nanobot-runner" / "backups"

    def test_init_custom_path(self, tmp_path: Path) -> None:
        manager = BackupManager(backup_base_dir=tmp_path / "backups")
        assert manager.backup_base_dir == tmp_path / "backups"

    def test_create_backup_single_file(self, tmp_path: Path) -> None:
        source = tmp_path / "source"
        source.mkdir()
        (source / "config.json").write_text('{"version": "0.9.4"}', encoding="utf-8")

        backup_dir = tmp_path / "backups"
        manager = BackupManager(backup_base_dir=backup_dir)

        result = manager.create_backup(source_paths=[source], compress=False)

        assert result.backup_path.exists()
        assert result.file_count > 0
        assert result.total_size > 0
        assert len(result.checksum) > 0

    def test_create_backup_compressed(self, tmp_path: Path) -> None:
        source = tmp_path / "source"
        source.mkdir()
        (source / "config.json").write_text('{"version": "0.9.4"}', encoding="utf-8")

        backup_dir = tmp_path / "backups"
        manager = BackupManager(backup_base_dir=backup_dir)

        result = manager.create_backup(source_paths=[source], compress=True)

        assert result.backup_path.exists()
        assert str(result.backup_path).endswith(".tar.gz")

    def test_restore_backup(self, tmp_path: Path) -> None:
        source = tmp_path / "source"
        source.mkdir()
        (source / "config.json").write_text('{"version": "0.9.4"}', encoding="utf-8")

        backup_dir = tmp_path / "backups"
        manager = BackupManager(backup_base_dir=backup_dir)

        backup_info = manager.create_backup(source_paths=[source], compress=False)

        restore_dir = tmp_path / "restored"
        restore_dir.mkdir()

        result = manager.restore_backup(backup_info)

        assert "restored_files" in result
        assert result["restored_files"] > 0

    def test_verify_backup(self, tmp_path: Path) -> None:
        source = tmp_path / "source"
        source.mkdir()
        (source / "config.json").write_text('{"version": "0.9.4"}', encoding="utf-8")

        backup_dir = tmp_path / "backups"
        manager = BackupManager(backup_base_dir=backup_dir)

        backup_info = manager.create_backup(source_paths=[source], compress=False)

        is_valid = manager.verify_backup(backup_info)
        assert is_valid is True

    def test_list_backups(self, tmp_path: Path) -> None:
        source = tmp_path / "source"
        source.mkdir()
        (source / "test.txt").write_text("test", encoding="utf-8")

        backup_dir = tmp_path / "backups"
        manager = BackupManager(backup_base_dir=backup_dir)

        manager.create_backup(source_paths=[source], compress=False)

        backups = manager.list_backups()
        assert len(backups) >= 1

    def test_cleanup_old_backups(self, tmp_path: Path) -> None:
        source = tmp_path / "source"
        source.mkdir()
        (source / "test.txt").write_text("test", encoding="utf-8")

        backup_dir = tmp_path / "backups"
        manager = BackupManager(backup_base_dir=backup_dir)

        import time

        manager.create_backup(source_paths=[source], compress=False)
        time.sleep(1.1)
        manager.create_backup(source_paths=[source], compress=False)

        removed = manager.cleanup_old_backups(keep_count=1)
        assert removed >= 1

        remaining = manager.list_backups()
        assert len(remaining) <= 1
