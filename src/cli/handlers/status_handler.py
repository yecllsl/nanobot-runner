from typing import Any

from src.core.base.context import AppContext, AppContextFactory


class StatusHandler:
    """状态查看业务逻辑"""

    def __init__(self, context: AppContext | None = None) -> None:
        if context is None:
            context = AppContextFactory.create()

        self.context = context

    def _get_engine(self):
        """获取身体信号引擎（通过AppContext统一装配）"""
        return self.context.body_signal_engine

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
