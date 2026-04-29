import json
import time
from pathlib import Path

from src.core.base.exceptions import StorageError
from src.core.base.logger import get_logger
from src.core.config.backup_manager import BackupManager
from src.core.config.manager import ConfigManager
from src.core.migrate.models import (
    BackupInfo,
    MigrationResult,
    RollbackResult,
    VersionInfo,
)
from src.core.migrate.strategy import MigrationStrategy, MigrationStrategyFactory
from src.core.verify_manager import VerifyManager

logger = get_logger(__name__)


class MigrationEngine:
    """迁移引擎

    执行配置和数据迁移，支持多版本迁移策略、备份和回滚。
    """

    def __init__(
        self,
        config: ConfigManager,
        backup_manager: BackupManager | None = None,
        verify_manager: VerifyManager | None = None,
    ) -> None:
        """初始化迁移引擎

        Args:
            config: 配置管理器
            backup_manager: 备份管理器（可选）
            verify_manager: 校验管理器（可选）
        """
        self.config = config
        self.backup_manager = backup_manager or BackupManager()
        self.verify_manager = verify_manager or VerifyManager()
        self._last_backup: BackupInfo | None = None

    def detect_old_version(self) -> VersionInfo | None:
        """检测旧版本信息

        Returns:
            VersionInfo | None: 旧版本信息，如果不存在则返回 None
        """
        legacy_path = Path.home() / ".nanobot"
        if legacy_path.exists():
            config_file = legacy_path / "config.json"
            version = "0.8.0"
            if config_file.exists():
                try:
                    with open(config_file, encoding="utf-8") as f:
                        old_config = json.load(f)
                    version = old_config.get("version", "0.8.0")
                except (json.JSONDecodeError, OSError):
                    pass

            data_path = legacy_path / "data"
            return VersionInfo(
                version=version,
                config_path=config_file,
                data_path=data_path,
                has_data=data_path.exists() and any(data_path.iterdir()),
            )

        current_config = self.config.config_file
        if current_config.exists():
            try:
                with open(current_config, encoding="utf-8") as f:
                    cfg = json.load(f)
                version = cfg.get("version", "0.9.0")
                if version != "0.9.4":
                    return VersionInfo(
                        version=version,
                        config_path=current_config,
                        data_path=self.config.data_dir,
                        has_data=self.config.data_dir.exists()
                        and any(self.config.data_dir.iterdir()),
                    )
            except (json.JSONDecodeError, OSError):
                pass

        return None

    def create_backup(self) -> BackupInfo:
        """创建备份

        Returns:
            BackupInfo: 备份信息
        """
        source_paths: list[Path] = []

        if self.config.base_dir.exists():
            source_paths.append(self.config.base_dir)

        legacy_path = Path.home() / ".nanobot"
        if legacy_path.exists():
            source_paths.append(legacy_path)

        if not source_paths:
            raise StorageError("没有可备份的数据")

        backup_info = self.backup_manager.create_backup(
            source_paths=source_paths,
            compress=True,
        )
        self._last_backup = backup_info
        logger.info(f"备份已创建: {backup_info.backup_path}")
        return backup_info

    def migrate(
        self,
        strategy: MigrationStrategy | None = None,
        auto: bool = False,
    ) -> MigrationResult:
        """执行迁移

        Args:
            strategy: 迁移策略（可选，自动检测时传入 None）
            auto: 是否自动模式

        Returns:
            MigrationResult: 迁移结果
        """
        start_time = time.time()

        try:
            if strategy is None:
                version_info = self.detect_old_version()
                if version_info is None:
                    return MigrationResult(
                        success=True,
                        warnings=["未检测到需要迁移的旧版本"],
                        elapsed_time=time.time() - start_time,
                    )

                try:
                    strategy = MigrationStrategyFactory.create_strategy(
                        version_info.version
                    )
                except ValueError as e:
                    return MigrationResult(
                        success=False,
                        errors=[str(e)],
                        elapsed_time=time.time() - start_time,
                    )

            total_migrated = 0
            total_failed = 0
            all_errors: list[str] = []
            all_warnings: list[str] = []

            if not auto:
                backup_info = self.create_backup()
                self._last_backup = backup_info

            config_result = strategy.migrate_config()
            total_migrated += config_result.migrated_files
            total_failed += config_result.failed_files
            all_errors.extend(config_result.errors)
            all_warnings.extend(config_result.warnings)

            data_result = strategy.migrate_data()
            total_migrated += data_result.migrated_files
            total_failed += data_result.failed_files
            all_errors.extend(data_result.errors)
            all_warnings.extend(data_result.warnings)

            if not all_errors:
                path_result = strategy.update_paths()
                total_migrated += path_result.migrated_files
                total_failed += path_result.failed_files
                all_errors.extend(path_result.errors)
                all_warnings.extend(path_result.warnings)

            elapsed = time.time() - start_time

            return MigrationResult(
                success=len(all_errors) == 0,
                migrated_files=total_migrated,
                failed_files=total_failed,
                elapsed_time=elapsed,
                errors=all_errors,
                warnings=all_warnings,
            )

        except Exception as e:
            logger.error(f"迁移执行失败: {e}")
            return MigrationResult(
                success=False,
                errors=[str(e)],
                elapsed_time=time.time() - start_time,
            )

    def rollback(self, backup_info: BackupInfo | None = None) -> RollbackResult:
        """回滚迁移

        Args:
            backup_info: 备份信息（可选，使用最近一次备份）

        Returns:
            RollbackResult: 回滚结果
        """
        target_backup = backup_info or self._last_backup

        if target_backup is None:
            return RollbackResult(
                success=False,
                errors=["没有可用的备份信息"],
            )

        start_time = time.time()

        try:
            result = self.backup_manager.restore_backup(target_backup)
            elapsed = time.time() - start_time

            return RollbackResult(
                success=result.get("failed_files", 1) == 0,
                restored_files=result.get("restored_files", 0),
                elapsed_time=elapsed,
                errors=[]
                if result.get("failed_files", 0) == 0
                else ["部分文件恢复失败"],
            )

        except StorageError as e:
            return RollbackResult(
                success=False,
                errors=[str(e)],
                elapsed_time=time.time() - start_time,
            )

    def verify_migration(self) -> MigrationResult:
        """验证迁移结果

        Returns:
            MigrationResult: 验证结果
        """
        errors: list[str] = []
        warnings: list[str] = []

        config_file = self.config.config_file
        if not config_file.exists():
            errors.append("配置文件不存在")
        else:
            config_report = self.verify_manager.verify_config(self.config.load_config())
            errors.extend(config_report.errors)
            warnings.extend(config_report.warnings)

        data_dir = self.config.data_dir
        if data_dir.exists():
            parquet_files = list(data_dir.glob("activities_*.parquet"))
            if parquet_files:
                file_report = self.verify_manager.verify_files(parquet_files)
                errors.extend(file_report.errors)
                warnings.extend(file_report.warnings)

        return MigrationResult(
            success=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )
