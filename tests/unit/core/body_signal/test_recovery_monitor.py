# 恢复监控器单元测试
# v0.19.0 新增

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import polars as pl
import pytest

from src.core.body_signal.models import DataQuality
from src.core.body_signal.recovery_monitor import RecoveryMonitor
from src.core.config.body_signal_config import BodySignalConfig
from src.core.models.recovery import RecoveryStatus


@pytest.fixture
def mock_session_repo():
    """创建Mock SessionRepository"""
    repo = MagicMock()
    repo.storage = MagicMock()
    return repo


@pytest.fixture
def mock_training_load_analyzer():
    """创建Mock TrainingLoadAnalyzer"""
    analyzer = MagicMock()
    analyzer.calculate_training_load_from_dataframe.return_value = {
        "atl": 50.0,
        "ctl": 60.0,
        "tsb": 10.0,
        "runs_count": 5,
    }
    analyzer.calculate_tss_for_run.return_value = 50.0
    return analyzer


@pytest.fixture
def mock_hrv_analyzer():
    """创建Mock HRVAnalyzer"""
    analyzer = MagicMock()
    analyzer.get_resting_hr_trend.return_value = []
    return analyzer


class TestRecoveryMonitor:
    """恢复监控器测试类"""

    def test_init(
        self, mock_session_repo, mock_training_load_analyzer, mock_hrv_analyzer
    ):
        """测试初始化"""
        config = BodySignalConfig()
        monitor = RecoveryMonitor(
            mock_session_repo, mock_training_load_analyzer, mock_hrv_analyzer, config
        )

        assert monitor.session_repo == mock_session_repo
        assert monitor.training_load_analyzer == mock_training_load_analyzer
        assert monitor.hrv_analyzer == mock_hrv_analyzer
        assert monitor.config == config

    def test_get_recovery_status_green(
        self, mock_session_repo, mock_training_load_analyzer, mock_hrv_analyzer
    ):
        """测试GREEN恢复状态"""
        mock_training_load_analyzer.calculate_training_load_from_dataframe.return_value = {
            "atl": 20.0,
            "ctl": 60.0,
            "tsb": 20.0,
            "runs_count": 5,
        }

        monitor = RecoveryMonitor(
            mock_session_repo, mock_training_load_analyzer, mock_hrv_analyzer
        )
        result = monitor.get_recovery_status()

        assert result.recovery_status == RecoveryStatus.GREEN
        assert result.data_quality == DataQuality.SUFFICIENT

    def test_get_recovery_status_red(
        self, mock_session_repo, mock_training_load_analyzer, mock_hrv_analyzer
    ):
        """测试RED恢复状态"""
        mock_training_load_analyzer.calculate_training_load_from_dataframe.return_value = {
            "atl": 80.0,
            "ctl": 50.0,
            "tsb": -30.0,
            "runs_count": 5,
        }

        monitor = RecoveryMonitor(
            mock_session_repo, mock_training_load_analyzer, mock_hrv_analyzer
        )
        result = monitor.get_recovery_status()

        assert result.recovery_status == RecoveryStatus.RED

    def test_get_recovery_status_no_data(
        self, mock_session_repo, mock_training_load_analyzer, mock_hrv_analyzer
    ):
        """测试无数据时返回EMPTY"""
        mock_training_load_analyzer.calculate_training_load_from_dataframe.return_value = {
            "atl": 0.0,
            "ctl": 0.0,
            "tsb": 0.0,
            "runs_count": 0,
        }

        monitor = RecoveryMonitor(
            mock_session_repo, mock_training_load_analyzer, mock_hrv_analyzer
        )
        result = monitor.get_recovery_status()

        assert result.data_quality == DataQuality.EMPTY

    def test_check_rest_day_effect_good(
        self, mock_session_repo, mock_training_load_analyzer, mock_hrv_analyzer
    ):
        """测试休息日效果良好"""
        from src.core.body_signal.models import RestingHRPoint

        mock_hrv_analyzer.get_resting_hr_trend.return_value = [
            RestingHRPoint("2024-01-01", 65.0, 5.0),
            RestingHRPoint("2024-01-02", 60.0, -2.0),
        ]

        monitor = RecoveryMonitor(
            mock_session_repo, mock_training_load_analyzer, mock_hrv_analyzer
        )
        result = monitor.check_rest_day_effect()

        assert result.effect_level == "good"
        assert "静息心率明显下降" in result.message

    def test_check_rest_day_effect_minimal(
        self, mock_session_repo, mock_training_load_analyzer, mock_hrv_analyzer
    ):
        """测试休息日效果不明显"""
        from src.core.body_signal.models import RestingHRPoint

        mock_hrv_analyzer.get_resting_hr_trend.return_value = [
            RestingHRPoint("2024-01-01", 60.0, 0.0),
            RestingHRPoint("2024-01-02", 60.0, 0.0),
        ]

        monitor = RecoveryMonitor(
            mock_session_repo, mock_training_load_analyzer, mock_hrv_analyzer
        )
        result = monitor.check_rest_day_effect()

        assert result.effect_level == "minimal"

    def test_get_recovery_trend(
        self, mock_session_repo, mock_training_load_analyzer, mock_hrv_analyzer
    ):
        """测试恢复趋势"""
        import polars as pl

        base_time = datetime(2024, 1, 1, 8, 0, 0)
        lf = pl.DataFrame(
            {
                "session_start_time": [
                    base_time,
                    base_time + timedelta(days=1),
                    base_time + timedelta(days=2),
                ],
                "session_total_distance": [5000.0, 8000.0, 6000.0],
                "session_total_timer_time": [1800.0, 3000.0, 2100.0],
                "session_avg_heart_rate": [150.0, 160.0, 155.0],
            }
        ).lazy()
        mock_session_repo.storage.read_parquet.return_value = lf

        monitor = RecoveryMonitor(
            mock_session_repo, mock_training_load_analyzer, mock_hrv_analyzer
        )
        trend = monitor.get_recovery_trend(days=7)

        assert isinstance(trend, list)

    def test_get_recovery_trend_empty(
        self, mock_session_repo, mock_training_load_analyzer, mock_hrv_analyzer
    ):
        """测试空数据的恢复趋势"""
        lf = pl.DataFrame(
            {
                "session_start_time": [],
            }
        ).lazy()
        mock_session_repo.storage.read_parquet.return_value = lf

        monitor = RecoveryMonitor(
            mock_session_repo, mock_training_load_analyzer, mock_hrv_analyzer
        )
        trend = monitor.get_recovery_trend(days=7)

        assert trend == []
