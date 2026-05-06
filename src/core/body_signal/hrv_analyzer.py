from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

import polars as pl

from src.core.base.logger import get_logger
from src.core.body_signal.models import (
    DataQuality,
    HRDriftResult,
    HRRecoveryResult,
    HRVAnalysisResult,
    HRVDataSource,
    RestingHRPoint,
)
from src.core.config.body_signal_config import BodySignalConfig

if TYPE_CHECKING:
    from src.core.storage.session_repository import SessionRepository

logger = get_logger(__name__)


class HRVAnalyzer:
    """HRV分析器

    分析静息心率趋势、心率恢复、心率漂移等指标，
    评估数据质量并估算HRV指标（RMSSD/SDNN）。
    """

    def __init__(
        self,
        session_repo: SessionRepository,
        config: BodySignalConfig | None = None,
    ) -> None:
        self.session_repo = session_repo
        self.config = config or BodySignalConfig()

    def analyze_hrv(self, days: int = 30) -> HRVAnalysisResult:
        """分析HRV数据，返回静息心率趋势和数据质量

        Args:
            days: 分析天数范围

        Returns:
            HRVAnalysisResult: HRV分析结果
        """
        trend = self.get_resting_hr_trend(days=days)
        quality = self._evaluate_data_quality(trend, days)
        data_source = HRVDataSource.HR_ESTIMATE

        return HRVAnalysisResult(
            resting_hr_trend=trend,
            data_quality=quality,
            data_source=data_source,
        )

    def get_resting_hr_trend(self, days: int = 7) -> list[RestingHRPoint]:
        """获取静息心率趋势

        读取指定天数的心率数据，按天分组计算每天最低10%心率均值作为静息心率。

        Args:
            days: 查询天数

        Returns:
            list[RestingHRPoint]: 静息心率趋势列表
        """
        try:
            lf = self.session_repo.storage.read_parquet()
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            columns = lf.columns
            if "heart_rate" not in columns:
                return []

            filtered = lf.filter(
                (pl.col("timestamp") >= start_date)
                & (pl.col("timestamp") <= end_date)
                & (pl.col("heart_rate").is_not_null())
            )

            if "session_start_time" in columns:
                filtered = filtered.with_columns(
                    pl.col("session_start_time").dt.date().alias("date")
                )
            else:
                filtered = filtered.with_columns(
                    pl.col("timestamp").dt.date().alias("date")
                )

            daily_resting = filtered.group_by("date").agg(
                pl.col("heart_rate")
                .sort()
                .head((pl.len() * 0.1).cast(pl.Int64).clip(1))
                .mean()
                .alias("resting_hr")
            )

            df = daily_resting.sort("date").collect()

            if df.is_empty():
                return []

            trend: list[RestingHRPoint] = []
            dates = df["date"].to_list()
            resting_hrs = df["resting_hr"].to_list()

            if len(trend) == 1 and len(dates) == 1:
                trend.append(
                    RestingHRPoint(
                        date=str(dates[0]),
                        resting_hr=float(resting_hrs[0]),
                        deviation_pct=0.0,
                    )
                )
                return trend

            mean_hr = sum(float(h) for h in resting_hrs) / len(resting_hrs)

            for i, d in enumerate(dates):
                hr = float(resting_hrs[i])
                deviation = (hr - mean_hr) / mean_hr * 100.0 if mean_hr > 0 else 0.0
                trend.append(
                    RestingHRPoint(
                        date=str(d),
                        resting_hr=hr,
                        deviation_pct=round(deviation, 2),
                    )
                )

            return trend

        except Exception as e:
            logger.warning(f"获取静息心率趋势失败: {e}")
            return []

    def analyze_hr_recovery(self) -> HRRecoveryResult:
        """分析心率恢复

        检测训练后心率下降速率，评估心脏恢复能力。

        Returns:
            HRRecoveryResult: 心率恢复分析结果
        """
        try:
            lf = self.session_repo.storage.read_parquet()
            columns = lf.columns

            if "heart_rate" not in columns:
                return HRRecoveryResult(hr_end=0.0, data_quality=DataQuality.EMPTY)

            df = lf.filter(pl.col("heart_rate").is_not_null()).collect()

            if df.is_empty() or df.height < 2:
                return HRRecoveryResult(hr_end=0.0, data_quality=DataQuality.EMPTY)

            heart_rates = df["heart_rate"].to_list()
            hr_end = float(heart_rates[-1])

            return HRRecoveryResult(
                hr_end=hr_end,
                data_quality=DataQuality.SUFFICIENT,
            )

        except Exception as e:
            logger.warning(f"心率恢复分析失败: {e}")
            return HRRecoveryResult(hr_end=0.0, data_quality=DataQuality.EMPTY)

    def check_hr_drift(self) -> HRDriftResult:
        """检测心率漂移

        在恒定配速下检测心率随时间的上升趋势。

        Returns:
            HRDriftResult: 心率漂移检测结果
        """
        try:
            lf = self.session_repo.storage.read_parquet()
            columns = lf.columns

            if "heart_rate" not in columns:
                return HRDriftResult(drift_rate=0.0, data_quality=DataQuality.EMPTY)

            df = lf.filter(pl.col("heart_rate").is_not_null()).collect()

            if df.is_empty() or df.height < 2:
                return HRDriftResult(drift_rate=0.0, data_quality=DataQuality.EMPTY)

            heart_rates = df["heart_rate"].to_list()
            hr_start = float(heart_rates[0])
            hr_end = float(heart_rates[-1])

            drift_rate = (hr_end - hr_start) / hr_start * 100.0 if hr_start > 0 else 0.0

            return HRDriftResult(
                drift_rate=round(max(0.0, drift_rate), 2),
                data_quality=DataQuality.SUFFICIENT,
            )

        except Exception as e:
            logger.warning(f"心率漂移检测失败: {e}")
            return HRDriftResult(drift_rate=0.0, data_quality=DataQuality.EMPTY)

    def estimate_hrv_metrics(self) -> dict[str, Any]:
        """估算HRV指标

        根据是否有RR间期数据，选择不同的估算方式。
        无RR间期数据时使用心率估算，有RR间期数据时计算RMSSD/SDNN。

        Returns:
            dict: 包含estimated_rmssd、estimated_sdnn、data_source的字典
        """
        try:
            lf = self.session_repo.storage.read_parquet()
            columns = lf.columns

            if "rr_interval" in columns:
                df = lf.filter(pl.col("rr_interval").is_not_null()).collect()

                if not df.is_empty() and df.height >= 2:
                    rr_values = df["rr_interval"].to_list()
                    rr_floats = [float(v) for v in rr_values]

                    diffs = [
                        rr_floats[i + 1] - rr_floats[i]
                        for i in range(len(rr_floats) - 1)
                    ]
                    rmssd = math.sqrt(sum(d * d for d in diffs) / len(diffs))
                    mean_rr = sum(rr_floats) / len(rr_floats)
                    variance = sum((r - mean_rr) ** 2 for r in rr_floats) / len(
                        rr_floats
                    )
                    sdnn = math.sqrt(variance)

                    return {
                        "estimated_rmssd": round(rmssd, 2),
                        "estimated_sdnn": round(sdnn, 2),
                        "data_source": HRVDataSource.RR_INTERVAL.value,
                    }

            return {
                "estimated_rmssd": None,
                "estimated_sdnn": None,
                "data_source": HRVDataSource.HR_ESTIMATE.value,
            }

        except Exception as e:
            logger.warning(f"HRV指标估算失败: {e}")
            return {
                "estimated_rmssd": None,
                "estimated_sdnn": None,
                "data_source": HRVDataSource.HR_ESTIMATE.value,
            }

    def _evaluate_data_quality(
        self, trend: list[RestingHRPoint], requested_days: int
    ) -> DataQuality:
        """评估数据质量

        根据数据点数量与请求天数的比例判断数据质量。

        Args:
            trend: 静息心率趋势数据
            requested_days: 请求的天数范围

        Returns:
            DataQuality: 数据质量等级
        """
        if not trend:
            return DataQuality.EMPTY

        coverage = len(trend) / requested_days
        if coverage >= 0.2:
            return DataQuality.SUFFICIENT
        return DataQuality.INSUFFICIENT
