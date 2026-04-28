# 反馈闭环机制单元测试


from src.core.personality.feedback_loop import FeedbackLoop
from src.core.personality.models import (
    FeedbackRecord,
    FeedbackType,
    PersonalizedSuggestion,
    PreferenceCategory,
    SuggestionType,
    UserPreferences,
)
from src.core.personality.preference_learner import PreferenceLearner


class TestFeedbackLoop:
    """FeedbackLoop 测试"""

    def setup_method(self):
        self.learner = PreferenceLearner()
        self.loop = FeedbackLoop(self.learner)

    def test_collect_feedback(self):
        feedback = self.loop.collect_feedback(
            feedback_type=FeedbackType.POSITIVE,
            content="建议很好",
            preference_category=PreferenceCategory.COMMUNICATION_STYLE,
        )

        assert feedback.feedback_type == FeedbackType.POSITIVE
        assert feedback.content == "建议很好"
        assert feedback.id != ""

    def test_process_feedback_positive(self):
        feedback = FeedbackRecord(
            id="fb-001",
            feedback_type=FeedbackType.POSITIVE,
            content="我喜欢evening跑步",
            preference_category=PreferenceCategory.TRAINING_TIME,
        )

        new_prefs = self.loop.process_feedback(feedback)
        assert isinstance(new_prefs, UserPreferences)

    def test_process_feedback_negative(self):
        feedback = FeedbackRecord(
            id="fb-002",
            feedback_type=FeedbackType.NEGATIVE,
            content="不喜欢morning跑步",
            preference_category=PreferenceCategory.TRAINING_TIME,
        )

        new_prefs = self.loop.process_feedback(feedback)
        assert isinstance(new_prefs, UserPreferences)

    def test_track_suggestion_effect_accepted(self):
        suggestion = PersonalizedSuggestion(
            id="sug-001",
            original_text="建议跑步5公里",
            personalized_text="很好的问题！建议跑步5公里",
            suggestion_type=SuggestionType.TRAINING_PLAN,
            confidence=0.8,
        )

        effect = self.loop.track_suggestion_effect(
            suggestion=suggestion,
            accepted=True,
            user_comment="很好",
        )

        assert effect["suggestion_id"] == "sug-001"
        assert effect["accepted"] is True
        assert effect["confidence"] == 0.8

    def test_track_suggestion_effect_rejected(self):
        suggestion = PersonalizedSuggestion(
            id="sug-002",
            original_text="建议高强度训练",
            personalized_text="建议高强度训练",
            confidence=0.6,
        )

        effect = self.loop.track_suggestion_effect(
            suggestion=suggestion,
            accepted=False,
            user_comment="太累了",
        )

        assert effect["accepted"] is False

    def test_get_effect_stats_empty(self):
        stats = self.loop.get_effect_stats()
        assert stats["total_suggestions"] == 0
        assert stats["acceptance_rate"] == 0.0

    def test_get_effect_stats_with_data(self):
        suggestion = PersonalizedSuggestion(
            id="sug-003",
            original_text="建议",
            personalized_text="建议",
            confidence=0.7,
        )

        self.loop.track_suggestion_effect(suggestion, accepted=True)
        self.loop.track_suggestion_effect(suggestion, accepted=False)

        stats = self.loop.get_effect_stats()
        assert stats["total_suggestions"] == 2
        assert stats["accepted_count"] == 1
        assert stats["rejected_count"] == 1
        assert stats["acceptance_rate"] == 0.5

    def test_full_feedback_loop(self):
        """测试完整反馈闭环流程"""
        suggestion = PersonalizedSuggestion(
            id="sug-full",
            original_text="建议进行轻松跑",
            personalized_text="建议进行轻松跑",
            suggestion_type=SuggestionType.PACE_GUIDANCE,
            confidence=0.7,
        )

        self.loop.track_suggestion_effect(
            suggestion, accepted=False, user_comment="太简单了，我喜欢high强度"
        )

        stats = self.loop.get_effect_stats()
        assert stats["rejected_count"] >= 1
