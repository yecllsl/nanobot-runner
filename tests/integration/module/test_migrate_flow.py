import json
from pathlib import Path
from unittest.mock import patch

from src.core.config.backup_manager import BackupManager
from src.core.config.manager import ConfigManager
from src.core.migrate.engine import MigrationEngine
from src.core.migrate.models import MigrationResult
from src.core.verify_manager import VerifyManager


class TestMigrateFlowIntegration:
    """迁移流程集成测试：MigrationEngine → BackupManager → VerifyManager"""

    def test_detect_old_v08_version(self, tmp_path: Path) -> None:
        """检测 v0.8.x 旧版本"""
        old_dir = tmp_path / ".nanobot"
        old_dir.mkdir(parents=True, exist_ok=True)
        (old_dir / "config.json").write_text(
            json.dumps({"version": "0.8.5", "data_dir": str(old_dir / "data")}),
            encoding="utf-8",
        )

        with patch.object(Path, "home", return_value=tmp_path):
            config = ConfigManager(allow_default=True)
            engine = MigrationEngine(config=config)

            version_info = engine.detect_old_version()
            assert version_info is not None
            assert version_info.version == "0.8.5"

    def test_detect_no_old_version(self, tmp_path: Path) -> None:
        """无旧版本时返回 None"""
        with patch.object(Path, "home", return_value=tmp_path):
            config = ConfigManager(allow_default=True)
            engine = MigrationEngine(config=config)

            version_info = engine.detect_old_version()
            assert version_info is None

    def test_backup_before_migration(self, tmp_path: Path) -> None:
        """迁移前自动备份"""
        config_dir = tmp_path / ".nanobot-runner"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "config.json").write_text(
            json.dumps({"version": "0.9.4", "data_dir": str(config_dir / "data")}),
            encoding="utf-8",
        )
        (config_dir / "data").mkdir(exist_ok=True)

        backup_dir = tmp_path / "backups"
        manager = BackupManager(backup_base_dir=backup_dir)

        result = manager.create_backup(
            source_paths=[config_dir],
            compress=False,
        )

        assert result.backup_path.exists()
        assert result.file_count > 0

    def test_backup_and_restore_roundtrip(self, tmp_path: Path) -> None:
        """备份 → 恢复完整流程"""
        source = tmp_path / "source"
        source.mkdir()
        (source / "config.json").write_text(
            json.dumps({"version": "0.9.4", "data_dir": "/tmp/data"}),
            encoding="utf-8",
        )
        (source / "data").mkdir()
        (source / "data" / "test.txt").write_text("test data", encoding="utf-8")

        backup_dir = tmp_path / "backups"
        manager = BackupManager(backup_base_dir=backup_dir)

        backup_info = manager.create_backup(
            source_paths=[source],
            compress=False,
        )

        assert backup_info.backup_path.exists()

        restore_result = manager.restore_backup(backup_info)
        assert restore_result is not None

    def test_verify_config_after_creation(self, tmp_path: Path) -> None:
        """创建配置后校验"""
        config_dir = tmp_path / ".nanobot-runner"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_data = {"version": "0.9.4", "data_dir": str(tmp_path / "data")}
        (config_dir / "config.json").write_text(
            json.dumps(config_data), encoding="utf-8"
        )

        verify_manager = VerifyManager()
        report = verify_manager.verify_config(config_data)
        assert report.success is True

    def test_verify_parquet_files(self, tmp_path: Path) -> None:
        """校验 Parquet 文件完整性"""
        import polars as pl

        data_dir = tmp_path / "data"
        data_dir.mkdir(parents=True, exist_ok=True)

        df = pl.DataFrame({"distance": [5.0, 10.0], "duration": [1800, 3600]})
        df.write_parquet(data_dir / "activities_2024.parquet")

        verify_manager = VerifyManager()
        report = verify_manager.verify_files([data_dir / "activities_2024.parquet"])

        assert report.success is True
        assert report.checked_files == 1

    def test_migration_auto_detect(self, tmp_path: Path) -> None:
        """自动检测迁移"""
        with patch.object(Path, "home", return_value=tmp_path):
            config = ConfigManager(allow_default=True)
            engine = MigrationEngine(config=config)

            result = engine.migrate(auto=True)
            assert isinstance(result, MigrationResult)
