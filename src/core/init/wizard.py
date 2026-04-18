import platform
import sys
from pathlib import Path
from typing import Any

from src.core.config import ConfigManager
from src.core.env_manager import EnvManager
from src.core.init.generator import ConfigGenerator
from src.core.init.models import EnvironmentInfo, InitMode, InitResult, ValidationResult
from src.core.logger import get_logger

logger = get_logger(__name__)


class InitWizard:
    """初始化向导

    引导用户完成首次配置，支持首次安装和升级迁移两种场景。
    """

    def __init__(
        self,
        config: ConfigManager,
        env_manager: EnvManager | None = None,
        config_generator: ConfigGenerator | None = None,
    ) -> None:
        """初始化向导

        Args:
            config: 配置管理器
            env_manager: 环境变量管理器（可选）
            config_generator: 配置文件生成器（可选）
        """
        self.config = config
        self.env_manager = env_manager or EnvManager()
        self.config_generator = config_generator or ConfigGenerator(self.env_manager)

    def run(
        self,
        mode: InitMode = InitMode.FRESH,
        force: bool = False,
        skip_optional: bool = False,
        workspace_dir: Path | None = None,
    ) -> InitResult:
        """运行初始化向导

        Args:
            mode: 初始化模式（FRESH/MIGRATE）
            force: 是否强制覆盖现有配置
            skip_optional: 是否跳过可选配置项
            workspace_dir: 指定 workspace 目录路径

        Returns:
            InitResult: 初始化结果
        """
        try:
            target_dir = workspace_dir or self.config.base_dir

            if self._is_already_initialized(target_dir) and not force:
                return InitResult(
                    success=False,
                    errors=["工作区已初始化，使用 --force 强制覆盖"],
                    next_steps=["运行: nanobotrun system init --force"],
                )

            env_info = self.detect_environment()

            missing = env_info.missing_dependencies
            if missing:
                logger.warning(f"缺少依赖: {missing}")

            self.create_directories(target_dir)

            wizard_result = self.guide_config(skip_optional=skip_optional)
            user_config = wizard_result.get("config", {})
            env_vars = wizard_result.get("env_vars", {})

            user_config["data_dir"] = str(target_dir / "data")

            validation = self.validate_config(user_config)
            if not validation.is_valid:
                return InitResult(
                    success=False,
                    errors=validation.errors,
                    warnings=validation.warnings,
                )

            written = self.generate_config_files(target_dir, user_config, env_vars)

            return InitResult(
                success=True,
                config_path=written.get("config"),
                env_path=written.get("env"),
                warnings=validation.warnings,
                next_steps=[
                    "导入数据: nanobotrun data import <FIT文件路径>",
                    "查看统计: nanobotrun data stats",
                    "Agent聊天: nanobotrun agent chat",
                ],
            )

        except Exception as e:
            logger.error(f"初始化失败: {e}")
            return InitResult(
                success=False,
                errors=[str(e)],
            )

    def detect_environment(self) -> EnvironmentInfo:
        """检测运行环境

        Returns:
            EnvironmentInfo: 环境信息
        """
        dependencies: dict[str, str] = {}
        missing: list[str] = []

        required_packages = ["polars", "pyarrow", "fitparse", "typer", "rich"]
        for pkg in required_packages:
            try:
                mod = __import__(pkg)
                version = getattr(mod, "__version__", "unknown")
                dependencies[pkg] = version
            except ImportError:
                missing.append(pkg)

        optional_packages = ["questionary"]
        for pkg in optional_packages:
            try:
                mod = __import__(pkg)
                version = getattr(mod, "__version__", "unknown")
                dependencies[pkg] = version
            except ImportError:
                missing.append(pkg)

        return EnvironmentInfo(
            python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            os_type=platform.system(),
            os_version=platform.release(),
            dependencies=dependencies,
            missing_dependencies=missing,
        )

    def create_directories(self, workspace_dir: Path | None = None) -> None:
        """创建必要的目录结构

        Args:
            workspace_dir: workspace 目录路径
        """
        target = workspace_dir or self.config.base_dir

        dirs = [
            target,
            target / "data",
            target / "memory",
            target / "sessions",
            target / "cron",
        ]

        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

        logger.info(f"目录结构已创建: {target}")

    def guide_config(self, skip_optional: bool = False) -> dict[str, Any]:
        """引导用户填写配置

        Args:
            skip_optional: 是否跳过可选项

        Returns:
            dict[str, Any]: 包含 config 和 env_vars 的字典
        """
        from src.core.init.prompts import InitPrompts

        return InitPrompts.run_full_wizard(skip_optional=skip_optional)

    def validate_config(self, config: dict[str, Any]) -> ValidationResult:
        """验证配置

        Args:
            config: 配置字典

        Returns:
            ValidationResult: 验证结果
        """
        errors: list[str] = []
        warnings: list[str] = []

        if not config.get("version"):
            errors.append("缺少版本号")

        if not config.get("data_dir"):
            errors.append("缺少数据目录配置")

        data_path = Path(config.get("data_dir", ""))
        if data_path.exists() and not data_path.is_dir():
            errors.append(f"数据路径已存在且不是目录: {data_path}")

        if not config.get("llm_provider"):
            warnings.append("未配置 LLM Provider，Agent 功能将不可用")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def generate_config_files(
        self,
        workspace_dir: Path,
        config: dict[str, Any],
        env_vars: dict[str, str] | None = None,
    ) -> dict[str, Path]:
        """生成配置文件

        Args:
            workspace_dir: workspace 目录路径
            config: 配置字典
            env_vars: 环境变量字典

        Returns:
            dict[str, Path]: 写入的文件路径字典
        """
        return self.config_generator.write_config_files(workspace_dir, config, env_vars)

    @staticmethod
    def _is_already_initialized(workspace_dir: Path) -> bool:
        """检查工作区是否已初始化

        Args:
            workspace_dir: workspace 目录路径

        Returns:
            bool: 是否已初始化
        """
        config_file = workspace_dir / "config.json"
        return config_file.exists()
