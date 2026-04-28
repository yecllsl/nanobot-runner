# 透明化集成测试
# 测试透明化+可观测性+Hook集成


from src.core.transparency.models import (
    AIDecision,
    DecisionType,
    DetailLevel,
    TraceStatus,
)
from src.core.transparency.observability_manager import ObservabilityManager
from src.core.transparency.trace_logger import TraceLogger
from src.core.transparency.transparency_engine import TransparencyEngine


class TestTransparencyObservabilityIntegration:
    """透明化与可观测性集成测试"""

    def setup_method(self):
        self.engine = TransparencyEngine()
        self.manager = ObservabilityManager()
        self.trace_logger = TraceLogger()

    def test_full_decision_flow(self):
        """测试完整决策流程：追踪→决策→解释→日志"""
        trace_id = self.manager.start_trace(
            "training_advice",
            tags={"session": "test"},
        )

        self.manager.record_event(trace_id, "iteration_start", {"iteration": 1})
        self.manager.record_event(
            trace_id, "tool_call", {"tool_name": "get_running_stats", "success": True}
        )

        decision = AIDecision(
            id=trace_id,
            decision_type=DecisionType.TRAINING_ADVICE,
            input_data={"user_query": "今天跑步吗", "training_data": True},
            reasoning="基于历史数据分析，建议轻松跑5km。",
            confidence=0.85,
            tools_used=["get_running_stats"],
            memory_referenced=["用户偏好晨跑"],
            duration_ms=1500,
        )

        explanation = self.engine.generate_explanation(decision, DetailLevel.BRIEF)

        self.trace_logger.log_decision(decision, explanation)

        self.manager.record_event(trace_id, "iteration_end", {"iteration": 1})
        report = self.manager.end_trace(trace_id, status="completed")

        assert report.status == TraceStatus.COMPLETED
        assert len(report.events) == 3

        assert explanation.decision_id == trace_id
        assert len(explanation.brief_reasons) > 0
        assert len(explanation.data_sources) > 0

        decision_logs = self.trace_logger.get_decision_logs()
        assert len(decision_logs) == 1

        metrics = self.manager.get_metrics()
        assert metrics.total_traces == 1
        assert metrics.successful_traces == 1

    def test_multiple_decisions_tracking(self):
        """测试多决策追踪"""
        for i in range(3):
            trace_id = self.manager.start_trace(f"decision_{i}")

            decision = AIDecision(
                id=f"multi-{i}",
                decision_type=DecisionType.GENERAL,
                confidence=0.7 + i * 0.1,
                tools_used=[f"tool_{i}"],
            )

            self.engine.generate_explanation(decision)
            self.trace_logger.log_decision(decision)

            self.manager.end_trace(trace_id)

        metrics = self.manager.get_metrics()
        assert metrics.total_traces == 3

        decision_logs = self.trace_logger.get_decision_logs()
        assert len(decision_logs) == 3

    def test_trace_with_tool_failure(self):
        """测试工具调用失败的追踪"""
        trace_id = self.manager.start_trace("failing_op")

        self.manager.record_event(
            trace_id, "tool_call", {"tool_name": "bad_tool", "success": False}
        )

        report = self.manager.end_trace(trace_id, status="failed")

        assert report.status == TraceStatus.FAILED

        metrics = self.manager.get_metrics()
        assert metrics.failed_traces == 1
        assert metrics.error_rate == 1.0

    def test_data_source_tracing_across_decisions(self):
        """测试跨决策的数据来源追溯"""
        decision1 = AIDecision(
            id="cross-001",
            decision_type=DecisionType.TRAINING_ADVICE,
            input_data={"training_data": True},
            tools_used=["get_running_stats"],
        )
        self.engine.generate_explanation(decision1)

        decision2 = AIDecision(
            id="cross-002",
            decision_type=DecisionType.RECOVERY_SUGGESTION,
            input_data={"user_profile": True},
            memory_referenced=["恢复记录"],
        )
        self.engine.generate_explanation(decision2)

        sources1 = self.engine.trace_data_sources("cross-001")
        sources2 = self.engine.trace_data_sources("cross-002")

        assert any(s.type.value == "training_data" for s in sources1)
        assert any(s.type.value == "memory" for s in sources2)


class TestTransparencyDashboardIntegration:
    """透明化看板集成测试"""

    def setup_method(self):
        self.manager = ObservabilityManager()
        self.trace_logger = TraceLogger()
        self.engine = TransparencyEngine()

    def test_dashboard_with_data(self):
        """测试有数据时的看板展示"""
        from src.core.transparency.ai_status_dashboard import AIStatusDashboard

        trace_id = self.manager.start_trace("dash_test")
        self.manager.record_event(
            trace_id, "tool_call", {"tool_name": "get_stats", "success": True}
        )
        self.manager.end_trace(trace_id)

        decision = AIDecision(
            id="dash-001",
            decision_type=DecisionType.GENERAL,
            confidence=0.8,
        )
        self.trace_logger.log_decision(decision)

        dashboard = AIStatusDashboard(
            manager=self.manager,
            trace_logger=self.trace_logger,
        )

        data = dashboard.get_dashboard_data()
        assert "evolution" in data
        assert "suggestion_quality" in data
        assert "tool_reliability" in data

    def test_training_insight_report(self):
        """测试训练洞察报告"""
        from src.core.transparency.training_insight_report import TrainingInsightReport

        decision = AIDecision(
            id="insight-001",
            decision_type=DecisionType.TRAINING_ADVICE,
            confidence=0.9,
        )
        self.trace_logger.log_decision(decision)

        report = TrainingInsightReport(
            manager=self.manager,
            trace_logger=self.trace_logger,
        )

        data = report.generate_report()
        assert "training_patterns" in data
        assert "recovery_trend" in data
        assert "ai_advice_effect" in data
        assert "evolution_report" in data

    def test_evolution_level_progression(self):
        """测试进化等级递进"""
        from src.core.transparency.ai_status_dashboard import AIStatusDashboard

        dashboard = AIStatusDashboard(
            manager=self.manager,
            trace_logger=self.trace_logger,
        )

        assert dashboard._calculate_evolution_level(0) == "新手"
        assert dashboard._calculate_evolution_level(20) == "初级"
        assert dashboard._calculate_evolution_level(100) == "中级"
        assert dashboard._calculate_evolution_level(500) == "高级"
        assert dashboard._calculate_evolution_level(1000) == "专家级"
