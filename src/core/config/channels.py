# 多通道配置模块 - v0.17.0
# 支持飞书、微信、邮件等多通道配置管理

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ChannelType(Enum):
    """通道类型枚举"""

    FEISHU = "feishu"
    WECHAT = "wechat"
    EMAIL = "email"
    WEBHOOK = "webhook"
    CLI = "cli"


class NotificationLevel(Enum):
    """通知级别枚举"""

    ALL = "all"  # 所有通知
    IMPORTANT = "important"  # 仅重要通知
    CRITICAL = "critical"  # 仅关键通知
    NONE = "none"  # 不通知


@dataclass
class ChannelConfig:
    """通道配置数据类

    Attributes:
        channel_type: 通道类型
        enabled: 是否启用
        level: 通知级别
        config: 通道特定配置
    """

    channel_type: ChannelType
    enabled: bool = True
    level: NotificationLevel = NotificationLevel.ALL
    config: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "type": self.channel_type.value,
            "enabled": self.enabled,
            "level": self.level.value,
            "config": self.config,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChannelConfig:
        """从字典创建实例"""
        return cls(
            channel_type=ChannelType(data.get("type", "cli")),
            enabled=data.get("enabled", True),
            level=NotificationLevel(data.get("level", "all")),
            config=data.get("config", {}),
        )


@dataclass
class FeishuChannelConfig(ChannelConfig):
    """飞书通道配置"""

    app_id: str = ""
    app_secret: str = ""
    receive_id: str = ""
    receive_id_type: str = "user_id"

    def __init__(
        self,
        app_id: str = "",
        app_secret: str = "",
        receive_id: str = "",
        receive_id_type: str = "user_id",
        enabled: bool = True,
        level: NotificationLevel = NotificationLevel.ALL,
    ) -> None:
        super().__init__(
            channel_type=ChannelType.FEISHU,
            enabled=enabled,
            level=level,
            config={
                "app_id": app_id,
                "app_secret": app_secret,
                "receive_id": receive_id,
                "receive_id_type": receive_id_type,
            },
        )


@dataclass
class EmailChannelConfig(ChannelConfig):
    """邮件通道配置"""

    smtp_host: str = ""
    smtp_port: int = 587
    username: str = ""
    password: str = ""
    to_addresses: list[str] = field(default_factory=list)
    use_tls: bool = True

    def __init__(
        self,
        smtp_host: str = "",
        smtp_port: int = 587,
        username: str = "",
        password: str = "",
        to_addresses: list[str] | None = None,
        use_tls: bool = True,
        enabled: bool = True,
        level: NotificationLevel = NotificationLevel.ALL,
    ) -> None:
        super().__init__(
            channel_type=ChannelType.EMAIL,
            enabled=enabled,
            level=level,
            config={
                "smtp_host": smtp_host,
                "smtp_port": smtp_port,
                "username": username,
                "password": password,
                "to_addresses": to_addresses or [],
                "use_tls": use_tls,
            },
        )


@dataclass
class WebhookChannelConfig(ChannelConfig):
    """Webhook通道配置"""

    url: str = ""
    method: str = "POST"
    headers: dict[str, str] = field(default_factory=dict)
    timeout: int = 30

    def __init__(
        self,
        url: str = "",
        method: str = "POST",
        headers: dict[str, str] | None = None,
        timeout: int = 30,
        enabled: bool = True,
        level: NotificationLevel = NotificationLevel.ALL,
    ) -> None:
        super().__init__(
            channel_type=ChannelType.WEBHOOK,
            enabled=enabled,
            level=level,
            config={
                "url": url,
                "method": method,
                "headers": headers or {},
                "timeout": timeout,
            },
        )


class ChannelManager:
    """多通道配置管理器

    管理所有通知通道的配置，支持多通道并行通知。

    使用方式：
        manager = ChannelManager()
        manager.add_channel(feishu_config)
        enabled_channels = manager.get_enabled_channels()
    """

    def __init__(self) -> None:
        """初始化通道管理器"""
        self._channels: dict[str, ChannelConfig] = {}

    def add_channel(self, name: str, config: ChannelConfig) -> None:
        """添加通道配置

        Args:
            name: 通道名称
            config: 通道配置
        """
        self._channels[name] = config
        logger.info(f"通道已添加: {name} ({config.channel_type.value})")

    def remove_channel(self, name: str) -> bool:
        """移除通道配置

        Args:
            name: 通道名称

        Returns:
            bool: 是否成功移除
        """
        if name in self._channels:
            del self._channels[name]
            logger.info(f"通道已移除: {name}")
            return True
        return False

    def get_channel(self, name: str) -> ChannelConfig | None:
        """获取通道配置

        Args:
            name: 通道名称

        Returns:
            ChannelConfig | None: 通道配置
        """
        return self._channels.get(name)

    def get_enabled_channels(
        self,
        level: NotificationLevel | None = None,
    ) -> dict[str, ChannelConfig]:
        """获取启用的通道

        Args:
            level: 过滤指定级别的通道，None表示不过滤

        Returns:
            dict[str, ChannelConfig]: 启用的通道配置
        """
        result = {}
        for name, config in self._channels.items():
            if not config.enabled:
                continue
            if level is not None and config.level != level:
                continue
            result[name] = config
        return result

    def get_channels_by_type(
        self,
        channel_type: ChannelType,
    ) -> dict[str, ChannelConfig]:
        """获取指定类型的通道

        Args:
            channel_type: 通道类型

        Returns:
            dict[str, ChannelConfig]: 该类型的通道配置
        """
        return {
            name: config
            for name, config in self._channels.items()
            if config.channel_type == channel_type
        }

    def enable_channel(self, name: str) -> bool:
        """启用通道

        Args:
            name: 通道名称

        Returns:
            bool: 是否成功启用
        """
        if name in self._channels:
            self._channels[name].enabled = True
            logger.info(f"通道已启用: {name}")
            return True
        return False

    def disable_channel(self, name: str) -> bool:
        """禁用通道

        Args:
            name: 通道名称

        Returns:
            bool: 是否成功禁用
        """
        if name in self._channels:
            self._channels[name].enabled = False
            logger.info(f"通道已禁用: {name}")
            return True
        return False

    def set_channel_level(self, name: str, level: NotificationLevel) -> bool:
        """设置通道通知级别

        Args:
            name: 通道名称
            level: 通知级别

        Returns:
            bool: 是否成功设置
        """
        if name in self._channels:
            self._channels[name].level = level
            logger.info(f"通道 {name} 级别已设置为: {level.value}")
            return True
        return False

    def to_dict(self) -> dict[str, dict[str, Any]]:
        """转换为字典"""
        return {name: config.to_dict() for name, config in self._channels.items()}

    @classmethod
    def from_dict(cls, data: dict[str, dict[str, Any]]) -> ChannelManager:
        """从字典创建实例"""
        manager = cls()
        for name, channel_data in data.items():
            config = ChannelConfig.from_dict(channel_data)
            manager.add_channel(name, config)
        return manager

    @property
    def channel_count(self) -> int:
        """通道总数"""
        return len(self._channels)

    @property
    def enabled_count(self) -> int:
        """启用的通道数"""
        return sum(1 for c in self._channels.values() if c.enabled)

    def __contains__(self, name: str) -> bool:
        """检查是否包含指定通道"""
        return name in self._channels

    def __iter__(self):
        """迭代通道名称"""
        return iter(self._channels)

    def __len__(self) -> int:
        """通道数量"""
        return len(self._channels)
