# v0.10.0 CLI集成测试
# 覆盖 plan log / plan stats 命令

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from src.cli.app import app
from src.core.models import PlanExecutionStats

runner = CliRunner()


class TestPlanLogCommand:
    """plan log 命令集成测试"""

    def test_plan_log_help(self):
        """测试 plan log --help"""
        result = runner.invoke(app, ["plan", "log", "--help"])
        assert result.exit_code == 0
        assert "记录" in result.output or "执行反馈" in result.output

    def test_plan_log_missing_args(self):
        """测试缺少必要参数"""
        result = runner.invoke(app, ["plan", "log"])
        assert result.exit_code != 0

    def test_plan_log_missing_date(self):
        """测试缺少日期参数"""
        result = runner.invoke(app, ["plan", "log", "plan_test"])
        assert result.exit_code != 0

    @patch("src.core.context.get_context")
    def test_plan_log_success(self, mock_get_context):
        """测试正常记录执行反馈"""
        mock_context = MagicMock()
        mock_plan_manager = MagicMock()
        mock_plan_manager.record_execution.return_value = {
            "success": True,
            "message": "已记录2026-04-20的执行反馈",
            "plan_id": "plan_test",
            "date": "2026-04-20",
        }
        mock_context.plan_manager = mock_plan_manager
        mock_get_context.return_value = mock_context

        result = runner.invoke(
            app,
            [
                "plan",
                "log",
                "plan_test",
                "2026-04-20",
                "--completion",
                "0.8",
                "--effort",
                "6",
            ],
        )

        assert result.exit_code == 0
        assert "OK" in result.output or "记录" in result.output

    @patch("src.core.context.get_context")
    def test_plan_log_with_notes(self, mock_get_context):
        """测试带备注的记录"""
        mock_context = MagicMock()
        mock_plan_manager = MagicMock()
        mock_plan_manager.record_execution.return_value = {
            "success": True,
            "message": "已记录2026-04-20的执行反馈",
            "plan_id": "plan_test",
            "date": "2026-04-20",
        }
        mock_context.plan_manager = mock_plan_manager
        mock_get_context.return_value = mock_context

        result = runner.invoke(
            app,
            [
                "plan",
                "log",
                "plan_test",
                "2026-04-20",
                "-c",
                "1.0",
                "-e",
                "4",
                "-n",
                "轻松完成",
            ],
        )

        assert result.exit_code == 0

    @patch("src.core.context.get_context")
    def test_plan_log_plan_not_found(self, mock_get_context):
        """测试计划不存在"""
        mock_context = MagicMock()
        mock_plan_manager = MagicMock()
        mock_plan_manager.record_execution.side_effect = Exception(
            "计划不存在：plan_unknown"
        )
        mock_context.plan_manager = mock_plan_manager
        mock_get_context.return_value = mock_context

        result = runner.invoke(
            app,
            ["plan", "log", "plan_unknown", "2026-04-20"],
        )

        assert result.exit_code != 0

    @patch("src.core.context.get_context")
    def test_plan_log_with_distance_and_duration(self, mock_get_context):
        """测试带实际距离和时长"""
        mock_context = MagicMock()
        mock_plan_manager = MagicMock()
        mock_plan_manager.record_execution.return_value = {
            "success": True,
            "message": "已记录2026-04-20的执行反馈",
            "plan_id": "plan_test",
            "date": "2026-04-20",
        }
        mock_context.plan_manager = mock_plan_manager
        mock_get_context.return_value = mock_context

        result = runner.invoke(
            app,
            [
                "plan",
                "log",
                "plan_test",
                "2026-04-20",
                "--distance",
                "10.5",
                "--duration",
                "60",
                "--hr",
                "145",
            ],
        )

        assert result.exit_code == 0


class TestPlanStatsCommand:
    """plan stats 命令集成测试"""

    def test_plan_stats_help(self):
        """测试 plan stats --help"""
        result = runner.invoke(app, ["plan", "stats", "--help"])
        assert result.exit_code == 0
        assert "统计" in result.output or "执行" in result.output

    def test_plan_stats_missing_args(self):
        """测试缺少必要参数"""
        result = runner.invoke(app, ["plan", "stats"])
        assert result.exit_code != 0

    @patch("src.core.context.get_context")
    def test_plan_stats_success(self, mock_get_context):
        """测试正常查询执行统计"""
        mock_context = MagicMock()
        mock_execution_repo = MagicMock()
        mock_stats = PlanExecutionStats(
            plan_id="plan_test",
            total_planned_days=28,
            completed_days=20,
            completion_rate=0.71,
            avg_effort_score=5.5,
            total_distance_km=150.0,
            total_duration_min=900,
            avg_hr=145,
            avg_hr_drift=2.5,
        )
        mock_execution_repo.get_plan_execution_stats.return_value = mock_stats
        mock_context.plan_execution_repo = mock_execution_repo
        mock_get_context.return_value = mock_context

        result = runner.invoke(app, ["plan", "stats", "plan_test"])

        assert result.exit_code == 0
        assert "plan_test" in result.output
        assert "28" in result.output
        assert "20" in result.output

    @patch("src.core.context.get_context")
    def test_plan_stats_plan_not_found(self, mock_get_context):
        """测试计划不存在"""
        mock_context = MagicMock()
        mock_execution_repo = MagicMock()
        mock_execution_repo.get_plan_execution_stats.side_effect = Exception(
            "计划不存在：plan_unknown"
        )
        mock_context.plan_execution_repo = mock_execution_repo
        mock_get_context.return_value = mock_context

        result = runner.invoke(app, ["plan", "stats", "plan_unknown"])

        assert result.exit_code != 0


class TestPlanCommandContract:
    """plan 命令契约测试"""

    def test_plan_command_exists(self):
        """测试 plan 命令存在"""
        result = runner.invoke(app, ["plan", "--help"])
        assert result.exit_code == 0
        assert "log" in result.output
        assert "stats" in result.output

    def test_plan_log_command_name(self):
        """测试 plan log 命令名称"""
        result = runner.invoke(app, ["plan", "log", "--help"])
        assert result.exit_code == 0

    def test_plan_stats_command_name(self):
        """测试 plan stats 命令名称"""
        result = runner.invoke(app, ["plan", "stats", "--help"])
        assert result.exit_code == 0
