# 飞书推送集成
# 实现飞书自定义机器人Webhook调用
# 支持两种推送方案：nanobot飞书通道 / HTTP Webhook

import logging
import time
from typing import Any, Dict, List, Optional

import requests

from src.core.config import ConfigManager

logger = logging.getLogger(__name__)


class FeishuBot:
    """飞书自定义机器人

    支持两种推送方案：
    - 方案A（推荐）：使用 nanobot.channels.feishu 发送消息
    - 方案B（兼容）：使用 HTTP Webhook 发送消息
    """

    # 重试配置
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0  # 秒

    def __init__(self, webhook: Optional[str] = None):
        """
        初始化飞书机器人

        Args:
            webhook: Webhook URL，不指定则从配置文件读取
        """
        self.config = ConfigManager()
        self.webhook = webhook or self._load_webhook_from_config()
        self._nanobot_feishu_enabled: Optional[bool] = None
        self._feishu_channel = None

    def _load_webhook_from_config(self) -> Optional[str]:
        """从配置文件加载Webhook"""
        return self.config.get("feishu_webhook")

    def _check_nanobot_feishu_config(self) -> bool:
        """
        检测是否配置了 nanobot 飞书机器人

        Returns:
            bool: 是否配置了 nanobot 飞书机器人
        """
        if self._nanobot_feishu_enabled is not None:
            return self._nanobot_feishu_enabled

        try:
            from nanobot.config.loader import load_config

            nanobot_config = load_config()
            feishu_config = nanobot_config.channels.feishu

            # 检查是否启用了飞书通道并配置了必要参数
            if (
                feishu_config.enabled
                and feishu_config.app_id
                and feishu_config.app_secret
            ):
                self._nanobot_feishu_enabled = True
                logger.info("检测到 nanobot 飞书配置，将使用 nanobot 飞书通道")
                return True
        except Exception as e:
            logger.debug(f"检测 nanobot 飞书配置失败: {e}")

        self._nanobot_feishu_enabled = False
        return False

    def _get_feishu_channel(self):
        """
        获取 nanobot 飞书通道实例

        Returns:
            FeishuChannel 实例或 None
        """
        if self._feishu_channel is not None:
            return self._feishu_channel

        try:
            from nanobot.bus import MessageBus
            from nanobot.channels.feishu import FeishuChannel
            from nanobot.config.loader import load_config

            config = load_config()
            bus = MessageBus()
            self._feishu_channel = FeishuChannel(config.channels.feishu, bus)
            return self._feishu_channel
        except Exception as e:
            logger.warning(f"创建 nanobot 飞书通道失败: {e}")
            return None

    def _send_with_retry(
        self, payload: Dict[str, Any], retry_count: int = 0
    ) -> Dict[str, Any]:
        """
        带重试机制的请求发送

        Args:
            payload: 请求负载
            retry_count: 当前重试次数

        Returns:
            dict: API响应
        """
        if not self.webhook:
            return {"success": False, "error": "未配置Webhook"}

        try:
            headers = {"Content-Type": "application/json"}
            response = requests.post(
                self.webhook, json=payload, headers=headers, timeout=10
            )
            result = response.json()

            # 检查飞书API响应
            if result.get("code") == 0 or result.get("StatusCode") == 0:
                return {"success": True, "data": result}
            else:
                error_msg = result.get("msg", result.get("status", "未知错误"))
                return {"success": False, "error": error_msg, "data": result}

        except requests.exceptions.Timeout:
            error_msg = "请求超时"
            if retry_count < self.MAX_RETRIES:
                logger.warning(f"{error_msg}，第 {retry_count + 1} 次重试...")
                time.sleep(self.RETRY_DELAY)
                return self._send_with_retry(payload, retry_count + 1)
            return {"success": False, "error": f"{error_msg}，已重试{self.MAX_RETRIES}次"}

        except requests.exceptions.ConnectionError as e:
            error_msg = f"连接错误: {str(e)}"
            if retry_count < self.MAX_RETRIES:
                logger.warning(f"{error_msg}，第 {retry_count + 1} 次重试...")
                time.sleep(self.RETRY_DELAY)
                return self._send_with_retry(payload, retry_count + 1)
            return {"success": False, "error": f"{error_msg}，已重试{self.MAX_RETRIES}次"}

        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"请求异常: {str(e)}"}

        except Exception as e:
            return {"success": False, "error": f"未知错误: {str(e)}"}

    def _send_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送HTTP请求（兼容旧接口）

        Args:
            payload: 请求负载

        Returns:
            dict: API响应
        """
        result = self._send_with_retry(payload)
        if not result.get("success"):
            return {"error": result.get("error", "发送失败")}
        return result.get("data", {"code": 0, "msg": "success"})

    def send_text(self, text: str) -> Dict[str, Any]:
        """
        发送文本消息

        Args:
            text: 消息文本

        Returns:
            dict: API响应
        """
        if not self.webhook:
            return {"error": "未配置Webhook"}

        payload = {"msg_type": "text", "content": {"text": text}}

        return self._send_request(payload)

    def send_card(self, title: str, content: str) -> Dict[str, Any]:
        """
        发送卡片消息

        Args:
            title: 卡片标题
            content: 卡片内容

        Returns:
            dict: API响应
        """
        if not self.webhook:
            return {"error": "未配置Webhook"}

        payload = {
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True},
                "header": {
                    "title": {"tag": "plain_text", "content": title},
                    "template": "blue",
                },
                "elements": [
                    {"tag": "div", "text": {"tag": "lark_md", "content": content}}
                ],
            },
        }

        return self._send_request(payload)

    def send_import_notification(self, stats: Dict[str, int]) -> Dict[str, Any]:
        """
        发送导入通知

        Args:
            stats: 导入统计字典

        Returns:
            dict: API响应
        """
        title = "📊 数据导入完成"
        content = f"""
**导入统计**
- 扫描文件数: {stats.get('total', 0)}
- 新增记录: {stats.get('added', 0)}
- 跳过重复: {stats.get('skipped', 0)}
- 错误数量: {stats.get('errors', 0)}
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
            dict: API响应
        """
        # 检查是否配置了推送渠道
        if not self.webhook and not self._check_nanobot_feishu_config():
            return {
                "success": False,
                "error": "未配置飞书推送渠道。请配置 feishu_webhook 或 nanobot 飞书机器人。",
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
- 状态评估: {status}"""
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
- 距离: {distance} km
- 时长: {duration} 分钟
- TSS: {tss}
- 训练次数: {run_count}"""
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
            for day_plan in weekly_plan[:7]:  # 最多显示7天
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

        payload = {
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True},
                "header": {
                    "title": {"tag": "plain_text", "content": title},
                    "template": "blue",
                },
                "elements": card_elements,
            },
        }

        # 发送消息
        result = self._send_with_retry(payload)

        # 兼容旧接口返回格式
        if result.get("success"):
            return {"success": True, "data": result.get("data")}
        else:
            return {"success": False, "error": result.get("error")}


def test_connection(webhook: Optional[str] = None) -> Dict[str, Any]:
    """
    测试Webhook连接

    Args:
        webhook: Webhook URL，不指定则从配置文件读取

    Returns:
        dict: 连接测试结果
    """
    bot = FeishuBot(webhook=webhook)
    result = bot.send_text("测试消息：如果收到此消息，说明Webhook配置正确")

    if "error" in result:
        return {"success": False, "error": result["error"]}

    return {"success": True, "message": "Webhook配置正确"}
