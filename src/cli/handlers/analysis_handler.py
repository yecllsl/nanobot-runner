from typing import Any

from src.agents.tools import RunnerTools
from src.core.base.context import AppContext, AppContextFactory


class AnalysisHandler:
    """分析业务逻辑"""

    def __init__(self, context: AppContext | None = None) -> None:
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

    def _get_body_signal_engine(self):
        """获取身体信号引擎（通过AppContext统一装配）"""
        return self.context.body_signal_engine

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

    def get_training_load(self, days: int = 42) -> dict[str, Any]:
        """
        获取训练负荷数据

        Args:
            days: 分析天数

        Returns:
            dict: 训练负荷数据
        """
        return self.engine.get_training_load(days=days)

    def get_hr_drift_analysis(self) -> dict[str, Any]:
        """
        获取心率漂移分析

        Returns:
            dict: 心率漂移分析结果
        """
        tools = RunnerTools(context=self.context)
        return tools.get_hr_drift_analysis()

    def get_hrv_analysis(self, days: int = 30) -> dict[str, Any]:
        """获取HRV分析结果"""
        engine = self._get_body_signal_engine()
        hrv_result = engine.hrv_analyzer.analyze_hrv(days=days)
        hrv_metrics = engine.hrv_analyzer.estimate_hrv_metrics()

        result = hrv_result.to_dict()
        result["estimated_hrv_metrics"] = hrv_metrics.to_dict()
        return result

    def get_hr_recovery(self) -> dict[str, Any]:
        """获取心率恢复分析"""
        engine = self._get_body_signal_engine()
        recovery_result = engine.hrv_analyzer.analyze_hr_recovery()
        return recovery_result.to_dict()

    def get_fatigue_score(self, rpe: int | None = None) -> dict[str, Any]:
        """获取疲劳度评估"""
        engine = self._get_body_signal_engine()
        fatigue_result = engine.fatigue_assessor.assess_fatigue(rpe=rpe)
        return fatigue_result.to_dict()

    def get_recovery_status(self) -> dict[str, Any]:
        """获取恢复状态"""
        engine = self._get_body_signal_engine()
        recovery_result = engine.recovery_monitor.get_recovery_status()
        return recovery_result.to_dict()

    def compare_training_periods(
        self, period1_days: int = 7, period2_days: int = 7
    ) -> dict[str, Any]:
        """对比两个训练周期的身体信号变化"""
        engine = self._get_body_signal_engine()

        trend1 = engine.recovery_monitor.get_recovery_trend(days=period1_days)
        trend2 = engine.recovery_monitor.get_recovery_trend(
            days=period2_days + period1_days
        )
        trend2 = trend2[:-period1_days] if len(trend2) > period1_days else []

        avg_tsb1 = sum(p.tsb for p in trend1) / len(trend1) if trend1 else 0.0
        avg_tsb2 = sum(p.tsb for p in trend2) / len(trend2) if trend2 else 0.0

        hrv1 = engine.hrv_analyzer.analyze_hrv(days=period1_days)
        hrv2 = engine.hrv_analyzer.analyze_hrv(days=period2_days + period1_days)

        return {
            "period1_days": period1_days,
            "period2_days": period2_days,
            "period1": {
                "avg_tsb": round(avg_tsb1, 2),
                "data_points": len(trend1),
                "hrv_data_quality": hrv1.data_quality.value,
            },
            "period2": {
                "avg_tsb": round(avg_tsb2, 2),
                "data_points": len(trend2),
                "hrv_data_quality": hrv2.data_quality.value,
            },
            "tsb_change": round(avg_tsb1 - avg_tsb2, 2),
            "comparison_summary": (
                "近期恢复状态改善" if avg_tsb1 > avg_tsb2 else "近期恢复状态下降"
            ),
        }
