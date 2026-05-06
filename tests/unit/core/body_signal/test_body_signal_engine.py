# 身体信号引擎单元测试
# v0.19.0 新增

from unittest.mock import MagicMock

import pytest

from src.core.body_signal.body_signal_engine import BodySignalEngine
from src.core.body_signal.models import (
    BodySignalAlert,
    BodySignalSummary,
    DataQuality,
    RecoveryPoint,
)
from src.core.models.recovery import RecoveryStatus


@pytest.fixture
def mock_hrv_analyzer():
    """创建Mock HRVAnalyzer"""
    analyzer = MagicMock()
    analyzer.analyze_hrv.return_value = MagicMock(
        resting_hr_trend=[],
        data_quality=DataQuality.SUFFICIENT,
        data_source=MagicMock(value="hr_estimate"),
        to_dict=lambda: {
            "resting_hr_trend": [],
            "data_quality": "sufficient",
            "data_source": "hr_estimate",
        },
    )
    analyzer.get_resting_hr_trend.return_value = []
    return analyzer


@pytest.fixture
def mock_fatigue_assessor():
    """创建Mock FatigueAssessor"""
    assessor = MagicMock()
    assessor.assess_fatigue.return_value = MagicMock(
        fatigue_score=30.0,
        recovery_status=RecoveryStatus.GREEN,
        consecutive_hard_days=0,
        breakdown=MagicMock(
            atl_component=30.0,
            hr_deviation_component=10.0,
            consecutive_component=0.0,
            subjective_component=0.0,
        ),
        recommendation="今天适合质量课训练",
        data_quality=DataQuality.SUFFICIENT,
        to_dict=lambda: {
            "fatigue_score": 30.0,
            "recovery_status": "green",
            "consecutive_hard_days": 0,
            "breakdown": {
                "atl_component": 30.0,
                "hr_deviation_component": 10.0,
                "consecutive_component": 0.0,
                "subjective_component": 0.0,
            },
            "recommendation": "今天适合质量课训练",
            "data_quality": "sufficient",
        },
    )
    return assessor


@pytest.fixture
def mock_recovery_monitor():
    """创建Mock RecoveryMonitor"""
    monitor = MagicMock()
    monitor.get_recovery_status.return_value = MagicMock(
        recovery_status=RecoveryStatus.GREEN,
        rest_day_effect=MagicMock(
            resting_hr_change_pct=0.0,
            tsb_change=0.0,
            effect_level="minimal",
            message="休息效果不明显",
        ),
        recovery_trend=[],
        data_quality=DataQuality.SUFFICIENT,
        to_dict=lambda: {
            "recovery_status": "green",
            "rest_day_effect": {
                "resting_hr_change_pct": 0.0,
                "tsb_change": 0.0,
                "effect_level": "minimal",
                "message": "休息效果不明显",
            },
            "recovery_trend": [],
            "data_quality": "sufficient",
        },
    )
    monitor.get_recovery_trend.return_value = []
    return monitor


class TestBodySignalEngine:
    """身体信号引擎测试类"""

    def test_init(
        self, mock_hrv_analyzer, mock_fatigue_assessor, mock_recovery_monitor
    ):
        """测试初始化"""
        engine = BodySignalEngine(
            hrv_analyzer=mock_hrv_analyzer,
            fatigue_assessor=mock_fatigue_assessor,
            recovery_monitor=mock_recovery_monitor,
        )

        assert engine.hrv_analyzer == mock_hrv_analyzer
        assert engine.fatigue_assessor == mock_fatigue_assessor
        assert engine.recovery_monitor == mock_recovery_monitor

    def test_get_daily_summary(
        self, mock_hrv_analyzer, mock_fatigue_assessor, mock_recovery_monitor
    ):
        """测试每日摘要"""
        engine = BodySignalEngine(
            hrv_analyzer=mock_hrv_analyzer,
            fatigue_assessor=mock_fatigue_assessor,
            recovery_monitor=mock_recovery_monitor,
        )

        summary = engine.get_daily_summary()

        assert isinstance(summary, BodySignalSummary)
        assert summary.recovery_status == RecoveryStatus.GREEN
        assert "今日状态" in summary.daily_summary

    def test_get_daily_summary_cache(
        self, mock_hrv_analyzer, mock_fatigue_assessor, mock_recovery_monitor
    ):
        """测试每日摘要缓存"""
        engine = BodySignalEngine(
            hrv_analyzer=mock_hrv_analyzer,
            fatigue_assessor=mock_fatigue_assessor,
            recovery_monitor=mock_recovery_monitor,
        )

        summary1 = engine.get_daily_summary()
        summary2 = engine.get_daily_summary()

        # 同一天第二次调用应返回缓存结果
        assert summary1 == summary2
        # HRV分析器只应被调用一次（缓存生效）
        mock_hrv_analyzer.analyze_hrv.assert_called_once()

    def test_get_weekly_summary(
        self, mock_hrv_analyzer, mock_fatigue_assessor, mock_recovery_monitor
    ):
        """测试每周摘要"""
        engine = BodySignalEngine(
            hrv_analyzer=mock_hrv_analyzer,
            fatigue_assessor=mock_fatigue_assessor,
            recovery_monitor=mock_recovery_monitor,
        )

        summary = engine.get_weekly_summary()

        assert isinstance(summary, BodySignalSummary)
        assert "本周状态" in summary.daily_summary

    def test_check_alerts_no_alerts(
        self, mock_hrv_analyzer, mock_fatigue_assessor, mock_recovery_monitor
    ):
        """测试无预警"""
        engine = BodySignalEngine(
            hrv_analyzer=mock_hrv_analyzer,
            fatigue_assessor=mock_fatigue_assessor,
            recovery_monitor=mock_recovery_monitor,
        )

        alerts = engine.check_alerts()

        assert alerts == []

    def test_check_alerts_hr_spike(
        self, mock_hrv_analyzer, mock_fatigue_assessor, mock_recovery_monitor
    ):
        """测试心率异常升高预警"""
        from src.core.body_signal.models import RestingHRPoint

        mock_hrv_analyzer.get_resting_hr_trend.return_value = [
            RestingHRPoint("2024-01-01", 60.0, 0.0),
            RestingHRPoint("2024-01-02", 60.0, 0.0),
            RestingHRPoint("2024-01-03", 60.0, 0.0),
            RestingHRPoint("2024-01-04", 60.0, 0.0),
            RestingHRPoint("2024-01-05", 60.0, 0.0),
            RestingHRPoint("2024-01-06", 60.0, 0.0),
            RestingHRPoint("2024-01-07", 70.0, 15.0),  # 偏差>10%
        ]

        engine = BodySignalEngine(
            hrv_analyzer=mock_hrv_analyzer,
            fatigue_assessor=mock_fatigue_assessor,
            recovery_monitor=mock_recovery_monitor,
        )

        alerts = engine.check_alerts()

        hr_spike_alerts = [a for a in alerts if a.alert_type == "hr_spike"]
        assert len(hr_spike_alerts) == 1
        assert hr_spike_alerts[0].severity == "warning"

    def test_check_alerts_overtraining(
        self, mock_hrv_analyzer, mock_fatigue_assessor, mock_recovery_monitor
    ):
        """测试过度训练预警"""
        mock_recovery_monitor.get_recovery_trend.return_value = [
            RecoveryPoint("2024-01-01", -25.0, 60.0),
            RecoveryPoint("2024-01-02", -25.0, 60.0),
            RecoveryPoint("2024-01-03", -25.0, 60.0),
        ]

        engine = BodySignalEngine(
            hrv_analyzer=mock_hrv_analyzer,
            fatigue_assessor=mock_fatigue_assessor,
            recovery_monitor=mock_recovery_monitor,
        )

        alerts = engine.check_alerts()

        overtraining_alerts = [a for a in alerts if a.alert_type == "overtraining"]
        assert len(overtraining_alerts) == 1
        assert overtraining_alerts[0].severity == "critical"

    def test_merge_recovery_status(
        self, mock_hrv_analyzer, mock_fatigue_assessor, mock_recovery_monitor
    ):
        """测试恢复状态合并"""
        engine = BodySignalEngine(
            hrv_analyzer=mock_hrv_analyzer,
            fatigue_assessor=mock_fatigue_assessor,
            recovery_monitor=mock_recovery_monitor,
        )

        assert (
            engine._merge_recovery_status(RecoveryStatus.GREEN, RecoveryStatus.YELLOW)
            == RecoveryStatus.YELLOW
        )
        assert (
            engine._merge_recovery_status(RecoveryStatus.YELLOW, RecoveryStatus.RED)
            == RecoveryStatus.RED
        )
        assert (
            engine._merge_recovery_status(RecoveryStatus.GREEN, RecoveryStatus.GREEN)
            == RecoveryStatus.GREEN
        )

    def test_merge_data_quality(
        self, mock_hrv_analyzer, mock_fatigue_assessor, mock_recovery_monitor
    ):
        """测试数据质量合并"""
        engine = BodySignalEngine(
            hrv_analyzer=mock_hrv_analyzer,
            fatigue_assessor=mock_fatigue_assessor,
            recovery_monitor=mock_recovery_monitor,
        )

        assert (
            engine._merge_data_quality(DataQuality.SUFFICIENT, DataQuality.INSUFFICIENT)
            == DataQuality.INSUFFICIENT
        )
        assert (
            engine._merge_data_quality(DataQuality.SUFFICIENT, DataQuality.EMPTY)
            == DataQuality.EMPTY
        )
        assert (
            engine._merge_data_quality(DataQuality.SUFFICIENT, DataQuality.SUFFICIENT)
            == DataQuality.SUFFICIENT
        )

    def test_status_to_emoji(
        self, mock_hrv_analyzer, mock_fatigue_assessor, mock_recovery_monitor
    ):
        """测试状态转emoji"""
        engine = BodySignalEngine(
            hrv_analyzer=mock_hrv_analyzer,
            fatigue_assessor=mock_fatigue_assessor,
            recovery_monitor=mock_recovery_monitor,
        )

        assert engine._status_to_emoji(RecoveryStatus.GREEN) == "🟢"
        assert engine._status_to_emoji(RecoveryStatus.YELLOW) == "🟡"
        assert engine._status_to_emoji(RecoveryStatus.RED) == "🔴"

    def test_generate_training_advice_critical(
        self, mock_hrv_analyzer, mock_fatigue_assessor, mock_recovery_monitor
    ):
        """测试严重预警时的建议"""
        engine = BodySignalEngine(
            hrv_analyzer=mock_hrv_analyzer,
            fatigue_assessor=mock_fatigue_assessor,
            recovery_monitor=mock_recovery_monitor,
        )

        alerts = [BodySignalAlert("overtraining", "critical", "持续过度训练", {})]
        advice = engine._generate_training_advice(RecoveryStatus.GREEN, 20.0, alerts)

        assert "⚠️" in advice
        assert "完全休息" in advice
