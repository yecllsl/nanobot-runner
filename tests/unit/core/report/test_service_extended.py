from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

from src.core.models import (
    MonthlyReportData,
    OperationResult,
    ReportType,
    WeeklyReportData,
)
from src.core.report.service import ReportService
from src.core.visualization.models import ChartData
from tests.conftest import create_mock_context


def _make_service_with_runs(runs=None, training_load=None):
    context = create_mock_context()
    service = ReportService(context)
    if runs is not None:
        service.storage.query_by_date_range.return_value = runs
    if training_load is not None:
        service.analytics.get_training_load.return_value = training_load
    else:
        service.analytics.get_training_load.return_value = {
            "atl": 45.0,
            "ctl": 65.0,
            "tsb": 20.0,
        }
    service.analytics.calculate_tss_for_run.return_value = 80.0
    service.analytics.calculate_vdot.return_value = 45.0
    return service


class TestReportServiceWeeklyHighlights:
    def test_highlights_with_runs(self):
        service = _make_service_with_runs()
        runs = [
            {"session_total_distance": 21000, "session_total_timer_time": 6300},
            {"session_total_distance": 10000, "session_total_timer_time": 3000},
            {"session_total_distance": 5000, "session_total_timer_time": 1500},
        ]
        highlights = service._identify_weekly_highlights(runs, 36000)
        assert len(highlights) > 0
        assert any("最长距离" in h for h in highlights)

    def test_highlights_no_runs(self):
        service = _make_service_with_runs()
        highlights = service._identify_weekly_highlights([], 0)
        assert highlights == []

    def test_highlights_frequent_training(self):
        service = _make_service_with_runs()
        runs = [
            {"session_total_distance": 5000, "session_total_timer_time": 1500},
        ] * 4
        highlights = service._identify_weekly_highlights(runs, 20000)
        assert any("训练频率" in h for h in highlights)


class TestReportServiceWeeklyConcerns:
    def test_concerns_no_runs(self):
        service = _make_service_with_runs()
        concerns = service._identify_weekly_concerns([], 0)
        assert any("无训练" in c for c in concerns)

    def test_concerns_low_frequency(self):
        service = _make_service_with_runs()
        runs = [{"session_total_distance": 5000, "session_total_timer_time": 1500}]
        concerns = service._identify_weekly_concerns(runs, 50.0)
        assert any("频率较低" in c for c in concerns)

    def test_concerns_high_tss(self):
        service = _make_service_with_runs()
        runs = [
            {"session_total_distance": 10000, "session_total_timer_time": 3000},
        ] * 3
        concerns = service._identify_weekly_concerns(runs, 450.0)
        assert any("TSS" in c for c in concerns)

    def test_concerns_normal(self):
        service = _make_service_with_runs()
        runs = [
            {"session_total_distance": 10000, "session_total_timer_time": 3000},
        ] * 3
        concerns = service._identify_weekly_concerns(runs, 200.0)
        assert len(concerns) == 0


class TestReportServiceWeeklyRecommendations:
    def test_recommendations_low_tsb(self):
        service = _make_service_with_runs(
            training_load={"atl": 60, "ctl": 35, "tsb": -25}
        )
        recs = service._generate_weekly_recommendations(
            [], {"atl": 60, "ctl": 35, "tsb": -25}
        )
        assert any("恢复" in r for r in recs)

    def test_recommendations_high_tsb(self):
        service = _make_service_with_runs(
            training_load={"atl": 30, "ctl": 65, "tsb": 35}
        )
        recs = service._generate_weekly_recommendations(
            [], {"atl": 30, "ctl": 65, "tsb": 35}
        )
        assert any("增加" in r for r in recs)

    def test_recommendations_low_ctl(self):
        service = _make_service_with_runs(
            training_load={"atl": 40, "ctl": 45, "tsb": 5}
        )
        recs = service._generate_weekly_recommendations(
            [], {"atl": 40, "ctl": 45, "tsb": 5}
        )
        assert any("LSD" in r for r in recs)

    def test_recommendations_high_ctl(self):
        service = _make_service_with_runs(
            training_load={"atl": 40, "ctl": 110, "tsb": 5}
        )
        recs = service._generate_weekly_recommendations(
            [], {"atl": 40, "ctl": 110, "tsb": 5}
        )
        assert any("间歇" in r for r in recs)


class TestReportServiceMonthlyHighlights:
    def test_highlights_high_volume(self):
        service = _make_service_with_runs()
        runs = [{"session_total_distance": 10000}] * 12
        highlights = service._identify_monthly_highlights(runs, 120000, 21000)
        assert any("月跑量" in h for h in highlights)

    def test_highlights_frequent(self):
        service = _make_service_with_runs()
        runs = [{"session_total_distance": 5000}] * 15
        highlights = service._identify_monthly_highlights(runs, 75000, 5000)
        assert any("频率" in h for h in highlights)

    def test_highlights_long_distance(self):
        service = _make_service_with_runs()
        runs = [{"session_total_distance": 25000}] * 5
        highlights = service._identify_monthly_highlights(runs, 125000, 25000)
        assert any("长距离" in h for h in highlights)

    def test_highlights_no_runs(self):
        service = _make_service_with_runs()
        highlights = service._identify_monthly_highlights([], 0, 0)
        assert highlights == []


class TestReportServiceMonthlyConcerns:
    def test_concerns_no_runs(self):
        service = _make_service_with_runs()
        concerns = service._identify_monthly_concerns([], 0)
        assert any("无训练" in c for c in concerns)

    def test_concerns_low_frequency(self):
        service = _make_service_with_runs()
        runs = [{"session_total_distance": 5000}]
        concerns = service._identify_monthly_concerns(runs, 50.0)
        assert any("频率较低" in c for c in concerns)

    def test_concerns_high_tss(self):
        service = _make_service_with_runs()
        runs = [{"session_total_distance": 5000}] * 10
        concerns = service._identify_monthly_concerns(runs, 1500.0)
        assert any("TSS" in c for c in concerns)


class TestReportServiceMonthlyRecommendations:
    def test_recommendations_low_tsb(self):
        service = _make_service_with_runs()
        recs = service._generate_monthly_recommendations(
            [], {"atl": 60, "ctl": 25, "tsb": -35}
        )
        assert any("恢复" in r for r in recs)

    def test_recommendations_high_tsb(self):
        service = _make_service_with_runs()
        recs = service._generate_monthly_recommendations(
            [], {"atl": 30, "ctl": 65, "tsb": 25}
        )
        assert any("提升" in r for r in recs)

    def test_recommendations_low_ctl(self):
        service = _make_service_with_runs()
        recs = service._generate_monthly_recommendations(
            [], {"atl": 40, "ctl": 50, "tsb": 10}
        )
        assert any("有氧" in r for r in recs)

    def test_recommendations_mid_ctl(self):
        service = _make_service_with_runs()
        recs = service._generate_monthly_recommendations(
            [], {"atl": 40, "ctl": 80, "tsb": 10}
        )
        assert any("乳酸阈值" in r for r in recs)

    def test_recommendations_high_ctl(self):
        service = _make_service_with_runs()
        recs = service._generate_monthly_recommendations(
            [], {"atl": 40, "ctl": 110, "tsb": 10}
        )
        assert any("间歇" in r for r in recs)


class TestReportServiceFormatContent:
    def test_format_daily_report_content(self):
        service = _make_service_with_runs()
        data = {
            "date": "2026-05-08",
            "greeting": "今日训练总结",
            "yesterday_run": {
                "distance_km": 10.5,
                "duration_min": 60,
                "tss": 85,
            },
            "fitness_status": {"atl": 45, "ctl": 65, "tsb": 20, "status": "良好"},
            "training_advice": "保持训练",
        }
        content = service._format_report_content(data)
        assert "2026-05-08" in content
        assert "10.5" in content
        assert "保持训练" in content

    def test_format_daily_report_no_yesterday_run(self):
        service = _make_service_with_runs()
        data = {
            "date": "2026-05-08",
            "greeting": "今日训练总结",
            "yesterday_run": None,
            "fitness_status": {"atl": 45, "ctl": 65, "tsb": 20, "status": "良好"},
            "training_advice": "建议轻松跑",
        }
        content = service._format_report_content(data)
        assert "昨日训练" in content

    def test_format_weekly_report_content(self):
        service = _make_service_with_runs()
        data = {
            "greeting": "本周训练总结",
            "total_runs": 3,
            "total_distance_km": 35.5,
            "total_duration_min": 180.0,
            "total_tss": 240.0,
            "avg_vdot": 45.0,
            "highlights": ["训练量充足"],
            "concerns": [],
            "recommendations": ["继续保持"],
        }
        content = service._format_weekly_report_content(data)
        assert "35.5" in content
        assert "训练量充足" in content

    def test_format_monthly_report_content(self):
        service = _make_service_with_runs()
        data = {
            "greeting": "本月训练总结",
            "total_runs": 12,
            "total_distance_km": 150.0,
            "total_duration_min": 720.0,
            "total_tss": 960.0,
            "avg_vdot": 45.0,
            "avg_weekly_distance_km": 37.5,
            "avg_weekly_duration_min": 180.0,
            "highlights": ["月跑量突破"],
            "concerns": [],
            "recommendations": ["保持节奏"],
        }
        content = service._format_monthly_report_content(data)
        assert "150" in content
        assert "月跑量突破" in content


class TestReportServiceBuildVdotChart:
    def test_build_vdot_chart_with_data(self):
        service = _make_service_with_runs()
        runs = [
            {
                "session_total_distance": 5000,
                "session_total_timer_time": 1500,
                "session_start_time": datetime(2026, 5, 1, 8, 0),
            },
            {
                "session_total_distance": 10000,
                "session_total_timer_time": 3000,
                "session_start_time": datetime(2026, 5, 3, 8, 0),
            },
        ]
        service.analytics.calculate_vdot.return_value = 45.0
        chart = service._build_vdot_chart(runs)
        assert isinstance(chart, ChartData)
        assert chart.title == "VDOT 趋势"

    def test_build_vdot_chart_no_valid_runs(self):
        service = _make_service_with_runs()
        runs = [{"session_total_distance": 500, "session_total_timer_time": 300}]
        chart = service._build_vdot_chart(runs)
        assert isinstance(chart, ChartData)

    def test_build_vdot_chart_exception(self):
        service = _make_service_with_runs()
        service.analytics.calculate_vdot.side_effect = Exception("error")
        chart = service._build_vdot_chart([])
        assert isinstance(chart, ChartData)


class TestReportServiceBuildLoadChart:
    def test_build_load_chart_weekly(self):
        service = _make_service_with_runs()
        service.analytics.get_training_load_trend.return_value = {
            "trend_data": [
                {"date": "2026-05-01", "ctl": 65, "atl": 45, "tsb": 20},
                {"date": "2026-05-02", "ctl": 66, "atl": 46, "tsb": 20},
            ]
        }
        report = WeeklyReportData(type="weekly", date_range="05.01-05.07")
        chart = service._build_load_chart(report)
        assert isinstance(chart, ChartData)
        assert chart.title == "训练负荷状态"

    def test_build_load_chart_monthly(self):
        service = _make_service_with_runs()
        service.analytics.get_training_load_trend.return_value = {
            "trend_data": [
                {"date": "2026-05-01", "ctl": 65, "atl": 45, "tsb": 20},
            ]
        }
        report = MonthlyReportData(type="monthly", month="2026年05月")
        chart = service._build_load_chart(report)
        assert isinstance(chart, ChartData)

    def test_build_load_chart_no_trend(self):
        service = _make_service_with_runs()
        service.analytics.get_training_load_trend.return_value = {}
        report = WeeklyReportData(type="weekly", date_range="05.01-05.07")
        chart = service._build_load_chart(report)
        assert isinstance(chart, ChartData)
        assert len(chart.series) == 0

    def test_build_load_chart_exception(self):
        service = _make_service_with_runs()
        service.analytics.get_training_load_trend.side_effect = Exception("error")
        report = WeeklyReportData(type="weekly", date_range="05.01-05.07")
        chart = service._build_load_chart(report)
        assert isinstance(chart, ChartData)


class TestReportServiceBuildVolumeChart:
    def test_build_volume_chart_with_data(self):
        service = _make_service_with_runs()
        runs = [
            {
                "session_total_distance": 10000,
                "session_start_time": datetime(2026, 5, 1, 8, 0),
            },
            {
                "session_total_distance": 15000,
                "session_start_time": datetime(2026, 5, 3, 8, 0),
            },
        ]
        service.storage.query_by_date_range.return_value = runs
        report = MonthlyReportData(type="monthly", month="2026年05月")
        chart = service._build_volume_chart(report)
        assert isinstance(chart, ChartData)
        assert chart.title == "跑量趋势"

    def test_build_volume_chart_no_data(self):
        service = _make_service_with_runs()
        service.storage.query_by_date_range.return_value = []
        report = MonthlyReportData(type="monthly", month="2026年05月")
        chart = service._build_volume_chart(report)
        assert isinstance(chart, ChartData)

    def test_build_volume_chart_exception(self):
        service = _make_service_with_runs()
        service.storage.query_by_date_range.side_effect = Exception("error")
        report = MonthlyReportData(type="monthly", month="2026年05月")
        chart = service._build_volume_chart(report)
        assert isinstance(chart, ChartData)


class TestReportServiceBuildHrZonesChart:
    def test_build_hr_zones_chart_with_data(self):
        service = _make_service_with_runs()
        runs = [
            {
                "session_avg_heart_rate": 140,
                "session_total_timer_time": 1800,
            },
            {
                "session_avg_heart_rate": 165,
                "session_total_timer_time": 3600,
            },
        ]
        service.storage.query_by_date_range.return_value = runs
        report = MonthlyReportData(type="monthly", month="2026年05月")
        chart = service._build_hr_zones_chart(report)
        assert isinstance(chart, ChartData)
        assert chart.title == "心率区间分布"

    def test_build_hr_zones_chart_no_data(self):
        service = _make_service_with_runs()
        service.storage.query_by_date_range.return_value = []
        report = MonthlyReportData(type="monthly", month="2026年05月")
        chart = service._build_hr_zones_chart(report)
        assert isinstance(chart, ChartData)

    def test_build_hr_zones_chart_exception(self):
        service = _make_service_with_runs()
        service.storage.query_by_date_range.side_effect = Exception("error")
        report = MonthlyReportData(type="monthly", month="2026年05月")
        chart = service._build_hr_zones_chart(report)
        assert isinstance(chart, ChartData)


class TestReportServiceEnableSchedule:
    def test_enable_schedule_no_job(self):
        service = _make_service_with_runs()
        mock_cron = MagicMock()
        mock_cron.list_jobs.return_value = []
        service.cron_service = mock_cron
        result = service.enable_schedule(True, ReportType.DAILY)
        assert result.success is False
        assert "未找到" in result.error

    def test_enable_schedule_with_job(self):
        service = _make_service_with_runs()
        mock_job = MagicMock()
        mock_job.name = "daily_report"
        mock_job.id = "job_001"
        mock_cron = MagicMock()
        mock_cron.list_jobs.return_value = [mock_job]
        service.cron_service = mock_cron
        result = service.enable_schedule(True, ReportType.DAILY)
        assert result.success is True

    def test_enable_schedule_exception(self):
        service = _make_service_with_runs()
        mock_cron = MagicMock()
        mock_cron.list_jobs.side_effect = Exception("error")
        service.cron_service = mock_cron
        result = service.enable_schedule(True, ReportType.DAILY)
        assert result.success is False


class TestReportServiceGetScheduleStatus:
    def test_get_schedule_status_no_job(self):
        service = _make_service_with_runs()
        mock_cron = MagicMock()
        mock_cron.list_jobs.return_value = []
        service.cron_service = mock_cron
        status = service.get_schedule_status(ReportType.DAILY)
        assert status.configured is False

    def test_get_schedule_status_with_job(self):
        service = _make_service_with_runs()
        mock_job = MagicMock()
        mock_job.name = "daily_report"
        mock_job.id = "job_001"
        mock_job.enabled = True
        mock_job.message = '{"push": true, "age": 30, "time": "08:00", "type": "daily"}'
        mock_cron = MagicMock()
        mock_cron.list_jobs.return_value = [mock_job]
        service.cron_service = mock_cron
        status = service.get_schedule_status(ReportType.DAILY)
        assert status.configured is True
        assert status.enabled is True

    def test_get_schedule_status_exception(self):
        service = _make_service_with_runs()
        mock_cron = MagicMock()
        mock_cron.list_jobs.side_effect = Exception("error")
        service.cron_service = mock_cron
        status = service.get_schedule_status(ReportType.DAILY)
        assert status.configured is False


class TestReportServiceRunReportNow:
    def test_run_report_now_daily(self):
        service = _make_service_with_runs()
        mock_report = MagicMock()
        mock_report.to_dict.return_value = {"date": "2026-05-08", "type": "daily"}
        service.analytics.generate_daily_report.return_value = mock_report
        result = service.run_report_now(
            push=False, age=30, report_type=ReportType.DAILY
        )
        assert result["success"] is True

    def test_run_report_now_with_push(self):
        service = _make_service_with_runs()
        mock_report = MagicMock()
        mock_report.to_dict.return_value = {"date": "2026-05-08", "type": "daily"}
        service.analytics.generate_daily_report.return_value = mock_report
        service.feishu = MagicMock()
        service.feishu.auth.is_configured.return_value = True
        service.feishu.receive_id = "test_user"
        service.feishu.send_card.return_value = OperationResult(success=True)
        result = service.run_report_now(push=True, age=30, report_type=ReportType.DAILY)
        assert result["success"] is True

    def test_run_report_now_exception(self):
        service = _make_service_with_runs()
        service.analytics.generate_daily_report.side_effect = Exception("error")
        result = service.run_report_now(
            push=False, age=30, report_type=ReportType.DAILY
        )
        assert result["success"] is False


class TestReportServiceMonthlyReportExtended:
    def test_monthly_report_with_vdot(self):
        runs = [
            {
                "session_total_distance": 10000,
                "session_total_timer_time": 3000,
                "session_avg_heart_rate": 150,
            },
            {
                "session_total_distance": 21000,
                "session_total_timer_time": 6300,
                "session_avg_heart_rate": 155,
            },
        ]
        service = _make_service_with_runs(runs=runs)
        result = service.generate_report(ReportType.MONTHLY, age=30)
        assert result.type == "monthly"
        assert result.total_runs == 2

    def test_monthly_report_exception(self):
        service = _make_service_with_runs()
        service.storage.query_by_date_range.side_effect = Exception("db error")
        result = service.generate_report(ReportType.MONTHLY, age=30)
        assert result.type == "monthly"
        assert hasattr(result, "error")


class TestReportServicePushReportExtended:
    def test_push_report_monthly(self):
        service = _make_service_with_runs()
        service.feishu = MagicMock()
        service.feishu.auth.is_configured.return_value = True
        service.feishu.receive_id = "test_user"
        service.feishu.send_card.return_value = OperationResult(success=True)
        data = {
            "greeting": "本月总结",
            "total_runs": 12,
            "total_distance_km": 150.0,
            "total_duration_min": 720.0,
            "total_tss": 960.0,
            "avg_vdot": 45.0,
            "avg_weekly_distance_km": 37.5,
            "avg_weekly_duration_min": 180.0,
            "highlights": [],
            "concerns": [],
            "recommendations": [],
        }
        result = service.push_report(data, ReportType.MONTHLY)
        assert result.success is True

    def test_push_report_no_receive_id(self):
        service = _make_service_with_runs()
        service.feishu = MagicMock()
        service.feishu.auth.is_configured.return_value = True
        service.feishu.receive_id = None
        result = service.push_report({"type": "daily"}, ReportType.DAILY)
        assert result.success is False
        assert "接收者" in result.error

    def test_push_report_dataclass_with_to_dict(self):
        service = _make_service_with_runs()
        service.feishu = MagicMock()
        service.feishu.auth.is_configured.return_value = True
        service.feishu.receive_id = "test_user"
        service.feishu.send_card.return_value = OperationResult(success=True)
        mock_report = MagicMock()
        mock_report.to_dict.return_value = {"date": "2026-05-08", "type": "daily"}
        result = service.push_report(mock_report, ReportType.DAILY)
        assert result.success is True
