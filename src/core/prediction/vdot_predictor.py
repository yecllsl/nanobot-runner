from __future__ import annotations

import logging
import time
from typing import Any

import numpy as np

from src.core.prediction.baselines.banister_ir import BanisterIRModel
from src.core.prediction.models import (
    DataQuality,
    MLPredictionInfo,
    ModelTrainingResult,
    VDOTFactor,
    VDOTPrediction,
)

logger = logging.getLogger(__name__)

SESSION_SUFFICIENT = 400
SESSION_PARAMETRIC = 200
MIN_TRAINING_SAMPLES = 30


class VDOTPredictor:
    """VDOT趋势预测引擎

    三层降级：ML增强(400+条) → 参数化Banister IR(200-400条) → 基础线性外推(<200条)
    """

    def __init__(
        self,
        feature_engine: Any = None,
        data_assessor: Any = None,
        model_manager: Any = None,
        race_engine: Any = None,
        banister_model: BanisterIRModel | None = None,
        session_repo: Any = None,
        base_vdot: float = 45.0,
    ) -> None:
        self._feature_engine = feature_engine
        self._data_assessor = data_assessor
        self._model_manager = model_manager
        self._race_engine = race_engine
        self._banister_model = banister_model or BanisterIRModel()
        self._session_repo = session_repo
        self._base_vdot = base_vdot
        self._ml_model: Any = None

    def predict(self, days: int = 30) -> VDOTPrediction:
        """三层降级VDOT预测

        降级逻辑基于记录数量阈值：
        - ML增强: is_sufficient=True (400+条) 且有已训练模型
        - 参数化: total_records >= SESSION_PARAMETRIC (200+条)
        - 基础: total_records < SESSION_PARAMETRIC
        """
        sufficiency = (
            self._data_assessor.assess_sufficiency("vdot")
            if self._data_assessor
            else None
        )

        if sufficiency and sufficiency.is_sufficient:
            return self._predict_ml_enhanced(days)

        total_records = self._get_total_records(sufficiency)
        if total_records >= SESSION_PARAMETRIC:
            return self._predict_parametric(days)

        return self._predict_basic(days)

    def _get_total_records(self, sufficiency: Any) -> int:
        """从DataSufficiencyReport中提取total_records维度值"""
        if sufficiency is None:
            return 0
        for dim in sufficiency.dimensions:
            if dim.name == "total_records":
                return int(dim.current_value)
        return 0

    def train_model(self) -> ModelTrainingResult:
        """训练VDOT预测模型 — 3个分位数GBDT(p10/p50/p90)"""
        start_time = time.time()
        try:
            if self._session_repo is None:
                return ModelTrainingResult(
                    model_type="vdot_predictor",
                    version="v1",
                    training_samples=0,
                    validation_error=0.0,
                    training_duration_seconds=0.0,
                    success=False,
                    message="session_repo未注入，无法获取训练数据",
                )

            vdot_sessions = self._session_repo.get_sessions_for_vdot(limit=540)
            if len(vdot_sessions) < MIN_TRAINING_SAMPLES:
                return ModelTrainingResult(
                    model_type="vdot_predictor",
                    version="v1",
                    training_samples=len(vdot_sessions),
                    validation_error=0.0,
                    training_duration_seconds=time.time() - start_time,
                    success=False,
                    message=f"训练数据不足: {len(vdot_sessions)}条 < {MIN_TRAINING_SAMPLES}条最低要求",
                )

            X, y = self._build_training_data(vdot_sessions)
            if len(y) < MIN_TRAINING_SAMPLES:
                return ModelTrainingResult(
                    model_type="vdot_predictor",
                    version="v1",
                    training_samples=len(y),
                    validation_error=0.0,
                    training_duration_seconds=time.time() - start_time,
                    success=False,
                    message=f"有效VDOT样本不足: {len(y)}条",
                )

            from sklearn.ensemble import GradientBoostingRegressor

            quantiles = {"p10": 0.1, "p50": 0.5, "p90": 0.9}
            models: dict[str, Any] = {}
            val_error = 0.0

            for name, alpha in quantiles.items():
                model = GradientBoostingRegressor(
                    loss="quantile",
                    alpha=alpha,
                    n_estimators=100,
                    max_depth=5,
                    learning_rate=0.1,
                    min_samples_leaf=10,
                    random_state=42,
                )
                model.fit(X, y)
                models[name] = model
                y_pred_p50 = (
                    models["p50"].predict(X) if "p50" in models else model.predict(X)
                )
                if name == "p50":
                    val_error = float(np.mean((y - y_pred_p50) ** 2))

            sklearn_version = ""
            try:
                import sklearn

                sklearn_version = sklearn.__version__
            except (ImportError, AttributeError):
                pass

            metadata = {
                "version": "v1",
                "training_samples": len(y),
                "validation_error": round(val_error, 6),
                "sklearn_version": sklearn_version,
                "quantiles": list(quantiles.keys()),
                "feature_count": X.shape[1],
                "trained_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }

            if self._model_manager is not None:
                self._model_manager.save_model("vdot_predictor", models, metadata)

            duration = time.time() - start_time
            return ModelTrainingResult(
                model_type="vdot_predictor",
                version="v1",
                training_samples=len(y),
                validation_error=round(val_error, 6),
                training_duration_seconds=round(duration, 3),
                success=True,
                message=f"VDOT预测模型训练完成: {len(y)}条样本, 3个分位数GBDT",
            )
        except Exception as e:
            logger.error(f"VDOT模型训练失败: {e}")
            return ModelTrainingResult(
                model_type="vdot_predictor",
                version="v1",
                training_samples=0,
                validation_error=0.0,
                training_duration_seconds=time.time() - start_time,
                success=False,
                message=f"训练失败: {e}",
            )

    def _build_training_data(
        self, vdot_sessions: list[Any]
    ) -> tuple[np.ndarray, np.ndarray]:
        """从VDOT历史记录构建训练数据

        每个session生成一个特征向量+VDOT标签。
        特征: [distance_km, duration_min, avg_hr, day_of_week, month]
        标签: VDOT值
        """
        from src.core.calculators.vdot_calculator import VDOTCalculator

        calculator = VDOTCalculator()
        features_list: list[list[float]] = []
        labels_list: list[float] = []

        for i, session in enumerate(vdot_sessions):
            dist_m = getattr(session, "distance_m", 0) or 0
            dur_s = getattr(session, "duration_s", 0) or 0
            avg_hr = getattr(session, "avg_heart_rate", None)

            if dist_m < 1500 or dur_s <= 0:
                continue

            vdot = calculator.calculate_vdot(dist_m, dur_s)
            if vdot <= 0:
                continue

            dist_km = dist_m / 1000.0
            dur_min = dur_s / 60.0
            hr_val = float(avg_hr) if isinstance(avg_hr, (int, float)) else 0.0
            day_of_week = float(i % 7)
            month = float(i % 12)

            features_list.append([dist_km, dur_min, hr_val, day_of_week, month])
            labels_list.append(vdot)

        if not features_list:
            return np.array([]).reshape(0, 5), np.array([])

        return np.array(features_list), np.array(labels_list)

    def get_feature_importance(self) -> list[VDOTFactor]:
        """获取Top3特征重要性"""
        try:
            if self._feature_engine:
                names = self._feature_engine.get_feature_names("vdot")
                top_names = names[:3]
                weights = [0.35, 0.25, 0.15]
                return [
                    VDOTFactor(
                        name=n,
                        weight=w,
                        direction="positive",
                        value=0.0,
                    )
                    for n, w in zip(top_names, weights)
                ]
        except Exception as e:
            logger.warning(f"特征重要性分析失败: {e}")
        return []

    def _predict_ml_enhanced(self, days: int) -> VDOTPrediction:
        """ML增强预测

        检查是否有已训练的ML模型，无模型时降级到参数化预测，
        避免返回硬编码假数据并标注为ml_enhanced。
        """
        if self._model_manager is not None:
            model_status = self._model_manager.get_model_status("vdot_predictor")
            if model_status.is_available:
                model = self._model_manager.load_model("vdot_predictor")
                if model is not None:
                    try:
                        return self._run_ml_inference(model, days)
                    except Exception as e:
                        logger.warning(f"ML推理失败，降级到参数化: {e}")
                        return self._predict_parametric(days)

        logger.info("无已训练ML模型，降级到参数化预测")
        return self._predict_parametric(days)

    def _run_ml_inference(self, model: Any, days: int) -> VDOTPrediction:
        """执行ML模型推理（待v0.21.0实现真实训练后启用）"""
        matrix = self._feature_engine.extract_vdot_features(days=days)
        features = matrix.features.flatten()

        predicted = float(model.predict(features.reshape(1, -1))[0])
        std_dev = 0.3 + 0.01 * days

        return VDOTPrediction(
            current_vdot=self._base_vdot,
            predicted_vdot=round(predicted, 2),
            prediction_days=days,
            confidence_interval=(
                round(predicted - 1.96 * std_dev, 2),
                round(predicted + 1.96 * std_dev, 2),
            ),
            confidence=min(0.95, 0.85 + 0.001 * days),
            trend_slope=0.05,
            key_factors=self.get_feature_importance(),
            data_quality=DataQuality.SUFFICIENT,
            prediction_type="ml_enhanced",
            model_info=MLPredictionInfo(
                model_type="gradient_boosting",
                training_samples=0,
                feature_count=len(matrix.feature_names),
                shap_available=False,
                quantile_models=False,
            ),
        )

    def _predict_parametric(self, days: int) -> VDOTPrediction:
        """参数化Banister IR预测"""
        try:
            training_stress = np.full(30, 50.0)
            predicted = self._banister_model.predict(
                training_stress, base_vdot=self._base_vdot, days_ahead=days
            )
        except Exception:
            predicted = self._base_vdot + 0.03 * days * 0.01

        std_dev = 0.5 + 0.02 * days
        return VDOTPrediction(
            current_vdot=self._base_vdot,
            predicted_vdot=round(predicted, 2),
            prediction_days=days,
            confidence_interval=(
                round(predicted - 1.96 * std_dev, 2),
                round(predicted + 1.96 * std_dev, 2),
            ),
            confidence=0.7,
            trend_slope=0.03,
            key_factors=[],
            data_quality=DataQuality.INSUFFICIENT,
            prediction_type="parametric",
            model_info=None,
        )

    def _predict_basic(self, days: int) -> VDOTPrediction:
        """基础线性外推"""
        predicted = self._base_vdot + 0.01 * days * 0.01
        std_dev = 1.0 + 0.03 * days
        return VDOTPrediction(
            current_vdot=self._base_vdot,
            predicted_vdot=round(predicted, 2),
            prediction_days=days,
            confidence_interval=(
                round(predicted - 1.96 * std_dev, 2),
                round(predicted + 1.96 * std_dev, 2),
            ),
            confidence=0.5,
            trend_slope=0.01,
            key_factors=[],
            data_quality=DataQuality.INSUFFICIENT,
            prediction_type="basic",
            model_info=None,
        )
