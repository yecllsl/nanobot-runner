# 数字孪生/预测工具类
# 包含数字孪生快照、推演、对比、VDOT预测、比赛预测、伤病预测、训练响应预测、
# 预测状态检查、伤病报告、模型管理、Subagent调用等工具

from __future__ import annotations

from typing import Any

from src.agents.tools import BaseTool


class PredictVdotTrendTool(BaseTool):
    """VDOT趋势预测工具 - v0.20.0新增"""

    @property
    def name(self) -> str:
        return "predict_vdot_trend"

    @property
    def description(self) -> str:
        return "预测VDOT（跑力值）趋势，基于训练数据预测未来VDOT变化。当用户询问'VDOT会怎么变'、'跑力趋势预测'、'未来VDOT'时使用此工具。"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "预测天数（默认30天）",
                    "default": 30,
                }
            },
        }

    async def execute(self, **kwargs: Any) -> str:
        days = kwargs.get("days", 30)
        return self._run_sync(self.runner_tools.predict_vdot_trend, days)


class PredictRaceResultTool(BaseTool):
    """比赛成绩预测工具 - v0.20.0新增"""

    @property
    def name(self) -> str:
        return "predict_race_result"

    @property
    def description(self) -> str:
        return "预测比赛完赛时间，基于个人化Riegel公式预测不同距离的比赛成绩。当用户询问'全马能跑多少'、'比赛预测'、'完赛时间预测'时使用此工具。"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "distance_km": {
                    "type": "number",
                    "description": "比赛距离（公里），如5/10/21.0975/42.195",
                },
                "race_date": {
                    "type": "string",
                    "description": "比赛日期（YYYY-MM-DD，可选）",
                },
            },
            "required": ["distance_km"],
        }

    async def execute(self, **kwargs: Any) -> str:
        distance_km = kwargs.get("distance_km", 42.195)
        race_date = kwargs.get("race_date")
        return self._run_sync(
            self.runner_tools.predict_race_result, distance_km, race_date
        )


class PredictInjuryRiskTool(BaseTool):
    """伤病风险预测工具 - v0.20.0新增"""

    @property
    def name(self) -> str:
        return "predict_injury_risk"

    @property
    def description(self) -> str:
        return "预测伤病风险，综合急性/慢性负荷比、训练单调性、身体信号等评估受伤概率。当用户询问'会不会受伤'、'伤病风险'、'训练安全吗'时使用此工具。"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "预测天数（默认21天）",
                    "default": 21,
                }
            },
        }

    async def execute(self, **kwargs: Any) -> str:
        days = kwargs.get("days", 21)
        return self._run_sync(self.runner_tools.predict_injury_risk, days)


class PredictTrainingResponseTool(BaseTool):
    """训练响应预测工具 - v0.20.0新增"""

    @property
    def name(self) -> str:
        return "predict_training_response"

    @property
    def description(self) -> str:
        return "预测单次训练的响应效果，包括VDOT影响、疲劳影响、恢复时间和伤病风险增量。当用户询问'这次训练效果如何'、'跑完会怎样'、'训练影响预测'时使用此工具。"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "session_type": {
                    "type": "string",
                    "description": "训练类型（easy/threshold/interval/recovery）",
                    "enum": ["easy", "threshold", "interval", "recovery"],
                },
                "duration_min": {
                    "type": "integer",
                    "description": "训练时长（分钟）",
                },
                "intensity": {
                    "type": "string",
                    "description": "强度（low/moderate/high）",
                    "enum": ["low", "moderate", "high"],
                },
            },
            "required": ["session_type", "duration_min", "intensity"],
        }

    async def execute(self, **kwargs: Any) -> str:
        session_type = kwargs.get("session_type", "easy")
        duration_min = kwargs.get("duration_min", 60)
        intensity = kwargs.get("intensity", "moderate")
        return self._run_sync(
            self.runner_tools.predict_training_response,
            session_type,
            duration_min,
            intensity,
        )


class CheckPredictionStatusTool(BaseTool):
    """预测数据充足度评估工具 - v0.20.0新增"""

    @property
    def name(self) -> str:
        return "check_prediction_status"

    @property
    def description(self) -> str:
        return "检查预测功能的数据充足度，评估各预测类型是否具备足够数据支撑ML增强预测。当用户询问'预测准不准'、'数据够不够预测'时使用此工具。"

    @property
    def parameters(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}}

    async def execute(self, **kwargs: Any) -> str:
        return self._run_sync(self.runner_tools.check_prediction_status)


class ReportInjuryTool(BaseTool):
    """伤病报告提交工具 - v0.20.1新增"""

    @property
    def name(self) -> str:
        return "report_injury"

    @property
    def description(self) -> str:
        return "提交伤病报告，记录伤病类型、严重程度和日期，用于ML模型训练标签。当用户报告受伤、疼痛、不适时使用此工具。"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "injury_type": {
                    "type": "string",
                    "description": "伤病类型（overuse/acute/chronic/other）",
                    "enum": ["overuse", "acute", "chronic", "other"],
                },
                "severity": {
                    "type": "string",
                    "description": "严重程度（mild/moderate/severe）",
                    "enum": ["mild", "moderate", "severe"],
                },
                "date": {
                    "type": "string",
                    "description": "伤病日期（YYYY-MM-DD）",
                },
            },
            "required": ["injury_type", "severity", "date"],
        }

    async def execute(self, **kwargs: Any) -> str:
        injury_type = kwargs.get("injury_type", "other")
        severity = kwargs.get("severity", "mild")
        date = kwargs.get("date", "")
        return self._run_sync(
            self.runner_tools.report_injury, injury_type, severity, date
        )


class ManagePredictionModelTool(BaseTool):
    """预测模型管理工具 - v0.20.1新增"""

    @property
    def name(self) -> str:
        return "manage_prediction_model"

    @property
    def description(self) -> str:
        return "管理预测模型，支持训练(train)、查看状态(status)、回滚(rollback)操作。当用户需要重新训练模型、查看模型状态或回滚模型版本时使用此工具。"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "操作类型",
                    "enum": ["train", "status", "rollback"],
                },
                "model_type": {
                    "type": "string",
                    "description": "模型类型",
                    "enum": ["vdot_predictor", "injury_predictor"],
                },
            },
            "required": ["action", "model_type"],
        }

    async def execute(self, **kwargs: Any) -> str:
        action = kwargs.get("action", "status")
        model_type = kwargs.get("model_type", "vdot_predictor")
        return self._run_sync(
            self.runner_tools.manage_prediction_model, action, model_type
        )


class GetTwinSnapshotTool(BaseTool):
    """数字孪生状态快照工具 - v0.21.0新增"""

    @property
    def name(self) -> str:
        return "get_twin_snapshot"

    @property
    def description(self) -> str:
        return "获取跑者数字孪生5维状态快照，包括体能(VDOT)、负荷(CTL/ATL/TSB)、身体信号(疲劳/恢复)、风险(伤病/过度训练)、训练模式(跑量/强度分布)。当用户询问'我的数字孪生'、'当前状态快照'、'5维状态'时使用此工具。返回JSON格式：{success: true, data: {fitness, load, body_signal, risk, training_pattern, snapshot_date, data_quality}} 或 {success: false, error: 错误信息}"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "required": [],
        }

    async def execute(self, **kwargs: Any) -> str:
        return self._run_sync(self.runner_tools.get_twin_snapshot)


class SimulateTwinTool(BaseTool):
    """数字孪生What-If推演工具 - v0.21.0新增"""

    @property
    def name(self) -> str:
        return "simulate_twin"

    @property
    def description(self) -> str:
        return "数字孪生What-If推演，基于当前状态模拟训练计划执行后的变化。当用户询问'如果我按这个计划训练会怎样'、'推演训练效果'、'What-If模拟'时使用此工具。返回JSON格式：{success: true, data: {plan_name, initial_state, final_state, snapshots, total_weeks, vdot_delta, peak_injury_risk, avg_tsb}} 或 {success: false, error: 错误信息}"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "plan_name": {
                    "type": "string",
                    "description": "计划名称（必填）",
                },
                "weeks": {
                    "type": "array",
                    "description": "周计划列表，每项包含weekly_volume_km/easy_ratio/tempo_ratio/interval_ratio/long_run_km/intensity_multiplier（必填）",
                    "items": {
                        "type": "object",
                        "properties": {
                            "weekly_volume_km": {"type": "number"},
                            "easy_ratio": {"type": "number"},
                            "tempo_ratio": {"type": "number"},
                            "interval_ratio": {"type": "number"},
                            "long_run_km": {"type": "number"},
                            "intensity_multiplier": {"type": "number"},
                        },
                    },
                },
                "prediction_type": {
                    "type": "string",
                    "description": "预测模式（basic/parametric/ml_enhanced，默认parametric）",
                    "enum": ["basic", "parametric", "ml_enhanced"],
                },
            },
            "required": ["plan_name", "weeks"],
        }

    async def execute(self, **kwargs: Any) -> str:
        plan_name = kwargs.get("plan_name", "自定义计划")
        weeks = kwargs.get("weeks", [])
        prediction_type = kwargs.get("prediction_type", "parametric")
        return self._run_sync(
            self.runner_tools.simulate_twin, plan_name, weeks, prediction_type
        )


class CompareTwinPlansTool(BaseTool):
    """数字孪生多计划对比工具 - v0.21.0新增"""

    @property
    def name(self) -> str:
        return "compare_twin_plans"

    @property
    def description(self) -> str:
        return "数字孪生多计划对比，对多个训练计划执行推演并按综合评分排序推荐最优方案。当用户询问'哪个计划更好'、'对比训练方案'、'推荐计划'时使用此工具。返回JSON格式：{success: true, data: {plans, best_plan, comparison_dimensions, recommendation}} 或 {success: false, error: 错误信息}"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "plans": {
                    "type": "array",
                    "description": "计划列表，每项包含name和weeks（必填）",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "weeks": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "weekly_volume_km": {"type": "number"},
                                        "easy_ratio": {"type": "number"},
                                        "tempo_ratio": {"type": "number"},
                                        "interval_ratio": {"type": "number"},
                                        "long_run_km": {"type": "number"},
                                        "intensity_multiplier": {"type": "number"},
                                    },
                                },
                            },
                        },
                    },
                },
                "prediction_type": {
                    "type": "string",
                    "description": "预测模式（basic/parametric/ml_enhanced，默认parametric）",
                    "enum": ["basic", "parametric", "ml_enhanced"],
                },
            },
            "required": ["plans"],
        }

    async def execute(self, **kwargs: Any) -> str:
        plans = kwargs.get("plans", [])
        prediction_type = kwargs.get("prediction_type", "parametric")
        return self._run_sync(
            self.runner_tools.compare_twin_plans, plans, prediction_type
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

    数据上下文大小控制: task参数总长度 <= 8000字符
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
            "调用Subagent执行专项任务。支持教练(coach)、伤病预防师(injury_prevention)、"
            "数据分析(data_analyst)、报告撰写(report_writer)四种Subagent。"
            "主Agent会自动预查询相关数据并传入Subagent。当用户需要训练建议、伤病风险评估、"
            "深度数据分析、生成训练周报/月报时使用此工具。"
            "返回JSON格式: {success: true, data: {subagent_type, result, context_size}} 或 "
            "{success: false, error: 错误信息, fallback_result: 降级结果}"
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "subagent_type": {
                    "type": "string",
                    "description": "Subagent类型: coach(教练) / injury_prevention(伤病预防师) / data_analyst(数据分析) / report_writer(报告撰写)",
                    "enum": [
                        "coach",
                        "injury_prevention",
                        "data_analyst",
                        "report_writer",
                    ],
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
