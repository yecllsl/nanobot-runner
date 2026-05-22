# 提示调优器模块
# 管理4维连续参数空间的自动/手动调整，基于用户反馈和接受率驱动参数进化

from __future__ import annotations

from src.core.base.logger import get_logger
from src.core.evolution.config import EvolutionConfig
from src.core.evolution.evolution_store import EvolutionStore
from src.core.evolution.models import PromptTuningParams

logger = get_logger(__name__)

# 默认调整步长和最大调整幅度
_DEFAULT_TUNING_STEP: float = 0.05
_DEFAULT_TUNING_MAX_ADJUSTMENT: float = 0.1
# 拒绝调整步长（aggressive用标准步长，data_driven用半步长）
_REJECTION_DATA_DRIVEN_STEP: float = 0.025


class PromptTuner:
    """提示调优器

    管理4维连续参数空间（语气强度、信息密度、推荐激进程度、数据驱动权重），
    支持手动更新和基于反馈/拒绝的自动调整。

    调整策略:
        - 基于反馈(avg_score, acceptance_rate): 4个维度根据评分和接受率独立调整
        - 基于拒绝: 降低aggressive和data_driven权重
        - 单次调整幅度不超过max_adjustment，防止参数剧烈波动

    Attributes:
        _store: EvolutionStore实例，负责持久化
        _config: EvolutionConfig配置
        _params: 缓存的当前参数（首次加载后缓存）
        _tuning_step: 调整步长（默认0.05）
        _tuning_max_adjustment: 单次最大调整幅度（默认0.1，即2*step）
    """

    def __init__(
        self,
        store: EvolutionStore,
        config: EvolutionConfig,
    ) -> None:
        """初始化提示调优器

        Args:
            store: EvolutionStore实例，负责持久化
            config: EvolutionConfig配置实例
        """
        self._store = store
        self._config = config
        self._params: PromptTuningParams | None = None
        # EvolutionConfig暂无tuning相关字段，使用合理默认值
        self._tuning_step: float = _DEFAULT_TUNING_STEP
        self._tuning_max_adjustment: float = _DEFAULT_TUNING_MAX_ADJUSTMENT

    def get_params(self) -> PromptTuningParams:
        """获取当前提示调优参数

        首次调用时从store加载，若store中无数据则返回默认参数。
        后续调用直接返回缓存的参数。

        Returns:
            PromptTuningParams: 当前提示调优参数
        """
        if self._params is not None:
            return self._params
        self._params = self._load_params()
        return self._params

    def update_params(
        self,
        tone: float | None = None,
        detail: float | None = None,
        aggressive: float | None = None,
        data_driven: float | None = None,
    ) -> PromptTuningParams:
        """手动更新提示调优参数

        仅更新指定的参数，未指定的参数保持不变。
        更新后自动持久化到store。

        Args:
            tone: 新的语气强度（None保持不变）
            detail: 新的信息密度（None保持不变）
            aggressive: 新的推荐激进程度（None保持不变）
            data_driven: 新的数据驱动权重（None保持不变）

        Returns:
            PromptTuningParams: 更新后的参数
        """
        current = self.get_params()
        updated = current.with_updates(
            tone=tone,
            detail=detail,
            aggressive=aggressive,
            data_driven=data_driven,
        )
        self._save_params(updated)
        self._params = updated
        logger.info(
            "手动更新提示参数: tone=%.2f, detail=%.2f, aggressive=%.2f, data_driven=%.2f",
            updated.tone_intensity,
            updated.detail_level_score,
            updated.recommendation_aggressiveness,
            updated.data_driven_weight,
        )
        return updated

    def auto_adjust_on_feedback(
        self, avg_score: float, acceptance_rate: float
    ) -> PromptTuningParams:
        """基于用户反馈自动调整参数

        根据平均评分和接受率调整4个维度:
            - tone: avg_score < 3 → 降低（用户不喜欢当前语气），avg_score > 4 → 提高
            - aggressive: acceptance_rate < 0.3 → 降低（推荐太激进），acceptance_rate > 0.7 → 提高
            - detail: avg_score < 3 → 降低（信息过多），avg_score > 4 → 提高
            - data_driven: acceptance_rate > 0.7 → 提高，acceptance_rate < 0.3 → 降低

        每个维度的调整幅度不超过tuning_max_adjustment。

        Args:
            avg_score: 平均用户反馈评分（1-5）
            acceptance_rate: 推荐接受率（0.0-1.0）

        Returns:
            PromptTuningParams: 调整后的参数
        """
        current = self.get_params()
        step = self._tuning_step
        max_adj = self._tuning_max_adjustment

        # 计算各维度调整量
        tone_delta = 0.0
        if avg_score < 3.0:
            # 低评分：降低语气强度
            tone_delta = -min(step, max_adj)
        elif avg_score > 4.0:
            # 高评分：微幅提高语气强度
            tone_delta = min(step, max_adj)

        aggressive_delta = 0.0
        if acceptance_rate < 0.3:
            # 低接受率：降低推荐激进程度
            aggressive_delta = -min(step, max_adj)
        elif acceptance_rate > 0.7:
            # 高接受率：微幅提高推荐激进程度
            aggressive_delta = min(step, max_adj)

        detail_delta = 0.0
        if avg_score < 3.0:
            # 低评分：降低信息密度
            detail_delta = -min(step, max_adj)
        elif avg_score > 4.0:
            # 高评分：提高信息密度
            detail_delta = min(step, max_adj)

        data_driven_delta = 0.0
        if acceptance_rate > 0.7:
            # 高接受率：提高数据驱动权重
            data_driven_delta = min(step, max_adj)
        elif acceptance_rate < 0.3:
            # 低接受率：降低数据驱动权重
            data_driven_delta = -min(step, max_adj)

        # 应用调整，with_updates内部会clamp到[0.0, 1.0]
        updated = current.with_updates(
            tone=current.tone_intensity + tone_delta,
            detail=current.detail_level_score + detail_delta,
            aggressive=current.recommendation_aggressiveness + aggressive_delta,
            data_driven=current.data_driven_weight + data_driven_delta,
        )
        self._save_params(updated)
        self._params = updated
        logger.info(
            "反馈自动调整: avg_score=%.1f, acceptance_rate=%.1f, "
            "tone=%.2f, detail=%.2f, aggressive=%.2f, data_driven=%.2f",
            avg_score,
            acceptance_rate,
            updated.tone_intensity,
            updated.detail_level_score,
            updated.recommendation_aggressiveness,
            updated.data_driven_weight,
        )
        return updated

    def auto_adjust_on_rejection(self) -> PromptTuningParams:
        """连续拒绝时自动调整参数

        降低推荐激进程度（标准步长0.05）和数据驱动权重（半步长0.025），
        使后续推荐更保守、更贴近用户偏好。

        Returns:
            PromptTuningParams: 调整后的参数
        """
        current = self.get_params()
        step = self._tuning_step
        max_adj = self._tuning_max_adjustment

        # 降低aggressive（标准步长）和data_driven（半步长）
        aggressive_delta = -min(step, max_adj)
        data_driven_delta = -min(_REJECTION_DATA_DRIVEN_STEP, max_adj)

        updated = current.with_updates(
            aggressive=current.recommendation_aggressiveness + aggressive_delta,
            data_driven=current.data_driven_weight + data_driven_delta,
        )
        self._save_params(updated)
        self._params = updated
        logger.info(
            "拒绝自动调整: aggressive=%.2f, data_driven=%.2f",
            updated.recommendation_aggressiveness,
            updated.data_driven_weight,
        )
        return updated

    def reset_to_default(self) -> PromptTuningParams:
        """重置所有参数为默认值（0.5）

        清除所有个性化调整，恢复中性参数。

        Returns:
            PromptTuningParams: 重置后的默认参数
        """
        default_params = PromptTuningParams.default()
        self._save_params(default_params)
        self._params = default_params
        logger.info("提示参数已重置为默认值")
        return default_params

    def _save_params(self, params: PromptTuningParams) -> None:
        """持久化参数到store

        Args:
            params: 要保存的提示调优参数
        """
        self._store.save_prompt_tuning_params(params)

    def _load_params(self) -> PromptTuningParams:
        """从store加载参数

        若store中无数据，返回默认参数。

        Returns:
            PromptTuningParams: 加载的参数或默认参数
        """
        loaded = self._store.load_prompt_tuning_params()
        if loaded is None:
            return PromptTuningParams.default()
        return loaded
