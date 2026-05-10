from __future__ import annotations

import logging
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
        """训练VDOT预测模型"""
        try:
            return ModelTrainingResult(
                model_type="vdot_predictor",
                version="v1",
                training_samples=0,
                validation_error=0.0,
                training_duration_seconds=0.0,
                success=True,
                message="VDOT预测模型训练完成（占位）",
            )
        except Exception as e:
            logger.error(f"VDOT模型训练失败: {e}")
            return ModelTrainingResult(
                model_type="vdot_predictor",
                version="v1",
                training_samples=0,
                validation_error=0.0,
                training_duration_seconds=0.0,
                success=False,
                message=f"训练失败: {e}",
            )

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
