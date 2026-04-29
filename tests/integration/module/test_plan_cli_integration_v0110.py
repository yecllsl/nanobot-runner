# v0.11.0 CLI集成测试
# 覆盖 plan adjust / plan suggest 命令

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from src.cli.app import app

runner = CliRunner()


class TestPlanAdjustCommand:
    """plan adjust 命令集成测试"""

    def test_plan_adjust_help(self):
        """测试 plan adjust --help"""
        result = runner.invoke(app, ["plan", "adjust", "--help"])
        assert result.exit_code == 0
        assert "调整" in result.output

    def test_plan_adjust_missing_args(self):
        """测试缺少必要参数"""
        result = runner.invoke(app, ["plan", "adjust"])
        assert result.exit_code != 0

    def test_plan_adjust_missing_request(self):
        """测试缺少调整请求参数"""
        result = runner.invoke(app, ["plan", "adjust", "plan_test"])
        assert result.exit_code != 0

    @patch("src.core.base.context.get_context")
    def test_plan_adjust_success_with_confirm(self, mock_get_context):
        """测试正常调整（需确认）"""
        mock_context = MagicMock()
        mock_context.runner_tools = None
        mock_get_context.return_value = mock_context

        mock_runner_tools = MagicMock()
        mock_runner_tools.adjust_plan.return_value = {
            "success": True,
            "plan_id": "plan_test",
            "adjustment": {
                "adjustment_type": "volume",
                "description": "减量20%",
                "adjusted_value": 0.8,
            },
            "validation": {"passed": True},
            "requires_confirmation": True,
        }

        with patch("src.agents.tools.RunnerTools", return_value=mock_runner_tools):
            result = runner.invoke(
                app,
                ["plan", "adjust", "plan_test", "减量20%"],
            )
            assert result.exit_code == 0
            assert "调整" in result.output or "确认" in result.output

    @patch("src.core.base.context.get_context")
    def test_plan_adjust_success_no_confirm(self, mock_get_context):
        """测试正常调整（无需确认）"""
        mock_context = MagicMock()
        mock_context.runner_tools = None
        mock_get_context.return_value = mock_context

        mock_runner_tools = MagicMock()
        mock_runner_tools.adjust_plan.return_value = {
            "success": True,
            "plan_id": "plan_test",
            "adjustment": {
                "adjustment_type": "volume",
                "description": "减量20%",
                "adjusted_value": 0.8,
            },
            "validation": {"passed": True},
            "requires_confirmation": False,
        }

        with patch("src.agents.tools.RunnerTools", return_value=mock_runner_tools):
            result = runner.invoke(
                app,
                ["plan", "adjust", "plan_test", "减量20%", "--no-confirm"],
            )
            assert result.exit_code == 0

    @patch("src.core.base.context.get_context")
    def test_plan_adjust_validation_failed(self, mock_get_context):
        """测试调整校验失败"""
        mock_context = MagicMock()
        mock_context.runner_tools = None
        mock_get_context.return_value = mock_context

        mock_runner_tools = MagicMock()
        mock_runner_tools.adjust_plan.return_value = {
            "success": False,
            "error": "调整建议不符合运动科学原则",
            "violations": ["周跑量增幅超过10%，违反运动科学原则"],
        }

        with patch("src.agents.tools.RunnerTools", return_value=mock_runner_tools):
            result = runner.invoke(
                app,
                ["plan", "adjust", "plan_test", "加量50%"],
            )
            assert result.exit_code == 1


class TestPlanSuggestCommand:
    """plan suggest 命令集成测试"""

    def test_plan_suggest_help(self):
        """测试 plan suggest --help"""
        result = runner.invoke(app, ["plan", "suggest", "--help"])
        assert result.exit_code == 0
        assert "建议" in result.output

    def test_plan_suggest_missing_args(self):
        """测试缺少必要参数"""
        result = runner.invoke(app, ["plan", "suggest"])
        assert result.exit_code != 0

    @patch("src.core.base.context.get_context")
    def test_plan_suggest_success(self, mock_get_context):
        """测试正常获取建议"""
        mock_context = MagicMock()
        mock_context.runner_tools = None
        mock_get_context.return_value = mock_context

        mock_runner_tools = MagicMock()
        mock_runner_tools.get_plan_adjustment_suggestions.return_value = {
            "success": True,
            "plan_id": "plan_test",
            "suggestions": [
                {
                    "suggestion_type": "training",
                    "suggestion_content": "完成率偏低，建议降低训练量或增加恢复日",
                    "priority": "high",
                    "confidence": 0.8,
                },
            ],
        }

        with patch("src.agents.tools.RunnerTools", return_value=mock_runner_tools):
            result = runner.invoke(
                app,
                ["plan", "suggest", "plan_test"],
            )
            assert result.exit_code == 0
            assert "建议" in result.output

    @patch("src.core.base.context.get_context")
    def test_plan_suggest_no_suggestions(self, mock_get_context):
        """测试无建议情况"""
        mock_context = MagicMock()
        mock_context.runner_tools = None
        mock_get_context.return_value = mock_context

        mock_runner_tools = MagicMock()
        mock_runner_tools.get_plan_adjustment_suggestions.return_value = {
            "success": True,
            "plan_id": "plan_test",
            "suggestions": [],
        }

        with patch("src.agents.tools.RunnerTools", return_value=mock_runner_tools):
            result = runner.invoke(
                app,
                ["plan", "suggest", "plan_test"],
            )
            assert result.exit_code == 0

    @patch("src.core.base.context.get_context")
    def test_plan_suggest_error(self, mock_get_context):
        """测试获取建议失败"""
        mock_context = MagicMock()
        mock_context.runner_tools = None
        mock_get_context.return_value = mock_context

        mock_runner_tools = MagicMock()
        mock_runner_tools.get_plan_adjustment_suggestions.return_value = {
            "error": "计划不存在",
        }

        with patch("src.agents.tools.RunnerTools", return_value=mock_runner_tools):
            result = runner.invoke(
                app,
                ["plan", "suggest", "plan_unknown"],
            )
            assert result.exit_code == 1
