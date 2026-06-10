"""训练计划 API 路由 (v0.29.0)

提供训练计划列表、日历视图、详情、进度、单日更新等5个端点。
业务逻辑全部委托 PlanManager，路由层仅做参数转换和响应组装。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from src.core.webui.auth import get_current_user

if TYPE_CHECKING:
    from src.core.base.context import AppContext

router = APIRouter()


class DailyPlanUpdate(BaseModel):
    """单日训练更新请求体"""

    completion_rate: float | None = Field(None, ge=0.0, le=1.0)
    effort_score: int | None = Field(None, ge=1, le=10)
    notes: str = ""
    actual_distance_km: float | None = None
    actual_duration_min: int | None = None
    actual_avg_hr: int | None = None


def _list_plans(context: AppContext, status: str | None, limit: int) -> dict[str, Any]:
    """同步获取训练计划列表"""
    from src.core.models.training_plan import PlanStatus

    plan_status = PlanStatus(status) if status else None
    plans = context.plan_manager.list_plans(status=plan_status, limit=limit)
    return {
        "plans": [
            {
                "plan_id": p.plan_id,
                "name": f"{p.plan_type.label}训练计划",
                "goal": p.goal_date,
                "status": p.status.value,
                "start_date": p.start_date,
                "end_date": p.end_date,
                "total_days": len([d for w in p.weeks for d in w.daily_plans]),
                "completed_days": len(
                    [d for w in p.weeks for d in w.daily_plans if d.completed]
                ),
                "updated_at": p.updated_at.isoformat()
                if hasattr(p.updated_at, "isoformat")
                else str(p.updated_at),
            }
            for p in plans
        ]
    }


@router.get("/plan/list")
async def list_plans(
    request: Request,
    status: str | None = None,
    limit: int = 100,
    user: str = Depends(get_current_user),
) -> dict[str, Any]:
    """获取训练计划列表"""
    context = request.app.state.context
    return await run_in_threadpool(_list_plans, context, status, limit)


def _get_plan_calendar(
    context: AppContext, year: int | None, month: int | None, view: str
) -> dict[str, Any]:
    """同步获取当前活跃计划日历数据"""
    plan = context.plan_manager.get_active_plan()
    if not plan:
        return {"plan_id": None, "plan_name": None, "days": []}

    days = []
    for week in plan.weeks:
        for day in week.daily_plans:
            days.append(
                {
                    "date": day.date,
                    "workout_type": day.workout_type.value,
                    "workout_label": day.workout_type.label,
                    "distance_km": day.distance_km,
                    "target_pace_min_per_km": day.target_pace_min_per_km,
                    "duration_min": day.duration_min,
                    "status": "completed" if day.completed else "pending",
                    "notes": day.notes,
                }
            )

    return {
        "plan_id": plan.plan_id,
        "plan_name": f"{plan.plan_type.label}训练计划",
        "view_mode": view,
        "year": year,
        "month": month,
        "days": days,
    }


@router.get("/plan/calendar")
async def get_plan_calendar(
    request: Request,
    year: int | None = None,
    month: int | None = None,
    view: str = "month",
    user: str = Depends(get_current_user),
) -> dict[str, Any]:
    """获取当前活跃计划日历数据"""
    context = request.app.state.context
    return await run_in_threadpool(_get_plan_calendar, context, year, month, view)


def _get_plan_detail(context: AppContext, plan_id: str) -> dict[str, Any] | None:
    """同步获取训练计划详情"""
    plan = context.plan_manager.get_plan(plan_id)
    if not plan:
        return None
    return plan.to_dict()


@router.get("/plan/{plan_id}")
async def get_plan_detail(
    request: Request,
    plan_id: str,
    user: str = Depends(get_current_user),
) -> dict[str, Any]:
    """获取训练计划详情"""
    context = request.app.state.context
    result = await run_in_threadpool(_get_plan_detail, context, plan_id)
    if result is None:
        raise HTTPException(status_code=404, detail="计划不存在")
    return result


def _get_plan_progress(context: AppContext, plan_id: str) -> dict[str, Any] | None:
    """同步获取计划执行进度"""
    plan = context.plan_manager.get_plan(plan_id)
    if not plan:
        return None

    all_days = [d for w in plan.weeks for d in w.daily_plans]
    completed_days = [d for d in all_days if d.completed]

    weekly_summary = []
    for week in plan.weeks:
        planned_dist = sum(d.distance_km for d in week.daily_plans)
        actual_dist = sum(d.actual_distance_km or 0 for d in week.daily_plans)
        completed = sum(1 for d in week.daily_plans if d.completed)
        weekly_summary.append(
            {
                "week": f"W{week.week_number}",
                "completion_rate": completed / len(week.daily_plans)
                if week.daily_plans
                else 0,
                "planned_distance_km": round(planned_dist, 2),
                "actual_distance_km": round(actual_dist, 2),
            }
        )

    return {
        "plan_id": plan_id,
        "completion_rate": len(completed_days) / len(all_days) if all_days else 0,
        "total_days": len(all_days),
        "completed_days": len(completed_days),
        "avg_fidelity": 0.0,
        "weekly_summary": weekly_summary,
    }


@router.get("/plan/progress/{plan_id}")
async def get_plan_progress(
    request: Request,
    plan_id: str,
    user: str = Depends(get_current_user),
) -> dict[str, Any]:
    """获取计划执行进度"""
    context = request.app.state.context
    result = await run_in_threadpool(_get_plan_progress, context, plan_id)
    if result is None:
        raise HTTPException(status_code=404, detail="计划不存在")
    return result


def _update_daily_plan(
    context: AppContext, plan_id: str, date: str, update: DailyPlanUpdate
) -> dict[str, Any]:
    """同步更新单日训练详情"""
    return context.plan_manager.record_execution(
        plan_id=plan_id,
        date=date,
        completion_rate=update.completion_rate,
        effort_score=update.effort_score,
        notes=update.notes,
        actual_distance_km=update.actual_distance_km,
        actual_duration_min=update.actual_duration_min,
        actual_avg_hr=update.actual_avg_hr,
    )


@router.put("/plan/daily/{plan_id}/{date}")
async def update_daily_plan(
    request: Request,
    plan_id: str,
    date: str,
    update: DailyPlanUpdate,
    user: str = Depends(get_current_user),
) -> dict[str, Any]:
    """更新单日训练详情"""
    context = request.app.state.context
    try:
        return await run_in_threadpool(
            _update_daily_plan, context, plan_id, date, update
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail="请求参数无效") from e
    except KeyError as e:
        raise HTTPException(status_code=404, detail="计划不存在") from e
