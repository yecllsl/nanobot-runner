import os
from pathlib import Path

from src.core.base.exceptions import ConfigError
from src.core.base.logger import get_logger

logger = get_logger(__name__)

_ENV_TEMPLATE = """# Nanobot Runner 环境变量配置
# 复制此文件为 .env.local 并填写实际值

# LLM Provider 配置
NANOBOT_LLM_PROVIDER=openai
NANOBOT_LLM_MODEL=gpt-4o-mini
NANOBOT_LLM_API_KEY=your-api-key-here
NANOBOT_LLM_BASE_URL=

# Workspace 配置
NANOBOT_WORKSPACE_DIR=
NANOBOT_DATA_DIR=

# 飞书通知配置（可选）
NANOBOT_FEISHU_APP_ID=
NANOBOT_FEISHU_APP_SECRET=
NANOBOT_FEISHU_RECEIVE_ID=
NANOBOT_AUTO_PUSH_FEISHU=false
"""


class EnvManager:
    """环境变量管理器

    提供环境变量的加载、读取、设置和持久化功能。
    支持 .env.local 文件格式。
    """

    def __init__(self, env_file: Path | None = None) -> None:
        """初始化环境变量管理器

        Args:
            env_file: 环境变量文件路径，默认为当前目录下的 .env.local
        """
        self.env_file = env_file or Path(".env.local")
        self._loaded = False

    def load_env(self, env_file: Path | None = None) -> dict[str, str]:
        """加载环境变量文件

        Args:
            env_file: 环境变量文件路径，默认使用初始化时指定的路径

        Returns:
            dict[str, str]: 加载的环境变量字典
        """
        target_file = env_file or self.env_file

        if not target_file.exists():
            logger.debug(f"环境变量文件不存在: {target_file}")
            return {}

        loaded: dict[str, str] = {}
        with open(target_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                if "=" not in line:
                    continue

                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip("\"'")

                if key and value:
                    os.environ[key] = value
                    loaded[key] = value

        self._loaded = True
        logger.debug(f"已加载 {len(loaded)} 个环境变量: {target_file}")
        return loaded

    def get_env(self, key: str, default: str | None = None) -> str | None:
        """获取环境变量

        Args:
            key: 环境变量名
            default: 默认值

        Returns:
            str | None: 环境变量值
        """
        return os.getenv(key, default)

    def set_env(self, key: str, value: str, persist: bool = False) -> None:
        """设置环境变量

        Args:
            key: 环境变量名
            value: 环境变量值
            persist: 是否持久化到 .env.local 文件
        """
        os.environ[key] = value

        if persist:
            self.save_env_file({key: value})

    def save_env_file(
        self, env_vars: dict[str, str], file_path: Path | None = None
    ) -> None:
        """保存环境变量到文件

        Args:
            env_vars: 环境变量字典
            file_path: 保存路径，默认使用初始化时指定的路径

        Raises:
            ConfigError: 保存失败时抛出
        """
        target_file = file_path or self.env_file

        try:
            existing: dict[str, str] = {}
            if target_file.exists():
                with open(target_file, encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if "=" in line:
                            k, _, v = line.partition("=")
                            existing[k.strip()] = v.strip().strip("\"'")

            existing.update(env_vars)

            lines: list[str] = ["# Nanobot Runner 环境变量配置\n"]
            for k, v in existing.items():
                lines.append(f"{k}={v}\n")

            target_file.parent.mkdir(parents=True, exist_ok=True)
            with open(target_file, "w", encoding="utf-8") as f:
                f.writelines(lines)

            logger.debug(f"已保存 {len(env_vars)} 个环境变量: {target_file}")
        except OSError as e:
            raise ConfigError(
                f"保存环境变量文件失败: {target_file}",
                recovery_suggestion="请检查文件路径和写入权限",
            ) from e

    def generate_env_template(self) -> str:
        """生成环境变量模板

        Returns:
            str: .env.example 文件内容
        """
        return _ENV_TEMPLATE

    def get_llm_env_vars(self) -> dict[str, str | None]:
        """获取LLM相关环境变量

        Returns:
            dict[str, str | None]: LLM环境变量字典
        """
        return {
            "provider": os.getenv("NANOBOT_LLM_PROVIDER"),
            "model": os.getenv("NANOBOT_LLM_MODEL"),
            "api_key": os.getenv("NANOBOT_LLM_API_KEY"),
            "base_url": os.getenv("NANOBOT_LLM_BASE_URL"),
        }

    def has_llm_api_key(self) -> bool:
        """检查是否配置了LLM API Key

        Returns:
            bool: 是否存在API Key
        """
        return bool(os.getenv("NANOBOT_LLM_API_KEY"))

    def load_llm_env(self, env_file: Path | None = None) -> dict[str, str]:
        """加载LLM相关环境变量

        优先加载指定文件中的环境变量，然后返回LLM配置。

        Args:
            env_file: 环境变量文件路径

        Returns:
            dict[str, str]: 加载的LLM环境变量
        """
        self.load_env(env_file)

        llm_keys = [
            "NANOBOT_LLM_PROVIDER",
            "NANOBOT_LLM_MODEL",
            "NANOBOT_LLM_API_KEY",
            "NANOBOT_LLM_BASE_URL",
        ]

        loaded: dict[str, str] = {}
        for key in llm_keys:
            value = os.getenv(key)
            if value:
                loaded[key] = value

        return loaded
