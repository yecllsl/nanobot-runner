from __future__ import annotations

import logging
from typing import Any

from src.core.base.exceptions import NanobotRunnerError
from src.core.base.formatters import format_pace_with_unit
from src.core.prediction.models import (
    PaceSplit,
    PaceStrategy,
    PersonalizationInfo,
    RacePredictionResult,
)

logger = logging.getLogger(__name__)

RACE_COUNT_SUFFICIENT = 3
RIEGEL_STANDARD_EXPONENT = 1.06
PACE_SECONDS_PER_KM = {
    "5k": 270,
    "10k": 285,
    "half": 300,
    "full": 330,
}


class RacePredictor:
    """个人化比赛成绩预测

    两层降级：个人化(≥3次比赛) → 标准Riegel公式
    """

    def __init__(
        self,
        feature_engine: Any = None,
        data_assessor: Any = None,
        model_manager: Any = None,
        race_engine: Any = None,
        body_signal_engine: Any = None,
        current_vdot: float = 45.0,
        race_records: list[dict[str, Any]] | None = None,
    ) -> None:
        self._feature_engine = feature_engine
        self._data_assessor = data_assessor
        self._model_manager = model_manager
        self._race_engine = race_engine
        self._body_signal_engine = body_signal_engine
        self._current_vdot = current_vdot
        self._race_records = race_records or []
        self._riegel_exponent = RIEGEL_STANDARD_EXPONENT
        self._correction_factor = 1.0
        self._runner_type = "balanced"

    def predict(
        self, distance_km: float, race_date: str | None = None
    ) -> RacePredictionResult:
        """比赛成绩预测"""
        sufficiency = (
            self._data_assessor.assess_sufficiency("race")
            if self._data_assessor
            else None
        )

        if sufficiency and sufficiency.is_sufficient:
            return self._predict_personalized(distance_km, race_date)
        else:
            return self._predict_standard(distance_km, race_date)

    def fit_riegel_curve(self) -> float:
        """拟合个人化Riegel指数"""
        if len(self._race_records) < 2:
            return RIEGEL_STANDARD_EXPONENT

        try:
            from scipy.optimize import curve_fit

            distances = [r["distance_km"] for r in self._race_records]
            times = [r["time_seconds"] for r in self._race_records]

            def riegel(d: float, t_ref: float, alpha: float) -> float:
                return t_ref * (d / distances[0]) ** alpha

            popt, _ = curve_fit(
                riegel, distances, times, p0=[times[0], RIEGEL_STANDARD_EXPONENT]
            )
            self._riegel_exponent = max(0.95, min(1.15, float(popt[1])))
        except NanobotRunnerError as e:
            logger.warning(f"Riegel拟合失败，使用标准值: {e}")
            self._riegel_exponent = RIEGEL_STANDARD_EXPONENT

        return self._riegel_exponent

    def learn_personalization(self) -> dict[str, Any]:
        """学习个人化参数"""
        if len(self._race_records) >= 3:
            self._runner_type = self._classify_runner_type()
            self._correction_factor = self._estimate_correction_factor()
        return {
            "runner_type": self._runner_type,
            "correction_factor": self._correction_factor,
            "riegel_exponent": self._riegel_exponent,
        }

    def _predict_personalized(
        self, distance_km: float, race_date: str | None
    ) -> RacePredictionResult:
        """个人化预测"""
        ref_time = self._estimate_ref_time()
        predicted_seconds = (
            ref_time
            * (distance_km / 5.0) ** self._riegel_exponent
            * self._correction_factor
        )

        fatigue_adj = 0.0
        if self._feature_engine:
            try:
                features = self._feature_engine.extract_race_features()
                fatigue_val = features.features.flatten()
                if len(fatigue_val) >= 4:
                    fatigue_adj = float(fatigue_val[3]) * 0.03
            except NanobotRunnerError as e:
                logger.debug(f"赛前疲劳修正提取失败: {e}")

        predicted_seconds *= 1.0 + fatigue_adj

        pace_strategy = self._generate_pace_strategy(distance_km, predicted_seconds)

        return RacePredictionResult(
            distance_km=distance_km,
            predicted_time=self._format_time(predicted_seconds),
            predicted_time_seconds=round(predicted_seconds, 1),
            confidence=0.8,
            best_case=self._format_time(predicted_seconds * 0.95),
            worst_case=self._format_time(predicted_seconds * 1.05),
            predicted_vdot=self._current_vdot,
            pace_strategy=pace_strategy,
            prediction_type="personalized",
            personalization_info=PersonalizationInfo(
                runner_type=self._runner_type,
                riegel_exponent=self._riegel_exponent,
                correction_factor=self._correction_factor,
                race_samples_count=len(self._race_records),
                pre_race_adjustment=fatigue_adj,
            ),
        )

    def _predict_standard(
        self, distance_km: float, race_date: str | None
    ) -> RacePredictionResult:
        """标准Riegel预测"""
        ref_time = self._estimate_ref_time()
        predicted_seconds = ref_time * (distance_km / 5.0) ** RIEGEL_STANDARD_EXPONENT

        return RacePredictionResult(
            distance_km=distance_km,
            predicted_time=self._format_time(predicted_seconds),
            predicted_time_seconds=round(predicted_seconds, 1),
            confidence=0.6,
            best_case=self._format_time(predicted_seconds * 0.93),
            worst_case=self._format_time(predicted_seconds * 1.07),
            predicted_vdot=self._current_vdot,
            pace_strategy=None,
            prediction_type="standard",
            personalization_info=None,
        )

    def _estimate_ref_time(self) -> float:
        """估算5km参考时间"""
        vdot = self._current_vdot
        ref_time = 1800.0 / (vdot / 45.0)
        return ref_time

    def _classify_runner_type(self) -> str:
        """分类跑者类型 — 基于比赛记录的短距离/长距离表现比"""
        if len(self._race_records) < 3:
            return "balanced"
        try:
            short_times: list[float] = []
            long_times: list[float] = []
            for r in self._race_records:
                d = r.get("distance_km", 0)
                t = r.get("time_seconds", 0)
                if d <= 10:
                    short_times.append(t / d if d > 0 else 0)
                elif d >= 21:
                    long_times.append(t / d if d > 0 else 0)
            if short_times and long_times:
                avg_short = sum(short_times) / len(short_times)
                avg_long = sum(long_times) / len(long_times)
                ratio = avg_long / avg_short if avg_short > 0 else 1.0
                if ratio < 1.05:
                    return "endurance"
                elif ratio > 1.12:
                    return "speed"
                else:
                    return "balanced"
        except NanobotRunnerError as e:
            logger.debug(f"选手类型判断失败: {e}")
        return "balanced"

    def _estimate_correction_factor(self) -> float:
        """估算修正因子 — 基于历史比赛与Riegel预测的偏差"""
        if len(self._race_records) < 3:
            return 1.0
        try:
            ref_time = self._estimate_ref_time()
            ratios: list[float] = []
            for r in self._race_records:
                d = r.get("distance_km", 0)
                actual = r.get("time_seconds", 0)
                if d > 0 and actual > 0:
                    predicted = ref_time * (d / 5.0) ** self._riegel_exponent
                    ratios.append(actual / predicted)
            if ratios:
                return round(sum(ratios) / len(ratios), 3)
        except NanobotRunnerError as e:
            logger.debug(f"修正因子估算失败: {e}")
        return 1.0

    def _generate_pace_strategy(
        self, distance_km: float, total_seconds: float
    ) -> PaceStrategy:
        """生成配速策略"""
        avg_pace = total_seconds / distance_km
        splits: list[PaceSplit] = []

        if distance_km >= 42.0:
            segments = [
                ("0-5km", avg_pace * 0.98),
                ("5-10km", avg_pace * 0.99),
                ("10-15km", avg_pace),
                ("15-20km", avg_pace),
                ("20-25km", avg_pace * 1.01),
                ("25-30km", avg_pace * 1.01),
                ("30-35km", avg_pace * 1.02),
                ("35-40km", avg_pace * 1.03),
                ("40-42.195km", avg_pace * 1.04),
            ]
            for seg, pace in segments:
                splits.append(
                    PaceSplit(
                        segment=seg,
                        pace=format_pace_with_unit(pace),
                        pace_seconds=round(pace, 1),
                    )
                )
        else:
            splits.append(
                PaceSplit(
                    segment="全程",
                    pace=format_pace_with_unit(avg_pace),
                    pace_seconds=round(avg_pace, 1),
                )
            )

        return PaceStrategy(strategy_type="even", splits=splits)

    @staticmethod
    def _format_time(seconds: float) -> str:
        """格式化时间为 HH:MM:SS"""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h}:{m:02d}:{s:02d}"
