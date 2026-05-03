# CLI Cron 命令单元测试 - v0.17.0

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from src.cli.app import app
from src.core.plan.training_reminder_manager import (
    ReminderSchedule,
    TrainingReminderManager,
)

runner = CliRunner()


def _create_mock_manager(data_dir: Path, **kwargs):
    """创建带控制的 TrainingReminderManager mock"""
    manager = MagicMock(spec=TrainingReminderManager)

    # 配置 schedule
    schedule = ReminderSchedule(**kwargs)
    manager.schedule = schedule

    # 配置历史记录
    manager.history = []
    manager.get_history.return_value = []
    manager.get_today_status.return_value = {"has_record": False}

    # 配置数据目录
    manager.data_dir = data_dir
    manager.HISTORY_FILE = "reminder_history.json"
    manager.history_file = data_dir / "reminder_history.json"

    return manager


# Patch 目标：因为 TrainingReminderManager 是在函数内部导入的，
# 我们需要 patch 它实际被导入的位置
PATCH_TARGET = "src.core.plan.training_reminder_manager.TrainingReminderManager"


class TestCronStatus:
    """cron status 命令测试"""

    def test_status_output(self):
        """测试状态命令输出"""
        data_dir = Path(tempfile.mkdtemp())

        try:
            with patch(PATCH_TARGET) as MockManager:
                mock_manager = _create_mock_manager(data_dir, enabled=True)
                MockManager.return_value = mock_manager

                result = runner.invoke(app, ["cron", "status"])

            assert result.exit_code == 0
            assert "训练提醒配置" in result.output
            assert "今日提醒状态" in result.output
            assert "已启用" in result.output
        finally:
            import shutil

            shutil.rmtree(data_dir, ignore_errors=True)

    def test_status_disabled(self):
        """测试禁用状态输出"""
        data_dir = Path(tempfile.mkdtemp())

        try:
            with patch(PATCH_TARGET) as MockManager:
                mock_manager = _create_mock_manager(data_dir, enabled=False)
                MockManager.return_value = mock_manager

                result = runner.invoke(app, ["cron", "status"])

            assert result.exit_code == 0
            assert "已禁用" in result.output
        finally:
            import shutil

            shutil.rmtree(data_dir, ignore_errors=True)

    def test_status_with_history(self):
        """测试有历史记录的状态命令"""
        data_dir = Path(tempfile.mkdtemp())

        try:
            with patch(PATCH_TARGET) as MockManager:
                mock_manager = _create_mock_manager(data_dir)
                today = datetime.now().strftime("%Y-%m-%d")
                mock_manager.get_today_status.return_value = {
                    "has_record": True,
                    "status": "sent",
                    "message": "测试消息",
                    "executed_at": "2024-01-01T07:00:00",
                }
                mock_manager.get_history.return_value = [
                    {
                        "id": "test_001",
                        "date": today,
                        "status": "sent",
                        "message": "测试消息",
                    }
                ]
                MockManager.return_value = mock_manager

                result = runner.invoke(app, ["cron", "status"])

            assert result.exit_code == 0
            assert "测试消息" in result.output
        finally:
            import shutil

            shutil.rmtree(data_dir, ignore_errors=True)


class TestCronEnable:
    """cron enable 命令测试"""

    def test_enable_default(self):
        """测试默认启用命令"""
        data_dir = Path(tempfile.mkdtemp())

        try:
            with patch(PATCH_TARGET) as MockManager:
                mock_manager = _create_mock_manager(data_dir)
                mock_manager.update_schedule.return_value = None
                MockManager.return_value = mock_manager

                result = runner.invoke(app, ["cron", "enable"])

            assert result.exit_code == 0
            assert "训练提醒已启用" in result.output
            assert "0 7 * * *" in result.output

            # 验证 update_schedule 被调用
            mock_manager.update_schedule.assert_called_once()
            call_kwargs = mock_manager.update_schedule.call_args.kwargs
            assert call_kwargs["enabled"] is True
        finally:
            import shutil

            shutil.rmtree(data_dir, ignore_errors=True)

    def test_enable_custom_cron(self):
        """测试自定义cron表达式启用"""
        data_dir = Path(tempfile.mkdtemp())

        try:
            with patch(PATCH_TARGET) as MockManager:
                mock_manager = _create_mock_manager(data_dir)
                mock_manager.update_schedule.return_value = None
                MockManager.return_value = mock_manager

                result = runner.invoke(
                    app, ["cron", "enable", "--cron", "0 6 * * *", "--advance", "60"]
                )

            assert result.exit_code == 0
            assert "0 6 * * *" in result.output
            assert "60" in result.output
        finally:
            import shutil

            shutil.rmtree(data_dir, ignore_errors=True)

    def test_enable_no_weather(self):
        """测试禁用天气检查启用"""
        data_dir = Path(tempfile.mkdtemp())

        try:
            with patch(PATCH_TARGET) as MockManager:
                mock_manager = _create_mock_manager(data_dir)
                mock_manager.update_schedule.return_value = None
                MockManager.return_value = mock_manager

                result = runner.invoke(app, ["cron", "enable", "--no-weather"])

            assert result.exit_code == 0
            assert "关闭" in result.output
        finally:
            import shutil

            shutil.rmtree(data_dir, ignore_errors=True)


class TestCronDisable:
    """cron disable 命令测试"""

    def test_disable(self):
        """测试禁用命令"""
        data_dir = Path(tempfile.mkdtemp())

        try:
            with patch(PATCH_TARGET) as MockManager:
                mock_manager = _create_mock_manager(data_dir)
                mock_manager.update_schedule.return_value = None
                MockManager.return_value = mock_manager

                result = runner.invoke(app, ["cron", "disable"])

            assert result.exit_code == 0
            assert "训练提醒已禁用" in result.output
            mock_manager.update_schedule.assert_called_once_with(enabled=False)
        finally:
            import shutil

            shutil.rmtree(data_dir, ignore_errors=True)


class TestCronTrigger:
    """cron trigger 命令测试"""

    def test_trigger_disabled(self):
        """测试触发已禁用的提醒"""
        data_dir = Path(tempfile.mkdtemp())

        try:
            with patch(PATCH_TARGET) as MockManager:
                mock_manager = _create_mock_manager(data_dir, enabled=False)
                mock_manager.on_reminder_trigger.return_value = {
                    "success": True,
                    "sent": False,
                    "reason": "disabled",
                    "record": {"message": "提醒功能已禁用"},
                }
                MockManager.return_value = mock_manager

                result = runner.invoke(app, ["cron", "trigger"])

            assert result.exit_code == 0
            assert "提醒功能已禁用" in result.output
        finally:
            import shutil

            shutil.rmtree(data_dir, ignore_errors=True)

    def test_trigger_no_plan(self):
        """测试触发无训练计划"""
        data_dir = Path(tempfile.mkdtemp())

        try:
            with patch(PATCH_TARGET) as MockManager:
                mock_manager = _create_mock_manager(data_dir)
                mock_manager.on_reminder_trigger.return_value = {
                    "success": True,
                    "sent": False,
                    "reason": "no_plan",
                    "record": {"message": "今日无训练计划"},
                }
                MockManager.return_value = mock_manager

                result = runner.invoke(app, ["cron", "trigger"])

            assert result.exit_code == 0
            assert "今日无训练计划" in result.output
        finally:
            import shutil

            shutil.rmtree(data_dir, ignore_errors=True)

    def test_trigger_success(self):
        """测试触发成功"""
        data_dir = Path(tempfile.mkdtemp())

        try:
            with patch(PATCH_TARGET) as MockManager:
                mock_manager = _create_mock_manager(data_dir)
                mock_manager.on_reminder_trigger.return_value = {
                    "success": True,
                    "sent": True,
                    "record": {"message": "提醒发送成功"},
                }
                MockManager.return_value = mock_manager

                result = runner.invoke(app, ["cron", "trigger"])

            assert result.exit_code == 0
            assert "训练提醒已发送" in result.output
        finally:
            import shutil

            shutil.rmtree(data_dir, ignore_errors=True)

    def test_trigger_force(self):
        """测试强制触发"""
        data_dir = Path(tempfile.mkdtemp())

        try:
            with patch(PATCH_TARGET) as MockManager:
                mock_manager = _create_mock_manager(data_dir)
                mock_manager.on_reminder_trigger.return_value = {
                    "success": True,
                    "sent": True,
                    "record": {"message": "强制提醒发送成功"},
                }
                MockManager.return_value = mock_manager

                result = runner.invoke(app, ["cron", "trigger", "--force"])

            assert result.exit_code == 0
            assert "训练提醒已发送" in result.output
        finally:
            import shutil

            shutil.rmtree(data_dir, ignore_errors=True)


class TestCronHistory:
    """cron history 命令测试"""

    def test_history_empty(self):
        """测试空历史记录"""
        data_dir = Path(tempfile.mkdtemp())

        try:
            with patch(PATCH_TARGET) as MockManager:
                mock_manager = _create_mock_manager(data_dir)
                mock_manager.get_history.return_value = []
                MockManager.return_value = mock_manager

                result = runner.invoke(app, ["cron", "history"])

            assert result.exit_code == 0
            assert "无提醒记录" in result.output
        finally:
            import shutil

            shutil.rmtree(data_dir, ignore_errors=True)

    def test_history_with_records(self):
        """测试有历史记录"""
        data_dir = Path(tempfile.mkdtemp())

        try:
            with patch(PATCH_TARGET) as MockManager:
                mock_manager = _create_mock_manager(data_dir)
                today = datetime.now().strftime("%Y-%m-%d")
                mock_manager.get_history.return_value = [
                    {
                        "id": "test_001",
                        "date": today,
                        "status": "sent",
                        "message": "测试消息",
                    },
                    {
                        "id": "test_002",
                        "date": today,
                        "status": "skipped",
                        "message": "跳过消息",
                        "skip_reason": "无训练计划",
                    },
                ]
                MockManager.return_value = mock_manager

                result = runner.invoke(app, ["cron", "history"])

            assert result.exit_code == 0
            assert "测试消息" in result.output
            assert "跳过消息" in result.output
        finally:
            import shutil

            shutil.rmtree(data_dir, ignore_errors=True)

    def test_history_clear(self):
        """测试清理历史记录"""
        data_dir = Path(tempfile.mkdtemp())

        try:
            with patch(PATCH_TARGET) as MockManager:
                mock_manager = _create_mock_manager(data_dir)
                mock_manager.clear_history.return_value = 5
                MockManager.return_value = mock_manager

                result = runner.invoke(app, ["cron", "history", "--clear"])

            assert result.exit_code == 0
            assert "已清理" in result.output
            assert "5" in result.output
        finally:
            import shutil

            shutil.rmtree(data_dir, ignore_errors=True)

    def test_history_days_option(self):
        """测试指定天数的历史记录"""
        data_dir = Path(tempfile.mkdtemp())

        try:
            with patch(PATCH_TARGET) as MockManager:
                mock_manager = _create_mock_manager(data_dir)
                mock_manager.get_history.return_value = []
                MockManager.return_value = mock_manager

                result = runner.invoke(app, ["cron", "history", "--days", "30"])

            assert result.exit_code == 0
            assert "最近 30 天" in result.output
        finally:
            import shutil

            shutil.rmtree(data_dir, ignore_errors=True)
