# 飞书通知单元测试
# 覆盖率目标：≥85%

from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from src.notify.feishu import FeishuBot, test_connection


class TestFeishuBotInit:
    """FeishuBot 初始化测试"""

    def test_init_with_webhook(self):
        """测试初始化带Webhook"""
        webhook = "https://example.com/webhook"
        bot = FeishuBot(webhook=webhook)
        assert bot.webhook == webhook

    def test_init_without_webhook(self):
        """测试初始化不带Webhook，从配置加载"""
        with patch("src.notify.feishu.ConfigManager") as mock_config:
            mock_config_instance = Mock()
            mock_config_instance.get.return_value = "https://config-webhook.com/webhook"
            mock_config.return_value = mock_config_instance

            bot = FeishuBot()

            assert bot.webhook == "https://config-webhook.com/webhook"

    def test_init_with_none_webhook(self):
        """测试初始化时Webhook为None"""
        with patch("src.notify.feishu.ConfigManager") as mock_config:
            mock_config_instance = Mock()
            mock_config_instance.get.return_value = None
            mock_config.return_value = mock_config_instance

            bot = FeishuBot()

            assert bot.webhook is None


class TestFeishuBotSendText:
    """发送文本消息测试"""

    def test_send_text_success(self):
        """测试发送文本消息成功"""
        webhook = "https://example.com/webhook"
        bot = FeishuBot(webhook=webhook)

        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"code": 0, "msg": "success"}
            mock_post.return_value = mock_response

            result = bot.send_text("测试消息")

            assert "error" not in result

    def test_send_text_no_webhook(self):
        """测试未配置Webhook时发送文本消息"""
        bot = FeishuBot(webhook=None)
        result = bot.send_text("测试消息")

        assert "error" in result
        assert result["error"] == "未配置Webhook"

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


class TestFeishuBotSendCard:
    """发送卡片消息测试"""

    def test_send_card_success(self):
        """测试发送卡片消息成功"""
        webhook = "https://example.com/webhook"
        bot = FeishuBot(webhook=webhook)

        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"code": 0, "msg": "success"}
            mock_post.return_value = mock_response

            result = bot.send_card("测试标题", "测试内容")

            assert "error" not in result

    def test_send_card_no_webhook(self):
        """测试未配置Webhook时发送卡片消息"""
        bot = FeishuBot(webhook=None)
        result = bot.send_card("测试标题", "测试内容")

        assert "error" in result

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


class TestFeishuBotImportNotification:
    """导入通知测试"""

    def test_send_import_notification_success(self):
        """测试发送导入通知成功"""
        webhook = "https://example.com/webhook"
        bot = FeishuBot(webhook=webhook)

        stats = {"total": 100, "added": 80, "skipped": 20, "errors": 0}

        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"code": 0, "msg": "success"}
            mock_post.return_value = mock_response

            result = bot.send_import_notification(stats)

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

    def test_send_import_notification_with_detailed_stats(self):
        """测试发送带详细统计的导入通知"""
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


class TestFeishuBotDailyReport:
    """每日晨报测试"""

    def test_send_daily_report_success(self):
        """测试发送每日晨报成功"""
        webhook = "https://example.com/webhook"
        bot = FeishuBot(webhook=webhook)

        report_data = {
            "date": "2024年3月15日 周五",
            "greeting": "早上好！今天是您的训练日。",
            "yesterday_run": {
                "distance_km": 10.5,
                "duration_min": 55.0,
                "tss": 85.5,
                "run_count": 1,
            },
            "fitness_status": {
                "atl": 45.2,
                "ctl": 52.8,
                "tsb": 7.6,
                "status": "状态正常",
            },
            "training_advice": "状态良好，可以进行中等强度训练。",
            "weekly_plan": [
                {"day": "周一", "plan": "休息", "is_today": False},
                {"day": "周二", "plan": "轻松跑 6km", "is_today": True},
            ],
        }

        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"code": 0, "msg": "success"}
            mock_post.return_value = mock_response

            result = bot.send_daily_report(report_data)

            assert result.get("success") is True

    def test_send_daily_report_no_yesterday_run(self):
        """测试发送无昨日训练的晨报"""
        webhook = "https://example.com/webhook"
        bot = FeishuBot(webhook=webhook)

        report_data = {
            "date": "2024年3月15日 周五",
            "greeting": "早上好！",
            "yesterday_run": None,
            "fitness_status": {
                "atl": 0.0,
                "ctl": 0.0,
                "tsb": 0.0,
                "status": "数据不足",
            },
            "training_advice": "暂无足够数据生成个性化建议。",
            "weekly_plan": [],
        }

        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"code": 0, "msg": "success"}
            mock_post.return_value = mock_response

            result = bot.send_daily_report(report_data)

            assert result.get("success") is True

    def test_send_daily_report_empty_data(self):
        """测试发送空数据晨报"""
        webhook = "https://example.com/webhook"
        bot = FeishuBot(webhook=webhook)

        report_data = {}

        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"code": 0, "msg": "success"}
            mock_post.return_value = mock_response

            result = bot.send_daily_report(report_data)

            assert result.get("success") is True

    def test_send_daily_report_no_webhook(self):
        """测试未配置Webhook时发送晨报"""
        bot = FeishuBot(webhook=None)

        # Mock _check_nanobot_feishu_config 返回 False
        with patch.object(bot, "_check_nanobot_feishu_config", return_value=False):
            report_data = {"date": "2024年3月15日"}
            result = bot.send_daily_report(report_data)

            assert result.get("success") is False
            assert "未配置飞书推送渠道" in result.get("error", "")

    def test_send_daily_report_with_weekly_plan(self):
        """测试发送包含完整周计划的晨报"""
        webhook = "https://example.com/webhook"
        bot = FeishuBot(webhook=webhook)

        report_data = {
            "date": "2024年3月15日 周五",
            "greeting": "早上好！",
            "fitness_status": {"atl": 50, "ctl": 60, "tsb": 10, "status": "良好"},
            "training_advice": "保持训练节奏。",
            "weekly_plan": [
                {"day": "周一", "plan": "休息", "is_today": False, "is_past": True},
                {"day": "周二", "plan": "轻松跑", "is_today": False, "is_past": True},
                {"day": "周三", "plan": "节奏跑", "is_today": False, "is_past": True},
                {"day": "周四", "plan": "间歇跑", "is_today": False, "is_past": True},
                {"day": "周五", "plan": "轻松跑", "is_today": True, "is_past": False},
                {"day": "周六", "plan": "长距离跑", "is_today": False, "is_past": False},
                {"day": "周日", "plan": "休息", "is_today": False, "is_past": False},
            ],
        }

        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"code": 0, "msg": "success"}
            mock_post.return_value = mock_response

            result = bot.send_daily_report(report_data)

            assert result.get("success") is True
            # 验证请求体包含周计划
            call_args = mock_post.call_args
            payload = call_args.kwargs["json"]
            assert "card" in payload
            assert "elements" in payload["card"]


class TestFeishuBotRetry:
    """重试机制测试"""

    def test_retry_on_timeout(self):
        """测试超时重试"""
        webhook = "https://example.com/webhook"
        bot = FeishuBot(webhook=webhook)

        with patch("requests.post") as mock_post:
            with patch("src.notify.feishu.time.sleep") as mock_sleep:
                # 前两次超时，第三次成功
                mock_post.side_effect = [
                    requests.exceptions.Timeout("Timeout"),
                    requests.exceptions.Timeout("Timeout"),
                    MagicMock(json=lambda: {"code": 0, "msg": "success"}),
                ]

                result = bot.send_text("测试消息")

                assert "error" not in result
                assert mock_post.call_count == 3
                # 验证sleep被调用了2次（两次重试）
                assert mock_sleep.call_count == 2

    def test_retry_on_connection_error(self):
        """测试连接错误重试"""
        webhook = "https://example.com/webhook"
        bot = FeishuBot(webhook=webhook)

        with patch("requests.post") as mock_post:
            with patch("src.notify.feishu.time.sleep") as mock_sleep:
                # 前两次连接错误，第三次成功
                mock_post.side_effect = [
                    requests.exceptions.ConnectionError("Connection refused"),
                    requests.exceptions.ConnectionError("Connection refused"),
                    MagicMock(json=lambda: {"code": 0, "msg": "success"}),
                ]

                result = bot.send_text("测试消息")

                assert "error" not in result
                assert mock_post.call_count == 3
                assert mock_sleep.call_count == 2

    def test_max_retries_exceeded(self):
        """测试超过最大重试次数"""
        webhook = "https://example.com/webhook"
        bot = FeishuBot(webhook=webhook)

        with patch("requests.post") as mock_post:
            with patch("src.notify.feishu.time.sleep") as mock_sleep:
                # 所有请求都超时
                mock_post.side_effect = requests.exceptions.Timeout("Timeout")

                result = bot.send_text("测试消息")

                assert "error" in result
                assert "已重试" in result["error"]
                assert mock_post.call_count == FeishuBot.MAX_RETRIES + 1
                assert mock_sleep.call_count == FeishuBot.MAX_RETRIES

    def test_no_retry_on_success(self):
        """测试成功时不重试"""
        webhook = "https://example.com/webhook"
        bot = FeishuBot(webhook=webhook)

        with patch("requests.post") as mock_post:
            with patch("src.notify.feishu.time.sleep") as mock_sleep:
                mock_response = MagicMock()
                mock_response.json.return_value = {"code": 0, "msg": "success"}
                mock_post.return_value = mock_response

                result = bot.send_text("测试消息")

                assert "error" not in result
                assert mock_post.call_count == 1
                # 成功时不应调用sleep
                assert mock_sleep.call_count == 0


class TestFeishuBotErrorHandling:
    """错误处理测试"""

    def test_request_failure(self):
        """测试请求失败"""
        webhook = "https://example.com/webhook"
        bot = FeishuBot(webhook=webhook)

        with patch("requests.post", side_effect=Exception("Network error")):
            result = bot.send_text("测试消息")

            assert "error" in result

    def test_api_error_response(self):
        """测试API错误响应"""
        webhook = "https://example.com/webhook"
        bot = FeishuBot(webhook=webhook)

        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"code": 1001, "msg": "token expired"}
            mock_post.return_value = mock_response

            result = bot.send_text("测试消息")

            assert "error" in result

    def test_request_timeout_exception(self):
        """测试请求超时异常"""
        webhook = "https://example.com/webhook"
        bot = FeishuBot(webhook=webhook)

        with patch("requests.post") as mock_post:
            with patch("src.notify.feishu.time.sleep") as mock_sleep:
                mock_post.side_effect = requests.exceptions.Timeout(
                    "Connection timed out"
                )
                result = bot.send_text("测试消息")

                assert "error" in result
                assert "超时" in result["error"]
                # 验证重试次数
                assert mock_sleep.call_count == FeishuBot.MAX_RETRIES

    def test_request_connection_error_exception(self):
        """测试连接错误异常"""
        webhook = "https://example.com/webhook"
        bot = FeishuBot(webhook=webhook)

        with patch("requests.post") as mock_post:
            with patch("src.notify.feishu.time.sleep") as mock_sleep:
                mock_post.side_effect = requests.exceptions.ConnectionError(
                    "Connection refused"
                )
                result = bot.send_text("测试消息")

                assert "error" in result
                assert "连接错误" in result["error"]
                # 验证重试次数
                assert mock_sleep.call_count == FeishuBot.MAX_RETRIES


class TestFeishuBotNanobotChannel:
    """nanobot 飞书通道测试"""

    def test_check_nanobot_feishu_config_enabled(self):
        """测试检测 nanobot 飞书配置已启用"""
        bot = FeishuBot(webhook=None)

        mock_feishu_config = Mock()
        mock_feishu_config.enabled = True
        mock_feishu_config.app_id = "test_app_id"
        mock_feishu_config.app_secret = "test_secret"

        mock_channels = Mock()
        mock_channels.feishu = mock_feishu_config

        mock_config = Mock()
        mock_config.channels = mock_channels

        with patch("nanobot.config.loader.load_config", return_value=mock_config):
            result = bot._check_nanobot_feishu_config()

            assert result is True

    def test_check_nanobot_feishu_config_disabled(self):
        """测试检测 nanobot 飞书配置未启用"""
        bot = FeishuBot(webhook=None)

        mock_feishu_config = Mock()
        mock_feishu_config.enabled = False
        mock_feishu_config.app_id = ""
        mock_feishu_config.app_secret = ""

        mock_channels = Mock()
        mock_channels.feishu = mock_feishu_config

        mock_config = Mock()
        mock_config.channels = mock_channels

        with patch("nanobot.config.loader.load_config", return_value=mock_config):
            result = bot._check_nanobot_feishu_config()

            assert result is False

    def test_check_nanobot_feishu_config_exception(self):
        """测试检测 nanobot 飞书配置异常"""
        bot = FeishuBot(webhook=None)

        with patch(
            "nanobot.config.loader.load_config",
            side_effect=Exception("Config load error"),
        ):
            result = bot._check_nanobot_feishu_config()

            assert result is False

    @pytest.mark.slow
    def test_get_feishu_channel_success(self):
        """测试获取 nanobot 飞书通道成功

        注意: 此测试涉及nanobot模块导入，执行较慢
        """
        bot = FeishuBot(webhook=None)

        mock_feishu_config = Mock()
        mock_channels = Mock()
        mock_channels.feishu = mock_feishu_config
        mock_config = Mock()
        mock_config.channels = mock_channels

        mock_channel = Mock()

        with patch("nanobot.config.loader.load_config", return_value=mock_config):
            with patch(
                "nanobot.channels.feishu.FeishuChannel", return_value=mock_channel
            ):
                with patch("nanobot.bus.MessageBus"):
                    channel = bot._get_feishu_channel()

                    assert channel is not None

    def test_get_feishu_channel_exception(self):
        """测试获取 nanobot 飞书通道异常"""
        bot = FeishuBot(webhook=None)

        with patch(
            "nanobot.config.loader.load_config",
            side_effect=Exception("Config error"),
        ):
            channel = bot._get_feishu_channel()

            assert channel is None


class TestTestConnection:
    """test_connection 函数测试"""

    def test_test_connection_success(self):
        """测试连接成功"""
        with patch("src.notify.feishu.FeishuBot") as mock_bot_class:
            mock_bot = Mock()
            mock_bot.send_text.return_value = {"code": 0, "msg": "success"}
            mock_bot_class.return_value = mock_bot

            result = test_connection("https://example.com/webhook")

            assert result["success"] is True

    def test_test_connection_failure(self):
        """测试连接失败"""
        with patch("src.notify.feishu.FeishuBot") as mock_bot_class:
            mock_bot = Mock()
            mock_bot.send_text.return_value = {"error": "Connection failed"}
            mock_bot_class.return_value = mock_bot

            result = test_connection("https://example.com/webhook")

            assert result["success"] is False
            assert "error" in result


class TestFeishuBotCardFormat:
    """飞书卡片消息格式测试"""

    def test_card_message_format(self):
        """测试卡片消息格式正确"""
        webhook = "https://example.com/webhook"
        bot = FeishuBot(webhook=webhook)

        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"code": 0, "msg": "success"}
            mock_post.return_value = mock_response

            bot.send_card("测试标题", "测试内容")

            call_args = mock_post.call_args
            payload = call_args.kwargs["json"]

            # 验证消息格式
            assert payload["msg_type"] == "interactive"
            assert "card" in payload
            assert payload["card"]["config"]["wide_screen_mode"] is True
            assert payload["card"]["header"]["template"] == "blue"

    def test_daily_report_card_format(self):
        """测试晨报卡片消息格式正确"""
        webhook = "https://example.com/webhook"
        bot = FeishuBot(webhook=webhook)

        report_data = {
            "date": "2024年3月15日",
            "greeting": "早上好！",
            "fitness_status": {"atl": 50, "ctl": 60, "tsb": 10, "status": "良好"},
            "training_advice": "保持训练。",
            "weekly_plan": [{"day": "周一", "plan": "休息", "is_today": False}],
        }

        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"code": 0, "msg": "success"}
            mock_post.return_value = mock_response

            bot.send_daily_report(report_data)

            call_args = mock_post.call_args
            payload = call_args.kwargs["json"]

            # 验证消息格式
            assert payload["msg_type"] == "interactive"
            assert "card" in payload
            assert "elements" in payload["card"]
            assert len(payload["card"]["elements"]) >= 4  # 至少包含问候语、体能状态、昨日训练、建议

    def test_daily_report_card_elements_content(self):
        """测试晨报卡片元素内容"""
        webhook = "https://example.com/webhook"
        bot = FeishuBot(webhook=webhook)

        report_data = {
            "date": "2024年3月15日",
            "greeting": "早上好！新的一天开始了。",
            "yesterday_run": {
                "distance_km": 10.5,
                "duration_min": 55.0,
                "tss": 85.5,
                "run_count": 1,
            },
            "fitness_status": {
                "atl": 45.2,
                "ctl": 52.8,
                "tsb": 7.6,
                "status": "状态正常",
            },
            "training_advice": "状态良好，可以进行中等强度训练。",
            "weekly_plan": [
                {"day": "周一", "plan": "休息", "is_today": False},
                {"day": "周二", "plan": "轻松跑", "is_today": True},
            ],
        }

        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"code": 0, "msg": "success"}
            mock_post.return_value = mock_response

            bot.send_daily_report(report_data)

            call_args = mock_post.call_args
            payload = call_args.kwargs["json"]
            elements = payload["card"]["elements"]

            # 验证元素内容
            element_contents = [e["text"]["content"] for e in elements]

            # 检查问候语
            assert any("早上好" in c for c in element_contents)

            # 检查体能状态
            assert any("体能状态" in c for c in element_contents)
            assert any("ATL" in c for c in element_contents)
            assert any("CTL" in c for c in element_contents)
            assert any("TSB" in c for c in element_contents)

            # 检查昨日训练
            assert any("昨日训练" in c for c in element_contents)

            # 检查今日建议
            assert any("今日建议" in c for c in element_contents)


class TestFeishuBotRetryConfig:
    """重试配置测试"""

    def test_max_retries_constant(self):
        """测试最大重试次数常量"""
        assert FeishuBot.MAX_RETRIES == 3

    def test_retry_delay_constant(self):
        """测试重试延迟常量"""
        assert FeishuBot.RETRY_DELAY == 1.0

    def test_retry_delay_applied(self):
        """测试重试延迟被应用"""
        webhook = "https://example.com/webhook"
        bot = FeishuBot(webhook=webhook)

        with patch("requests.post") as mock_post:
            with patch("src.notify.feishu.time.sleep") as mock_sleep:
                mock_post.side_effect = [
                    requests.exceptions.Timeout("Timeout"),
                    MagicMock(json=lambda: {"code": 0, "msg": "success"}),
                ]

                bot.send_text("测试消息")

                # 验证 sleep 被调用
                mock_sleep.assert_called_once_with(FeishuBot.RETRY_DELAY)
