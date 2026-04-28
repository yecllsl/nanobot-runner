# Dream集成调优模块
# 集成nanobot-ai的Dream能力，实现对话历史自动归档、偏好自动提取
# 记忆整理频率可配置，人格进化参数可调

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class DreamIntegration:
    """Dream集成管理器

    集成nanobot-ai的Dream能力，提供：
    - 对话历史自动归档
    - 偏好自动提取
    - 记忆整理频率配置
    - 人格进化参数调整

    Dream配置存储在config.json中：
    {
        "dream": {
            "enabled": true,
            "frequency": "daily",
            "auto_archive": true,
            "auto_extract_preferences": true
        }
    }

    Attributes:
        config_path: config.json文件路径
        workspace: 工作空间目录
    """

    DREAM_CONFIG_KEY = "dream"

    FREQUENCY_OPTIONS = ["never", "daily", "weekly", "monthly", "on_exit"]

    def __init__(self, config_path: Path, workspace: Path | None = None) -> None:
        """初始化Dream集成

        Args:
            config_path: config.json路径
            workspace: 工作空间目录（可选）
        """
        self.config_path = config_path
        self.workspace = workspace

    def get_dream_config(self) -> dict[str, Any]:
        """获取Dream配置

        Returns:
            dict: Dream配置字典
        """
        config = self._load_config()
        return config.get(self.DREAM_CONFIG_KEY, self._default_dream_config())

    def update_dream_config(self, **kwargs: Any) -> bool:
        """更新Dream配置

        Args:
            **kwargs: 配置项键值对

        Returns:
            bool: 是否更新成功
        """
        try:
            config = self._load_config()

            if self.DREAM_CONFIG_KEY not in config:
                config[self.DREAM_CONFIG_KEY] = self._default_dream_config()

            dream_config = config[self.DREAM_CONFIG_KEY]

            for key, value in kwargs.items():
                if key == "frequency" and value not in self.FREQUENCY_OPTIONS:
                    logger.warning(f"无效的频率选项: {value}")
                    continue
                dream_config[key] = value

            config[self.DREAM_CONFIG_KEY] = dream_config
            self._save_config(config)

            logger.info(f"Dream配置已更新: {kwargs}")
            return True

        except Exception as e:
            logger.error(f"更新Dream配置失败: {e}")
            return False

    def enable_auto_archive(self) -> bool:
        """启用对话历史自动归档

        Returns:
            bool: 是否启用成功
        """
        return self.update_dream_config(auto_archive=True)

    def disable_auto_archive(self) -> bool:
        """禁用对话历史自动归档

        Returns:
            bool: 是否禁用成功
        """
        return self.update_dream_config(auto_archive=False)

    def enable_auto_extract_preferences(self) -> bool:
        """启用偏好自动提取

        Returns:
            bool: 是否启用成功
        """
        return self.update_dream_config(auto_extract_preferences=True)

    def disable_auto_extract_preferences(self) -> bool:
        """禁用偏好自动提取

        Returns:
            bool: 是否禁用成功
        """
        return self.update_dream_config(auto_extract_preferences=False)

    def set_frequency(self, frequency: str) -> bool:
        """设置记忆整理频率

        Args:
            frequency: 频率选项（never/daily/weekly/monthly/on_exit）

        Returns:
            bool: 是否设置成功
        """
        if frequency not in self.FREQUENCY_OPTIONS:
            logger.warning(
                f"无效的频率选项: {frequency}, 可选: {self.FREQUENCY_OPTIONS}"
            )
            return False
        return self.update_dream_config(frequency=frequency)

    def get_dream_status(self) -> dict[str, Any]:
        """获取Dream状态报告

        Returns:
            dict: Dream状态信息
        """
        dream_config = self.get_dream_config()

        return {
            "enabled": dream_config.get("enabled", False),
            "frequency": dream_config.get("frequency", "daily"),
            "auto_archive": dream_config.get("auto_archive", True),
            "auto_extract_preferences": dream_config.get(
                "auto_extract_preferences", True
            ),
            "workspace": str(self.workspace) if self.workspace else "",
            "memory_file_exists": self._check_memory_file(),
        }

    def trigger_dream(self) -> dict[str, Any]:
        """手动触发Dream整理

        在实际运行时，会调用nanobot SDK的Dream.run()方法。
        此处提供配置层面的触发接口。

        Returns:
            dict: 触发结果
        """
        dream_config = self.get_dream_config()

        if not dream_config.get("enabled", False):
            return {
                "success": False,
                "message": "Dream未启用，请先在配置中启用Dream功能",
            }

        logger.info("手动触发Dream整理")

        return {
            "success": True,
            "message": "Dream整理已触发（实际执行由nanobot SDK处理）",
            "config": dream_config,
        }

    def _check_memory_file(self) -> bool:
        """检查记忆文件是否存在

        Returns:
            bool: 记忆文件是否存在
        """
        if self.workspace is None:
            return False

        memory_file = self.workspace / "MEMORY.md"
        return memory_file.exists()

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
    def _default_dream_config() -> dict[str, Any]:
        """默认Dream配置

        Returns:
            dict: 默认配置字典
        """
        return {
            "enabled": True,
            "frequency": "daily",
            "auto_archive": True,
            "auto_extract_preferences": True,
        }
