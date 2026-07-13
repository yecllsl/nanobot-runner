"""Cron 会话绑定集成测试

验证 CronCallbackHandler 接入 nanobot 0.2.2 origin_delivery_context 的完整流程。
"""

import pytest
from nanobot.cron.types import CronJob, CronJobState, CronPayload, CronSchedule

from src.core.plan.cron_callback import CronCallbackHandler


@pytest.mark.anyio
async def test_session_binding_full_flow():
    """测试带完整会话信息的 Cron 任务处理"""
    handler = CronCallbackHandler()

    job = CronJob(
        id="job_001",
        name="session_task",
        enabled=True,
        schedule=CronSchedule(kind="cron", expr="0 9 * * *"),
        payload=CronPayload(
            kind="agent_turn",
            message="会话任务",
            session_key="feishu:12345",
            origin_channel="feishu",
            origin_chat_id="chat_001",
            origin_metadata={"user_id": "user_123"},
        ),
        state=CronJobState(),
        created_at_ms=0,
        updated_at_ms=0,
    )

    result = await handler._handle_default(job)

    assert result is not None
    assert "session=feishu:12345" in result
    assert "channel=feishu" in result


@pytest.mark.anyio
async def test_session_key_only_without_origin():
    """测试仅有 session_key 无 origin 上下文的任务"""
    handler = CronCallbackHandler()

    job = CronJob(
        id="job_002",
        name="simple_session",
        enabled=True,
        schedule=CronSchedule(kind="cron", expr="0 9 * * *"),
        payload=CronPayload(
            kind="agent_turn",
            message="简单会话",
            session_key="telegram:67890",
        ),
        state=CronJobState(),
        created_at_ms=0,
        updated_at_ms=0,
    )

    result = await handler._handle_default(job)
    assert result is not None
    assert "session=telegram:67890" in result


@pytest.mark.anyio
async def test_backward_compatible_no_session():
    """测试无会话信息的向后兼容"""
    handler = CronCallbackHandler()

    job = CronJob(
        id="job_003",
        name="legacy_task",
        enabled=True,
        schedule=CronSchedule(kind="cron", expr="0 9 * * *"),
        payload=CronPayload(kind="agent_turn", message="遗留任务"),
        state=CronJobState(),
        created_at_ms=0,
        updated_at_ms=0,
    )

    result = await handler._handle_default(job)
    assert result is not None
    assert "任务已记录" in result
    assert "session=" not in result
