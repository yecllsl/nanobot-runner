# Session数据仓储层
# 封装Session数据的聚合查询逻辑，消除重复代码

from datetime import datetime
from typing import Any, Dict, List, Optional

import polars as pl

from src.core.logger import get_logger

logger = get_logger(__name__)


class SessionRepository:
    """Session数据仓储，封装Session级别的数据聚合查询"""

    SESSION_COLUMNS = [
        "session_start_time",
        "session_total_distance",
        "session_total_timer_time",
        "session_avg_heart_rate",
        "max_heart_rate",
        "total_calories",
    ]

    def __init__(self, storage) -> None:
        self.storage = storage

    def get_sessions(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        min_distance: Optional[float] = None,
        max_distance: Optional[float] = None,
        limit: Optional[int] = None,
        descending: bool = True,
    ) -> pl.DataFrame:
        lf = self.storage.read_parquet()

        session_df = lf.group_by("session_start_time").agg(
            [
                pl.col("session_start_time").first().alias("session_start"),
                pl.col("session_total_distance").first().alias("distance"),
                pl.col("session_total_timer_time").first().alias("duration"),
                pl.col("session_avg_heart_rate").first().alias("avg_hr"),
                pl.col("max_heart_rate").first().alias("max_hr"),
                pl.col("total_calories").first().alias("calories"),
            ]
        )

        if start_date and end_date:
            session_df = session_df.filter(
                pl.col("session_start").is_between(start_date, end_date)
            )

        if min_distance is not None and max_distance is not None:
            session_df = session_df.filter(
                pl.col("distance").is_between(min_distance, max_distance)
            )
        elif min_distance is not None:
            session_df = session_df.filter(pl.col("distance") >= min_distance)

        session_df = session_df.sort("session_start", descending=descending)

        if limit:
            session_df = session_df.limit(limit)

        return session_df.collect()

    def get_recent_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        session_df = self.get_sessions(limit=limit)

        sessions = []
        for row in session_df.iter_rows(named=True):
            distance = row.get("distance") or 0
            duration = row.get("duration") or 0
            distance_km = distance / 1000
            duration_min = duration / 60
            pace = duration_min / distance_km if distance_km > 0 else 0

            sessions.append(
                {
                    "timestamp": str(row.get("session_start", "N/A")),
                    "distance_m": distance,
                    "distance_km": round(distance_km, 2),
                    "duration_s": duration,
                    "duration_min": round(duration_min, 1),
                    "avg_pace_sec_km": round(pace, 1) if pace > 0 else None,
                    "avg_heart_rate": row.get("avg_hr"),
                    "max_heart_rate": row.get("max_hr"),
                    "calories": row.get("calories"),
                }
            )

        return sessions

    def get_sessions_for_vdot(
        self, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        session_df = self.get_sessions(limit=limit)

        sessions = []
        for row in session_df.iter_rows(named=True):
            distance = row.get("distance") or 0
            duration = row.get("duration") or 0

            sessions.append(
                {
                    "timestamp": str(row.get("session_start", "N/A")),
                    "distance_m": distance,
                    "duration_s": duration,
                    "avg_heart_rate": row.get("avg_hr"),
                }
            )

        return sessions

    def get_sessions_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[Dict[str, Any]]:
        session_df = self.get_sessions(start_date=start_date, end_date=end_date)

        sessions = []
        for row in session_df.iter_rows(named=True):
            distance = row.get("distance") or 0
            duration = row.get("duration") or 0
            distance_km = distance / 1000
            duration_min = duration / 60
            pace = duration_min / distance_km if distance_km > 0 else 0

            sessions.append(
                {
                    "timestamp": str(row.get("session_start", "N/A")),
                    "distance_km": round(distance_km, 2),
                    "duration_min": round(duration_min, 1),
                    "avg_pace_sec_km": round(pace, 1) if pace > 0 else None,
                    "avg_heart_rate": row.get("avg_hr"),
                }
            )

        return sessions

    def get_sessions_by_distance(
        self, min_meters: float, max_meters: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        session_df = self.get_sessions(min_distance=min_meters, max_distance=max_meters)

        sessions = []
        for row in session_df.iter_rows(named=True):
            distance = row.get("distance") or 0
            duration = row.get("duration") or 0
            distance_km = distance / 1000
            duration_min = duration / 60
            pace = duration_min / distance_km if distance_km > 0 else 0

            sessions.append(
                {
                    "timestamp": str(row.get("session_start", "N/A")),
                    "distance_km": round(distance_km, 2),
                    "duration_min": round(duration_min, 1),
                    "avg_pace_sec_km": round(pace, 1) if pace > 0 else None,
                    "avg_heart_rate": row.get("avg_hr"),
                }
            )

        return sessions

    def get_session_count(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> int:
        session_df = self.get_sessions(start_date=start_date, end_date=end_date)
        return session_df.height

    def get_total_distance(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> float:
        session_df = self.get_sessions(start_date=start_date, end_date=end_date)

        if session_df.is_empty():
            return 0.0

        return session_df["distance"].sum()

    def get_total_duration(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> float:
        session_df = self.get_sessions(start_date=start_date, end_date=end_date)

        if session_df.is_empty():
            return 0.0

        return session_df["duration"].sum()
