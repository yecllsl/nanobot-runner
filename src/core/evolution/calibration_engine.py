# 预测校准引擎
# 基于预测-实际配对数据，检测偏差方向和幅度
# 通过EMA更新scale因子，实现渐进式校准
# 遵循振幅限制(0.9-1.1)，防止过度修正

from __future__ import annotations

from datetime import datetime

from src.core.base.logger import get_logger
from src.core.evolution.config import EvolutionConfig
from src.core.evolution.evolution_store import EvolutionStore
from src.core.evolution.models import CalibrationProfile, CalibrationReport

logger = get_logger(__name__)


class CalibrationEngine:
    """预测校准引擎

    基于预测-实际配对数据，检测模型偏差方向和幅度，
    通过EMA更新scale因子实现渐进式校准。
    仅使用scale修正（评审MEDIUM-1整改：无bias字段）。
    """

    def __init__(
        self,
        store: EvolutionStore,
        config: EvolutionConfig | None = None,
    ) -> None:
        self._store = store
        self._config = config or EvolutionConfig()

    def run_calibration(
        self,
        model_type: str,
        override_pairs: list[tuple[float, float]] | None = None,
    ) -> CalibrationReport:
        """执行校准流程

        1. 获取预测-实际配对
        2. 检测偏差方向和幅度
        3. 计算新scale
        4. EMA更新
        5. 振幅限制
        6. 计算MAE前后对比
        7. 保存CalibrationProfile
        8. 返回CalibrationReport

        Args:
            model_type: 模型类型
            override_pairs: 测试用预测-实际配对数据，None时从store获取

        Raises:
            ValueError: 校准数据不足时抛出
        """
        # 获取预测-实际配对
        pairs = override_pairs
        if pairs is None:
            pairs = self._store.get_prediction_actual_pairs(
                model_type, self._config.calibration_min_samples
            )

        if len(pairs) < self._config.calibration_min_samples:
            raise ValueError(
                f"校准数据不足: 需要{self._config.calibration_min_samples}对，"
                f"当前{len(pairs)}对"
            )

        # 检测偏差
        direction, magnitude = self._detect_bias(pairs)

        # 计算新scale
        predicted_values = [p for p, _ in pairs]
        actual_values = [a for _, a in pairs]
        mean_predicted = sum(predicted_values) / len(predicted_values)
        mean_actual = sum(actual_values) / len(actual_values)
        new_scale = mean_actual / mean_predicted if mean_predicted != 0 else 1.0

        # 获取当前profile
        current_profile = self._store.load_calibration_profile(model_type)
        if current_profile is None:
            current_profile = CalibrationProfile.default(model_type)

        scale_before = current_profile.scale

        # EMA更新
        updated_scale = self._update_params_ema(current_profile.scale, new_scale)

        # 振幅限制
        updated_scale = self._enforce_amplitude_limit(updated_scale)

        # 计算MAE前后对比
        mae_before = self._calculate_mae(pairs, scale_before)
        mae_after = self._calculate_mae(pairs, updated_scale)

        improvement_pct = (
            (mae_before - mae_after) / mae_before * 100.0 if mae_before > 0 else 0.0
        )

        # 保存CalibrationProfile
        updated_profile = CalibrationProfile(
            model_type=model_type,
            scale=updated_scale,
            last_updated=datetime.now(),
            sample_count=len(pairs),
            mae_before=round(mae_before, 4),
            mae_after=round(mae_after, 4),
        )
        self._store.save_calibration_profile(updated_profile)

        report = CalibrationReport(
            model_type=model_type,
            timestamp=datetime.now(),
            direction=direction,
            magnitude=round(magnitude, 4),
            scale_before=scale_before,
            scale_after=updated_scale,
            mae_before=round(mae_before, 4),
            mae_after=round(mae_after, 4),
            improvement_pct=round(improvement_pct, 2),
            sample_count=len(pairs),
        )
        logger.info(
            "校准完成: model_type=%s, direction=%s, scale %.4f→%.4f, MAE %.4f→%.4f",
            model_type,
            direction,
            scale_before,
            updated_scale,
            mae_before,
            mae_after,
        )
        return report

    def apply_calibration(self, model_type: str, raw_value: float) -> float:
        """应用校准: corrected = raw * scale"""
        profile = self.get_profile(model_type)
        return raw_value * profile.scale

    def get_profile(self, model_type: str) -> CalibrationProfile:
        """获取校准配置，无已保存配置时返回默认profile"""
        profile = self._store.load_calibration_profile(model_type)
        if profile is None:
            return CalibrationProfile.default(model_type)
        return profile

    def reset_calibration(self, model_type: str) -> CalibrationProfile:
        """重置校准配置为默认值"""
        default_profile = CalibrationProfile.default(model_type)
        self._store.save_calibration_profile(default_profile)
        logger.info("校准已重置: model_type=%s", model_type)
        return default_profile

    def _detect_bias(self, pairs: list[tuple[float, float]]) -> tuple[str, float]:
        """检测偏差方向和幅度

        mean_error = clamp(mean(predicted-actual)/mean(actual), -0.5, 0.5)
        direction: >0.05→overestimate, <-0.05→underestimate, else→none
        """
        if not pairs:
            return "none", 0.0

        predicted_values = [p for p, _ in pairs]
        actual_values = [a for _, a in pairs]
        mean_predicted = sum(predicted_values) / len(predicted_values)
        mean_actual = sum(actual_values) / len(actual_values)

        if mean_actual == 0:
            return "none", 0.0

        mean_error = (mean_predicted - mean_actual) / mean_actual
        mean_error = max(-0.5, min(0.5, mean_error))

        if mean_error > 0.05:
            direction = "overestimate"
        elif mean_error < -0.05:
            direction = "underestimate"
        else:
            direction = "none"

        return direction, abs(mean_error)

    def _update_params_ema(self, current_scale: float, new_scale: float) -> float:
        """EMA更新: alpha * new + (1 - alpha) * current"""
        alpha = self._config.calibration_alpha
        return alpha * new_scale + (1 - alpha) * current_scale

    def _enforce_amplitude_limit(self, scale: float) -> float:
        """振幅限制: clamp(0.9, 1.1)"""
        return max(0.9, min(1.1, scale))

    @staticmethod
    def _calculate_mae(pairs: list[tuple[float, float]], scale: float) -> float:
        """计算MAE（应用scale后）"""
        if not pairs:
            return 0.0
        errors = [abs(p * scale - a) for p, a in pairs]
        return sum(errors) / len(errors)
