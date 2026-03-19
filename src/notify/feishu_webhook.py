# 飞书日历 Webhook 处理器
# 实现飞书日历事件的反向同步与冲突解决

import hashlib
import hmac
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from src.core.config import ConfigManager
from src.core.training_plan import DailyPlan, WorkoutType

logger = logging.getLogger(__name__)


class WebhookEventType(str, Enum):
    """Webhook 事件类型"""

    EVENT_CREATED = "calendar.event.created"
    EVENT_UPDATED = "calendar.event.updated"
    EVENT_DELETED = "calendar.event.deleted"
    EVENT_REMINDER = "calendar.event.reminder"
    CHALLENGE = "challenge"  # 飞书验证挑战


class ConflictResolutionStrategy(str, Enum):
    """冲突解决策略"""

    KEEP_REMOTE = "keep_remote"  # 保留飞书日历的修改
    KEEP_LOCAL = "keep_local"  # 保留本地训练计划
    MERGE = "merge"  # 合并双方数据
    MANUAL = "manual"  # 需要人工干预


@dataclass
class WebhookConfig:
    """Webhook 配置"""

    enabled: bool = True
    verification_token: Optional[str] = None  # 飞书验证 Token
    encryption_key: Optional[str] = None  # 加密密钥
    webhook_path: str = "/webhook/calendar"
    allowed_event_types: List[str] = field(
        default_factory=lambda: [
            WebhookEventType.EVENT_CREATED.value,
            WebhookEventType.EVENT_UPDATED.value,
            WebhookEventType.EVENT_DELETED.value,
        ]
    )
    conflict_strategy: ConflictResolutionStrategy = (
        ConflictResolutionStrategy.KEEP_REMOTE
    )
    sync_to_local: bool = True  # 是否同步到本地


@dataclass
class WebhookEvent:
    """Webhook 事件"""

    event_type: str
    event_id: str
    calendar_id: str
    event_data: Dict[str, Any]
    timestamp: datetime
    raw_payload: Dict[str, Any]


@dataclass
class WebhookResponse:
    """Webhook 响应"""

    success: bool
    message: str
    challenge: Optional[str] = None  # 飞书验证挑战响应
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class FeishuCalendarWebhookHandler:
    """
    飞书日历 Webhook 处理器

    职责：
    1. 接收并验证飞书日历 Webhook 请求
    2. 解析事件类型并路由到对应处理器
    3. 检测并解决日历事件与本地训练计划的冲突
    4. 将变更同步到本地存储
    """

    def __init__(self, config: Optional[WebhookConfig] = None):
        """
        初始化 Webhook 处理器

        Args:
            config: Webhook 配置，不指定则从配置文件读取
        """
        self.config = config or self._load_config()
        logger.info("飞书日历 Webhook 处理器初始化完成")

    def _load_config(self) -> WebhookConfig:
        """从配置文件加载配置"""
        config_manager = ConfigManager()
        config_dict = config_manager.load_config()

        return WebhookConfig(
            enabled=config_dict.get("webhook_enabled", True),
            verification_token=config_dict.get("webhook_verification_token"),
            encryption_key=config_dict.get("webhook_encryption_key"),
            webhook_path=config_dict.get("webhook_path", "/webhook/calendar"),
            allowed_event_types=config_dict.get(
                "webhook_allowed_events",
                [
                    WebhookEventType.EVENT_CREATED.value,
                    WebhookEventType.EVENT_UPDATED.value,
                    WebhookEventType.EVENT_DELETED.value,
                ],
            ),
            conflict_strategy=ConflictResolutionStrategy(
                config_dict.get("webhook_conflict_strategy", "keep_remote")
            ),
            sync_to_local=config_dict.get("webhook_sync_to_local", True),
        )

    def verify_signature(self, payload: Dict[str, Any], signature: str) -> bool:
        """
        验证飞书请求签名

        Args:
            payload: 请求负载
            signature: 签名值

        Returns:
            bool: 签名是否有效

        注意：
        - 飞书使用 SHA256 HMAC 算法进行签名
        - 签名计算：HMAC_SHA256(encryption_key, payload_body)
        """
        if not self.config.encryption_key:
            logger.warning("未配置加密密钥，跳过签名验证")
            return True

        try:
            # 获取请求体（JSON 字符串）
            body = json.dumps(payload, separators=(",", ":"), sort_keys=True)
            body_bytes = body.encode("utf-8")

            # 计算签名
            key_bytes = self.config.encryption_key.encode("utf-8")
            computed_signature = hmac.new(
                key_bytes, body_bytes, hashlib.sha256
            ).hexdigest()

            # 比较签名
            is_valid = hmac.compare_digest(computed_signature, signature)

            if not is_valid:
                logger.error("签名验证失败")

            return is_valid

        except Exception as e:
            logger.error(f"签名验证异常：{e}", exc_info=True)
            return False

    def verify_challenge(self, payload: Dict[str, Any]) -> Optional[str]:
        """
        处理飞书验证挑战

        Args:
            payload: 包含 challenge 的请求负载

        Returns:
            str: challenge 值，用于响应飞书验证

        注意：
        - 飞书在订阅 Webhook 时会发送验证请求
        - 需要原样返回 challenge 字段
        """
        if payload.get("type") == "url_verification":
            challenge = payload.get("challenge")
            if challenge:
                logger.info(f"收到飞书验证挑战：{challenge}")
                return challenge
            else:
                logger.error("验证挑战缺少 challenge 字段")
                return None
        return None

    def parse_event(self, payload: Dict[str, Any]) -> Optional[WebhookEvent]:
        """
        解析 Webhook 事件

        Args:
            payload: Webhook 请求负载

        Returns:
            WebhookEvent: 解析后的事件，解析失败返回 None

        飞书日历事件格式：
        {
            "header": {
                "event_type": "calendar.event.created",
                "event_id": "evt_xxx",
                "create_time": "1234567890"
            },
            "event": {
                "calendar_id": "cal_xxx",
                "event_id": "event_xxx",
                "summary": "训练标题",
                "start_time": {...},
                "end_time": {...},
                ...
            }
        }
        """
        try:
            header = payload.get("header", {})
            event_data = payload.get("event", {})

            event_type = header.get("event_type")
            event_id = header.get("event_id")
            create_time = header.get("create_time")

            if not all([event_type, event_id, event_data]):
                logger.error(f"Webhook 事件格式无效：{payload}")
                return None

            # 解析时间戳
            timestamp = (
                datetime.fromtimestamp(int(create_time))
                if create_time
                else datetime.now()
            )

            return WebhookEvent(
                event_type=event_type,
                event_id=event_id,
                calendar_id=event_data.get("calendar_id", ""),
                event_data=event_data,
                timestamp=timestamp,
                raw_payload=payload,
            )

        except Exception as e:
            logger.error(f"解析 Webhook 事件失败：{e}", exc_info=True)
            return None

    def handle_event(self, event: WebhookEvent) -> WebhookResponse:
        """
        处理 Webhook 事件

        Args:
            event: 解析后的 Webhook 事件

        Returns:
            WebhookResponse: 处理结果
        """
        if not self.config.enabled:
            return WebhookResponse(
                success=False,
                message="Webhook 功能未启用",
                error="功能已禁用",
            )

        # 检查事件类型是否允许
        if event.event_type not in self.config.allowed_event_types:
            logger.info(f"忽略未订阅的事件类型：{event.event_type}")
            return WebhookResponse(
                success=True,
                message=f"事件类型 {event.event_type} 未订阅，已忽略",
            )

        try:
            # 路由到对应的处理器
            if event.event_type == WebhookEventType.EVENT_CREATED.value:
                return self._handle_event_created(event)
            elif event.event_type == WebhookEventType.EVENT_UPDATED.value:
                return self._handle_event_updated(event)
            elif event.event_type == WebhookEventType.EVENT_DELETED.value:
                return self._handle_event_deleted(event)
            else:
                logger.warning(f"未知的事件类型：{event.event_type}")
                return WebhookResponse(
                    success=False,
                    message=f"未知的事件类型：{event.event_type}",
                )

        except Exception as e:
            logger.error(f"处理 Webhook 事件失败：{e}", exc_info=True)
            return WebhookResponse(
                success=False,
                message="事件处理失败",
                error=str(e),
            )

    def _handle_event_created(self, event: WebhookEvent) -> WebhookResponse:
        """
        处理事件创建

        Args:
            event: Webhook 事件

        Returns:
            WebhookResponse: 处理结果
        """
        logger.info(f"处理事件创建：{event.event_id}")

        # 检测是否与本地训练计划冲突
        conflict_info = self._detect_conflict(event)

        if conflict_info and conflict_info["has_conflict"]:
            # 根据策略解决冲突
            resolution = self._resolve_conflict(event, conflict_info)
            if not resolution["resolved"]:
                return WebhookResponse(
                    success=False,
                    message="检测到冲突且无法自动解决",
                    details=conflict_info,
                )

        # 同步到本地（如果配置启用）
        if self.config.sync_to_local:
            self._sync_to_local(event, action="create")

        return WebhookResponse(
            success=True,
            message="事件创建已处理",
            details={
                "event_id": event.event_id,
                "conflict_detected": conflict_info is not None,
            }
            if conflict_info
            else None,
        )

    def _handle_event_updated(self, event: WebhookEvent) -> WebhookResponse:
        """
        处理事件更新

        Args:
            event: Webhook 事件

        Returns:
            WebhookResponse: 处理结果
        """
        logger.info(f"处理事件更新：{event.event_id}")

        # 检测冲突
        conflict_info = self._detect_conflict(event)

        if conflict_info and conflict_info["has_conflict"]:
            resolution = self._resolve_conflict(event, conflict_info)
            if not resolution["resolved"]:
                return WebhookResponse(
                    success=False,
                    message="检测到冲突且无法自动解决",
                    details=conflict_info,
                )

        # 同步到本地
        if self.config.sync_to_local:
            self._sync_to_local(event, action="update")

        return WebhookResponse(
            success=True,
            message="事件更新已处理",
            details={
                "event_id": event.event_id,
                "conflict_detected": conflict_info is not None,
            }
            if conflict_info
            else None,
        )

    def _handle_event_deleted(self, event: WebhookEvent) -> WebhookResponse:
        """
        处理事件删除

        Args:
            event: Webhook 事件

        Returns:
            WebhookResponse: 处理结果
        """
        logger.info(f"处理事件删除：{event.event_id}")

        # 同步删除到本地
        if self.config.sync_to_local:
            self._sync_to_local(event, action="delete")

        return WebhookResponse(
            success=True,
            message="事件删除已处理",
            details={"event_id": event.event_id},
        )

    def _detect_conflict(self, event: WebhookEvent) -> Optional[Dict[str, Any]]:
        """
        检测日历事件与本地训练计划的冲突

        Args:
            event: Webhook 事件

        Returns:
            Dict[str, Any]: 冲突信息，无冲突返回 None

        冲突检测维度：
        1. 时间冲突：同一时间段已有其他训练
        2. 内容冲突：训练类型/距离/时长与计划不一致
        3. 状态冲突：已完成的训练被修改
        """
        try:
            event_data = event.event_data
            event_date = self._extract_event_date(event_data)

            if not event_date:
                return None

            # TODO: 从本地存储查询该日期的训练计划
            # 这里需要集成 StorageManager 和 TrainingPlan 服务
            # 由于任务要求不修改架构，这里实现检测逻辑框架

            conflict_info = {
                "has_conflict": False,
                "conflict_type": [],
                "local_plan": None,
                "remote_event": self._extract_event_summary(event_data),
                "resolution_suggestion": None,
            }

            # 示例：检测时间冲突（伪代码）
            # local_plans = storage.get_plans_by_date(event_date)
            # for plan in local_plans:
            #     if self._is_time_conflict(plan, event_data):
            #         conflict_info["has_conflict"] = True
            #         conflict_info["conflict_type"].append("time_overlap")
            #         conflict_info["local_plan"] = plan

            logger.debug(f"冲突检测结果：{conflict_info}")
            return conflict_info if conflict_info["has_conflict"] else None

        except Exception as e:
            logger.error(f"冲突检测失败：{e}", exc_info=True)
            return None

    def _is_time_conflict(
        self, local_plan: DailyPlan, event_data: Dict[str, Any]
    ) -> bool:
        """
        检测时间是否冲突

        Args:
            local_plan: 本地训练计划
            event_data: 飞书事件数据

        Returns:
            bool: 是否存在时间冲突
        """
        # 提取事件时间范围
        start_time = event_data.get("start_time", {})
        end_time = event_data.get("end_time", {})

        if not start_time or not end_time:
            return False

        # TODO: 实现时间重叠检测逻辑
        # 需要比较本地计划的时间段与事件时间段是否有重叠
        return False

    def _resolve_conflict(
        self, event: WebhookEvent, conflict_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        解决冲突

        Args:
            event: Webhook 事件
            conflict_info: 冲突信息

        Returns:
            Dict[str, Any]: 解决结果

        解决策略：
        1. KEEP_REMOTE: 优先保留飞书日历的修改
        2. KEEP_LOCAL: 优先保留本地训练计划
        3. MERGE: 合并双方数据（智能合并）
        4. MANUAL: 标记为需要人工干预
        """
        strategy = self.config.conflict_strategy

        logger.info(f"使用冲突解决策略：{strategy.value}")

        resolution = {
            "resolved": False,
            "strategy": strategy.value,
            "action": None,
            "message": "",
        }

        if strategy == ConflictResolutionStrategy.KEEP_REMOTE:
            # 保留远程修改，更新本地
            resolution["resolved"] = True
            resolution["action"] = "update_local"
            resolution["message"] = "已采用飞书日历的数据"

        elif strategy == ConflictResolutionStrategy.KEEP_LOCAL:
            # 保留本地数据，忽略远程修改
            resolution["resolved"] = True
            resolution["action"] = "ignore_remote"
            resolution["message"] = "已保留本地训练计划"

            # 可选：将本地数据同步回飞书
            # self._sync_to_feishu(conflict_info["local_plan"])

        elif strategy == ConflictResolutionStrategy.MERGE:
            # 智能合并
            merged_data = self._merge_event_data(event, conflict_info)
            resolution["resolved"] = True
            resolution["action"] = "merge"
            resolution["message"] = "已合并双方数据"
            # 类型忽略：merged_data 是 Dict[str, Any] 类型
            resolution["merged_data"] = merged_data  # type: ignore[assignment]

        elif strategy == ConflictResolutionStrategy.MANUAL:
            # 需要人工干预
            resolution["resolved"] = False
            resolution["action"] = "manual_review"
            resolution["message"] = "需要人工审核冲突"

        logger.info(f"冲突解决完成：{resolution}")
        return resolution

    def _merge_event_data(
        self, event: WebhookEvent, conflict_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        智能合并事件数据

        Args:
            event: Webhook 事件
            conflict_info: 冲突信息

        Returns:
            Dict[str, Any]: 合并后的数据
        """
        # 合并策略示例：
        # - 时间：优先采用飞书日历（用户可能调整了时间）
        # - 训练类型：优先采用本地计划（更准确）
        # - 描述：合并双方描述

        remote_data = conflict_info.get("remote_event", {})
        local_data = conflict_info.get("local_plan", {})

        merged = {
            "start_time": remote_data.get("start_time"),
            "end_time": remote_data.get("end_time"),
            "summary": remote_data.get("summary"),
            "description": self._merge_descriptions(
                local_data.get("notes", ""),
                remote_data.get("description", ""),
            ),
        }

        return merged

    def _merge_descriptions(self, local_desc: str, remote_desc: str) -> str:
        """合并描述信息"""
        if local_desc and remote_desc:
            return f"{local_desc}\n\n[飞书备注]\n{remote_desc}"
        return local_desc or remote_desc

    def _sync_to_local(self, event: WebhookEvent, action: str) -> bool:
        """
        同步事件到本地存储

        Args:
            event: Webhook 事件
            action: 操作类型 (create/update/delete)

        Returns:
            bool: 同步是否成功
        """
        try:
            logger.info(f"同步事件到本地：{event.event_id}, 操作：{action}")

            # TODO: 实现本地存储同步逻辑
            # 需要集成 StorageManager 来保存/更新/删除事件数据

            # 伪代码示例：
            # if action == "create":
            #     storage.save_calendar_event(event.event_data)
            # elif action == "update":
            #     storage.update_calendar_event(event.event_id, event.event_data)
            # elif action == "delete":
            #     storage.delete_calendar_event(event.event_id)

            return True

        except Exception as e:
            logger.error(f"同步到本地失败：{e}", exc_info=True)
            return False

    def _extract_event_date(self, event_data: Dict[str, Any]) -> Optional[datetime]:
        """从事件数据中提取日期"""
        start_time = event_data.get("start_time", {})
        timestamp = start_time.get("timestamp")

        if timestamp:
            return datetime.fromtimestamp(int(timestamp))
        return None

    def _extract_event_summary(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """提取事件摘要信息"""
        return {
            "summary": event_data.get("summary", ""),
            "start_time": event_data.get("start_time"),
            "end_time": event_data.get("end_time"),
            "description": event_data.get("description", ""),
        }

    def process_request(
        self, payload: Dict[str, Any], signature: Optional[str] = None
    ) -> WebhookResponse:
        """
        处理 Webhook 请求的完整流程

        Args:
            payload: 请求负载
            signature: 签名（可选）

        Returns:
            WebhookResponse: 处理结果

        流程：
        1. 处理验证挑战（如果是验证请求）
        2. 验证签名
        3. 解析事件
        4. 处理事件
        """
        # 1. 处理验证挑战
        challenge = self.verify_challenge(payload)
        if challenge:
            return WebhookResponse(
                success=True,
                message="验证挑战通过",
                challenge=challenge,
            )

        # 2. 验证签名
        if signature and not self.verify_signature(payload, signature):
            return WebhookResponse(
                success=False,
                message="签名验证失败",
                error="Invalid signature",
            )

        # 3. 解析事件
        event = self.parse_event(payload)
        if not event:
            return WebhookResponse(
                success=False,
                message="事件解析失败",
                error="Invalid event format",
            )

        # 4. 处理事件
        return self.handle_event(event)


class WebhookRouter:
    """
    Webhook 路由管理器

    提供 FastAPI/Flask 等框架的路由装饰器
    """

    def __init__(self, handler: Optional[FeishuCalendarWebhookHandler] = None):
        """
        初始化路由管理器

        Args:
            handler: Webhook 处理器实例
        """
        self.handler = handler or FeishuCalendarWebhookHandler()

    def get_route_config(self) -> Dict[str, Any]:
        """
        获取路由配置

        Returns:
            Dict[str, Any]: 路由配置
        """
        return {
            "path": self.handler.config.webhook_path,
            "methods": ["POST"],
            "description": "飞书日历 Webhook 接收端点",
        }

    def handle_webhook(
        self, payload: Dict[str, Any], signature: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        处理 Webhook 请求

        Args:
            payload: 请求负载
            signature: 签名

        Returns:
            Dict[str, Any]: HTTP 响应
        """
        response = self.handler.process_request(payload, signature)

        # 构建 HTTP 响应
        http_response: Dict[str, Any] = {
            "status_code": 200 if response.success else 400,
            "body": {},
        }

        # 如果是验证挑战，返回 challenge
        if response.challenge:
            http_response["body"] = {"challenge": response.challenge}
        else:
            http_response["body"] = {
                "success": response.success,
                "message": response.message,
            }
            if response.error:
                http_response["body"]["error"] = response.error
            if response.details:
                http_response["body"]["details"] = response.details

        return http_response


def create_webhook_handler(
    config_path: Optional[str] = None,
) -> Tuple[FeishuCalendarWebhookHandler, WebhookRouter]:
    """
    创建 Webhook 处理器和路由管理器

    Args:
        config_path: 配置文件路径（可选）

    Returns:
        Tuple[FeishuCalendarWebhookHandler, WebhookRouter]: 处理器和路由管理器
    """
    handler = FeishuCalendarWebhookHandler()
    router = WebhookRouter(handler)
    return handler, router


def get_subscription_config() -> Dict[str, Any]:
    """
    获取飞书事件订阅配置

    用于在飞书开发者后台配置事件订阅

    Returns:
        Dict[str, Any]: 订阅配置
    """
    handler = FeishuCalendarWebhookHandler()

    return {
        "enabled": handler.config.enabled,
        "webhook_url": handler.config.webhook_path,
        "event_types": handler.config.allowed_event_types,
        "verification_token_required": True,  # nosec B105
        "encryption_key_required": True,  # nosec B105
        "subscription_guide": """
        飞书事件订阅配置步骤：
        1. 登录飞书开发者后台 (https://open.feishu.cn/)
        2. 进入应用管理 -> 事件订阅
        3. 启用事件订阅功能
        4. 配置请求地址：{webhook_url}
        5. 搜索并添加以下事件类型：
           - 日历事件创建 (calendar.event.created)
           - 日历事件更新 (calendar.event.updated)
           - 日历事件删除 (calendar.event.deleted)
        6. 保存配置，等待验证完成
        7. 将 verification_token 和 encryption_key 填入配置文件
        """.format(
            webhook_url=handler.config.webhook_path
        ),
    }
