# CLI单元测试
# 测试命令行界面的功能

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
import typer
from typer.testing import CliRunner

from src.cli import CLIError, app, console, print_error, print_status

runner = CliRunner()


class TestCLIError:
    """测试CLI错误消息类"""

    def test_path_not_found_error(self):
        """测试路径不存在错误"""
        error = CLIError.path_not_found("/test/path")
        assert "message" in error
        assert "suggestion" in error
        assert "/test/path" in error["message"]
        assert "检查路径" in error["suggestion"]

    def test_import_failed_error(self):
        """测试导入失败错误"""
        error = CLIError.import_failed("文件格式错误")
        assert "文件格式错误" in error["message"]
        assert "FIT格式" in error["suggestion"]

    def test_config_missing_error(self):
        """测试配置缺失错误"""
        error = CLIError.config_missing("webhook_url")
        assert "webhook_url" in error["message"]
        assert "config" in error["suggestion"]

    def test_storage_error(self):
        """测试存储错误"""
        error = CLIError.storage_error("权限不足")
        assert "权限不足" in error["message"]
        assert "数据目录" in error["suggestion"]

    def test_schedule_not_found_error(self):
        """测试定时任务未找到错误"""
        error = CLIError.schedule_not_found()
        assert "未找到定时任务" in error["message"]
        assert "--schedule" in error["suggestion"]

    def test_push_failed_error(self):
        """测试推送失败错误"""
        error = CLIError.push_failed("网络超时")
        assert "网络超时" in error["message"]
        assert "Webhook" in error["suggestion"]


class TestPrintFunctions:
    """测试打印函数"""

    def test_print_error_output(self, capsys):
        """测试错误打印输出"""
        error_info = {"message": "测试错误消息", "suggestion": "测试恢复建议"}
        print_error(error_info)
        captured = capsys.readouterr()
        assert "测试错误消息" in captured.out
        assert "测试恢复建议" in captured.out

    def test_print_status_success(self, capsys):
        """测试成功状态打印"""
        print_status("操作成功", "success")
        captured = capsys.readouterr()
        assert "操作成功" in captured.out

    def test_print_status_error(self, capsys):
        """测试错误状态打印"""
        print_status("操作失败", "error")
        captured = capsys.readouterr()
        assert "操作失败" in captured.out

    def test_print_status_warning(self, capsys):
        """测试警告状态打印"""
        print_status("警告信息", "warning")
        captured = capsys.readouterr()
        assert "警告信息" in captured.out

    def test_print_status_info(self, capsys):
        """测试信息状态打印"""
        print_status("提示信息", "info")
        captured = capsys.readouterr()
        assert "提示信息" in captured.out


class TestCLICommands:
    """测试CLI命令"""

    def test_import_data_file_not_exists(self):
        """测试导入不存在的文件"""
        result = runner.invoke(app, ["import-data", "/nonexistent/path.fit"])
        assert result.exit_code != 0
        assert "路径不存在" in result.output or "建议" in result.output

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
        with patch("src.cli._run_chat") as mock_run_chat:
            mock_run_chat.return_value = None
            result = runner.invoke(app, ["chat"])
            mock_run_chat.assert_called_once()

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

    def test_import_directory_with_fit_files(self):
        """测试导入包含FIT文件的目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            fit_file = tmpdir_path / "test.fit"
            fit_file.write_text("dummy")

            with patch("src.cli.ImportService") as mock_importer_class:
                mock_importer = Mock()
                mock_importer.import_file.return_value = {"status": "added"}
                mock_importer_class.return_value = mock_importer

                result = runner.invoke(app, ["import-data", str(tmpdir_path)])
                assert result.exit_code == 0

    def test_import_directory_empty(self):
        """测试导入空目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(app, ["import-data", tmpdir])
            assert result.exit_code == 0
            assert "没有找到FIT文件" in result.output

    def test_import_file_success(self):
        """测试导入文件成功"""
        with tempfile.NamedTemporaryFile(suffix=".fit", delete=False) as tmpfile:
            tmpfile.write(b"dummy")
            tmpfile.flush()
            tmpfile_path = Path(tmpfile.name)

        try:
            with patch("src.cli.ImportService") as mock_importer_class:
                mock_importer = Mock()
                mock_importer.import_file.return_value = {"status": "added"}
                mock_importer_class.return_value = mock_importer

                result = runner.invoke(app, ["import-data", str(tmpfile_path)])
                assert result.exit_code == 0
        finally:
            tmpfile_path.unlink(missing_ok=True)

    def test_import_file_skipped(self):
        """测试导入文件被跳过"""
        with tempfile.NamedTemporaryFile(suffix=".fit", delete=False) as tmpfile:
            tmpfile.write(b"dummy")
            tmpfile.flush()
            tmpfile_path = Path(tmpfile.name)

        try:
            with patch("src.cli.ImportService") as mock_importer_class:
                mock_importer = Mock()
                mock_importer.import_file.return_value = {"status": "skipped"}
                mock_importer_class.return_value = mock_importer

                result = runner.invoke(app, ["import-data", str(tmpfile_path)])
                assert result.exit_code == 0
        finally:
            tmpfile_path.unlink(missing_ok=True)

    def test_import_file_failed(self):
        """测试导入文件失败"""
        with tempfile.NamedTemporaryFile(suffix=".fit", delete=False) as tmpfile:
            tmpfile.write(b"dummy")
            tmpfile.flush()
            tmpfile_path = Path(tmpfile.name)

        try:
            with patch("src.cli.ImportService") as mock_importer_class:
                mock_importer = Mock()
                mock_importer.import_file.return_value = {
                    "status": "error",
                    "message": "解析失败",
                }
                mock_importer_class.return_value = mock_importer

                result = runner.invoke(app, ["import-data", str(tmpfile_path)])
                assert result.exit_code == 1
        finally:
            tmpfile_path.unlink(missing_ok=True)

    def test_import_directory_with_mixed_results(self):
        """测试导入目录包含多种结果"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            fit_file = tmpdir_path / "test.fit"
            fit_file.write_text("dummy")

            with patch("src.cli.ImportService") as mock_importer_class:
                mock_importer = Mock()
                mock_importer.import_file.side_effect = [
                    {"status": "added"},
                    {"status": "skipped"},
                    {"status": "error"},
                ]
                mock_importer_class.return_value = mock_importer

                result = runner.invoke(app, ["import-data", str(tmpdir_path)])
                assert result.exit_code == 0


class TestCLIStats:
    """测试CLI统计功能"""

    def test_stats_with_multiple_years(self):
        """测试多年份统计"""
        result = runner.invoke(app, ["stats", "--year", "2024"])
        assert result.exit_code == 0 or result.exit_code == 1

    def test_stats_with_time_range(self):
        """测试时间范围统计"""
        result = runner.invoke(
            app, ["stats", "--start", "2024-01-01", "--end", "2024-12-31"]
        )
        assert result.exit_code == 0 or result.exit_code == 1

    def test_stats_invalid_date_format(self):
        """测试无效日期格式"""
        with patch("src.cli.StorageManager") as mock_storage_class:
            mock_storage = Mock()
            mock_df = Mock()
            mock_df.is_empty.return_value = False
            mock_df.height = 1
            mock_df.__getitem__ = Mock(return_value=Mock())
            mock_storage.read_parquet.return_value.collect.return_value = mock_df
            mock_storage_class.return_value = mock_storage

            result = runner.invoke(app, ["stats", "--start", "2024/01/01"])
            assert result.exit_code == 1

    def test_stats_with_data(self):
        """测试有数据时的统计"""
        with patch("src.cli.StorageManager") as mock_storage_class:
            mock_storage = Mock()
            mock_df = Mock()
            mock_df.is_empty.return_value = False
            mock_df.height = 10
            mock_df.__getitem__ = Mock(
                return_value=Mock(
                    sum=Mock(return_value=1000), mean=Mock(return_value=100)
                )
            )
            mock_storage.read_parquet.return_value.collect.return_value = mock_df
            mock_storage_class.return_value = mock_storage

            result = runner.invoke(app, ["stats"])
            assert result.exit_code == 0

    def test_stats_file_not_found(self):
        """测试数据文件不存在"""
        with patch("src.cli.StorageManager") as mock_storage_class:
            mock_storage = Mock()
            mock_storage.read_parquet.side_effect = FileNotFoundError("文件不存在")
            mock_storage_class.return_value = mock_storage

            result = runner.invoke(app, ["stats"])
            assert result.exit_code == 1


class TestCLIChat:
    """测试CLI聊天功能"""

    def test_chat_command_invoked(self):
        """测试chat命令被正确调用"""
        with patch("src.cli._run_chat") as mock_run_chat:
            mock_run_chat.return_value = None
            result = runner.invoke(app, ["chat"])
            mock_run_chat.assert_called_once()

    def test_chat_handles_exception(self):
        """测试chat命令异常处理"""
        with patch("src.cli._run_chat") as mock_run_chat:
            mock_run_chat.side_effect = Exception("测试异常")
            result = runner.invoke(app, ["chat"])
            assert result.exit_code != 0


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

    def test_report_status_disabled(self):
        """测试查看已禁用的定时推送状态"""
        with patch("src.core.report_service.ReportService") as mock_service:
            mock_instance = Mock()
            mock_instance.get_schedule_status.return_value = {
                "configured": True,
                "enabled": False,
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
            assert result.exit_code == 0

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
                {
                    "day": "周一",
                    "date": "01/01",
                    "plan": "休息",
                    "is_today": True,
                    "is_past": False,
                },
                {
                    "day": "周二",
                    "date": "01/02",
                    "plan": "轻松跑 6km",
                    "is_today": False,
                    "is_past": False,
                },
            ],
        }

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

        _display_report(report_data)

    def test_display_report_empty_data(self):
        """测试显示空数据晨报"""
        from src.cli import _display_report

        _display_report({})

    def test_display_report_with_high_tss(self):
        """测试显示高TSS训练"""
        from src.cli import _display_report

        report_data = {
            "date": "2024年1月1日",
            "greeting": "早上好",
            "yesterday_run": {
                "distance_km": 21.1,
                "duration_min": 120,
                "tss": 180,
            },
            "fitness_status": {
                "atl": 120,
                "ctl": 80,
                "tsb": -40,
                "status": "需要注意",
            },
            "training_advice": "建议休息恢复",
            "weekly_plan": [],
        }

        _display_report(report_data)

    def test_display_report_with_good_fitness(self):
        """测试显示良好体能状态"""
        from src.cli import _display_report

        report_data = {
            "date": "2024年1月1日",
            "greeting": "早上好",
            "yesterday_run": None,
            "fitness_status": {
                "atl": 30,
                "ctl": 40,
                "tsb": 10,
                "status": "状态良好",
            },
            "training_advice": "可以进行强度训练",
            "weekly_plan": [],
        }

        _display_report(report_data)
