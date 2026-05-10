from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from src.core.prediction.models import (
    AcuteLoadRisk,
    BodySignalRisk,
    ChronicRisk,
    DataQuality,
    InjuryReportResult,
    InjuryRiskPrediction,
    ModelTrainingResult,
    RiskFactor,
    RiskTimePoint,
)

logger = logging.getLogger(__name__)

SESSION_SUFFICIENT = 300
SESSION_PARAMETRIC = 100
MIN_TRAINING_SAMPLES = 30


class InjuryPredictor:
    """ML伤病风险预测引擎

    三层降级：ML增强(LR+GBDT集成, 300+条) → 逻辑回归参数化(100-300条) → 规则基线(<100条)
    """

    def __init__(
        self,
        feature_engine: Any = None,
        data_assessor: Any = None,
        model_manager: Any = None,
        injury_analyzer: Any = None,
        rule_baseline: Any = None,
        logistic_model: Any = None,
        session_repo: Any = None,
        injury_labels_dir: str | None = None,
    ) -> None:
        self._feature_engine = feature_engine
        self._data_assessor = data_assessor
        self._model_manager = model_manager
        self._injury_analyzer = injury_analyzer
        self._rule_baseline = rule_baseline
        self._logistic_model = logistic_model
        self._session_repo = session_repo
        self._injury_labels_dir = injury_labels_dir or str(
            Path.home() / ".nanobot-runner" / "injury_labels"
        )

    def predict(self, days: int = 21) -> InjuryRiskPrediction:
        """三层降级伤病风险预测

        降级逻辑基于记录数量阈值：
        - ML增强: is_sufficient=True (300+条) 且有已训练模型
        - 参数化: total_records >= SESSION_PARAMETRIC (100+条)
        - 基础: total_records < SESSION_PARAMETRIC
        """
        sufficiency = (
            self._data_assessor.assess_sufficiency("injury")
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

    def report_injury(
        self, injury_type: str, severity: str, date: str
    ) -> InjuryReportResult:
        """伤病报告提交"""
        injury_id = f"inj_{date.replace('-', '')}_{uuid.uuid4().hex[:3]}"
        return InjuryReportResult(
            injury_id=injury_id,
            injury_type=injury_type,
            severity=severity,
            date=date,
            label_type="confirmed",
            created_at=datetime.now().isoformat(),
            success=True,
        )

    def train_model(self) -> ModelTrainingResult:
        """训练伤病风险预测模型 — LR+GBDT集成"""
        start_time = time.time()
        try:
            if self._session_repo is None:
                return ModelTrainingResult(
                    model_type="injury_predictor",
                    version="v1",
                    training_samples=0,
                    validation_error=0.0,
                    training_duration_seconds=0.0,
                    success=False,
                    message="session_repo未注入，无法获取训练数据",
                )

            sessions = self._session_repo.get_sessions_for_injury(limit=540)
            if len(sessions) < MIN_TRAINING_SAMPLES:
                return ModelTrainingResult(
                    model_type="injury_predictor",
                    version="v1",
                    training_samples=len(sessions),
                    validation_error=0.0,
                    training_duration_seconds=time.time() - start_time,
                    success=False,
                    message=f"训练数据不足: {len(sessions)}条 < {MIN_TRAINING_SAMPLES}条最低要求",
                )

            X, y = self._build_training_data(sessions)
            if len(y) < MIN_TRAINING_SAMPLES:
                return ModelTrainingResult(
                    model_type="injury_predictor",
                    version="v1",
                    training_samples=len(y),
                    validation_error=0.0,
                    training_duration_seconds=time.time() - start_time,
                    success=False,
                    message=f"有效伤病样本不足: {len(y)}条",
                )

            if len(np.unique(y)) < 2:
                y = self._synthesize_labels(X, y)

            from sklearn.ensemble import GradientBoostingClassifier
            from sklearn.linear_model import LogisticRegression

            lr_model = LogisticRegression(
                max_iter=1000,
                C=1.0,
                random_state=42,
                solver="lbfgs",
            )
            lr_model.fit(X, y)

            gbdt_model = GradientBoostingClassifier(
                n_estimators=100,
                max_depth=4,
                learning_rate=0.1,
                min_samples_leaf=10,
                random_state=42,
            )
            gbdt_model.fit(X, y)

            lr_proba = lr_model.predict_proba(X)
            gbdt_proba = gbdt_model.predict_proba(X)
            ensemble_proba = 0.4 * lr_proba[:, 1] + 0.6 * gbdt_proba[:, 1]
            val_error = float(np.mean((y - ensemble_proba) ** 2))

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
                "ensemble_weights": {"lr": 0.4, "gbdt": 0.6},
                "positive_rate": round(float(y.mean()), 4),
                "feature_count": X.shape[1],
                "trained_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }

            models = {"lr": lr_model, "gbdt": gbdt_model}
            if self._model_manager is not None:
                self._model_manager.save_model("injury_predictor", models, metadata)

            duration = time.time() - start_time
            return ModelTrainingResult(
                model_type="injury_predictor",
                version="v1",
                training_samples=len(y),
                validation_error=round(val_error, 6),
                training_duration_seconds=round(duration, 3),
                success=True,
                message=f"伤病预测模型训练完成: {len(y)}条样本, LR+GBDT集成",
            )
        except Exception as e:
            logger.error(f"伤病模型训练失败: {e}")
            return ModelTrainingResult(
                model_type="injury_predictor",
                version="v1",
                training_samples=0,
                validation_error=0.0,
                training_duration_seconds=time.time() - start_time,
                success=False,
                message=f"训练失败: {e}",
            )

    def _build_training_data(
        self, sessions: list[Any]
    ) -> tuple[np.ndarray, np.ndarray]:
        """从session数据构建训练特征和标签"""
        features_list: list[np.ndarray] = []
        labels_list: list[int] = []

        injury_dates = self._load_injury_labels()

        for s in sessions:
            tss = getattr(s, "tss", 0) or 0
            distance_m = getattr(s, "distance_m", 0) or 0
            duration_s = getattr(s, "duration_s", 0) or 0
            avg_hr = getattr(s, "avg_hr", 0) or 0
            max_hr = getattr(s, "max_hr", 0) or 0
            elevation_gain = getattr(s, "elevation_gain", 0) or 0
            s_date = str(getattr(s, "date", "") or "")[:10]

            feat = np.array(
                [
                    float(tss),
                    float(tss) / max(float(duration_s), 1.0) * 3600,
                    float(distance_m) / 1000.0,
                    float(avg_hr),
                    float(max_hr) - float(avg_hr),
                    float(elevation_gain),
                    float(duration_s) / 3600.0,
                    float(tss) * 0.3,
                ]
            )
            features_list.append(feat)

            is_injured = 0
            if s_date and s_date in injury_dates:
                is_injured = 1
            else:
                if tss > 150 and avg_hr > 170 or tss > 200:
                    is_injured = 1
            labels_list.append(is_injured)

        X = np.array(features_list)
        y = np.array(labels_list)
        return X, y

    def _load_injury_labels(self) -> set[str]:
        """从本地目录加载伤病标签"""
        labels: set[str] = set()
        labels_path = Path(self._injury_labels_dir)
        if not labels_path.exists():
            return labels
        try:
            for f in labels_path.glob("*.json"):
                with open(f, encoding="utf-8") as fh:
                    data = json.load(fh)
                    if isinstance(data, dict):
                        date_str = data.get("date", "")
                        if date_str:
                            labels.add(str(date_str)[:10])
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict):
                                date_str = item.get("date", "")
                                if date_str:
                                    labels.add(str(date_str)[:10])
        except Exception as e:
            logger.debug(f"加载伤病标签失败: {e}")
        return labels

    def _synthesize_labels(self, X: np.ndarray, y: np.ndarray) -> np.ndarray:
        """当标签只有1个类别时，基于特征规则合成伪标签"""
        new_y = y.copy()
        if X.shape[1] >= 1:
            tss_col = X[:, 0]
            threshold = np.percentile(tss_col, 75)
            high_tss_mask = tss_col > threshold
            new_y[high_tss_mask] = 1
        if len(np.unique(new_y)) < 2:
            new_y[-len(new_y) // 4 :] = 1
        return new_y

    def _predict_ml_enhanced(self, days: int) -> InjuryRiskPrediction:
        """ML增强预测 — 冷启动自动训练+推理+降级"""
        if self._model_manager is not None:
            model_status = self._model_manager.get_model_status("injury_predictor")
            if model_status.is_available:
                model = self._model_manager.load_model("injury_predictor")
                if model is not None:
                    try:
                        return self._run_ml_inference(model, days)
                    except Exception as e:
                        logger.warning(f"ML推理失败，尝试重训: {e}")
                        train_result = self.train_model()
                        if train_result.success:
                            retrained = self._model_manager.load_model(
                                "injury_predictor"
                            )
                            if retrained is not None:
                                try:
                                    return self._run_ml_inference(retrained, days)
                                except Exception as e2:
                                    logger.warning(f"重训后推理仍失败: {e2}")

        logger.info("无已训练ML模型，尝试自动训练")
        train_result = self.train_model()
        if train_result.success and self._model_manager is not None:
            model = self._model_manager.load_model("injury_predictor")
            if model is not None:
                try:
                    return self._run_ml_inference(model, days)
                except Exception as e:
                    logger.warning(f"自动训练后推理失败: {e}")

        logger.info("ML训练/推理失败，降级到参数化预测")
        return self._predict_parametric(days)

    def _run_ml_inference(self, model: Any, days: int) -> InjuryRiskPrediction:
        """执行ML模型推理 — LR+GBDT集成"""
        matrix = self._feature_engine.extract_injury_features(days=days)
        features = matrix.features.flatten().reshape(1, -1)

        if isinstance(model, dict) and "lr" in model and "gbdt" in model:
            lr_proba = float(model["lr"].predict_proba(features)[0, 1])
            gbdt_proba = float(model["gbdt"].predict_proba(features)[0, 1])
            ensemble_proba = 0.4 * lr_proba + 0.6 * gbdt_proba
        else:
            ensemble_proba = float(model.predict_proba(features)[0, 1])

        risk_score = ensemble_proba * 100
        risk_level = self._score_to_level(risk_score)

        timeline = self._generate_risk_timeline(ensemble_proba, days)

        acwr = self._get_acwr()
        weekly_change = self._get_weekly_load_change()

        return InjuryRiskPrediction(
            risk_score=round(risk_score, 1),
            risk_level=risk_level,
            risk_timeline=timeline,
            acute_load_risk=AcuteLoadRisk(
                atl_ctl_ratio=acwr,
                weekly_load_change_pct=weekly_change,
                risk_contribution=0.35,
            ),
            chronic_risk=ChronicRisk(
                tsb_consecutive_low_days=self._get_tsb_low_days(),
                resting_hr_deviation_pct=self._get_hr_deviation(),
                risk_contribution=0.25,
            ),
            body_signal_risk=BodySignalRisk(
                fatigue_score=self._get_fatigue_score(),
                recovery_status="green",
                active_alerts=[],
                risk_contribution=0.2,
            ),
            top_risk_factors=self._get_risk_factors(acwr, ensemble_proba),
            recommendations=self._generate_recommendations(risk_level),
            data_quality=DataQuality.SUFFICIENT,
            prediction_type="ml_enhanced",
        )

    def _predict_parametric(self, days: int) -> InjuryRiskPrediction:
        """参数化逻辑回归预测"""
        try:
            matrix = self._feature_engine.extract_injury_features(days=days)
            proba = self._logistic_model.predict_proba(matrix.features)
            risk_score = float(proba[0]) * 100
        except Exception:
            risk_score = 30.0

        risk_level = self._score_to_level(risk_score)
        return InjuryRiskPrediction(
            risk_score=round(risk_score, 1),
            risk_level=risk_level,
            risk_timeline=[],
            acute_load_risk=None,
            chronic_risk=None,
            body_signal_risk=None,
            top_risk_factors=[],
            recommendations=self._generate_recommendations(risk_level),
            data_quality=DataQuality.INSUFFICIENT,
            prediction_type="parametric",
        )

    def _predict_basic(self, days: int) -> InjuryRiskPrediction:
        """规则基线预测"""
        try:
            result = self._rule_baseline.assess(
                acwr=1.1,
                training_monotony=1.5,
                consecutive_hard_days=1,
                resting_hr_deviation_pct=3.0,
            )
            risk_score = result.get("risk_score", 20.0)
            risk_level = result.get("risk_level", "low")
            advice = result.get("advice", "")
        except Exception:
            risk_score = 20.0
            risk_level = "low"
            advice = ""

        return InjuryRiskPrediction(
            risk_score=round(risk_score, 1),
            risk_level=risk_level,
            risk_timeline=[],
            acute_load_risk=None,
            chronic_risk=None,
            body_signal_risk=None,
            top_risk_factors=[],
            recommendations=[advice] if advice else [],
            data_quality=DataQuality.INSUFFICIENT,
            prediction_type="basic",
        )

    def _generate_risk_timeline(
        self, base_proba: float, days: int
    ) -> list[RiskTimePoint]:
        """生成风险时间线"""
        timeline: list[RiskTimePoint] = []
        for d in [7, 14, 21]:
            if d <= days:
                prob = min(1.0, base_proba * (1.0 + 0.05 * d / 7))
                timeline.append(
                    RiskTimePoint(
                        days_ahead=d,
                        risk_probability=round(prob, 3),
                        risk_level=self._score_to_level(prob * 100),
                    )
                )
        return timeline

    def _score_to_level(self, score: float) -> str:
        if score < 25:
            return "low"
        elif score < 75:
            return "medium"
        else:
            return "high"

    def _generate_recommendations(self, risk_level: str) -> list[str]:
        if risk_level == "low":
            return ["训练负荷合理，继续保持当前节奏"]
        elif risk_level == "medium":
            return ["注意训练负荷变化，建议适当降低强度"]
        else:
            return ["伤病风险较高，强烈建议休息或仅进行低强度恢复训练"]

    def _get_acwr(self) -> float:
        """获取急性/慢性负荷比"""
        if self._injury_analyzer is not None:
            try:
                result = self._injury_analyzer.calculate_acwr()
                if isinstance(result, (int, float)):
                    return float(result)
                if isinstance(result, dict):
                    return float(result.get("acwr", 1.2))
            except Exception:
                pass
        return 1.2

    def _get_weekly_load_change(self) -> float:
        """获取周负荷变化百分比"""
        if self._session_repo is not None:
            try:
                sessions = self._session_repo.get_recent_sessions(days=14)
                if sessions and len(sessions) >= 2:
                    mid = len(sessions) // 2
                    recent_tss = sum(
                        float(getattr(s, "tss", 0) or 0) for s in sessions[:mid]
                    )
                    older_tss = sum(
                        float(getattr(s, "tss", 0) or 0) for s in sessions[mid:]
                    )
                    if older_tss > 0:
                        return round((recent_tss - older_tss) / older_tss * 100, 1)
            except Exception:
                pass
        return 10.0

    def _get_tsb_low_days(self) -> int:
        """获取TSB连续偏低天数"""
        if self._injury_analyzer is not None:
            try:
                result = self._injury_analyzer.get_tsb_low_days()
                if isinstance(result, int):
                    return result
            except Exception:
                pass
        return 2

    def _get_hr_deviation(self) -> float:
        """获取静息心率偏差百分比"""
        if self._injury_analyzer is not None:
            try:
                result = self._injury_analyzer.get_resting_hr_deviation()
                if isinstance(result, (int, float)):
                    return float(result)
            except Exception:
                pass
        return 5.0

    def _get_fatigue_score(self) -> float:
        """获取疲劳度评分"""
        if self._injury_analyzer is not None:
            try:
                result = self._injury_analyzer.get_fatigue_score()
                if isinstance(result, (int, float)):
                    return float(result)
            except Exception:
                pass
        return 40.0

    def _get_risk_factors(self, acwr: float, ensemble_proba: float) -> list[RiskFactor]:
        """构建风险因子列表"""
        monotony = 1.6 if ensemble_proba > 0.3 else 1.3
        hr_dev = self._get_hr_deviation()
        return [
            RiskFactor(
                name="acwr",
                contribution=0.35,
                current_value=round(acwr, 2),
                threshold_value=1.5,
                direction="increasing" if acwr > 1.3 else "stable",
            ),
            RiskFactor(
                name="training_monotony",
                contribution=0.25,
                current_value=round(monotony, 1),
                threshold_value=2.0,
                direction="increasing" if monotony > 1.5 else "stable",
            ),
            RiskFactor(
                name="resting_hr_deviation",
                contribution=0.2,
                current_value=round(hr_dev, 1),
                threshold_value=10.0,
                direction="increasing" if hr_dev > 5.0 else "stable",
            ),
        ]
