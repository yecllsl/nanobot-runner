"""BUG-2202回归测试：fatigue/recovery无心率数据时应区分"无数据"和"有数据但无心率"

验证当已导入数据但缺少心率信息时，fatigue/recovery不应显示"暂无训练数据"，
而应给出更有意义的提示。
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import polars as pl
import pytest

from src.core.body_signal.fatigue_assessor import FatigueAssessor
from src.core.body_signal.models import DataQuality
from src.core.body_signal.recovery_monitor import RecoveryMonitor


@pytest.fixture
def mock_session_repo_with_no_hr_data():
    """创建有数据但无心率列的Mock SessionRepository"""
    repo = MagicMock()
    repo.storage = MagicMock()

    now = datetime.now()
    lf = pl.DataFrame(
        {
            "session_start_time": [now - timedelta(days=i) for i in range(5)],
            "session_total_distance": [8000.0, 10000.0, 5000.0, 12000.0, 6000.0],
            "session_total_timer_time": [2400.0, 3000.0, 1800.0, 3600.0, 2100.0],
            "session_avg_heart_rate": [None, None, None, None, None],
        }
    ).lazy()
    repo.storage.read_parquet.return_value = lf
    return repo


@pytest.fixture
def mock_training_load_analyzer_no_hr():
    """创建返回runs_count=0（因无心率）的Mock TrainingLoadAnalyzer"""
    analyzer = MagicMock()
    analyzer.calculate_training_load_from_dataframe.return_value = {
        "atl": 0.0,
        "ctl": 0.0,
        "tsb": 0.0,
        "runs_count": 0,
        "total_runs": 5,
    }
    analyzer.calculate_tss_for_run.return_value = 0.0
    return analyzer


class TestBug2202FatigueNoHeartRate:
    """BUG-2202: fatigue无心率数据时的处理"""

    def test_fatigue_with_data_but_no_hr_not_empty(
        self, mock_session_repo_with_no_hr_data, mock_training_load_analyzer_no_hr
    ):
        """有训练数据但无心率时，data_quality不应为EMPTY"""
        assessor = FatigueAssessor(
            mock_session_repo_with_no_hr_data,
            mock_training_load_analyzer_no_hr,
        )
        result = assessor.assess_fatigue()

        assert result.data_quality != DataQuality.EMPTY, (
            "有训练数据（即使无心率）时，data_quality不应为EMPTY"
        )

    def test_fatigue_with_data_but_no_hr_has_meaningful_message(
        self, mock_session_repo_with_no_hr_data, mock_training_load_analyzer_no_hr
    ):
        """有训练数据但无心率时，建议应提及心率缺失"""
        assessor = FatigueAssessor(
            mock_session_repo_with_no_hr_data,
            mock_training_load_analyzer_no_hr,
        )
        result = assessor.assess_fatigue()

        assert "暂无训练数据" not in result.recommendation, (
            f"有训练数据时不应显示'暂无训练数据'，实际为'{result.recommendation}'"
        )


class TestBug2202RecoveryNoHeartRate:
    """BUG-2202: recovery无心率数据时的处理"""

    def test_recovery_with_data_but_no_hr_not_empty(
        self, mock_session_repo_with_no_hr_data, mock_training_load_analyzer_no_hr
    ):
        """有训练数据但无心率时，data_quality不应为EMPTY"""
        hrv_analyzer = MagicMock()
        hrv_analyzer.analyze_hrv.return_value = MagicMock(
            data_quality=DataQuality.EMPTY
        )

        monitor = RecoveryMonitor(
            mock_session_repo_with_no_hr_data,
            mock_training_load_analyzer_no_hr,
            hrv_analyzer,
        )
        result = monitor.get_recovery_status()

        assert result.data_quality != DataQuality.EMPTY, (
            "有训练数据（即使无心率）时，data_quality不应为EMPTY"
        )

    def test_recovery_with_data_but_no_hr_has_meaningful_message(
        self, mock_session_repo_with_no_hr_data, mock_training_load_analyzer_no_hr
    ):
        """有训练数据但无心率时，不应显示'暂无训练数据'"""
        hrv_analyzer = MagicMock()
        hrv_analyzer.analyze_hrv.return_value = MagicMock(
            data_quality=DataQuality.EMPTY
        )

        monitor = RecoveryMonitor(
            mock_session_repo_with_no_hr_data,
            mock_training_load_analyzer_no_hr,
            hrv_analyzer,
        )
        result = monitor.get_recovery_status()

        assert "暂无训练数据" not in result.rest_day_effect.message, (
            f"有训练数据时不应显示'暂无训练数据'，实际为'{result.rest_day_effect.message}'"
        )
