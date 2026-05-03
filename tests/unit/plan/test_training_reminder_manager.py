# TrainingReminderManager 单元测试 - v0.17.0

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.core.plan.notify_tool import NotifyTool, SkipReason
from src.core.plan.training_reminder_manager import (
    ReminderRecord,
    ReminderSchedule,
    ReminderStatus,
    TrainingReminderManager,
)


class TestReminderStatus:
    """ReminderStatus 枚举测试"""

    def test_status_values(self):
        """测试状态值"""
        assert ReminderStatus.PENDING == "pending"
        assert ReminderStatus.SENT == "sent"
        assert ReminderStatus.SKIPPED == "skipped"
        assert ReminderStatus.FAILED == "failed"


class TestReminderRecord:
    """ReminderRecord 数据类测试"""

    def test_record_creation(self):
        """测试记录创建"""
        record = ReminderRecord(
            id="test_001",
            date="2024-01-15",
            scheduled_time="0 7 * * *",
            status=ReminderStatus.SENT,
            message="测试消息",
        )

        assert record.id == "test_001"
        assert record.date == "2024-01-15"
        assert record.status == ReminderStatus.SENT
        assert record.message == "测试消息"
        assert record.skip_reason is None
        assert record.executed_at is None

    def test_record_with_skip_reason(self):
        """测试带跳过原因的记录"""
        record = ReminderRecord(
            id="test_002",
            date="2024-01-15",
            scheduled_time="0 7 * * *",
            status=ReminderStatus.SKIPPED,
            message="已跳过",
            skip_reason=SkipReason.DISABLED.value,
        )

        assert record.skip_reason == SkipReason.DISABLED.value


class TestReminderSchedule:
    """ReminderSchedule 数据类测试"""

    def test_default_schedule(self):
        """测试默认调度配置"""
        schedule = ReminderSchedule()

        assert schedule.enabled is True
        assert schedule.cron_expression == "0 7 * * *"
        assert schedule.advance_minutes == 30
        assert schedule.check_weather is True
        assert schedule.do_not_disturb_start == "22:00"
        assert schedule.do_not_disturb_end == "07:00"

    def test_custom_schedule(self):
        """测试自定义调度配置"""
        schedule = ReminderSchedule(
            enabled=False,
            cron_expression="0 8 * * *",
            advance_minutes=60,
        )

        assert schedule.enabled is False
        assert schedule.cron_expression == "0 8 * * *"
        assert schedule.advance_minutes == 60


class TestTrainingReminderManagerInit:
    """TrainingReminderManager 初始化测试"""

    def test_init_with_defaults(self):
        """测试使用默认值初始化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            manager = TrainingReminderManager(data_dir=data_dir)

            assert manager.notify_tool is not None
            assert manager.data_dir == data_dir
            assert manager.history_file == data_dir / "reminder_history.json"
            assert isinstance(manager.schedule, ReminderSchedule)
            assert isinstance(manager.history, list)

    def test_init_with_custom_notify_tool(self):
        """测试使用自定义NotifyTool初始化"""
        mock_notify = MagicMock(spec=NotifyTool)
        manager = TrainingReminderManager(notify_tool=mock_notify)

        assert manager.notify_tool == mock_notify

    def test_init_loads_existing_history(self):
        """测试初始化时加载已有历史"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            history_file = data_dir / "reminder_history.json"

            # 创建历史记录文件
            history_data = [
                {
                    "id": "reminder_20240115_070000",
                    "date": "2024-01-15",
                    "scheduled_time": "0 7 * * *",
                    "status": "sent",
                    "message": "提醒发送成功",
                    "skip_reason": None,
                    "created_at": "2024-01-15T07:00:00",
                    "executed_at": "2024-01-15T07:00:00",
                }
            ]

            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(history_data, f)

            manager = TrainingReminderManager(data_dir=data_dir)

            assert len(manager.history) == 1
            assert manager.history[0].id == "reminder_20240115_070000"
            assert manager.history[0].status == ReminderStatus.SENT


class TestOnReminderTrigger:
    """on_reminder_trigger 方法测试"""

    def test_trigger_when_disabled(self):
        """测试提醒功能禁用时触发"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            manager = TrainingReminderManager(data_dir=data_dir)
            manager.schedule.enabled = False

            result = manager.on_reminder_trigger()

            assert result["success"] is True
            assert result["sent"] is False
            assert result["reason"] == "disabled"
            assert result["record"]["status"] == "skipped"

    def test_trigger_no_plan(self):
        """测试无训练计划时触发"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            manager = TrainingReminderManager(data_dir=data_dir)

            # 模拟无训练计划
            with patch.object(manager, "_get_today_plan", return_value=None):
                result = manager.on_reminder_trigger()

            assert result["success"] is True
            assert result["sent"] is False
            assert result["reason"] == "no_plan"
            assert result["record"]["status"] == "skipped"

    def test_trigger_do_not_disturb(self):
        """测试免打扰时段触发"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            manager = TrainingReminderManager(data_dir=data_dir)

            # 设置免打扰时段为当前时间
            now = datetime.now()
            current_time = now.strftime("%H:%M")
            manager.schedule.do_not_disturb_start = current_time
            manager.schedule.do_not_disturb_end = (now + timedelta(minutes=1)).strftime(
                "%H:%M"
            )

            # 模拟有训练计划
            mock_plan = MagicMock()
            with patch.object(manager, "_get_today_plan", return_value=mock_plan):
                result = manager.on_reminder_trigger()

            assert result["success"] is True
            assert result["sent"] is False
            assert result["reason"] == "do_not_disturb"
            assert result["record"]["status"] == "skipped"

    def test_trigger_send_success(self):
        """测试成功发送提醒"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            manager = TrainingReminderManager(data_dir=data_dir)

            # 设置免打扰时段为过去，避免触发
            manager.schedule.do_not_disturb_start = "22:00"
            manager.schedule.do_not_disturb_end = "23:00"

            # 模拟有训练计划
            mock_plan = MagicMock()

            # 模拟发送成功
            mock_result = MagicMock()
            mock_result.sent = True
            mock_result.skipped = False
            mock_result.message = "发送成功"

            with patch.object(manager, "_get_today_plan", return_value=mock_plan):
                with patch.object(manager, "_send_reminder", return_value=mock_result):
                    result = manager.on_reminder_trigger()

            assert result["success"] is True
            assert result["sent"] is True
            assert result["record"]["status"] == "sent"

    def test_trigger_send_failed(self):
        """测试发送提醒失败"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            manager = TrainingReminderManager(data_dir=data_dir)

            # 设置免打扰时段为过去
            manager.schedule.do_not_disturb_start = "22:00"
            manager.schedule.do_not_disturb_end = "23:00"

            mock_plan = MagicMock()

            # 模拟发送失败
            mock_result = MagicMock()
            mock_result.sent = False
            mock_result.skipped = False
            mock_result.message = "发送失败"

            with patch.object(manager, "_get_today_plan", return_value=mock_plan):
                with patch.object(manager, "_send_reminder", return_value=mock_result):
                    result = manager.on_reminder_trigger()

            assert result["success"] is False
            assert result["sent"] is False
            assert result["reason"] == "failed"
            assert result["record"]["status"] == "failed"

    def test_trigger_send_exception(self):
        """测试发送提醒异常"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            manager = TrainingReminderManager(data_dir=data_dir)

            # 设置免打扰时段为过去
            manager.schedule.do_not_disturb_start = "22:00"
            manager.schedule.do_not_disturb_end = "23:00"

            mock_plan = MagicMock()

            with patch.object(manager, "_get_today_plan", return_value=mock_plan):
                with patch.object(
                    manager, "_send_reminder", side_effect=Exception("发送异常")
                ):
                    result = manager.on_reminder_trigger()

            assert result["success"] is False
            assert result["sent"] is False
            assert result["reason"] == "exception"
            assert result["record"]["status"] == "failed"


class TestCheckDoNotDisturb:
    """_check_do_not_disturb 方法测试"""

    def test_within_do_not_disturb(self):
        """测试在免打扰时段内"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            manager = TrainingReminderManager(data_dir=data_dir)

            # 设置当前时间在免打扰时段内
            now = datetime.now()
            manager.schedule.do_not_disturb_start = now.strftime("%H:%M")
            manager.schedule.do_not_disturb_end = (now + timedelta(hours=1)).strftime(
                "%H:%M"
            )

            result = manager._check_do_not_disturb()

            assert result is not None
            assert "免打扰时段" in result

    def test_outside_do_not_disturb(self):
        """测试在免打扰时段外"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            manager = TrainingReminderManager(data_dir=data_dir)

            # 设置免打扰时段为过去
            now = datetime.now()
            manager.schedule.do_not_disturb_start = (now - timedelta(hours=2)).strftime(
                "%H:%M"
            )
            manager.schedule.do_not_disturb_end = (now - timedelta(hours=1)).strftime(
                "%H:%M"
            )

            result = manager._check_do_not_disturb()

            assert result is None

    def test_cross_midnight_do_not_disturb(self):
        """测试跨午夜免打扰时段"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            manager = TrainingReminderManager(data_dir=data_dir)

            # 设置跨午夜免打扰（22:00 - 07:00）
            manager.schedule.do_not_disturb_start = "22:00"
            manager.schedule.do_not_disturb_end = "07:00"

            # 当前时间设为 23:00（在免打扰时段内）
            with patch(
                "src.core.plan.training_reminder_manager.datetime"
            ) as mock_datetime:
                mock_now = datetime(2024, 1, 15, 23, 0)
                mock_datetime.now.return_value = mock_now

                result = manager._check_do_not_disturb()

                assert result is not None
                assert "免打扰时段" in result


class TestHistoryManagement:
    """历史记录管理测试"""

    def test_get_history(self):
        """测试获取历史记录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            manager = TrainingReminderManager(data_dir=data_dir)

            # 添加测试记录
            today = datetime.now().strftime("%Y-%m-%d")
            manager.history = [
                ReminderRecord(
                    id="test_001",
                    date=today,
                    scheduled_time="0 7 * * *",
                    status=ReminderStatus.SENT,
                    message="测试",
                ),
                ReminderRecord(
                    id="test_002",
                    date=today,
                    scheduled_time="0 7 * * *",
                    status=ReminderStatus.SKIPPED,
                    message="跳过",
                ),
            ]

            # 获取所有记录
            history = manager.get_history(days=7)
            assert len(history) == 2

            # 按状态筛选
            sent_history = manager.get_history(days=7, status=ReminderStatus.SENT)
            assert len(sent_history) == 1
            assert sent_history[0]["status"] == "sent"

    def test_get_today_status(self):
        """测试获取今日状态"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            manager = TrainingReminderManager(data_dir=data_dir)

            # 无记录时
            status = manager.get_today_status()
            assert status["has_record"] is False
            assert status["status"] == "none"

            # 添加今日记录
            today = datetime.now().strftime("%Y-%m-%d")
            manager.history = [
                ReminderRecord(
                    id="test_001",
                    date=today,
                    scheduled_time="0 7 * * *",
                    status=ReminderStatus.SENT,
                    message="测试",
                ),
            ]

            status = manager.get_today_status()
            assert status["has_record"] is True
            assert status["status"] == "sent"

    def test_clear_history(self):
        """测试清理历史记录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            manager = TrainingReminderManager(data_dir=data_dir)

            # 添加旧记录和新记录
            old_date = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
            new_date = datetime.now().strftime("%Y-%m-%d")

            manager.history = [
                ReminderRecord(
                    id="old_001",
                    date=old_date,
                    scheduled_time="0 7 * * *",
                    status=ReminderStatus.SENT,
                    message="旧记录",
                ),
                ReminderRecord(
                    id="new_001",
                    date=new_date,
                    scheduled_time="0 7 * * *",
                    status=ReminderStatus.SENT,
                    message="新记录",
                ),
            ]

            # 清理30天前的记录
            removed = manager.clear_history(days=30)

            assert removed == 1
            assert len(manager.history) == 1
            assert manager.history[0].id == "new_001"


class TestUpdateSchedule:
    """update_schedule 方法测试"""

    def test_update_enabled(self):
        """测试更新启用状态"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            manager = TrainingReminderManager(data_dir=data_dir)

            assert manager.schedule.enabled is True

            manager.update_schedule(enabled=False)

            assert manager.schedule.enabled is False

    def test_update_cron_expression(self):
        """测试更新cron表达式"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            manager = TrainingReminderManager(data_dir=data_dir)

            manager.update_schedule(cron_expression="0 8 * * *")

            assert manager.schedule.cron_expression == "0 8 * * *"

    def test_update_multiple(self):
        """测试同时更新多个配置"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            manager = TrainingReminderManager(data_dir=data_dir)

            manager.update_schedule(
                enabled=False,
                advance_minutes=60,
                check_weather=False,
            )

            assert manager.schedule.enabled is False
            assert manager.schedule.advance_minutes == 60
            assert manager.schedule.check_weather is False


class TestSaveAndLoadHistory:
    """历史记录保存和加载测试"""

    def test_save_history(self):
        """测试保存历史记录到文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            manager = TrainingReminderManager(data_dir=data_dir)

            today = datetime.now().strftime("%Y-%m-%d")
            manager.history = [
                ReminderRecord(
                    id="test_001",
                    date=today,
                    scheduled_time="0 7 * * *",
                    status=ReminderStatus.SENT,
                    message="测试",
                ),
            ]

            manager._save_history()

            # 验证文件存在
            assert manager.history_file.exists()

            # 验证文件内容
            with open(manager.history_file, encoding="utf-8") as f:
                data = json.load(f)

            assert len(data) == 1
            assert data[0]["id"] == "test_001"
            assert data[0]["status"] == "sent"

    def test_load_corrupted_history(self):
        """测试加载损坏的历史文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            history_file = data_dir / "reminder_history.json"

            # 写入损坏的JSON
            with open(history_file, "w", encoding="utf-8") as f:
                f.write("invalid json")

            manager = TrainingReminderManager(data_dir=data_dir)

            # 应返回空列表而不是抛出异常
            assert isinstance(manager.history, list)
            assert len(manager.history) == 0

    def test_max_history_limit(self):
        """测试历史记录数量限制"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            manager = TrainingReminderManager(data_dir=data_dir)

            # 创建超过最大限制的记录
            manager.history = [
                ReminderRecord(
                    id=f"test_{i:03d}",
                    date="2024-01-15",
                    scheduled_time="0 7 * * *",
                    status=ReminderStatus.SENT,
                    message=f"记录{i}",
                )
                for i in range(150)
            ]

            manager._save_history()

            # 验证只保存了最近的100条
            with open(manager.history_file, encoding="utf-8") as f:
                data = json.load(f)

            assert len(data) == 100


class TestSendReminder:
    """_send_reminder 方法测试"""

    def test_send_reminder_calls_notify_tool(self):
        """测试_send_reminder调用NotifyTool"""
        mock_notify = MagicMock(spec=NotifyTool)
        mock_result = MagicMock()
        mock_notify.send_reminder.return_value = mock_result

        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            manager = TrainingReminderManager(
                notify_tool=mock_notify,
                data_dir=data_dir,
            )

            mock_plan = MagicMock()
            result = manager._send_reminder(mock_plan)

            assert result == mock_result
            mock_notify.send_reminder.assert_called_once()

            # 验证调用参数
            call_args = mock_notify.send_reminder.call_args
            assert call_args.kwargs["daily_plan"] == mock_plan
            assert call_args.kwargs["check_do_not_disturb"] is False
