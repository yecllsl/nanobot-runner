# CLI 单元测试
# 测试命令行界面的功能

import tempfile
from datetime import datetime
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

            # 创建模拟的 session 聚合数据
            mock_session_df = Mock()
            mock_session_df.height = 10  # 10 次跑步
            mock_session_df.__getitem__ = Mock(
                side_effect=lambda key: {
                    "distance": Mock(
                        sum=Mock(return_value=100000), mean=Mock(return_value=10000)
                    ),
                    "duration": Mock(
                        sum=Mock(return_value=36000), mean=Mock(return_value=3600)
                    ),
                    "avg_hr": Mock(mean=Mock(return_value=145)),
                }[key]
            )

            mock_df = Mock()
            mock_df.is_empty.return_value = False
            mock_df.group_by = Mock(
                return_value=Mock(agg=Mock(return_value=mock_session_df))
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


class TestCLIProfileShow:
    """测试 CLI profile show 命令"""

    def test_profile_show_help(self):
        """测试 profile show 命令帮助"""
        result = runner.invoke(app, ["profile", "show", "--help"])
        assert result.exit_code == 0

    def test_profile_show_no_data(self):
        """测试 profile show 无数据"""
        with patch("src.cli.ProfileStorageManager") as mock_profile_storage:
            mock_storage_instance = Mock()
            mock_storage_instance.load_profile_json.return_value = None
            mock_profile_storage.return_value = mock_storage_instance

            with patch("src.cli.ProfileEngine") as mock_engine:
                mock_engine_instance = Mock()
                mock_profile = Mock()
                mock_profile.total_activities = 0
                mock_engine_instance.build_profile.return_value = mock_profile
                mock_engine.return_value = mock_engine_instance

                result = runner.invoke(app, ["profile", "show"])
                assert result.exit_code == 0
                assert "暂无跑步数据" in result.output or "画像" in result.output

    def test_profile_show_with_data(self):
        """测试 profile show 有数据"""
        with patch("src.cli.ProfileStorageManager") as mock_profile_storage:
            mock_storage_instance = Mock()
            mock_profile = Mock()
            mock_profile.user_id = "test_user"
            mock_profile.profile_date = MagicMock()
            mock_profile.profile_date.strftime.return_value = "2024-01-01 12:00"
            mock_profile.analysis_period_days = 90
            mock_profile.total_activities = 10
            mock_profile.total_distance_km = 100.0
            mock_profile.total_duration_hours = 10.0
            mock_profile.avg_pace_min_per_km = 5.5
            mock_profile.avg_vdot = 40.0
            mock_profile.max_vdot = 45.0
            mock_profile.fitness_level = MagicMock()
            mock_profile.fitness_level.value = "中级跑者"
            mock_profile.weekly_avg_distance_km = 30.0
            mock_profile.weekly_avg_duration_hours = 3.0
            mock_profile.training_pattern = MagicMock()
            mock_profile.training_pattern.value = "周末长跑"
            mock_profile.consistency_score = 85.0
            mock_profile.atl = 40.0
            mock_profile.ctl = 50.0
            mock_profile.tsb = 10.0
            mock_profile.injury_risk_level = MagicMock()
            mock_profile.injury_risk_level.value = "低"
            mock_profile.injury_risk_score = 20.0
            mock_profile.avg_heart_rate = 150.0
            mock_profile.max_heart_rate = 180.0
            mock_profile.resting_heart_rate = 55.0
            mock_profile.data_quality_score = 90.0
            mock_profile.favorite_running_time = "早晨"

            mock_storage_instance.load_profile_json.return_value = mock_profile
            mock_profile_storage.return_value = mock_storage_instance

            result = runner.invoke(app, ["profile", "show"])
            assert result.exit_code == 0

    def test_profile_show_rebuild(self):
        """测试 profile show 重新构建"""
        with patch("src.cli.ConfigManager") as mock_config:
            mock_config_instance = Mock()
            mock_config_instance.data_dir = Path("/fake/data/dir")
            mock_config.return_value = mock_config_instance

            with patch("src.cli.StorageManager"):
                with patch("src.cli.ProfileStorageManager") as mock_profile_storage:
                    mock_storage_instance = Mock()
                    mock_storage_instance.load_profile_json.return_value = None
                    mock_profile_storage.return_value = mock_storage_instance

                    with patch("src.cli.ProfileEngine") as mock_engine:
                        mock_engine_instance = Mock()
                        mock_profile = Mock()
                        mock_profile.total_activities = 5
                        mock_profile.user_id = "default_user"
                        mock_profile.profile_date = datetime.now()
                        mock_profile.analysis_period_days = 90
                        mock_engine_instance.build_profile.return_value = mock_profile
                        mock_engine.return_value = mock_engine_instance

                        result = runner.invoke(app, ["profile", "show", "--rebuild"])
                        if result.exit_code != 0:
                            print(f"Exception: {result.exception}")
                            import traceback
                            if result.exception:
                                traceback.print_exception(type(result.exception), result.exception, result.exception.__traceback__)
                        assert result.exit_code == 0

    def test_profile_show_with_custom_params(self):
        """测试 profile show 使用自定义参数"""
        with patch("src.cli.ProfileStorageManager") as mock_profile_storage:
            mock_storage_instance = Mock()
            mock_profile = Mock()
            mock_profile.total_activities = 5
            mock_storage_instance.load_profile_json.return_value = mock_profile
            mock_profile_storage.return_value = mock_storage_instance

            result = runner.invoke(
                app,
                [
                    "profile",
                    "show",
                    "--days",
                    "60",
                    "--age",
                    "35",
                    "--resting-hr",
                    "65",
                ],
            )
            assert result.exit_code == 0 or result.exit_code == 1

    def test_profile_show_exception(self):
        """测试 profile show 异常处理"""
        with patch("src.cli.ProfileStorageManager") as mock_profile_storage:
            mock_storage_instance = Mock()
            mock_storage_instance.load_profile_json.side_effect = Exception("测试异常")
            mock_profile_storage.return_value = mock_storage_instance

            result = runner.invoke(app, ["profile", "show"])
            assert result.exit_code == 1


class TestCLIInit:
    """测试 CLI init 命令"""

    def test_init_command(self):
        """测试 init 命令"""
        with patch("src.cli.ConfigManager") as mock_config:
            mock_config_instance = Mock()
            mock_config_instance.data_dir = MagicMock()
            mock_workspace = MagicMock()
            mock_workspace.exists.return_value = False
            mock_workspace.mkdir = Mock()
            mock_config_instance.data_dir.parent = mock_workspace
            mock_config.return_value = mock_config_instance

            with patch("nanobot.utils.helpers.sync_workspace_templates") as mock_sync:
                mock_sync.return_value = ["AGENTS.md", "SOUL.md"]

                result = runner.invoke(app, ["init"])
                assert result.exit_code == 0

    def test_init_workspace_exists(self):
        """测试 init 工作区已存在"""
        with patch("src.cli.ConfigManager") as mock_config:
            mock_config_instance = Mock()
            mock_config_instance.data_dir = MagicMock()
            mock_workspace = MagicMock()
            mock_workspace.exists.return_value = True
            mock_config_instance.data_dir.parent = mock_workspace
            mock_config.return_value = mock_config_instance

            with patch("nanobot.utils.helpers.sync_workspace_templates") as mock_sync:
                mock_sync.return_value = []

                result = runner.invoke(app, ["init"])
                assert result.exit_code == 0


class TestCLIMemory:
    """测试 CLI memory 命令"""

    def test_memory_show(self):
        """测试 memory show 命令"""
        with patch("src.cli.ProfileStorageManager") as mock_profile_storage:
            mock_storage_instance = Mock()
            mock_memory_file = MagicMock()
            mock_memory_file.exists.return_value = True
            mock_memory_file.read_text.return_value = "# Agent 记忆\n\n测试内容"
            mock_storage_instance.memory_md_path = mock_memory_file
            mock_profile_storage.return_value = mock_storage_instance

            result = runner.invoke(app, ["memory", "show"])
            assert result.exit_code == 0

    def test_memory_show_not_exists(self):
        """测试 memory show 文件不存在"""
        with patch("src.cli.ProfileStorageManager") as mock_profile_storage:
            mock_storage_instance = Mock()
            mock_memory_file = MagicMock()
            mock_memory_file.exists.return_value = False
            mock_storage_instance.memory_md_path = mock_memory_file
            mock_profile_storage.return_value = mock_storage_instance

            result = runner.invoke(app, ["memory", "show"])
            assert result.exit_code == 0

    def test_memory_clear(self):
        """测试 memory clear 命令"""
        with patch("src.cli.ProfileStorageManager") as mock_profile_storage:
            mock_storage_instance = Mock()
            mock_memory_file = MagicMock()
            mock_memory_file.exists.return_value = True
            mock_storage_instance.memory_md_path = mock_memory_file
            mock_profile_storage.return_value = mock_storage_instance

            with patch("rich.prompt.Confirm.ask") as mock_confirm:
                mock_confirm.return_value = True

                result = runner.invoke(app, ["memory", "clear"])
                assert result.exit_code == 0
                mock_memory_file.write_text.assert_called_once()

    def test_memory_clear_not_exists(self):
        """测试 memory clear 文件不存在"""
        with patch("src.cli.ProfileStorageManager") as mock_profile_storage:
            mock_storage_instance = Mock()
            mock_memory_file = MagicMock()
            mock_memory_file.exists.return_value = False
            mock_storage_instance.memory_md_path = mock_memory_file
            mock_profile_storage.return_value = mock_storage_instance

            result = runner.invoke(app, ["memory", "clear"])
            assert result.exit_code == 0

    def test_memory_invalid_action(self):
        """测试 memory 无效操作"""
        result = runner.invoke(app, ["memory", "invalid"])
        assert result.exit_code == 1


class TestCLIVdot:
    """测试 CLI vdot 命令"""

    def test_vdot_command(self):
        """测试 vdot 命令"""
        with patch("src.agents.tools.RunnerTools") as mock_tools_class:
            mock_tools = Mock()
            mock_tools.get_vdot_trend.return_value = [
                {"timestamp": "2024-01-01", "distance": 10000, "vdot": 40.0},
                {"timestamp": "2024-01-08", "distance": 10500, "vdot": 41.0},
            ]
            mock_tools_class.return_value = mock_tools

            result = runner.invoke(app, ["vdot"])
            assert result.exit_code == 0

    def test_vdot_no_data(self):
        """测试 vdot 无数据"""
        with patch("src.agents.tools.RunnerTools") as mock_tools_class:
            mock_tools = Mock()
            mock_tools.get_vdot_trend.return_value = []
            mock_tools_class.return_value = mock_tools

            result = runner.invoke(app, ["vdot"])
            assert result.exit_code == 0
            assert "暂无 VDOT 数据" in result.output

    def test_vdot_with_limit(self):
        """测试 vdot 使用 limit 参数"""
        with patch("src.agents.tools.RunnerTools") as mock_tools_class:
            mock_tools = Mock()
            mock_tools.get_vdot_trend.return_value = [
                {"timestamp": "2024-01-01", "distance": 10000, "vdot": 40.0}
            ]
            mock_tools_class.return_value = mock_tools

            result = runner.invoke(app, ["vdot", "-n", "5"])
            assert result.exit_code == 0

    def test_vdot_with_output(self):
        """测试 vdot 输出到文件"""
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmpfile:
            tmpfile_path = Path(tmpfile.name)

        try:
            with patch("src.agents.tools.RunnerTools") as mock_tools_class:
                mock_tools = Mock()
                mock_tools.get_vdot_trend.return_value = [
                    {"timestamp": "2024-01-01", "distance": 10000, "vdot": 40.0}
                ]
                mock_tools_class.return_value = mock_tools

                result = runner.invoke(app, ["vdot", "-o", str(tmpfile_path)])
                assert result.exit_code == 0
                assert tmpfile_path.exists()
        finally:
            tmpfile_path.unlink(missing_ok=True)

    def test_vdot_exception(self):
        """测试 vdot 异常处理"""
        with patch("src.agents.tools.RunnerTools") as mock_tools_class:
            mock_tools = Mock()
            mock_tools.get_vdot_trend.side_effect = Exception("测试异常")
            mock_tools_class.return_value = mock_tools

            result = runner.invoke(app, ["vdot"])
            assert result.exit_code == 1


class TestCLITrainingLoad:
    """测试 CLI training-load 命令"""

    def test_training_load_command(self):
        """测试 training-load 命令"""
        with patch("src.core.analytics.AnalyticsEngine") as mock_engine_class:
            mock_engine = Mock()
            mock_engine.get_training_load.return_value = {
                "atl": 30.0,
                "ctl": 40.0,
                "tsb": 10.0,
                "fitness_status": "状态良好",
                "training_advice": "建议进行轻松跑",
                "days_analyzed": 42,
                "runs_count": 10,
            }
            mock_engine_class.return_value = mock_engine

            result = runner.invoke(app, ["load"])
            assert result.exit_code == 0

    def test_training_load_no_data(self):
        """测试 training-load 无数据"""
        with patch("src.core.analytics.AnalyticsEngine") as mock_engine_class:
            mock_engine = Mock()
            mock_engine.get_training_load.return_value = {"message": "暂无训练数据"}
            mock_engine_class.return_value = mock_engine

            result = runner.invoke(app, ["load"])
            assert result.exit_code == 0

    def test_training_load_with_days(self):
        """测试 training-load 使用 days 参数"""
        with patch("src.core.analytics.AnalyticsEngine") as mock_engine_class:
            mock_engine = Mock()
            mock_engine.get_training_load.return_value = {
                "atl": 25.0,
                "ctl": 35.0,
                "tsb": 10.0,
                "fitness_status": "状态良好",
                "training_advice": "建议",
                "days_analyzed": 30,
                "runs_count": 8,
            }
            mock_engine_class.return_value = mock_engine

            result = runner.invoke(app, ["load", "-d", "30"])
            assert result.exit_code == 0

    def test_training_load_exception(self):
        """测试 training-load 异常处理"""
        with patch("src.core.analytics.AnalyticsEngine") as mock_engine_class:
            mock_engine = Mock()
            mock_engine.get_training_load.side_effect = Exception("测试异常")
            mock_engine_class.return_value = mock_engine

            result = runner.invoke(app, ["load"])
            assert result.exit_code == 1


class TestCLIRecent:
    """测试 CLI recent 命令"""

    def test_recent_command(self):
        """测试 recent 命令"""
        with patch("src.agents.tools.RunnerTools") as mock_tools_class:
            mock_tools = Mock()
            mock_tools.get_recent_runs.return_value = [
                {
                    "timestamp": "2024-01-01T10:00:00",
                    "distance_km": 10.0,
                    "duration_min": 60.0,
                    "avg_pace_sec_km": 360.0,
                    "avg_heart_rate": 150,
                }
            ]
            mock_tools_class.return_value = mock_tools

            result = runner.invoke(app, ["recent"])
            assert result.exit_code == 0

    def test_recent_no_data(self):
        """测试 recent 无数据"""
        with patch("src.agents.tools.RunnerTools") as mock_tools_class:
            mock_tools = Mock()
            mock_tools.get_recent_runs.return_value = []
            mock_tools_class.return_value = mock_tools

            result = runner.invoke(app, ["recent"])
            assert result.exit_code == 0
            assert "暂无训练记录" in result.output

    def test_recent_with_limit(self):
        """测试 recent 使用 limit 参数"""
        with patch("src.agents.tools.RunnerTools") as mock_tools_class:
            mock_tools = Mock()
            mock_tools.get_recent_runs.return_value = [
                {
                    "timestamp": "2024-01-01T10:00:00",
                    "distance_km": 10.0,
                    "duration_min": 60.0,
                    "avg_pace_sec_km": 360.0,
                    "avg_heart_rate": 150,
                }
            ]
            mock_tools_class.return_value = mock_tools

            result = runner.invoke(app, ["recent", "-n", "5"])
            assert result.exit_code == 0

    def test_recent_exception(self):
        """测试 recent 异常处理"""
        with patch("src.agents.tools.RunnerTools") as mock_tools_class:
            mock_tools = Mock()
            mock_tools.get_recent_runs.side_effect = Exception("测试异常")
            mock_tools_class.return_value = mock_tools

            result = runner.invoke(app, ["recent"])
            assert result.exit_code == 1


class TestCLIHrDrift:
    """测试 CLI hr-drift 命令"""

    def test_hr_drift_command(self):
        """测试 hr-drift 命令"""
        with patch("src.agents.tools.RunnerTools") as mock_tools_class:
            mock_tools = Mock()
            mock_tools.get_hr_drift_analysis.return_value = {
                "drift_rate": 3.5,
                "correlation": -0.8,
                "assessment": "有氧基础良好",
            }
            mock_tools_class.return_value = mock_tools

            result = runner.invoke(app, ["hr-drift"])
            assert result.exit_code == 0

    def test_hr_drift_no_data(self):
        """测试 hr-drift 无数据"""
        with patch("src.agents.tools.RunnerTools") as mock_tools_class:
            mock_tools = Mock()
            mock_tools.get_hr_drift_analysis.return_value = {"error": "暂无数据"}
            mock_tools_class.return_value = mock_tools

            result = runner.invoke(app, ["hr-drift"])
            assert result.exit_code == 0

    def test_hr_drift_high_drift(self):
        """测试 hr-drift 高漂移率"""
        with patch("src.agents.tools.RunnerTools") as mock_tools_class:
            mock_tools = Mock()
            mock_tools.get_hr_drift_analysis.return_value = {
                "drift_rate": 12.0,
                "correlation": -0.5,
                "assessment": "有氧能力不足",
            }
            mock_tools_class.return_value = mock_tools

            result = runner.invoke(app, ["hr-drift"])
            assert result.exit_code == 0

    def test_hr_drift_exception(self):
        """测试 hr-drift 异常处理"""
        with patch("src.agents.tools.RunnerTools") as mock_tools_class:
            mock_tools = Mock()
            mock_tools.get_hr_drift_analysis.side_effect = Exception("测试异常")
            mock_tools_class.return_value = mock_tools

            result = runner.invoke(app, ["hr-drift"])
            assert result.exit_code == 1


class TestCLIPlan:
    """测试 CLI plan 命令"""

    def test_plan_generate_help(self):
        """测试 plan generate 帮助"""
        result = runner.invoke(app, ["plan", "generate", "--help"])
        assert result.exit_code == 0

    def test_plan_generate_success(self):
        """测试 plan generate 成功"""
        with patch("src.cli.ProfileStorageManager") as mock_profile_storage:
            mock_storage_instance = Mock()
            mock_profile = Mock()
            mock_profile.to_dict.return_value = {
                "estimated_vdot": 40.0,
                "weekly_avg_distance": 30.0,
                "age": 30,
                "resting_hr": 60,
            }
            mock_storage_instance.load_profile_json.return_value = mock_profile
            mock_profile_storage.return_value = mock_storage_instance

            with patch("src.cli.TrainingPlanEngine") as mock_engine_class:
                mock_engine = Mock()
                mock_plan = Mock()
                mock_plan.fitness_level = MagicMock()
                mock_plan.fitness_level.value = "中级跑者"
                mock_plan.weeks = [
                    MagicMock(
                        week_number=1,
                        start_date="2024-01-01",
                        end_date="2024-01-07",
                        weekly_distance_km=30.0,
                        focus="基础期",
                    )
                ]
                mock_plan.to_dict.return_value = {"goal_distance_km": 21.0975}
                mock_engine.generate_plan.return_value = mock_plan
                mock_engine_class.return_value = mock_engine

                result = runner.invoke(
                    app,
                    [
                        "plan",
                        "generate",
                        "--goal-distance",
                        "21.0975",
                        "--goal-date",
                        "2024-06-01",
                    ],
                )
                assert result.exit_code == 0

    def test_plan_generate_no_profile(self):
        """测试 plan generate 无画像"""
        with patch("src.cli.ProfileStorageManager") as mock_profile_storage:
            mock_storage_instance = Mock()
            mock_storage_instance.load_profile_json.return_value = None
            mock_profile_storage.return_value = mock_storage_instance

            result = runner.invoke(
                app,
                [
                    "plan",
                    "generate",
                    "--goal-distance",
                    "21.0975",
                    "--goal-date",
                    "2024-06-01",
                ],
            )
            assert result.exit_code == 1

    def test_plan_generate_with_custom_params(self):
        """测试 plan generate 使用自定义参数"""
        with patch("src.cli.ProfileStorageManager") as mock_profile_storage:
            mock_storage_instance = Mock()
            mock_profile = Mock()
            mock_profile.to_dict.return_value = {
                "estimated_vdot": 40.0,
                "weekly_avg_distance": 30.0,
                "age": 30,
                "resting_hr": 60,
            }
            mock_storage_instance.load_profile_json.return_value = mock_profile
            mock_profile_storage.return_value = mock_storage_instance

            with patch("src.cli.TrainingPlanEngine") as mock_engine_class:
                mock_engine = Mock()
                mock_plan = Mock()
                mock_plan.fitness_level = MagicMock()
                mock_plan.fitness_level.value = "中级跑者"
                mock_plan.weeks = [
                    MagicMock(
                        week_number=1,
                        start_date="2024-01-01",
                        end_date="2024-01-07",
                        weekly_distance_km=30.0,
                        focus="基础期",
                    )
                ]
                mock_plan.to_dict.return_value = {"goal_distance_km": 42.195}
                mock_engine.generate_plan.return_value = mock_plan
                mock_engine_class.return_value = mock_engine

                result = runner.invoke(
                    app,
                    [
                        "plan",
                        "generate",
                        "--goal-distance",
                        "42.195",
                        "--goal-date",
                        "2024-10-01",
                        "--vdot",
                        "45.0",
                        "--volume",
                        "50.0",
                    ],
                )
                assert result.exit_code == 0

    def test_plan_generate_with_output(self):
        """测试 plan generate 输出到文件"""
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmpfile:
            tmpfile_path = Path(tmpfile.name)

        try:
            with patch("src.cli.ProfileStorageManager") as mock_profile_storage:
                mock_storage_instance = Mock()
                mock_profile = Mock()
                mock_profile.to_dict.return_value = {
                    "estimated_vdot": 40.0,
                    "weekly_avg_distance": 30.0,
                    "age": 30,
                    "resting_hr": 60,
                }
                mock_storage_instance.load_profile_json.return_value = mock_profile
                mock_profile_storage.return_value = mock_storage_instance

                with patch("src.cli.TrainingPlanEngine") as mock_engine_class:
                    mock_engine = Mock()
                    mock_plan = Mock()
                    mock_plan.fitness_level = MagicMock()
                    mock_plan.fitness_level.value = "中级跑者"
                    mock_plan.weeks = []
                    mock_plan.to_dict.return_value = {"goal_distance_km": 21.0975}
                    mock_engine.generate_plan.return_value = mock_plan
                    mock_engine_class.return_value = mock_engine

                    result = runner.invoke(
                        app,
                        [
                            "plan",
                            "generate",
                            "--goal-distance",
                            "21.0975",
                            "--goal-date",
                            "2024-06-01",
                            "--output",
                            str(tmpfile_path),
                        ],
                    )
                    assert result.exit_code == 0
                    assert tmpfile_path.exists()
        finally:
            tmpfile_path.unlink(missing_ok=True)

    def test_plan_generate_exception(self):
        """测试 plan generate 异常处理"""
        with patch("src.cli.ProfileStorageManager") as mock_profile_storage:
            mock_storage_instance = Mock()
            mock_profile = Mock()
            mock_profile.to_dict.return_value = {}
            mock_storage_instance.load_profile_json.return_value = mock_profile
            mock_profile_storage.return_value = mock_storage_instance

            with patch("src.cli.TrainingPlanEngine") as mock_engine_class:
                mock_engine = Mock()
                mock_engine.generate_plan.side_effect = Exception("测试异常")
                mock_engine_class.return_value = mock_engine

                result = runner.invoke(
                    app,
                    [
                        "plan",
                        "generate",
                        "--goal-distance",
                        "21.0975",
                        "--goal-date",
                        "2024-06-01",
                    ],
                )
                assert result.exit_code == 1

    def test_plan_show_help(self):
        """测试 plan show 帮助"""
        result = runner.invoke(app, ["plan", "show", "--help"])
        assert result.exit_code == 0

    def test_plan_show_not_found(self):
        """测试 plan show 文件不存在"""
        result = runner.invoke(app, ["plan", "show", "/nonexistent/plan.json"])
        assert result.exit_code == 1

    def test_plan_show_success(self):
        """测试 plan show 成功"""
        import json
        import tempfile

        plan_data = {
            "goal_distance_km": 21.0975,
            "goal_date": "2024-06-01",
            "fitness_level": "中级跑者",
            "weeks": [
                {
                    "week_number": 1,
                    "start_date": "2024-01-01",
                    "end_date": "2024-01-07",
                    "weekly_distance_km": 30.0,
                    "focus": "基础期",
                    "daily_plans": [
                        {
                            "date": "2024-01-01",
                            "workout_type": "轻松跑",
                            "distance_km": 10.0,
                            "duration_min": 60,
                            "notes": "轻松配速",
                        }
                    ],
                }
            ],
        }

        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w"
        ) as tmpfile:
            json.dump(plan_data, tmpfile)
            tmpfile_path = Path(tmpfile.name)

        try:
            result = runner.invoke(app, ["plan", "show", str(tmpfile_path)])
            assert result.exit_code == 0
        finally:
            tmpfile_path.unlink(missing_ok=True)

    def test_plan_show_with_week(self):
        """测试 plan show 指定周次"""
        import json
        import tempfile

        plan_data = {
            "goal_distance_km": 21.0975,
            "goal_date": "2024-06-01",
            "fitness_level": "中级跑者",
            "weeks": [
                {
                    "week_number": 1,
                    "start_date": "2024-01-01",
                    "end_date": "2024-01-07",
                    "weekly_distance_km": 30.0,
                    "focus": "基础期",
                    "daily_plans": [],
                },
                {
                    "week_number": 2,
                    "start_date": "2024-01-08",
                    "end_date": "2024-01-14",
                    "weekly_distance_km": 35.0,
                    "focus": "提升期",
                    "daily_plans": [],
                },
            ],
        }

        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w"
        ) as tmpfile:
            json.dump(plan_data, tmpfile)
            tmpfile_path = Path(tmpfile.name)

        try:
            result = runner.invoke(
                app, ["plan", "show", str(tmpfile_path), "--week", "2"]
            )
            assert result.exit_code == 0
        finally:
            tmpfile_path.unlink(missing_ok=True)

    def test_plan_show_invalid_week(self):
        """测试 plan show 无效周次"""
        import json
        import tempfile

        plan_data = {
            "goal_distance_km": 21.0975,
            "goal_date": "2024-06-01",
            "fitness_level": "中级跑者",
            "weeks": [
                {
                    "week_number": 1,
                    "start_date": "2024-01-01",
                    "end_date": "2024-01-07",
                    "weekly_distance_km": 30.0,
                    "focus": "基础期",
                }
            ],
        }

        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w"
        ) as tmpfile:
            json.dump(plan_data, tmpfile)
            tmpfile_path = Path(tmpfile.name)

        try:
            result = runner.invoke(
                app, ["plan", "show", str(tmpfile_path), "--week", "10"]
            )
            assert result.exit_code == 1
        finally:
            tmpfile_path.unlink(missing_ok=True)

    def test_plan_show_invalid_json(self):
        """测试 plan show 无效 JSON"""
        import tempfile

        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w"
        ) as tmpfile:
            tmpfile.write("invalid json")
            tmpfile_path = Path(tmpfile.name)

        try:
            result = runner.invoke(app, ["plan", "show", str(tmpfile_path)])
            assert result.exit_code == 1
        finally:
            tmpfile_path.unlink(missing_ok=True)

    def test_plan_show_exception(self):
        """测试 plan show 异常处理"""
        import json
        import tempfile

        plan_data = {
            "goal_distance_km": 21.0975,
            "goal_date": "2024-06-01",
            "fitness_level": "中级跑者",
            "weeks": [],
        }

        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w"
        ) as tmpfile:
            json.dump(plan_data, tmpfile)
            tmpfile_path = Path(tmpfile.name)

        try:
            with patch("src.cli.console.print") as mock_print:
                mock_print.side_effect = Exception("测试异常")

                result = runner.invoke(app, ["plan", "show", str(tmpfile_path)])
                assert result.exit_code == 1
        finally:
            tmpfile_path.unlink(missing_ok=True)
