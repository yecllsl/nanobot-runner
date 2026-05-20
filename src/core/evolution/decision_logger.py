# 决策日志记录器
# 提供决策日志的记录、执行状态更新、历史查询等高层接口
# 委托EvolutionStore完成底层持久化操作

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from typing import Any

from src.core.base.logger import get_logger
from src.core.evolution.config import EvolutionConfig
from src.core.evolution.evolution_store import EvolutionStore
from src.core.evolution.models import DecisionLog
from src.core.transparency.models import DecisionType

logger = get_logger(__name__)


class DecisionLogger:
    """决策日志记录器

    提供决策日志的记录、执行状态更新、历史查询等高层接口。
    内部委托EvolutionStore完成持久化操作，对frozen dataclass的更新
    通过dataclasses.replace重建对象并调用store.update_decision实现。

    Attributes:
        runner_state_fields: 跑者状态追踪字段列表，从配置获取
    """

    def __init__(
        self, store: EvolutionStore, config: EvolutionConfig | None = None
    ) -> None:
        """初始化决策日志记录器

        Args:
            store: 决策追踪存储层实例
            config: 决策追踪模块配置，为None时使用默认配置
        """
        self._store = store
        self._config = config or EvolutionConfig()

    @property
    def runner_state_fields(self) -> list[str]:
        """获取跑者状态追踪字段列表

        Returns:
            list[str]: 字段名称列表
        """
        return list(self._config.runner_state_fields)

    def log_decision(self, decision: DecisionLog) -> str:
        """记录决策日志，持久化到存储层

        Args:
            decision: 决策日志对象

        Returns:
            str: 决策唯一标识decision_id
        """
        self._store.save_decision(decision)
        logger.info(
            "决策已记录: decision_id=%s, type=%s",
            decision.decision_id,
            decision.decision_type.value,
        )
        return decision.decision_id

    def update_execution_status(
        self,
        decision_id: str,
        status: str,
        accepted: bool | None = None,
    ) -> bool:
        """更新决策的执行状态

        由于DecisionLog是frozen dataclass，需要通过dataclasses.replace
        重建整个对象。更新后委托EvolutionStore.update_decision完成Parquet原子写入。

        Args:
            decision_id: 决策唯一标识
            status: 新的执行状态（pending/executed/skipped/modified/failed）
            accepted: 推荐是否被采纳（可选，None表示不更新该字段）

        Returns:
            bool: 更新成功返回True，决策不存在返回False
        """
        existing = self._store.get_decision_by_id(decision_id)
        if existing is None:
            logger.warning("更新执行状态失败: 决策不存在, decision_id=%s", decision_id)
            return False

        # frozen dataclass，使用dataclasses.replace重建对象
        update_kwargs: dict[str, Any] = {"execution_status": status}
        if accepted is not None:
            update_kwargs["recommendation_accepted"] = accepted
        updated = replace(existing, **update_kwargs)

        # 委托store完成Parquet原子更新
        success = self._store.update_decision(updated)
        if success:
            logger.info(
                "执行状态已更新: decision_id=%s, status=%s, accepted=%s",
                decision_id,
                status,
                accepted,
            )
        return success

    def get_decision_history(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        decision_type: DecisionType | None = None,
        limit: int = 100,
    ) -> list[DecisionLog]:
        """获取决策历史记录

        按时间倒序返回符合条件的决策日志列表。

        Args:
            start_date: 起始日期过滤（可选）
            end_date: 结束日期过滤（可选）
            decision_type: 决策类型过滤（可选）
            limit: 返回数量限制，默认100

        Returns:
            list[DecisionLog]: 符合条件的决策日志列表
        """
        return self._store.query_decisions(
            start_date=start_date,
            end_date=end_date,
            decision_type=decision_type,
            limit=limit,
        )

    def get_decision_by_id(self, decision_id: str) -> DecisionLog | None:
        """根据决策ID获取决策日志

        Args:
            decision_id: 决策唯一标识

        Returns:
            DecisionLog | None: 决策日志对象，未找到返回None
        """
        return self._store.get_decision_by_id(decision_id)
