# 训练计划工具类
# 包含训练计划生成、执行、调整、目标评估、长期规划、智能建议、天气建议等工具

from __future__ import annotations

from typing import Any

from src.agents.tools import BaseTool


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
