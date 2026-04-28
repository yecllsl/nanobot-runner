# 记忆管理数据模型
# 定义记忆版本等核心数据结构

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class MemoryVersion:
    """记忆版本（不可变数据类）

    记录记忆文件的版本快照，支持版本回溯。

    Attributes:
        version: 版本号
        timestamp: 版本创建时间
        memory_hash: memory.md文件的SHA256哈希
        user_hash: user.md文件的SHA256哈希
        personality_hash: 人格数据的SHA256哈希
        backup_path: 备份文件路径
    """

    version: str
    timestamp: datetime
    memory_hash: str
    user_hash: str
    personality_hash: str = ""
    backup_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "version": self.version,
            "timestamp": self.timestamp.isoformat(),
            "memory_hash": self.memory_hash,
            "user_hash": self.user_hash,
            "personality_hash": self.personality_hash,
            "backup_path": self.backup_path,
        }
