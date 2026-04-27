# 技能管理器模块
# 负责技能发现、启用、禁用、导入等管理功能
# 注意：技能加载由nanobot SDK的SkillsLoader自动处理

import logging
import re
import shutil
from pathlib import Path

from src.core.skills.models import (
    SkillDependency,
    SkillInfo,
    SkillStatus,
)

logger = logging.getLogger(__name__)


class SkillManager:
    """技能管理器

    负责技能发现、启用、禁用、导入等管理功能。
    注意：技能加载由nanobot SDK的SkillsLoader自动处理。

    SkillManager的核心职责是配置管理而非技能加载：
    - 列出/发现可用技能
    - 启用/禁用技能（更新config.json）
    - 导入自定义技能
    - 获取技能内容

    Attributes:
        workspace: 工作空间目录
        skills_dir: 技能目录
        config_path: config.json文件路径
    """

    SKILL_FILE = "SKILL.md"

    def __init__(self, workspace: Path, config_path: Path) -> None:
        """初始化技能管理器

        Args:
            workspace: 工作空间目录
            config_path: config.json路径
        """
        self.workspace = workspace
        self.skills_dir = workspace / "skills"
        self.config_path = config_path

    def list_skills(self) -> list[SkillInfo]:
        """列出所有可用技能

        扫描skills目录，解析SKILL.md文件

        Returns:
            list[SkillInfo]: 技能信息列表
        """
        skills: list[SkillInfo] = []

        if not self.skills_dir.exists():
            logger.debug(f"技能目录不存在: {self.skills_dir}")
            return skills

        disabled_skills = self._load_disabled_skills()

        for skill_dir in self.skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue

            skill_file = skill_dir / self.SKILL_FILE
            if not skill_file.exists():
                logger.debug(f"技能文件不存在: {skill_file}")
                continue

            skill_info = self._parse_skill_file(skill_dir, skill_file)
            if skill_info is not None:
                if skill_info.name in disabled_skills:
                    skill_info.status = SkillStatus.DISABLED
                skills.append(skill_info)

        return skills

    def get_skill(self, skill_name: str) -> SkillInfo | None:
        """获取指定技能信息

        Args:
            skill_name: 技能名称

        Returns:
            SkillInfo | None: 技能信息，不存在返回None
        """
        skills = self.list_skills()
        for skill in skills:
            if skill.name == skill_name:
                return skill
        return None

    def enable_skill(self, skill_name: str) -> bool:
        """启用技能

        从config.json的skills.disabled列表中移除

        Args:
            skill_name: 技能名称

        Returns:
            bool: 是否启用成功
        """
        import json

        skill = self.get_skill(skill_name)
        if skill is None:
            logger.warning(f"技能不存在: {skill_name}")
            return False

        if skill.status == SkillStatus.ENABLED:
            logger.debug(f"技能已启用: {skill_name}")
            return True

        try:
            with open(self.config_path, encoding="utf-8") as f:
                config = json.load(f)

            disabled_skills = config.get("skills", {}).get("disabled", [])
            if skill_name in disabled_skills:
                disabled_skills.remove(skill_name)
                config.setdefault("skills", {})["disabled"] = disabled_skills

                with open(self.config_path, "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)

            logger.info(f"技能已启用: {skill_name}")
            return True

        except Exception as e:
            logger.error(f"启用技能失败: {skill_name}, 错误: {e}")
            return False

    def disable_skill(self, skill_name: str) -> bool:
        """禁用技能

        添加到config.json的skills.disabled列表

        Args:
            skill_name: 技能名称

        Returns:
            bool: 是否禁用成功
        """
        import json

        skill = self.get_skill(skill_name)
        if skill is None:
            logger.warning(f"技能不存在: {skill_name}")
            return False

        if skill.status == SkillStatus.DISABLED:
            logger.debug(f"技能已禁用: {skill_name}")
            return True

        try:
            with open(self.config_path, encoding="utf-8") as f:
                config = json.load(f)

            disabled_skills = config.get("skills", {}).get("disabled", [])
            if skill_name not in disabled_skills:
                disabled_skills.append(skill_name)
                config.setdefault("skills", {})["disabled"] = disabled_skills

                with open(self.config_path, "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)

            logger.info(f"技能已禁用: {skill_name}")
            return True

        except Exception as e:
            logger.error(f"禁用技能失败: {skill_name}, 错误: {e}")
            return False

    def import_skill(self, skill_path: Path) -> bool:
        """导入自定义技能

        复制到skills目录

        Args:
            skill_path: 技能目录路径

        Returns:
            bool: 是否导入成功
        """
        if not skill_path.exists():
            logger.warning(f"技能目录不存在: {skill_path}")
            return False

        skill_file = skill_path / self.SKILL_FILE
        if not skill_file.exists():
            logger.warning(f"技能文件不存在: {skill_file}")
            return False

        skill_info = self._parse_skill_file(skill_path, skill_file)
        if skill_info is None:
            logger.warning(f"无法解析技能文件: {skill_file}")
            return False

        target_dir = self.skills_dir / skill_info.name
        if target_dir.exists():
            logger.warning(f"技能已存在: {skill_info.name}")
            return False

        try:
            self.skills_dir.mkdir(parents=True, exist_ok=True)
            shutil.copytree(skill_path, target_dir)
            logger.info(f"技能已导入: {skill_info.name}")
            return True

        except Exception as e:
            logger.error(f"导入技能失败: {skill_path}, 错误: {e}")
            return False

    def get_skill_content(self, skill_name: str) -> str | None:
        """获取技能内容

        Args:
            skill_name: 技能名称

        Returns:
            str | None: 技能内容，不存在返回None
        """
        skill = self.get_skill(skill_name)
        if skill is None or skill.path is None:
            return None

        skill_file = skill.path / self.SKILL_FILE
        if not skill_file.exists():
            return None

        try:
            return skill_file.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"读取技能内容失败: {skill_file}, 错误: {e}")
            return None

    def _load_disabled_skills(self) -> list[str]:
        """从config.json加载禁用的技能列表

        Returns:
            list[str]: 禁用的技能名称列表
        """
        import json

        try:
            with open(self.config_path, encoding="utf-8") as f:
                config = json.load(f)
            return config.get("skills", {}).get("disabled", [])
        except Exception as e:
            logger.debug(f"加载禁用技能列表失败: {e}")
            return []

    def _parse_skill_file(self, skill_dir: Path, skill_file: Path) -> SkillInfo | None:
        """解析SKILL.md文件

        Args:
            skill_dir: 技能目录
            skill_file: SKILL.md文件路径

        Returns:
            SkillInfo | None: 技能信息，解析失败返回None
        """
        try:
            content = skill_file.read_text(encoding="utf-8")
            return self._parse_skill_content(skill_dir, content)
        except Exception as e:
            logger.error(f"解析技能文件失败: {skill_file}, 错误: {e}")
            return None

    def _parse_skill_content(self, skill_dir: Path, content: str) -> SkillInfo:
        """解析技能内容

        支持YAML front matter格式

        Args:
            skill_dir: 技能目录
            content: 技能文件内容

        Returns:
            SkillInfo: 技能信息
        """
        name = skill_dir.name
        description = ""
        version = "1.0.0"
        author = "unknown"
        dependencies: list[SkillDependency] = []
        tags: list[str] = []
        enabled_tools: list[str] = []

        front_matter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
        if front_matter_match:
            import yaml

            try:
                front_matter = yaml.safe_load(front_matter_match.group(1))
                if isinstance(front_matter, dict):
                    name = front_matter.get("name", name)
                    description = front_matter.get("description", "")
                    version = front_matter.get("version", version)
                    author = front_matter.get("author", author)
                    tags = front_matter.get("tags", [])

                    deps_data = front_matter.get("dependencies", [])
                    if isinstance(deps_data, list):
                        for dep in deps_data:
                            if isinstance(dep, str):
                                dependencies.append(SkillDependency(name=dep))
                            elif isinstance(dep, dict):
                                dependencies.append(
                                    SkillDependency(
                                        name=dep.get("name", ""),
                                        version=dep.get("version"),
                                        optional=dep.get("optional", False),
                                    )
                                )

                    enabled_tools = front_matter.get("enabled_tools", [])
            except Exception as e:
                logger.debug(f"解析front matter失败: {e}")
        else:
            lines = content.strip().split("\n")
            for line in lines:
                line = line.strip()
                if line.startswith("# "):
                    description = line[2:].strip()
                    break

        return SkillInfo(
            name=name,
            description=description,
            version=version,
            author=author,
            status=SkillStatus.ENABLED,
            path=skill_dir,
            dependencies=dependencies,
            tags=tags,
            enabled_tools=enabled_tools,
        )
