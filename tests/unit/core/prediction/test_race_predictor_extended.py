from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np

from src.core.prediction.race_predictor import RacePredictor


def _make_assessor(race_count: int = 5):
    assessor = MagicMock()
    report = MagicMock()
    report.is_sufficient = race_count >= 3
    report.overall_progress_pct = min(100.0, race_count / 3.0 * 100)
    assessor.assess_sufficiency.return_value = report
    return assessor


def _make_feature_engine():
    fe = MagicMock()
    matrix = MagicMock()
    matrix.features = np.array([[45.0, 1.06, 1.0, 0.5, 0.8]])
    matrix.feature_names = [
        "current_vdot",
        "riegel_exponent",
        "correction_factor",
        "pre_race_fatigue",
        "pre_race_recovery",
    ]
    matrix.feature_type = "race"
    fe.extract_race_features.return_value = matrix
    return fe


class TestRacePredictorEstimateCorrectionFactor:
    def test_estimate_correction_factor_no_records(self):
        predictor = RacePredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=_make_assessor(race_count=0),
            model_manager=MagicMock(),
            current_vdot=45.0,
            race_records=[],
        )
        factor = predictor._estimate_correction_factor()
        assert factor == 1.0

    def test_estimate_correction_factor_with_records(self):
        race_records = [
            {"distance_km": 5.0, "time_seconds": 1500.0},
            {"distance_km": 10.0, "time_seconds": 3300.0},
            {"distance_km": 21.1, "time_seconds": 7500.0},
        ]
        predictor = RacePredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=_make_assessor(race_count=3),
            model_manager=MagicMock(),
            current_vdot=45.0,
            race_records=race_records,
        )
        factor = predictor._estimate_correction_factor()
        assert isinstance(factor, float)
        assert factor > 0


class TestRacePredictorPredictStandard:
    def test_predict_standard_no_assessor(self):
        predictor = RacePredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=None,
            model_manager=MagicMock(),
            current_vdot=45.0,
        )
        result = predictor.predict(distance_km=10.0)
        assert result.prediction_type == "standard"
        assert result.predicted_time_seconds > 0

    def test_predict_standard_insufficient_data(self):
        assessor = _make_assessor(race_count=1)
        assessor.assess_sufficiency.return_value = MagicMock(is_sufficient=False)
        predictor = RacePredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=assessor,
            model_manager=MagicMock(),
            current_vdot=45.0,
        )
        result = predictor.predict(distance_km=10.0)
        assert result.prediction_type == "standard"

    def test_predict_personalized_sufficient_data(self):
        assessor = _make_assessor(race_count=5)
        assessor.assess_sufficiency.return_value = MagicMock(is_sufficient=True)
        race_records = [
            {"distance_km": 5.0, "time_seconds": 1500.0},
            {"distance_km": 10.0, "time_seconds": 3300.0},
            {"distance_km": 21.1, "time_seconds": 7500.0},
        ]
        predictor = RacePredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=assessor,
            model_manager=MagicMock(),
            current_vdot=45.0,
            race_records=race_records,
        )
        result = predictor.predict(distance_km=42.195)
        assert result.prediction_type == "personalized"
        assert result.predicted_time_seconds > 0


class TestRacePredictorEstimateRefTime:
    def test_estimate_ref_time_vdot45(self):
        predictor = RacePredictor(current_vdot=45.0)
        ref_time = predictor._estimate_ref_time()
        assert abs(ref_time - 1800.0) < 1.0

    def test_estimate_ref_time_vdot50(self):
        predictor = RacePredictor(current_vdot=50.0)
        ref_time = predictor._estimate_ref_time()
        assert ref_time < 1800.0


class TestRacePredictorClassifyRunnerType:
    def test_classify_balanced(self):
        race_records = [
            {"distance_km": 5.0, "time_seconds": 1500.0},
            {"distance_km": 10.0, "time_seconds": 3300.0},
            {"distance_km": 21.1, "time_seconds": 7500.0},
        ]
        predictor = RacePredictor(current_vdot=45.0, race_records=race_records)
        rtype = predictor._classify_runner_type()
        assert rtype in ("balanced", "endurance", "speed")

    def test_classify_insufficient_records(self):
        predictor = RacePredictor(current_vdot=45.0, race_records=[])
        rtype = predictor._classify_runner_type()
        assert rtype == "balanced"


class TestRacePredictorPaceStrategy:
    def test_generate_pace_strategy_personalized(self):
        assessor = _make_assessor(race_count=5)
        assessor.assess_sufficiency.return_value = MagicMock(is_sufficient=True)
        race_records = [
            {"distance_km": 5.0, "time_seconds": 1500.0},
            {"distance_km": 10.0, "time_seconds": 3300.0},
            {"distance_km": 21.1, "time_seconds": 7500.0},
        ]
        predictor = RacePredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=assessor,
            model_manager=MagicMock(),
            current_vdot=45.0,
            race_records=race_records,
        )
        result = predictor.predict(distance_km=42.195)
        if result.pace_strategy is not None:
            assert len(result.pace_strategy.splits) > 0


class TestRacePredictorPersonalizationExtended:
    def test_learn_personalization_with_records(self):
        race_records = [
            {"distance_km": 5.0, "time_seconds": 1200.0},
            {"distance_km": 10.0, "time_seconds": 2700.0},
            {"distance_km": 21.1, "time_seconds": 6000.0},
            {"distance_km": 42.195, "time_seconds": 13000.0},
            {"distance_km": 5.0, "time_seconds": 1180.0},
        ]
        predictor = RacePredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=_make_assessor(race_count=5),
            model_manager=MagicMock(),
            current_vdot=50.0,
            race_records=race_records,
        )
        result = predictor.learn_personalization()
        assert "runner_type" in result
        assert "correction_factor" in result

    def test_learn_personalization_no_records(self):
        predictor = RacePredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=_make_assessor(race_count=0),
            model_manager=MagicMock(),
            current_vdot=45.0,
            race_records=[],
        )
        result = predictor.learn_personalization()
        assert result["runner_type"] == "balanced"
        assert result["correction_factor"] == 1.0


class TestRacePredictorFitRiegelExtended:
    def test_fit_riegel_curve_with_two_records(self):
        race_records = [
            {"distance_km": 5.0, "time_seconds": 1500.0},
            {"distance_km": 10.0, "time_seconds": 3300.0},
        ]
        predictor = RacePredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=_make_assessor(race_count=2),
            model_manager=MagicMock(),
            current_vdot=45.0,
            race_records=race_records,
        )
        exponent = predictor.fit_riegel_curve()
        assert isinstance(exponent, float)
        assert 0.95 <= exponent <= 1.15

    def test_fit_riegel_curve_with_outlier(self):
        race_records = [
            {"distance_km": 5.0, "time_seconds": 1500.0},
            {"distance_km": 10.0, "time_seconds": 3300.0},
            {"distance_km": 21.1, "time_seconds": 20000.0},
        ]
        predictor = RacePredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=_make_assessor(race_count=3),
            model_manager=MagicMock(),
            current_vdot=45.0,
            race_records=race_records,
        )
        exponent = predictor.fit_riegel_curve()
        assert isinstance(exponent, float)

    def test_fit_riegel_curve_insufficient_records(self):
        predictor = RacePredictor(
            current_vdot=45.0,
            race_records=[{"distance_km": 5.0, "time_seconds": 1500.0}],
        )
        exponent = predictor.fit_riegel_curve()
        assert exponent == 1.06
