# 日历同步工具
# 扩展FeishuCalendarSync，支持完整的增删改生命周期管理

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from src.core.config.manager import ConfigManager
from src.core.models import DailyPlan, TrainingPlan
from src.notify.feishu_calendar import (
    CalendarSyncConfig,
    FeishuCalendarSync,
    SyncResult,
)

logger = logging.getLogger(__name__)


class SyncMode(StrEnum):
    """同步模式"""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class HealthCheckItem(StrEnum):
    """健康检查项"""

    NETWORK = "network"
    TOKEN = "token"  # nosec B105  # 枚举值，非真实密码
    CALENDAR_PERMISSION = "calendar_permission"
    CALENDAR_ID = "calendar_id"


@dataclass
class HealthCheckResult:
    """健康检查结果"""

    healthy: bool
    item: HealthCheckItem
    message: str
    details: dict[str, Any] | None = None


@dataclass
class BatchSyncResult:
    """批量同步结果"""

    success: bool
    message: str
    total_count: int
    synced_count: int
    failed_count: int
    event_ids: list[str] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class OptimisticUpdateContext:
    """乐观更新上下文"""

    plan_id: str
    event_id: str
    daily_plan: DailyPlan
    date: datetime
    rollback_data: dict[str, Any] | None = None


class CalendarTool:
    """日历同步工具"""

    def __init__(
        self,
        config_manager: ConfigManager | None = None,
        config: CalendarSyncConfig | None = None,
    ):
        """
        初始化日历同步工具

        Args:
            config_manager: 配置管理器，不指定则创建默认实例
            config: 同步配置，不指定则从配置文件读取
        """
        self._sync_service = FeishuCalendarSync(
            config_manager=config_manager, config=config
        )
        self._optimistic_contexts: dict[str, OptimisticUpdateContext] = {}

    async def pre_sync_check(
        self, check_items: list[HealthCheckItem] | None = None
    ) -> list[HealthCheckResult]:
        """
        预同步检查（健康检测）

        Args:
            check_items: 检查项列表，不指定则检查全部

        Returns:
            List[HealthCheckResult]: 检查结果列表
        """
        if check_items is None:
            check_items = list(HealthCheckItem)

        results = []

        for item in check_items:
            try:
                if item == HealthCheckItem.NETWORK:
                    result = await self._check_network()
                elif item == HealthCheckItem.TOKEN:
                    result = await self._check_token()
                elif item == HealthCheckItem.CALENDAR_PERMISSION:
                    result = await self._check_calendar_permission()
                elif item == HealthCheckItem.CALENDAR_ID:
                    result = await self._check_calendar_id()
                else:
                    result = HealthCheckResult(
                        healthy=False,
                        item=item,
                        message=f"未知的检查项：{item}",
                    )
            except Exception as e:
                result = HealthCheckResult(
                    healthy=False,
                    item=item,
                    message=f"检查异常：{str(e)}",
                )

            results.append(result)

        return results

    async def _check_network(self) -> HealthCheckResult:
        """检查网络连接"""
        try:
            import requests

            response = requests.get("https://open.feishu.cn", timeout=5)
            if response.status_code == 200:
                return HealthCheckResult(
                    healthy=True,
                    item=HealthCheckItem.NETWORK,
                    message="网络连接正常",
                )
            else:
                return HealthCheckResult(
                    healthy=False,
                    item=HealthCheckItem.NETWORK,
                    message=f"网络连接异常，状态码：{response.status_code}",
                )
        except Exception as e:
            return HealthCheckResult(
                healthy=False,
                item=HealthCheckItem.NETWORK,
                message=f"网络连接失败：{str(e)}",
            )

    async def _check_token(self) -> HealthCheckResult:
        """检查访问令牌"""
        try:
            if not self._sync_service._api:
                return HealthCheckResult(
                    healthy=False,
                    item=HealthCheckItem.TOKEN,
                    message="飞书 API 未初始化",
                )

            token = self._sync_service._api._get_access_token()
            if token:
                return HealthCheckResult(
                    healthy=True,
                    item=HealthCheckItem.TOKEN,
                    message="访问令牌有效",
                )
            else:
                return HealthCheckResult(
                    healthy=False,
                    item=HealthCheckItem.TOKEN,
                    message="访问令牌获取失败",
                )
        except Exception as e:
            return HealthCheckResult(
                healthy=False,
                item=HealthCheckItem.TOKEN,
                message=f"访问令牌检查失败：{str(e)}",
            )

    async def _check_calendar_permission(self) -> HealthCheckResult:
        """检查日历权限"""
        try:
            if not self._sync_service._api:
                return HealthCheckResult(
                    healthy=False,
                    item=HealthCheckItem.CALENDAR_PERMISSION,
                    message="飞书 API 未初始化",
                )

            calendars = await self._sync_service._api.get_calendar_list()
            if calendars:
                return HealthCheckResult(
                    healthy=True,
                    item=HealthCheckItem.CALENDAR_PERMISSION,
                    message=f"日历权限正常，可用日历数：{len(calendars)}",
                    details={"calendar_count": len(calendars)},
                )
            else:
                return HealthCheckResult(
                    healthy=False,
                    item=HealthCheckItem.CALENDAR_PERMISSION,
                    message="无可用的日历",
                )
        except Exception as e:
            return HealthCheckResult(
                healthy=False,
                item=HealthCheckItem.CALENDAR_PERMISSION,
                message=f"日历权限检查失败：{str(e)}",
            )

    async def _check_calendar_id(self) -> HealthCheckResult:
        """检查日历ID配置"""
        calendar_id = self._sync_service._get_default_calendar_id()
        if calendar_id:
            return HealthCheckResult(
                healthy=True,
                item=HealthCheckItem.CALENDAR_ID,
                message=f"日历ID已配置：{calendar_id}",
                details={"calendar_id": calendar_id},
            )
        else:
            return HealthCheckResult(
                healthy=False,
                item=HealthCheckItem.CALENDAR_ID,
                message="日历ID未配置",
            )

    async def sync_plan(
        self, plan: TrainingPlan, mode: SyncMode = SyncMode.CREATE
    ) -> SyncResult:
        """
        同步训练计划到日历

        Args:
            plan: 训练计划
            mode: 同步模式

        Returns:
            SyncResult: 同步结果
        """
        if mode == SyncMode.CREATE:
            return await self._sync_service.sync_plan(plan)
        elif mode == SyncMode.UPDATE:
            return await self._update_plan_events(plan)
        elif mode == SyncMode.DELETE:
            return await self._delete_plan_events(plan)
        else:
            return SyncResult(
                success=False,
                message=f"不支持的同步模式：{mode}",
                error="无效的同步模式",
            )

    async def _update_plan_events(self, plan: TrainingPlan) -> SyncResult:
        """更新训练计划的所有事件"""
        if not self._sync_service._api:
            return SyncResult(
                success=False,
                message="飞书 API 未初始化",
                error="API 凭证缺失",
            )

        calendar_id = self._sync_service._get_default_calendar_id()
        if not calendar_id:
            return SyncResult(
                success=False,
                message="未指定日历 ID",
                error="请在配置中设置 calendar_id",
            )

        updated_count = 0
        failed_count = 0

        for week in plan.weeks:
            for daily_plan in week.daily_plans:
                if daily_plan.workout_type.value == "休息":
                    continue

                if not daily_plan.event_id:
                    continue

                try:
                    run_date = datetime.strptime(daily_plan.date, "%Y-%m-%d")
                    result = await self._sync_service.update_event(
                        daily_plan.event_id, daily_plan, run_date
                    )
                    if result.success:
                        updated_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    failed_count += 1
                    logger.error(
                        f"更新训练计划事件失败：{daily_plan.date} - {str(e)}",
                        exc_info=True,
                    )

        if failed_count == 0:
            return SyncResult(
                success=True,
                message=f"成功更新 {updated_count} 个训练事件",
                details={"updated_count": updated_count},
            )
        else:
            return SyncResult(
                success=True,
                message=f"更新完成：成功 {updated_count} 个，失败 {failed_count} 个",
                error=f"有 {failed_count} 个事件更新失败",
                details={"updated_count": updated_count, "failed_count": failed_count},
            )

    async def _delete_plan_events(self, plan: TrainingPlan) -> SyncResult:
        """删除训练计划的所有事件"""
        if not self._sync_service._api:
            return SyncResult(
                success=False,
                message="飞书 API 未初始化",
                error="API 凭证缺失",
            )

        calendar_id = self._sync_service._get_default_calendar_id()
        if not calendar_id:
            return SyncResult(
                success=False,
                message="未指定日历 ID",
                error="请在配置中设置 calendar_id",
            )

        deleted_count = 0
        failed_count = 0

        for week in plan.weeks:
            for daily_plan in week.daily_plans:
                if not daily_plan.event_id:
                    continue

                try:
                    await self._sync_service._api.delete_event(
                        calendar_id, daily_plan.event_id
                    )
                    deleted_count += 1
                    logger.info(
                        f"删除训练计划事件成功：{daily_plan.date} - {daily_plan.event_id}"
                    )
                except Exception as e:
                    failed_count += 1
                    logger.error(
                        f"删除训练计划事件失败：{daily_plan.date} - {str(e)}",
                        exc_info=True,
                    )

        if failed_count == 0:
            return SyncResult(
                success=True,
                message=f"成功删除 {deleted_count} 个训练事件",
                details={"deleted_count": deleted_count},
            )
        else:
            return SyncResult(
                success=True,
                message=f"删除完成：成功 {deleted_count} 个，失败 {failed_count} 个",
                error=f"有 {failed_count} 个事件删除失败",
                details={"deleted_count": deleted_count, "failed_count": failed_count},
            )

    async def optimistic_update(
        self, plan: TrainingPlan, daily_plan: DailyPlan, date: datetime
    ) -> SyncResult:
        """
        乐观更新（预分配 event_id）

        Args:
            plan: 训练计划
            daily_plan: 日训练计划
            date: 日期

        Returns:
            SyncResult: 同步结果
        """
        import uuid

        plan_id = plan.plan_id
        temp_event_id = f"temp_{uuid.uuid4().hex[:16]}"

        context = OptimisticUpdateContext(
            plan_id=plan_id,
            event_id=temp_event_id,
            daily_plan=daily_plan,
            date=date,
            rollback_data={"original_event_id": daily_plan.event_id},
        )

        self._optimistic_contexts[temp_event_id] = context

        try:
            daily_plan.event_id = temp_event_id

            result = await self._sync_service.sync_daily_workout(daily_plan, date)

            if result.success and result.event_id:
                del self._optimistic_contexts[temp_event_id]
                daily_plan.event_id = result.event_id
                return result
            else:
                await self._rollback_optimistic_update(temp_event_id, daily_plan)
                return SyncResult(
                    success=False,
                    message="乐观更新失败，已回滚",
                    error=result.error,
                )

        except Exception as e:
            await self._rollback_optimistic_update(temp_event_id, daily_plan)
            return SyncResult(
                success=False,
                message=f"乐观更新异常，已回滚：{str(e)}",
                error=str(e),
            )

    async def _rollback_optimistic_update(
        self, temp_event_id: str, daily_plan: DailyPlan
    ) -> None:
        """回滚乐观更新"""
        context = self._optimistic_contexts.get(temp_event_id)
        if context:
            if context.rollback_data and "original_event_id" in context.rollback_data:
                daily_plan.event_id = context.rollback_data["original_event_id"]
            del self._optimistic_contexts[temp_event_id]
            logger.info(f"已回滚乐观更新：{temp_event_id}")

    async def batch_sync(
        self,
        plans: list[TrainingPlan],
        mode: SyncMode = SyncMode.CREATE,
        batch_size: int = 10,
    ) -> BatchSyncResult:
        """
        批量同步训练计划

        Args:
            plans: 训练计划列表
            mode: 同步模式
            batch_size: 批次大小

        Returns:
            BatchSyncResult: 批量同步结果
        """
        total_count = len(plans)
        synced_count = 0
        failed_count = 0
        all_event_ids: list[str] = []
        all_errors: list[dict[str, Any]] = []

        for i in range(0, total_count, batch_size):
            batch = plans[i : i + batch_size]

            for plan in batch:
                try:
                    result = await self.sync_plan(plan, mode)

                    if result.success:
                        synced_count += 1
                        if result.details and "event_ids" in result.details:
                            all_event_ids.extend(result.details["event_ids"])
                    else:
                        failed_count += 1
                        all_errors.append(
                            {
                                "plan_id": plan.plan_id,
                                "error": result.error,
                                "message": result.message,
                            }
                        )

                except Exception as e:
                    failed_count += 1
                    all_errors.append(
                        {
                            "plan_id": plan.plan_id,
                            "error": str(e),
                            "message": f"同步异常：{str(e)}",
                        }
                    )

        success = failed_count == 0
        if success:
            message = f"批量同步成功，共 {synced_count} 个计划"
        else:
            message = f"批量同步完成：成功 {synced_count} 个，失败 {failed_count} 个"

        return BatchSyncResult(
            success=success,
            message=message,
            total_count=total_count,
            synced_count=synced_count,
            failed_count=failed_count,
            event_ids=all_event_ids,
            errors=all_errors,
        )

    async def sync_daily_workout(
        self, daily_plan: DailyPlan, date: datetime, mode: SyncMode = SyncMode.CREATE
    ) -> SyncResult:
        """
        同步单日训练到日历

        Args:
            daily_plan: 日训练计划
            date: 日期
            mode: 同步模式

        Returns:
            SyncResult: 同步结果
        """
        if mode == SyncMode.CREATE:
            return await self._sync_service.sync_daily_workout(daily_plan, date)
        elif mode == SyncMode.UPDATE:
            if not daily_plan.event_id:
                return SyncResult(
                    success=False,
                    message="无法更新：事件ID不存在",
                    error="缺少event_id",
                )
            return await self._sync_service.update_event(
                daily_plan.event_id, daily_plan, date
            )
        elif mode == SyncMode.DELETE:
            if not daily_plan.event_id:
                return SyncResult(
                    success=False,
                    message="无法删除：事件ID不存在",
                    error="缺少event_id",
                )

            calendar_id = self._sync_service._get_default_calendar_id()
            if not calendar_id:
                return SyncResult(
                    success=False,
                    message="未指定日历 ID",
                    error="请在配置中设置 calendar_id",
                )

            if not self._sync_service._api:
                return SyncResult(
                    success=False,
                    message="飞书 API 未初始化",
                    error="API 凭证缺失",
                )

            try:
                await self._sync_service._api.delete_event(
                    calendar_id, daily_plan.event_id
                )
                return SyncResult(
                    success=True,
                    message="训练事件已删除",
                    event_id=daily_plan.event_id,
                )
            except Exception as e:
                return SyncResult(
                    success=False,
                    message="删除失败",
                    error=str(e),
                )
        else:
            return SyncResult(
                success=False,
                message=f"不支持的同步模式：{mode}",
                error="无效的同步模式",
            )
