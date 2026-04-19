from typing import Any

from src.core.logger import get_logger

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
                choices=["openai", "anthropic", "deepseek", "zhipu", "other"],
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

            return {
                "NANOBOT_LLM_PROVIDER": provider,
                "NANOBOT_LLM_MODEL": model or "gpt-4o-mini",
                "NANOBOT_LLM_API_KEY": api_key or "",
                "NANOBOT_LLM_BASE_URL": base_url or "",
            }

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
            "version": "0.9.5",
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
            "zhipu": "glm-4-flash",
        }
        return defaults.get(provider, "gpt-4o-mini")
