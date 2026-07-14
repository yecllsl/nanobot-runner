import platform
import sys
from pathlib import Path
from typing import Any

from src.core.base.exceptions import NanobotRunnerError
from src.core.base.logger import get_logger
from src.core.config.env_manager import EnvManager
from src.core.config.manager import ConfigManager
from src.core.init.generator import ConfigGenerator
from src.core.init.models import EnvironmentInfo, InitMode, InitResult, ValidationResult

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
        agent_mode: bool = True,
    ) -> InitResult:
        """运行初始化向导

        Args:
            mode: 初始化模式（FRESH/MIGRATE）
            force: 是否强制覆盖现有配置
            skip_optional: 是否跳过可选配置项
            workspace_dir: 指定 workspace 目录路径
            agent_mode: 是否配置LLM（True=Agent模式，False=数据模式）

        Returns:
            InitResult: 初始化结果
        """
        try:
            target_dir = workspace_dir or self.config.base_dir

            if mode == InitMode.MIGRATE:
                return self._run_migrate_mode(target_dir, force=force)

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

            # 规格 7.1: 检测旧版 config.json，提示迁移
            nano_path = target_dir / "nanobot_config.json"
            if (target_dir / "config.json").exists() and not nano_path.exists():
                try:
                    legacy_fields = self.config.check_legacy_fields()
                except (ValueError, OSError):
                    legacy_fields = []

                if legacy_fields:
                    import typer

                    from src.cli.common import console

                    console.print(
                        f"[yellow]检测到旧版配置格式（config.json 含 {legacy_fields[0]} 等字段）。[/yellow]"
                    )
                    console.print(
                        "建议先运行 [cyan]nanobotrun system migrate-config[/cyan] 迁移到 nanobot_config.json。"
                    )
                    if not typer.confirm("是否跳过迁移继续初始化？", default=False):
                        return InitResult(
                            success=False,
                            errors=["请先运行 nanobotrun system migrate-config 完成迁移"],
                        )

            wizard_result = self.guide_config(
                skip_optional=skip_optional,
                agent_mode=agent_mode,
            )
            runner_config = wizard_result.get("runner_config", {})
            nanobot_config = wizard_result.get("nanobot_config")

            runner_config["data_dir"] = str(target_dir / "data")

            validation = self.validate_config(runner_config)
            if not validation.is_valid:
                return InitResult(
                    success=False,
                    errors=validation.errors,
                    warnings=validation.warnings,
                )

            written = self.config_generator.write_config_files(
                target_dir,
                runner_config,
                nanobot_config=nanobot_config,
            )

            next_steps = [
                "导入数据: nanobotrun data import <FIT文件路径>",
                "查看统计: nanobotrun data stats",
            ]
            if agent_mode and nanobot_config:
                next_steps.append("Agent聊天: nanobotrun agent chat")

            return InitResult(
                success=True,
                config_path=written.get("config"),
                warnings=validation.warnings,
                next_steps=next_steps,
            )

        except NanobotRunnerError as e:
            logger.error(f"初始化失败: {e}")
            return InitResult(
                success=False,
                errors=[str(e)],
            )

    def _run_migrate_mode(
        self,
        target_dir: Path,
        force: bool = False,
    ) -> InitResult:
        """运行迁移模式

        从nanobot配置迁移到项目配置。

        Args:
            target_dir: 目标workspace目录
            force: 是否强制覆盖

        Returns:
            InitResult: 迁移结果
        """
        from src.core.init.migrate import ConfigMigrator

        if self._is_already_initialized(target_dir) and not force:
            return InitResult(
                success=False,
                errors=["工作区已初始化，使用 --force 强制覆盖"],
                next_steps=["运行: nanobotrun system init --mode migrate --force"],
            )

        self.create_directories(target_dir)

        migrator = ConfigMigrator(self.config)
        result = migrator.migrate_from_nanobot()

        if not result.success:
            # 如果迁移失败是因为nanobot配置文件不存在，且用户使用了--force
            # 则回退到FRESH模式重新初始化
            if any("nanobot配置文件不存在" in err for err in result.errors) and force:
                logger.warning("nanobot配置不存在，回退到全新初始化模式")
                return self.run(
                    mode=InitMode.FRESH,
                    force=force,
                    skip_optional=True,
                    workspace_dir=target_dir,
                    agent_mode=False,
                )
            return InitResult(
                success=False,
                errors=result.errors,
                warnings=result.warnings,
            )

        next_steps = [
            "导入数据: nanobotrun data import <FIT文件路径>",
            "查看统计: nanobotrun data stats",
            "Agent聊天: nanobotrun agent chat",
        ]

        return InitResult(
            success=True,
            config_path=result.config_path,
            env_path=result.env_path,
            warnings=result.warnings,
            next_steps=next_steps,
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

    def guide_config(
        self,
        skip_optional: bool = False,
        agent_mode: bool = True,
    ) -> dict[str, Any]:
        """引导用户填写配置

        Args:
            skip_optional: 是否跳过可选项
            agent_mode: 是否配置LLM（True=Agent模式，False=数据模式）

        Returns:
            dict[str, Any]: 包含 config 和 env_vars 的字典
        """
        from src.core.init.prompts import InitPrompts

        return InitPrompts.run_full_wizard(
            skip_optional=skip_optional,
            agent_mode=agent_mode,
        )

    def validate_config(self, config: dict[str, Any]) -> ValidationResult:
        """验证配置

        Args:
            config: Runner 专有配置字典

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

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

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
