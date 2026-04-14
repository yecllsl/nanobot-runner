# 心率分析器
# 分析心率漂移、心率区间、训练效果等

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

import polars as pl

from src.core.models import HRDriftResult

if TYPE_CHECKING:
    from src.core.storage import StorageManager


class HeartRateAnalyzer:
    """心率分析器"""

    def __init__(self, storage_manager: "StorageManager") -> None:
        """
        初始化心率分析器

        Args:
            storage_manager: StorageManager实例
        """
        self.storage = storage_manager

    def analyze_hr_drift(
        self, heart_rate: list[float], pace: list[float]
    ) -> HRDriftResult:
        """
        分析心率漂移情况

        Args:
            heart_rate: 心率数据列表
            pace: 配速数据列表

        Returns:
            HRDriftResult: 分析结果
        """
        if not heart_rate or not pace:
            return HRDriftResult(error="数据量不足")

        hr_clean = []
        pace_clean = []

        for hr, p in zip(heart_rate, pace):
            if hr is not None and p is not None and p > 0:
                hr_clean.append(hr)
                pace_clean.append(p)

        if len(hr_clean) < 10 or len(pace_clean) < 10:
            return HRDriftResult(error="数据量不足")

        try:
            hr_series = pl.Series("heart_rate", hr_clean)
            pace_series = pl.Series("pace", pace_clean)

            df = pl.DataFrame([hr_series, pace_series])
            correlation = df.corr()[0, 1]

            if len(hr_clean) >= 2:
                first_half_hr = hr_clean[: len(hr_clean) // 2]
                second_half_hr = hr_clean[len(hr_clean) // 2 :]
                drift = (sum(second_half_hr) / len(second_half_hr)) - (
                    sum(first_half_hr) / len(first_half_hr)
                )
            else:
                drift = 0

            drift_rate = (
                (drift / (sum(hr_clean) / len(hr_clean))) * 100 if hr_clean else 0
            )

            if drift_rate > 5:
                assessment = "心率漂移明显，可能有氧基础不扎实"
            elif drift_rate > 0:
                assessment = "心率漂移正常，跑步状态稳定"
            else:
                assessment = "心率表现优异，状态非常好"

            return HRDriftResult(
                drift=round(drift, 2),
                drift_rate=round(drift_rate, 2),
                correlation=round(correlation, 3) if correlation else 0,
                assessment=assessment,
            )
        except Exception as e:
            return HRDriftResult(error=f"分析失败: {str(e)}")

    def analyze_hr_drift_vectorized(
        self, heart_rate: pl.Series, pace: pl.Series
    ) -> dict[str, Any]:
        """
        向量化分析心率漂移情况

        使用 Polars 表达式批量计算，性能提升 30%+。

        Args:
            heart_rate: 心率数据序列
            pace: 配速数据序列

        Returns:
            dict: 分析结果
        """
        if heart_rate.is_empty() or pace.is_empty():
            return {"error": "数据量不足"}

        df = pl.DataFrame({"heart_rate": heart_rate, "pace": pace})

        df_clean = df.filter(
            pl.col("heart_rate").is_not_null()
            & pl.col("pace").is_not_null()
            & (pl.col("pace") > 0)
        )

        if df_clean.height < 10:
            return {"error": "数据量不足"}

        try:
            hr_series = df_clean["heart_rate"]
            df_clean["pace"]

            correlation = float(df_clean.select(pl.corr("heart_rate", "pace")).item())

            n = hr_series.len()
            first_half_end = n // 2

            first_half_hr = hr_series.slice(0, first_half_end)
            second_half_hr = hr_series.slice(first_half_end, n - first_half_end)

            first_half_mean = float(first_half_hr.mean())  # type: ignore[arg-type]
            second_half_mean = float(second_half_hr.mean())  # type: ignore[arg-type]

            drift = second_half_mean - first_half_mean

            overall_mean = float(hr_series.mean())  # type: ignore[arg-type]
            drift_rate = (drift / overall_mean) * 100 if overall_mean > 0 else 0

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
                "assessment": assessment,
            }
        except Exception as e:
            return {"error": f"分析失败: {str(e)}"}

    def analyze_hr_drift_batch(
        self, df: pl.DataFrame, hr_col: str = "heart_rate", pace_col: str = "pace"
    ) -> list[dict[str, Any]]:
        """
        批量分析心率漂移情况

        Args:
            df: 包含心率数据的 DataFrame
            hr_col: 心率列名
            pace_col: 配速列名

        Returns:
            List[Dict[str, Any]]: 分析结果列表
        """
        results = []

        if hr_col not in df.columns or pace_col not in df.columns:
            return [{"error": "缺少必要列"}]

        for i in range(df.height):
            hr_data = df[hr_col][i]
            pace_data = df[pace_col][i]

            if hr_data is None or pace_data is None:
                results.append({"error": "数据缺失"})
                continue

            hr_series = pl.Series(hr_data) if isinstance(hr_data, list) else hr_data

            if isinstance(pace_data, list):
                pace_series = pl.Series(pace_data)
            else:
                pace_series = pace_data

            result = self.analyze_hr_drift_vectorized(hr_series, pace_series)
            results.append(result)

        return results

    def _calculate_hr_zones(self, max_hr: int) -> dict[str, tuple]:
        """
        计算心率区间边界

        Args:
            max_hr: 最大心率

        Returns:
            dict: 心率区间边界字典
        """
        return {
            "zone1": (int(max_hr * 0.50), int(max_hr * 0.60)),
            "zone2": (int(max_hr * 0.60), int(max_hr * 0.70)),
            "zone3": (int(max_hr * 0.70), int(max_hr * 0.80)),
            "zone4": (int(max_hr * 0.80), int(max_hr * 0.90)),
            "zone5": (int(max_hr * 0.90), int(max_hr * 1.00)),
        }

    def _calculate_zone_time(
        self, heart_rate_data: list[int], hr_zones: dict[str, tuple]
    ) -> dict[str, int]:
        """
        计算各心率区间的时长（秒）

        Args:
            heart_rate_data: 心率数据列表（每秒一个数据点）
            hr_zones: 心率区间边界

        Returns:
            dict: 各区间时长（秒）
        """
        zone_time = {"zone1": 0, "zone2": 0, "zone3": 0, "zone4": 0, "zone5": 0}

        if not heart_rate_data:
            return zone_time

        for hr in heart_rate_data:
            if hr < hr_zones["zone1"][0]:
                continue
            elif hr < hr_zones["zone1"][1]:
                zone_time["zone1"] += 1
            elif hr < hr_zones["zone2"][1]:
                zone_time["zone2"] += 1
            elif hr < hr_zones["zone3"][1]:
                zone_time["zone3"] += 1
            elif hr < hr_zones["zone4"][1]:
                zone_time["zone4"] += 1
            else:
                zone_time["zone5"] += 1

        return zone_time

    def _calculate_zone_time_vectorized(
        self, heart_rate_series: pl.Series, hr_zones: dict[str, tuple]
    ) -> dict[str, int]:
        """
        向量化计算各心率区间的时长（秒）

        使用 Polars 表达式批量计算，性能提升 30%+。

        Args:
            heart_rate_series: 心率数据序列
            hr_zones: 心率区间边界

        Returns:
            dict: 各区间时长（秒）
        """
        zone_time = {"zone1": 0, "zone2": 0, "zone3": 0, "zone4": 0, "zone5": 0}

        if heart_rate_series.is_empty():
            return zone_time

        df = pl.DataFrame({"hr": heart_rate_series})

        df_clean = df.filter(pl.col("hr").is_not_null() & (pl.col("hr") > 0))

        if df_clean.is_empty():
            return zone_time

        zone_time["zone1"] = df_clean.filter(
            (pl.col("hr") >= hr_zones["zone1"][0])
            & (pl.col("hr") < hr_zones["zone1"][1])
        ).height

        zone_time["zone2"] = df_clean.filter(
            (pl.col("hr") >= hr_zones["zone2"][0])
            & (pl.col("hr") < hr_zones["zone2"][1])
        ).height

        zone_time["zone3"] = df_clean.filter(
            (pl.col("hr") >= hr_zones["zone3"][0])
            & (pl.col("hr") < hr_zones["zone3"][1])
        ).height

        zone_time["zone4"] = df_clean.filter(
            (pl.col("hr") >= hr_zones["zone4"][0])
            & (pl.col("hr") < hr_zones["zone4"][1])
        ).height

        zone_time["zone5"] = df_clean.filter(
            pl.col("hr") >= hr_zones["zone5"][0]
        ).height

        return zone_time

    def _calculate_aerobic_effect(
        self, zone_time: dict[str, int], total_duration: int
    ) -> float:
        """
        计算有氧训练效果（1.0-5.0）

        有氧效果基于心率区间2-3的时间占比：
        - 区间2（有氧基础）: 权重0.8
        - 区间3（有氧耐力）: 权重1.0

        Args:
            zone_time: 各区间时长
            total_duration: 总时长（秒）

        Returns:
            float: 有氧效果值（1.0-5.0）
        """
        if total_duration == 0:
            return 1.0

        zone2_time = zone_time.get("zone2", 0)
        zone3_time = zone_time.get("zone3", 0)

        weighted_time = zone2_time * 0.8 + zone3_time * 1.0

        ratio = weighted_time / total_duration

        effect = 1.0 + ratio * 4.0

        return round(min(max(effect, 1.0), 5.0), 1)

    def _calculate_anaerobic_effect(
        self, zone_time: dict[str, int], total_duration: int
    ) -> float:
        """
        计算无氧训练效果（1.0-5.0）

        无氧效果基于心率区间4-5的时间占比：
        - 区间4（乳酸阈值）: 权重0.8
        - 区间5（无氧耐力）: 权重1.2

        Args:
            zone_time: 各区间时长
            total_duration: 总时长（秒）

        Returns:
            float: 无氧效果值（1.0-5.0）
        """
        if total_duration == 0:
            return 1.0

        zone4_time = zone_time.get("zone4", 0)
        zone5_time = zone_time.get("zone5", 0)

        weighted_time = zone4_time * 0.8 + zone5_time * 1.2

        ratio = weighted_time / total_duration

        effect = 1.0 + ratio * 6.67

        return round(min(max(effect, 1.0), 5.0), 1)

    def _calculate_recovery_time(
        self,
        aerobic_effect: float,
        anaerobic_effect: float,
        duration_s: float,
        avg_heart_rate: float,
        max_hr: int,
    ) -> int:
        """
        计算恢复时间（小时）

        基于训练效果、时长和心率强度估算恢复时间

        Args:
            aerobic_effect: 有氧效果值
            anaerobic_effect: 无氧效果值
            duration_s: 训练时长（秒）
            avg_heart_rate: 平均心率
            max_hr: 最大心率

        Returns:
            int: 恢复时间（小时）
        """
        base_recovery = (aerobic_effect + anaerobic_effect) / 2 * 12

        duration_factor = 1.0 + (duration_s / 1800) * 0.1

        hr_intensity = avg_heart_rate / max_hr if max_hr > 0 else 0.5
        hr_factor = 1.0 + (hr_intensity - 0.5) * 0.5

        recovery_hours = base_recovery * duration_factor * hr_factor

        return int(min(max(recovery_hours, 6), 72))

    def get_training_effect(
        self,
        heart_rate_data: list[int],
        duration_s: float,
        age: int = 30,
        avg_heart_rate: float | None = None,
    ) -> dict[str, Any]:
        """
        获取训练效果评估

        Args:
            heart_rate_data: 心率数据列表（每秒一个数据点）
            duration_s: 训练时长（秒）
            age: 年龄（用于估算最大心率）
            avg_heart_rate: 平均心率（可选，不提供则从数据计算）

        Returns:
            dict: 训练效果评估结果
                - aerobic_effect: 有氧效果（1.0-5.0）
                - anaerobic_effect: 无氧效果（1.0-5.0）
                - recovery_time_hours: 恢复时间（小时）
                - hr_zones: 心率区间边界
                - zone_time: 各区间时长
                - avg_heart_rate: 平均心率

        Raises:
            ValueError: 当输入参数无效时
        """
        if duration_s <= 0:
            raise ValueError("训练时长必须为正数")
        if age <= 0 or age > 120:
            raise ValueError("年龄必须在1-120之间")

        max_hr = 220 - age

        if avg_heart_rate is None:
            if not heart_rate_data:
                raise ValueError("心率数据不能为空")
            avg_heart_rate = sum(heart_rate_data) / len(heart_rate_data)

        hr_zones = self._calculate_hr_zones(max_hr)

        zone_time = self._calculate_zone_time(heart_rate_data, hr_zones)

        total_zone_time = sum(zone_time.values())
        if total_zone_time == 0:
            total_zone_time = int(duration_s)

        aerobic_effect = self._calculate_aerobic_effect(zone_time, total_zone_time)

        anaerobic_effect = self._calculate_anaerobic_effect(zone_time, total_zone_time)

        recovery_hours = self._calculate_recovery_time(
            aerobic_effect, anaerobic_effect, duration_s, avg_heart_rate, max_hr
        )

        return {
            "aerobic_effect": aerobic_effect,
            "anaerobic_effect": anaerobic_effect,
            "recovery_time_hours": recovery_hours,
            "hr_zones": hr_zones,
            "zone_time": zone_time,
            "avg_heart_rate": round(avg_heart_rate, 1),
            "max_heart_rate": max_hr,
        }

    def _calculate_zones_from_avg_hr(
        self,
        df: pl.DataFrame,
        max_hr: int,
        zone_boundaries: dict[str, tuple],
    ) -> dict[str, Any]:
        """
        使用平均心率估算心率区间分布

        Args:
            df: 活动数据DataFrame
            max_hr: 最大心率
            zone_boundaries: 心率区间边界

        Returns:
            dict: 心率区间分析结果
        """
        if "session_avg_heart_rate" not in df.columns:
            return {
                "max_hr": max_hr,
                "zones": [],
                "total_time_in_hr": 0,
                "activities_count": df.height,
                "message": "暂无心率数据",
            }

        hr_df = df.filter(
            pl.col("session_avg_heart_rate").is_not_null()
            & (pl.col("session_avg_heart_rate") > 0)
        )

        if hr_df.is_empty():
            return {
                "max_hr": max_hr,
                "zones": [],
                "total_time_in_hr": 0,
                "activities_count": df.height,
                "message": "暂无心率数据",
            }

        zone_times = {}
        for zone_name, (lower_pct, upper_pct, zone_desc) in zone_boundaries.items():
            lower_hr = int(max_hr * lower_pct)
            upper_hr = int(max_hr * upper_pct)

            zone_count = hr_df.filter(
                (pl.col("session_avg_heart_rate") >= lower_hr)
                & (pl.col("session_avg_heart_rate") < upper_hr)
            ).height

            if zone_name == "Z5":
                zone_count = hr_df.filter(
                    (pl.col("session_avg_heart_rate") >= lower_hr)
                    & (pl.col("session_avg_heart_rate") <= upper_hr)
                ).height

            zone_times[zone_name] = zone_count

        total_activities = hr_df.height

        zones = []
        for zone_name, (lower_pct, upper_pct, zone_desc) in zone_boundaries.items():
            count = zone_times.get(zone_name, 0)
            percentage = (
                (count / total_activities * 100) if total_activities > 0 else 0.0
            )

            zones.append(
                {
                    "zone": zone_name,
                    "name": zone_desc,
                    "hr_range": f"{int(max_hr * lower_pct)}-{int(max_hr * upper_pct)}",
                    "lower_hr": int(max_hr * lower_pct),
                    "upper_hr": int(max_hr * upper_pct),
                    "time_seconds": count,
                    "percentage": round(percentage, 2),
                }
            )

        return {
            "max_hr": max_hr,
            "zones": zones,
            "total_time_in_hr": total_activities,
            "activities_count": df.height,
            "message": "基于平均心率估算",
        }

    def get_heart_rate_zones(
        self,
        age: int = 30,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """
        计算心率区间分布

        基于最大心率百分比划分心率区间：
        - Z1 恢复区: 50-60% 最大心率
        - Z2 有氧区: 60-70% 最大心率
        - Z3 节奏区: 70-80% 最大心率
        - Z4 阈值区: 80-90% 最大心率
        - Z5 无氧区: 90-100% 最大心率

        Args:
            age: 年龄，用于计算最大心率（最大心率 = 220 - 年龄）
            start_date: 开始日期（可选，格式：YYYY-MM-DD）
            end_date: 结束日期（可选，格式：YYYY-MM-DD）

        Returns:
            Dict[str, Any]: 心率区间分析结果，包含：
                - max_hr: 最大心率
                - zones: 各区间详情列表
                - total_time_in_hr: 有心率数据的总时长（秒）
                - activities_count: 活动数量

        Raises:
            ValueError: 当年龄参数无效时
        """
        if age <= 0 or age > 120:
            raise ValueError("年龄必须在 1-120 范围内")

        max_hr = 220 - age

        zone_boundaries = {
            "Z1": (0.50, 0.60, "恢复区"),
            "Z2": (0.60, 0.70, "有氧区"),
            "Z3": (0.70, 0.80, "节奏区"),
            "Z4": (0.80, 0.90, "阈值区"),
            "Z5": (0.90, 1.00, "无氧区"),
        }

        try:
            lf = self.storage.read_parquet()

            if start_date or end_date:
                if start_date:
                    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                    lf = lf.filter(pl.col("timestamp") >= start_dt)
                if end_date:
                    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                    end_dt = end_dt + timedelta(days=1)
                    lf = lf.filter(pl.col("timestamp") < end_dt)

            df = lf.collect()

            if df.is_empty():
                return {
                    "max_hr": max_hr,
                    "zones": [],
                    "total_time_in_hr": 0,
                    "activities_count": 0,
                    "message": "暂无跑步数据",
                }

            if "heart_rate" not in df.columns and "avg_heart_rate" not in df.columns:
                return {
                    "max_hr": max_hr,
                    "zones": [],
                    "total_time_in_hr": 0,
                    "activities_count": df.height,
                    "message": "暂无心率数据",
                }

            if "heart_rate" in df.columns:
                hr_df = df.filter(
                    pl.col("heart_rate").is_not_null() & (pl.col("heart_rate") > 0)
                )

                if hr_df.is_empty():
                    return self._calculate_zones_from_avg_hr(
                        df, max_hr, zone_boundaries
                    )

                zone_times = {}
                for zone_name, (
                    lower_pct,
                    upper_pct,
                    zone_desc,
                ) in zone_boundaries.items():
                    lower_hr = int(max_hr * lower_pct)
                    upper_hr = int(max_hr * upper_pct)

                    zone_count = hr_df.filter(
                        (pl.col("heart_rate") >= lower_hr)
                        & (pl.col("heart_rate") < upper_hr)
                    ).height

                    if zone_name == "Z5":
                        zone_count = hr_df.filter(
                            (pl.col("heart_rate") >= lower_hr)
                            & (pl.col("heart_rate") <= upper_hr)
                        ).height

                    zone_times[zone_name] = zone_count

                total_records = hr_df.height
                total_time_in_hr = total_records

            else:
                return self._calculate_zones_from_avg_hr(df, max_hr, zone_boundaries)

            zones = []
            for zone_name, (lower_pct, upper_pct, zone_desc) in zone_boundaries.items():
                time_seconds = zone_times.get(zone_name, 0)
                percentage = (
                    (time_seconds / total_time_in_hr * 100)
                    if total_time_in_hr > 0
                    else 0.0
                )

                zones.append(
                    {
                        "zone": zone_name,
                        "name": zone_desc,
                        "hr_range": f"{int(max_hr * lower_pct)}-{int(max_hr * upper_pct)}",
                        "lower_hr": int(max_hr * lower_pct),
                        "upper_hr": int(max_hr * upper_pct),
                        "time_seconds": time_seconds,
                        "percentage": round(percentage, 2),
                    }
                )

            return {
                "max_hr": max_hr,
                "zones": zones,
                "total_time_in_hr": total_time_in_hr,
                "activities_count": df.height,
                "age": age,
            }

        except Exception as e:
            raise RuntimeError(f"心率区间分析失败: {e}") from e
