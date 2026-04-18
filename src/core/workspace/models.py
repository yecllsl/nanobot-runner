from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class WorkspaceInfo:
    path: Path
    source: str
    exists: bool
    subdirectories: list[str] = field(default_factory=list)
    disk_usage_mb: float = 0.0


@dataclass
class WorkspaceValidationResult:
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
