# 统计数据聚合器
# 提供跑步数据的统计汇总功能

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

import polars as pl

if TYPE_CHECKING:
    from src.core.storage import StorageManager


class StatisticsAggregator:
    """统计数据聚合器"""

    def __init__(self, storage_manager: "StorageManager") -> None:
        """
        初始化统计聚合器

        Args:
            storage_manager: StorageManager实例
        """
        self.storage = storage_manager

    def get_running_summary(
        self, start_date: str | None = None, end_date: str | None = None
    ) -> pl.DataFrame:
        """
        获取跑步摘要统计

        Args:
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）

        Returns:
            pl.DataFrame: 统计结果
        """
        try:
            lf = self.storage.read_parquet()

            if len(lf.collect_schema()) == 0:
                return pl.DataFrame()

            if start_date or end_date:
                if start_date:
                    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                    lf = lf.filter(pl.col("timestamp") >= start_dt)
                if end_date:
                    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                    end_dt = end_dt + timedelta(days=1)
                    lf = lf.filter(pl.col("timestamp") < end_dt)

            session_df = (
                lf.group_by("session_start_time")
                .agg(
                    [
                        pl.col("session_total_distance").first().alias("distance"),
                        pl.col("session_total_timer_time").first().alias("duration"),
                        pl.col("session_avg_heart_rate").first().alias("avg_hr"),
                    ]
                )
                .collect()
            )

            if session_df.is_empty():
                return pl.DataFrame()

            distance_col = session_df["distance"].fill_null(0)
            duration_col = session_df["duration"].fill_null(0)
            avg_hr_col = session_df["avg_hr"].fill_null(0)

            total_runs = session_df.height
            total_distance = distance_col.sum()
            total_timer_time = duration_col.sum()
            avg_distance = distance_col.mean()
            avg_timer_time = duration_col.mean()
            max_distance = distance_col.max()
            avg_heart_rate = avg_hr_col.mean()

            result = pl.DataFrame(
                {
                    "total_runs": [total_runs],
                    "total_distance": [total_distance],
                    "total_timer_time": [total_timer_time],
                    "avg_distance": [avg_distance],
                    "avg_timer_time": [avg_timer_time],
                    "max_distance": [max_distance],
                    "avg_heart_rate": [avg_heart_rate],
                }
            )

            return result
        except Exception as e:
            raise RuntimeError(f"获取跑步摘要失败: {e}") from e

    def _format_duration(self, duration_s: float) -> str:
        """
        格式化时长（HH:MM:SS）

        Args:
            duration_s: 时长（秒）

        Returns:
            str: 格式化后的时长
        """
        try:
            hours = int(duration_s // 3600)
            minutes = int((duration_s % 3600) // 60)
            seconds = int(duration_s % 60)
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        except Exception:
            return "00:00:00"

    def _format_pace(self, pace_sec_per_km: float | None) -> str:
        """
        格式化配速（M'SS"/km）

        Args:
            pace_sec_per_km: 配速（秒/公里）

        Returns:
            str: 格式化后的配速
        """
        try:
            if pace_sec_per_km is None or pace_sec_per_km <= 0:
                return "0'00\""
            minutes = int(pace_sec_per_km // 60)
            seconds = int(pace_sec_per_km % 60)
            return f"{minutes}'{seconds:02d}\""
        except Exception:
            return "0'00\""

    def get_running_stats(self, year: int | None = None) -> dict[str, Any]:
        """
        获取跑步统计数据

        Args:
            year: 年份，不指定则统计所有数据

        Returns:
            Dict[str, Any]: 统计信息字典
        """
        try:
            years = [year] if year else None
            lf = self.storage.read_parquet(years)

            if len(lf.collect_schema()) == 0:
                return {
                    "total_runs": 0,
                    "total_distance": 0.0,
                    "total_duration": 0.0,
                    "avg_heart_rate": 0.0,
                }

            session_df = (
                lf.group_by("session_start_time")
                .agg(
                    [
                        pl.col("session_total_distance").first().alias("distance"),
                        pl.col("session_total_timer_time").first().alias("duration"),
                        pl.col("session_avg_heart_rate").first().alias("avg_hr"),
                    ]
                )
                .collect()
            )

            if session_df.is_empty():
                return {"total_runs": 0, "total_distance": 0.0, "total_duration": 0.0}

            total_runs = session_df.height
            total_distance = float(session_df["distance"].sum())
            total_duration = float(session_df["duration"].sum())
            avg_heart_rate_result = session_df["avg_hr"].mean()
            avg_heart_rate = (
                float(avg_heart_rate_result)  # type: ignore[arg-type]
                if avg_heart_rate_result is not None
                else 0.0
            )

            stats = {
                "total_runs": total_runs,
                "total_distance": round(total_distance / 1000, 2),
                "total_duration": round(total_duration / 3600, 2),
                "avg_heart_rate": round(avg_heart_rate, 1),
                "avg_pace": self._calculate_avg_pace_from_values(
                    total_distance, total_duration
                ),
            }
            return stats
        except Exception as e:
            raise RuntimeError(f"获取统计数据失败: {e}") from e

    def _calculate_avg_pace_from_values(
        self, total_distance: float, total_duration: float
    ) -> str:
        """
        根据总距离和总时长计算平均配速

        Args:
            total_distance: 总距离（米）
            total_duration: 总时长（秒）

        Returns:
            str: 平均配速（分钟/公里）
        """
        try:
            if total_distance <= 0:
                return "0:00"

            avg_pace_min_km = (total_duration / 60) / (total_distance / 1000)
            minutes = int(avg_pace_min_km)
            seconds = int((avg_pace_min_km - minutes) * 60)
            return f"{minutes}:{seconds:02d}"
        except Exception:
            return "0:00"

    def _calculate_avg_pace(self, df: pl.DataFrame) -> str:
        """
        计算平均配速

        Args:
            df: 跑步数据DataFrame

        Returns:
            str: 平均配速（分钟/公里）
        """
        try:
            total_distance = float(df["distance"].sum()) / 1000.0
            total_duration = float(df["duration"].sum()) / 60.0

            if total_distance <= 0:
                return "0:00"

            avg_pace_min_km = total_duration / total_distance
            minutes = int(avg_pace_min_km)
            seconds = int((avg_pace_min_km - minutes) * 60)
            return f"{minutes}:{seconds:02d}"
        except Exception:
            return "0:00"

    def get_pace_distribution(self, year: int | None = None) -> dict[str, Any]:
        """
        获取配速分布统计

        Args:
            year: 年份，不指定则统计所有数据

        Returns:
            Dict[str, Any]: 配速分布数据
        """
        PACE_ZONES = {
            "Z1": {"min": 360, "max": float("inf"), "label": "恢复跑"},
            "Z2": {"min": 300, "max": 360, "label": "轻松跑"},
            "Z3": {"min": 240, "max": 300, "label": "节奏跑"},
            "Z4": {"min": 210, "max": 240, "label": "间歇跑"},
            "Z5": {"min": 0, "max": 210, "label": "冲刺跑"},
        }

        try:
            years = [year] if year else None
            lf = self.storage.read_parquet(years)

            if len(lf.collect_schema()) == 0:
                return {"zones": {}, "trend": [], "message": "无有效配速数据"}

            result = (
                lf.with_columns(
                    [
                        (
                            pl.col("session_total_timer_time")
                            / (pl.col("session_total_distance") / 1000)
                        ).alias("avg_pace_sec_per_km")
                    ]
                )
                .filter(
                    (pl.col("session_total_distance") > 0)
                    & (pl.col("session_total_timer_time") > 0)
                    & (pl.col("avg_pace_sec_per_km").is_not_null())
                )
                .with_columns(
                    [
                        pl.when(pl.col("avg_pace_sec_per_km") > 360)
                        .then(pl.lit("Z1"))
                        .when(pl.col("avg_pace_sec_per_km") > 300)
                        .then(pl.lit("Z2"))
                        .when(pl.col("avg_pace_sec_per_km") > 240)
                        .then(pl.lit("Z3"))
                        .when(pl.col("avg_pace_sec_per_km") > 210)
                        .then(pl.lit("Z4"))
                        .otherwise(pl.lit("Z5"))
                        .alias("pace_zone")
                    ]
                )
                .group_by("pace_zone")
                .agg([pl.len().alias("count")])
                .collect()
            )

            zones = {}
            for row in result.iter_rows(named=True):
                zone = row["pace_zone"]
                count = row["count"]
                if zone in PACE_ZONES:
                    zones[zone] = {
                        "label": PACE_ZONES[zone]["label"],
                        "count": count,
                        "percentage": 0.0,
                    }

            total_count = sum(z["count"] for z in zones.values())
            for zone in zones:
                if total_count > 0:
                    zones[zone]["percentage"] = round(
                        zones[zone]["count"] / total_count * 100, 2
                    )

            return {"zones": zones, "trend": [], "total_count": total_count}

        except Exception as e:
            raise RuntimeError(f"配速分布分析失败: {e}") from e
