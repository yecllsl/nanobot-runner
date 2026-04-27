# CLI tools命令单元测试
# 测试工具管理CLI命令的功能

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from src.cli.app import app

runner = CliRunner()


@pytest.fixture
def config_with_weather(tmp_path: Path) -> Path:
    """创建包含天气MCP服务器配置的config.json"""
    config_path = tmp_path / "config.json"
    config = {
        "version": "0.13.0",
        "data_dir": str(tmp_path / "data"),
        "tools": {
            "mcp_servers": {
                "weather": {
                    "type": "stdio",
                    "command": "npx",
                    "args": ["-y", "@dangahagan/weather-mcp"],
                    "tool_timeout": 30,
                    "enabled_tools": ["*"],
                }
            }
        },
    }
    config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
    return config_path


@pytest.fixture
def config_empty(tmp_path: Path) -> Path:
    """创建空的config.json"""
    config_path = tmp_path / "config.json"
    config = {
        "version": "0.13.0",
        "data_dir": str(tmp_path / "data"),
    }
    config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
    return config_path


class TestToolsListCommand:
    """测试tools list命令"""

    @patch("src.cli.commands.tools._get_config_path")
    def test_list_with_weather(self, mock_path, config_with_weather: Path):
        """测试列出包含天气工具的配置"""
        mock_path.return_value = config_with_weather
        result = runner.invoke(app, ["tools", "list"])
        assert result.exit_code == 0
        assert "weather" in result.output

    @patch("src.cli.commands.tools._get_config_path")
    def test_list_empty(self, mock_path, config_empty: Path):
        """测试无工具配置时的列表"""
        mock_path.return_value = config_empty
        result = runner.invoke(app, ["tools", "list"])
        assert result.exit_code == 0
        assert "未配置任何工具" in result.output


class TestToolsAddCommand:
    """测试tools add命令"""

    @patch("src.cli.commands.tools._get_config_path")
    def test_add_weather_server(self, mock_path, config_empty: Path):
        """测试添加天气MCP服务器"""
        mock_path.return_value = config_empty
        result = runner.invoke(
            app,
            [
                "tools",
                "add",
                "weather",
                "--command",
                "npx",
                "--args",
                '["-y", "@dangahagan/weather-mcp"]',
                "--type",
                "stdio",
            ],
        )
        assert result.exit_code == 0
        assert "添加成功" in result.output

        with open(config_empty, encoding="utf-8") as f:
            config = json.load(f)
        assert "weather" in config["tools"]["mcp_servers"]

    @patch("src.cli.commands.tools._get_config_path")
    def test_add_server_with_invalid_type(self, mock_path, config_empty: Path):
        """测试添加无效传输类型的服务器"""
        mock_path.return_value = config_empty
        result = runner.invoke(
            app,
            [
                "tools",
                "add",
                "test",
                "--command",
                "test-cmd",
                "--type",
                "invalid",
            ],
        )
        assert result.exit_code == 1

    @patch("src.cli.commands.tools._get_config_path")
    def test_add_server_with_invalid_args(self, mock_path, config_empty: Path):
        """测试添加无效args参数的服务器"""
        mock_path.return_value = config_empty
        result = runner.invoke(
            app,
            [
                "tools",
                "add",
                "test",
                "--command",
                "test-cmd",
                "--args",
                "not-a-json-array",
            ],
        )
        assert result.exit_code == 1


class TestToolsRemoveCommand:
    """测试tools remove命令"""

    @patch("src.cli.commands.tools._get_config_path")
    def test_remove_existing_server(self, mock_path, config_with_weather: Path):
        """测试移除已存在的MCP服务器"""
        mock_path.return_value = config_with_weather
        result = runner.invoke(app, ["tools", "remove", "weather"])
        assert result.exit_code == 0
        assert "已移除" in result.output

    @patch("src.cli.commands.tools._get_config_path")
    def test_remove_nonexistent_server(self, mock_path, config_empty: Path):
        """测试移除不存在的MCP服务器"""
        mock_path.return_value = config_empty
        result = runner.invoke(app, ["tools", "remove", "nonexistent"])
        assert result.exit_code == 1


class TestToolsEnableDisableCommand:
    """测试tools enable/disable命令"""

    @patch("src.cli.commands.tools._get_config_path")
    def test_enable_server(self, mock_path, config_with_weather: Path):
        """测试启用MCP服务器"""
        mock_path.return_value = config_with_weather
        result = runner.invoke(app, ["tools", "enable", "weather"])
        assert result.exit_code == 0
        assert "已启用" in result.output

    @patch("src.cli.commands.tools._get_config_path")
    def test_disable_server(self, mock_path, config_with_weather: Path):
        """测试禁用MCP服务器"""
        mock_path.return_value = config_with_weather
        result = runner.invoke(app, ["tools", "disable", "weather"])
        assert result.exit_code == 0
        assert "已禁用" in result.output

    @patch("src.cli.commands.tools._get_config_path")
    def test_enable_nonexistent_server(self, mock_path, config_empty: Path):
        """测试启用不存在的MCP服务器"""
        mock_path.return_value = config_empty
        result = runner.invoke(app, ["tools", "enable", "nonexistent"])
        assert result.exit_code == 1


class TestToolsValidateCommand:
    """测试tools validate命令"""

    @patch("src.cli.commands.tools._get_config_path")
    def test_validate_valid_config(self, mock_path, config_with_weather: Path):
        """测试验证有效的MCP配置"""
        mock_path.return_value = config_with_weather
        result = runner.invoke(app, ["tools", "validate"])
        assert result.exit_code == 0
        assert "验证通过" in result.output

    @patch("src.cli.commands.tools._get_config_path")
    def test_validate_empty_config(self, mock_path, config_empty: Path):
        """测试验证无MCP配置"""
        mock_path.return_value = config_empty
        result = runner.invoke(app, ["tools", "validate"])
        assert result.exit_code == 0
        assert "验证通过" in result.output
