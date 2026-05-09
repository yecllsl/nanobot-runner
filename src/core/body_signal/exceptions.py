from dataclasses import dataclass

from src.core.base.exceptions import NanobotRunnerError


@dataclass
class BodySignalError(NanobotRunnerError):
    """身体信号分析基础异常"""

    error_code: str = "BODY_SIGNAL_ERROR"
    recovery_suggestion: str | None = "请检查身体信号数据是否完整"


@dataclass
class DataNotFoundError(BodySignalError):
    """数据未找到异常"""

    error_code: str = "DATA_NOT_FOUND"
    recovery_suggestion: str | None = "请先导入跑步数据以进行分析"


@dataclass
class CalculationError(BodySignalError):
    """计算过程异常"""

    error_code: str = "CALCULATION_ERROR"
    recovery_suggestion: str | None = "请检查输入数据是否有效"
