from __future__ import annotations

from datetime import datetime

import pytest

from src.core.evolution.calibration_engine import CalibrationEngine
from src.core.evolution.config import EvolutionConfig
from src.core.evolution.evolution_store import EvolutionStore
from src.core.evolution.models import CalibrationProfile


class TestCalibrationEngine:
    """CalibrationEngine 校准引擎测试"""

    def test_run_calibration_insufficient_data(self, tmp_path):
        store = EvolutionStore(tmp_path)
        config = EvolutionConfig(calibration_min_samples=10)
        engine = CalibrationEngine(store, config)
        with pytest.raises(ValueError, match="校准数据不足"):
            engine.run_calibration("vdot")

    def test_run_calibration_overestimate(self, tmp_path):
        store = EvolutionStore(tmp_path)
        engine = CalibrationEngine(store, EvolutionConfig(calibration_min_samples=3))
        override_pairs = [(48.0, 45.0), (47.0, 44.5), (49.0, 46.0)]
        report = engine.run_calibration("vdot", override_pairs=override_pairs)
        assert report.direction == "overestimate"
        assert report.scale_after < 1.0
        assert report.sample_count == 3

    def test_run_calibration_underestimate(self, tmp_path):
        store = EvolutionStore(tmp_path)
        engine = CalibrationEngine(store, EvolutionConfig(calibration_min_samples=3))
        override_pairs = [(42.0, 45.0), (43.0, 46.0), (41.0, 44.0)]
        report = engine.run_calibration("vdot", override_pairs=override_pairs)
        assert report.direction == "underestimate"
        assert report.scale_after > 1.0

    def test_run_calibration_accurate(self, tmp_path):
        store = EvolutionStore(tmp_path)
        engine = CalibrationEngine(store, EvolutionConfig(calibration_min_samples=3))
        override_pairs = [(45.0, 45.1), (44.0, 44.2), (46.0, 45.8)]
        report = engine.run_calibration("vdot", override_pairs=override_pairs)
        assert report.direction == "none"

    def test_apply_calibration(self, tmp_path):
        store = EvolutionStore(tmp_path)
        engine = CalibrationEngine(store)
        profile = CalibrationProfile(
            model_type="vdot",
            scale=0.95,
            last_updated=datetime(2026, 5, 20, 10, 0, 0),
            sample_count=10,
        )
        store.save_calibration_profile(profile)
        corrected = engine.apply_calibration("vdot", 46.0)
        assert abs(corrected - 46.0 * 0.95) < 0.01

    def test_get_profile_default(self, tmp_path):
        store = EvolutionStore(tmp_path)
        engine = CalibrationEngine(store)
        profile = engine.get_profile("vdot")
        assert profile.model_type == "vdot"
        assert profile.scale == 1.0

    def test_reset_calibration(self, tmp_path):
        store = EvolutionStore(tmp_path)
        profile = CalibrationProfile(
            model_type="vdot",
            scale=0.9,
            last_updated=datetime(2026, 5, 20, 10, 0, 0),
            sample_count=10,
        )
        store.save_calibration_profile(profile)
        engine = CalibrationEngine(store)
        reset_profile = engine.reset_calibration("vdot")
        assert reset_profile.scale == 1.0
        assert reset_profile.sample_count == 0

    def test_enforce_amplitude_limit(self, tmp_path):
        store = EvolutionStore(tmp_path)
        engine = CalibrationEngine(store)
        assert engine._enforce_amplitude_limit(0.85) == 0.9
        assert engine._enforce_amplitude_limit(1.15) == 1.1
        assert engine._enforce_amplitude_limit(1.0) == 1.0

    def test_update_params_ema(self, tmp_path):
        store = EvolutionStore(tmp_path)
        engine = CalibrationEngine(store, EvolutionConfig(calibration_alpha=0.7))
        result = engine._update_params_ema(1.0, 0.9)
        assert abs(result - 0.93) < 0.001

    def test_detect_bias_overestimate(self, tmp_path):
        store = EvolutionStore(tmp_path)
        engine = CalibrationEngine(store)
        direction, magnitude = engine._detect_bias(
            [(48.0, 45.0), (47.0, 44.0), (49.0, 46.0)]
        )
        assert direction == "overestimate"
        assert magnitude > 0.05

    def test_detect_bias_underestimate(self, tmp_path):
        store = EvolutionStore(tmp_path)
        engine = CalibrationEngine(store)
        direction, magnitude = engine._detect_bias(
            [(42.0, 45.0), (43.0, 46.0), (41.0, 44.0)]
        )
        assert direction == "underestimate"
        assert magnitude > 0.05

    def test_detect_bias_accurate(self, tmp_path):
        store = EvolutionStore(tmp_path)
        engine = CalibrationEngine(store)
        direction, magnitude = engine._detect_bias(
            [(45.0, 45.1), (44.0, 44.1), (46.0, 45.9)]
        )
        assert direction == "none"
