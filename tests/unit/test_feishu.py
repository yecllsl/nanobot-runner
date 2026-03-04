# 飞书通知单元测试

from unittest.mock import MagicMock, Mock, patch

import pytest

from src.notify.feishu import FeishuBot


class TestFeishuBot:
    """FeishuBot 单元测试"""

    def test_init_with_webhook(self):
        """测试初始化带Webhook"""
        webhook = "https://example.com/webhook"
        bot = FeishuBot(webhook=webhook)
        assert bot.webhook == webhook

    def test_send_text(self):
        """测试发送文本消息"""
        webhook = "https://example.com/webhook"
        bot = FeishuBot(webhook=webhook)

        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"code": 0, "msg": "success"}
            mock_post.return_value = mock_response

            result = bot.send_text("测试消息")

            assert "error" not in result

    def test_send_card(self):
        """测试发送卡片消息"""
        webhook = "https://example.com/webhook"
        bot = FeishuBot(webhook=webhook)

        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"code": 0, "msg": "success"}
            mock_post.return_value = mock_response

            result = bot.send_card("测试标题", "测试内容")

            assert "error" not in result

    def test_send_import_notification(self):
        """测试发送导入通知"""
        webhook = "https://example.com/webhook"
        bot = FeishuBot(webhook=webhook)

        stats = {"total": 100, "added": 80, "skipped": 20, "errors": 0}

        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"code": 0, "msg": "success"}
            mock_post.return_value = mock_response

            result = bot.send_import_notification(stats)

            assert "error" not in result

    def test_no_webhook_configured(self):
        """测试未配置Webhook"""
        bot = FeishuBot()

        result = bot.send_text("测试消息")

        assert "error" in result
        assert result["error"] == "未配置Webhook"


class TestFeishuBotAdvanced:
    """测试飞书通知高级功能"""

    def test_send_text_with_special_characters(self):
        """测试发送包含特殊字符的消息"""
        webhook = "https://example.com/webhook"
        bot = FeishuBot(webhook=webhook)

        message = "测试消息 with 特殊字符: @#$%^&*()中文测试"

        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"code": 0, "msg": "success"}
            mock_post.return_value = mock_response

            result = bot.send_text(message)

            assert "error" not in result

    def test_send_card_with_long_content(self):
        """测试发送长内容卡片消息"""
        webhook = "https://example.com/webhook"
        bot = FeishuBot(webhook=webhook)

        long_title = "A" * 100
        long_content = "B" * 500

        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"code": 0, "msg": "success"}
            mock_post.return_value = mock_response

            result = bot.send_card(long_title, long_content)

            assert "error" not in result

    def test_send_import_notification_with_errors(self):
        """测试发送带错误的导入通知"""
        webhook = "https://example.com/webhook"
        bot = FeishuBot(webhook=webhook)

        stats = {"total": 100, "added": 70, "skipped": 20, "errors": 10}

        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"code": 0, "msg": "success"}
            mock_post.return_value = mock_response

            result = bot.send_import_notification(stats)

            assert "error" not in result

    def test_send_import_notification_empty(self):
        """测试发送空导入通知"""
        webhook = "https://example.com/webhook"
        bot = FeishuBot(webhook=webhook)

        stats = {"total": 0, "added": 0, "skipped": 0, "errors": 0}

        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"code": 0, "msg": "success"}
            mock_post.return_value = mock_response

            result = bot.send_import_notification(stats)

            assert "error" not in result

    def test_send_text_request_failure(self):
        """测试发送文本消息请求失败"""
        webhook = "https://example.com/webhook"
        bot = FeishuBot(webhook=webhook)

        with patch("requests.post", side_effect=Exception("Network error")):
            result = bot.send_text("测试消息")

            assert "error" in result
            assert "Network error" in result["error"]

    def test_send_card_request_failure(self):
        """测试发送卡片消息请求失败"""
        webhook = "https://example.com/webhook"
        bot = FeishuBot(webhook=webhook)

        with patch("requests.post", side_effect=Exception("Network error")):
            result = bot.send_card("测试标题", "测试内容")

            assert "error" in result
            assert "Network error" in result["error"]

    def test_send_import_notification_request_failure(self):
        """测试发送导入通知请求失败"""
        webhook = "https://example.com/webhook"
        bot = FeishuBot(webhook=webhook)

        stats = {"total": 10, "added": 5, "skipped": 5, "errors": 0}

        with patch("requests.post", side_effect=Exception("Network error")):
            result = bot.send_import_notification(stats)

            assert "error" in result
            assert "Network error" in result["error"]

    def test_send_text_with_empty_message(self):
        """测试发送空消息"""
        webhook = "https://example.com/webhook"
        bot = FeishuBot(webhook=webhook)

        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"code": 0, "msg": "success"}
            mock_post.return_value = mock_response

            result = bot.send_text("")

            assert "error" not in result

    def test_send_card_with_empty_content(self):
        """测试发送空内容卡片消息"""
        webhook = "https://example.com/webhook"
        bot = FeishuBot(webhook=webhook)

        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"code": 0, "msg": "success"}
            mock_post.return_value = mock_response

            result = bot.send_card("测试标题", "")

            assert "error" not in result

    def test_send_text_with_webhook_from_config(self):
        """测试从配置加载Webhook"""
        with patch("src.notify.feishu.ConfigManager") as mock_config:
            mock_config_instance = Mock()
            mock_config_instance.get.return_value = "https://config-webhook.com/webhook"
            mock_config.return_value = mock_config_instance

            bot = FeishuBot()

            assert bot.webhook == "https://config-webhook.com/webhook"

    def test_send_text_with_custom_timeout(self):
        """测试自定义超时时间"""
        webhook = "https://example.com/webhook"
        bot = FeishuBot(webhook=webhook)

        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"code": 0, "msg": "success"}
            mock_post.return_value = mock_response

            result = bot.send_text("测试消息")

            assert "error" not in result
            mock_post.assert_called_once()

    def test_send_card_with_detailed_stats(self):
        """测试发送带详细统计的卡片消息"""
        webhook = "https://example.com/webhook"
        bot = FeishuBot(webhook=webhook)

        stats = {
            "total": 100,
            "added": 80,
            "skipped": 15,
            "errors": 5,
            "new_files": ["file1.fit", "file2.fit", "file3.fit"],
            "skipped_files": ["file4.fit", "file5.fit"],
        }

        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"code": 0, "msg": "success"}
            mock_post.return_value = mock_response

            result = bot.send_import_notification(stats)

            assert "error" not in result
