# 透明化模块单元测试
# 覆盖 TransparencyEngine、ObservabilityManager、TraceLogger、TransparencyDisplay

from datetime import datetime

from src.core.transparency.models import (
    AIDecision,
    DataSource,
    DataSourceType,
    DecisionExplanation,
    DecisionPath,
    DecisionStep,
    DecisionType,
    DetailLevel,
    LogEntry,
    LogFilters,
    ObservabilityMetrics,
    TraceReport,
    TraceStatus,
    TransparencySettings,
)
from src.core.transparency.observability_manager import ObservabilityManager
from src.core.transparency.trace_logger import TraceLogger
from src.core.transparency.transparency_display import TransparencyDisplay
from src.core.transparency.transparency_engine import TransparencyEngine


class TestTransparencyModels:
    """透明化数据模型测试"""

    def test_ai_decision_creation(self):
        decision = AIDecision(
            id="test-001",
            decision_type=DecisionType.TRAINING_ADVICE,
            input_data={"user_query": "今天跑步吗"},
            output_data={"suggestion": "建议轻松跑5km"},
            reasoning="用户询问今日训练建议",
            confidence=0.85,
            tools_used=["get_running_stats"],
            memory_referenced=["用户偏好晨跑"],
            duration_ms=1500,
        )
        assert decision.id == "test-001"
        assert decision.decision_type == DecisionType.TRAINING_ADVICE
        assert decision.confidence == 0.85
        assert len(decision.tools_used) == 1

    def test_ai_decision_to_dict(self):
        decision = AIDecision(
            id="test-002",
            decision_type=DecisionType.DATA_QUERY,
        )
        d = decision.to_dict()
        assert d["id"] == "test-002"
        assert d["decision_type"] == "data_query"

    def test_data_source_creation(self):
        ds = DataSource(
            type=DataSourceType.TRAINING_DATA,
            name="历史训练数据",
            description="用户过去30天训练数据",
            quality_score=0.95,
        )
        assert ds.type == DataSourceType.TRAINING_DATA
        assert ds.quality_score == 0.95

    def test_decision_path_to_mermaid(self):
        path = DecisionPath(
            steps=[
                DecisionStep(
                    name="接收请求", description="用户查询", step_type="reasoning"
                ),
                DecisionStep(
                    name="调用工具", description="get_stats", step_type="tool_call"
                ),
                DecisionStep(
                    name="生成响应", description="输出建议", step_type="reasoning"
                ),
            ],
            total_duration_ms=1000,
        )
        mermaid = path.to_mermaid()
        assert "graph LR" in mermaid
        assert "接收请求" in mermaid
        assert "调用工具" in mermaid

    def test_detail_level_values(self):
        assert DetailLevel.OFF.value == "off"
        assert DetailLevel.BRIEF.value == "brief"
        assert DetailLevel.DETAILED.value == "detailed"

    def test_transparency_settings_default(self):
        settings = TransparencySettings.default()
        assert settings.detail_level == DetailLevel.BRIEF
        assert settings.show_data_sources is True
        assert settings.auto_explain is True

    def test_observability_metrics_to_dict(self):
        metrics = ObservabilityMetrics(
            total_traces=10,
            successful_traces=9,
            failed_traces=1,
            avg_duration_ms=500.0,
            error_rate=0.1,
            tool_call_count=20,
            tool_success_rate=0.95,
        )
        d = metrics.to_dict()
        assert d["total_traces"] == 10
        assert d["tool_success_rate"] == 0.95

    def test_trace_report_creation(self):
        report = TraceReport(
            trace_id="trace-001",
            operation_name="test_op",
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration_ms=100,
            status=TraceStatus.COMPLETED,
        )
        assert report.trace_id == "trace-001"
        assert report.status == TraceStatus.COMPLETED

    def test_log_entry_creation(self):
        entry = LogEntry(
            timestamp=datetime.now(),
            level="INFO",
            message="测试日志",
            context={"key": "value"},
            entry_type="decision",
        )
        assert entry.level == "INFO"
        assert entry.entry_type == "decision"

    def test_log_filters_creation(self):
        filters = LogFilters(limit=50)
        assert filters.limit == 50
        assert filters.start_time is None

    def test_decision_type_values(self):
        assert DecisionType.TRAINING_ADVICE.value == "training_advice"
        assert DecisionType.PLAN_ADJUSTMENT.value == "plan_adjustment"
        assert DecisionType.RECOVERY_SUGGESTION.value == "recovery_suggestion"
        assert DecisionType.WEATHER_ADVICE.value == "weather_advice"
        assert DecisionType.DATA_QUERY.value == "data_query"
        assert DecisionType.GENERAL.value == "general"


class TestTransparencyEngine:
    """TransparencyEngine 测试"""

    def setup_method(self):
        self.engine = TransparencyEngine()

    def test_generate_explanation_brief(self):
        decision = AIDecision(
            id="eng-001",
            decision_type=DecisionType.TRAINING_ADVICE,
            input_data={"user_query": "今天跑步吗"},
            reasoning="用户询问训练建议。结合历史数据分析。建议轻松跑。",
            confidence=0.85,
            tools_used=["get_running_stats"],
            memory_referenced=["用户偏好晨跑"],
            duration_ms=1500,
        )
        explanation = self.engine.generate_explanation(decision, DetailLevel.BRIEF)

        assert explanation.decision_id == "eng-001"
        assert len(explanation.brief_reasons) > 0
        assert explanation.confidence_score == 0.85

    def test_generate_explanation_detailed(self):
        decision = AIDecision(
            id="eng-002",
            decision_type=DecisionType.RECOVERY_SUGGESTION,
            reasoning="建议休息一天",
            confidence=0.7,
            tools_used=["get_training_load"],
        )
        explanation = self.engine.generate_explanation(decision, DetailLevel.DETAILED)

        assert explanation.decision_id == "eng-002"
        assert explanation.detailed_analysis != ""
        assert "recovery_suggestion" in explanation.detailed_analysis

    def test_trace_data_sources(self):
        decision = AIDecision(
            id="eng-003",
            decision_type=DecisionType.GENERAL,
            input_data={"training_data": True, "user_profile": True},
            tools_used=["weather_tool"],
            memory_referenced=["历史记忆"],
        )
        self.engine.generate_explanation(decision)
        sources = self.engine.trace_data_sources("eng-003")

        assert len(sources) > 0
        source_types = [s.type for s in sources]
        assert DataSourceType.TRAINING_DATA in source_types
        assert DataSourceType.EXTERNAL_TOOL in source_types
        assert DataSourceType.MEMORY in source_types

    def test_trace_data_sources_not_found(self):
        sources = self.engine.trace_data_sources("nonexistent")
        assert sources == []

    def test_visualize_decision_path(self):
        decision = AIDecision(
            id="eng-004",
            decision_type=DecisionType.DATA_QUERY,
            input_data={"user_query": "配速建议"},
            tools_used=["get_vdot_trend"],
            memory_referenced=["VDOT历史"],
            duration_ms=2000,
        )
        path = self.engine.visualize_decision_path(decision)

        assert len(path.steps) >= 3
        assert path.total_duration_ms == 2000
        step_names = [s.name for s in path.steps]
        assert "接收用户请求" in step_names

    def test_get_decision(self):
        decision = AIDecision(id="eng-005", decision_type=DecisionType.GENERAL)
        self.engine.generate_explanation(decision)

        retrieved = self.engine.get_decision("eng-005")
        assert retrieved is not None
        assert retrieved.id == "eng-005"

    def test_clear_store(self):
        decision = AIDecision(id="eng-006", decision_type=DecisionType.GENERAL)
        self.engine.generate_explanation(decision)
        self.engine.clear_store()

        assert self.engine.get_decision("eng-006") is None


class TestObservabilityManager:
    """ObservabilityManager 测试"""

    def setup_method(self):
        self.manager = ObservabilityManager()

    def test_start_trace(self):
        trace_id = self.manager.start_trace("test_operation")
        assert trace_id != ""
        assert self.manager.get_active_trace_count() == 1

    def test_record_event(self):
        trace_id = self.manager.start_trace("test_op")
        self.manager.record_event(trace_id, "test_event", {"key": "value"})

        assert self.manager.get_active_trace_count() == 1

    def test_end_trace(self):
        trace_id = self.manager.start_trace("test_op")
        report = self.manager.end_trace(trace_id, status="completed")

        assert report.trace_id == trace_id
        assert report.status == TraceStatus.COMPLETED
        assert self.manager.get_active_trace_count() == 0

    def test_end_trace_failed(self):
        trace_id = self.manager.start_trace("test_op")
        report = self.manager.end_trace(trace_id, status="failed")

        assert report.status == TraceStatus.FAILED

    def test_end_trace_not_found(self):
        report = self.manager.end_trace("nonexistent", status="completed")
        assert report.status == TraceStatus.FAILED

    def test_get_metrics(self):
        trace_id = self.manager.start_trace("test_op")
        self.manager.record_event(trace_id, "tool_call", {"success": True})
        self.manager.end_trace(trace_id)

        metrics = self.manager.get_metrics()
        assert metrics.total_traces == 1
        assert metrics.successful_traces == 1
        assert metrics.tool_call_count == 1

    def test_get_recent_traces(self):
        for i in range(5):
            trace_id = self.manager.start_trace(f"op_{i}")
            self.manager.end_trace(trace_id)

        recent = self.manager.get_recent_traces(limit=3)
        assert len(recent) == 3

    def test_get_trace(self):
        trace_id = self.manager.start_trace("test_op")
        self.manager.end_trace(trace_id)

        found = self.manager.get_trace(trace_id)
        assert found is not None
        assert found.trace_id == trace_id

    def test_clear_history(self):
        trace_id = self.manager.start_trace("test_op")
        self.manager.end_trace(trace_id)
        self.manager.clear_history()

        metrics = self.manager.get_metrics()
        assert metrics.total_traces == 0


class TestTraceLogger:
    """TraceLogger 测试"""

    def setup_method(self):
        self.logger = TraceLogger()

    def test_log_decision(self):
        decision = AIDecision(
            id="log-001",
            decision_type=DecisionType.TRAINING_ADVICE,
            confidence=0.9,
            tools_used=["get_running_stats"],
        )
        self.logger.log_decision(decision)

        stats = self.logger.get_stats()
        assert stats["decision_count"] == 1

    def test_log_decision_with_explanation(self):
        decision = AIDecision(
            id="log-002",
            decision_type=DecisionType.GENERAL,
            confidence=0.8,
        )
        explanation = DecisionExplanation(
            decision_id="log-002",
            brief_reasons=["理由1", "理由2"],
        )
        self.logger.log_decision(decision, explanation)

        logs = self.logger.get_decision_logs()
        assert len(logs) == 1

    def test_log_tool_invocation(self):
        self.logger.log_tool_invocation(
            tool_id="get_stats",
            params={"limit": 10},
            result={"total": 5},
            success=True,
            duration_ms=200,
        )

        stats = self.logger.get_stats()
        assert stats["tool_call_count"] == 1

    def test_log_tool_invocation_failure(self):
        self.logger.log_tool_invocation(
            tool_id="bad_tool",
            params={},
            success=False,
            duration_ms=100,
        )

        tool_logs = self.logger.get_tool_call_logs()
        assert len(tool_logs) == 1
        assert tool_logs[0].level == "WARNING"

    def test_query_logs_no_filter(self):
        decision = AIDecision(id="q-001", decision_type=DecisionType.GENERAL)
        self.logger.log_decision(decision)

        logs = self.logger.query_logs()
        assert len(logs) == 1

    def test_query_logs_with_filter(self):
        decision = AIDecision(
            id="q-002",
            decision_type=DecisionType.TRAINING_ADVICE,
        )
        self.logger.log_decision(decision)

        filters = LogFilters(decision_type="training_advice")
        logs = self.logger.query_logs(filters)
        assert len(logs) == 1

    def test_get_stats(self):
        decision = AIDecision(id="s-001", decision_type=DecisionType.GENERAL)
        self.logger.log_decision(decision)
        self.logger.log_tool_invocation("tool1", {}, success=True)

        stats = self.logger.get_stats()
        assert stats["total_entries"] == 2
        assert stats["decision_count"] == 1
        assert stats["tool_call_count"] == 1

    def test_clear(self):
        decision = AIDecision(id="c-001", decision_type=DecisionType.GENERAL)
        self.logger.log_decision(decision)
        self.logger.clear()

        stats = self.logger.get_stats()
        assert stats["total_entries"] == 0


class TestTransparencyDisplay:
    """TransparencyDisplay 测试"""

    def setup_method(self):
        self.display = TransparencyDisplay()

    def test_display_brief_explanation(self):
        explanation = DecisionExplanation(
            decision_id="disp-001",
            brief_reasons=["理由1", "理由2"],
            confidence_score=0.85,
        )
        panel = self.display.display_brief_explanation(explanation)
        assert panel is not None

    def test_display_detailed_explanation(self):
        explanation = DecisionExplanation(
            decision_id="disp-002",
            brief_reasons=["理由1"],
            detailed_analysis="详细分析内容",
            data_sources=[
                DataSource(
                    type=DataSourceType.TRAINING_DATA,
                    name="训练数据",
                    description="历史训练数据",
                    quality_score=0.9,
                )
            ],
            decision_path=DecisionPath(
                steps=[
                    DecisionStep(
                        name="步骤1", description="描述", step_type="reasoning"
                    ),
                ],
                total_duration_ms=500,
            ),
            confidence_score=0.7,
        )
        panel = self.display.display_detailed_explanation(explanation)
        assert panel is not None

    def test_display_data_sources(self):
        sources = [
            DataSource(
                type=DataSourceType.TRAINING_DATA,
                name="训练数据",
                description="历史训练数据",
                quality_score=0.9,
            ),
            DataSource(
                type=DataSourceType.EXTERNAL_TOOL,
                name="天气工具",
                description="天气数据",
                quality_score=0.85,
            ),
        ]
        table = self.display.display_data_sources(sources)
        assert table is not None

    def test_display_decision_path(self):
        path = DecisionPath(
            steps=[
                DecisionStep(name="步骤1", description="描述1", step_type="reasoning"),
                DecisionStep(name="步骤2", description="描述2", step_type="tool_call"),
            ],
            total_duration_ms=1000,
        )
        mermaid = self.display.display_decision_path(path)
        assert "graph LR" in mermaid

    def test_display_explanation_by_level_off(self):
        explanation = DecisionExplanation(decision_id="disp-003")
        result = self.display.display_explanation_by_level(explanation, DetailLevel.OFF)
        assert result is not None

    def test_format_confidence(self):
        high = TransparencyDisplay.format_confidence(0.9)
        assert "90%" in str(high)

        mid = TransparencyDisplay.format_confidence(0.6)
        assert "60%" in str(mid)

        low = TransparencyDisplay.format_confidence(0.3)
        assert "30%" in str(low)


class TestAIStatusDashboard:
    """AI状态洞察看板测试"""

    def setup_method(self):
        from src.core.transparency.ai_status_dashboard import AIStatusDashboard

        self.manager = ObservabilityManager()
        self.trace_logger = TraceLogger()
        self.dashboard = AIStatusDashboard(
            manager=self.manager,
            trace_logger=self.trace_logger,
        )

    def test_render(self):
        layout = self.dashboard.render()
        assert layout is not None

    def test_render_evolution_status(self):
        panel = self.dashboard.render_evolution_status()
        assert panel is not None

    def test_render_suggestion_quality(self):
        panel = self.dashboard.render_suggestion_quality()
        assert panel is not None

    def test_render_tool_reliability(self):
        table = self.dashboard.render_tool_reliability()
        assert table is not None

    def test_render_memory_log_empty(self):
        panel = self.dashboard.render_memory_log()
        assert panel is not None

    def test_render_memory_log_with_data(self):
        decision = AIDecision(id="mem-001", decision_type=DecisionType.GENERAL)
        self.trace_logger.log_decision(decision)

        panel = self.dashboard.render_memory_log()
        assert panel is not None

    def test_get_dashboard_data(self):
        data = self.dashboard.get_dashboard_data()
        assert "evolution" in data
        assert "suggestion_quality" in data
        assert "tool_reliability" in data
        assert "log_stats" in data

    def test_get_dashboard_data_with_traces(self):
        trace_id = self.manager.start_trace("test_op")
        self.manager.record_event(
            trace_id, "tool_call", {"tool_name": "tool1", "success": True}
        )
        self.manager.end_trace(trace_id)

        decision = AIDecision(id="d-001", decision_type=DecisionType.GENERAL)
        self.trace_logger.log_decision(decision)

        data = self.dashboard.get_dashboard_data()
        assert data["evolution"]["total_traces"] == 1
        assert data["evolution"]["total_decisions"] == 1
        assert data["evolution"]["success_rate"] == 1.0

    def test_calculate_evolution_level(self):
        from src.core.transparency.ai_status_dashboard import AIStatusDashboard

        assert AIStatusDashboard._calculate_evolution_level(0) == "新手"
        assert AIStatusDashboard._calculate_evolution_level(20) == "初级"
        assert AIStatusDashboard._calculate_evolution_level(100) == "中级"
        assert AIStatusDashboard._calculate_evolution_level(500) == "高级"
        assert AIStatusDashboard._calculate_evolution_level(1000) == "专家级"

    def test_calculate_quality_score(self):
        from src.core.transparency.ai_status_dashboard import AIStatusDashboard

        score = AIStatusDashboard._calculate_quality_score(1.0, 0, 10)
        assert score >= 8.0

        score = AIStatusDashboard._calculate_quality_score(0.5, 5, 10)
        assert score < 5.0


class TestTrainingInsightReport:
    """训练洞察报告测试"""

    def setup_method(self):
        from src.core.transparency.training_insight_report import TrainingInsightReport

        self.manager = ObservabilityManager()
        self.trace_logger = TraceLogger()
        self.report = TrainingInsightReport(
            manager=self.manager,
            trace_logger=self.trace_logger,
        )

    def test_generate_report(self):
        data = self.report.generate_report()
        assert "generated_at" in data
        assert "training_patterns" in data
        assert "recovery_trend" in data
        assert "ai_advice_effect" in data
        assert "evolution_report" in data

    def test_analyze_training_patterns(self):
        decision = AIDecision(id="tp-001", decision_type=DecisionType.TRAINING_ADVICE)
        self.trace_logger.log_decision(decision)

        patterns = self.report.analyze_training_patterns()
        assert patterns["total_decisions"] == 1
        assert patterns["tool_calls"] == 0

    def test_analyze_recovery_trend(self):
        trace_id = self.manager.start_trace("recovery_test")
        self.manager.end_trace(trace_id)

        trend = self.report.analyze_recovery_trend()
        assert trend["trace_success_rate"] == 1.0
        assert trend["error_rate"] == 0.0

    def test_evaluate_ai_advice_effect(self):
        effect = self.report.evaluate_ai_advice_effect()
        assert "quality_score" in effect
        assert "tool_success_rate" in effect

    def test_generate_evolution_report(self):
        decision = AIDecision(id="evo-001", decision_type=DecisionType.GENERAL)
        self.trace_logger.log_decision(decision)

        evo = self.report.generate_evolution_report()
        assert evo["level"] == "新手"
        assert evo["experience"] == 1
        assert "再积累" in evo["next_level_requirement"]

    def test_render_report(self):
        panel = self.report.render_report()
        assert panel is not None

    def test_render_training_patterns_table(self):
        table = self.report.render_training_patterns_table()
        assert table is not None

    def test_calculate_level(self):
        from src.core.transparency.training_insight_report import TrainingInsightReport

        assert TrainingInsightReport._calculate_level(0) == "新手"
        assert TrainingInsightReport._calculate_level(20) == "初级"
        assert TrainingInsightReport._calculate_level(100) == "中级"
        assert TrainingInsightReport._calculate_level(500) == "高级"
        assert TrainingInsightReport._calculate_level(1000) == "专家级"

    def test_get_next_level_requirement(self):
        from src.core.transparency.training_insight_report import TrainingInsightReport

        req = TrainingInsightReport._get_next_level_requirement(0)
        assert "再积累" in req

        req = TrainingInsightReport._get_next_level_requirement(1000)
        assert "已达最高等级" in req

    def test_calculate_tool_mastery(self):
        self.trace_logger.log_tool_invocation(
            tool_id="tool_a", params={}, success=True, duration_ms=100
        )
        self.trace_logger.log_tool_invocation(
            tool_id="tool_a", params={}, success=True, duration_ms=100
        )

        mastery = self.report._calculate_tool_mastery()
        assert "tool_a" in mastery
        assert mastery["tool_a"] == 0.1
