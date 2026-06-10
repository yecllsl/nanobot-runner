"""身体信号 API 路由 (v0.28.0)

提供每日/每周身体信号摘要和预警信息查询。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, Request
from starlette.concurrency import run_in_threadpool

from src.core.webui.auth import get_current_user

if TYPE_CHECKING:
    from src.core.base.context import AppContext

router = APIRouter()


def _get_daily_summary(context: AppContext) -> dict[str, Any]:
    """同步获取每日身体信号摘要

    Args:
        context: 应用上下文实例
    """
    summary = context.body_signal_engine.get_daily_summary()
    return summary.to_dict()


def _get_weekly_summary(context: AppContext) -> dict[str, Any]:
    """同步获取每周身体信号摘要

    Args:
        context: 应用上下文实例
    """
    summary = context.body_signal_engine.get_weekly_summary()
    return summary.to_dict()


def _get_alerts(context: AppContext) -> dict[str, Any]:
    """同步获取身体信号预警

    Args:
        context: 应用上下文实例
    """
    alerts = context.body_signal_engine.check_alerts()
    return {
        "alerts": [a.to_dict() for a in alerts],
        "count": len(alerts),
    }


@router.get("/body-signal/daily")
async def get_daily_summary(
    request: Request,
    user: str = Depends(get_current_user),
) -> dict[str, Any]:
    """获取每日身体信号摘要"""
    context = request.app.state.context
    return await run_in_threadpool(_get_daily_summary, context)


@router.get("/body-signal/weekly")
async def get_weekly_summary(
    request: Request,
    user: str = Depends(get_current_user),
) -> dict[str, Any]:
    """获取每周身体信号摘要"""
    context = request.app.state.context
    return await run_in_threadpool(_get_weekly_summary, context)


@router.get("/body-signal/alerts")
async def get_alerts(
    request: Request,
    user: str = Depends(get_current_user),
) -> dict[str, Any]:
    """获取身体信号预警列表"""
    context = request.app.state.context
    return await run_in_threadpool(_get_alerts, context)
