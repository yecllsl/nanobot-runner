# 个性化引擎与偏好学习器单元测试


import pytest

from src.core.personality.models import (
    FeedbackRecord,
    FeedbackType,
    Personality,
    PersonalizedSuggestion,
    PreferenceCategory,
    SuggestionType,
    UserPreferences,
)
from src.core.personality.personalization_engine import PersonalizationEngine
from src.core.personality.preference_learner import PreferenceLearner


class TestUserPreferences:
    """UserPreferences 数据模型测试"""

    def test_default_preferences(self):
        prefs = UserPreferences.default()
        assert prefs.training_time == "morning"
        assert prefs.training_intensity == "medium"
        assert prefs.communication_style == "encouraging"

    def test_custom_preferences(self):
        prefs = UserPreferences(
            training_time="evening",
            communication_style="brief",
        )
        assert prefs.training_time == "evening"
        assert prefs.communication_style == "brief"

    def test_to_dict(self):
        prefs = UserPreferences(training_time="afternoon")
        d = prefs.to_dict()
        assert d["training_time"] == "afternoon"
        assert "communication_style" in d

    def test_from_dict(self):
        data = {"training_time": "evening", "communication_style": "analytical"}
        prefs = UserPreferences.from_dict(data)
        assert prefs.training_time == "evening"
        assert prefs.communication_style == "analytical"

    def test_from_dict_with_missing_fields(self):
        prefs = UserPreferences.from_dict({})
        assert prefs.training_time == "morning"
        assert prefs.communication_style == "encouraging"

    def test_roundtrip(self):
        original = UserPreferences(
            training_time="evening",
            training_intensity="high",
            communication_style="brief",
            custom_preferences={"timezone": "UTC+8"},
        )
        restored = UserPreferences.from_dict(original.to_dict())
        assert restored.training_time == original.training_time
        assert restored.training_intensity == original.training_intensity
        assert restored.custom_preferences == original.custom_preferences


class TestPersonality:
    """Personality 数据模型测试"""

    def test_default_personality(self):
        p = Personality.default()
        assert p.communication_style == "encouraging"
        assert p.empathy_level == 0.7
        assert p.motivation_style == "supportive"

    def test_custom_personality(self):
        p = Personality(
            communication_style="analytical",
            empathy_level=0.5,
            humor_level=0.1,
        )
        assert p.communication_style == "analytical"
        assert p.empathy_level == 0.5

    def test_roundtrip(self):
        original = Personality(
            communication_style="brief",
            suggestion_approach="direct",
            empathy_level=0.8,
        )
        restored = Personality.from_dict(original.to_dict())
        assert restored.communication_style == original.communication_style
        assert restored.suggestion_approach == original.suggestion_approach


class TestPersonalizedSuggestion:
    """PersonalizedSuggestion 数据模型测试"""

    def test_create_suggestion(self):
        s = PersonalizedSuggestion(
            id="sug-001",
            original_text="建议跑步5公里",
            personalized_text="很好的问题！建议跑步5公里",
            suggestion_type=SuggestionType.TRAINING_PLAN,
            confidence=0.8,
        )
        assert s.id == "sug-001"
        assert s.original_text != s.personalized_text
        assert s.confidence == 0.8

    def test_to_dict(self):
        s = PersonalizedSuggestion(
            id="sug-002",
            original_text="跑步",
            personalized_text="跑步",
        )
        d = s.to_dict()
        assert d["id"] == "sug-002"
        assert d["suggestion_type"] == "general"


class TestFeedbackRecord:
    """FeedbackRecord 数据模型测试"""

    def test_create_feedback(self):
        fb = FeedbackRecord(
            id="fb-001",
            feedback_type=FeedbackType.POSITIVE,
            content="建议很好",
            preference_category=PreferenceCategory.COMMUNICATION_STYLE,
        )
        assert fb.feedback_type == FeedbackType.POSITIVE
        assert fb.accepted is True

    def test_negative_feedback(self):
        fb = FeedbackRecord(
            id="fb-002",
            feedback_type=FeedbackType.NEGATIVE,
            content="太啰嗦了",
            preference_category=PreferenceCategory.COMMUNICATION_STYLE,
            accepted=False,
        )
        assert fb.feedback_type == FeedbackType.NEGATIVE
        assert fb.accepted is False


class TestPersonalizationEngine:
    """PersonalizationEngine 测试"""

    def test_personalize_with_default_preferences(self):
        engine = PersonalizationEngine()
        suggestion = engine.personalize_suggestion("建议今天进行轻松跑，距离5公里")

        assert suggestion.original_text == "建议今天进行轻松跑，距离5公里"
        assert suggestion.personalized_text != ""
        assert suggestion.confidence >= 0.0
        assert suggestion.confidence <= 1.0

    def test_personalize_with_brief_style(self):
        prefs = UserPreferences(communication_style="brief")
        engine = PersonalizationEngine(preferences=prefs)
        suggestion = engine.personalize_suggestion(
            "建议今天进行轻松跑，距离5公里。注意补充水分。保持良好心态。"
        )

        assert suggestion.preference_factors.get("communication_style") == "brief"

    def test_personalize_with_encouraging_style(self):
        prefs = UserPreferences(communication_style="encouraging")
        engine = PersonalizationEngine(preferences=prefs)
        suggestion = engine.personalize_suggestion("建议今天进行轻松跑")

        assert "鼓励" in suggestion.preference_factors.get(
            "communication_style", ""
        ) or "encouraging" in suggestion.preference_factors.get(
            "communication_style", ""
        )

    def test_personalize_with_analytical_style(self):
        prefs = UserPreferences(communication_style="analytical")
        engine = PersonalizationEngine(preferences=prefs)
        suggestion = engine.personalize_suggestion("建议今天进行轻松跑")

        assert suggestion.preference_factors.get("communication_style") == "analytical"

    def test_adjust_intensity_low(self):
        engine = PersonalizationEngine()
        result = engine.adjust_intensity("必须完成10公里", "low")
        assert "建议" in result
        assert "必须" not in result

    def test_adjust_intensity_high(self):
        engine = PersonalizationEngine()
        result = engine.adjust_intensity("建议进行轻松跑", "high")
        assert "强烈建议" in result

    def test_get_preference_weights(self):
        engine = PersonalizationEngine()
        weights = engine.get_preference_weights()
        assert "communication_style" in weights
        assert "training_time" in weights
        assert sum(weights.values()) == pytest.approx(1.0, abs=0.01)

    def test_update_preferences(self):
        engine = PersonalizationEngine()
        new_prefs = UserPreferences(training_time="evening")
        engine.update_preferences(new_prefs)
        assert engine.preferences.training_time == "evening"

    def test_update_personality(self):
        engine = PersonalizationEngine()
        new_personality = Personality(communication_style="analytical")
        engine.update_personality(new_personality)
        assert engine.personality.communication_style == "analytical"


class TestPreferenceLearner:
    """PreferenceLearner 测试"""

    def test_default_preferences(self):
        learner = PreferenceLearner()
        prefs = learner.get_learned_preferences()
        assert prefs.training_time == "morning"
        assert prefs.communication_style == "encouraging"

    def test_learn_from_positive_feedback(self):
        learner = PreferenceLearner()
        fb = FeedbackRecord(
            id="fb-001",
            feedback_type=FeedbackType.POSITIVE,
            content="我喜欢evening跑步",
            preference_category=PreferenceCategory.TRAINING_TIME,
        )
        new_prefs = learner.learn_from_feedback(fb)
        assert isinstance(new_prefs, UserPreferences)

    def test_learn_from_negative_feedback(self):
        learner = PreferenceLearner()
        fb = FeedbackRecord(
            id="fb-002",
            feedback_type=FeedbackType.NEGATIVE,
            content="太啰嗦了，我喜欢brief风格",
            preference_category=PreferenceCategory.COMMUNICATION_STYLE,
        )
        new_prefs = learner.learn_from_feedback(fb)
        assert isinstance(new_prefs, UserPreferences)

    def test_update_preference_model_directly(self):
        learner = PreferenceLearner()
        new_prefs = learner.update_preference_model(
            {"training_time": "evening", "communication_style": "brief"}
        )
        assert new_prefs.training_time == "evening"
        assert new_prefs.communication_style == "brief"

    def test_reset_preferences(self):
        learner = PreferenceLearner()
        learner.update_preference_model({"training_time": "evening"})
        reset_prefs = learner.reset_preferences()
        assert reset_prefs.training_time == "morning"

    def test_get_feedback_stats_empty(self):
        learner = PreferenceLearner()
        stats = learner.get_feedback_stats()
        assert stats["total_feedback"] == 0

    def test_get_feedback_stats_with_data(self):
        learner = PreferenceLearner()
        fb1 = FeedbackRecord(
            id="fb-001",
            feedback_type=FeedbackType.POSITIVE,
            content="好",
            preference_category=PreferenceCategory.COMMUNICATION_STYLE,
        )
        fb2 = FeedbackRecord(
            id="fb-002",
            feedback_type=FeedbackType.NEGATIVE,
            content="不好",
            preference_category=PreferenceCategory.TRAINING_INTENSITY,
        )
        learner.learn_from_feedback(fb1)
        learner.learn_from_feedback(fb2)

        stats = learner.get_feedback_stats()
        assert stats["total_feedback"] == 2
        assert stats["positive_count"] == 1
        assert stats["negative_count"] == 1

    def test_extract_training_time_preference(self):
        learner = PreferenceLearner()
        fb = FeedbackRecord(
            id="fb-003",
            feedback_type=FeedbackType.POSITIVE,
            content="我喜欢evening跑步",
            preference_category=PreferenceCategory.TRAINING_TIME,
        )
        extracted = learner._extract_preference_from_feedback(fb)
        assert extracted.get("training_time") == "evening"

    def test_extract_communication_style_preference(self):
        learner = PreferenceLearner()
        fb = FeedbackRecord(
            id="fb-004",
            feedback_type=FeedbackType.CORRECTION,
            content="请用brief风格回答",
            preference_category=PreferenceCategory.COMMUNICATION_STYLE,
        )
        extracted = learner._extract_preference_from_feedback(fb)
        assert extracted.get("communication_style") == "brief"

    def test_learning_rate_effect(self):
        learner_fast = PreferenceLearner(learning_rate=1.0)
        learner_slow = PreferenceLearner(learning_rate=0.1)

        for _ in range(3):
            fb = FeedbackRecord(
                id="fb-005",
                feedback_type=FeedbackType.POSITIVE,
                content="evening",
                preference_category=PreferenceCategory.TRAINING_TIME,
            )
            learner_fast.learn_from_feedback(fb)
            learner_slow.learn_from_feedback(fb)

    def test_reset_personality(self):
        learner = PreferenceLearner()
        learner.reset_personality()
        assert learner.get_personality().communication_style == "encouraging"
