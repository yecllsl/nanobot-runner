from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np

from src.core.prediction.injury_predictor import InjuryPredictor
from src.core.prediction.models import InjuryRiskPrediction


def _make_assessor(sufficient: bool, parametric: bool = False):
    assessor = MagicMock()
    report = MagicMock()
    report.is_sufficient = sufficient
    report.overall_progress_pct = 90.0 if sufficient else (60.0 if parametric else 30.0)
    total_dim = MagicMock()
    total_dim.name = "total_records"
    total_dim.current_value = 400.0 if sufficient else (150.0 if parametric else 30.0)
    report.dimensions = [total_dim]
    assessor.assess_sufficiency.return_value = report
    return assessor


def _make_feature_engine():
    fe = MagicMock()
    matrix = MagicMock()
    matrix.features = np.random.randn(1, 8)
    matrix.feature_names = [f"f{i}" for i in range(8)]
    matrix.feature_type = "injury"
    fe.extract_injury_features.return_value = matrix
    return fe


class TestInjuryPredictorMLEnhanced:
    def test_ml_enhanced_prediction(self):
        predictor = InjuryPredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=_make_assessor(sufficient=True),
            model_manager=MagicMock(),
            rule_baseline=MagicMock(),
            logistic_model=MagicMock(),
        )
        result = predictor.predict(days=21)
        assert isinstance(result, InjuryRiskPrediction)
        assert result.prediction_type == "ml_enhanced"

    def test_ml_enhanced_has_risk_timeline(self):
        predictor = InjuryPredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=_make_assessor(sufficient=True),
            model_manager=MagicMock(),
            rule_baseline=MagicMock(),
            logistic_model=MagicMock(),
        )
        result = predictor.predict(days=21)
        assert len(result.risk_timeline) > 0


class TestInjuryPredictorParametric:
    def test_parametric_prediction(self):
        logistic = MagicMock()
        logistic.predict_proba.return_value = np.array([0.4])
        predictor = InjuryPredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=_make_assessor(sufficient=False, parametric=True),
            model_manager=MagicMock(),
            rule_baseline=MagicMock(),
            logistic_model=logistic,
        )
        result = predictor.predict(days=21)
        assert result.prediction_type == "parametric"


class TestInjuryPredictorBasic:
    def test_basic_prediction(self):
        rule_baseline = MagicMock()
        rule_baseline.assess.return_value = {
            "risk_level": "low",
            "risk_score": 20.0,
            "risk_factors": [],
            "dimension_scores": {},
            "advice": "训练负荷合理",
        }
        predictor = InjuryPredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=_make_assessor(sufficient=False, parametric=False),
            model_manager=MagicMock(),
            rule_baseline=rule_baseline,
            logistic_model=MagicMock(),
        )
        result = predictor.predict(days=21)
        assert result.prediction_type == "basic"
        assert result.risk_level == "low"


class TestInjuryPredictorReportInjury:
    def test_report_injury(self):
        predictor = InjuryPredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=_make_assessor(sufficient=True),
            model_manager=MagicMock(),
            rule_baseline=MagicMock(),
            logistic_model=MagicMock(),
        )
        result = predictor.report_injury(
            injury_type="overuse",
            severity="moderate",
            date="2026-05-08",
        )
        assert result.success is True
        assert result.injury_type == "overuse"
