from __future__ import annotations

from datetime import date, datetime
from unittest.mock import MagicMock

import numpy as np
import pytest

from src.core.prediction.feature_engine import (
    INJURY_FEATURE_NAMES,
    RACE_FEATURE_NAMES,
    VDOT_FEATURE_NAMES,
    FeatureEngine,
    FeatureMatrix,
)


def _make_session_repo(session_count: int = 10):
    repo = MagicMock()
    sessions = []
    for i in range(session_count):
        s = MagicMock()
        s.distance_km = 5.0 + i * 0.5
        s.distance = 5.0 + i * 0.5
        s.tss = 50.0 + i * 5
        s.intensity_factor = 0.8 + i * 0.01
        s.avg_heart_rate = 150 + i
        s.date = f"2026-05-{1 + i:02d}"
        s.timestamp = datetime(2026, 5, 1 + i, 8, 0, 0)
        sessions.append(s)
    repo.get_recent_sessions.return_value = sessions
    repo.get_sessions_by_date_range.return_value = sessions
    return repo


def _make_load_analyzer():
    analyzer = MagicMock()
    analyzer.calculate_ctl.return_value = 65.0
    analyzer.calculate_atl.return_value = 55.0
    analyzer.get_load_ramp_rate.return_value = 2.5
    analyzer.get_training_load_trend.return_value = {
        "trend_data": [
            {"date": "2026-05-01", "tsb": -5.0},
            {"date": "2026-05-02", "tsb": -12.0},
            {"date": "2026-05-03", "tsb": -15.0},
            {"date": "2026-05-04", "tsb": 5.0},
            {"date": "2026-05-05", "tsb": 10.0},
        ]
    }
    return analyzer


def _make_hrv_analyzer():
    analyzer = MagicMock()
    analyzer.get_resting_hr_deviation.return_value = 3.5
    analyzer.get_resting_hr_7d_trend.return_value = 0.5
    analyzer.get_rmssd_trend.return_value = -0.2
    analyzer.get_sdnn_deviation.return_value = 1.5
    return analyzer


def _make_body_signal_engine():
    engine = MagicMock()
    engine.get_fatigue_score.return_value = 45.0
    return engine


def _make_vdot_calculator():
    calc = MagicMock()
    calc.calculate_vdot.return_value = 45.0
    return calc


class TestFeatureMatrixToDict:
    def test_to_dict(self):
        matrix = FeatureMatrix(
            features=np.array([[1.0, 2.0]]),
            feature_names=["a", "b"],
            feature_type="vdot",
            dates=["2026-05-01"],
            data_quality="sufficient",
        )
        d = matrix.to_dict()
        assert d["feature_type"] == "vdot"
        assert d["feature_names"] == ["a", "b"]
        assert d["data_quality"] == "sufficient"
        assert d["dates"] == ["2026-05-01"]


class TestFeatureEngineGetFeatureNames:
    def test_vdot_feature_names(self):
        fe = FeatureEngine()
        names = fe.get_feature_names("vdot")
        assert names == list(VDOT_FEATURE_NAMES)

    def test_injury_feature_names(self):
        fe = FeatureEngine()
        names = fe.get_feature_names("injury")
        assert names == list(INJURY_FEATURE_NAMES)

    def test_race_feature_names(self):
        fe = FeatureEngine()
        names = fe.get_feature_names("race")
        assert names == list(RACE_FEATURE_NAMES)

    def test_unknown_feature_type(self):
        fe = FeatureEngine()
        with pytest.raises(ValueError, match="未知"):
            fe.get_feature_names("unknown")


class TestFeatureEngineInvalidateCache:
    def test_invalidate_cache(self):
        fe = FeatureEngine(session_repo=_make_session_repo())
        fe._cache["test_key"] = MagicMock()
        fe.invalidate_cache()
        assert len(fe._cache) == 0


class TestFeatureEngineExtractVdotFeatures:
    def test_extract_vdot_features_with_all_deps(self):
        fe = FeatureEngine(
            session_repo=_make_session_repo(10),
            training_load_analyzer=_make_load_analyzer(),
            hrv_analyzer=_make_hrv_analyzer(),
            body_signal_engine=_make_body_signal_engine(),
            vdot_calculator=_make_vdot_calculator(),
        )
        matrix = fe.extract_vdot_features(days=30)
        assert isinstance(matrix, FeatureMatrix)
        assert matrix.feature_type == "vdot"
        assert matrix.features.shape == (1, 12)

    def test_extract_vdot_features_no_deps(self):
        fe = FeatureEngine()
        matrix = fe.extract_vdot_features(days=30)
        assert isinstance(matrix, FeatureMatrix)
        assert matrix.feature_type == "vdot"

    def test_extract_vdot_features_cached(self):
        fe = FeatureEngine(session_repo=_make_session_repo())
        matrix1 = fe.extract_vdot_features(days=30)
        matrix2 = fe.extract_vdot_features(days=30)
        assert matrix1 is matrix2


class TestFeatureEngineExtractInjuryFeatures:
    def test_extract_injury_features_with_all_deps(self):
        fe = FeatureEngine(
            session_repo=_make_session_repo(10),
            training_load_analyzer=_make_load_analyzer(),
            hrv_analyzer=_make_hrv_analyzer(),
        )
        matrix = fe.extract_injury_features(days=30)
        assert isinstance(matrix, FeatureMatrix)
        assert matrix.feature_type == "injury"
        assert matrix.features.shape == (1, 8)

    def test_extract_injury_features_no_deps(self):
        fe = FeatureEngine()
        matrix = fe.extract_injury_features(days=30)
        assert isinstance(matrix, FeatureMatrix)
        assert matrix.feature_type == "injury"


class TestFeatureEngineExtractRaceFeatures:
    def test_extract_race_features_with_deps(self):
        fe = FeatureEngine(
            session_repo=_make_session_repo(),
            vdot_calculator=_make_vdot_calculator(),
        )
        matrix = fe.extract_race_features()
        assert isinstance(matrix, FeatureMatrix)
        assert matrix.feature_type == "race"
        assert matrix.features.shape == (1, 5)

    def test_extract_race_features_no_deps(self):
        fe = FeatureEngine()
        matrix = fe.extract_race_features()
        assert isinstance(matrix, FeatureMatrix)
        assert matrix.feature_type == "race"


class TestFeatureEngineGetWeeklyVolumeKm:
    def test_with_sessions(self):
        fe = FeatureEngine(session_repo=_make_session_repo(5))
        vol = fe._get_weekly_volume_km()
        assert vol > 0

    def test_no_repo(self):
        fe = FeatureEngine()
        vol = fe._get_weekly_volume_km()
        assert vol == 0.0

    def test_empty_sessions(self):
        repo = MagicMock()
        repo.get_recent_sessions.return_value = []
        fe = FeatureEngine(session_repo=repo)
        vol = fe._get_weekly_volume_km()
        assert vol == 0.0


class TestFeatureEngineGetVolumeChangeRate:
    def test_with_sessions(self):
        fe = FeatureEngine(session_repo=_make_session_repo(10))
        rate = fe._get_volume_change_rate()
        assert isinstance(rate, float)

    def test_no_repo(self):
        fe = FeatureEngine()
        rate = fe._get_volume_change_rate()
        assert rate == 0.0


class TestFeatureEngineGetAtlCtlRatio:
    def test_with_analyzer(self):
        fe = FeatureEngine(
            session_repo=_make_session_repo(),
            training_load_analyzer=_make_load_analyzer(),
        )
        ratio = fe._get_atl_ctl_ratio()
        assert ratio > 0

    def test_no_analyzer(self):
        fe = FeatureEngine()
        ratio = fe._get_atl_ctl_ratio()
        assert ratio == 0.0


class TestFeatureEngineGetHighIntensityPct:
    def test_with_sessions(self):
        fe = FeatureEngine(session_repo=_make_session_repo(10))
        pct = fe._get_high_intensity_pct()
        assert 0.0 <= pct <= 1.0

    def test_no_repo(self):
        fe = FeatureEngine()
        pct = fe._get_high_intensity_pct()
        assert pct == 0.0


class TestFeatureEngineGetAvgIntensityFactor:
    def test_with_sessions(self):
        fe = FeatureEngine(session_repo=_make_session_repo(10))
        avg_if = fe._get_avg_intensity_factor()
        assert avg_if > 0

    def test_no_repo(self):
        fe = FeatureEngine()
        avg_if = fe._get_avg_intensity_factor()
        assert avg_if == 0.0


class TestFeatureEngineGetWeeklyLoadChangePct:
    def test_with_sessions(self):
        fe = FeatureEngine(session_repo=_make_session_repo(10))
        pct = fe._get_weekly_load_change_pct()
        assert isinstance(pct, float)

    def test_no_repo(self):
        fe = FeatureEngine()
        pct = fe._get_weekly_load_change_pct()
        assert pct == 0.0


class TestFeatureEngineGetTsbConsecutiveLowDays:
    def test_with_analyzer(self):
        fe = FeatureEngine(
            training_load_analyzer=_make_load_analyzer(),
        )
        days = fe._get_tsb_consecutive_low_days()
        assert isinstance(days, float)

    def test_no_analyzer(self):
        fe = FeatureEngine()
        days = fe._get_tsb_consecutive_low_days()
        assert days == 0.0


class TestFeatureEngineGetTsbTrendSlope:
    def test_with_analyzer(self):
        fe = FeatureEngine(
            training_load_analyzer=_make_load_analyzer(),
        )
        slope = fe._get_tsb_trend_slope()
        assert isinstance(slope, float)

    def test_no_analyzer(self):
        fe = FeatureEngine()
        slope = fe._get_tsb_trend_slope()
        assert slope == 0.0


class TestFeatureEngineGetCtlValue:
    def test_with_analyzer_and_sessions(self):
        fe = FeatureEngine(
            session_repo=_make_session_repo(),
            training_load_analyzer=_make_load_analyzer(),
        )
        ctl = fe._get_ctl_value()
        assert ctl == 65.0

    def test_no_analyzer(self):
        fe = FeatureEngine()
        ctl = fe._get_ctl_value()
        assert ctl == 0.0


class TestFeatureEngineGetAtlValue:
    def test_with_analyzer_and_sessions(self):
        fe = FeatureEngine(
            session_repo=_make_session_repo(),
            training_load_analyzer=_make_load_analyzer(),
        )
        atl = fe._get_atl_value()
        assert atl == 55.0

    def test_no_analyzer(self):
        fe = FeatureEngine()
        atl = fe._get_atl_value()
        assert atl == 0.0


class TestFeatureEngineGetTsbValue:
    def test_with_analyzer_and_sessions(self):
        fe = FeatureEngine(
            session_repo=_make_session_repo(),
            training_load_analyzer=_make_load_analyzer(),
        )
        tsb = fe._get_tsb_value()
        assert tsb == 10.0

    def test_no_deps(self):
        fe = FeatureEngine()
        tsb = fe._get_tsb_value()
        assert tsb == 0.0


class TestFeatureEngineGetFatigueScore:
    def test_with_body_signal_engine(self):
        fe = FeatureEngine(body_signal_engine=_make_body_signal_engine())
        score = fe._get_fatigue_score()
        assert score == 45.0

    def test_no_body_signal_engine(self):
        fe = FeatureEngine()
        score = fe._get_fatigue_score()
        assert score == 0.0

    def test_with_fatigue_assessor(self):
        class FakeBodySignalEngine:
            @property
            def fatigue_assessor(self):
                return self._assessor

        bse = FakeBodySignalEngine()
        assessor = MagicMock()
        assessor.assess_fatigue.return_value = {"fatigue_score": 55.0}
        bse._assessor = assessor
        fe = FeatureEngine(body_signal_engine=bse)
        score = fe._get_fatigue_score()
        assert score == 55.0


class TestFeatureEngineGetRestingHrDeviation:
    def test_with_hrv_analyzer(self):
        fe = FeatureEngine(hrv_analyzer=_make_hrv_analyzer())
        dev = fe._get_resting_hr_deviation()
        assert dev == 3.5

    def test_no_hrv_analyzer(self):
        fe = FeatureEngine()
        dev = fe._get_resting_hr_deviation()
        assert dev == 0.0


class TestFeatureEngineGetLoadRampRate:
    def test_with_analyzer(self):
        fe = FeatureEngine(
            session_repo=_make_session_repo(),
            training_load_analyzer=_make_load_analyzer(),
        )
        rate = fe._get_load_ramp_rate()
        assert rate == 2.5

    def test_no_analyzer(self):
        fe = FeatureEngine()
        rate = fe._get_load_ramp_rate()
        assert rate == 0.0


class TestFeatureEngineSafeFloat:
    def test_safe_float_normal(self):
        fe = FeatureEngine()
        result = fe._safe_float("test", lambda: 42.0)
        assert result == 42.0

    def test_safe_float_exception(self):
        fe = FeatureEngine()
        result = fe._safe_float("test", lambda: 1 / 0)
        assert result == 0.0

    def test_safe_float_non_numeric(self):
        fe = FeatureEngine()
        result = fe._safe_float("test", lambda: "not_a_number")
        assert result == 0.0


class TestFeatureEngineDefaultMatrix:
    def test_default_matrix(self):
        fe = FeatureEngine()
        matrix = fe._default_matrix("vdot", VDOT_FEATURE_NAMES)
        assert matrix.feature_type == "vdot"
        assert matrix.data_quality == "insufficient"
        assert matrix.features.shape == (1, 12)
        assert np.all(matrix.features == 0.0)


class TestFeatureEngineGetSessionsWindow:
    def test_no_repo(self):
        fe = FeatureEngine()
        result = fe._get_sessions_window(days=7)
        assert result == []

    def test_with_ref_date(self):
        repo = _make_session_repo(5)
        fe = FeatureEngine(session_repo=repo)
        fe._ref_date = date(2026, 5, 10)
        result = fe._get_sessions_window(days=7)
        assert len(result) > 0

    def test_without_ref_date(self):
        repo = _make_session_repo(5)
        fe = FeatureEngine(session_repo=repo)
        result = fe._get_sessions_window(days=7)
        assert len(result) > 0

    def test_repo_exception(self):
        repo = MagicMock()
        repo.get_recent_sessions.side_effect = Exception("error")
        fe = FeatureEngine(session_repo=repo)
        result = fe._get_sessions_window(days=7)
        assert result == []
