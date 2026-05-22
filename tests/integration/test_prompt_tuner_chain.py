"""集成测试: PromptTuner全链路 (T13)

验证参数初始化 -> 手动调整 -> 自动调整 -> 持久化 -> 加载 的完整链路。
"""

from __future__ import annotations

from typing import Any

import pytest

from src.core.evolution.config import EvolutionConfig
from src.core.evolution.evolution_store import EvolutionStore
from src.core.evolution.prompt_tuner import PromptTuner


@pytest.fixture
def tuner_with_real_store(tmp_path: Any) -> tuple[PromptTuner, EvolutionStore]:
    """创建使用真实Store的PromptTuner"""
    store = EvolutionStore(tmp_path)
    config = EvolutionConfig(data_dir=str(tmp_path))
    tuner = PromptTuner(store=store, config=config)
    return tuner, store


class TestPromptTunerFullChain:
    """PromptTuner全链路集成测试"""

    def test_init_to_persistence_roundtrip(
        self, tuner_with_real_store: tuple[PromptTuner, EvolutionStore]
    ) -> None:
        """初始化 -> 调整 -> 持久化 -> 重新加载"""
        tuner, store = tuner_with_real_store

        # 1. 初始默认参数
        params = tuner.get_params()
        assert params.tone_intensity == 0.5

        # 2. 手动调整
        updated = tuner.update_params(tone=0.7, aggressive=0.3)
        assert updated.tone_intensity == 0.7
        assert updated.recommendation_aggressiveness == 0.3

        # 3. 验证持久化
        store.save_prompt_tuning_params(updated)
        loaded = store.load_prompt_tuning_params()
        assert loaded is not None
        assert loaded.tone_intensity == 0.7

        # 4. 重新创建tuner加载
        tuner2 = PromptTuner(
            store=store, config=EvolutionConfig(data_dir=str(store._data_dir))
        )
        params2 = tuner2.get_params()
        assert params2.tone_intensity == 0.7

    def test_auto_adjust_on_feedback_chain(
        self, tuner_with_real_store: tuple[PromptTuner, EvolutionStore]
    ) -> None:
        """反馈调整链路: 低评分 -> 降低语气/激进 -> 高评分 -> 恢复"""
        tuner, _ = tuner_with_real_store

        # 低评分调整（acceptance_rate=0.29 < 0.3阈值，触发降低aggressive）
        low_result = tuner.auto_adjust_on_feedback(avg_score=2.0, acceptance_rate=0.29)
        assert low_result.tone_intensity < 0.5
        assert low_result.recommendation_aggressiveness < 0.5

        # 高评分恢复（反弹机制）
        high_result = tuner.auto_adjust_on_feedback(avg_score=4.5, acceptance_rate=0.8)
        assert high_result.tone_intensity > low_result.tone_intensity

    def test_rejection_floor_protection_chain(
        self, tuner_with_real_store: tuple[PromptTuner, EvolutionStore]
    ) -> None:
        """拒绝下限保护链路: 连续拒绝 -> 触及下限 -> 不低于0.1/0.2"""
        tuner, _ = tuner_with_real_store

        for _ in range(20):
            tuner.auto_adjust_on_rejection()

        params = tuner.get_params()
        assert params.recommendation_aggressiveness >= 0.1
        assert params.data_driven_weight >= 0.2

    def test_reset_to_default_chain(
        self, tuner_with_real_store: tuple[PromptTuner, EvolutionStore]
    ) -> None:
        """重置链路: 调整 -> 重置 -> 验证全部0.5"""
        tuner, _ = tuner_with_real_store

        tuner.update_params(tone=0.9, aggressive=0.1, detail=0.8, data_driven=0.2)
        reset = tuner.reset_to_default()
        assert reset.tone_intensity == 0.5
        assert reset.recommendation_aggressiveness == 0.5
        assert reset.detail_level_score == 0.5
        assert reset.data_driven_weight == 0.5
        assert reset.update_count == 0
