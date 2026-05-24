# Model Presets CLI 单元测试
# 验证 model list 命令的显示逻辑

from __future__ import annotations

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from src.cli.app import app

runner = CliRunner()


class TestModelListCommand:
    """Model Presets CLI 测试"""

    @patch("src.cli.handlers.model_handler.ModelHandler.__init__", return_value=None)
    def test_model_list_shows_presets(self, mock_init: MagicMock) -> None:
        """model list 应显示预设列表"""
        with patch(
            "src.cli.handlers.model_handler.ModelHandler.list_presets",
            return_value=[
                {"name": "fast", "provider": "openai", "model": "gpt-4o-mini"},
                {
                    "name": "quality",
                    "provider": "anthropic",
                    "model": "claude-sonnet-4-20250514",
                },
            ],
        ):
            result = runner.invoke(app, ["model", "list"])
            assert result.exit_code == 0
            assert "fast" in result.output
            assert "quality" in result.output

    @patch("src.cli.handlers.model_handler.ModelHandler.__init__", return_value=None)
    def test_model_list_no_presets(self, mock_init: MagicMock) -> None:
        """无预设时显示提示信息"""
        with patch(
            "src.cli.handlers.model_handler.ModelHandler.list_presets",
            return_value=[],
        ):
            result = runner.invoke(app, ["model", "list"])
            assert result.exit_code == 0
            assert (
                "暂无" in result.output
                or "无预设" in result.output
                or "No" in result.output
            )
