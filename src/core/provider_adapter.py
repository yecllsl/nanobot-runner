from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from src.core.base.exceptions import LLMError, NanobotRunnerError
from src.core.base.logger import get_logger
from src.core.config.llm_config import LLMConfig
from src.core.config.manager import ConfigManager

logger = get_logger(__name__)

_BLOCKED_SETTINGS_PATHS: frozenset[str] = frozenset(
    {
        "/api/settings/update",
        "/api/settings/provider/update",
        "/api/settings/web-search/update",
    }
)

_SETTINGS_UPDATE_BLOCKED_MESSAGE = (
    "Settings updates are managed by nanobot-runner config. "
    "Use 'nanobotrun system init' or edit ~/.nanobot-runner/config.json"
)


def _patch_websocket_settings_api() -> None:
    """拦截 WebUI Settings 写操作，防止写入 ~/.nanobot/config.json

    通过 monkey-patch WebSocketChannel._dispatch_http 方法，
    拦截 3 个设置写端点，返回 403 Forbidden。
    仅在 WebSocket 通道启用时调用。幂等：多次调用安全。
    """
    from nanobot.channels.websocket import (
        WebSocketChannel,
        _http_error,
        _parse_request_path,
    )

    # 幂等保护：已 patch 过则跳过
    if getattr(WebSocketChannel._dispatch_http, "_runner_patched", False):
        return

    _original_dispatch = WebSocketChannel._dispatch_http

    async def _runner_dispatch_http(
        self: WebSocketChannel, connection: Any, request: Any
    ) -> Any:
        got, _ = _parse_request_path(request.path)
        if got in _BLOCKED_SETTINGS_PATHS:
            return _http_error(403, _SETTINGS_UPDATE_BLOCKED_MESSAGE)
        return await _original_dispatch(self, connection, request)

    _runner_dispatch_http._runner_patched = True  # type: ignore[attr-defined]
    WebSocketChannel._dispatch_http = _runner_dispatch_http


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

    def __init__(
        self, runner_config: ConfigManager, *, webui_enabled: bool = False
    ) -> None:
        """初始化配置注入器

        Args:
            runner_config: 项目配置管理器实例
            webui_enabled: 是否启用 WebUI，启用时自动激活 WebSocket 通道
        """
        self._runner_config = runner_config
        self._webui_enabled = webui_enabled
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

        从 ConfigManager 读取 fallback_models 配置，
        转换为底座 ModelPresetConfig 格式。
        跳过 API Key 缺失的条目。

        Returns:
            list[Any]: ModelPresetConfig 列表
        """
        try:
            from nanobot.config.schema import ModelPresetConfig
        except ImportError:
            logger.warning("nanobot-ai 不支持 ModelPresetConfig，跳过 fallback 配置")
            return []

        fallback_list = self._runner_config.get_fallback_models()
        if not fallback_list:
            return []

        presets: list[Any] = []
        for fb in fallback_list:
            api_key = fb.get("api_key")
            if not api_key:
                logger.warning(
                    "备选供应商 '%s' API Key 缺失，跳过",
                    fb.get("provider", "unknown"),
                )
                continue

            preset = ModelPresetConfig(
                model=fb["model"],
                provider=fb["provider"],
            )
            presets.append(preset)

        return presets

    def _create_fallback_provider(self, preset: Any) -> Any:
        """为 fallback 预设创建 Provider 实例

        Args:
            preset: ModelPresetConfig 实例

        Returns:
            Any: nanobot Provider 实例
        """
        from nanobot.providers.openai_compat_provider import OpenAICompatProvider
        from nanobot.providers.registry import find_by_name

        api_key = self._runner_config.get_fallback_api_key(preset.provider)
        spec = find_by_name(preset.provider)

        fb_config = self._runner_config.get_fallback_models()
        base_url: str | None = None
        for fb in fb_config:
            if (
                fb.get("provider") == preset.provider
                and fb.get("model") == preset.model
            ):
                base_url = fb.get("base_url")
                break

        return OpenAICompatProvider(
            api_key=api_key,
            api_base=base_url,
            default_model=preset.model,
            spec=spec,
        )

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

            # 从 config.json 读取 WebSocket 配置节，支持环境变量覆盖
            ws_config = self._runner_config.get_websocket_config()

            # 品牌字段：从 config.json websocket 配置节读取，缺失时使用默认值
            bot_name = ws_config.get("bot_name", "Nanobot-Runner")
            bot_icon = ws_config.get("bot_icon", "🏃‍♂️")
            # unified_session: 启用后 CLI/飞书/WebUI 共享同一会话，默认关闭
            unified_session = ws_config.get("unified_session", False)

            # v0.27.0: 设置 workspace 为项目目录，避免使用默认的 ~/.nanobot
            workspace_path = str(self._runner_config.base_dir / "workspace")

            agents = AgentsConfig(
                defaults={
                    "model": llm_dict.get("model", "gpt-4o-mini"),
                    "bot_name": bot_name,
                    "bot_icon": bot_icon,
                    "unified_session": unified_session,
                    "workspace": workspace_path,
                },
            )

            channels: dict[str, Any] = {}
            self._build_feishu_channel_config(channels)
            self._build_websocket_channel_config(channels, ws_config)

            # WebSocket 通道启用时，拦截 Settings 写操作以保持配置独立性
            if "websocket" in channels:
                _patch_websocket_settings_api()

            # 注入 fallback_models 到 nanobot Config
            runner_config = self._runner_config.load_config()
            fallback_names = runner_config.get("fallback_models", [])
            if fallback_names:
                try:
                    from nanobot.config.schema import InlineFallbackConfig

                    presets_raw = runner_config.get("model_presets", {})
                    fallback_candidates: list[Any] = []
                    for name in fallback_names:
                        preset_data = presets_raw.get(name, {})
                        provider = preset_data.get("provider", "")
                        model = preset_data.get("model", "")
                        if provider and model:
                            fallback_candidates.append(
                                InlineFallbackConfig(
                                    model=model,
                                    provider=provider,
                                )
                            )
                    if fallback_candidates:
                        agents.defaults.fallback_models = fallback_candidates
                except ImportError:
                    logger.debug(
                        "nanobot-ai 不支持 InlineFallbackConfig，跳过 fallback 注入"
                    )

            config = Config(
                providers=providers,
                agents=agents,
                channels=channels,
            )

            self._nanobot_config = config
            return config
        except (ImportError, NanobotRunnerError) as e:
            logger.debug(f"从项目配置构建nanobot配置失败: {e}")
            raise LLMError(
                f"无法构建nanobot配置: {e}",
                recovery_suggestion="请确认已安装nanobot-ai",
            ) from e

    def _build_feishu_channel_config(self, channels: dict[str, Any]) -> None:
        """构建飞书通道配置

        从环境变量和 .env.local 文件读取飞书凭据，
        配置有效时写入 channels["feishu"]。

        Args:
            channels: 通道配置字典，本方法会向其中写入 feishu 键
        """
        feishu_app_id = os.getenv("NANOBOT_FEISHU_APP_ID")
        feishu_app_secret = os.getenv("NANOBOT_FEISHU_APP_SECRET")
        feishu_receive_id = os.getenv("NANOBOT_FEISHU_RECEIVE_ID")

        if not (feishu_app_id and feishu_app_secret):
            env_file = Path.home() / ".nanobot-runner" / ".env.local"
            if env_file.exists():
                env_vars = self._parse_env_file(env_file)
                feishu_app_id = feishu_app_id or env_vars.get("NANOBOT_FEISHU_APP_ID")
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

    def _build_websocket_channel_config(
        self, channels: dict[str, Any], ws_config: dict[str, Any]
    ) -> None:
        """构建WebSocket通道配置

        当 webui_enabled=True 或 config.json 中 websocket.enabled=True 时激活，
        将配置写入 channels["websocket"]。

        Args:
            channels: 通道配置字典，本方法会向其中写入 websocket 键
            ws_config: 从 config.json websocket 配置节读取的字典
        """
        ws_enabled_in_config = ws_config.get("enabled", False)
        if self._webui_enabled or ws_enabled_in_config:
            channels["websocket"] = {
                "enabled": True,
                "host": ws_config.get("host", "127.0.0.1"),
                "port": ws_config.get("port", 8765),
                "path": ws_config.get("path", "/"),
                "token": ws_config.get("token", ""),
                "token_issue_path": ws_config.get("token_issue_path", ""),
                "token_issue_secret": ws_config.get("token_issue_secret", ""),
                "token_ttl_s": ws_config.get("token_ttl_s", 300),
                "websocket_requires_token": ws_config.get(
                    "websocket_requires_token", True
                ),
                "allow_from": ws_config.get("allow_from", ["*"]),
                "streaming": ws_config.get("streaming", True),
                "max_message_bytes": ws_config.get("max_message_bytes", 37748736),
                "ping_interval_s": ws_config.get("ping_interval_s", 20.0),
                "ping_timeout_s": ws_config.get("ping_timeout_s", 20.0),
                "ssl_certfile": ws_config.get("ssl_certfile", ""),
                "ssl_keyfile": ws_config.get("ssl_keyfile", ""),
            }

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
        except (NanobotRunnerError, OSError) as e:
            logger.debug(f"解析 .env 文件失败: {e}")
        return env_vars

    def _has_runner_llm_config(self) -> bool:
        """检查项目配置中是否有LLM配置

        Returns:
            bool: 是否存在LLM配置
        """
        try:
            return self._runner_config.has_llm_config()
        except (NanobotRunnerError, Exception):
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
