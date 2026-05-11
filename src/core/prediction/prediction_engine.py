from __future__ import annotations

import logging
from datetime import date
from typing import Any

from src.core.prediction.models import (
    InjuryReportResult,
    InjuryRiskPrediction,
    ModelManagementResult,
    PredictionStatusReport,
    RacePredictionResult,
    TrainingResponse,
    VDOTPrediction,
)

logger = logging.getLogger(__name__)


class PredictionEngine:
    """预测引擎编排层

    统一入口，管理预测器实例和降级逻辑，
    同日缓存机制避免重复计算。
    """

    def __init__(
        self,
        vdot_predictor: Any = None,
        race_predictor: Any = None,
        injury_predictor: Any = None,
        training_response_predictor: Any = None,
        data_assessor: Any = None,
        model_manager: Any = None,
    ) -> None:
        self._vdot_predictor = vdot_predictor
        self._race_predictor = race_predictor
        self._injury_predictor = injury_predictor
        self._training_response_predictor = training_response_predictor
        self._data_assessor = data_assessor
        self._model_manager = model_manager

        self._cache_date: str | None = None
        self._cache_vdot: VDOTPrediction | None = None
        self._cache_race: RacePredictionResult | None = None
        self._cache_injury: InjuryRiskPrediction | None = None

    def predict_vdot_trend(self, days: int = 30) -> VDOTPrediction:
        """VDOT趋势预测"""
        if self._is_same_day_cache() and self._cache_vdot is not None:
            return self._cache_vdot

        result = self._vdot_predictor.predict(days=days)
        self._cache_vdot = result
        self._touch_cache_date()
        return result

    def predict_race_result(
        self,
        distance_km: float,
        race_date: str | None = None,
    ) -> RacePredictionResult:
        """比赛成绩预测"""
        if self._is_same_day_cache() and self._cache_race is not None:
            return self._cache_race

        result = self._race_predictor.predict(
            distance_km=distance_km, race_date=race_date
        )
        self._cache_race = result
        self._touch_cache_date()
        return result

    def predict_injury_risk(self, days: int = 21) -> InjuryRiskPrediction:
        """伤病风险预测"""
        if self._is_same_day_cache() and self._cache_injury is not None:
            return self._cache_injury

        result = self._injury_predictor.predict(days=days)
        self._cache_injury = result
        self._touch_cache_date()
        return result

    def predict_training_response(
        self,
        session_type: str,
        duration_min: int,
        intensity: str,
    ) -> TrainingResponse:
        """训练响应预测"""
        return self._training_response_predictor.predict(
            session_type=session_type,
            duration_min=duration_min,
            intensity=intensity,
        )

    def report_injury(
        self,
        injury_type: str,
        severity: str,
        date: str,
    ) -> InjuryReportResult:
        """伤病报告提交"""
        return self._injury_predictor.report_injury(
            injury_type=injury_type,
            severity=severity,
            date=date,
        )

    def check_prediction_status(self) -> PredictionStatusReport:
        """数据充足度评估"""
        return self._data_assessor.get_full_status()

    def manage_model(
        self,
        action: str,
        model_type: str,
    ) -> ModelManagementResult:
        """模型管理 — train/status/rollback"""
        if action == "status":
            status = self._model_manager.get_model_status(model_type)
            return ModelManagementResult(
                action=action,
                model_type=model_type,
                success=True,
                message=f"模型状态: {'可用' if status.is_available else '不可用'}",
                details={"is_available": status.is_available},
            )
        elif action == "train":
            return self._train_model(model_type)
        elif action == "rollback":
            return self._rollback_model(model_type)
        else:
            return ModelManagementResult(
                action=action,
                model_type=model_type,
                success=False,
                message=f"未知操作: {action}",
                details={},
            )

    def _train_model(self, model_type: str) -> ModelManagementResult:
        """执行模型训练"""
        if model_type == "vdot_predictor":
            train_result = self._vdot_predictor.train_model()
            return ModelManagementResult(
                action="train",
                model_type=model_type,
                success=train_result.success,
                message=train_result.message,
                details={},
            )
        elif model_type == "injury_predictor":
            train_result = self._injury_predictor.train_model()
            return ModelManagementResult(
                action="train",
                model_type=model_type,
                success=train_result.success,
                message=train_result.message,
                details={},
            )
        return ModelManagementResult(
            action="train",
            model_type=model_type,
            success=False,
            message=f"暂不支持训练{model_type}",
            details={},
        )

    def _rollback_model(self, model_type: str) -> ModelManagementResult:
        """回滚模型到上一版本"""
        if self._model_manager is None:
            return ModelManagementResult(
                action="rollback",
                model_type=model_type,
                success=False,
                message="model_manager未注入",
                details={},
            )
        try:
            rollback_result = self._model_manager.rollback(model_type)
            if rollback_result:
                self.invalidate_cache()
                return ModelManagementResult(
                    action="rollback",
                    model_type=model_type,
                    success=True,
                    message=f"{model_type}已回滚到上一版本",
                    details={},
                )
            return ModelManagementResult(
                action="rollback",
                model_type=model_type,
                success=False,
                message=f"{model_type}无可回滚版本",
                details={},
            )
        except Exception as e:
            return ModelManagementResult(
                action="rollback",
                model_type=model_type,
                success=False,
                message=f"回滚失败: {e}",
                details={},
            )

    def invalidate_cache(self) -> None:
        """清空缓存"""
        self._cache_date = None
        self._cache_vdot = None
        self._cache_race = None
        self._cache_injury = None

    def _is_same_day_cache(self) -> bool:
        """检查是否同日缓存"""
        today = date.today().isoformat()
        return self._cache_date == today

    def _touch_cache_date(self) -> None:
        """更新缓存日期"""
        if self._cache_date is None:
            self._cache_date = date.today().isoformat()
