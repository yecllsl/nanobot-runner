# MyTool集成模块
# 集成nanobot-ai的MyTool能力，提供自反思和参数调优
# MyTool配置在config.json的tools.my字段中

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class MyToolIntegration:
    """MyTool集成管理器

    集成nanobot-ai的MyTool能力，提供：
    - enable_self_reflection: 启用自反思能力
    - enable_parameter_tuning: 启用参数调优
    - get_reflection_report: 获取自反思报告

    MyTool配置存储在config.json的tools.my字段中：
    {
        "tools": {
            "my": {
                "enable": true,
                "allow_set": true
            }
        }
    }

    Attributes:
        config_path: config.json文件路径
    """

    MYTOOL_CONFIG_KEY = "my"
    TOOLS_CONFIG_KEY = "tools"

    def __init__(self, config_path: Path) -> None:
        """初始化MyTool集成

        Args:
            config_path: config.json路径
        """
        self.config_path = config_path

    def enable_self_reflection(self) -> bool:
        """启用自反思能力

        在config.json中设置tools.my.enable=true，
        使AI Agent具备自我检查和反思能力。

        Returns:
            bool: 是否启用成功
        """
        return self._update_mytool_config(enable=True, allow_set=True)

    def enable_parameter_tuning(self) -> bool:
        """启用参数调优

        在config.json中设置tools.my.allow_set=true，
        允许AI Agent自行调整参数以优化输出。

        Returns:
            bool: 是否启用成功
        """
        return self._update_mytool_config(allow_set=True)

    def disable_self_reflection(self) -> bool:
        """禁用自反思能力

        Returns:
            bool: 是否禁用成功
        """
        return self._update_mytool_config(enable=False)

    def disable_parameter_tuning(self) -> bool:
        """禁用参数调优

        Returns:
            bool: 是否禁用成功
        """
        return self._update_mytool_config(allow_set=False)

    def get_reflection_report(self) -> dict[str, Any]:
        """获取自反思报告

        返回MyTool的当前配置状态和自反思能力信息。

        Returns:
            dict: 自反思报告，包含配置状态和能力描述
        """
        config = self._load_config()
        my_config = self._get_my_config(config)

        return {
            "self_reflection_enabled": my_config.get("enable", False),
            "parameter_tuning_enabled": my_config.get("allow_set", False),
            "config_path": str(self.config_path),
            "capabilities": self._describe_capabilities(my_config),
        }

    def is_enabled(self) -> bool:
        """检查MyTool是否启用

        Returns:
            bool: MyTool是否启用
        """
        config = self._load_config()
        my_config = self._get_my_config(config)
        return my_config.get("enable", False)

    def is_parameter_tuning_enabled(self) -> bool:
        """检查参数调优是否启用

        Returns:
            bool: 参数调优是否启用
        """
        config = self._load_config()
        my_config = self._get_my_config(config)
        return my_config.get("allow_set", False)

    def _update_mytool_config(
        self,
        enable: bool | None = None,
        allow_set: bool | None = None,
    ) -> bool:
        """更新MyTool配置

        Args:
            enable: 是否启用自反思（可选）
            allow_set: 是否允许参数调优（可选）

        Returns:
            bool: 是否更新成功
        """
        try:
            config = self._load_config()

            if self.TOOLS_CONFIG_KEY not in config:
                config[self.TOOLS_CONFIG_KEY] = {}
            if self.MYTOOL_CONFIG_KEY not in config[self.TOOLS_CONFIG_KEY]:
                config[self.TOOLS_CONFIG_KEY][self.MYTOOL_CONFIG_KEY] = {}

            my_config = config[self.TOOLS_CONFIG_KEY][self.MYTOOL_CONFIG_KEY]

            if enable is not None:
                my_config["enable"] = enable
            if allow_set is not None:
                my_config["allow_set"] = allow_set

            self._save_config(config)
            logger.info(
                f"MyTool配置已更新: enable={my_config.get('enable')}, "
                f"allow_set={my_config.get('allow_set')}"
            )
            return True

        except Exception as e:
            logger.error(f"更新MyTool配置失败: {e}")
            return False

    def _load_config(self) -> dict[str, Any]:
        """加载配置文件

        Returns:
            dict: 配置字典
        """
        if not self.config_path.exists():
            return {}

        with open(self.config_path, encoding="utf-8") as f:
            return json.load(f)

    def _save_config(self, config: dict[str, Any]) -> None:
        """保存配置文件

        Args:
            config: 配置字典
        """
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    @staticmethod
    def _get_my_config(config: dict[str, Any]) -> dict[str, Any]:
        """从配置中获取MyTool配置

        Args:
            config: 完整配置字典

        Returns:
            dict: MyTool配置字典
        """
        return config.get("tools", {}).get("my", {})

    @staticmethod
    def _describe_capabilities(my_config: dict[str, Any]) -> list[str]:
        """描述MyTool当前启用的能力

        Args:
            my_config: MyTool配置

        Returns:
            list[str]: 能力描述列表
        """
        capabilities: list[str] = []

        if my_config.get("enable", False):
            capabilities.append("自反思: AI可自我检查建议质量")
        if my_config.get("allow_set", False):
            capabilities.append("参数调优: AI可自行调整参数")

        if not capabilities:
            capabilities.append("MyTool未启用")

        return capabilities
