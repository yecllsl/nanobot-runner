# 技能数据模型
# 定义技能相关的数据结构

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class SkillStatus(Enum):
    """技能状态枚举"""

    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"


@dataclass
class SkillDependency:
    """技能依赖"""

    name: str
    version: str | None = None
    optional: bool = False


@dataclass
class SkillInfo:
    """技能信息"""

    name: str
    description: str
    version: str = "1.0.0"
    author: str = "unknown"
    status: SkillStatus = SkillStatus.ENABLED
    path: Path | None = None
    dependencies: list[SkillDependency] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    enabled_tools: list[str] = field(default_factory=list)

    @property
    def is_enabled(self) -> bool:
        """检查技能是否启用"""
        return self.status == SkillStatus.ENABLED

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "status": self.status.value,
            "path": str(self.path) if self.path else None,
            "dependencies": [
                {
                    "name": dep.name,
                    "version": dep.version,
                    "optional": dep.optional,
                }
                for dep in self.dependencies
            ],
            "tags": self.tags,
            "enabled_tools": self.enabled_tools,
        }
