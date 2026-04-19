import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from src.core.env_manager import EnvManager
from src.core.exceptions import ConfigError
from src.core.logger import get_logger

logger = get_logger(__name__)

_TEMPLATE_FILES = [
    "AGENTS.md",
    "HEARTBEAT.md",
    "SOUL.md",
    "TOOLS.md",
    "USER.md",
]

_MEMORY_FILES = [
    "MEMORY.md",
    "history.jsonl",
]

_TRACKED_FILES = [
    "MEMORY.md",
    "history.jsonl",
    "AGENTS.md",
    "HEARTBEAT.md",
    "SOUL.md",
    "TOOLS.md",
    "USER.md",
    "config.json",
    ".env.local",
]


def _get_template_dir() -> Path:
    """获取模板目录路径

    Returns:
        Path: 模板目录路径
    """
    return Path(__file__).parent.parent.parent.parent / "templates"


def _build_gitignore(tracked_files: list[str]) -> str:
    """生成 .gitignore 文件内容

    采用白名单模式：先忽略所有文件，然后用 ! 取消忽略需要追踪的文件。

    Args:
        tracked_files: 需要追踪的文件列表

    Returns:
        str: .gitignore 文件内容
    """
    dirs: set[str] = set()
    for f in tracked_files:
        parent = str(Path(f).parent)
        if parent != ".":
            dirs.add(parent)

    lines = ["/*"]
    for d in sorted(dirs):
        lines.append(f"!{d}/")
    for f in tracked_files:
        lines.append(f"!{f}")
    lines.append("!.gitignore")
    return "\n".join(lines) + "\n"


class ConfigGenerator:
    """配置文件生成器

    根据用户输入生成 config.json、.env.local 等配置文件，
    并从 templates 目录复制模板文件到工作区。
    """

    def __init__(self, env_manager: EnvManager | None = None) -> None:
        """初始化配置文件生成器

        Args:
            env_manager: 环境变量管理器（可选）
        """
        self.env_manager = env_manager or EnvManager()
        self.template_dir = _get_template_dir()

    def generate_config_json(self, config: dict[str, Any]) -> str:
        """生成 config.json 文件内容

        Args:
            config: 配置字典

        Returns:
            str: JSON 格式的配置文件内容
        """
        return json.dumps(config, indent=2, ensure_ascii=False)

    def generate_env_local(self, env_vars: dict[str, str]) -> str:
        """生成 .env.local 文件内容

        Args:
            env_vars: 环境变量字典

        Returns:
            str: .env.local 文件内容
        """
        lines: list[str] = ["# Nanobot Runner 环境变量配置\n"]

        if env_vars.get("NANOBOT_LLM_API_KEY"):
            lines.append("# LLM 配置\n")
            lines.append(
                f"NANOBOT_LLM_PROVIDER={env_vars.get('NANOBOT_LLM_PROVIDER', 'openai')}\n"
            )
            lines.append(
                f"NANOBOT_LLM_MODEL={env_vars.get('NANOBOT_LLM_MODEL', 'gpt-4o-mini')}\n"
            )
            lines.append(f"NANOBOT_LLM_API_KEY={env_vars['NANOBOT_LLM_API_KEY']}\n")
            base_url = env_vars.get("NANOBOT_LLM_BASE_URL", "")
            if base_url:
                lines.append(f"NANOBOT_LLM_BASE_URL={base_url}\n")

        feishu_keys = [
            "NANOBOT_FEISHU_APP_ID",
            "NANOBOT_FEISHU_APP_SECRET",
            "NANOBOT_FEISHU_RECEIVE_ID",
        ]
        has_feishu = any(env_vars.get(k) for k in feishu_keys)
        if has_feishu:
            lines.append("\n# 飞书通知配置\n")
            for key in feishu_keys:
                if env_vars.get(key):
                    lines.append(f"{key}={env_vars[key]}\n")
            lines.append(
                f"NANOBOT_AUTO_PUSH_FEISHU={env_vars.get('NANOBOT_AUTO_PUSH_FEISHU', 'false')}\n"
            )

        return "".join(lines)

    def _copy_template_files(self, workspace_dir: Path) -> list[Path]:
        """复制模板文件到工作区

        Args:
            workspace_dir: 工作区目录路径

        Returns:
            list[Path]: 复制的文件路径列表
        """
        copied: list[Path] = []

        for filename in _TEMPLATE_FILES:
            src = self.template_dir / filename
            dst = workspace_dir / filename
            if src.exists():
                shutil.copy2(src, dst)
                copied.append(dst)
                logger.debug(f"已复制模板文件: {filename}")

        return copied

    def _copy_skills_directory(self, workspace_dir: Path) -> list[Path]:
        """复制 skills 目录到工作区

        Args:
            workspace_dir: 工作区目录路径

        Returns:
            list[Path]: 复制的文件路径列表
        """
        src_skills = self.template_dir / "skills"
        dst_skills = workspace_dir / "skills"

        if not src_skills.exists():
            logger.debug("skills 目录不存在，跳过复制")
            return []

        copied: list[Path] = []

        for item in src_skills.rglob("*"):
            if item.is_file():
                rel_path = item.relative_to(src_skills)
                dst = dst_skills / rel_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dst)
                copied.append(dst)
                logger.debug(f"已复制 skills 文件: {rel_path}")

        return copied

    def _create_memory_files(self, workspace_dir: Path) -> list[Path]:
        """创建 memory 目录和文件

        Args:
            workspace_dir: 工作区目录路径

        Returns:
            list[Path]: 创建的文件路径列表
        """
        memory_dir = workspace_dir / "memory"
        memory_dir.mkdir(parents=True, exist_ok=True)

        created: list[Path] = []

        for filename in _MEMORY_FILES:
            src = self.template_dir / "memory" / filename
            dst = memory_dir / filename

            if src.exists():
                content = src.read_text(encoding="utf-8")
                if filename == "history.jsonl":
                    content = content.replace(
                        "INIT_TIMESTAMP", datetime.now().isoformat()
                    )
                dst.write_text(content, encoding="utf-8")
                created.append(dst)
                logger.debug(f"已创建 memory 文件: {filename}")

        return created

    def _init_git_repo(self, workspace_dir: Path) -> bool:
        """初始化 Git 仓库

        使用 dulwich 库初始化 Git 仓库，用于版本控制。
        创建 .gitignore 文件并提交初始内容。

        Args:
            workspace_dir: 工作区目录路径

        Returns:
            bool: 是否成功初始化
        """
        try:
            from dulwich import porcelain

            git_dir = workspace_dir / ".git"
            if git_dir.exists():
                logger.debug("Git 仓库已存在，跳过初始化")
                return False

            porcelain.init(str(workspace_dir))

            gitignore_path = workspace_dir / ".gitignore"
            gitignore_content = _build_gitignore(_TRACKED_FILES)
            gitignore_path.write_text(gitignore_content, encoding="utf-8")

            tracked_paths = [".gitignore"]
            for f in _TRACKED_FILES:
                file_path = workspace_dir / f
                if file_path.exists():
                    tracked_paths.append(f)

            porcelain.add(str(workspace_dir), paths=tracked_paths)
            porcelain.commit(
                str(workspace_dir),
                message=b"init: nanobot-runner workspace",
                author=b"nanobot-runner <nanobot-runner@local>",
                committer=b"nanobot-runner <nanobot-runner@local>",
            )

            logger.info(f"Git 仓库已初始化: {workspace_dir}")
            return True

        except ImportError:
            logger.warning("dulwich 未安装，跳过 Git 初始化")
            return False
        except Exception as e:
            logger.warning(f"Git 初始化失败: {e}")
            return False

    def write_config_files(
        self,
        workspace_dir: Path,
        config: dict[str, Any],
        env_vars: dict[str, str] | None = None,
        init_git: bool = True,
    ) -> dict[str, Path]:
        """写入所有配置文件

        Args:
            workspace_dir: workspace 目录路径
            config: 配置字典
            env_vars: 环境变量字典（可选）
            init_git: 是否初始化 Git 仓库

        Returns:
            dict[str, Path]: 写入的文件路径字典

        Raises:
            ConfigError: 写入失败时抛出
        """
        written: dict[str, Path] = {}

        try:
            workspace_dir.mkdir(parents=True, exist_ok=True)

            config_path = workspace_dir / "config.json"
            config_path.write_text(self.generate_config_json(config), encoding="utf-8")
            written["config"] = config_path

            if env_vars:
                env_path = workspace_dir / ".env.local"
                env_path.write_text(self.generate_env_local(env_vars), encoding="utf-8")
                written["env"] = env_path

            for path in self._copy_template_files(workspace_dir):
                written[path.name] = path

            for path in self._create_memory_files(workspace_dir):
                written[f"memory/{path.name}"] = path

            for path in self._copy_skills_directory(workspace_dir):
                rel_path = path.relative_to(workspace_dir)
                written[str(rel_path)] = path

            if init_git:
                self._init_git_repo(workspace_dir)

            logger.info(f"配置文件已写入: {list(written.keys())}")
            return written

        except OSError as e:
            raise ConfigError(
                f"写入配置文件失败: {e}",
                recovery_suggestion="请检查目录权限和磁盘空间",
            ) from e
