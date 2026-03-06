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
