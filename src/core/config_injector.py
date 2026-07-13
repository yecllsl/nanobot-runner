"""配置注入器 - 通过 SDK 配置注入替代 monkey-patch

替代 _patch_websocket_settings_api() 机制，将 RunFlowAgent 自有配置
（~/.nanobot-runner/config.json）注入 nanobot 运行时。

注意：基于 nanobot-ai 0.2.2 实际 Schema 调研：
- 顶层 Config 字段：agents / channels / transcription / providers / api / gateway / tools / model_presets
- 不存在 WebSocketConfig / WebUIConfig（设计文档假设有误）
- runner_config 中的 websocket / webui 字段为 RunFlowAgent 自有概念，不直接映射到 nanobot Config
- ProvidersConfig 已开启 extra="allow"，支持任意 provider 名称
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ConfigInjectionError(Exception):
    """配置注入失败异常"""


class ConfigInjector:
    """通过 SDK 配置注入替代 monkey-patch

    将 RunFlowAgent 配置（~/.nanobot-runner/config.json）转换为
    nanobot Config 对象，替代运行时 patch load_config/save_config。
    """

    def __init__(self, config_path: Path):
        """初始化配置注入器

        Args:
            config_path: RunFlowAgent 配置文件路径
        """
        self.config_path = config_path

    def build_nanobot_config(self, runner_config: dict[str, Any]) -> Any:
        """构建 nanobot Config 对象

        将 RunFlowAgent 自有配置字典映射为 nanobot 0.2.2 Config 实例。
        仅映射 nanobot Config 实际支持的字段；runner_config 中的
        websocket / webui 等 RunFlowAgent 私有字段不传递给 nanobot。

        Args:
            runner_config: RunFlowAgent 配置字典

        Returns:
            Config: nanobot 配置对象

        Raises:
            ConfigInjectionError: 配置构建失败（缺少必要字段或 Schema 不匹配）
        """
        try:
            from nanobot.config.schema import (
                AgentDefaults,
                AgentsConfig,
                Config,
                ProviderConfig,
                ProvidersConfig,
                TranscriptionConfig,
            )

            # 校验必要字段：agents.defaults 是 Runner 配置的最小要求
            agents_section = runner_config.get("agents")
            if not isinstance(agents_section, dict) or "defaults" not in agents_section:
                raise ConfigInjectionError(
                    "缺少必要字段 agents.defaults，请检查 ~/.nanobot-runner/config.json"
                )

            agents_defaults = agents_section["defaults"]
            providers_raw = runner_config.get("providers", {})

            # 构建 Provider 配置：ProvidersConfig 开启了 extra="allow"，
            # 支持任意 provider 名称（含内置与自定义）
            providers_kwargs: dict[str, Any] = {}
            for name, prov_cfg in providers_raw.items():
                providers_kwargs[name] = ProviderConfig(
                    api_key=prov_cfg.get("api_key"),
                    api_base=prov_cfg.get("api_base"),
                )

            # 处理 transcription 配置（nanobot 0.2.2 新增）
            # 用户未配置时使用 nanobot 默认值（enabled=True）
            transcription_raw = runner_config.get("transcription")
            transcription_cfg = None
            if isinstance(transcription_raw, dict):
                transcription_cfg = TranscriptionConfig(
                    enabled=transcription_raw.get("enabled", False),
                    provider=transcription_raw.get("provider"),
                    model=transcription_raw.get("model"),
                    language=transcription_raw.get("language"),
                    max_duration_sec=transcription_raw.get("max_duration_sec", 120),
                    max_upload_mb=transcription_raw.get("max_upload_mb", 25),
                )

            # 仅传递 nanobot Config 实际支持的字段；websocket / webui
            # 等 RunFlowAgent 私有字段不映射（nanobot 0.2.2 无对应 Schema）
            config_kwargs: dict[str, Any] = {
                "agents": AgentsConfig(defaults=AgentDefaults(**agents_defaults)),
                "providers": ProvidersConfig(**providers_kwargs)
                if providers_kwargs
                else ProvidersConfig(),
            }
            if transcription_cfg is not None:
                config_kwargs["transcription"] = transcription_cfg

            config = Config(**config_kwargs)

            logger.debug("成功构建 nanobot Config")
            return config

        except ConfigInjectionError:
            # 校验类异常直接向上抛出，不再包装
            raise
        except Exception as e:
            logger.error("配置注入失败: %s", e)
            raise ConfigInjectionError(
                f"无法构建 nanobot Config: {e}。请检查 ~/.nanobot-runner/config.json"
            ) from e

    def save_runner_config(self, config: dict[str, Any]) -> None:
        """保存 RunFlowAgent 配置

        Args:
            config: 配置字典
        """
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        logger.debug("配置已保存到 %s", self.config_path)

    def resolve_webui_dist(self) -> Path | None:
        """解析 WebUI dist 目录

        优先使用 RunFlowAgent 自有 dist（项目根/webui/dist），
        回退到 nanobot 内置 dist（nanobot/web/dist）。

        Returns:
            Path | None: dist 目录路径，不存在则返回 None
        """
        # 优先 RunFlowAgent 自有 dist
        custom_dist = Path(__file__).parent.parent.parent / "webui" / "dist"
        if custom_dist.exists():
            return custom_dist

        # 回退 nanobot 内置 dist
        try:
            import nanobot.web as web_pkg

            nanobot_dist = Path(web_pkg.__file__).parent / "dist"
            if nanobot_dist.exists():
                return nanobot_dist
        except (ImportError, AttributeError):
            pass

        return None
