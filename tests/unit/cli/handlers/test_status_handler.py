from unittest.mock import MagicMock

import pytest

from src.cli.handlers.status_handler import StatusHandler
from src.core.body_signal.models import DataQuality
from src.core.models.recovery import RecoveryStatus


@pytest.fixture
def mock_context():
    """创建 Mock 应用上下文"""
    context = MagicMock()
    context.session_repo = MagicMock()
    context.body_signal_engine = MagicMock()
    return context


@pytest.fixture
def mock_body_signal_summary():
    """创建 Mock 身体信号摘要"""
    summary = MagicMock()
    summary.to_dict.return_value = {
        "recovery_status": RecoveryStatus.GREEN.value,
        "fatigue_score": 25.0,
        "data_quality": DataQuality.SUFFICIENT.value,
        "daily_summary": "状态良好",
        "training_advice": "今天适合质量课训练",
        "alerts": [],
    }
    return summary


class TestStatusHandler:
    """StatusHandler 单元测试"""

    def test_init_with_context(self, mock_context):
        """测试使用自定义上下文初始化"""
        handler = StatusHandler(context=mock_context)
        assert handler.context == mock_context

    def test_get_today_status(self, mock_context, mock_body_signal_summary):
        """测试获取今日身体状态"""
        mock_context.body_signal_engine.get_daily_summary.return_value = (
            mock_body_signal_summary
        )

        handler = StatusHandler(context=mock_context)
        result = handler.get_today_status()

        assert result["recovery_status"] == RecoveryStatus.GREEN.value
        assert result["fatigue_score"] == 25.0
        assert result["data_quality"] == DataQuality.SUFFICIENT.value
        assert result["daily_summary"] == "状态良好"
        mock_context.body_signal_engine.get_daily_summary.assert_called_once()

    def test_get_weekly_status(self, mock_context, mock_body_signal_summary):
        """测试获取本周身体状态"""
        mock_context.body_signal_engine.get_weekly_summary.return_value = (
            mock_body_signal_summary
        )

        handler = StatusHandler(context=mock_context)
        result = handler.get_weekly_status()

        assert result["recovery_status"] == RecoveryStatus.GREEN.value
        assert result["fatigue_score"] == 25.0
        mock_context.body_signal_engine.get_weekly_summary.assert_called_once()

    def test_get_today_status_with_alerts(self, mock_context):
        """测试获取今日状态包含预警信息"""
        summary_with_alerts = MagicMock()
        summary_with_alerts.to_dict.return_value = {
            "recovery_status": RecoveryStatus.RED.value,
            "fatigue_score": 85.0,
            "data_quality": DataQuality.SUFFICIENT.value,
            "daily_summary": "疲劳累积警告",
            "training_advice": "建议休息",
            "alerts": [
                {
                    "alert_type": "fatigue",
                    "severity": "critical",
                    "message": "疲劳度过高",
                }
            ],
        }

        mock_context.body_signal_engine.get_daily_summary.return_value = (
            summary_with_alerts
        )

        handler = StatusHandler(context=mock_context)
        result = handler.get_today_status()

        assert result["recovery_status"] == RecoveryStatus.RED.value
        assert result["fatigue_score"] == 85.0
        assert len(result["alerts"]) == 1
        assert result["alerts"][0]["severity"] == "critical"
