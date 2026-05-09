from __future__ import annotations

import logging

import numpy as np
from scipy.optimize import curve_fit

logger = logging.getLogger(__name__)


class BanisterIRModel:
    """Banister IR模型 - 参数化VDOT趋势基线

    使用Banister冲动-响应模型预测VDOT趋势：
    Performance(t) = P0 + k1 * Fitness(t) - k2 * Fatigue(t)

    其中：
    - Fitness(t) = Σ TSS(t-i) * exp(-i/τ1)
    - Fatigue(t) = Σ TSS(t-i) * exp(-i/τ2)
    """

    DEFAULT_TAU_FITNESS = 42.0
    DEFAULT_TAU_FATIGUE = 10.0
    DEFAULT_K1 = 0.0038
    DEFAULT_K2 = 0.043

    def __init__(
        self,
        tau_fitness: float = DEFAULT_TAU_FITNESS,
        tau_fatigue: float = DEFAULT_TAU_FATIGUE,
        k1: float = DEFAULT_K1,
        k2: float = DEFAULT_K2,
    ) -> None:
        self.tau_fitness = tau_fitness
        self.tau_fatigue = tau_fatigue
        self.k1 = k1
        self.k2 = k2
        self._fitted = False

    def predict(
        self,
        training_stress: np.ndarray,
        base_vdot: float = 45.0,
        days_ahead: int = 0,
    ) -> float:
        """预测VDOT值"""
        fitness = self._ewma_sum(training_stress, self.tau_fitness)
        fatigue = self._ewma_sum(training_stress, self.tau_fatigue)

        if days_ahead > 0:
            avg_stress = (
                float(np.mean(training_stress[-7:]))
                if len(training_stress) >= 7
                else float(np.mean(training_stress))
            )
            future_stress = np.full(days_ahead, avg_stress)
            extended = np.concatenate([training_stress, future_stress])
            fitness = self._ewma_sum(extended, self.tau_fitness)
            fatigue = self._ewma_sum(extended, self.tau_fatigue)

        predicted = base_vdot + self.k1 * fitness - self.k2 * fatigue
        return max(0.0, float(predicted))

    def fit(self, training_stress: np.ndarray, vdot_values: np.ndarray) -> None:
        """拟合模型参数"""
        try:
            popt, _ = curve_fit(
                self._banister_func,
                training_stress,
                vdot_values,
                p0=[self.tau_fitness, self.tau_fatigue, self.k1, self.k2],
                bounds=([30, 7, 0.0027, 0.030], [55, 14, 0.0049, 0.056]),
                maxfev=5000,
            )
            self.tau_fitness, self.tau_fatigue, self.k1, self.k2 = popt
            self._fitted = True
        except Exception as e:
            logger.warning(f"Banister IR拟合失败，使用默认参数: {e}")

    def _banister_func(
        self, stress: np.ndarray, tau1: float, tau2: float, k1: float, k2: float
    ) -> np.ndarray:
        """Banister函数用于curve_fit

        逐元素计算，返回与stress同形的数组，满足curve_fit对ydata形状的要求。
        """
        n = len(stress)
        result = np.zeros(n)
        for i in range(n):
            fitness = self._ewma_sum(stress[: i + 1], tau1)
            fatigue = self._ewma_sum(stress[: i + 1], tau2)
            result[i] = k1 * fitness - k2 * fatigue
        return result

    @staticmethod
    def _ewma_sum(values: np.ndarray, tau: float) -> float:
        """计算指数加权移动累计"""
        n = len(values)
        weights = np.exp(-np.arange(n) / tau)
        return float(np.dot(values, weights))
