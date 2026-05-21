# 模型进化器
# 基于校准结果调整Banister IR模型参数
# 高估时增加tau_fitness、降低k1；低估时反向调整
# 单次调整不超过参数值5%，进化后参数持久化

from __future__ import annotations

from datetime import datetime
from typing import Any

from src.core.base.logger import get_logger
from src.core.evolution.calibration_engine import CalibrationEngine
from src.core.evolution.config import EvolutionConfig
from src.core.evolution.evolution_store import EvolutionStore
from src.core.evolution.models import (
    CalibrationProfile,
    ModelEvolutionResult,
    ParameterChange,
)
from src.core.prediction.baselines.banister_ir import BanisterIRModel

logger = get_logger(__name__)


class ModelEvolver:
    """模型进化器

    基于校准结果调整Banister IR模型参数。
    高估时增加tau_fitness、降低k1；低估时反向调整。
    单次调整不超过参数值5%。
    """

    def __init__(
        self,
        calibration_engine: CalibrationEngine,
        store: EvolutionStore,
        prediction_config: Any | None = None,
        config: EvolutionConfig | None = None,
    ) -> None:
        self._calibration_engine = calibration_engine
        self._store = store
        self._prediction_config = prediction_config
        self._config = config or EvolutionConfig()

    def evolve_vdot_model(self) -> ModelEvolutionResult:
        """进化VDOT模型"""
        return self._evolve_model("vdot")

    def evolve_injury_model(self) -> ModelEvolutionResult:
        """进化伤病预测模型"""
        return self._evolve_model("injury")

    def evolve_training_response_model(self) -> ModelEvolutionResult:
        """进化训练响应预测模型"""
        return self._evolve_model("training_response")

    def _evolve_model(self, model_type: str) -> ModelEvolutionResult:
        """执行模型进化"""
        # 运行校准
        try:
            cal_report = self._calibration_engine.run_calibration(model_type)
        except ValueError:
            logger.info("校准数据不足，跳过模型进化: model_type=%s", model_type)
            return ModelEvolutionResult(
                model_type=model_type,
                timestamp=datetime.now(),
                parameter_changes=[],
                mae_before=0.0,
                mae_after=0.0,
                improvement_pct=0.0,
                calibration_report=None,
            )

        # 获取校准后的profile
        profile = self._calibration_engine.get_profile(model_type)

        # 调整Banister参数（仅vdot模型使用Banister IR）
        parameter_changes: list[ParameterChange] = []
        if model_type == "vdot":
            parameter_changes = self._adjust_banister_params(profile)

        # 持久化参数
        if parameter_changes:
            params = self._build_params_dict(model_type, parameter_changes)
            self._store.save_model_params(model_type, params)

        result = ModelEvolutionResult(
            model_type=model_type,
            timestamp=datetime.now(),
            parameter_changes=parameter_changes,
            mae_before=cal_report.mae_before,
            mae_after=cal_report.mae_after,
            improvement_pct=cal_report.improvement_pct,
            calibration_report=cal_report,
        )
        logger.info(
            "模型进化完成: model_type=%s, changes=%d, MAE %.4f→%.4f",
            model_type,
            len(parameter_changes),
            result.mae_before,
            result.mae_after,
        )
        return result

    def _adjust_banister_params(
        self, profile: CalibrationProfile
    ) -> list[ParameterChange]:
        """调整Banister IR参数

        持续高估(scale<1.0): tau_fitness += 2.0, k1 *= 0.95
        持续低估(scale>1.0): tau_fitness -= 2.0, k1 *= 1.05
        单次调整不超过参数值5%
        """
        saved_params = self._store.load_model_params("vdot")
        current_tau_fitness = (
            saved_params.get("tau_fitness", BanisterIRModel.DEFAULT_TAU_FITNESS)
            if saved_params
            else BanisterIRModel.DEFAULT_TAU_FITNESS
        )
        current_k1 = (
            saved_params.get("k1", BanisterIRModel.DEFAULT_K1)
            if saved_params
            else BanisterIRModel.DEFAULT_K1
        )

        changes: list[ParameterChange] = []

        if profile.scale < 1.0:
            # 持续高估: tau_fitness增加, k1降低
            new_tau = current_tau_fitness + 2.0
            max_tau = current_tau_fitness * 1.05
            new_tau = min(new_tau, max_tau)
            change_pct = (new_tau - current_tau_fitness) / current_tau_fitness * 100.0
            changes.append(
                ParameterChange(
                    name="tau_fitness",
                    old_value=current_tau_fitness,
                    new_value=round(new_tau, 4),
                    change_pct=round(change_pct, 2),
                )
            )

            new_k1 = current_k1 * 0.95
            min_k1 = current_k1 * 0.95
            new_k1 = max(new_k1, min_k1)
            k1_change_pct = (new_k1 - current_k1) / current_k1 * 100.0
            changes.append(
                ParameterChange(
                    name="k1",
                    old_value=current_k1,
                    new_value=round(new_k1, 6),
                    change_pct=round(k1_change_pct, 2),
                )
            )

        elif profile.scale > 1.0:
            # 持续低估: tau_fitness减少, k1增加
            new_tau = current_tau_fitness - 2.0
            min_tau = current_tau_fitness * 0.95
            new_tau = max(new_tau, min_tau)
            change_pct = (new_tau - current_tau_fitness) / current_tau_fitness * 100.0
            changes.append(
                ParameterChange(
                    name="tau_fitness",
                    old_value=current_tau_fitness,
                    new_value=round(new_tau, 4),
                    change_pct=round(change_pct, 2),
                )
            )

            new_k1 = current_k1 * 1.05
            max_k1 = current_k1 * 1.05
            new_k1 = min(new_k1, max_k1)
            k1_change_pct = (new_k1 - current_k1) / current_k1 * 100.0
            changes.append(
                ParameterChange(
                    name="k1",
                    old_value=current_k1,
                    new_value=round(new_k1, 6),
                    change_pct=round(k1_change_pct, 2),
                )
            )

        return changes

    def _build_params_dict(
        self, model_type: str, changes: list[ParameterChange]
    ) -> dict[str, float]:
        """构建参数字典用于持久化"""
        saved_params = self._store.load_model_params(model_type)
        if model_type == "vdot":
            params: dict[str, float] = {
                "tau_fitness": saved_params.get(
                    "tau_fitness", BanisterIRModel.DEFAULT_TAU_FITNESS
                )
                if saved_params
                else BanisterIRModel.DEFAULT_TAU_FITNESS,
                "tau_fatigue": saved_params.get(
                    "tau_fatigue", BanisterIRModel.DEFAULT_TAU_FATIGUE
                )
                if saved_params
                else BanisterIRModel.DEFAULT_TAU_FATIGUE,
                "k1": saved_params.get("k1", BanisterIRModel.DEFAULT_K1)
                if saved_params
                else BanisterIRModel.DEFAULT_K1,
                "k2": saved_params.get("k2", BanisterIRModel.DEFAULT_K2)
                if saved_params
                else BanisterIRModel.DEFAULT_K2,
            }
        else:
            params = dict(saved_params) if saved_params else {}

        for change in changes:
            params[change.name] = change.new_value

        return params
