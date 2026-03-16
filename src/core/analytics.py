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

    def get_running_summary(
        self, start_date: Optional[str] = None, end_date: Optional[str] = None
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
            df = lf.collect()

            if df.is_empty():
                return pl.DataFrame()

            result = df.select(
                [
                    pl.len().alias("total_runs"),
                    pl.col("total_distance").sum().alias("total_distance"),
                    pl.col("total_timer_time").sum().alias("total_timer_time"),
                    pl.col("total_distance").mean().alias("avg_distance"),
                    pl.col("total_timer_time").mean().alias("avg_timer_time"),
                    pl.col("total_distance").max().alias("max_distance"),
                    pl.col("avg_heart_rate").mean().alias("avg_heart_rate"),
                ]
            )

            return result
        except Exception as e:
            raise RuntimeError(f"获取跑步摘要失败: {e}") from e

    def analyze_hr_drift(
        self, heart_rate: List[float], pace: List[float]
    ) -> Dict[str, Any]:
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
                first_half_hr = heart_rate[: len(heart_rate) // 2]
                second_half_hr = heart_rate[len(heart_rate) // 2 :]
                drift = (sum(second_half_hr) / len(second_half_hr)) - (
                    sum(first_half_hr) / len(first_half_hr)
                )
            else:
                drift = 0

            drift_rate = (
                (drift / (sum(heart_rate) / len(heart_rate))) * 100 if heart_rate else 0
            )

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

    def calculate_atl_ctl(
        self, tss_values: List[float], atl_days: int = 7, ctl_days: int = 42
    ) -> Dict[str, float]:
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
        avg_heart_rate: Optional[float],
        age: int = 30,
        rest_hr: int = 60,
    ) -> float:
        """
        计算单次跑步的 TSS 值（基于心率的训练压力分数）

        计算公式：
            IF = (avg_hr - rest_hr) / (max_hr - rest_hr)
            TSS = (duration_s * IF²) / 3600 * 100

        Args:
            distance_m: 距离（米）
            duration_s: 时长（秒）
            avg_heart_rate: 平均心率（可为 None）
            age: 年龄（用于估算最大心率，默认 30）
            rest_hr: 静息心率（默认 60）

        Returns:
            float: TSS 值，范围 0-500

        Notes:
            - 心率数据缺失时返回 0
            - 时长为 0 时返回 0
            - 强度因子上限为 1.5
            - 最大心率估算公式：220 - 年龄
        """
        # 边界条件：时长为 0 或距离为 0
        if duration_s <= 0 or distance_m <= 0:
            return 0.0

        # 边界条件：心率数据缺失
        if avg_heart_rate is None or avg_heart_rate <= 0:
            return 0.0

        # 计算最大心率（220 - 年龄公式）
        max_hr = 220 - age

        # 边界条件：静息心率必须小于最大心率
        if rest_hr >= max_hr:
            return 0.0

        # 边界条件：平均心率不能超过最大心率
        if avg_heart_rate > max_hr:
            avg_heart_rate = max_hr

        # 边界条件：平均心率低于静息心率，返回 0
        if avg_heart_rate <= rest_hr:
            return 0.0

        # 计算强度因子 (Intensity Factor)
        # IF = (avg_hr - rest_hr) / (max_hr - rest_hr)
        intensity_factor = (avg_heart_rate - rest_hr) / (max_hr - rest_hr)

        # 强度因子上限为 1.5
        intensity_factor = min(intensity_factor, 1.5)

        # 计算 TSS：TSS = (duration_s * IF²) / 3600 * 100
        tss = (duration_s * intensity_factor**2) / 3600 * 100

        # TSS 范围限制：0-500
        tss = max(0.0, min(tss, 500.0))

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

        df = lf.filter(pl.col("timestamp").is_between(start_date, end_date)).collect()

        if df.is_empty():
            return {"message": "暂无跑步数据", "atl": 0.0, "ctl": 0.0, "tsb": 0.0}

        tss_values = []
        for row in df.iter_rows(named=True):
            tss = self.calculate_tss_for_run(
                distance_m=row.get("total_distance", 0),
                duration_s=row.get("total_timer_time", 0),
                avg_heart_rate=row.get("avg_heart_rate", 0),
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

    def _calculate_hr_zones(self, max_hr: int) -> Dict[str, tuple]:
        """
        计算心率区间边界

        Args:
            max_hr: 最大心率

        Returns:
            dict: 心率区间边界字典
        """
        return {
            "zone1": (int(max_hr * 0.50), int(max_hr * 0.60)),  # 恢复区
            "zone2": (int(max_hr * 0.60), int(max_hr * 0.70)),  # 有氧基础区
            "zone3": (int(max_hr * 0.70), int(max_hr * 0.80)),  # 有氧耐力区
            "zone4": (int(max_hr * 0.80), int(max_hr * 0.90)),  # 乳酸阈值区
            "zone5": (int(max_hr * 0.90), int(max_hr * 1.00)),  # 无氧耐力区
        }

    def _calculate_zone_time(
        self, heart_rate_data: List[int], hr_zones: Dict[str, tuple]
    ) -> Dict[str, int]:
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

    def _calculate_aerobic_effect(
        self, zone_time: Dict[str, int], total_duration: int
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

        # 计算区间2和区间3的加权时长
        zone2_time = zone_time.get("zone2", 0)
        zone3_time = zone_time.get("zone3", 0)

        # 加权计算：区间3权重更高
        weighted_time = zone2_time * 0.8 + zone3_time * 1.0

        # 计算占比
        ratio = weighted_time / total_duration

        # 映射到1.0-5.0范围
        # ratio 0.0 -> 1.0, ratio 0.5 -> 3.0, ratio 1.0 -> 5.0
        effect = 1.0 + ratio * 4.0

        return round(min(max(effect, 1.0), 5.0), 1)

    def _calculate_anaerobic_effect(
        self, zone_time: Dict[str, int], total_duration: int
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

        # 计算区间4和区间5的加权时长
        zone4_time = zone_time.get("zone4", 0)
        zone5_time = zone_time.get("zone5", 0)

        # 加权计算：区间5权重更高
        weighted_time = zone4_time * 0.8 + zone5_time * 1.2

        # 计算占比
        ratio = weighted_time / total_duration

        # 映射到1.0-5.0范围
        # ratio 0.0 -> 1.0, ratio 0.3 -> 3.0, ratio 0.6 -> 5.0
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
        # 基础恢复时间（基于训练效果）
        base_recovery = (aerobic_effect + anaerobic_effect) / 2 * 12  # 最大60小时

        # 时长因子（每30分钟增加10%恢复时间）
        duration_factor = 1.0 + (duration_s / 1800) * 0.1

        # 心率强度因子
        hr_intensity = avg_heart_rate / max_hr if max_hr > 0 else 0.5
        hr_factor = 1.0 + (hr_intensity - 0.5) * 0.5

        # 综合计算
        recovery_hours = base_recovery * duration_factor * hr_factor

        # 限制在6-72小时范围内
        return int(min(max(recovery_hours, 6), 72))

    def get_training_effect(
        self,
        heart_rate_data: List[int],
        duration_s: float,
        age: int = 30,
        avg_heart_rate: Optional[float] = None,
    ) -> Dict[str, Any]:
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
        # 参数验证
        if duration_s <= 0:
            raise ValueError("训练时长必须为正数")
        if age <= 0 or age > 120:
            raise ValueError("年龄必须在1-120之间")

        # 估算最大心率
        max_hr = 220 - age

        # 计算平均心率
        if avg_heart_rate is None:
            if not heart_rate_data:
                raise ValueError("心率数据不能为空")
            avg_heart_rate = sum(heart_rate_data) / len(heart_rate_data)

        # 计算心率区间
        hr_zones = self._calculate_hr_zones(max_hr)

        # 计算各区间时长
        zone_time = self._calculate_zone_time(heart_rate_data, hr_zones)

        # 计算总时长（用于百分比计算）
        total_zone_time = sum(zone_time.values())
        if total_zone_time == 0:
            total_zone_time = int(duration_s)

        # 计算有氧效果
        aerobic_effect = self._calculate_aerobic_effect(zone_time, total_zone_time)

        # 计算无氧效果
        anaerobic_effect = self._calculate_anaerobic_effect(zone_time, total_zone_time)

        # 计算恢复时间
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

    def get_heart_rate_zones(
        self,
        age: int = 30,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
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

        # 计算最大心率
        max_hr = 220 - age

        # 定义心率区间边界
        zone_boundaries = {
            "Z1": (0.50, 0.60, "恢复区"),
            "Z2": (0.60, 0.70, "有氧区"),
            "Z3": (0.70, 0.80, "节奏区"),
            "Z4": (0.80, 0.90, "阈值区"),
            "Z5": (0.90, 1.00, "无氧区"),
        }

        try:
            lf = self.storage.read_parquet()

            # 日期过滤
            if start_date or end_date:
                from datetime import datetime

                if start_date:
                    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                    lf = lf.filter(pl.col("timestamp") >= start_dt)
                if end_date:
                    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                    # 包含结束日期当天
                    from datetime import timedelta

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

            # 检查是否有心率数据
            if "heart_rate" not in df.columns and "avg_heart_rate" not in df.columns:
                return {
                    "max_hr": max_hr,
                    "zones": [],
                    "total_time_in_hr": 0,
                    "activities_count": df.height,
                    "message": "暂无心率数据",
                }

            # 使用秒级心率数据（heart_rate字段）进行精确分析
            if "heart_rate" in df.columns:
                # 过滤有效心率数据
                hr_df = df.filter(
                    pl.col("heart_rate").is_not_null() & (pl.col("heart_rate") > 0)
                )

                if hr_df.is_empty():
                    # 回退到使用平均心率
                    return self._calculate_zones_from_avg_hr(
                        df, max_hr, zone_boundaries
                    )

                # 计算每个心率区间的时间
                zone_times = {}
                for zone_name, (
                    lower_pct,
                    upper_pct,
                    zone_desc,
                ) in zone_boundaries.items():
                    lower_hr = int(max_hr * lower_pct)
                    upper_hr = int(max_hr * upper_pct)

                    # 统计该区间内的记录数（假设每条记录代表1秒）
                    zone_count = hr_df.filter(
                        (pl.col("heart_rate") >= lower_hr)
                        & (pl.col("heart_rate") < upper_hr)
                    ).height

                    # Z5 包含上边界
                    if zone_name == "Z5":
                        zone_count = hr_df.filter(
                            (pl.col("heart_rate") >= lower_hr)
                            & (pl.col("heart_rate") <= upper_hr)
                        ).height

                    zone_times[zone_name] = zone_count

                total_records = hr_df.height
                total_time_in_hr = total_records  # 秒级记录数即为时长

            else:
                # 使用平均心率估算
                return self._calculate_zones_from_avg_hr(df, max_hr, zone_boundaries)

            # 构建结果
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

    def _calculate_zones_from_avg_hr(
        self, df: pl.DataFrame, max_hr: int, zone_boundaries: Dict[str, tuple]
    ) -> Dict[str, Any]:
        """
        基于平均心率估算心率区间分布

        Args:
            df: 包含 avg_heart_rate 的 DataFrame
            max_hr: 最大心率
            zone_boundaries: 心率区间边界定义

        Returns:
            Dict[str, Any]: 心率区间分析结果
        """
        # 过滤有平均心率的活动
        hr_df = df.filter(
            pl.col("avg_heart_rate").is_not_null() & (pl.col("avg_heart_rate") > 0)
        )

        if hr_df.is_empty():
            return {
                "max_hr": max_hr,
                "zones": [],
                "total_time_in_hr": 0,
                "activities_count": df.height,
                "message": "暂无有效心率数据",
            }

        # 使用活动时长作为权重计算区间分布
        zone_times = {zone: 0 for zone in zone_boundaries.keys()}
        total_time = 0

        for row in hr_df.iter_rows(named=True):
            avg_hr = row.get("avg_heart_rate", 0)
            duration = row.get("total_timer_time", 0)

            if avg_hr <= 0 or duration <= 0:
                continue

            total_time += duration

            # 判断该活动主要在哪个心率区间
            for zone_name, (lower_pct, upper_pct, _) in zone_boundaries.items():
                lower_hr = int(max_hr * lower_pct)
                upper_hr = int(max_hr * upper_pct)

                if zone_name == "Z5":
                    if lower_hr <= avg_hr <= upper_hr:
                        zone_times[zone_name] += duration
                        break
                else:
                    if lower_hr <= avg_hr < upper_hr:
                        zone_times[zone_name] += duration
                        break

        # 构建结果
        zones = []
        for zone_name, (lower_pct, upper_pct, zone_desc) in zone_boundaries.items():
            time_seconds = zone_times.get(zone_name, 0)
            percentage = (time_seconds / total_time * 100) if total_time > 0 else 0.0

            zones.append(
                {
                    "zone": zone_name,
                    "name": zone_desc,
                    "hr_range": f"{int(max_hr * lower_pct)}-{int(max_hr * upper_pct)}",
                    "lower_hr": int(max_hr * lower_pct),
                    "upper_hr": int(max_hr * upper_pct),
                    "time_seconds": int(time_seconds),
                    "percentage": round(percentage, 2),
                }
            )

        return {
            "max_hr": max_hr,
            "zones": zones,
            "total_time_in_hr": int(total_time),
            "activities_count": hr_df.height,
            "data_type": "avg_heart_rate",
        }

    def get_pace_distribution(self, year: Optional[int] = None) -> Dict[str, Any]:
        """
        获取配速分布统计

        Args:
            year: 年份，不指定则统计所有数据

        Returns:
            Dict[str, Any]: 配速分布数据，包含各区间统计和趋势分析

        Raises:
            RuntimeError: 当数据处理失败时
        """
        # 配速区间定义（秒/公里）
        PACE_ZONES = {
            "Z1": {"min": 360, "max": float("inf"), "label": "恢复跑"},
            "Z2": {"min": 300, "max": 360, "label": "轻松跑"},
            "Z3": {"min": 240, "max": 300, "label": "节奏跑"},
            "Z4": {"min": 210, "max": 240, "label": "间歇跑"},
            "Z5": {"min": 0, "max": 210, "label": "冲刺跑"},
        }

        try:
            # 读取数据
            df = self.storage.read_activities(year)

            if df.is_empty():
                return {"zones": {}, "trend": [], "message": "暂无跑步数据"}

            # 计算每次跑步的平均配速（秒/公里）
            # 配速 = 时长(秒) / 距离(公里)
            df = df.with_columns(
                [
                    (
                        pl.col("total_timer_time") / (pl.col("total_distance") / 1000)
                    ).alias("avg_pace_sec_per_km")
                ]
            )

            # 过滤掉无效配速（距离为0或时间为0）
            df = df.filter(
                (pl.col("total_distance") > 0)
                & (pl.col("total_timer_time") > 0)
                & (pl.col("avg_pace_sec_per_km").is_not_null())
            )

            if df.is_empty():
                return {"zones": {}, "trend": [], "message": "无有效配速数据"}

            # 为每条记录分配配速区间
            def get_pace_zone(pace: float) -> str:
                """根据配速返回区间"""
                if pace > 360:
                    return "Z1"
                elif pace > 300:
                    return "Z2"
                elif pace > 240:
                    return "Z3"
                elif pace > 210:
                    return "Z4"
                else:
                    return "Z5"

            # 添加区间列
            df = df.with_columns(
                [
                    pl.col("avg_pace_sec_per_km")
                    .map_elements(get_pace_zone, return_dtype=pl.String)
                    .alias("pace_zone")
                ]
            )

            # 按区间分组统计
            zone_stats = df.group_by("pace_zone").agg(
                [
                    pl.len().alias("count"),
                    pl.col("total_distance").sum().alias("total_distance"),
                    pl.col("avg_pace_sec_per_km").mean().alias("avg_pace"),
                    pl.col("total_timer_time").sum().alias("total_time"),
                ]
            )

            # 构建返回结果
            zones_result = {}
            for row in zone_stats.iter_rows(named=True):
                zone = row["pace_zone"]
                if zone in PACE_ZONES:
                    zones_result[zone] = {
                        "count": row["count"],
                        "distance": round(row["total_distance"], 2),
                        "label": PACE_ZONES[zone]["label"],
                        "avg_pace": round(row["avg_pace"], 2),
                        "total_time": row["total_time"],
                    }

            # 补充空区间
            for zone, info in PACE_ZONES.items():
                if zone not in zones_result:
                    zones_result[zone] = {
                        "count": 0,
                        "distance": 0.0,
                        "label": info["label"],
                        "avg_pace": 0.0,
                        "total_time": 0,
                    }

            # 计算配速趋势（按时间排序）
            trend_df = df.sort("timestamp").select(
                ["timestamp", "avg_pace_sec_per_km", "total_distance", "pace_zone"]
            )

            trend_data = []
            for row in trend_df.iter_rows(named=True):
                trend_data.append(
                    {
                        "date": row["timestamp"].strftime("%Y-%m-%d")
                        if hasattr(row["timestamp"], "strftime")
                        else str(row["timestamp"]),
                        "pace": round(row["avg_pace_sec_per_km"], 2),
                        "distance": round(row["total_distance"], 2),
                        "zone": row["pace_zone"],
                    }
                )

            return {
                "zones": zones_result,
                "trend": trend_data,
                "total_runs": df.height,
                "total_distance": round(df["total_distance"].sum(), 2),
            }

        except Exception as e:
            raise RuntimeError(f"获取配速分布失败: {e}") from e
