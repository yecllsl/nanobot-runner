from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class InitMode(Enum):
    FRESH = "fresh"
    MIGRATE = "migrate"


@dataclass(frozen=True)
class EnvironmentInfo:
    python_version: str
    os_type: str
    os_version: str
    dependencies: dict[str, str] = field(default_factory=dict)
    missing_dependencies: list[str] = field(default_factory=list)


@dataclass
class InitResult:
    success: bool
    config_path: Path | None = None
    env_path: Path | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
