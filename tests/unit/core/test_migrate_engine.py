import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from src.core.backup_manager import BackupManager
from src.core.base.exceptions import StorageError
from src.core.config import ConfigManager
from src.core.migrate.engine import MigrationEngine
from src.core.migrate.models import (
    BackupInfo,
    MigrationResult,
    RollbackResult,
    VersionInfo,
)
from src.core.migrate.strategy import (
    MigrationStrategy,
    MigrationStrategyFactory,
    V08xMigrationStrategy,
    V09xMigrationStrategy,
)


@pytest.fixture(autouse=True)
def reset_config_cache():
    """每个测试前重置 ConfigManager 缓存"""
    ConfigManager.reset_cache()
    yield
    ConfigManager.reset_cache()


class TestMigrationModels:
    """迁移模块数据结构测试"""

    def test_version_info(self) -> None:
        info = VersionInfo(
            version="0.8.3",
            config_path=Path("/tmp/config.json"),
            data_path=Path("/tmp/data"),
            has_data=True,
        )
        assert info.version == "0.8.3"
        assert info.has_data is True

    def test_migration_result_success(self) -> None:
        result = MigrationResult(success=True, migrated_files=5)
        assert result.success is True
        assert result.migrated_files == 5

    def test_migration_result_failure(self) -> None:
        result = MigrationResult(success=False, errors=["error1"])
        assert result.success is False
        assert "error1" in result.errors

    def test_rollback_result(self) -> None:
        result = RollbackResult(success=True, restored_files=3)
        assert result.success is True
        assert result.restored_files == 3


class TestV08xMigrationStrategy:
    """v0.8.x 迁移策略测试"""

    def test_get_source_path(self) -> None:
        strategy = V08xMigrationStrategy()
        assert strategy.get_source_path() == Path.home() / ".nanobot"

    def test_get_target_path(self) -> None:
        strategy = V08xMigrationStrategy()
        assert strategy.get_target_path() == Path.home() / ".nanobot-runner"

    def test_migrate_config_no_source(self, tmp_path: Path) -> None:
        strategy = V08xMigrationStrategy()
        with patch.object(
            strategy, "get_source_path", return_value=tmp_path / "nonexist"
        ):
            result = strategy.migrate_config()
            assert result.success is True
            assert any("不存在" in w for w in result.warnings)

    def test_migrate_config_with_source(self, tmp_path: Path) -> None:
        source = tmp_path / "source"
        source.mkdir()
        (source / "config.json").write_text(
            json.dumps({"auto_push_feishu": True, "feishu_app_id": "test_id"}),
            encoding="utf-8",
        )
        target = tmp_path / "target"

        strategy = V08xMigrationStrategy()
        with patch.object(strategy, "get_source_path", return_value=source):
            with patch.object(strategy, "get_target_path", return_value=target):
                result = strategy.migrate_config()
                assert result.success is True
                assert result.migrated_files == 1

    def test_migrate_data_no_source(self, tmp_path: Path) -> None:
        strategy = V08xMigrationStrategy()
        with patch.object(
            strategy, "get_source_path", return_value=tmp_path / "nonexist"
        ):
            result = strategy.migrate_data()
            assert result.success is True

    def test_update_paths(self, tmp_path: Path) -> None:
        target = tmp_path / "target"
        target.mkdir()
        (target / "config.json").write_text(
            json.dumps({"version": "0.9.4", "data_dir": "/old/path"}),
            encoding="utf-8",
        )

        strategy = V08xMigrationStrategy()
        with patch.object(strategy, "get_target_path", return_value=target):
            result = strategy.update_paths()
            assert result.success is True


class TestV09xMigrationStrategy:
    """v0.9.x 迁移策略测试"""

    def test_migrate_config_adds_defaults(self, tmp_path: Path) -> None:
        target = tmp_path / "nanobot-runner"
        target.mkdir()
        (target / "config.json").write_text(
            json.dumps({"version": "0.9.0", "data_dir": "/tmp/data"}),
            encoding="utf-8",
        )

        strategy = V09xMigrationStrategy(source_version="0.9.0")
        with patch.object(strategy, "get_target_path", return_value=target):
            result = strategy.migrate_config()
            assert result.success is True

            with open(target / "config.json", encoding="utf-8") as f:
                config = json.load(f)
            assert config["version"] == "0.9.4"
            assert "auto_push_feishu" in config

    def test_migrate_data_no_op(self) -> None:
        strategy = V09xMigrationStrategy()
        result = strategy.migrate_data()
        assert result.success is True

    def test_update_paths_no_op(self) -> None:
        strategy = V09xMigrationStrategy()
        result = strategy.update_paths()
        assert result.success is True


class TestMigrationStrategyFactory:
    """迁移策略工厂测试"""

    def test_create_v08_strategy(self) -> None:
        strategy = MigrationStrategyFactory.create_strategy("0.8.3")
        assert isinstance(strategy, V08xMigrationStrategy)

    def test_create_v09_strategy(self) -> None:
        strategy = MigrationStrategyFactory.create_strategy("0.9.1")
        assert isinstance(strategy, V09xMigrationStrategy)

    def test_create_unsupported_version(self) -> None:
        with pytest.raises(ValueError, match="不支持的版本号"):
            MigrationStrategyFactory.create_strategy("1.0.0")


class TestMigrationEngine:
    """迁移引擎测试"""

    def test_detect_old_version_no_legacy(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                config = ConfigManager(allow_default=True)
                engine = MigrationEngine(config=config)
                result = engine.detect_old_version()
                assert result is None

    def test_detect_old_version_with_legacy(self, tmp_path: Path) -> None:
        legacy = tmp_path / ".nanobot"
        legacy.mkdir()
        (legacy / "config.json").write_text(
            json.dumps({"version": "0.8.3"}), encoding="utf-8"
        )

        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                config = ConfigManager(allow_default=True)
                engine = MigrationEngine(config=config)
                result = engine.detect_old_version()
                assert result is not None
                assert result.version == "0.8.3"

    def test_detect_old_version_legacy_bad_json(self, tmp_path: Path) -> None:
        legacy = tmp_path / ".nanobot"
        legacy.mkdir()
        (legacy / "config.json").write_text("invalid json{{{", encoding="utf-8")

        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                config = ConfigManager(allow_default=True)
                engine = MigrationEngine(config=config)
                result = engine.detect_old_version()
                assert result is not None
                assert result.version == "0.8.0"

    def test_detect_old_version_legacy_with_data(self, tmp_path: Path) -> None:
        legacy = tmp_path / ".nanobot"
        legacy.mkdir()
        (legacy / "config.json").write_text(
            json.dumps({"version": "0.8.3"}), encoding="utf-8"
        )
        data_dir = legacy / "data"
        data_dir.mkdir()
        (data_dir / "test.txt").write_text("data", encoding="utf-8")

        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                config = ConfigManager(allow_default=True)
                engine = MigrationEngine(config=config)
                result = engine.detect_old_version()
                assert result is not None
                assert result.has_data is True

    def test_detect_old_version_legacy_no_data(self, tmp_path: Path) -> None:
        legacy = tmp_path / ".nanobot"
        legacy.mkdir()
        (legacy / "config.json").write_text(
            json.dumps({"version": "0.8.3"}), encoding="utf-8"
        )
        (legacy / "data").mkdir()

        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                config = ConfigManager(allow_default=True)
                engine = MigrationEngine(config=config)
                result = engine.detect_old_version()
                assert result is not None
                assert result.has_data is False

    def test_detect_old_version_current_old_version(self, tmp_path: Path) -> None:
        config_dir = tmp_path / ".nanobot-runner"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "config.json").write_text(
            json.dumps({"version": "0.9.2", "data_dir": str(tmp_path / "data")}),
            encoding="utf-8",
        )

        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                config = ConfigManager(allow_default=True)
                engine = MigrationEngine(config=config)
                result = engine.detect_old_version()
                assert result is not None
                assert result.version == "0.9.2"

    def test_detect_old_version_current_bad_json(self, tmp_path: Path) -> None:
        config_dir = tmp_path / ".nanobot-runner"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "config.json").write_text("bad json{{{", encoding="utf-8")

        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                config = ConfigManager(allow_default=True)
                engine = MigrationEngine(config=config)
                result = engine.detect_old_version()
                assert result is None

    def test_detect_old_version_current_already_latest(self, tmp_path: Path) -> None:
        config_dir = tmp_path / ".nanobot-runner"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "config.json").write_text(
            json.dumps({"version": "0.9.4", "data_dir": str(tmp_path / "data")}),
            encoding="utf-8",
        )

        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                config = ConfigManager(allow_default=True)
                engine = MigrationEngine(config=config)
                result = engine.detect_old_version()
                assert result is None

    def test_create_backup_success(self, tmp_path: Path) -> None:
        config_dir = tmp_path / ".nanobot-runner"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "config.json").write_text(
            json.dumps({"version": "0.9.4"}), encoding="utf-8"
        )

        backup_dir = tmp_path / "backups"

        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                config = ConfigManager(allow_default=True)
                engine = MigrationEngine(config=config)
                engine.backup_manager = BackupManager(backup_base_dir=backup_dir)

                backup_info = engine.create_backup()
                assert backup_info is not None
                assert backup_info.file_count > 0

    def test_create_backup_no_source_raises(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                config = ConfigManager(allow_default=True)
                engine = MigrationEngine(config=config)

                with pytest.raises(StorageError, match="没有可备份的数据"):
                    engine.create_backup()

    def test_create_backup_with_legacy(self, tmp_path: Path) -> None:
        legacy = tmp_path / ".nanobot"
        legacy.mkdir()
        (legacy / "config.json").write_text(
            json.dumps({"version": "0.8.3"}), encoding="utf-8"
        )

        config_dir = tmp_path / ".nanobot-runner"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "config.json").write_text(
            json.dumps({"version": "0.9.4"}), encoding="utf-8"
        )

        backup_dir = tmp_path / "backups"

        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                config = ConfigManager(allow_default=True)
                engine = MigrationEngine(config=config)
                engine.backup_manager = BackupManager(backup_base_dir=backup_dir)

                backup_info = engine.create_backup()
                assert backup_info is not None

    def test_migrate_no_old_version(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                config = ConfigManager(allow_default=True)
                engine = MigrationEngine(config=config)
                result = engine.migrate(auto=True)
                assert result.success is True
                assert any("未检测到" in w for w in result.warnings)

    def test_migrate_with_unsupported_version(self, tmp_path: Path) -> None:
        legacy = tmp_path / ".nanobot"
        legacy.mkdir()
        (legacy / "config.json").write_text(
            json.dumps({"version": "0.8.3"}), encoding="utf-8"
        )

        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                config = ConfigManager(allow_default=True)
                engine = MigrationEngine(config=config)

                with patch.object(
                    engine,
                    "detect_old_version",
                    return_value=VersionInfo(
                        version="1.0.0",
                        config_path=legacy / "config.json",
                        data_path=legacy / "data",
                        has_data=False,
                    ),
                ):
                    result = engine.migrate(auto=True)
                    assert result.success is False
                    assert any("不支持的版本号" in e for e in result.errors)

    def test_migrate_with_v08_strategy_auto(self, tmp_path: Path) -> None:
        legacy = tmp_path / ".nanobot"
        legacy.mkdir()
        (legacy / "config.json").write_text(
            json.dumps({"version": "0.8.3", "auto_push_feishu": True}),
            encoding="utf-8",
        )
        (legacy / "data").mkdir()
        (legacy / "data" / "test.txt").write_text("data", encoding="utf-8")

        backup_dir = tmp_path / "backups"

        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                config = ConfigManager(allow_default=True)
                engine = MigrationEngine(config=config)
                engine.backup_manager = BackupManager(backup_base_dir=backup_dir)

                result = engine.migrate(auto=True)
                assert isinstance(result, MigrationResult)

    def test_migrate_with_explicit_strategy(self, tmp_path: Path) -> None:
        strategy = V09xMigrationStrategy(source_version="0.9.0")

        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                config = ConfigManager(allow_default=True)
                engine = MigrationEngine(config=config)

                result = engine.migrate(strategy=strategy, auto=True)
                assert isinstance(result, MigrationResult)

    def test_migrate_non_auto_creates_backup(self, tmp_path: Path) -> None:
        strategy = V09xMigrationStrategy(source_version="0.9.0")
        backup_dir = tmp_path / "backups"

        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                config = ConfigManager(allow_default=True)
                engine = MigrationEngine(config=config)
                engine.backup_manager = BackupManager(backup_base_dir=backup_dir)

                result = engine.migrate(strategy=strategy, auto=False)
                assert isinstance(result, MigrationResult)

    def test_migrate_config_errors_skip_path_update(self, tmp_path: Path) -> None:
        from unittest.mock import Mock

        mock_strategy = Mock(spec=MigrationStrategy)
        mock_strategy.migrate_config.return_value = MigrationResult(
            success=False, errors=["config error"]
        )
        mock_strategy.migrate_data.return_value = MigrationResult(success=True)

        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                config = ConfigManager(allow_default=True)
                engine = MigrationEngine(config=config)

                result = engine.migrate(strategy=mock_strategy, auto=True)
                assert result.success is False
                mock_strategy.update_paths.assert_not_called()

    def test_migrate_exception_returns_failure(self, tmp_path: Path) -> None:
        from unittest.mock import Mock

        mock_strategy = Mock(spec=MigrationStrategy)
        mock_strategy.migrate_config.side_effect = RuntimeError("unexpected")

        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                config = ConfigManager(allow_default=True)
                engine = MigrationEngine(config=config)

                result = engine.migrate(strategy=mock_strategy, auto=True)
                assert result.success is False
                assert any("unexpected" in e for e in result.errors)

    def test_rollback_no_backup(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                config = ConfigManager(allow_default=True)
                engine = MigrationEngine(config=config)

                result = engine.rollback()
                assert result.success is False
                assert any("没有可用的备份" in e for e in result.errors)

    def test_rollback_with_explicit_backup(self, tmp_path: Path) -> None:
        source = tmp_path / "source"
        source.mkdir()
        (source / "config.json").write_text(
            json.dumps({"version": "0.9.4"}), encoding="utf-8"
        )

        backup_dir = tmp_path / "backups"
        backup_mgr = BackupManager(backup_base_dir=backup_dir)
        backup_info = backup_mgr.create_backup(source_paths=[source], compress=False)

        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                config = ConfigManager(allow_default=True)
                engine = MigrationEngine(config=config, backup_manager=backup_mgr)

                result = engine.rollback(backup_info=backup_info)
                assert isinstance(result, RollbackResult)

    def test_rollback_with_last_backup(self, tmp_path: Path) -> None:
        source = tmp_path / "source"
        source.mkdir()
        (source / "config.json").write_text(
            json.dumps({"version": "0.9.4"}), encoding="utf-8"
        )

        backup_dir = tmp_path / "backups"
        backup_mgr = BackupManager(backup_base_dir=backup_dir)
        backup_info = backup_mgr.create_backup(source_paths=[source], compress=False)

        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                config = ConfigManager(allow_default=True)
                engine = MigrationEngine(config=config, backup_manager=backup_mgr)
                engine._last_backup = backup_info

                result = engine.rollback()
                assert isinstance(result, RollbackResult)

    def test_rollback_storage_error(self, tmp_path: Path) -> None:
        from unittest.mock import Mock

        mock_backup_mgr = Mock()
        mock_backup_mgr.restore_backup.side_effect = StorageError("restore failed")

        backup_info = BackupInfo(
            backup_path=tmp_path / "backup",
            backup_time="20260418_120000",
            file_count=1,
            total_size=100,
            checksum="abc",
        )

        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                config = ConfigManager(allow_default=True)
                engine = MigrationEngine(config=config, backup_manager=mock_backup_mgr)

                result = engine.rollback(backup_info=backup_info)
                assert result.success is False
                assert any("restore failed" in e for e in result.errors)

    def test_verify_migration(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                config = ConfigManager(allow_default=True)
                engine = MigrationEngine(config=config)
                result = engine.verify_migration()
                assert isinstance(result, MigrationResult)

    def test_verify_migration_with_data_files(self, tmp_path: Path) -> None:
        config_dir = tmp_path / ".nanobot-runner"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "config.json").write_text(
            json.dumps({"version": "0.9.4", "data_dir": str(tmp_path / "data")}),
            encoding="utf-8",
        )

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "activities_2024.parquet").write_text("fake", encoding="utf-8")

        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=tmp_path):
                config = ConfigManager(allow_default=True)
                engine = MigrationEngine(config=config)
                result = engine.verify_migration()
                assert isinstance(result, MigrationResult)
