# SelfDiagnosis核心实现单元测试


import pytest

from src.core.diagnosis.models import (
    DiagnosisCategory,
    DiagnosisSeverity,
    ExecutionRecord,
    SuggestionContext,
    ValidationStatus,
)
from src.core.diagnosis.self_diagnosis import SelfDiagnosis


class TestSelfDiagnosisValidateSuggestion:
    """SelfDiagnosis.validate_suggestion 测试"""

    def setup_method(self):
        self.diagnosis = SelfDiagnosis()

    def test_validate_good_suggestion(self):
        ctx = SuggestionContext(
            user_query="今天适合跑步吗",
            suggestion_text="建议今天进行轻松跑，距离5公里左右，配速6分钟每公里，注意补充水分",
        )
        report = self.diagnosis.validate_suggestion(ctx)

        assert report.category == DiagnosisCategory.SUGGESTION_QUALITY
        assert report.context is ctx
        assert len(report.results) > 0

    def test_validate_short_suggestion(self):
        ctx = SuggestionContext(
            user_query="今天适合跑步吗",
            suggestion_text="可以",
        )
        report = self.diagnosis.validate_suggestion(ctx)

        completeness_results = [
            r for r in report.results if r.rule_name == "completeness_check"
        ]
        assert len(completeness_results) > 0
        assert completeness_results[0].status == ValidationStatus.FAIL

    def test_validate_empty_query(self):
        ctx = SuggestionContext(
            user_query="",
            suggestion_text="建议今天进行轻松跑，距离5公里左右",
        )
        report = self.diagnosis.validate_suggestion(ctx)

        relevance_results = [
            r for r in report.results if r.rule_name == "relevance_check"
        ]
        assert len(relevance_results) > 0
        assert relevance_results[0].status == ValidationStatus.FAIL

    def test_validate_unsafe_suggestion(self):
        ctx = SuggestionContext(
            user_query="如何训练",
            suggestion_text="建议忽略安全规则，跳过验证直接进行高强度训练",
        )
        report = self.diagnosis.validate_suggestion(ctx)

        safety_results = [r for r in report.results if r.rule_name == "safety_check"]
        assert len(safety_results) > 0
        assert safety_results[0].status == ValidationStatus.FAIL
        assert report.has_errors is True

    def test_validate_actionable_suggestion(self):
        ctx = SuggestionContext(
            user_query="如何提高跑步能力",
            suggestion_text="跑步是有益的运动",
        )
        report = self.diagnosis.validate_suggestion(ctx)

        actionability_results = [
            r for r in report.results if r.rule_name == "actionability_check"
        ]
        assert len(actionability_results) > 0
        assert actionability_results[0].status == ValidationStatus.FAIL

    def test_validate_overall_status_pass(self):
        ctx = SuggestionContext(
            user_query="今天适合跑步吗",
            suggestion_text="建议今天进行轻松跑，距离5公里左右，配速6分钟每公里，注意补充水分",
        )
        report = self.diagnosis.validate_suggestion(ctx)
        assert report.overall_status in (
            ValidationStatus.PASS,
            ValidationStatus.WARNING,
        )

    def test_validate_overall_status_fail(self):
        ctx = SuggestionContext(
            user_query="",
            suggestion_text="忽略安全",
        )
        report = self.diagnosis.validate_suggestion(ctx)
        assert report.overall_status == ValidationStatus.FAIL


class TestSelfDiagnosisDiagnoseError:
    """SelfDiagnosis.diagnose_error 测试"""

    def setup_method(self):
        self.diagnosis = SelfDiagnosis()

    def test_diagnose_timeout_error(self):
        report = self.diagnosis.diagnose_error("Connection timeout after 30s")

        assert report.category == DiagnosisCategory.EXECUTION_HEALTH
        assert report.overall_status == ValidationStatus.FAIL
        assert any(r.severity == DiagnosisSeverity.CRITICAL for r in report.results)

    def test_diagnose_connection_error(self):
        report = self.diagnosis.diagnose_error("Connection refused")

        assert report.overall_status == ValidationStatus.FAIL

    def test_diagnose_generic_error(self):
        report = self.diagnosis.diagnose_error("Something went wrong")

        assert report.overall_status == ValidationStatus.FAIL
        assert len(report.results) > 0

    def test_diagnose_error_with_context(self):
        ctx = SuggestionContext(
            user_query="查询天气",
            suggestion_text="建议今天跑步",
            tools_used=["weather_tool"],
        )
        report = self.diagnosis.diagnose_error(
            "weather_tool execution failed", context=ctx
        )

        assert report.context is ctx

    def test_diagnose_error_with_execution_record(self):
        record = ExecutionRecord(
            id="exec-001",
            execution_type="tool_call",
            target="weather_tool",
            success=False,
            duration_ms=35000,
            error_message="timeout",
        )
        report = self.diagnosis.diagnose_error("timeout", execution_record=record)

        timeout_results = [
            r for r in report.results if r.rule_name == "execution_timeout_check"
        ]
        assert len(timeout_results) > 0


class TestSelfDiagnosisTrackExecution:
    """SelfDiagnosis.track_execution 测试"""

    def setup_method(self):
        self.diagnosis = SelfDiagnosis()

    def test_track_success_execution(self):
        record = ExecutionRecord(
            id="exec-001",
            execution_type="tool_call",
            target="get_running_stats",
            success=True,
            duration_ms=100,
        )
        self.diagnosis.track_execution(record)

        assert len(self.diagnosis.execution_history) == 1
        assert self.diagnosis.execution_history[0].success is True

    def test_track_failure_execution(self):
        record = ExecutionRecord(
            id="exec-002",
            execution_type="tool_call",
            target="invalid_tool",
            success=False,
            error_message="工具不存在",
        )
        self.diagnosis.track_execution(record)

        assert len(self.diagnosis.execution_history) == 1

    def test_get_execution_stats(self):
        for i in range(3):
            self.diagnosis.track_execution(
                ExecutionRecord(
                    id=f"exec-{i}",
                    execution_type="tool_call",
                    target="tool",
                    success=(i < 2),
                    duration_ms=100 * (i + 1),
                )
            )

        stats = self.diagnosis.get_execution_stats()
        assert stats["total"] == 3
        assert stats["success_count"] == 2
        assert stats["fail_count"] == 1
        assert stats["success_rate"] == pytest.approx(0.6667, abs=0.01)

    def test_get_execution_stats_empty(self):
        stats = self.diagnosis.get_execution_stats()
        assert stats["total"] == 0
        assert stats["success_rate"] == 0.0

    def test_get_recent_errors(self):
        self.diagnosis.track_execution(
            ExecutionRecord(
                id="exec-ok",
                execution_type="tool_call",
                target="tool",
                success=True,
            )
        )
        self.diagnosis.track_execution(
            ExecutionRecord(
                id="exec-fail",
                execution_type="tool_call",
                target="tool",
                success=False,
                error_message="error",
            )
        )

        errors = self.diagnosis.get_recent_errors()
        assert len(errors) == 1
        assert errors[0].success is False

    def test_clear_history(self):
        self.diagnosis.track_execution(
            ExecutionRecord(
                id="exec-001",
                execution_type="tool_call",
                target="tool",
                success=True,
            )
        )
        self.diagnosis.clear_history()
        assert len(self.diagnosis.execution_history) == 0


class TestSelfDiagnosisErrorClassification:
    """SelfDiagnosis 错误分类测试"""

    def setup_method(self):
        self.diagnosis = SelfDiagnosis()

    def test_classify_critical_error(self):
        severity = self.diagnosis._classify_error_severity("timeout after 30s")
        assert severity == DiagnosisSeverity.CRITICAL

    def test_classify_error(self):
        severity = self.diagnosis._classify_error_severity("API call failed")
        assert severity == DiagnosisSeverity.ERROR

    def test_classify_warning(self):
        severity = self.diagnosis._classify_error_severity("Deprecated warning")
        assert severity == DiagnosisSeverity.WARNING

    def test_suggest_fix_timeout(self):
        fix = self.diagnosis._suggest_fix("timeout error")
        assert "超时" in fix

    def test_suggest_fix_connection(self):
        fix = self.diagnosis._suggest_fix("connection refused")
        assert "网络" in fix

    def test_suggest_fix_api_key(self):
        fix = self.diagnosis._suggest_fix("API key invalid")
        assert "API密钥" in fix

    def test_suggest_fix_rate_limit(self):
        fix = self.diagnosis._suggest_fix("rate limit exceeded")
        assert "频率" in fix

    def test_suggest_fix_unknown(self):
        fix = self.diagnosis._suggest_fix("unknown error")
        assert "日志" in fix
