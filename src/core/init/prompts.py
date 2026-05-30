from typing import Any

from src import __version__
from src.core.base.logger import get_logger

logger = get_logger(__name__)


class InitPrompts:
    """交互式配置向导

    使用 Questionary 库实现交互式 CLI 向导，引导用户填写配置信息。
    当 Questionary 不可用时，回退到默认值模式。
    """

    @staticmethod
    def run_llm_provider_wizard() -> dict[str, str]:
        """运行 LLM Provider 配置向导

        Returns:
            dict[str, str]: LLM 配置字典
        """
        try:
            import questionary

            provider = questionary.select(
                "选择 LLM Provider:",
                choices=[
                    "openai",
                    "anthropic",
                    "deepseek",
                    "zhipu",
                    "siliconflow",
                    "other",
                ],
                default="openai",
            ).ask()

            if provider is None:
                return InitPrompts._default_llm_config()

            model = questionary.text(
                "输入模型名称:",
                default=InitPrompts._default_model_for_provider(provider),
            ).ask()

            api_key = questionary.password(
                "输入 API Key:",
            ).ask()

            base_url = questionary.text(
                "输入 Base URL（可选，留空使用默认）:",
                default="",
            ).ask()

            result = {
                "NANOBOT_LLM_PROVIDER": provider,
                "NANOBOT_LLM_MODEL": model or "gpt-4o-mini",
                "NANOBOT_LLM_API_KEY": api_key or "",
                "NANOBOT_LLM_BASE_URL": base_url or "",
            }

            fallback_result = InitPrompts.run_fallback_wizard(provider or "openai")
            result.update(fallback_result)

            return result

        except ImportError:
            logger.warning("questionary 未安装，使用默认 LLM 配置")
            return InitPrompts._default_llm_config()

    @staticmethod
    def run_business_config_wizard() -> dict[str, Any]:
        """运行业务参数配置向导

        Returns:
            dict[str, Any]: 业务配置字典
        """
        try:
            import questionary

            timezone = questionary.select(
                "选择时区:",
                choices=["Asia/Shanghai", "Asia/Tokyo", "America/New_York", "UTC"],
                default="Asia/Shanghai",
            ).ask()

            return {
                "timezone": timezone or "Asia/Shanghai",
            }

        except ImportError:
            return {"timezone": "Asia/Shanghai"}

    @staticmethod
    def run_feishu_config_wizard() -> dict[str, str]:
        """运行飞书通知配置向导（可选）

        Returns:
            dict[str, str]: 飞书配置字典
        """
        try:
            import questionary

            enable = questionary.confirm(
                "是否启用飞书通知？（可选）",
                default=False,
            ).ask()

            if not enable:
                return {"NANOBOT_AUTO_PUSH_FEISHU": "false"}

            app_id = questionary.text("输入飞书 App ID:").ask()
            app_secret = questionary.password("输入飞书 App Secret:").ask()
            receive_id = questionary.text("输入飞书接收者 ID:").ask()

            return {
                "NANOBOT_AUTO_PUSH_FEISHU": "true",
                "NANOBOT_FEISHU_APP_ID": app_id or "",
                "NANOBOT_FEISHU_APP_SECRET": app_secret or "",
                "NANOBOT_FEISHU_RECEIVE_ID": receive_id or "",
            }

        except ImportError:
            return {"NANOBOT_AUTO_PUSH_FEISHU": "false"}

    @staticmethod
    def run_full_wizard(
        skip_optional: bool = False,
        agent_mode: bool = True,
    ) -> dict[str, Any]:
        """运行完整的配置向导

        Args:
            skip_optional: 是否跳过可选项
            agent_mode: 是否配置LLM（True=Agent模式，False=数据模式）

        Returns:
            dict[str, Any]: 完整配置字典，包含 config 和 env_vars
        """
        llm_env: dict[str, str] = {}
        if agent_mode:
            llm_env = InitPrompts.run_llm_provider_wizard()

        business_config = InitPrompts.run_business_config_wizard()

        feishu_env: dict[str, str] = {}
        if not skip_optional:
            feishu_env = InitPrompts.run_feishu_config_wizard()

        config: dict[str, Any] = {
            "version": __version__,
            **business_config,
            "auto_push_feishu": feishu_env.get("NANOBOT_AUTO_PUSH_FEISHU", "false")
            == "true",
        }

        if agent_mode:
            config["llm_provider"] = llm_env.get("NANOBOT_LLM_PROVIDER", "openai")
            config["llm_model"] = llm_env.get("NANOBOT_LLM_MODEL", "gpt-4o-mini")
            base_url = llm_env.get("NANOBOT_LLM_BASE_URL", "")
            if base_url:
                config["llm_base_url"] = base_url

            # 注入 fallback 配置到 config.json
            _fb_raw: list[str] | str = llm_env.pop("_fallback_models", [])
            _mp_raw: dict[str, Any] | str = llm_env.pop("_model_presets", {})
            fallback_models: list[str] = _fb_raw if isinstance(_fb_raw, list) else []
            model_presets: dict[str, Any] = _mp_raw if isinstance(_mp_raw, dict) else {}
            if fallback_models:
                config["fallback_models"] = fallback_models
            if model_presets:
                config["model_presets"] = model_presets

            config["tools"] = InitPrompts._default_tools_config()

        env_vars = {**llm_env, **feishu_env}

        return {"config": config, "env_vars": env_vars}

    @staticmethod
    def _default_llm_config() -> dict[str, str]:
        """获取默认 LLM 配置

        Returns:
            dict[str, str]: 默认 LLM 配置字典
        """
        return {
            "NANOBOT_LLM_PROVIDER": "openai",
            "NANOBOT_LLM_MODEL": "gpt-4o-mini",
            "NANOBOT_LLM_API_KEY": "",
            "NANOBOT_LLM_BASE_URL": "",
        }

    @staticmethod
    def _default_model_for_provider(provider: str) -> str:
        """根据 Provider 获取默认模型

        Args:
            provider: LLM Provider 名称

        Returns:
            str: 默认模型名称
        """
        defaults: dict[str, str] = {
            "openai": "gpt-4o-mini",
            "anthropic": "claude-3-5-sonnet-20241022",
            "deepseek": "deepseek-chat",
            "zhipu": "glm-4.7-flash",
            "siliconflow": "Qwen/Qwen3-235B-A22B",
        }
        return defaults.get(provider, "gpt-4o-mini")

    @staticmethod
    def _generate_preset_name(provider: str, model: str) -> str:
        """生成预设名

        格式: {provider}-{model简短标识}
        取 model 的最后一段（按 / 分割），再截取前两个 - 分隔段。

        Args:
            provider: 供应商名称
            model: 模型名称

        Returns:
            str: 预设名
        """
        short_model = model.split("/")[-1]
        segments = short_model.split("-")
        if len(segments) >= 3:
            ident = "-".join(segments[:3])
        elif len(segments) >= 2:
            ident = "-".join(segments[:2])
        else:
            ident = segments[0]
        return f"{provider}-{ident}"

    @staticmethod
    def run_fallback_wizard(primary_provider: str) -> dict[str, Any]:
        """运行备选供应商配置向导

        交互式引导用户添加一个或多个备选供应商，
        当主供应商故障时自动故障转移。

        Args:
            primary_provider: 主供应商名称

        Returns:
            dict[str, Any]: 包含 _model_presets / _fallback_models / 环境变量
        """
        result: dict[str, Any] = {"_model_presets": {}, "_fallback_models": []}

        try:
            import questionary
        except ImportError:
            logger.warning("questionary 未安装，跳过备选供应商配置")
            return result

        add_fallback = questionary.confirm(
            "是否配置备选供应商（主供应商故障时自动切换）？",
            default=False,
        ).ask()

        if not add_fallback:
            return result

        available_providers = [
            "nvidia",
            "openrouter",
            "zhipu",
            "siliconflow",
            "deepseek",
            "other",
        ]
        filtered = [p for p in available_providers if p != primary_provider]

        while True:
            provider = questionary.select(
                "选择备选供应商:",
                choices=filtered,
            ).ask()

            if provider is None:
                break

            if provider == "other":
                provider = questionary.text("输入供应商名称:").ask()
                if not provider:
                    break

            model = questionary.text(
                "输入模型名称:",
                default=InitPrompts._default_model_for_provider(provider),
            ).ask()

            base_url = questionary.text(
                "输入 Base URL（可选，留空使用默认）:",
                default="",
            ).ask()

            api_key = questionary.password(
                f"输入 {provider} API Key:",
            ).ask()

            if not api_key:
                logger.warning("API Key 为空，跳过此备选供应商")
                continue

            preset_name = InitPrompts._generate_preset_name(
                provider, model or "unknown"
            )

            result["_model_presets"][preset_name] = {
                "provider": provider,
                "model": model,
                "base_url": base_url or None,
            }
            result["_fallback_models"].append(preset_name)
            result[f"NANOBOT_LLM_API_KEY_{provider.upper()}"] = api_key

            add_more = questionary.confirm(
                "是否继续添加备选供应商？",
                default=False,
            ).ask()

            if not add_more:
                break

        return result

    @staticmethod
    def _default_tools_config() -> dict[str, Any]:
        """获取默认工具生态配置

        包含四个默认MCP服务器：Chrome DevTools、天气、地图、COROS数据同步。

        Returns:
            dict[str, Any]: 默认工具配置字典
        """
        return {
            "mcp_servers": {
                "Chrome DevTools MCP": {
                    "command": "npx",
                    "args": ["-y", "chrome-devtools-mcp@latest", "--autoConnect"],
                    "env": {},
                },
                "weather": {
                    "type": "stdio",
                    "command": "npx",
                    "args": ["-y", "@dangahagan/weather-mcp"],
                    "tool_timeout": 30,
                    "enabled_tools": ["*"],
                },
                "osm": {
                    "type": "stdio",
                    "command": "uvx",
                    "args": ["osm-mcp-server"],
                    "tool_timeout": 30,
                    "enabled_tools": ["*"],
                },
                "coros": {
                    "type": "stdio",
                    "command": "npx",
                    "args": ["-y", "coros-cli", "mcp"],
                    "tool_timeout": 30,
                    "enabled_tools": ["*"],
                },
            },
        }
