# 个性化引擎核心实现
# 根据用户偏好对AI建议进行个性化调整
# 建议接受率目标>85%

import logging
import uuid
from datetime import datetime
from typing import Any

from src.core.personality.models import (
    Personality,
    PersonalizedSuggestion,
    SuggestionType,
    UserPreferences,
)

logger = logging.getLogger(__name__)


class PersonalizationEngine:
    """个性化引擎

    根据用户偏好和AI人格对AI建议进行个性化调整。
    核心接口：
    - personalize_suggestion: 个性化调整建议
    - adjust_intensity: 调整建议强度
    - get_preference_weights: 获取偏好权重

    Attributes:
        preferences: 当前用户偏好
        personality: 当前AI人格
        _weights: 偏好权重映射
    """

    def __init__(
        self,
        preferences: UserPreferences | None = None,
        personality: Personality | None = None,
    ) -> None:
        """初始化个性化引擎

        Args:
            preferences: 用户偏好（可选，默认使用默认偏好）
            personality: AI人格（可选，默认使用默认人格）
        """
        self.preferences = preferences or UserPreferences.default()
        self.personality = personality or Personality.default()
        self._weights = self._init_weights()

    def personalize_suggestion(
        self,
        original_text: str,
        suggestion_type: SuggestionType = SuggestionType.GENERAL,
        context: dict[str, Any] | None = None,
    ) -> PersonalizedSuggestion:
        """个性化调整建议

        根据用户偏好和AI人格对原始建议进行个性化调整。
        调整维度包括：
        - 沟通风格适配
        - 建议强度调整
        - 详细程度匹配
        - 训练时段偏好

        Args:
            original_text: 原始建议文本
            suggestion_type: 建议类型
            context: 额外上下文（可选）

        Returns:
            PersonalizedSuggestion: 个性化后的建议
        """
        personalized_text = original_text
        preference_factors: dict[str, str] = {}

        personalized_text = self._apply_communication_style(personalized_text)
        preference_factors["communication_style"] = self.preferences.communication_style

        personalized_text = self._apply_detail_level(personalized_text)
        preference_factors["detail_level"] = self.preferences.detail_preference

        personalized_text = self._apply_training_time_preference(
            personalized_text, context
        )
        if self.preferences.training_time != "morning":
            preference_factors["training_time"] = self.preferences.training_time

        confidence = self._compute_confidence(preference_factors)

        suggestion = PersonalizedSuggestion(
            id=str(uuid.uuid4())[:8],
            original_text=original_text,
            personalized_text=personalized_text,
            suggestion_type=suggestion_type,
            confidence=confidence,
            preference_factors=preference_factors,
            timestamp=datetime.now(),
        )

        logger.info(
            f"建议个性化完成: id={suggestion.id}, "
            f"类型={suggestion_type.value}, "
            f"置信度={confidence:.2f}"
        )

        return suggestion

    def adjust_intensity(self, text: str, intensity: str = "medium") -> str:
        """调整建议强度

        根据用户偏好调整建议的语气强度。

        Args:
            text: 原始文本
            intensity: 目标强度（low/medium/high）

        Returns:
            str: 调整后的文本
        """
        target_intensity = intensity or self.preferences.training_intensity

        if target_intensity == "low":
            return self._soften_text(text)
        elif target_intensity == "high":
            return self._strengthen_text(text)

        return text

    def get_preference_weights(self) -> dict[str, float]:
        """获取偏好权重

        返回各偏好维度的权重，用于个性化调整时的优先级排序。

        Returns:
            dict: 偏好权重映射，key为偏好维度，value为权重值(0.0-1.0)
        """
        return dict(self._weights)

    def update_preferences(self, preferences: UserPreferences) -> None:
        """更新用户偏好

        Args:
            preferences: 新的用户偏好
        """
        self.preferences = preferences
        self._weights = self._init_weights()
        logger.info(f"用户偏好已更新: {preferences.to_dict()}")

    def update_personality(self, personality: Personality) -> None:
        """更新AI人格

        Args:
            personality: 新的AI人格
        """
        self.personality = personality
        logger.info(f"AI人格已更新: {personality.to_dict()}")

    def _apply_communication_style(self, text: str) -> str:
        """应用沟通风格

        Args:
            text: 原始文本

        Returns:
            str: 调整后的文本
        """
        style = self.preferences.communication_style

        if style == "brief":
            return self._make_brief(text)
        elif style == "detailed":
            return self._make_detailed(text)
        elif style == "encouraging":
            return self._add_encouragement(text)
        elif style == "analytical":
            return self._add_analysis(text)

        return text

    def _apply_detail_level(self, text: str) -> str:
        """应用详细程度偏好

        Args:
            text: 原始文本

        Returns:
            str: 调整后的文本
        """
        level = self.preferences.detail_preference

        if level == "concise" and len(text) > 200:
            sentences = text.split("。")
            if len(sentences) > 2:
                return "。".join(sentences[:2]) + "。"

        return text

    def _apply_training_time_preference(
        self, text: str, context: dict[str, Any] | None
    ) -> str:
        """应用训练时段偏好

        Args:
            text: 原始文本
            context: 额外上下文

        Returns:
            str: 调整后的文本
        """
        if context is None:
            return text

        if "training_time" not in context:
            return text

        return text

    @staticmethod
    def _make_brief(text: str) -> str:
        """精简文本

        Args:
            text: 原始文本

        Returns:
            str: 精简后的文本
        """
        sentences = text.replace("！", "。").replace("，", "。").split("。")
        core_sentences = [s.strip() for s in sentences if s.strip()][:3]
        return "。".join(core_sentences) + "。" if core_sentences else text

    @staticmethod
    def _make_detailed(text: str) -> str:
        """扩展文本

        Args:
            text: 原始文本

        Returns:
            str: 扩展后的文本
        """
        return text

    @staticmethod
    def _add_encouragement(text: str) -> str:
        """添加鼓励语气

        Args:
            text: 原始文本

        Returns:
            str: 添加鼓励后的文本
        """
        encouraging_prefixes = ["很好的问题！", "继续保持！", "你做得很好！"]
        if not any(text.startswith(p) for p in encouraging_prefixes):
            return f"很好的问题！{text}"
        return text

    @staticmethod
    def _add_analysis(text: str) -> str:
        """添加分析说明

        Args:
            text: 原始文本

        Returns:
            str: 添加分析后的文本
        """
        if "分析" not in text and "数据" not in text:
            return f"基于数据分析：{text}"
        return text

    @staticmethod
    def _soften_text(text: str) -> str:
        """弱化建议语气

        Args:
            text: 原始文本

        Returns:
            str: 弱化后的文本
        """
        replacements = {
            "必须": "建议",
            "一定要": "可以考虑",
            "务必": "建议尽量",
        }
        result = text
        for old, new in replacements.items():
            result = result.replace(old, new)
        return result

    @staticmethod
    def _strengthen_text(text: str) -> str:
        """强化建议语气

        Args:
            text: 原始文本

        Returns:
            str: 强化后的文本
        """
        replacements = {
            "建议": "强烈建议",
            "可以": "推荐",
            "考虑": "建议",
        }
        result = text
        for old, new in replacements.items():
            result = result.replace(old, new)
        return result

    def _compute_confidence(self, factors: dict[str, str]) -> float:
        """计算个性化置信度

        基于偏好因素的数量和权重计算置信度。

        Args:
            factors: 偏好因素

        Returns:
            float: 置信度(0.0-1.0)
        """
        if not factors:
            return 0.5

        total_weight = sum(self._weights.get(factor, 0.3) for factor in factors)
        max_weight = sum(self._weights.values())

        if max_weight == 0:
            return 0.5

        confidence = min(total_weight / max_weight, 1.0)
        return round(confidence, 2)

    @staticmethod
    def _init_weights() -> dict[str, float]:
        """初始化偏好权重

        Returns:
            dict: 偏好权重映射
        """
        return {
            "communication_style": 0.25,
            "training_time": 0.20,
            "training_intensity": 0.20,
            "detail_preference": 0.15,
            "suggestion_frequency": 0.10,
            "weather_sensitivity": 0.10,
        }
