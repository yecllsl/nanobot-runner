# 决策追踪工具类
# 包含决策反馈记录、计划执行检查、预测精度检查、决策历史查询等工具

from __future__ import annotations

from typing import Any

from src.agents.tools import BaseTool


class RecordFeedbackTool(BaseTool):
    """决策反馈记录工具 - v0.23.0新增"""

    @property
    def name(self) -> str:
        return "record_decision_feedback"

    @property
    def description(self) -> str:
        return (
            "记录用户对AI决策的反馈评分。当用户表达对训练建议的满意度或反馈时使用此工具。"
            "返回JSON格式：{success: true, data: {...}} 或 {success: false, error: ...}"
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "decision_id": {
                    "type": "string",
                    "description": "决策唯一标识（必填）",
                },
                "score": {
                    "type": "integer",
                    "description": "用户反馈评分（1-5，必填）",
                    "minimum": 1,
                    "maximum": 5,
                },
                "text": {
                    "type": "string",
                    "description": "用户反馈文本（可选）",
                },
                "accepted": {
                    "type": "boolean",
                    "description": "推荐是否被采纳（可选）",
                },
            },
            "required": ["decision_id", "score"],
        }

    async def execute(self, **kwargs: Any) -> str:
        decision_id = kwargs.get("decision_id", "")
        score = kwargs.get("score", 3)
        text = kwargs.get("text")
        accepted = kwargs.get("accepted")
        return self._run_sync(
            self.runner_tools.record_decision_feedback,
            decision_id,
            score,
            text,
            accepted,
        )


class CheckPlanExecutionTool(BaseTool):
    """计划执行忠实度检查工具 - v0.23.0新增"""

    @property
    def name(self) -> str:
        return "check_plan_execution"

    @property
    def description(self) -> str:
        return (
            "检查训练计划的执行忠实度。当需要评估用户是否按计划执行训练时使用此工具。"
            "返回JSON格式：{success: true, data: {...}}"
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "decision_id": {
                    "type": "string",
                    "description": "决策唯一标识（必填）",
                },
            },
            "required": ["decision_id"],
        }

    async def execute(self, **kwargs: Any) -> str:
        decision_id = kwargs.get("decision_id", "")
        return self._run_sync(
            self.runner_tools.check_plan_execution,
            decision_id,
        )


class CheckPredictionAccuracyTool(BaseTool):
    """预测精度检查工具 - v0.23.0新增"""

    @property
    def name(self) -> str:
        return "check_prediction_accuracy"

    @property
    def description(self) -> str:
        return (
            "检查VDOT预测的准确度。当需要评估AI预测与实际表现的偏差时使用此工具。"
            "返回JSON格式：{success: true, data: {...}}"
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "decision_id": {
                    "type": "string",
                    "description": "决策唯一标识（必填）",
                },
                "actual_vdot": {
                    "type": "number",
                    "description": "实际VDOT值（可选，默认0.0表示从最新session获取）",
                },
            },
            "required": ["decision_id"],
        }

    async def execute(self, **kwargs: Any) -> str:
        decision_id = kwargs.get("decision_id", "")
        actual_vdot = kwargs.get("actual_vdot", 0.0)
        return self._run_sync(
            self.runner_tools.check_prediction_accuracy,
            decision_id,
            actual_vdot,
        )


class GetDecisionHistoryTool(BaseTool):
    """决策历史查询工具 - v0.23.0新增"""

    @property
    def name(self) -> str:
        return "get_decision_history"

    @property
    def description(self) -> str:
        return (
            "查询AI决策历史记录。当用户询问过去的训练建议或决策记录时使用此工具。"
            "返回JSON格式：{success: true, data: {...}}"
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "description": "起始日期（可选，格式：YYYY-MM-DD）",
                },
                "end_date": {
                    "type": "string",
                    "description": "结束日期（可选，格式：YYYY-MM-DD）",
                },
                "type": {
                    "type": "string",
                    "description": "决策类型过滤（可选，如training_plan/prediction/recovery等）",
                },
                "limit": {
                    "type": "integer",
                    "description": "返回数量限制（默认50）",
                    "default": 50,
                },
            },
        }

    async def execute(self, **kwargs: Any) -> str:
        start_date = kwargs.get("start_date")
        end_date = kwargs.get("end_date")
        decision_type = kwargs.get("type")
        limit = kwargs.get("limit", 50)
        return self._run_sync(
            self.runner_tools.get_decision_history,
            start_date,
            end_date,
            decision_type,
            limit,
        )


class AnalyzeTrainingResponseV2Tool(BaseTool):
    """训练响应性分析工具 - v0.24.0新增"""

    @property
    def name(self) -> str:
        return "analyze_training_response"

    @property
    def description(self) -> str:
        return (
            "分析不同训练类型对跑者VDOT变化的响应效果，识别最佳/最差训练类型。"
            "当用户询问'哪种训练最有效'、'训练效果分析'、'个性化训练建议'时使用此工具。"
            "返回JSON格式：{success: true, data: {...}} 或 {success: false, error: ...}"
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "months": {
                    "type": "integer",
                    "description": "分析月数（默认6）",
                    "default": 6,
                },
            },
        }

    async def execute(self, **kwargs: Any) -> str:
        months = kwargs.get("months", 6)
        return self._run_sync(
            self.runner_tools.analyze_training_response_v2,
            months,
        )


class RunCalibrationTool(BaseTool):
    """预测校准工具 - v0.24.0新增"""

    @property
    def name(self) -> str:
        return "run_calibration"

    @property
    def description(self) -> str:
        return (
            "执行预测校准，检测模型偏差方向和幅度，通过EMA更新scale因子。"
            "当需要校准VDOT/伤病/训练响应预测模型时使用此工具。"
            "返回JSON格式：{success: true, data: {...}} 或 {success: false, error: ...}"
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "model_type": {
                    "type": "string",
                    "description": "模型类型（vdot/injury/training_response，默认vdot）",
                    "default": "vdot",
                },
            },
        }

    async def execute(self, **kwargs: Any) -> str:
        model_type = kwargs.get("model_type", "vdot")
        return self._run_sync(
            self.runner_tools.run_calibration,
            model_type,
        )


class GetCalibrationStatusTool(BaseTool):
    """校准状态查询工具 - v0.24.0新增"""

    @property
    def name(self) -> str:
        return "get_calibration_status"

    @property
    def description(self) -> str:
        return (
            "查询预测校准的当前状态，包括scale因子、样本数、MAE等。"
            "当用户询问'校准状态'、'模型修正情况'时使用此工具。"
            "返回JSON格式：{success: true, data: {...}} 或 {success: false, error: ...}"
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "model_type": {
                    "type": "string",
                    "description": "模型类型（可选，空则返回所有模型状态）",
                },
            },
        }

    async def execute(self, **kwargs: Any) -> str:
        model_type = kwargs.get("model_type")
        return self._run_sync(
            self.runner_tools.get_calibration_status,
            model_type,
        )
