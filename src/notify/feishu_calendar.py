# 飞书日历同步服务
# 实现训练计划与飞书日历的双向同步

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import requests

from src.cli_formatter import format_distance
from src.core.config import ConfigManager
from src.core.training_plan import DailyPlan, TrainingPlan

logger = logging.getLogger(__name__)


@dataclass
class CalendarSyncConfig:
    """日历同步配置"""

    enabled: bool = True
    calendar_id: str | None = None  # 指定日历 ID
    reminder_minutes: int = 60  # 提前提醒时间（分钟）
    sync_completed: bool = False  # 是否同步已完成训练
    include_description: bool = True  # 是否包含详细描述
    app_id: str | None = None  # 飞书应用 App ID
    app_secret: str | None = None  # 飞书应用 App Secret


@dataclass
class SyncResult:
    """同步结果"""

    success: bool
    message: str
    event_id: str | None = None
    error: str | None = None
    details: dict[str, Any] | None = None


@dataclass
class CalendarEventCreateRequest:
    """日历事件创建请求"""

    summary: str
    start_time: datetime
    end_time: datetime
    description: str | None = None
    reminders: list[dict[str, Any]] = field(default_factory=list)


class FeishuCalendarAPI:
    """飞书日历 API 封装"""

    BASE_URL = "https://open.feishu.cn/open-apis/calendar/v4"
    TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"  # nosec B105

    def __init__(self, app_id: str, app_secret: str):
        """
        初始化飞书日历 API

        Args:
            app_id: 飞书应用 App ID
            app_secret: 飞书应用 App Secret
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self._access_token: str | None = None
        self._token_expire_time: float | None = None

    def _get_access_token(self) -> str:
        """
        获取访问令牌

        Returns:
            str: 访问令牌

        Raises:
            RuntimeError: 当获取令牌失败时
        """
        # 检查令牌是否有效
        if (
            self._access_token
            and self._token_expire_time
            and time.time() < self._token_expire_time - 300  # 提前 5 分钟刷新
        ):
            return self._access_token

        try:
            url = self.TOKEN_URL
            payload = {
                "app_id": self.app_id,
                "app_secret": self.app_secret,
            }
            headers = {"Content-Type": "application/json"}
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            result = response.json()

            if result.get("code") == 0:
                self._access_token = result.get("tenant_access_token")
                # 令牌有效期通常为 2 小时，提前 5 分钟刷新
                self._token_expire_time = time.time() + 7200 - 300
                logger.info("成功获取飞书访问令牌")
                return self._access_token
            else:
                error_msg = result.get("msg", "获取令牌失败")
                logger.error(f"获取飞书访问令牌失败：{error_msg}")
                raise RuntimeError(f"获取飞书访问令牌失败：{error_msg}")

        except requests.exceptions.RequestException as e:
            logger.error(f"获取飞书访问令牌请求异常：{e}")
            raise RuntimeError(f"获取飞书访问令牌请求异常：{e}")

    def _get_headers(self) -> dict[str, str]:
        """获取请求头"""
        token = self._get_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        通用请求方法

        Args:
            method: HTTP 方法
            endpoint: API 端点
            params: 查询参数
            json: 请求体

        Returns:
            Dict[str, Any]: API 响应

        Raises:
            RuntimeError: 当请求失败时
        """
        url = f"{self.BASE_URL}{endpoint}"
        headers = self._get_headers()

        try:
            response = requests.request(
                method, url, params=params, json=json, headers=headers, timeout=10
            )
            result = response.json()

            # 检查飞书 API 响应码
            if result.get("code") == 0:
                return result
            else:
                error_msg = result.get("msg", "API 调用失败")
                logger.error(f"飞书 API 调用失败：{error_msg}")
                raise RuntimeError(f"飞书 API 调用失败：{error_msg}")

        except requests.exceptions.Timeout:
            logger.error("飞书 API 请求超时")
            raise RuntimeError("飞书 API 请求超时")
        except requests.exceptions.RequestException as e:
            logger.error(f"飞书 API 请求异常：{e}")
            raise RuntimeError(f"飞书 API 请求异常：{e}")

    async def create_event(
        self, calendar_id: str, event: CalendarEventCreateRequest
    ) -> dict[str, Any]:
        """
        创建日历事件

        Args:
            calendar_id: 日历 ID
            event: 事件创建请求

        Returns:
            Dict[str, Any]: API 响应，包含 event_id

        Raises:
            RuntimeError: 当创建失败时
        """
        endpoint = "/calendars/events"
        payload = {
            "calendar_id": calendar_id,
            "summary": event.summary,
            "start_time": {
                "timestamp": int(event.start_time.timestamp()),
                "timezone": "Asia/Shanghai",
            },
            "end_time": {
                "timestamp": int(event.end_time.timestamp()),
                "timezone": "Asia/Shanghai",
            },
        }

        if event.description:
            payload["description"] = event.description

        if event.reminders:
            payload["reminders"] = event.reminders  # type: ignore[assignment]

        result = self._request("POST", endpoint, json=payload)
        return result.get("data", {})

    async def update_event(
        self, calendar_id: str, event_id: str, event: dict[str, Any]
    ) -> dict[str, Any]:
        """
        更新日历事件

        Args:
            calendar_id: 日历 ID
            event_id: 事件 ID
            event: 更新内容

        Returns:
            Dict[str, Any]: API 响应

        Raises:
            RuntimeError: 当更新失败时
        """
        endpoint = f"/calendars/{calendar_id}/events/{event_id}"
        result = self._request("PATCH", endpoint, json=event)
        return result.get("data", {})

    async def delete_event(self, calendar_id: str, event_id: str) -> dict[str, Any]:
        """
        删除日历事件

        Args:
            calendar_id: 日历 ID
            event_id: 事件 ID

        Returns:
            Dict[str, Any]: API 响应

        Raises:
            RuntimeError: 当删除失败时
        """
        endpoint = f"/calendars/{calendar_id}/events/{event_id}"
        result = self._request("DELETE", endpoint)
        return result.get("data", {})

    async def get_event(self, calendar_id: str, event_id: str) -> dict[str, Any]:
        """
        获取日历事件

        Args:
            calendar_id: 日历 ID
            event_id: 事件 ID

        Returns:
            Dict[str, Any]: 事件详情

        Raises:
            RuntimeError: 当获取失败时
        """
        endpoint = f"/calendars/{calendar_id}/events/{event_id}"
        result = self._request("GET", endpoint)
        return result.get("data", {})

    async def get_calendar_list(self) -> list[dict[str, Any]]:
        """
        获取日历列表

        Returns:
            List[Dict[str, Any]]: 日历列表

        Raises:
            RuntimeError: 当获取失败时
        """
        endpoint = "/calendars"
        result = self._request("GET", endpoint)
        return result.get("data", {}).get("items", [])


class FeishuCalendarSync:
    """飞书日历同步服务"""

    # 重试配置
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0  # 秒

    def __init__(self, config: CalendarSyncConfig | None = None):
        """
        初始化飞书日历同步服务

        Args:
            config: 同步配置，不指定则从配置文件读取
        """
        self.config = config or self._load_config()
        self._api: FeishuCalendarAPI | None = None

        # 初始化 API 客户端
        if self.config.app_id and self.config.app_secret:
            self._api = FeishuCalendarAPI(self.config.app_id, self.config.app_secret)
            logger.info("飞书日历 API 初始化成功")
        else:
            logger.warning("未配置飞书日历 API 凭证")

    def _load_config(self) -> CalendarSyncConfig:
        """从配置文件加载配置"""
        config_manager = ConfigManager()
        config_dict = config_manager.load_config()

        return CalendarSyncConfig(
            enabled=config_dict.get("calendar_sync_enabled", True),
            calendar_id=config_dict.get("calendar_id"),
            reminder_minutes=config_dict.get("calendar_reminder_minutes", 60),
            sync_completed=config_dict.get("calendar_sync_completed", False),
            include_description=config_dict.get("calendar_include_description", True),
            app_id=config_dict.get("feishu_app_id"),
            app_secret=config_dict.get("feishu_app_secret"),
        )

    def _get_default_calendar_id(self) -> str | None:
        """获取默认日历 ID"""
        if self.config.calendar_id:
            return self.config.calendar_id

        # 获取第一个可用的日历
        if self._api:
            try:
                import asyncio

                calendars = asyncio.get_event_loop().run_until_complete(
                    self._api.get_calendar_list()
                )
                if calendars:
                    return calendars[0].get("calendar_id")
            except Exception as e:
                logger.error(f"获取日历列表失败：{e}")

        return None

    def _build_event_description(self, daily_plan: DailyPlan) -> str:
        """
        构建事件描述

        Args:
            daily_plan: 日训练计划

        Returns:
            str: 事件描述
        """
        lines = [
            f"训练类型：{daily_plan.workout_type.value}",
        ]

        if daily_plan.distance_km > 0:
            lines.append(f"目标距离：{daily_plan.distance_km} km")

        if daily_plan.duration_min > 0:
            lines.append(f"目标时长：{daily_plan.duration_min} 分钟")

        if daily_plan.target_hr_zone:
            lines.append(f"目标心率区间：Z{daily_plan.target_hr_zone}")

        if daily_plan.notes:
            lines.append(f"训练说明：{daily_plan.notes}")

        return "\n".join(lines)

    def build_calendar_event(
        self, daily_plan: DailyPlan, date: datetime
    ) -> CalendarEventCreateRequest:
        """
        构建日历事件

        Args:
            daily_plan: 日训练计划
            date: 日期

        Returns:
            CalendarEventCreateRequest: 日历事件创建请求
        """
        # 默认训练开始时间为早上 6 点
        start_time = datetime.combine(date.date(), datetime.min.time().replace(hour=6))
        end_time = start_time + timedelta(minutes=daily_plan.duration_min)

        # 构建事件摘要
        distance_str = format_distance(daily_plan.distance_km * 1000)
        summary = f"🏃 {daily_plan.workout_type.value} - {distance_str}"

        # 构建事件描述
        description = None
        if self.config.include_description:
            description = self._build_event_description(daily_plan)

        # 构建提醒
        reminders = []
        if self.config.reminder_minutes > 0:
            reminders = [
                {
                    "method": "app_push",
                    "minutes": self.config.reminder_minutes,
                }
            ]

        return CalendarEventCreateRequest(
            summary=summary,
            start_time=start_time,
            end_time=end_time,
            description=description,
            reminders=reminders,
        )

    async def sync_plan(self, plan: TrainingPlan) -> SyncResult:
        """
        同步训练计划到飞书日历

        Args:
            plan: 训练计划

        Returns:
            SyncResult: 同步结果
        """
        if not self.config.enabled:
            return SyncResult(
                success=False, message="日历同步功能未启用", error="功能未启用"
            )

        if not self._api:
            return SyncResult(
                success=False, message="飞书 API 未初始化", error="API 凭证缺失"
            )

        calendar_id = self._get_default_calendar_id()
        if not calendar_id:
            return SyncResult(
                success=False,
                message="未指定日历 ID",
                error="请在配置中设置 calendar_id",
            )

        synced_count = 0
        failed_count = 0
        event_ids = []

        # 遍历所有周计划
        for week in plan.weeks:
            for daily_plan in week.daily_plans:
                # 跳过休息日
                if daily_plan.workout_type.value == "休息":
                    continue

                # 跳过已完成的训练（如果配置不同步）
                if daily_plan.completed and not self.config.sync_completed:
                    continue

                try:
                    # 解析日期
                    run_date = datetime.strptime(daily_plan.date, "%Y-%m-%d")

                    # 跳过过去的训练
                    if run_date < datetime.now():
                        continue

                    # 构建并创建事件
                    event = self.build_calendar_event(daily_plan, run_date)
                    result = await self._api.create_event(calendar_id, event)

                    event_id = result.get("event_id")
                    if event_id:
                        event_ids.append(event_id)
                        synced_count += 1
                        logger.info(
                            f"同步训练计划事件成功：{daily_plan.date} - {daily_plan.workout_type.value}"
                        )
                    else:
                        failed_count += 1
                        logger.warning(
                            f"同步训练计划事件失败：{daily_plan.date} - 未返回 event_id"
                        )

                except Exception as e:
                    failed_count += 1
                    logger.error(
                        f"同步训练计划事件失败：{daily_plan.date} - {str(e)}",
                        exc_info=True,
                    )

        # 生成同步结果
        if failed_count == 0:
            return SyncResult(
                success=True,
                message=f"成功同步 {synced_count} 个训练事件到飞书日历",
                details={"synced_count": synced_count, "event_ids": event_ids},
            )
        else:
            return SyncResult(
                success=True,
                message=f"同步完成：成功 {synced_count} 个，失败 {failed_count} 个",
                error=f"有 {failed_count} 个事件同步失败",
                details={"synced_count": synced_count, "failed_count": failed_count},
            )

    async def sync_daily_workout(
        self, daily_plan: DailyPlan, date: datetime
    ) -> SyncResult:
        """
        同步单日训练到日历

        Args:
            daily_plan: 日训练计划
            date: 日期

        Returns:
            SyncResult: 同步结果
        """
        if not self.config.enabled:
            return SyncResult(
                success=False, message="日历同步功能未启用", error="功能未启用"
            )

        if not self._api:
            return SyncResult(
                success=False, message="飞书 API 未初始化", error="API 凭证缺失"
            )

        calendar_id = self._get_default_calendar_id()
        if not calendar_id:
            return SyncResult(
                success=False,
                message="未指定日历 ID",
                error="请在配置中设置 calendar_id",
            )

        try:
            # 构建事件
            event = self.build_calendar_event(daily_plan, date)

            # 创建事件
            result = await self._api.create_event(calendar_id, event)

            event_id = result.get("event_id")
            if event_id:
                logger.info(
                    f"同步单日训练成功：{date.strftime('%Y-%m-%d')} - {daily_plan.workout_type.value}"
                )
                return SyncResult(
                    success=True,
                    message="训练事件已同步到飞书日历",
                    event_id=event_id,
                    details={"event_id": event_id, "date": date.strftime("%Y-%m-%d")},
                )
            else:
                logger.error("同步单日训练失败：未返回 event_id")
                return SyncResult(
                    success=False,
                    message="同步失败",
                    error="未返回 event_id",
                )

        except Exception as e:
            logger.error(f"同步单日训练失败：{str(e)}", exc_info=True)
            return SyncResult(
                success=False,
                message="同步失败",
                error=str(e),
            )

    async def update_event(
        self, event_id: str, daily_plan: DailyPlan, date: datetime
    ) -> SyncResult:
        """
        更新日历事件

        Args:
            event_id: 事件 ID
            daily_plan: 日训练计划
            date: 日期

        Returns:
            SyncResult: 同步结果
        """
        if not self.config.enabled:
            return SyncResult(
                success=False, message="日历同步功能未启用", error="功能未启用"
            )

        if not self._api:
            return SyncResult(
                success=False, message="飞书 API 未初始化", error="API 凭证缺失"
            )

        calendar_id = self._get_default_calendar_id()
        if not calendar_id:
            return SyncResult(
                success=False,
                message="未指定日历 ID",
                error="请在配置中设置 calendar_id",
            )

        try:
            # 构建更新内容
            event = self.build_calendar_event(daily_plan, date)
            update_payload = {
                "summary": event.summary,
                "start_time": {
                    "timestamp": int(event.start_time.timestamp()),
                    "timezone": "Asia/Shanghai",
                },
                "end_time": {
                    "timestamp": int(event.end_time.timestamp()),
                    "timezone": "Asia/Shanghai",
                },
            }

            if event.description:
                update_payload["description"] = event.description

            # 更新事件
            result = await self._api.update_event(calendar_id, event_id, update_payload)

            logger.info(f"更新日历事件成功：{event_id}")
            return SyncResult(
                success=True,
                message="日历事件已更新",
                event_id=event_id,
                details=result,
            )

        except Exception as e:
            logger.error(f"更新日历事件失败：{event_id} - {str(e)}", exc_info=True)
            return SyncResult(
                success=False,
                message="更新失败",
                error=str(e),
            )

    async def delete_event(self, event_id: str) -> SyncResult:
        """
        删除日历事件

        Args:
            event_id: 事件 ID

        Returns:
            SyncResult: 同步结果
        """
        if not self.config.enabled:
            return SyncResult(
                success=False, message="日历同步功能未启用", error="功能未启用"
            )

        if not self._api:
            return SyncResult(
                success=False, message="飞书 API 未初始化", error="API 凭证缺失"
            )

        calendar_id = self._get_default_calendar_id()
        if not calendar_id:
            return SyncResult(
                success=False,
                message="未指定日历 ID",
                error="请在配置中设置 calendar_id",
            )

        try:
            await self._api.delete_event(calendar_id, event_id)
            logger.info(f"删除日历事件成功：{event_id}")
            return SyncResult(
                success=True,
                message="日历事件已删除",
                event_id=event_id,
            )

        except Exception as e:
            logger.error(f"删除日历事件失败：{event_id} - {str(e)}", exc_info=True)
            return SyncResult(
                success=False,
                message="删除失败",
                error=str(e),
            )

    async def check_conflicts(
        self, date: datetime, time_range: tuple[int, int]
    ) -> list[dict[str, Any]]:
        """
        检测日程冲突

        Args:
            date: 日期
            time_range: 时间范围（开始小时，结束小时）

        Returns:
            List[Dict[str, Any]]: 冲突事件列表
        """
        if not self._api:
            logger.warning("飞书 API 未初始化，无法检测冲突")
            return []

        calendar_id = self._get_default_calendar_id()
        if not calendar_id:
            return []

        try:
            # 获取指定日期的事件
            start_time = datetime.combine(
                date.date(), datetime.min.time().replace(hour=0)
            )
            end_time = start_time + timedelta(days=1)

            # 查询日历事件（需要 API 支持时间范围查询）
            # 注意：飞书日历 API 可能需要使用特定的查询参数
            events: list[dict[str, Any]] = []

            # 检查是否有事件在指定时间范围内
            conflicts = []
            for event in events:
                event_start = event.get("start_time", {})
                event_timestamp = event_start.get("timestamp", 0)
                event_date = datetime.fromtimestamp(event_timestamp)

                if event_date.date() == date.date():
                    event_hour = event_date.hour
                    if time_range[0] <= event_hour <= time_range[1]:
                        conflicts.append(event)

            return conflicts

        except Exception as e:
            logger.error(f"检测日程冲突失败：{str(e)}", exc_info=True)
            return []
