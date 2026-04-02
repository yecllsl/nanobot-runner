"""
意图解析器模块

负责解析用户的自然语言输入或斜杠命令，提取训练计划相关的意图和参数
"""

import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from src.core.exceptions import ValidationError
from src.core.logger import get_logger
from src.core.models import IntentResult

logger = get_logger(__name__)


class IntentParser:
    """
    意图解析器

    支持自然语言和斜杠命令两种输入方式
    """

    INTENT_CREATE_PLAN = "create_plan"
    INTENT_MODIFY_PLAN = "modify_plan"
    INTENT_QUERY_PLAN = "query_plan"
    INTENT_CANCEL_PLAN = "cancel_plan"
    INTENT_SYNC_CALENDAR = "sync_calendar"
    INTENT_QUERY_PROGRESS = "query_progress"
    INTENT_UNKNOWN = "unknown"

    COMMAND_PATTERNS = {
        INTENT_CREATE_PLAN: r"^/create\s+(.+)",
        INTENT_MODIFY_PLAN: r"^/modify\s+(.+)",
        INTENT_QUERY_PLAN: r"^/query\s*(.*)",
        INTENT_CANCEL_PLAN: r"^/cancel\s*(.*)",
        INTENT_SYNC_CALENDAR: r"^/sync\s*(.*)",
        INTENT_QUERY_PROGRESS: r"^/progress\s*(.*)",
    }

    NATURAL_LANGUAGE_KEYWORDS = {
        INTENT_CREATE_PLAN: [
            "制定训练计划",
            "生成训练计划",
            "创建训练计划",
            "帮我制定",
            "帮我生成",
            "我想制定",
            "我想生成",
            "准备训练",
            "开始训练",
        ],
        INTENT_MODIFY_PLAN: [
            "修改训练计划",
            "调整训练计划",
            "更新训练计划",
            "改一下计划",
            "调整一下",
        ],
        INTENT_QUERY_PLAN: [
            "查看训练计划",
            "查询训练计划",
            "我的训练计划",
            "当前计划",
            "今天的训练",
            "本周训练",
        ],
        INTENT_CANCEL_PLAN: [
            "取消训练计划",
            "删除训练计划",
            "停止训练",
            "放弃计划",
        ],
        INTENT_SYNC_CALENDAR: [
            "同步到日历",
            "同步飞书日历",
            "添加到日历",
            "日历同步",
        ],
        INTENT_QUERY_PROGRESS: [
            "训练进度",
            "完成情况",
            "执行情况",
            "训练统计",
        ],
    }

    DISTANCE_PATTERNS = {
        "5k": 5.0,
        "5公里": 5.0,
        "五公里": 5.0,
        "10k": 10.0,
        "10公里": 10.0,
        "十公里": 10.0,
        "半马": 21.0975,
        "半程马拉松": 21.0975,
        "全马": 42.195,
        "马拉松": 42.195,
        "全程马拉松": 42.195,
    }

    TIME_PATTERNS = {
        "一周": 7,
        "两周": 14,
        "三周": 21,
        "一个月": 30,
        "两个月": 60,
        "三个月": 90,
    }

    def __init__(self) -> None:
        """初始化意图解析器"""
        pass

    def parse(self, user_input: str) -> IntentResult:
        """
        解析用户输入，提取意图和参数

        Args:
            user_input: 用户输入（自然语言或斜杠命令）

        Returns:
            IntentResult: 解析结果，包含意图、参数和置信度

        Raises:
            ValidationError: 当输入为空或格式错误时
        """
        if not user_input or not user_input.strip():
            raise ValidationError("用户输入不能为空")

        user_input = user_input.strip()
        logger.info(f"解析用户输入: {user_input}")

        if user_input.startswith("/"):
            result = self._parse_command(user_input)
        else:
            result = self._parse_natural_language(user_input)

        logger.info(
            f"解析结果: 意图={result.intent}, 参数={result.parameters}, 置信度={result.confidence}"
        )
        return result

    def _parse_command(self, command: str) -> IntentResult:
        """
        解析斜杠命令

        Args:
            command: 斜杠命令

        Returns:
            IntentResult: 解析结果
        """
        for intent, pattern in self.COMMAND_PATTERNS.items():
            match = re.match(pattern, command, re.IGNORECASE)
            if match:
                params_str = match.group(1).strip() if match.groups() else ""
                parameters = self._extract_parameters(params_str, intent)
                return IntentResult(
                    intent=intent,
                    parameters=parameters,
                    confidence=1.0,
                    input_type="slash_command",
                )

        return IntentResult(
            intent=self.INTENT_UNKNOWN,
            parameters={},
            confidence=0.0,
            input_type="slash_command",
        )

    def _parse_natural_language(self, text: str) -> IntentResult:
        """
        解析自然语言输入

        Args:
            text: 自然语言文本

        Returns:
            IntentResult: 解析结果
        """
        detected_intent = self.INTENT_UNKNOWN
        max_score = 0

        for intent, keywords in self.NATURAL_LANGUAGE_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in text)
            if score > max_score:
                max_score = score
                detected_intent = intent

        confidence = min(1.0, max_score * 0.3 + 0.4) if max_score > 0 else 0.0

        parameters = self._extract_parameters(text, detected_intent)

        return IntentResult(
            intent=detected_intent,
            parameters=parameters,
            confidence=confidence,
            input_type="natural_language",
        )

    def _extract_parameters(self, text: str, intent: str) -> Dict[str, Any]:
        """
        从文本中提取参数

        Args:
            text: 输入文本
            intent: 意图类型

        Returns:
            Dict[str, Any]: 提取的参数
        """
        parameters: Dict[str, Any] = {}

        if intent == self.INTENT_CREATE_PLAN:
            parameters.update(self._extract_plan_parameters(text))
        elif intent == self.INTENT_MODIFY_PLAN:
            parameters.update(self._extract_modify_parameters(text))
        elif intent == self.INTENT_QUERY_PLAN:
            parameters.update(self._extract_query_parameters(text))

        return parameters

    def _extract_plan_parameters(self, text: str) -> Dict[str, Any]:
        """
        提取创建计划的参数

        Args:
            text: 输入文本

        Returns:
            Dict[str, Any]: 计划参数
        """
        params: Dict[str, Any] = {}

        for pattern, distance in self.DISTANCE_PATTERNS.items():
            if pattern in text.lower():
                params["goal_distance_km"] = distance
                break

        date_patterns = [
            (r"(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?)", "%Y-%m-%d"),
            (r"(\d{1,2}月\d{1,2}日)", "%m月%d日"),
            (r"(\d{1,2}/\d{1,2})", "%m/%d"),
        ]

        for pattern, date_format in date_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    date_str = match.group(1)
                    if "年" in date_str:
                        date_str = (
                            date_str.replace("年", "-")
                            .replace("月", "-")
                            .replace("日", "")
                        )
                    elif "月" in date_str:
                        date_str = date_str.replace("月", "-").replace("日", "")
                        date_str = f"{datetime.now().year}-{date_str}"
                    elif "/" in date_str and date_str.count("/") == 1:
                        date_str = f"{datetime.now().year}-{date_str}"

                    parsed_date = datetime.strptime(date_str, "%Y-%m-%d")
                    params["goal_date"] = parsed_date.strftime("%Y-%m-%d")
                    break
                except ValueError:
                    continue

        for pattern, days in self.TIME_PATTERNS.items():
            if pattern in text:
                target_date = datetime.now() + timedelta(days=days)
                params["goal_date"] = target_date.strftime("%Y-%m-%d")
                break

        time_match = re.search(r"(\d{1,2}):(\d{2})", text)
        if time_match:
            hours = int(time_match.group(1))
            minutes = int(time_match.group(2))
            params["target_time"] = f"{hours:02d}:{minutes:02d}:00"

        return params

    def _extract_modify_parameters(self, text: str) -> Dict[str, Any]:
        """
        提取修改计划的参数

        Args:
            text: 输入文本

        Returns:
            Dict[str, Any]: 修改参数
        """
        params: Dict[str, Any] = {}

        if "增加" in text or "提高" in text:
            params["adjustment_type"] = "increase"
        elif "减少" in text or "降低" in text:
            params["adjustment_type"] = "decrease"

        if "跑量" in text or "距离" in text:
            params["adjustment_target"] = "distance"
        elif "强度" in text:
            params["adjustment_target"] = "intensity"

        return params

    def _extract_query_parameters(self, text: str) -> Dict[str, Any]:
        """
        提取查询计划的参数

        Args:
            text: 输入文本

        Returns:
            Dict[str, Any]: 查询参数
        """
        params: Dict[str, Any] = {}

        if "今天" in text:
            params["query_type"] = "today"
        elif "本周" in text or "这周" in text:
            params["query_type"] = "week"
        elif "下周" in text:
            params["query_type"] = "next_week"
        elif "本月" in text or "这个月" in text:
            params["query_type"] = "month"
        else:
            params["query_type"] = "current"

        return params
