"""PlanModificationDialogManager 单元测试 - v0.11.0"""

from src.core.models import PlanAdjustment
from src.core.plan.plan_modification_dialog import (
    DialogContext,
    DialogState,
    DialogTurn,
    PlanModificationDialogManager,
)


class TestDialogState:
    """DialogState 枚举测试"""

    def test_all_states_defined(self) -> None:
        expected = {
            "INITIATED",
            "SUGGESTION_GENERATED",
            "VALIDATION_FAILED",
            "PENDING_CONFIRMATION",
            "CONFIRMED",
            "REJECTED",
            "COMPLETED",
            "CANCELLED",
        }
        actual = {s.name for s in DialogState}
        assert actual == expected

    def test_state_is_string(self) -> None:
        assert DialogState.INITIATED.value == "initiated"
        assert DialogState.COMPLETED.value == "completed"


class TestDialogTurn:
    """DialogTurn 数据类测试"""

    def test_create_turn(self) -> None:
        turn = DialogTurn(
            turn_id="abc123",
            role="user",
            content="减量",
            timestamp="2026-01-01T00:00:00",
        )
        assert turn.turn_id == "abc123"
        assert turn.role == "user"
        assert turn.content == "减量"
        assert turn.metadata == {}

    def test_turn_to_dict(self) -> None:
        turn = DialogTurn(
            turn_id="abc123",
            role="assistant",
            content="建议调整",
            timestamp="2026-01-01T00:00:00",
            metadata={"key": "value"},
        )
        d = turn.to_dict()
        assert d["turn_id"] == "abc123"
        assert d["role"] == "assistant"
        assert d["metadata"] == {"key": "value"}


class TestDialogContext:
    """DialogContext 数据类测试"""

    def test_create_context(self) -> None:
        ctx = DialogContext(plan_id="plan-1", adjustment_request="减量")
        assert ctx.plan_id == "plan-1"
        assert ctx.adjustment_request == "减量"
        assert ctx.state == DialogState.INITIATED
        assert ctx.turns == []
        assert ctx.current_suggestion is None
        assert ctx.retry_count == 0
        assert ctx.max_retries == 3

    def test_context_to_dict(self) -> None:
        ctx = DialogContext(
            plan_id="plan-1",
            adjustment_request="减量",
            state=DialogState.PENDING_CONFIRMATION,
        )
        d = ctx.to_dict()
        assert d["plan_id"] == "plan-1"
        assert d["state"] == "pending_confirmation"
        assert d["current_suggestion"] is None
        assert d["retry_count"] == 0

    def test_context_to_dict_with_suggestion(self) -> None:
        suggestion = PlanAdjustment(
            adjustment_type="volume",
            original_value=1.0,
            adjusted_value=0.8,
            reason="减量周",
            confidence=0.7,
        )
        ctx = DialogContext(
            plan_id="plan-1",
            adjustment_request="减量",
            current_suggestion=suggestion,
        )
        d = ctx.to_dict()
        assert d["current_suggestion"] is not None
        assert d["current_suggestion"]["adjustment_type"] == "volume"


class TestPlanModificationDialogManager:
    """PlanModificationDialogManager 核心逻辑测试"""

    def setup_method(self) -> None:
        self.manager = PlanModificationDialogManager()

    def test_initiate_dialog(self) -> None:
        ctx = self.manager.initiate_dialog("plan-1", "下周减量")

        assert ctx.plan_id == "plan-1"
        assert ctx.adjustment_request == "下周减量"
        assert ctx.state == DialogState.INITIATED
        assert len(ctx.turns) == 1
        assert ctx.turns[0].role == "user"
        assert ctx.turns[0].content == "下周减量"

    def test_generate_suggestion_success(self) -> None:
        self.manager.initiate_dialog("plan-1", "减量")
        result = self.manager.generate_suggestion("plan-1")

        assert result["success"] is True
        assert result["state"] == "pending_confirmation"
        assert result["requires_confirmation"] is True
        assert "suggestion" in result

    def test_generate_suggestion_no_dialog(self) -> None:
        result = self.manager.generate_suggestion("nonexistent")

        assert result["success"] is False
        assert "未找到" in result["error"]

    def test_generate_suggestion_wrong_state(self) -> None:
        self.manager.initiate_dialog("plan-1", "减量")
        self.manager.generate_suggestion("plan-1")
        result = self.manager.generate_suggestion("plan-1")

        assert result["success"] is False
        assert "不允许生成建议" in result["error"]

    def test_confirm_adjustment(self) -> None:
        self.manager.initiate_dialog("plan-1", "减量")
        self.manager.generate_suggestion("plan-1")
        result = self.manager.confirm_adjustment("plan-1")

        assert result["success"] is True
        assert result["state"] == "completed"
        assert result["adjustment"] is not None

    def test_confirm_without_suggestion(self) -> None:
        self.manager.initiate_dialog("plan-1", "减量")
        result = self.manager.confirm_adjustment("plan-1")

        assert result["success"] is False
        assert "不允许确认" in result["error"]

    def test_reject_adjustment(self) -> None:
        self.manager.initiate_dialog("plan-1", "减量")
        self.manager.generate_suggestion("plan-1")
        result = self.manager.reject_adjustment("plan-1", "太少了")

        assert result["success"] is True
        assert result["state"] == "rejected"

    def test_reject_without_pending(self) -> None:
        self.manager.initiate_dialog("plan-1", "减量")
        result = self.manager.reject_adjustment("plan-1")

        assert result["success"] is False
        assert "不允许拒绝" in result["error"]

    def test_refine_request_after_rejection(self) -> None:
        self.manager.initiate_dialog("plan-1", "减量")
        self.manager.generate_suggestion("plan-1")
        self.manager.reject_adjustment("plan-1", "太少了")
        result = self.manager.refine_request("plan-1", "减量30%")

        assert result["success"] is True
        assert result["state"] == "pending_confirmation"

    def test_refine_request_wrong_state(self) -> None:
        self.manager.initiate_dialog("plan-1", "减量")
        result = self.manager.refine_request("plan-1", "减量30%")

        assert result["success"] is False
        assert "不允许细化请求" in result["error"]

    def test_cancel_dialog(self) -> None:
        self.manager.initiate_dialog("plan-1", "减量")
        result = self.manager.cancel_dialog("plan-1")

        assert result["success"] is True
        assert result["state"] == "cancelled"

    def test_cancel_nonexistent_dialog(self) -> None:
        result = self.manager.cancel_dialog("nonexistent")

        assert result["success"] is False

    def test_get_dialog_context(self) -> None:
        self.manager.initiate_dialog("plan-1", "减量")
        result = self.manager.get_dialog_context("plan-1")

        assert result["success"] is True
        assert result["data"]["plan_id"] == "plan-1"

    def test_get_dialog_context_nonexistent(self) -> None:
        result = self.manager.get_dialog_context("nonexistent")

        assert result["success"] is False

    def test_get_dialog_history(self) -> None:
        self.manager.initiate_dialog("plan-1", "减量")
        self.manager.generate_suggestion("plan-1")
        history = self.manager.get_dialog_history("plan-1")

        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"

    def test_get_dialog_history_nonexistent(self) -> None:
        history = self.manager.get_dialog_history("nonexistent")

        assert history == []

    def test_full_dialog_flow(self) -> None:
        """完整多轮对话流程：发起→生成→确认→完成"""
        self.manager.initiate_dialog("plan-1", "减量")
        gen_result = self.manager.generate_suggestion("plan-1")
        assert gen_result["success"] is True

        confirm_result = self.manager.confirm_adjustment("plan-1")
        assert confirm_result["success"] is True
        assert confirm_result["state"] == "completed"

        history = self.manager.get_dialog_history("plan-1")
        assert len(history) == 3

    def test_reject_and_refine_flow(self) -> None:
        """拒绝→细化→重新确认流程"""
        self.manager.initiate_dialog("plan-1", "减量")
        self.manager.generate_suggestion("plan-1")
        self.manager.reject_adjustment("plan-1", "减量不够")

        refine_result = self.manager.refine_request("plan-1", "减量30%")
        assert refine_result["success"] is True

        confirm_result = self.manager.confirm_adjustment("plan-1")
        assert confirm_result["success"] is True

        history = self.manager.get_dialog_history("plan-1")
        assert len(history) == 6

    def test_retry_exhausted(self) -> None:
        """重试次数耗尽后取消对话"""
        self.manager.initiate_dialog("plan-1", "减量")

        dialog = self.manager._active_dialogs["plan-1"]
        dialog.max_retries = 1

        self.manager.generate_suggestion("plan-1")
        self.manager.reject_adjustment("plan-1")

        result = self.manager.refine_request("plan-1", "再试试")
        assert result["success"] is False
        assert "重试次数" in result["error"] or dialog.state == DialogState.CANCELLED

    def test_multiple_dialogs_independent(self) -> None:
        """多个对话互不干扰"""
        self.manager.initiate_dialog("plan-1", "减量")
        self.manager.initiate_dialog("plan-2", "加量")

        self.manager.generate_suggestion("plan-1")
        self.manager.generate_suggestion("plan-2")

        ctx1 = self.manager.get_dialog_context("plan-1")
        ctx2 = self.manager.get_dialog_context("plan-2")

        assert ctx1["data"]["adjustment_request"] == "减量"
        assert ctx2["data"]["adjustment_request"] == "加量"

    def test_dialog_turns_accumulate(self) -> None:
        """对话轮次正确累积"""
        self.manager.initiate_dialog("plan-1", "减量")
        assert len(self.manager.get_dialog_history("plan-1")) == 1

        self.manager.generate_suggestion("plan-1")
        assert len(self.manager.get_dialog_history("plan-1")) == 2

        self.manager.confirm_adjustment("plan-1")
        assert len(self.manager.get_dialog_history("plan-1")) == 3

    def test_cancel_at_any_state(self) -> None:
        """任何状态下都可以取消对话"""
        self.manager.initiate_dialog("plan-1", "减量")
        self.manager.generate_suggestion("plan-1")

        result = self.manager.cancel_dialog("plan-1")
        assert result["success"] is True
        assert result["state"] == "cancelled"

    def test_generate_suggestion_adds_assistant_turn(self) -> None:
        """生成建议时添加assistant轮次"""
        self.manager.initiate_dialog("plan-1", "减量")
        self.manager.generate_suggestion("plan-1")

        history = self.manager.get_dialog_history("plan-1")
        assistant_turns = [t for t in history if t["role"] == "assistant"]
        assert len(assistant_turns) == 1
        assert "建议调整" in assistant_turns[0]["content"]
