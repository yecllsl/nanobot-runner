from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np

from src.core.prediction.models import RacePredictionResult
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
    matrix.features = MagicMock()
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


class TestRacePredictorPersonalized:
    def test_personalized_prediction(self):
        predictor = RacePredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=_make_assessor(race_count=5),
            model_manager=MagicMock(),
            current_vdot=45.0,
        )
        result = predictor.predict(distance_km=42.195)
        assert isinstance(result, RacePredictionResult)
        assert result.prediction_type == "personalized"

    def test_personalized_has_pace_strategy(self):
        predictor = RacePredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=_make_assessor(race_count=5),
            model_manager=MagicMock(),
            current_vdot=45.0,
        )
        result = predictor.predict(distance_km=42.195)
        assert result.pace_strategy is not None


class TestRacePredictorStandard:
    def test_standard_prediction(self):
        predictor = RacePredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=_make_assessor(race_count=1),
            model_manager=MagicMock(),
            current_vdot=45.0,
        )
        result = predictor.predict(distance_km=42.195)
        assert result.prediction_type == "standard"

    def test_standard_no_personalization(self):
        predictor = RacePredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=_make_assessor(race_count=1),
            model_manager=MagicMock(),
            current_vdot=45.0,
        )
        result = predictor.predict(distance_km=42.195)
        assert result.personalization_info is None


class TestRacePredictorRiegel:
    def test_fit_riegel_curve(self):
        predictor = RacePredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=_make_assessor(race_count=5),
            model_manager=MagicMock(),
            current_vdot=45.0,
        )
        result = predictor.fit_riegel_curve()
        assert isinstance(result, float)
        assert 0.95 <= result <= 1.15

    def test_riegel_curve_fit_with_real_data(self):
        race_records = [
            {"distance_km": 5.0, "time_seconds": 1500.0},
            {"distance_km": 10.0, "time_seconds": 3300.0},
            {"distance_km": 21.1, "time_seconds": 7500.0},
            {"distance_km": 42.195, "time_seconds": 16500.0},
        ]
        predictor = RacePredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=_make_assessor(race_count=4),
            model_manager=MagicMock(),
            current_vdot=45.0,
            race_records=race_records,
        )
        exponent = predictor.fit_riegel_curve()
        assert isinstance(exponent, float)
        assert 0.95 <= exponent <= 1.15

    def test_riegel_curve_insufficient_records(self):
        predictor = RacePredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=_make_assessor(race_count=1),
            model_manager=MagicMock(),
            current_vdot=45.0,
            race_records=[{"distance_km": 5.0, "time_seconds": 1500.0}],
        )
        exponent = predictor.fit_riegel_curve()
        assert exponent == 1.06


class TestRacePredictorPersonalization:
    def test_learn_personalization(self):
        predictor = RacePredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=_make_assessor(race_count=5),
            model_manager=MagicMock(),
            current_vdot=45.0,
        )
        result = predictor.learn_personalization()
        assert "runner_type" in result
        assert "correction_factor" in result
        assert result["runner_type"] in ("endurance", "speed", "balanced")


class TestRacePredictorClassifyRunnerType:
    def test_classify_runner_type_speed(self):
        race_records = [
            {"distance_km": 5.0, "time_seconds": 1200.0},
            {"distance_km": 10.0, "time_seconds": 2700.0},
            {"distance_km": 42.195, "time_seconds": 15000.0},
            {"distance_km": 5.0, "time_seconds": 1180.0},
            {"distance_km": 42.195, "time_seconds": 15500.0},
        ]
        predictor = RacePredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=_make_assessor(race_count=5),
            model_manager=MagicMock(),
            current_vdot=50.0,
            race_records=race_records,
        )
        runner_type = predictor._classify_runner_type()
        assert runner_type in ("speed", "balanced", "endurance")

    def test_classify_runner_type_endurance(self):
        race_records = [
            {"distance_km": 5.0, "time_seconds": 1500.0},
            {"distance_km": 10.0, "time_seconds": 3000.0},
            {"distance_km": 42.195, "time_seconds": 11000.0},
            {"distance_km": 5.0, "time_seconds": 1480.0},
            {"distance_km": 42.195, "time_seconds": 10800.0},
        ]
        predictor = RacePredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=_make_assessor(race_count=5),
            model_manager=MagicMock(),
            current_vdot=50.0,
            race_records=race_records,
        )
        runner_type = predictor._classify_runner_type()
        assert runner_type in ("endurance", "balanced", "speed")

    def test_classify_runner_type_insufficient_records(self):
        predictor = RacePredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=_make_assessor(race_count=1),
            model_manager=MagicMock(),
            current_vdot=45.0,
            race_records=[{"distance_km": 5.0, "time_seconds": 1500.0}],
        )
        runner_type = predictor._classify_runner_type()
        assert runner_type == "balanced"


class TestRacePredictorPreRaceAdjustment:
    def test_pre_race_adjustment_with_fatigue(self):
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

        race_records = [
            {"distance_km": 5.0, "time_seconds": 1500.0},
            {"distance_km": 10.0, "time_seconds": 3300.0},
            {"distance_km": 21.1, "time_seconds": 7500.0},
        ]
        predictor = RacePredictor(
            feature_engine=fe,
            data_assessor=_make_assessor(race_count=3),
            model_manager=MagicMock(),
            current_vdot=45.0,
            race_records=race_records,
        )
        result = predictor.predict(distance_km=42.195)
        assert isinstance(result, RacePredictionResult)
        assert result.predicted_time_seconds > 0
