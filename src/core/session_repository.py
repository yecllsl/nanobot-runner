# Session数据仓储层
# 封装Session数据的聚合查询逻辑，消除重复代码
# 保持LazyFrame链式操作，仅在最终输出时collect()

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import polars as pl

from src.core.logger import get_logger

if TYPE_CHECKING:
    from src.core.storage import StorageManager

logger = get_logger(__name__)


@dataclass(frozen=True)
class SessionSummary:
    """Session摘要数据类，替代 Dict[str, Any] 提升类型安全"""

    timestamp: str
    distance_km: float
    duration_min: float
    avg_pace_sec_km: Optional[float]
    avg_heart_rate: Optional[float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "distance_km": self.distance_km,
            "duration_min": self.duration_min,
            "avg_pace_sec_km": self.avg_pace_sec_km,
            "avg_heart_rate": self.avg_heart_rate,
        }


@dataclass(frozen=True)
class SessionDetail(SessionSummary):
    """Session详情数据类，包含完整字段"""

    distance_m: float = 0.0
    duration_s: float = 0.0
    max_heart_rate: Optional[float] = None
    calories: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update(
            {
                "distance_m": self.distance_m,
                "duration_s": self.duration_s,
                "max_heart_rate": self.max_heart_rate,
                "calories": self.calories,
            }
        )
        return d


@dataclass(frozen=True)
class SessionVdot:
    """VDOT计算所需的Session数据"""

    timestamp: str
    distance_m: float
    duration_s: float
    avg_heart_rate: Optional[float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "distance_m": self.distance_m,
            "duration_s": self.duration_s,
            "avg_heart_rate": self.avg_heart_rate,
        }


class SessionRepository:
    """Session数据仓储，封装Session级别的数据聚合查询

    保持LazyFrame链式操作，仅在最终输出时调用collect()，
    避免过早物化导致内存压力。使用Polars表达式替代iter_rows循环。
    """

    SESSION_COLUMNS = [
        "session_start_time",
        "session_total_distance",
        "session_total_timer_time",
        "session_avg_heart_rate",
        "max_heart_rate",
        "total_calories",
    ]

    def __init__(self, storage: StorageManager) -> None:
        self.storage = storage

    def _build_session_lazy(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        min_distance: Optional[float] = None,
        max_distance: Optional[float] = None,
        descending: bool = True,
    ) -> pl.LazyFrame:
        """构建Session聚合查询的LazyFrame链

        保持LazyFrame延迟求值，所有过滤和排序操作在LazyFrame上执行，
        仅在调用方需要时才collect()。

        Args:
            start_date: 开始日期
            end_date: 结束日期
            min_distance: 最小距离（米）
            max_distance: 最大距离（米）
            descending: 是否按时间降序

        Returns:
            pl.LazyFrame: 延迟求值的Session聚合结果
        """
        lf = self.storage.read_parquet()

        if len(lf.collect_schema()) == 0:
            return lf

        session_lf = lf.group_by("session_start_time").agg(
            [
                pl.col("session_start_time").first().alias("session_start"),
                pl.col("session_total_distance").first().alias("distance"),
                pl.col("session_total_timer_time").first().alias("duration"),
                pl.col("session_avg_heart_rate").first().alias("avg_hr"),
                pl.col("max_heart_rate").first().alias("max_hr"),
                pl.col("total_calories").first().alias("calories"),
            ]
        )

        if start_date is not None and end_date is not None:
            session_lf = session_lf.filter(
                pl.col("session_start").is_between(start_date, end_date)
            )

        if min_distance is not None and max_distance is not None:
            session_lf = session_lf.filter(
                pl.col("distance").is_between(min_distance, max_distance)
            )
        elif min_distance is not None:
            session_lf = session_lf.filter(pl.col("distance") >= min_distance)

        session_lf = session_lf.sort("session_start", descending=descending)

        return session_lf

    def _add_computed_columns(self, df: pl.DataFrame) -> pl.DataFrame:
        """使用Polars表达式批量添加计算列，替代iter_rows逐行计算

        Args:
            df: 原始Session DataFrame

        Returns:
            pl.DataFrame: 添加了distance_km/duration_min/avg_pace_sec_km的DataFrame
        """
        return df.with_columns(
            [
                (pl.col("distance") / 1000).round(2).alias("distance_km"),
                (pl.col("duration") / 60).round(1).alias("duration_min"),
                pl.when(pl.col("distance") > 0)
                .then(
                    ((pl.col("duration") / 60) / (pl.col("distance") / 1000)).round(1)
                )
                .otherwise(None)
                .alias("avg_pace_sec_km"),
            ]
        )

    def _df_to_session_details(self, df: pl.DataFrame) -> List[SessionDetail]:
        """将DataFrame转换为SessionDetail列表

        Args:
            df: 包含计算列的DataFrame

        Returns:
            List[SessionDetail]: Session详情列表
        """
        if df.is_empty():
            return []

        df = self._add_computed_columns(df)

        results: List[SessionDetail] = []
        for row in df.iter_rows(named=True):
            results.append(
                SessionDetail(
                    timestamp=str(row.get("session_start", "N/A")),
                    distance_km=row.get("distance_km", 0.0),
                    duration_min=row.get("duration_min", 0.0),
                    avg_pace_sec_km=row.get("avg_pace_sec_km"),
                    avg_heart_rate=row.get("avg_hr"),
                    distance_m=row.get("distance", 0) or 0,
                    duration_s=row.get("duration", 0) or 0,
                    max_heart_rate=row.get("max_hr"),
                    calories=row.get("calories"),
                )
            )

        return results

    def _df_to_session_summaries(self, df: pl.DataFrame) -> List[SessionSummary]:
        """将DataFrame转换为SessionSummary列表

        Args:
            df: 包含计算列的DataFrame

        Returns:
            List[SessionSummary]: Session摘要列表
        """
        if df.is_empty():
            return []

        df = self._add_computed_columns(df)

        results: List[SessionSummary] = []
        for row in df.iter_rows(named=True):
            results.append(
                SessionSummary(
                    timestamp=str(row.get("session_start", "N/A")),
                    distance_km=row.get("distance_km", 0.0),
                    duration_min=row.get("duration_min", 0.0),
                    avg_pace_sec_km=row.get("avg_pace_sec_km"),
                    avg_heart_rate=row.get("avg_hr"),
                )
            )

        return results

    def get_sessions(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        min_distance: Optional[float] = None,
        max_distance: Optional[float] = None,
        limit: Optional[int] = None,
        descending: bool = True,
    ) -> pl.DataFrame:
        """获取Session聚合数据

        保持LazyFrame链式操作，仅在最终返回前collect()。

        Args:
            start_date: 开始日期
            end_date: 结束日期
            min_distance: 最小距离（米）
            max_distance: 最大距离（米）
            limit: 返回数量限制
            descending: 是否按时间降序

        Returns:
            pl.DataFrame: Session聚合结果
        """
        session_lf = self._build_session_lazy(
            start_date=start_date,
            end_date=end_date,
            min_distance=min_distance,
            max_distance=max_distance,
            descending=descending,
        )

        if limit:
            session_lf = session_lf.limit(limit)

        return session_lf.collect()

    def get_recent_sessions(self, limit: int = 10) -> List[SessionDetail]:
        """获取最近的Session详情

        Args:
            limit: 返回数量限制

        Returns:
            List[SessionDetail]: Session详情列表
        """
        session_lf = self._build_session_lazy(descending=True)
        session_lf = session_lf.limit(limit)
        df = session_lf.collect()

        return self._df_to_session_details(df)

    def get_sessions_for_vdot(self, limit: Optional[int] = None) -> List[SessionVdot]:
        """获取VDOT计算所需的Session数据

        Args:
            limit: 返回数量限制

        Returns:
            List[SessionVdot]: VDOT计算所需的Session列表
        """
        session_lf = self._build_session_lazy(descending=True)
        if limit:
            session_lf = session_lf.limit(limit)
        df = session_lf.collect()

        if df.is_empty():
            return []

        results: List[SessionVdot] = []
        for row in df.iter_rows(named=True):
            results.append(
                SessionVdot(
                    timestamp=str(row.get("session_start", "N/A")),
                    distance_m=row.get("distance", 0) or 0,
                    duration_s=row.get("duration", 0) or 0,
                    avg_heart_rate=row.get("avg_hr"),
                )
            )

        return results

    def get_sessions_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[SessionSummary]:
        """按日期范围获取Session摘要

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            List[SessionSummary]: Session摘要列表
        """
        session_lf = self._build_session_lazy(
            start_date=start_date, end_date=end_date, descending=True
        )
        df = session_lf.collect()

        return self._df_to_session_summaries(df)

    def get_sessions_by_distance(
        self, min_meters: float, max_meters: Optional[float] = None
    ) -> List[SessionSummary]:
        """按距离范围获取Session摘要

        Args:
            min_meters: 最小距离（米）
            max_meters: 最大距离（米），可选

        Returns:
            List[SessionSummary]: Session摘要列表
        """
        session_lf = self._build_session_lazy(
            min_distance=min_meters, max_distance=max_meters, descending=True
        )
        df = session_lf.collect()

        return self._df_to_session_summaries(df)

    def get_session_count(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> int:
        """获取Session数量

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            int: Session数量
        """
        session_lf = self._build_session_lazy(start_date=start_date, end_date=end_date)
        return session_lf.collect().height

    def get_total_distance(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> float:
        """获取总距离

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            float: 总距离（米）
        """
        session_lf = self._build_session_lazy(start_date=start_date, end_date=end_date)
        df = session_lf.collect()

        if df.is_empty():
            return 0.0

        return float(df["distance"].sum())

    def get_total_duration(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> float:
        """获取总时长

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            float: 总时长（秒）
        """
        session_lf = self._build_session_lazy(start_date=start_date, end_date=end_date)
        df = session_lf.collect()

        if df.is_empty():
            return 0.0

        return float(df["duration"].sum())
