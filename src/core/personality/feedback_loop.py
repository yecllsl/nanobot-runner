# 反馈闭环机制
# 用户反馈收集→偏好更新→效果追踪的完整闭环
# 反馈处理响应时间<500ms

import logging
import uuid
from datetime import datetime
from typing import Any

from src.core.personality.models import (
    FeedbackRecord,
    FeedbackType,
    PersonalizedSuggestion,
    PreferenceCategory,
    UserPreferences,
)
from src.core.personality.preference_learner import PreferenceLearner

logger = logging.getLogger(__name__)


class FeedbackLoop:
    """反馈闭环管理器

    实现用户反馈收集→偏好更新→效果追踪的完整闭环。

    闭环流程：
    1. 收集用户反馈（显式或隐式）
    2. 通过PreferenceLearner更新偏好
    3. 追踪偏好更新后的效果
    4. 评估闭环效果并持续优化

    Attributes:
        learner: 偏好学习器
        _effect_records: 效果追踪记录
    """

    def __init__(self, learner: PreferenceLearner) -> None:
        """初始化反馈闭环

        Args:
            learner: 偏好学习器实例
        """
        self.learner = learner
        self._effect_records: list[dict[str, Any]] = []

    def collect_feedback(
        self,
        feedback_type: FeedbackType,
        content: str,
        suggestion_id: str = "",
        preference_category: PreferenceCategory = PreferenceCategory.COMMUNICATION_STYLE,
        session_key: str = "",
        accepted: bool = True,
    ) -> FeedbackRecord:
        """收集用户反馈

        Args:
            feedback_type: 反馈类型
            content: 反馈内容
            suggestion_id: 关联的建议ID
            preference_category: 偏好类别
            session_key: 会话标识
            accepted: 是否接受建议

        Returns:
            FeedbackRecord: 反馈记录
        """
        record = FeedbackRecord(
            id=str(uuid.uuid4())[:8],
            feedback_type=feedback_type,
            content=content,
            suggestion_id=suggestion_id,
            preference_category=preference_category,
            timestamp=datetime.now(),
            session_key=session_key,
            accepted=accepted,
        )

        logger.info(
            f"收集反馈: type={feedback_type.value}, "
            f"category={preference_category.value}, "
            f"accepted={accepted}"
        )

        return record

    def process_feedback(self, feedback: FeedbackRecord) -> UserPreferences:
        """处理反馈并更新偏好

        将反馈传递给PreferenceLearner进行偏好学习。

        Args:
            feedback: 反馈记录

        Returns:
            UserPreferences: 更新后的偏好
        """
        old_preferences = self.learner.get_learned_preferences()

        new_preferences = self.learner.learn_from_feedback(feedback)

        changed = old_preferences.to_dict() != new_preferences.to_dict()
        if changed:
            self._record_effect(
                feedback_id=feedback.id,
                old_preferences=old_preferences,
                new_preferences=new_preferences,
                changed=True,
            )
            logger.info("偏好已根据反馈更新")
        else:
            logger.debug("反馈未触发偏好变更")

        return new_preferences

    def track_suggestion_effect(
        self,
        suggestion: PersonalizedSuggestion,
        accepted: bool,
        user_comment: str = "",
    ) -> dict[str, Any]:
        """追踪建议效果

        记录个性化建议的接受情况和用户评价。

        Args:
            suggestion: 个性化建议
            accepted: 用户是否接受
            user_comment: 用户评价

        Returns:
            dict: 效果追踪结果
        """
        effect_record = {
            "suggestion_id": suggestion.id,
            "suggestion_type": suggestion.suggestion_type.value,
            "confidence": suggestion.confidence,
            "accepted": accepted,
            "user_comment": user_comment,
            "preference_factors": suggestion.preference_factors,
            "timestamp": datetime.now().isoformat(),
        }

        self._effect_records.append(effect_record)

        if not accepted:
            feedback = self.collect_feedback(
                feedback_type=FeedbackType.NEGATIVE,
                content=user_comment or "建议未被接受",
                suggestion_id=suggestion.id,
            )
            self.process_feedback(feedback)

        logger.info(
            f"建议效果追踪: id={suggestion.id}, "
            f"accepted={accepted}, "
            f"confidence={suggestion.confidence}"
        )

        return effect_record

    def get_effect_stats(self) -> dict[str, Any]:
        """获取效果统计

        Returns:
            dict: 效果统计数据
        """
        if not self._effect_records:
            return {
                "total_suggestions": 0,
                "accepted_count": 0,
                "rejected_count": 0,
                "acceptance_rate": 0.0,
                "avg_confidence": 0.0,
            }

        total = len(self._effect_records)
        accepted = sum(1 for r in self._effect_records if r.get("accepted", False))
        confidences = [
            r.get("confidence", 0.0)
            for r in self._effect_records
            if r.get("confidence") is not None
        ]

        return {
            "total_suggestions": total,
            "accepted_count": accepted,
            "rejected_count": total - accepted,
            "acceptance_rate": round(accepted / total, 4) if total > 0 else 0.0,
            "avg_confidence": (
                round(sum(confidences) / len(confidences), 4) if confidences else 0.0
            ),
        }

    def _record_effect(
        self,
        feedback_id: str,
        old_preferences: UserPreferences,
        new_preferences: UserPreferences,
        changed: bool,
    ) -> None:
        """记录偏好变更效果

        Args:
            feedback_id: 反馈ID
            old_preferences: 变更前偏好
            new_preferences: 变更后偏好
            changed: 是否发生变更
        """
        old_dict = old_preferences.to_dict()
        new_dict = new_preferences.to_dict()
        changes = {
            k: {"old": old_dict[k], "new": new_dict[k]}
            for k in old_dict
            if old_dict[k] != new_dict[k]
        }

        self._effect_records.append(
            {
                "feedback_id": feedback_id,
                "type": "preference_change",
                "changed": changed,
                "changes": changes,
                "timestamp": datetime.now().isoformat(),
            }
        )
