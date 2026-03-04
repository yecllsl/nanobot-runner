# 飞书推送集成
# 实现飞书自定义机器人Webhook调用

import requests
import json
from typing import Dict, Any, Optional
from pathlib import Path

from src.core.config import ConfigManager


class FeishuBot:
    """飞书自定义机器人"""
    
    def __init__(self, webhook: Optional[str] = None):
        """
        初始化飞书机器人
        
        Args:
            webhook: Webhook URL，不指定则从配置文件读取
        """
        self.config = ConfigManager()
        self.webhook = webhook or self._load_webhook_from_config()
    
    def _load_webhook_from_config(self) -> Optional[str]:
        """从配置文件加载Webhook"""
        return self.config.get("feishu_webhook")
    
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
        
        payload = {
            "msg_type": "text",
            "content": {"text": text}
        }
        
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
                    "template": "blue"
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {"tag": "lark_md", "content": content}
                    }
                ]
            }
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
        发送每日晨报
        
        Args:
            report_data: 报告数据
            
        Returns:
            dict: API响应
        """
        title = "☀️ 每日跑步晨报"
        
        content = f"""
**今日训练建议**
- 疲劳度评估: 待计算
- 今日建议: 待生成

**历史数据**
- 本周总距离: {report_data.get('weekly_distance', 'N/A')} km
- 本周总时长: {report_data.get('weekly_duration', 'N/A')} 小时
        """
        
        return self.send_card(title, content.strip())
    
    def _send_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送HTTP请求
        
        Args:
            payload: 请求负载
            
        Returns:
            dict: API响应
        """
        try:
            headers = {"Content-Type": "application/json"}
            response = requests.post(
                self.webhook,
                json=payload,
                headers=headers,
                timeout=10
            )
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": f"未知错误: {e}"}


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
        return {
            "success": False,
            "error": result["error"]
        }
    
    return {
        "success": True,
        "message": "Webhook配置正确"
    }
