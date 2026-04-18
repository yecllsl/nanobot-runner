from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class VersionInfo:
    version: str
    config_path: Path
    data_path: Path
    has_data: bool


@dataclass(frozen=True)
class BackupInfo:
    backup_path: Path
    backup_time: str
    file_count: int
    total_size: int
    checksum: str


@dataclass
class MigrationResult:
    success: bool
    migrated_files: int = 0
    failed_files: int = 0
    elapsed_time: float = 0.0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    report_path: Path | None = None


@dataclass
class RollbackResult:
    success: bool
    restored_files: int = 0
    elapsed_time: float = 0.0
    errors: list[str] = field(default_factory=list)
