from __future__ import annotations

from unittest.mock import MagicMock

from src.core.twin.models import (
    BodySignalDimension,
    FitnessDimension,
    LoadDimension,
    RiskDimension,
    RunnerStateVector,
    TrainingPatternDimension,
)
from src.core.twin.state_vector_builder import StateVectorBuilder


def _make_mock_prediction_engine() -> MagicMock:
    """Mock PredictionEngine: predict_vdot_trend/predict_injury_risk"""
    engine = MagicMock()
    engine.predict_vdot_trend.return_value = MagicMock(
        to_dict=lambda: {
            "current_vdot": 45.0,
            "trend_slope": 0.02,
            "confidence": 0.85,
            "prediction_type": "ml_enhanced",
        }
    )
    engine.predict_injury_risk.return_value = MagicMock(
        to_dict=lambda: {
            "risk_score": 25.0,
            "risk_level": "medium",
            "risk_timeline": [
                {"days_ahead": 7, "risk_probability": 0.05, "risk_level": "low"},
                {"days_ahead": 28, "risk_probability": 0.15, "risk_level": "medium"},
            ],
            "prediction_type": "parametric",
        }
    )
    return engine


def _make_mock_body_signal_engine() -> MagicMock:
    """Mock BodySignalEngine: get_daily_summary"""
    engine = MagicMock()
    engine.get_daily_summary.return_value = MagicMock(
        to_dict=lambda: {
            "fatigue_score": 3.5,
            "recovery_status": "good",
            "data_quality": "sufficient",
        }
    )
    return engine


def _make_mock_training_load_analyzer() -> MagicMock:
    """Mock TrainingLoadAnalyzer: calculate_atl/ctl/tsb/acwr"""
    analyzer = MagicMock()
    analyzer.calculate_atl.return_value = 50.0
    analyzer.calculate_ctl.return_value = 65.0
    analyzer.calculate_atl_ctl.return_value = {"atl": 50.0, "ctl": 65.0}
    analyzer.calculate_training_load_from_dataframe.return_value = {
        "atl": 50.0,
        "ctl": 65.0,
        "tsb": 15.0,
        "runs_count": 5,
    }
    return analyzer


def _make_mock_session_repo() -> MagicMock:
    """Mock SessionRepository: get_recent_sessions"""
    import polars as pl

    repo = MagicMock()
    repo.get_recent_sessions.return_value = [
        MagicMock(
            distance_m=8000.0,
            duration_s=2400.0,
        ),
        MagicMock(
            distance_m=10000.0,
            duration_s=3600.0,
        ),
        MagicMock(
            distance_m=5000.0,
            duration_s=1800.0,
        ),
        MagicMock(
            distance_m=12000.0,
            duration_s=4200.0,
        ),
    ]
    repo.storage.read_parquet.return_value = pl.DataFrame(
        {
            "session_total_distance": [8000.0, 10000.0, 5000.0, 12000.0],
            "session_total_timer_time": [2400.0, 3600.0, 1800.0, 4200.0],
            "session_avg_heart_rate": [150.0, 160.0, 145.0, 165.0],
        }
    ).lazy()
    return repo


class TestStateVectorBuilderBuild:
    """测试正常构建流程"""

    def setup_method(self) -> None:
        self.prediction_engine = _make_mock_prediction_engine()
        self.body_signal_engine = _make_mock_body_signal_engine()
        self.training_load_analyzer = _make_mock_training_load_analyzer()
        self.session_repo = _make_mock_session_repo()
        self.builder = StateVectorBuilder(
            prediction_engine=self.prediction_engine,
            body_signal_engine=self.body_signal_engine,
            training_load_analyzer=self.training_load_analyzer,
            session_repo=self.session_repo,
        )

    def test_returns_runner_state_vector(self) -> None:
        result = self.builder.build()
        assert isinstance(result, RunnerStateVector)

    def test_fitness_dimension(self) -> None:
        result = self.builder.build()
        assert isinstance(result.fitness, FitnessDimension)
        assert result.fitness.vdot == 45.0
        assert result.fitness.vdot_trend == 0.02

    def test_load_dimension(self) -> None:
        result = self.builder.build()
        assert isinstance(result.load, LoadDimension)
        assert result.load.ctl == 65.0
        assert result.load.atl == 50.0
        assert result.load.tsb == 15.0

    def test_body_signal_dimension(self) -> None:
        result = self.builder.build()
        assert isinstance(result.body_signal, BodySignalDimension)
        assert result.body_signal.fatigue_score == 3.5
        assert result.body_signal.recovery_status == "good"

    def test_risk_dimension(self) -> None:
        result = self.builder.build()
        assert isinstance(result.risk, RiskDimension)
        assert result.risk.injury_risk_7d == 5.0
        assert result.risk.injury_risk_28d == 15.0

    def test_training_pattern_dimension(self) -> None:
        result = self.builder.build()
        assert isinstance(result.training_pattern, TrainingPatternDimension)
        assert result.training_pattern.weekly_volume_km > 0


class TestStateVectorBuilderFallback:
    """测试依赖失败时的零值默认维度"""

    def test_prediction_engine_failure(self) -> None:
        engine = _make_mock_prediction_engine()
        engine.predict_vdot_trend.side_effect = Exception("ML模型不可用")
        builder = StateVectorBuilder(
            prediction_engine=engine,
            body_signal_engine=_make_mock_body_signal_engine(),
            training_load_analyzer=_make_mock_training_load_analyzer(),
            session_repo=_make_mock_session_repo(),
        )
        result = builder.build()
        assert result.fitness.vdot == 0.0
        assert result.fitness.vdot_trend == 0.0


class TestStateVectorBuilderBug2203:
    """BUG-2203回归：验证build_load从session_repo读取数据"""

    def test_build_load_with_session_data(self) -> None:
        """验证build_load从session_repo读取数据计算CTL/ATL"""
        import polars as pl

        mock_repo = MagicMock()
        mock_repo.storage.read_parquet.return_value = pl.DataFrame(
            {
                "session_total_distance": [5000.0, 8000.0],
                "session_total_timer_time": [1800.0, 3000.0],
                "session_avg_heart_rate": [150.0, 160.0],
            }
        ).lazy()
        mock_analyzer = MagicMock()
        mock_analyzer.calculate_training_load_from_dataframe.return_value = {
            "atl": 50.0,
            "ctl": 60.0,
            "tsb": 10.0,
            "runs_count": 2,
        }

        builder = StateVectorBuilder(
            training_load_analyzer=mock_analyzer,
            session_repo=mock_repo,
        )
        load = builder.build_load()

        assert load.ctl == 60.0
        assert load.atl == 50.0
        assert load.tsb == 10.0
        mock_repo.storage.read_parquet.assert_called()
        mock_analyzer.calculate_training_load_from_dataframe.assert_called()

    def test_build_load_without_session_repo(self) -> None:
        """验证无session_repo时回退到calculate_atl_ctl"""
        mock_analyzer = MagicMock()
        mock_analyzer.calculate_atl_ctl.return_value = {"atl": 30.0, "ctl": 40.0}

        builder = StateVectorBuilder(
            training_load_analyzer=mock_analyzer,
            session_repo=None,
        )
        load = builder.build_load()

        assert load.atl == 30.0
        assert load.ctl == 40.0
        mock_analyzer.calculate_atl_ctl.assert_called_with([])

    def test_build_load_read_parquet_exception(self) -> None:
        """验证read_parquet异常时回退到空DataFrame"""
        mock_repo = MagicMock()
        mock_repo.storage.read_parquet.side_effect = Exception("文件不存在")
        mock_analyzer = MagicMock()
        mock_analyzer.calculate_training_load_from_dataframe.return_value = {
            "atl": 0.0,
            "ctl": 0.0,
            "tsb": 0.0,
            "runs_count": 0,
        }

        builder = StateVectorBuilder(
            training_load_analyzer=mock_analyzer,
            session_repo=mock_repo,
        )
        load = builder.build_load()

        assert load.ctl == 0.0
        assert load.atl == 0.0

    def test_body_signal_engine_failure(self) -> None:
        engine = _make_mock_body_signal_engine()
        engine.get_daily_summary.side_effect = Exception("数据不足")
        builder = StateVectorBuilder(
            prediction_engine=_make_mock_prediction_engine(),
            body_signal_engine=engine,
            training_load_analyzer=_make_mock_training_load_analyzer(),
            session_repo=_make_mock_session_repo(),
        )
        result = builder.build()
        assert result.body_signal.fatigue_score == 0.0
        assert result.body_signal.recovery_status == "unknown"

    def test_training_load_analyzer_failure(self) -> None:
        analyzer = _make_mock_training_load_analyzer()
        analyzer.calculate_training_load_from_dataframe.side_effect = Exception(
            "无TSS数据"
        )
        builder = StateVectorBuilder(
            prediction_engine=_make_mock_prediction_engine(),
            body_signal_engine=_make_mock_body_signal_engine(),
            training_load_analyzer=analyzer,
            session_repo=_make_mock_session_repo(),
        )
        result = builder.build()
        assert result.load.ctl == 0.0
        assert result.load.atl == 0.0

    def test_session_repo_failure(self) -> None:
        repo = _make_mock_session_repo()
        repo.get_recent_sessions.side_effect = Exception("存储不可用")
        builder = StateVectorBuilder(
            prediction_engine=_make_mock_prediction_engine(),
            body_signal_engine=_make_mock_body_signal_engine(),
            training_load_analyzer=_make_mock_training_load_analyzer(),
            session_repo=repo,
        )
        result = builder.build()
        assert result.training_pattern.weekly_volume_km == 0.0

    def test_injury_risk_failure(self) -> None:
        engine = _make_mock_prediction_engine()
        engine.predict_injury_risk.side_effect = Exception("风险模型不可用")
        builder = StateVectorBuilder(
            prediction_engine=engine,
            body_signal_engine=_make_mock_body_signal_engine(),
            training_load_analyzer=_make_mock_training_load_analyzer(),
            session_repo=_make_mock_session_repo(),
        )
        result = builder.build()
        assert result.risk.injury_risk_7d == 0.0
        assert result.risk.injury_risk_28d == 0.0


class TestStateVectorBuilderExceptionDistinction:
    """测试预期异常与意外异常的区分（P2-06）"""

    def test_attribute_error_returns_default_fitness(self) -> None:
        engine = _make_mock_prediction_engine()
        engine.predict_vdot_trend.side_effect = AttributeError("no method")
        builder = StateVectorBuilder(
            prediction_engine=engine,
            body_signal_engine=_make_mock_body_signal_engine(),
            training_load_analyzer=_make_mock_training_load_analyzer(),
            session_repo=_make_mock_session_repo(),
        )
        result = builder.build()
        assert result.fitness.vdot == 0.0

    def test_value_error_returns_default_load(self) -> None:
        analyzer = _make_mock_training_load_analyzer()
        analyzer.calculate_training_load_from_dataframe.side_effect = ValueError(
            "bad value"
        )
        builder = StateVectorBuilder(
            prediction_engine=_make_mock_prediction_engine(),
            body_signal_engine=_make_mock_body_signal_engine(),
            training_load_analyzer=analyzer,
            session_repo=_make_mock_session_repo(),
        )
        result = builder.build()
        assert result.load.ctl == 0.0

    def test_type_error_returns_default_body_signal(self) -> None:
        engine = _make_mock_body_signal_engine()
        engine.get_daily_summary.side_effect = TypeError("wrong type")
        builder = StateVectorBuilder(
            prediction_engine=_make_mock_prediction_engine(),
            body_signal_engine=engine,
            training_load_analyzer=_make_mock_training_load_analyzer(),
            session_repo=_make_mock_session_repo(),
        )
        result = builder.build()
        assert result.body_signal.fatigue_score == 0.0

    def test_key_error_returns_default_risk(self) -> None:
        engine = _make_mock_prediction_engine()
        engine.predict_injury_risk.side_effect = KeyError("missing key")
        builder = StateVectorBuilder(
            prediction_engine=engine,
            body_signal_engine=_make_mock_body_signal_engine(),
            training_load_analyzer=_make_mock_training_load_analyzer(),
            session_repo=_make_mock_session_repo(),
        )
        result = builder.build()
        assert result.risk.injury_risk_7d == 0.0

    def test_unexpected_exception_returns_default_fitness(self) -> None:
        engine = _make_mock_prediction_engine()
        engine.predict_vdot_trend.side_effect = RuntimeError("unexpected")
        builder = StateVectorBuilder(
            prediction_engine=engine,
            body_signal_engine=_make_mock_body_signal_engine(),
            training_load_analyzer=_make_mock_training_load_analyzer(),
            session_repo=_make_mock_session_repo(),
        )
        result = builder.build()
        assert result.fitness.vdot == 0.0
