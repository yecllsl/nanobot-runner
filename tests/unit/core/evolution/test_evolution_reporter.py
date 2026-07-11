# EvolutionReporter 单元测试
# 覆盖月度进化报告生成的全部方法

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from src.core.evolution.config import EvolutionConfig
from src.core.evolution.evolution_reporter import EvolutionReporter
from src.core.evolution.models import CalibrationProfile, PromptTuningParams


@pytest.fixture
def mock_store() -> MagicMock:
    """创建 mock EvolutionStore"""
    store = MagicMock()
    store.count_decisions.return_value = 42
    store.get_prediction_actual_pairs.return_value = [(45.0, 44.5), (46.0, 45.8)]
    store.get_decision_outcome_pairs.return_value = []
    store.load_calibration_profile.return_value = None
    store.load_trigger_state.return_value = None
    return store


@pytest.fixture
def mock_calibration_engine() -> MagicMock:
    """创建 mock CalibrationEngine"""
    return MagicMock()


@pytest.fixture
def mock_prompt_tuner() -> MagicMock:
    """创建 mock PromptTuner，默认返回中性参数"""
    tuner = MagicMock()
    tuner.get_params.return_value = PromptTuningParams.default()
    return tuner


@pytest.fixture
def config() -> EvolutionConfig:
    """创建测试用 EvolutionConfig"""
    return EvolutionConfig()


@pytest.fixture
def reporter(
    mock_store: MagicMock,
    mock_calibration_engine: MagicMock,
    mock_prompt_tuner: MagicMock,
    config: EvolutionConfig,
) -> EvolutionReporter:
    """创建测试用 EvolutionReporter"""
    return EvolutionReporter(
        store=mock_store,
        calibration_engine=mock_calibration_engine,
        prompt_tuner=mock_prompt_tuner,
        config=config,
    )


class TestGenerateReport:
    """generate_report 方法测试"""

    def test_generate_report_default_month_returns_report(
        self, reporter: EvolutionReporter
    ):
        """默认月份应返回当月报告"""
        report = reporter.generate_report()
        expected_month = datetime.now().strftime("%Y-%m")
        assert report.month == expected_month

    def test_generate_report_specified_month_returns_report(
        self, reporter: EvolutionReporter
    ):
        """指定月份应返回对应报告"""
        report = reporter.generate_report(month="2026-05")
        assert report.month == "2026-05"

    def test_generate_report_saves_trigger_state(
        self, reporter: EvolutionReporter, mock_store: MagicMock
    ):
        """生成报告后应保存 trigger_state 标记"""
        reporter.generate_report(month="2026-06")
        mock_store.save_trigger_state.assert_called_once_with(
            "last_monthly_report", "2026-06"
        )

    def test_generate_report_contains_total_decisions(
        self, reporter: EvolutionReporter, mock_store: MagicMock
    ):
        """报告应包含决策总数"""
        mock_store.count_decisions.return_value = 100
        report = reporter.generate_report()
        assert report.total_decisions == 100

    def test_generate_report_report_id_starts_with_rpt(
        self, reporter: EvolutionReporter
    ):
        """报告 ID 应以 rpt_ 开头"""
        report = reporter.generate_report()
        assert report.report_id.startswith("rpt_")

    def test_generate_report_generated_at_is_datetime(
        self, reporter: EvolutionReporter
    ):
        """报告生成时间应为 datetime 类型"""
        report = reporter.generate_report()
        assert isinstance(report.generated_at, datetime)


class TestGetPersonalizationDegree:
    """_get_personalization_degree 方法测试"""

    def test_default_params_returns_zero(self, reporter: EvolutionReporter):
        """默认参数（全0.5）应返回 0.0"""
        degree = reporter._get_personalization_degree()
        assert degree == 0.0

    def test_customized_params_returns_positive(
        self, reporter: EvolutionReporter, mock_prompt_tuner: MagicMock
    ):
        """自定义参数应返回正的个性化程度"""
        mock_prompt_tuner.get_params.return_value = PromptTuningParams(
            tone_intensity=0.8,
            detail_level_score=0.3,
            recommendation_aggressiveness=0.7,
            data_driven_weight=0.6,
        )
        degree = reporter._get_personalization_degree()
        assert degree > 0.0

    def test_fully_customized_params_returns_max(
        self, reporter: EvolutionReporter, mock_prompt_tuner: MagicMock
    ):
        """全极端参数应返回接近 0.5 的个性化程度"""
        mock_prompt_tuner.get_params.return_value = PromptTuningParams(
            tone_intensity=1.0,
            detail_level_score=1.0,
            recommendation_aggressiveness=1.0,
            data_driven_weight=1.0,
        )
        degree = reporter._get_personalization_degree()
        assert degree == 0.5

    def test_params_none_returns_zero(
        self, reporter: EvolutionReporter, mock_prompt_tuner: MagicMock
    ):
        """get_params 返回 None 应返回 0.0"""
        mock_prompt_tuner.get_params.return_value = None
        degree = reporter._get_personalization_degree()
        assert degree == 0.0

    def test_get_params_exception_returns_zero(
        self, reporter: EvolutionReporter, mock_prompt_tuner: MagicMock
    ):
        """get_params 抛异常应返回 0.0"""
        mock_prompt_tuner.get_params.side_effect = RuntimeError("test error")
        degree = reporter._get_personalization_degree()
        assert degree == 0.0


class TestGetPredictionAccuracyTrend:
    """_get_prediction_accuracy_trend 方法测试"""

    def test_with_pairs_returns_trend(
        self, reporter: EvolutionReporter, mock_store: MagicMock
    ):
        """有预测配对时应返回趋势数据"""
        mock_store.get_prediction_actual_pairs.return_value = [(45.0, 44.5)]
        trend = reporter._get_prediction_accuracy_trend()
        assert len(trend) == 1
        assert "date" in trend[0]
        assert "mae" in trend[0]
        assert "sample_count" in trend[0]

    def test_with_no_pairs_returns_empty(
        self, reporter: EvolutionReporter, mock_store: MagicMock
    ):
        """无预测配对时应返回空列表"""
        mock_store.get_prediction_actual_pairs.return_value = []
        trend = reporter._get_prediction_accuracy_trend()
        assert trend == []

    def test_exception_returns_empty(
        self, reporter: EvolutionReporter, mock_store: MagicMock
    ):
        """异常时应返回空列表"""
        mock_store.get_prediction_actual_pairs.side_effect = RuntimeError("db error")
        trend = reporter._get_prediction_accuracy_trend()
        assert trend == []


class TestGetDecisionAcceptanceRate:
    """_get_decision_acceptance_rate 方法测试"""

    def test_no_pairs_returns_zero(
        self, reporter: EvolutionReporter, mock_store: MagicMock
    ):
        """无配对应返回 0.0"""
        mock_store.get_decision_outcome_pairs.return_value = []
        rate = reporter._get_decision_acceptance_rate()
        assert rate == 0.0

    def test_all_accepted_returns_one(
        self, reporter: EvolutionReporter, mock_store: MagicMock
    ):
        """全部接受应返回 1.0"""
        outcome1 = MagicMock()
        outcome1.recommendation_accepted = True
        outcome2 = MagicMock()
        outcome2.recommendation_accepted = True
        mock_store.get_decision_outcome_pairs.return_value = [
            (MagicMock(), outcome1),
            (MagicMock(), outcome2),
        ]
        rate = reporter._get_decision_acceptance_rate()
        assert rate == 1.0

    def test_half_accepted_returns_half(
        self, reporter: EvolutionReporter, mock_store: MagicMock
    ):
        """一半接受应返回 0.5"""
        outcome1 = MagicMock()
        outcome1.recommendation_accepted = True
        outcome2 = MagicMock()
        outcome2.recommendation_accepted = False
        mock_store.get_decision_outcome_pairs.return_value = [
            (MagicMock(), outcome1),
            (MagicMock(), outcome2),
        ]
        rate = reporter._get_decision_acceptance_rate()
        assert rate == 0.5

    def test_exception_returns_zero(
        self, reporter: EvolutionReporter, mock_store: MagicMock
    ):
        """异常时应返回 0.0"""
        mock_store.get_decision_outcome_pairs.side_effect = RuntimeError("error")
        rate = reporter._get_decision_acceptance_rate()
        assert rate == 0.0


class TestGetModelVersions:
    """_get_model_versions 方法测试"""

    def test_no_profiles_returns_empty(
        self, reporter: EvolutionReporter, mock_store: MagicMock
    ):
        """无校准配置应返回空字典"""
        mock_store.load_calibration_profile.return_value = None
        versions = reporter._get_model_versions()
        assert versions == {}

    def test_with_profiles_returns_versions(
        self, reporter: EvolutionReporter, mock_store: MagicMock
    ):
        """有校准配置应返回版本信息"""
        profile = CalibrationProfile(model_type="vdot", scale=0.95)
        mock_store.load_calibration_profile.side_effect = lambda t: (
            profile if t == "vdot" else None
        )
        versions = reporter._get_model_versions()
        assert "vdot" in versions
        assert "scale=0.950" in versions["vdot"]

    def test_exception_returns_empty(
        self, reporter: EvolutionReporter, mock_store: MagicMock
    ):
        """异常时应返回空字典"""
        mock_store.load_calibration_profile.side_effect = RuntimeError("error")
        versions = reporter._get_model_versions()
        assert versions == {}


class TestGetEvolutionActionsCount:
    """_get_evolution_actions_count 方法测试"""

    def test_no_state_returns_zero(
        self, reporter: EvolutionReporter, mock_store: MagicMock
    ):
        """无状态应返回 0"""
        mock_store.load_trigger_state.return_value = None
        count = reporter._get_evolution_actions_count()
        assert count == 0

    def test_integer_state_returns_value(
        self, reporter: EvolutionReporter, mock_store: MagicMock
    ):
        """整数状态应返回对应值"""
        mock_store.load_trigger_state.return_value = 5
        count = reporter._get_evolution_actions_count()
        assert count == 5

    def test_float_state_returns_int(
        self, reporter: EvolutionReporter, mock_store: MagicMock
    ):
        """浮点状态应返回整数"""
        mock_store.load_trigger_state.return_value = 3.0
        count = reporter._get_evolution_actions_count()
        assert count == 3

    def test_string_state_returns_zero(
        self, reporter: EvolutionReporter, mock_store: MagicMock
    ):
        """字符串状态应返回 0"""
        mock_store.load_trigger_state.return_value = "invalid"
        count = reporter._get_evolution_actions_count()
        assert count == 0

    def test_exception_returns_zero(
        self, reporter: EvolutionReporter, mock_store: MagicMock
    ):
        """异常时应返回 0"""
        mock_store.load_trigger_state.side_effect = RuntimeError("error")
        count = reporter._get_evolution_actions_count()
        assert count == 0


class TestGetLastEvolutionTime:
    """_get_last_evolution_time 方法测试"""

    def test_no_state_returns_none(
        self, reporter: EvolutionReporter, mock_store: MagicMock
    ):
        """无状态应返回 None"""
        mock_store.load_trigger_state.return_value = None
        result = reporter._get_last_evolution_time()
        assert result is None

    def test_valid_iso_string_returns_datetime(
        self, reporter: EvolutionReporter, mock_store: MagicMock
    ):
        """有效 ISO 字符串应返回 datetime"""
        mock_store.load_trigger_state.return_value = "2026-06-15T10:30:00"
        result = reporter._get_last_evolution_time()
        assert isinstance(result, datetime)
        assert result.year == 2026
        assert result.month == 6

    def test_non_string_returns_none(
        self, reporter: EvolutionReporter, mock_store: MagicMock
    ):
        """非字符串状态应返回 None"""
        mock_store.load_trigger_state.return_value = 12345
        result = reporter._get_last_evolution_time()
        assert result is None

    def test_exception_returns_none(
        self, reporter: EvolutionReporter, mock_store: MagicMock
    ):
        """异常时应返回 None"""
        mock_store.load_trigger_state.side_effect = RuntimeError("error")
        result = reporter._get_last_evolution_time()
        assert result is None


class TestGetCalibrationSummary:
    """_get_calibration_summary 方法测试"""

    def test_no_profiles_returns_empty(
        self, reporter: EvolutionReporter, mock_store: MagicMock
    ):
        """无校准配置应返回空字典"""
        mock_store.load_calibration_profile.return_value = None
        summary = reporter._get_calibration_summary()
        assert summary == {}

    def test_with_profiles_returns_summary(
        self, reporter: EvolutionReporter, mock_store: MagicMock
    ):
        """有校准配置应返回摘要"""
        profile = CalibrationProfile(model_type="vdot", scale=0.95)
        mock_store.load_calibration_profile.side_effect = lambda t: (
            profile if t == "vdot" else None
        )
        summary = reporter._get_calibration_summary()
        assert "vdot" in summary
        assert summary["vdot"]["scale"] == 0.95

    def test_exception_returns_empty(
        self, reporter: EvolutionReporter, mock_store: MagicMock
    ):
        """异常时应返回空字典"""
        mock_store.load_calibration_profile.side_effect = RuntimeError("error")
        summary = reporter._get_calibration_summary()
        assert summary == {}


class TestGetPromptTuningSummary:
    """_get_prompt_tuning_summary 方法测试"""

    def test_with_params_returns_dict(
        self, reporter: EvolutionReporter, mock_prompt_tuner: MagicMock
    ):
        """有参数时应返回字典"""
        summary = reporter._get_prompt_tuning_summary()
        assert isinstance(summary, dict)
        assert "tone_intensity" in summary

    def test_params_none_returns_empty(
        self, reporter: EvolutionReporter, mock_prompt_tuner: MagicMock
    ):
        """参数为 None 应返回空字典"""
        mock_prompt_tuner.get_params.return_value = None
        summary = reporter._get_prompt_tuning_summary()
        assert summary == {}

    def test_exception_returns_empty(
        self, reporter: EvolutionReporter, mock_prompt_tuner: MagicMock
    ):
        """异常时应返回空字典"""
        mock_prompt_tuner.get_params.side_effect = RuntimeError("error")
        summary = reporter._get_prompt_tuning_summary()
        assert summary == {}


class TestGenerateRecommendations:
    """_generate_recommendations 方法测试"""

    def test_low_personalization_suggests_data_accumulation(
        self, reporter: EvolutionReporter
    ):
        """低个性化程度应建议增加数据积累"""
        recs = reporter._generate_recommendations(
            personalization_degree=0.05, acceptance_rate=0.8, accuracy_trend=[]
        )
        assert any("数据积累" in r for r in recs)

    def test_low_acceptance_suggests_strategy_adjustment(
        self, reporter: EvolutionReporter
    ):
        """低接受率应建议调整策略"""
        recs = reporter._generate_recommendations(
            personalization_degree=0.5, acceptance_rate=0.3, accuracy_trend=[]
        )
        assert any("推荐策略" in r for r in recs)

    def test_high_mae_suggests_calibration(self, reporter: EvolutionReporter):
        """高预测误差应建议增加校准频率"""
        recs = reporter._generate_recommendations(
            personalization_degree=0.5,
            acceptance_rate=0.8,
            accuracy_trend=[{"mae": 0.1}],
        )
        assert any("校准频率" in r for r in recs)

    def test_good_status_suggests_continue(self, reporter: EvolutionReporter):
        """良好状态应建议继续积累数据"""
        recs = reporter._generate_recommendations(
            personalization_degree=0.5, acceptance_rate=0.8, accuracy_trend=[]
        )
        assert any("继续积累" in r for r in recs)

    def test_multiple_issues_returns_multiple_recommendations(
        self, reporter: EvolutionReporter
    ):
        """多个问题应返回多条建议"""
        recs = reporter._generate_recommendations(
            personalization_degree=0.05,
            acceptance_rate=0.3,
            accuracy_trend=[{"mae": 0.1}],
        )
        assert len(recs) >= 3

    def test_empty_accuracy_trend_no_calibration_advice(
        self, reporter: EvolutionReporter
    ):
        """空准确率趋势不应建议校准"""
        recs = reporter._generate_recommendations(
            personalization_degree=0.5, acceptance_rate=0.8, accuracy_trend=[]
        )
        assert not any("校准频率" in r for r in recs)
