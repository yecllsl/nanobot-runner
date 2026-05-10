from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock

import pytest

from src.core.prediction.feature_engine import FeatureEngine


@pytest.fixture
def mock_session_repo() -> MagicMock:
    repo = MagicMock()
    recent_sessions = []
    for i in range(7):
        s = MagicMock()
        s.distance_km = 10.0
        s.distance = 10.0
        s.tss = 60.0 + i * 5
        s.intensity_factor = 0.85
        s.duration_s = 2700.0
        s.total_timer_time = 2700.0
        s.date = (date.today() - timedelta(days=i)).isoformat()
        recent_sessions.append(s)
    repo.get_recent_sessions.return_value = recent_sessions
    return repo


@pytest.fixture
def mock_load_analyzer() -> MagicMock:
    analyzer = MagicMock()
    analyzer.calculate_ctl.return_value = 55.0
    analyzer.calculate_atl.return_value = 50.0
    analyzer.get_load_ramp_rate.return_value = 5.0
    analyzer.get_training_load_trend.return_value = {
        "trend_data": [{"tsb": -5.0 + i} for i in range(14)]
    }
    return analyzer


@pytest.fixture
def mock_hrv_analyzer() -> MagicMock:
    analyzer = MagicMock()
    analyzer.get_resting_hr_deviation.return_value = 3.0
    analyzer.get_rmssd_trend.return_value = -0.5
    analyzer.get_sdnn_deviation.return_value = 2.0
    analyzer.get_resting_hr_7d_trend.return_value = 0.2
    return analyzer


@pytest.fixture
def mock_body_signal_engine() -> MagicMock:
    engine = MagicMock()
    engine.get_fatigue_score.return_value = 35.0
    engine.hrv_analyzer = MagicMock()
    engine.hrv_analyzer.get_resting_hr_deviation.return_value = 3.0
    engine.hrv_analyzer.get_rmssd_trend.return_value = -0.5
    engine.hrv_analyzer.get_sdnn_deviation.return_value = 2.0
    engine.hrv_analyzer.get_resting_hr_7d_trend.return_value = 0.2
    return engine


@pytest.fixture
def mock_vdot_calculator() -> MagicMock:
    calc = MagicMock()
    calc.calculate_vdot.return_value = 48.0
    return calc


def test_vdot_features_nonzero_with_data(
    mock_session_repo,
    mock_load_analyzer,
    mock_hrv_analyzer,
    mock_body_signal_engine,
    mock_vdot_calculator,
):
    engine = FeatureEngine(
        session_repo=mock_session_repo,
        training_load_analyzer=mock_load_analyzer,
        hrv_analyzer=mock_hrv_analyzer,
        body_signal_engine=mock_body_signal_engine,
        vdot_calculator=mock_vdot_calculator,
    )
    matrix = engine.extract_vdot_features(days=30)
    features = matrix.features.flatten()

    assert features[0] > 0, "weekly_volume_km should be > 0"
    assert features[4] > 0, "ctl_value should be > 0"
    assert features[5] != 0, "tsb_value should be != 0"
    assert features[10] > 0, "fatigue_score should be > 0"


def test_injury_features_nonzero_with_data(
    mock_session_repo,
    mock_load_analyzer,
    mock_hrv_analyzer,
    mock_body_signal_engine,
    mock_vdot_calculator,
):
    engine = FeatureEngine(
        session_repo=mock_session_repo,
        training_load_analyzer=mock_load_analyzer,
        hrv_analyzer=mock_hrv_analyzer,
        body_signal_engine=mock_body_signal_engine,
        vdot_calculator=mock_vdot_calculator,
    )
    matrix = engine.extract_injury_features(days=30)
    features = matrix.features.flatten()

    assert features[0] > 0, "atl_ctl_ratio should be > 0"


def test_race_features_nonzero_with_data(
    mock_session_repo,
    mock_load_analyzer,
    mock_hrv_analyzer,
    mock_body_signal_engine,
    mock_vdot_calculator,
):
    engine = FeatureEngine(
        session_repo=mock_session_repo,
        training_load_analyzer=mock_load_analyzer,
        hrv_analyzer=mock_hrv_analyzer,
        body_signal_engine=mock_body_signal_engine,
        vdot_calculator=mock_vdot_calculator,
    )
    matrix = engine.extract_race_features()
    features = matrix.features.flatten()

    assert features[0] > 0, "current_vdot should be > 0"
