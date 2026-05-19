# 数据管理/系统工具类
# 包含记忆更新、诊断、个性化建议、反馈、偏好、透明化/解释、数据追溯、透明化洞察等工具

from __future__ import annotations

from typing import Any

from src.agents.tools import BaseTool


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
