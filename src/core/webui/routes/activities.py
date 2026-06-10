"""活动列表与详情 API 路由 (v0.28.0)

提供跑步活动列表查询和单个活动详情查询。
活动ID使用SHA256哈希字符串，基于 session timestamp 生成。
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from starlette.concurrency import run_in_threadpool

from src.core.webui.auth import get_current_user

if TYPE_CHECKING:
    from src.core.base.context import AppContext

router = APIRouter()


def _compute_session_id(timestamp: str) -> str:
    """根据 session timestamp 计算 SHA256 哈希作为唯一ID

    Args:
        timestamp: 会话时间戳字符串

    Returns:
        str: SHA256 哈希字符串
    """
    return hashlib.sha256(timestamp.encode("utf-8")).hexdigest()


def _get_activities(context: AppContext, limit: int = 20) -> dict[str, Any]:
    """同步获取最近活动列表

    Args:
        context: 应用上下文实例
        limit: 返回数量限制
    """
    try:
        sessions = context.session_repo.get_recent_sessions(limit=limit)
    except Exception:
        # 仓库异常时返回空列表，避免内部错误泄露
        sessions = []

    items = []
    for s in sessions:
        session_dict = s.to_dict() if hasattr(s, "to_dict") else {}
        # 为每个活动添加 session_id（基于 timestamp 的 SHA256 哈希）
        timestamp = session_dict.get("timestamp", "")
        session_dict["session_id"] = _compute_session_id(timestamp)
        items.append(session_dict)

    return {
        "items": items,
        "count": len(sessions),
        "limit": limit,
    }


def _get_activity_detail(context: AppContext, session_id: str) -> dict[str, Any] | None:
    """同步获取单个活动详情（通过SHA256哈希ID）

    Args:
        context: 应用上下文实例
        session_id: 活动的SHA256哈希ID
    """
    # 获取足够多的 session 以搜索目标
    sessions = context.session_repo.get_recent_sessions(limit=100)
    for session in sessions:
        session_dict = session.to_dict() if hasattr(session, "to_dict") else {}
        # 通过 timestamp 计算 SHA256 哈希，与请求的 session_id 匹配
        timestamp = session_dict.get("timestamp", "")
        computed_id = _compute_session_id(timestamp)
        if computed_id == session_id:
            session_dict["session_id"] = computed_id
            return session_dict
    return None


@router.get("/activities")
async def get_activities(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100, description="返回数量限制"),
    user: str = Depends(get_current_user),
) -> dict[str, Any]:
    """获取最近跑步活动列表"""
    context = request.app.state.context
    return await run_in_threadpool(_get_activities, context, limit)


@router.get("/activities/{session_id}")
async def get_activity_detail(
    request: Request,
    session_id: str,
    user: str = Depends(get_current_user),
) -> dict[str, Any]:
    """获取单个跑步活动详情

    Args:
        session_id: 活动ID（SHA256哈希）
    """
    context = request.app.state.context
    result = await run_in_threadpool(_get_activity_detail, context, session_id)
    if result is None:
        raise HTTPException(status_code=404, detail="活动不存在")
    return result
