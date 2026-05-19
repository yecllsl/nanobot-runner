# 身体信号/健康工具类
# 包含HRV、心率恢复、疲劳度、恢复状态、身体信号摘要、周期对比、用户确认等工具

from __future__ import annotations

from typing import Any

from src.agents.tools import BaseTool


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


class GetHrvAnalysisTool(BaseTool):
    """获取HRV分析工具 - v0.19.0新增"""

    @property
    def name(self) -> str:
        return "get_hrv_analysis"

    @property
    def description(self) -> str:
        return "获取HRV（心率变异）分析结果，包括静息心率趋势和估算的HRV指标（RMSSD/SDNN）。当用户询问'HRV是多少'、'心率变异分析'、'静息心率趋势'时使用此工具。"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "分析天数（默认30天）",
                    "default": 30,
                }
            },
        }

    async def execute(self, **kwargs: Any) -> str:
        days = kwargs.get("days", 30)
        return self._run_sync(self.runner_tools.get_hrv_analysis, days)


class GetHrRecoveryTool(BaseTool):
    """获取心率恢复分析工具 - v0.19.0新增"""

    @property
    def name(self) -> str:
        return "get_hr_recovery"

    @property
    def description(self) -> str:
        return "获取心率恢复分析结果，评估训练后心率下降速率和心脏恢复能力。当用户询问'心率恢复'、'恢复能力'时使用此工具。"

    @property
    def parameters(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}}

    async def execute(self, **kwargs: Any) -> str:
        return self._run_sync(self.runner_tools.get_hr_recovery)


class GetFatigueScoreTool(BaseTool):
    """获取疲劳度评估工具 - v0.19.0新增"""

    @property
    def name(self) -> str:
        return "get_fatigue_score"

    @property
    def description(self) -> str:
        return "获取疲劳度评估结果，综合训练负荷、心率偏差、连续训练天数等维度计算疲劳度分数。当用户询问'我累不累'、'疲劳度'、'身体状态'时使用此工具。"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "rpe": {
                    "type": "integer",
                    "description": "主观疲劳度 (1-10)，可选",
                }
            },
        }

    async def execute(self, **kwargs: Any) -> str:
        rpe = kwargs.get("rpe")
        return self._run_sync(self.runner_tools.get_fatigue_score, rpe)


class GetRecoveryStatusTool(BaseTool):
    """获取恢复状态工具 - v0.19.0新增"""

    @property
    def name(self) -> str:
        return "get_recovery_status"

    @property
    def description(self) -> str:
        return "获取恢复状态评估，包括TSB变化、休息日效果和恢复趋势。当用户询问'恢复得怎么样'、'今天能训练吗'时使用此工具。"

    @property
    def parameters(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}}

    async def execute(self, **kwargs: Any) -> str:
        return self._run_sync(self.runner_tools.get_recovery_status)


class GetBodySignalSummaryTool(BaseTool):
    """获取身体信号综合摘要工具 - v0.19.0新增"""

    @property
    def name(self) -> str:
        return "get_body_signal_summary"

    @property
    def description(self) -> str:
        return "获取身体信号综合摘要，整合HRV、疲劳度和恢复状态三个维度生成每日或每周摘要。当用户询问'今天状态怎么样'、'身体信号'、'综合状态'时使用此工具。"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "description": "周期类型（daily/weekly，默认daily）",
                    "enum": ["daily", "weekly"],
                    "default": "daily",
                }
            },
        }

    async def execute(self, **kwargs: Any) -> str:
        period = kwargs.get("period", "daily")
        return self._run_sync(self.runner_tools.get_body_signal_summary, period)


class CompareTrainingPeriodsTool(BaseTool):
    """对比训练周期工具 - v0.19.0新增"""

    @property
    def name(self) -> str:
        return "compare_training_periods"

    @property
    def description(self) -> str:
        return "对比两个训练周期的身体信号变化，分析恢复状态趋势。当用户询问'最近状态有没有变好'、'对比上周'、'训练趋势'时使用此工具。"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "period1_days": {
                    "type": "integer",
                    "description": "近期周期天数（默认7天）",
                    "default": 7,
                },
                "period2_days": {
                    "type": "integer",
                    "description": "对比周期天数（默认7天）",
                    "default": 7,
                },
            },
        }

    async def execute(self, **kwargs: Any) -> str:
        period1_days = kwargs.get("period1_days", 7)
        period2_days = kwargs.get("period2_days", 7)
        return self._run_sync(
            self.runner_tools.compare_training_periods, period1_days, period2_days
        )
