# 错误分类器模块
# 将原始异常分类为标准错误类型，生成友好提示和恢复建议

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

from src.core.base.exceptions import (
    ConfigError,
    ImportError,
    IndexStoreError,
    LLMError,
    NanobotRunnerError,
    ParseError,
    StorageError,
    ValidationError,
)

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """标准错误类型枚举"""

    NETWORK = "network"
    DATA = "data"
    CONFIG = "config"
    PERMISSION = "permission"
    TIMEOUT = "timeout"
    TOOL = "tool"
    UNKNOWN = "unknown"


@dataclass
class FriendlyError:
    """友好错误信息数据类

    Attributes:
        category: 错误分类
        original_error: 原始异常对象
        friendly_message: 面向用户的友好提示
        recovery_suggestion: 恢复建议
        context_data: 额外的上下文数据
    """

    category: ErrorCategory
    original_error: Exception
    friendly_message: str
    recovery_suggestion: str
    context_data: dict[str, Any] | None = None


# 错误模式匹配规则：异常类型 -> 错误分类
ERROR_TYPE_PATTERNS: dict[type[Exception], ErrorCategory] = {
    # 存储相关 -> DATA
    StorageError: ErrorCategory.DATA,
    IndexStoreError: ErrorCategory.DATA,
    # 解析相关 -> DATA
    ParseError: ErrorCategory.DATA,
    ValidationError: ErrorCategory.DATA,
    # 配置相关 -> CONFIG
    ConfigError: ErrorCategory.CONFIG,
    # 导入相关 -> TOOL
    ImportError: ErrorCategory.TOOL,
    # LLM相关 -> NETWORK
    LLMError: ErrorCategory.NETWORK,
}

# 错误消息关键词匹配规则：关键词 -> 错误分类
ERROR_MESSAGE_PATTERNS: dict[ErrorCategory, list[str]] = {
    ErrorCategory.NETWORK: [
        "connection",
        "connect",
        "network",
        "unreachable",
        "refused",
        "dns",
        "timeout",
        "timed out",
        "ssl",
        "certificate",
        "llm",
        "api",
        "http",
        "请求",
        "连接",
        "网络",
    ],
    ErrorCategory.DATA: [
        "storage",
        "database",
        "parquet",
        "index",
        "parse",
        "format",
        "invalid",
        "corrupt",
        "missing",
        "not found",
        "storage",
        "数据",
        "解析",
        "格式",
        "损坏",
    ],
    ErrorCategory.CONFIG: [
        "config",
        "configuration",
        "setting",
        "env",
        "environment",
        "配置",
        "设置",
    ],
    ErrorCategory.PERMISSION: [
        "permission",
        "access denied",
        "forbidden",
        "unauthorized",
        "auth",
        "权限",
        "拒绝",
    ],
    ErrorCategory.TIMEOUT: [
        "timeout",
        "timed out",
        "deadline",
        "expired",
        "超时",
    ],
    ErrorCategory.TOOL: [
        "tool",
        "mcp",
        "spawn",
        "subagent",
        "invoke",
        "工具",
        "调用",
    ],
}

# 分类对应的友好消息模板
FRIENDLY_MESSAGES: dict[ErrorCategory, str] = {
    ErrorCategory.NETWORK: "网络连接出现问题，无法与外部服务通信。",
    ErrorCategory.DATA: "数据读取或处理时出现问题。",
    ErrorCategory.CONFIG: "配置信息有误或缺失。",
    ErrorCategory.PERMISSION: "权限不足，无法执行该操作。",
    ErrorCategory.TIMEOUT: "操作执行时间过长，已超时。",
    ErrorCategory.TOOL: "工具调用失败。",
    ErrorCategory.UNKNOWN: "发生未知错误。",
}

# 分类对应的恢复建议模板
RECOVERY_SUGGESTIONS: dict[ErrorCategory, str] = {
    ErrorCategory.NETWORK: "请检查网络连接，确认服务地址和端口是否正确，稍后重试。",
    ErrorCategory.DATA: "请检查数据文件是否完整，尝试重新导入数据或重建索引。",
    ErrorCategory.CONFIG: "请检查配置文件格式，或运行 `nanobotrun system init` 重新初始化。",
    ErrorCategory.PERMISSION: "请检查文件/目录权限，确认API密钥是否有效。",
    ErrorCategory.TIMEOUT: "请稍后重试，或检查服务是否过载。",
    ErrorCategory.TOOL: "请检查工具配置，确认MCP服务器是否正常运行。",
    ErrorCategory.UNKNOWN: "请查看详细错误信息，或联系支持人员。",
}


class ErrorClassifier:
    """错误分类器

    将原始异常分类为标准错误类型，生成友好提示和恢复建议。
    """

    @staticmethod
    def classify(
        error: str | Exception,
        context_data: dict[str, Any] | None = None,
    ) -> FriendlyError:
        """将原始异常分类为友好错误信息

        支持通过异常类型和错误消息关键词两种方式进行分类。

        Args:
            error: 原始异常对象或错误消息字符串
            context_data: 额外的上下文数据

        Returns:
            FriendlyError: 分类后的友好错误信息
        """
        if isinstance(error, str):
            original_error = Exception(error)
            error_message = error.lower()
        else:
            original_error = error
            error_message = str(error).lower()

        category = ErrorClassifier._classify_by_type(original_error)
        if category == ErrorCategory.UNKNOWN:
            category = ErrorClassifier._classify_by_message(error_message)

        friendly_message = FRIENDLY_MESSAGES[category]
        recovery_suggestion = RECOVERY_SUGGESTIONS[category]

        # 如果是项目自定义异常，使用异常自带的恢复建议
        if (
            isinstance(original_error, NanobotRunnerError)
            and original_error.recovery_suggestion
        ):
            recovery_suggestion = original_error.recovery_suggestion

        # 如果是项目自定义异常，使用异常消息作为友好消息
        if isinstance(original_error, NanobotRunnerError):
            friendly_message = original_error.message

        return FriendlyError(
            category=category,
            original_error=original_error,
            friendly_message=friendly_message,
            recovery_suggestion=recovery_suggestion,
            context_data=context_data,
        )

    @staticmethod
    def _classify_by_type(error: Exception) -> ErrorCategory:
        """通过异常类型分类

        Args:
            error: 原始异常对象

        Returns:
            ErrorCategory: 错误分类
        """
        error_type = type(error)
        for pattern_type, category in ERROR_TYPE_PATTERNS.items():
            if error_type is pattern_type or (
                isinstance(error, pattern_type) and issubclass(error_type, pattern_type)
            ):
                return category
        return ErrorCategory.UNKNOWN

    @staticmethod
    def _classify_by_message(error_message: str) -> ErrorCategory:
        """通过错误消息关键词分类

        Args:
            error_message: 错误消息（小写）

        Returns:
            ErrorCategory: 错误分类
        """
        for category, keywords in ERROR_MESSAGE_PATTERNS.items():
            for keyword in keywords:
                if keyword in error_message:
                    return category
        return ErrorCategory.UNKNOWN
