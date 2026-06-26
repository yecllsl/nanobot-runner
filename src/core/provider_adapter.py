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


def _patch_websocket_settings_api() -> None:
    """代理 nanobot 配置读写到项目配置

    通过 monkey-patch nanobot.config.loader 的 load_config/save_config 源函数，
    及所有已导入该函数的 webui 模块本地引用（settings_api/mcp_presets_api/cli_apps_api），
    让所有调用者读写项目配置（~/.nanobot-runner/config.json）。

    - load_config: 直接构造默认 Config，用项目配置覆盖 LLM 字段
      （不读取项目配置文件，避免 Pydantic 验证错误）
    - save_config: 从 nanobot Config 提取 LLM 字段，写入项目 ConfigManager

    仅在 WebSocket 通道启用时调用。幂等：多次调用安全。
    """
    from nanobot.config import loader as nanobot_loader

    # 幂等保护：已 patch 过则跳过（用 is True 避免 MagicMock 误判）
    if getattr(nanobot_loader.load_config, "_runner_patched", False) is True:
        return

    def _runner_load_config(config_path: Any = None) -> Any:
        """返回默认 Config，用项目配置覆盖 LLM 字段

        不调用原始 load_config，避免读取项目配置文件触发 Pydantic 验证错误。
        同时从环境变量恢复非默认供应商的 api_key/api_base。
        """
        from nanobot.config.schema import Config

        config = Config()
        try:
            llm = ConfigManager().get_llm_config()
            if llm.get("model"):
                config.agents.defaults.model = llm["model"]
            if llm.get("provider"):
                config.agents.defaults.provider = llm["provider"]
            provider_name = llm.get("provider", "")
            if provider_name:
                provider_config = getattr(config.providers, provider_name, None)
                if provider_config:
                    if llm.get("api_key"):
                        provider_config.api_key = llm["api_key"]
                    if llm.get("base_url"):
                        provider_config.api_base = llm["base_url"]

            # 从环境变量恢复非默认供应商的 api_key/api_base
            # （update_provider_settings 保存到 NANOBOT_LLM_API_KEY_{UPPER}）
            for attr_name in dir(config.providers):
                if attr_name.startswith("_") or attr_name == provider_name:
                    continue
                pc = getattr(config.providers, attr_name, None)
                if pc is None or not hasattr(pc, "api_key"):
                    continue
                upper = attr_name.upper()
                pk = os.environ.get(f"NANOBOT_LLM_API_KEY_{upper}")
                if pk:
                    pc.api_key = pk
                pb = os.environ.get(f"NANOBOT_LLM_BASE_URL_{upper}")
                if pb:
                    pc.api_base = pb

            # 从项目配置 websocket 节读取 bot_name/bot_icon
            ws_config = ConfigManager().get_websocket_config()
            if ws_config.get("bot_name"):
                config.agents.defaults.bot_name = ws_config["bot_name"]
            if ws_config.get("bot_icon"):
                config.agents.defaults.bot_icon = ws_config["bot_icon"]

            # 从项目配置读取时区，覆盖 nanobot 默认 UTC
            timezone = ConfigManager().get("timezone")
            if isinstance(timezone, str) and timezone:
                config.agents.defaults.timezone = timezone

            # 强制 workspace 指向项目目录，避免 nanobot 默认的 ~/.nanobot
            config.agents.defaults.workspace = str(ConfigManager().base_dir)
        except Exception as e:
            logger.debug(f"从项目配置同步到 nanobot Config 失败: {e}")
        return config

    def _runner_save_config(config: Any, config_path: Any = None) -> None:
        """从 nanobot Config 提取 LLM 配置，写入项目配置

        1. 默认供应商（defaults.provider）→ ConfigManager.save_llm_config() + os.environ
        2. 其他供应商的 api_key/api_base → .env.local（NANOBOT_LLM_API_KEY_{UPPER}）
        """
        try:
            defaults = config.agents.defaults
            provider_name = defaults.provider
            provider_config = getattr(config.providers, provider_name, None)
            api_key = provider_config.api_key if provider_config else None
            api_base = provider_config.api_base if provider_config else None
            ConfigManager().save_llm_config(
                provider=provider_name,
                model=defaults.model,
                base_url=api_base,
                api_key=api_key,
            )
            # ponytail: 非敏感配置 (provider/model/base_url) 已写入 config.json，
            # 不再写入环境变量。仅同步 API Key 到进程环境变量确保 get_llm_config() 可读到。
            if api_key:
                os.environ["NANOBOT_LLM_API_KEY"] = api_key

            # 保存非默认供应商的 api_key 到 .env.local
            # （update_provider_settings 可能配置了其他供应商）
            # ponytail: api_base 是非敏感配置，不再写入 .env.local/环境变量
            provider_env: dict[str, str] = {}
            for attr_name in dir(config.providers):
                if attr_name.startswith("_"):
                    continue
                pc = getattr(config.providers, attr_name, None)
                if pc is None or not hasattr(pc, "api_key"):
                    continue
                # 跳过默认供应商（已通过 save_llm_config 处理）
                if attr_name == provider_name:
                    continue
                pk = getattr(pc, "api_key", None)
                upper = attr_name.upper()
                if pk and isinstance(pk, str):
                    env_key = f"NANOBOT_LLM_API_KEY_{upper}"
                    provider_env[env_key] = pk
                    os.environ[env_key] = pk

            if provider_env:
                from src.core.config.env_manager import EnvManager

                EnvManager(
                    env_file=ConfigManager().base_dir / ".env.local"
                ).save_env_file(provider_env)

            # 保存 bot_name/bot_icon 到项目配置 websocket 节
            # 保存 timezone 到项目配置顶层，确保 WebUI 修改后持久化
            cm = ConfigManager()
            proj_config = cm.load_config()

            bot_name = getattr(defaults, "bot_name", None)
            bot_icon = getattr(defaults, "bot_icon", None)
            if bot_name or bot_icon:
                ws = proj_config.get("websocket", {})
                if not isinstance(ws, dict):
                    ws = {}
                if bot_name:
                    ws["bot_name"] = bot_name
                if bot_icon:
                    ws["bot_icon"] = bot_icon
                proj_config["websocket"] = ws

            timezone = getattr(defaults, "timezone", None)
            if isinstance(timezone, str) and proj_config.get("timezone") != timezone:
                proj_config["timezone"] = timezone

            cm.save_config(proj_config)

            logger.info(
                "WebUI 设置已同步到项目配置: provider=%s, model=%s, timezone=%s",
                provider_name,
                defaults.model,
                proj_config.get("timezone", "UTC"),
            )
        except Exception as e:
            logger.warning(f"从 nanobot Config 同步到项目配置失败: {e}")

    _runner_load_config._runner_patched = True  # type: ignore[attr-defined]

    # patch 源函数（影响函数内导入和直接调用，如 websocket.py 的 _default_model_name_from_config）
    nanobot_loader.load_config = _runner_load_config
    nanobot_loader.save_config = _runner_save_config

    # patch 已导入的 webui 模块本地引用（模块级 from ... import 绑定的引用不会被源函数 patch 影响）
    import importlib

    for module_name in (
        "nanobot.webui.settings_api",
        "nanobot.webui.mcp_presets_api",
        "nanobot.webui.cli_apps_api",
    ):
        try:
            module: Any = importlib.import_module(module_name)
            if hasattr(module, "load_config"):
                module.load_config = _runner_load_config
            if hasattr(module, "save_config"):
                module.save_config = _runner_save_config
        except ImportError:
            pass


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
            webui_enabled: 是否启用 WebUI，启用时自动激活 WebSocket 通道
        """
        self._runner_config = runner_config
        self._webui_enabled = webui_enabled
        self._nanobot_config: Any | None = None
        self._provider_instance: Any | None = None

    def get_llm_config(self) -> LLMConfig:
        """获取LLM配置

        从项目配置读取，未配置时抛出异常。

        Returns:
            LLMConfig: LLM配置数据类实例

        Raises:
            LLMError: 未配置LLM时抛出
        """
        if self._has_runner_llm_config():
            return self._from_runner_config()
        raise LLMError(
            "未配置LLM，请运行 'nanobotrun system init' 完成配置",
            recovery_suggestion="运行 nanobotrun system init 配置LLM",
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
        # 从项目配置读取时区，未配置或类型异常时回退到 UTC
        raw_timezone = self._runner_config.get("timezone")
        timezone = raw_timezone if isinstance(raw_timezone, str) else "UTC"
        return AgentDefaults(
            model=llm_config.model,
            max_tool_iterations=llm_config.max_iterations,
            context_window_tokens=llm_config.context_window_tokens,
            context_block_limit=llm_config.context_block_limit,
            max_tool_result_chars=llm_config.max_tool_result_chars,
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
            workspace_path = str(self._runner_config.base_dir)

            # 从项目配置读取时区，仅当为有效字符串时才覆盖 nanobot 默认 UTC
            timezone = self._runner_config.get("timezone")
            timezone_kwarg = {"timezone": timezone} if isinstance(timezone, str) else {}

            agents = AgentsConfig(
                defaults={
                    "model": llm_dict.get("model", "gpt-4o-mini"),
                    "bot_name": bot_name,
                    "bot_icon": bot_icon,
                    "unified_session": unified_session,
                    "workspace": workspace_path,
                    **timezone_kwarg,
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

            # 注入 model_presets 到 nanobot Config（v0.30.0: nanobot-ai 0.2.1 运行时模型切换）
            model_presets_dict: dict[str, Any] = {}
            try:
                from nanobot.config.schema import ModelPresetConfig as _MPC

                presets_raw = runner_config.get("model_presets", {})
                for preset_name, preset_data in presets_raw.items():
                    if not isinstance(preset_data, dict):
                        continue
                    # config.json 使用 snake_case，ModelPresetConfig 使用 camelCase
                    model_presets_dict[preset_name] = _MPC(
                        model=preset_data.get("model", ""),
                        provider=preset_data.get("provider", "auto"),
                        maxTokens=preset_data.get(
                            "maxTokens",
                            preset_data.get("max_tokens", 8192),
                        ),
                        contextWindowTokens=preset_data.get(
                            "contextWindowTokens",
                            preset_data.get("context_window_tokens", 65536),
                        ),
                        temperature=preset_data.get("temperature", 0.1),
                        reasoningEffort=preset_data.get(
                            "reasoningEffort",
                            preset_data.get("reasoning_effort", None),
                        ),
                        label=preset_data.get("label", None),
                    )
            except ImportError:
                logger.debug(
                    "nanobot-ai 不支持 ModelPresetConfig，跳过 model_presets 注入"
                )

            # 注入 tools 配置到 nanobot Config（v0.30.0: nanobot-ai 0.2.1 CLI Apps + MCP）
            tools_config_obj: Any = None
            try:
                from nanobot.config.schema import (
                    CliAppsToolConfig as _CliAppsCfg,
                )
                from nanobot.config.schema import (
                    MCPServerConfig as _MCPServerCfg,
                )
                from nanobot.config.schema import (
                    ToolsConfig as _ToolsCfg,
                )

                tools_section = runner_config.get("tools", {})

                # 构建 cli_apps 配置
                cli_apps_raw = tools_section.get("cli_apps", {})
                cli_apps_cfg = _CliAppsCfg(
                    enable=cli_apps_raw.get("enable", True),
                    installTimeout=cli_apps_raw.get(
                        "installTimeout",
                        cli_apps_raw.get("install_timeout", 300),
                    ),
                    runTimeout=cli_apps_raw.get(
                        "runTimeout",
                        cli_apps_raw.get("run_timeout", 60),
                    ),
                    catalogTtlSeconds=cli_apps_raw.get(
                        "catalogTtlSeconds",
                        cli_apps_raw.get("catalog_ttl_seconds", 3600),
                    ),
                )

                # 构建 mcp_servers 配置
                mcp_servers_raw = tools_section.get("mcp_servers", {})
                mcp_servers_dict: dict[str, Any] = {}
                for server_name, server_data in mcp_servers_raw.items():
                    if not isinstance(server_data, dict):
                        continue
                    mcp_servers_dict[server_name] = _MCPServerCfg(
                        type=server_data.get("type", None),
                        command=server_data.get("command", ""),
                        args=server_data.get("args", []),
                        env=server_data.get("env", {}),
                        cwd=server_data.get("cwd", ""),
                        url=server_data.get("url", ""),
                        headers=server_data.get("headers", {}),
                        toolTimeout=server_data.get(
                            "toolTimeout",
                            server_data.get("tool_timeout", 30),
                        ),
                        enabledTools=server_data.get(
                            "enabledTools",
                            server_data.get("enabled_tools", []),
                        ),
                    )

                tools_config_obj = _ToolsCfg(
                    cliApps=cli_apps_cfg,
                    mcpServers=mcp_servers_dict,
                )
            except ImportError:
                logger.debug("nanobot-ai 不支持 ToolsConfig，跳过 tools 配置注入")

            config = Config(
                providers=providers,
                agents=agents,
                channels=channels,
                model_presets=model_presets_dict,
                **({"tools": tools_config_obj} if tools_config_obj is not None else {}),
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
