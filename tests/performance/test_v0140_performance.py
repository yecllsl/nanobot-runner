# v0.14.0 AI教练进化版 性能测试
# 验证记忆加载、偏好加载、反馈处理等性能指标

import json
import time
from pathlib import Path

from src.core.memory.dream_integration import DreamIntegration
from src.core.memory.memory_manager import MemoryManager
from src.core.personality.feedback_loop import FeedbackLoop
from src.core.personality.models import (
    FeedbackRecord,
    FeedbackType,
    Personality,
    PreferenceCategory,
)
from src.core.personality.personalization_engine import PersonalizationEngine
from src.core.personality.preference_learner import PreferenceLearner


class TestMemoryPerformance:
    """记忆管理性能测试"""

    def test_memory_load_time(self, tmp_path: Path):
        """TC-PERF-001: 记忆加载时间 < 100ms"""
        manager = MemoryManager(tmp_path)

        # 写入较大记忆内容
        large_content = "# 项目记忆\n\n" + "\n".join(
            [f"- 训练记录{i}: 5km 轻松跑" for i in range(100)]
        )
        manager.write_memory(large_content)

        # 测量加载时间
        start = time.perf_counter()
        content = manager.read_memory()
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert content == large_content
        assert elapsed_ms < 100, f"记忆加载时间{elapsed_ms:.2f}ms >= 100ms"

    def test_personality_load_time(self, tmp_path: Path):
        """TC-PERF-002: 偏好数据加载时间 < 100ms"""
        manager = MemoryManager(tmp_path)

        personality = Personality(
            communication_style="analytical",
            empathy_level=0.9,
            humor_level=0.5,
            motivation_style="challenging",
        )
        manager.write_personality(personality)

        # 测量加载时间
        start = time.perf_counter()
        loaded = manager.read_personality()
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert loaded.communication_style == "analytical"
        assert elapsed_ms < 100, f"人格加载时间{elapsed_ms:.2f}ms >= 100ms"

    def test_backup_creation_time(self, tmp_path: Path):
        """TC-PERF-004: 记忆备份创建时间 < 1秒"""
        manager = MemoryManager(tmp_path)

        # 写入记忆
        manager.write_memory("# 记忆内容\n" * 100)
        manager.write_user_profile("# 用户画像\n" * 50)

        # 测量备份时间
        start = time.perf_counter()
        backup_path = manager.create_backup()
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert backup_path != ""
        assert elapsed_ms < 1000, f"备份创建时间{elapsed_ms:.2f}ms >= 1000ms"


class TestPersonalityPerformance:
    """人格进化性能测试"""

    def test_feedback_processing_time(self):
        """TC-PERF-003: 反馈处理响应时间 < 500ms"""
        learner = PreferenceLearner(learning_rate=0.3)
        loop = FeedbackLoop(learner)

        feedback = FeedbackRecord(
            id="fb-perf-001",
            feedback_type=FeedbackType.POSITIVE,
            content="我喜欢evening跑步，简洁风格",
            preference_category=PreferenceCategory.TRAINING_TIME,
        )

        start = time.perf_counter()
        loop.process_feedback(feedback)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 500, f"反馈处理时间{elapsed_ms:.2f}ms >= 500ms"

    def test_personality_evolution_computation_time(self):
        """TC-PERF-005: 人格进化计算时间 < 100ms"""
        learner = PreferenceLearner(learning_rate=1.0)

        # 先积累一些反馈
        for i in range(5):
            feedback = FeedbackRecord(
                id=f"fb-perf-{i}",
                feedback_type=FeedbackType.POSITIVE,
                content="evening",
                preference_category=PreferenceCategory.TRAINING_TIME,
            )
            learner.learn_from_feedback(feedback)

        # 测量最后一次学习的时间
        feedback = FeedbackRecord(
            id="fb-perf-final",
            feedback_type=FeedbackType.POSITIVE,
            content="evening",
            preference_category=PreferenceCategory.TRAINING_TIME,
        )

        start = time.perf_counter()
        learner.learn_from_feedback(feedback)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 100, f"人格进化计算时间{elapsed_ms:.2f}ms >= 100ms"

    def test_personalization_suggestion_time(self):
        """个性化建议生成时间 < 50ms"""
        engine = PersonalizationEngine()

        suggestion_text = "建议今天进行轻松跑，距离5公里，注意补充水分，保持良好心态。"

        start = time.perf_counter()
        suggestion = engine.personalize_suggestion(suggestion_text)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert suggestion.personalized_text != ""
        assert elapsed_ms < 50, f"个性化建议生成时间{elapsed_ms:.2f}ms >= 50ms"


class TestDreamPerformance:
    """Dream集成性能测试"""

    def test_dream_config_load_time(self, tmp_path: Path):
        """Dream配置加载时间 < 50ms"""
        config_path = tmp_path / "config.json"
        config_data = {
            "dream": {
                "enabled": True,
                "frequency": "daily",
                "auto_archive": True,
                "auto_extract_preferences": True,
            }
        }
        config_path.write_text(json.dumps(config_data), encoding="utf-8")
        dream = DreamIntegration(config_path)

        start = time.perf_counter()
        config = dream.get_dream_config()
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert config["enabled"] is True
        assert elapsed_ms < 50, f"Dream配置加载时间{elapsed_ms:.2f}ms >= 50ms"
