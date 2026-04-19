"""
Prompt模板引擎模块 - v0.11.0

管理Prompt模板，渲染上下文数据到模板中供LLM调用
"""

import json
from dataclasses import asdict
from typing import Any

from src.core.exceptions import ValidationError
from src.core.logger import get_logger
from src.core.models import PlanExecutionStats, UserContext

logger = get_logger(__name__)

ADJUST_PLAN_PROMPT = """你是一位专业的跑步教练，需要根据用户的训练反馈和当前状态，调整训练计划。

## 用户上下文
{user_context}

## 执行统计
{execution_stats}

## 调整请求
{adjustment_request}

## 要求
1. 根据用户的训练反馈和当前状态，给出合理的调整建议
2. 调整建议必须符合运动科学原则
3. 周跑量增幅不超过10%
4. 长距离跑不超过周跑量的30%
5. 间歇跑后需安排恢复日
6. 请以JSON格式返回调整建议，包含以下字段：
   - adjustment_type: 调整类型（volume/intensity/type/date）
   - original_value: 原始值
   - adjusted_value: 调整后的值
   - reason: 调整原因
   - confidence: 置信度（0.0-1.0）"""

GET_SUGGESTION_PROMPT = """你是一位专业的跑步教练，需要根据用户的训练数据给出调整建议。

## 用户上下文
{user_context}

## 执行统计
{execution_stats}

## 要求
1. 分析用户的训练数据，识别潜在问题
2. 给出具体的调整建议
3. 建议必须符合运动科学原则
4. 请以JSON格式返回建议列表，每条建议包含：
   - suggestion_type: 建议类型（training/recovery/nutrition/injury_prevention）
   - suggestion_content: 建议内容
   - priority: 优先级（high/medium/low）
   - context: 上下文说明
   - confidence: 置信度（0.0-1.0）"""


class TemplateNotFoundError(ValidationError):
    """模板未找到异常"""

    def __init__(self, template_name: str):
        super().__init__(
            message=f"Prompt模板不存在：{template_name}",
            error_code="TEMPLATE_NOT_FOUND",
        )


class PromptTemplateEngine:
    """Prompt模板引擎"""

    def __init__(self) -> None:
        self._templates: dict[str, str] = {}
        self._load_templates()

    def _load_templates(self) -> None:
        """加载Prompt模板"""
        self._templates = {
            "adjust_plan": ADJUST_PLAN_PROMPT,
            "get_suggestion": GET_SUGGESTION_PROMPT,
        }

    def get_template_names(self) -> list[str]:
        """获取所有模板名称"""
        return list(self._templates.keys())

    def render(
        self,
        template_name: str,
        user_context: UserContext | None = None,
        execution_stats: PlanExecutionStats | None = None,
        **kwargs: Any,
    ) -> str:
        """渲染Prompt模板"""
        template = self._templates.get(template_name)
        if not template:
            raise TemplateNotFoundError(template_name)

        user_context_str = (
            json.dumps(user_context.to_dict(), ensure_ascii=False, indent=2)
            if user_context
            else "{}"
        )
        execution_stats_str = (
            json.dumps(asdict(execution_stats), ensure_ascii=False, indent=2)
            if execution_stats
            else "{}"
        )

        prompt = template.format(
            user_context=user_context_str,
            execution_stats=execution_stats_str,
            **kwargs,
        )

        return prompt

    def add_template(self, name: str, template: str) -> None:
        """添加自定义模板"""
        self._templates[name] = template

    def remove_template(self, name: str) -> bool:
        """移除模板"""
        if name in self._templates:
            del self._templates[name]
            return True
        return False
