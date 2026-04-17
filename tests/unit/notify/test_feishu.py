"""飞书应用机器人单元测试"""

from unittest.mock import MagicMock, patch

import pytest
import requests

from src.core.models import OperationResult
from src.notify.feishu import FeishuAuth, FeishuBot, FeishuMessageAPI, verify_connection


class TestFeishuAuth:
    """测试飞书认证管理"""

    @pytest.fixture
    def mock_config(self):
        """创建 Mock ConfigManager"""
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda key: {
            "feishu_app_id": "test_app_id",
            "feishu_app_secret": "test_app_secret",
        }.get(key)
        return mock_config

    def test_init_with_config(self, mock_config):
        """测试使用配置初始化"""
        auth = FeishuAuth(config=mock_config)

        assert auth.app_id == "test_app_id"
        assert auth.app_secret == "test_app_secret"
        assert auth._access_token is None

    def test_init_with_credentials(self):
        """测试使用凭证初始化"""
        auth = FeishuAuth(app_id="custom_id", app_secret="custom_secret")

        assert auth.app_id == "custom_id"
        assert auth.app_secret == "custom_secret"

    @patch("src.notify.feishu.ConfigManager")
    def test_init_without_credentials(self, mock_config_manager):
        """测试无凭证初始化"""
        mock_config = MagicMock()
        mock_config.get.return_value = None
        mock_config_manager.return_value = mock_config

        auth = FeishuAuth()

        assert not auth.app_id
        assert not auth.app_secret

    @patch("src.notify.feishu.requests.post")
    def test_get_access_token_success(self, mock_post, mock_config):
        """测试成功获取访问令牌"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "tenant_access_token": "test_token",
            "expire": 7200,
        }
        mock_post.return_value = mock_response

        auth = FeishuAuth(config=mock_config)
        token = auth.get_token()

        assert token == "test_token"
        assert auth._access_token == "test_token"
        assert auth._token_expire_time is not None

    @patch("src.notify.feishu.requests.post")
    def test_get_access_token_failure(self, mock_post, mock_config):
        """测试获取访问令牌失败"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 10001,
            "msg": "Invalid app_id or app_secret",
        }
        mock_post.return_value = mock_response

        auth = FeishuAuth(config=mock_config)

        with pytest.raises(RuntimeError, match="获取飞书访问令牌失败"):
            auth.get_token()

    @patch("src.notify.feishu.requests.post")
    def test_get_access_token_cached(self, mock_post, mock_config):
        """测试令牌缓存"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "tenant_access_token": "test_token",
            "expire": 7200,
        }
        mock_post.return_value = mock_response

        auth = FeishuAuth(config=mock_config)

        token1 = auth.get_token()
        token2 = auth.get_token()

        assert token1 == token2
        assert mock_post.call_count == 1

    @patch("src.notify.feishu.requests.post")
    def test_get_access_token_request_exception(self, mock_post, mock_config):
        """测试请求异常"""
        mock_post.side_effect = requests.exceptions.RequestException("Network error")

        auth = FeishuAuth(config=mock_config)

        with pytest.raises(RuntimeError, match="获取飞书访问令牌请求异常"):
            auth.get_token()

    def test_is_configured_true(self, mock_config):
        """测试已配置"""
        auth = FeishuAuth(config=mock_config)
        assert auth.is_configured() is True

    @patch("src.notify.feishu.ConfigManager")
    def test_is_configured_false(self, mock_config_manager):
        """测试未配置"""
        mock_config = MagicMock()
        mock_config.get.return_value = None
        mock_config_manager.return_value = mock_config

        auth = FeishuAuth()
        assert auth.is_configured() is False


class TestFeishuMessageAPI:
    """测试飞书消息 API"""

    @pytest.fixture
    def mock_auth(self):
        """创建 Mock 认证管理器"""
        mock_auth = MagicMock()
        mock_auth.get_token.return_value = "test_token"
        return mock_auth

    @pytest.fixture
    def message_api(self, mock_auth):
        """创建消息 API 实例"""
        return FeishuMessageAPI(auth=mock_auth)

    @patch("src.notify.feishu.requests.request")
    def test_send_text_success(self, mock_request, message_api, mock_auth):
        """测试发送文本消息成功"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {"message_id": "msg_123"},
        }
        mock_request.return_value = mock_response

        result = message_api.send_text(
            content="Test message",
            receive_id="user_123",
            receive_id_type="user_id",
        )

        assert result["code"] == 0
        assert result["data"]["message_id"] == "msg_123"
        mock_auth.get_token.assert_called_once()

    @patch("src.notify.feishu.requests.request")
    def test_send_card_success(self, mock_request, message_api, mock_auth):
        """测试发送卡片消息成功"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {"message_id": "msg_456"},
        }
        mock_request.return_value = mock_response

        card_content = {
            "config": {"wide_screen_mode": True},
            "header": {"title": {"tag": "plain_text", "content": "Test Card"}},
        }

        result = message_api.send_card(
            card_content=card_content,
            receive_id="user_123",
            receive_id_type="user_id",
        )

        assert result["code"] == 0
        assert result["data"]["message_id"] == "msg_456"

    @patch("src.notify.feishu.requests.request")
    def test_request_failure(self, mock_request, message_api):
        """测试请求失败"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 10001,
            "msg": "Invalid parameter",
        }
        mock_request.return_value = mock_response

        with pytest.raises(RuntimeError, match="飞书 API 调用失败"):
            message_api.send_text(
                content="Test message",
                receive_id="user_123",
                receive_id_type="user_id",
            )

    @patch("src.notify.feishu.requests.request")
    def test_request_timeout(self, mock_request, message_api):
        """测试请求超时"""
        mock_request.side_effect = requests.exceptions.Timeout()

        with pytest.raises(RuntimeError, match="飞书 API 请求超时"):
            message_api.send_text(
                content="Test message",
                receive_id="user_123",
                receive_id_type="user_id",
            )

    @patch("src.notify.feishu.requests.request")
    def test_request_exception(self, mock_request, message_api):
        """测试请求异常"""
        mock_request.side_effect = requests.exceptions.RequestException("Network error")

        with pytest.raises(RuntimeError, match="飞书 API 请求异常"):
            message_api.send_text(
                content="Test message",
                receive_id="user_123",
                receive_id_type="user_id",
            )


class TestFeishuBot:
    """测试飞书应用机器人"""

    @pytest.fixture
    def mock_config(self):
        """创建 Mock ConfigManager"""
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda key, default=None: {
            "feishu_app_id": "test_app_id",
            "feishu_app_secret": "test_app_secret",
            "feishu_receive_id": "user_123",
            "feishu_receive_id_type": "user_id",
        }.get(key, default)
        return mock_config

    @pytest.fixture
    def bot(self, mock_config):
        """创建机器人实例"""
        return FeishuBot(config=mock_config)

    def test_init_with_config(self, mock_config):
        """测试使用配置初始化"""
        bot = FeishuBot(config=mock_config)

        assert bot.receive_id == "user_123"
        assert bot.receive_id_type == "user_id"
        assert bot.auth is not None
        assert bot.message_api is not None

    def test_init_with_credentials(self):
        """测试使用凭证初始化"""
        bot = FeishuBot(
            app_id="custom_id",
            app_secret="custom_secret",
            receive_id="custom_user",
            receive_id_type="chat_id",
        )

        assert bot.receive_id == "custom_user"
        assert bot.receive_id_type == "chat_id"

    @patch("src.notify.feishu.requests.post")
    @patch("src.notify.feishu.requests.request")
    def test_send_text_success(self, mock_request, mock_post, bot):
        """测试发送文本消息成功"""
        mock_token_response = MagicMock()
        mock_token_response.json.return_value = {
            "code": 0,
            "tenant_access_token": "test_token",
        }
        mock_post.return_value = mock_token_response

        mock_message_response = MagicMock()
        mock_message_response.json.return_value = {
            "code": 0,
            "data": {"message_id": "msg_123"},
        }
        mock_request.return_value = mock_message_response

        result = bot.send_text("Test message")

        assert result.success is True
        assert result.data is not None

    @patch("src.notify.feishu.ConfigManager")
    def test_send_text_no_credentials(self, mock_config_manager):
        """测试发送文本消息无凭证"""
        mock_config = MagicMock()
        mock_config.get.return_value = None
        mock_config_manager.return_value = mock_config

        bot = FeishuBot()
        result = bot.send_text("Test message")

        assert result.success is False
        assert "未配置飞书应用凭证" in result.error

    def test_send_text_no_receive_id(self, mock_config):
        """测试发送文本消息无接收者ID"""
        mock_config.get.side_effect = lambda key, default=None: {
            "feishu_app_id": "test_app_id",
            "feishu_app_secret": "test_app_secret",
            "feishu_receive_id": None,
            "feishu_receive_id_type": "user_id",
        }.get(key, default)

        bot = FeishuBot(config=mock_config)
        result = bot.send_text("Test message")

        assert result.success is False
        assert "未配置接收者 ID" in result.error

    @patch("src.notify.feishu.requests.post")
    @patch("src.notify.feishu.requests.request")
    def test_send_card_success(self, mock_request, mock_post, bot):
        """测试发送卡片消息成功"""
        mock_token_response = MagicMock()
        mock_token_response.json.return_value = {
            "code": 0,
            "tenant_access_token": "test_token",
        }
        mock_post.return_value = mock_token_response

        mock_message_response = MagicMock()
        mock_message_response.json.return_value = {
            "code": 0,
            "data": {"message_id": "msg_456"},
        }
        mock_request.return_value = mock_message_response

        result = bot.send_card("Test Title", "Test Content")

        assert result.success is True
        assert result.data is not None

    @patch("src.notify.feishu.requests.post")
    @patch("src.notify.feishu.requests.request")
    def test_send_import_notification(self, mock_request, mock_post, bot):
        """测试发送导入通知"""
        mock_token_response = MagicMock()
        mock_token_response.json.return_value = {
            "code": 0,
            "tenant_access_token": "test_token",
        }
        mock_post.return_value = mock_token_response

        mock_message_response = MagicMock()
        mock_message_response.json.return_value = {
            "code": 0,
            "data": {"message_id": "msg_789"},
        }
        mock_request.return_value = mock_message_response

        stats = {
            "total": 10,
            "added": 8,
            "skipped": 1,
            "errors": 1,
        }

        result = bot.send_import_notification(stats)

        assert result.success is True

    @patch("src.notify.feishu.requests.post")
    @patch("src.notify.feishu.requests.request")
    def test_send_daily_report(self, mock_request, mock_post, bot):
        """测试发送每日晨报"""
        mock_token_response = MagicMock()
        mock_token_response.json.return_value = {
            "code": 0,
            "tenant_access_token": "test_token",
        }
        mock_post.return_value = mock_token_response

        mock_message_response = MagicMock()
        mock_message_response.json.return_value = {
            "code": 0,
            "data": {"message_id": "msg_daily"},
        }
        mock_request.return_value = mock_message_response

        report_data = {
            "date": "2024-01-15",
            "greeting": "早上好！",
            "fitness_status": {
                "atl": 50.0,
                "ctl": 60.0,
                "tsb": 10.0,
                "status": "良好",
            },
            "yesterday_run": {
                "distance_km": 10.0,
                "duration_min": 60,
                "tss": 100,
                "run_count": 1,
            },
            "training_advice": "今天可以进行轻松跑",
            "weekly_plan": [
                {"day": "周一", "plan": "轻松跑", "is_today": True},
                {"day": "周二", "plan": "间歇跑", "is_today": False},
            ],
        }

        result = bot.send_daily_report(report_data)

        assert result.success is True

    @patch("src.notify.feishu.requests.post")
    @patch("src.notify.feishu.requests.request")
    def test_send_with_retry_success_after_retry(self, mock_request, mock_post, bot):
        """测试重试成功"""
        mock_token_response = MagicMock()
        mock_token_response.json.return_value = {
            "code": 0,
            "tenant_access_token": "test_token",
        }
        mock_post.return_value = mock_token_response

        call_count = [0]

        def mock_request_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] < 3:
                mock_response = MagicMock()
                mock_response.json.return_value = {
                    "code": 10001,
                    "msg": "Temporary error",
                }
                return mock_response
            else:
                mock_response = MagicMock()
                mock_response.json.return_value = {
                    "code": 0,
                    "data": {"message_id": "msg_retry"},
                }
                return mock_response

        mock_request.side_effect = mock_request_side_effect

        result = bot.send_text("Test message")

        assert result.success is True

    @patch("src.notify.feishu.requests.post")
    @patch("src.notify.feishu.requests.request")
    def test_send_with_retry_max_retries(self, mock_request, mock_post, bot):
        """测试达到最大重试次数"""
        mock_token_response = MagicMock()
        mock_token_response.json.return_value = {
            "code": 0,
            "tenant_access_token": "test_token",
        }
        mock_post.return_value = mock_token_response

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 10001,
            "msg": "Permanent error",
        }
        mock_request.return_value = mock_response

        result = bot.send_text("Test message")

        assert result.success is False
        assert "已重试" in result.error


class TestTestConnection:
    """测试连接测试函数"""

    @patch("src.notify.feishu.FeishuBot")
    @patch("src.notify.feishu.requests.post")
    @patch("src.notify.feishu.requests.request")
    def test_test_connection_success(self, mock_request, mock_post, mock_feishu_bot):
        """测试连接成功"""
        mock_token_response = MagicMock()
        mock_token_response.json.return_value = {
            "code": 0,
            "tenant_access_token": "test_token",
        }
        mock_post.return_value = mock_token_response

        mock_message_response = MagicMock()
        mock_message_response.json.return_value = {
            "code": 0,
            "data": {"message_id": "msg_test"},
        }
        mock_request.return_value = mock_message_response

        mock_bot = MagicMock()
        mock_bot.send_text.return_value = OperationResult(
            success=True, message="测试成功"
        )
        mock_feishu_bot.return_value = mock_bot

        result = verify_connection(
            app_id="test_app_id",
            app_secret="test_app_secret",
            receive_id="user_123",
        )

        assert result.success is True

    @patch("src.notify.feishu.FeishuBot")
    def test_test_connection_failure(self, mock_feishu_bot):
        """测试连接失败"""
        mock_bot = MagicMock()
        mock_bot.send_text.return_value = OperationResult(
            success=False, error="未配置飞书应用凭证"
        )
        mock_feishu_bot.return_value = mock_bot

        result = verify_connection()

        assert result.success is False
        assert result.error is not None


@patch("src.notify.feishu.FeishuBot")
def test_verify_connection_function(mock_feishu_bot):
    """测试连接验证函数"""
    mock_bot = MagicMock()
    mock_bot.send_text.return_value = OperationResult(success=True, message="测试成功")
    mock_feishu_bot.return_value = mock_bot

    result = verify_connection(
        app_id="test_app_id",
        app_secret="test_app_secret",
        receive_id="user_123",
    )

    assert result.success is True
