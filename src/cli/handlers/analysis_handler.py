# 分析处理 Handler
# 负责VDOT、训练负荷、心率漂移等分析的业务逻辑调用

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
        from src.core.body_signal.hrv_analyzer import HRVAnalyzer

        hrv_analyzer = HRVAnalyzer(session_repo=self.context.session_repo)
        hrv_result = hrv_analyzer.analyze_hrv(days=days)
        hrv_metrics = hrv_analyzer.estimate_hrv_metrics()

        result = hrv_result.to_dict()
        result["estimated_hrv_metrics"] = hrv_metrics
        return result

    def get_hr_recovery(self) -> dict[str, Any]:
        """获取心率恢复分析"""
        from src.core.body_signal.hrv_analyzer import HRVAnalyzer

        hrv_analyzer = HRVAnalyzer(session_repo=self.context.session_repo)
        recovery_result = hrv_analyzer.analyze_hr_recovery()
        return recovery_result.to_dict()

    def get_fatigue_score(self, rpe: int | None = None) -> dict[str, Any]:
        """获取疲劳度评估"""
        from src.core.body_signal.fatigue_assessor import FatigueAssessor
        from src.core.calculators.training_load_analyzer import TrainingLoadAnalyzer

        training_load_analyzer = TrainingLoadAnalyzer()
        fatigue_assessor = FatigueAssessor(
            session_repo=self.context.session_repo,
            training_load_analyzer=training_load_analyzer,
        )
        fatigue_result = fatigue_assessor.assess_fatigue(rpe=rpe)
        return fatigue_result.to_dict()

    def get_recovery_status(self) -> dict[str, Any]:
        """获取恢复状态"""
        from src.core.body_signal.hrv_analyzer import HRVAnalyzer
        from src.core.body_signal.recovery_monitor import RecoveryMonitor
        from src.core.calculators.training_load_analyzer import TrainingLoadAnalyzer

        training_load_analyzer = TrainingLoadAnalyzer()
        hrv_analyzer = HRVAnalyzer(session_repo=self.context.session_repo)
        recovery_monitor = RecoveryMonitor(
            session_repo=self.context.session_repo,
            training_load_analyzer=training_load_analyzer,
            hrv_analyzer=hrv_analyzer,
        )
        recovery_result = recovery_monitor.get_recovery_status()
        return recovery_result.to_dict()

    def compare_training_periods(
        self, period1_days: int = 7, period2_days: int = 7
    ) -> dict[str, Any]:
        """对比两个训练周期的身体信号变化"""
        from src.core.body_signal.hrv_analyzer import HRVAnalyzer
        from src.core.body_signal.recovery_monitor import RecoveryMonitor
        from src.core.calculators.training_load_analyzer import TrainingLoadAnalyzer

        training_load_analyzer = TrainingLoadAnalyzer()
        hrv_analyzer = HRVAnalyzer(session_repo=self.context.session_repo)
        recovery_monitor = RecoveryMonitor(
            session_repo=self.context.session_repo,
            training_load_analyzer=training_load_analyzer,
            hrv_analyzer=hrv_analyzer,
        )

        # 获取最近两个周期的恢复趋势
        trend1 = recovery_monitor.get_recovery_trend(days=period1_days)
        trend2 = recovery_monitor.get_recovery_trend(days=period2_days + period1_days)
        # 取更早的 period2_days 数据
        trend2 = trend2[:-period1_days] if len(trend2) > period1_days else []

        avg_tsb1 = sum(p.tsb for p in trend1) / len(trend1) if trend1 else 0.0
        avg_tsb2 = sum(p.tsb for p in trend2) / len(trend2) if trend2 else 0.0

        hrv1 = hrv_analyzer.analyze_hrv(days=period1_days)
        hrv2 = hrv_analyzer.analyze_hrv(days=period2_days + period1_days)

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
