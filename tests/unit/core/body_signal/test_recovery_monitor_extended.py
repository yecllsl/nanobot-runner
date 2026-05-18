from datetime import datetime, timedelta
from unittest.mock import MagicMock

import polars as pl
import pytest

from src.core.body_signal.exceptions import BodySignalError
from src.core.body_signal.models import (
    DataQuality,
    RecoveryPoint,
    RestingHRPoint,
)
from src.core.body_signal.recovery_monitor import RecoveryMonitor
from src.core.config.body_signal_config import BodySignalConfig
from src.core.models.recovery import RecoveryStatus


@pytest.fixture
def mock_session_repo():
    repo = MagicMock()
    repo.storage = MagicMock()
    return repo


@pytest.fixture
def mock_training_load_analyzer():
    analyzer = MagicMock()
    analyzer.calculate_training_load_from_dataframe.return_value = {
        "atl": 50.0,
        "ctl": 60.0,
        "tsb": 10.0,
        "runs_count": 5,
    }
    analyzer.calculate_tss_for_run.return_value = 50.0
    analyzer.update_atl_ctl_incremental.return_value = {
        "atl": 40.0,
        "ctl": 55.0,
    }
    return analyzer


@pytest.fixture
def mock_hrv_analyzer():
    analyzer = MagicMock()
    analyzer.get_resting_hr_trend.return_value = []
    return analyzer


class TestRecoveryMonitorYellowStatus:
    def test_yellow_status_tsb_between_zero_and_threshold(
        self, mock_session_repo, mock_training_load_analyzer, mock_hrv_analyzer
    ):
        mock_training_load_analyzer.calculate_training_load_from_dataframe.return_value = {
            "atl": 65.0,
            "ctl": 60.0,
            "tsb": -5.0,
            "runs_count": 5,
        }
        monitor = RecoveryMonitor(
            mock_session_repo, mock_training_load_analyzer, mock_hrv_analyzer
        )
        result = monitor.get_recovery_status()
        assert result.recovery_status == RecoveryStatus.YELLOW
        assert result.data_quality == DataQuality.SUFFICIENT

    def test_tsb_capped_at_config_value(
        self, mock_session_repo, mock_training_load_analyzer, mock_hrv_analyzer
    ):
        mock_training_load_analyzer.calculate_training_load_from_dataframe.return_value = {
            "atl": 10.0,
            "ctl": 100.0,
            "tsb": 90.0,
            "runs_count": 5,
        }
        config = BodySignalConfig(tsb_cap=50.0)
        monitor = RecoveryMonitor(
            mock_session_repo, mock_training_load_analyzer, mock_hrv_analyzer, config
        )
        result = monitor.get_recovery_status()
        assert result.recovery_status == RecoveryStatus.GREEN


class TestRecoveryMonitorRestDayEffect:
    def test_rest_day_effect_insufficient_data(
        self, mock_session_repo, mock_training_load_analyzer, mock_hrv_analyzer
    ):
        mock_hrv_analyzer.get_resting_hr_trend.return_value = [
            RestingHRPoint("2024-01-01", 65.0, 0.0),
        ]
        monitor = RecoveryMonitor(
            mock_session_repo, mock_training_load_analyzer, mock_hrv_analyzer
        )
        result = monitor.check_rest_day_effect()
        assert result.effect_level == "minimal"
        assert "数据不足" in result.message

    def test_rest_day_effect_zero_previous_hr(
        self, mock_session_repo, mock_training_load_analyzer, mock_hrv_analyzer
    ):
        mock_hrv_analyzer.get_resting_hr_trend.return_value = [
            RestingHRPoint("2024-01-01", 0.0, 0.0),
            RestingHRPoint("2024-01-02", 60.0, 0.0),
        ]
        monitor = RecoveryMonitor(
            mock_session_repo, mock_training_load_analyzer, mock_hrv_analyzer
        )
        result = monitor.check_rest_day_effect()
        assert result.resting_hr_change_pct == 0.0

    def test_rest_day_effect_body_signal_error(
        self, mock_session_repo, mock_training_load_analyzer, mock_hrv_analyzer
    ):
        mock_hrv_analyzer.get_resting_hr_trend.side_effect = BodySignalError(
            "HRV数据异常"
        )
        monitor = RecoveryMonitor(
            mock_session_repo, mock_training_load_analyzer, mock_hrv_analyzer
        )
        result = monitor.check_rest_day_effect()
        assert result.effect_level == "minimal"
        assert "评估失败" in result.message

    def test_rest_day_effect_good_hr_improvement(
        self, mock_session_repo, mock_training_load_analyzer, mock_hrv_analyzer
    ):
        mock_hrv_analyzer.get_resting_hr_trend.return_value = [
            RestingHRPoint("2024-01-01", 70.0, 5.0),
            RestingHRPoint("2024-01-02", 62.0, -3.0),
        ]
        config = BodySignalConfig(rest_hr_improvement_pct=5.0)
        monitor = RecoveryMonitor(
            mock_session_repo, mock_training_load_analyzer, mock_hrv_analyzer, config
        )
        result = monitor.check_rest_day_effect()
        assert result.effect_level == "good"
        assert result.resting_hr_change_pct > 0

    def test_rest_day_effect_minimal_change(
        self, mock_session_repo, mock_training_load_analyzer, mock_hrv_analyzer
    ):
        mock_hrv_analyzer.get_resting_hr_trend.return_value = [
            RestingHRPoint("2024-01-01", 60.0, 0.0),
            RestingHRPoint("2024-01-02", 59.5, 0.0),
        ]
        config = BodySignalConfig(rest_hr_improvement_pct=5.0)
        monitor = RecoveryMonitor(
            mock_session_repo, mock_training_load_analyzer, mock_hrv_analyzer, config
        )
        result = monitor.check_rest_day_effect()
        assert result.effect_level == "minimal"


class TestRecoveryMonitorTrend:
    def test_get_recovery_trend_no_session_start_time(
        self, mock_session_repo, mock_training_load_analyzer, mock_hrv_analyzer
    ):
        lf = pl.DataFrame({"other_col": [1, 2, 3]}).lazy()
        mock_session_repo.storage.read_parquet.return_value = lf

        monitor = RecoveryMonitor(
            mock_session_repo, mock_training_load_analyzer, mock_hrv_analyzer
        )
        trend = monitor.get_recovery_trend(days=7)
        assert trend == []

    def test_get_recovery_trend_with_data(
        self, mock_session_repo, mock_training_load_analyzer, mock_hrv_analyzer
    ):
        now = datetime.now()
        base_time = now - timedelta(days=2)
        lf = pl.DataFrame(
            {
                "session_start_time": [
                    base_time,
                    base_time + timedelta(days=1),
                ],
                "session_total_distance": [5000.0, 8000.0],
                "session_total_timer_time": [1800.0, 3000.0],
                "session_avg_heart_rate": [150.0, 160.0],
            }
        ).lazy()
        mock_session_repo.storage.read_parquet.return_value = lf
        mock_training_load_analyzer.update_atl_ctl_incremental.return_value = {
            "atl": 40.0,
            "ctl": 55.0,
        }

        monitor = RecoveryMonitor(
            mock_session_repo, mock_training_load_analyzer, mock_hrv_analyzer
        )
        trend = monitor.get_recovery_trend(days=7)
        assert isinstance(trend, list)
        if len(trend) > 0:
            assert all(isinstance(p, RecoveryPoint) for p in trend)

    def test_get_recovery_trend_body_signal_error(
        self, mock_session_repo, mock_training_load_analyzer, mock_hrv_analyzer
    ):
        mock_session_repo.storage.read_parquet.side_effect = BodySignalError("error")
        monitor = RecoveryMonitor(
            mock_session_repo, mock_training_load_analyzer, mock_hrv_analyzer
        )
        trend = monitor.get_recovery_trend(days=7)
        assert trend == []

    def test_get_recovery_trend_resets_incremental_state(
        self, mock_session_repo, mock_training_load_analyzer, mock_hrv_analyzer
    ):
        now = datetime.now()
        base_time = now - timedelta(days=2)
        lf = pl.DataFrame(
            {
                "session_start_time": [base_time],
                "session_total_distance": [5000.0],
                "session_total_timer_time": [1800.0],
            }
        ).lazy()
        mock_session_repo.storage.read_parquet.return_value = lf

        monitor = RecoveryMonitor(
            mock_session_repo, mock_training_load_analyzer, mock_hrv_analyzer
        )
        monitor.get_recovery_trend(days=7)
        mock_training_load_analyzer.reset_incremental_state.assert_called()

    def test_get_recovery_trend_missing_optional_columns(
        self, mock_session_repo, mock_training_load_analyzer, mock_hrv_analyzer
    ):
        now = datetime.now()
        base_time = now - timedelta(days=2)
        lf = pl.DataFrame(
            {
                "session_start_time": [base_time],
            }
        ).lazy()
        mock_session_repo.storage.read_parquet.return_value = lf

        monitor = RecoveryMonitor(
            mock_session_repo, mock_training_load_analyzer, mock_hrv_analyzer
        )
        trend = monitor.get_recovery_trend(days=7)
        assert isinstance(trend, list)

    def test_get_recovery_trend_null_session_time(
        self, mock_session_repo, mock_training_load_analyzer, mock_hrv_analyzer
    ):
        lf = pl.DataFrame(
            {
                "session_start_time": [None, None],
                "session_total_distance": [5000.0, 8000.0],
                "session_total_timer_time": [1800.0, 3000.0],
            }
        ).lazy()
        mock_session_repo.storage.read_parquet.return_value = lf

        monitor = RecoveryMonitor(
            mock_session_repo, mock_training_load_analyzer, mock_hrv_analyzer
        )
        trend = monitor.get_recovery_trend(days=7)
        assert isinstance(trend, list)
