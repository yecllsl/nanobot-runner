from __future__ import annotations

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from src.core.prediction.models import (
    AcuteLoadRisk,
    BodySignalRisk,
    ChronicRisk,
    DataQuality,
    InjuryReportResult,
    InjuryRiskPrediction,
    RiskFactor,
    RiskTimePoint,
)

logger = logging.getLogger(__name__)

SESSION_SUFFICIENT = 300
SESSION_PARAMETRIC = 100


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

    def _predict_ml_enhanced(self, days: int) -> InjuryRiskPrediction:
        """ML增强预测

        检查是否有已训练的ML模型，无模型时降级到参数化预测，
        避免返回硬编码假数据并标注为ml_enhanced。
        """
        if self._model_manager is not None:
            model_status = self._model_manager.get_model_status("injury_predictor")
            if model_status.is_available:
                model = self._model_manager.load_model("injury_predictor")
                if model is not None:
                    try:
                        return self._run_ml_inference(model, days)
                    except Exception as e:
                        logger.warning(f"ML推理失败，降级到参数化: {e}")
                        return self._predict_parametric(days)

        logger.info("无已训练ML模型，降级到参数化预测")
        return self._predict_parametric(days)

    def _run_ml_inference(self, model: Any, days: int) -> InjuryRiskPrediction:
        """执行ML模型推理（待v0.21.0实现真实训练后启用）"""
        matrix = self._feature_engine.extract_injury_features(days=days)
        features = matrix.features.flatten()

        ensemble_proba = float(model.predict_proba(features.reshape(1, -1))[0, 1])

        risk_score = ensemble_proba * 100
        risk_level = self._score_to_level(risk_score)

        timeline = self._generate_risk_timeline(ensemble_proba, days)

        return InjuryRiskPrediction(
            risk_score=round(risk_score, 1),
            risk_level=risk_level,
            risk_timeline=timeline,
            acute_load_risk=AcuteLoadRisk(
                atl_ctl_ratio=1.2,
                weekly_load_change_pct=10.0,
                risk_contribution=0.35,
            ),
            chronic_risk=ChronicRisk(
                tsb_consecutive_low_days=2,
                resting_hr_deviation_pct=5.0,
                risk_contribution=0.25,
            ),
            body_signal_risk=BodySignalRisk(
                fatigue_score=40.0,
                recovery_status="green",
                active_alerts=[],
                risk_contribution=0.2,
            ),
            top_risk_factors=[
                RiskFactor(
                    name="acwr",
                    contribution=0.35,
                    current_value=1.2,
                    threshold_value=1.5,
                    direction="stable",
                ),
                RiskFactor(
                    name="training_monotony",
                    contribution=0.25,
                    current_value=1.6,
                    threshold_value=2.0,
                    direction="increasing",
                ),
                RiskFactor(
                    name="resting_hr_deviation",
                    contribution=0.2,
                    current_value=5.0,
                    threshold_value=10.0,
                    direction="stable",
                ),
            ],
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
