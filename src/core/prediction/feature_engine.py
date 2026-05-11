from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
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
        self._ref_date: date | None = None

    def extract_vdot_features(
        self, days: int = 30, reference_date: date | None = None
    ) -> FeatureMatrix:
        """提取VDOT预测特征（12个）

        Args:
            days: 回溯天数
            reference_date: 参考日期，为None时使用今天（推理场景），
                            指定时回溯至该日期（训练场景）
        """
        ref = reference_date or date.today()
        cache_key = f"vdot_features_{days}_{ref}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        old_ref = self._ref_date
        self._ref_date = reference_date
        try:
            month = ref.month
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
                        self._safe_float("ctl_value", self._get_ctl_value),
                        self._safe_float("tsb_value", self._get_tsb_value),
                        self._safe_float("atl_ctl_ratio", self._get_atl_ctl_ratio),
                        self._safe_float(
                            "load_ramp_rate",
                            self._get_load_ramp_rate,
                        ),
                        self._safe_float(
                            "high_intensity_pct", self._get_high_intensity_pct
                        ),
                        self._safe_float(
                            "avg_intensity_factor", self._get_avg_intensity_factor
                        ),
                        self._safe_float(
                            "fatigue_score",
                            self._get_fatigue_score,
                        ),
                        self._safe_float(
                            "resting_hr_deviation",
                            self._get_resting_hr_deviation,
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
        finally:
            self._ref_date = old_ref

        self._cache[cache_key] = matrix
        return matrix

    def extract_injury_features(
        self, days: int = 30, reference_date: date | None = None
    ) -> FeatureMatrix:
        """提取伤病预测特征（8个）

        Args:
            days: 回溯天数
            reference_date: 参考日期，为None时使用今天（推理场景），
                            指定时回溯至该日期（训练场景）
        """
        ref = reference_date or date.today()
        cache_key = f"injury_features_{days}_{ref}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        old_ref = self._ref_date
        self._ref_date = reference_date
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
        finally:
            self._ref_date = old_ref

        self._cache[cache_key] = matrix
        return matrix

    def extract_race_features(
        self, reference_date: date | None = None
    ) -> FeatureMatrix:
        """提取比赛预测特征（5个）

        Args:
            reference_date: 参考日期，为None时使用今天
        """
        ref = reference_date or date.today()
        cache_key = f"race_features_{ref}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            features = np.array(
                [
                    [
                        self._safe_float(
                            "current_vdot",
                            self._get_current_vdot,
                        ),
                        self._safe_float("riegel_exponent", lambda: 1.06),
                        self._safe_float("correction_factor", lambda: 1.0),
                        self._safe_float(
                            "pre_race_fatigue",
                            self._get_pre_race_fatigue,
                        ),
                        self._safe_float(
                            "pre_race_recovery",
                            self._get_pre_race_recovery,
                        ),
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

    def _get_sessions_window(self, days: int) -> list[Any]:
        """获取最近N天的session数据，支持reference_date回溯

        当_ref_date被设置时，使用get_sessions_by_date_range按日期范围查询；
        否则使用get_recent_sessions获取最近记录。
        """
        if self._repo is None:
            return []
        if self._ref_date is not None:
            start = self._ref_date - timedelta(days=days)
            start_dt = datetime.combine(start, datetime.min.time())
            end_dt = datetime.combine(self._ref_date, datetime.min.time())
            try:
                return self._repo.get_sessions_by_date_range(start_dt, end_dt)
            except Exception as e:
                logger.debug(f"按日期范围获取session失败({days}天): {e}")
                return []
        try:
            return self._repo.get_recent_sessions(limit=days * 3)
        except Exception as e:
            logger.debug(f"获取最近session失败: {e}")
            return []

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
        sessions = self._get_sessions_window(days=7)
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
        sessions = self._get_sessions_window(days=days)
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
        sessions_prev = self._get_sessions_window(days=14)
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
        atl = self._get_atl_value()
        ctl = self._get_ctl_value()
        if ctl <= 0:
            return 0.0
        return atl / ctl

    def _get_high_intensity_pct(self) -> float:
        if self._repo is None:
            return 0.0
        sessions = self._get_sessions_window(days=30)
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
        sessions = self._get_sessions_window(days=30)
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
            self._get_resting_hr_deviation,
        )
        return abs(deviation)

    def _get_tss_series(self, days: int = 42) -> list[float]:
        if self._repo is None:
            return []
        sessions = self._get_sessions_window(days=days)
        if not sessions:
            return []
        tss_map: dict[str, float] = {}
        for s in sessions:
            s_date = getattr(s, "date", None)
            if s_date is None:
                continue
            date_str = str(s_date)[:10]
            tss = getattr(s, "tss", None)
            if isinstance(tss, (int, float)):
                tss_map[date_str] = tss_map.get(date_str, 0.0) + float(tss)
        if not tss_map:
            return []
        sorted_dates = sorted(tss_map.keys())
        return [tss_map[d] for d in sorted_dates]

    def _get_ctl_value(self) -> float:
        if self._load_analyzer is None:
            return 0.0
        tss_series = self._get_tss_series(days=42)
        if not tss_series:
            return 0.0
        return float(self._load_analyzer.calculate_ctl(tss_series))

    def _get_atl_value(self) -> float:
        if self._load_analyzer is None:
            return 0.0
        tss_series = self._get_tss_series(days=42)
        if not tss_series:
            return 0.0
        return float(self._load_analyzer.calculate_atl(tss_series))

    def _get_tsb_value(self) -> float:
        ctl = self._get_ctl_value()
        atl = self._get_atl_value()
        return ctl - atl

    def _get_load_ramp_rate(self) -> float:
        if self._load_analyzer is None:
            return 0.0
        if hasattr(self._load_analyzer, "get_load_ramp_rate"):
            try:
                return float(self._load_analyzer.get_load_ramp_rate())
            except TypeError:
                tss_series = self._get_tss_series(days=42)
                if not tss_series:
                    return 0.0
                return float(self._load_analyzer.get_load_ramp_rate(tss_series))
        return 0.0

    def _get_fatigue_score(self) -> float:
        if self._body_signal_engine is None:
            return 0.0
        if hasattr(self._body_signal_engine, "get_fatigue_score"):
            return float(self._body_signal_engine.get_fatigue_score())
        if hasattr(self._body_signal_engine, "fatigue_assessor"):
            try:
                result = self._body_signal_engine.fatigue_assessor.assess_fatigue()
                if isinstance(result, dict):
                    return float(result.get("fatigue_score", 0.0))
                if isinstance(result, (int, float)):
                    return float(result)
            except Exception as e:
                logger.debug(f"fatigue_score提取失败: {e}")
        return 0.0

    def _get_resting_hr_deviation(self) -> float:
        if self._hrv_analyzer is None:
            return 0.0
        if hasattr(self._hrv_analyzer, "get_resting_hr_deviation"):
            return float(self._hrv_analyzer.get_resting_hr_deviation())
        return 0.0

    def _get_current_vdot(self) -> float:
        if self._vdot_calculator is None:
            return 0.0
        if self._repo is None:
            return 0.0
        sessions = self._get_sessions_window(days=30)
        if not sessions:
            return 0.0
        best_vdot = 0.0
        for s in sessions:
            dist = getattr(s, "distance_km", None) or getattr(s, "distance", None)
            dur = getattr(s, "duration_s", None) or getattr(s, "total_timer_time", None)
            if isinstance(dist, (int, float)) and isinstance(dur, (int, float)):
                dist_m = float(dist) * 1000.0
                time_s = float(dur)
                if dist_m >= 1500 and time_s > 0:
                    vdot = self._vdot_calculator.calculate_vdot(dist_m, time_s)
                    if vdot > best_vdot:
                        best_vdot = vdot
        return best_vdot

    def _get_pre_race_fatigue(self) -> float:
        score = self._get_fatigue_score()
        return score / 100.0

    def _get_pre_race_recovery(self) -> float:
        if self._body_signal_engine is None:
            return 0.0
        if hasattr(self._body_signal_engine, "recovery_monitor"):
            try:
                status = self._body_signal_engine.recovery_monitor.get_recovery_status()
                if isinstance(status, dict):
                    level = status.get("recovery_level", "moderate")
                    return {"good": 0.8, "moderate": 0.5, "poor": 0.2}.get(level, 0.5)
                if isinstance(status, str):
                    return {"good": 0.8, "moderate": 0.5, "poor": 0.2}.get(status, 0.5)
            except Exception as e:
                logger.debug(f"pre_race_recovery提取失败: {e}")
        return 0.0
