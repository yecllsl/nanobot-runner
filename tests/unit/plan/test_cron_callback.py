# CronCallbackHandler 单元测试 - v0.17.0

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from nanobot.cron.types import CronJob, CronJobState, CronPayload, CronSchedule

from src.core.plan.cron_callback import CronCallbackHandler
from src.core.plan.training_reminder_manager import TrainingReminderManager


class TestCronCallbackHandlerInit:
    """CronCallbackHandler 初始化测试"""

    def test_init_without_reminder_manager(self):
        """测试无提醒管理器初始化"""
        handler = CronCallbackHandler()

        assert handler.reminder_manager is None
        assert handler.TRAINING_REMINDER_JOB == "training_reminder"
        assert handler.SYSTEM_JOB_PREFIX == "system_"

    def test_init_with_reminder_manager(self):
        """测试有提醒管理器初始化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            reminder_manager = TrainingReminderManager(data_dir=data_dir)
            handler = CronCallbackHandler(reminder_manager=reminder_manager)

            assert handler.reminder_manager == reminder_manager


class TestOnJob:
    """on_job 方法测试"""

    @pytest.mark.anyio
    async def test_training_reminder_job_sent(self):
        """测试训练提醒任务发送成功"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            reminder_manager = TrainingReminderManager(data_dir=data_dir)
            handler = CronCallbackHandler(reminder_manager=reminder_manager)

            # 模拟提醒功能已禁用（避免实际发送）
            reminder_manager.schedule.enabled = False

            job = CronJob(
                id="test_001",
                name="training_reminder",
                enabled=True,
                schedule=CronSchedule(kind="cron", expr="0 7 * * *"),
                payload=CronPayload(kind="system_event", message="训练提醒"),
                state=CronJobState(),
                created_at_ms=0,
                updated_at_ms=0,
            )

            result = await handler.on_job(job)

            assert result is not None
            assert "提醒功能已禁用" in result

    @pytest.mark.anyio
    async def test_training_reminder_no_manager(self):
        """测试无提醒管理器时的训练提醒任务"""
        handler = CronCallbackHandler()

        job = CronJob(
            id="test_001",
            name="training_reminder",
            enabled=True,
            schedule=CronSchedule(kind="cron", expr="0 7 * * *"),
            payload=CronPayload(kind="system_event", message="训练提醒"),
            state=CronJobState(),
            created_at_ms=0,
            updated_at_ms=0,
        )

        result = await handler.on_job(job)

        assert result == "提醒管理器未初始化"

    @pytest.mark.anyio
    async def test_system_event_job(self):
        """测试系统事件任务"""
        handler = CronCallbackHandler()

        job = CronJob(
            id="test_002",
            name="system_heartbeat",
            enabled=True,
            schedule=CronSchedule(kind="cron", expr="0 * * * *"),
            payload=CronPayload(kind="system_event", message="心跳检测"),
            state=CronJobState(),
            created_at_ms=0,
            updated_at_ms=0,
        )

        result = await handler.on_job(job)

        assert result is not None
        assert "系统事件已处理" in result

    @pytest.mark.anyio
    async def test_default_job(self):
        """测试默认任务处理"""
        handler = CronCallbackHandler()

        job = CronJob(
            id="test_003",
            name="custom_job",
            enabled=True,
            schedule=CronSchedule(kind="cron", expr="0 9 * * *"),
            payload=CronPayload(kind="agent_turn", message="自定义任务消息"),
            state=CronJobState(),
            created_at_ms=0,
            updated_at_ms=0,
        )

        result = await handler.on_job(job)

        assert result is not None
        assert "任务已记录" in result
        assert "custom_job" in result

    @pytest.mark.anyio
    async def test_default_job_no_payload(self):
        """测试无payload的默认任务"""
        handler = CronCallbackHandler()

        job = CronJob(
            id="test_004",
            name="empty_job",
            enabled=True,
            schedule=CronSchedule(kind="cron", expr="0 9 * * *"),
            payload=CronPayload(kind="agent_turn", message=""),
            state=CronJobState(),
            created_at_ms=0,
            updated_at_ms=0,
        )

        result = await handler.on_job(job)

        assert result is not None
        assert "empty_job" in result

    @pytest.mark.anyio
    async def test_on_job_exception(self):
        """测试on_job异常处理"""
        handler = CronCallbackHandler()

        # 创建一个会触发异常的任务名称
        job = MagicMock()
        job.name = "training_reminder"
        job.id = "test_005"

        # 模拟异常
        with patch.object(
            handler, "_handle_training_reminder", side_effect=Exception("测试异常")
        ):
            with pytest.raises(Exception, match="测试异常"):
                await handler.on_job(job)


class TestHandleTrainingReminder:
    """_handle_training_reminder 方法测试"""

    @pytest.mark.anyio
    async def test_reminder_disabled(self):
        """测试提醒功能禁用"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            reminder_manager = TrainingReminderManager(data_dir=data_dir)
            handler = CronCallbackHandler(reminder_manager=reminder_manager)

            reminder_manager.schedule.enabled = False

            job = CronJob(
                id="test_001",
                name="training_reminder",
                enabled=True,
                schedule=CronSchedule(kind="cron", expr="0 7 * * *"),
                payload=CronPayload(kind="system_event", message="训练提醒"),
                state=CronJobState(),
                created_at_ms=0,
                updated_at_ms=0,
            )

            result = await handler._handle_training_reminder(job)

            assert "提醒功能已禁用" in result

    @pytest.mark.anyio
    async def test_reminder_no_plan(self):
        """测试无训练计划"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            reminder_manager = TrainingReminderManager(data_dir=data_dir)
            handler = CronCallbackHandler(reminder_manager=reminder_manager)

            # 模拟无训练计划
            with patch.object(reminder_manager, "_get_today_plan", return_value=None):
                job = CronJob(
                    id="test_001",
                    name="training_reminder",
                    enabled=True,
                    schedule=CronSchedule(kind="cron", expr="0 7 * * *"),
                    payload=CronPayload(kind="system_event", message="训练提醒"),
                    state=CronJobState(),
                    created_at_ms=0,
                    updated_at_ms=0,
                )

                result = await handler._handle_training_reminder(job)

            assert "今日无训练计划" in result

    @pytest.mark.anyio
    async def test_reminder_do_not_disturb(self):
        """测试免打扰时段"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            reminder_manager = TrainingReminderManager(data_dir=data_dir)
            handler = CronCallbackHandler(reminder_manager=reminder_manager)

            # 设置免打扰时段为当前时间
            from datetime import datetime, timedelta

            now = datetime.now()
            reminder_manager.schedule.do_not_disturb_start = now.strftime("%H:%M")
            reminder_manager.schedule.do_not_disturb_end = (
                now + timedelta(hours=1)
            ).strftime("%H:%M")

            # 模拟有训练计划
            mock_plan = MagicMock()
            with patch.object(
                reminder_manager, "_get_today_plan", return_value=mock_plan
            ):
                job = CronJob(
                    id="test_001",
                    name="training_reminder",
                    enabled=True,
                    schedule=CronSchedule(kind="cron", expr="0 7 * * *"),
                    payload=CronPayload(kind="system_event", message="训练提醒"),
                    state=CronJobState(),
                    created_at_ms=0,
                    updated_at_ms=0,
                )

                result = await handler._handle_training_reminder(job)

            assert "免打扰时段" in result

    @pytest.mark.anyio
    async def test_reminder_sent_success(self):
        """测试提醒发送成功"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            reminder_manager = TrainingReminderManager(data_dir=data_dir)
            handler = CronCallbackHandler(reminder_manager=reminder_manager)

            # 设置免打扰时段为过去
            reminder_manager.schedule.do_not_disturb_start = "22:00"
            reminder_manager.schedule.do_not_disturb_end = "23:00"

            mock_plan = MagicMock()

            # 模拟发送成功
            mock_result = MagicMock()
            mock_result.sent = True
            mock_result.skipped = False
            mock_result.message = "发送成功"

            with patch.object(
                reminder_manager, "_get_today_plan", return_value=mock_plan
            ):
                with patch.object(
                    reminder_manager, "_send_reminder", return_value=mock_result
                ):
                    job = CronJob(
                        id="test_001",
                        name="training_reminder",
                        enabled=True,
                        schedule=CronSchedule(kind="cron", expr="0 7 * * *"),
                        payload=CronPayload(kind="system_event", message="训练提醒"),
                        state=CronJobState(),
                        created_at_ms=0,
                        updated_at_ms=0,
                    )

                    result = await handler._handle_training_reminder(job)

            assert "训练提醒已发送" in result


class TestCreateTrainingReminderJob:
    """create_training_reminder_job 方法测试"""

    def test_create_default_job(self):
        """测试创建默认训练提醒任务"""
        handler = CronCallbackHandler()

        job_config = handler.create_training_reminder_job()

        assert job_config["id"] == "training_reminder"
        assert job_config["name"] == "training_reminder"
        assert job_config["enabled"] is True
        assert job_config["schedule"]["kind"] == "cron"
        assert job_config["schedule"]["expr"] == "0 7 * * *"
        assert job_config["payload"]["kind"] == "system_event"

    def test_create_custom_job(self):
        """测试创建自定义训练提醒任务"""
        handler = CronCallbackHandler()

        job_config = handler.create_training_reminder_job(
            cron_expr="0 8 * * *",
            tz="Asia/Shanghai",
        )

        assert job_config["schedule"]["expr"] == "0 8 * * *"
        assert job_config["schedule"]["tz"] == "Asia/Shanghai"
