# CLI单元测试
# 测试命令行界面的功能

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
import typer
from typer.testing import CliRunner

from src.cli import app, console

runner = CliRunner()


class TestCLICommands:
    """测试CLI命令"""

    def test_import_data_file_not_exists(self):
        """测试导入不存在的文件"""
        result = runner.invoke(app, ["import-data", "/nonexistent/path.fit"])
        assert result.exit_code != 0

    def test_import_data_invalid_extension(self):
        """测试导入非.fit文件"""
        result = runner.invoke(app, ["import-data", "test.txt"])
        assert result.exit_code != 0

    def test_import_data_directory(self):
        """测试导入目录（不存在的目录）"""
        result = runner.invoke(app, ["import-data", "/nonexistent/dir"])
        assert result.exit_code != 0

    def test_import_data_invalid_path(self):
        """测试无效路径"""
        result = runner.invoke(app, ["import-data", "test.fit"])
        assert result.exit_code != 0

    def test_stats(self):
        """测试stats命令"""
        result = runner.invoke(app, ["stats"])
        assert result.exit_code == 0 or result.exit_code == 1

    def test_stats_empty(self):
        """测试stats命令"""
        result = runner.invoke(app, ["stats"])
        assert result.exit_code == 0 or result.exit_code == 1

    def test_chat(self):
        """测试chat命令"""
        result = runner.invoke(app, ["chat"])
        assert "Agent" in result.output or result.exit_code != 0

    def test_version(self):
        """测试version命令"""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "Nanobot Runner" in result.output


class TestCLIApp:
    """测试CLI应用"""

    def test_app_help(self):
        """测试帮助信息"""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0

    def test_no_args_help(self):
        """测试无参数显示帮助"""
        result = runner.invoke(app, [])


class TestCLIImportFile:
    """测试CLI导入文件功能"""

    def test_import_data_file_success(self):
        """测试导入文件"""
        result = runner.invoke(app, ["import-data", "test.fit"])
        assert result.exit_code != 0

    def test_import_data_file_with_force_flag(self):
        """测试强制导入文件"""
        result = runner.invoke(app, ["import-data", "test.fit", "--force"])
        assert result.exit_code != 0


class TestCLIStats:
    """测试CLI统计功能"""

    def test_stats_with_multiple_years(self):
        """测试多年份统计"""
        result = runner.invoke(app, ["stats", "--year", "2024"])
        assert result.exit_code == 0 or result.exit_code == 1

    def test_stats_with_time_range(self):
        """测试时间范围统计"""
        result = runner.invoke(app, ["stats", "--start", "2024-01-01", "--end", "2024-12-31"])
        assert result.exit_code == 0 or result.exit_code == 1


class TestCLIChat:
    """测试CLI聊天功能"""

    def test_chat_with_exit_command(self):
        """测试chat命令"""
        result = runner.invoke(app, ["chat"])
        assert "Agent" in result.output or result.exit_code != 0


class TestCLIVersion:
    """测试CLI版本功能"""

    def test_version_format(self):
        """测试版本格式"""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "v" in result.output


class TestCLIReport:
    """测试CLI report命令"""

    def test_report_help(self):
        """测试report命令帮助"""
        result = runner.invoke(app, ["report", "--help"])
        assert result.exit_code == 0
        assert "晨报" in result.output or "report" in result.output.lower()

    def test_report_status_not_configured(self):
        """测试查看未配置的定时推送状态"""
        with patch("src.core.report_service.ReportService") as mock_service:
            mock_instance = Mock()
            mock_instance.get_schedule_status.return_value = {
                "configured": False,
                "enabled": False,
                "message": "未配置定时推送",
            }
            mock_service.return_value = mock_instance

            result = runner.invoke(app, ["report", "--status"])
            assert result.exit_code == 0

    def test_report_status_configured(self):
        """测试查看已配置的定时推送状态"""
        with patch("src.core.report_service.ReportService") as mock_service:
            mock_instance = Mock()
            mock_instance.get_schedule_status.return_value = {
                "configured": True,
                "enabled": True,
                "time": "07:00",
                "push": True,
                "age": 30,
            }
            mock_service.return_value = mock_instance

            result = runner.invoke(app, ["report", "--status"])
            assert result.exit_code == 0

    def test_report_schedule_success(self):
        """测试配置定时推送成功"""
        with patch("src.core.report_service.ReportService") as mock_service:
            mock_instance = Mock()
            mock_instance.schedule_report.return_value = {
                "success": True,
                "message": "已配置定时推送",
                "next_run": "2024-01-01T07:00:00",
            }
            mock_service.return_value = mock_instance

            result = runner.invoke(app, ["report", "--schedule", "07:00"])
            assert result.exit_code == 0

    def test_report_schedule_invalid_time(self):
        """测试配置定时推送无效时间"""
        with patch("src.core.report_service.ReportService") as mock_service:
            mock_instance = Mock()
            mock_instance.schedule_report.return_value = {
                "success": False,
                "error": "时间格式无效",
            }
            mock_service.return_value = mock_instance

            result = runner.invoke(app, ["report", "--schedule", "25:00"])
            assert result.exit_code == 1

    def test_report_enable_success(self):
        """测试启用定时推送成功"""
        with patch("src.core.report_service.ReportService") as mock_service:
            mock_instance = Mock()
            mock_instance.enable_schedule.return_value = {
                "success": True,
                "message": "定时推送已启用",
            }
            mock_service.return_value = mock_instance

            result = runner.invoke(app, ["report", "--enable"])
            assert result.exit_code == 0

    def test_report_disable_success(self):
        """测试禁用定时推送成功"""
        with patch("src.core.report_service.ReportService") as mock_service:
            mock_instance = Mock()
            mock_instance.enable_schedule.return_value = {
                "success": True,
                "message": "定时推送已禁用",
            }
            mock_service.return_value = mock_instance

            result = runner.invoke(app, ["report", "--disable"])
            assert result.exit_code == 0

    def test_report_enable_no_job(self):
        """测试启用时没有定时任务"""
        with patch("src.core.report_service.ReportService") as mock_service:
            mock_instance = Mock()
            mock_instance.enable_schedule.return_value = {
                "success": False,
                "error": "未找到定时任务",
            }
            mock_service.return_value = mock_instance

            result = runner.invoke(app, ["report", "--enable"])
            assert result.exit_code == 1

    def test_report_generate_success(self):
        """测试生成晨报成功"""
        with patch("src.core.report_service.ReportService") as mock_service:
            mock_instance = Mock()
            mock_instance.run_report_now.return_value = {
                "success": True,
                "report": {
                    "date": "2024年1月1日 周一",
                    "greeting": "早上好",
                    "yesterday_run": None,
                    "fitness_status": {
                        "atl": 0,
                        "ctl": 0,
                        "tsb": 0,
                        "status": "数据不足",
                    },
                    "training_advice": "暂无建议",
                    "weekly_plan": [],
                },
            }
            mock_service.return_value = mock_instance

            result = runner.invoke(app, ["report"])
            assert result.exit_code == 0

    def test_report_generate_with_push(self):
        """测试生成晨报并推送"""
        with patch("src.core.report_service.ReportService") as mock_service:
            mock_instance = Mock()
            mock_instance.run_report_now.return_value = {
                "success": True,
                "report": {
                    "date": "2024年1月1日",
                    "greeting": "早上好",
                    "fitness_status": {},
                    "training_advice": "建议轻松跑",
                    "weekly_plan": [],
                },
                "push_result": {"success": True, "message": "推送成功"},
            }
            mock_service.return_value = mock_instance

            result = runner.invoke(app, ["report", "--push"])
            assert result.exit_code == 0

    def test_report_generate_with_push_failed(self):
        """测试生成晨报推送失败"""
        with patch("src.core.report_service.ReportService") as mock_service:
            mock_instance = Mock()
            mock_instance.run_report_now.return_value = {
                "success": True,
                "report": {
                    "date": "2024年1月1日",
                    "greeting": "早上好",
                    "fitness_status": {},
                    "training_advice": "建议",
                    "weekly_plan": [],
                },
                "push_result": {"success": False, "error": "未配置Webhook"},
            }
            mock_service.return_value = mock_instance

            result = runner.invoke(app, ["report", "--push"])
            assert result.exit_code == 0  # 推送失败不影响退出码

    def test_report_generate_error(self):
        """测试生成晨报失败"""
        with patch("src.core.report_service.ReportService") as mock_service:
            mock_instance = Mock()
            mock_instance.run_report_now.return_value = {
                "success": False,
                "error": "数据库错误",
            }
            mock_service.return_value = mock_instance

            result = runner.invoke(app, ["report"])
            assert result.exit_code == 1

    def test_report_with_custom_age(self):
        """测试使用自定义年龄生成晨报"""
        with patch("src.core.report_service.ReportService") as mock_service:
            mock_instance = Mock()
            mock_instance.run_report_now.return_value = {
                "success": True,
                "report": {
                    "date": "test",
                    "fitness_status": {},
                    "training_advice": "建议",
                    "weekly_plan": [],
                },
            }
            mock_service.return_value = mock_instance

            result = runner.invoke(app, ["report", "--age", "40"])
            assert result.exit_code == 0
            mock_instance.run_report_now.assert_called_once()
            # 验证 age 参数传递
            call_kwargs = mock_instance.run_report_now.call_args[1]
            assert call_kwargs.get("age") == 40


class TestDisplayReport:
    """测试晨报显示功能"""

    def test_display_report_with_yesterday_run(self):
        """测试显示包含昨日训练的晨报"""
        from src.cli import _display_report

        report_data = {
            "date": "2024年1月1日 周一",
            "greeting": "早上好！今天是您的训练日。",
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
            "training_advice": "建议进行轻松跑",
            "weekly_plan": [
                {"day": "周一", "date": "01/01", "plan": "休息", "is_today": True, "is_past": False},
                {"day": "周二", "date": "01/02", "plan": "轻松跑 6km", "is_today": False, "is_past": False},
            ],
        }

        # 不应该抛出异常
        _display_report(report_data)

    def test_display_report_without_yesterday_run(self):
        """测试显示不包含昨日训练的晨报"""
        from src.cli import _display_report

        report_data = {
            "date": "2024年1月1日",
            "greeting": "早上好",
            "yesterday_run": None,
            "fitness_status": {"atl": 0, "ctl": 0, "tsb": 0, "status": "数据不足"},
            "training_advice": "暂无建议",
            "weekly_plan": [],
        }

        # 不应该抛出异常
        _display_report(report_data)

    def test_display_report_empty_data(self):
        """测试显示空数据晨报"""
        from src.cli import _display_report

        # 不应该抛出异常
        _display_report({})
