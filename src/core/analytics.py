# 分析引擎
# 基于Polars实现核心数据分析算法

from typing import Any, Dict, List, Optional

import polars as pl


class AnalyticsEngine:
    """数据分析引擎"""

    def __init__(self, storage_manager) -> None:
        """
        初始化分析引擎

        Args:
            storage_manager: StorageManager实例
        """
        self.storage = storage_manager

    def calculate_vdot(self, distance_m: float, time_s: float) -> float:
        """
        计算VDOT值（跑力值）

        Args:
            distance_m: 距离（米）
            time_s: 用时（秒）

        Returns:
            float: VDOT值

        Raises:
            ValueError: 当距离或时间为负数时
        """
        if distance_m <= 0 or time_s <= 0:
            raise ValueError("距离和时间必须为正数")

        # 使用Powers公式计算VDOT
        # VDOT = (0.0001 * distance^1.06 * 24.6) / time^0.43
        vdot = (0.0001 * (distance_m**1.06) * 24.6) / (time_s**0.43)
        return round(vdot, 2)

    def calculate_tss(
        self, heart_rate_data: pl.Series, duration_s: float, ftp: int = 200
    ) -> float:
        """
        计算训练压力分数（TSS）

        Args:
            heart_rate_data: 心率数据序列
            duration_s: 时长（秒）
            ftp: 功能阈值功率（默认200）

        Returns:
            float: TSS值

        Raises:
            ValueError: 当输入参数无效时
        """
        if heart_rate_data.is_empty() or duration_s <= 0:
            raise ValueError("心率数据不能为空且时长必须为正数")

        try:
            # 计算平均心率
            avg_hr = heart_rate_data.mean()
            # TSS = (平均功率 / FTP) ^ 2 * 时长(小时) * 100
            # 这里简化计算，使用心率近似
            intensity_factor = avg_hr / 180  # 假设最大心率为180
            tss = (intensity_factor**2) * (duration_s / 3600) * 100
            return round(tss, 2)
        except Exception as e:
            raise ValueError(f"TSS计算失败: {e}") from e

    def get_running_stats(self, year: Optional[int] = None) -> Dict[str, Any]:
        """
        获取跑步统计数据

        Args:
            year: 年份，不指定则统计所有数据

        Returns:
            Dict[str, Any]: 统计信息字典
        """
        try:
            df = self.storage.read_activities(year)
            if df.is_empty():
                return {"total_runs": 0, "total_distance": 0.0, "total_duration": 0.0}

            stats = {
                "total_runs": df.height,
                "total_distance": round(df["distance"].sum() / 1000, 2),  # 转换为公里
                "total_duration": round(df["duration"].sum() / 3600, 2),  # 转换为小时
                "avg_heart_rate": round(df["heart_rate"].mean(), 1)
                if "heart_rate" in df.columns
                else 0,
                "avg_pace": self._calculate_avg_pace(df),
            }
            return stats
        except Exception as e:
            raise RuntimeError(f"获取统计数据失败: {e}") from e

    def _calculate_avg_pace(self, df: pl.DataFrame) -> str:
        """
        计算平均配速

        Args:
            df: 跑步数据DataFrame

        Returns:
            str: 平均配速（分钟/公里）
        """
        try:
            total_distance = df["distance"].sum() / 1000  # 转换为公里
            total_duration = df["duration"].sum() / 60  # 转换为分钟

            if total_distance <= 0:
                return "0:00"

            avg_pace_min_km = total_duration / total_distance
            minutes = int(avg_pace_min_km)
            seconds = int((avg_pace_min_km - minutes) * 60)
            return f"{minutes}:{seconds:02d}"
        except Exception as e:
            raise ValueError(f"配速计算失败: {e}") from e

    def get_vdot_trend(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        获取VDOT趋势数据

        Args:
            days: 统计天数

        Returns:
            List[Dict[str, Any]]: VDOT趋势数据
        """
        try:
            df = self.storage.read_activities()
            if df.is_empty():
                return []

            # 过滤最近days天的数据
            recent_df = df.filter(
                pl.col("timestamp") >= (pl.max("timestamp") - pl.duration(days=days))
            )

            trend_data = []
            for row in recent_df.iter_rows(named=True):
                vdot = self.calculate_vdot(row["distance"], row["duration"])
                trend_data.append(
                    {
                        "date": row["timestamp"].strftime("%Y-%m-%d"),
                        "vdot": vdot,
                        "distance": row["distance"],
                        "duration": row["duration"],
                    }
                )

            return trend_data
        except Exception as e:
            raise RuntimeError(f"获取VDOT趋势失败: {e}") from e
