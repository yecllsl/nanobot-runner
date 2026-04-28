# AI人格进化与个性化模块
# 提供用户偏好学习、个性化建议、人格进化等能力

from src.core.personality.feedback_loop import FeedbackLoop
from src.core.personality.models import (
    FeedbackRecord,
    FeedbackType,
    Personality,
    PersonalityVersion,
    PersonalizedSuggestion,
    PreferenceCategory,
    SuggestionType,
    UserPreferences,
)
from src.core.personality.personalization_engine import PersonalizationEngine
from src.core.personality.preference_learner import PreferenceLearner

__all__ = [
    "FeedbackLoop",
    "FeedbackRecord",
    "FeedbackType",
    "Personality",
    "PersonalityVersion",
    "PersonalizedSuggestion",
    "PersonalizationEngine",
    "PreferenceCategory",
    "PreferenceLearner",
    "SuggestionType",
    "UserPreferences",
]
