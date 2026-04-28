# 人格进化与个性化数据模型
# 定义用户偏好、个性化建议、反馈记录、AI人格等核心数据结构

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class FeedbackType(Enum):
    """反馈类型"""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    CORRECTION = "correction"


class PreferenceCategory(Enum):
    """偏好类别"""

    TRAINING_TIME = "training_time"
    TRAINING_INTENSITY = "training_intensity"
    COMMUNICATION_STYLE = "communication_style"
    SUGGESTION_FREQUENCY = "suggestion_frequency"
    DETAIL_PREFERENCE = "detail_preference"
    PACE_PREFERENCE = "pace_preference"
    DISTANCE_PREFERENCE = "distance_preference"
    WEATHER_SENSITIVITY = "weather_sensitivity"


class SuggestionType(Enum):
    """建议类型"""

    TRAINING_PLAN = "training_plan"
    RECOVERY_ADVICE = "recovery_advice"
    PACE_GUIDANCE = "pace_guidance"
    WEATHER_ADVICE = "weather_advice"
    NUTRITION_TIP = "nutrition_tip"
    INJURY_PREVENTION = "injury_prevention"
    GENERAL = "general"


@dataclass(frozen=True)
class UserPreferences:
    """用户偏好（不可变数据类）

    存储用户在训练和交互方面的偏好设置。
    通过PreferenceLearner从用户反馈中自动学习得到。

    Attributes:
        training_time: 偏好训练时段（morning/afternoon/evening）
        training_intensity: 偏好训练强度（low/medium/high）
        communication_style: 偏好沟通风格（brief/detailed/encouraging/analytical）
        suggestion_frequency: 偏好建议频率（minimal/moderate/frequent）
        detail_preference: 偏好详细程度（concise/standard/detailed）
        pace_preference: 偏好配速范围描述
        distance_preference: 偏好距离范围描述
        weather_sensitivity: 天气敏感度（low/medium/high）
        custom_preferences: 自定义偏好键值对
    """

    training_time: str = "morning"
    training_intensity: str = "medium"
    communication_style: str = "encouraging"
    suggestion_frequency: str = "moderate"
    detail_preference: str = "standard"
    pace_preference: str = ""
    distance_preference: str = ""
    weather_sensitivity: str = "medium"
    custom_preferences: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        result: dict[str, Any] = {
            "training_time": self.training_time,
            "training_intensity": self.training_intensity,
            "communication_style": self.communication_style,
            "suggestion_frequency": self.suggestion_frequency,
            "detail_preference": self.detail_preference,
            "pace_preference": self.pace_preference,
            "distance_preference": self.distance_preference,
            "weather_sensitivity": self.weather_sensitivity,
        }
        if self.custom_preferences:
            result["custom_preferences"] = self.custom_preferences
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UserPreferences":
        """从字典创建实例

        Args:
            data: 偏好字典

        Returns:
            UserPreferences: 用户偏好实例
        """
        return cls(
            training_time=data.get("training_time", "morning"),
            training_intensity=data.get("training_intensity", "medium"),
            communication_style=data.get("communication_style", "encouraging"),
            suggestion_frequency=data.get("suggestion_frequency", "moderate"),
            detail_preference=data.get("detail_preference", "standard"),
            pace_preference=data.get("pace_preference", ""),
            distance_preference=data.get("distance_preference", ""),
            weather_sensitivity=data.get("weather_sensitivity", "medium"),
            custom_preferences=data.get("custom_preferences", {}),
        )

    @classmethod
    def default(cls) -> "UserPreferences":
        """创建默认偏好

        Returns:
            UserPreferences: 默认偏好实例
        """
        return cls()


@dataclass(frozen=True)
class PersonalizedSuggestion:
    """个性化建议（不可变数据类）

    经过个性化引擎调整后的建议，包含原始建议和个性化调整信息。

    Attributes:
        id: 建议唯一标识
        original_text: 原始建议文本
        personalized_text: 个性化调整后的建议文本
        suggestion_type: 建议类型
        confidence: 建议置信度（0.0-1.0）
        preference_factors: 影响此建议的偏好因素
        timestamp: 建议生成时间
    """

    id: str
    original_text: str
    personalized_text: str
    suggestion_type: SuggestionType = SuggestionType.GENERAL
    confidence: float = 0.5
    preference_factors: dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "original_text": self.original_text,
            "personalized_text": self.personalized_text,
            "suggestion_type": self.suggestion_type.value,
            "confidence": self.confidence,
            "preference_factors": self.preference_factors,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass(frozen=True)
class FeedbackRecord:
    """反馈记录（不可变数据类）

    用户对AI建议的反馈，用于偏好学习。

    Attributes:
        id: 反馈记录唯一标识
        feedback_type: 反馈类型
        content: 反馈内容
        suggestion_id: 关联的建议ID
        preference_category: 偏好类别
        timestamp: 反馈时间
        session_key: 会话标识
        accepted: 用户是否接受了建议
    """

    id: str
    feedback_type: FeedbackType
    content: str
    suggestion_id: str = ""
    preference_category: PreferenceCategory = PreferenceCategory.COMMUNICATION_STYLE
    timestamp: datetime = field(default_factory=datetime.now)
    session_key: str = ""
    accepted: bool = True

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "feedback_type": self.feedback_type.value,
            "content": self.content,
            "suggestion_id": self.suggestion_id,
            "preference_category": self.preference_category.value,
            "timestamp": self.timestamp.isoformat(),
            "session_key": self.session_key,
            "accepted": self.accepted,
        }


@dataclass(frozen=True)
class Personality:
    """AI人格（不可变数据类）

    描述AI教练的沟通风格和人格特征。

    Attributes:
        communication_style: 沟通风格（brief/detailed/encouraging/analytical）
        suggestion_approach: 建议方式（direct/gradual/collaborative）
        expression_habits: 表达习惯描述
        empathy_level: 共情等级（0.0-1.0）
        detail_level: 详细程度（concise/standard/detailed）
        humor_level: 幽默程度（0.0-1.0）
        motivation_style: 激励风格（supportive/challenging/balanced）
    """

    communication_style: str = "encouraging"
    suggestion_approach: str = "gradual"
    expression_habits: str = ""
    empathy_level: float = 0.7
    detail_level: str = "standard"
    humor_level: float = 0.3
    motivation_style: str = "supportive"

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "communication_style": self.communication_style,
            "suggestion_approach": self.suggestion_approach,
            "expression_habits": self.expression_habits,
            "empathy_level": self.empathy_level,
            "detail_level": self.detail_level,
            "humor_level": self.humor_level,
            "motivation_style": self.motivation_style,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Personality":
        """从字典创建实例

        Args:
            data: 人格字典

        Returns:
            Personality: AI人格实例
        """
        return cls(
            communication_style=data.get("communication_style", "encouraging"),
            suggestion_approach=data.get("suggestion_approach", "gradual"),
            expression_habits=data.get("expression_habits", ""),
            empathy_level=data.get("empathy_level", 0.7),
            detail_level=data.get("detail_level", "standard"),
            humor_level=data.get("humor_level", 0.3),
            motivation_style=data.get("motivation_style", "supportive"),
        )

    @classmethod
    def default(cls) -> "Personality":
        """创建默认人格

        Returns:
            Personality: 默认人格实例
        """
        return cls()


@dataclass(frozen=True)
class PersonalityVersion:
    """人格版本（不可变数据类）

    记录人格进化的历史版本，支持版本回溯。

    Attributes:
        version: 版本号
        timestamp: 版本创建时间
        personality: 人格快照
        changes: 相较上一版本的变更描述
        trigger: 触发变更的原因
    """

    version: str
    timestamp: datetime
    personality: Personality
    changes: list[str] = field(default_factory=list)
    trigger: str = ""

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "version": self.version,
            "timestamp": self.timestamp.isoformat(),
            "personality": self.personality.to_dict(),
            "changes": self.changes,
            "trigger": self.trigger,
        }
