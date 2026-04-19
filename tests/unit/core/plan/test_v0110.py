# v0.11.0 单元测试
# 覆盖 PlanAdjustmentValidator / PromptTemplateEngine / PlanAdjustment / PlanSuggestion

from unittest.mock import MagicMock

import pytest

from src.core.models import PlanAdjustment, PlanExecutionStats, PlanSuggestion
from src.core.plan.plan_adjustment_validator import (
    PlanAdjustmentValidator,
    RulePriority,
    ValidationRule,
)
from src.core.plan.prompt_template_engine import (
    PromptTemplateEngine,
    TemplateNotFoundError,
)


class TestPlanAdjustment:
    """PlanAdjustment 数据模型测试"""

    def test_create_valid_adjustment(self):
        adj = PlanAdjustment(
            adjustment_type="volume",
            original_value=1.0,
            adjusted_value=0.8,
            reason="减量周",
            confidence=0.7,
        )
        assert adj.adjustment_type == "volume"
        assert adj.confidence == 0.7

    def test_invalid_confidence_too_high(self):
        with pytest.raises(ValueError, match="confidence"):
            PlanAdjustment(
                adjustment_type="volume",
                original_value=1.0,
                adjusted_value=0.8,
                reason="test",
                confidence=1.5,
            )

    def test_invalid_confidence_negative(self):
        with pytest.raises(ValueError, match="confidence"):
            PlanAdjustment(
                adjustment_type="volume",
                original_value=1.0,
                adjusted_value=0.8,
                reason="test",
                confidence=-0.1,
            )

    def test_invalid_adjustment_type(self):
        with pytest.raises(ValueError, match="adjustment_type"):
            PlanAdjustment(
                adjustment_type="invalid_type",
                original_value=1.0,
                adjusted_value=0.8,
                reason="test",
                confidence=0.5,
            )

    def test_to_dict(self):
        adj = PlanAdjustment(
            adjustment_type="intensity",
            original_value=5,
            adjusted_value=3,
            reason="降低强度",
            confidence=0.85,
        )
        d = adj.to_dict()
        assert d["adjustment_type"] == "intensity"
        assert d["confidence"] == 0.85
        assert d["reason"] == "降低强度"

    def test_all_valid_types(self):
        for adj_type in ("volume", "intensity", "type", "date"):
            adj = PlanAdjustment(
                adjustment_type=adj_type,
                original_value=1.0,
                adjusted_value=0.8,
                reason="test",
                confidence=0.5,
            )
            assert adj.adjustment_type == adj_type


class TestPlanSuggestion:
    """PlanSuggestion 数据模型测试"""

    def test_create_valid_suggestion(self):
        s = PlanSuggestion(
            suggestion_type="training",
            suggestion_content="增加有氧基础训练",
            priority="high",
            context="VDOT偏低",
            confidence=0.8,
        )
        assert s.suggestion_type == "training"
        assert s.priority == "high"

    def test_invalid_confidence(self):
        with pytest.raises(ValueError, match="confidence"):
            PlanSuggestion(
                suggestion_type="training",
                suggestion_content="test",
                priority="high",
                context="test",
                confidence=2.0,
            )

    def test_invalid_priority(self):
        with pytest.raises(ValueError, match="priority"):
            PlanSuggestion(
                suggestion_type="training",
                suggestion_content="test",
                priority="urgent",
                context="test",
                confidence=0.5,
            )

    def test_to_dict(self):
        s = PlanSuggestion(
            suggestion_type="recovery",
            suggestion_content="增加恢复日",
            priority="medium",
            context="疲劳累积",
            confidence=0.65,
        )
        d = s.to_dict()
        assert d["suggestion_type"] == "recovery"
        assert d["priority"] == "medium"
        assert d["confidence"] == 0.65

    def test_all_valid_priorities(self):
        for priority in ("high", "medium", "low"):
            s = PlanSuggestion(
                suggestion_type="training",
                suggestion_content="test",
                priority=priority,
                context="test",
                confidence=0.5,
            )
            assert s.priority == priority


class TestPlanAdjustmentValidator:
    """PlanAdjustmentValidator 规则引擎测试"""

    def setup_method(self):
        self.validator = PlanAdjustmentValidator()

    def test_default_rules_loaded(self):
        rules = self.validator.get_rules()
        assert len(rules) == 5
        rule_names = [r.name for r in rules]
        assert "volume_increase_limit" in rule_names
        assert "long_run_ratio" in rule_names
        assert "recovery_after_interval" in rule_names
        assert "race_taper" in rule_names
        assert "easy_day_intensity" in rule_names

    def test_validate_volume_increase_within_limit(self):
        adj = PlanAdjustment(
            adjustment_type="volume",
            original_value=100.0,
            adjusted_value=108.0,
            reason="小幅加量",
            confidence=0.7,
        )
        result = self.validator.validate(adj)
        assert result.passed is True

    def test_validate_volume_increase_exceeds_limit(self):
        adj = PlanAdjustment(
            adjustment_type="volume",
            original_value=100.0,
            adjusted_value=115.0,
            reason="大幅加量",
            confidence=0.7,
        )
        result = self.validator.validate(adj)
        assert result.passed is False
        violation_msgs = [v.message for v in result.violations]
        assert any("10%" in msg for msg in violation_msgs)

    def test_validate_volume_increase_zero_original(self):
        adj = PlanAdjustment(
            adjustment_type="volume",
            original_value=0.0,
            adjusted_value=50.0,
            reason="从零开始",
            confidence=0.5,
        )
        result = self.validator.validate(adj)
        assert result.passed is True

    def test_validate_non_volume_type_passes_all(self):
        adj = PlanAdjustment(
            adjustment_type="type",
            original_value="interval",
            adjusted_value="easy",
            reason="改为轻松跑",
            confidence=0.6,
        )
        result = self.validator.validate(adj)
        assert result.passed is True

    def test_validate_intensity_high_value(self):
        adj = PlanAdjustment(
            adjustment_type="intensity",
            original_value=5,
            adjusted_value=9,
            reason="高强度间歇",
            confidence=0.7,
        )
        result = self.validator.validate(adj)
        assert result.passed is False

    def test_validate_intensity_moderate_value(self):
        adj = PlanAdjustment(
            adjustment_type="intensity",
            original_value=5,
            adjusted_value=4,
            reason="适度降低",
            confidence=0.7,
        )
        result = self.validator.validate(adj)
        assert result.passed is True

    def test_add_custom_rule(self):
        custom_rule = ValidationRule(
            name="custom_rule",
            description="自定义规则",
            priority=RulePriority.LOW,
            check=lambda _: True,
            violation_message="自定义规则违反",
        )
        self.validator.add_rule(custom_rule)
        rules = self.validator.get_rules()
        assert len(rules) == 6
        assert any(r.name == "custom_rule" for r in rules)

    def test_remove_rule(self):
        removed = self.validator.remove_rule("easy_day_intensity")
        assert removed is True
        rules = self.validator.get_rules()
        assert len(rules) == 4
        assert all(r.name != "easy_day_intensity" for r in rules)

    def test_remove_nonexistent_rule(self):
        removed = self.validator.remove_rule("nonexistent")
        assert removed is False

    def test_enable_disable_rule(self):
        self.validator.enable_rule("easy_day_intensity", False)
        rules = self.validator.get_rules()
        easy_rule = next(r for r in rules if r.name == "easy_day_intensity")
        assert easy_rule.enabled is False

        self.validator.enable_rule("easy_day_intensity", True)
        easy_rule = next(r for r in rules if r.name == "easy_day_intensity")
        assert easy_rule.enabled is True

    def test_enable_nonexistent_rule(self):
        result = self.validator.enable_rule("nonexistent", False)
        assert result is False

    def test_get_default_adjustment_reduce(self):
        adj = self.validator.get_default_adjustment("下周减量")
        assert adj.adjustment_type == "volume"
        assert adj.adjusted_value == 0.8
        assert adj.confidence == 0.7

    def test_get_default_adjustment_increase(self):
        adj = self.validator.get_default_adjustment("加量训练")
        assert adj.adjustment_type == "volume"
        assert adj.adjusted_value == 1.1
        assert adj.confidence == 0.6

    def test_get_default_adjustment_unknown(self):
        adj = self.validator.get_default_adjustment("随便调整")
        assert adj.confidence == 0.0

    def test_validate_disabled_rule_skipped(self):
        self.validator.enable_rule("volume_increase_limit", False)
        adj = PlanAdjustment(
            adjustment_type="volume",
            original_value=100.0,
            adjusted_value=150.0,
            reason="大幅加量",
            confidence=0.7,
        )
        result = self.validator.validate(adj)
        volume_violations = [v for v in result.violations if "10%" in v.message]
        assert len(volume_violations) == 0


class TestPromptTemplateEngine:
    """PromptTemplateEngine 测试"""

    def setup_method(self):
        self.engine = PromptTemplateEngine()

    def test_default_templates_loaded(self):
        names = self.engine.get_template_names()
        assert "adjust_plan" in names
        assert "get_suggestion" in names

    def test_render_adjust_plan(self):
        mock_user_ctx = MagicMock()
        mock_user_ctx.to_dict.return_value = {"fitness_level": "intermediate"}
        stats = PlanExecutionStats(
            plan_id="plan_test",
            total_planned_days=28,
            completed_days=20,
            completion_rate=0.71,
            avg_effort_score=5.5,
            total_distance_km=150.0,
            total_duration_min=900,
            avg_hr=145,
            avg_hr_drift=2.5,
        )
        prompt = self.engine.render(
            "adjust_plan",
            user_context=mock_user_ctx,
            execution_stats=stats,
            adjustment_request="下周减量20%",
        )
        assert "下周减量20%" in prompt
        assert "intermediate" in prompt
        assert "plan_test" in prompt

    def test_render_get_suggestion(self):
        mock_user_ctx = MagicMock()
        mock_user_ctx.to_dict.return_value = {"fitness_level": "beginner"}
        stats = PlanExecutionStats(
            plan_id="plan_test",
            total_planned_days=14,
            completed_days=10,
            completion_rate=0.71,
            avg_effort_score=6.0,
            total_distance_km=80.0,
            total_duration_min=500,
            avg_hr=140,
            avg_hr_drift=3.0,
        )
        prompt = self.engine.render(
            "get_suggestion",
            user_context=mock_user_ctx,
            execution_stats=stats,
        )
        assert "beginner" in prompt
        assert "plan_test" in prompt

    def test_render_without_context(self):
        prompt = self.engine.render(
            "adjust_plan",
            adjustment_request="减量",
        )
        assert "减量" in prompt
        assert "{}" in prompt

    def test_render_nonexistent_template(self):
        with pytest.raises(TemplateNotFoundError, match="nonexistent"):
            self.engine.render("nonexistent")

    def test_add_custom_template(self):
        self.engine.add_template("custom", "Hello {name}!")
        prompt = self.engine.render("custom", name="Runner")
        assert prompt == "Hello Runner!"

    def test_remove_template(self):
        removed = self.engine.remove_template("adjust_plan")
        assert removed is True
        assert "adjust_plan" not in self.engine.get_template_names()

    def test_remove_nonexistent_template(self):
        removed = self.engine.remove_template("nonexistent")
        assert removed is False
