from __future__ import annotations

import os
from dataclasses import dataclass, fields
from typing import Any


@dataclass(frozen=True)
class PredictionConfig:
    """预测模块配置

    管理ML模型参数、数据充足度阈值、Banister IR参数等。

    Attributes:
        gb_n_estimators: GradientBoosting树数量
        gb_learning_rate: GradientBoosting学习率
        gb_max_depth: GradientBoosting最大深度
        gb_min_samples_leaf: GradientBoosting叶节点最小样本数
        gb_subsample: GradientBoosting子采样率
        logistic_c: 逻辑回归正则化强度
        logistic_max_iter: 逻辑回归最大迭代次数
        vdot_min_months: VDOT预测最少数据月数
        vdot_min_records: VDOT预测最少记录数(ML层)
        vdot_parametric_min_records: VDOT参数化基线最少记录数
        race_min_races: 比赛预测最少比赛记录数
        injury_min_months: 伤病预测最少数据月数
        injury_min_records: 伤病预测最少记录数(ML层)
        injury_parametric_min_records: 伤病参数化基线最少记录数
        injury_min_hr_completeness: 伤病预测最低心率完整度
        banister_tau_fitness: Banister IR体能衰减时间常数
        banister_tau_fatigue: Banister IR疲劳衰减时间常数
        banister_k1: Banister IR体能增益系数
        banister_k2: Banister IR疲劳增益系数
        risk_warning_threshold: 风险预警阈值(0-1)
        pre_race_fatigue_adjustment_range: 赛前疲劳修正范围
        pre_race_recovery_adjustment_range: 赛前恢复修正范围
    """

    gb_n_estimators: int = 100
    gb_learning_rate: float = 0.05
    gb_max_depth: int = 5
    gb_min_samples_leaf: int = 30
    gb_subsample: float = 0.8
    logistic_c: float = 0.1
    logistic_max_iter: int = 1000
    vdot_min_months: int = 18
    vdot_min_records: int = 400
    vdot_parametric_min_records: int = 200
    race_min_races: int = 3
    injury_min_months: int = 12
    injury_min_records: int = 300
    injury_parametric_min_records: int = 100
    injury_min_hr_completeness: float = 0.5
    banister_tau_fitness: float = 42.0
    banister_tau_fatigue: float = 10.0
    banister_k1: float = 0.0038
    banister_k2: float = 0.043
    risk_warning_threshold: float = 0.7
    pre_race_fatigue_adjustment_range: tuple[float, float] = (0.0, 0.05)
    pre_race_recovery_adjustment_range: tuple[float, float] = (-0.03, 0.0)

    def __post_init__(self) -> None:
        if self.gb_n_estimators < 10:
            raise ValueError(f"gb_n_estimators必须≥10，当前为{self.gb_n_estimators}")
        if self.gb_learning_rate <= 0.0 or self.gb_learning_rate > 1.0:
            raise ValueError(
                f"gb_learning_rate必须在(0, 1]范围内，当前为{self.gb_learning_rate}"
            )
        if self.gb_max_depth < 1:
            raise ValueError(f"gb_max_depth必须≥1，当前为{self.gb_max_depth}")
        if self.vdot_min_months < 6:
            raise ValueError(f"vdot_min_months必须≥6，当前为{self.vdot_min_months}")
        if self.risk_warning_threshold <= 0.0 or self.risk_warning_threshold > 1.0:
            raise ValueError(
                f"risk_warning_threshold必须在(0, 1]范围内，当前为{self.risk_warning_threshold}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "gb_n_estimators": self.gb_n_estimators,
            "gb_learning_rate": self.gb_learning_rate,
            "gb_max_depth": self.gb_max_depth,
            "gb_min_samples_leaf": self.gb_min_samples_leaf,
            "gb_subsample": self.gb_subsample,
            "logistic_c": self.logistic_c,
            "logistic_max_iter": self.logistic_max_iter,
            "vdot_min_months": self.vdot_min_months,
            "vdot_min_records": self.vdot_min_records,
            "vdot_parametric_min_records": self.vdot_parametric_min_records,
            "race_min_races": self.race_min_races,
            "injury_min_months": self.injury_min_months,
            "injury_min_records": self.injury_min_records,
            "injury_parametric_min_records": self.injury_parametric_min_records,
            "injury_min_hr_completeness": self.injury_min_hr_completeness,
            "banister_tau_fitness": self.banister_tau_fitness,
            "banister_tau_fatigue": self.banister_tau_fatigue,
            "banister_k1": self.banister_k1,
            "banister_k2": self.banister_k2,
            "risk_warning_threshold": self.risk_warning_threshold,
            "pre_race_fatigue_adjustment_range": list(
                self.pre_race_fatigue_adjustment_range
            ),
            "pre_race_recovery_adjustment_range": list(
                self.pre_race_recovery_adjustment_range
            ),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PredictionConfig:
        """从字典创建配置，忽略无效key"""
        valid_keys = {
            f.name
            for f in fields(cls)
            if f.name != "pre_race_fatigue_adjustment_range"
            and f.name != "pre_race_recovery_adjustment_range"
        }
        filtered = {k: v for k, v in d.items() if k in valid_keys}
        if "pre_race_fatigue_adjustment_range" in d:
            val = d["pre_race_fatigue_adjustment_range"]
            if isinstance(val, list):
                val = tuple(val)
            filtered["pre_race_fatigue_adjustment_range"] = val
        if "pre_race_recovery_adjustment_range" in d:
            val = d["pre_race_recovery_adjustment_range"]
            if isinstance(val, list):
                val = tuple(val)
            filtered["pre_race_recovery_adjustment_range"] = val
        return cls(**filtered)

    @classmethod
    def from_env(cls) -> PredictionConfig:
        """从环境变量加载配置

        环境变量前缀为 NANOBOT_PREDICTION_
        """
        import contextlib

        def _get_env(key: str, default: str) -> str:
            return os.environ.get(key, default)

        kwargs: dict[str, Any] = {}
        for f in fields(cls):
            env_key = f"NANOBOT_PREDICTION_{f.name.upper()}"
            val = os.environ.get(env_key)
            if val is not None:
                if f.name in (
                    "pre_race_fatigue_adjustment_range",
                    "pre_race_recovery_adjustment_range",
                ):
                    parts = val.split(",")
                    if len(parts) == 2:
                        kwargs[f.name] = (float(parts[0]), float(parts[1]))
                elif f.type is int or f.type == "int":
                    with contextlib.suppress(ValueError):
                        kwargs[f.name] = int(val)
                elif f.type is float or f.type == "float":
                    with contextlib.suppress(ValueError):
                        kwargs[f.name] = float(val)
        return cls(**kwargs)
