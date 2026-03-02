# 飞书通知单元测试

import pytest
from unittest.mock import patch, MagicMock

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
        
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"code": 0, "msg": "success"}
            mock_post.return_value = mock_response
            
            result = bot.send_text("测试消息")
            
            assert "error" not in result
    
    def test_send_card(self):
        """测试发送卡片消息"""
        webhook = "https://example.com/webhook"
        bot = FeishuBot(webhook=webhook)
        
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"code": 0, "msg": "success"}
            mock_post.return_value = mock_response
            
            result = bot.send_card("测试标题", "测试内容")
            
            assert "error" not in result
    
    def test_send_import_notification(self):
        """测试发送导入通知"""
        webhook = "https://example.com/webhook"
        bot = FeishuBot(webhook=webhook)
        
        stats = {
            "total": 100,
            "added": 80,
            "skipped": 20,
            "errors": 0
        }
        
        with patch('requests.post') as mock_post:
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
