# 飞书推送集成
# 实现飞书自定义机器人 Webhook 调用
# 支持两种推送方案：nanobot 飞书通道 / HTTP Webhook

import logging
import re
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

import requests

from src.core.config import ConfigManager

logger = logging.getLogger(__name__)


class CommandType(str, Enum):
    """命令类型枚举"""

    STATS = "/stats"
    IMPORT = "/import"
    HELP = "/help"
    RECENT = "/recent"
    VD = "/vd"
    HR_DRIFT = "/hr_drift"
    LOAD = "/load"
    UNKNOWN = "unknown"


@dataclass
class ParsedCommand:
    """解析后的命令数据结构"""

    command_type: CommandType
    raw_text: str
    args: List[str]
    chat_id: Optional[str] = None
    user_id: Optional[str] = None
    message_id: Optional[str] = None


class FeishuBot:
    """飞书自定义机器人

    支持两种推送方案：
    - 方案 A（推荐）：使用 nanobot.channels.feishu 发送消息
    - 方案 B（兼容）：使用 HTTP Webhook 发送消息

    支持命令：
    - /stats [选项]：查询跑步统计
    - /import <路径>：导入 FIT 文件
    - /recent [数量]：查询最近训练记录
    - /vd：查询 VDOT 趋势
    - /hr_drift：查询心率漂移分析
    - /load [日期范围]：查询训练负荷
    - /help：显示帮助信息
    """

    # 重试配置
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0  # 秒

    # 命令注册表
    _command_handlers: Dict[CommandType, Callable] = {}

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
        self._command_handlers = self._init_command_handlers()

    def _load_webhook_from_config(self) -> Optional[str]:
        """从配置文件加载 Webhook"""
        return self.config.get("feishu_webhook")

    def _init_command_handlers(self) -> Dict[CommandType, Callable]:
        """初始化命令处理器注册表"""
        return {
            CommandType.HELP: self._handle_help,
            CommandType.STATS: self._handle_stats,
            CommandType.RECENT: self._handle_recent,
            CommandType.VD: self._handle_vd,
            CommandType.HR_DRIFT: self._handle_hr_drift,
            CommandType.LOAD: self._handle_load,
            CommandType.IMPORT: self._handle_import,
        }

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
            logger.warning(f"创建 nanobot 飞书通道失败：{e}")
            return None

    # ========== 消息接收与命令解析 ==========

    def parse_message(self, message_data: Dict[str, Any]) -> Optional[ParsedCommand]:
        """
        解析飞书消息，提取命令

        Args:
            message_data: 飞书消息数据，包含：
                - content: 消息内容
                - chat_id: 聊天 ID
                - user_id: 用户 ID
                - message_id: 消息 ID

        Returns:
            ParsedCommand: 解析后的命令，解析失败返回 None
        """
        content = message_data.get("content")
        if not content or not isinstance(content, str):
            return None

        content = content.strip()
        if not content:
            return None

        # 提取命令类型
        command_type = self._extract_command_type(content)
        if command_type == CommandType.UNKNOWN:
            return None

        # 提取参数
        args = self._extract_command_args(content)

        return ParsedCommand(
            command_type=command_type,
            raw_text=content,
            args=args,
            chat_id=message_data.get("chat_id"),
            user_id=message_data.get("user_id"),
            message_id=message_data.get("message_id"),
        )

    def _extract_command_type(self, content: str) -> CommandType:
        """
        从消息内容中提取命令类型

        Args:
            content: 消息内容

        Returns:
            CommandType: 命令类型
        """
        # 支持多种命令前缀格式
        patterns = {
            CommandType.STATS: r"^/(stats|统计)\b",
            CommandType.IMPORT: r"^/(import|导入)\b",
            CommandType.HELP: r"^/(help|帮助)\b",
            CommandType.RECENT: r"^/(recent|最近)\b",
            CommandType.VD: r"^/(vd|vdot)\b",
            CommandType.HR_DRIFT: r"^/(hr_drift|心率漂移)\b",
            CommandType.LOAD: r"^/(load|负荷)\b",
        }

        for cmd_type, pattern in patterns.items():
            if re.search(pattern, content, re.IGNORECASE):
                return cmd_type

        return CommandType.UNKNOWN

    def _extract_command_args(self, content: str) -> List[str]:
        """
        从消息内容中提取命令参数

        Args:
            content: 消息内容

        Returns:
            List[str]: 参数列表
        """
        # 移除命令本身，提取后续参数
        parts = content.split(None, 1)
        if len(parts) < 2:
            return []

        # 按空格分割参数
        return parts[1].strip().split()

    async def handle_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理飞书消息（异步入口）

        Args:
            message_data: 飞书消息数据

        Returns:
            dict: 处理结果
        """
        # 解析命令
        parsed_cmd = self.parse_message(message_data)
        if not parsed_cmd:
            return {
                "success": False,
                "message": "未识别的命令格式",
            }

        # 获取对应的处理器
        handler = self._command_handlers.get(parsed_cmd.command_type)
        if not handler:
            return {
                "success": False,
                "message": f"不支持的命令：{parsed_cmd.command_type.value}",
            }

        # 执行命令处理器
        try:
            result = handler(parsed_cmd)
            return result
        except Exception as e:
            logger.error(f"执行命令失败：{e}", exc_info=True)
            return {
                "success": False,
                "message": f"命令执行失败：{str(e)}",
            }

    # ========== 命令处理器实现 ==========

    def _handle_help(self, cmd: ParsedCommand) -> Dict[str, Any]:
        """处理帮助命令"""
        help_text = """🏃 **跑步助理命令帮助**

/stat [选项] - 查询跑步统计
  选项：
    --year YYYY    指定年份
    --start DATE   开始日期 (YYYY-MM-DD)
    --end DATE     结束日期 (YYYY-MM-DD)

/recent [数量] - 查询最近训练记录
  默认显示 5 条

/vd - 查询 VDOT 趋势

/hr_drift - 查询心率漂移分析

/load [日期范围] - 查询训练负荷 (ATL/CTL/TSB)

/import <路径> - 导入 FIT 文件/目录

/help - 显示此帮助信息

**示例**:
  /stats --year 2024
  /recent 10
  /import D:/garmin/activities
"""
        return {"success": True, "message": help_text, "msg_type": "text"}

    def _handle_stats(self, cmd: ParsedCommand) -> Dict[str, Any]:
        """处理统计命令"""
        # 解析参数
        year = None
        start_date = None
        end_date = None

        i = 0
        while i < len(cmd.args):
            if cmd.args[i] == "--year" and i + 1 < len(cmd.args):
                year = cmd.args[i + 1]
                i += 2
            elif cmd.args[i] == "--start" and i + 1 < len(cmd.args):
                start_date = cmd.args[i + 1]
                i += 2
            elif cmd.args[i] == "--end" and i + 1 < len(cmd.args):
                end_date = cmd.args[i + 1]
                i += 2
            else:
                i += 1

        # 构建统计查询响应（实际执行需要调用 AnalyticsEngine）
        stats_info = {
            "year": year,
            "start_date": start_date,
            "end_date": end_date,
            "note": "统计查询已接收，将调用 AnalyticsEngine 获取数据",
        }

        return {
            "success": True,
            "message": f"查询统计：{stats_info}",
            "msg_type": "text",
        }

    def _handle_recent(self, cmd: ParsedCommand) -> Dict[str, Any]:
        """处理最近记录命令"""
        count = 5  # 默认 5 条
        if cmd.args and cmd.args[0].isdigit():
            count = min(int(cmd.args[0]), 20)  # 最多 20 条

        return {
            "success": True,
            "message": f"查询最近 {count} 条训练记录",
            "msg_type": "text",
        }

    def _handle_vd(self, cmd: ParsedCommand) -> Dict[str, Any]:
        """处理 VDOT 趋势命令"""
        return {
            "success": True,
            "message": "查询 VDOT 趋势分析",
            "msg_type": "text",
        }

    def _handle_hr_drift(self, cmd: ParsedCommand) -> Dict[str, Any]:
        """处理心率漂移命令"""
        return {
            "success": True,
            "message": "查询心率漂移分析",
            "msg_type": "text",
        }

    def _handle_load(self, cmd: ParsedCommand) -> Dict[str, Any]:
        """处理训练负荷命令"""
        date_range = " ".join(cmd.args) if cmd.args else "最近 7 天"
        return {
            "success": True,
            "message": f"查询训练负荷：{date_range}",
            "msg_type": "text",
        }

    def _handle_import(self, cmd: ParsedCommand) -> Dict[str, Any]:
        """处理导入命令"""
        if not cmd.args:
            return {
                "success": False,
                "message": "请提供 FIT 文件路径\n示例：/import D:/garmin/activities",
                "msg_type": "text",
            }

        file_path = cmd.args[0]
        return {
            "success": True,
            "message": f"开始导入 FIT 文件：{file_path}",
            "msg_type": "text",
        }

    def register_command_handler(
        self, command_type: CommandType, handler: Callable
    ) -> None:
        """
        注册自定义命令处理器

        Args:
            command_type: 命令类型
            handler: 处理函数，接收 ParsedCommand 参数，返回 Dict
        """
        self._command_handlers[command_type] = handler
        logger.info(f"已注册命令处理器：{command_type.value}")

    def unregister_command_handler(self, command_type: CommandType) -> None:
        """
        注销命令处理器

        Args:
            command_type: 命令类型
        """
        if command_type in self._command_handlers:
            del self._command_handlers[command_type]
            logger.info(f"已注销命令处理器：{command_type.value}")

    # ========== 消息发送方法 ==========

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
