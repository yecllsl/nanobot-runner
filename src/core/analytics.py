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
            ValueError: 当距离或时间为负数或零时
        """
        if distance_m <= 0 or time_s <= 0:
            raise ValueError("距离和时间必须为正数")

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
            avg_hr = heart_rate_data.mean()
            intensity_factor = avg_hr / 180
            tss = (intensity_factor**2) * (duration_s / 3600) * 100
            return round(tss, 2)
        except Exception as e:
            raise ValueError(f"TSS计算失败: {e}") from e

    def get_running_summary(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pl.DataFrame:
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
            df = lf.collect()
            
            if df.is_empty():
                return pl.DataFrame()

            result = df.select([
                pl.len().alias("total_runs"),
                pl.col("total_distance").sum().alias("total_distance"),
                pl.col("total_timer_time").sum().alias("total_timer_time"),
                pl.col("total_distance").mean().alias("avg_distance"),
                pl.col("total_timer_time").mean().alias("avg_timer_time"),
                pl.col("total_distance").max().alias("max_distance"),
                pl.col("avg_heart_rate").mean().alias("avg_heart_rate")
            ])
            
            return result
        except Exception as e:
            raise RuntimeError(f"获取跑步摘要失败: {e}") from e

    def analyze_hr_drift(self, heart_rate: List[float], pace: List[float]) -> Dict[str, Any]:
        """
        分析心率漂移情况

        Args:
            heart_rate: 心率数据列表
            pace: 配速数据列表

        Returns:
            dict: 分析结果
        """
        if not heart_rate or not pace:
            return {"error": "数据量不足"}

        if len(heart_rate) < 10 or len(pace) < 10:
            return {"error": "数据量不足"}

        try:
            hr_series = pl.Series("heart_rate", heart_rate)
            pace_series = pl.Series("pace", pace)
            
            df = pl.DataFrame([hr_series, pace_series])
            correlation = df.corr()[0, 1]
            
            if len(heart_rate) >= 2:
                first_half_hr = heart_rate[:len(heart_rate)//2]
                second_half_hr = heart_rate[len(heart_rate)//2:]
                drift = (sum(second_half_hr) / len(second_half_hr)) - (sum(first_half_hr) / len(first_half_hr))
            else:
                drift = 0

            drift_rate = (drift / (sum(heart_rate) / len(heart_rate))) * 100 if heart_rate else 0

            if drift_rate > 5:
                assessment = "心率漂移明显，可能有氧基础不扎实"
            elif drift_rate > 0:
                assessment = "心率漂移正常，跑步状态稳定"
            else:
                assessment = "心率表现优异，状态非常好"

            return {
                "drift": round(drift, 2),
                "drift_rate": round(drift_rate, 2),
                "correlation": round(correlation, 3) if correlation else 0,
                "assessment": assessment
            }
        except Exception as e:
            return {"error": f"分析失败: {str(e)}"}

    def calculate_atl(self, tss_values: List[float]) -> float:
        """
        计算急性训练负荷（ATL，7天指数移动平均）

        Args:
            tss_values: TSS值列表

        Returns:
            float: ATL值
        """
        if not tss_values:
            return 0.0

        atl_alpha = 1 / 7
        atl_value = tss_values[0]

        for tss in tss_values:
            atl_value = atl_alpha * tss + (1 - atl_alpha) * atl_value

        return round(atl_value, 2)

    def calculate_ctl(self, tss_values: List[float]) -> float:
        """
        计算慢性训练负荷（CTL，42天指数移动平均）

        Args:
            tss_values: TSS值列表

        Returns:
            float: CTL值
        """
        if not tss_values:
            return 0.0

        ctl_alpha = 1 / 42
        ctl_value = tss_values[0]

        for tss in tss_values:
            ctl_value = ctl_alpha * tss + (1 - ctl_alpha) * ctl_value

        return round(ctl_value, 2)

    def calculate_atl_ctl(self, tss_values: List[float], atl_days: int = 7, ctl_days: int = 42) -> Dict[str, float]:
        """
        计算ATL和CTL

        Args:
            tss_values: TSS值列表
            atl_days: ATL计算天数
            ctl_days: CTL计算天数

        Returns:
            dict: ATL和CTL值
        """
        if not tss_values:
            return {"atl": 0.0, "ctl": 0.0}

        atl = self.calculate_atl(tss_values)
        ctl = self.calculate_ctl(tss_values)

        return {"atl": atl, "ctl": ctl}

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
                "total_distance": round(df["distance"].sum() / 1000, 2),
                "total_duration": round(df["duration"].sum() / 3600, 2),
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
            total_distance = df["distance"].sum() / 1000
            total_duration = df["duration"].sum() / 60

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

    def calculate_tss_for_run(
        self,
        distance_m: float,
        duration_s: float,
        avg_heart_rate: float,
        age: int = 30
    ) -> float:
        """
        计算单次跑步的 TSS 值

        Args:
            distance_m: 距离（米）
            duration_s: 时长（秒）
            avg_heart_rate: 平均心率
            age: 年龄（用于估算最大心率）

        Returns:
            float: TSS 值
        """
        if distance_m <= 0 or duration_s <= 0:
            return 0.0

        max_hr = 220 - age
        rest_hr = 60

        if avg_heart_rate <= rest_hr:
            return 0.0

        intensity_factor = (avg_heart_rate - rest_hr) / (max_hr - rest_hr)
        intensity_factor = min(intensity_factor, 1.5)

        tss = (duration_s * intensity_factor) / 3600 * 100

        return round(tss, 2)

    def get_training_load(self, days: int = 42) -> Dict[str, Any]:
        """
        获取训练负荷（ATL/CTL）

        Args:
            days: 分析天数

        Returns:
            dict: 训练负荷数据
        """
        from datetime import datetime, timedelta

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        lf = self.storage.read_parquet()

        df = lf.filter(
            pl.col("timestamp").is_between(start_date, end_date)
        ).collect()

        if df.is_empty():
            return {"message": "暂无跑步数据", "atl": 0.0, "ctl": 0.0, "tsb": 0.0}

        tss_values = []
        for row in df.iter_rows(named=True):
            tss = self.calculate_tss_for_run(
                distance_m=row.get("total_distance", 0),
                duration_s=row.get("total_timer_time", 0),
                avg_heart_rate=row.get("avg_heart_rate", 0)
            )
            tss_values.append(tss)

        if not tss_values:
            return {"message": "数据不足", "atl": 0.0, "ctl": 0.0, "tsb": 0.0}

        atl = self.calculate_atl(tss_values)
        ctl = self.calculate_ctl(tss_values)
        tsb = ctl - atl

        return {
            "atl": atl,
            "ctl": ctl,
            "tsb": round(tsb, 2),
            "days_analyzed": days,
            "runs_count": len(tss_values),
        }
