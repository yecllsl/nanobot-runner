# Agent 工具集
# 封装为 nanobot-ai 可识别的工具

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import polars as pl

from src.core.analytics import AnalyticsEngine
from src.core.profile import ProfileStorageManager, RunnerProfile
from src.core.storage import StorageManager

logger = logging.getLogger(__name__)


class BaseTool(ABC):
    """工具基类（适配nanobot-ai 0.1.4+）"""

    def __init__(self, runner_tools: "RunnerTools"):
        self.runner_tools = runner_tools

    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述"""
        pass

    @property
    @abstractmethod
    def parameters(self) -> dict[str, Any]:
        """参数schema"""
        pass

    @abstractmethod
    async def execute(self, **kwargs: Any) -> str:
        """执行工具"""
        pass

    def to_schema(self) -> dict[str, Any]:
        """转换为OpenAI function schema格式"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def validate_params(self, params: dict[str, Any]) -> list[str]:
        """验证工具参数"""
        schema = self.parameters or {}
        if schema.get("type", "object") != "object":
            return [f"Schema must be object type, got {schema.get('type')!r}"]

        errors = []
        required = schema.get("required", [])
        properties = schema.get("properties", {})

        for field in required:
            if field not in params:
                errors.append(f"missing required field: {field}")

        for field, value in params.items():
            if field in properties:
                prop_schema = properties[field]
                prop_type = prop_schema.get("type")
                if prop_type == "integer" and not isinstance(value, int):
                    errors.append(f"{field} must be integer")
                elif prop_type == "number" and not isinstance(value, (int, float)):
                    errors.append(f"{field} must be number")
                elif prop_type == "string" and not isinstance(value, str):
                    errors.append(f"{field} must be string")

        return errors

    def _run_sync(self, func, *args, **kwargs) -> str:
        """同步调用方法并返回JSON字符串"""
        try:
            result = func(*args, **kwargs)
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)


class GetRunningStatsTool(BaseTool):
    """获取跑步统计数据"""

    @property
    def name(self) -> str:
        return "get_running_stats"

    @property
    def description(self) -> str:
        return "获取跑步统计数据，包括总次数、总距离、总时长、平均距离、平均时长、最大距离、平均心率等"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "description": "开始日期（可选，格式：YYYY-MM-DD）",
                },
                "end_date": {"type": "string", "description": "结束日期（可选，格式：YYYY-MM-DD）"},
            },
        }

    async def execute(self, **kwargs: Any) -> str:
        start_date = kwargs.get("start_date")
        end_date = kwargs.get("end_date")
        return self._run_sync(self.runner_tools.get_running_stats, start_date, end_date)


class GetRecentRunsTool(BaseTool):
    """获取最近跑步记录"""

    @property
    def name(self) -> str:
        return "get_recent_runs"

    @property
    def description(self) -> str:
        return "获取最近的跑步记录列表"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "返回数量限制（默认10条）",
                    "default": 10,
                }
            },
        }

    async def execute(self, **kwargs: Any) -> str:
        limit = kwargs.get("limit", 10)
        return self._run_sync(self.runner_tools.get_recent_runs, limit)


class CalculateVdotForRunTool(BaseTool):
    """计算单次跑步的VDOT值"""

    @property
    def name(self) -> str:
        return "calculate_vdot_for_run"

    @property
    def description(self) -> str:
        return "计算单次跑步的VDOT值（跑力值），用于评估跑步能力"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "distance_m": {"type": "number", "description": "距离（米）"},
                "time_s": {"type": "number", "description": "用时（秒）"},
            },
            "required": ["distance_m", "time_s"],
        }

    async def execute(self, **kwargs: Any) -> str:
        distance_m = kwargs.get("distance_m", 0)
        time_s = kwargs.get("time_s", 0)
        return self._run_sync(
            self.runner_tools.calculate_vdot_for_run, distance_m, time_s
        )


class GetVdotTrendTool(BaseTool):
    """获取VDOT趋势"""

    @property
    def name(self) -> str:
        return "get_vdot_trend"

    @property
    def description(self) -> str:
        return "获取VDOT趋势变化，了解跑步能力的变化趋势"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "返回数量限制（默认20条）",
                    "default": 20,
                }
            },
        }

    async def execute(self, **kwargs: Any) -> str:
        limit = kwargs.get("limit", 20)
        return self._run_sync(self.runner_tools.get_vdot_trend, limit)


class GetHrDriftAnalysisTool(BaseTool):
    """分析心率漂移"""

    @property
    def name(self) -> str:
        return "get_hr_drift_analysis"

    @property
    def description(self) -> str:
        return "分析心率漂移情况，评估跑步效率和有氧基础"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"run_id": {"type": "string", "description": "活动ID（可选）"}},
        }

    async def execute(self, **kwargs: Any) -> str:
        run_id = kwargs.get("run_id")
        return self._run_sync(self.runner_tools.get_hr_drift_analysis, run_id)


class GetTrainingLoadTool(BaseTool):
    """获取训练负荷"""

    @property
    def name(self) -> str:
        return "get_training_load"

    @property
    def description(self) -> str:
        return "获取训练负荷数据，包括ATL（急性负荷）、CTL（慢性负荷）、TSB（训练压力平衡）"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "分析天数（默认42天）", "default": 42}
            },
        }

    async def execute(self, **kwargs: Any) -> str:
        days = kwargs.get("days", 42)
        return self._run_sync(self.runner_tools.get_training_load, days)


class QueryByDateRangeTool(BaseTool):
    """按日期范围查询"""

    @property
    def name(self) -> str:
        return "query_by_date_range"

    @property
    def description(self) -> str:
        return "按日期范围查询跑步记录"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "开始日期（格式：YYYY-MM-DD）"},
                "end_date": {"type": "string", "description": "结束日期（格式：YYYY-MM-DD）"},
            },
            "required": ["start_date", "end_date"],
        }

    async def execute(self, **kwargs: Any) -> str:
        start_date = kwargs.get("start_date", "")
        end_date = kwargs.get("end_date", "")
        return self._run_sync(
            self.runner_tools.query_by_date_range, start_date, end_date
        )


class QueryByDistanceTool(BaseTool):
    """按距离范围查询"""

    @property
    def name(self) -> str:
        return "query_by_distance"

    @property
    def description(self) -> str:
        return "按距离范围查询跑步记录"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "min_distance": {"type": "number", "description": "最小距离（公里）"},
                "max_distance": {"type": "number", "description": "最大距离（公里，可选）"},
            },
            "required": ["min_distance"],
        }

    async def execute(self, **kwargs: Any) -> str:
        min_distance = kwargs.get("min_distance", 0)
        max_distance = kwargs.get("max_distance")
        return self._run_sync(
            self.runner_tools.query_by_distance, min_distance, max_distance
        )


class UpdateMemoryTool(BaseTool):
    """更新 Agent 记忆工具（Agent 专用）"""

    @property
    def name(self) -> str:
        return "update_memory"

    @property
    def description(self) -> str:
        return "更新 Agent 观察笔记到 MEMORY.md，用于记录用户偏好、训练反馈等长期记忆"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "note": {
                    "type": "string",
                    "description": "要添加的观察笔记内容",
                },
                "category": {
                    "type": "string",
                    "description": "笔记分类（可选）：training(训练), preference(偏好), injury(伤病), other(其他)",
                    "enum": ["training", "preference", "injury", "other"],
                    "default": "other",
                },
            },
            "required": ["note"],
        }

    async def execute(self, **kwargs: Any) -> str:
        note = kwargs.get("note", "")
        category = kwargs.get("category", "other")
        return self._run_sync(self.runner_tools.update_memory, note, category)


class RunnerTools:
    """跑步助理工具集（业务逻辑层）"""

    def __init__(self, storage: Optional[StorageManager] = None):
        self.storage = storage or StorageManager()
        self.analytics = AnalyticsEngine(self.storage)
        self.profile_storage = ProfileStorageManager()

    def get_running_stats(
        self, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        summary = self.analytics.get_running_summary(start_date, end_date)

        if summary.height == 0:
            return {"message": "暂无跑步数据"}

        row = summary.row(0)

        return {
            "total_runs": row[0],
            "total_distance": row[1],
            "total_duration": row[2],
            "avg_distance": row[3],
            "avg_duration": row[4],
            "max_distance": row[5],
            "avg_heart_rate": row[6],
        }

    def get_recent_runs(self, limit: int = 10) -> List[Dict[str, Any]]:
        lf = self.storage.read_parquet()
        df = lf.sort("timestamp", descending=True).limit(limit).collect()

        runs = []
        for row in df.iter_rows(named=True):
            distance_km = row.get("total_distance", 0) / 1000
            duration_min = row.get("total_timer_time", 0) / 60
            pace = duration_min / distance_km if distance_km > 0 else 0

            runs.append(
                {
                    "timestamp": str(row.get("timestamp", "N/A")),
                    "distance_km": round(distance_km, 2),
                    "duration_min": round(duration_min, 1),
                    "avg_pace_sec_km": round(pace, 1) if pace > 0 else None,
                    "avg_heart_rate": row.get("avg_heart_rate"),
                    "vdot": row.get("vdot_estimate"),
                }
            )

        return runs

    def calculate_vdot_for_run(self, distance_m: float, time_s: float) -> float:
        return self.analytics.calculate_vdot(distance_m, time_s)

    def get_vdot_trend(self, limit: int = 20) -> List[Dict[str, Any]]:
        lf = self.storage.read_parquet()
        df = lf.sort("timestamp", descending=True).limit(limit).collect()

        vdot_trend = []
        for row in df.iter_rows(named=True):
            distance = row.get("total_distance", 0)
            duration = row.get("total_timer_time", 0)

            if distance > 0 and duration > 0:
                vdot = self.analytics.calculate_vdot(distance, duration)
                vdot_trend.append(
                    {
                        "timestamp": str(row.get("timestamp", "N/A")),
                        "distance": distance,
                        "vdot": vdot,
                    }
                )

        return vdot_trend

    def get_hr_drift_analysis(self, run_id: Optional[str] = None) -> Dict[str, Any]:
        lf = self.storage.read_parquet()
        df = lf.collect()

        if df.height == 0:
            return {"error": "暂无数据"}

        heart_rate = df.select(pl.col("heart_rate")).to_series().to_list()
        pace = df.select(pl.col("pace")).to_series().to_list()

        return self.analytics.analyze_hr_drift(heart_rate, pace)

    def get_training_load(self, days: int = 42) -> Dict[str, Any]:
        return self.analytics.get_training_load(days)

    def query_by_date_range(
        self, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            return [{"error": "日期格式错误，应为 YYYY-MM-DD"}]

        lf = self.storage.read_parquet()

        filtered_lf = lf.filter(pl.col("timestamp").is_between(start_dt, end_dt))

        selected_lf = filtered_lf.select(
            [
                "timestamp",
                "total_distance",
                "total_timer_time",
                "avg_heart_rate",
            ]
        )

        df = selected_lf.sort("timestamp", descending=True).collect()

        results = []
        for row in df.iter_rows(named=True):
            distance_km = row.get("total_distance", 0) / 1000
            duration_minutes = row.get("total_timer_time", 0) / 60
            pace = duration_minutes / distance_km if distance_km > 0 else 0

            results.append(
                {
                    "timestamp": str(row.get("timestamp", "N/A")),
                    "distance": round(distance_km, 2),
                    "duration": row.get("total_timer_time", 0),
                    "heart_rate": row.get("avg_heart_rate", "N/A"),
                    "pace": round(pace, 2),
                }
            )

        return results

    def query_by_distance(
        self, min_distance: float, max_distance: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        min_meters = min_distance * 1000
        max_meters = max_distance * 1000 if max_distance else None

        lf = self.storage.read_parquet()

        if max_meters:
            distance_filter = pl.col("total_distance").is_between(
                min_meters, max_meters
            )
        else:
            distance_filter = pl.col("total_distance") >= min_meters

        filtered_lf = lf.filter(distance_filter).select(
            [
                "timestamp",
                "total_distance",
                "total_timer_time",
                "avg_heart_rate",
            ]
        )

        df = filtered_lf.sort("timestamp", descending=True).collect()

        results = []
        for row in df.iter_rows(named=True):
            distance_km = row.get("total_distance", 0) / 1000
            duration_minutes = row.get("total_timer_time", 0) / 60
            pace = duration_minutes / distance_km if distance_km > 0 else 0

            results.append(
                {
                    "timestamp": str(row.get("timestamp", "N/A")),
                    "distance": round(distance_km, 2),
                    "duration": row.get("total_timer_time", 0),
                    "heart_rate": row.get("avg_heart_rate", "N/A"),
                    "pace": round(pace, 2),
                }
            )

        return results

    def update_memory(self, note: str, category: str = "other") -> Dict[str, Any]:
        """
        更新 Agent 观察笔记到 MEMORY.md

        Args:
            note: 观察笔记内容
            category: 笔记分类（training/preference/injury/other）

        Returns:
            Dict: 包含成功/失败状态和消息
        """
        try:
            if not note or not note.strip():
                return {"error": "笔记内容不能为空"}

            # 验证分类
            valid_categories = ["training", "preference", "injury", "other"]
            if category not in valid_categories:
                return {"error": f"无效的分类，必须是 {', '.join(valid_categories)} 之一"}

            # 格式化笔记内容（添加分类标签）
            category_map = {
                "training": "训练",
                "preference": "偏好",
                "injury": "伤病",
                "other": "其他",
            }
            formatted_note = f"[{category_map.get(category, '其他')}] {note}"

            # 追加到 MEMORY.md
            success = self.profile_storage.save_memory_md(
                f"- @agent {formatted_note}", append=True
            )

            if success:
                return {
                    "success": True,
                    "message": "记忆更新成功",
                    "note": formatted_note,
                }
            else:
                return {"error": "保存 MEMORY.md 失败"}

        except Exception as e:
            logger.error(f"更新记忆失败：{e}")
            return {"error": f"更新记忆失败：{str(e)}"}


def create_tools(runner_tools: RunnerTools) -> List[BaseTool]:
    """创建工具实例列表（供 nanobot-ai 使用）"""
    return [
        GetRunningStatsTool(runner_tools),
        GetRecentRunsTool(runner_tools),
        CalculateVdotForRunTool(runner_tools),
        GetVdotTrendTool(runner_tools),
        GetHrDriftAnalysisTool(runner_tools),
        GetTrainingLoadTool(runner_tools),
        QueryByDateRangeTool(runner_tools),
        QueryByDistanceTool(runner_tools),
        UpdateMemoryTool(runner_tools),
    ]


TOOL_DESCRIPTIONS = {
    "get_running_stats": {
        "description": "获取跑步统计数据，包括总次数、总距离、平均距离等",
        "parameters": {
            "start_date": "开始日期（可选，格式：YYYY-MM-DD）",
            "end_date": "结束日期（可选，格式：YYYY-MM-DD）",
        },
    },
    "get_recent_runs": {
        "description": "获取最近的跑步记录",
        "parameters": {"limit": "返回数量限制（默认 10 条）"},
    },
    "calculate_vdot_for_run": {
        "description": "计算单次跑步的 VDOT 值（跑力值）",
        "parameters": {"distance_m": "距离（米）", "time_s": "用时（秒）"},
    },
    "get_vdot_trend": {
        "description": "获取 VDOT 趋势变化",
        "parameters": {"limit": "返回数量限制（默认 20 条）"},
    },
    "get_hr_drift_analysis": {
        "description": "分析心率漂移情况",
        "parameters": {"run_id": "活动 ID（可选）"},
    },
    "get_training_load": {
        "description": "获取训练负荷（ATL/CTL）",
        "parameters": {"days": "分析天数（默认 42 天）"},
    },
    "query_by_date_range": {
        "description": "按日期范围查询跑步记录",
        "parameters": {
            "start_date": "开始日期（格式：YYYY-MM-DD）",
            "end_date": "结束日期（格式：YYYY-MM-DD）",
        },
    },
    "query_by_distance": {
        "description": "按距离范围查询跑步记录",
        "parameters": {
            "min_distance": "最小距离（公里）",
            "max_distance": "最大距离（公里，可选）",
        },
    },
    "update_memory": {
        "description": "更新 Agent 观察笔记到 MEMORY.md",
        "parameters": {
            "note": "观察笔记内容",
            "category": "笔记分类（training/preference/injury/other，默认 other）",
        },
    },
}
