from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.core.prediction.data_assessor import DataAssessor
from src.core.prediction.models import PredictionStatusReport


class TestDataAssessorVDOT:
    def test_sufficient(self):
        repo = MagicMock()
        repo.get_total_session_count.return_value = 500
        repo.get_data_span_months.return_value = 24.0
        assessor = DataAssessor(session_repo=repo)
        report = assessor.assess_sufficiency("vdot")
        assert report.is_sufficient is True
        assert report.prediction_type == "vdot"

    def test_parametric_range(self):
        repo = MagicMock()
        repo.get_total_session_count.return_value = 250
        repo.get_data_span_months.return_value = 20.0
        assessor = DataAssessor(session_repo=repo)
        report = assessor.assess_sufficiency("vdot")
        assert report.is_sufficient is False
        assert report.overall_progress_pct > 50.0

    def test_insufficient(self):
        repo = MagicMock()
        repo.get_total_session_count.return_value = 50
        repo.get_data_span_months.return_value = 5.0
        assessor = DataAssessor(session_repo=repo)
        report = assessor.assess_sufficiency("vdot")
        assert report.is_sufficient is False
        assert report.overall_progress_pct < 50.0


class TestDataAssessorRace:
    def test_sufficient(self):
        repo = MagicMock()
        repo.get_race_session_count.return_value = 5
        assessor = DataAssessor(session_repo=repo)
        report = assessor.assess_sufficiency("race")
        assert report.is_sufficient is True

    def test_insufficient(self):
        repo = MagicMock()
        repo.get_race_session_count.return_value = 1
        assessor = DataAssessor(session_repo=repo)
        report = assessor.assess_sufficiency("race")
        assert report.is_sufficient is False


class TestDataAssessorInjury:
    def test_sufficient(self):
        repo = MagicMock()
        repo.get_total_session_count.return_value = 400
        repo.get_data_span_months.return_value = 18.0
        repo.get_hr_completeness.return_value = 0.8
        assessor = DataAssessor(session_repo=repo)
        report = assessor.assess_sufficiency("injury")
        assert report.is_sufficient is True

    def test_insufficient(self):
        repo = MagicMock()
        repo.get_total_session_count.return_value = 50
        repo.get_data_span_months.return_value = 5.0
        repo.get_hr_completeness.return_value = 0.2
        assessor = DataAssessor(session_repo=repo)
        report = assessor.assess_sufficiency("injury")
        assert report.is_sufficient is False


class TestDataAssessorFullStatus:
    def test_get_full_status(self):
        repo = MagicMock()
        repo.get_total_session_count.return_value = 500
        repo.get_data_span_months.return_value = 24.0
        repo.get_race_session_count.return_value = 5
        repo.get_hr_completeness.return_value = 0.8
        assessor = DataAssessor(session_repo=repo)
        status = assessor.get_full_status()
        assert isinstance(status, PredictionStatusReport)
        assert status.vdot_status.is_sufficient is True
        assert status.race_status.is_sufficient is True
        assert status.injury_status.is_sufficient is True


class TestDataAssessorAdvice:
    def test_get_accumulation_advice_vdot(self):
        repo = MagicMock()
        repo.get_total_session_count.return_value = 100
        repo.get_data_span_months.return_value = 10.0
        assessor = DataAssessor(session_repo=repo)
        advice = assessor.get_accumulation_advice("vdot")
        assert isinstance(advice, list)
        assert len(advice) > 0


class TestDataAssessorEdgeCases:
    def test_unknown_prediction_type(self):
        repo = MagicMock()
        assessor = DataAssessor(session_repo=repo)
        with pytest.raises(ValueError, match="未知的预测类型"):
            assessor.assess_sufficiency("unknown")

    def test_repo_method_not_exists(self):
        repo = MagicMock(spec=[])
        assessor = DataAssessor(session_repo=repo)
        report = assessor.assess_sufficiency("vdot")
        assert report.is_sufficient is False

    def test_repo_method_raises_exception(self):
        repo = MagicMock()
        repo.get_total_session_count.side_effect = RuntimeError("db error")
        assessor = DataAssessor(session_repo=repo)
        report = assessor.assess_sufficiency("vdot")
        assert report.is_sufficient is False
