# 偏好学习器核心实现
# 从用户反馈中学习偏好，渐进式更新偏好模型
# 学习速率可配置，避免过度拟合

import logging
from typing import Any, TypedDict, cast

from src.core.personality.models import (
    FeedbackRecord,
    FeedbackType,
    Personality,
    PreferenceCategory,
    UserPreferences,
)

logger = logging.getLogger(__name__)


class FeedbackStats(TypedDict):
    """反馈统计数据

    Attributes:
        total_feedback: 反馈总数
        positive_count: 正面反馈数
        negative_count: 负面反馈数
        neutral_count: 中性反馈数
        correction_count: 纠正反馈数
        category_distribution: 各偏好类别的反馈分布
    """

    total_feedback: int
    positive_count: int
    negative_count: int
    neutral_count: int
    correction_count: int
    category_distribution: dict[str, int]


class PreferenceLearner:
    """偏好学习器

    从用户反馈中学习偏好，渐进式更新偏好模型。
    核心接口：
    - learn_from_feedback: 从反馈中学习偏好
    - update_preference_model: 更新偏好模型
    - get_learned_preferences: 获取学习到的偏好
    - reset_preferences: 重置偏好到默认值

    学习策略：
    - 渐进式学习：每次反馈只做小幅调整
    - 多数投票：同一偏好需要多次反馈才确认变更
    - 可配置学习速率：控制偏好更新速度

    Attributes:
        preferences: 当前偏好
        personality: 当前AI人格
        _feedback_history: 反馈历史
        _learning_rate: 学习速率(0.0-1.0)
        _category_votes: 偏好类别投票计数
    """

    def __init__(
        self,
        preferences: UserPreferences | None = None,
        personality: Personality | None = None,
        learning_rate: float = 0.3,
    ) -> None:
        """初始化偏好学习器

        Args:
            preferences: 初始偏好（可选，默认使用默认偏好）
            personality: 初始AI人格（可选，默认使用默认人格）
            learning_rate: 学习速率(0.0-1.0)，值越大学习越快
        """
        self.preferences = preferences or UserPreferences.default()
        self.personality = personality or Personality.default()
        self._feedback_history: list[FeedbackRecord] = []
        self._learning_rate = max(0.0, min(1.0, learning_rate))
        self._category_votes: dict[str, dict[str, int]] = {}

    def learn_from_feedback(self, feedback: FeedbackRecord) -> UserPreferences:
        """从反馈中学习偏好

        根据用户反馈内容分析偏好变化，渐进式更新偏好模型。

        Args:
            feedback: 用户反馈记录

        Returns:
            UserPreferences: 更新后的偏好
        """
        self._feedback_history.append(feedback)

        category = feedback.preference_category.value
        if category not in self._category_votes:
            self._category_votes[category] = {}

        extracted = self._extract_preference_from_feedback(feedback)
        for key, value in extracted.items():
            if value not in self._category_votes[category]:
                self._category_votes[category][value] = 0
            self._category_votes[category][value] += 1

        if feedback.feedback_type == FeedbackType.NEGATIVE:
            self._handle_negative_feedback(feedback)

        if self._should_update_preference(category):
            self.preferences = self._compute_new_preferences(category)

        logger.info(
            f"偏好学习: category={category}, "
            f"feedback_type={feedback.feedback_type.value}, "
            f"extracted={extracted}"
        )

        return self.preferences

    def update_preference_model(self, updates: dict[str, str]) -> UserPreferences:
        """直接更新偏好模型

        通过显式参数更新偏好，用于CLI命令或配置导入场景。

        Args:
            updates: 偏好更新键值对，key为偏好字段名，value为新值

        Returns:
            UserPreferences: 更新后的偏好
        """
        current_dict = self.preferences.to_dict()

        for key, value in updates.items():
            if key in current_dict:
                current_dict[key] = value
                logger.info(f"偏好直接更新: {key}={value}")

        self.preferences = UserPreferences.from_dict(current_dict)
        return self.preferences

    def get_learned_preferences(self) -> UserPreferences:
        """获取学习到的偏好

        Returns:
            UserPreferences: 当前偏好
        """
        return self.preferences

    def get_personality(self) -> Personality:
        """获取当前AI人格

        Returns:
            Personality: 当前AI人格
        """
        return self.personality

    def reset_preferences(self) -> UserPreferences:
        """重置偏好到默认值

        Returns:
            UserPreferences: 默认偏好
        """
        self.preferences = UserPreferences.default()
        self._feedback_history.clear()
        self._category_votes.clear()
        logger.info("偏好已重置为默认值")
        return self.preferences

    def reset_personality(self) -> Personality:
        """重置AI人格到默认值

        Returns:
            Personality: 默认AI人格
        """
        self.personality = Personality.default()
        logger.info("AI人格已重置为默认值")
        return self.personality

    def get_feedback_stats(self) -> FeedbackStats:
        """获取反馈统计

        Returns:
            FeedbackStats: 反馈统计数据
        """
        if not self._feedback_history:
            return {
                "total_feedback": 0,
                "positive_count": 0,
                "negative_count": 0,
                "neutral_count": 0,
                "correction_count": 0,
                "category_distribution": {},
            }

        type_counts: dict[str, int] = {}
        category_counts: dict[str, int] = {}

        for fb in self._feedback_history:
            ft = fb.feedback_type.value
            type_counts[ft] = type_counts.get(ft, 0) + 1
            cat = fb.preference_category.value
            category_counts[cat] = category_counts.get(cat, 0) + 1

        return {
            "total_feedback": len(self._feedback_history),
            "positive_count": type_counts.get("positive", 0),
            "negative_count": type_counts.get("negative", 0),
            "neutral_count": type_counts.get("neutral", 0),
            "correction_count": type_counts.get("correction", 0),
            "category_distribution": category_counts,
        }

    def _extract_preference_from_feedback(
        self, feedback: FeedbackRecord
    ) -> dict[str, str]:
        """从反馈中提取偏好信息

        Args:
            feedback: 反馈记录

        Returns:
            dict: 提取的偏好键值对
        """
        content = feedback.content.lower()
        category = feedback.preference_category

        extractors = {
            PreferenceCategory.TRAINING_TIME: self._extract_training_time_preference,
            PreferenceCategory.TRAINING_INTENSITY: self._extract_training_intensity_preference,
            PreferenceCategory.COMMUNICATION_STYLE: self._extract_communication_style_preference,
            PreferenceCategory.DETAIL_PREFERENCE: self._extract_detail_preference,
        }

        extractor = extractors.get(category)
        if extractor is None:
            return {}

        result = extractor(content)
        return dict([result]) if result else {}

    def _extract_training_time_preference(self, content: str) -> tuple[str, str] | None:
        """从内容中提取训练时间偏好"""
        for time_val in ["morning", "afternoon", "evening"]:
            if time_val in content:
                return ("training_time", time_val)
        return None

    def _extract_training_intensity_preference(
        self, content: str
    ) -> tuple[str, str] | None:
        """从内容中提取训练强度偏好"""
        # 英文关键词
        for intensity in ["low", "medium", "high"]:
            if intensity in content:
                return ("training_intensity", intensity)

        # 中文关键词
        for keyword, value in [
            ("轻松", "low"),
            ("适中", "medium"),
            ("高强度", "high"),
        ]:
            if keyword in content:
                return ("training_intensity", value)

        return None

    def _extract_communication_style_preference(
        self, content: str
    ) -> tuple[str, str] | None:
        """从内容中提取沟通风格偏好"""
        # 英文关键词
        for style in ["brief", "detailed", "encouraging", "analytical"]:
            if style in content:
                return ("communication_style", style)

        # 中文关键词
        for keyword, value in [
            ("简洁", "brief"),
            ("详细", "detailed"),
            ("鼓励", "encouraging"),
            ("分析", "analytical"),
        ]:
            if keyword in content:
                return ("communication_style", value)

        return None

    def _extract_detail_preference(self, content: str) -> tuple[str, str] | None:
        """从内容中提取详细度偏好"""
        for level in ["concise", "standard", "detailed"]:
            if level in content:
                return ("detail_preference", level)
        return None

    def _handle_negative_feedback(self, feedback: FeedbackRecord) -> None:
        """处理负面反馈

        负面反馈时降低相关偏好的投票权重。

        Args:
            feedback: 负面反馈记录
        """
        category = feedback.preference_category.value
        current_pref = self._get_current_preference_value(category)

        if (
            current_pref
            and category in self._category_votes
            and current_pref in self._category_votes[category]
        ):
            self._category_votes[category][current_pref] = max(
                0, self._category_votes[category][current_pref] - 1
            )

    def _should_update_preference(self, category: str) -> bool:
        """判断是否应该更新偏好

        基于投票数和学习速率判断是否达到更新阈值。

        Args:
            category: 偏好类别

        Returns:
            bool: 是否应该更新
        """
        if category not in self._category_votes:
            return False

        votes = self._category_votes[category]
        if not votes:
            return False

        max_votes = max(votes.values())
        threshold = max(2, int(3 / self._learning_rate))

        return max_votes >= threshold

    def _compute_new_preferences(self, category: str) -> UserPreferences:
        """根据投票结果计算新偏好

        Args:
            category: 偏好类别

        Returns:
            UserPreferences: 新的偏好
        """
        current_dict = self.preferences.to_dict()

        if category in self._category_votes:
            votes = self._category_votes[category]
            if votes:
                winner = max(votes, key=cast(Any, votes.get))
                category_to_field = {
                    "training_time": "training_time",
                    "training_intensity": "training_intensity",
                    "communication_style": "communication_style",
                    "suggestion_frequency": "suggestion_frequency",
                    "detail_preference": "detail_preference",
                    "pace_preference": "pace_preference",
                    "distance_preference": "distance_preference",
                    "weather_sensitivity": "weather_sensitivity",
                }
                field_name = category_to_field.get(category)
                if field_name and field_name in current_dict:
                    current_dict[field_name] = winner

        return UserPreferences.from_dict(current_dict)

    def _get_current_preference_value(self, category: str) -> str | None:
        """获取当前偏好值

        Args:
            category: 偏好类别

        Returns:
            str | None: 当前偏好值
        """
        pref_dict = self.preferences.to_dict()
        category_to_field = {
            "training_time": "training_time",
            "training_intensity": "training_intensity",
            "communication_style": "communication_style",
            "suggestion_frequency": "suggestion_frequency",
            "detail_preference": "detail_preference",
            "pace_preference": "pace_preference",
            "distance_preference": "distance_preference",
            "weather_sensitivity": "weather_sensitivity",
        }
        field_name = category_to_field.get(category)
        if field_name:
            return pref_dict.get(field_name)
        return None
