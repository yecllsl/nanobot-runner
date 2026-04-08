# 分析处理 Handler
# 负责VDOT、训练负荷、心率漂移等分析的业务逻辑调用

from typing import Any, Dict, Optional

from src.agents.tools import RunnerTools
from src.core.context import AppContext, AppContextFactory


class AnalysisHandler:
    """分析业务逻辑"""

    def __init__(self, context: Optional[AppContext] = None) -> None:
        """
        初始化分析处理器

        Args:
            context: 应用上下文（可选），未提供则使用全局上下文
        """
        if context is None:
            context = AppContextFactory.create()

        self.context = context
        self.storage = context.storage
        self.engine = context.analytics

    def get_vdot_trend(self, limit: int = 10) -> list:
        """
        获取VDOT趋势数据

        Args:
            limit: 显示最近N条记录

        Returns:
            list: VDOT趋势数据
        """
        tools = RunnerTools(context=self.context)
        return tools.get_vdot_trend(limit=limit)

    def get_training_load(self, days: int = 42) -> Dict[str, Any]:
        """
        获取训练负荷数据

        Args:
            days: 分析天数

        Returns:
            dict: 训练负荷数据
        """
        return self.engine.get_training_load(days=days)

    def get_hr_drift_analysis(self) -> Dict[str, Any]:
        """
        获取心率漂移分析

        Returns:
            dict: 心率漂移分析结果
        """
        tools = RunnerTools(context=self.context)
        return tools.get_hr_drift_analysis()
