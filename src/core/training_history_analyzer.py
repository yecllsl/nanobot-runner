# 训练历史分析器
# 分析训练一致性、时间偏好等历史数据

from datetime import timedelta
from typing import TYPE_CHECKING, Any

import polars as pl

from src.core.logger import get_logger
from src.core.user_profile_manager import RunnerProfile

if TYPE_CHECKING:
    from src.core.storage import StorageManager

logger = get_logger(__name__)


class TrainingHistoryAnalyzer:
    """训练历史分析器"""

    def __init__(self, storage_manager: "StorageManager") -> None:
        """
        初始化训练历史分析器

        Args:
            storage_manager: StorageManager 实例
        """
        self.storage = storage_manager

    def analyze_running_time_preference(self, timestamps: pl.Series) -> str:
        """
        分析跑步时间偏好

        Args:
            timestamps: 时间戳序列（UTC 时间）

        Returns:
            str: 偏好时间段（morning/afternoon/evening）
        """
        try:
            beijing_hours = [
                (t + timedelta(hours=8)).hour for t in timestamps.to_list()
            ]

            morning_count = sum(1 for h in beijing_hours if 5 <= h < 12)
            afternoon_count = sum(1 for h in beijing_hours if 12 <= h < 18)
            evening_count = sum(1 for h in beijing_hours if h >= 18 or h < 5)

            if morning_count >= afternoon_count and morning_count >= evening_count:
                return "morning"
            elif afternoon_count >= evening_count:
                return "afternoon"
            else:
                return "evening"
        except Exception:
            return "morning"

    def calculate_consistency_score(self, df: pl.DataFrame, days: int) -> float:
        """
        计算训练一致性评分（0-100）

        基于：
        1. 每周跑步天数
        2. 训练间隔的规律性

        Args:
            df: DataFrame 对象
            days: 分析天数

        Returns:
            float: 一致性评分 (0-100)
        """
        try:
            if df.is_empty():
                return 0.0

            weeks = max(days / 7, 1)
            total_runs = df.height
            runs_per_week = total_runs / weeks

            base_score = min(runs_per_week / 5 * 60, 60)

            regularity_score = self._calculate_regularity_score(df, total_runs)

            consistency_score = base_score + regularity_score
            return min(max(consistency_score, 0), 100)
        except Exception:
            return 0.0

    def _calculate_regularity_score(self, df: pl.DataFrame, total_runs: int) -> float:
        """计算规律性评分"""
        if total_runs < 2:
            return 0.0

        try:
            timestamps = df["timestamp"].sort()
            intervals = []

            for i in range(1, len(timestamps)):
                delta = timestamps[i] - timestamps[i - 1]
                if hasattr(delta, "total_seconds"):
                    interval_days = delta.total_seconds() / 86400
                else:
                    interval_days = delta.dt.total_seconds() / 86400
                intervals.append(interval_days)

            if not intervals:
                return 0.0

            intervals_series = pl.Series(intervals)
            std_dev_value = intervals_series.std()
            std_dev = (
                float(std_dev_value)
                if std_dev_value is not None and isinstance(std_dev_value, (int, float))
                else 0.0
            )

            return max(40 - (std_dev / 3 * 40), 0)
        except Exception:
            return 0.0

    def calculate_data_quality(self, lf: pl.LazyFrame, profile: RunnerProfile) -> None:
        """
        计算数据质量评分（0-100）

        基于：
        1. 数据完整性（必填字段）
        2. 心率数据覆盖率
        3. 数据量充足度

        Args:
            lf: LazyFrame 对象
            profile: 画像对象
        """
        try:
            df = lf.collect()

            if df.is_empty():
                profile.data_quality_score = 0.0
                return

            score = 0.0

            timestamp_ratio = (
                df.filter(pl.col("timestamp").is_not_null()).height / df.height
            )
            score += timestamp_ratio * 30

            distance_df = df.filter(
                (pl.col("total_distance").is_not_null())
                & (pl.col("total_distance") > 0)
            )
            distance_ratio = distance_df.height / df.height
            score += distance_ratio * 20

            hr_df = df.filter(
                (pl.col("avg_heart_rate").is_not_null())
                & (pl.col("avg_heart_rate") > 0)
            )
            hr_ratio = hr_df.height / df.height
            score += hr_ratio * 30

            if df.height >= 10:
                score += 20
            elif df.height >= 5:
                score += 10

            profile.data_quality_score = min(max(score, 0), 100)
        except Exception as e:
            logger.warning(f"计算数据质量评分失败：{e}")
            profile.data_quality_score = 0.0

    def get_training_summary(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """
        获取训练摘要

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            dict: 训练摘要
        """
        try:
            lf = self.storage.read_parquet()

            if len(lf.collect_schema()) == 0:
                return {"total_runs": 0, "message": "无训练数据"}

            df = lf.collect()

            if df.is_empty():
                return {"total_runs": 0, "message": "无训练数据"}

            total_runs = df.height
            total_distance = (
                float(df["total_distance"].sum())
                if "total_distance" in df.columns
                else 0.0
            )
            total_duration = (
                float(df["total_timer_time"].sum())
                if "total_timer_time" in df.columns
                else 0.0
            )

            return {
                "total_runs": total_runs,
                "total_distance_km": round(total_distance / 1000, 2),
                "total_duration_hours": round(total_duration / 3600, 2),
            }
        except Exception as e:
            logger.error(f"获取训练摘要失败：{e}")
            return {"total_runs": 0, "message": f"获取失败: {e}"}

    def analyze_weekly_pattern(self, df: pl.DataFrame) -> dict[str, int]:
        """
        分析每周训练模式

        Args:
            df: DataFrame 对象

        Returns:
            dict: 每周各天的训练次数
        """
        try:
            if df.is_empty() or "timestamp" not in df.columns:
                return {}

            df_with_weekday = df.with_columns(
                pl.col("timestamp").dt.weekday().alias("weekday")
            )

            weekday_counts = df_with_weekday.group_by("weekday").len()

            result = {}
            for row in weekday_counts.iter_rows(named=True):
                weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
                weekday = row["weekday"]
                if 0 <= weekday <= 6:
                    result[weekday_names[weekday]] = row["len"]

            return result
        except Exception as e:
            logger.warning(f"分析每周训练模式失败：{e}")
            return {}

    def get_recent_activities(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        获取最近的活动记录

        Args:
            limit: 返回数量限制

        Returns:
            list: 活动记录列表
        """
        try:
            lf = self.storage.read_parquet()

            if len(lf.collect_schema()) == 0:
                return []

            df = lf.sort("timestamp", descending=True).limit(limit).collect()

            if df.is_empty():
                return []

            activities = []
            for row in df.iter_rows(named=True):
                activities.append(
                    {
                        "timestamp": row.get("timestamp"),
                        "distance_km": round(
                            (row.get("total_distance") or 0) / 1000, 2
                        ),
                        "duration_min": round(
                            (row.get("total_timer_time") or 0) / 60, 1
                        ),
                        "avg_hr": row.get("avg_heart_rate") or 0,
                    }
                )

            return activities
        except Exception as e:
            logger.error(f"获取最近活动失败：{e}")
            return []
