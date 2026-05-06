from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import polars as pl

from src.core.base.logger import get_logger
from src.core.body_signal.models import (
    DataQuality,
    RecoveryPoint,
    RecoveryStatusResult,
    RestDayEffect,
)
from src.core.config.body_signal_config import BodySignalConfig
from src.core.models.recovery import RecoveryStatus

if TYPE_CHECKING:
    from src.core.body_signal.hrv_analyzer import HRVAnalyzer
    from src.core.calculators.training_load_analyzer import TrainingLoadAnalyzer
    from src.core.storage.session_repository import SessionRepository

logger = get_logger(__name__)


class RecoveryMonitor:
    """恢复监控器

    综合训练负荷和心率数据，评估恢复状态、休息日效果和恢复趋势。
    """

    def __init__(
        self,
        session_repo: SessionRepository,
        training_load_analyzer: TrainingLoadAnalyzer,
        hrv_analyzer: HRVAnalyzer,
        config: BodySignalConfig | None = None,
    ) -> None:
        self.session_repo = session_repo
        self.training_load_analyzer = training_load_analyzer
        self.hrv_analyzer = hrv_analyzer
        self.config = config or BodySignalConfig()

    def get_recovery_status(self) -> RecoveryStatusResult:
        """获取当前恢复状态

        综合TSB和心率数据评估恢复状态。

        Returns:
            RecoveryStatusResult: 恢复状态结果
        """
        load_data = self.training_load_analyzer.calculate_training_load_from_dataframe(
            pl.DataFrame()
        )
        tsb = float(load_data.get("tsb", 0.0))
        runs_count = int(load_data.get("runs_count", 0))

        if runs_count == 0:
            return RecoveryStatusResult(
                recovery_status=RecoveryStatus.GREEN,
                rest_day_effect=RestDayEffect(
                    resting_hr_change_pct=0.0,
                    tsb_change=0.0,
                    effect_level="minimal",
                    message="暂无训练数据",
                ),
                recovery_trend=[],
                data_quality=DataQuality.EMPTY,
            )

        tsb_capped = min(tsb, self.config.tsb_cap)

        if tsb_capped < self.config.overtraining_tsb_threshold:
            recovery_status = RecoveryStatus.RED
        elif tsb_capped < 0:
            recovery_status = RecoveryStatus.YELLOW
        else:
            recovery_status = RecoveryStatus.GREEN

        rest_day_effect = self.check_rest_day_effect()

        return RecoveryStatusResult(
            recovery_status=recovery_status,
            rest_day_effect=rest_day_effect,
            recovery_trend=[],
            data_quality=DataQuality.SUFFICIENT,
        )

    def check_rest_day_effect(self) -> RestDayEffect:
        """检查休息日效果

        比较最近两天的静息心率变化和TSB变化，评估休息效果。

        Returns:
            RestDayEffect: 休息日效果
        """
        try:
            trend = self.hrv_analyzer.get_resting_hr_trend(days=7)

            if len(trend) < 2:
                return RestDayEffect(
                    resting_hr_change_pct=0.0,
                    tsb_change=0.0,
                    effect_level="minimal",
                    message="数据不足，无法评估休息效果",
                )

            latest = trend[-1]
            previous = trend[-2]

            hr_change_pct = previous.resting_hr - latest.resting_hr
            if previous.resting_hr > 0:
                hr_change_pct = (hr_change_pct / previous.resting_hr) * 100.0
            else:
                hr_change_pct = 0.0

            tsb_change = 0.0

            if (
                hr_change_pct >= self.config.rest_hr_improvement_pct
                or tsb_change >= self.config.rest_tsb_improvement
            ):
                return RestDayEffect(
                    resting_hr_change_pct=round(hr_change_pct, 2),
                    tsb_change=tsb_change,
                    effect_level="good",
                    message="静息心率明显下降，休息效果良好",
                )

            return RestDayEffect(
                resting_hr_change_pct=round(hr_change_pct, 2),
                tsb_change=tsb_change,
                effect_level="minimal",
                message="休息效果不明显",
            )

        except Exception as e:
            logger.warning(f"检查休息日效果失败: {e}")
            return RestDayEffect(
                resting_hr_change_pct=0.0,
                tsb_change=0.0,
                effect_level="minimal",
                message="评估失败",
            )

    def get_recovery_trend(self, days: int = 7) -> list[RecoveryPoint]:
        """获取恢复趋势

        读取指定天数的训练数据，计算每天的TSB和CTL。

        Args:
            days: 查询天数

        Returns:
            list[RecoveryPoint]: 恢复趋势数据列表
        """
        try:
            lf = self.session_repo.storage.read_parquet()
            columns = lf.columns

            if "session_start_time" not in columns:
                return []

            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            filtered = lf.filter(
                (pl.col("session_start_time") >= start_date)
                & (pl.col("session_start_time") <= end_date)
            )

            df = filtered.collect()

            if df.is_empty():
                return []

            trend: list[RecoveryPoint] = []
            for row in df.iter_rows(named=True):
                session_time = row.get("session_start_time")
                if session_time is None:
                    continue

                date_str = (
                    str(session_time.date())
                    if hasattr(session_time, "date")
                    else str(session_time)
                )

                load_data = (
                    self.training_load_analyzer.calculate_training_load_from_dataframe(
                        pl.DataFrame()
                    )
                )
                tsb = float(load_data.get("tsb", 0.0))
                ctl = float(load_data.get("ctl", 0.0))

                trend.append(RecoveryPoint(date=date_str, tsb=tsb, ctl=ctl))

            return trend

        except Exception as e:
            logger.warning(f"获取恢复趋势失败: {e}")
            return []
