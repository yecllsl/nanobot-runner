# 决策追踪业务逻辑层
# 封装EvolutionEngine调用，为CLI命令提供统一的业务接口

from __future__ import annotations

from datetime import datetime
from typing import Any

from src.core.base.context import AppContext, AppContextFactory
from src.core.evolution.evolution_engine import EvolutionEngine
from src.core.transparency.models import DecisionType


class EvolutionHandler:
    """决策追踪业务逻辑层

    封装EvolutionEngine的调用，为CLI命令提供统一的业务接口。
    负责参数转换（字符串→枚举/日期）和数据格式化（对象→字典）。

    Attributes:
        context: 应用上下文实例
    """

    def __init__(self, context: AppContext | None = None) -> None:
        if context is None:
            context = AppContextFactory.create()
        self.context = context

    def _get_engine(self) -> EvolutionEngine:
        """获取决策追踪引擎实例

        Returns:
            EvolutionEngine: 决策追踪引擎

        Raises:
            RuntimeError: 引擎未初始化时抛出
        """
        engine = self.context.evolution_engine
        if engine is None:
            raise RuntimeError("决策追踪引擎未初始化，请先运行 nanobotrun system init")
        return engine

    def get_history(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        decision_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """获取决策历史记录

        Args:
            start_date: 起始日期字符串（YYYY-MM-DD格式），可选
            end_date: 结束日期字符串（YYYY-MM-DD格式），可选
            decision_type: 决策类型字符串，可选

        Returns:
            list[dict]: 决策日志字典列表
        """
        engine = self._get_engine()

        # 日期参数转换
        start_dt: Any = None
        end_dt: Any = None
        if start_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        if end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")

        # 决策类型参数转换
        dtype: Any = None
        if decision_type:
            dtype = DecisionType(decision_type)

        decisions = engine.get_decision_history(
            start_date=start_dt,
            end_date=end_dt,
            decision_type=dtype,
        )
        return [d.to_dict() for d in decisions]

    def record_feedback(
        self,
        decision_id: str,
        score: int,
        text: str | None = None,
        accepted: bool | None = None,
    ) -> dict[str, Any]:
        """记录用户反馈

        Args:
            decision_id: 决策唯一标识
            score: 用户反馈评分（1-5）
            text: 用户反馈文本，可选
            accepted: 推荐是否被采纳，可选

        Returns:
            dict: 结果记录字典
        """
        engine = self._get_engine()
        outcome = engine.record_feedback(
            decision_id=decision_id,
            score=score,
            text=text,
            accepted=accepted,
        )
        return outcome.to_dict()

    def get_accuracy(self, days: int = 30) -> dict[str, Any]:
        """获取预测精度统计

        从EvolutionStore获取决策-结果配对，计算预测精度统计。
        按指定天数过滤结果记录。

        Args:
            days: 统计天数，默认30天

        Returns:
            dict: 预测精度统计字典
        """
        engine = self._get_engine()
        stats = engine.outcome_collector.get_accuracy_stats(days=days)
        return stats.to_dict()

    def get_fidelity(self, days: int = 30) -> dict[str, Any]:
        """获取执行忠实度统计

        从EvolutionStore获取结果记录，计算执行忠实度统计。
        按指定天数过滤结果记录。

        Args:
            days: 统计天数，默认30天

        Returns:
            dict: 执行忠实度统计字典
        """
        engine = self._get_engine()
        return engine.outcome_collector.get_fidelity_stats(days=days)

    def get_status(self) -> dict[str, Any]:
        """获取决策追踪整体状态

        Returns:
            dict: 决策追踪状态字典
        """
        engine = self._get_engine()
        return engine.get_evolution_status()
