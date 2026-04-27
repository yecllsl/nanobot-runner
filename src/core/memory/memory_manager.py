# 记忆管理器核心实现
# 提供记忆文件读写、备份恢复、版本管理、跨会话记忆连贯
# 记忆文件由nanobot SDK自动管理，MemoryManager提供辅助管理能力

import hashlib
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from src.core.memory.models import MemoryVersion
from src.core.personality.models import Personality

logger = logging.getLogger(__name__)


class MemoryManager:
    """记忆管理器

    提供记忆文件的读取、写入、备份恢复和版本管理能力。
    注意：Agent运行时的记忆读写由nanobot SDK自动处理，
    MemoryManager提供的是辅助管理能力（备份、恢复、版本追踪等）。

    记忆文件位置：
    - workspace/MEMORY.md: 项目记忆
    - workspace/USER.md: 用户画像
    - workspace/personality.json: AI人格数据
    - workspace/.memory_versions/: 记忆版本备份目录

    核心接口：
    - read_memory: 读取项目记忆
    - write_memory: 写入项目记忆
    - read_user_profile: 读取用户画像
    - write_user_profile: 写入用户画像
    - save_preference_to_memory: 保存偏好到记忆
    - load_preference_from_memory: 从记忆加载偏好
    - update_memory_context: 更新记忆上下文
    - create_backup: 创建记忆备份
    - restore_backup: 恢复记忆备份

    Attributes:
        workspace: 工作空间目录
        memory_file: 项目记忆文件路径
        user_file: 用户画像文件路径
        personality_file: AI人格数据文件路径
        versions_dir: 版本备份目录
    """

    MEMORY_FILENAME = "MEMORY.md"
    USER_FILENAME = "USER.md"
    PERSONALITY_FILENAME = "personality.json"
    VERSIONS_DIRNAME = ".memory_versions"

    def __init__(self, workspace: Path) -> None:
        """初始化记忆管理器

        Args:
            workspace: 工作空间目录
        """
        self.workspace = workspace
        self.memory_file = workspace / self.MEMORY_FILENAME
        self.user_file = workspace / self.USER_FILENAME
        self.personality_file = workspace / self.PERSONALITY_FILENAME
        self.versions_dir = workspace / self.VERSIONS_DIRNAME

    def read_memory(self) -> str:
        """读取项目记忆文件

        Returns:
            str: memory.md文件内容，不存在返回空字符串
        """
        if not self.memory_file.exists():
            logger.debug(f"记忆文件不存在: {self.memory_file}")
            return ""

        try:
            content = self.memory_file.read_text(encoding="utf-8")
            logger.debug(f"读取记忆文件: {len(content)}字符")
            return content
        except Exception as e:
            logger.error(f"读取记忆文件失败: {e}")
            return ""

    def write_memory(self, content: str) -> None:
        """写入项目记忆文件

        Args:
            content: 记忆内容
        """
        try:
            self.workspace.mkdir(parents=True, exist_ok=True)
            self.memory_file.write_text(content, encoding="utf-8")
            logger.info(f"写入记忆文件: {len(content)}字符")
        except Exception as e:
            logger.error(f"写入记忆文件失败: {e}")

    def read_user_profile(self) -> str:
        """读取用户画像文件

        Returns:
            str: user.md文件内容，不存在返回空字符串
        """
        if not self.user_file.exists():
            logger.debug(f"用户画像文件不存在: {self.user_file}")
            return ""

        try:
            content = self.user_file.read_text(encoding="utf-8")
            logger.debug(f"读取用户画像: {len(content)}字符")
            return content
        except Exception as e:
            logger.error(f"读取用户画像失败: {e}")
            return ""

    def write_user_profile(self, content: str) -> None:
        """写入用户画像文件

        Args:
            content: 用户画像内容
        """
        try:
            self.workspace.mkdir(parents=True, exist_ok=True)
            self.user_file.write_text(content, encoding="utf-8")
            logger.info(f"写入用户画像: {len(content)}字符")
        except Exception as e:
            logger.error(f"写入用户画像失败: {e}")

    def read_personality(self) -> Personality:
        """读取AI人格数据

        Returns:
            Personality: AI人格实例
        """
        if not self.personality_file.exists():
            logger.debug(f"人格数据文件不存在: {self.personality_file}")
            return Personality.default()

        try:
            content = self.personality_file.read_text(encoding="utf-8")
            data = json.loads(content)
            return Personality.from_dict(data)
        except Exception as e:
            logger.error(f"读取人格数据失败: {e}")
            return Personality.default()

    def write_personality(self, personality: Personality) -> None:
        """写入AI人格数据

        Args:
            personality: AI人格实例
        """
        try:
            self.workspace.mkdir(parents=True, exist_ok=True)
            data = personality.to_dict()
            self.personality_file.write_text(
                json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            logger.info("写入AI人格数据")
        except Exception as e:
            logger.error(f"写入人格数据失败: {e}")

    def save_preference_to_memory(self, preferences: dict[str, Any]) -> bool:
        """保存偏好到记忆

        将用户偏好数据追加到MEMORY.md文件中。

        Args:
            preferences: 偏好数据字典

        Returns:
            bool: 是否保存成功
        """
        try:
            current_memory = self.read_memory()

            preference_section = "\n## 用户偏好\n\n"
            for key, value in preferences.items():
                preference_section += f"- {key}: {value}\n"
            preference_section += f"\n> 更新时间: {datetime.now().isoformat()}\n"

            if "## 用户偏好" in current_memory:
                start_idx = current_memory.index("## 用户偏好")
                next_section_idx = current_memory.find("\n## ", start_idx + 1)
                if next_section_idx == -1:
                    updated_memory = current_memory[:start_idx] + preference_section
                else:
                    updated_memory = (
                        current_memory[:start_idx]
                        + preference_section
                        + current_memory[next_section_idx:]
                    )
            else:
                updated_memory = current_memory + "\n" + preference_section

            self.write_memory(updated_memory)
            logger.info("偏好已保存到记忆")
            return True

        except Exception as e:
            logger.error(f"保存偏好到记忆失败: {e}")
            return False

    def load_preference_from_memory(self) -> dict[str, Any]:
        """从记忆加载偏好

        解析MEMORY.md中的用户偏好部分。

        Returns:
            dict: 偏好数据字典
        """
        memory_content = self.read_memory()

        if not memory_content or "## 用户偏好" not in memory_content:
            return {}

        preferences: dict[str, Any] = {}
        in_preference_section = False

        for line in memory_content.split("\n"):
            if line.strip() == "## 用户偏好":
                in_preference_section = True
                continue
            if in_preference_section and line.startswith("## "):
                break
            if in_preference_section and line.startswith("- "):
                parts = line[2:].split(": ", 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    preferences[key] = value

        return preferences

    def update_memory_context(self, context_key: str, context_value: str) -> bool:
        """更新记忆上下文

        在MEMORY.md中添加或更新指定上下文条目。

        Args:
            context_key: 上下文键名
            context_value: 上下文值

        Returns:
            bool: 是否更新成功
        """
        try:
            current_memory = self.read_memory()

            context_line = f"- {context_key}: {context_value}"

            section_header = "## 上下文信息"
            if section_header not in current_memory:
                current_memory += f"\n{section_header}\n\n{context_line}\n"
            else:
                start_idx = current_memory.index(section_header)
                lines_after = current_memory[start_idx:].split("\n")
                updated = False

                new_lines = [lines_after[0]]
                for line in lines_after[1:]:
                    if line.startswith(f"- {context_key}:"):
                        new_lines.append(context_line)
                        updated = True
                    elif line.startswith("## ") and not updated:
                        new_lines.append(context_line)
                        new_lines.append(line)
                        updated = True
                    else:
                        new_lines.append(line)

                if not updated:
                    new_lines.append(context_line)

                current_memory = current_memory[:start_idx] + "\n".join(new_lines)

            self.write_memory(current_memory)
            logger.info(f"记忆上下文已更新: {context_key}")
            return True

        except Exception as e:
            logger.error(f"更新记忆上下文失败: {e}")
            return False

    def create_backup(self) -> str:
        """创建记忆备份

        备份当前所有记忆文件，生成版本快照。

        Returns:
            str: 备份目录路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        version = f"v_{timestamp}"
        backup_dir = self.versions_dir / version

        try:
            backup_dir.mkdir(parents=True, exist_ok=True)

            if self.memory_file.exists():
                shutil.copy2(self.memory_file, backup_dir / self.MEMORY_FILENAME)
            if self.user_file.exists():
                shutil.copy2(self.user_file, backup_dir / self.USER_FILENAME)
            if self.personality_file.exists():
                shutil.copy2(
                    self.personality_file, backup_dir / self.PERSONALITY_FILENAME
                )

            memory_hash = self._compute_file_hash(self.memory_file)
            user_hash = self._compute_file_hash(self.user_file)
            personality_hash = self._compute_file_hash(self.personality_file)

            version_info = MemoryVersion(
                version=version,
                timestamp=datetime.now(),
                memory_hash=memory_hash,
                user_hash=user_hash,
                personality_hash=personality_hash,
                backup_path=str(backup_dir),
            )

            version_file = backup_dir / "version.json"
            version_file.write_text(
                json.dumps(version_info.to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

            logger.info(f"记忆备份已创建: {version}")
            return str(backup_dir)

        except Exception as e:
            logger.error(f"创建记忆备份失败: {e}")
            return ""

    def restore_backup(self, backup_path: Path) -> bool:
        """恢复记忆备份

        Args:
            backup_path: 备份目录路径

        Returns:
            bool: 是否恢复成功
        """
        if not backup_path.exists():
            logger.warning(f"备份目录不存在: {backup_path}")
            return False

        try:
            memory_backup = backup_path / self.MEMORY_FILENAME
            if memory_backup.exists():
                shutil.copy2(memory_backup, self.memory_file)

            user_backup = backup_path / self.USER_FILENAME
            if user_backup.exists():
                shutil.copy2(user_backup, self.user_file)

            personality_backup = backup_path / self.PERSONALITY_FILENAME
            if personality_backup.exists():
                shutil.copy2(personality_backup, self.personality_file)

            logger.info(f"记忆备份已恢复: {backup_path}")
            return True

        except Exception as e:
            logger.error(f"恢复记忆备份失败: {e}")
            return False

    def list_versions(self) -> list[MemoryVersion]:
        """列出所有记忆版本

        Returns:
            list[MemoryVersion]: 版本列表
        """
        versions: list[MemoryVersion] = []

        if not self.versions_dir.exists():
            return versions

        for version_dir in sorted(self.versions_dir.iterdir()):
            version_file = version_dir / "version.json"
            if not version_file.exists():
                continue

            try:
                data = json.loads(version_file.read_text(encoding="utf-8"))
                versions.append(
                    MemoryVersion(
                        version=data["version"],
                        timestamp=datetime.fromisoformat(data["timestamp"]),
                        memory_hash=data["memory_hash"],
                        user_hash=data["user_hash"],
                        personality_hash=data.get("personality_hash", ""),
                        backup_path=data.get("backup_path", str(version_dir)),
                    )
                )
            except Exception as e:
                logger.warning(f"读取版本信息失败: {version_dir}, 错误: {e}")

        return versions

    def get_memory_stats(self) -> dict[str, Any]:
        """获取记忆统计信息

        Returns:
            dict: 记忆统计
        """
        return {
            "memory_exists": self.memory_file.exists(),
            "user_profile_exists": self.user_file.exists(),
            "personality_exists": self.personality_file.exists(),
            "memory_size": (
                self.memory_file.stat().st_size if self.memory_file.exists() else 0
            ),
            "user_profile_size": (
                self.user_file.stat().st_size if self.user_file.exists() else 0
            ),
            "version_count": len(self.list_versions()),
        }

    @staticmethod
    def _compute_file_hash(file_path: Path) -> str:
        """计算文件SHA256哈希

        Args:
            file_path: 文件路径

        Returns:
            str: SHA256哈希值，文件不存在返回空字符串
        """
        if not file_path.exists():
            return ""

        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()[:16]
