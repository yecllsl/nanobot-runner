from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import date
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

VDOT_FEATURE_NAMES = [
    "weekly_volume_km",
    "volume_change_rate",
    "month_sin",
    "month_cos",
    "ctl_value",
    "tsb_value",
    "atl_ctl_ratio",
    "load_ramp_rate",
    "high_intensity_pct",
    "avg_intensity_factor",
    "fatigue_score",
    "resting_hr_deviation",
]

INJURY_FEATURE_NAMES = [
    "atl_ctl_ratio",
    "weekly_load_change_pct",
    "tsb_consecutive_low_days",
    "tsb_trend_slope",
    "resting_hr_deviation_pct",
    "resting_hr_7d_trend",
    "hrv_rmssd_trend",
    "hrv_sdnn_deviation",
]

RACE_FEATURE_NAMES = [
    "current_vdot",
    "riegel_exponent",
    "correction_factor",
    "pre_race_fatigue",
    "pre_race_recovery",
]


@dataclass
class FeatureMatrix:
    """特征矩阵"""

    features: np.ndarray
    feature_names: list[str]
    feature_type: str
    dates: list[str] = field(default_factory=list)
    data_quality: str = "sufficient"

    def to_dict(self) -> dict[str, Any]:
        return {
            "features": self.features.tolist(),
            "feature_names": self.feature_names,
            "feature_type": self.feature_type,
            "dates": self.dates,
            "data_quality": self.data_quality,
        }


class FeatureEngine:
    """特征工程引擎

    复用已有计算器提取时序/负荷/身体信号特征，
    支持同日缓存，异常时返回默认值0.0的FeatureMatrix。
    """

    def __init__(
        self,
        session_repo: Any = None,
        training_load_analyzer: Any = None,
        hrv_analyzer: Any = None,
        body_signal_engine: Any = None,
        vdot_calculator: Any = None,
    ) -> None:
        self._repo = session_repo
        self._load_analyzer = training_load_analyzer
        self._hrv_analyzer = hrv_analyzer
        self._body_signal_engine = body_signal_engine
        self._vdot_calculator = vdot_calculator
        self._cache: dict[str, FeatureMatrix] = {}

    def extract_vdot_features(self, days: int = 30) -> FeatureMatrix:
        """提取VDOT预测特征（12个）"""
        cache_key = f"vdot_features_{days}_{date.today()}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            now = date.today()
            month = now.month
            features = np.array(
                [
                    [
                        self._safe_float(
                            "weekly_volume_km", self._get_weekly_volume_km
                        ),
                        self._safe_float(
                            "volume_change_rate", self._get_volume_change_rate
                        ),
                        math.sin(2 * math.pi * month / 12),
                        math.cos(2 * math.pi * month / 12),
                        self._safe_float(
                            "ctl_value", lambda: self._load_analyzer.calculate_ctl()
                        ),
                        self._safe_float(
                            "tsb_value", lambda: self._load_analyzer.calculate_tsb()
                        ),
                        self._safe_float("atl_ctl_ratio", self._get_atl_ctl_ratio),
                        self._safe_float(
                            "load_ramp_rate",
                            lambda: self._load_analyzer.get_load_ramp_rate(),
                        ),
                        self._safe_float(
                            "high_intensity_pct", self._get_high_intensity_pct
                        ),
                        self._safe_float(
                            "avg_intensity_factor", self._get_avg_intensity_factor
                        ),
                        self._safe_float(
                            "fatigue_score",
                            lambda: self._body_signal_engine.get_fatigue_score(),
                        ),
                        self._safe_float(
                            "resting_hr_deviation",
                            lambda: self._hrv_analyzer.get_resting_hr_deviation(),
                        ),
                    ]
                ]
            )

            matrix = FeatureMatrix(
                features=features,
                feature_names=list(VDOT_FEATURE_NAMES),
                feature_type="vdot",
            )
        except Exception as e:
            logger.warning(f"VDOT特征提取失败: {e}")
            matrix = self._default_matrix("vdot", VDOT_FEATURE_NAMES)

        self._cache[cache_key] = matrix
        return matrix

    def extract_injury_features(self, days: int = 30) -> FeatureMatrix:
        """提取伤病预测特征（8个）"""
        cache_key = f"injury_features_{days}_{date.today()}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            features = np.array(
                [
                    [
                        self._safe_float("atl_ctl_ratio", self._get_atl_ctl_ratio),
                        self._safe_float(
                            "weekly_load_change_pct", self._get_weekly_load_change_pct
                        ),
                        self._safe_float(
                            "tsb_consecutive_low_days",
                            self._get_tsb_consecutive_low_days,
                        ),
                        self._safe_float("tsb_trend_slope", self._get_tsb_trend_slope),
                        self._safe_float(
                            "resting_hr_deviation_pct",
                            self._get_resting_hr_deviation_pct,
                        ),
                        self._safe_float(
                            "resting_hr_7d_trend",
                            lambda: (
                                self._hrv_analyzer.get_resting_hr_7d_trend()
                                if hasattr(
                                    self._hrv_analyzer, "get_resting_hr_7d_trend"
                                )
                                else 0.0
                            ),
                        ),
                        self._safe_float(
                            "hrv_rmssd_trend",
                            lambda: self._hrv_analyzer.get_rmssd_trend(),
                        ),
                        self._safe_float(
                            "hrv_sdnn_deviation",
                            lambda: self._hrv_analyzer.get_sdnn_deviation(),
                        ),
                    ]
                ]
            )

            matrix = FeatureMatrix(
                features=features,
                feature_names=list(INJURY_FEATURE_NAMES),
                feature_type="injury",
            )
        except Exception as e:
            logger.warning(f"Injury特征提取失败: {e}")
            matrix = self._default_matrix("injury", INJURY_FEATURE_NAMES)

        self._cache[cache_key] = matrix
        return matrix

    def extract_race_features(self) -> FeatureMatrix:
        """提取比赛预测特征（5个）"""
        cache_key = f"race_features_{date.today()}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            features = np.array(
                [
                    [
                        self._safe_float(
                            "current_vdot",
                            lambda: self._vdot_calculator.calculate_vdot(),
                        ),
                        self._safe_float("riegel_exponent", lambda: 1.06),
                        self._safe_float("correction_factor", lambda: 1.0),
                        self._safe_float(
                            "pre_race_fatigue",
                            lambda: (
                                self._body_signal_engine.get_fatigue_score() / 100.0
                            ),
                        ),
                        self._safe_float("pre_race_recovery", lambda: 0.0),
                    ]
                ]
            )

            matrix = FeatureMatrix(
                features=features,
                feature_names=list(RACE_FEATURE_NAMES),
                feature_type="race",
            )
        except Exception as e:
            logger.warning(f"Race特征提取失败: {e}")
            matrix = self._default_matrix("race", RACE_FEATURE_NAMES)

        self._cache[cache_key] = matrix
        return matrix

    def get_feature_names(self, feature_type: str) -> list[str]:
        """获取指定类型的特征名称列表"""
        if feature_type == "vdot":
            return list(VDOT_FEATURE_NAMES)
        elif feature_type == "injury":
            return list(INJURY_FEATURE_NAMES)
        elif feature_type == "race":
            return list(RACE_FEATURE_NAMES)
        else:
            raise ValueError(f"未知的特征类型: {feature_type}")

    def invalidate_cache(self) -> None:
        """清空缓存"""
        self._cache.clear()

    def _default_matrix(
        self, feature_type: str, feature_names: list[str]
    ) -> FeatureMatrix:
        """返回默认值0.0的FeatureMatrix"""
        return FeatureMatrix(
            features=np.zeros((1, len(feature_names))),
            feature_names=list(feature_names),
            feature_type=feature_type,
            data_quality="insufficient",
        )

    def _safe_float(self, name: str, func: Any) -> float:
        """防御性调用，异常时返回0.0"""
        try:
            result = func()
            if isinstance(result, (int, float)):
                return float(result)
            return 0.0
        except Exception as e:
            logger.debug(f"特征{name}提取失败: {e}")
            return 0.0

    def _get_weekly_volume_km(self) -> float:
        if self._repo is None:
            return 0.0
        sessions = self._repo.get_recent_sessions(days=7)
        if not sessions:
            return 0.0
        total = 0.0
        for s in sessions:
            dist = getattr(s, "distance_km", None) or getattr(s, "distance", None)
            if isinstance(dist, (int, float)):
                total += float(dist)
        return total

    def _compute_weekly_tss(self, days: int = 7) -> float:
        """计算最近N天的TSS总和"""
        if self._repo is None:
            return 0.0
        sessions = self._repo.get_recent_sessions(days=days)
        if not sessions:
            return 0.0
        total = 0.0
        for s in sessions:
            tss = getattr(s, "tss", None)
            if isinstance(tss, (int, float)):
                total += float(tss)
        return total

    def _get_volume_change_rate(self) -> float:
        if self._repo is None:
            return 0.0
        current = self._get_weekly_volume_km()
        sessions_prev = self._repo.get_recent_sessions(days=14)
        if not sessions_prev:
            return 0.0
        prev_total = 0.0
        for s in sessions_prev:
            dist = getattr(s, "distance_km", None) or getattr(s, "distance", None)
            if isinstance(dist, (int, float)):
                prev_total += float(dist)
        prev_week = prev_total - current
        if prev_week <= 0:
            return 0.0
        return (current - prev_week) / prev_week

    def _get_atl_ctl_ratio(self) -> float:
        if self._load_analyzer is None:
            return 0.0
        atl = self._safe_float("atl", lambda: self._load_analyzer.calculate_atl())
        ctl = self._safe_float("ctl", lambda: self._load_analyzer.calculate_ctl())
        if ctl <= 0:
            return 0.0
        return atl / ctl

    def _get_high_intensity_pct(self) -> float:
        if self._repo is None:
            return 0.0
        sessions = self._repo.get_recent_sessions(days=30)
        if not sessions:
            return 0.0
        high_count = 0
        total = 0
        for s in sessions:
            tss = getattr(s, "tss", None)
            if isinstance(tss, (int, float)):
                total += 1
                if float(tss) >= 80:
                    high_count += 1
        if total == 0:
            return 0.0
        return high_count / total

    def _get_avg_intensity_factor(self) -> float:
        if self._repo is None:
            return 0.0
        sessions = self._repo.get_recent_sessions(days=30)
        if not sessions:
            return 0.85
        total_if = 0.0
        count = 0
        for s in sessions:
            if_val = getattr(s, "intensity_factor", None)
            if isinstance(if_val, (int, float)):
                total_if += float(if_val)
                count += 1
        if count == 0:
            return 0.85
        return total_if / count

    def _get_weekly_load_change_pct(self) -> float:
        if self._repo is None:
            return 0.0
        current_week = self._compute_weekly_tss(days=7)
        previous_week = self._compute_weekly_tss(days=14) - current_week
        if previous_week <= 0:
            return 0.0
        return (current_week - previous_week) / previous_week * 100.0

    def _get_tsb_consecutive_low_days(self) -> float:
        if self._load_analyzer is None:
            return 0.0
        try:
            trend = (
                self._load_analyzer.get_training_load_trend(days=30)
                if hasattr(self._load_analyzer, "get_training_load_trend")
                else None
            )
            if trend is None:
                return 0.0
            trend_data = trend.get("trend_data", [])
            consecutive = 0
            for point in reversed(trend_data):
                tsb = point.get("tsb", 0.0)
                if tsb < -10:
                    consecutive += 1
                else:
                    break
            return float(consecutive)
        except Exception as e:
            logger.debug(f"TSB连续低天数计算失败: {e}")
            return 0.0

    def _get_tsb_trend_slope(self) -> float:
        if self._load_analyzer is None:
            return 0.0
        try:
            trend = (
                self._load_analyzer.get_training_load_trend(days=14)
                if hasattr(self._load_analyzer, "get_training_load_trend")
                else None
            )
            if trend is None:
                return 0.0
            trend_data = trend.get("trend_data", [])
            tsb_values = [point.get("tsb", 0.0) for point in trend_data]
            if len(tsb_values) < 3:
                return 0.0
            n = len(tsb_values)
            x = np.arange(n, dtype=float)
            y = np.array(tsb_values)
            x_mean = np.mean(x)
            y_mean = np.mean(y)
            numerator = np.sum((x - x_mean) * (y - y_mean))
            denominator = np.sum((x - x_mean) ** 2)
            if denominator == 0:
                return 0.0
            return float(numerator / denominator)
        except Exception as e:
            logger.debug(f"TSB趋势斜率计算失败: {e}")
            return 0.0

    def _get_resting_hr_deviation_pct(self) -> float:
        if self._hrv_analyzer is None:
            return 0.0
        deviation = self._safe_float(
            "resting_hr_deviation",
            lambda: self._hrv_analyzer.get_resting_hr_deviation(),
        )
        return abs(deviation)
