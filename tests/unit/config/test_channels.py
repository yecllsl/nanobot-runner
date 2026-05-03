# 多通道配置模块单元测试 - v0.17.0

import pytest

from src.core.config.channels import (
    ChannelConfig,
    ChannelManager,
    ChannelType,
    EmailChannelConfig,
    FeishuChannelConfig,
    NotificationLevel,
    WebhookChannelConfig,
)


class TestChannelConfig:
    """ChannelConfig 测试"""

    def test_default_creation(self):
        """测试默认创建"""
        config = ChannelConfig(channel_type=ChannelType.CLI)
        assert config.channel_type == ChannelType.CLI
        assert config.enabled is True
        assert config.level == NotificationLevel.ALL
        assert config.config == {}

    def test_to_dict(self):
        """测试转换为字典"""
        config = ChannelConfig(
            channel_type=ChannelType.FEISHU,
            enabled=True,
            level=NotificationLevel.IMPORTANT,
            config={"key": "value"},
        )
        data = config.to_dict()
        assert data["type"] == "feishu"
        assert data["enabled"] is True
        assert data["level"] == "important"
        assert data["config"] == {"key": "value"}

    def test_from_dict(self):
        """测试从字典创建"""
        data = {
            "type": "email",
            "enabled": False,
            "level": "critical",
            "config": {"host": "smtp.example.com"},
        }
        config = ChannelConfig.from_dict(data)
        assert config.channel_type == ChannelType.EMAIL
        assert config.enabled is False
        assert config.level == NotificationLevel.CRITICAL
        assert config.config["host"] == "smtp.example.com"


class TestFeishuChannelConfig:
    """FeishuChannelConfig 测试"""

    def test_creation(self):
        """测试创建飞书配置"""
        config = FeishuChannelConfig(
            app_id="test_id",
            app_secret="test_secret",
            receive_id="user123",
            receive_id_type="open_id",
        )
        assert config.channel_type == ChannelType.FEISHU
        assert config.config["app_id"] == "test_id"
        assert config.config["app_secret"] == "test_secret"
        assert config.config["receive_id"] == "user123"
        assert config.config["receive_id_type"] == "open_id"


class TestEmailChannelConfig:
    """EmailChannelConfig 测试"""

    def test_creation(self):
        """测试创建邮件配置"""
        config = EmailChannelConfig(
            smtp_host="smtp.example.com",
            smtp_port=465,
            username="test@example.com",
            to_addresses=["to@example.com"],
        )
        assert config.channel_type == ChannelType.EMAIL
        assert config.config["smtp_host"] == "smtp.example.com"
        assert config.config["smtp_port"] == 465
        assert config.config["to_addresses"] == ["to@example.com"]
        assert config.config["use_tls"] is True


class TestWebhookChannelConfig:
    """WebhookChannelConfig 测试"""

    def test_creation(self):
        """测试创建Webhook配置"""
        config = WebhookChannelConfig(
            url="https://example.com/webhook",
            method="POST",
            headers={"Authorization": "Bearer token"},
            timeout=60,
        )
        assert config.channel_type == ChannelType.WEBHOOK
        assert config.config["url"] == "https://example.com/webhook"
        assert config.config["method"] == "POST"
        assert config.config["headers"]["Authorization"] == "Bearer token"
        assert config.config["timeout"] == 60


class TestChannelManager:
    """ChannelManager 测试"""

    @pytest.fixture
    def manager(self):
        """创建通道管理器"""
        return ChannelManager()

    @pytest.fixture
    def feishu_config(self):
        """创建飞书配置"""
        return FeishuChannelConfig(app_id="id", app_secret="secret")

    @pytest.fixture
    def email_config(self):
        """创建邮件配置"""
        return EmailChannelConfig(smtp_host="smtp.example.com")

    def test_add_channel(self, manager, feishu_config):
        """测试添加通道"""
        manager.add_channel("feishu", feishu_config)
        assert "feishu" in manager
        assert manager.channel_count == 1

    def test_remove_channel(self, manager, feishu_config):
        """测试移除通道"""
        manager.add_channel("feishu", feishu_config)
        assert manager.remove_channel("feishu") is True
        assert "feishu" not in manager
        assert manager.remove_channel("nonexistent") is False

    def test_get_channel(self, manager, feishu_config):
        """测试获取通道"""
        manager.add_channel("feishu", feishu_config)
        config = manager.get_channel("feishu")
        assert config is not None
        assert config.channel_type == ChannelType.FEISHU
        assert manager.get_channel("nonexistent") is None

    def test_get_enabled_channels(self, manager, feishu_config, email_config):
        """测试获取启用的通道"""
        manager.add_channel("feishu", feishu_config)
        manager.add_channel("email", email_config)

        enabled = manager.get_enabled_channels()
        assert len(enabled) == 2

        # 禁用一个通道
        manager.disable_channel("email")
        enabled = manager.get_enabled_channels()
        assert len(enabled) == 1
        assert "feishu" in enabled

    def test_get_enabled_channels_by_level(self, manager):
        """测试按级别获取启用的通道"""
        config_all = ChannelConfig(
            channel_type=ChannelType.CLI,
            level=NotificationLevel.ALL,
        )
        config_important = ChannelConfig(
            channel_type=ChannelType.FEISHU,
            level=NotificationLevel.IMPORTANT,
        )
        config_critical = ChannelConfig(
            channel_type=ChannelType.EMAIL,
            level=NotificationLevel.CRITICAL,
        )

        manager.add_channel("cli", config_all)
        manager.add_channel("feishu", config_important)
        manager.add_channel("email", config_critical)

        # 获取CRITICAL级别的通道（精确匹配）
        critical_channels = manager.get_enabled_channels(NotificationLevel.CRITICAL)
        assert len(critical_channels) == 1
        assert "email" in critical_channels

        # 获取ALL级别的通道
        all_channels = manager.get_enabled_channels(NotificationLevel.ALL)
        assert len(all_channels) == 1
        assert "cli" in all_channels

    def test_get_channels_by_type(self, manager, feishu_config, email_config):
        """测试按类型获取通道"""
        manager.add_channel("feishu", feishu_config)
        manager.add_channel("email", email_config)

        feishu_channels = manager.get_channels_by_type(ChannelType.FEISHU)
        assert len(feishu_channels) == 1
        assert "feishu" in feishu_channels

        email_channels = manager.get_channels_by_type(ChannelType.EMAIL)
        assert len(email_channels) == 1
        assert "email" in email_channels

        cli_channels = manager.get_channels_by_type(ChannelType.CLI)
        assert len(cli_channels) == 0

    def test_enable_disable_channel(self, manager, feishu_config):
        """测试启用/禁用通道"""
        manager.add_channel("feishu", feishu_config)

        assert manager.enabled_count == 1

        manager.disable_channel("feishu")
        assert manager.enabled_count == 0

        manager.enable_channel("feishu")
        assert manager.enabled_count == 1

    def test_set_channel_level(self, manager, feishu_config):
        """测试设置通道级别"""
        manager.add_channel("feishu", feishu_config)

        assert manager.set_channel_level("feishu", NotificationLevel.CRITICAL) is True
        config = manager.get_channel("feishu")
        assert config.level == NotificationLevel.CRITICAL

        assert manager.set_channel_level("nonexistent", NotificationLevel.ALL) is False

    def test_to_dict(self, manager, feishu_config):
        """测试转换为字典"""
        manager.add_channel("feishu", feishu_config)

        data = manager.to_dict()
        assert "feishu" in data
        assert data["feishu"]["type"] == "feishu"
        assert data["feishu"]["enabled"] is True

    def test_from_dict(self):
        """测试从字典创建"""
        data = {
            "feishu": {
                "type": "feishu",
                "enabled": True,
                "level": "all",
                "config": {"app_id": "test"},
            },
            "email": {
                "type": "email",
                "enabled": False,
                "level": "important",
                "config": {"smtp_host": "smtp.example.com"},
            },
        }

        manager = ChannelManager.from_dict(data)
        assert manager.channel_count == 2
        assert "feishu" in manager
        assert "email" in manager
        assert manager.enabled_count == 1

    def test_iteration(self, manager, feishu_config, email_config):
        """测试迭代"""
        manager.add_channel("feishu", feishu_config)
        manager.add_channel("email", email_config)

        names = list(manager)
        assert "feishu" in names
        assert "email" in names

    def test_length(self, manager, feishu_config):
        """测试长度"""
        assert len(manager) == 0
        manager.add_channel("feishu", feishu_config)
        assert len(manager) == 1
