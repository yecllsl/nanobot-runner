# 诊断数据模型单元测试

from datetime import datetime

from src.core.diagnosis.models import (
    DiagnosisCategory,
    DiagnosisReport,
    DiagnosisSeverity,
    ExecutionRecord,
    SuggestionContext,
    ValidationResult,
    ValidationStatus,
)


class TestSuggestionContext:
    """SuggestionContext 测试"""

    def test_create_with_defaults(self):
        ctx = SuggestionContext(
            user_query="今天适合跑步吗",
            suggestion_text="建议今天进行轻松跑",
        )
        assert ctx.user_query == "今天适合跑步吗"
        assert ctx.suggestion_text == "建议今天进行轻松跑"
        assert ctx.tools_used == []
        assert ctx.memory_referenced == []
        assert isinstance(ctx.timestamp, datetime)

    def test_create_with_all_fields(self):
        ctx = SuggestionContext(
            user_query="查询",
            suggestion_text="建议",
            tools_used=["get_running_stats"],
            memory_referenced=["用户偏好晨跑"],
            timestamp=datetime(2026, 1, 1),
            session_key="test_session",
        )
        assert ctx.tools_used == ["get_running_stats"]
        assert ctx.memory_referenced == ["用户偏好晨跑"]
        assert ctx.session_key == "test_session"


class TestValidationResult:
    """ValidationResult 测试"""

    def test_create_pass_result(self):
        result = ValidationResult(
            rule_name="completeness_check",
            status=ValidationStatus.PASS,
            message="建议长度正常",
        )
        assert result.rule_name == "completeness_check"
        assert result.status == ValidationStatus.PASS
        assert result.severity == DiagnosisSeverity.INFO

    def test_create_fail_result(self):
        result = ValidationResult(
            rule_name="safety_check",
            status=ValidationStatus.FAIL,
            message="建议包含不安全内容",
            severity=DiagnosisSeverity.ERROR,
            suggestion_fix="建议移除不安全内容",
        )
        assert result.status == ValidationStatus.FAIL
        assert result.severity == DiagnosisSeverity.ERROR
        assert result.suggestion_fix == "建议移除不安全内容"


class TestDiagnosisReport:
    """DiagnosisReport 测试"""

    def test_create_report(self):
        results = [
            ValidationResult(
                rule_name="check1",
                status=ValidationStatus.PASS,
                message="通过",
            ),
            ValidationResult(
                rule_name="check2",
                status=ValidationStatus.FAIL,
                message="失败",
                severity=DiagnosisSeverity.ERROR,
            ),
        ]
        report = DiagnosisReport(
            id="test-001",
            category=DiagnosisCategory.SUGGESTION_QUALITY,
            results=results,
            summary="1通过, 1失败",
            overall_status=ValidationStatus.FAIL,
        )
        assert report.id == "test-001"
        assert report.category == DiagnosisCategory.SUGGESTION_QUALITY
        assert len(report.results) == 2

    def test_has_errors(self):
        report = DiagnosisReport(
            id="test-002",
            category=DiagnosisCategory.SUGGESTION_QUALITY,
            results=[
                ValidationResult(
                    rule_name="check1",
                    status=ValidationStatus.FAIL,
                    message="失败",
                    severity=DiagnosisSeverity.ERROR,
                ),
            ],
            overall_status=ValidationStatus.FAIL,
        )
        assert report.has_errors is True

    def test_has_no_errors(self):
        report = DiagnosisReport(
            id="test-003",
            category=DiagnosisCategory.SUGGESTION_QUALITY,
            results=[
                ValidationResult(
                    rule_name="check1",
                    status=ValidationStatus.PASS,
                    message="通过",
                ),
            ],
            overall_status=ValidationStatus.PASS,
        )
        assert report.has_errors is False

    def test_has_warnings(self):
        report = DiagnosisReport(
            id="test-004",
            category=DiagnosisCategory.SUGGESTION_QUALITY,
            results=[
                ValidationResult(
                    rule_name="check1",
                    status=ValidationStatus.WARNING,
                    message="警告",
                    severity=DiagnosisSeverity.WARNING,
                ),
            ],
            overall_status=ValidationStatus.WARNING,
        )
        assert report.has_warnings is True

    def test_pass_fail_counts(self):
        results = [
            ValidationResult(rule_name="c1", status=ValidationStatus.PASS, message=""),
            ValidationResult(rule_name="c2", status=ValidationStatus.PASS, message=""),
            ValidationResult(rule_name="c3", status=ValidationStatus.FAIL, message=""),
        ]
        report = DiagnosisReport(
            id="test-005",
            category=DiagnosisCategory.SUGGESTION_QUALITY,
            results=results,
        )
        assert report.pass_count == 2
        assert report.fail_count == 1

    def test_to_dict(self):
        report = DiagnosisReport(
            id="test-006",
            category=DiagnosisCategory.EXECUTION_HEALTH,
            results=[],
            summary="测试",
            overall_status=ValidationStatus.PASS,
            timestamp=datetime(2026, 1, 1),
        )
        d = report.to_dict()
        assert d["id"] == "test-006"
        assert d["category"] == "execution_health"
        assert d["overall_status"] == "pass"


class TestExecutionRecord:
    """ExecutionRecord 测试"""

    def test_create_success_record(self):
        record = ExecutionRecord(
            id="exec-001",
            execution_type="tool_call",
            target="get_running_stats",
            success=True,
            duration_ms=150,
        )
        assert record.success is True
        assert record.duration_ms == 150
        assert record.error_message is None

    def test_create_failure_record(self):
        record = ExecutionRecord(
            id="exec-002",
            execution_type="tool_call",
            target="invalid_tool",
            success=False,
            duration_ms=50,
            error_message="工具不存在",
        )
        assert record.success is False
        assert record.error_message == "工具不存在"

    def test_to_dict(self):
        record = ExecutionRecord(
            id="exec-003",
            execution_type="suggestion",
            target="training_plan",
            success=True,
            timestamp=datetime(2026, 1, 1),
        )
        d = record.to_dict()
        assert d["id"] == "exec-003"
        assert d["execution_type"] == "suggestion"
        assert d["success"] is True


class TestEnums:
    """枚举类型测试"""

    def test_diagnosis_severity_values(self):
        assert DiagnosisSeverity.INFO.value == "info"
        assert DiagnosisSeverity.WARNING.value == "warning"
        assert DiagnosisSeverity.ERROR.value == "error"
        assert DiagnosisSeverity.CRITICAL.value == "critical"

    def test_diagnosis_category_values(self):
        assert DiagnosisCategory.SUGGESTION_QUALITY.value == "suggestion_quality"
        assert DiagnosisCategory.PARAMETER_VALIDITY.value == "parameter_validity"
        assert DiagnosisCategory.EXECUTION_HEALTH.value == "execution_health"

    def test_validation_status_values(self):
        assert ValidationStatus.PASS.value == "pass"
        assert ValidationStatus.FAIL.value == "fail"
        assert ValidationStatus.WARNING.value == "warning"
        assert ValidationStatus.SKIPPED.value == "skipped"
