# 自定义异常类模块
# 提供统一的异常处理机制

from dataclasses import dataclass
from typing import Any


@dataclass
class ToolResult:
    """工具统一返回格式"""

    success: bool
    data: Any | None = None
    message: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        result: dict[str, Any] = {"success": self.success}
        if self.data is not None:
            result["data"] = self.data
        if self.message is not None:
            result["message"] = self.message
        if self.error is not None:
            result["error"] = self.error
        return result

    def to_json(self) -> str:
        """转换为JSON字符串"""
        import json

        return json.dumps(self.to_dict(), ensure_ascii=False)


@dataclass
class NanobotRunnerError(Exception):
    """Nanobot Runner 基础异常类"""

    message: str
    error_code: str = "UNKNOWN_ERROR"
    recovery_suggestion: str | None = None

    def __post_init__(self) -> None:
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "error": self.message,
            "error_code": self.error_code,
            "recovery_suggestion": self.recovery_suggestion,
        }


@dataclass
class StorageError(NanobotRunnerError):
    """存储相关错误"""

    error_code: str = "STORAGE_ERROR"
    recovery_suggestion: str | None = "请检查数据目录权限和磁盘空间"


@dataclass
class ParseError(NanobotRunnerError):
    """解析相关错误"""

    error_code: str = "PARSE_ERROR"
    recovery_suggestion: str | None = "请确认文件格式正确，或尝试重新导出FIT文件"


@dataclass
class ConfigError(NanobotRunnerError):
    """配置相关错误"""

    error_code: str = "CONFIG_ERROR"
    recovery_suggestion: str | None = "请检查配置文件格式，或删除配置文件后重新初始化"


@dataclass
class ValidationError(NanobotRunnerError):
    """数据验证错误"""

    error_code: str = "VALIDATION_ERROR"
    recovery_suggestion: str | None = "请检查输入数据是否符合要求"


@dataclass
class IndexStoreError(NanobotRunnerError):
    """索引相关错误"""

    error_code: str = "INDEX_ERROR"
    recovery_suggestion: str | None = "请尝试重新导入数据以重建索引"


@dataclass
class ImportError(NanobotRunnerError):
    """导入相关错误"""

    error_code: str = "IMPORT_ERROR"
    recovery_suggestion: str | None = "请检查文件路径和文件格式"


@dataclass
class LLMError(NanobotRunnerError):
    """LLM调用相关错误"""

    error_code: str = "LLM_ERROR"
    recovery_suggestion: str | None = "请检查LLM服务配置或稍后重试"
