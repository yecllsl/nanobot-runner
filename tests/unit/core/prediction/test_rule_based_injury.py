from __future__ import annotations

from src.core.prediction.baselines.rule_based_injury import RuleBasedInjuryBaseline


class TestRuleBasedInjuryLowRisk:
    def test_low_risk(self):
        baseline = RuleBasedInjuryBaseline()
        result = baseline.assess(
            acwr=1.1,
            training_monotony=1.5,
            consecutive_hard_days=1,
            resting_hr_deviation_pct=3.0,
        )
        assert result["risk_level"] == "low"
        assert result["risk_score"] < 25


class TestRuleBasedInjuryMediumRisk:
    def test_medium_risk(self):
        baseline = RuleBasedInjuryBaseline()
        result = baseline.assess(
            acwr=1.4,
            training_monotony=1.8,
            consecutive_hard_days=3,
            resting_hr_deviation_pct=8.0,
        )
        assert result["risk_level"] == "medium"
        assert 25 <= result["risk_score"] < 75


class TestRuleBasedInjuryHighRisk:
    def test_high_risk(self):
        baseline = RuleBasedInjuryBaseline()
        result = baseline.assess(
            acwr=2.2,
            training_monotony=2.8,
            consecutive_hard_days=7,
            resting_hr_deviation_pct=20.0,
        )
        assert result["risk_level"] == "high"
        assert result["risk_score"] >= 75


class TestRuleBasedInjuryBoundary:
    def test_acwr_boundary_at_1_5(self):
        baseline = RuleBasedInjuryBaseline()
        result = baseline.assess(
            acwr=1.5,
            training_monotony=1.0,
            consecutive_hard_days=0,
            resting_hr_deviation_pct=0.0,
        )
        assert "acwr" in result["risk_factors"]
