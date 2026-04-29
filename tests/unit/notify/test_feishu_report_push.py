# 飞书报告推送单元测试
# 测试周报和月报的推送功能

from unittest.mock import MagicMock

import pytest

from src.core.models import OperationResult, ReportType
from src.core.report.service import ReportService
from tests.conftest import create_mock_context


class TestReportType:
    """测试 ReportType 枚举"""

    def test_report_type_values(self):
        """测试报告类型枚举值"""
        assert ReportType.DAILY.value == "daily"
        assert ReportType.WEEKLY.value == "weekly"
        assert ReportType.MONTHLY.value == "monthly"

    def test_report_type_from_string(self):
        """测试从字符串创建报告类型"""
        assert ReportType("daily") == ReportType.DAILY
        assert ReportType("weekly") == ReportType.WEEKLY
        assert ReportType("monthly") == ReportType.MONTHLY


class TestReportServiceWeeklyReport:
    """测试周报生成"""

    @pytest.fixture
    def mock_service(self):
        """创建 Mock 服务"""
        context = create_mock_context()
        return ReportService(context)

    def test_generate_weekly_report_success(self, mock_service):
        """测试成功生成周报"""
        # Mock 存储查询返回空数据
        mock_service.storage.query_by_date_range.return_value = []
        mock_service.analytics.get_training_load.return_value = {
            "atl": 10,
            "ctl": 20,
            "tsb": 10,
        }

        result = mock_service.generate_report(report_type=ReportType.WEEKLY)

        assert result.type == "weekly"
        assert hasattr(result, "date_range")
        assert hasattr(result, "greeting")
        assert hasattr(result, "total_runs")
        assert hasattr(result, "highlights")
        assert hasattr(result, "concerns")
        assert hasattr(result, "recommendations")

    def test_generate_weekly_report_with_data(self, mock_service):
        """测试使用真实数据生成周报"""
        mock_runs = [
            {
                "session_total_distance": 10000,
                "session_total_timer_time": 3000,
                "session_avg_heart_rate": 150,
            },
            {
                "session_total_distance": 15000,
                "session_total_timer_time": 4500,
                "session_avg_heart_rate": 155,
            },
        ]
        mock_service.storage.query_by_date_range.return_value = mock_runs
        mock_service.analytics.get_training_load.return_value = {
            "atl": 30,
            "ctl": 50,
            "tsb": 20,
        }
        mock_service.analytics.calculate_vdot.return_value = 45.5
        mock_service.analytics.calculate_tss_for_run.return_value = 50.0

        result = mock_service.generate_report(report_type=ReportType.WEEKLY)

        assert result.total_runs == 2
        assert result.total_distance_km > 0
        assert result.total_tss > 0

    def test_generate_weekly_report_highlights(self, mock_service):
        """测试周报亮点识别"""
        mock_runs = [
            {"session_total_distance": 21000, "session_total_timer_time": 3600},
            {"session_total_distance": 10000, "session_total_timer_time": 1800},
            {"session_total_distance": 12000, "session_total_timer_time": 2400},
        ]
        mock_service.storage.query_by_date_range.return_value = mock_runs
        mock_service.analytics.get_training_load.return_value = {}
        mock_service.analytics.calculate_vdot.return_value = 50.0

        highlights = mock_service._identify_weekly_highlights(mock_runs, 43000.0)

        assert len(highlights) > 0
        assert any("最长距离" in h for h in highlights)

    def test_generate_weekly_report_concerns_no_runs(self, mock_service):
        """测试周报关注点 - 无训练记录"""
        concerns = mock_service._identify_weekly_concerns([], 0.0)

        assert len(concerns) > 0
        assert "无训练记录" in concerns[0]

    def test_generate_weekly_report_concerns_low_frequency(self, mock_service):
        """测试周报关注点 - 训练频率低"""
        mock_runs = [{"session_total_distance": 5000, "session_total_timer_time": 1200}]
        concerns = mock_service._identify_weekly_concerns(mock_runs, 30.0)

        assert any("训练频率较低" in c for c in concerns)

    def test_generate_weekly_report_concerns_high_tss(self, mock_service):
        """测试周报关注点 - TSS 过高"""
        mock_runs = [
            {"session_total_distance": 10000, "session_total_timer_time": 3600},
            {"session_total_distance": 10000, "session_total_timer_time": 3600},
        ]
        concerns = mock_service._identify_weekly_concerns(mock_runs, 480.0)

        assert any("TSS 较高" in c for c in concerns)

    def test_generate_weekly_report_recommendations(self, mock_service):
        """测试周报建议生成"""
        training_load = {"atl": 40, "ctl": 30, "tsb": -25}
        recommendations = mock_service._generate_weekly_recommendations(
            [], training_load
        )

        assert len(recommendations) > 0
        assert any("疲劳累积" in r for r in recommendations)

    def test_generate_weekly_report_recommendations_good_status(self, mock_service):
        """测试周报建议 - 状态良好"""
        training_load = {"atl": 20, "ctl": 80, "tsb": 35}
        recommendations = mock_service._generate_weekly_recommendations(
            [], training_load
        )

        assert any("状态良好" in r for r in recommendations)


class TestReportServiceMonthlyReport:
    """测试月报生成"""

    @pytest.fixture
    def mock_service(self):
        """创建 Mock 服务"""
        context = create_mock_context()
        return ReportService(context)

    def test_generate_monthly_report_success(self, mock_service):
        """测试成功生成月报"""
        mock_service.storage.query_by_date_range.return_value = []
        mock_service.analytics.get_training_load.return_value = {}

        result = mock_service.generate_report(report_type=ReportType.MONTHLY)

        assert result.type == "monthly"
        assert hasattr(result, "month")
        assert hasattr(result, "greeting")
        assert hasattr(result, "total_runs")
        assert hasattr(result, "avg_weekly_distance_km")

    def test_generate_monthly_report_highlights(self, mock_service):
        """测试月报亮点识别"""
        mock_runs = [
            {"session_total_distance": 25000, "session_total_timer_time": 5400},
            {"session_total_distance": 20000, "session_total_timer_time": 4200},
        ] * 6

        total_distance = 270000.0
        max_distance = 25000.0
        highlights = mock_service._identify_monthly_highlights(
            mock_runs, total_distance, max_distance
        )

        assert len(highlights) > 0
        assert any("月跑量突破" in h for h in highlights)
        assert any("训练频率优秀" in h for h in highlights)

    def test_generate_monthly_report_concerns_no_runs(self, mock_service):
        """测试月报关注点 - 无训练记录"""
        concerns = mock_service._identify_monthly_concerns([], 0.0)

        assert len(concerns) > 0
        assert "无训练记录" in concerns[0]

    def test_generate_monthly_report_recommendations(self, mock_service):
        """测试月报建议生成"""
        training_load = {"ctl": 40, "tsb": -35}
        recommendations = mock_service._generate_monthly_recommendations(
            [], training_load
        )

        assert len(recommendations) > 0
        assert any("疲劳累积" in r for r in recommendations)


class TestReportServicePush:
    """测试报告推送"""

    @pytest.fixture
    def mock_service_with_feishu(self):
        """创建带飞书的 Mock 服务"""
        context = create_mock_context()
        service = ReportService(context)
        # 在创建服务后设置feishu mock
        service.feishu = MagicMock()
        service.feishu.webhook = "https://test.webhook.com"
        service.feishu.send_card.return_value = OperationResult(success=True)
        service.feishu.auth.is_configured.return_value = True
        service.feishu.receive_id = "test_user"
        return service

    def test_push_daily_report(self, mock_service_with_feishu):
        """测试推送晨报"""
        report_data = {
            "date": "2024-01-01",
            "greeting": "早上好",
            "yesterday_run": {"distance_km": 10, "duration_min": 60, "tss": 50},
            "fitness_status": {"atl": 10, "ctl": 20, "tsb": 10, "status": "良好"},
            "training_advice": "保持训练",
        }

        result = mock_service_with_feishu.push_report(
            report_data, report_type=ReportType.DAILY
        )

        assert result.success is True
        mock_service_with_feishu.feishu.send_card.assert_called_once()

    def test_push_weekly_report(self, mock_service_with_feishu):
        """测试推送周报"""
        report_data = {
            "greeting": "本周总结",
            "total_runs": 3,
            "total_distance_km": 30.5,
            "total_tss": 150,
            "highlights": ["亮点 1"],
            "concerns": ["关注点 1"],
            "recommendations": ["建议 1"],
        }

        result = mock_service_with_feishu.push_report(
            report_data, report_type=ReportType.WEEKLY
        )

        assert result.success is True
        call_args = mock_service_with_feishu.feishu.send_card.call_args
        assert "每周跑步总结" in call_args[0][0]

    def test_push_monthly_report(self, mock_service_with_feishu):
        """测试推送月报"""
        report_data = {
            "greeting": "本月总结",
            "total_runs": 12,
            "total_distance_km": 120.5,
            "total_tss": 600,
            "highlights": ["亮点 1"],
            "concerns": ["关注点 1"],
            "recommendations": ["建议 1"],
        }

        result = mock_service_with_feishu.push_report(
            report_data, report_type=ReportType.MONTHLY
        )

        assert result.success is True
        call_args = mock_service_with_feishu.feishu.send_card.call_args
        assert "每月跑步总结" in call_args[0][0]

    def test_push_report_no_feishu_config(self):
        """测试无飞书配置时推送失败"""
        context = create_mock_context()
        service = ReportService(context)
        # 设置feishu mock为未配置状态
        service.feishu = MagicMock()
        service.feishu.auth.is_configured.return_value = False

        result = service.push_report({}, report_type=ReportType.DAILY)

        assert result.success is False
        assert "未配置" in result.error


class TestReportServiceSchedule:
    """测试定时推送配置"""

    @pytest.fixture
    def mock_service(self):
        """创建 Mock 服务"""
        context = create_mock_context()
        return ReportService(context)

    def test_schedule_daily_report(self, mock_service):
        """测试配置晨报定时推送"""
        result = mock_service.schedule_report(
            time_str="07:00",
            push=True,
            age=30,
            report_type=ReportType.DAILY,
        )

        assert result.success is True
        assert "daily" in result.message

    def test_schedule_weekly_report(self, mock_service):
        """测试配置周报定时推送"""
        result = mock_service.schedule_report(
            time_str="09:00",
            push=True,
            age=30,
            report_type=ReportType.WEEKLY,
        )

        assert result.success is True
        assert "weekly" in result.message

    def test_schedule_monthly_report(self, mock_service):
        """测试配置月报定时推送"""
        result = mock_service.schedule_report(
            time_str="10:00",
            push=True,
            age=30,
            report_type=ReportType.MONTHLY,
        )

        assert result.success is True
        assert "monthly" in result.message

    def test_schedule_invalid_time(self, mock_service):
        """测试无效时间格式"""
        result = mock_service.schedule_report(
            time_str="25:00",
            report_type=ReportType.DAILY,
        )

        assert result.success is False
        assert "时间格式无效" in result.error

    def test_get_job_name(self, mock_service):
        """测试获取任务名称"""
        assert (
            mock_service._get_job_name(ReportType.DAILY) == mock_service.JOB_NAME_DAILY
        )
        assert (
            mock_service._get_job_name(ReportType.WEEKLY)
            == mock_service.JOB_NAME_WEEKLY
        )
        assert (
            mock_service._get_job_name(ReportType.MONTHLY)
            == mock_service.JOB_NAME_MONTHLY
        )


class TestReportServiceFormat:
    """测试报告格式化"""

    @pytest.fixture
    def mock_service(self):
        """创建 Mock 服务"""
        context = create_mock_context()
        return ReportService(context)

    def test_format_daily_report_content(self, mock_service):
        """测试晨报格式化"""
        report_data = {
            "date": "2024-01-01",
            "greeting": "早上好",
            "yesterday_run": {"distance_km": 10, "duration_min": 60, "tss": 50},
            "fitness_status": {"atl": 10, "ctl": 20, "tsb": 10, "status": "良好"},
            "training_advice": "保持训练",
        }

        content = mock_service._format_report_content(report_data)

        assert "昨日训练" in content
        assert "体能状态" in content
        assert "今日建议" in content

    def test_format_weekly_report_content(self, mock_service):
        """测试周报格式化"""
        report_data = {
            "greeting": "本周总结",
            "total_runs": 3,
            "total_distance_km": 30.5,
            "highlights": ["亮点 1", "亮点 2"],
            "concerns": ["关注点 1"],
            "recommendations": ["建议 1"],
        }

        content = mock_service._format_weekly_report_content(report_data)

        assert "训练统计" in content
        assert "亮点" in content
        assert any("亮点 1" in content for _ in [1])
        assert "建议" in content

    def test_format_monthly_report_content(self, mock_service):
        """测试月报格式化"""
        report_data = {
            "greeting": "本月总结",
            "total_runs": 12,
            "total_distance_km": 120.5,
            "avg_weekly_distance_km": 30.0,
            "highlights": ["月跑量突破"],
            "recommendations": ["建议 1"],
        }

        content = mock_service._format_monthly_report_content(report_data)

        assert "训练统计" in content
        assert "周均距离" in content
        assert "亮点" in content


class TestReportServiceRunReportNow:
    """测试立即生成报告"""

    @pytest.fixture
    def mock_service_with_feishu(self):
        """创建带飞书的 Mock 服务"""
        context = create_mock_context()
        context.analytics.generate_daily_report.return_value = {
            "date": "2024-01-01",
            "greeting": "早上好",
        }
        service = ReportService(context)
        # 在创建服务后设置feishu mock
        service.feishu = MagicMock()
        service.feishu.webhook = "https://test.webhook.com"
        service.feishu.send_card.return_value = OperationResult(success=True)
        service.feishu.auth.is_configured.return_value = True
        service.feishu.receive_id = "test_user"
        return service

    def test_run_daily_report_now(self, mock_service_with_feishu):
        """测试立即生成晨报"""
        result = mock_service_with_feishu.run_report_now(
            push=False, age=30, report_type=ReportType.DAILY
        )

        assert result["success"] is True
        assert "report" in result

    def test_run_weekly_report_now(self, mock_service_with_feishu):
        """测试立即生成周报"""
        mock_service_with_feishu.storage.query_by_date_range.return_value = []
        mock_service_with_feishu.analytics.get_training_load.return_value = {}

        result = mock_service_with_feishu.run_report_now(
            push=False, report_type=ReportType.WEEKLY
        )

        assert result["success"] is True
        assert "report" in result
        assert result["report"]["type"] == "weekly"

    def test_run_monthly_report_now(self, mock_service_with_feishu):
        """测试立即生成月报"""
        mock_service_with_feishu.storage.query_by_date_range.return_value = []
        mock_service_with_feishu.analytics.get_training_load.return_value = {}

        result = mock_service_with_feishu.run_report_now(
            push=False, report_type=ReportType.MONTHLY
        )

        assert result["success"] is True
        assert "report" in result
        assert result["report"]["type"] == "monthly"


if __name__ == "__main__":
    pytest.main(
        [
            __file__,
            "-v",
            "--cov=src.core.report_service",
            "--cov-report=term-missing",
            "--cov-report=html",
        ]
    )
