# Agent 工具集
# 封装为 nanobot-ai 可识别的工具

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any

import polars as pl

from src.core.context import AppContext, AppContextFactory

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
        """同步调用方法并返回 JSON 字符串

        返回格式：直接返回数据本身（dict/list 等），错误时返回包含 error 字段的 dict
        """
        try:
            logger.info(f"工具调用开始: {func.__name__}, 参数: {kwargs}")
            result = func(*args, **kwargs)
            logger.info(
                f"工具调用成功: {func.__name__}, 结果类型: {type(result)}, 结果: {str(result)[:200]}"
            )

            # 如果结果已经是 dict 且包含 error 字段，直接返回
            if isinstance(result, dict) and "error" in result:
                logger.warning(f"工具返回错误: {result}")
                return json.dumps(result, ensure_ascii=False, default=str)
            # 如果结果是 dict 且包含 message 字段（如暂无数据），转换为 error 格式
            if isinstance(result, dict) and "message" in result:
                logger.info(f"工具返回消息: {result}")
                return json.dumps(
                    {"error": result["message"]}, ensure_ascii=False, default=str
                )
            # 正常返回数据（直接返回，不包装）
            json_result = json.dumps(result, ensure_ascii=False, default=str)
            logger.info(f"工具返回 JSON 长度: {len(json_result)}")
            return json_result
        except Exception as e:
            logger.error(
                f"工具调用异常: {func.__name__}, 错误: {str(e)}", exc_info=True
            )
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
        return "按日期范围查询跑步记录"

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
        return "按距离范围查询跑步记录"

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


class GenerateTrainingPlanTool(BaseTool):
    """生成训练计划工具"""

    @property
    def name(self) -> str:
        return "generate_training_plan"

    @property
    def description(self) -> str:
        return "根据用户目标生成个性化训练计划"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "goal_distance_km": {
                    "type": "number",
                    "description": "目标比赛距离（公里），例如：5, 10, 21.0975, 42.195",
                },
                "goal_date": {
                    "type": "string",
                    "description": "目标比赛日期（YYYY-MM-DD）",
                },
            },
            "required": ["goal_distance_km", "goal_date"],
        }

    async def execute(self, **kwargs: Any) -> str:
        goal_distance_km = float(kwargs.get("goal_distance_km", 0))
        goal_date = kwargs.get("goal_date", "")
        return self._run_sync(
            self.runner_tools.generate_training_plan, goal_distance_km, goal_date
        )


class RunnerTools:
    """跑步助理工具集（业务逻辑层）"""

    def __init__(self, context: AppContext | None = None):
        """
        初始化工具集

        Args:
            context: 应用上下文（可选），未提供则使用全局上下文
        """
        if context is None:
            context = AppContextFactory.create()

        self.storage = context.storage
        self.analytics = context.analytics
        self.profile_storage = context.profile_storage

    def get_running_stats(
        self, start_date: str | None = None, end_date: str | None = None
    ) -> dict[str, Any]:
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

    def get_recent_runs(self, limit: int = 10) -> list[dict[str, Any]]:
        lf = self.storage.read_parquet()

        session_df = (
            lf.group_by("session_start_time")
            .agg(
                [
                    pl.col("session_start_time").first().alias("timestamp"),
                    pl.col("session_total_distance").first().alias("distance"),
                    pl.col("session_total_timer_time").first().alias("duration"),
                    pl.col("session_avg_heart_rate").first().alias("avg_hr"),
                ]
            )
            .sort("timestamp", descending=True)
            .limit(limit)
            .collect()
        )

        runs = []
        for row in session_df.iter_rows(named=True):
            distance = row.get("distance") or 0
            duration = row.get("duration") or 0
            distance_km = distance / 1000
            duration_min = duration / 60
            pace = duration_min / distance_km if distance_km > 0 else 0

            # 计算VDOT值
            vdot = None
            if distance > 0 and duration > 0:
                vdot = self.analytics.calculate_vdot(distance, duration)

            runs.append(
                {
                    "timestamp": str(row.get("timestamp", "N/A")),
                    "distance_km": round(distance_km, 2),
                    "duration_min": round(duration_min, 1),
                    "avg_pace_sec_km": round(pace, 1) if pace > 0 else None,
                    "avg_heart_rate": row.get("avg_hr"),
                    "vdot": round(vdot, 2) if vdot else None,
                }
            )

        return runs

    def calculate_vdot_for_run(self, distance_m: float, time_s: float) -> float:
        return self.analytics.calculate_vdot(distance_m, time_s)

    def get_vdot_trend(self, limit: int = 20) -> list[dict[str, Any]]:
        lf = self.storage.read_parquet()

        session_df = (
            lf.group_by("session_start_time")
            .agg(
                [
                    pl.col("session_start_time").first().alias("timestamp"),
                    pl.col("session_total_distance").first().alias("distance"),
                    pl.col("session_total_timer_time").first().alias("duration"),
                ]
            )
            .sort("timestamp", descending=True)
            .limit(limit)
            .collect()
        )

        vdot_trend = []
        for row in session_df.iter_rows(named=True):
            distance = row.get("distance", 0)
            duration = row.get("duration", 0)

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

    def get_hr_drift_analysis(self, run_id: str | None = None) -> dict[str, Any]:
        lf = self.storage.read_parquet()
        df = lf.collect()

        if df.height == 0:
            return {"error": "暂无数据"}

        if "heart_rate" not in df.columns:
            return {"error": "暂无心率数据"}

        heart_rate = df.select(pl.col("heart_rate")).to_series().to_list()

        pace_list: list[float] = []
        if "speed" in df.columns:
            speed_values = df.select(pl.col("speed")).to_series().to_list()
            pace_list = [1000 / s for s in speed_values if s and s > 0]
        elif "enhanced_speed" in df.columns:
            speed_values = df.select(pl.col("enhanced_speed")).to_series().to_list()
            pace_list = [1000 / s for s in speed_values if s and s > 0]

        return self.analytics.analyze_hr_drift(heart_rate, pace_list)

    def get_training_load(self, days: int = 42) -> dict[str, Any]:
        return self.analytics.get_training_load(days)

    def query_by_date_range(
        self, start_date: str, end_date: str
    ) -> list[dict[str, Any]]:
        """
        按日期范围查询跑步记录（按会话聚合）

        数据模型说明：
        - 存储的数据包含采样点数据和会话数据
        - 需要按 session_start_time 聚合，避免返回重复的采样点数据
        - 使用 session_start_time 进行日期过滤，而不是 timestamp
        - 结束日期包含当天一整天
        """
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
        except ValueError:
            return [{"error": "日期格式错误，应为 YYYY-MM-DD"}]

        lf = self.storage.read_parquet()

        # 检查空数据
        if len(lf.collect_schema()) == 0:
            return []

        # 按会话聚合，使用 session_start_time 进行过滤
        session_df = (
            lf.group_by("session_start_time")
            .agg(
                [
                    pl.col("session_start_time").first().alias("session_start"),
                    pl.col("session_total_distance").first().alias("distance"),
                    pl.col("session_total_timer_time").first().alias("duration"),
                    pl.col("session_avg_heart_rate").first().alias("avg_hr"),
                ]
            )
            .filter(pl.col("session_start").is_between(start_dt, end_dt))
            .sort("session_start", descending=True)
            .collect()
        )

        if session_df.is_empty():
            return []

        results = []
        for row in session_df.iter_rows(named=True):
            distance = row.get("distance") or 0
            duration = row.get("duration") or 0
            avg_hr = row.get("avg_hr")

            distance_km = distance / 1000
            duration_minutes = duration / 60
            pace = duration_minutes / distance_km if distance_km > 0 else 0

            results.append(
                {
                    "timestamp": str(row.get("session_start", "N/A")),
                    "distance": round(distance_km, 2),
                    "duration": duration,
                    "heart_rate": avg_hr if avg_hr is not None else "N/A",
                    "pace": round(pace, 2),
                }
            )

        return results

    def query_by_distance(
        self, min_distance: float, max_distance: float | None = None
    ) -> list[dict[str, Any]]:
        """
        按距离范围查询跑步记录（按会话聚合）

        数据模型说明：
        - 存储的数据包含采样点数据和会话数据
        - 需要按 session_start_time 聚合，避免返回重复的采样点数据
        """
        min_meters = min_distance * 1000
        max_meters = max_distance * 1000 if max_distance else None

        lf = self.storage.read_parquet()

        if max_meters:
            distance_filter = pl.col("session_total_distance").is_between(
                min_meters, max_meters
            )
        else:
            distance_filter = pl.col("session_total_distance") >= min_meters

        # 按会话聚合，避免返回重复的采样点数据
        session_df = (
            lf.filter(distance_filter)
            .group_by("session_start_time")
            .agg(
                [
                    pl.col("session_start_time").first().alias("session_start"),
                    pl.col("session_total_distance").first().alias("distance"),
                    pl.col("session_total_timer_time").first().alias("duration"),
                    pl.col("session_avg_heart_rate").first().alias("avg_hr"),
                ]
            )
            .sort("session_start", descending=True)
            .collect()
        )

        results = []
        for row in session_df.iter_rows(named=True):
            distance = row.get("distance") or 0
            duration = row.get("duration") or 0
            avg_hr = row.get("avg_hr")

            distance_km = distance / 1000
            duration_minutes = duration / 60
            pace = duration_minutes / distance_km if distance_km > 0 else 0

            results.append(
                {
                    "timestamp": str(row.get("session_start", "N/A")),
                    "distance": round(distance_km, 2),
                    "duration": duration,
                    "heart_rate": avg_hr if avg_hr is not None else "N/A",
                    "pace": round(pace, 2),
                }
            )

        return results

    def update_memory(self, note: str, category: str = "other") -> dict[str, Any]:
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
                return {
                    "error": f"无效的分类，必须是 {', '.join(valid_categories)} 之一"
                }

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

    def generate_training_plan(
        self, goal_distance_km: float, goal_date: str
    ) -> dict[str, Any]:
        """
        生成训练计划

        Args:
            goal_distance_km: 目标比赛距离（公里）
            goal_date: 目标比赛日期（YYYY-MM-DD）

        Returns:
            Dict: 包含训练计划信息
        """
        try:
            from src.core.training_plan import TrainingPlanEngine

            # 获取用户画像
            profile = self.profile_storage.load_profile_json()
            if not profile:
                return {"error": "未找到用户画像，请先导入跑步数据"}

            profile_dict = profile.to_dict()
            vdot = profile_dict.get("estimated_vdot", 35.0)
            volume = profile_dict.get("weekly_avg_distance", 30.0)
            age = profile_dict.get("age", 30)
            resting_hr = profile_dict.get("resting_hr", 60)

            # 生成训练计划
            engine = TrainingPlanEngine()
            plan = engine.generate_plan(
                user_id="default",
                goal_distance_km=goal_distance_km,
                goal_date=goal_date,
                current_vdot=vdot,
                current_weekly_distance_km=volume,
                age=age,
                resting_hr=resting_hr,
            )

            return {
                "success": True,
                "message": f"已生成{goal_distance_km}km 训练计划，共{len(plan.weeks)}周",
                "fitness_level": plan.fitness_level.value,
                "total_weeks": len(plan.weeks),
                "total_distance": sum(ws.weekly_distance_km for ws in plan.weeks),
            }

        except Exception as e:
            logger.error(f"生成训练计划失败：{e}")
            return {"error": str(e)}


def create_tools(runner_tools: RunnerTools) -> list[BaseTool]:
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
        GenerateTrainingPlanTool(runner_tools),
    ]


TOOL_DESCRIPTIONS = {
    "get_running_stats": {
        "description": "获取跑步统计数据，包括总次数、总距离、平均距离等。返回JSON格式：{success: true, data: {total_runs: 总次数, total_distance: 总距离(米), total_duration: 总时长(秒), avg_distance: 平均距离(米), avg_duration: 平均时长(秒), max_distance: 最大距离(米), avg_heart_rate: 平均心率}} 或 {success: false, error: 错误信息}",
        "parameters": {
            "start_date": "开始日期（可选，格式：YYYY-MM-DD）",
            "end_date": "结束日期（可选，格式：YYYY-MM-DD）",
        },
    },
    "get_recent_runs": {
        "description": "获取最近的跑步记录列表。返回JSON格式：{success: true, data: [{timestamp: 时间, distance_km: 距离(公里), duration_min: 时长(分钟), avg_pace_sec_km: 配速(秒/公里), avg_heart_rate: 平均心率, vdot: VDOT值}, ...]} 或 {success: false, error: 错误信息}。注意：vdot字段已包含计算好的VDOT值，直接使用即可，不要自己计算",
        "parameters": {"limit": "返回数量限制（默认 10 条）"},
    },
    "calculate_vdot_for_run": {
        "description": "计算单次跑步的VDOT值（跑力值），使用Jack Daniels公式自动计算。注意：VDOT计算公式复杂，请使用此工具计算，不要自己用简单公式计算",
        "parameters": {"distance_m": "距离（米）", "time_s": "用时（秒）"},
    },
    "get_vdot_trend": {
        "description": "获取VDOT（跑力值）趋势变化，自动从历史跑步数据计算每次跑步的VDOT值。当用户询问'我的VDOT是多少'、'我的跑力值'或'查看VDOT趋势'时使用此工具。不需要用户提供任何参数。返回JSON格式：{success: true, data: [{timestamp: 时间, distance: 距离(米), vdot: VDOT值}, ...]} 或 {success: false, error: 错误信息}",
        "parameters": {"limit": "返回数量限制（默认 20 条，可选）"},
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
        "description": "按日期范围查询跑步记录。返回JSON格式：{success: true, data: [{timestamp: 时间, distance: 距离(公里), duration: 时长(秒), heart_rate: 平均心率, pace: 配速(分钟/公里)}, ...]} 或 {success: false, error: 错误信息}",
        "parameters": {
            "start_date": "开始日期（格式：YYYY-MM-DD）",
            "end_date": "结束日期（格式：YYYY-MM-DD）",
        },
    },
    "query_by_distance": {
        "description": "按距离范围查询跑步记录。返回JSON格式：{success: true, data: [{timestamp: 时间, distance: 距离(公里), duration: 时长(秒), heart_rate: 平均心率, pace: 配速(分钟/公里)}, ...]} 或 {success: false, error: 错误信息}",
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
