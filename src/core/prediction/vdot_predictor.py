from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any

import numpy as np

from src.core.prediction.baselines.banister_ir import BanisterIRModel
from src.core.prediction.feature_engine import VDOT_FEATURE_NAMES
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
                    message=(
                        f"训练数据不足: {len(vdot_sessions)}条 < "
                        f"{MIN_TRAINING_SAMPLES}条最低要求"
                    ),
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

        使用FeatureEngine提取12维特征，确保训练/推理特征维度一致。
        每个session生成一个特征向量+VDOT标签。
        """
        from src.core.calculators.vdot_calculator import VDOTCalculator

        calculator = VDOTCalculator()
        features_list: list[list[float]] = []
        labels_list: list[float] = []
        n_features = len(VDOT_FEATURE_NAMES)

        if self._feature_engine is None:
            logger.warning("FeatureEngine未注入，无法构建训练数据")
            return np.array([]).reshape(0, n_features), np.array([])

        for session in vdot_sessions:
            dist_m = getattr(session, "distance_m", 0) or 0
            dur_s = getattr(session, "duration_s", 0) or 0

            if dist_m < 1500 or dur_s <= 0:
                continue

            vdot = calculator.calculate_vdot(dist_m, dur_s)
            if vdot <= 0:
                continue

            ts = getattr(session, "timestamp", None)
            if ts is None:
                continue
            try:
                s_date = datetime.strptime(str(ts)[:10], "%Y-%m-%d").date()
            except (ValueError, TypeError):
                continue

            try:
                matrix = self._feature_engine.extract_vdot_features(
                    reference_date=s_date
                )
                feat = matrix.features.flatten().tolist()
            except Exception as e:
                logger.debug(f"VDOT特征提取失败({s_date}): {e}")
                continue

            if len(feat) != n_features:
                logger.debug(f"特征维度不匹配({s_date}): {len(feat)} != {n_features}")
                continue

            features_list.append(feat)
            labels_list.append(vdot)

        if not features_list:
            return np.array([]).reshape(0, n_features), np.array([])

        return np.array(features_list), np.array(labels_list)

    def get_feature_importance(self) -> list[VDOTFactor]:
        """获取Top3特征重要性 — SHAP > sklearn feature_importances_ > 固定权重"""
        try:
            if self._ml_model is not None and isinstance(self._ml_model, dict):
                p50_model = self._ml_model.get("p50")
                if p50_model is not None:
                    names = (
                        self._feature_engine.get_feature_names("vdot")
                        if self._feature_engine
                        else [f"f{i}" for i in range(12)]
                    )
                    importances = self._extract_importances(p50_model, names)
                    if importances:
                        return importances[:3]

            if self._model_manager is not None:
                model = self._model_manager.load_model("vdot_predictor")
                if model is not None and isinstance(model, dict):
                    p50_model = model.get("p50")
                    if p50_model is not None:
                        names = (
                            self._feature_engine.get_feature_names("vdot")
                            if self._feature_engine
                            else [f"f{i}" for i in range(12)]
                        )
                        importances = self._extract_importances(p50_model, names)
                        if importances:
                            return importances[:3]

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

    def _extract_importances(
        self, model: Any, feature_names: list[str]
    ) -> list[VDOTFactor]:
        """从模型提取特征重要性 — SHAP > sklearn feature_importances_"""
        try:
            import shap

            explainer = shap.TreeExplainer(model)
            n_features = len(feature_names)
            dummy = np.zeros((1, model.n_features_in_))
            if dummy.shape[1] < n_features:
                dummy = np.zeros((1, n_features))
            shap_values = explainer.shap_values(dummy)
            if isinstance(shap_values, np.ndarray) and shap_values.ndim >= 2:
                mean_abs = np.abs(shap_values[0])
            else:
                mean_abs = np.abs(np.array(shap_values))
            total = mean_abs.sum()
            normalized = mean_abs / total if total > 0 else mean_abs
            pairs = list(
                zip(feature_names[: len(normalized)], normalized[: len(feature_names)])
            )
            pairs.sort(key=lambda x: x[1], reverse=True)
            return [
                VDOTFactor(
                    name=name,
                    weight=round(float(weight), 4),
                    direction="positive",
                    value=0.0,
                )
                for name, weight in pairs
                if weight > 0
            ]
        except ImportError:
            logger.debug("shap未安装，降级到sklearn feature_importances_")
        except Exception as e:
            logger.debug(f"SHAP计算失败，降级: {e}")

        try:
            if hasattr(model, "feature_importances_"):
                importances = model.feature_importances_
                total = importances.sum()
                normalized = importances / total if total > 0 else importances
                pairs = list(
                    zip(
                        feature_names[: len(normalized)],
                        normalized[: len(feature_names)],
                    )
                )
                pairs.sort(key=lambda x: x[1], reverse=True)
                return [
                    VDOTFactor(
                        name=name,
                        weight=round(float(weight), 4),
                        direction="positive",
                        value=0.0,
                    )
                    for name, weight in pairs
                    if weight > 0
                ]
        except Exception as e:
            logger.debug(f"sklearn feature_importances_提取失败: {e}")

        return []

    def _predict_ml_enhanced(self, days: int) -> VDOTPrediction:
        """ML增强预测 — 冷启动自动训练+推理+降级"""
        if self._model_manager is not None:
            model_status = self._model_manager.get_model_status("vdot_predictor")
            if model_status.is_available:
                model = self._model_manager.load_model("vdot_predictor")
                if model is not None:
                    try:
                        return self._run_ml_inference(model, days)
                    except Exception as e:
                        logger.warning(f"ML推理失败，尝试重训: {e}")
                        train_result = self.train_model()
                        if train_result.success:
                            retrained = self._model_manager.load_model("vdot_predictor")
                            if retrained is not None:
                                try:
                                    return self._run_ml_inference(retrained, days)
                                except Exception as e2:
                                    logger.warning(f"重训后推理仍失败: {e2}")

        logger.info("无已训练ML模型，尝试自动训练")
        train_result = self.train_model()
        if train_result.success and self._model_manager is not None:
            model = self._model_manager.load_model("vdot_predictor")
            if model is not None:
                try:
                    return self._run_ml_inference(model, days)
                except Exception as e:
                    logger.warning(f"自动训练后推理失败: {e}")

        logger.info("ML训练/推理失败，降级到参数化预测")
        return self._predict_parametric(days)

    def _run_ml_inference(self, model: Any, days: int) -> VDOTPrediction:
        """执行ML模型推理 — 3个分位数模型获取p10/p50/p90"""
        matrix = self._feature_engine.extract_vdot_features(days=days)
        features = matrix.features.flatten()

        if (
            isinstance(model, dict)
            and "p10" in model
            and "p50" in model
            and "p90" in model
        ):
            p10 = float(model["p10"].predict(features.reshape(1, -1))[0])
            p50 = float(model["p50"].predict(features.reshape(1, -1))[0])
            p90 = float(model["p90"].predict(features.reshape(1, -1))[0])
            predicted = p50
            ci_lower = p10
            ci_upper = p90
            ci_width = p90 - p10
            if ci_width < 1.0:
                confidence = 0.95
            elif ci_width < 2.0:
                confidence = 0.85
            else:
                confidence = 0.70
            quantile_models = True
        else:
            predicted = float(model.predict(features.reshape(1, -1))[0])
            std_dev = 0.3 + 0.01 * days
            ci_lower = round(predicted - 1.96 * std_dev, 2)
            ci_upper = round(predicted + 1.96 * std_dev, 2)
            confidence = min(0.95, 0.85 + 0.001 * days)
            quantile_models = False

        trend_slope = 0.0
        if self._session_repo is not None:
            try:
                sessions = self._session_repo.get_sessions_for_vdot(limit=10)
                if len(sessions) >= 2:
                    from src.core.calculators.vdot_calculator import VDOTCalculator

                    calc = VDOTCalculator()
                    recent = []
                    for s in sessions[:5]:
                        d = getattr(s, "distance_m", 0) or 0
                        t = getattr(s, "duration_s", 0) or 0
                        if d >= 1500 and t > 0:
                            recent.append(calc.calculate_vdot(d, t))
                    if len(recent) >= 2:
                        trend_slope = (recent[0] - recent[-1]) / len(recent)
            except Exception as e:
                logger.debug(f"VDOT趋势计算失败: {e}")

        return VDOTPrediction(
            current_vdot=self._base_vdot,
            predicted_vdot=round(predicted, 2),
            prediction_days=days,
            confidence_interval=(round(ci_lower, 2), round(ci_upper, 2)),
            confidence=confidence,
            trend_slope=round(trend_slope, 4),
            key_factors=self.get_feature_importance(),
            data_quality=DataQuality.SUFFICIENT,
            prediction_type="ml_enhanced",
            model_info=MLPredictionInfo(
                model_type="gradient_boosting",
                training_samples=0,
                feature_count=len(matrix.feature_names),
                shap_available=False,
                quantile_models=quantile_models,
            ),
        )

    def _predict_parametric(self, days: int) -> VDOTPrediction:
        """参数化Banister IR预测 — 使用真实TSS序列"""
        try:
            tss_series = self._get_tss_series()
            if tss_series and len(tss_series) > 0:
                training_stress = np.array(tss_series, dtype=float)
            else:
                training_stress = np.full(30, 50.0)
            predicted = self._banister_model.predict(
                training_stress, base_vdot=self._base_vdot, days_ahead=days
            )
        except Exception as e:
            logger.debug(f"Banister模型预测失败: {e}")
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

    def _get_tss_series(self, days: int = 42) -> list[float]:
        """从session_repo获取TSS序列"""
        if self._session_repo is None:
            return []
        try:
            sessions = self._session_repo.get_recent_sessions(limit=days * 3)
            if not sessions:
                return []
            tss_map: dict[str, float] = {}
            for s in sessions:
                s_date = getattr(s, "date", None) or getattr(s, "timestamp", None)
                if s_date is None:
                    continue
                date_str = str(s_date)[:10]
                tss = getattr(s, "tss", None)
                if isinstance(tss, (int, float)):
                    tss_map[date_str] = tss_map.get(date_str, 0.0) + float(tss)
            if not tss_map:
                return []
            sorted_dates = sorted(tss_map.keys())
            return [tss_map[d] for d in sorted_dates]
        except Exception as e:
            logger.debug(f"TSS序列获取失败: {e}")
            return []
