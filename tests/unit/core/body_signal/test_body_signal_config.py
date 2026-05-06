# 身体信号配置单元测试
# v0.19.0 新增


import pytest

from src.core.config.body_signal_config import BodySignalConfig


class TestBodySignalConfig:
    """身体信号配置测试类"""

    def test_default_values(self):
        """测试默认值"""
        config = BodySignalConfig()

        assert config.fatigue_weight_atl == 40.0
        assert config.fatigue_weight_hr == 20.0
        assert config.fatigue_weight_consecutive == 20.0
        assert config.fatigue_weight_subjective == 20.0
        assert config.hard_training_tss_threshold == 80.0
        assert config.hr_spike_threshold_pct == 10.0
        assert config.overtraining_tsb_threshold == -20.0
        assert config.overtraining_consecutive_days == 3
        assert config.fatigue_rising_consecutive_days == 3
        assert config.rest_hr_improvement_pct == 5.0
        assert config.rest_tsb_improvement == 10.0
        assert config.tsb_cap == 50.0

    def test_weight_sum_validation(self):
        """测试权重和校验"""
        with pytest.raises(ValueError, match="疲劳度权重之和必须等于100%"):
            BodySignalConfig(
                fatigue_weight_atl=50.0,
                fatigue_weight_hr=20.0,
                fatigue_weight_consecutive=20.0,
                fatigue_weight_subjective=20.0,
            )

    def test_threshold_validation(self):
        """测试阈值校验"""
        with pytest.raises(ValueError, match="hard_training_tss_threshold必须大于0"):
            BodySignalConfig(hard_training_tss_threshold=0)

        with pytest.raises(ValueError, match="hr_spike_threshold_pct必须大于0"):
            BodySignalConfig(hr_spike_threshold_pct=-1)

        with pytest.raises(ValueError, match="overtraining_consecutive_days必须大于0"):
            BodySignalConfig(overtraining_consecutive_days=0)

        with pytest.raises(
            ValueError, match="fatigue_rising_consecutive_days必须大于0"
        ):
            BodySignalConfig(fatigue_rising_consecutive_days=-1)

        with pytest.raises(ValueError, match="rest_hr_improvement_pct必须大于0"):
            BodySignalConfig(rest_hr_improvement_pct=0)

        with pytest.raises(ValueError, match="rest_tsb_improvement必须大于0"):
            BodySignalConfig(rest_tsb_improvement=0)

        with pytest.raises(ValueError, match="tsb_cap必须大于0"):
            BodySignalConfig(tsb_cap=0)

    def test_to_dict(self):
        """测试字典转换"""
        config = BodySignalConfig()
        d = config.to_dict()

        assert d["fatigue_weight_atl"] == 40.0
        assert d["fatigue_weight_hr"] == 20.0
        assert d["tsb_cap"] == 50.0

    def test_from_env(self, monkeypatch):
        """测试从环境变量加载"""
        # 设置所有权重环境变量，确保总和为100%
        monkeypatch.setenv("NANOBOT_BODY_SIGNAL_FATIGUE_WEIGHT_ATL", "35.0")
        monkeypatch.setenv("NANOBOT_BODY_SIGNAL_FATIGUE_WEIGHT_HR", "25.0")
        monkeypatch.setenv("NANOBOT_BODY_SIGNAL_FATIGUE_WEIGHT_CONSECUTIVE", "20.0")
        monkeypatch.setenv("NANOBOT_BODY_SIGNAL_FATIGUE_WEIGHT_SUBJECTIVE", "20.0")
        monkeypatch.setenv("NANOBOT_BODY_SIGNAL_HR_SPIKE_THRESHOLD_PCT", "15.0")
        monkeypatch.setenv("NANOBOT_BODY_SIGNAL_OVERTRAINING_CONSECUTIVE_DAYS", "5")

        config = BodySignalConfig.from_env()

        assert config.fatigue_weight_atl == 35.0
        assert config.hr_spike_threshold_pct == 15.0
        assert config.overtraining_consecutive_days == 5
        # 未设置的环境变量保持默认值
        assert config.fatigue_weight_hr == 25.0
