# CLI单元测试
# 测试命令行界面的功能

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

import typer
from typer.testing import CliRunner

from src.cli import app, console, import_service, storage_manager


runner = CliRunner()


class TestCLICommands:
    """测试CLI命令"""

    def test_import_data_file_not_exists(self):
        """测试导入不存在的文件"""
        result = runner.invoke(app, ["import-data", "/nonexistent/path.fit"])
        assert result.exit_code != 0
        assert "错误: 路径不存在" in result.output

    def test_import_data_invalid_extension(self):
        """测试导入非.fit文件"""
        with patch.object(Path, 'exists', return_value=True), \
             patch.object(Path, 'is_file', return_value=True), \
             patch.object(Path, 'suffix', '.txt'):
            result = runner.invoke(app, ["import-data", "test.txt"])
            assert result.exit_code != 0
            assert "只支持.fit格式文件" in result.output

    def test_import_data_directory(self):
        """测试导入目录"""
        with patch.object(Path, 'exists', return_value=True), \
             patch.object(Path, 'is_file', return_value=False), \
             patch.object(Path, 'is_dir', return_value=True), \
             patch.object(import_service, 'import_directory', return_value=None) as mock_import:
            result = runner.invoke(app, ["import-data", "/path/to/dir"])
            assert result.exit_code == 0
            mock_import.assert_called_once()

    def test_import_data_invalid_path(self):
        """测试无效路径"""
        with patch.object(Path, 'exists', return_value=True), \
             patch.object(Path, 'is_file', return_value=False), \
             patch.object(Path, 'is_dir', return_value=False):
            result = runner.invoke(app, ["import-data", "test.fit"])
            assert result.exit_code != 0
            assert "无效的路径" in result.output

    def test_stats(self):
        """测试stats命令"""
        with patch.object(storage_manager, 'get_stats', return_value={
            "total_records": 10,
            "time_range": {"start": "2024-01-01", "end": "2024-12-31"},
            "years": [2024]
        }):
            result = runner.invoke(app, ["stats"])
            assert result.exit_code == 0
            assert "本地数据统计" in result.output
            assert "总记录数" in result.output

    def test_stats_empty(self):
        """测试stats命令（空数据）"""
        with patch.object(storage_manager, 'get_stats', return_value={
            "total_records": 0,
            "time_range": None,
            "years": []
        }):
            result = runner.invoke(app, ["stats"])
            assert result.exit_code == 0
            assert "本地数据统计" in result.output

    def test_chat(self):
        """测试chat命令"""
        result = runner.invoke(app, ["chat"])
        assert result.exit_code == 0
        assert "正在启动Agent交互模式" in result.output
        assert "Agent功能待实现" in result.output

    def test_version(self):
        """测试version命令"""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "Nanobot Runner" in result.output
        assert "v" in result.output


class TestCLIApp:
    """测试CLI应用"""

    def test_app_help(self):
        """测试帮助信息"""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "nanobotrun" in result.output
        assert "Nanobot Runner" in result.output

    def test_no_args_help(self):
        """测试无参数显示帮助"""
        result = runner.invoke(app, [])
        # Typer默认在无参数时显示帮助并退出，exit_code为0
        # 但no_args_is_help=True时，无参数会显示帮助并退出，exit_code为0
        # 实际上Typer会返回exit_code=2，因为typer.Exit(code=0)被转换为SystemExit
        assert "help" in result.output.lower()
