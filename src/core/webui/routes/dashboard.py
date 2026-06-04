"""Dashboard 汇总 API 路由 (v0.28.0)

提供 Dashboard 页面所需的汇总数据，一次性返回训练负荷、身体信号等关键指标。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from starlette.concurrency import run_in_threadpool

from src.core.webui.auth import get_current_user

router = APIRouter()


def _get_dashboard_data(context: Any) -> dict[str, Any]:
    """同步获取 Dashboard 汇总数据

    Args:
        context: 应用上下文实例
    """
    # 训练负荷
    training_load = context.analytics.get_training_load(days=42)

    # 身体信号
    body_signal_summary = context.body_signal_engine.get_daily_summary()

    return {
        "training_load": training_load,
        "body_signal": body_signal_summary.to_dict(),
    }


@router.get("/dashboard")
async def get_dashboard(
    request: Request,
    user: str = Depends(get_current_user),
) -> dict[str, Any]:
    """获取 Dashboard 汇总数据"""
    context = request.app.state.context
    return await run_in_threadpool(_get_dashboard_data, context)
