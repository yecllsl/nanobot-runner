"""
AskUserConfirmManager 扩展测试 - v0.23.0 决策追踪模块

测试 DECISION_FEEDBACK 场景和 create_decision_feedback_prompt 方法。
"""

from src.core.plan.ask_user_confirm import (
    AskUserConfirmManager,
    ConfirmPrompt,
    ConfirmScenario,
)


class TestConfirmScenarioDecisionFeedback:
    """测试 ConfirmScenario.DECISION_FEEDBACK 枚举值"""

    def test_decision_feedback_exists(self) -> None:
        """DECISION_FEEDBACK 枚举成员存在"""
        assert hasattr(ConfirmScenario, "DECISION_FEEDBACK")

    def test_decision_feedback_value(self) -> None:
        """DECISION_FEEDBACK 枚举值为 'decision_feedback'"""
        assert ConfirmScenario.DECISION_FEEDBACK.value == "decision_feedback"


class TestCreateDecisionFeedbackPrompt:
    """测试 create_decision_feedback_prompt 方法"""

    def setup_method(self) -> None:
        """每个测试方法前创建管理器实例"""
        self.manager = AskUserConfirmManager()

    def test_returns_confirm_prompt(self) -> None:
        """create_decision_feedback_prompt 返回 ConfirmPrompt 实例"""
        prompt = self.manager.create_decision_feedback_prompt(
            decision_id="decision-abc12345",
            recommendation_summary="建议将本周跑量从40km降至35km",
        )
        assert isinstance(prompt, ConfirmPrompt)

    def test_scenario_is_decision_feedback(self) -> None:
        """prompt 的 scenario 为 DECISION_FEEDBACK"""
        prompt = self.manager.create_decision_feedback_prompt(
            decision_id="decision-abc12345",
            recommendation_summary="建议将本周跑量从40km降至35km",
        )
        assert prompt.scenario == ConfirmScenario.DECISION_FEEDBACK

    def test_has_three_options(self) -> None:
        """prompt 有 3 个选项（accept/modify/reject）"""
        prompt = self.manager.create_decision_feedback_prompt(
            decision_id="decision-abc12345",
            recommendation_summary="建议将本周跑量从40km降至35km",
        )
        assert len(prompt.options) == 3

    def test_option_keys(self) -> None:
        """选项的 key 分别为 accept、modify、reject"""
        prompt = self.manager.create_decision_feedback_prompt(
            decision_id="decision-abc12345",
            recommendation_summary="建议将本周跑量从40km降至35km",
        )
        keys = [opt.key for opt in prompt.options]
        assert keys == ["accept", "modify", "reject"]

    def test_option_values(self) -> None:
        """选项的 value 正确：accept=True, modify='modify', reject=False"""
        prompt = self.manager.create_decision_feedback_prompt(
            decision_id="decision-abc12345",
            recommendation_summary="建议将本周跑量从40km降至35km",
        )
        assert prompt.options[0].value is True
        assert prompt.options[1].value == "modify"
        assert prompt.options[2].value is False

    def test_default_key_is_accept(self) -> None:
        """默认选项为 accept"""
        prompt = self.manager.create_decision_feedback_prompt(
            decision_id="decision-abc12345",
            recommendation_summary="建议将本周跑量从40km降至35km",
        )
        assert prompt.default_key == "accept"

    def test_metadata_contains_decision_id(self) -> None:
        """metadata 中包含 decision_id"""
        decision_id = "decision-abc12345"
        prompt = self.manager.create_decision_feedback_prompt(
            decision_id=decision_id,
            recommendation_summary="建议将本周跑量从40km降至35km",
        )
        assert prompt.metadata["decision_id"] == decision_id

    def test_title_contains_decision_id_prefix(self) -> None:
        """title 包含 decision_id 的前8位"""
        decision_id = "decision-abc12345"
        prompt = self.manager.create_decision_feedback_prompt(
            decision_id=decision_id,
            recommendation_summary="建议将本周跑量从40km降至35km",
        )
        assert decision_id[:8] in prompt.title

    def test_message_contains_recommendation(self) -> None:
        """message 包含建议摘要"""
        recommendation = "建议将本周跑量从40km降至35km"
        prompt = self.manager.create_decision_feedback_prompt(
            decision_id="decision-abc12345",
            recommendation_summary=recommendation,
        )
        assert recommendation in prompt.message

    def test_prompt_registered_in_pending(self) -> None:
        """创建的 prompt 注册到 _pending_confirms 中"""
        decision_id = "decision-abc12345"
        prompt = self.manager.create_decision_feedback_prompt(
            decision_id=decision_id,
            recommendation_summary="建议将本周跑量从40km降至35km",
        )
        assert self.manager.has_pending_confirm(decision_id)
        assert self.manager.get_pending_prompt(decision_id) is prompt
