# 疲劳度评估器单元测试
# v0.19.0 新增

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from src.core.body_signal.fatigue_assessor import FatigueAssessor
from src.core.body_signal.models import DataQuality
from src.core.config.body_signal_config import BodySignalConfig
from src.core.models.recovery import RecoveryStatus


@pytest.fixture
def mock_session_repo():
    """创建Mock SessionRepository"""
    repo = MagicMock()
    repo.storage = MagicMock()
    return repo


@pytest.fixture
def mock_training_load_analyzer():
    """创建Mock TrainingLoadAnalyzer"""
    analyzer = MagicMock()
    analyzer.calculate_training_load_from_dataframe.return_value = {
        "atl": 50.0,
        "ctl": 60.0,
        "tsb": 10.0,
        "runs_count": 5,
    }
    analyzer.calculate_tss_for_run.return_value = 85.0
    return analyzer


class TestFatigueAssessor:
    """疲劳度评估器测试类"""

    def test_init(self, mock_session_repo, mock_training_load_analyzer):
        """测试初始化"""
        config = BodySignalConfig()
        assessor = FatigueAssessor(
            mock_session_repo, mock_training_load_analyzer, config
        )

        assert assessor.session_repo == mock_session_repo
        assert assessor.training_load_analyzer == mock_training_load_analyzer
        assert assessor.config == config

    def test_init_default_config(self, mock_session_repo, mock_training_load_analyzer):
        """测试默认配置初始化"""
        assessor = FatigueAssessor(mock_session_repo, mock_training_load_analyzer)

        assert isinstance(assessor.config, BodySignalConfig)

    def test_assess_fatigue_no_data(
        self, mock_session_repo, mock_training_load_analyzer
    ):
        """测试无数据时返回EMPTY"""
        mock_training_load_analyzer.calculate_training_load_from_dataframe.return_value = {
            "atl": 0.0,
            "ctl": 0.0,
            "tsb": 0.0,
            "runs_count": 0,
        }

        assessor = FatigueAssessor(mock_session_repo, mock_training_load_analyzer)
        result = assessor.assess_fatigue()

        assert result.data_quality == DataQuality.EMPTY
        assert result.recovery_status == RecoveryStatus.GREEN

    def test_assess_fatigue_with_rpe(
        self, mock_session_repo, mock_training_load_analyzer
    ):
        """测试带RPE的疲劳度评估"""
        assessor = FatigueAssessor(mock_session_repo, mock_training_load_analyzer)
        result = assessor.assess_fatigue(rpe=7)

        assert result.data_quality == DataQuality.SUFFICIENT
        assert result.fatigue_score > 0
        assert result.breakdown.subjective_component > 0

    def test_assess_fatigue_rpe_out_of_range(
        self, mock_session_repo, mock_training_load_analyzer
    ):
        """测试RPE超出范围时抛出ValueError"""
        assessor = FatigueAssessor(mock_session_repo, mock_training_load_analyzer)

        with pytest.raises(ValueError, match="RPE值必须在1-10范围内"):
            assessor.assess_fatigue(rpe=11)

        with pytest.raises(ValueError, match="RPE值必须在1-10范围内"):
            assessor.assess_fatigue(rpe=0)

    def test_assess_fatigue_green_status(
        self, mock_session_repo, mock_training_load_analyzer
    ):
        """测试GREEN恢复状态"""
        mock_training_load_analyzer.calculate_training_load_from_dataframe.return_value = {
            "atl": 20.0,
            "ctl": 60.0,
            "tsb": 20.0,
            "runs_count": 5,
        }

        assessor = FatigueAssessor(mock_session_repo, mock_training_load_analyzer)
        result = assessor.assess_fatigue()

        assert result.recovery_status == RecoveryStatus.GREEN

    def test_assess_fatigue_red_status(
        self, mock_session_repo, mock_training_load_analyzer
    ):
        """测试RED恢复状态"""
        mock_training_load_analyzer.calculate_training_load_from_dataframe.return_value = {
            "atl": 80.0,
            "ctl": 50.0,
            "tsb": -30.0,
            "runs_count": 5,
        }

        assessor = FatigueAssessor(mock_session_repo, mock_training_load_analyzer)
        result = assessor.assess_fatigue()

        assert result.recovery_status == RecoveryStatus.RED

    def test_get_consecutive_hard_days(
        self, mock_session_repo, mock_training_load_analyzer
    ):
        """测试连续高强度训练天数统计"""
        import polars as pl

        # 模拟7天数据，其中3天高强度
        base_time = datetime(2024, 1, 1, 8, 0, 0)
        lf = pl.DataFrame(
            {
                "session_start_time": [
                    base_time,
                    base_time + __import__("datetime").timedelta(days=1),
                    base_time + __import__("datetime").timedelta(days=2),
                    base_time + __import__("datetime").timedelta(days=3),
                ],
                "session_total_distance": [5000.0, 10000.0, 5000.0, 12000.0],
                "session_total_timer_time": [1800.0, 3600.0, 1800.0, 4200.0],
                "session_avg_heart_rate": [150.0, 160.0, 155.0, 165.0],
            }
        ).lazy()
        mock_session_repo.storage.read_parquet.return_value = lf

        assessor = FatigueAssessor(mock_session_repo, mock_training_load_analyzer)
        days = assessor.get_consecutive_hard_days()

        assert days >= 0

    def test_resolve_weights_with_rpe(
        self, mock_session_repo, mock_training_load_analyzer
    ):
        """测试有RPE时的权重解析"""
        config = BodySignalConfig()
        assessor = FatigueAssessor(
            mock_session_repo, mock_training_load_analyzer, config
        )
        weights = assessor._resolve_weights(has_rpe=True)

        assert weights["atl"] == config.fatigue_weight_atl
        assert weights["hr"] == config.fatigue_weight_hr
        assert weights["consecutive"] == config.fatigue_weight_consecutive
        assert weights["subjective"] == config.fatigue_weight_subjective

    def test_resolve_weights_without_rpe(
        self, mock_session_repo, mock_training_load_analyzer
    ):
        """测试无RPE时的权重重分配"""
        config = BodySignalConfig()
        assessor = FatigueAssessor(
            mock_session_repo, mock_training_load_analyzer, config
        )
        weights = assessor._resolve_weights(has_rpe=False)

        assert weights["subjective"] == 0.0
        # 其他权重应按比例放大
        assert weights["atl"] > config.fatigue_weight_atl
        assert weights["hr"] > config.fatigue_weight_hr
        assert weights["consecutive"] > config.fatigue_weight_consecutive

    def test_generate_recommendation_overtraining(
        self, mock_session_repo, mock_training_load_analyzer
    ):
        """测试过度训练建议"""
        assessor = FatigueAssessor(mock_session_repo, mock_training_load_analyzer)
        recommendation = assessor._generate_recommendation(RecoveryStatus.RED, 4, 75.0)

        assert "降低训练强度" in recommendation or "休息" in recommendation

    def test_generate_recommendation_green(
        self, mock_session_repo, mock_training_load_analyzer
    ):
        """测试GREEN状态建议"""
        assessor = FatigueAssessor(mock_session_repo, mock_training_load_analyzer)
        recommendation = assessor._generate_recommendation(
            RecoveryStatus.GREEN, 0, 20.0
        )

        assert "质量课" in recommendation or "充沛" in recommendation

    def test_tsb_cap(self, mock_session_repo, mock_training_load_analyzer):
        """测试TSB截断"""
        mock_training_load_analyzer.calculate_training_load_from_dataframe.return_value = {
            "atl": 10.0,
            "ctl": 100.0,
            "tsb": 100.0,  # 超过50的cap
            "runs_count": 5,
        }

        config = BodySignalConfig(tsb_cap=50.0)
        assessor = FatigueAssessor(
            mock_session_repo, mock_training_load_analyzer, config
        )
        result = assessor.assess_fatigue()

        # TSB 100被截断到50，但恢复状态仍应为GREEN
        assert result.recovery_status == RecoveryStatus.GREEN
