# Agent 工具集
# 封装为 nanobot-ai 可识别的工具

from __future__ import annotations

import json
import logging
from abc import abstractmethod
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.core.personality import UserPreferences

import polars as pl
from nanobot.agent.tools.base import Tool

from src.core.base.context import AppContext, AppContextFactory
from src.core.tools.weather_training_coordinator import TrainingData

logger = logging.getLogger(__name__)


class BaseTool(Tool):
    """工具基类（适配nanobot-ai 0.1.4+）"""

    concurrency_safe: bool = True

    def __init__(self, runner_tools: RunnerTools):
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
    async def execute(self, **kwargs: Any) -> Any:
        """执行工具"""
        pass

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
            # 如果结果是 dict 且仅含 message 字段（如暂无数据），转换为 error 格式
            if (
                isinstance(result, dict)
                and "message" in result
                and "success" not in result
            ):
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


class RecordPlanExecutionTool(BaseTool):
    """记录计划执行反馈工具 - v0.10.0新增"""

    @property
    def name(self) -> str:
        return "record_plan_execution"

    @property
    def description(self) -> str:
        return "记录训练计划执行反馈，包括完成度、体感评分、反馈备注等。当用户说'记录训练反馈'、'今天跑完了'、'训练完成'时使用此工具。"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "plan_id": {
                    "type": "string",
                    "description": "训练计划ID",
                },
                "date": {
                    "type": "string",
                    "description": "日期（YYYY-MM-DD）",
                },
                "completion_rate": {
                    "type": "number",
                    "description": "完成度（0.0-1.0），1.0表示完全完成",
                },
                "effort_score": {
                    "type": "integer",
                    "description": "体感评分（1-10），1最轻松，10最吃力",
                },
                "notes": {
                    "type": "string",
                    "description": "反馈备注",
                },
                "actual_distance_km": {
                    "type": "number",
                    "description": "实际距离（公里）",
                },
                "actual_duration_min": {
                    "type": "integer",
                    "description": "实际时长（分钟）",
                },
                "actual_avg_hr": {
                    "type": "integer",
                    "description": "实际平均心率",
                },
            },
            "required": ["plan_id", "date"],
        }

    async def execute(self, **kwargs: Any) -> str:
        return self._run_sync(
            self.runner_tools.record_plan_execution,
            plan_id=kwargs.get("plan_id", ""),
            date=kwargs.get("date", ""),
            completion_rate=kwargs.get("completion_rate"),
            effort_score=kwargs.get("effort_score"),
            notes=kwargs.get("notes", ""),
            actual_distance_km=kwargs.get("actual_distance_km"),
            actual_duration_min=kwargs.get("actual_duration_min"),
            actual_avg_hr=kwargs.get("actual_avg_hr"),
        )


class GetPlanExecutionStatsTool(BaseTool):
    """获取计划执行统计工具 - v0.10.0新增"""

    @property
    def name(self) -> str:
        return "get_plan_execution_stats"

    @property
    def description(self) -> str:
        return "获取训练计划执行统计，包括完成率、平均体感评分、总距离等。当用户询问'训练完成情况'、'计划执行统计'时使用此工具。"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "plan_id": {
                    "type": "string",
                    "description": "训练计划ID",
                },
            },
            "required": ["plan_id"],
        }

    async def execute(self, **kwargs: Any) -> str:
        return self._run_sync(
            self.runner_tools.get_plan_execution_stats,
            plan_id=kwargs.get("plan_id", ""),
        )


class AnalyzeTrainingResponseTool(BaseTool):
    """训练响应分析工具 - v0.10.0新增"""

    @property
    def name(self) -> str:
        return "analyze_training_response"

    @property
    def description(self) -> str:
        return "分析训练响应模式，识别用户最适应和最不适应的训练类型。当用户询问'训练适应情况'、'哪种训练最适合我'时使用此工具。"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "plan_id": {
                    "type": "string",
                    "description": "训练计划ID",
                },
            },
            "required": ["plan_id"],
        }

    async def execute(self, **kwargs: Any) -> str:
        return self._run_sync(
            self.runner_tools.analyze_training_response,
            plan_id=kwargs.get("plan_id", ""),
        )


class AdjustPlanTool(BaseTool):
    """计划调整工具 - v0.11.0新增"""

    @property
    def name(self) -> str:
        return "adjust_plan"

    @property
    def description(self) -> str:
        return "调整训练计划。支持自然语言调整指令，如'下周减量'、'把周三的间歇跑改成轻松跑'。当用户说'调整计划'、'减量'、'加量'时使用此工具。"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "plan_id": {
                    "type": "string",
                    "description": "训练计划ID",
                },
                "adjustment_request": {
                    "type": "string",
                    "description": "调整请求（自然语言），如'下周减量20%'、'增加间歇跑'",
                },
                "confirmation_required": {
                    "type": "boolean",
                    "description": "是否需要确认后再执行调整（默认true）",
                },
            },
            "required": ["plan_id", "adjustment_request"],
        }

    async def execute(self, **kwargs: Any) -> str:
        return self._run_sync(
            self.runner_tools.adjust_plan,
            plan_id=kwargs.get("plan_id", ""),
            adjustment_request=kwargs.get("adjustment_request", ""),
            confirmation_required=kwargs.get("confirmation_required", True),
        )


class GetPlanAdjustmentSuggestionsTool(BaseTool):
    """获取计划调整建议工具 - v0.11.0新增"""

    @property
    def name(self) -> str:
        return "get_plan_adjustment_suggestions"

    @property
    def description(self) -> str:
        return "获取训练计划调整建议。基于训练数据和执行反馈，生成个性化调整建议。当用户说'给我建议'、'如何调整'、'训练建议'时使用此工具。"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "plan_id": {
                    "type": "string",
                    "description": "训练计划ID",
                },
            },
            "required": ["plan_id"],
        }

    async def execute(self, **kwargs: Any) -> str:
        return self._run_sync(
            self.runner_tools.get_plan_adjustment_suggestions,
            plan_id=kwargs.get("plan_id", ""),
        )


class EvaluateGoalAchievementTool(BaseTool):
    """目标达成评估工具 - v0.12.0新增"""

    @property
    def name(self) -> str:
        return "evaluate_goal_achievement"

    @property
    def description(self) -> str:
        return "评估目标达成概率。基于当前体能、训练趋势和目标差距，预测目标达成概率和关键风险。当用户说'我能达到目标吗'、'目标评估'、'达成概率'时使用此工具。"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "goal_type": {
                    "type": "string",
                    "description": "目标类型（vdot/5k/10k/half_marathon/marathon）",
                },
                "goal_value": {
                    "type": "number",
                    "description": "目标值（VDOT值或秒数）",
                },
                "current_vdot": {
                    "type": "number",
                    "description": "当前VDOT值",
                },
                "weeks_available": {
                    "type": "integer",
                    "description": "可用训练周数（可选）",
                },
            },
            "required": ["goal_type", "goal_value", "current_vdot"],
        }

    async def execute(self, **kwargs: Any) -> str:
        return self._run_sync(
            self.runner_tools.evaluate_goal_achievement,
            goal_type=kwargs.get("goal_type", "vdot"),
            goal_value=kwargs.get("goal_value", 0.0),
            current_vdot=kwargs.get("current_vdot", 0.0),
            weeks_available=kwargs.get("weeks_available"),
        )


class CreateLongTermPlanTool(BaseTool):
    """创建长期训练规划工具 - v0.12.0新增"""

    @property
    def name(self) -> str:
        return "create_long_term_plan"

    @property
    def description(self) -> str:
        return "创建长期训练规划。支持年度/赛季/多周期规划，自动生成基础期、提升期、巅峰期、减量期。当用户说'制定长期计划'、'备赛计划'、'年度规划'时使用此工具。"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "plan_name": {
                    "type": "string",
                    "description": "计划名称",
                },
                "current_vdot": {
                    "type": "number",
                    "description": "当前VDOT值",
                },
                "target_vdot": {
                    "type": "number",
                    "description": "目标VDOT值（可选）",
                },
                "target_race": {
                    "type": "string",
                    "description": "目标赛事名称（可选）",
                },
                "target_date": {
                    "type": "string",
                    "description": "目标日期（YYYY-MM-DD，可选）",
                },
                "total_weeks": {
                    "type": "integer",
                    "description": "总训练周数（默认16）",
                },
                "fitness_level": {
                    "type": "string",
                    "description": "体能水平（beginner/intermediate/advanced/elite，默认intermediate）",
                },
            },
            "required": ["plan_name", "current_vdot"],
        }

    async def execute(self, **kwargs: Any) -> str:
        return self._run_sync(
            self.runner_tools.create_long_term_plan,
            plan_name=kwargs.get("plan_name", ""),
            current_vdot=kwargs.get("current_vdot", 0.0),
            target_vdot=kwargs.get("target_vdot"),
            target_race=kwargs.get("target_race"),
            target_date=kwargs.get("target_date"),
            total_weeks=kwargs.get("total_weeks", 16),
            fitness_level=kwargs.get("fitness_level", "intermediate"),
        )


class GetSmartTrainingAdviceTool(BaseTool):
    """获取智能训练建议工具 - v0.12.0新增"""

    @property
    def name(self) -> str:
        return "get_smart_training_advice"

    @property
    def description(self) -> str:
        return "获取智能训练建议。基于训练数据和体能状态，生成训练、恢复、营养、伤病预防等多维度建议。当用户说'给我训练建议'、'如何恢复'、'营养建议'时使用此工具。"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "current_vdot": {
                    "type": "number",
                    "description": "当前VDOT值（可选）",
                },
                "weekly_volume_km": {
                    "type": "number",
                    "description": "周跑量（公里，可选）",
                },
                "training_consistency": {
                    "type": "number",
                    "description": "训练一致性（0-1，可选）",
                },
                "injury_risk": {
                    "type": "string",
                    "description": "伤病风险（low/medium/high，可选）",
                },
                "goal_type": {
                    "type": "string",
                    "description": "目标类型（5k/10k/half_marathon/marathon，可选）",
                },
            },
            "required": [],
        }

    async def execute(self, **kwargs: Any) -> str:
        return self._run_sync(
            self.runner_tools.get_smart_training_advice,
            current_vdot=kwargs.get("current_vdot"),
            weekly_volume_km=kwargs.get("weekly_volume_km", 0.0),
            training_consistency=kwargs.get("training_consistency", 1.0),
            injury_risk=kwargs.get("injury_risk", "low"),
            goal_type=kwargs.get("goal_type"),
        )


class GetWeatherTrainingAdviceTool(BaseTool):
    """天气+训练协同建议工具 - v0.13.0新增"""

    @property
    def name(self) -> str:
        return "get_weather_training_advice"

    @property
    def description(self) -> str:
        return "获取天气+训练综合建议。结合天气数据和训练数据，生成多维度的训练建议。当用户询问'今天适合跑步吗'、'天气对训练的影响'、'综合训练建议'时使用此工具。"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "temperature": {
                    "type": "number",
                    "description": "温度（摄氏度）",
                },
                "humidity": {
                    "type": "number",
                    "description": "湿度（百分比，0-100）",
                },
                "weather": {
                    "type": "string",
                    "description": "天气状况（晴/阴/雨/雪等）",
                },
                "wind": {
                    "type": "string",
                    "description": "风力描述（可选）",
                },
                "precipitation": {
                    "type": "number",
                    "description": "降水概率（百分比，0-100，可选）",
                },
                "uv_index": {
                    "type": "number",
                    "description": "紫外线指数（可选）",
                },
            },
            "required": ["temperature", "humidity", "weather"],
        }

    async def execute(self, **kwargs: Any) -> str:
        return self._run_sync(
            self.runner_tools.get_weather_training_advice,
            temperature=kwargs.get("temperature", 20.0),
            humidity=kwargs.get("humidity", 50.0),
            weather=kwargs.get("weather", "晴"),
            wind=kwargs.get("wind", "无风"),
            precipitation=kwargs.get("precipitation", 0.0),
            uv_index=kwargs.get("uv_index", 0.0),
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
            "total_runs": row[0] if row[0] is not None else 0,
            "total_distance": row[1] if row[1] is not None else 0.0,
            "total_duration": row[2] if row[2] is not None else 0.0,
            "avg_distance": row[3] if row[3] is not None else 0.0,
            "avg_duration": row[4] if row[4] is not None else 0.0,
            "max_distance": row[5] if row[5] is not None else 0.0,
            "avg_heart_rate": row[6] if row[6] is not None else 0.0,
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
            distance_raw = row.get("distance")
            duration_raw = row.get("duration")
            distance = float(distance_raw) if distance_raw is not None else 0.0
            duration = float(duration_raw) if duration_raw is not None else 0.0
            distance_km = distance / 1000
            duration_min = duration / 60
            pace = duration_min / distance_km if distance_km > 0 else 0

            vdot = None
            if distance >= 1500 and duration > 0:
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
            distance_raw = row.get("distance")
            duration_raw = row.get("duration")
            timestamp = row.get("timestamp")
            distance = float(distance_raw) if distance_raw is not None else 0.0
            duration = float(duration_raw) if duration_raw is not None else 0.0

            if distance >= 1500 and duration > 0:
                vdot = self.analytics.calculate_vdot(distance, duration)

                date_str = "N/A"
                if timestamp is not None:
                    date_str = str(timestamp)[:10]

                duration_min = duration / 60
                hours = int(duration_min // 60)
                minutes = int(duration_min % 60)
                seconds = int(duration % 60)
                duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

                vdot_trend.append(
                    {
                        "date": date_str,
                        "distance_km": distance / 1000,
                        "duration": duration_str,
                        "vdot": vdot,
                    }
                )

        return vdot_trend

    def get_hr_drift_analysis(self, _run_id: str | None = None) -> dict[str, Any]:
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

        result = self.analytics.analyze_hr_drift(heart_rate, pace_list)
        return result.to_dict()

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
            distance_raw = row.get("distance")
            duration_raw = row.get("duration")
            avg_hr = row.get("avg_hr")
            distance = float(distance_raw) if distance_raw is not None else 0.0
            duration = float(duration_raw) if duration_raw is not None else 0.0

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
            distance_raw = row.get("distance")
            duration_raw = row.get("duration")
            avg_hr = row.get("avg_hr")
            distance = float(distance_raw) if distance_raw is not None else 0.0
            duration = float(duration_raw) if duration_raw is not None else 0.0

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

            profile = self.profile_storage.load_profile_json()
            if not profile:
                return {"error": "未找到用户画像，请先导入跑步数据"}

            profile_dict = profile.to_dict()
            vdot = profile_dict.get("estimated_vdot", 35.0)
            volume = profile_dict.get("weekly_avg_distance", 30.0)
            age = profile_dict.get("age", 30)
            resting_hr = profile_dict.get("resting_hr", 60)

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

    def record_plan_execution(
        self,
        plan_id: str,
        date: str,
        completion_rate: float | None = None,
        effort_score: int | None = None,
        notes: str = "",
        actual_distance_km: float | None = None,
        actual_duration_min: int | None = None,
        actual_avg_hr: int | None = None,
    ) -> dict[str, Any]:
        """记录计划执行反馈

        Args:
            plan_id: 计划ID
            date: 日期（YYYY-MM-DD）
            completion_rate: 完成度（0.0-1.0）
            effort_score: 体感评分（1-10）
            notes: 反馈备注
            actual_distance_km: 实际距离（公里）
            actual_duration_min: 实际时长（分钟）
            actual_avg_hr: 实际平均心率

        Returns:
            dict: 记录结果
        """
        try:
            from src.core.base.context import get_context

            context = get_context()
            plan_manager = context.plan_manager
            result = plan_manager.record_execution(
                plan_id=plan_id,
                date=date,
                completion_rate=completion_rate,
                effort_score=effort_score,
                notes=notes,
                actual_distance_km=actual_distance_km,
                actual_duration_min=actual_duration_min,
                actual_avg_hr=actual_avg_hr,
            )
            return result
        except Exception as e:
            logger.error(f"记录执行反馈失败：{e}")
            return {"error": str(e)}

    def get_plan_execution_stats(self, plan_id: str) -> dict[str, Any]:
        """获取计划执行统计

        Args:
            plan_id: 计划ID

        Returns:
            dict: 执行统计数据
        """
        try:
            from src.core.base.context import get_context

            context = get_context()
            execution_repo = context.plan_execution_repo
            stats = execution_repo.get_plan_execution_stats(plan_id)
            return stats.to_dict()
        except Exception as e:
            logger.error(f"获取执行统计失败：{e}")
            return {"error": str(e)}

    def analyze_training_response(self, plan_id: str) -> dict[str, Any]:
        """分析训练响应模式

        Args:
            plan_id: 计划ID

        Returns:
            dict: 训练响应分析结果
        """
        try:
            from src.core.base.context import get_context

            context = get_context()
            analyzer = context.training_response_analyzer
            return analyzer.analyze_plan_response(plan_id)
        except Exception as e:
            logger.error(f"训练响应分析失败：{e}")
            return {"error": str(e)}

    def adjust_plan(
        self,
        plan_id: str,
        adjustment_request: str,
        confirmation_required: bool = True,
    ) -> dict[str, Any]:
        """调整训练计划

        Args:
            plan_id: 计划ID
            adjustment_request: 调整请求（自然语言）
            confirmation_required: 是否需要确认

        Returns:
            dict: 调整结果
        """
        try:
            from src.core.base.context import get_context

            context = get_context()
            validator = context.plan_adjustment_validator

            default_adjustment = validator.get_default_adjustment(adjustment_request)

            validation = validator.validate(default_adjustment)

            if not validation.passed:
                violation_msgs = [v.message for v in validation.violations]
                return {
                    "success": False,
                    "error": "调整建议不符合运动科学原则",
                    "violations": violation_msgs,
                }

            if confirmation_required:
                return {
                    "success": True,
                    "plan_id": plan_id,
                    "adjustment": default_adjustment.to_dict(),
                    "validation": {"passed": True},
                    "requires_confirmation": True,
                }

            return {
                "success": True,
                "plan_id": plan_id,
                "adjustment": default_adjustment.to_dict(),
                "validation": {"passed": True},
                "requires_confirmation": False,
            }
        except Exception as e:
            logger.error(f"调整训练计划失败：{e}")
            return {"error": str(e)}

    def get_plan_adjustment_suggestions(self, plan_id: str) -> dict[str, Any]:
        """获取计划调整建议

        Args:
            plan_id: 计划ID

        Returns:
            dict: 调整建议
        """
        try:
            from src.core.base.context import get_context

            context = get_context()
            execution_repo = context.plan_execution_repo
            stats = execution_repo.get_plan_execution_stats(plan_id)

            suggestions: list[dict[str, Any]] = []

            if stats.completion_rate < 0.5:
                suggestions.append(
                    {
                        "suggestion_type": "training",
                        "suggestion_content": "完成率偏低，建议降低训练量或增加恢复日",
                        "priority": "high",
                        "confidence": 0.8,
                    }
                )

            if stats.avg_effort_score > 7:
                suggestions.append(
                    {
                        "suggestion_type": "recovery",
                        "suggestion_content": "体感评分偏高，建议减少高强度训练比例",
                        "priority": "high",
                        "confidence": 0.75,
                    }
                )

            if stats.avg_hr_drift is not None and stats.avg_hr_drift > 5.0:
                suggestions.append(
                    {
                        "suggestion_type": "training",
                        "suggestion_content": "心率漂移较大，建议增加有氧基础训练",
                        "priority": "medium",
                        "confidence": 0.7,
                    }
                )

            if not suggestions:
                suggestions.append(
                    {
                        "suggestion_type": "training",
                        "suggestion_content": "训练状态良好，保持当前计划即可",
                        "priority": "low",
                        "confidence": 0.6,
                    }
                )

            return {
                "success": True,
                "plan_id": plan_id,
                "suggestions": suggestions,
            }
        except Exception as e:
            logger.error(f"获取调整建议失败：{e}")
            return {"error": str(e)}

    def evaluate_goal_achievement(
        self,
        goal_type: str,
        goal_value: float,
        current_vdot: float,
        weeks_available: int | None = None,
    ) -> dict[str, Any]:
        """评估目标达成概率 - v0.12.0新增

        Args:
            goal_type: 目标类型
            goal_value: 目标值
            current_vdot: 当前VDOT
            weeks_available: 可用周数

        Returns:
            dict: 评估结果
        """
        try:
            from src.core.plan.goal_prediction_engine import GoalPredictionEngine

            engine = GoalPredictionEngine()
            evaluation = engine.evaluate_goal(
                goal_type=goal_type,
                goal_value=goal_value,
                current_vdot=current_vdot,
                weeks_available=weeks_available,
            )

            return {
                "success": True,
                "data": evaluation.to_dict(),
            }
        except Exception as e:
            logger.error(f"目标评估失败：{e}")
            return {"success": False, "error": str(e)}

    def create_long_term_plan(
        self,
        plan_name: str,
        current_vdot: float,
        target_vdot: float | None = None,
        target_race: str | None = None,
        target_date: str | None = None,
        total_weeks: int = 16,
        fitness_level: str = "intermediate",
    ) -> dict[str, Any]:
        """创建长期训练规划 - v0.12.0新增

        Args:
            plan_name: 计划名称
            current_vdot: 当前VDOT
            target_vdot: 目标VDOT
            target_race: 目标赛事
            target_date: 目标日期
            total_weeks: 总周数
            fitness_level: 体能水平

        Returns:
            dict: 规划结果
        """
        try:
            from src.core.plan.long_term_plan_generator import LongTermPlanGenerator

            generator = LongTermPlanGenerator()
            plan = generator.generate_plan(
                plan_name=plan_name,
                current_vdot=current_vdot,
                target_vdot=target_vdot,
                target_race=target_race,
                target_date=target_date,
                total_weeks=total_weeks,
                fitness_level=fitness_level,
            )

            return {
                "success": True,
                "data": plan.to_dict(),
            }
        except Exception as e:
            logger.error(f"创建长期规划失败：{e}")
            return {"success": False, "error": str(e)}

    def get_smart_training_advice(
        self,
        current_vdot: float | None = None,
        weekly_volume_km: float = 0.0,
        training_consistency: float = 1.0,
        injury_risk: str = "low",
        goal_type: str | None = None,
    ) -> dict[str, Any]:
        """获取智能训练建议 - v0.12.0新增

        Args:
            current_vdot: 当前VDOT
            weekly_volume_km: 周跑量
            training_consistency: 训练一致性
            injury_risk: 伤病风险
            goal_type: 目标类型

        Returns:
            dict: 建议结果
        """
        try:
            from src.core.plan.smart_advice_engine import SmartAdviceEngine

            engine = SmartAdviceEngine()
            advices = engine.generate_advice(
                current_vdot=current_vdot,
                weekly_volume_km=weekly_volume_km,
                training_consistency=training_consistency,
                injury_risk=injury_risk,
                goal_type=goal_type,
            )

            return {
                "success": True,
                "data": {
                    "advices": [a.to_dict() for a in advices],
                    "total_count": len(advices),
                },
            }
        except Exception as e:
            logger.error(f"获取训练建议失败：{e}")
            return {"success": False, "error": str(e)}

    def get_weather_training_advice(
        self,
        temperature: float = 20.0,
        humidity: float = 50.0,
        weather: str = "晴",
        wind: str = "无风",
        precipitation: float = 0.0,
        uv_index: float = 0.0,
    ) -> dict[str, Any]:
        """获取天气+训练综合建议 - v0.13.0新增

        结合天气数据和训练数据，生成多维度的训练建议。

        Args:
            temperature: 温度（摄氏度）
            humidity: 湿度（百分比）
            weather: 天气状况
            wind: 风力描述
            precipitation: 降水概率
            uv_index: 紫外线指数

        Returns:
            dict: 综合建议结果
        """
        try:
            from src.core.tools.weather_training_coordinator import (
                WeatherData,
                WeatherTrainingCoordinator,
            )

            # 创建天气数据
            weather_data = WeatherData(
                temperature=temperature,
                humidity=humidity,
                weather=weather,
                wind=wind,
                precipitation=precipitation,
                uv_index=uv_index,
            )

            # 获取训练数据摘要
            profile = self.profile_storage.load_profile_json()
            training_data = self._build_training_data_summary(profile)

            # 使用协调器生成建议
            coordinator = WeatherTrainingCoordinator()
            advices = coordinator.generate_advice(weather_data, training_data)

            # 分析天气影响
            weather_impact = coordinator.analyze_weather_impact(weather_data)

            # 格式化建议
            formatted_advice = coordinator.format_advice_for_display(advices)

            return {
                "success": True,
                "data": {
                    "advices": [
                        {
                            "advice_type": a.advice_type,
                            "content": a.content,
                            "priority": a.priority,
                            "reason": a.reason,
                            "weather_impact": a.weather_impact,
                            "training_impact": a.training_impact,
                        }
                        for a in advices
                    ],
                    "total_count": len(advices),
                    "weather_impact": weather_impact,
                    "formatted_advice": formatted_advice,
                },
            }
        except Exception as e:
            logger.error(f"获取天气+训练建议失败：{e}")
            return {"success": False, "error": str(e)}

    def _build_training_data_summary(self, profile: Any) -> TrainingData:
        """构建训练数据摘要

        Args:
            profile: 用户画像数据

        Returns:
            TrainingData: 训练数据摘要
        """
        from src.core.tools.weather_training_coordinator import TrainingData

        # 获取最近一周跑量
        recent_runs = self.get_recent_runs(limit=7)
        recent_distance_km = sum(run.get("distance_km", 0) for run in recent_runs)

        # 获取平均VDOT
        vdot_trend = self.get_vdot_trend(limit=20)
        avg_vdot = None
        if vdot_trend:
            vdot_values: list[float] = [
                v.get("vdot", 0.0) for v in vdot_trend if v.get("vdot") is not None
            ]
            if vdot_values:
                avg_vdot = sum(vdot_values) / len(vdot_values)

        # 获取训练负荷
        training_load_data = self.get_training_load(days=42)
        training_load = training_load_data.get("ctl")

        # 判断恢复状态
        recovery_status = "良好"
        if training_load and training_load > 50:
            recovery_status = "疲劳"
        elif training_load and training_load > 40:
            recovery_status = "一般"

        # 获取最近一次跑步日期
        last_run_date = None
        if recent_runs:
            last_run_date = recent_runs[0].get("timestamp", "")[:10]

        return TrainingData(
            recent_distance_km=recent_distance_km,
            avg_vdot=avg_vdot,
            training_load=training_load,
            recovery_status=recovery_status,
            last_run_date=last_run_date,
        )

    def diagnose_suggestion(
        self,
        user_query: str,
        suggestion_text: str,
        tools_used: list[str] | None = None,
    ) -> dict[str, Any]:
        """验证AI建议质量 - v0.14.0新增

        Args:
            user_query: 用户原始查询
            suggestion_text: AI生成的建议文本
            tools_used: 使用的工具列表

        Returns:
            dict: 诊断报告
        """
        try:
            from src.core.diagnosis import SelfDiagnosis, SuggestionContext

            diagnosis = SelfDiagnosis()
            context = SuggestionContext(
                user_query=user_query,
                suggestion_text=suggestion_text,
                tools_used=tools_used or [],
            )
            report = diagnosis.validate_suggestion(context)

            return {
                "success": True,
                "data": report.to_dict(),
            }
        except Exception as e:
            logger.error(f"建议诊断失败: {e}")
            return {"success": False, "error": str(e)}

    def diagnose_error(self, error_message: str) -> dict[str, Any]:
        """诊断错误原因 - v0.14.0新增

        Args:
            error_message: 错误信息

        Returns:
            dict: 诊断报告
        """
        try:
            from src.core.diagnosis import SelfDiagnosis

            diagnosis = SelfDiagnosis()
            report = diagnosis.diagnose_error(error_message)

            return {
                "success": True,
                "data": report.to_dict(),
            }
        except Exception as e:
            logger.error(f"错误诊断失败: {e}")
            return {"success": False, "error": str(e)}

    def get_personalized_suggestion(
        self,
        suggestion_text: str,
        suggestion_type: str = "general",
    ) -> dict[str, Any]:
        """获取个性化建议 - v0.14.0新增

        Args:
            suggestion_text: 原始建议文本
            suggestion_type: 建议类型

        Returns:
            dict: 个性化建议
        """
        try:
            from src.core.base.context import get_context
            from src.core.personality import (
                PersonalizationEngine,
                SuggestionType,
            )

            context = get_context()
            preferences = self._load_preferences(context)

            engine = PersonalizationEngine(preferences=preferences)
            st = (
                SuggestionType(suggestion_type)
                if suggestion_type
                else SuggestionType.GENERAL
            )
            suggestion = engine.personalize_suggestion(suggestion_text, st)

            return {
                "success": True,
                "data": suggestion.to_dict(),
            }
        except Exception as e:
            logger.error(f"获取个性化建议失败: {e}")
            return {"success": False, "error": str(e)}

    def record_feedback(
        self,
        feedback_type: str,
        content: str,
        preference_category: str = "communication_style",
        suggestion_id: str = "",
    ) -> dict[str, Any]:
        """记录用户反馈 - v0.14.0新增

        Args:
            feedback_type: 反馈类型
            content: 反馈内容
            preference_category: 偏好类别
            suggestion_id: 关联的建议ID

        Returns:
            dict: 反馈记录结果
        """
        try:
            from src.core.base.context import get_context
            from src.core.personality import (
                FeedbackLoop,
                FeedbackType,
                PreferenceCategory,
                PreferenceLearner,
            )

            context = get_context()
            preferences = self._load_preferences(context)

            learner = PreferenceLearner(preferences=preferences)
            loop = FeedbackLoop(learner)

            ft = FeedbackType(feedback_type)
            pc = PreferenceCategory(preference_category)

            feedback = loop.collect_feedback(
                feedback_type=ft,
                content=content,
                suggestion_id=suggestion_id,
                preference_category=pc,
            )

            new_preferences = loop.process_feedback(feedback)

            self._save_preferences(context, new_preferences)

            return {
                "success": True,
                "data": {
                    "feedback_id": feedback.id,
                    "feedback_type": feedback.feedback_type.value,
                    "preference_updated": True,
                    "current_preferences": new_preferences.to_dict(),
                },
            }
        except Exception as e:
            logger.error(f"记录反馈失败: {e}")
            return {"success": False, "error": str(e)}

    def get_user_preferences(self) -> dict[str, Any]:
        """获取用户偏好 - v0.14.0新增

        Returns:
            dict: 用户偏好
        """
        try:
            from src.core.base.context import get_context

            context = get_context()
            preferences = self._load_preferences(context)

            return {
                "success": True,
                "data": preferences.to_dict(),
            }
        except Exception as e:
            logger.error(f"获取用户偏好失败: {e}")
            return {"success": False, "error": str(e)}

    def update_user_preferences(self, updates: dict[str, str]) -> dict[str, Any]:
        """更新用户偏好 - v0.14.0新增

        Args:
            updates: 偏好更新键值对

        Returns:
            dict: 更新结果
        """
        try:
            from src.core.base.context import get_context
            from src.core.personality import PreferenceLearner

            context = get_context()
            preferences = self._load_preferences(context)

            learner = PreferenceLearner(preferences=preferences)
            new_preferences = learner.update_preference_model(updates)

            self._save_preferences(context, new_preferences)

            return {
                "success": True,
                "data": {
                    "updated_preferences": new_preferences.to_dict(),
                },
            }
        except Exception as e:
            logger.error(f"更新用户偏好失败: {e}")
            return {"success": False, "error": str(e)}

    def _load_preferences(self, context: Any) -> UserPreferences:
        """从存储加载用户偏好

        Args:
            context: 应用上下文

        Returns:
            UserPreferences: 用户偏好
        """
        from src.core.personality import UserPreferences

        try:
            profile = self.profile_storage.load_profile_json()
            if profile is not None:
                profile_dict = profile.to_dict() if hasattr(profile, "to_dict") else {}
                pref_data = profile_dict.get("preferences", {})
                if pref_data:
                    return UserPreferences.from_dict(pref_data)
        except Exception:
            pass

        return UserPreferences.default()

    def _save_preferences(self, context: Any, preferences: UserPreferences) -> None:
        """保存用户偏好到存储

        Args:
            context: 应用上下文
            preferences: 用户偏好
        """
        try:
            profile = self.profile_storage.load_profile_json()
            if profile is not None and hasattr(profile, "to_dict"):
                profile_dict = profile.to_dict()
            else:
                profile_dict = {}

            profile_dict["preferences"] = preferences.to_dict()

            # 将 dict 转换回 RunnerProfile 对象以满足类型要求
            if hasattr(self.profile_storage, "save_profile_json") and hasattr(
                self.profile_storage, "_dict_to_profile"
            ):
                profile_obj = self.profile_storage._dict_to_profile(profile_dict)
                self.profile_storage.save_profile_json(profile_obj)
        except Exception as e:
            logger.warning(f"保存偏好到存储失败: {e}")

    def explain_decision(
        self,
        decision_id: str | None = None,
        detail_level: str = "brief",
    ) -> dict[str, Any]:
        """解释AI决策过程 - v0.15.0新增

        Args:
            decision_id: 决策ID（可选）
            detail_level: 详细程度（brief/detailed）

        Returns:
            dict: 决策解释
        """
        try:
            from src.core.transparency import DetailLevel

            engine = self._get_transparency_engine()
            if engine is None:
                return {
                    "success": False,
                    "error": "透明化引擎未初始化",
                }

            if decision_id is not None:
                decision = engine.get_decision(decision_id)
                if decision is None:
                    return {
                        "success": False,
                        "error": f"决策不存在: {decision_id}",
                    }
            else:
                return {
                    "success": False,
                    "error": "无可用决策记录，请提供decision_id",
                }

            level = (
                DetailLevel.DETAILED
                if detail_level == "detailed"
                else DetailLevel.BRIEF
            )
            explanation = engine.generate_explanation(decision, level)

            return {
                "success": True,
                "data": {
                    "decision_id": explanation.decision_id,
                    "brief_reasons": explanation.brief_reasons,
                    "confidence": explanation.confidence_score,
                    "data_sources": [
                        {
                            "name": ds.name,
                            "type": ds.type.value,
                            "description": ds.description,
                            "quality_score": ds.quality_score,
                        }
                        for ds in explanation.data_sources
                    ],
                    "decision_path": {
                        "steps": [
                            {
                                "name": step.name,
                                "description": step.description,
                                "type": step.step_type,
                            }
                            for step in explanation.decision_path.steps
                        ],
                        "total_duration_ms": explanation.decision_path.total_duration_ms,
                    },
                    "detailed_analysis": explanation.detailed_analysis,
                },
            }
        except Exception as e:
            logger.error(f"解释决策失败: {e}")
            return {"success": False, "error": str(e)}

    def trace_data_sources(
        self,
        decision_id: str | None = None,
    ) -> dict[str, Any]:
        """追溯数据来源 - v0.15.0新增

        Args:
            decision_id: 决策ID（可选）

        Returns:
            dict: 数据来源信息
        """
        try:
            engine = self._get_transparency_engine()
            if engine is None:
                return {
                    "success": False,
                    "error": "透明化引擎未初始化",
                }

            if decision_id is not None:
                sources = engine.trace_data_sources(decision_id)
                if not sources:
                    return {
                        "success": False,
                        "error": f"决策不存在: {decision_id}",
                    }
            else:
                return {
                    "success": False,
                    "error": "无可用决策记录，请提供decision_id",
                }

            return {
                "success": True,
                "data": {
                    "decision_id": decision_id,
                    "sources": [
                        {
                            "name": ds.name,
                            "type": ds.type.value,
                            "description": ds.description,
                            "quality_score": ds.quality_score,
                        }
                        for ds in sources
                    ],
                },
            }
        except Exception as e:
            logger.error(f"追溯数据来源失败: {e}")
            return {"success": False, "error": str(e)}

    def get_transparency_insight(
        self,
        include_metrics: bool = True,
        include_recent_decisions: bool = True,
        recent_limit: int = 5,
    ) -> dict[str, Any]:
        """获取透明化洞察 - v0.15.0新增

        Args:
            include_metrics: 是否包含可观测性指标
            include_recent_decisions: 是否包含最近决策
            recent_limit: 最近决策返回数量

        Returns:
            dict: 透明化洞察信息
        """
        try:
            result: dict[str, Any] = {"success": True, "data": {}}

            if include_metrics:
                manager = self._get_observability_manager()
                if manager is not None:
                    metrics = manager.get_metrics()
                    result["data"]["metrics"] = metrics.to_dict()

            if include_recent_decisions:
                trace_logger = self._get_trace_logger()
                if trace_logger is not None:
                    recent = trace_logger.get_decision_logs(recent_limit)
                    result["data"]["recent_decisions"] = [
                        {
                            "timestamp": str(e.timestamp),
                            "message": e.message,
                            "level": e.level,
                            "context": e.context,
                        }
                        for e in recent
                    ]
                    result["data"]["log_stats"] = trace_logger.get_stats()

            return result
        except Exception as e:
            logger.error(f"获取透明化洞察失败: {e}")
            return {"success": False, "error": str(e)}

    def _get_transparency_engine(self) -> Any:
        """获取透明化引擎实例"""
        if not hasattr(self, "_transparency_engine"):
            from src.core.transparency import TransparencyEngine

            self._transparency_engine: Any = TransparencyEngine()
        return self._transparency_engine

    def _get_observability_manager(self) -> Any:
        """获取可观测性管理器实例"""
        if not hasattr(self, "_observability_manager"):
            from src.core.transparency import ObservabilityManager

            self._observability_manager: Any = ObservabilityManager()
        return self._observability_manager

    def _get_trace_logger(self) -> Any:
        """获取追踪日志记录器实例"""
        if not hasattr(self, "_trace_logger"):
            from src.core.transparency import TraceLogger

            self._trace_logger: Any = TraceLogger()
        return self._trace_logger

    def spawn_subagent(
        self,
        subagent_type: str,
        user_request: str,
        date_range: str = "",
        report_type: str = "",
    ) -> dict[str, Any]:
        """调用Subagent执行专项任务

        实现"主Agent预查询 + 数据上下文传入"模式：
        1. 根据subagent_type预查询相关数据
        2. 将数据序列化并嵌入task参数
        3. 调用SpawnTool执行Subagent
        4. 返回Subagent执行结果或降级处理结果

        Args:
            subagent_type: Subagent类型 (data_analyst/report_writer)
            user_request: 用户原始请求
            date_range: 日期范围（可选，格式：YYYY-MM-DD ~ YYYY-MM-DD）
            report_type: 报告类型（可选，仅report_writer使用）

        Returns:
            dict: 包含success/data或error/fallback_result的字典
        """
        try:
            # 1. 预查询数据
            context_data = self._prepare_subagent_context(
                subagent_type=subagent_type,
                user_request=user_request,
                date_range=date_range,
                report_type=report_type,
            )

            # 2. 组装task参数（数据上下文格式）
            task = self._build_subagent_task(
                user_request=user_request,
                context_data=context_data,
            )

            # 3. 检查数据上下文大小
            context_size = len(task)
            if context_size > SpawnSubagentTool.MAX_CONTEXT_LENGTH:
                logger.warning(
                    f"Subagent数据上下文过大({context_size}字符)，进行截断处理"
                )
                task = self._truncate_context(task)
                context_size = len(task)

            # 4. 调用Subagent（通过SpawnTool）
            # 注意：SpawnTool由nanobot-ai底座自动注册，这里构建调用参数
            subagent_result = self._invoke_subagent(
                subagent_type=subagent_type,
                task=task,
            )

            return {
                "success": True,
                "data": {
                    "subagent_type": subagent_type,
                    "result": subagent_result,
                    "context_size": context_size,
                    "task_preview": task[:200] + "..." if len(task) > 200 else task,
                },
            }

        except Exception as e:
            logger.error(f"Subagent调用失败: {e}", exc_info=True)
            # 降级处理：返回预查询数据，让主Agent直接处理
            fallback_result = self._prepare_fallback_response(
                subagent_type=subagent_type,
                user_request=user_request,
                date_range=date_range,
                report_type=report_type,
            )
            return {
                "success": False,
                "error": f"Subagent调用失败: {str(e)}",
                "fallback_result": fallback_result,
            }

    def _prepare_subagent_context(
        self,
        subagent_type: str,
        user_request: str,
        date_range: str = "",
        report_type: str = "",
    ) -> dict[str, Any]:
        """预查询Subagent所需数据

        根据Subagent类型预查询相关数据：
        - data_analyst: VDOT趋势、训练负荷、心率漂移、最近跑步记录
        - report_writer: 跑步统计、日期范围查询、VDOT趋势

        Args:
            subagent_type: Subagent类型
            user_request: 用户请求
            date_range: 日期范围
            report_type: 报告类型

        Returns:
            dict: 预查询数据字典
        """
        context: dict[str, Any] = {}

        try:
            if subagent_type == "data_analyst":
                # 数据分析Subagent：预查询VDOT趋势、训练负荷、心率漂移
                context["vdot_trend"] = self.get_vdot_trend(limit=20)
                context["training_load"] = self.get_training_load(days=42)
                context["hr_drift"] = self.get_hr_drift_analysis()
                context["recent_runs"] = self.get_recent_runs(limit=10)
                context["user_request"] = user_request

            elif subagent_type == "report_writer":
                # 报告撰写Subagent：预查询跑步统计、日期范围数据
                if date_range:
                    # 解析日期范围
                    dates = date_range.split(" ~ ")
                    if len(dates) == 2:
                        context["runs_in_range"] = self.query_by_date_range(
                            dates[0], dates[1]
                        )
                    else:
                        context["recent_runs"] = self.get_recent_runs(limit=30)
                else:
                    context["recent_runs"] = self.get_recent_runs(limit=30)

                context["running_stats"] = self.get_running_stats()
                context["vdot_trend"] = self.get_vdot_trend(limit=20)
                context["training_load"] = self.get_training_load(days=42)
                context["report_type"] = report_type or "summary"
                context["user_request"] = user_request

            else:
                logger.warning(f"未知的Subagent类型: {subagent_type}")
                context["user_request"] = user_request
                context["error"] = f"不支持的Subagent类型: {subagent_type}"

        except Exception as e:
            logger.error(f"预查询Subagent数据失败: {e}")
            context["user_request"] = user_request
            context["error"] = f"数据预查询失败: {str(e)}"

        return context

    def _build_subagent_task(
        self,
        user_request: str,
        context_data: dict[str, Any],
    ) -> str:
        """组装Subagent的task参数

        数据上下文格式:
        {user_request}\n---数据上下文---\n{serialized_data}\n---数据上下文结束---

        Args:
            user_request: 用户请求
            context_data: 预查询数据

        Returns:
            str: 组装后的task参数字符串
        """
        # 序列化数据上下文
        serialized_data = json.dumps(
            context_data,
            ensure_ascii=False,
            default=str,
            indent=2,
        )

        # 组装task参数
        task = (
            f"{user_request}"
            f"{SpawnSubagentTool.CONTEXT_SEPARATOR}"
            f"{serialized_data}"
            f"{SpawnSubagentTool.CONTEXT_END}"
        )

        return task

    def _truncate_context(self, task: str) -> str:
        """截断数据上下文至最大长度

        当数据上下文超过MAX_CONTEXT_LENGTH时，保留用户请求部分，
        截断数据上下文部分。

        Args:
            task: 原始task参数

        Returns:
            str: 截断后的task参数
        """
        # 分离用户请求和数据上下文
        parts = task.split(SpawnSubagentTool.CONTEXT_SEPARATOR)
        if len(parts) != 2:
            # 格式异常，直接截断
            return task[: SpawnSubagentTool.MAX_CONTEXT_LENGTH - 3] + "..."

        user_request = parts[0]
        data_context = parts[1]

        # 计算固定开销（分隔符 + 结束标记 + "..."）
        fixed_overhead = (
            len(SpawnSubagentTool.CONTEXT_SEPARATOR)
            + len(SpawnSubagentTool.CONTEXT_END)
            + 3  # "..."长度
        )

        # 计算可用空间
        available_space = (
            SpawnSubagentTool.MAX_CONTEXT_LENGTH - len(user_request) - fixed_overhead
        )

        if available_space <= 0:
            # 用户请求本身已超限，截断用户请求
            # 计算错误消息长度
            error_msg = '{"error": "数据上下文被截断，仅保留用户请求"}'
            max_request_len = (
                SpawnSubagentTool.MAX_CONTEXT_LENGTH - fixed_overhead - len(error_msg)
            )
            return (
                f"{user_request[:max_request_len]}..."
                f"{SpawnSubagentTool.CONTEXT_SEPARATOR}"
                f"{error_msg}"
                f"{SpawnSubagentTool.CONTEXT_END}"
            )

        # 截断数据上下文
        truncated_data = data_context[:available_space] + "..."

        return (
            f"{user_request}"
            f"{SpawnSubagentTool.CONTEXT_SEPARATOR}"
            f"{truncated_data}"
            f"{SpawnSubagentTool.CONTEXT_END}"
        )

    def _invoke_subagent(
        self,
        subagent_type: str,
        task: str,
    ) -> dict[str, Any]:
        """调用Subagent执行

        通过nanobot-ai底座的SpawnTool调用Subagent。
        由于SpawnTool由AgentLoop自动管理，这里构建调用规范并返回预期结果格式。

        Args:
            subagent_type: Subagent类型
            task: 任务描述（包含数据上下文）

        Returns:
            dict: Subagent执行结果
        """
        # 验证Subagent类型
        valid_types = ["data_analyst", "report_writer"]
        if subagent_type not in valid_types:
            return {
                "subagent_type": subagent_type,
                "task": task,
                "label": subagent_type,
                "status": "error",
                "error": f"不支持的Subagent类型: {subagent_type}，支持的类型: {', '.join(valid_types)}",
                "note": (
                    f"Subagent类型 '{subagent_type}' 无效。"
                    f"请使用以下类型之一: {', '.join(valid_types)}"
                ),
            }

        # 构建Subagent调用规范
        # 注意：实际调用由AgentLoop的SpawnTool处理，这里返回调用参数供Agent使用
        return {
            "subagent_type": subagent_type,
            "task": task,
            "label": subagent_type,
            "status": "ready_to_spawn",
            "note": (
                "Subagent调用参数已准备就绪。"
                "实际调用由AgentLoop通过SpawnTool执行，"
                "结果将通过MessageBus注入主Agent会话。"
            ),
        }

    def _prepare_fallback_response(
        self,
        subagent_type: str,
        user_request: str,
        date_range: str = "",
        report_type: str = "",
    ) -> dict[str, Any]:
        """准备降级响应

        当Subagent调用失败时，返回预查询数据让主Agent直接处理。

        Args:
            subagent_type: Subagent类型
            user_request: 用户请求
            date_range: 日期范围
            report_type: 报告类型

        Returns:
            dict: 降级响应数据
        """
        try:
            fallback_data = self._prepare_subagent_context(
                subagent_type=subagent_type,
                user_request=user_request,
                date_range=date_range,
                report_type=report_type,
            )
            return {
                "type": "fallback",
                "subagent_type": subagent_type,
                "data": fallback_data,
                "message": "Subagent调用失败，已返回预查询数据供主Agent处理",
            }
        except Exception as e:
            logger.error(f"降级响应准备失败: {e}")
            return {
                "type": "fallback",
                "subagent_type": subagent_type,
                "error": f"无法准备降级数据: {str(e)}",
                "message": "Subagent调用失败且无法获取预查询数据",
            }

    def ask_user_confirm(
        self,
        scenario: str,
        prompt_id: str,
        context_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """创建异步用户确认提示 - v0.17.0新增（实验性功能）

        Agent通过此工具输出结构化选项+确认提示，用户在下一轮对话中确认。
        不支持同步阻塞模式（底座不支持）。

        支持场景：
        - training_plan: 训练计划确认
        - rpe_feedback: RPE体感评分
        - injury_risk: 伤病风险调整建议

        Args:
            scenario: 确认场景类型
            prompt_id: 提示ID（plan_id或session_id）
            context_data: 场景相关数据

        Returns:
            dict: 包含确认提示的结果
        """
        try:
            from src.core.base.context import get_context

            context = get_context()
            manager = context.ask_user_confirm_manager

            if scenario == "training_plan":
                plan_summary = context_data or {}
                prompt = manager.create_plan_confirm_prompt(prompt_id, plan_summary)
                return {
                    "success": True,
                    "prompt": prompt.to_dict(),
                    "agent_prompt": prompt.to_agent_prompt(),
                    "requires_user_response": True,
                    "note": "实验性功能：请在下轮对话中回复选项编号确认",
                }

            elif scenario == "rpe_feedback":
                session_summary = context_data or {}
                prompt = manager.create_rpe_prompt(prompt_id, session_summary)
                return {
                    "success": True,
                    "prompt": prompt.to_dict(),
                    "agent_prompt": prompt.to_agent_prompt(),
                    "requires_user_response": True,
                    "note": "实验性功能：请回复1-10分评分",
                }

            elif scenario == "injury_risk":
                risk_level = (
                    context_data.get("risk_level", "medium")
                    if context_data
                    else "medium"
                )
                suggestions = (
                    context_data.get("suggestions", []) if context_data else []
                )
                prompt = manager.create_injury_risk_prompt(
                    prompt_id, risk_level, suggestions
                )
                return {
                    "success": True,
                    "prompt": prompt.to_dict(),
                    "agent_prompt": prompt.to_agent_prompt(),
                    "requires_user_response": True,
                    "note": "实验性功能：请在下轮对话中回复选项确认",
                }

            else:
                return {
                    "success": False,
                    "error": f"不支持的确认场景: {scenario}",
                    "supported_scenarios": [
                        "training_plan",
                        "rpe_feedback",
                        "injury_risk",
                    ],
                }

        except Exception as e:
            logger.error(f"创建确认提示失败: {e}")
            return {"success": False, "error": str(e)}

    def parse_user_confirm_response(
        self,
        prompt_id: str,
        user_input: str,
    ) -> dict[str, Any]:
        """解析用户确认响应 - v0.17.0新增（实验性功能）

        解析用户对确认提示的响应，返回结构化结果。

        Args:
            prompt_id: 提示ID
            user_input: 用户输入

        Returns:
            dict: 解析结果
        """
        try:
            from src.core.base.context import get_context

            context = get_context()
            manager = context.ask_user_confirm_manager

            result = manager.parse_user_response(prompt_id, user_input)

            return {
                "success": True,
                "confirmed": result.is_confirmed,
                "status": result.status.value,
                "selected_key": result.selected_key,
                "selected_label": (
                    result.selected_option.label if result.selected_option else None
                ),
                "raw_input": result.raw_input,
                "result": result.to_dict(),
            }

        except Exception as e:
            logger.error(f"解析用户响应失败: {e}")
            return {"success": False, "error": str(e)}

    def ask_rpe_in_cli(
        self, session_summary: dict[str, Any] | None = None
    ) -> int | None:
        """在CLI中询问RPE评分 - v0.17.0新增

        Args:
            session_summary: 会话摘要

        Returns:
            int | None: RPE评分（1-10），取消返回None
        """
        try:
            from src.core.plan.ask_user_confirm import CLIConfirmHelper

            return CLIConfirmHelper.ask_rpe_in_cli(session_summary)
        except Exception as e:
            logger.error(f"CLI RPE询问失败: {e}")
            return None


class AskUserConfirmTool(BaseTool):
    """异步用户确认工具 - v0.17.0新增（实验性功能）

    实现ask_user异步确认模式。Agent通过此工具输出结构化选项+确认提示，
    用户在下一轮对话中确认。不支持同步阻塞模式。

    使用场景：
    1. 训练计划确认 - 输出结构化选项 + 确认提示
    2. RPE 反馈 - 输出 1-10 分选择提示
    3. 伤病风险调整 - 输出调整建议 + 确认提示

    使用方式：
    1. Agent调用此工具创建确认提示
    2. 将agent_prompt展示给用户
    3. 用户在下轮对话中回复选项编号
    4. Agent调用parse_user_confirm解析用户响应
    """

    @property
    def name(self) -> str:
        return "ask_user_confirm"

    @property
    def description(self) -> str:
        return (
            "异步用户确认工具（实验性功能）。当需要用户确认训练计划、RPE评分、"
            "伤病风险调整建议时使用此工具。工具会生成结构化选项，用户在下轮对话中"
            "回复选项编号确认。支持场景: training_plan(训练计划确认)/rpe_feedback(体感评分)/"
            "injury_risk(伤病风险调整)。返回JSON格式: {success: true, prompt: 提示结构, "
            "agent_prompt: 展示给用户的文本, requires_user_response: true} 或 "
            "{success: false, error: 错误信息}"
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "scenario": {
                    "type": "string",
                    "description": "确认场景: training_plan(训练计划确认) / rpe_feedback(体感评分) / injury_risk(伤病风险调整)",
                    "enum": ["training_plan", "rpe_feedback", "injury_risk"],
                },
                "prompt_id": {
                    "type": "string",
                    "description": "提示ID（plan_id或session_id）",
                },
                "context_data": {
                    "type": "object",
                    "description": "场景相关数据（可选）。training_plan需要{goal, weeks, weekly_volume_km}；rpe_feedback需要{distance_km, duration_min}；injury_risk需要{risk_level, suggestions}",
                },
            },
            "required": ["scenario", "prompt_id"],
        }

    async def execute(self, **kwargs: Any) -> str:
        scenario = kwargs.get("scenario", "")
        prompt_id = kwargs.get("prompt_id", "")
        context_data = kwargs.get("context_data")
        return self._run_sync(
            self.runner_tools.ask_user_confirm,
            scenario=scenario,
            prompt_id=prompt_id,
            context_data=context_data,
        )


class ParseUserConfirmTool(BaseTool):
    """解析用户确认响应工具 - v0.17.0新增（实验性功能）"""

    @property
    def name(self) -> str:
        return "parse_user_confirm"

    @property
    def description(self) -> str:
        return (
            "解析用户对确认提示的响应（实验性功能）。在ask_user_confirm之后使用，"
            "解析用户回复的选项编号或选项名称。返回JSON格式: "
            "{success: true, confirmed: 是否确认, status: 状态, selected_key: 选项key, "
            "selected_label: 选项标签, raw_input: 原始输入} 或 "
            "{success: false, error: 错误信息}"
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "prompt_id": {
                    "type": "string",
                    "description": "提示ID（与ask_user_confirm中的prompt_id一致）",
                },
                "user_input": {
                    "type": "string",
                    "description": "用户的回复内容",
                },
            },
            "required": ["prompt_id", "user_input"],
        }

    async def execute(self, **kwargs: Any) -> str:
        prompt_id = kwargs.get("prompt_id", "")
        user_input = kwargs.get("user_input", "")
        return self._run_sync(
            self.runner_tools.parse_user_confirm_response,
            prompt_id=prompt_id,
            user_input=user_input,
        )


class SpawnSubagentTool(BaseTool):
    """调用Subagent工具 - v0.17.0新增

    实现"主Agent预查询 + 数据上下文传入"模式：
    1. 主Agent识别子任务类型（数据分析/报告撰写）
    2. 通过RunnerTools预查询相关数据
    3. 将序列化数据嵌入task参数传入Subagent
    4. Subagent基于传入数据进行分析和报告生成

    支持的Subagent:
    - data_analyst: 数据分析专家，解释VDOT趋势、训练负荷、心率漂移等
    - report_writer: 报告撰写专家，生成周报/月报/训练总结

    数据上下文格式:
    {user_request}\n---数据上下文---\n{serialized_data}\n---数据上下文结束---

    数据上下文大小控制: task参数总长度 ≤ 8000字符
    """

    # 数据上下文最大长度限制
    MAX_CONTEXT_LENGTH: int = 8000
    # 数据上下文分隔符
    CONTEXT_SEPARATOR: str = "\n---数据上下文---\n"
    CONTEXT_END: str = "\n---数据上下文结束---"

    @property
    def name(self) -> str:
        return "spawn_subagent"

    @property
    def description(self) -> str:
        return (
            "调用Subagent执行专项任务。支持数据分析(data_analyst)和报告撰写(report_writer)两种Subagent。"
            "主Agent会自动预查询相关数据并传入Subagent。当用户需要深度数据分析、生成训练周报/月报时使用此工具。"
            "返回JSON格式: {success: true, data: {subagent_type, result, context_size}} 或 {success: false, error: 错误信息, fallback_result: 降级结果}"
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "subagent_type": {
                    "type": "string",
                    "description": "Subagent类型: data_analyst(数据分析) / report_writer(报告撰写)",
                    "enum": ["data_analyst", "report_writer"],
                },
                "user_request": {
                    "type": "string",
                    "description": "用户的原始请求描述",
                },
                "date_range": {
                    "type": "string",
                    "description": "日期范围（可选，格式：YYYY-MM-DD ~ YYYY-MM-DD）",
                },
                "report_type": {
                    "type": "string",
                    "description": "报告类型（可选，仅report_writer使用）：weekly/monthly/summary",
                    "enum": ["weekly", "monthly", "summary"],
                },
            },
            "required": ["subagent_type", "user_request"],
        }

    async def execute(self, **kwargs: Any) -> str:
        """执行Subagent调用

        Args:
            subagent_type: Subagent类型
            user_request: 用户请求
            date_range: 日期范围（可选）
            report_type: 报告类型（可选）

        Returns:
            JSON字符串，包含Subagent执行结果或降级处理结果
        """
        subagent_type = kwargs.get("subagent_type", "")
        user_request = kwargs.get("user_request", "")
        date_range = kwargs.get("date_range", "")
        report_type = kwargs.get("report_type", "")

        return self._run_sync(
            self.runner_tools.spawn_subagent,
            subagent_type=subagent_type,
            user_request=user_request,
            date_range=date_range,
            report_type=report_type,
        )


class DiagnoseSuggestionTool(BaseTool):
    """诊断AI建议质量 - v0.14.0新增"""

    @property
    def name(self) -> str:
        return "diagnose_suggestion"

    @property
    def description(self) -> str:
        return "验证AI建议质量，检查建议的完整性、相关性、安全性和可执行性。当AI需要自我检查建议质量、诊断错误原因时使用此工具。返回JSON格式：{success: true, data: {report_id, category, overall_status, pass_count, fail_count, results: [{rule_name, status, message, severity, suggestion_fix}]}} 或 {success: false, error: 错误信息}"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "user_query": {
                    "type": "string",
                    "description": "用户原始查询",
                },
                "suggestion_text": {
                    "type": "string",
                    "description": "AI生成的建议文本",
                },
                "tools_used": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "使用的工具列表（可选）",
                },
            },
            "required": ["user_query", "suggestion_text"],
        }

    async def execute(self, **kwargs: Any) -> str:
        user_query = kwargs.get("user_query", "")
        suggestion_text = kwargs.get("suggestion_text", "")
        tools_used = kwargs.get("tools_used", [])
        return self._run_sync(
            self.runner_tools.diagnose_suggestion,
            user_query,
            suggestion_text,
            tools_used,
        )


class DiagnoseErrorTool(BaseTool):
    """诊断错误原因 - v0.14.0新增"""

    @property
    def name(self) -> str:
        return "diagnose_error"

    @property
    def description(self) -> str:
        return "诊断错误原因，分析错误根因并给出修复建议。当AI遇到执行错误、工具调用失败时使用此工具进行自我诊断。返回JSON格式：{success: true, data: {report_id, category, overall_status, results: [{rule_name, status, message, severity, suggestion_fix}]}} 或 {success: false, error: 错误信息}"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "error_message": {
                    "type": "string",
                    "description": "错误信息",
                },
            },
            "required": ["error_message"],
        }

    async def execute(self, **kwargs: Any) -> str:
        error_message = kwargs.get("error_message", "")
        return self._run_sync(self.runner_tools.diagnose_error, error_message)


class GetPersonalizedSuggestionTool(BaseTool):
    """获取个性化建议 - v0.14.0新增"""

    @property
    def name(self) -> str:
        return "get_personalized_suggestion"

    @property
    def description(self) -> str:
        return "根据用户偏好对建议进行个性化调整。当AI需要根据用户偏好调整建议风格、强度、详细程度时使用此工具。返回JSON格式：{success: true, data: {id, original_text, personalized_text, suggestion_type, confidence, preference_factors}} 或 {success: false, error: 错误信息}"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "suggestion_text": {
                    "type": "string",
                    "description": "原始建议文本",
                },
                "suggestion_type": {
                    "type": "string",
                    "description": "建议类型（training_plan/recovery_advice/pace_guidance/weather_advice/nutrition_tip/injury_prevention/general，默认general）",
                },
            },
            "required": ["suggestion_text"],
        }

    async def execute(self, **kwargs: Any) -> str:
        suggestion_text = kwargs.get("suggestion_text", "")
        suggestion_type = kwargs.get("suggestion_type", "general")
        return self._run_sync(
            self.runner_tools.get_personalized_suggestion,
            suggestion_text,
            suggestion_type,
        )


class RecordFeedbackTool(BaseTool):
    """记录用户反馈 - v0.14.0新增"""

    @property
    def name(self) -> str:
        return "record_feedback"

    @property
    def description(self) -> str:
        return "记录用户对AI建议的反馈，用于偏好学习和个性化进化。当用户对建议表达满意、不满或修正意见时使用此工具。返回JSON格式：{success: true, data: {feedback_id, feedback_type, preference_updated, current_preferences}} 或 {success: false, error: 错误信息}"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "feedback_type": {
                    "type": "string",
                    "description": "反馈类型（positive/negative/neutral/correction）",
                },
                "content": {
                    "type": "string",
                    "description": "反馈内容",
                },
                "preference_category": {
                    "type": "string",
                    "description": "偏好类别（training_time/training_intensity/communication_style/suggestion_frequency/detail_preference/pace_preference/distance_preference/weather_sensitivity，默认communication_style）",
                },
                "suggestion_id": {
                    "type": "string",
                    "description": "关联的建议ID（可选）",
                },
            },
            "required": ["feedback_type", "content"],
        }

    async def execute(self, **kwargs: Any) -> str:
        feedback_type = kwargs.get("feedback_type", "neutral")
        content = kwargs.get("content", "")
        preference_category = kwargs.get("preference_category", "communication_style")
        suggestion_id = kwargs.get("suggestion_id", "")
        return self._run_sync(
            self.runner_tools.record_feedback,
            feedback_type,
            content,
            preference_category,
            suggestion_id,
        )


class GetUserPreferencesTool(BaseTool):
    """获取用户偏好 - v0.14.0新增"""

    @property
    def name(self) -> str:
        return "get_user_preferences"

    @property
    def description(self) -> str:
        return "获取当前用户的偏好设置，包括训练时段、强度偏好、沟通风格等。当AI需要了解用户偏好以提供更个性化的建议时使用此工具。返回JSON格式：{success: true, data: {training_time, training_intensity, communication_style, suggestion_frequency, detail_preference, pace_preference, distance_preference, weather_sensitivity, custom_preferences}} 或 {success: false, error: 错误信息}"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
        }

    async def execute(self, **kwargs: Any) -> str:
        return self._run_sync(self.runner_tools.get_user_preferences)


class UpdateUserPreferencesTool(BaseTool):
    """更新用户偏好 - v0.14.0新增"""

    @property
    def name(self) -> str:
        return "update_user_preferences"

    @property
    def description(self) -> str:
        return "直接更新用户偏好设置。当用户明确表达偏好变更时使用此工具，如'我喜欢简洁的回答'、'把训练强度调低'。返回JSON格式：{success: true, data: {updated_preferences}} 或 {success: false, error: 错误信息}"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "updates": {
                    "type": "object",
                    "description": "偏好更新键值对，key为偏好字段名（training_time/training_intensity/communication_style/suggestion_frequency/detail_preference/pace_preference/distance_preference/weather_sensitivity），value为新值",
                    "additionalProperties": {"type": "string"},
                },
            },
            "required": ["updates"],
        }

    async def execute(self, **kwargs: Any) -> str:
        updates = kwargs.get("updates", {})
        return self._run_sync(self.runner_tools.update_user_preferences, updates)


class ExplainDecisionTool(BaseTool):
    """解释AI决策过程 - v0.15.0新增"""

    @property
    def name(self) -> str:
        return "explain_decision"

    @property
    def description(self) -> str:
        return "解释AI决策过程，展示思考过程和决策依据。当用户询问'为什么这么建议'、'你是怎么想的'、'解释一下你的建议'时使用此工具。返回JSON格式：{success: true, data: {decision_id, brief_reasons, confidence, data_sources, decision_path}} 或 {success: false, error: 错误信息}"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "decision_id": {
                    "type": "string",
                    "description": "决策ID（可选，不提供则解释最近一次决策）",
                },
                "detail_level": {
                    "type": "string",
                    "description": "详细程度（brief/detailed，默认brief）",
                },
            },
            "required": [],
        }

    async def execute(self, **kwargs: Any) -> str:
        decision_id = kwargs.get("decision_id")
        detail_level = kwargs.get("detail_level", "brief")
        return self._run_sync(
            self.runner_tools.explain_decision, decision_id, detail_level
        )


class TraceDataSourcesTool(BaseTool):
    """追溯数据来源 - v0.15.0新增"""

    @property
    def name(self) -> str:
        return "trace_data_sources"

    @property
    def description(self) -> str:
        return "追溯AI决策使用的数据来源，展示决策基于哪些数据做出。当用户询问'你的数据来源是什么'、'这个建议基于什么数据'、'你怎么知道这些'时使用此工具。返回JSON格式：{success: true, data: {decision_id, sources: [{name, type, description, quality_score}]}} 或 {success: false, error: 错误信息}"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "decision_id": {
                    "type": "string",
                    "description": "决策ID（可选，不提供则追溯最近一次决策）",
                },
            },
            "required": [],
        }

    async def execute(self, **kwargs: Any) -> str:
        decision_id = kwargs.get("decision_id")
        return self._run_sync(self.runner_tools.trace_data_sources, decision_id)


class GetTransparencyInsightTool(BaseTool):
    """获取透明化洞察 - v0.15.0新增"""

    @property
    def name(self) -> str:
        return "get_transparency_insight"

    @property
    def description(self) -> str:
        return "获取AI透明化洞察信息，包括可观测性指标、决策统计、工具可靠性等。当用户询问'AI表现如何'、'你的决策质量怎么样'、'工具调用情况'时使用此工具。返回JSON格式：{success: true, data: {metrics: {total_traces, successful_traces, avg_duration_ms, error_rate, tool_success_rate}, recent_decisions, log_stats}} 或 {success: false, error: 错误信息}"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "include_metrics": {
                    "type": "boolean",
                    "description": "是否包含可观测性指标（默认true）",
                },
                "include_recent_decisions": {
                    "type": "boolean",
                    "description": "是否包含最近决策（默认true）",
                },
                "recent_limit": {
                    "type": "integer",
                    "description": "最近决策返回数量（默认5）",
                },
            },
            "required": [],
        }

    async def execute(self, **kwargs: Any) -> str:
        include_metrics = kwargs.get("include_metrics", True)
        include_recent_decisions = kwargs.get("include_recent_decisions", True)
        recent_limit = kwargs.get("recent_limit", 5)
        return self._run_sync(
            self.runner_tools.get_transparency_insight,
            include_metrics,
            include_recent_decisions,
            recent_limit,
        )


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
        RecordPlanExecutionTool(runner_tools),
        GetPlanExecutionStatsTool(runner_tools),
        AnalyzeTrainingResponseTool(runner_tools),
        AdjustPlanTool(runner_tools),
        GetPlanAdjustmentSuggestionsTool(runner_tools),
        EvaluateGoalAchievementTool(runner_tools),
        CreateLongTermPlanTool(runner_tools),
        GetSmartTrainingAdviceTool(runner_tools),
        GetWeatherTrainingAdviceTool(runner_tools),
        SpawnSubagentTool(runner_tools),
        AskUserConfirmTool(runner_tools),
        ParseUserConfirmTool(runner_tools),
        DiagnoseSuggestionTool(runner_tools),
        DiagnoseErrorTool(runner_tools),
        GetPersonalizedSuggestionTool(runner_tools),
        RecordFeedbackTool(runner_tools),
        GetUserPreferencesTool(runner_tools),
        UpdateUserPreferencesTool(runner_tools),
        ExplainDecisionTool(runner_tools),
        TraceDataSourcesTool(runner_tools),
        GetTransparencyInsightTool(runner_tools),
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
    "record_plan_execution": {
        "description": "记录训练计划执行反馈，包括完成度、体感评分、反馈备注等。返回JSON格式：{success: true, data: {plan_id: 计划ID, date: 日期, message: 反馈消息}} 或 {success: false, error: 错误信息}",
        "parameters": {
            "plan_id": "训练计划ID（必填）",
            "date": "日期，格式YYYY-MM-DD（必填）",
            "completion_rate": "完成度（0.0-1.0，可选）",
            "effort_score": "体感评分（1-10，可选）",
            "notes": "反馈备注（可选）",
            "actual_distance_km": "实际距离（公里，可选）",
            "actual_duration_min": "实际时长（分钟，可选）",
            "actual_avg_hr": "实际平均心率（可选）",
        },
    },
    "get_plan_execution_stats": {
        "description": "获取训练计划执行统计，包括完成率、平均体感评分、总距离等。返回JSON格式：{success: true, data: {plan_id, total_planned_days, completed_days, completion_rate, avg_effort_score, total_distance_km, total_duration_min, avg_hr, avg_hr_drift}} 或 {success: false, error: 错误信息}",
        "parameters": {
            "plan_id": "训练计划ID（必填）",
        },
    },
    "analyze_training_response": {
        "description": "分析训练响应模式，识别用户最适应和最不适应的训练类型。返回JSON格式：{success: true, data: {plan_id, stats, patterns, overall_assessment, weak_types, strong_types}} 或 {success: false, error: 错误信息}",
        "parameters": {
            "plan_id": "训练计划ID（必填）",
        },
    },
    "adjust_plan": {
        "description": "调整训练计划。支持自然语言调整指令，如'下周减量'、'把周三的间歇跑改成轻松跑'。返回JSON格式：{success: true, data: {plan_id, adjustment, validation, requires_confirmation}} 或 {success: false, error: 错误信息, violations: 违规列表}",
        "parameters": {
            "plan_id": "训练计划ID（必填）",
            "adjustment_request": "调整请求（自然语言），如'下周减量20%'、'增加间歇跑'（必填）",
            "confirmation_required": "是否需要确认后再执行调整（默认true）",
        },
    },
    "get_plan_adjustment_suggestions": {
        "description": "获取训练计划调整建议。基于训练数据和执行反馈，生成个性化调整建议。返回JSON格式：{success: true, data: {plan_id, suggestions}} 或 {success: false, error: 错误信息}",
        "parameters": {
            "plan_id": "训练计划ID（必填）",
        },
    },
    "evaluate_goal_achievement": {
        "description": "评估目标达成概率。基于当前体能、训练趋势和目标差距，预测目标达成概率和关键风险。返回JSON格式：{success: true, data: {goal_type, goal_value, current_value, achievement_probability, key_risks, improvement_suggestions, estimated_weeks_to_achieve, confidence, gap, achievement_rate}} 或 {success: false, error: 错误信息}",
        "parameters": {
            "goal_type": "目标类型（vdot/5k/10k/half_marathon/marathon，必填）",
            "goal_value": "目标值（VDOT值或秒数，必填）",
            "current_vdot": "当前VDOT值（必填）",
            "weeks_available": "可用训练周数（可选）",
        },
    },
    "create_long_term_plan": {
        "description": "创建长期训练规划。支持年度/赛季/多周期规划，自动生成基础期、提升期、巅峰期、减量期。返回JSON格式：{success: true, data: {plan_name, target_race, target_date, current_vdot, target_vdot, total_weeks, cycles, weekly_volume_range_km, key_milestones}} 或 {success: false, error: 错误信息}",
        "parameters": {
            "plan_name": "计划名称（必填）",
            "current_vdot": "当前VDOT值（必填）",
            "target_vdot": "目标VDOT值（可选）",
            "target_race": "目标赛事名称（可选）",
            "target_date": "目标日期（YYYY-MM-DD，可选）",
            "total_weeks": "总训练周数（默认16）",
            "fitness_level": "体能水平（beginner/intermediate/advanced/elite，默认intermediate）",
        },
    },
    "get_smart_training_advice": {
        "description": "获取智能训练建议。基于训练数据和体能状态，生成训练、恢复、营养、伤病预防等多维度建议。返回JSON格式：{success: true, data: {advices: [{advice_type, content, priority, context, confidence, related_metrics}], total_count}} 或 {success: false, error: 错误信息}",
        "parameters": {
            "current_vdot": "当前VDOT值（可选）",
            "weekly_volume_km": "周跑量（公里，可选）",
            "training_consistency": "训练一致性（0-1，可选）",
            "injury_risk": "伤病风险（low/medium/high，可选）",
            "goal_type": "目标类型（5k/10k/half_marathon/marathon，可选）",
        },
    },
    "get_weather_training_advice": {
        "description": "获取天气+训练综合建议。结合天气数据和训练数据，生成多维度的训练建议。当用户询问'今天适合跑步吗'、'天气对训练的影响'、'综合训练建议'时使用此工具。返回JSON格式：{success: true, data: {advices: [{advice_type, content, priority, reason, weather_impact, training_impact}], total_count, weather_impact, formatted_advice}} 或 {success: false, error: 错误信息}",
        "parameters": {
            "temperature": "温度（摄氏度，必填）",
            "humidity": "湿度（百分比，0-100，必填）",
            "weather": "天气状况（晴/阴/雨/雪等，必填）",
            "wind": "风力描述（可选）",
            "precipitation": "降水概率（百分比，0-100，可选）",
            "uv_index": "紫外线指数（可选）",
        },
    },
    "spawn_subagent": {
        "description": "调用Subagent执行专项任务。支持数据分析(data_analyst)和报告撰写(report_writer)两种Subagent。主Agent会自动预查询相关数据并传入Subagent。当用户需要深度数据分析、生成训练周报/月报时使用此工具。返回JSON格式: {success: true, data: {subagent_type, result, context_size}} 或 {success: false, error: 错误信息, fallback_result: 降级结果}",
        "parameters": {
            "subagent_type": "Subagent类型: data_analyst(数据分析) / report_writer(报告撰写)",
            "user_request": "用户的原始请求描述",
            "date_range": "日期范围（可选，格式：YYYY-MM-DD ~ YYYY-MM-DD）",
            "report_type": "报告类型（可选，仅report_writer使用）：weekly/monthly/summary",
        },
    },
    "ask_user_confirm": {
        "description": "异步用户确认工具（实验性功能）。当需要用户确认训练计划、RPE评分、伤病风险调整建议时使用此工具。工具会生成结构化选项，用户在下轮对话中回复选项编号确认。返回JSON格式: {success: true, prompt: 提示结构, agent_prompt: 展示给用户的文本, requires_user_response: true} 或 {success: false, error: 错误信息}",
        "parameters": {
            "scenario": "确认场景: training_plan(训练计划确认) / rpe_feedback(体感评分) / injury_risk(伤病风险调整)",
            "prompt_id": "提示ID（plan_id或session_id）",
            "context_data": "场景相关数据（可选）。training_plan需要{goal, weeks, weekly_volume_km}；rpe_feedback需要{distance_km, duration_min}；injury_risk需要{risk_level, suggestions}",
        },
    },
    "parse_user_confirm": {
        "description": "解析用户对确认提示的响应（实验性功能）。在ask_user_confirm之后使用，解析用户回复的选项编号或选项名称。返回JSON格式: {success: true, confirmed: 是否确认, status: 状态, selected_key: 选项key, selected_label: 选项标签, raw_input: 原始输入} 或 {success: false, error: 错误信息}",
        "parameters": {
            "prompt_id": "提示ID（与ask_user_confirm中的prompt_id一致）",
            "user_input": "用户的回复内容",
        },
    },
    "diagnose_suggestion": {
        "description": "验证AI建议质量，检查建议的完整性、相关性、安全性和可执行性。当AI需要自我检查建议质量时使用此工具。返回JSON格式：{success: true, data: {id, category, overall_status, pass_count, fail_count, results}} 或 {success: false, error: 错误信息}",
        "parameters": {
            "user_query": "用户原始查询（必填）",
            "suggestion_text": "AI生成的建议文本（必填）",
            "tools_used": "使用的工具列表（可选）",
        },
    },
    "diagnose_error": {
        "description": "诊断错误原因，分析错误根因并给出修复建议。当AI遇到执行错误、工具调用失败时使用此工具进行自我诊断。返回JSON格式：{success: true, data: {id, category, overall_status, results}} 或 {success: false, error: 错误信息}",
        "parameters": {
            "error_message": "错误信息（必填）",
        },
    },
    "get_personalized_suggestion": {
        "description": "根据用户偏好对建议进行个性化调整。当AI需要根据用户偏好调整建议风格、强度、详细程度时使用此工具。返回JSON格式：{success: true, data: {id, original_text, personalized_text, suggestion_type, confidence, preference_factors}} 或 {success: false, error: 错误信息}",
        "parameters": {
            "suggestion_text": "原始建议文本（必填）",
            "suggestion_type": "建议类型（training_plan/recovery_advice/pace_guidance/weather_advice/nutrition_tip/injury_prevention/general，默认general）",
        },
    },
    "record_feedback": {
        "description": "记录用户对AI建议的反馈，用于偏好学习和个性化进化。当用户对建议表达满意、不满或修正意见时使用此工具。返回JSON格式：{success: true, data: {feedback_id, feedback_type, preference_updated, current_preferences}} 或 {success: false, error: 错误信息}",
        "parameters": {
            "feedback_type": "反馈类型（positive/negative/neutral/correction，必填）",
            "content": "反馈内容（必填）",
            "preference_category": "偏好类别（training_time/training_intensity/communication_style/suggestion_frequency/detail_preference/pace_preference/distance_preference/weather_sensitivity，默认communication_style）",
            "suggestion_id": "关联的建议ID（可选）",
        },
    },
    "get_user_preferences": {
        "description": "获取当前用户的偏好设置，包括训练时段、强度偏好、沟通风格等。当AI需要了解用户偏好以提供更个性化的建议时使用此工具。返回JSON格式：{success: true, data: {training_time, training_intensity, communication_style, suggestion_frequency, detail_preference, pace_preference, distance_preference, weather_sensitivity}} 或 {success: false, error: 错误信息}",
        "parameters": {},
    },
    "update_user_preferences": {
        "description": "直接更新用户偏好设置。当用户明确表达偏好变更时使用此工具，如'我喜欢简洁的回答'、'把训练强度调低'。返回JSON格式：{success: true, data: {updated_preferences}} 或 {success: false, error: 错误信息}",
        "parameters": {
            "updates": "偏好更新键值对，key为偏好字段名，value为新值（必填）",
        },
    },
    "explain_decision": {
        "description": "解释AI决策过程，展示思考过程和决策依据。当用户询问'为什么这么建议'、'你是怎么想的'、'解释一下你的建议'时使用此工具。返回JSON格式：{success: true, data: {decision_id, brief_reasons, confidence, data_sources, decision_path}} 或 {success: false, error: 错误信息}",
        "parameters": {
            "decision_id": "决策ID（可选，不提供则解释最近一次决策）",
            "detail_level": "详细程度（brief/detailed，默认brief）",
        },
    },
    "trace_data_sources": {
        "description": "追溯AI决策使用的数据来源，展示决策基于哪些数据做出。当用户询问'你的数据来源是什么'、'这个建议基于什么数据'、'你怎么知道这些'时使用此工具。返回JSON格式：{success: true, data: {decision_id, sources: [{name, type, description, quality_score}]}} 或 {success: false, error: 错误信息}",
        "parameters": {
            "decision_id": "决策ID（可选，不提供则追溯最近一次决策）",
        },
    },
    "get_transparency_insight": {
        "description": "获取AI透明化洞察信息，包括可观测性指标、决策统计、工具可靠性等。当用户询问'AI表现如何'、'你的决策质量怎么样'、'工具调用情况'时使用此工具。返回JSON格式：{success: true, data: {metrics: {total_traces, successful_traces, avg_duration_ms, error_rate, tool_success_rate}, recent_decisions, log_stats}} 或 {success: false, error: 错误信息}",
        "parameters": {
            "include_metrics": "是否包含可观测性指标（默认true）",
            "include_recent_decisions": "是否包含最近决策（默认true）",
            "recent_limit": "最近决策返回数量（默认5）",
        },
    },
}
