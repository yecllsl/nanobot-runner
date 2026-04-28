# 追踪日志记录器
# 提供决策日志、工具调用日志的记录和查询能力

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from src.core.transparency.models import (
    AIDecision,
    DecisionExplanation,
    LogEntry,
    LogFilters,
)

logger = logging.getLogger(__name__)


class TraceLogger:
    """追踪日志记录器

    记录AI决策日志和工具调用日志，支持持久化存储和回溯查询。
    核心接口：
    - log_decision: 记录决策日志
    - log_tool_invocation: 记录工具调用日志
    - query_logs: 查询日志
    """

    def __init__(self, log_dir: Path | None = None) -> None:
        """初始化追踪日志记录器

        Args:
            log_dir: 日志存储目录（可选，为空则仅内存存储）
        """
        self._entries: list[LogEntry] = []
        self._log_dir = log_dir

        if log_dir is not None:
            log_dir.mkdir(parents=True, exist_ok=True)

    def log_decision(
        self,
        decision: AIDecision,
        explanation: DecisionExplanation | None = None,
    ) -> None:
        """记录决策日志

        Args:
            decision: AI决策
            explanation: 决策解释（可选）
        """
        context: dict[str, Any] = {
            "decision_id": decision.id,
            "decision_type": decision.decision_type.value,
            "confidence": decision.confidence,
            "tools_used": decision.tools_used,
            "memory_referenced": decision.memory_referenced,
            "duration_ms": decision.duration_ms,
        }

        if explanation is not None:
            context["brief_reasons"] = explanation.brief_reasons
            context["data_sources_count"] = len(explanation.data_sources)

        entry = LogEntry(
            timestamp=decision.timestamp,
            level="INFO",
            message=f"决策记录: {decision.decision_type.value}, "
            f"置信度={decision.confidence:.1%}",
            context=context,
            trace_id=decision.id,
            entry_type="decision",
        )

        self._add_entry(entry)

    def log_tool_invocation(
        self,
        tool_id: str,
        params: dict[str, Any],
        result: dict[str, Any] | None = None,
        success: bool = True,
        duration_ms: int = 0,
        trace_id: str | None = None,
    ) -> None:
        """记录工具调用日志

        Args:
            tool_id: 工具ID
            params: 调用参数
            result: 调用结果
            success: 是否成功
            duration_ms: 调用耗时（毫秒）
            trace_id: 关联的追踪ID
        """
        context: dict[str, Any] = {
            "tool_id": tool_id,
            "success": success,
            "duration_ms": duration_ms,
        }

        params_str = json.dumps(params, ensure_ascii=False, default=str)
        if len(params_str) <= 500:
            context["params"] = params
        else:
            context["params_summary"] = params_str[:500] + "..."

        if result is not None:
            result_str = json.dumps(result, ensure_ascii=False, default=str)
            if len(result_str) <= 500:
                context["result"] = result
            else:
                context["result_summary"] = result_str[:500] + "..."

        level = "INFO" if success else "WARNING"
        message = (
            f"工具调用: {tool_id}, "
            f"成功={'是' if success else '否'}, "
            f"耗时={duration_ms}ms"
        )

        entry = LogEntry(
            timestamp=datetime.now(),
            level=level,
            message=message,
            context=context,
            trace_id=trace_id,
            entry_type="tool_call",
        )

        self._add_entry(entry)

    def query_logs(self, filters: LogFilters | None = None) -> list[LogEntry]:
        """查询日志

        根据过滤条件查询日志条目。

        Args:
            filters: 日志过滤条件（可选）

        Returns:
            list[LogEntry]: 日志条目列表
        """
        if filters is None:
            return self._entries[-100:]

        results = self._entries

        if filters.start_time is not None:
            results = [e for e in results if e.timestamp >= filters.start_time]

        if filters.end_time is not None:
            results = [e for e in results if e.timestamp <= filters.end_time]

        if filters.decision_type is not None:
            results = [
                e
                for e in results
                if e.context.get("decision_type") == filters.decision_type
            ]

        if filters.tool_id is not None:
            results = [
                e for e in results if e.context.get("tool_id") == filters.tool_id
            ]

        if filters.status is not None:
            results = [e for e in results if e.level == filters.status]

        if filters.session_key is not None:
            results = [
                e
                for e in results
                if e.context.get("session_key") == filters.session_key
            ]

        return results[-filters.limit :]

    def get_decision_logs(self, limit: int = 20) -> list[LogEntry]:
        """获取决策日志

        Args:
            limit: 返回数量限制

        Returns:
            list[LogEntry]: 决策日志列表
        """
        decision_entries = [e for e in self._entries if e.entry_type == "decision"]
        return decision_entries[-limit:]

    def get_tool_call_logs(self, limit: int = 20) -> list[LogEntry]:
        """获取工具调用日志

        Args:
            limit: 返回数量限制

        Returns:
            list[LogEntry]: 工具调用日志列表
        """
        tool_entries = [e for e in self._entries if e.entry_type == "tool_call"]
        return tool_entries[-limit:]

    def get_stats(self) -> dict[str, Any]:
        """获取日志统计

        Returns:
            dict: 日志统计数据
        """
        total = len(self._entries)
        decision_count = sum(1 for e in self._entries if e.entry_type == "decision")
        tool_call_count = sum(1 for e in self._entries if e.entry_type == "tool_call")
        error_count = sum(1 for e in self._entries if e.level == "WARNING")

        return {
            "total_entries": total,
            "decision_count": decision_count,
            "tool_call_count": tool_call_count,
            "error_count": error_count,
        }

    def clear(self) -> None:
        """清除所有日志"""
        self._entries.clear()

    def _add_entry(self, entry: LogEntry) -> None:
        """添加日志条目

        Args:
            entry: 日志条目
        """
        self._entries.append(entry)

        if self._log_dir is not None:
            self._persist_entry(entry)

        logger.debug(
            f"日志记录: type={entry.entry_type}, "
            f"level={entry.level}, "
            f"message={entry.message[:100]}"
        )

    def _persist_entry(self, entry: LogEntry) -> None:
        """持久化日志条目到文件

        Args:
            entry: 日志条目
        """
        if self._log_dir is None:
            return

        try:
            date_str = entry.timestamp.strftime("%Y-%m-%d")
            log_file = self._log_dir / f"trace_{date_str}.jsonl"

            entry_dict = entry.to_dict()
            line = json.dumps(entry_dict, ensure_ascii=False, default=str)
            log_file.write_text(
                log_file.read_text(encoding="utf-8") + line + "\n",
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning(f"日志持久化失败: {e}")
