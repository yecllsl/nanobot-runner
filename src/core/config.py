# 配置管理模块
# 管理项目配置和本地数据目录

import json
import os
import shutil
from pathlib import Path

from src.core.config_schema import AppConfig


class ConfigManager:
    """配置管理器，管理项目配置和本地数据目录"""

    def __init__(self):
        """初始化配置管理器"""
        # 支持通过环境变量指定配置目录（用于CI环境）
        if os.environ.get("NANOBOT_CONFIG_DIR"):
            self.base_dir = Path(os.environ.get("NANOBOT_CONFIG_DIR"))
        else:
            self.base_dir = Path.home() / ".nanobot-runner"

        self.config_file = self.base_dir / "config.json"

        # 先初始化默认路径
        self.data_dir = self.base_dir / "data"
        self.index_file = self.data_dir / "index.json"
        self.cron_dir = self.base_dir / "cron"
        self.cron_store = self.cron_dir / "jobs.json"

        # 确保目录和配置文件存在
        self._ensure_dirs()
        self._ensure_config()

        # 尝试从配置文件读取 data_dir，如果存在则更新
        try:
            config = self.load_config()
            if "data_dir" in config:
                self.data_dir = Path(config["data_dir"])
                self.index_file = self.data_dir / "index.json"
        except Exception as e:
            # 如果读取配置失败，继续使用默认路径，记录警告日志
            import loguru

            loguru.logger.debug(f"读取配置文件失败，使用默认路径: {e}")

    def _ensure_dirs(self):
        """确保必要目录存在，并迁移旧的定时任务配置"""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cron_dir.mkdir(parents=True, exist_ok=True)

        # 迁移旧的定时任务配置
        self._migrate_old_cron_config()

    def _migrate_old_cron_config(self):
        """迁移旧的定时任务配置到新位置"""
        import loguru

        old_cron_store = Path.home() / ".nanobot" / "cron" / "jobs.json"
        new_cron_store = self.cron_store

        if old_cron_store.exists() and not new_cron_store.exists():
            try:
                shutil.copy2(old_cron_store, new_cron_store)
                loguru.logger.info(f"已迁移定时任务配置：{old_cron_store} -> {new_cron_store}")
            except Exception as e:
                loguru.logger.warning(f"迁移定时任务配置失败：{e}")

    def _ensure_config(self):
        """确保配置文件存在"""
        if not self.config_file.exists():
            default_config = {
                "version": "0.1.0",
                "data_dir": str(self.data_dir),
                "auto_push_feishu": False,
                # 飞书应用机器人配置（推荐）
                "feishu_app_id": "",
                "feishu_app_secret": "",  # nosec B105
                "feishu_receive_id": "",
                "feishu_receive_id_type": "user_id",
                # 兼容旧配置（已废弃）
                "feishu_webhook": "",  # nosec B105
            }
            self.save_config(default_config)

    def save_config(self, config: dict):
        """保存配置

        Args:
            config: 配置字典

        Raises:
            ValueError: 配置验证失败时抛出
        """
        # 保存前验证配置
        is_valid, errors = AppConfig.validate(config)
        if not is_valid:
            error_msg = "配置验证失败，无法保存:\n" + "\n".join(f"  - {e}" for e in errors)
            raise ValueError(error_msg)

        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    def load_config(self) -> dict:
        """加载配置

        Returns:
            dict: 配置字典

        Raises:
            ValueError: 配置验证失败时抛出
        """
        with open(self.config_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        # 加载后验证配置
        is_valid, errors = AppConfig.validate(config)
        if not is_valid:
            error_msg = "配置文件验证失败:\n" + "\n".join(f"  - {e}" for e in errors)
            raise ValueError(error_msg)

        return config

    def get(self, key: str, default=None):
        """获取配置项

        Args:
            key: 配置项键名
            default: 默认值

        Returns:
            配置项值

        Raises:
            ValueError: 配置验证失败时抛出
        """
        config = self.load_config()
        return config.get(key, default)

    def set(self, key: str, value):
        """设置配置项

        Args:
            key: 配置项键名
            value: 配置项值

        Raises:
            ValueError: 配置验证失败时抛出
        """
        config = self.load_config()
        config[key] = value
        self.save_config(config)

    def get_typed_config(self) -> AppConfig:
        """获取类型化的配置对象

        Returns:
            AppConfig: 类型化的配置实例

        Raises:
            ValueError: 配置验证失败时抛出
        """
        config = self.load_config()
        return AppConfig.from_dict(config)


config = ConfigManager()
