from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import MagicMock

import numpy as np

from src.core.prediction.injury_predictor import InjuryPredictor
from src.core.prediction.models import RiskFactor


def _make_assessor(sufficient: bool, parametric: bool = False):
    assessor = MagicMock()
    report = MagicMock()
    report.is_sufficient = sufficient
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


def _make_injury_sessions(count: int = 50) -> list[MagicMock]:
    sessions = []
    for i in range(count):
        s = MagicMock()
        s.distance_m = 5000.0 + i * 100
        s.duration_s = 1800.0 + i * 10
        s.tss = 50.0 + i * 2
        s.avg_heart_rate = 150 + i
        s.timestamp = datetime(2026, 3, 1 + (i % 28), 8, 0, 0)
        sessions.append(s)
    return sessions


class TestInjuryPredictorGetAcwr:
    def test_get_acwr_with_analyzer_float(self):
        analyzer = MagicMock()
        analyzer.calculate_acwr.return_value = 1.3
        predictor = InjuryPredictor(injury_analyzer=analyzer)
        result = predictor._get_acwr()
        assert result == 1.3

    def test_get_acwr_with_analyzer_dict(self):
        analyzer = MagicMock()
        analyzer.calculate_acwr.return_value = {"acwr": 1.5}
        predictor = InjuryPredictor(injury_analyzer=analyzer)
        result = predictor._get_acwr()
        assert result == 1.5

    def test_get_acwr_no_analyzer(self):
        predictor = InjuryPredictor()
        result = predictor._get_acwr()
        assert result == 1.2

    def test_get_acwr_exception(self):
        analyzer = MagicMock()
        analyzer.calculate_acwr.side_effect = Exception("error")
        predictor = InjuryPredictor(injury_analyzer=analyzer)
        result = predictor._get_acwr()
        assert result == 1.2


class TestInjuryPredictorGetWeeklyLoadChange:
    def test_get_weekly_load_change_with_sessions(self):
        session_repo = MagicMock()
        sessions = []
        for i in range(20):
            s = MagicMock()
            s.tss = 50.0 + i * 5
            sessions.append(s)
        session_repo.get_recent_sessions.return_value = sessions
        predictor = InjuryPredictor(session_repo=session_repo)
        result = predictor._get_weekly_load_change()
        assert isinstance(result, float)

    def test_get_weekly_load_change_no_repo(self):
        predictor = InjuryPredictor()
        result = predictor._get_weekly_load_change()
        assert result == 10.0

    def test_get_weekly_load_change_exception(self):
        session_repo = MagicMock()
        session_repo.get_recent_sessions.side_effect = Exception("error")
        predictor = InjuryPredictor(session_repo=session_repo)
        result = predictor._get_weekly_load_change()
        assert result == 10.0


class TestInjuryPredictorGetTsbLowDays:
    def test_get_tsb_low_days_with_analyzer(self):
        analyzer = MagicMock()
        analyzer.get_tsb_low_days.return_value = 5
        predictor = InjuryPredictor(injury_analyzer=analyzer)
        result = predictor._get_tsb_low_days()
        assert result == 5

    def test_get_tsb_low_days_no_analyzer(self):
        predictor = InjuryPredictor()
        result = predictor._get_tsb_low_days()
        assert result == 2

    def test_get_tsb_low_days_exception(self):
        analyzer = MagicMock()
        analyzer.get_tsb_low_days.side_effect = Exception("error")
        predictor = InjuryPredictor(injury_analyzer=analyzer)
        result = predictor._get_tsb_low_days()
        assert result == 2


class TestInjuryPredictorGetHrDeviation:
    def test_get_hr_deviation_with_analyzer(self):
        analyzer = MagicMock()
        analyzer.get_resting_hr_deviation.return_value = 7.5
        predictor = InjuryPredictor(injury_analyzer=analyzer)
        result = predictor._get_hr_deviation()
        assert result == 7.5

    def test_get_hr_deviation_no_analyzer(self):
        predictor = InjuryPredictor()
        result = predictor._get_hr_deviation()
        assert result == 5.0


class TestInjuryPredictorGetFatigueScore:
    def test_get_fatigue_score_with_analyzer(self):
        analyzer = MagicMock()
        analyzer.get_fatigue_score.return_value = 60.0
        predictor = InjuryPredictor(injury_analyzer=analyzer)
        result = predictor._get_fatigue_score()
        assert result == 60.0

    def test_get_fatigue_score_no_analyzer(self):
        predictor = InjuryPredictor()
        result = predictor._get_fatigue_score()
        assert result == 40.0


class TestInjuryPredictorGetRiskFactors:
    def test_get_risk_factors_low_risk(self):
        predictor = InjuryPredictor()
        factors = predictor._get_risk_factors(acwr=1.1, ensemble_proba=0.2)
        assert isinstance(factors, list)
        assert len(factors) == 3
        for f in factors:
            assert isinstance(f, RiskFactor)
            assert f.name in ("acwr", "training_monotony", "resting_hr_deviation")

    def test_get_risk_factors_high_risk(self):
        predictor = InjuryPredictor()
        factors = predictor._get_risk_factors(acwr=1.6, ensemble_proba=0.5)
        assert isinstance(factors, list)
        assert len(factors) == 3
        acwr_factor = [f for f in factors if f.name == "acwr"][0]
        assert acwr_factor.direction == "increasing"


class TestInjuryPredictorScoreToLevel:
    def test_score_to_level_low(self):
        predictor = InjuryPredictor()
        assert predictor._score_to_level(20.0) == "low"

    def test_score_to_level_medium(self):
        predictor = InjuryPredictor()
        assert predictor._score_to_level(50.0) == "medium"

    def test_score_to_level_high(self):
        predictor = InjuryPredictor()
        assert predictor._score_to_level(80.0) == "high"

    def test_score_to_level_boundary(self):
        predictor = InjuryPredictor()
        assert predictor._score_to_level(25.0) == "medium"
        assert predictor._score_to_level(75.0) == "high"


class TestInjuryPredictorRecommendations:
    def test_recommendations_low(self):
        predictor = InjuryPredictor()
        recs = predictor._generate_recommendations("low")
        assert len(recs) == 1
        assert "合理" in recs[0]

    def test_recommendations_medium(self):
        predictor = InjuryPredictor()
        recs = predictor._generate_recommendations("medium")
        assert len(recs) == 1
        assert "降低" in recs[0]

    def test_recommendations_high(self):
        predictor = InjuryPredictor()
        recs = predictor._generate_recommendations("high")
        assert len(recs) == 1
        assert "休息" in recs[0]


class TestInjuryPredictorRiskTimeline:
    def test_generate_risk_timeline(self):
        predictor = InjuryPredictor()
        timeline = predictor._generate_risk_timeline(0.3, 21)
        assert len(timeline) == 3
        for tp in timeline:
            assert tp.days_ahead in (7, 14, 21)
            assert 0.0 <= tp.risk_probability <= 1.0

    def test_generate_risk_timeline_short_days(self):
        predictor = InjuryPredictor()
        timeline = predictor._generate_risk_timeline(0.3, 10)
        assert len(timeline) == 1
        assert timeline[0].days_ahead == 7


class TestInjuryPredictorSynthesizeLabels:
    def test_synthesize_labels_single_class(self):
        predictor = InjuryPredictor()
        X = np.random.randn(50, 8)
        y = np.zeros(50)
        new_y = predictor._synthesize_labels(X, y)
        assert len(np.unique(new_y)) >= 2

    def test_synthesize_labels_already_two_classes(self):
        predictor = InjuryPredictor()
        X = np.random.randn(50, 8)
        y = np.array([0] * 25 + [1] * 25)
        new_y = predictor._synthesize_labels(X, y)
        assert len(np.unique(new_y)) >= 2


class TestInjuryPredictorBuildTrainingData:
    def test_build_training_data_no_feature_engine(self):
        predictor = InjuryPredictor()
        X, y = predictor._build_training_data(_make_injury_sessions(10))
        assert X.shape[0] == 0
        assert len(y) == 0

    def test_build_training_data_with_injury_labels(self, tmp_path):
        labels_dir = tmp_path / "labels"
        labels_dir.mkdir()
        label_data = {
            "injury_id": "inj_001",
            "injury_type": "overuse",
            "severity": "moderate",
            "date": "2026-03-05",
        }
        (labels_dir / "inj_001.json").write_text(
            json.dumps(label_data), encoding="utf-8"
        )
        fe = _make_feature_engine()
        predictor = InjuryPredictor(
            feature_engine=fe,
            injury_labels_dir=str(labels_dir),
        )
        sessions = _make_injury_sessions(10)
        X, y = predictor._build_training_data(sessions)
        assert X.shape[0] > 0

    def test_build_training_data_high_hr_flagged(self):
        fe = _make_feature_engine()
        sessions = []
        for i in range(10):
            s = MagicMock()
            s.distance_m = 25000.0
            s.duration_s = 7200.0
            s.avg_heart_rate = 175.0
            s.timestamp = datetime(2026, 3, 1 + i, 8, 0, 0)
            sessions.append(s)
        predictor = InjuryPredictor(feature_engine=fe)
        X, y = predictor._build_training_data(sessions)
        assert X.shape[0] > 0
        assert 1 in y


class TestInjuryPredictorPredictBasicEdgeCases:
    def test_basic_prediction_rule_failure(self):
        rule_baseline = MagicMock()
        rule_baseline.assess.side_effect = Exception("rule error")
        predictor = InjuryPredictor(
            data_assessor=_make_assessor(sufficient=False, parametric=False),
            rule_baseline=rule_baseline,
        )
        result = predictor.predict(days=21)
        assert result.prediction_type == "basic"
        assert result.risk_level == "low"

    def test_basic_prediction_with_advice(self):
        rule_baseline = MagicMock()
        rule_baseline.assess.return_value = {
            "risk_level": "low",
            "risk_score": 20.0,
            "advice": "保持训练",
        }
        predictor = InjuryPredictor(
            data_assessor=_make_assessor(sufficient=False, parametric=False),
            rule_baseline=rule_baseline,
        )
        result = predictor.predict(days=21)
        assert result.prediction_type == "basic"
        assert len(result.recommendations) > 0


class TestInjuryPredictorParametricEdgeCases:
    def test_parametric_prediction_failure(self):
        fe = MagicMock()
        fe.extract_injury_features.side_effect = Exception("feature error")
        logistic = MagicMock()
        logistic.predict_proba.side_effect = Exception("model error")
        predictor = InjuryPredictor(
            feature_engine=fe,
            data_assessor=_make_assessor(sufficient=False, parametric=True),
            logistic_model=logistic,
        )
        result = predictor.predict(days=21)
        assert result.prediction_type == "parametric"
        assert result.risk_score == 30.0


class TestInjuryPredictorSaveLabel:
    def test_save_injury_label_failure(self, tmp_path):
        predictor = InjuryPredictor(
            injury_labels_dir="/nonexistent/path/that/cannot/be/created",
        )
        predictor._save_injury_label("inj_001", "overuse", "moderate", "2026-05-08")
