from __future__ import annotations

import json
from datetime import datetime
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


def _make_injury_sessions(count: int = 50) -> list[MagicMock]:
    """创建带timestamp的伤病训练session列表"""
    sessions = []
    for i in range(count):
        s = MagicMock()
        s.distance_m = 5000.0 + i * 100
        s.duration_s = 1800.0 + i * 10
        s.tss = 50.0 + i * 2
        s.timestamp = datetime(2026, 3, 1 + (i % 28), 8, 0, 0)
        sessions.append(s)
    return sessions


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

    def test_report_injury_saves_file(self, tmp_path):
        predictor = InjuryPredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=_make_assessor(sufficient=True),
            model_manager=MagicMock(),
            rule_baseline=MagicMock(),
            logistic_model=MagicMock(),
            injury_labels_dir=str(tmp_path / "labels"),
        )
        result = predictor.report_injury(
            injury_type="overuse",
            severity="moderate",
            date="2026-05-08",
        )
        assert result.success is True
        labels_dir = tmp_path / "labels"
        assert labels_dir.exists()
        json_files = list(labels_dir.glob("*.json"))
        assert len(json_files) == 1
        data = json.loads(json_files[0].read_text(encoding="utf-8"))
        assert data["injury_type"] == "overuse"
        assert data["severity"] == "moderate"
        assert data["date"] == "2026-05-08"
        assert data["label_type"] == "confirmed"


class TestInjuryPredictorMLTraining:
    def test_train_lr_gbdt_ensemble(self):
        session_repo = MagicMock()
        session_repo.get_recent_sessions.return_value = _make_injury_sessions(50)
        model_manager = MagicMock()
        predictor = InjuryPredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=_make_assessor(sufficient=True),
            model_manager=model_manager,
            injury_analyzer=MagicMock(),
            rule_baseline=MagicMock(),
            logistic_model=MagicMock(),
            session_repo=session_repo,
        )
        result = predictor.train_model()
        assert result.success is True
        assert result.model_type == "injury_predictor"
        assert result.training_samples > 0
        model_manager.save_model.assert_called_once()
        call_args = model_manager.save_model.call_args[0]
        assert call_args[0] == "injury_predictor"
        saved_models = call_args[1]
        assert "lr" in saved_models
        assert "gbdt" in saved_models

    def test_ensemble_weights(self):
        session_repo = MagicMock()
        session_repo.get_recent_sessions.return_value = _make_injury_sessions(50)
        model_manager = MagicMock()
        predictor = InjuryPredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=_make_assessor(sufficient=True),
            model_manager=model_manager,
            injury_analyzer=MagicMock(),
            rule_baseline=MagicMock(),
            logistic_model=MagicMock(),
            session_repo=session_repo,
        )
        predictor.train_model()
        saved_data = model_manager.save_model.call_args[0][1]
        sample = np.random.randn(1, 8)
        lr_proba = saved_data["lr"].predict_proba(sample)
        gbdt_proba = saved_data["gbdt"].predict_proba(sample)
        ensemble = 0.4 * lr_proba[0, 1] + 0.6 * gbdt_proba[0, 1]
        assert 0.0 <= ensemble <= 1.0

    def test_train_model_insufficient_data(self):
        session_repo = MagicMock()
        session_repo.get_recent_sessions.return_value = _make_injury_sessions(5)
        predictor = InjuryPredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=_make_assessor(sufficient=True),
            model_manager=MagicMock(),
            session_repo=session_repo,
        )
        result = predictor.train_model()
        assert result.success is False
        assert "不足" in result.message

    def test_train_model_no_session_repo(self):
        predictor = InjuryPredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=_make_assessor(sufficient=True),
            model_manager=MagicMock(),
        )
        result = predictor.train_model()
        assert result.success is False


class TestInjuryLabelPersistence:
    def test_injury_label_persistence(self, tmp_path):
        predictor = InjuryPredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=_make_assessor(sufficient=True),
            model_manager=MagicMock(),
            rule_baseline=MagicMock(),
            logistic_model=MagicMock(),
            injury_labels_dir=str(tmp_path / "labels"),
        )
        predictor.report_injury(
            injury_type="overuse", severity="moderate", date="2026-05-08"
        )
        loaded = predictor._load_injury_labels()
        assert "2026-05-08" in loaded

    def test_load_injury_labels_empty_dir(self, tmp_path):
        predictor = InjuryPredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=_make_assessor(sufficient=True),
            model_manager=MagicMock(),
            injury_labels_dir=str(tmp_path / "nonexistent"),
        )
        labels = predictor._load_injury_labels()
        assert isinstance(labels, set)
        assert len(labels) == 0

    def test_load_injury_labels_multiple(self, tmp_path):
        labels_dir = tmp_path / "labels"
        labels_dir.mkdir()
        for i, d in enumerate(["2026-05-01", "2026-05-05", "2026-05-10"]):
            f = labels_dir / f"inj_{d.replace('-', '')}_{i:03d}.json"
            f.write_text(
                json.dumps({"date": d, "injury_type": "overuse"}), encoding="utf-8"
            )
        predictor = InjuryPredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=_make_assessor(sufficient=True),
            model_manager=MagicMock(),
            injury_labels_dir=str(labels_dir),
        )
        loaded = predictor._load_injury_labels()
        assert len(loaded) == 3
        assert "2026-05-01" in loaded
        assert "2026-05-05" in loaded
        assert "2026-05-10" in loaded


class TestInjuryPredictorMLInference:
    def _train_and_get_predictor(self):
        session_repo = MagicMock()
        session_repo.get_recent_sessions.return_value = _make_injury_sessions(50)
        model_manager = MagicMock()
        predictor = InjuryPredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=_make_assessor(sufficient=True),
            model_manager=model_manager,
            injury_analyzer=MagicMock(),
            rule_baseline=MagicMock(),
            logistic_model=MagicMock(),
            session_repo=session_repo,
        )
        predictor.train_model()
        return predictor, model_manager

    def test_ml_inference_with_ensemble_model(self):
        predictor, model_manager = self._train_and_get_predictor()
        saved_data = model_manager.save_model.call_args[0][1]
        sample = np.random.randn(1, 8)
        lr_proba = saved_data["lr"].predict_proba(sample)
        gbdt_proba = saved_data["gbdt"].predict_proba(sample)
        assert lr_proba.shape[1] == 2
        assert gbdt_proba.shape[1] == 2
        ensemble = 0.4 * lr_proba[0, 1] + 0.6 * gbdt_proba[0, 1]
        assert 0.0 <= ensemble <= 1.0

    def test_auto_train_on_first_predict(self):
        session_repo = MagicMock()
        session_repo.get_recent_sessions.return_value = _make_injury_sessions(50)
        model_manager = MagicMock()
        model_manager.get_model_status.return_value = MagicMock(is_available=False)
        model_manager.load_model.return_value = None
        predictor = InjuryPredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=_make_assessor(sufficient=True),
            model_manager=model_manager,
            injury_analyzer=MagicMock(),
            rule_baseline=MagicMock(),
            logistic_model=MagicMock(),
            session_repo=session_repo,
        )
        result = predictor.predict(days=21)
        assert result.prediction_type in ("ml_enhanced", "parametric")

    def test_model_corruption_auto_retrain(self):
        session_repo = MagicMock()
        session_repo.get_recent_sessions.return_value = _make_injury_sessions(50)
        model_manager = MagicMock()
        model_manager.get_model_status.return_value = MagicMock(is_available=True)
        model_manager.load_model.return_value = None
        predictor = InjuryPredictor(
            feature_engine=_make_feature_engine(),
            data_assessor=_make_assessor(sufficient=True),
            model_manager=model_manager,
            injury_analyzer=MagicMock(),
            rule_baseline=MagicMock(),
            logistic_model=MagicMock(),
            session_repo=session_repo,
        )
        result = predictor.predict(days=21)
        assert result.prediction_type in ("ml_enhanced", "parametric")
