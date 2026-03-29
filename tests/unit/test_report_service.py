# ReportService 单元测试
# 测试晨报生成、推送和定时调度功能

import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.core.report_service import ReportService


class TestReportServiceInit:
    """测试 ReportService 初始化"""

    def test_init_default(self):
        """测试默认初始化"""
        with patch("src.core.report_service.ConfigManager") as mock_config:
            mock_config_instance = Mock()
            mock_config_instance.base_dir = Path("/tmp/test")
            mock_config_instance.data_dir = Path("/tmp/test/data")
            mock_config.return_value = mock_config_instance

            with patch("src.core.report_service.StorageManager"):
                with patch("src.core.report_service.AnalyticsEngine"):
                    with patch("src.core.report_service.CronService"):
                        service = ReportService()
                        assert service is not None

    def test_init_with_dependencies(self):
        """测试使用依赖注入初始化"""
        mock_config = Mock()
        mock_config.base_dir = Path("/tmp/test")
        mock_storage = Mock()
        mock_analytics = Mock()
        mock_feishu = Mock()

        with patch("src.core.report_service.CronService"):
            service = ReportService(
                config=mock_config,
                storage=mock_storage,
                analytics=mock_analytics,
                feishu=mock_feishu,
            )
            assert service.config == mock_config
            assert service.storage == mock_storage
            assert service.analytics == mock_analytics
            assert service.feishu == mock_feishu


class TestGenerateReport:
    """测试生成晨报"""

    def test_generate_report_success(self):
        """测试成功生成晨报"""
        mock_config = Mock()
        mock_config.base_dir = Path("/tmp/test")

        mock_analytics = Mock()
        mock_analytics.generate_daily_report.return_value = {
            "date": "2024年1月1日 周一",
            "greeting": "早上好",
            "fitness_status": {"atl": 10, "ctl": 20, "tsb": 10},
        }

        with patch("src.core.report_service.CronService"):
            service = ReportService(config=mock_config, analytics=mock_analytics)
            result = service.generate_report(age=30)

            assert "date" in result
            assert "greeting" in result
            mock_analytics.generate_daily_report.assert_called_once_with(age=30)

    def test_generate_report_with_custom_age(self):
        """测试使用自定义年龄生成晨报"""
        mock_config = Mock()
        mock_config.base_dir = Path("/tmp/test")

        mock_analytics = Mock()
        mock_analytics.generate_daily_report.return_value = {"date": "test"}

        with patch("src.core.report_service.CronService"):
            service = ReportService(config=mock_config, analytics=mock_analytics)
            service.generate_report(age=40)

            mock_analytics.generate_daily_report.assert_called_once_with(age=40)


class TestPushReport:
    """测试推送晨报"""

    def test_push_report_success(self):
        """测试成功推送晨报"""
        mock_config = Mock()
        mock_config.base_dir = Path("/tmp/test")

        mock_feishu = Mock()
        mock_feishu.webhook = "https://test.webhook.com"
        mock_feishu.send_card.return_value = {"code": 0}

        with patch("src.core.report_service.CronService"):
            service = ReportService(config=mock_config, feishu=mock_feishu)
            result = service.push_report({"date": "test"})

            assert result.get("success") is True
            mock_feishu.send_card.assert_called_once()

    def test_push_report_no_feishu_config(self):
        """测试未配置飞书应用机器人"""
        mock_config = Mock()
        mock_config.base_dir = Path("/tmp/test")
        mock_config.get.return_value = None  # 返回 None 表示未配置

        mock_feishu = Mock()
        mock_feishu.auth.is_configured.return_value = False

        with patch("src.core.report_service.CronService"):
            service = ReportService(config=mock_config, feishu=mock_feishu)
            result = service.push_report({"date": "test"})

            assert result.get("success") is False
            assert "未配置" in result.get("error", "")

    def test_push_report_send_error(self):
        """测试发送失败"""
        mock_config = Mock()
        mock_config.base_dir = Path("/tmp/test")

        mock_feishu = Mock()
        mock_feishu.webhook = "https://test.webhook.com"
        mock_feishu.send_card.return_value = {"error": "Network error"}

        with patch("src.core.report_service.CronService"):
            service = ReportService(config=mock_config, feishu=mock_feishu)
            result = service.push_report({"date": "test"})

            assert result.get("success") is False
            assert "Network error" in result.get("error", "")


class TestFormatReportContent:
    """测试格式化晨报内容"""

    def test_format_report_with_yesterday_run(self):
        """测试格式化包含昨日训练的晨报"""
        mock_config = Mock()
        mock_config.base_dir = Path("/tmp/test")

        with patch("src.core.report_service.CronService"):
            service = ReportService(config=mock_config)

            report_data = {
                "date": "2024年1月1日",
                "greeting": "早上好",
                "yesterday_run": {
                    "distance_km": 10.5,
                    "duration_min": 60,
                    "tss": 85,
                },
                "fitness_status": {
                    "atl": 15,
                    "ctl": 25,
                    "tsb": 10,
                    "status": "状态良好",
                },
                "training_advice": "建议轻松跑",
            }

            content = service._format_report_content(report_data)

            assert "2024年1月1日" in content
            assert "早上好" in content
            assert "10.5 km" in content
            assert "ATL" in content
            assert "建议轻松跑" in content

    def test_format_report_without_yesterday_run(self):
        """测试格式化不包含昨日训练的晨报"""
        mock_config = Mock()
        mock_config.base_dir = Path("/tmp/test")

        with patch("src.core.report_service.CronService"):
            service = ReportService(config=mock_config)

            report_data = {
                "date": "2024年1月1日",
                "greeting": "早上好",
                "yesterday_run": None,
                "fitness_status": {"atl": 0, "ctl": 0, "tsb": 0, "status": "数据不足"},
                "training_advice": "暂无建议",
            }

            content = service._format_report_content(report_data)

            assert "昨日训练**: 无" in content


class TestScheduleReport:
    """测试配置定时推送"""

    def test_schedule_report_success(self):
        """测试成功配置定时推送"""
        mock_config = Mock()
        mock_config.base_dir = Path("/tmp/test")
        mock_config.set = Mock()

        mock_cron_service = Mock()
        mock_cron_service.list_jobs.return_value = []
        mock_cron_service.add_job.return_value = Mock(id="job_123")

        with patch(
            "src.core.report_service.CronService", return_value=mock_cron_service
        ):
            service = ReportService(config=mock_config)
            result = service.schedule_report("07:00", push=True, age=30)

            assert result.get("success") is True
            assert "next_run" in result
            mock_cron_service.add_job.assert_called_once()

    def test_schedule_report_invalid_time_format(self):
        """测试无效时间格式"""
        mock_config = Mock()
        mock_config.base_dir = Path("/tmp/test")

        with patch("src.core.report_service.CronService"):
            service = ReportService(config=mock_config)
            result = service.schedule_report("25:00")

            assert result.get("success") is False
            assert "error" in result

    def test_schedule_report_invalid_time_value(self):
        """测试无效时间值"""
        mock_config = Mock()
        mock_config.base_dir = Path("/tmp/test")

        with patch("src.core.report_service.CronService"):
            service = ReportService(config=mock_config)
            result = service.schedule_report("ab:cd")

            assert result.get("success") is False
            assert "error" in result

    def test_schedule_report_replace_existing(self):
        """测试替换已存在的定时任务"""
        mock_config = Mock()
        mock_config.base_dir = Path("/tmp/test")
        mock_config.set = Mock()

        # 创建一个真正的 Mock 对象，并设置 name 属性
        existing_job = Mock()
        existing_job.id = "old_job"
        existing_job.name = "daily_report"  # 设置 name 属性

        mock_cron_service = Mock()
        mock_cron_service.list_jobs.return_value = [existing_job]
        mock_cron_service.add_job.return_value = Mock(id="new_job")

        with patch(
            "src.core.report_service.CronService", return_value=mock_cron_service
        ):
            service = ReportService(config=mock_config)
            result = service.schedule_report("08:00")

            assert result.get("success") is True
            # 验证 remove_job 被调用
            mock_cron_service.remove_job.assert_called_once()


class TestEnableSchedule:
    """测试启用/禁用定时推送"""

    def test_enable_schedule_success(self):
        """测试成功启用定时推送"""
        mock_config = Mock()
        mock_config.base_dir = Path("/tmp/test")
        mock_config.set = Mock()

        # 创建 Mock 对象并设置属性
        existing_job = Mock()
        existing_job.id = "job_123"
        existing_job.name = "daily_report"  # 必须设置 name 属性

        mock_cron_service = Mock()
        mock_cron_service.list_jobs.return_value = [existing_job]
        mock_cron_service.enable_job.return_value = existing_job

        with patch(
            "src.core.report_service.CronService", return_value=mock_cron_service
        ):
            service = ReportService(config=mock_config)
            result = service.enable_schedule(enabled=True)

            assert result.get("success") is True
            mock_cron_service.enable_job.assert_called_once()

    def test_disable_schedule_success(self):
        """测试成功禁用定时推送"""
        mock_config = Mock()
        mock_config.base_dir = Path("/tmp/test")
        mock_config.set = Mock()

        # 创建 Mock 对象并设置属性
        existing_job = Mock()
        existing_job.id = "job_123"
        existing_job.name = "daily_report"  # 必须设置 name 属性

        mock_cron_service = Mock()
        mock_cron_service.list_jobs.return_value = [existing_job]

        with patch(
            "src.core.report_service.CronService", return_value=mock_cron_service
        ):
            service = ReportService(config=mock_config)
            result = service.enable_schedule(enabled=False)

            assert result.get("success") is True
            mock_cron_service.enable_job.assert_called_once_with(
                "job_123", enabled=False
            )

    def test_enable_schedule_no_job(self):
        """测试启用时没有定时任务"""
        mock_config = Mock()
        mock_config.base_dir = Path("/tmp/test")

        mock_cron_service = Mock()
        mock_cron_service.list_jobs.return_value = []

        with patch(
            "src.core.report_service.CronService", return_value=mock_cron_service
        ):
            service = ReportService(config=mock_config)
            result = service.enable_schedule(enabled=True)

            assert result.get("success") is False
            assert "未找到" in result.get("error", "")


class TestGetScheduleStatus:
    """测试获取定时推送状态"""

    def test_get_schedule_status_configured(self):
        """测试获取已配置的状态"""
        mock_config = Mock()
        mock_config.base_dir = Path("/tmp/test")
        mock_config.get = Mock(return_value="07:00")

        message = json.dumps({"push": True, "age": 30, "time": "07:00"})

        # 创建 Mock 对象并设置属性
        existing_job = Mock()
        existing_job.id = "job_123"
        existing_job.name = "daily_report"  # 必须设置 name 属性
        existing_job.enabled = True
        existing_job.message = message

        mock_cron_service = Mock()
        mock_cron_service.list_jobs.return_value = [existing_job]

        with patch(
            "src.core.report_service.CronService", return_value=mock_cron_service
        ):
            service = ReportService(config=mock_config)
            result = service.get_schedule_status()

            assert result.get("configured") is True
            assert result.get("enabled") is True
            assert result.get("time") == "07:00"

    def test_get_schedule_status_not_configured(self):
        """测试获取未配置的状态"""
        mock_config = Mock()
        mock_config.base_dir = Path("/tmp/test")

        mock_cron_service = Mock()
        mock_cron_service.list_jobs.return_value = []

        with patch(
            "src.core.report_service.CronService", return_value=mock_cron_service
        ):
            service = ReportService(config=mock_config)
            result = service.get_schedule_status()

            assert result.get("configured") is False

    def test_get_schedule_status_disabled(self):
        """测试获取已禁用的状态"""
        mock_config = Mock()
        mock_config.base_dir = Path("/tmp/test")

        message = json.dumps({"push": False, "age": 25, "time": "08:00"})

        # 创建 Mock 对象并设置属性
        existing_job = Mock()
        existing_job.id = "job_123"
        existing_job.name = "daily_report"  # 必须设置 name 属性
        existing_job.enabled = False
        existing_job.message = message

        mock_cron_service = Mock()
        mock_cron_service.list_jobs.return_value = [existing_job]

        with patch(
            "src.core.report_service.CronService", return_value=mock_cron_service
        ):
            service = ReportService(config=mock_config)
            result = service.get_schedule_status()

            assert result.get("configured") is True
            assert result.get("enabled") is False


class TestRunReportNow:
    """测试立即生成晨报"""

    def test_run_report_now_without_push(self):
        """测试立即生成晨报（不推送）"""
        mock_config = Mock()
        mock_config.base_dir = Path("/tmp/test")

        mock_analytics = Mock()
        mock_analytics.generate_daily_report.return_value = {
            "date": "test",
            "fitness_status": {},
        }

        with patch("src.core.report_service.CronService"):
            service = ReportService(config=mock_config, analytics=mock_analytics)
            result = service.run_report_now(push=False, age=30)

            assert result.get("success") is True
            assert "report" in result

    def test_run_report_now_with_push(self):
        """测试立即生成晨报并推送"""
        mock_config = Mock()
        mock_config.base_dir = Path("/tmp/test")

        mock_analytics = Mock()
        mock_analytics.generate_daily_report.return_value = {
            "date": "test",
            "fitness_status": {},
        }

        mock_feishu = Mock()
        mock_feishu.webhook = "https://test.webhook.com"
        mock_feishu.send_card.return_value = {"code": 0}

        with patch("src.core.report_service.CronService"):
            service = ReportService(
                config=mock_config, analytics=mock_analytics, feishu=mock_feishu
            )
            result = service.run_report_now(push=True, age=30)

            assert result.get("success") is True
            assert "push_result" in result

    def test_run_report_now_error(self):
        """测试生成晨报失败"""
        mock_config = Mock()
        mock_config.base_dir = Path("/tmp/test")

        mock_analytics = Mock()
        mock_analytics.generate_daily_report.side_effect = Exception("Database error")

        with patch("src.core.report_service.CronService"):
            service = ReportService(config=mock_config, analytics=mock_analytics)
            result = service.run_report_now(push=False)

            assert result.get("success") is False
            assert "error" in result


class TestRunScheduledReport:
    """测试执行定时推送任务"""

    def test_run_scheduled_report_success(self):
        """测试成功执行定时推送"""
        mock_config = Mock()
        mock_config.base_dir = Path("/tmp/test")

        mock_analytics = Mock()
        mock_analytics.generate_daily_report.return_value = {
            "date": "test",
            "fitness_status": {},
        }

        mock_feishu = Mock()
        mock_feishu.webhook = "https://test.webhook.com"
        mock_feishu.send_card.return_value = {"code": 0}

        message = json.dumps({"push": True, "age": 30, "time": "07:00"})

        # 创建 Mock 对象并设置属性
        existing_job = Mock()
        existing_job.id = "job_123"
        existing_job.name = "daily_report"
        existing_job.enabled = True
        existing_job.message = message

        mock_cron_service = Mock()
        mock_cron_service.list_jobs.return_value = [existing_job]

        with patch(
            "src.core.report_service.CronService", return_value=mock_cron_service
        ):
            service = ReportService(
                config=mock_config, analytics=mock_analytics, feishu=mock_feishu
            )
            # 使用 asyncio.run 来测试异步方法
            import asyncio

            result = asyncio.run(service.run_scheduled_report())

            assert result is True

    def test_run_scheduled_report_no_push(self):
        """测试执行定时任务但不推送"""
        mock_config = Mock()
        mock_config.base_dir = Path("/tmp/test")

        mock_analytics = Mock()
        mock_analytics.generate_daily_report.return_value = {
            "date": "test",
            "fitness_status": {},
        }

        message = json.dumps({"push": False, "age": 30, "time": "07:00"})

        # 创建 Mock 对象并设置属性
        existing_job = Mock()
        existing_job.id = "job_123"
        existing_job.name = "daily_report"
        existing_job.enabled = True
        existing_job.message = message

        mock_cron_service = Mock()
        mock_cron_service.list_jobs.return_value = [existing_job]

        with patch(
            "src.core.report_service.CronService", return_value=mock_cron_service
        ):
            service = ReportService(config=mock_config, analytics=mock_analytics)
            # 使用 asyncio.run 来测试异步方法
            import asyncio

            result = asyncio.run(service.run_scheduled_report())

            assert result is True


class TestGetFeishuBot:
    """测试获取飞书机器人实例"""

    def test_get_feishu_bot_lazy_init(self):
        """测试懒加载飞书机器人"""
        mock_config = Mock()
        mock_config.base_dir = Path("/tmp/test")

        with patch("src.core.report_service.CronService"):
            service = ReportService(config=mock_config)
            assert service.feishu is None

            with patch("src.core.report_service.FeishuBot") as mock_feishu_class:
                mock_feishu_class.return_value = Mock()
                bot = service._get_feishu_bot()
                assert bot is not None

    def test_get_feishu_bot_existing(self):
        """测试使用已存在的飞书机器人"""
        mock_config = Mock()
        mock_config.base_dir = Path("/tmp/test")

        mock_feishu = Mock()

        with patch("src.core.report_service.CronService"):
            service = ReportService(config=mock_config, feishu=mock_feishu)
            bot = service._get_feishu_bot()
            assert bot == mock_feishu


class TestEdgeCases:
    """测试边界条件"""

    def test_schedule_report_midnight(self):
        """测试午夜时间配置"""
        mock_config = Mock()
        mock_config.base_dir = Path("/tmp/test")
        mock_config.set = Mock()

        mock_cron_service = Mock()
        mock_cron_service.list_jobs.return_value = []
        mock_cron_service.add_job.return_value = Mock(id="job_123")

        with patch(
            "src.core.report_service.CronService", return_value=mock_cron_service
        ):
            service = ReportService(config=mock_config)
            result = service.schedule_report("00:00")

            assert result.get("success") is True

    def test_schedule_report_end_of_day(self):
        """测试一天结束时间配置"""
        mock_config = Mock()
        mock_config.base_dir = Path("/tmp/test")
        mock_config.set = Mock()

        mock_cron_service = Mock()
        mock_cron_service.list_jobs.return_value = []
        mock_cron_service.add_job.return_value = Mock(id="job_123")

        with patch(
            "src.core.report_service.CronService", return_value=mock_cron_service
        ):
            service = ReportService(config=mock_config)
            result = service.schedule_report("23:59")

            assert result.get("success") is True

    def test_format_report_empty_data(self):
        """测试格式化空数据"""
        mock_config = Mock()
        mock_config.base_dir = Path("/tmp/test")

        with patch("src.core.report_service.CronService"):
            service = ReportService(config=mock_config)
            content = service._format_report_content({})

            assert content is not None
            assert isinstance(content, str)

    def test_get_schedule_status_invalid_json(self):
        """测试获取状态时无效 JSON"""
        mock_config = Mock()
        mock_config.base_dir = Path("/tmp/test")
        mock_config.get = Mock(return_value=None)

        # 创建 Mock 对象并设置属性
        existing_job = Mock()
        existing_job.id = "job_123"
        existing_job.name = "daily_report"
        existing_job.enabled = True
        existing_job.message = "invalid json"

        mock_cron_service = Mock()
        mock_cron_service.list_jobs.return_value = [existing_job]

        with patch(
            "src.core.report_service.CronService", return_value=mock_cron_service
        ):
            service = ReportService(config=mock_config)
            result = service.get_schedule_status()

            # 应该能处理无效 JSON，返回默认值
            assert result.get("configured") is True
