from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import polars as pl

from src.core.base.logger import get_logger
from src.core.body_signal.models import (
    DataQuality,
    FatigueBreakdown,
    FatigueResult,
)
from src.core.config.body_signal_config import BodySignalConfig
from src.core.models.recovery import RecoveryStatus

if TYPE_CHECKING:
    from src.core.calculators.training_load_analyzer import TrainingLoadAnalyzer
    from src.core.storage.session_repository import SessionRepository

logger = get_logger(__name__)


class FatigueAssessor:
    """疲劳度评估器

    综合ATL、心率偏差、连续训练天数和主观疲劳度(RPE)四个维度，
    计算疲劳度分数并给出恢复状态和建议。
    """

    def __init__(
        self,
        session_repo: SessionRepository,
        training_load_analyzer: TrainingLoadAnalyzer,
        config: BodySignalConfig | None = None,
    ) -> None:
        self.session_repo = session_repo
        self.training_load_analyzer = training_load_analyzer
        self.config = config or BodySignalConfig()

    def assess_fatigue(self, rpe: int | None = None) -> FatigueResult:
        """评估疲劳度

        综合训练负荷、心率偏差、连续训练天数和主观疲劳度，
        计算加权疲劳度分数。

        Args:
            rpe: 主观疲劳度(1-10)，可选

        Returns:
            FatigueResult: 疲劳度评估结果

        Raises:
            ValueError: RPE值不在1-10范围内
        """
        if rpe is not None and (rpe < 1 or rpe > 10):
            raise ValueError("RPE值必须在1-10范围内")

        load_data = self.training_load_analyzer.calculate_training_load_from_dataframe(
            pl.DataFrame()
        )
        atl = float(load_data.get("atl", 0.0))
        tsb_raw = float(load_data.get("tsb", 0.0))
        runs_count = int(load_data.get("runs_count", 0))

        if runs_count == 0:
            return FatigueResult(
                fatigue_score=0.0,
                recovery_status=RecoveryStatus.GREEN,
                consecutive_hard_days=0,
                breakdown=FatigueBreakdown(),
                recommendation="暂无训练数据",
                data_quality=DataQuality.EMPTY,
            )

        tsb = min(tsb_raw, self.config.tsb_cap)

        consecutive_hard_days = self.get_consecutive_hard_days()

        atl_component = self._calc_atl_component(atl, tsb)
        hr_deviation_component = 0.0
        consecutive_component = self._calc_consecutive_component(consecutive_hard_days)
        subjective_component = self._calc_subjective_component(rpe) if rpe else 0.0

        weights = self._resolve_weights(has_rpe=rpe is not None)

        fatigue_score = (
            atl_component * weights["atl"] / 100.0
            + hr_deviation_component * weights["hr"] / 100.0
            + consecutive_component * weights["consecutive"] / 100.0
            + subjective_component * weights["subjective"] / 100.0
        )
        fatigue_score = min(100.0, max(0.0, fatigue_score))

        recovery_status = self._determine_recovery_status(tsb, fatigue_score)

        breakdown = FatigueBreakdown(
            atl_component=round(atl_component, 2),
            hr_deviation_component=round(hr_deviation_component, 2),
            consecutive_component=round(consecutive_component, 2),
            subjective_component=round(subjective_component, 2),
        )

        recommendation = self._generate_recommendation(
            recovery_status, consecutive_hard_days, fatigue_score
        )

        return FatigueResult(
            fatigue_score=round(fatigue_score, 2),
            recovery_status=recovery_status,
            consecutive_hard_days=consecutive_hard_days,
            breakdown=breakdown,
            recommendation=recommendation,
            data_quality=DataQuality.SUFFICIENT,
        )

    def get_consecutive_hard_days(self) -> int:
        """统计连续高强度训练天数

        读取最近训练记录，统计TSS超过阈值的连续天数。

        Returns:
            int: 连续高强度训练天数
        """
        try:
            lf = self.session_repo.storage.read_parquet()
            columns = lf.columns

            if "session_start_time" not in columns:
                return 0

            end_date = datetime.now()
            start_date = end_date - timedelta(days=14)

            filtered = lf.filter(
                (pl.col("session_start_time") >= start_date)
                & (pl.col("session_start_time") <= end_date)
            )

            df = filtered.sort("session_start_time", descending=True).collect()

            if df.is_empty():
                return 0

            consecutive = 0
            for row in df.iter_rows(named=True):
                distance = float(row.get("session_total_distance", 0))
                duration = float(row.get("session_total_timer_time", 0))
                avg_hr = row.get("session_avg_heart_rate")

                tss = self.training_load_analyzer.calculate_tss_for_run(
                    distance_m=distance,
                    duration_s=duration,
                    avg_heart_rate=avg_hr if isinstance(avg_hr, (int, float)) else None,
                )

                if tss >= self.config.hard_training_tss_threshold:
                    consecutive += 1
                else:
                    break

            return consecutive

        except Exception as e:
            logger.warning(f"统计连续高强度训练天数失败: {e}")
            return 0

    def _resolve_weights(self, has_rpe: bool) -> dict[str, float]:
        """解析权重配置

        无RPE时，将主观疲劳度权重按比例分配给其他三个维度。

        Args:
            has_rpe: 是否有RPE数据

        Returns:
            dict: 各维度权重
        """
        if has_rpe:
            return {
                "atl": self.config.fatigue_weight_atl,
                "hr": self.config.fatigue_weight_hr,
                "consecutive": self.config.fatigue_weight_consecutive,
                "subjective": self.config.fatigue_weight_subjective,
            }

        active_weight_sum = (
            self.config.fatigue_weight_atl
            + self.config.fatigue_weight_hr
            + self.config.fatigue_weight_consecutive
        )
        scale = 100.0 / active_weight_sum if active_weight_sum > 0 else 1.0

        return {
            "atl": self.config.fatigue_weight_atl * scale,
            "hr": self.config.fatigue_weight_hr * scale,
            "consecutive": self.config.fatigue_weight_consecutive * scale,
            "subjective": 0.0,
        }

    def _calc_atl_component(self, atl: float, tsb: float) -> float:
        """计算ATL维度疲劳度贡献

        基于ATL值和TSB计算训练负荷维度的疲劳度。
        """
        if atl <= 30:
            return atl
        elif atl <= 60:
            return atl * 1.2
        else:
            return atl * 1.5

    def _calc_consecutive_component(self, consecutive_days: int) -> float:
        """计算连续训练维度疲劳度贡献"""
        if consecutive_days <= 1:
            return 0.0
        elif consecutive_days <= 3:
            return consecutive_days * 10.0
        else:
            return 30.0 + (consecutive_days - 3) * 15.0

    def _calc_subjective_component(self, rpe: int) -> float:
        """计算主观疲劳度维度贡献"""
        return rpe * 8.0

    def _determine_recovery_status(
        self, tsb: float, fatigue_score: float
    ) -> RecoveryStatus:
        """根据TSB和疲劳度分数判断恢复状态"""
        if tsb < self.config.overtraining_tsb_threshold or fatigue_score >= 70:
            return RecoveryStatus.RED
        elif tsb < 0 or fatigue_score >= 40:
            return RecoveryStatus.YELLOW
        return RecoveryStatus.GREEN

    def _generate_recommendation(
        self,
        recovery_status: RecoveryStatus,
        consecutive_hard_days: int,
        fatigue_score: float,
    ) -> str:
        """生成训练建议"""
        if recovery_status == RecoveryStatus.RED:
            if consecutive_hard_days >= self.config.overtraining_consecutive_days:
                return "⚠️ 过度训练风险！建议完全休息1-2天，降低训练强度"
            return "身体疲劳度较高，建议降低训练强度或安排休息日"

        if recovery_status == RecoveryStatus.YELLOW:
            return "身体状态一般，建议以轻松跑为主，注意恢复"

        return "体能充沛，今天适合质量课训练"
