# RunnerTools 身体信号方法单元测试
# v0.19.0 新增

from unittest.mock import MagicMock, patch

import pytest

from src.agents.tools import (
    TOOL_DESCRIPTIONS,
    CompareTrainingPeriodsTool,
    GetBodySignalSummaryTool,
    GetFatigueScoreTool,
    GetHrRecoveryTool,
    GetHrvAnalysisTool,
    GetRecoveryStatusTool,
    RunnerTools,
)
from src.core.body_signal.models import DataQuality
from src.core.models.recovery import RecoveryStatus


@pytest.fixture
def mock_context():
    """创建 Mock 应用上下文"""
    context = MagicMock()
    context.storage = MagicMock()
    context.analytics = MagicMock()
    context.profile_storage = MagicMock()
    context.session_repo = MagicMock()
    return context


@pytest.fixture
def runner_tools(mock_context):
    """创建 RunnerTools 实例"""
    return RunnerTools(context=mock_context)


class TestRunnerToolsBodySignal:
    """RunnerTools 身体信号方法单元测试"""

    @patch("src.core.body_signal.hrv_analyzer.HRVAnalyzer")
    @patch("src.core.storage.session_repository.SessionRepository")
    def test_get_hrv_analysis_success(self, mock_sr_cls, mock_hrv_cls, runner_tools):
        """测试获取HRV分析成功"""
        mock_hrv_result = MagicMock()
        mock_hrv_result.to_dict.return_value = {
            "resting_hr_trend": [],
            "data_quality": DataQuality.SUFFICIENT.value,
        }
        mock_hrv_metrics = {"estimated_rmssd": 42.0, "data_source": "hr_estimate"}

        mock_hrv_analyzer = MagicMock()
        mock_hrv_analyzer.analyze_hrv.return_value = mock_hrv_result
        mock_hrv_analyzer.estimate_hrv_metrics.return_value = mock_hrv_metrics
        mock_hrv_cls.return_value = mock_hrv_analyzer

        result = runner_tools.get_hrv_analysis(days=30)

        assert result["success"] is True
        assert "data" in result
        assert "estimated_hrv_metrics" in result["data"]

    @patch("src.core.body_signal.hrv_analyzer.HRVAnalyzer")
    @patch("src.core.storage.session_repository.SessionRepository")
    def test_get_hrv_analysis_error(self, mock_sr_cls, mock_hrv_cls, runner_tools):
        """测试获取HRV分析异常"""
        mock_hrv_cls.side_effect = Exception("数据库错误")

        result = runner_tools.get_hrv_analysis(days=30)

        assert result["success"] is False
        assert "error" in result

    @patch("src.core.body_signal.hrv_analyzer.HRVAnalyzer")
    @patch("src.core.storage.session_repository.SessionRepository")
    def test_get_hr_recovery_success(self, mock_sr_cls, mock_hrv_cls, runner_tools):
        """测试获取心率恢复分析成功"""
        mock_recovery_result = MagicMock()
        mock_recovery_result.to_dict.return_value = {
            "hr_end": 165.0,
            "hr_recovery_1min": 25.0,
            "data_quality": DataQuality.SUFFICIENT.value,
        }

        mock_hrv_analyzer = MagicMock()
        mock_hrv_analyzer.analyze_hr_recovery.return_value = mock_recovery_result
        mock_hrv_cls.return_value = mock_hrv_analyzer

        result = runner_tools.get_hr_recovery()

        assert result["success"] is True
        assert result["data"]["hr_end"] == 165.0

    @patch("src.core.body_signal.fatigue_assessor.FatigueAssessor")
    @patch("src.core.calculators.training_load_analyzer.TrainingLoadAnalyzer")
    @patch("src.core.storage.session_repository.SessionRepository")
    def test_get_fatigue_score_success(
        self, mock_sr_cls, mock_tla_cls, mock_fatigue_cls, runner_tools
    ):
        """测试获取疲劳度评估成功"""
        mock_fatigue_result = MagicMock()
        mock_fatigue_result.to_dict.return_value = {
            "fatigue_score": 45.0,
            "recovery_status": RecoveryStatus.YELLOW.value,
            "consecutive_hard_days": 2,
            "recommendation": "注意休息",
            "data_quality": DataQuality.SUFFICIENT.value,
        }

        mock_fatigue_assessor = MagicMock()
        mock_fatigue_assessor.assess_fatigue.return_value = mock_fatigue_result
        mock_fatigue_cls.return_value = mock_fatigue_assessor

        result = runner_tools.get_fatigue_score(rpe=7)

        assert result["success"] is True
        assert result["data"]["fatigue_score"] == 45.0

    @patch("src.core.body_signal.recovery_monitor.RecoveryMonitor")
    @patch("src.core.body_signal.hrv_analyzer.HRVAnalyzer")
    @patch("src.core.calculators.training_load_analyzer.TrainingLoadAnalyzer")
    @patch("src.core.storage.session_repository.SessionRepository")
    def test_get_recovery_status_success(
        self, mock_sr_cls, mock_tla_cls, mock_hrv_cls, mock_recovery_cls, runner_tools
    ):
        """测试获取恢复状态成功"""
        mock_recovery_result = MagicMock()
        mock_recovery_result.to_dict.return_value = {
            "recovery_status": RecoveryStatus.GREEN.value,
            "rest_day_effect": {"effect_level": "good"},
            "data_quality": DataQuality.SUFFICIENT.value,
        }

        mock_recovery_monitor = MagicMock()
        mock_recovery_monitor.get_recovery_status.return_value = mock_recovery_result
        mock_recovery_cls.return_value = mock_recovery_monitor

        result = runner_tools.get_recovery_status()

        assert result["success"] is True
        assert result["data"]["recovery_status"] == RecoveryStatus.GREEN.value

    @patch("src.core.body_signal.BodySignalEngine")
    @patch("src.core.body_signal.recovery_monitor.RecoveryMonitor")
    @patch("src.core.body_signal.fatigue_assessor.FatigueAssessor")
    @patch("src.core.body_signal.hrv_analyzer.HRVAnalyzer")
    @patch("src.core.calculators.training_load_analyzer.TrainingLoadAnalyzer")
    @patch("src.core.storage.session_repository.SessionRepository")
    def test_get_body_signal_summary_daily(
        self,
        mock_sr_cls,
        mock_tla_cls,
        mock_hrv_cls,
        mock_fatigue_cls,
        mock_recovery_cls,
        mock_engine_cls,
        runner_tools,
    ):
        """测试获取每日身体信号摘要"""
        mock_summary = MagicMock()
        mock_summary.to_dict.return_value = {
            "recovery_status": RecoveryStatus.GREEN.value,
            "fatigue_score": 20.0,
            "data_quality": DataQuality.SUFFICIENT.value,
        }

        mock_engine = MagicMock()
        mock_engine.get_daily_summary.return_value = mock_summary
        mock_engine_cls.return_value = mock_engine

        result = runner_tools.get_body_signal_summary(period="daily")

        assert result["success"] is True
        mock_engine.get_daily_summary.assert_called_once()

    @patch("src.core.body_signal.BodySignalEngine")
    @patch("src.core.body_signal.recovery_monitor.RecoveryMonitor")
    @patch("src.core.body_signal.fatigue_assessor.FatigueAssessor")
    @patch("src.core.body_signal.hrv_analyzer.HRVAnalyzer")
    @patch("src.core.calculators.training_load_analyzer.TrainingLoadAnalyzer")
    @patch("src.core.storage.session_repository.SessionRepository")
    def test_get_body_signal_summary_weekly(
        self,
        mock_sr_cls,
        mock_tla_cls,
        mock_hrv_cls,
        mock_fatigue_cls,
        mock_recovery_cls,
        mock_engine_cls,
        runner_tools,
    ):
        """测试获取每周身体信号摘要"""
        mock_summary = MagicMock()
        mock_summary.to_dict.return_value = {
            "recovery_status": RecoveryStatus.GREEN.value,
            "fatigue_score": 25.0,
            "data_quality": DataQuality.SUFFICIENT.value,
        }

        mock_engine = MagicMock()
        mock_engine.get_weekly_summary.return_value = mock_summary
        mock_engine_cls.return_value = mock_engine

        result = runner_tools.get_body_signal_summary(period="weekly")

        assert result["success"] is True
        mock_engine.get_weekly_summary.assert_called_once()

    @patch("src.core.body_signal.recovery_monitor.RecoveryMonitor")
    @patch("src.core.body_signal.hrv_analyzer.HRVAnalyzer")
    @patch("src.core.calculators.training_load_analyzer.TrainingLoadAnalyzer")
    @patch("src.core.storage.session_repository.SessionRepository")
    def test_compare_training_periods_success(
        self, mock_sr_cls, mock_tla_cls, mock_hrv_cls, mock_recovery_cls, runner_tools
    ):
        """测试对比训练周期成功"""
        from src.core.body_signal.models import RecoveryPoint

        mock_recovery_monitor = MagicMock()
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

        result = runner_tools.compare_training_periods(period1_days=2, period2_days=2)

        assert result["success"] is True
        assert result["data"]["period1"]["avg_tsb"] == 9.0
        assert result["data"]["period2"]["avg_tsb"] == 4.0
        assert result["data"]["tsb_change"] == 5.0


class TestBodySignalToolSchemas:
    """身体信号工具 Schema 测试"""

    def test_hrv_analysis_tool_schema(self):
        """测试HRV分析工具Schema"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = GetHrvAnalysisTool(runner_tools)

            assert tool.name == "get_hrv_analysis"
            schema = tool.to_schema()
            assert schema["function"]["name"] == "get_hrv_analysis"
            assert "days" in schema["function"]["parameters"]["properties"]

    def test_hr_recovery_tool_schema(self):
        """测试心率恢复工具Schema"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = GetHrRecoveryTool(runner_tools)

            assert tool.name == "get_hr_recovery"
            schema = tool.to_schema()
            assert schema["function"]["name"] == "get_hr_recovery"

    def test_fatigue_score_tool_schema(self):
        """测试疲劳度工具Schema"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = GetFatigueScoreTool(runner_tools)

            assert tool.name == "get_fatigue_score"
            schema = tool.to_schema()
            assert "rpe" in schema["function"]["parameters"]["properties"]

    def test_recovery_status_tool_schema(self):
        """测试恢复状态工具Schema"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = GetRecoveryStatusTool(runner_tools)

            assert tool.name == "get_recovery_status"

    def test_body_signal_summary_tool_schema(self):
        """测试身体信号摘要工具Schema"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = GetBodySignalSummaryTool(runner_tools)

            assert tool.name == "get_body_signal_summary"
            schema = tool.to_schema()
            assert "period" in schema["function"]["parameters"]["properties"]

    def test_compare_training_periods_tool_schema(self):
        """测试训练周期对比工具Schema"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = CompareTrainingPeriodsTool(runner_tools)

            assert tool.name == "compare_training_periods"
            schema = tool.to_schema()
            assert "period1_days" in schema["function"]["parameters"]["properties"]
            assert "period2_days" in schema["function"]["parameters"]["properties"]


class TestToolDescriptionsBodySignal:
    """TOOL_DESCRIPTIONS 身体信号条目测试"""

    def test_hrv_analysis_description_exists(self):
        """测试HRV分析描述存在"""
        assert "get_hrv_analysis" in TOOL_DESCRIPTIONS
        assert "description" in TOOL_DESCRIPTIONS["get_hrv_analysis"]

    def test_hr_recovery_description_exists(self):
        """测试心率恢复描述存在"""
        assert "get_hr_recovery" in TOOL_DESCRIPTIONS

    def test_fatigue_score_description_exists(self):
        """测试疲劳度描述存在"""
        assert "get_fatigue_score" in TOOL_DESCRIPTIONS

    def test_recovery_status_description_exists(self):
        """测试恢复状态描述存在"""
        assert "get_recovery_status" in TOOL_DESCRIPTIONS

    def test_body_signal_summary_description_exists(self):
        """测试身体信号摘要描述存在"""
        assert "get_body_signal_summary" in TOOL_DESCRIPTIONS

    def test_compare_training_periods_description_exists(self):
        """测试训练周期对比描述存在"""
        assert "compare_training_periods" in TOOL_DESCRIPTIONS
