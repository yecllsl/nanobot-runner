"""训练负荷 API 路由 (v0.28.0)"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, Query, Request
from starlette.concurrency import run_in_threadpool

from src.core.webui.auth import get_current_user

if TYPE_CHECKING:
    from src.core.base.context import AppContext

router = APIRouter()


def _get_training_load(context: AppContext, days: int = 42) -> dict[str, Any]:
    """同步获取训练负荷数据

    Args:
        context: 应用上下文实例
        days: 分析天数
    """
    return context.analytics.get_training_load(days=days)


def _get_training_load_trend(context: AppContext, days: int = 90) -> dict[str, Any]:
    """同步获取训练负荷趋势数据

    Args:
        context: 应用上下文实例
        days: 趋势天数
    """
    return context.analytics.get_training_load_trend(days=days)


@router.get("/training-load")
async def get_training_load(
    request: Request,
    days: int = Query(default=42, ge=7, le=365, description="分析天数"),
    user: str = Depends(get_current_user),
) -> dict[str, Any]:
    """获取训练负荷（ATL/CTL/TSB）"""
    context = request.app.state.context
    return await run_in_threadpool(_get_training_load, context, days)


@router.get("/training-load/trend")
async def get_training_load_trend(
    request: Request,
    days: int = Query(default=90, ge=7, le=365, description="趋势天数"),
    user: str = Depends(get_current_user),
) -> dict[str, Any]:
    """获取训练负荷趋势（每日 TSS/ATL/CTL/TSB）"""
    context = request.app.state.context
    return await run_in_threadpool(_get_training_load_trend, context, days)
