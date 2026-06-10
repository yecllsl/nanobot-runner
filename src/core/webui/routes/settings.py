"""设置中心 API 路由 (v0.29.0)

提供个人信息 GET/PUT 和系统配置 GET 共3个端点。
业务逻辑全部委托 ConfigManager，路由层仅做参数转换和响应组装。
"""

from __future__ import annotations

import importlib.metadata
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from src.core.webui.auth import get_current_user

if TYPE_CHECKING:
    from src.core.base.context import AppContext

router = APIRouter()


class ProfileUpdate(BaseModel):
    """个人信息更新请求体"""

    nickname: str | None = None
    age: int | None = Field(None, gt=0)
    gender: str | None = None
    max_heart_rate: int | None = Field(None, gt=0, le=250)
    resting_heart_rate: int | None = Field(None, gt=0, le=150)


def _get_profile(context: AppContext) -> dict[str, Any]:
    """同步获取个人信息配置"""
    config = context.config.load_config()
    profile = config.get("profile", {})
    return {
        "nickname": profile.get("nickname", ""),
        "age": profile.get("age", 0),
        "gender": profile.get("gender", ""),
        "max_heart_rate": profile.get("max_heart_rate", 190),
        "resting_heart_rate": profile.get("resting_heart_rate", 60),
    }


@router.get("/settings/profile")
async def get_profile(
    request: Request,
    user: str = Depends(get_current_user),
) -> dict[str, Any]:
    """获取个人信息配置"""
    context = request.app.state.context
    return await run_in_threadpool(_get_profile, context)


def _update_profile(context: AppContext, update: ProfileUpdate) -> dict[str, Any]:
    """同步更新个人信息配置"""
    config = context.config.load_config()
    profile = config.get("profile", {})
    update_data = update.model_dump(exclude_none=True)
    profile.update(update_data)
    config["profile"] = profile
    context.config.save_config(config)
    return {"success": True, "message": "个人信息已更新"}


@router.put("/settings/profile")
async def update_profile(
    request: Request,
    update: ProfileUpdate,
    user: str = Depends(get_current_user),
) -> dict[str, Any]:
    """更新个人信息配置"""
    context = request.app.state.context
    return await run_in_threadpool(_update_profile, context, update)


def _get_system_config(context: AppContext) -> dict[str, Any]:
    """同步获取系统配置（只读）"""
    webui_config = context.config.get_webui_config()
    # 动态读取包版本号，避免硬编码
    try:
        version = importlib.metadata.version("nanobot-runner")
    except importlib.metadata.PackageNotFoundError:
        version = "dev"
    return {
        "data_dir": str(context.config.data_dir),
        "version": version,
        "webui_enabled": webui_config.get("enabled", True),
        "webui_port": webui_config.get("port", 8766),
        "gateway_status": "unknown",
    }


@router.get("/settings/system")
async def get_system_config(
    request: Request,
    user: str = Depends(get_current_user),
) -> dict[str, Any]:
    """获取系统配置（只读）"""
    context = request.app.state.context
    return await run_in_threadpool(_get_system_config, context)
