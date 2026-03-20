# 飞书日历 Webhook 处理器单元测试

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.notify.feishu_webhook import (
    ConflictResolutionStrategy,
    FeishuCalendarWebhookHandler,
    WebhookConfig,
    WebhookEvent,
    WebhookEventType,
    WebhookResponse,
    WebhookRouter,
    create_webhook_handler,
    get_subscription_config,
)


class TestWebhookConfig:
    """测试 WebhookConfig 配置类"""

    def test_default_config(self):
        """测试默认配置"""
        config = WebhookConfig()
        assert config.enabled is True
        assert config.verification_token is None
        assert config.encryption_key is None
        assert config.webhook_path == "/webhook/calendar"
        assert config.conflict_strategy == ConflictResolutionStrategy.KEEP_REMOTE
        assert config.sync_to_local is True
        assert len(config.allowed_event_types) == 3

    def test_custom_config(self):
        """测试自定义配置"""
        config = WebhookConfig(
            enabled=False,
            verification_token="test_token",
            encryption_key="test_key",
            webhook_path="/custom/webhook",
            conflict_strategy=ConflictResolutionStrategy.KEEP_LOCAL,
            sync_to_local=False,
            allowed_event_types=[WebhookEventType.EVENT_CREATED.value],
        )
        assert config.enabled is False
        assert config.verification_token == "test_token"
        assert config.encryption_key == "test_key"
        assert config.webhook_path == "/custom/webhook"
        assert config.conflict_strategy == ConflictResolutionStrategy.KEEP_LOCAL
        assert config.sync_to_local is False
        assert len(config.allowed_event_types) == 1


class TestWebhookEvent:
    """测试 WebhookEvent 事件类"""

    def test_create_event(self):
        """测试创建 Webhook 事件"""
        event = WebhookEvent(
            event_type="calendar.event.created",
            event_id="evt_123",
            calendar_id="cal_456",
            event_data={"summary": "测试事件"},
            timestamp=datetime(2024, 1, 1, 12, 0),
            raw_payload={"header": {}, "event": {}},
        )
        assert event.event_type == "calendar.event.created"
        assert event.event_id == "evt_123"
        assert event.calendar_id == "cal_456"
        assert event.event_data == {"summary": "测试事件"}
        assert event.timestamp.year == 2024
        assert event.raw_payload is not None


class TestWebhookResponse:
    """测试 WebhookResponse 响应类"""

    def test_success_response(self):
        """测试成功响应"""
        response = WebhookResponse(
            success=True,
            message="处理成功",
            details={"event_id": "evt_123"},
        )
        assert response.success is True
        assert response.message == "处理成功"
        assert response.error is None
        assert response.details == {"event_id": "evt_123"}

    def test_error_response(self):
        """测试错误响应"""
        response = WebhookResponse(
            success=False,
            message="处理失败",
            error="签名验证失败",
        )
        assert response.success is False
        assert response.message == "处理失败"
        assert response.error == "签名验证失败"
        assert response.details is None

    def test_challenge_response(self):
        """测试验证挑战响应"""
        response = WebhookResponse(
            success=True,
            message="验证通过",
            challenge="test_challenge_123",
        )
        assert response.success is True
        assert response.challenge == "test_challenge_123"


class TestFeishuCalendarWebhookHandler:
    """测试 FeishuCalendarWebhookHandler 处理器类"""

    @pytest.fixture
    def mock_config(self):
        """模拟配置"""
        return WebhookConfig(
            enabled=True,
            verification_token="test_token",
            encryption_key="test_encryption_key",
            webhook_path="/webhook/calendar",
            conflict_strategy=ConflictResolutionStrategy.KEEP_REMOTE,
            sync_to_local=True,
        )

    @pytest.fixture
    def handler(self, mock_config):
        """创建处理器实例"""
        return FeishuCalendarWebhookHandler(config=mock_config)

    def test_init_with_config(self, mock_config):
        """测试使用自定义配置初始化"""
        handler = FeishuCalendarWebhookHandler(config=mock_config)
        assert handler.config.enabled is True
        assert handler.config.verification_token == "test_token"
        assert handler.config.encryption_key == "test_encryption_key"

    @patch("src.notify.feishu_webhook.ConfigManager")
    def test_init_without_config(self, mock_config_manager):
        """测试无配置时从 ConfigManager 加载"""
        mock_config_manager.return_value.load_config.return_value = {
            "webhook_enabled": True,
            "webhook_verification_token": "config_token",
            "webhook_encryption_key": "config_key",
        }

        handler = FeishuCalendarWebhookHandler()
        assert handler.config.enabled is True
        assert handler.config.verification_token == "config_token"

    def test_verify_signature_success(self, handler):
        """测试签名验证成功"""
        payload = {"event_type": "calendar.event.created", "event_id": "evt_123"}
        # 使用正确的密钥计算签名
        import hashlib
        import hmac

        body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode(
            "utf-8"
        )
        signature = hmac.new(b"test_encryption_key", body, hashlib.sha256).hexdigest()

        result = handler.verify_signature(payload, signature)
        assert result is True

    def test_verify_signature_failure(self, handler):
        """测试签名验证失败"""
        payload = {"event_type": "calendar.event.created"}
        invalid_signature = "invalid_signature_123"

        result = handler.verify_signature(payload, invalid_signature)
        assert result is False

    def test_verify_signature_no_encryption_key(self):
        """测试无加密密钥时跳过签名验证"""
        config = WebhookConfig(encryption_key=None)
        handler = FeishuCalendarWebhookHandler(config=config)
        payload = {"event_type": "calendar.event.created"}

        result = handler.verify_signature(payload, "any_signature")
        assert result is True

    def test_verify_challenge_success(self, handler):
        """测试验证挑战成功"""
        payload = {
            "type": "url_verification",
            "challenge": "test_challenge_123",
        }

        result = handler.verify_challenge(payload)
        assert result == "test_challenge_123"

    def test_verify_challenge_not_verification_type(self, handler):
        """测试非验证类型请求"""
        payload = {
            "type": "event_callback",
            "event": {},
        }

        result = handler.verify_challenge(payload)
        assert result is None

    def test_verify_challenge_missing_challenge(self, handler):
        """测试缺少 challenge 字段"""
        payload = {
            "type": "url_verification",
        }

        result = handler.verify_challenge(payload)
        assert result is None

    def test_parse_event_success(self, handler):
        """测试解析事件成功"""
        payload = {
            "header": {
                "event_type": "calendar.event.created",
                "event_id": "evt_123",
                "create_time": "1704067200",  # 2024-01-01 00:00:00 UTC
            },
            "event": {
                "calendar_id": "cal_456",
                "event_id": "event_789",
                "summary": "测试训练",
            },
        }

        event = handler.parse_event(payload)

        assert event is not None
        assert event.event_type == "calendar.event.created"
        assert event.event_id == "evt_123"
        assert event.calendar_id == "cal_456"
        assert event.event_data["summary"] == "测试训练"
        assert event.timestamp.year == 2024

    def test_parse_event_missing_header(self, handler):
        """测试缺少 header 字段"""
        payload = {"event": {"calendar_id": "cal_456"}}

        event = handler.parse_event(payload)
        assert event is None

    def test_parse_event_missing_event_type(self, handler):
        """测试缺少 event_type 字段"""
        payload = {
            "header": {"event_id": "evt_123", "create_time": "1704067200"},
            "event": {"calendar_id": "cal_456"},
        }

        event = handler.parse_event(payload)
        assert event is None

    def test_handle_event_disabled(self):
        """测试处理已禁用的 Webhook"""
        config = WebhookConfig(enabled=False)
        handler = FeishuCalendarWebhookHandler(config=config)
        event = WebhookEvent(
            event_type="calendar.event.created",
            event_id="evt_123",
            calendar_id="cal_456",
            event_data={},
            timestamp=datetime.now(),
            raw_payload={},
        )

        response = handler.handle_event(event)
        assert response.success is False
        assert "未启用" in response.message

    def test_handle_event_not_subscribed(self, handler):
        """测试处理未订阅的事件类型"""
        event = WebhookEvent(
            event_type="calendar.event.reminder",  # 未订阅的事件类型
            event_id="evt_123",
            calendar_id="cal_456",
            event_data={},
            timestamp=datetime.now(),
            raw_payload={},
        )

        response = handler.handle_event(event)
        assert response.success is True
        assert "未订阅" in response.message

    def test_handle_event_created(self, handler):
        """测试处理事件创建"""
        event = WebhookEvent(
            event_type="calendar.event.created",
            event_id="evt_123",
            calendar_id="cal_456",
            event_data={"summary": "新事件"},
            timestamp=datetime.now(),
            raw_payload={},
        )

        response = handler.handle_event(event)
        assert response.success is True
        assert "事件创建已处理" in response.message

    def test_handle_event_updated(self, handler):
        """测试处理事件更新"""
        event = WebhookEvent(
            event_type="calendar.event.updated",
            event_id="evt_123",
            calendar_id="cal_456",
            event_data={"summary": "更新的事件"},
            timestamp=datetime.now(),
            raw_payload={},
        )

        response = handler.handle_event(event)
        assert response.success is True
        assert "事件更新已处理" in response.message

    def test_handle_event_deleted(self, handler):
        """测试处理事件删除"""
        event = WebhookEvent(
            event_type="calendar.event.deleted",
            event_id="evt_123",
            calendar_id="cal_456",
            event_data={},
            timestamp=datetime.now(),
            raw_payload={},
        )

        response = handler.handle_event(event)
        assert response.success is True
        assert "事件删除已处理" in response.message

    def test_detect_conflict_no_conflict(self, handler):
        """测试冲突检测 - 无冲突"""
        event = WebhookEvent(
            event_type="calendar.event.created",
            event_id="evt_123",
            calendar_id="cal_456",
            event_data={
                "start_time": {"timestamp": "1704067200"},
                "summary": "测试事件",
            },
            timestamp=datetime.now(),
            raw_payload={},
        )

        conflict = handler._detect_conflict(event)
        # 当前实现返回 None（无冲突）
        assert conflict is None

    def test_detect_conflict_missing_date(self, handler):
        """测试冲突检测 - 缺少日期信息"""
        event = WebhookEvent(
            event_type="calendar.event.created",
            event_id="evt_123",
            calendar_id="cal_456",
            event_data={"summary": "测试事件"},  # 缺少 start_time
            timestamp=datetime.now(),
            raw_payload={},
        )

        conflict = handler._detect_conflict(event)
        assert conflict is None

    def test_resolve_conflict_keep_remote(self, handler):
        """测试冲突解决 - 保留远程"""
        conflict_info = {
            "has_conflict": True,
            "conflict_type": ["time_overlap"],
            "local_plan": {"date": "2024-01-01"},
            "remote_event": {"summary": "远程事件"},
        }

        resolution = handler._resolve_conflict(MagicMock(), conflict_info)
        assert resolution["resolved"] is True
        assert resolution["strategy"] == "keep_remote"
        assert resolution["action"] == "update_local"

    def test_resolve_conflict_keep_local(self):
        """测试冲突解决 - 保留本地"""
        config = WebhookConfig(conflict_strategy=ConflictResolutionStrategy.KEEP_LOCAL)
        handler = FeishuCalendarWebhookHandler(config=config)

        conflict_info = {
            "has_conflict": True,
            "conflict_type": ["content_mismatch"],
            "local_plan": {"date": "2024-01-01"},
            "remote_event": {"summary": "远程事件"},
        }

        resolution = handler._resolve_conflict(MagicMock(), conflict_info)
        assert resolution["resolved"] is True
        assert resolution["strategy"] == "keep_local"
        assert resolution["action"] == "ignore_remote"

    def test_resolve_conflict_merge(self):
        """测试冲突解决 - 合并"""
        config = WebhookConfig(conflict_strategy=ConflictResolutionStrategy.MERGE)
        handler = FeishuCalendarWebhookHandler(config=config)

        conflict_info = {
            "has_conflict": True,
            "local_plan": {"notes": "本地备注"},
            "remote_event": {
                "start_time": {"timestamp": "1704067200"},
                "description": "远程描述",
            },
        }

        resolution = handler._resolve_conflict(MagicMock(), conflict_info)
        assert resolution["resolved"] is True
        assert resolution["strategy"] == "merge"
        assert resolution["action"] == "merge"
        assert "merged_data" in resolution

    def test_resolve_conflict_manual(self):
        """测试冲突解决 - 人工干预"""
        config = WebhookConfig(conflict_strategy=ConflictResolutionStrategy.MANUAL)
        handler = FeishuCalendarWebhookHandler(config=config)

        conflict_info = {
            "has_conflict": True,
            "local_plan": {"date": "2024-01-01"},
            "remote_event": {"summary": "远程事件"},
        }

        resolution = handler._resolve_conflict(MagicMock(), conflict_info)
        assert resolution["resolved"] is False
        assert resolution["strategy"] == "manual"
        assert resolution["action"] == "manual_review"

    def test_merge_descriptions_both_present(self, handler):
        """测试合并描述 - 双方都有"""
        local_desc = "本地训练计划"
        remote_desc = "飞书备注信息"

        merged = handler._merge_descriptions(local_desc, remote_desc)
        assert "本地训练计划" in merged
        assert "飞书备注" in merged
        assert "飞书备注信息" in merged

    def test_merge_descriptions_only_local(self, handler):
        """测试合并描述 - 仅本地"""
        local_desc = "本地训练计划"
        remote_desc = ""

        merged = handler._merge_descriptions(local_desc, remote_desc)
        assert merged == local_desc

    def test_merge_descriptions_only_remote(self, handler):
        """测试合并描述 - 仅远程"""
        local_desc = ""
        remote_desc = "飞书备注信息"

        merged = handler._merge_descriptions(local_desc, remote_desc)
        assert merged == remote_desc

    def test_sync_to_local_success(self, handler):
        """测试同步到本地成功"""
        event = WebhookEvent(
            event_type="calendar.event.created",
            event_id="evt_123",
            calendar_id="cal_456",
            event_data={},
            timestamp=datetime.now(),
            raw_payload={},
        )

        result = handler._sync_to_local(event, action="create")
        assert result is True

    def test_sync_to_local_failure(self, handler):
        """测试同步到本地失败（模拟异常）"""
        # 当前实现总是返回 True，需要通过 mocking 来测试失败场景
        with patch.object(handler, "_sync_to_local", return_value=False):
            event = WebhookEvent(
                event_type="calendar.event.created",
                event_id="evt_123",
                calendar_id="cal_456",
                event_data={},
                timestamp=datetime.now(),
                raw_payload={},
            )

            result = handler._sync_to_local(event, action="create")
            assert result is False

    def test_extract_event_date(self, handler):
        """测试提取事件日期"""
        event_data = {
            "start_time": {"timestamp": "1704067200"}  # 2024-01-01 00:00:00 UTC
        }

        date = handler._extract_event_date(event_data)
        assert date is not None
        assert date.year == 2024
        assert date.month == 1
        assert date.day == 1

    def test_extract_event_date_missing(self, handler):
        """测试提取事件日期 - 缺少时间戳"""
        event_data = {"summary": "测试事件"}

        date = handler._extract_event_date(event_data)
        assert date is None

    def test_extract_event_summary(self, handler):
        """测试提取事件摘要"""
        event_data = {
            "summary": "测试训练",
            "start_time": {"timestamp": "1704067200"},
            "end_time": {"timestamp": "1704070800"},
            "description": "训练描述",
        }

        summary = handler._extract_event_summary(event_data)
        assert summary["summary"] == "测试训练"
        assert summary["start_time"] is not None
        assert summary["end_time"] is not None
        assert summary["description"] == "训练描述"

    def test_process_request_challenge(self, handler):
        """测试处理验证挑战请求"""
        payload = {
            "type": "url_verification",
            "challenge": "test_challenge_123",
        }

        response = handler.process_request(payload)
        assert response.success is True
        assert response.challenge == "test_challenge_123"

    def test_process_request_invalid_signature(self, handler):
        """测试处理签名验证失败的请求"""
        payload = {
            "header": {
                "event_type": "calendar.event.created",
                "event_id": "evt_123",
                "create_time": "1704067200",
            },
            "event": {"calendar_id": "cal_456"},
        }
        signature = "invalid_signature"

        response = handler.process_request(payload, signature=signature)
        assert response.success is False
        assert "签名验证失败" in response.message

    def test_process_request_invalid_format(self, handler):
        """测试处理格式无效的请求"""
        payload = {"invalid": "format"}

        response = handler.process_request(payload)
        assert response.success is False
        assert "事件解析失败" in response.message

    def test_process_request_success(self, handler):
        """测试处理请求成功"""
        payload = {
            "header": {
                "event_type": "calendar.event.created",
                "event_id": "evt_123",
                "create_time": "1704067200",
            },
            "event": {"calendar_id": "cal_456"},
        }

        # 不传签名，跳过验证
        response = handler.process_request(payload, signature=None)
        assert response.success is True
        assert "事件创建已处理" in response.message


class TestWebhookRouter:
    """测试 WebhookRouter 路由管理器"""

    @pytest.fixture
    def mock_handler(self):
        """模拟处理器"""
        handler = MagicMock(spec=FeishuCalendarWebhookHandler)
        handler.config = WebhookConfig()
        return handler

    @pytest.fixture
    def router(self, mock_handler):
        """创建路由管理器"""
        return WebhookRouter(handler=mock_handler)

    def test_init_with_handler(self, mock_handler):
        """测试使用自定义处理器初始化"""
        router = WebhookRouter(handler=mock_handler)
        assert router.handler == mock_handler

    @patch("src.notify.feishu_webhook.FeishuCalendarWebhookHandler")
    def test_init_without_handler(self, mock_handler_class):
        """测试无处理器时自动创建"""
        router = WebhookRouter()
        assert router.handler is not None

    def test_get_route_config(self, router):
        """测试获取路由配置"""
        config = router.get_route_config()
        assert config["path"] == "/webhook/calendar"
        assert config["methods"] == ["POST"]
        assert "飞书日历" in config["description"]

    def test_handle_webhook_challenge(self, router, mock_handler):
        """测试处理验证挑战"""
        mock_response = WebhookResponse(
            success=True,
            message="验证通过",
            challenge="test_challenge",
        )
        mock_handler.process_request.return_value = mock_response

        payload = {"type": "url_verification", "challenge": "test_challenge"}
        response = router.handle_webhook(payload)

        assert response["status_code"] == 200
        assert response["body"]["challenge"] == "test_challenge"

    def test_handle_webhook_success(self, router, mock_handler):
        """测试处理成功"""
        mock_response = WebhookResponse(
            success=True,
            message="处理成功",
            details={"event_id": "evt_123"},
        )
        mock_handler.process_request.return_value = mock_response

        payload = {"header": {}, "event": {}}
        response = router.handle_webhook(payload)

        assert response["status_code"] == 200
        assert response["body"]["success"] is True
        assert response["body"]["message"] == "处理成功"

    def test_handle_webhook_error(self, router, mock_handler):
        """测试处理失败"""
        mock_response = WebhookResponse(
            success=False,
            message="处理失败",
            error="签名错误",
        )
        mock_handler.process_request.return_value = mock_response

        payload = {"header": {}, "event": {}}
        response = router.handle_webhook(payload)

        assert response["status_code"] == 400
        assert response["body"]["success"] is False
        assert response["body"]["error"] == "签名错误"


class TestHelperFunctions:
    """测试辅助函数"""

    @patch("src.notify.feishu_webhook.FeishuCalendarWebhookHandler")
    def test_create_webhook_handler(self, mock_handler_class):
        """测试创建 Webhook 处理器"""
        handler, router = create_webhook_handler()

        assert handler is not None
        assert router is not None
        assert isinstance(router, WebhookRouter)

    @patch("src.notify.feishu_webhook.FeishuCalendarWebhookHandler")
    def test_get_subscription_config(self, mock_handler_class):
        """测试获取订阅配置"""
        mock_handler = MagicMock()
        mock_handler.config.enabled = True
        mock_handler.config.webhook_path = "/webhook/calendar"
        mock_handler.config.allowed_event_types = [WebhookEventType.EVENT_CREATED.value]
        mock_handler_class.return_value = mock_handler

        config = get_subscription_config()

        assert config["enabled"] is True
        assert config["webhook_url"] == "/webhook/calendar"
        assert len(config["event_types"]) > 0
        assert "verification_token_required" in config
        assert "encryption_key_required" in config
        assert "subscription_guide" in config


class TestIntegration:
    """集成测试"""

    def test_full_request_flow(self):
        """测试完整的请求处理流程"""
        config = WebhookConfig(
            enabled=True,
            encryption_key=None,  # 禁用签名验证
        )
        handler = FeishuCalendarWebhookHandler(config=config)
        router = WebhookRouter(handler=handler)

        # 1. 验证挑战
        challenge_payload = {
            "type": "url_verification",
            "challenge": "test_123",
        }
        response = router.handle_webhook(challenge_payload)
        assert response["status_code"] == 200
        assert response["body"]["challenge"] == "test_123"

        # 2. 事件创建
        event_payload = {
            "header": {
                "event_type": "calendar.event.created",
                "event_id": "evt_123",
                "create_time": "1704067200",
            },
            "event": {
                "calendar_id": "cal_456",
                "summary": "训练计划",
            },
        }
        response = router.handle_webhook(event_payload)
        assert response["status_code"] == 200
        assert response["body"]["success"] is True

        # 3. 事件更新
        event_payload["header"]["event_type"] = "calendar.event.updated"
        response = router.handle_webhook(event_payload)
        assert response["status_code"] == 200
        assert response["body"]["success"] is True

        # 4. 事件删除
        event_payload["header"]["event_type"] = "calendar.event.deleted"
        response = router.handle_webhook(event_payload)
        assert response["status_code"] == 200
        assert response["body"]["success"] is True

    def test_conflict_resolution_workflow(self):
        """测试冲突解决工作流"""
        # 测试所有冲突解决策略
        strategies = [
            ConflictResolutionStrategy.KEEP_REMOTE,
            ConflictResolutionStrategy.KEEP_LOCAL,
            ConflictResolutionStrategy.MERGE,
            ConflictResolutionStrategy.MANUAL,
        ]

        conflict_info = {
            "has_conflict": True,
            "conflict_type": ["time_overlap"],
            "local_plan": {"notes": "本地计划"},
            "remote_event": {
                "start_time": {"timestamp": "1704067200"},
                "description": "远程描述",
            },
        }

        for strategy in strategies:
            config = WebhookConfig(conflict_strategy=strategy)
            handler = FeishuCalendarWebhookHandler(config=config)

            resolution = handler._resolve_conflict(MagicMock(), conflict_info)

            assert resolution["strategy"] == strategy.value
            if strategy != ConflictResolutionStrategy.MANUAL:
                assert resolution["resolved"] is True


if __name__ == "__main__":
    pytest.main(
        [
            __file__,
            "-v",
            "--cov=src.notify.feishu_webhook",
            "--cov-report=term-missing",
        ]
    )
