from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any

from src.core.base.logger import get_logger
from src.core.body_signal.models import (
    BodySignalAlert,
    BodySignalSummary,
    DataQuality,
)
from src.core.models.recovery import RecoveryStatus

if TYPE_CHECKING:
    from src.core.body_signal.fatigue_assessor import FatigueAssessor
    from src.core.body_signal.hrv_analyzer import HRVAnalyzer
    from src.core.body_signal.recovery_monitor import RecoveryMonitor
    from src.core.config.body_signal_config import BodySignalConfig

logger = get_logger(__name__)


class BodySignalEngine:
    """身体信号引擎

    整合HRV分析、疲劳度评估和恢复监控三个子模块，
    提供统一的每日/每周摘要和预警检查功能。
    """

    def __init__(
        self,
        hrv_analyzer: HRVAnalyzer,
        fatigue_assessor: FatigueAssessor,
        recovery_monitor: RecoveryMonitor,
        advice_engine: Any | None = None,
        config: BodySignalConfig | None = None,
    ) -> None:
        self.hrv_analyzer = hrv_analyzer
        self.fatigue_assessor = fatigue_assessor
        self.recovery_monitor = recovery_monitor
        self.advice_engine = advice_engine
        self.config = config
        self._daily_cache: BodySignalSummary | None = None
        self._cache_date: date | None = None

    def get_daily_summary(self) -> BodySignalSummary:
        """获取每日身体信号摘要

        整合HRV分析、疲劳度评估和恢复状态，生成每日摘要。
        同一天内重复调用返回缓存结果。

        Returns:
            BodySignalSummary: 身体信号摘要
        """
        today = date.today()
        if self._daily_cache is not None and self._cache_date == today:
            return self._daily_cache

        hrv_result = self.hrv_analyzer.analyze_hrv(days=30)
        fatigue_result = self.fatigue_assessor.assess_fatigue()
        recovery_result = self.recovery_monitor.get_recovery_status()

        merged_status = self._merge_recovery_status(
            fatigue_result.recovery_status, recovery_result.recovery_status
        )
        merged_quality = self._merge_data_quality(
            hrv_result.data_quality, fatigue_result.data_quality
        )

        alerts = self.check_alerts()

        daily_summary = (
            f"今日状态: {self._status_to_emoji(merged_status)} {merged_status.value}"
        )
        training_advice = self._generate_training_advice(
            merged_status, fatigue_result.fatigue_score, alerts
        )

        summary = BodySignalSummary(
            recovery_status=merged_status,
            fatigue_score=fatigue_result.fatigue_score,
            data_quality=merged_quality,
            daily_summary=daily_summary,
            training_advice=training_advice,
            alerts=alerts,
        )

        self._daily_cache = summary
        self._cache_date = today

        return summary

    def get_weekly_summary(self) -> BodySignalSummary:
        """获取每周身体信号摘要

        Returns:
            BodySignalSummary: 身体信号周摘要
        """
        hrv_result = self.hrv_analyzer.analyze_hrv(days=30)
        fatigue_result = self.fatigue_assessor.assess_fatigue()
        recovery_result = self.recovery_monitor.get_recovery_status()

        merged_status = self._merge_recovery_status(
            fatigue_result.recovery_status, recovery_result.recovery_status
        )
        merged_quality = self._merge_data_quality(
            hrv_result.data_quality, fatigue_result.data_quality
        )

        alerts = self.check_alerts()

        daily_summary = (
            f"本周状态: {self._status_to_emoji(merged_status)} {merged_status.value}"
        )
        training_advice = self._generate_training_advice(
            merged_status, fatigue_result.fatigue_score, alerts
        )

        return BodySignalSummary(
            recovery_status=merged_status,
            fatigue_score=fatigue_result.fatigue_score,
            data_quality=merged_quality,
            daily_summary=daily_summary,
            training_advice=training_advice,
            alerts=alerts,
        )

    def check_alerts(self) -> list[BodySignalAlert]:
        """检查身体信号预警

        检测心率异常升高和过度训练风险。

        Returns:
            list[BodySignalAlert]: 预警列表
        """
        alerts: list[BodySignalAlert] = []

        try:
            hr_trend = self.hrv_analyzer.get_resting_hr_trend(days=7)
            if len(hr_trend) >= 2:
                latest = hr_trend[-1]
                if latest.deviation_pct > 10.0:
                    alerts.append(
                        BodySignalAlert(
                            alert_type="hr_spike",
                            severity="warning",
                            message=f"静息心率异常升高 {latest.deviation_pct:.1f}%",
                            details={"deviation_pct": latest.deviation_pct},
                        )
                    )
        except Exception as e:
            logger.warning(f"心率预警检查失败: {e}")

        try:
            recovery_trend = self.recovery_monitor.get_recovery_trend(days=7)
            overtraining_days = sum(1 for p in recovery_trend if p.tsb < -20.0)
            if overtraining_days >= 3:
                alerts.append(
                    BodySignalAlert(
                        alert_type="overtraining",
                        severity="critical",
                        message=f"连续{overtraining_days}天过度训练",
                        details={"overtraining_days": overtraining_days},
                    )
                )
        except Exception as e:
            logger.warning(f"过度训练预警检查失败: {e}")

        return alerts

    def _merge_recovery_status(
        self, status1: RecoveryStatus, status2: RecoveryStatus
    ) -> RecoveryStatus:
        """合并两个恢复状态，取较严重的那个"""
        severity = {
            RecoveryStatus.GREEN: 0,
            RecoveryStatus.YELLOW: 1,
            RecoveryStatus.RED: 2,
        }
        if severity.get(status1, 0) >= severity.get(status2, 0):
            return status1
        return status2

    def _merge_data_quality(
        self, quality1: DataQuality, quality2: DataQuality
    ) -> DataQuality:
        """合并两个数据质量，取较差的那个"""
        severity = {
            DataQuality.SUFFICIENT: 0,
            DataQuality.INSUFFICIENT: 1,
            DataQuality.EMPTY: 2,
        }
        if severity.get(quality1, 0) >= severity.get(quality2, 0):
            return quality1
        return quality2

    def _status_to_emoji(self, status: RecoveryStatus) -> str:
        """将恢复状态转换为emoji"""
        emoji_map = {
            RecoveryStatus.GREEN: "🟢",
            RecoveryStatus.YELLOW: "🟡",
            RecoveryStatus.RED: "🔴",
        }
        return emoji_map.get(status, "⚪")

    def _generate_training_advice(
        self,
        recovery_status: RecoveryStatus,
        fatigue_score: float,
        alerts: list[BodySignalAlert],
    ) -> str:
        """根据恢复状态和预警生成训练建议"""
        critical_alerts = [a for a in alerts if a.severity == "critical"]
        if critical_alerts:
            return "⚠️ 存在严重预警，建议完全休息，暂停训练"

        if recovery_status == RecoveryStatus.RED:
            return "身体疲劳度较高，建议降低训练强度或安排休息日"

        if recovery_status == RecoveryStatus.YELLOW:
            return "身体状态一般，建议以轻松跑为主，注意恢复"

        return "体能充沛，可以正常训练"
