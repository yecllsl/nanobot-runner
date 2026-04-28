# 透明化E2E测试
# 完整决策→追踪→解释→展示流程测试


from src.core.transparency.models import (
    AIDecision,
    DecisionType,
    DetailLevel,
    TraceStatus,
)
from src.core.transparency.observability_manager import ObservabilityManager
from src.core.transparency.trace_logger import TraceLogger
from src.core.transparency.transparency_display import TransparencyDisplay
from src.core.transparency.transparency_engine import TransparencyEngine


class TestTransparencyE2E:
    """透明化端到端流程测试"""

    def setup_method(self):
        self.engine = TransparencyEngine()
        self.manager = ObservabilityManager()
        self.trace_logger = TraceLogger()
        self.display = TransparencyDisplay()

    def test_full_e2e_brief_flow(self):
        """E2E: 完整简洁版流程 - 决策→追踪→解释→展示"""
        trace_id = self.manager.start_trace(
            "e2e_brief",
            tags={"test_type": "brief"},
        )

        self.manager.record_event(trace_id, "iteration_start")
        self.manager.record_event(
            trace_id,
            "tool_call",
            {"tool_name": "get_running_stats", "success": True},
        )
        self.manager.record_event(
            trace_id,
            "tool_call",
            {"tool_name": "get_vdot_trend", "success": True},
        )

        decision = AIDecision(
            id=trace_id,
            decision_type=DecisionType.TRAINING_ADVICE,
            input_data={
                "user_query": "帮我制定本周训练计划",
                "training_data": True,
                "user_profile": True,
            },
            output_data={"plan": "周一轻松跑5km，周三间歇跑"},
            reasoning="基于用户VDOT趋势和训练历史。建议适度增加训练量。注意恢复。",
            confidence=0.88,
            tools_used=["get_running_stats", "get_vdot_trend"],
            memory_referenced=["用户偏好晨跑", "VDOT历史记录"],
            duration_ms=2500,
        )

        explanation = self.engine.generate_explanation(decision, DetailLevel.BRIEF)
        self.trace_logger.log_decision(decision, explanation)

        self.manager.record_event(trace_id, "iteration_end")
        report = self.manager.end_trace(trace_id)

        panel = self.display.display_brief_explanation(explanation)
        assert panel is not None

        assert report.status == TraceStatus.COMPLETED
        assert len(report.events) == 4

        assert explanation.decision_id == trace_id
        assert len(explanation.brief_reasons) >= 1
        assert len(explanation.data_sources) >= 2

        metrics = self.manager.get_metrics()
        assert metrics.total_traces == 1
        assert metrics.tool_call_count == 2
        assert metrics.tool_success_rate == 1.0

        decision_logs = self.trace_logger.get_decision_logs()
        assert len(decision_logs) == 1

    def test_full_e2e_detailed_flow(self):
        """E2E: 完整详细版流程 - 决策→追踪→解释→展示"""
        trace_id = self.manager.start_trace("e2e_detailed")

        decision = AIDecision(
            id=trace_id,
            decision_type=DecisionType.RECOVERY_SUGGESTION,
            input_data={"user_query": "今天感觉疲劳", "weather_data": True},
            reasoning="用户表示疲劳，结合天气数据和训练负荷分析。建议休息或轻松跑。",
            confidence=0.75,
            tools_used=["get_training_load", "get_weather_training_advice"],
            memory_referenced=["上次高强度训练"],
            duration_ms=1800,
        )

        explanation = self.engine.generate_explanation(decision, DetailLevel.DETAILED)
        self.trace_logger.log_decision(decision, explanation)

        self.manager.end_trace(trace_id)

        panel = self.display.display_detailed_explanation(explanation)
        assert panel is not None

        if explanation.data_sources:
            table = self.display.display_data_sources(explanation.data_sources)
            assert table is not None

        mermaid = self.display.display_decision_path(explanation.decision_path)
        assert "graph LR" in mermaid

        assert explanation.detailed_analysis != ""
        assert "recovery_suggestion" in explanation.detailed_analysis

    def test_e2e_multi_session_flow(self):
        """E2E: 多会话流程 - 多次决策→追踪→统计"""
        sessions = [
            ("session-1", DecisionType.TRAINING_ADVICE, 0.9),
            ("session-2", DecisionType.DATA_QUERY, 0.8),
            ("session-3", DecisionType.RECOVERY_SUGGESTION, 0.7),
        ]

        for session_id, decision_type, confidence in sessions:
            trace_id = self.manager.start_trace(session_id)

            self.manager.record_event(
                trace_id, "tool_call", {"tool_name": "tool", "success": True}
            )

            decision = AIDecision(
                id=session_id,
                decision_type=decision_type,
                confidence=confidence,
                tools_used=["tool"],
            )
            explanation = self.engine.generate_explanation(decision)
            self.trace_logger.log_decision(decision, explanation)

            self.manager.end_trace(trace_id)

        metrics = self.manager.get_metrics()
        assert metrics.total_traces == 3
        assert metrics.successful_traces == 3

        decision_logs = self.trace_logger.get_decision_logs()
        assert len(decision_logs) == 3

    def test_e2e_error_recovery_flow(self):
        """E2E: 错误恢复流程 - 工具失败→重试→成功"""
        trace_id = self.manager.start_trace("error_recovery")

        self.manager.record_event(
            trace_id,
            "tool_call",
            {"tool_name": "failing_tool", "success": False},
        )

        self.manager.record_event(
            trace_id,
            "tool_call",
            {"tool_name": "retry_tool", "success": True},
        )

        decision = AIDecision(
            id="error-001",
            decision_type=DecisionType.GENERAL,
            confidence=0.5,
            tools_used=["failing_tool", "retry_tool"],
        )
        explanation = self.engine.generate_explanation(decision)
        self.trace_logger.log_decision(decision, explanation)

        self.manager.end_trace(trace_id)

        metrics = self.manager.get_metrics()
        assert metrics.tool_call_count == 2
        assert metrics.tool_success_rate == 0.5

    def test_e2e_dashboard_and_insight(self):
        """E2E: 看板和洞察报告流程"""
        from src.core.transparency.ai_status_dashboard import AIStatusDashboard
        from src.core.transparency.training_insight_report import TrainingInsightReport

        for i in range(5):
            trace_id = self.manager.start_trace(f"insight_{i}")
            self.manager.record_event(
                trace_id, "tool_call", {"tool_name": f"tool_{i}", "success": True}
            )
            self.manager.end_trace(trace_id)

            decision = AIDecision(
                id=f"insight-{i}",
                decision_type=DecisionType.TRAINING_ADVICE,
                confidence=0.8 + i * 0.02,
                tools_used=[f"tool_{i}"],
            )
            self.trace_logger.log_decision(decision)

        dashboard = AIStatusDashboard(
            manager=self.manager,
            trace_logger=self.trace_logger,
        )
        dashboard_data = dashboard.get_dashboard_data()
        assert dashboard_data["evolution"]["level"] == "新手"

        report = TrainingInsightReport(
            manager=self.manager,
            trace_logger=self.trace_logger,
        )
        report_data = report.generate_report()
        assert report_data["training_patterns"]["total_decisions"] == 5
        assert report_data["evolution_report"]["level"] == "新手"
