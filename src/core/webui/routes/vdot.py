"""VDOT 趋势 API 路由 (v0.28.0)"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from starlette.concurrency import run_in_threadpool

from src.core.webui.auth import get_current_user

router = APIRouter()


def _get_vdot_trend(context: Any, days: int = 30) -> dict[str, Any]:
    """同步获取 VDOT 趋势数据

    Args:
        context: 应用上下文实例
        days: 查询天数
    """
    trend_items = context.analytics.get_vdot_trend(days=days)
    return {
        "items": [item.to_dict() for item in trend_items],
        "days": days,
        "count": len(trend_items),
    }


@router.get("/vdot/trend")
async def get_vdot_trend(
    request: Request,
    days: int = Query(default=30, ge=1, le=365, description="查询天数"),
    user: str = Depends(get_current_user),
) -> dict[str, Any]:
    """获取 VDOT 趋势数据"""
    context = request.app.state.context
    return await run_in_threadpool(_get_vdot_trend, context, days)
