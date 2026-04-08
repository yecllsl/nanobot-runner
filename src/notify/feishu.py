# 飞书推送集成
# 实现飞书应用机器人 API 调用
# 使用 access_token 调用消息发送接口

import logging
import re
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

import requests

from src.core.config import ConfigManager

logger = logging.getLogger(__name__)


class FeishuAuth:
    """飞书应用认证管理

    职责：
    1. 管理 app_id 和 app_secret
    2. 获取和刷新 tenant_access_token
    3. 处理 token 过期和重试

    配置位置：~/.nanobot-runner/config.json
    配置字段：
        - feishu_app_id: 飞书应用 App ID
        - feishu_app_secret: 飞书应用 App Secret
    """

    TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"  # nosec B105

    def __init__(self, app_id: Optional[str] = None, app_secret: Optional[str] = None):
        """
        初始化认证管理器

        Args:
            app_id: 飞书应用 App ID，不指定则从配置文件读取
            app_secret: 飞书应用 App Secret，不指定则从配置文件读取
        """
        self.config = ConfigManager()
        self.app_id = app_id or self.config.get("feishu_app_id")
        self.app_secret = app_secret or self.config.get("feishu_app_secret")

        self._access_token: Optional[str] = None
        self._token_expire_time: Optional[float] = None

        if not self.app_id or not self.app_secret:
            logger.warning("未配置飞书应用凭证 (feishu_app_id 或 feishu_app_secret)")

    def _get_access_token(self) -> str:
        """
        获取访问令牌（带缓存和自动刷新）

        Returns:
            str: 访问令牌

        Raises:
            RuntimeError: 当获取令牌失败时
        """
        # 检查令牌是否有效（提前 5 分钟刷新）
        if (
            self._access_token
            and self._token_expire_time
            and time.time() < self._token_expire_time - 300
        ):
            return self._access_token

        try:
            payload = {
                "app_id": self.app_id,
                "app_secret": self.app_secret,
            }
            headers = {"Content-Type": "application/json"}
            response = requests.post(
                self.TOKEN_URL, json=payload, headers=headers, timeout=10
            )
            result = response.json()

            if result.get("code") == 0:
                self._access_token = result.get("tenant_access_token")
                # 令牌有效期通常为 2 小时，提前 5 分钟刷新
                self._token_expire_time = time.time() + 7200 - 300
                logger.info("成功获取飞书访问令牌")
                return self._access_token
            else:
                error_msg = result.get("msg", "获取令牌失败")
                logger.error(f"获取飞书访问令牌失败：{error_msg}")
                raise RuntimeError(f"获取飞书访问令牌失败：{error_msg}")

        except requests.exceptions.RequestException as e:
            logger.error(f"获取飞书访问令牌请求异常：{e}")
            raise RuntimeError(f"获取飞书访问令牌请求异常：{e}")

    def get_token(self) -> str:
        """
        获取有效的访问令牌（对外接口）

        Returns:
            str: 访问令牌
        """
        return self._get_access_token()

    def is_configured(self) -> bool:
        """
        检查是否已配置应用凭证

        Returns:
            bool: 是否已配置
        """
        return bool(self.app_id and self.app_secret)


class FeishuMessageAPI:
    """飞书消息 API 封装

    职责：
    1. 发送文本消息
    2. 发送卡片消息
    3. 发送富文本消息

    API 文档：https://open.feishu.cn/document/ukTMukTMukTM/uAjNwUjN2YDM14iN2YDM
    """

    BASE_URL = "https://open.feishu.cn/open-apis/im/v1"

    def __init__(self, auth: Optional[FeishuAuth] = None):
        """
        初始化消息 API

        Args:
            auth: 认证管理器，不指定则创建默认实例
        """
        self.auth = auth or FeishuAuth()

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        token = self.auth.get_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        通用请求方法

        Args:
            method: HTTP 方法
            endpoint: API 端点
            params: 查询参数
            json: 请求体

        Returns:
            Dict[str, Any]: API 响应

        Raises:
            RuntimeError: 当请求失败时
        """
        url = f"{self.BASE_URL}{endpoint}"
        headers = self._get_headers()

        try:
            response = requests.request(
                method, url, params=params, json=json, headers=headers, timeout=10
            )
            result = response.json()

            # 检查飞书 API 响应码
            if result.get("code") == 0:
                return result
            else:
                error_msg = result.get("msg", "API 调用失败")
                logger.error(f"飞书 API 调用失败：{error_msg}")
                raise RuntimeError(f"飞书 API 调用失败：{error_msg}")

        except requests.exceptions.Timeout:
            logger.error("飞书 API 请求超时")
            raise RuntimeError("飞书 API 请求超时")
        except requests.exceptions.RequestException as e:
            logger.error(f"飞书 API 请求异常：{e}")
            raise RuntimeError(f"飞书 API 请求异常：{e}")

    def send_text(
        self,
        content: str,
        receive_id: str,
        receive_id_type: str = "user_id",
    ) -> Dict[str, Any]:
        """
        发送文本消息

        Args:
            content: 消息内容
            receive_id: 接收者 ID（用户 ID 或群 ID）
            receive_id_type: 接收者 ID 类型 ("user_id" 或 "chat_id")

        Returns:
            Dict[str, Any]: API 响应，包含 message_id
        """
        endpoint = "/messages"
        params = {"receive_id_type": receive_id_type}
        payload = {
            "receive_id": receive_id,
            "msg_type": "text",
            "content": content,
        }

        return self._request("POST", endpoint, params=params, json=payload)

    def send_card(
        self,
        card_content: Dict[str, Any],
        receive_id: str,
        receive_id_type: str = "user_id",
    ) -> Dict[str, Any]:
        """
        发送卡片消息

        Args:
            card_content: 卡片内容（JSON 对象）
            receive_id: 接收者 ID（用户 ID 或群 ID）
            receive_id_type: 接收者 ID 类型 ("user_id" 或 "chat_id")

        Returns:
            Dict[str, Any]: API 响应，包含 message_id
        """
        import json

        endpoint = "/messages"
        params = {"receive_id_type": receive_id_type}
        payload = {
            "receive_id": receive_id,
            "msg_type": "interactive",
            "content": json.dumps(card_content, ensure_ascii=False),
        }

        return self._request("POST", endpoint, params=params, json=payload)


class FeishuBot:
    """飞书应用机器人

    使用飞书开放平台 API 进行消息推送
    基于 access_token 认证，支持发送文本、卡片、富文本消息

    配置位置：~/.nanobot-runner/config.json
    配置字段：
        - feishu_app_id: 飞书应用 App ID
        - feishu_app_secret: 飞书应用 App Secret
        - feishu_receive_id: 接收者 ID（用户 ID 或群 ID）
        - feishu_receive_id_type: 接收者 ID 类型 ("user_id" 或 "chat_id")，默认"user_id"
    """

    # 重试配置
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0  # 秒

    def __init__(
        self,
        app_id: Optional[str] = None,
        app_secret: Optional[str] = None,
        receive_id: Optional[str] = None,
        receive_id_type: Optional[str] = None,
    ):
        """
        初始化飞书机器人

        Args:
            app_id: 飞书应用 App ID，不指定则从配置文件读取
            app_secret: 飞书应用 App Secret，不指定则从配置文件读取
            receive_id: 接收者 ID，不指定则从配置文件读取
            receive_id_type: 接收者 ID 类型，不指定则从配置文件读取（默认"user_id"）
        """
        self.config = ConfigManager()

        # 初始化认证管理
        self.auth = FeishuAuth(app_id=app_id, app_secret=app_secret)

        # 初始化消息 API
        self.message_api = FeishuMessageAPI(auth=self.auth)

        # 加载接收者配置
        self.receive_id = receive_id or self.config.get("feishu_receive_id")
        self.receive_id_type = receive_id_type or self.config.get(
            "feishu_receive_id_type", "user_id"
        )

        self._nanobot_feishu_enabled: Optional[bool] = None
        self._feishu_channel = None

    # ========== 消息发送方法 ==========

    def _send_with_retry(
        self, send_func: Callable, retry_count: int = 0
    ) -> Dict[str, Any]:
        """
        带重试机制的消息发送

        Args:
            send_func: 发送函数 (无参数，已闭包)
            retry_count: 当前重试次数

        Returns:
            dict: API 响应
        """
        try:
            result = send_func()
            return {"success": True, "data": result}

        except RuntimeError as e:
            error_msg = str(e)
            if retry_count < self.MAX_RETRIES:
                logger.warning(f"{error_msg}，第 {retry_count + 1} 次重试...")
                time.sleep(self.RETRY_DELAY)
                return self._send_with_retry(send_func, retry_count + 1)
            return {"success": False, "error": f"{error_msg}，已重试{self.MAX_RETRIES}次"}

        except Exception as e:
            return {"success": False, "error": f"发送失败：{str(e)}"}

    def send_text(self, text: str) -> Dict[str, Any]:
        """
        发送文本消息

        Args:
            text: 消息文本

        Returns:
            dict: API 响应
        """
        if not self.auth.is_configured():
            return {"success": False, "error": "未配置飞书应用凭证"}

        if not self.receive_id:
            return {"success": False, "error": "未配置接收者 ID"}

        def _send() -> Dict[str, Any]:
            return self.message_api.send_text(
                content=text,
                receive_id=self.receive_id,
                receive_id_type=self.receive_id_type,
            )

        return self._send_with_retry(_send)

    def send_card(self, title: str, content: str) -> Dict[str, Any]:
        """
        发送卡片消息

        Args:
            title: 卡片标题
            content: 卡片内容

        Returns:
            dict: API 响应
        """
        if not self.auth.is_configured():
            return {"success": False, "error": "未配置飞书应用凭证"}

        if not self.receive_id:
            return {"success": False, "error": "未配置接收者 ID"}

        card_payload = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": title,
                },
                "template": "blue",
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": content,
                    },
                },
            ],
        }

        def _send() -> Dict[str, Any]:
            return self.message_api.send_card(
                card_content=card_payload,
                receive_id=self.receive_id,
                receive_id_type=self.receive_id_type,
            )

        return self._send_with_retry(_send)

    def send_import_notification(self, stats: Dict[str, int]) -> Dict[str, Any]:
        """
        发送导入通知

        Args:
            stats: 导入统计字典

        Returns:
            dict: API 响应
        """
        title = "📊 数据导入完成"
        content = f"""
**导入统计**
- 扫描文件数：{stats.get('total', 0)}
- 新增记录：{stats.get('added', 0)}
- 跳过重复：{stats.get('skipped', 0)}
- 错误数量：{stats.get('errors', 0)}
        """

        return self.send_card(title, content.strip())

    def send_daily_report(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送每日晨报（飞书卡片消息格式）

        Args:
            report_data: 报告数据，包含：
                - date: 日期字符串
                - greeting: 问候语
                - yesterday_run: 昨日训练摘要（可选）
                - fitness_status: 体能状态数据
                - training_advice: 今日训练建议
                - weekly_plan: 本周训练计划预览

        Returns:
            dict: API 响应
        """
        # 检查是否配置了推送渠道
        if not self.auth.is_configured() or not self.receive_id:
            return {
                "success": False,
                "error": "未配置飞书推送渠道。请配置 feishu_app_id、feishu_app_secret 和 feishu_receive_id。",
            }

        # 构建飞书卡片消息
        card_elements = []

        # 1. 问候语
        greeting = report_data.get("greeting", "早上好！新的一天开始了。")
        card_elements.append(
            {"tag": "div", "text": {"tag": "lark_md", "content": f"**{greeting}**"}}
        )

        # 2. 体能状态
        fitness_status = report_data.get("fitness_status", {})
        atl = fitness_status.get("atl", 0.0)
        ctl = fitness_status.get("ctl", 0.0)
        tsb = fitness_status.get("tsb", 0.0)
        status = fitness_status.get("status", "数据不足")

        fitness_content = f"""**📊 体能状态**
- ATL (急性训练负荷): {atl}
- CTL (慢性训练负荷): {ctl}
- TSB (训练压力平衡): {tsb}
- 状态评估：{status}"""
        card_elements.append(
            {"tag": "div", "text": {"tag": "lark_md", "content": fitness_content}}
        )

        # 3. 昨日训练
        yesterday_run = report_data.get("yesterday_run")
        if yesterday_run:
            distance = yesterday_run.get("distance_km", 0)
            duration = yesterday_run.get("duration_min", 0)
            tss = yesterday_run.get("tss", 0)
            run_count = yesterday_run.get("run_count", 0)

            yesterday_content = f"""**🏃 昨日训练**
- 距离：{distance} km
- 时长：{duration} 分钟
- TSS: {tss}
- 训练次数：{run_count}"""
            card_elements.append(
                {"tag": "div", "text": {"tag": "lark_md", "content": yesterday_content}}
            )
        else:
            card_elements.append(
                {
                    "tag": "div",
                    "text": {"tag": "lark_md", "content": "**🏃 昨日训练**\n无训练记录"},
                }
            )

        # 4. 今日建议
        training_advice = report_data.get("training_advice", "暂无训练建议")
        advice_content = f"""**💡 今日建议**
{training_advice}"""
        card_elements.append(
            {"tag": "div", "text": {"tag": "lark_md", "content": advice_content}}
        )

        # 5. 本周计划预览（简化版）
        weekly_plan = report_data.get("weekly_plan", [])
        if weekly_plan:
            plan_lines = []
            for day_plan in weekly_plan[:7]:  # 最多显示 7 天
                day = day_plan.get("day", "")
                plan = day_plan.get("plan", "")
                is_today = day_plan.get("is_today", False)
                marker = "📍 " if is_today else "  "
                plan_lines.append(f"{marker}{day}: {plan}")

            plan_content = f"""**📅 本周计划**
{chr(10).join(plan_lines)}"""
            card_elements.append(
                {"tag": "div", "text": {"tag": "lark_md", "content": plan_content}}
            )

        # 构建完整卡片
        date_str = report_data.get("date", "")
        title = f"🌅 每日晨报 - {date_str}" if date_str else "🌅 每日晨报"

        card_payload = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": "blue",
            },
            "elements": card_elements,
        }

        # 发送消息
        def _send() -> Dict[str, Any]:
            return self.message_api.send_card(
                card_content=card_payload,
                receive_id=self.receive_id,
                receive_id_type=self.receive_id_type,
            )

        result = self._send_with_retry(_send)

        # 兼容旧接口返回格式
        if result.get("success"):
            return {"success": True, "data": result.get("data")}
        else:
            return {"success": False, "error": result.get("error")}


def test_connection(
    app_id: Optional[str] = None,
    app_secret: Optional[str] = None,
    receive_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    测试飞书应用机器人连接

    Args:
        app_id: 飞书应用 App ID，不指定则从配置文件读取
        app_secret: 飞书应用 App Secret，不指定则从配置文件读取
        receive_id: 接收者 ID，不指定则从配置文件读取

    Returns:
        dict: 连接测试结果
    """
    bot = FeishuBot(app_id=app_id, app_secret=app_secret, receive_id=receive_id)
    result = bot.send_text("测试消息：如果收到此消息，说明飞书应用机器人配置正确")

    if not result.get("success"):
        return {"success": False, "error": result.get("error")}

    return {"success": True, "message": "飞书应用机器人配置正确"}
