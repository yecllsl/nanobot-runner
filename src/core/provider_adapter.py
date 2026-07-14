from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Protocol

from nanobot.providers.registry import PROVIDERS, ProviderSpec, create_dynamic_spec

from src.core.base.exceptions import LLMError, NanobotRunnerError
from src.core.base.logger import get_logger
from src.core.config.llm_config import LLMConfig
from src.core.config.manager import ConfigManager

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
        timezone: Agent 时区（IANA 格式），影响日程和时间感知回复
    """

    model: str
    max_tool_iterations: int = 10
    context_window_tokens: int = 128000
    context_block_limit: int = 10
    max_tool_result_chars: int = 32000
    timezone: str = "UTC"


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
    完全依赖项目配置（~/.nanobot-runner/config.json），不回退到 ~/.nanobot/config.json。
    """

    def __init__(
        self, runner_config: ConfigManager, *, webui_enabled: bool = False
    ) -> None:
        """初始化配置注入器

        Args:
            runner_config: 项目配置管理器实例
            webui_enabled: 已废弃，保留兼容性，Task 5+ 清理
        """
        self._runner_config = runner_config
        self._provider_instance: Any | None = None

    def get_llm_config(self) -> LLMConfig:
        """获取LLM配置

        从 nanobot_config.json 读取 providers 和 agents.defaults.model。

        Returns:
            LLMConfig: LLM配置数据类实例

        Raises:
            LLMError: 未配置LLM时抛出
        """
        if not self._has_runner_llm_config():
            raise LLMError(
                "未配置LLM，请运行 'nanobotrun system init' 完成配置",
                recovery_suggestion="运行 nanobotrun system init 配置LLM",
            )
        return self._from_nanobot_config()

    def get_provider_instance(self) -> Any:
        """获取Provider实例

        支持 FallbackProvider 包装：当配置了 fallback_models 时，
        自动创建主备链式故障转移。

        Returns:
            Any: nanobot Provider实例（可能是 FallbackProvider 包装）

        Raises:
            LLMError: Provider创建失败时抛出
        """
        if self._provider_instance is not None:
            return self._provider_instance

        llm_config = self.get_llm_config()
        primary = self._create_primary_provider(llm_config)

        fallback_presets = self._resolve_fallback_presets()
        if not fallback_presets:
            self._provider_instance = primary
            return primary

        try:
            from nanobot.providers.fallback_provider import FallbackProvider

            self._provider_instance = FallbackProvider(
                primary=primary,
                fallback_presets=fallback_presets,
                provider_factory=self._create_fallback_provider,
            )
            logger.info(
                "FallbackProvider 已启用，主供应商: %s，备选: %d 个",
                llm_config.provider,
                len(fallback_presets),
            )
            return self._provider_instance
        except ImportError:
            logger.warning("nanobot-ai 未支持 FallbackProvider，降级为单供应商模式")
            self._provider_instance = primary
            return primary

    def _create_primary_provider(self, llm_config: LLMConfig) -> Any:
        """创建主 Provider 实例

        Args:
            llm_config: LLM 配置

        Returns:
            Any: nanobot Provider 实例

        Raises:
            LLMError: Provider 创建失败时抛出
        """
        try:
            from nanobot.providers.openai_compat_provider import OpenAICompatProvider
            from nanobot.providers.registry import find_by_name

            spec = find_by_name(llm_config.provider)
            return OpenAICompatProvider(
                api_key=llm_config.api_key,
                api_base=llm_config.base_url,
                default_model=llm_config.model,
                spec=spec,
            )
        except ImportError as e:
            raise LLMError(
                f"无法导入nanobot模块: {e}",
                recovery_suggestion="请确认已安装nanobot-ai: uv add nanobot-ai",
            ) from e
        except (NanobotRunnerError, OSError, ValueError) as e:
            raise LLMError(
                f"创建Provider失败: {e}",
                recovery_suggestion="请检查LLM配置是否正确，特别是API Key和Base URL",
            ) from e

    def _resolve_fallback_presets(self) -> list[Any]:
        """解析 fallback 预设列表

        从 nanobot_config.json 的 agents.defaults.fallbackModels 读取。

        Returns:
            list[Any]: ModelPresetConfig 列表
        """
        try:
            from nanobot.config.schema import ModelPresetConfig
        except ImportError:
            logger.warning("nanobot-ai 不支持 ModelPresetConfig，跳过 fallback 配置")
            return []

        nano_cfg = self._runner_config.load_nanobot_config()
        fallback_list = (
            nano_cfg.get("agents", {}).get("defaults", {}).get("fallbackModels", [])
        )
        if not fallback_list:
            return []

        presets: list[Any] = []
        for fb in fallback_list:
            model = fb.get("model", "")
            provider = fb.get("provider", "")
            if not model or not provider:
                continue
            preset = ModelPresetConfig(model=model, provider=provider)
            presets.append(preset)

        return presets

    def _create_fallback_provider(self, preset: Any) -> Any:
        """为 fallback 预设创建 Provider 实例

        从 nanobot_config.json 的 providers 读取对应 provider 的 apiKey 和 apiBase。

        Args:
            preset: ModelPresetConfig 实例

        Returns:
            Any: nanobot Provider 实例
        """
        from nanobot.providers.openai_compat_provider import OpenAICompatProvider
        from nanobot.providers.registry import find_by_name

        nano_cfg = self._runner_config.load_nanobot_config()
        providers = nano_cfg.get("providers", {})
        provider_cfg = providers.get(preset.provider, {})

        api_key = provider_cfg.get("apiKey", "")
        base_url = provider_cfg.get("apiBase")
        spec = find_by_name(preset.provider)

        return OpenAICompatProvider(
            api_key=api_key,
            api_base=base_url,
            default_model=preset.model,
            spec=spec,
        )

    def get_agent_defaults(self) -> AgentDefaults:
        """获取Agent默认配置

        从 nanobot_config.json 的 agents.defaults 读取。

        Returns:
            AgentDefaults: Agent默认配置实例
        """
        nano_cfg = self._runner_config.load_nanobot_config()
        defaults = nano_cfg.get("agents", {}).get("defaults", {})

        raw_timezone = self._runner_config.get("timezone")
        timezone = raw_timezone if isinstance(raw_timezone, str) else "UTC"

        return AgentDefaults(
            model=defaults.get("model", ""),
            max_tool_iterations=defaults.get("maxToolIterations", 200),
            context_window_tokens=defaults.get("contextWindowTokens", 200000),
            timezone=timezone,
        )

    def is_available(self) -> bool:
        """检查配置是否可用

        Returns:
            bool: 项目配置是否包含LLM配置
        """
        return self._has_runner_llm_config()

    def close(self) -> None:
        """关闭Provider连接，释放资源"""
        self._provider_instance = None

    # ponytail: 移除了 _get_or_create_nanobot_config / save_nanobot_config /
    # _build_nanobot_config_from_runner / _build_feishu_channel_config /
    # _build_websocket_channel_config / _parse_env_file（v0.32.0 配置物理分离，
    # nanobot_config.json 由 ConfigManager 直接管理）

    def _has_runner_llm_config(self) -> bool:
        """检查项目配置中是否有LLM配置

        Returns:
            bool: 是否存在LLM配置
        """
        try:
            return self._runner_config.has_llm_config()
        except Exception:
            return False

    def _from_nanobot_config(self) -> LLMConfig:
        """从 nanobot_config.json 提取 LLM 配置

        Returns:
            LLMConfig: LLM配置数据类实例
        """
        nano_cfg = self._runner_config.load_nanobot_config()
        providers = nano_cfg.get("providers", {})
        default_provider = providers.get("default", "")
        provider_cfg = providers.get(default_provider, {})

        return LLMConfig(
            provider=default_provider,
            model=nano_cfg.get("agents", {}).get("defaults", {}).get("model", ""),
            api_key=provider_cfg.get("apiKey", ""),
            base_url=provider_cfg.get("apiBase"),
        )


class DynamicProviderRegistry:
    """动态 Provider 注册器

    利用 nanobot 0.2.2 的 create_dynamic_spec() 和 ProvidersConfig.extra="allow" 能力，
    支持运行时注册自定义 OpenAI 兼容 Provider。
    """

    _custom_providers: dict[str, ProviderSpec] = {}
    _provider_metadata: dict[str, dict[str, str]] = {}

    @classmethod
    def register_custom_provider(
        cls,
        name: str,
        api_base: str,
        api_key: str,
        default_model: str,
    ) -> None:
        """注册自定义 OpenAI 兼容 Provider

        Args:
            name: Provider 名称（不能与内置冲突）
            api_base: API 端点
            api_key: API 密钥（存储在 metadata 中，供配置层使用）
            default_model: 默认模型（存储在 metadata 中，供配置层使用）
        """
        builtin_names = {p.name for p in PROVIDERS}
        if name.lower() in builtin_names:
            logger.warning("Provider 名称 '%s' 与内置冲突，拒绝注册", name)
            return

        spec = create_dynamic_spec(name)
        if api_base:
            spec = replace(spec, default_api_base=api_base)

        cls._custom_providers[name] = spec
        cls._provider_metadata[name] = {
            "api_key": api_key,
            "default_model": default_model,
        }
        logger.info("自定义 Provider '%s' 注册成功", name)

    @classmethod
    def list_custom_providers(cls) -> list[str]:
        """列出已注册的自定义 Provider 名称"""
        return list(cls._custom_providers.keys())

    @classmethod
    def get_provider_spec(cls, name: str) -> ProviderSpec | None:
        """获取已注册的 ProviderSpec

        Args:
            name: Provider 名称

        Returns:
            ProviderSpec | None: 已注册的 spec，未注册返回 None
        """
        return cls._custom_providers.get(name)
