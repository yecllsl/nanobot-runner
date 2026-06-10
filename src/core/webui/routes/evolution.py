"""进化引擎 API 路由 (v0.29.0)

提供进化状态查看、提示参数调优、报告列表/详情等5个端点。
业务逻辑全部委托 EvolutionEngine 公共方法，路由层仅做参数转换和响应组装。

注意: GET /status 仅调用 check_triggers() 检查触发条件，
不执行任何进化动作（retrain_model/adjust_strategy等）。
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from src.core.webui.auth import get_current_user

if TYPE_CHECKING:
    from src.core.base.context import AppContext

router = APIRouter()


class TuningParamsUpdate(BaseModel):
    """提示调优参数更新请求体"""

    tone: float | None = Field(None, ge=0.0, le=1.0)
    detail: float | None = Field(None, ge=0.0, le=1.0)
    aggressive: float | None = Field(None, ge=0.0, le=1.0)
    data_driven: float | None = Field(None, ge=0.0, le=1.0)


def _get_evolution_status(context: AppContext) -> dict[str, Any]:
    """同步获取进化引擎状态（只读，不触发任何进化动作）

    check_triggers() 仅检查触发条件返回 TriggerCheckResult，
    不执行任何进化动作（retrain_model/adjust_strategy等）。
    """
    result = context.evolution_engine.check_evolution_triggers()

    trigger_conditions = [
        {
            "rule": "vdot_error",
            "description": "VDOT预测误差连续3次>5%",
            "is_triggered": any(
                a.action_type == "retrain_model" and "vdot" in a.trigger_reason
                for a in result.triggered_actions
            ),
        },
        {
            "rule": "consecutive_rejection",
            "description": "连续2次拒绝推荐",
            "is_triggered": any(
                a.action_type == "adjust_strategy" for a in result.triggered_actions
            ),
        },
        {
            "rule": "new_data_accumulation",
            "description": "新数据积累>=50条",
            "is_triggered": any(
                a.action_type == "incremental_learn" for a in result.triggered_actions
            ),
        },
        {
            "rule": "monthly_review",
            "description": "当月未生成报告",
            "is_triggered": any(
                a.action_type == "generate_report" for a in result.triggered_actions
            ),
        },
    ]

    recent_actions = [
        {
            "action_type": a.action_type,
            "triggered_at": a.created_at.isoformat()
            if hasattr(a.created_at, "isoformat")
            else str(a.created_at),
            "status": "completed" if a.executed else "pending",
        }
        for a in result.triggered_actions[:5]
    ]

    return {
        "engine_status": "running",
        "trigger_conditions": trigger_conditions,
        "recent_actions": recent_actions,
    }


@router.get("/evolution/status")
async def get_evolution_status(
    request: Request,
    user: str = Depends(get_current_user),
) -> dict[str, Any]:
    """获取进化引擎状态（只读，不触发任何进化动作）"""
    context = request.app.state.context
    return await run_in_threadpool(_get_evolution_status, context)


def _get_tuning_params(context: AppContext) -> dict[str, Any]:
    """同步获取当前提示调优参数"""
    params = context.evolution_engine.get_prompt_tuning_params()
    return {
        "tone": params.tone_intensity,
        "detail": params.detail_level_score,
        "aggressive": params.recommendation_aggressiveness,
        "data_driven": params.data_driven_weight,
    }


@router.get("/evolution/tuning")
async def get_tuning_params(
    request: Request,
    user: str = Depends(get_current_user),
) -> dict[str, Any]:
    """获取当前提示调优参数"""
    context = request.app.state.context
    return await run_in_threadpool(_get_tuning_params, context)


def _update_tuning_params(
    context: AppContext, update: TuningParamsUpdate
) -> dict[str, Any]:
    """同步更新提示调优参数"""
    params = context.evolution_engine.adjust_prompt_params(
        tone=update.tone,
        detail=update.detail,
        aggressive=update.aggressive,
        data_driven=update.data_driven,
    )
    return {
        "tone": params.tone_intensity,
        "detail": params.detail_level_score,
        "aggressive": params.recommendation_aggressiveness,
        "data_driven": params.data_driven_weight,
    }


@router.put("/evolution/tuning")
async def update_tuning_params(
    request: Request,
    update: TuningParamsUpdate,
    user: str = Depends(get_current_user),
) -> dict[str, Any]:
    """更新提示调优参数"""
    context = request.app.state.context
    return await run_in_threadpool(_update_tuning_params, context, update)


def _list_report_months(context: AppContext) -> dict[str, Any]:
    """同步获取可用的进化报告月份列表

    通过扫描 data_dir/decisions/ 目录下的月份子目录（YYYY-MM格式）
    确定可生成报告的月份列表。
    """
    months = context.evolution_engine.get_available_report_months()
    return {"available_months": months, "count": len(months)}


@router.get("/evolution/reports")
async def list_evolution_reports(
    request: Request,
    user: str = Depends(get_current_user),
) -> dict[str, Any]:
    """获取可用的进化报告月份列表"""
    context = request.app.state.context
    return await run_in_threadpool(_list_report_months, context)


def _get_evolution_report(context: AppContext, month: str) -> dict[str, Any]:
    """同步获取指定月份进化报告"""
    report = context.evolution_engine.get_evolution_report(month=month)
    return report.to_dict()


@router.get("/evolution/reports/{month}")
async def get_evolution_report(
    request: Request,
    month: str,
    user: str = Depends(get_current_user),
) -> dict[str, Any]:
    """获取指定月份进化报告"""
    if not re.match(r"\d{4}-\d{2}", month):
        raise HTTPException(status_code=400, detail="月份格式错误，应为YYYY-MM")
    context = request.app.state.context
    return await run_in_threadpool(_get_evolution_report, context, month)
