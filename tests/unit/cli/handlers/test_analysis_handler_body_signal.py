# 分析 Handler 身体信号方法单元测试
# v0.19.0 新增

from unittest.mock import MagicMock, patch

import pytest

from src.cli.handlers.analysis_handler import AnalysisHandler
from src.core.body_signal.models import DataQuality
from src.core.models.recovery import RecoveryStatus


@pytest.fixture
def mock_context():
    """创建 Mock 应用上下文"""
    context = MagicMock()
    context.session_repo = MagicMock()
    context.storage = MagicMock()
    context.analytics = MagicMock()
    return context


class TestAnalysisHandlerBodySignal:
    """AnalysisHandler 身体信号方法单元测试"""

    @patch("src.core.body_signal.hrv_analyzer.HRVAnalyzer")
    def test_get_hrv_analysis(self, mock_hrv_analyzer_cls, mock_context):
        """测试获取HRV分析结果"""
        mock_hrv_result = MagicMock()
        mock_hrv_result.to_dict.return_value = {
            "resting_hr_trend": [
                {"date": "2024-01-01", "resting_hr": 55.0, "deviation_pct": -2.0}
            ],
            "data_quality": DataQuality.SUFFICIENT.value,
            "data_source": "hr_estimate",
        }

        mock_hrv_metrics = {
            "estimated_rmssd": 45.5,
            "estimated_sdnn": 55.2,
            "data_source": "hr_estimate",
        }

        mock_hrv_analyzer = MagicMock()
        mock_hrv_analyzer.analyze_hrv.return_value = mock_hrv_result
        mock_hrv_analyzer.estimate_hrv_metrics.return_value = mock_hrv_metrics
        mock_hrv_analyzer_cls.return_value = mock_hrv_analyzer

        handler = AnalysisHandler(context=mock_context)
        result = handler.get_hrv_analysis(days=30)

        assert result["data_quality"] == DataQuality.SUFFICIENT.value
        assert "estimated_hrv_metrics" in result
        assert result["estimated_hrv_metrics"]["estimated_rmssd"] == 45.5
        mock_hrv_analyzer.analyze_hrv.assert_called_once_with(days=30)

    @patch("src.core.body_signal.hrv_analyzer.HRVAnalyzer")
    def test_get_hr_recovery(self, mock_hrv_analyzer_cls, mock_context):
        """测试获取心率恢复分析"""
        mock_recovery_result = MagicMock()
        mock_recovery_result.to_dict.return_value = {
            "hr_end": 165.0,
            "hr_recovery_1min": 25.0,
            "data_quality": DataQuality.SUFFICIENT.value,
        }

        mock_hrv_analyzer = MagicMock()
        mock_hrv_analyzer.analyze_hr_recovery.return_value = mock_recovery_result
        mock_hrv_analyzer_cls.return_value = mock_hrv_analyzer

        handler = AnalysisHandler(context=mock_context)
        result = handler.get_hr_recovery()

        assert result["hr_end"] == 165.0
        assert result["hr_recovery_1min"] == 25.0
        mock_hrv_analyzer.analyze_hr_recovery.assert_called_once()

    @patch("src.core.calculators.training_load_analyzer.TrainingLoadAnalyzer")
    @patch("src.core.body_signal.fatigue_assessor.FatigueAssessor")
    def test_get_fatigue_score(self, mock_fatigue_cls, mock_tla_cls, mock_context):
        """测试获取疲劳度评估"""
        mock_fatigue_result = MagicMock()
        mock_fatigue_result.to_dict.return_value = {
            "fatigue_score": 35.0,
            "recovery_status": RecoveryStatus.GREEN.value,
            "consecutive_hard_days": 1,
            "recommendation": "状态良好",
            "data_quality": DataQuality.SUFFICIENT.value,
            "breakdown": {
                "atl_component": 20.0,
                "hr_deviation_component": 5.0,
                "consecutive_component": 10.0,
                "subjective_component": 0.0,
            },
        }

        mock_fatigue_assessor = MagicMock()
        mock_fatigue_assessor.assess_fatigue.return_value = mock_fatigue_result
        mock_fatigue_cls.return_value = mock_fatigue_assessor

        handler = AnalysisHandler(context=mock_context)
        result = handler.get_fatigue_score(rpe=6)

        assert result["fatigue_score"] == 35.0
        assert result["recovery_status"] == RecoveryStatus.GREEN.value
        mock_fatigue_assessor.assess_fatigue.assert_called_once_with(rpe=6)

    @patch("src.core.calculators.training_load_analyzer.TrainingLoadAnalyzer")
    @patch("src.core.body_signal.hrv_analyzer.HRVAnalyzer")
    @patch("src.core.body_signal.recovery_monitor.RecoveryMonitor")
    def test_get_recovery_status(
        self, mock_recovery_cls, mock_hrv_cls, mock_tla_cls, mock_context
    ):
        """测试获取恢复状态"""
        mock_recovery_result = MagicMock()
        mock_recovery_result.to_dict.return_value = {
            "recovery_status": RecoveryStatus.GREEN.value,
            "rest_day_effect": {
                "resting_hr_change_pct": -3.0,
                "tsb_change": 5.0,
                "effect_level": "good",
                "message": "休息效果好",
            },
            "data_quality": DataQuality.SUFFICIENT.value,
        }

        mock_recovery_monitor = MagicMock()
        mock_recovery_monitor.get_recovery_status.return_value = mock_recovery_result
        mock_recovery_cls.return_value = mock_recovery_monitor

        handler = AnalysisHandler(context=mock_context)
        result = handler.get_recovery_status()

        assert result["recovery_status"] == RecoveryStatus.GREEN.value
        assert result["rest_day_effect"]["effect_level"] == "good"
        mock_recovery_monitor.get_recovery_status.assert_called_once()

    @patch("src.core.calculators.training_load_analyzer.TrainingLoadAnalyzer")
    @patch("src.core.body_signal.hrv_analyzer.HRVAnalyzer")
    @patch("src.core.body_signal.recovery_monitor.RecoveryMonitor")
    def test_compare_training_periods(
        self, mock_recovery_cls, mock_hrv_cls, mock_tla_cls, mock_context
    ):
        """测试对比训练周期"""
        from src.core.body_signal.models import RecoveryPoint

        mock_recovery_monitor = MagicMock()
        # 数据按时间顺序排列（最早在前，最近在后）
        # period1 = 最近2天, period2 = 更早的2天
        mock_recovery_monitor.get_recovery_trend.side_effect = [
            [
                RecoveryPoint(date="2024-01-07", tsb=8.0, ctl=48.0),
                RecoveryPoint(date="2024-01-08", tsb=10.0, ctl=50.0),
            ],
            [
                RecoveryPoint(date="2024-01-05", tsb=3.0, ctl=43.0),
                RecoveryPoint(date="2024-01-06", tsb=5.0, ctl=45.0),
                RecoveryPoint(date="2024-01-07", tsb=8.0, ctl=48.0),
                RecoveryPoint(date="2024-01-08", tsb=10.0, ctl=50.0),
            ],
        ]
        mock_recovery_cls.return_value = mock_recovery_monitor

        mock_hrv_result = MagicMock()
        mock_hrv_result.data_quality = DataQuality.SUFFICIENT
        mock_hrv_analyzer = MagicMock()
        mock_hrv_analyzer.analyze_hrv.return_value = mock_hrv_result
        mock_hrv_cls.return_value = mock_hrv_analyzer

        handler = AnalysisHandler(context=mock_context)
        result = handler.compare_training_periods(period1_days=2, period2_days=2)

        assert "period1" in result
        assert "period2" in result
        assert "tsb_change" in result
        assert "comparison_summary" in result
        assert result["period1_days"] == 2
        assert result["period2_days"] == 2
        # period1 avg_tsb = (8 + 10) / 2 = 9.0
        # period2 = 总共4天排除最近2天 = [3.0, 5.0], avg_tsb = 4.0
        assert result["period1"]["avg_tsb"] == 9.0
        assert result["period2"]["avg_tsb"] == 4.0
        assert result["tsb_change"] == 5.0
        assert "改善" in result["comparison_summary"]

    @patch("src.core.calculators.training_load_analyzer.TrainingLoadAnalyzer")
    @patch("src.core.body_signal.hrv_analyzer.HRVAnalyzer")
    @patch("src.core.body_signal.recovery_monitor.RecoveryMonitor")
    def test_compare_training_periods_empty_data(
        self, mock_recovery_cls, mock_hrv_cls, mock_tla_cls, mock_context
    ):
        """测试对比训练周期无数据情况"""
        mock_recovery_monitor = MagicMock()
        mock_recovery_monitor.get_recovery_trend.return_value = []
        mock_recovery_cls.return_value = mock_recovery_monitor

        mock_hrv_result = MagicMock()
        mock_hrv_result.data_quality = DataQuality.EMPTY
        mock_hrv_analyzer = MagicMock()
        mock_hrv_analyzer.analyze_hrv.return_value = mock_hrv_result
        mock_hrv_cls.return_value = mock_hrv_analyzer

        handler = AnalysisHandler(context=mock_context)
        result = handler.compare_training_periods(period1_days=7, period2_days=7)

        assert result["period1"]["avg_tsb"] == 0.0
        assert result["period2"]["avg_tsb"] == 0.0
        assert result["tsb_change"] == 0.0
