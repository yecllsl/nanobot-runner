# 配置管理模块
# 管理项目配置和本地数据目录

import json
import os
import shutil
import time
from pathlib import Path
from typing import Any

from src.core.config_schema import AppConfig


class ConfigManager:
    """配置管理器，管理项目配置和本地数据目录

    使用缓存机制提升配置读取性能，避免频繁的文件 I/O 操作。
    """

    _cache: dict[str, Any] | None = None
    _cache_time: float = 0
    _cache_ttl: float = 300.0

    def __init__(self) -> None:
        """初始化配置管理器"""
        config_dir = os.environ.get("NANOBOT_CONFIG_DIR")
        if config_dir:
            self.base_dir = Path(config_dir)
        else:
            self.base_dir = Path.home() / ".nanobot-runner"

        self.config_file = self.base_dir / "config.json"

        self.data_dir = self.base_dir / "data"
        self.index_file = self.data_dir / "index.json"
        self.cron_dir = self.base_dir / "cron"
        self.cron_store = self.cron_dir / "jobs.json"

        self._ensure_dirs()
        self._ensure_config()

        try:
            config = self.load_config()
            if "data_dir" in config:
                self.data_dir = Path(config["data_dir"])
                self.index_file = self.data_dir / "index.json"
        except Exception as e:
            import loguru

            loguru.logger.debug(f"读取配置文件失败，使用默认路径: {e}")

    def _ensure_dirs(self) -> None:
        """确保必要目录存在，并迁移旧的定时任务配置"""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cron_dir.mkdir(parents=True, exist_ok=True)

        self._migrate_old_cron_config()

    def _migrate_old_cron_config(self) -> None:
        """迁移旧的定时任务配置到新位置"""
        import loguru

        old_cron_store = Path.home() / ".nanobot" / "cron" / "jobs.json"
        new_cron_store = self.cron_store

        if old_cron_store.exists() and not new_cron_store.exists():
            try:
                shutil.copy2(old_cron_store, new_cron_store)
                loguru.logger.info(
                    f"已迁移定时任务配置：{old_cron_store} -> {new_cron_store}"
                )
            except Exception as e:
                loguru.logger.warning(f"迁移定时任务配置失败：{e}")

    def _ensure_config(self) -> None:
        """确保配置文件存在"""
        if not self.config_file.exists():
            default_config = {
                "version": "0.1.0",
                "data_dir": str(self.data_dir),
                "auto_push_feishu": False,
                "feishu_app_id": "",
                "feishu_app_secret": "",
                "feishu_receive_id": "",
                "feishu_receive_id_type": "user_id",
            }
            self.save_config(default_config)

    def _invalidate_cache(self) -> None:
        """清除配置缓存"""
        ConfigManager._cache = None
        ConfigManager._cache_time = 0

    def _is_cache_valid(self) -> bool:
        """检查缓存是否有效"""
        if ConfigManager._cache is None:
            return False

        if time.time() - ConfigManager._cache_time > ConfigManager._cache_ttl:
            return False

        if self.config_file.exists():
            file_mtime = self.config_file.stat().st_mtime
            if file_mtime > ConfigManager._cache_time:
                return False

        return True

    def save_config(self, config: dict[str, Any]) -> None:
        """保存配置

        Args:
            config: 配置字典

        Raises:
            ValueError: 配置验证失败时抛出
        """
        is_valid, errors = AppConfig.validate(config)
        if not is_valid:
            error_msg = "配置验证失败，无法保存:\n" + "\n".join(
                f"  - {e}" for e in errors
            )
            raise ValueError(error_msg)

        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        self._invalidate_cache()

    def load_config(self, use_cache: bool = True) -> dict:
        """加载配置

        Args:
            use_cache: 是否使用缓存（默认 True）

        Returns:
            dict: 配置字典

        Raises:
            ValueError: 配置验证失败时抛出
        """
        if use_cache and self._is_cache_valid():
            if ConfigManager._cache is None:
                raise RuntimeError("配置缓存状态异常：缓存有效但值为 None")
            return ConfigManager._cache.copy()

        with open(self.config_file, encoding="utf-8") as f:
            config = json.load(f)

        is_valid, errors = AppConfig.validate(config)
        if not is_valid:
            error_msg = "配置文件验证失败:\n" + "\n".join(f"  - {e}" for e in errors)
            raise ValueError(error_msg)

        ConfigManager._cache = config.copy()
        ConfigManager._cache_time = time.time()

        return config

    def get(self, key: str, default: Any = None) -> Any:
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

    def set(self, key: str, value: Any) -> None:
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

    def reload_config(self) -> dict:
        """强制重新加载配置（忽略缓存）

        Returns:
            dict: 配置字典
        """
        self._invalidate_cache()
        return self.load_config(use_cache=False)


config = ConfigManager()
