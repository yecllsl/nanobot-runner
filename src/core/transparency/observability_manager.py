# 可观测性管理器
# 提供全链路追踪、事件记录、指标收集等能力

import logging
import uuid
from datetime import datetime
from typing import Any

from src.core.transparency.models import (
    ObservabilityMetrics,
    TraceEvent,
    TraceReport,
    TraceStatus,
)

logger = logging.getLogger(__name__)


class ObservabilityManager:
    """可观测性管理器

    提供全链路追踪、事件记录、指标收集能力。
    核心接口：
    - start_trace: 开始追踪
    - record_event: 记录事件
    - end_trace: 结束追踪
    - get_metrics: 获取指标
    """

    def __init__(self) -> None:
        """初始化可观测性管理器"""
        self._active_traces: dict[str, dict[str, Any]] = {}
        self._completed_traces: list[TraceReport] = []
        self._tool_call_count: int = 0
        self._tool_success_count: int = 0

    def start_trace(
        self,
        operation_name: str,
        tags: dict[str, str] | None = None,
    ) -> str:
        """开始追踪

        创建一个新的追踪上下文，返回追踪ID。

        Args:
            operation_name: 操作名称
            tags: 标签

        Returns:
            str: 追踪ID
        """
        trace_id = str(uuid.uuid4())[:8]
        now = datetime.now()

        self._active_traces[trace_id] = {
            "trace_id": trace_id,
            "operation_name": operation_name,
            "start_time": now,
            "events": [],
            "tags": tags or {},
        }

        logger.debug(f"追踪开始: trace_id={trace_id}, operation={operation_name}")
        return trace_id

    def record_event(
        self,
        trace_id: str,
        event_name: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        """记录事件

        在指定追踪上下文中记录一个事件。

        Args:
            trace_id: 追踪ID
            event_name: 事件名称
            data: 事件数据
        """
        trace = self._active_traces.get(trace_id)
        if trace is None:
            logger.warning(f"追踪不存在: trace_id={trace_id}")
            return

        event = TraceEvent(
            timestamp=datetime.now(),
            name=event_name,
            data=data or {},
        )
        trace["events"].append(event)

        if event_name == "tool_call":
            self._tool_call_count += 1
            if data and data.get("success", True):
                self._tool_success_count += 1

        logger.debug(f"事件记录: trace_id={trace_id}, event={event_name}")

    def end_trace(
        self,
        trace_id: str,
        status: str = "completed",
    ) -> TraceReport:
        """结束追踪

        结束指定追踪上下文，生成追踪报告。

        Args:
            trace_id: 追踪ID
            status: 状态（completed/failed）

        Returns:
            TraceReport: 追踪报告
        """
        trace = self._active_traces.pop(trace_id, None)
        if trace is None:
            logger.warning(f"追踪不存在: trace_id={trace_id}")
            return TraceReport(
                trace_id=trace_id,
                operation_name="unknown",
                status=TraceStatus.FAILED,
            )

        end_time = datetime.now()
        duration_ms = int((end_time - trace["start_time"]).total_seconds() * 1000)

        trace_status = (
            TraceStatus.COMPLETED if status == "completed" else TraceStatus.FAILED
        )

        report = TraceReport(
            trace_id=trace_id,
            operation_name=trace["operation_name"],
            start_time=trace["start_time"],
            end_time=end_time,
            duration_ms=duration_ms,
            status=trace_status,
            events=trace["events"],
            tags=trace["tags"],
        )

        self._completed_traces.append(report)

        logger.info(
            f"追踪结束: trace_id={trace_id}, "
            f"status={trace_status.value}, "
            f"duration={duration_ms}ms, "
            f"events={len(trace['events'])}"
        )

        return report

    def get_metrics(self) -> ObservabilityMetrics:
        """获取可观测性指标

        Returns:
            ObservabilityMetrics: 可观测性指标
        """
        total = len(self._completed_traces)
        successful = sum(
            1 for t in self._completed_traces if t.status == TraceStatus.COMPLETED
        )
        failed = total - successful

        avg_duration = 0.0
        if total > 0:
            avg_duration = sum(t.duration_ms for t in self._completed_traces) / total

        error_rate = failed / total if total > 0 else 0.0
        tool_success_rate = (
            self._tool_success_count / self._tool_call_count
            if self._tool_call_count > 0
            else 0.0
        )

        return ObservabilityMetrics(
            total_traces=total,
            successful_traces=successful,
            failed_traces=failed,
            avg_duration_ms=avg_duration,
            error_rate=error_rate,
            tool_call_count=self._tool_call_count,
            tool_success_rate=tool_success_rate,
        )

    def get_trace(self, trace_id: str) -> TraceReport | None:
        """获取追踪报告

        Args:
            trace_id: 追踪ID

        Returns:
            TraceReport | None: 追踪报告，不存在则返回None
        """
        for report in self._completed_traces:
            if report.trace_id == trace_id:
                return report
        return None

    def get_recent_traces(self, limit: int = 10) -> list[TraceReport]:
        """获取最近的追踪报告

        Args:
            limit: 返回数量限制

        Returns:
            list[TraceReport]: 追踪报告列表
        """
        return self._completed_traces[-limit:]

    def get_active_trace_count(self) -> int:
        """获取活跃追踪数量

        Returns:
            int: 活跃追踪数量
        """
        return len(self._active_traces)

    def clear_history(self) -> None:
        """清除历史追踪数据"""
        self._completed_traces.clear()
        self._tool_call_count = 0
        self._tool_success_count = 0
