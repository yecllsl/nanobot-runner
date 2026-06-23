from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import numpy as np

from src.core.base.exceptions import NanobotRunnerError
from src.core.prediction.models import DataQuality, VDOTFactor
from src.core.prediction.vdot_predictor import VDOTPredictor


def _make_assessor(sufficient: bool, parametric: bool = False):
    assessor = MagicMock()
    report = MagicMock()
    report.is_sufficient = sufficient
    report.overall_progress_pct = 90.0 if sufficient else (60.0 if parametric else 30.0)
    total_dim = MagicMock()
    total_dim.name = "total_records"
    total_dim.current_value = 500.0 if sufficient else (250.0 if parametric else 30.0)
    report.dimensions = [total_dim]
    assessor.assess_sufficiency.return_value = report
    return assessor


def _make_feature_engine():
    fe = MagicMock()
    matrix = MagicMock()
    matrix.features = np.random.randn(1, 12)
    matrix.feature_names = [f"f{i}" for i in range(12)]
    matrix.feature_type = "vdot"
    matrix.data_quality = "sufficient"
    fe.extract_vdot_features.return_value = matrix
    fe.get_feature_names.return_value = [f"f{i}" for i in range(12)]
    return fe


def _make_vdot_sessions(count: int = 50) -> list[MagicMock]:
    sessions = []
    for i in range(count):
        s = MagicMock()
        s.distance_m = 5000.0 + i * 100
        s.duration_s = 1800.0 + i * 10
        s.timestamp = datetime(2024, 1, 1 + (i % 28), 8, 0, 0)
        sessions.append(s)
    return sessions


def _make_model_manager():
    mm = MagicMock()
    mm.load_model.return_value = MagicMock()
    mm.get_model_status.return_value = MagicMock(is_available=True)
    return mm


class TestVDOTPredictorGetTssSeries:
    def test_get_tss_series_no_repo(self):
        predictor = VDOTPredictor(base_vdot=45.0)
        result = predictor._get_tss_series()
        assert result == []

    def test_get_tss_series_with_sessions(self):
        session_repo = MagicMock()
        sessions = []
        for i in range(5):
            s = MagicMock()
            s.date = f"2024-01-{10 + i:02d}"
            s.tss = 50.0 + i * 10
            sessions.append(s)
        session_repo.get_recent_sessions.return_value = sessions
        predictor = VDOTPredictor(session_repo=session_repo, base_vdot=45.0)
        result = predictor._get_tss_series()
        assert len(result) == 5
        assert result[0] == 50.0

    def test_get_tss_series_empty_sessions(self):
        session_repo = MagicMock()
        session_repo.get_recent_sessions.return_value = []
        predictor = VDOTPredictor(session_repo=session_repo, base_vdot=45.0)
        result = predictor._get_tss_series()
        assert result == []

    def test_get_tss_series_exception(self):
        session_repo = MagicMock()
        session_repo.get_recent_sessions.side_effect = NanobotRunnerError("db error")
        predictor = VDOTPredictor(session_repo=session_repo, base_vdot=45.0)
        result = predictor._get_tss_series()
        assert result == []

    def test_get_tss_series_aggregates_same_date(self):
        session_repo = MagicMock()
        sessions = []
        for i in range(4):
            s = MagicMock()
            s.date = "2024-01-10" if i < 2 else "2024-01-11"
            s.tss = 30.0
            sessions.append(s)
        session_repo.get_recent_sessions.return_value = sessions
        predictor = VDOTPredictor(session_repo=session_repo, base_vdot=45.0)
        result = predictor._get_tss_series()
        assert len(result) == 2
        assert result[0] == 60.0
        assert result[1] == 60.0


class TestVDOTPredictorGetTotalRecords:
    def test_get_total_records_none(self):
        predictor = VDOTPredictor(base_vdot=45.0)
        result = predictor._get_total_records(None)
        assert result == 0

    def test_get_total_records_with_dim(self):
        sufficiency = MagicMock()
        dim = MagicMock()
        dim.name = "total_records"
        dim.current_value = 300.0
        sufficiency.dimensions = [dim]
        predictor = VDOTPredictor(base_vdot=45.0)
        result = predictor._get_total_records(sufficiency)
        assert result == 300

    def test_get_total_records_no_matching_dim(self):
        sufficiency = MagicMock()
        dim = MagicMock()
        dim.name = "other_dim"
        dim.current_value = 300.0
        sufficiency.dimensions = [dim]
        predictor = VDOTPredictor(base_vdot=45.0)
        result = predictor._get_total_records(sufficiency)
        assert result == 0


class TestVDOTPredictorBuildTrainingData:
    def test_build_training_data_no_feature_engine(self):
        predictor = VDOTPredictor(base_vdot=45.0)
        X, y = predictor._build_training_data(_make_vdot_sessions(10))
        assert X.shape[0] == 0
        assert len(y) == 0

    def test_build_training_data_with_sessions(self):
        fe = _make_feature_engine()
        session_repo = MagicMock()
        session_repo.get_sessions_for_vdot.return_value = _make_vdot_sessions(50)
        predictor = VDOTPredictor(
            feature_engine=fe,
            session_repo=session_repo,
            base_vdot=45.0,
        )
        X, y = predictor._build_training_data(_make_vdot_sessions(50))
        assert X.shape[0] > 0
        assert len(y) > 0

    def test_build_training_data_short_distance_filtered(self):
        fe = _make_feature_engine()
        sessions = []
        for i in range(10):
            s = MagicMock()
            s.distance_m = 500.0
            s.duration_s = 300.0
            s.timestamp = datetime(2024, 1, 1 + i, 8, 0, 0)
            sessions.append(s)
        predictor = VDOTPredictor(feature_engine=fe, base_vdot=45.0)
        X, y = predictor._build_training_data(sessions)
        assert X.shape[0] == 0

    def test_build_training_data_no_timestamp(self):
        fe = _make_feature_engine()
        sessions = []
        for i in range(5):
            s = MagicMock()
            s.distance_m = 5000.0
            s.duration_s = 1800.0
            s.timestamp = None
            sessions.append(s)
        predictor = VDOTPredictor(feature_engine=fe, base_vdot=45.0)
        X, y = predictor._build_training_data(sessions)
        assert X.shape[0] == 0


class TestVDOTPredictorPredictParametric:
    def test_parametric_with_tss_series(self):
        banister = MagicMock()
        banister.predict.return_value = 46.5
        session_repo = MagicMock()
        sessions = []
        for i in range(5):
            s = MagicMock()
            s.date = f"2024-01-{10 + i:02d}"
            s.tss = 50.0
            sessions.append(s)
        session_repo.get_recent_sessions.return_value = sessions
        predictor = VDOTPredictor(
            data_assessor=_make_assessor(sufficient=False, parametric=True),
            banister_model=banister,
            session_repo=session_repo,
            base_vdot=45.0,
        )
        result = predictor._predict_parametric(days=30)
        assert result.prediction_type == "parametric"
        assert result.data_quality == DataQuality.INSUFFICIENT

    def test_parametric_banister_failure(self):
        banister = MagicMock()
        banister.predict.side_effect = NanobotRunnerError("model error")
        predictor = VDOTPredictor(
            data_assessor=_make_assessor(sufficient=False, parametric=True),
            banister_model=banister,
            base_vdot=45.0,
        )
        result = predictor._predict_parametric(days=30)
        assert result.prediction_type == "parametric"


class TestVDOTPredictorPredictBasic:
    def test_basic_prediction_values(self):
        predictor = VDOTPredictor(base_vdot=45.0)
        result = predictor._predict_basic(days=30)
        assert result.current_vdot == 45.0
        assert result.prediction_type == "basic"
        assert result.confidence == 0.5
        assert result.trend_slope == 0.01
        assert len(result.confidence_interval) == 2
        assert result.confidence_interval[0] < result.confidence_interval[1]


class TestVDOTPredictorMLEnhancedDegradation:
    def test_ml_enhanced_model_available_inference_fails_retrain_fails(self):
        fe = _make_feature_engine()
        mm = MagicMock()
        mm.get_model_status.return_value = MagicMock(is_available=True)
        mm.load_model.return_value = None
        session_repo = MagicMock()
        session_repo.get_sessions_for_vdot.return_value = _make_vdot_sessions(5)
        predictor = VDOTPredictor(
            feature_engine=fe,
            data_assessor=_make_assessor(sufficient=True),
            model_manager=mm,
            session_repo=session_repo,
            base_vdot=45.0,
        )
        result = predictor.predict(days=30)
        assert result.prediction_type in ("ml_enhanced", "parametric", "basic")

    def test_ml_enhanced_no_model_manager(self):
        fe = _make_feature_engine()
        session_repo = MagicMock()
        session_repo.get_sessions_for_vdot.return_value = _make_vdot_sessions(5)
        predictor = VDOTPredictor(
            feature_engine=fe,
            data_assessor=_make_assessor(sufficient=True),
            model_manager=None,
            session_repo=session_repo,
            base_vdot=45.0,
        )
        result = predictor.predict(days=30)
        assert result.prediction_type in ("ml_enhanced", "parametric", "basic")

    def test_ml_enhanced_no_data_assessor(self):
        fe = _make_feature_engine()
        predictor = VDOTPredictor(
            feature_engine=fe,
            data_assessor=None,
            model_manager=_make_model_manager(),
            base_vdot=45.0,
        )
        result = predictor.predict(days=30)
        assert result.prediction_type in ("basic", "parametric")


class TestVDOTPredictorFeatureImportance:
    def test_feature_importance_with_model_manager(self):
        fe = _make_feature_engine()
        mm = MagicMock()
        mock_model = MagicMock()
        mock_model.feature_importances_ = np.array(
            [0.3, 0.2, 0.15, 0.1, 0.08, 0.06, 0.04, 0.03, 0.02, 0.01, 0.005, 0.005]
        )
        mm.load_model.return_value = {"p50": mock_model}
        predictor = VDOTPredictor(
            feature_engine=fe,
            model_manager=mm,
            base_vdot=45.0,
        )
        factors = predictor.get_feature_importance()
        assert isinstance(factors, list)
        assert len(factors) <= 3

    def test_feature_importance_no_model_no_manager(self):
        fe = _make_feature_engine()
        predictor = VDOTPredictor(
            feature_engine=fe,
            model_manager=None,
            base_vdot=45.0,
        )
        factors = predictor.get_feature_importance()
        assert isinstance(factors, list)
        assert len(factors) <= 3
        if factors:
            for f in factors:
                assert f.weight > 0

    def test_feature_importance_no_feature_engine(self):
        predictor = VDOTPredictor(
            feature_engine=None,
            model_manager=None,
            base_vdot=45.0,
        )
        factors = predictor.get_feature_importance()
        assert isinstance(factors, list)
        assert len(factors) == 0


class TestVDOTPredictorTrainModelEdgeCases:
    def test_train_model_exception(self):
        session_repo = MagicMock()
        session_repo.get_sessions_for_vdot.side_effect = NanobotRunnerError("db error")
        predictor = VDOTPredictor(
            feature_engine=_make_feature_engine(),
            session_repo=session_repo,
            base_vdot=45.0,
        )
        result = predictor.train_model()
        assert result.success is False
        assert "训练失败" in result.message

    def test_train_model_valid_samples_insufficient(self):
        session_repo = MagicMock()
        sessions = []
        for i in range(5):
            s = MagicMock()
            s.distance_m = 500.0
            s.duration_s = 300.0
            s.timestamp = datetime(2024, 1, 1 + i, 8, 0, 0)
            sessions.append(s)
        session_repo.get_sessions_for_vdot.return_value = sessions
        predictor = VDOTPredictor(
            feature_engine=_make_feature_engine(),
            session_repo=session_repo,
            base_vdot=45.0,
        )
        result = predictor.train_model()
        assert result.success is False


class TestVDOTPredictorTrainModelValidSamplesInsufficient:
    """覆盖 line 117: _build_training_data 返回有效样本不足时"""

    def test_train_model_enough_sessions_but_filtered_out(self):
        """35个session但全部被_build_training_data过滤，len(y) < 30"""
        session_repo = MagicMock()
        # 创建35个短距离session，通过len检查但被_build_training_data过滤
        sessions = []
        for i in range(35):
            s = MagicMock()
            s.distance_m = 500.0  # < 1500，会被过滤
            s.duration_s = 300.0
            s.timestamp = datetime(2024, 1, 1 + (i % 28), 8, 0, 0)
            sessions.append(s)
        session_repo.get_sessions_for_vdot.return_value = sessions
        predictor = VDOTPredictor(
            feature_engine=_make_feature_engine(),
            session_repo=session_repo,
            base_vdot=45.0,
        )
        result = predictor.train_model()
        assert result.success is False
        assert "有效VDOT样本不足" in result.message


class TestVDOTPredictorBuildTrainingDataEdgeCases:
    """覆盖 _build_training_data 的边界条件 (lines 222, 229-230, 237-239, 242-243)"""

    def test_vdot_zero_or_negative_filtered(self):
        """覆盖 line 222: vdot <= 0 时跳过"""
        fe = _make_feature_engine()
        sessions = []
        for i in range(5):
            s = MagicMock()
            s.distance_m = 5000.0
            s.duration_s = 1800.0
            s.timestamp = datetime(2024, 1, 1 + i, 8, 0, 0)
            sessions.append(s)
        with patch("src.core.calculators.vdot_calculator.VDOTCalculator") as MockCalc:
            MockCalc.return_value.calculate_vdot.return_value = 0.0
            predictor = VDOTPredictor(feature_engine=fe, base_vdot=45.0)
            X, y = predictor._build_training_data(sessions)
            assert X.shape[0] == 0

    def test_timestamp_parsing_error(self):
        """覆盖 lines 229-230: timestamp 解析错误"""
        fe = _make_feature_engine()
        sessions = []
        for i in range(5):
            s = MagicMock()
            s.distance_m = 5000.0
            s.duration_s = 1800.0
            s.timestamp = "invalid-date-format"
            sessions.append(s)
        predictor = VDOTPredictor(feature_engine=fe, base_vdot=45.0)
        X, y = predictor._build_training_data(sessions)
        assert X.shape[0] == 0

    def test_feature_extraction_nanobot_error(self):
        """覆盖 lines 237-239: 特征提取 NanobotRunnerError"""
        fe = MagicMock()
        fe.extract_vdot_features.side_effect = NanobotRunnerError("feature error")
        sessions = []
        for i in range(5):
            s = MagicMock()
            s.distance_m = 5000.0
            s.duration_s = 1800.0
            s.timestamp = datetime(2024, 1, 1 + i, 8, 0, 0)
            sessions.append(s)
        predictor = VDOTPredictor(feature_engine=fe, base_vdot=45.0)
        X, y = predictor._build_training_data(sessions)
        assert X.shape[0] == 0

    def test_feature_dimension_mismatch(self):
        """覆盖 lines 242-243: 特征维度不匹配"""
        fe = MagicMock()
        matrix = MagicMock()
        # 返回8维特征而非12维
        matrix.features = np.random.randn(1, 8)
        fe.extract_vdot_features.return_value = matrix
        sessions = []
        for i in range(5):
            s = MagicMock()
            s.distance_m = 5000.0
            s.duration_s = 1800.0
            s.timestamp = datetime(2024, 1, 1 + i, 8, 0, 0)
            sessions.append(s)
        predictor = VDOTPredictor(feature_engine=fe, base_vdot=45.0)
        X, y = predictor._build_training_data(sessions)
        assert X.shape[0] == 0


class TestVDOTPredictorGetFeatureImportanceBranches:
    """覆盖 get_feature_importance 和 _extract_importances 的分支 (lines 266, 295-296, 333, 359-362)"""

    def test_ml_model_with_p50_returns_importances(self):
        """覆盖 line 266: _ml_model 存在且有 p50 模型时返回 importances"""
        fe = _make_feature_engine()
        mock_model = MagicMock()
        mock_model.feature_importances_ = np.array(
            [0.3, 0.2, 0.15, 0.1, 0.08, 0.06, 0.04, 0.03, 0.02, 0.01, 0.005, 0.005]
        )
        mock_model.n_features_in_ = 12
        predictor = VDOTPredictor(feature_engine=fe, base_vdot=45.0)
        predictor._ml_model = {"p50": mock_model}
        factors = predictor.get_feature_importance()
        assert isinstance(factors, list)
        assert len(factors) <= 3
        if factors:
            for f in factors:
                assert isinstance(f, VDOTFactor)
                assert f.weight > 0

    def test_feature_importance_exception_returns_empty(self):
        """覆盖 lines 295-296: get_feature_importance 异常时返回空列表"""
        fe = MagicMock()
        fe.get_feature_names.side_effect = AttributeError("broken")
        mm = MagicMock()
        mm.load_model.return_value = None
        predictor = VDOTPredictor(
            feature_engine=fe,
            model_manager=mm,
            base_vdot=45.0,
        )
        predictor._ml_model = None
        factors = predictor.get_feature_importance()
        assert isinstance(factors, list)

    def test_extract_importances_sklearn_error(self):
        """覆盖 lines 359-362: sklearn feature_importances_ 提取异常"""
        fe = _make_feature_engine()
        mock_model = MagicMock()
        # feature_importances_ 访问时抛出异常
        type(mock_model).feature_importances_ = property(
            lambda self: (_ for _ in ()).throw(NanobotRunnerError("importance error"))
        )
        predictor = VDOTPredictor(feature_engine=fe, base_vdot=45.0)
        # 直接调用 _extract_importances
        result = predictor._extract_importances(
            mock_model, [f"f{i}" for i in range(12)]
        )
        assert isinstance(result, list)


class TestVDOTPredictorMLEnhancedRetrain:
    """覆盖 _predict_ml_enhanced 的降级路径 (lines 373-382, 389-392)"""

    def test_ml_inference_fails_retrain_succeeds_retrain_inference_fails(self):
        """覆盖 lines 373-382: ML推理失败→重训成功→重训后推理仍失败→降级"""
        fe = _make_feature_engine()
        mm = MagicMock()
        mm.get_model_status.return_value = MagicMock(is_available=True)

        # 推理会失败的模型
        mock_bad_model = MagicMock()
        mock_bad_model.predict.side_effect = NanobotRunnerError("inference error")

        # 重训后 load_model 也返回会导致推理失败的模型
        mm.load_model.return_value = {
            "p10": mock_bad_model,
            "p50": mock_bad_model,
            "p90": mock_bad_model,
        }

        # 提供50个session确保train_model能成功
        session_repo = MagicMock()
        session_repo.get_sessions_for_vdot.return_value = _make_vdot_sessions(50)
        session_repo.get_recent_sessions.return_value = []

        predictor = VDOTPredictor(
            feature_engine=fe,
            data_assessor=_make_assessor(sufficient=True),
            model_manager=mm,
            session_repo=session_repo,
            base_vdot=45.0,
        )
        result = predictor.predict(days=30)
        # 应降级到 parametric 或 basic
        assert result.prediction_type in ("parametric", "basic")

    def test_auto_train_succeeds_but_inference_fails(self):
        """覆盖 lines 389-392: 自动训练成功但推理失败→降级"""
        fe = _make_feature_engine()
        mm = MagicMock()
        mm.get_model_status.return_value = MagicMock(is_available=False)
        # 第一次 load_model 返回 None（无已训练模型）
        # 重训后 load_model 返回会导致推理失败的模型
        call_count = [0]

        def load_model_side_effect(name):
            call_count[0] += 1
            if call_count[0] <= 1:
                return None
            mock_model = MagicMock()
            mock_model.predict.side_effect = NanobotRunnerError("inference error")
            return {"p10": mock_model, "p50": mock_model, "p90": mock_model}

        mm.load_model.side_effect = load_model_side_effect

        # 提供50个session确保train_model能成功
        session_repo = MagicMock()
        session_repo.get_sessions_for_vdot.return_value = _make_vdot_sessions(50)
        session_repo.get_recent_sessions.return_value = []

        predictor = VDOTPredictor(
            feature_engine=fe,
            data_assessor=_make_assessor(sufficient=True),
            model_manager=mm,
            session_repo=session_repo,
            base_vdot=45.0,
        )
        result = predictor.predict(days=30)
        assert result.prediction_type in ("parametric", "basic")


class TestVDOTPredictorMLInferenceQuantileModels:
    """覆盖 _run_ml_inference 的分位数模型路径 (lines 408-421)"""

    def test_run_ml_inference_with_quantile_models_narrow_ci(self):
        """覆盖 lines 408-416: 分位数模型，窄置信区间 (ci_width < 1.0)"""
        fe = _make_feature_engine()
        # 创建 p10/p50/p90 模型，p90 - p10 < 1.0
        mock_p10 = MagicMock()
        mock_p10.predict.return_value = np.array([44.5])
        mock_p50 = MagicMock()
        mock_p50.predict.return_value = np.array([45.0])
        mock_p90 = MagicMock()
        mock_p90.predict.return_value = np.array([45.3])

        model = {"p10": mock_p10, "p50": mock_p50, "p90": mock_p90}
        predictor = VDOTPredictor(feature_engine=fe, base_vdot=45.0)
        result = predictor._run_ml_inference(model, days=30)
        assert result.confidence == 0.95  # ci_width = 0.8 < 1.0
        assert result.predicted_vdot == 45.0

    def test_run_ml_inference_with_quantile_models_medium_ci(self):
        """覆盖 lines 417-418: 中等置信区间 (1.0 <= ci_width < 2.0)"""
        fe = _make_feature_engine()
        mock_p10 = MagicMock()
        mock_p10.predict.return_value = np.array([44.0])
        mock_p50 = MagicMock()
        mock_p50.predict.return_value = np.array([45.0])
        mock_p90 = MagicMock()
        mock_p90.predict.return_value = np.array([45.8])

        model = {"p10": mock_p10, "p50": mock_p50, "p90": mock_p90}
        predictor = VDOTPredictor(feature_engine=fe, base_vdot=45.0)
        result = predictor._run_ml_inference(model, days=30)
        assert result.confidence == 0.85  # ci_width = 1.8, 1.0 <= 1.8 < 2.0

    def test_run_ml_inference_with_quantile_models_wide_ci(self):
        """覆盖 lines 419-420: 宽置信区间 (ci_width >= 2.0)"""
        fe = _make_feature_engine()
        mock_p10 = MagicMock()
        mock_p10.predict.return_value = np.array([43.0])
        mock_p50 = MagicMock()
        mock_p50.predict.return_value = np.array([45.0])
        mock_p90 = MagicMock()
        mock_p90.predict.return_value = np.array([46.0])

        model = {"p10": mock_p10, "p50": mock_p50, "p90": mock_p90}
        predictor = VDOTPredictor(feature_engine=fe, base_vdot=45.0)
        result = predictor._run_ml_inference(model, days=30)
        assert result.confidence == 0.70  # ci_width = 3.0 >= 2.0


class TestVDOTPredictorMLInferenceTrendSlope:
    """覆盖 _run_ml_inference 的趋势斜率计算 (lines 432-447)"""

    def test_run_ml_inference_with_trend_slope(self):
        """覆盖 lines 432-447: 有 session_repo 且有效 session 时计算趋势斜率"""
        fe = _make_feature_engine()
        mock_p50 = MagicMock()
        mock_p50.predict.return_value = np.array([45.0])
        model = {"p10": mock_p50, "p50": mock_p50, "p90": mock_p50}

        session_repo = MagicMock()
        sessions = []
        for i in range(5):
            s = MagicMock()
            s.distance_m = 5000.0 + i * 100
            s.duration_s = 1800.0 + i * 10
            sessions.append(s)
        session_repo.get_sessions_for_vdot.return_value = sessions

        predictor = VDOTPredictor(
            feature_engine=fe,
            session_repo=session_repo,
            base_vdot=45.0,
        )
        result = predictor._run_ml_inference(model, days=30)
        assert result.trend_slope != 0.0  # 有趋势斜率

    def test_run_ml_inference_trend_slope_calculation_error(self):
        """覆盖 lines 446-447: 趋势斜率计算异常"""
        fe = _make_feature_engine()
        mock_p50 = MagicMock()
        mock_p50.predict.return_value = np.array([45.0])
        model = {"p10": mock_p50, "p50": mock_p50, "p90": mock_p50}

        session_repo = MagicMock()
        session_repo.get_sessions_for_vdot.side_effect = NanobotRunnerError("db error")

        predictor = VDOTPredictor(
            feature_engine=fe,
            session_repo=session_repo,
            base_vdot=45.0,
        )
        result = predictor._run_ml_inference(model, days=30)
        assert result.trend_slope == 0.0  # 异常时默认0.0


class TestVDOTPredictorGetTssSeriesEdgeCases:
    """覆盖 _get_tss_series 的边界条件 (line 532)"""

    def test_get_tss_series_none_date_and_timestamp(self):
        """覆盖 line 532: session 的 date 和 timestamp 都为 None"""
        session_repo = MagicMock()
        s = MagicMock()
        s.date = None
        s.timestamp = None
        s.tss = 50.0
        session_repo.get_recent_sessions.return_value = [s]
        predictor = VDOTPredictor(session_repo=session_repo, base_vdot=45.0)
        result = predictor._get_tss_series()
        assert result == []

    def test_get_tss_series_non_numeric_tss(self):
        """覆盖: tss 不是数字类型时跳过"""
        session_repo = MagicMock()
        s = MagicMock()
        s.date = "2024-01-10"
        s.tss = "not_a_number"  # 非数字
        session_repo.get_recent_sessions.return_value = [s]
        predictor = VDOTPredictor(session_repo=session_repo, base_vdot=45.0)
        result = predictor._get_tss_series()
        assert result == []

    def test_get_tss_series_uses_timestamp_fallback(self):
        """覆盖: date 为 None 但 timestamp 有值时使用 timestamp"""
        session_repo = MagicMock()
        s = MagicMock()
        s.date = None
        s.timestamp = "2024-01-10"
        s.tss = 50.0
        session_repo.get_recent_sessions.return_value = [s]
        predictor = VDOTPredictor(session_repo=session_repo, base_vdot=45.0)
        result = predictor._get_tss_series()
        assert len(result) == 1
        assert result[0] == 50.0
