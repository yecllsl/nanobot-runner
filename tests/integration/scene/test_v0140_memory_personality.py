# v0.14.0 AI教练进化版 场景级集成测试
# 覆盖记忆管理、人格进化、Dream集成、跨会话连贯等核心场景

from pathlib import Path

from src.core.memory.dream_integration import DreamIntegration
from src.core.memory.memory_manager import MemoryManager
from src.core.personality.feedback_loop import FeedbackLoop
from src.core.personality.models import (
    FeedbackRecord,
    FeedbackType,
    Personality,
    PreferenceCategory,
    UserPreferences,
)
from src.core.personality.personalization_engine import PersonalizationEngine
from src.core.personality.preference_learner import PreferenceLearner


class TestMemoryFlow:
    """记忆写入→读取→备份→恢复完整链路"""

    def test_memory_write_read_backup_restore(self, tmp_path: Path):
        """TC-SCENE-001: 记忆写入→读取→备份→恢复全流程"""
        manager = MemoryManager(tmp_path)

        # 写入记忆
        original_content = "# 项目记忆\n\n## 训练历史\n- 2024-01-01: 5km 轻松跑\n"
        manager.write_memory(original_content)
        manager.write_user_profile("# 用户画像\n- 目标: 半马\n")

        # 读取验证
        read_content = manager.read_memory()
        assert read_content == original_content

        # 创建备份
        backup_path = manager.create_backup()
        assert backup_path != ""
        assert Path(backup_path).exists()

        # 修改记忆
        manager.write_memory("# 修改后的记忆\n")
        assert manager.read_memory() == "# 修改后的记忆\n"

        # 恢复备份
        result = manager.restore_backup(Path(backup_path))
        assert result is True

        # 验证恢复内容
        restored_content = manager.read_memory()
        assert "训练历史" in restored_content
        assert "5km 轻松跑" in restored_content

    def test_cross_session_memory_consistency(self, tmp_path: Path):
        """TC-SCENE-004: 跨会话记忆连贯性"""
        # 第一次会话：写入记忆
        manager_session1 = MemoryManager(tmp_path)
        manager_session1.write_memory(
            "# 记忆\n\n## 用户偏好\n- training_time: morning\n"
        )
        manager_session1.write_personality(
            Personality(communication_style="encouraging")
        )

        # 模拟新会话：重新初始化
        manager_session2 = MemoryManager(tmp_path)

        # 验证记忆连贯
        assert "training_time: morning" in manager_session2.read_memory()
        personality = manager_session2.read_personality()
        assert personality.communication_style == "encouraging"

    def test_memory_version_list_and_restore(self, tmp_path: Path):
        """TC-SCENE-005: 人格版本回溯"""
        manager = MemoryManager(tmp_path)

        # 创建多个版本
        manager.write_memory("版本1内容")
        backup1 = manager.create_backup()

        manager.write_memory("版本2内容")
        backup2 = manager.create_backup()

        # 列出所有版本
        versions = manager.list_versions()
        assert len(versions) == 2

        # 恢复到第一个版本
        manager.restore_backup(Path(backup1))
        assert manager.read_memory() == "版本1内容"


class TestPersonalityEvolutionFlow:
    """反馈收集→偏好学习→人格进化完整链路"""

    def test_feedback_to_personality_evolution(self, tmp_path: Path):
        """TC-SCENE-002: 反馈收集→偏好学习→人格进化"""
        learner = PreferenceLearner(learning_rate=1.0)
        loop = FeedbackLoop(learner)

        # 初始偏好
        initial_prefs = learner.get_learned_preferences()
        assert initial_prefs.training_time == "morning"

        # 多次反馈训练时段偏好
        for i in range(3):
            feedback = FeedbackRecord(
                id=f"fb-{i}",
                feedback_type=FeedbackType.POSITIVE,
                content="我喜欢evening跑步",
                preference_category=PreferenceCategory.TRAINING_TIME,
            )
            loop.process_feedback(feedback)

        # 验证偏好已更新
        updated_prefs = learner.get_learned_preferences()
        assert updated_prefs.training_time == "evening"

    def test_preference_learning_accuracy(self):
        """TC-SCENE-006: 偏好学习准确率验证"""
        learner = PreferenceLearner(learning_rate=1.0)
        loop = FeedbackLoop(learner)

        # 构造已知偏好反馈
        test_cases = [
            ("evening", PreferenceCategory.TRAINING_TIME),
            ("brief", PreferenceCategory.COMMUNICATION_STYLE),
            ("high", PreferenceCategory.TRAINING_INTENSITY),
        ]

        correct_count = 0
        total_count = len(test_cases)

        for expected_value, category in test_cases:
            for _ in range(3):
                feedback = FeedbackRecord(
                    id=f"fb-{category.value}-{_}",
                    feedback_type=FeedbackType.POSITIVE,
                    content=expected_value,
                    preference_category=category,
                )
                loop.process_feedback(feedback)

            prefs = learner.get_learned_preferences()
            actual_value = prefs.to_dict().get(category.value)
            if actual_value == expected_value:
                correct_count += 1

        accuracy = correct_count / total_count
        assert accuracy >= 0.85, f"偏好学习准确率{accuracy:.2%} < 85%"


class TestDreamIntegrationFlow:
    """Dream配置→自动归档→偏好提取完整链路"""

    def test_dream_config_and_trigger(self, tmp_path: Path):
        """TC-SCENE-003: Dream配置→自动归档→偏好提取"""
        config_path = tmp_path / "config.json"
        config_path.write_text("{}", encoding="utf-8")
        dream = DreamIntegration(config_path, workspace=tmp_path)

        # 启用自动归档
        result = dream.enable_auto_archive()
        assert result is True

        # 启用偏好自动提取
        result = dream.enable_auto_extract_preferences()
        assert result is True

        # 验证配置
        status = dream.get_dream_status()
        assert status["auto_archive"] is True
        assert status["auto_extract_preferences"] is True

        # 触发Dream整理
        result = dream.trigger_dream()
        assert result["success"] is True

    def test_dream_config_persistence(self, tmp_path: Path):
        """TC-DREAM-012: Dream配置持久化"""
        config_path = tmp_path / "config.json"
        config_path.write_text("{}", encoding="utf-8")
        dream = DreamIntegration(config_path)

        # 更新配置
        dream.update_dream_config(frequency="weekly", auto_archive=False)

        # 重新加载配置
        dream2 = DreamIntegration(config_path)
        config = dream2.get_dream_config()

        assert config["frequency"] == "weekly"
        assert config["auto_archive"] is False


class TestMemoryPersonalityCollaboration:
    """记忆+人格协同工作"""

    def test_memory_to_personality_flow(self, tmp_path: Path):
        """TC-SCENE-007: 记忆+人格协同工作"""
        manager = MemoryManager(tmp_path)

        # 写入偏好到记忆
        manager.write_memory(
            "# 项目记忆\n\n## 用户偏好\n- training_time: evening\n- communication_style: brief\n"
        )

        # 从记忆加载偏好
        prefs_dict = manager.load_preference_from_memory()
        assert prefs_dict.get("training_time") == "evening"
        assert prefs_dict.get("communication_style") == "brief"

        # 应用到个性化引擎
        prefs = UserPreferences.from_dict(prefs_dict)
        engine = PersonalizationEngine(preferences=prefs)

        # 生成个性化建议
        suggestion = engine.personalize_suggestion(
            "建议今天进行轻松跑，距离5公里，注意补充水分，保持良好心态。"
        )

        # 验证偏好已应用
        assert suggestion.preference_factors.get("communication_style") == "brief"
        assert suggestion.preference_factors.get("training_time") == "evening"

    def test_full_memory_personality_cycle(self, tmp_path: Path):
        """完整记忆-人格循环：记忆→偏好→学习→更新→记忆"""
        manager = MemoryManager(tmp_path)
        learner = PreferenceLearner(learning_rate=1.0)
        loop = FeedbackLoop(learner)

        # 初始记忆
        manager.write_memory("# 项目记忆\n\n## 用户偏好\n- training_time: morning\n")

        # 从记忆加载初始偏好
        initial_prefs = manager.load_preference_from_memory()
        learner.update_preference_model(initial_prefs)

        # 用户反馈更新偏好
        for _ in range(3):
            feedback = FeedbackRecord(
                id=f"fb-cycle-{_}",
                feedback_type=FeedbackType.POSITIVE,
                content="evening",
                preference_category=PreferenceCategory.TRAINING_TIME,
            )
            loop.process_feedback(feedback)

        # 保存更新后的偏好到记忆
        updated_prefs = learner.get_learned_preferences()
        manager.save_preference_to_memory(updated_prefs.to_dict())

        # 验证记忆已更新
        final_prefs = manager.load_preference_from_memory()
        assert final_prefs.get("training_time") == "evening"
