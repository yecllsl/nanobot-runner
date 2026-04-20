from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from src.core.config import ConfigManager
from src.core.exceptions import LLMError
from src.core.llm_config import LLMConfig
from src.core.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class AgentDefaults:
    """Agent默认配置数据类

    封装AgentLoop所需的默认参数配置。

    Attributes:
        model: 模型名称
        max_tool_iterations: 最大工具调用迭代次数
        context_window_tokens: 上下文窗口token数量
        context_block_limit: 上下文块数量限制
        max_tool_result_chars: 工具返回结果最大字符数
    """

    model: str
    max_tool_iterations: int = 10
    context_window_tokens: int = 128000
    context_block_limit: int = 10
    max_tool_result_chars: int = 32000


class ProviderAdapter(Protocol):
    """配置注入层协议

    负责将项目配置注入到nanobot-ai模块，替代其默认的~/.nanobot/config.json加载机制。
    所有LLM配置的获取都应通过此协议进行，确保配置来源的一致性。
    """

    def get_llm_config(self) -> LLMConfig:
        """获取LLM配置

        Returns:
            LLMConfig: LLM配置数据类实例
        """
        ...

    def get_provider_instance(self) -> Any:
        """获取Provider实例（用于AgentLoop）

        Returns:
            Any: nanobot Provider实例
        """
        ...

    def get_agent_defaults(self) -> AgentDefaults:
        """获取Agent默认配置（用于AgentLoop）

        Returns:
            AgentDefaults: Agent默认配置实例
        """
        ...

    def is_available(self) -> bool:
        """检查配置是否可用

        Returns:
            bool: 配置是否可用
        """
        ...

    def close(self) -> None:
        """关闭Provider连接，释放资源"""
        ...


class RunnerProviderAdapter:
    """项目配置注入器

    从项目配置读取LLM配置，注入到nanobot-ai模块。
    支持回退到nanobot配置（仅用于兼容已安装nanobot的用户）。

    配置优先级：
    1. 项目配置（主配置源）：~/.nanobot-runner/config.json + 环境变量
    2. nanobot配置（回退）：~/.nanobot/config.json
    """

    def __init__(self, runner_config: ConfigManager) -> None:
        """初始化配置注入器

        Args:
            runner_config: 项目配置管理器实例
        """
        self._runner_config = runner_config
        self._nanobot_config: Any | None = None
        self._provider_instance: Any | None = None

    def get_llm_config(self) -> LLMConfig:
        """获取LLM配置

        优先从项目配置读取，回退到nanobot配置。

        Returns:
            LLMConfig: LLM配置数据类实例

        Raises:
            LLMError: 未配置LLM时抛出
        """
        if self._has_runner_llm_config():
            return self._from_runner_config()
        if self._try_load_nanobot_config():
            return self._from_nanobot_config()
        raise LLMError(
            "未配置LLM，请运行 'nanobotrun system init' 完成配置",
            recovery_suggestion="运行 nanobotrun system init 配置LLM，或设置 NANOBOT_LLM_PROVIDER 和 NANOBOT_LLM_MODEL 环境变量",
        )

    def get_provider_instance(self) -> Any:
        """获取Provider实例

        使用nanobot-ai的Provider创建逻辑，从项目配置构建Provider。

        Returns:
            Any: nanobot Provider实例

        Raises:
            LLMError: Provider创建失败时抛出
        """
        if self._provider_instance is not None:
            return self._provider_instance

        llm_config = self.get_llm_config()

        try:
            from nanobot.providers.openai_compat_provider import OpenAICompatProvider
            from nanobot.providers.registry import find_by_name

            spec = find_by_name(llm_config.provider)
            self._provider_instance = OpenAICompatProvider(
                api_key=llm_config.api_key,
                api_base=llm_config.base_url,
                default_model=llm_config.model,
                spec=spec,
            )
            return self._provider_instance
        except ImportError as e:
            raise LLMError(
                f"无法导入nanobot模块: {e}",
                recovery_suggestion="请确认已安装nanobot-ai: uv add nanobot-ai",
            ) from e
        except Exception as e:
            raise LLMError(
                f"创建Provider失败: {e}",
                recovery_suggestion="请检查LLM配置是否正确，特别是API Key和Base URL",
            ) from e

    def get_agent_defaults(self) -> AgentDefaults:
        """获取Agent默认配置

        Returns:
            AgentDefaults: Agent默认配置实例
        """
        llm_config = self.get_llm_config()
        return AgentDefaults(
            model=llm_config.model,
            max_tool_iterations=llm_config.max_iterations,
            context_window_tokens=llm_config.context_window_tokens,
            context_block_limit=llm_config.context_block_limit,
            max_tool_result_chars=llm_config.max_tool_result_chars,
        )

    def is_available(self) -> bool:
        """检查配置是否可用

        Returns:
            bool: 项目配置或nanobot配置是否包含LLM配置
        """
        return self._has_runner_llm_config() or self._try_load_nanobot_config()

    def close(self) -> None:
        """关闭Provider连接，释放资源"""
        self._provider_instance = None

    def _get_or_create_nanobot_config(self) -> Any:
        """获取或创建nanobot配置对象

        用于ChannelManager等需要nanobot配置对象的场景。
        始终从项目配置构建，确保包含飞书通道配置。

        Returns:
            Any: nanobot配置对象
        """
        if self._nanobot_config is not None:
            return self._nanobot_config

        return self._build_nanobot_config_from_runner()

    def _build_nanobot_config_from_runner(self) -> Any:
        """从项目配置构建nanobot配置对象

        Returns:
            Any: nanobot配置对象
        """
        try:
            from nanobot.config.loader import Config
            from nanobot.config.schema import AgentsConfig, ProvidersConfig

            llm_dict = self._runner_config.get_llm_config()
            provider_name = llm_dict.get("provider", "openai")

            providers = ProvidersConfig(
                default=provider_name,
            )
            setattr(
                providers,
                provider_name,
                {
                    "api_key_env": "NANOBOT_LLM_API_KEY",
                    **(
                        {"base_url": llm_dict["base_url"]}
                        if llm_dict.get("base_url")
                        else {}
                    ),
                },
            )

            agents = AgentsConfig(
                defaults={"model": llm_dict.get("model", "gpt-4o-mini")},
            )

            channels: dict[str, Any] = {}

            feishu_app_id = os.getenv("NANOBOT_FEISHU_APP_ID")
            feishu_app_secret = os.getenv("NANOBOT_FEISHU_APP_SECRET")
            feishu_receive_id = os.getenv("NANOBOT_FEISHU_RECEIVE_ID")

            if not (feishu_app_id and feishu_app_secret):
                env_file = Path.home() / ".nanobot-runner" / ".env.local"
                if env_file.exists():
                    env_vars = self._parse_env_file(env_file)
                    feishu_app_id = feishu_app_id or env_vars.get(
                        "NANOBOT_FEISHU_APP_ID"
                    )
                    feishu_app_secret = feishu_app_secret or env_vars.get(
                        "NANOBOT_FEISHU_APP_SECRET"
                    )
                    feishu_receive_id = feishu_receive_id or env_vars.get(
                        "NANOBOT_FEISHU_RECEIVE_ID"
                    )

            if feishu_app_id and feishu_app_secret:
                channels["feishu"] = {
                    "enabled": True,
                    "app_id": feishu_app_id,
                    "app_secret": feishu_app_secret,
                    "receive_id": feishu_receive_id or "",
                    "receive_id_type": os.getenv(
                        "NANOBOT_FEISHU_RECEIVE_ID_TYPE", "user_id"
                    ),
                    "allowFrom": ["*"],
                }

            config = Config(
                providers=providers,
                agents=agents,
                channels=channels,
            )

            self._nanobot_config = config
            return config
        except (ImportError, Exception) as e:
            logger.debug(f"从项目配置构建nanobot配置失败: {e}")
            raise LLMError(
                f"无法构建nanobot配置: {e}",
                recovery_suggestion="请确认已安装nanobot-ai",
            ) from e

    @staticmethod
    def _parse_env_file(env_file: Path) -> dict[str, str]:
        """解析 .env 文件

        Args:
            env_file: .env 文件路径

        Returns:
            dict[str, str]: 环境变量字典
        """
        env_vars: dict[str, str] = {}
        try:
            with open(env_file, encoding="utf-8") as f:
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
                        env_vars[key] = value
        except Exception as e:
            logger.debug(f"解析 .env 文件失败: {e}")
        return env_vars

    def _has_runner_llm_config(self) -> bool:
        """检查项目配置中是否有LLM配置

        Returns:
            bool: 是否存在LLM配置
        """
        try:
            return self._runner_config.has_llm_config()
        except Exception:
            return False

    def _try_load_nanobot_config(self) -> bool:
        """尝试加载nanobot配置（回退）

        Returns:
            bool: 是否成功加载nanobot配置
        """
        if self._nanobot_config is not None:
            return True

        try:
            from nanobot.config.loader import load_config

            self._nanobot_config = load_config()
            return True
        except (ImportError, FileNotFoundError, ValueError) as e:
            logger.debug(f"nanobot配置加载失败: {e}")
            return False

    def _from_runner_config(self) -> LLMConfig:
        """从项目配置提取LLM配置

        Returns:
            LLMConfig: LLM配置数据类实例
        """
        llm_dict = self._runner_config.get_llm_config()
        return LLMConfig(
            provider=llm_dict.get("provider", "openai"),
            model=llm_dict.get("model", "gpt-4o-mini"),
            api_key=llm_dict.get("api_key"),
            base_url=llm_dict.get("base_url"),
        )

    def _from_nanobot_config(self) -> LLMConfig:
        """从nanobot配置提取LLM配置（回退）

        Returns:
            LLMConfig: LLM配置数据类实例
        """
        if self._nanobot_config is None:
            raise LLMError(
                "nanobot配置未加载",
                recovery_suggestion="请确认已安装nanobot-ai并正确配置",
            )

        defaults = self._nanobot_config.agents.defaults
        provider_name = self._nanobot_config.providers.default

        api_key: str | None = None
        providers = self._nanobot_config.providers
        if hasattr(providers, provider_name):
            provider_cfg = getattr(providers, provider_name)
            api_key = getattr(provider_cfg, "api_key", None)

        base_url: str | None = None
        if hasattr(providers, provider_name):
            provider_cfg = getattr(providers, provider_name)
            base_url = getattr(provider_cfg, "base_url", None)

        return LLMConfig(
            provider=provider_name,
            model=defaults.model,
            api_key=api_key or os.getenv("NANOBOT_LLM_API_KEY"),
            base_url=base_url,
            max_iterations=defaults.max_tool_iterations,
            context_window_tokens=defaults.context_window_tokens,
            context_block_limit=defaults.context_block_limit,
            max_tool_result_chars=defaults.max_tool_result_chars,
        )
