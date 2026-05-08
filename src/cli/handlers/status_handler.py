# 状态查看 Handler
# 负责今日/本周身体状态的业务逻辑调用

from typing import Any

from src.core.base.context import AppContext, AppContextFactory
from src.core.body_signal import BodySignalEngine
from src.core.body_signal.fatigue_assessor import FatigueAssessor
from src.core.body_signal.hrv_analyzer import HRVAnalyzer
from src.core.body_signal.recovery_monitor import RecoveryMonitor


class StatusHandler:
    """状态查看业务逻辑"""

    def __init__(self, context: AppContext | None = None) -> None:
        if context is None:
            context = AppContextFactory.create()

        self.context = context
        self._engine: BodySignalEngine | None = None

    def _get_engine(self) -> BodySignalEngine:
        """获取或创建 BodySignalEngine 实例"""
        if self._engine is None:
            hrv_analyzer = HRVAnalyzer(session_repo=self.context.session_repo)
            from src.core.calculators.training_load_analyzer import TrainingLoadAnalyzer

            training_load_analyzer = TrainingLoadAnalyzer()
            fatigue_assessor = FatigueAssessor(
                session_repo=self.context.session_repo,
                training_load_analyzer=training_load_analyzer,
            )
            recovery_monitor = RecoveryMonitor(
                session_repo=self.context.session_repo,
                training_load_analyzer=training_load_analyzer,
                hrv_analyzer=hrv_analyzer,
            )
            self._engine = BodySignalEngine(
                hrv_analyzer=hrv_analyzer,
                fatigue_assessor=fatigue_assessor,
                recovery_monitor=recovery_monitor,
            )
        return self._engine

    def get_today_status(self) -> dict[str, Any]:
        """获取今日身体状态"""
        engine = self._get_engine()
        summary = engine.get_daily_summary()
        return summary.to_dict()

    def get_weekly_status(self) -> dict[str, Any]:
        """获取本周身体状态"""
        engine = self._get_engine()
        summary = engine.get_weekly_summary()
        return summary.to_dict()
