"""BUG-2205回归测试：HRV分析模块lf.columns触发Polars PerformanceWarning

验证所有body_signal模块中使用lf.columns的地方已替换为lf.collect_schema().names()
"""

import contextlib
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import polars as pl

from src.core.body_signal.fatigue_assessor import FatigueAssessor
from src.core.body_signal.hrv_analyzer import HRVAnalyzer
from src.core.body_signal.recovery_monitor import RecoveryMonitor
from src.core.config.body_signal_config import BodySignalConfig


def _make_session_repo_with_parquet():
    """创建包含session数据的Mock"""
    repo = MagicMock()
    repo.storage = MagicMock()

    now = datetime.now()
    lf = pl.DataFrame(
        {
            "session_start_time": [now - timedelta(days=i) for i in range(5)],
            "session_total_distance": [8000.0] * 5,
            "session_total_timer_time": [2400.0] * 5,
            "session_avg_heart_rate": [150.0] * 5,
        }
    ).lazy()
    repo.storage.read_parquet.return_value = lf
    return repo


class TestBug2205NoPerformanceWarning:
    """BUG-2205: 确保不触发Polars PerformanceWarning"""

    def test_hrv_analyzer_no_lf_columns_warning(self):
        """HRVAnalyzer不应使用lf.columns触发PerformanceWarning"""
        import warnings

        repo = _make_session_repo_with_parquet()
        config = BodySignalConfig()
        analyzer = HRVAnalyzer(session_repo=repo, config=config)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            with contextlib.suppress(Exception):
                analyzer.analyze_hrv(days=7)

            perf_warnings = [
                x
                for x in w
                if "Determining the column names" in str(x.message)
                or "PerformanceWarning" in str(x.category)
            ]
            assert len(perf_warnings) == 0, (
                f"不应触发PerformanceWarning，实际触发了{len(perf_warnings)}次"
            )

    def test_fatigue_assessor_no_lf_columns_warning(self):
        """FatigueAssessor不应使用lf.columns触发PerformanceWarning"""
        import warnings

        repo = _make_session_repo_with_parquet()
        training_load_analyzer = MagicMock()
        training_load_analyzer.calculate_training_load_from_dataframe.return_value = {
            "atl": 50.0,
            "ctl": 60.0,
            "tsb": 10.0,
            "runs_count": 5,
        }
        training_load_analyzer.calculate_tss_for_run.return_value = 85.0

        assessor = FatigueAssessor(repo, training_load_analyzer)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            with contextlib.suppress(Exception):
                assessor.get_consecutive_hard_days()

            perf_warnings = [
                x
                for x in w
                if "Determining the column names" in str(x.message)
                or "PerformanceWarning" in str(x.category)
            ]
            assert len(perf_warnings) == 0, (
                f"不应触发PerformanceWarning，实际触发了{len(perf_warnings)}次"
            )

    def test_recovery_monitor_no_lf_columns_warning(self):
        """RecoveryMonitor不应使用lf.columns触发PerformanceWarning"""
        import warnings

        repo = _make_session_repo_with_parquet()
        training_load_analyzer = MagicMock()
        training_load_analyzer.calculate_training_load_from_dataframe.return_value = {
            "atl": 50.0,
            "ctl": 60.0,
            "tsb": 10.0,
            "runs_count": 5,
        }
        training_load_analyzer.calculate_tss_for_run.return_value = 85.0
        training_load_analyzer.reset_incremental_state.return_value = None
        training_load_analyzer.update_atl_ctl_incremental.return_value = {
            "atl": 50.0,
            "ctl": 60.0,
        }

        hrv_analyzer = MagicMock()

        monitor = RecoveryMonitor(repo, training_load_analyzer, hrv_analyzer)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            with contextlib.suppress(Exception):
                monitor.get_recovery_trend(days=7)

            perf_warnings = [
                x
                for x in w
                if "Determining the column names" in str(x.message)
                or "PerformanceWarning" in str(x.category)
            ]
            assert len(perf_warnings) == 0, (
                f"不应触发PerformanceWarning，实际触发了{len(perf_warnings)}次"
            )
