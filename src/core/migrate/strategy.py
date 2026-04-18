from abc import ABC, abstractmethod
from pathlib import Path

from src.core.migrate.models import MigrationResult


class MigrationStrategy(ABC):
    """迁移策略抽象基类

    定义迁移策略的接口规范，所有版本迁移策略必须实现此接口。
    """

    @abstractmethod
    def get_source_path(self) -> Path:
        """获取源路径

        Returns:
            Path: 旧版本配置/数据的源路径
        """

    @abstractmethod
    def get_target_path(self) -> Path:
        """获取目标路径

        Returns:
            Path: 新版本配置/数据的目标路径
        """

    @abstractmethod
    def migrate_config(self) -> MigrationResult:
        """迁移配置文件

        Returns:
            MigrationResult: 迁移结果
        """

    @abstractmethod
    def migrate_data(self) -> MigrationResult:
        """迁移数据目录

        Returns:
            MigrationResult: 迁移结果
        """

    @abstractmethod
    def update_paths(self) -> MigrationResult:
        """更新路径引用

        Returns:
            MigrationResult: 更新结果
        """


class V08xMigrationStrategy(MigrationStrategy):
    """v0.8.x 版本迁移策略

    从 v0.8.x 版本迁移到 v0.9.4，主要变更：
    - 配置目录从 ~/.nanobot/ 迁移到 ~/.nanobot-runner/
    - 配置文件格式更新
    """

    def get_source_path(self) -> Path:
        return Path.home() / ".nanobot"

    def get_target_path(self) -> Path:
        return Path.home() / ".nanobot-runner"

    def migrate_config(self) -> MigrationResult:
        import json

        source_config = self.get_source_path() / "config.json"
        target_config = self.get_target_path() / "config.json"

        if not source_config.exists():
            return MigrationResult(
                success=True,
                warnings=["源配置文件不存在，跳过配置迁移"],
            )

        try:
            with open(source_config, encoding="utf-8") as f:
                old_config = json.load(f)

            new_config = {
                "version": "0.9.4",
                "data_dir": str(self.get_target_path() / "data"),
                "auto_push_feishu": old_config.get("auto_push_feishu", False),
                "feishu_app_id": old_config.get("feishu_app_id", ""),
                "feishu_app_secret": old_config.get("feishu_app_secret", ""),
                "feishu_receive_id": old_config.get("feishu_receive_id", ""),
                "feishu_receive_id_type": old_config.get(
                    "feishu_receive_id_type", "user_id"
                ),
            }

            self.get_target_path().mkdir(parents=True, exist_ok=True)
            with open(target_config, "w", encoding="utf-8") as f:
                json.dump(new_config, f, indent=2, ensure_ascii=False)

            return MigrationResult(success=True, migrated_files=1)

        except (OSError, json.JSONDecodeError) as e:
            return MigrationResult(success=False, errors=[f"配置迁移失败: {e}"])

    def migrate_data(self) -> MigrationResult:
        import shutil

        source_data = self.get_source_path() / "data"
        target_data = self.get_target_path() / "data"

        if not source_data.exists():
            return MigrationResult(
                success=True,
                warnings=["源数据目录不存在，跳过数据迁移"],
            )

        try:
            migrated = 0
            if target_data.exists():
                for item in source_data.iterdir():
                    target_item = target_data / item.name
                    if item.is_file():
                        shutil.copy2(item, target_item)
                        migrated += 1
                    elif item.is_dir():
                        shutil.copytree(item, target_item, dirs_exist_ok=True)
                        migrated += 1
            else:
                shutil.copytree(source_data, target_data)
                migrated = sum(1 for _ in target_data.rglob("*") if _.is_file())

            return MigrationResult(success=True, migrated_files=migrated)

        except OSError as e:
            return MigrationResult(success=False, errors=[f"数据迁移失败: {e}"])

    def update_paths(self) -> MigrationResult:
        import json

        target_config = self.get_target_path() / "config.json"

        if not target_config.exists():
            return MigrationResult(
                success=True,
                warnings=["目标配置文件不存在，跳过路径更新"],
            )

        try:
            with open(target_config, encoding="utf-8") as f:
                config = json.load(f)

            config["data_dir"] = str(self.get_target_path() / "data")

            with open(target_config, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            return MigrationResult(success=True, migrated_files=1)

        except (OSError, json.JSONDecodeError) as e:
            return MigrationResult(success=False, errors=[f"路径更新失败: {e}"])


class V09xMigrationStrategy(MigrationStrategy):
    """v0.9.x 版本迁移策略

    从 v0.9.x 版本迁移到 v0.9.4，主要变更：
    - 配置文件版本号更新
    - 新增配置项补充默认值
    """

    def __init__(self, source_version: str = "0.9.0") -> None:
        self.source_version = source_version

    def get_source_path(self) -> Path:
        return Path.home() / ".nanobot-runner"

    def get_target_path(self) -> Path:
        return Path.home() / ".nanobot-runner"

    def migrate_config(self) -> MigrationResult:
        import json

        config_file = self.get_target_path() / "config.json"

        if not config_file.exists():
            return MigrationResult(
                success=True,
                warnings=["配置文件不存在，跳过配置迁移"],
            )

        try:
            with open(config_file, encoding="utf-8") as f:
                config = json.load(f)

            config["version"] = "0.9.4"

            defaults = {
                "auto_push_feishu": False,
                "feishu_app_id": "",
                "feishu_app_secret": "",
                "feishu_receive_id": "",
                "feishu_receive_id_type": "user_id",
            }
            for key, default_value in defaults.items():
                config.setdefault(key, default_value)

            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            return MigrationResult(success=True, migrated_files=1)

        except (OSError, json.JSONDecodeError) as e:
            return MigrationResult(success=False, errors=[f"配置迁移失败: {e}"])

    def migrate_data(self) -> MigrationResult:
        return MigrationResult(
            success=True,
            warnings=["v0.9.x 数据目录无需迁移"],
        )

    def update_paths(self) -> MigrationResult:
        return MigrationResult(
            success=True,
            warnings=["v0.9.x 路径无需更新"],
        )


class MigrationStrategyFactory:
    """迁移策略工厂

    根据检测到的版本自动选择合适的迁移策略。
    """

    _STRATEGY_MAP: dict[str, type[MigrationStrategy]] = {
        "0.8": V08xMigrationStrategy,
        "0.9": V09xMigrationStrategy,
    }

    @classmethod
    def create_strategy(cls, version: str) -> MigrationStrategy:
        """根据版本号创建迁移策略

        Args:
            version: 版本号字符串（如 "0.8.3" 或 "0.9.1"）

        Returns:
            MigrationStrategy: 对应的迁移策略实例

        Raises:
            ValueError: 不支持的版本号
        """
        major_minor = ".".join(version.split(".")[:2])

        strategy_class = cls._STRATEGY_MAP.get(major_minor)
        if strategy_class is None:
            raise ValueError(
                f"不支持的版本号: {version}，"
                f"支持的版本: {list(cls._STRATEGY_MAP.keys())}"
            )

        if major_minor == "0.9":
            strategy: MigrationStrategy = V09xMigrationStrategy(source_version=version)
            return strategy

        return strategy_class()
