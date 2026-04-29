# 工具返回结果模块
# 提供统一的工具返回格式

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
