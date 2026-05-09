from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

try:
    import joblib
    from sklearn.linear_model import LogisticRegression

    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


class LogisticInjuryModel:
    """逻辑回归伤病风险模型

    当scikit-learn可用时使用真实模型，
    不可用时退化为基于规则的简单概率映射。
    """

    N_FEATURES = 8

    def __init__(self) -> None:
        self._model: Any = None
        self._fitted = False
        if HAS_SKLEARN:
            self._model = LogisticRegression(max_iter=1000, random_state=42)

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        """训练模型"""
        if not HAS_SKLEARN:
            logger.warning("scikit-learn不可用，跳过训练")
            return
        if X.shape[1] != self.N_FEATURES:
            raise ValueError(f"期望{self.N_FEATURES}个特征，得到{X.shape[1]}个")
        self._model.fit(X, y)
        self._fitted = True

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """预测伤病概率"""
        if HAS_SKLEARN and self._fitted:
            probas = self._model.predict_proba(X)
            return probas[:, 1]

        return self._fallback_proba(X)

    def save(self, path: str) -> None:
        """保存模型"""
        if not HAS_SKLEARN or not self._fitted:
            logger.warning("模型未训练或scikit-learn不可用，跳过保存")
            return
        joblib.dump(self._model, path)

    def load(self, path: str) -> None:
        """加载模型"""
        if not HAS_SKLEARN:
            logger.warning("scikit-learn不可用，跳过加载")
            return
        if not Path(path).exists():
            raise FileNotFoundError(f"模型文件不存在: {path}")
        self._model = joblib.load(path)
        self._fitted = True

    def _fallback_proba(self, X: np.ndarray) -> np.ndarray:
        """无scikit-learn时的退避预测"""
        acwr = X[:, 0] if X.shape[1] > 0 else np.ones(X.shape[0])
        probas = 1.0 / (1.0 + np.exp(-5.0 * (acwr - 1.5)))
        return probas
