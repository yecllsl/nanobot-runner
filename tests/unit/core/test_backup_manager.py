from pathlib import Path
from unittest.mock import patch

import pytest

from src.core.backup_manager import BackupManager
from src.core.exceptions import StorageError
from src.core.migrate.models import BackupInfo


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

    def test_create_backup_source_not_exists(self, tmp_path: Path) -> None:
        source = tmp_path / "source"
        source.mkdir()
        (source / "config.json").write_text('{"version": "0.9.4"}', encoding="utf-8")

        backup_dir = tmp_path / "backups"
        manager = BackupManager(backup_base_dir=backup_dir)

        result = manager.create_backup(
            source_paths=[source, tmp_path / "nonexist"], compress=False
        )
        assert result.file_count > 0

    def test_create_backup_single_file_source(self, tmp_path: Path) -> None:
        single_file = tmp_path / "single.txt"
        single_file.write_text("single file content", encoding="utf-8")

        backup_dir = tmp_path / "backups"
        manager = BackupManager(backup_base_dir=backup_dir)

        result = manager.create_backup(source_paths=[single_file], compress=False)
        assert result.file_count == 1

    def test_create_backup_os_error(self, tmp_path: Path) -> None:
        source = tmp_path / "source"
        source.mkdir()
        (source / "config.json").write_text('{"version": "0.9.4"}', encoding="utf-8")

        backup_dir = tmp_path / "backups"
        manager = BackupManager(backup_base_dir=backup_dir)

        with patch("shutil.copytree", side_effect=OSError("disk full")):
            with pytest.raises(StorageError, match="创建备份失败"):
                manager.create_backup(source_paths=[source], compress=False)

    def test_restore_backup(self, tmp_path: Path) -> None:
        source = tmp_path / "source"
        source.mkdir()
        (source / "config.json").write_text('{"version": "0.9.4"}', encoding="utf-8")

        backup_dir = tmp_path / "backups"
        manager = BackupManager(backup_base_dir=backup_dir)

        backup_info = manager.create_backup(source_paths=[source], compress=False)

        result = manager.restore_backup(backup_info)

        assert "restored_files" in result
        assert result["restored_files"] > 0

    def test_restore_backup_path_not_exists(self, tmp_path: Path) -> None:
        backup_info = BackupInfo(
            backup_path=tmp_path / "nonexist",
            backup_time="20260418_120000",
            file_count=1,
            total_size=100,
            checksum="abc",
        )

        manager = BackupManager(backup_base_dir=tmp_path / "backups")

        with pytest.raises(StorageError, match="备份路径不存在"):
            manager.restore_backup(backup_info)

    def test_restore_backup_compressed(self, tmp_path: Path) -> None:
        source = tmp_path / "source"
        source.mkdir()
        (source / "config.json").write_text('{"version": "0.9.4"}', encoding="utf-8")

        backup_dir = tmp_path / "backups"
        manager = BackupManager(backup_base_dir=backup_dir)

        backup_info = manager.create_backup(source_paths=[source], compress=True)

        result = manager.restore_backup(backup_info)
        assert "restored_files" in result

    def test_restore_backup_with_subdir(self, tmp_path: Path) -> None:
        source = tmp_path / "source"
        source.mkdir()
        (source / "data").mkdir()
        (source / "data" / "test.txt").write_text("test", encoding="utf-8")
        (source / "config.json").write_text('{"version": "0.9.4"}', encoding="utf-8")

        backup_dir = tmp_path / "backups"
        manager = BackupManager(backup_base_dir=backup_dir)

        backup_info = manager.create_backup(source_paths=[source], compress=False)

        result = manager.restore_backup(backup_info)
        assert result["restored_files"] > 0

    def test_restore_backup_os_error_on_copy(self, tmp_path: Path) -> None:
        source = tmp_path / "source"
        source.mkdir()
        (source / "config.json").write_text('{"version": "0.9.4"}', encoding="utf-8")

        backup_dir = tmp_path / "backups"
        manager = BackupManager(backup_base_dir=backup_dir)

        backup_info = manager.create_backup(source_paths=[source], compress=False)

        with patch("shutil.copytree", side_effect=OSError("permission denied")):
            result = manager.restore_backup(backup_info)
            assert result["failed_files"] > 0

    def test_restore_backup_tar_error(self, tmp_path: Path) -> None:
        backup_info = BackupInfo(
            backup_path=tmp_path / "corrupt.tar.gz",
            backup_time="20260418_120000",
            file_count=1,
            total_size=100,
            checksum="abc",
        )
        corrupt_file = tmp_path / "corrupt.tar.gz"
        corrupt_file.write_text("not a tar file", encoding="utf-8")

        manager = BackupManager(backup_base_dir=tmp_path / "backups")

        with pytest.raises(StorageError, match="恢复备份失败"):
            manager.restore_backup(backup_info)

    def test_verify_backup(self, tmp_path: Path) -> None:
        source = tmp_path / "source"
        source.mkdir()
        (source / "config.json").write_text('{"version": "0.9.4"}', encoding="utf-8")

        backup_dir = tmp_path / "backups"
        manager = BackupManager(backup_base_dir=backup_dir)

        backup_info = manager.create_backup(source_paths=[source], compress=False)

        is_valid = manager.verify_backup(backup_info)
        assert is_valid is True

    def test_verify_backup_compressed(self, tmp_path: Path) -> None:
        source = tmp_path / "source"
        source.mkdir()
        (source / "config.json").write_text('{"version": "0.9.4"}', encoding="utf-8")

        backup_dir = tmp_path / "backups"
        manager = BackupManager(backup_base_dir=backup_dir)

        backup_info = manager.create_backup(source_paths=[source], compress=True)

        is_valid = manager.verify_backup(backup_info)
        assert is_valid is True

    def test_verify_backup_not_exists(self, tmp_path: Path) -> None:
        backup_info = BackupInfo(
            backup_path=tmp_path / "nonexist",
            backup_time="20260418_120000",
            file_count=1,
            total_size=100,
            checksum="abc",
        )

        manager = BackupManager(backup_base_dir=tmp_path / "backups")
        assert manager.verify_backup(backup_info) is False

    def test_verify_backup_corrupt_tar(self, tmp_path: Path) -> None:
        corrupt_file = tmp_path / "backup_test.tar.gz"
        corrupt_file.write_text("not a tar file", encoding="utf-8")

        backup_info = BackupInfo(
            backup_path=corrupt_file,
            backup_time="20260418_120000",
            file_count=1,
            total_size=100,
            checksum="abc",
        )

        manager = BackupManager(backup_base_dir=tmp_path / "backups")
        assert manager.verify_backup(backup_info) is False

    def test_list_backups(self, tmp_path: Path) -> None:
        source = tmp_path / "source"
        source.mkdir()
        (source / "test.txt").write_text("test", encoding="utf-8")

        backup_dir = tmp_path / "backups"
        manager = BackupManager(backup_base_dir=backup_dir)

        manager.create_backup(source_paths=[source], compress=False)

        backups = manager.list_backups()
        assert len(backups) >= 1

    def test_list_backups_empty(self, tmp_path: Path) -> None:
        backup_dir = tmp_path / "backups"
        manager = BackupManager(backup_base_dir=backup_dir)

        backups = manager.list_backups()
        assert backups == []

    def test_list_backups_compressed(self, tmp_path: Path) -> None:
        source = tmp_path / "source"
        source.mkdir()
        (source / "test.txt").write_text("test", encoding="utf-8")

        backup_dir = tmp_path / "backups"
        manager = BackupManager(backup_base_dir=backup_dir)

        manager.create_backup(source_paths=[source], compress=True)

        backups = manager.list_backups()
        assert len(backups) >= 1

    def test_list_backups_dir_without_info(self, tmp_path: Path) -> None:
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        manual_backup = backup_dir / "backup_manual"
        manual_backup.mkdir()
        (manual_backup / "data.txt").write_text("data", encoding="utf-8")

        manager = BackupManager(backup_base_dir=backup_dir)
        backups = manager.list_backups()
        assert len(backups) == 1
        assert backups[0].file_count > 0

    def test_list_backups_corrupt_info_json(self, tmp_path: Path) -> None:
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        corrupt_backup = backup_dir / "backup_corrupt"
        corrupt_backup.mkdir()
        (corrupt_backup / "backup_info.json").write_text(
            "bad json{{{", encoding="utf-8"
        )

        manager = BackupManager(backup_base_dir=backup_dir)
        backups = manager.list_backups()
        assert len(backups) == 0

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

    def test_cleanup_old_backups_nothing_to_delete(self, tmp_path: Path) -> None:
        backup_dir = tmp_path / "backups"
        manager = BackupManager(backup_base_dir=backup_dir)

        removed = manager.cleanup_old_backups(keep_count=5)
        assert removed == 0

    def test_cleanup_old_backups_compressed(self, tmp_path: Path) -> None:
        source = tmp_path / "source"
        source.mkdir()
        (source / "test.txt").write_text("test", encoding="utf-8")

        backup_dir = tmp_path / "backups"
        manager = BackupManager(backup_base_dir=backup_dir)

        import time

        manager.create_backup(source_paths=[source], compress=True)
        time.sleep(1.1)
        manager.create_backup(source_paths=[source], compress=True)

        removed = manager.cleanup_old_backups(keep_count=1)
        assert removed >= 1

    def test_compute_file_checksum(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("hello", encoding="utf-8")

        result = BackupManager._compute_file_checksum(f)
        assert len(result) == 32

    def test_compress_backup_failure(self, tmp_path: Path) -> None:
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "test.txt").write_text("test", encoding="utf-8")

        with patch("tarfile.open", side_effect=OSError("tar error")):
            result = BackupManager._compress_backup(source_dir)
            assert result is None
