"""
计划修改对话管理器 - v0.11.0

管理计划调整的多轮对话流程，支持上下文感知和确认机制
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from src.core.logger import get_logger
from src.core.models import PlanAdjustment, ValidationResult
from src.core.plan.plan_adjustment_validator import PlanAdjustmentValidator
from src.core.plan.prompt_template_engine import PromptTemplateEngine

logger = get_logger(__name__)


class DialogState(Enum):
    """对话状态"""

    INITIATED = "initiated"
    SUGGESTION_GENERATED = "suggestion_generated"
    VALIDATION_FAILED = "validation_failed"
    PENDING_CONFIRMATION = "pending_confirmation"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class DialogTurn:
    """对话轮次"""

    turn_id: str
    role: str
    content: str
    timestamp: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "turn_id": self.turn_id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class DialogContext:
    """对话上下文"""

    plan_id: str
    adjustment_request: str
    state: DialogState = DialogState.INITIATED
    turns: list[DialogTurn] = field(default_factory=list)
    current_suggestion: PlanAdjustment | None = None
    validation_result: ValidationResult | None = None
    retry_count: int = 0
    max_retries: int = 3
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "adjustment_request": self.adjustment_request,
            "state": self.state.value,
            "turns": [t.to_dict() for t in self.turns],
            "current_suggestion": (
                self.current_suggestion.to_dict() if self.current_suggestion else None
            ),
            "validation_result": (
                self.validation_result.to_dict() if self.validation_result else None
            ),
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class PlanModificationDialogManager:
    """计划修改对话管理器

    管理计划调整的多轮对话流程：
    1. 用户发起调整请求
    2. 生成调整建议
    3. 校验建议是否符合规则
    4. 等待用户确认或修改
    5. 执行确认的调整

    支持上下文感知：记录对话历史，允许用户在多轮对话中逐步细化调整。
    支持确认机制：关键调整需要用户明确确认后才执行。
    """

    def __init__(
        self,
        validator: PlanAdjustmentValidator | None = None,
        prompt_engine: PromptTemplateEngine | None = None,
    ) -> None:
        self._validator = validator or PlanAdjustmentValidator()
        self._prompt_engine = prompt_engine or PromptTemplateEngine()
        self._active_dialogs: dict[str, DialogContext] = {}

    def initiate_dialog(self, plan_id: str, adjustment_request: str) -> DialogContext:
        """发起对话

        Args:
            plan_id: 计划ID
            adjustment_request: 调整请求

        Returns:
            DialogContext: 对话上下文
        """
        context = DialogContext(
            plan_id=plan_id,
            adjustment_request=adjustment_request,
        )

        context.turns.append(
            DialogTurn(
                turn_id=str(uuid.uuid4())[:8],
                role="user",
                content=adjustment_request,
                timestamp=datetime.now().isoformat(),
            )
        )

        self._active_dialogs[plan_id] = context

        logger.info(
            f"发起计划调整对话：plan_id={plan_id}, request={adjustment_request}"
        )
        return context

    def generate_suggestion(self, plan_id: str) -> dict[str, Any]:
        """生成调整建议

        Args:
            plan_id: 计划ID

        Returns:
            dict: 生成结果
        """
        dialog = self._active_dialogs.get(plan_id)
        if dialog is None:
            return {"success": False, "error": f"未找到计划{plan_id}的对话"}

        if dialog.state not in (DialogState.INITIATED, DialogState.VALIDATION_FAILED):
            return {
                "success": False,
                "error": f"当前状态{dialog.state.value}不允许生成建议",
            }

        if dialog.retry_count >= dialog.max_retries:
            dialog.state = DialogState.CANCELLED
            return {"success": False, "error": "重试次数已达上限，对话已取消"}

        suggestion = self._validator.get_default_adjustment(dialog.adjustment_request)
        dialog.current_suggestion = suggestion

        validation = self._validator.validate(suggestion)
        dialog.validation_result = validation
        dialog.retry_count += 1

        if validation.passed:
            dialog.state = DialogState.PENDING_CONFIRMATION
            dialog.turns.append(
                DialogTurn(
                    turn_id=str(uuid.uuid4())[:8],
                    role="assistant",
                    content=f"建议调整：{suggestion.reason}（置信度：{suggestion.confidence:.0%}）",
                    timestamp=datetime.now().isoformat(),
                    metadata={"suggestion": suggestion.to_dict()},
                )
            )

            return {
                "success": True,
                "state": dialog.state.value,
                "suggestion": suggestion.to_dict(),
                "requires_confirmation": True,
            }
        else:
            dialog.state = DialogState.VALIDATION_FAILED
            violation_msgs = [v.message for v in validation.violations]

            dialog.turns.append(
                DialogTurn(
                    turn_id=str(uuid.uuid4())[:8],
                    role="assistant",
                    content=f"调整建议未通过校验：{'; '.join(violation_msgs)}",
                    timestamp=datetime.now().isoformat(),
                    metadata={"violations": violation_msgs},
                )
            )

            return {
                "success": False,
                "state": dialog.state.value,
                "violations": violation_msgs,
                "retry_remaining": dialog.max_retries - dialog.retry_count,
            }

    def confirm_adjustment(self, plan_id: str) -> dict[str, Any]:
        """确认调整

        Args:
            plan_id: 计划ID

        Returns:
            dict: 确认结果
        """
        dialog = self._active_dialogs.get(plan_id)
        if dialog is None:
            return {"success": False, "error": f"未找到计划{plan_id}的对话"}

        if dialog.state != DialogState.PENDING_CONFIRMATION:
            return {
                "success": False,
                "error": f"当前状态{dialog.state.value}不允许确认",
            }

        dialog.state = DialogState.CONFIRMED
        dialog.updated_at = datetime.now().isoformat()

        dialog.turns.append(
            DialogTurn(
                turn_id=str(uuid.uuid4())[:8],
                role="user",
                content="确认调整",
                timestamp=datetime.now().isoformat(),
            )
        )

        suggestion = dialog.current_suggestion
        dialog.state = DialogState.COMPLETED

        logger.info(f"计划调整已确认：plan_id={plan_id}")

        return {
            "success": True,
            "state": dialog.state.value,
            "adjustment": suggestion.to_dict() if suggestion else None,
        }

    def reject_adjustment(self, plan_id: str, reason: str = "") -> dict[str, Any]:
        """拒绝调整

        Args:
            plan_id: 计划ID
            reason: 拒绝原因

        Returns:
            dict: 拒绝结果
        """
        dialog = self._active_dialogs.get(plan_id)
        if dialog is None:
            return {"success": False, "error": f"未找到计划{plan_id}的对话"}

        if dialog.state != DialogState.PENDING_CONFIRMATION:
            return {
                "success": False,
                "error": f"当前状态{dialog.state.value}不允许拒绝",
            }

        dialog.state = DialogState.REJECTED
        dialog.updated_at = datetime.now().isoformat()

        dialog.turns.append(
            DialogTurn(
                turn_id=str(uuid.uuid4())[:8],
                role="user",
                content=f"拒绝调整：{reason}" if reason else "拒绝调整",
                timestamp=datetime.now().isoformat(),
            )
        )

        logger.info(f"计划调整已拒绝：plan_id={plan_id}, reason={reason}")

        return {
            "success": True,
            "state": dialog.state.value,
            "message": "调整已拒绝",
        }

    def refine_request(self, plan_id: str, new_request: str) -> dict[str, Any]:
        """细化调整请求（多轮对话核心）

        用户拒绝当前建议后，可以提供更具体的调整请求，
        系统基于对话历史重新生成建议。

        Args:
            plan_id: 计划ID
            new_request: 新的调整请求

        Returns:
            dict: 细化结果
        """
        dialog = self._active_dialogs.get(plan_id)
        if dialog is None:
            return {"success": False, "error": f"未找到计划{plan_id}的对话"}

        if dialog.state not in (DialogState.REJECTED, DialogState.VALIDATION_FAILED):
            return {
                "success": False,
                "error": f"当前状态{dialog.state.value}不允许细化请求",
            }

        dialog.adjustment_request = new_request
        dialog.state = DialogState.INITIATED
        dialog.current_suggestion = None
        dialog.validation_result = None
        dialog.updated_at = datetime.now().isoformat()

        dialog.turns.append(
            DialogTurn(
                turn_id=str(uuid.uuid4())[:8],
                role="user",
                content=new_request,
                timestamp=datetime.now().isoformat(),
            )
        )

        return self.generate_suggestion(plan_id)

    def cancel_dialog(self, plan_id: str) -> dict[str, Any]:
        """取消对话

        Args:
            plan_id: 计划ID

        Returns:
            dict: 取消结果
        """
        dialog = self._active_dialogs.get(plan_id)
        if dialog is None:
            return {"success": False, "error": f"未找到计划{plan_id}的对话"}

        dialog.state = DialogState.CANCELLED
        dialog.updated_at = datetime.now().isoformat()

        dialog.turns.append(
            DialogTurn(
                turn_id=str(uuid.uuid4())[:8],
                role="system",
                content="对话已取消",
                timestamp=datetime.now().isoformat(),
            )
        )

        logger.info(f"计划调整对话已取消：plan_id={plan_id}")

        return {"success": True, "state": dialog.state.value}

    def get_dialog_context(self, plan_id: str) -> dict[str, Any]:
        """获取对话上下文

        Args:
            plan_id: 计划ID

        Returns:
            dict: 对话上下文
        """
        dialog = self._active_dialogs.get(plan_id)
        if dialog is None:
            return {"success": False, "error": f"未找到计划{plan_id}的对话"}

        return {"success": True, "data": dialog.to_dict()}

    def get_dialog_history(self, plan_id: str) -> list[dict[str, Any]]:
        """获取对话历史

        Args:
            plan_id: 计划ID

        Returns:
            list: 对话历史
        """
        dialog = self._active_dialogs.get(plan_id)
        if dialog is None:
            return []

        return [t.to_dict() for t in dialog.turns]
