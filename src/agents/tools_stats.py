# 统计/分析工具类
# 包含跑步统计、VDOT计算、训练负荷、心率漂移、日期/距离查询等工具

from __future__ import annotations

from typing import Any

from src.agents.tools import BaseTool


class GetRunningStatsTool(BaseTool):
    """获取跑步统计数据"""

    @property
    def name(self) -> str:
        return "get_running_stats"

    @property
    def description(self) -> str:
        return "获取跑步统计数据。返回JSON格式数据，包含 total_runs（总次数）、total_distance（总距离，单位米）、total_duration（总时长，单位秒）等字段。当用户询问'跑了多少次'、'总距离'、'跑步统计'时使用此工具。"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "description": "开始日期（可选，格式：YYYY-MM-DD）",
                },
                "end_date": {
                    "type": "string",
                    "description": "结束日期（可选，格式：YYYY-MM-DD）",
                },
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
        return "获取最近的跑步记录列表。返回JSON数组，每条记录包含 timestamp（时间）、distance_km（距离，单位公里）、duration_min（时长，单位分钟）、vdot（跑力值）等字段。当用户询问'最近跑步'、'跑步记录'时使用此工具。"

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
        import json

        distance_m = kwargs.get("distance_m")
        time_s = kwargs.get("time_s")

        if distance_m is None or time_s is None:
            return json.dumps(
                {
                    "success": False,
                    "error": "缺少必要参数：distance_m（距离，米）和 time_s（用时，秒）",
                },
                ensure_ascii=False,
            )

        try:
            distance_m = float(distance_m)
            time_s = float(time_s)
        except (TypeError, ValueError):
            return json.dumps(
                {
                    "success": False,
                    "error": "参数类型错误：distance_m 和 time_s 必须为数字",
                },
                ensure_ascii=False,
            )

        if distance_m <= 0 or time_s <= 0:
            return json.dumps(
                {"success": False, "error": "参数值错误：距离和时间必须为正数"},
                ensure_ascii=False,
            )

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
        return "获取VDOT（跑力值）趋势变化，自动从历史跑步数据计算每次跑步的VDOT值。当用户询问'我的VDOT是多少'、'我的跑力值'或'查看VDOT趋势'时使用此工具。不需要用户提供任何参数，工具会自动从已导入的跑步数据中计算VDOT"

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
            "properties": {
                "run_id": {"type": "string", "description": "活动ID（可选）"}
            },
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
                "days": {
                    "type": "integer",
                    "description": "分析天数（默认42天）",
                    "default": 42,
                }
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
        return "按日期范围查询跑步记录。返回JSON数组，每条记录包含 timestamp（时间）、distance（距离，单位公里）、duration（时长，单位秒）、heart_rate（平均心率）、pace（配速，单位分钟/公里）。当用户询问'某段时间跑了多少'、'上个月跑步'、'本周跑步'时使用此工具。"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "description": "开始日期（格式：YYYY-MM-DD）",
                },
                "end_date": {
                    "type": "string",
                    "description": "结束日期（格式：YYYY-MM-DD）",
                },
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
        return "按距离范围查询跑步记录。返回JSON数组，每条记录包含 timestamp（时间）、distance（距离，单位公里）、duration（时长，单位秒）、heart_rate（平均心率）、pace（配速，单位分钟/公里）。当用户询问'跑了多少公里'、'长距离跑步'、'短距离跑步'时使用此工具。"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "min_distance": {"type": "number", "description": "最小距离（公里）"},
                "max_distance": {
                    "type": "number",
                    "description": "最大距离（公里，可选）",
                },
            },
            "required": ["min_distance"],
        }

    async def execute(self, **kwargs: Any) -> str:
        min_distance = kwargs.get("min_distance", 0)
        max_distance = kwargs.get("max_distance")
        return self._run_sync(
            self.runner_tools.query_by_distance, min_distance, max_distance
        )
