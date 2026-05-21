# 决策追踪模块配置
# 管理异步写入、反馈提示频率、跑者状态字段等配置

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Any


@dataclass(frozen=True)
class EvolutionConfig:
    """决策追踪模块配置（不可变数据类）

    管理决策日志存储路径、异步写入参数、反馈提示频率、
    跑者状态追踪字段等配置项。

    Attributes:
        data_dir: 数据存储目录
        async_write_enabled: 是否启用异步写入
        async_write_queue_size: 异步写入队列大小
        async_write_max_retries: 异步写入最大重试次数
        async_write_retry_backoff: 异步写入重试退避时间（秒）
        feedback_prompt_frequency: 每N次决策提示一次反馈
        runner_state_fields: 跑者状态追踪字段列表
    """

    data_dir: str = "~/.nanobot-runner"
    async_write_enabled: bool = False
    async_write_queue_size: int = 100
    async_write_max_retries: int = 3
    async_write_retry_backoff: float = 1.0
    feedback_prompt_frequency: int = 3
    runner_state_fields: list[str] = field(
        default_factory=lambda: ["vdot", "ctl", "atl", "tsb", "fatigue_score"]
    )

    # v0.24 校准配置
    calibration_alpha: float = 0.7
    calibration_max_amplitude: float = 0.10
    calibration_min_samples: int = 10
    response_min_fidelity: float = 0.7
    response_min_samples_per_type: int = 5
    window_min_months: int = 6

    def __post_init__(self) -> None:
        """验证配置参数合法性"""
        if self.feedback_prompt_frequency < 1:
            raise ValueError(
                f"feedback_prompt_frequency必须>=1，当前为{self.feedback_prompt_frequency}"
            )
        if self.async_write_queue_size < 1:
            raise ValueError(
                f"async_write_queue_size必须>=1，当前为{self.async_write_queue_size}"
            )
        if self.async_write_max_retries < 0:
            raise ValueError(
                f"async_write_max_retries必须>=0，当前为{self.async_write_max_retries}"
            )

        # v0.24 校准参数校验
        if self.calibration_alpha <= 0.0 or self.calibration_alpha > 1.0:
            raise ValueError(
                f"calibration_alpha必须在(0, 1]范围内，当前为{self.calibration_alpha}"
            )
        if (
            self.calibration_max_amplitude <= 0.0
            or self.calibration_max_amplitude > 1.0
        ):
            raise ValueError(
                f"calibration_max_amplitude必须在(0, 1]范围内，当前为{self.calibration_max_amplitude}"
            )
        if self.calibration_min_samples < 1:
            raise ValueError(
                f"calibration_min_samples必须>=1，当前为{self.calibration_min_samples}"
            )
        if self.response_min_fidelity <= 0.0 or self.response_min_fidelity > 1.0:
            raise ValueError(
                f"response_min_fidelity必须在(0, 1]范围内，当前为{self.response_min_fidelity}"
            )
        if self.response_min_samples_per_type < 1:
            raise ValueError(
                f"response_min_samples_per_type必须>=1，当前为{self.response_min_samples_per_type}"
            )
        if self.window_min_months < 1:
            raise ValueError(
                f"window_min_months必须>=1，当前为{self.window_min_months}"
            )

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式

        Returns:
            包含所有配置项的字典
        """
        return {
            "data_dir": self.data_dir,
            "async_write_enabled": self.async_write_enabled,
            "async_write_queue_size": self.async_write_queue_size,
            "async_write_max_retries": self.async_write_max_retries,
            "async_write_retry_backoff": self.async_write_retry_backoff,
            "feedback_prompt_frequency": self.feedback_prompt_frequency,
            "runner_state_fields": list(self.runner_state_fields),
            "calibration_alpha": self.calibration_alpha,
            "calibration_max_amplitude": self.calibration_max_amplitude,
            "calibration_min_samples": self.calibration_min_samples,
            "response_min_fidelity": self.response_min_fidelity,
            "response_min_samples_per_type": self.response_min_samples_per_type,
            "window_min_months": self.window_min_months,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> EvolutionConfig:
        """从字典创建配置，忽略无效key

        仅提取与EvolutionConfig字段名匹配的key，忽略字典中
        不属于该配置类的key，避免因多余字段导致实例化失败。

        Args:
            d: 配置字典

        Returns:
            EvolutionConfig实例
        """
        valid_keys = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in d.items() if k in valid_keys}
        return cls(**filtered)
