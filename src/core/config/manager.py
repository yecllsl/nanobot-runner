# 配置管理模块
# 管理项目配置和本地数据目录

import json
import os
import shutil
import time
from enum import Enum
from pathlib import Path
from typing import Any

from src.core.base.logger import get_logger
from src.core.config.schema import AppConfig

logger = get_logger(__name__)


class ConfigSource(Enum):
    ENV = "env"
    FILE = "file"
    DEFAULT = "default"


ENV_KEY_MAPPING: dict[str, str] = {
    "data_dir": "NANOBOT_DATA_DIR",
    "workspace_dir": "NANOBOT_WORKSPACE_DIR",
    "auto_push_feishu": "NANOBOT_AUTO_PUSH_FEISHU",
    "feishu_app_id": "NANOBOT_FEISHU_APP_ID",
    "feishu_app_secret": "NANOBOT_FEISHU_APP_SECRET",
    "feishu_receive_id": "NANOBOT_FEISHU_RECEIVE_ID",
    "feishu_receive_id_type": "NANOBOT_FEISHU_RECEIVE_ID_TYPE",
    "timezone": "NANOBOT_TIMEZONE",
    "default_year": "NANOBOT_DEFAULT_YEAR",
    "llm_provider": "NANOBOT_LLM_PROVIDER",
    "llm_model": "NANOBOT_LLM_MODEL",
    "llm_base_url": "NANOBOT_LLM_BASE_URL",
}


class ConfigManager:
    """配置管理器，管理项目配置和本地数据目录

    使用缓存机制提升配置读取性能，避免频繁的文件 I/O 操作。
    支持环境变量覆盖（优先级：环境变量 > 配置文件 > 默认值）和无配置模式。
    """

    _cache: dict[str, Any] | None = None
    _cache_time: float = 0
    _cache_ttl: float = 300.0

    @classmethod
    def reset_cache(cls) -> None:
        """重置配置缓存

        用于测试场景，确保每次测试都从文件读取最新配置
        """
        cls._cache = None
        cls._cache_time = 0

    def __init__(self, allow_default: bool = False) -> None:
        """初始化配置管理器

        Args:
            allow_default: 是否允许使用默认配置（配置文件不存在时），
                           用于初始化向导等场景解决Bootstrap问题
        """
        self.allow_default = allow_default
        self._using_default = False

        self.config_file = self._detect_config_file()

        config_dir = self.config_file.parent
        self.base_dir = config_dir
        self.data_dir = config_dir / "data"
        self.index_file = self.data_dir / "index.json"
        self.cron_dir = config_dir / "cron"
        self.cron_store = self.cron_dir / "jobs.json"

        if not self._using_default:
            self._ensure_dirs()
            self._ensure_config()

            try:
                config = self.load_config()
                if "data_dir" in config:
                    self.data_dir = Path(config["data_dir"])
                    self.index_file = self.data_dir / "index.json"
                # 读取 user_id，如果没有则使用默认值
                self.user_id = config.get("user_id", "default_user")
            except Exception as e:
                logger.debug(f"读取配置文件失败，使用默认路径: {e}")
                self.user_id = "default_user"
        else:
            self.user_id = "default_user"

    def _detect_config_file(self) -> Path:
        """检测配置文件路径

        优先级：
        1. 环境变量 NANOBOT_CONFIG_FILE
        2. 环境变量 NANOBOT_CONFIG_DIR 下的 config.json
        3. ~/.nanobot-runner/config.json

        当 allow_default=True 且配置文件不存在时，设置 _using_default=True，
        避免自动创建配置文件（用于初始化向导场景）。

        Returns:
            Path: 配置文件路径
        """
        if env_file := os.getenv("NANOBOT_CONFIG_FILE"):
            path = Path(env_file)
            if path.exists():
                return path
            if not self.allow_default:
                return path
            self._using_default = True
            return path

        if config_dir := os.getenv("NANOBOT_CONFIG_DIR"):
            path = Path(config_dir) / "config.json"
            if path.exists():
                return path
            if not self.allow_default:
                return path
            self._using_default = True
            return path

        default_path = Path.home() / ".nanobot-runner" / "config.json"
        if default_path.exists():
            return default_path
        if not self.allow_default:
            return default_path

        self._using_default = True
        return default_path

    @staticmethod
    def _get_default_config() -> dict[str, Any]:
        """获取默认配置

        Returns:
            dict: 默认配置字典
        """
        return {
            "version": "0.9.4",
            "data_dir": str(Path.home() / ".nanobot-runner" / "data"),
            "auto_push_feishu": False,
            "feishu_app_id": "",
            "feishu_app_secret": "",
            "feishu_receive_id": "",
            "feishu_receive_id_type": "user_id",
        }

    def _ensure_dirs(self) -> None:
        """确保必要目录存在，并迁移旧的定时任务配置"""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cron_dir.mkdir(parents=True, exist_ok=True)

        self._migrate_old_cron_config()

    def _migrate_old_cron_config(self) -> None:
        """迁移旧的定时任务配置到新位置"""
        old_cron_store = Path.home() / ".nanobot" / "cron" / "jobs.json"
        new_cron_store = self.cron_store

        if old_cron_store.exists() and not new_cron_store.exists():
            try:
                shutil.copy2(old_cron_store, new_cron_store)
                logger.info(f"已迁移定时任务配置：{old_cron_store} -> {new_cron_store}")
            except Exception as e:
                logger.warning(f"迁移定时任务配置失败：{e}")

    def _ensure_config(self) -> None:
        """确保配置文件存在

        在初始化向导场景下（allow_default=True），不自动创建配置文件，
        由向导引导用户完成配置后再生成，避免误判为"工作区已初始化"。
        """
        if not self.config_file.exists() and not self.allow_default:
            self.save_config(self._get_default_config())

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
        if self._using_default:
            return self._get_default_config()

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

    def load_config_with_env_override(self) -> dict[str, Any]:
        """加载配置并支持环境变量覆盖

        配置加载优先级：环境变量 > 配置文件 > 默认值

        Returns:
            dict[str, Any]: 合并后的配置字典
        """
        config = self.load_config()

        for config_key, env_key in ENV_KEY_MAPPING.items():
            env_value = os.getenv(env_key)
            if env_value is not None:
                config[config_key] = self._cast_env_value(config_key, env_value)

        return config

    @staticmethod
    def _cast_env_value(key: str, value: str) -> Any:
        """将环境变量字符串值转换为对应类型

        Args:
            key: 配置项键名
            value: 环境变量字符串值

        Returns:
            Any: 类型转换后的值
        """
        bool_keys = {"auto_push_feishu"}
        int_keys = {"default_year"}

        if key in bool_keys:
            return value.lower() in ("true", "1", "yes")
        if key in int_keys:
            try:
                return int(value)
            except ValueError:
                return value
        return value

    def get_config_source(self, field: str) -> ConfigSource:
        """获取配置值的来源

        Args:
            field: 配置项键名

        Returns:
            ConfigSource: 配置值来源
        """
        env_key = ENV_KEY_MAPPING.get(field)
        if env_key and os.getenv(env_key) is not None:
            return ConfigSource.ENV

        if self._using_default:
            return ConfigSource.DEFAULT

        try:
            config = self.load_config()
            if field in config:
                return ConfigSource.FILE
        except Exception:
            pass

        return ConfigSource.DEFAULT

    def validate_config_consistency(self) -> list[dict[str, str]]:
        """验证配置一致性

        检查环境变量与配置文件之间的值是否冲突。

        Returns:
            list[dict[str, str]]: 不一致项列表，每项包含field、env_value、file_value
        """
        inconsistencies: list[dict[str, str]] = []

        if self._using_default:
            return inconsistencies

        try:
            file_config = self.load_config()
        except Exception:
            return inconsistencies

        for config_key, env_key in ENV_KEY_MAPPING.items():
            env_value = os.getenv(env_key)
            if env_value is not None and config_key in file_config:
                file_value = str(file_config[config_key])
                casted_env = self._cast_env_value(config_key, env_value)
                if str(casted_env) != file_value:
                    inconsistencies.append(
                        {
                            "field": config_key,
                            "env_value": env_value,
                            "file_value": file_value,
                        }
                    )

        return inconsistencies

    def get_llm_config(self) -> dict[str, Any]:
        """获取LLM配置

        优先级：环境变量 > 配置文件 > 默认值

        Returns:
            dict[str, Any]: LLM配置字典，包含provider、model、api_key、base_url
        """
        config = self.load_config()
        return {
            "provider": os.getenv("NANOBOT_LLM_PROVIDER")
            or config.get("llm_provider", ""),
            "model": os.getenv("NANOBOT_LLM_MODEL") or config.get("llm_model", ""),
            "api_key": os.getenv("NANOBOT_LLM_API_KEY"),
            "base_url": os.getenv("NANOBOT_LLM_BASE_URL") or config.get("llm_base_url"),
        }

    def has_llm_config(self) -> bool:
        """检查是否配置了LLM

        Returns:
            bool: 是否存在LLM配置（至少包含provider和model）
        """
        llm = self.get_llm_config()
        return bool(llm.get("provider") and llm.get("model"))

    def save_llm_config(
        self,
        provider: str,
        model: str,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        """保存LLM配置

        将LLM配置项保存到config.json，API Key保存到.env.local。

        Args:
            provider: LLM提供商名称
            model: 模型名称
            base_url: 自定义API端点URL（可选）
            api_key: API密钥（可选，保存到.env.local而非config.json）
        """
        config = self.load_config()
        config["llm_provider"] = provider
        config["llm_model"] = model

        if base_url is not None:
            config["llm_base_url"] = base_url
        elif "llm_base_url" in config:
            del config["llm_base_url"]

        self.save_config(config)

        if api_key is not None:
            from src.core.config.env_manager import EnvManager

            env_manager = EnvManager(env_file=self.base_dir / ".env.local")
            env_vars: dict[str, str] = {
                "NANOBOT_LLM_API_KEY": api_key,
                "NANOBOT_LLM_PROVIDER": provider,
                "NANOBOT_LLM_MODEL": model,
            }
            if base_url:
                env_vars["NANOBOT_LLM_BASE_URL"] = base_url
            env_manager.save_env_file(env_vars)


config = ConfigManager(allow_default=True)
