from dataclasses import dataclass, field
from enum import Enum


class ErrorLevel(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class ValidationError:
    level: ErrorLevel
    field: str
    message: str
    suggestion: str = ""
    doc_link: str | None = None


@dataclass
class ValidationReport:
    is_valid: bool
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationError] = field(default_factory=list)
    infos: list[ValidationError] = field(default_factory=list)
    summary: dict[str, int] = field(default_factory=dict)
    elapsed_time: float = 0.0


@dataclass(frozen=True)
class ConnectivityResult:
    provider: str
    is_connected: bool
    response_time: float = 0.0
    error_message: str | None = None
