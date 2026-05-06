from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


@dataclass
class BodySignalConfig:
    """身体信号配置

    管理疲劳度评估、HRV分析、恢复监控等模块的参数配置。
    支持从环境变量加载，权重之和必须等于100%。

    Attributes:
        fatigue_weight_atl: ATL权重（%）
        fatigue_weight_hr: 心率偏差权重（%）
        fatigue_weight_consecutive: 连续训练权重（%）
        fatigue_weight_subjective: 主观疲劳度(RPE)权重（%）
        hard_training_tss_threshold: 高强度训练TSS阈值
        hr_spike_threshold_pct: 心率异常升高阈值（%）
        overtraining_tsb_threshold: 过度训练TSB阈值
        overtraining_consecutive_days: 过度训练连续天数阈值
        fatigue_rising_consecutive_days: 疲劳上升连续天数阈值
        rest_hr_improvement_pct: 休息后心率改善百分比阈值
        rest_tsb_improvement: 休息后TSB改善阈值
        tsb_cap: TSB截断上限
    """

    fatigue_weight_atl: float = 40.0
    fatigue_weight_hr: float = 20.0
    fatigue_weight_consecutive: float = 20.0
    fatigue_weight_subjective: float = 20.0
    hard_training_tss_threshold: float = 80.0
    hr_spike_threshold_pct: float = 10.0
    overtraining_tsb_threshold: float = -20.0
    overtraining_consecutive_days: int = 3
    fatigue_rising_consecutive_days: int = 3
    rest_hr_improvement_pct: float = 5.0
    rest_tsb_improvement: float = 10.0
    tsb_cap: float = 50.0

    def __post_init__(self) -> None:
        weight_sum = (
            self.fatigue_weight_atl
            + self.fatigue_weight_hr
            + self.fatigue_weight_consecutive
            + self.fatigue_weight_subjective
        )
        if abs(weight_sum - 100.0) > 0.01:
            raise ValueError(f"疲劳度权重之和必须等于100%，当前为{weight_sum}%")

        if self.hard_training_tss_threshold <= 0:
            raise ValueError("hard_training_tss_threshold必须大于0")
        if self.hr_spike_threshold_pct <= 0:
            raise ValueError("hr_spike_threshold_pct必须大于0")
        if self.overtraining_consecutive_days <= 0:
            raise ValueError("overtraining_consecutive_days必须大于0")
        if self.fatigue_rising_consecutive_days <= 0:
            raise ValueError("fatigue_rising_consecutive_days必须大于0")
        if self.rest_hr_improvement_pct <= 0:
            raise ValueError("rest_hr_improvement_pct必须大于0")
        if self.rest_tsb_improvement <= 0:
            raise ValueError("rest_tsb_improvement必须大于0")
        if self.tsb_cap <= 0:
            raise ValueError("tsb_cap必须大于0")

    def to_dict(self) -> dict[str, Any]:
        return {
            "fatigue_weight_atl": self.fatigue_weight_atl,
            "fatigue_weight_hr": self.fatigue_weight_hr,
            "fatigue_weight_consecutive": self.fatigue_weight_consecutive,
            "fatigue_weight_subjective": self.fatigue_weight_subjective,
            "hard_training_tss_threshold": self.hard_training_tss_threshold,
            "hr_spike_threshold_pct": self.hr_spike_threshold_pct,
            "overtraining_tsb_threshold": self.overtraining_tsb_threshold,
            "overtraining_consecutive_days": self.overtraining_consecutive_days,
            "fatigue_rising_consecutive_days": self.fatigue_rising_consecutive_days,
            "rest_hr_improvement_pct": self.rest_hr_improvement_pct,
            "rest_tsb_improvement": self.rest_tsb_improvement,
            "tsb_cap": self.tsb_cap,
        }

    @classmethod
    def from_env(cls) -> BodySignalConfig:
        """从环境变量加载配置

        环境变量前缀为 NANOBOT_BODY_SIGNAL_，例如：
        - NANOBOT_BODY_SIGNAL_FATIGUE_WEIGHT_ATL
        - NANOBOT_BODY_SIGNAL_FATIGUE_WEIGHT_HR
        """

        def _get_env_float(key: str, default: float) -> float:
            val = os.environ.get(key)
            if val is not None:
                try:
                    return float(val)
                except ValueError:
                    return default
            return default

        def _get_env_int(key: str, default: int) -> int:
            val = os.environ.get(key)
            if val is not None:
                try:
                    return int(val)
                except ValueError:
                    return default
            return default

        return cls(
            fatigue_weight_atl=_get_env_float(
                "NANOBOT_BODY_SIGNAL_FATIGUE_WEIGHT_ATL", 40.0
            ),
            fatigue_weight_hr=_get_env_float(
                "NANOBOT_BODY_SIGNAL_FATIGUE_WEIGHT_HR", 20.0
            ),
            fatigue_weight_consecutive=_get_env_float(
                "NANOBOT_BODY_SIGNAL_FATIGUE_WEIGHT_CONSECUTIVE", 20.0
            ),
            fatigue_weight_subjective=_get_env_float(
                "NANOBOT_BODY_SIGNAL_FATIGUE_WEIGHT_SUBJECTIVE", 20.0
            ),
            hard_training_tss_threshold=_get_env_float(
                "NANOBOT_BODY_SIGNAL_HARD_TRAINING_TSS_THRESHOLD", 80.0
            ),
            hr_spike_threshold_pct=_get_env_float(
                "NANOBOT_BODY_SIGNAL_HR_SPIKE_THRESHOLD_PCT", 10.0
            ),
            overtraining_tsb_threshold=_get_env_float(
                "NANOBOT_BODY_SIGNAL_OVERTRAINING_TSB_THRESHOLD", -20.0
            ),
            overtraining_consecutive_days=_get_env_int(
                "NANOBOT_BODY_SIGNAL_OVERTRAINING_CONSECUTIVE_DAYS", 3
            ),
            fatigue_rising_consecutive_days=_get_env_int(
                "NANOBOT_BODY_SIGNAL_FATIGUE_RISING_CONSECUTIVE_DAYS", 3
            ),
            rest_hr_improvement_pct=_get_env_float(
                "NANOBOT_BODY_SIGNAL_REST_HR_IMPROVEMENT_PCT", 5.0
            ),
            rest_tsb_improvement=_get_env_float(
                "NANOBOT_BODY_SIGNAL_REST_TSB_IMPROVEMENT", 10.0
            ),
            tsb_cap=_get_env_float("NANOBOT_BODY_SIGNAL_TSB_CAP", 50.0),
        )
