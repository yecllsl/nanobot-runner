import hashlib
import json
import shutil
import tarfile
from datetime import datetime
from pathlib import Path

from src.core.exceptions import StorageError
from src.core.logger import get_logger
from src.core.migrate.models import BackupInfo

logger = get_logger(__name__)


class BackupManager:
    """备份和恢复管理器

    提供配置和数据的备份、恢复、验证功能，支持压缩备份。
    """

    def __init__(self, backup_base_dir: Path | None = None) -> None:
        """初始化备份管理器

        Args:
            backup_base_dir: 备份基础目录，默认为 ~/.nanobot-runner/backups
        """
        self.backup_base_dir = backup_base_dir or (
            Path.home() / ".nanobot-runner" / "backups"
        )

    def create_backup(
        self,
        source_paths: list[Path],
        backup_dir: Path | None = None,
        compress: bool = True,
    ) -> BackupInfo:
        """创建备份

        Args:
            source_paths: 需要备份的源路径列表
            backup_dir: 备份目录，默认使用时间戳自动生成
            compress: 是否压缩备份

        Returns:
            BackupInfo: 备份信息

        Raises:
            StorageError: 备份创建失败时抛出
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_dir = backup_dir or self.backup_base_dir / f"backup_{timestamp}"

        try:
            target_dir.mkdir(parents=True, exist_ok=True)

            file_count = 0
            total_size = 0
            checksum_parts: list[str] = []

            for source_path in source_paths:
                if not source_path.exists():
                    logger.warning(f"源路径不存在，跳过: {source_path}")
                    continue

                if source_path.is_file():
                    dest = target_dir / source_path.name
                    shutil.copy2(source_path, dest)
                    file_count += 1
                    total_size += dest.stat().st_size
                    checksum_parts.append(self._compute_file_checksum(dest))
                elif source_path.is_dir():
                    dest = target_dir / source_path.name
                    shutil.copytree(source_path, dest, dirs_exist_ok=True)
                    count, size, cks = self._compute_dir_stats(dest)
                    file_count += count
                    total_size += size
                    checksum_parts.extend(cks)

            checksum = hashlib.md5(
                ",".join(sorted(checksum_parts)).encode()
            ).hexdigest()

            if compress:
                archive_path = self._compress_backup(target_dir)
                if archive_path:
                    shutil.rmtree(target_dir, ignore_errors=True)
                    target_dir = archive_path

            backup_info = BackupInfo(
                backup_path=target_dir,
                backup_time=timestamp,
                file_count=file_count,
                total_size=total_size,
                checksum=checksum,
            )

            info_file = (
                self.backup_base_dir / f"backup_{timestamp}" / "backup_info.json"
            )
            if not compress:
                info_file.parent.mkdir(parents=True, exist_ok=True)
                with open(info_file, "w", encoding="utf-8") as f:
                    json.dump(
                        {
                            "backup_path": str(backup_info.backup_path),
                            "backup_time": backup_info.backup_time,
                            "file_count": backup_info.file_count,
                            "total_size": backup_info.total_size,
                            "checksum": backup_info.checksum,
                        },
                        f,
                        indent=2,
                    )

            logger.info(f"备份创建成功: {file_count} 个文件, {total_size} 字节")
            return backup_info

        except OSError as e:
            raise StorageError(
                f"创建备份失败: {e}",
                recovery_suggestion="请检查磁盘空间和目录权限",
            ) from e

    def restore_backup(self, backup_info: BackupInfo) -> dict[str, int]:
        """恢复备份

        Args:
            backup_info: 备份信息

        Returns:
            dict[str, int]: 恢复结果，包含 restored_files 和 failed_files

        Raises:
            StorageError: 恢复失败时抛出
        """
        backup_path = backup_info.backup_path

        if not backup_path.exists():
            raise StorageError(
                f"备份路径不存在: {backup_path}",
                recovery_suggestion="请确认备份文件是否已被删除",
            )

        try:
            restored = 0
            failed = 0

            tar_path = backup_path.with_suffix(".tar.gz")
            if tar_path.exists():
                with tarfile.open(tar_path, "r:gz") as tar:
                    tar.extractall(path=backup_path.parent)
                    restored = len(tar.getmembers())
            else:
                for item in backup_path.iterdir():
                    if item.name == "backup_info.json":
                        continue
                    try:
                        target = Path.home() / ".nanobot-runner" / item.name
                        if item.is_file():
                            shutil.copy2(item, target)
                            restored += 1
                        elif item.is_dir():
                            shutil.copytree(item, target, dirs_exist_ok=True)
                            count, _, _ = self._compute_dir_stats(target)
                            restored += count
                    except OSError as e:
                        logger.warning(f"恢复文件失败: {item} - {e}")
                        failed += 1

            logger.info(f"备份恢复完成: 恢复 {restored} 个, 失败 {failed} 个")
            return {"restored_files": restored, "failed_files": failed}

        except (OSError, tarfile.TarError) as e:
            raise StorageError(
                f"恢复备份失败: {e}",
                recovery_suggestion="请检查备份文件完整性",
            ) from e

    def verify_backup(self, backup_info: BackupInfo) -> bool:
        """验证备份完整性

        Args:
            backup_info: 备份信息

        Returns:
            bool: 备份是否完整
        """
        backup_path = backup_info.backup_path

        tar_path = backup_path.with_suffix(".tar.gz")
        if tar_path.exists():
            try:
                with tarfile.open(tar_path, "r:gz") as tar:
                    tar.getmembers()
                return True
            except tarfile.TarError:
                return False

        if not backup_path.exists():
            return False

        _, _, checksums = self._compute_dir_stats(backup_path)
        current_checksum = hashlib.md5(",".join(sorted(checksums)).encode()).hexdigest()

        return current_checksum == backup_info.checksum

    def list_backups(self) -> list[BackupInfo]:
        """列出所有备份

        Returns:
            list[BackupInfo]: 备份信息列表
        """
        backups: list[BackupInfo] = []

        if not self.backup_base_dir.exists():
            return backups

        for item in sorted(self.backup_base_dir.iterdir(), reverse=True):
            if not item.name.startswith("backup_"):
                continue

            if item.is_file() and item.suffix == ".gz" and ".tar" in item.name:
                backups.append(
                    BackupInfo(
                        backup_path=item,
                        backup_time=item.stem.replace("backup_", "").replace(
                            ".tar", ""
                        ),
                        file_count=0,
                        total_size=item.stat().st_size,
                        checksum="",
                    )
                )
            elif item.is_dir():
                info_file = item / "backup_info.json"
                if info_file.exists():
                    try:
                        with open(info_file, encoding="utf-8") as f:
                            data = json.load(f)
                        backups.append(
                            BackupInfo(
                                backup_path=Path(data["backup_path"]),
                                backup_time=data["backup_time"],
                                file_count=data["file_count"],
                                total_size=data["total_size"],
                                checksum=data["checksum"],
                            )
                        )
                    except (json.JSONDecodeError, KeyError):
                        logger.warning(f"备份信息文件损坏: {info_file}")
                else:
                    count, size, _ = self._compute_dir_stats(item)
                    backups.append(
                        BackupInfo(
                            backup_path=item,
                            backup_time=item.name.replace("backup_", ""),
                            file_count=count,
                            total_size=size,
                            checksum="",
                        )
                    )

        return backups

    def cleanup_old_backups(self, keep_count: int = 5) -> int:
        """清理旧备份

        Args:
            keep_count: 保留的备份数量

        Returns:
            int: 删除的备份数量
        """
        backups = self.list_backups()
        if len(backups) <= keep_count:
            return 0

        to_delete = backups[keep_count:]
        deleted = 0

        for backup in to_delete:
            try:
                if backup.backup_path.is_dir():
                    shutil.rmtree(backup.backup_path)
                elif backup.backup_path.is_file():
                    backup.backup_path.unlink()
                tar_path = backup.backup_path.with_suffix(".tar.gz")
                if tar_path.exists() and tar_path != backup.backup_path:
                    tar_path.unlink()
                deleted += 1
            except OSError as e:
                logger.warning(f"删除备份失败: {backup.backup_path} - {e}")

        logger.info(f"已清理 {deleted} 个旧备份")
        return deleted

    @staticmethod
    def _compute_file_checksum(file_path: Path) -> str:
        """计算文件校验和

        Args:
            file_path: 文件路径

        Returns:
            str: MD5校验和
        """
        hasher = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def _compute_dir_stats(dir_path: Path) -> tuple[int, int, list[str]]:
        """计算目录统计信息

        Args:
            dir_path: 目录路径

        Returns:
            tuple[int, int, list[str]]: (文件数, 总大小, 校验和列表)
        """
        file_count = 0
        total_size = 0
        checksums: list[str] = []

        for item in dir_path.rglob("*"):
            if item.is_file() and item.name != "backup_info.json":
                file_count += 1
                total_size += item.stat().st_size
                try:
                    hasher = hashlib.md5()
                    with open(item, "rb") as f:
                        for chunk in iter(lambda: f.read(8192), b""):
                            hasher.update(chunk)
                    checksums.append(hasher.hexdigest())
                except OSError:
                    pass

        return file_count, total_size, checksums

    @staticmethod
    def _compress_backup(source_dir: Path) -> Path | None:
        """压缩备份目录

        Args:
            source_dir: 源目录

        Returns:
            Path | None: 压缩文件路径，失败返回 None
        """
        archive_path = source_dir.with_suffix(".tar.gz")
        try:
            with tarfile.open(archive_path, "w:gz") as tar:
                for item in source_dir.iterdir():
                    tar.add(item, arcname=item.name)
            return archive_path
        except (OSError, tarfile.TarError) as e:
            logger.warning(f"压缩备份失败: {e}")
            return None
