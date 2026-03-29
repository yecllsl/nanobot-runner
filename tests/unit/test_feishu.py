# 飞书通知单元测试
# 覆盖率目标：≥85%

from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from src.notify.feishu import FeishuAuth, FeishuBot, FeishuMessageAPI, test_connection


class TestFeishuBotInit:
    """FeishuBot 初始化测试"""

    def test_init_with_app_credentials(self):
        """测试初始化带应用凭证"""
        bot = FeishuBot(
            app_id="test_app_id",
            app_secret="test_app_secret",
            receive_id="test_user_id",
            receive_id_type="user_id",
        )
        assert bot.auth.app_id == "test_app_id"
        assert bot.auth.app_secret == "test_app_secret"
        assert bot.receive_id == "test_user_id"
        assert bot.receive_id_type == "user_id"

    def test_init_without_credentials(self):
        """测试初始化不带凭证，从配置加载"""
        with patch("src.notify.feishu.ConfigManager") as mock_config:
            mock_config_instance = Mock()
            mock_config_instance.get.side_effect = lambda key, default=None: {
                "feishu_app_id": "config_app_id",
                "feishu_app_secret": "config_app_secret",
                "feishu_receive_id": "config_user_id",
                "feishu_receive_id_type": "user_id",
            }.get(key, default)
            mock_config.return_value = mock_config_instance

            bot = FeishuBot()

            assert bot.auth.app_id == "config_app_id"
            assert bot.auth.app_secret == "config_app_secret"
            assert bot.receive_id == "config_user_id"

    def test_init_with_none_credentials(self):
        """测试初始化时凭证为 None"""
        with patch("src.notify.feishu.ConfigManager") as mock_config:
            mock_config_instance = Mock()
            mock_config_instance.get.return_value = None
            mock_config.return_value = mock_config_instance

            bot = FeishuBot()

            assert bot.auth.app_id is None
            assert bot.auth.app_secret is None
            assert bot.receive_id is None


class TestFeishuBotSendText:
    """发送文本消息测试"""

    def test_send_text_success(self):
        """测试发送文本消息成功"""
        bot = FeishuBot(
            app_id="test_app_id",
            app_secret="test_app_secret",
            receive_id="test_user_id",
        )

        with patch.object(bot.message_api, "send_text") as mock_send:
            mock_send.return_value = {
                "code": 0,
                "msg": "success",
                "data": {"message_id": "123"},
            }

            result = bot.send_text("测试消息")

            assert result.get("success") is True
            mock_send.assert_called_once_with(
                content="测试消息",
                receive_id="test_user_id",
                receive_id_type="user_id",
            )

    def test_send_text_no_credentials(self):
        """测试未配置凭证时发送文本消息"""
        with patch("src.notify.feishu.ConfigManager") as mock_config:
            mock_config_instance = Mock()
            mock_config_instance.get.return_value = None
            mock_config.return_value = mock_config_instance

            bot = FeishuBot()
            result = bot.send_text("测试消息")

            assert result.get("success") is False
            assert "未配置飞书应用凭证" in result.get("error", "")

    def test_send_text_no_receive_id(self):
        """测试未配置接收者 ID 时发送文本消息"""
        bot = FeishuBot(
            app_id="test_app_id",
            app_secret="test_app_secret",
            receive_id=None,
        )

        result = bot.send_text("测试消息")

        assert result.get("success") is False
        assert "未配置接收者 ID" in result.get("error", "")

    def test_send_text_with_special_characters(self):
        """测试发送包含特殊字符的消息"""
        bot = FeishuBot(
            app_id="test_app_id",
            app_secret="test_app_secret",
            receive_id="test_user_id",
        )

        message = "测试消息 with 特殊字符：@#$%^&*() 中文测试"

        with patch.object(bot.message_api, "send_text") as mock_send:
            mock_send.return_value = {"code": 0, "msg": "success"}
            mock_send.return_value = {
                "code": 0,
                "msg": "success",
                "data": {"message_id": "123"},
            }

            result = bot.send_text(message)

            assert result.get("success") is True


class TestFeishuBotSendCard:
    """发送卡片消息测试"""

    def test_send_card_success(self):
        """测试发送卡片消息成功"""
        bot = FeishuBot(
            app_id="test_app_id",
            app_secret="test_app_secret",
            receive_id="test_user_id",
        )

        with patch.object(bot.message_api, "send_card") as mock_send:
            mock_send.return_value = {
                "code": 0,
                "msg": "success",
                "data": {"message_id": "123"},
            }

            result = bot.send_card("标题", "内容")

            assert result.get("success") is True
            mock_send.assert_called_once()

    def test_send_card_no_credentials(self):
        """测试未配置凭证时发送卡片消息"""
        with patch("src.notify.feishu.ConfigManager") as mock_config:
            mock_config_instance = Mock()
            mock_config_instance.get.return_value = None
            mock_config.return_value = mock_config_instance

            bot = FeishuBot()
            result = bot.send_card("标题", "内容")

            assert result.get("success") is False
            assert "未配置飞书应用凭证" in result.get("error", "")

    def test_send_card_no_receive_id(self):
        """测试未配置接收者 ID 时发送卡片消息"""
        bot = FeishuBot(
            app_id="test_app_id",
            app_secret="test_app_secret",
            receive_id=None,
        )

        result = bot.send_card("标题", "内容")

        assert result.get("success") is False
        assert "未配置接收者 ID" in result.get("error", "")


class TestFeishuBotImportNotification:
    """导入通知测试"""

    def test_send_import_notification_success(self):
        """测试发送导入通知成功"""
        bot = FeishuBot(
            app_id="test_app_id",
            app_secret="test_app_secret",
            receive_id="test_user_id",
        )

        stats = {"total": 10, "added": 5, "skipped": 3, "errors": 2}

        with patch.object(bot, "send_card") as mock_send_card:
            mock_send_card.return_value = {
                "success": True,
                "data": {"message_id": "123"},
            }

            result = bot.send_import_notification(stats)

            assert result.get("success") is True
            mock_send_card.assert_called_once()

    def test_send_import_notification_with_errors(self):
        """测试发送包含错误的导入通知"""
        bot = FeishuBot(
            app_id="test_app_id",
            app_secret="test_app_secret",
            receive_id="test_user_id",
        )

        stats = {"total": 10, "added": 0, "skipped": 0, "errors": 10}

        with patch.object(bot, "send_card") as mock_send_card:
            mock_send_card.return_value = {
                "success": True,
                "data": {"message_id": "123"},
            }

            result = bot.send_import_notification(stats)

            assert result.get("success") is True

    def test_send_import_notification_empty(self):
        """测试发送空统计的导入通知"""
        bot = FeishuBot(
            app_id="test_app_id",
            app_secret="test_app_secret",
            receive_id="test_user_id",
        )

        stats = {}

        with patch.object(bot, "send_card") as mock_send_card:
            mock_send_card.return_value = {
                "success": True,
                "data": {"message_id": "123"},
            }

            result = bot.send_import_notification(stats)

            assert result.get("success") is True

    def test_send_import_notification_with_detailed_stats(self):
        """测试发送详细统计的导入通知"""
        bot = FeishuBot(
            app_id="test_app_id",
            app_secret="test_app_secret",
            receive_id="test_user_id",
        )

        stats = {
            "total": 100,
            "added": 50,
            "skipped": 45,
            "errors": 5,
        }

        with patch.object(bot, "send_card") as mock_send_card:
            mock_send_card.return_value = {
                "success": True,
                "data": {"message_id": "123"},
            }

            result = bot.send_import_notification(stats)

            assert result.get("success") is True


class TestFeishuBotDailyReport:
    """每日晨报测试"""

    def test_send_daily_report_success(self):
        """测试发送每日晨报成功"""
        bot = FeishuBot(
            app_id="test_app_id",
            app_secret="test_app_secret",
            receive_id="test_user_id",
        )

        report_data = {
            "date": "2024-01-01",
            "greeting": "早上好！",
            "yesterday_run": {
                "distance_km": 5.0,
                "duration_min": 30,
                "tss": 50,
                "run_count": 1,
            },
            "fitness_status": {
                "atl": 80,
                "ctl": 60,
                "tsb": 20,
                "status": "状态良好",
            },
            "training_advice": "建议进行轻松跑",
        }

        with patch.object(bot.message_api, "send_card") as mock_send:
            mock_send.return_value = {
                "code": 0,
                "msg": "success",
                "data": {"message_id": "123"},
            }

            result = bot.send_daily_report(report_data)

            assert result.get("success") is True
            mock_send.assert_called_once()

    def test_send_daily_report_no_yesterday_run(self):
        """测试发送无昨日训练的每日晨报"""
        bot = FeishuBot(
            app_id="test_app_id",
            app_secret="test_app_secret",
            receive_id="test_user_id",
        )

        report_data = {
            "date": "2024-01-01",
            "greeting": "早上好！",
            "fitness_status": {
                "atl": 80,
                "ctl": 60,
                "tsb": 20,
                "status": "状态良好",
            },
            "training_advice": "建议休息",
        }

        with patch.object(bot.message_api, "send_card") as mock_send:
            mock_send.return_value = {
                "code": 0,
                "msg": "success",
                "data": {"message_id": "123"},
            }

            result = bot.send_daily_report(report_data)

            assert result.get("success") is True

    def test_send_daily_report_empty_data(self):
        """测试发送空数据的每日晨报"""
        bot = FeishuBot(
            app_id="test_app_id",
            app_secret="test_app_secret",
            receive_id="test_user_id",
        )

        report_data = {}

        with patch.object(bot.message_api, "send_card") as mock_send:
            mock_send.return_value = {
                "code": 0,
                "msg": "success",
                "data": {"message_id": "123"},
            }

            result = bot.send_daily_report(report_data)

            assert result.get("success") is True

    def test_send_daily_report_no_credentials(self):
        """测试未配置凭证时发送每日晨报"""
        with patch("src.notify.feishu.ConfigManager") as mock_config:
            mock_config_instance = Mock()
            mock_config_instance.get.return_value = None
            mock_config.return_value = mock_config_instance

            bot = FeishuBot()
            result = bot.send_daily_report({})

            assert result.get("success") is False
            assert "未配置飞书推送渠道" in result.get("error", "")

    def test_send_daily_report_with_weekly_plan(self):
        """测试发送包含周计划的每日晨报"""
        bot = FeishuBot(
            app_id="test_app_id",
            app_secret="test_app_secret",
            receive_id="test_user_id",
        )

        report_data = {
            "date": "2024-01-01",
            "greeting": "早上好！",
            "fitness_status": {
                "atl": 80,
                "ctl": 60,
                "tsb": 20,
                "status": "状态良好",
            },
            "training_advice": "建议进行间歇跑",
            "weekly_plan": [
                {"day": "周一", "plan": "轻松跑 5km", "is_today": True},
                {"day": "周二", "plan": "间歇跑 8km", "is_today": False},
                {"day": "周三", "plan": "休息", "is_today": False},
            ],
        }

        with patch.object(bot.message_api, "send_card") as mock_send:
            mock_send.return_value = {
                "code": 0,
                "msg": "success",
                "data": {"message_id": "123"},
            }

            result = bot.send_daily_report(report_data)

            assert result.get("success") is True


class TestFeishuBotRetry:
    """重试机制测试"""

    def test_retry_on_timeout(self):
        """测试超时时重试"""
        bot = FeishuBot(
            app_id="test_app_id",
            app_secret="test_app_secret",
            receive_id="test_user_id",
        )

        call_count = 0

        def mock_send_text(content, receive_id, receive_id_type="user_id"):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RuntimeError("请求超时")
            return {"code": 0, "msg": "success"}

        with patch.object(bot.message_api, "send_text", side_effect=mock_send_text):
            result = bot.send_text("测试消息")

            assert result.get("success") is True
            assert call_count == 2  # 第一次失败，第二次成功

    def test_retry_on_connection_error(self):
        """测试连接错误时重试"""
        bot = FeishuBot(
            app_id="test_app_id",
            app_secret="test_app_secret",
            receive_id="test_user_id",
        )

        call_count = 0

        def mock_send_text(content, receive_id, receive_id_type="user_id"):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError("连接错误")
            return {"code": 0, "msg": "success"}

        with patch.object(bot.message_api, "send_text", side_effect=mock_send_text):
            result = bot.send_text("测试消息")

            assert result.get("success") is True
            assert call_count == 3

    def test_max_retries_exceeded(self):
        """测试超过最大重试次数"""
        bot = FeishuBot(
            app_id="test_app_id",
            app_secret="test_app_secret",
            receive_id="test_user_id",
        )

        def mock_send_text(content, receive_id, receive_id_type="user_id"):
            raise RuntimeError("持续失败")

        with patch.object(bot.message_api, "send_text", side_effect=mock_send_text):
            result = bot.send_text("测试消息")

            assert result.get("success") is False
            assert "已重试" in result.get("error", "")
            assert "3" in result.get("error", "")  # 验证重试次数

    def test_no_retry_on_success(self):
        """测试成功时不重试"""
        bot = FeishuBot(
            app_id="test_app_id",
            app_secret="test_app_secret",
            receive_id="test_user_id",
        )

        with patch.object(bot.message_api, "send_text") as mock_send:
            mock_send.return_value = {"code": 0, "msg": "success"}

            result = bot.send_text("测试消息")

            assert result.get("success") is True
            mock_send.assert_called_once()


class TestFeishuBotErrorHandling:
    """错误处理测试"""

    def test_request_failure(self):
        """测试请求失败"""
        bot = FeishuBot(
            app_id="test_app_id",
            app_secret="test_app_secret",
            receive_id="test_user_id",
        )

        def mock_send_text(content, receive_id, receive_id_type="user_id"):
            raise RuntimeError("API 调用失败")

        with patch.object(bot.message_api, "send_text", side_effect=mock_send_text):
            result = bot.send_text("测试消息")

            assert result.get("success") is False
            assert "API 调用失败" in result.get("error", "")

    def test_api_error_response(self):
        """测试 API 错误响应"""
        bot = FeishuBot(
            app_id="test_app_id",
            app_secret="test_app_secret",
            receive_id="test_user_id",
        )

        with patch.object(bot.message_api, "send_text") as mock_send:
            mock_send.side_effect = RuntimeError("飞书 API 调用失败")

            result = bot.send_text("测试消息")

            assert result.get("success") is False

    def test_request_timeout_exception(self):
        """测试请求超时异常"""
        bot = FeishuBot(
            app_id="test_app_id",
            app_secret="test_app_secret",
            receive_id="test_user_id",
        )

        with patch.object(bot.message_api, "send_text") as mock_send:
            mock_send.side_effect = RuntimeError("飞书 API 请求超时")

            result = bot.send_text("测试消息")

            assert result.get("success") is False

    def test_request_connection_error_exception(self):
        """测试请求连接错误异常"""
        bot = FeishuBot(
            app_id="test_app_id",
            app_secret="test_app_secret",
            receive_id="test_user_id",
        )

        with patch.object(bot.message_api, "send_text") as mock_send:
            mock_send.side_effect = RuntimeError("飞书 API 请求异常")

            result = bot.send_text("测试消息")

            assert result.get("success") is False


class TestFeishuAuth:
    """FeishuAuth 认证测试"""

    def test_get_access_token_success(self):
        """测试成功获取访问令牌"""
        auth = FeishuAuth(app_id="test_app_id", app_secret="test_app_secret")

        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "code": 0,
                "tenant_access_token": "test_token",
            }
            mock_post.return_value = mock_response

            token = auth.get_token()

            assert token == "test_token"

    def test_get_access_token_failure(self):
        """测试获取访问令牌失败"""
        auth = FeishuAuth(app_id="test_app_id", app_secret="test_app_secret")

        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "code": 99991661,
                "msg": "app_access_token 无效",
            }
            mock_post.return_value = mock_response

            with pytest.raises(RuntimeError):
                auth.get_token()

    def test_is_configured(self):
        """测试检查是否已配置"""
        auth = FeishuAuth(app_id="test_app_id", app_secret="test_app_secret")
        assert auth.is_configured() is True

        auth_unconfigured = FeishuAuth(app_id=None, app_secret=None)
        assert auth_unconfigured.is_configured() is False


class TestFeishuMessageAPI:
    """FeishuMessageAPI 消息 API 测试"""

    def test_send_text_success(self):
        """测试发送文本消息成功"""
        auth = MagicMock()
        auth.get_token.return_value = "test_token"
        api = FeishuMessageAPI(auth=auth)

        with patch.object(api, "_request") as mock_request:
            mock_request.return_value = {
                "code": 0,
                "msg": "success",
                "data": {"message_id": "123"},
            }

            result = api.send_text(
                content="测试消息",
                receive_id="test_user_id",
                receive_id_type="user_id",
            )

            assert result.get("code") == 0
            assert result.get("data", {}).get("message_id") == "123"

    def test_send_card_success(self):
        """测试发送卡片消息成功"""
        auth = MagicMock()
        auth.get_token.return_value = "test_token"
        api = FeishuMessageAPI(auth=auth)

        with patch.object(api, "_request") as mock_request:
            mock_request.return_value = {
                "code": 0,
                "msg": "success",
                "data": {"message_id": "123"},
            }

            result = api.send_card(
                card_content={"config": {}},
                receive_id="test_user_id",
                receive_id_type="user_id",
            )

            assert result.get("code") == 0


class TestTestConnection:
    """test_connection 函数测试"""

    def test_test_connection_success(self):
        """测试连接测试成功"""
        with patch("src.notify.feishu.FeishuBot") as MockBot:
            mock_bot = MagicMock()
            mock_bot.send_text.return_value = {"success": True, "data": {}}
            MockBot.return_value = mock_bot

            result = test_connection(
                app_id="test_app_id",
                app_secret="test_app_secret",
                receive_id="test_user_id",
            )

            assert result.get("success") is True

    def test_test_connection_failure(self):
        """测试连接测试失败"""
        with patch("src.notify.feishu.FeishuBot") as MockBot:
            mock_bot = MagicMock()
            mock_bot.send_text.return_value = {
                "success": False,
                "error": "配置错误",
            }
            MockBot.return_value = mock_bot

            result = test_connection(
                app_id="test_app_id",
                app_secret="test_app_secret",
                receive_id="test_user_id",
            )

            assert result.get("success") is False
            assert result.get("error") == "配置错误"


class TestFeishuBotCardFormat:
    """卡片消息格式测试"""

    def test_card_message_format(self):
        """测试卡片消息格式"""
        bot = FeishuBot(
            app_id="test_app_id",
            app_secret="test_app_secret",
            receive_id="test_user_id",
        )

        with patch.object(bot.message_api, "send_card") as mock_send:
            mock_send.return_value = {"code": 0, "msg": "success"}

            result = bot.send_card("测试标题", "测试内容")

            assert result.get("success") is True
            call_args = mock_send.call_args
            card_content = call_args[1]["card_content"]

            assert card_content["header"]["title"]["content"] == "测试标题"
            assert len(card_content["elements"]) == 1

    def test_daily_report_card_format(self):
        """测试每日晨报卡片格式"""
        bot = FeishuBot(
            app_id="test_app_id",
            app_secret="test_app_secret",
            receive_id="test_user_id",
        )

        report_data = {
            "date": "2024-01-01",
            "greeting": "早上好！",
            "fitness_status": {
                "atl": 80,
                "ctl": 60,
                "tsb": 20,
                "status": "状态良好",
            },
        }

        with patch.object(bot.message_api, "send_card") as mock_send:
            mock_send.return_value = {"code": 0, "msg": "success"}

            result = bot.send_daily_report(report_data)

            assert result.get("success") is True
            mock_send.assert_called_once()

    def test_daily_report_card_elements_content(self):
        """测试每日晨报卡片元素内容"""
        bot = FeishuBot(
            app_id="test_app_id",
            app_secret="test_app_secret",
            receive_id="test_user_id",
        )

        report_data = {
            "date": "2024-01-01",
            "greeting": "早上好！",
            "fitness_status": {
                "atl": 80,
                "ctl": 60,
                "tsb": 20,
                "status": "状态良好",
            },
            "training_advice": "建议进行轻松跑",
        }

        with patch.object(bot.message_api, "send_card") as mock_send:
            mock_send.return_value = {"code": 0, "msg": "success"}

            bot.send_daily_report(report_data)

            call_args = mock_send.call_args
            card_content = call_args[1]["card_content"]

            # 验证卡片包含必要的元素
            assert "elements" in card_content
            assert len(card_content["elements"]) >= 3  # 问候语、体能状态、训练建议


class TestFeishuBotRetryConfig:
    """重试配置测试"""

    def test_retry_delay_applied(self):
        """测试重试延迟应用"""
        bot = FeishuBot(
            app_id="test_app_id",
            app_secret="test_app_secret",
            receive_id="test_user_id",
        )

        call_times = []

        def mock_send(*args, **kwargs):
            call_times.append(__import__("time").time())
            raise RuntimeError("持续失败")

        with patch.object(bot.message_api, "send_text", side_effect=mock_send):
            result = bot.send_text("测试消息")

            assert result.get("success") is False

            # 验证调用间隔（至少 1 秒延迟）
            if len(call_times) > 1:
                for i in range(1, len(call_times)):
                    assert (
                        call_times[i] - call_times[i - 1] >= bot.RETRY_DELAY * 0.9
                    )  # 允许 10% 误差
