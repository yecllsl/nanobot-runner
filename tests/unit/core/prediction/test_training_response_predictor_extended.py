from __future__ import annotations

from unittest.mock import MagicMock

from src.core.prediction.baselines.banister_ir import BanisterIRModel
from src.core.prediction.training_response_predictor import TrainingResponsePredictor


class TestTrainingResponsePredictorTSB:
    def test_get_current_tsb_with_analyzer(self):
        analyzer = MagicMock()
        analyzer.get_ctl.return_value = 65.0
        analyzer.get_atl.return_value = 55.0
        predictor = TrainingResponsePredictor(
            banister_model=BanisterIRModel(),
            base_vdot=45.0,
            training_load_analyzer=analyzer,
        )
        result = predictor._get_current_tsb()
        assert result == 10.0

    def test_get_current_tsb_no_analyzer(self):
        predictor = TrainingResponsePredictor(
            banister_model=BanisterIRModel(),
            base_vdot=45.0,
        )
        result = predictor._get_current_tsb()
        assert result == 0.0

    def test_get_current_tsb_exception(self):
        analyzer = MagicMock()
        analyzer.get_ctl.side_effect = Exception("error")
        predictor = TrainingResponsePredictor(
            banister_model=BanisterIRModel(),
            base_vdot=45.0,
            training_load_analyzer=analyzer,
        )
        result = predictor._get_current_tsb()
        assert result == 0.0


class TestTrainingResponsePredictorRecentTss:
    def test_get_recent_tss_7d_with_repo(self):
        session_repo = MagicMock()
        sessions = []
        for i in range(5):
            s = MagicMock()
            s.tss = 50.0 + i * 10
            sessions.append(s)
        session_repo.get_recent_sessions.return_value = sessions
        predictor = TrainingResponsePredictor(
            banister_model=BanisterIRModel(),
            base_vdot=45.0,
            session_repo=session_repo,
        )
        result = predictor._get_recent_tss_7d()
        assert result > 0

    def test_get_recent_tss_7d_no_repo(self):
        predictor = TrainingResponsePredictor(
            banister_model=BanisterIRModel(),
            base_vdot=45.0,
        )
        result = predictor._get_recent_tss_7d()
        assert result == 0.0

    def test_get_recent_tss_7d_exception(self):
        session_repo = MagicMock()
        session_repo.get_recent_sessions.side_effect = Exception("error")
        predictor = TrainingResponsePredictor(
            banister_model=BanisterIRModel(),
            base_vdot=45.0,
            session_repo=session_repo,
        )
        result = predictor._get_recent_tss_7d()
        assert result == 0.0


class TestTrainingResponsePredictorSessionTypes:
    def test_long_run(self):
        predictor = TrainingResponsePredictor(
            banister_model=BanisterIRModel(),
            base_vdot=45.0,
        )
        result = predictor.predict(
            session_type="long",
            duration_min=120,
            intensity="moderate",
        )
        assert result.session_type == "long"
        assert result.predicted_recovery_hours > 0

    def test_recovery_run(self):
        predictor = TrainingResponsePredictor(
            banister_model=BanisterIRModel(),
            base_vdot=45.0,
        )
        result = predictor.predict(
            session_type="recovery",
            duration_min=30,
            intensity="very_low",
        )
        assert result.session_type == "recovery"
        assert result.predicted_recovery_hours < 24

    def test_tempo_run(self):
        predictor = TrainingResponsePredictor(
            banister_model=BanisterIRModel(),
            base_vdot=45.0,
        )
        result = predictor.predict(
            session_type="tempo",
            duration_min=45,
            intensity="moderate",
        )
        assert result.session_type == "tempo"
        assert result.predicted_recovery_hours > 0


class TestTrainingResponsePredictorTSBAdjustment:
    def test_high_tsb_positive_adjustment(self):
        analyzer = MagicMock()
        analyzer.get_ctl.return_value = 65.0
        analyzer.get_atl.return_value = 45.0
        predictor = TrainingResponsePredictor(
            banister_model=BanisterIRModel(),
            base_vdot=45.0,
            training_load_analyzer=analyzer,
        )
        result = predictor.predict(
            session_type="easy",
            duration_min=45,
            intensity="low",
        )
        assert result.predicted_recovery_hours > 0

    def test_low_tsb_negative_adjustment(self):
        analyzer = MagicMock()
        analyzer.get_ctl.return_value = 40.0
        analyzer.get_atl.return_value = 60.0
        predictor = TrainingResponsePredictor(
            banister_model=BanisterIRModel(),
            base_vdot=45.0,
            training_load_analyzer=analyzer,
        )
        result = predictor.predict(
            session_type="easy",
            duration_min=45,
            intensity="low",
        )
        assert result.predicted_recovery_hours > 0


class TestTrainingResponsePredictorDurationIntensity:
    def test_short_low_intensity(self):
        predictor = TrainingResponsePredictor(
            banister_model=BanisterIRModel(),
            base_vdot=45.0,
        )
        result = predictor.predict(
            session_type="easy",
            duration_min=20,
            intensity="very_low",
        )
        assert result.predicted_fatigue_impact < 10

    def test_long_high_intensity(self):
        predictor = TrainingResponsePredictor(
            banister_model=BanisterIRModel(),
            base_vdot=45.0,
        )
        result = predictor.predict(
            session_type="interval",
            duration_min=90,
            intensity="very_high",
        )
        assert result.predicted_fatigue_impact > 10
        assert result.predicted_recovery_hours > 24
