from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

from src.core.evolution.calibration_engine import CalibrationEngine
from src.core.evolution.config import EvolutionConfig
from src.core.evolution.evolution_store import EvolutionStore
from src.core.evolution.model_evolver import ModelEvolver
from src.core.evolution.models import CalibrationProfile


class TestModelEvolver:
    """ModelEvolver 模型进化器测试"""

    def test_evolve_vdot_model_overestimate(self, tmp_path):
        store = EvolutionStore(tmp_path)
        config = EvolutionConfig(calibration_min_samples=3)
        calibration_engine = CalibrationEngine(store, config)
        evolver = ModelEvolver(calibration_engine, store, config=config)
        override_pairs = [(48.0, 45.0), (47.0, 44.5), (49.0, 46.0)]
        with patch.object(
            store, "get_prediction_actual_pairs", return_value=override_pairs
        ):
            result = evolver.evolve_vdot_model()
        assert result.model_type == "vdot"
        assert len(result.parameter_changes) > 0
        tau_change = next(
            (c for c in result.parameter_changes if c.name == "tau_fitness"), None
        )
        assert tau_change is not None
        assert tau_change.new_value > tau_change.old_value

    def test_evolve_vdot_model_underestimate(self, tmp_path):
        store = EvolutionStore(tmp_path)
        config = EvolutionConfig(calibration_min_samples=3)
        calibration_engine = CalibrationEngine(store, config)
        evolver = ModelEvolver(calibration_engine, store, config=config)
        override_pairs = [(42.0, 45.0), (43.0, 46.0), (41.0, 44.0)]
        with patch.object(
            store, "get_prediction_actual_pairs", return_value=override_pairs
        ):
            result = evolver.evolve_vdot_model()
        tau_change = next(
            (c for c in result.parameter_changes if c.name == "tau_fitness"), None
        )
        assert tau_change is not None
        assert tau_change.new_value < tau_change.old_value

    def test_evolve_injury_model(self, tmp_path):
        store = EvolutionStore(tmp_path)
        config = EvolutionConfig(calibration_min_samples=3)
        calibration_engine = CalibrationEngine(store, config)
        evolver = ModelEvolver(calibration_engine, store, config=config)
        override_pairs = [(0.6, 0.3), (0.7, 0.2), (0.5, 0.4)]
        with patch.object(
            store, "get_prediction_actual_pairs", return_value=override_pairs
        ):
            result = evolver.evolve_injury_model()
        assert result.model_type == "injury"

    def test_evolve_training_response_model(self, tmp_path):
        store = EvolutionStore(tmp_path)
        config = EvolutionConfig(calibration_min_samples=3)
        calibration_engine = CalibrationEngine(store, config)
        evolver = ModelEvolver(calibration_engine, store, config=config)
        override_pairs = [(0.5, 0.3), (0.4, 0.2), (0.6, 0.4)]
        with patch.object(
            store, "get_prediction_actual_pairs", return_value=override_pairs
        ):
            result = evolver.evolve_training_response_model()
        assert result.model_type == "training_response"

    def test_evolve_no_calibration_data(self, tmp_path):
        store = EvolutionStore(tmp_path)
        config = EvolutionConfig(calibration_min_samples=100)
        calibration_engine = CalibrationEngine(store, config)
        evolver = ModelEvolver(calibration_engine, store, config=config)
        result = evolver.evolve_vdot_model()
        assert result.parameter_changes == []
        assert result.mae_before == 0.0
        assert result.mae_after == 0.0

    def test_adjust_banister_params_overestimate(self, tmp_path):
        store = EvolutionStore(tmp_path)
        calibration_engine = CalibrationEngine(store)
        evolver = ModelEvolver(calibration_engine, store)
        profile = CalibrationProfile(
            model_type="vdot",
            scale=0.93,
            last_updated=datetime(2026, 5, 20, 10, 0, 0),
            sample_count=15,
        )
        changes = evolver._adjust_banister_params(profile)
        assert len(changes) > 0
        tau_change = next(c for c in changes if c.name == "tau_fitness")
        assert tau_change.new_value == 42.0 + 2.0
        k1_change = next(c for c in changes if c.name == "k1")
        assert abs(k1_change.new_value - 0.0038 * 0.95) < 0.0001

    def test_adjust_banister_params_underestimate(self, tmp_path):
        store = EvolutionStore(tmp_path)
        calibration_engine = CalibrationEngine(store)
        evolver = ModelEvolver(calibration_engine, store)
        profile = CalibrationProfile(
            model_type="vdot",
            scale=1.07,
            last_updated=datetime(2026, 5, 20, 10, 0, 0),
            sample_count=15,
        )
        changes = evolver._adjust_banister_params(profile)
        tau_change = next(c for c in changes if c.name == "tau_fitness")
        assert tau_change.new_value == 42.0 - 2.0
        k1_change = next(c for c in changes if c.name == "k1")
        assert abs(k1_change.new_value - 0.0038 * 1.05) < 0.0001

    def test_parameter_change_within_5pct(self, tmp_path):
        store = EvolutionStore(tmp_path)
        calibration_engine = CalibrationEngine(store)
        evolver = ModelEvolver(calibration_engine, store)
        profile = CalibrationProfile(
            model_type="vdot",
            scale=0.93,
            last_updated=datetime(2026, 5, 20, 10, 0, 0),
            sample_count=15,
        )
        changes = evolver._adjust_banister_params(profile)
        for change in changes:
            assert abs(change.change_pct) <= 5.0

    def test_params_persisted_after_evolution(self, tmp_path):
        store = EvolutionStore(tmp_path)
        config = EvolutionConfig(calibration_min_samples=3)
        calibration_engine = CalibrationEngine(store, config)
        evolver = ModelEvolver(calibration_engine, store, config=config)
        override_pairs = [(48.0, 45.0), (47.0, 44.5), (49.0, 46.0)]
        with patch.object(
            store, "get_prediction_actual_pairs", return_value=override_pairs
        ):
            evolver.evolve_vdot_model()
        params = store.load_model_params("vdot")
        assert params is not None
        assert "tau_fitness" in params
