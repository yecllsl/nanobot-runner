# 配置管理模块
# 管理项目配置和本地数据目录

import json
import os
import time
from enum import Enum
from pathlib import Path
from typing import Any

from src.core.base.exceptions import ConfigError, NanobotRunnerError
from src.core.base.logger import get_logger
from src.core.config.legacy import LEGACY_NANOBOT_FIELDS
from src.core.config.schema import AppConfig

logger = get_logger(__name__)


class ConfigSource(Enum):
    ENV = "env"
    FILE = "file"
    DEFAULT = "default"


# Runner 专有字段无需环境变量覆盖
ENV_KEY_MAPPING: dict[str, str] = {}

# 需要布尔类型转换的配置键
BOOL_KEYS: set[str] = {"auto_push_feishu", "enabled"}

# 需要整数类型转换的配置键
INT_KEYS: set[str] = {"default_year", "port", "token_ttl_s"}


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
            except (
                NanobotRunnerError,
                json.JSONDecodeError,
                ValueError,
                AttributeError,
                TypeError,
            ) as e:
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
        """获取默认配置（仅 Runner 专有字段）

        Returns:
            dict: 默认配置字典
        """
        return {
            "version": "0.32.0",
            "data_dir": str(Path.home() / ".nanobot-runner" / "data"),
            "timezone": "Asia/Shanghai",
            "auto_push_feishu": False,
            "user_id": "default_user",
        }

    def _ensure_dirs(self) -> None:
        """确保必要目录存在"""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cron_dir.mkdir(parents=True, exist_ok=True)

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

    def get_nanobot_config_path(self) -> Path:
        """获取 nanobot_config.json 路径

        Returns:
            Path: nanobot_config.json 文件路径
        """
        return self.base_dir / "nanobot_config.json"

    def load_nanobot_config(self) -> dict[str, Any]:
        """加载 nanobot_config.json

        nanobot_config.json 是 nanobot 配置的唯一真实源，包含
        providers/agents/channels/model_presets/tools 等字段。

        Returns:
            dict[str, Any]: nanobot 配置字典，文件不存在时返回空 dict

        Raises:
            ConfigError: JSON 格式错误时抛出（规格 7.3 错误处理要求）
        """
        path = self.get_nanobot_config_path()
        if not path.exists():
            return {}
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigError(
                f"配置文件格式错误，请检查 nanobot_config.json: {e}",
                recovery_suggestion="请修正 JSON 语法错误",
            ) from e

    def get_webui_config(self) -> dict[str, Any]:
        """获取 WebUI 配置

        从 nanobot_config.json 的 channels.websocket 读取 WebUI 相关配置，
        不存在时返回默认值。

        Returns:
            dict[str, Any]: WebUI 配置字典，包含 host、port、token_secret、
                           token_ttl_s、cors_origins 等字段
        """
        defaults: dict[str, Any] = {
            "host": "127.0.0.1",
            "port": 8766,
            "token_secret": "",
            "token_ttl_s": 86400,
            "cors_origins": ["http://127.0.0.1:8765"],
        }

        nanobot_config = self.load_nanobot_config()
        channels = nanobot_config.get("channels", {})
        ws_config = channels.get("websocket", {})

        if not ws_config:
            return defaults

        result = {**defaults}
        if "host" in ws_config:
            result["host"] = ws_config["host"]
        if "port" in ws_config:
            result["port"] = ws_config["port"]
        if "tokenIssueSecret" in ws_config:
            result["token_secret"] = ws_config["tokenIssueSecret"]
        if "token_ttl_s" in ws_config:
            result["token_ttl_s"] = ws_config["token_ttl_s"]

        return result

    def check_legacy_fields(self) -> list[str]:
        """检测 config.json 是否含旧版 nanobot 字段

        迁移完成后 config.json 不应含这些字段。若存在则打印 warning
        并返回字段名列表，供调用方提示用户运行 migrate-config。

        Returns:
            list[str]: 存在的旧版字段名列表
        """
        config = self.load_config()
        found = [f for f in LEGACY_NANOBOT_FIELDS if f in config]
        if found:
            logger.warning(
                "检测到 config.json 含旧版 nanobot 字段 %s，"
                "建议运行 'nanobotrun system migrate-config' 迁移",
                found,
            )
        return found

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
        if key in BOOL_KEYS:
            return value.lower() in ("true", "1", "yes")
        if key in INT_KEYS:
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
        except NanobotRunnerError:
            pass

        return ConfigSource.DEFAULT

    def validate_config_consistency(self) -> list[dict[str, str]]:
        """验证配置一致性

        Returns:
            list[dict[str, str]]: 不一致项列表
        """
        return []

    def has_llm_config(self) -> bool:
        """检查是否配置了有效的 LLM

        检查 nanobot_config.json 是否有 providers.default
        且对应 provider 有非空 apiKey。

        Returns:
            bool: 是否存在有效 LLM 配置
        """
        nano_cfg = self.load_nanobot_config()
        providers = nano_cfg.get("providers", {})
        default_provider = providers.get("default", "")
        if not default_provider:
            return False
        provider_cfg = providers.get(default_provider, {})
        return bool(provider_cfg.get("apiKey"))

    def resolve_webui_dist(self) -> Path | None:
        """解析 WebUI dist 目录

        优先使用 RunFlowAgent 自有 dist（项目根/webui/dist），
        回退到 nanobot 内置 dist（nanobot/web/dist）。

        Returns:
            Path | None: dist 目录路径，不存在则返回 None
        """
        custom_dist = Path(__file__).parent.parent.parent.parent / "webui" / "dist"
        if custom_dist.exists():
            return custom_dist

        try:
            import nanobot.web as web_pkg

            nanobot_dist = Path(web_pkg.__file__).parent / "dist"
            if nanobot_dist.exists():
                return nanobot_dist
        except (ImportError, AttributeError):
            pass

        return None


config = ConfigManager(allow_default=True)
