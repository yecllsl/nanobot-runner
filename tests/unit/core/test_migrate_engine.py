import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.core.config import ConfigManager
from src.core.migrate.engine import MigrationEngine
from src.core.migrate.models import (
    MigrationResult,
    RollbackResult,
    VersionInfo,
)
from src.core.migrate.strategy import (
    MigrationStrategyFactory,
    V08xMigrationStrategy,
    V09xMigrationStrategy,
)


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

        with patch.object(Path, "home", return_value=tmp_path):
            config = ConfigManager(allow_default=True)
            engine = MigrationEngine(config=config)
            result = engine.detect_old_version()
            assert result is not None
            assert result.version == "0.8.3"

    def test_migrate_no_old_version(self, tmp_path: Path) -> None:
        with patch.object(Path, "home", return_value=tmp_path):
            config = ConfigManager(allow_default=True)
            engine = MigrationEngine(config=config)
            result = engine.migrate(auto=True)
            assert result.success is True
            assert any("未检测到" in w for w in result.warnings)

    def test_verify_migration(self, tmp_path: Path) -> None:
        with patch.object(Path, "home", return_value=tmp_path):
            config = ConfigManager(allow_default=True)
            engine = MigrationEngine(config=config)
            result = engine.verify_migration()
            assert isinstance(result, MigrationResult)
