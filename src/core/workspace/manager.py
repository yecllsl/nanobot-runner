import os
import shutil
from pathlib import Path

from src.core.base.logger import get_logger
from src.core.config.manager import ConfigManager
from src.core.workspace.models import WorkspaceInfo, WorkspaceValidationResult

logger = get_logger(__name__)


class WorkspaceManager:
    """Workspace 位置管理器

    管理 workspace 目录的创建和路径解析。
    支持环境变量、配置文件和默认值三种配置方式。
    """

    _DEFAULT_SUBDIRS = ["data", "memory", "sessions", "cron", "skills"]

    def __init__(self, config: ConfigManager) -> None:
        """初始化 Workspace 管理器

        Args:
            config: 配置管理器
        """
        self.config = config

    def resolve_workspace_path(self) -> Path:
        """解析 workspace 路径

        优先级：环境变量 > 配置文件 > 默认值

        Returns:
            Path: workspace 目录路径
        """
        if env_path := os.getenv("NANOBOT_WORKSPACE_DIR"):
            return Path(env_path).expanduser().resolve()

        config_path = self.config.get("workspace_dir")
        if config_path:
            return Path(config_path).expanduser().resolve()

        return Path.home() / ".nanobot-runner"

    def create_workspace(self, path: Path | None = None) -> Path:
        """创建 workspace 目录

        Args:
            path: 指定路径，如果为 None 则使用解析的路径

        Returns:
            Path: 创建的 workspace 路径
        """
        workspace_path = path or self.resolve_workspace_path()
        workspace_path.mkdir(parents=True, exist_ok=True)

        for subdir in self._DEFAULT_SUBDIRS:
            (workspace_path / subdir).mkdir(exist_ok=True)

        logger.info(f"Workspace 已创建: {workspace_path}")
        return workspace_path

    def validate_path(self, path: Path) -> WorkspaceValidationResult:
        """验证路径是否有效

        Args:
            path: 待验证的路径

        Returns:
            WorkspaceValidationResult: 验证结果
        """
        errors: list[str] = []
        warnings: list[str] = []
        suggestions: list[str] = []

        if path.exists() and not path.is_dir():
            errors.append(f"路径已存在且不是目录: {path}")
            suggestions.append("请指定一个目录路径或删除现有文件")

        parent = path.parent
        if parent.exists() and not os.access(parent, os.W_OK):
            errors.append(f"无权限在 {parent} 下创建目录")
            suggestions.append("请检查目录权限或选择其他路径")

        if parent.exists():
            try:
                disk_usage = shutil.disk_usage(parent)
                free_gb = disk_usage.free / (1024 * 1024 * 1024)
                if free_gb < 1.0:
                    warnings.append(f"磁盘空间不足: {free_gb:.1f}GB 可用")
                    suggestions.append("建议清理磁盘空间或选择其他磁盘")
            except OSError:
                pass

        return WorkspaceValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
        )

    def get_workspace_info(self) -> WorkspaceInfo:
        """获取 workspace 信息

        Returns:
            WorkspaceInfo: workspace 信息
        """
        workspace_path = self.resolve_workspace_path()

        source = "default"
        if os.getenv("NANOBOT_WORKSPACE_DIR"):
            source = "env"
        elif self.config.get("workspace_dir"):
            source = "config"

        subdirs: list[str] = []
        if workspace_path.exists():
            subdirs = [d.name for d in workspace_path.iterdir() if d.is_dir()]

        disk_usage_mb = 0.0
        if workspace_path.exists():
            try:
                total_size = sum(
                    f.stat().st_size for f in workspace_path.rglob("*") if f.is_file()
                )
                disk_usage_mb = total_size / (1024 * 1024)
            except OSError:
                pass

        return WorkspaceInfo(
            path=workspace_path,
            source=source,
            exists=workspace_path.exists(),
            subdirectories=subdirs,
            disk_usage_mb=round(disk_usage_mb, 2),
        )
