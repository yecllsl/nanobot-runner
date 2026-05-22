"""PromptTuner单元测试"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.core.evolution.config import EvolutionConfig
from src.core.evolution.models import PromptTuningParams
from src.core.evolution.prompt_tuner import PromptTuner


@pytest.fixture
def mock_store() -> MagicMock:
    """创建Mock EvolutionStore"""
    store = MagicMock()
    store.load_prompt_tuning_params.return_value = None
    store.save_prompt_tuning_params.return_value = None
    store.get_decision_outcome_pairs.return_value = []
    return store


@pytest.fixture
def tuner(mock_store: MagicMock) -> PromptTuner:
    config = EvolutionConfig(data_dir="/tmp/test_tuner")
    return PromptTuner(store=mock_store, config=config)


class TestGetParams:
    """get_params()测试"""

    def test_returns_default_when_no_file(
        self, tuner: PromptTuner, mock_store: MagicMock
    ) -> None:
        """JSON文件不存在时返回默认参数"""
        mock_store.load_prompt_tuning_params.return_value = None
        params = tuner.get_params()
        assert params.tone_intensity == 0.5
        assert params.recommendation_aggressiveness == 0.5
        assert params.update_count == 0

    def test_loads_from_store(self, tuner: PromptTuner, mock_store: MagicMock) -> None:
        """从EvolutionStore加载已保存的参数"""
        saved_params = PromptTuningParams(
            tone_intensity=0.6,
            detail_level_score=0.4,
            recommendation_aggressiveness=0.7,
            data_driven_weight=0.3,
            update_count=5,
        )
        mock_store.load_prompt_tuning_params.return_value = saved_params
        params = tuner.get_params()
        assert params.tone_intensity == 0.6
        assert params.recommendation_aggressiveness == 0.7


class TestUpdateParams:
    """update_params()测试"""

    def test_manual_update(self, tuner: PromptTuner, mock_store: MagicMock) -> None:
        """手动更新参数"""
        result = tuner.update_params(tone=0.7, aggressive=0.3)
        assert result.tone_intensity == 0.7
        assert result.recommendation_aggressiveness == 0.3
        mock_store.save_prompt_tuning_params.assert_called_once()

    def test_update_only_specified_params(
        self, tuner: PromptTuner, mock_store: MagicMock
    ) -> None:
        """仅更新指定参数，其余保持不变"""
        result = tuner.update_params(tone=0.8)
        assert result.tone_intensity == 0.8
        assert result.detail_level_score == 0.5
        assert result.recommendation_aggressiveness == 0.5
        assert result.data_driven_weight == 0.5


class TestAutoAdjustOnFeedback:
    """auto_adjust_on_feedback()测试"""

    def test_low_score_reduces_tone(
        self, tuner: PromptTuner, mock_store: MagicMock
    ) -> None:
        """低评分降低语气强度"""
        result = tuner.auto_adjust_on_feedback(avg_score=2.0, acceptance_rate=0.5)
        assert result.tone_intensity < 0.5

    def test_high_score_slightly_increases_tone(
        self, tuner: PromptTuner, mock_store: MagicMock
    ) -> None:
        """高评分微幅提高语气强度"""
        result = tuner.auto_adjust_on_feedback(avg_score=4.5, acceptance_rate=0.5)
        assert result.tone_intensity > 0.5

    def test_low_acceptance_reduces_aggressiveness(
        self, tuner: PromptTuner, mock_store: MagicMock
    ) -> None:
        """低接受率降低推荐激进程度"""
        result = tuner.auto_adjust_on_feedback(avg_score=3.0, acceptance_rate=0.2)
        assert result.recommendation_aggressiveness < 0.5

    def test_high_acceptance_slightly_increases_aggressiveness(
        self, tuner: PromptTuner, mock_store: MagicMock
    ) -> None:
        """高接受率微幅提高推荐激进程度"""
        result = tuner.auto_adjust_on_feedback(avg_score=3.0, acceptance_rate=0.8)
        assert result.recommendation_aggressiveness > 0.5

    def test_max_adjustment_bounded(
        self, tuner: PromptTuner, mock_store: MagicMock
    ) -> None:
        """单次调整幅度不超过tuning_max_adjustment"""
        result = tuner.auto_adjust_on_feedback(avg_score=1.0, acceptance_rate=0.0)
        # 默认参数0.5，最大调整0.1，所以结果应>=0.4
        assert result.tone_intensity >= 0.4
        assert result.recommendation_aggressiveness >= 0.4


class TestAutoAdjustOnRejection:
    """auto_adjust_on_rejection()测试"""

    def test_reduces_aggressiveness(
        self, tuner: PromptTuner, mock_store: MagicMock
    ) -> None:
        """连续拒绝时降低激进程度"""
        result = tuner.auto_adjust_on_rejection()
        assert result.recommendation_aggressiveness < 0.5

    def test_reduces_data_driven(
        self, tuner: PromptTuner, mock_store: MagicMock
    ) -> None:
        """连续拒绝时降低数据驱动权重"""
        result = tuner.auto_adjust_on_rejection()
        assert result.data_driven_weight < 0.5

    def test_saves_params(self, tuner: PromptTuner, mock_store: MagicMock) -> None:
        """调整后持久化参数"""
        tuner.auto_adjust_on_rejection()
        mock_store.save_prompt_tuning_params.assert_called_once()


class TestResetToDefault:
    """reset_to_default()测试"""

    def test_resets_all_params(self, tuner: PromptTuner, mock_store: MagicMock) -> None:
        """重置所有参数为0.5"""
        # 先调整参数
        tuner.update_params(tone=0.8, aggressive=0.2)
        # 重置
        result = tuner.reset_to_default()
        assert result.tone_intensity == 0.5
        assert result.recommendation_aggressiveness == 0.5
        assert result.detail_level_score == 0.5
        assert result.data_driven_weight == 0.5
        assert result.update_count == 0


class TestParameterFloorProtection:
    """参数下限保护测试（H-03整改）"""

    def test_aggressive_floor_on_rejection(
        self, tuner: PromptTuner, mock_store: MagicMock
    ) -> None:
        """连续拒绝后aggressive不低于0.1"""
        for _ in range(10):
            tuner.auto_adjust_on_rejection()

        params = tuner.get_params()
        assert params.recommendation_aggressiveness >= 0.1

    def test_data_driven_floor_on_rejection(
        self, tuner: PromptTuner, mock_store: MagicMock
    ) -> None:
        """连续拒绝后data_driven不低于0.2"""
        for _ in range(10):
            tuner.auto_adjust_on_rejection()

        params = tuner.get_params()
        assert params.data_driven_weight >= 0.2

    def test_warning_on_approaching_floor(
        self,
        tuner: PromptTuner,
        mock_store: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """接近下限时输出warning日志"""
        import logging

        tuner.update_params(aggressive=0.12)
        tuner.auto_adjust_on_rejection()

        assert any(
            "接近下限" in r.message or "aggressive" in r.message.lower()
            for r in caplog.records
            if r.levelno >= logging.WARNING
        )

    def test_bounce_back_mechanism(
        self, tuner: PromptTuner, mock_store: MagicMock
    ) -> None:
        """反弹机制：接受推荐后aggressive恢复步长(0.08)大于降低步长(0.05)"""
        tuner.update_params(aggressive=0.3)
        result = tuner.auto_adjust_on_feedback(avg_score=4.0, acceptance_rate=0.8)
        assert result.recommendation_aggressiveness == pytest.approx(
            0.3 + 0.08, abs=0.01
        )

    def test_with_updates_min_bounds(self, mock_store: MagicMock) -> None:
        """with_updates支持min_bounds参数"""
        from src.core.evolution.models import PromptTuningParams

        params = PromptTuningParams(
            recommendation_aggressiveness=0.08,
            data_driven_weight=0.15,
        )
        updated = params.with_updates(
            aggressive=0.05,
            data_driven=0.1,
            min_bounds={
                "recommendation_aggressiveness": 0.1,
                "data_driven_weight": 0.2,
            },
        )
        assert updated.recommendation_aggressiveness == 0.1
        assert updated.data_driven_weight == 0.2

    def test_with_updates_no_min_bounds_backward_compat(
        self, mock_store: MagicMock
    ) -> None:
        """with_updates不传min_bounds时保持向后兼容"""
        from src.core.evolution.models import PromptTuningParams

        params = PromptTuningParams.default()
        updated = params.with_updates(aggressive=0.0)
        assert updated.recommendation_aggressiveness == 0.0
