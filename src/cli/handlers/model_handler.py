# Model Presets 业务逻辑层
# 封装配置读取，为 CLI 命令提供 Model Presets 查询接口

from __future__ import annotations

from typing import Any

from src.core.base.context import AppContext, AppContextFactory


class ModelHandler:
    """Model Presets 业务逻辑层

    封装配置读取，为 CLI 命令提供 Model Presets 查询接口。

    Attributes:
        context: 应用上下文实例
    """

    def __init__(self, context: AppContext | None = None) -> None:
        if context is None:
            context = AppContextFactory.create()
        self.context = context

    def list_presets(self) -> list[dict[str, Any]]:
        """获取 Model Presets 列表

        从配置文件中读取 model_presets 字段，转换为列表格式返回。
        同时标记 fallback_models 引用的预设。

        Returns:
            list[dict]: 预设列表，每个预设包含 name/provider/model/temperature/is_fallback 等字段
        """
        config = self.context.config
        raw_config = config.load_config()
        presets = raw_config.get("model_presets", {})
        if presets is None:
            return []

        fallback_names = set(raw_config.get("fallback_models") or [])

        result: list[dict[str, Any]] = []
        for name, preset in presets.items():
            result.append(
                {
                    "name": name,
                    "provider": preset.get("provider", ""),
                    "model": preset.get("model", ""),
                    "temperature": preset.get("temperature"),
                    "is_fallback": name in fallback_names,
                }
            )
        return result
