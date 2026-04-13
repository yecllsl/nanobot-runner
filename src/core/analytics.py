# 分析引擎
# 基于Polars实现核心数据分析算法

from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING, Any

import polars as pl

from src.core.heart_rate_analyzer import HeartRateAnalyzer
from src.core.race_prediction import RacePredictionEngine
from src.core.statistics_aggregator import StatisticsAggregator
from src.core.training_load_analyzer import TrainingLoadAnalyzer
from src.core.vdot_calculator import VDOTCalculator

if TYPE_CHECKING:
    from src.core.storage import StorageManager

# VDOT 计算常量 (Jack Daniels 公式)
VDOT_COEFFICIENT = 0.000104
VDOT_DISTANCE_EXPONENT = 1.06


def _resolve_col(df: pl.DataFrame, *candidates: str) -> str:
    """按优先级从候选列名中查找DataFrame中存在的列名

    Args:
        df: 目标DataFrame
        *candidates: 按优先级排列的候选列名

    Returns:
        str: 第一个存在的列名

    Raises:
        RuntimeError: 所有候选列名均不存在
    """
    for col in candidates:
        if col in df.columns:
            return col
    raise RuntimeError(f"DataFrame中未找到候选列: {candidates}")


VDOT_TIME_EXPONENT = 0.5
VDOT_MULTIPLIER = 100

# TSS 计算常量
DEFAULT_LTHR = 180  # 默认乳酸阈值心率

# 训练负荷计算常量
ATL_TIME_CONSTANT = 7.0  # 急性训练负荷时间常数（天）
CTL_TIME_CONSTANT = 42.0  # 慢性训练负荷时间常数（天）


class AnalyticsEngine:
    """数据分析引擎"""

    def __init__(self, storage_manager: "StorageManager") -> None:
        """
        初始化分析引擎

        Args:
            storage_manager: StorageManager实例
        """
        self.storage = storage_manager
        self.vdot_calculator = VDOTCalculator()
        self.training_load_analyzer = TrainingLoadAnalyzer()
        self.heart_rate_analyzer = HeartRateAnalyzer(storage_manager)
        self.statistics_aggregator = StatisticsAggregator(storage_manager)
        self.race_prediction_engine = RacePredictionEngine()

    def calculate_vdot(self, distance_m: float, time_s: float) -> float:
        """
        计算VDOT值（跑力值）

        使用 Jack Daniels 的 VDOT 表近似公式

        Args:
            distance_m: 距离（米）
            time_s: 用时（秒）

        Returns:
            float: VDOT值

        Raises:
            ValueError: 当距离或时间为负数或零时
        """
        return self.vdot_calculator.calculate_vdot(distance_m, time_s)

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
        return self.training_load_analyzer.calculate_tss(
            heart_rate_data, duration_s, ftp
        )

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
        return self.statistics_aggregator.get_running_summary(start_date, end_date)

    def analyze_hr_drift(
        self, heart_rate: list[float], pace: list[float]
    ) -> dict[str, Any]:
        """
        分析心率漂移情况

        Args:
            heart_rate: 心率数据列表
            pace: 配速数据列表

        Returns:
            dict: 分析结果
        """
        return self.heart_rate_analyzer.analyze_hr_drift(heart_rate, pace)

    def calculate_atl(self, tss_values: list[float]) -> float:
        """
        计算急性训练负荷（ATL，7天指数移动平均）

        Args:
            tss_values: TSS值列表

        Returns:
            float: ATL值
        """
        return self.training_load_analyzer.calculate_atl(tss_values)

    def calculate_ctl(self, tss_values: list[float]) -> float:
        """
        计算慢性训练负荷（CTL，42天指数移动平均）

        Args:
            tss_values: TSS值列表

        Returns:
            float: CTL值
        """
        return self.training_load_analyzer.calculate_ctl(tss_values)

    def calculate_atl_ctl(
        self, tss_values: list[float], _atl_days: int = 7, _ctl_days: int = 42
    ) -> dict[str, float]:
        """
        计算ATL和CTL

        Args:
            tss_values: TSS值列表
            atl_days: ATL计算天数
            ctl_days: CTL计算天数

        Returns:
            dict: ATL和CTL值
        """
        return self.training_load_analyzer.calculate_atl_ctl(tss_values)

    def get_running_stats(self, year: int | None = None) -> dict[str, Any]:
        """
        获取跑步统计数据

        Args:
            year: 年份，不指定则统计所有数据

        Returns:
            Dict[str, Any]: 统计信息字典
        """
        return self.statistics_aggregator.get_running_stats(year)

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
        except Exception as e:
            raise ValueError(f"配速计算失败: {e}") from e

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
        except Exception as e:
            raise ValueError(f"配速计算失败: {e}") from e

    def get_vdot_trend(self, days: int = 30) -> list[dict[str, Any]]:
        """
        获取VDOT趋势数据

        Args:
            days: 统计天数

        Returns:
            List[Dict[str, Any]]: VDOT趋势数据
        """
        try:
            lf = self.storage.read_parquet()

            if len(lf.collect_schema()) == 0:
                return []

            recent_lf = lf.filter(
                pl.col("timestamp")
                >= (pl.col("timestamp").max() - pl.duration(days=days))
            ).sort("timestamp")

            df = recent_lf.collect()

            if df.is_empty():
                return []

            distance_col = _resolve_col(
                df, "session_total_distance", "total_distance", "distance"
            )
            duration_col = _resolve_col(
                df, "session_total_timer_time", "total_timer_time", "duration"
            )

            vdot_series = self.vdot_calculator.calculate_vdot_batch(
                df, distance_col=distance_col, duration_col=duration_col
            )

            date_series = df["timestamp"].dt.strftime("%Y-%m-%d")
            distance_series = df[distance_col]
            duration_series = df[duration_col]

            trend_data = []
            for i in range(df.height):
                trend_data.append(
                    {
                        "date": date_series[i],
                        "vdot": float(vdot_series[i]),
                        "distance": float(distance_series[i]),
                        "duration": float(duration_series[i]),
                    }
                )

            return trend_data
        except Exception as e:
            raise RuntimeError(f"获取VDOT趋势失败: {e}") from e

    def calculate_tss_for_run(
        self,
        distance_m: float,
        duration_s: float,
        avg_heart_rate: float | None,
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
        # 边界条件：参数为 None
        if distance_m is None or duration_s is None:
            return 0.0

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

    def get_training_load(self, days: int = 42) -> dict[str, Any]:
        """
        获取训练负荷（ATL/CTL/TSB）及体能状态评估

        计算说明：
        - ATL (急性训练负荷): 7天 EWMA，反映短期疲劳
        - CTL (慢性训练负荷): 42天 EWMA，反映长期体能
        - TSB (训练压力平衡): CTL - ATL，反映当前状态

        Args:
            days: 分析天数（建议至少 42 天以获得准确的 CTL）

        Returns:
            dict: 训练负荷数据，包含：
                - atl: 急性训练负荷
                - ctl: 慢性训练负荷
                - tsb: 训练压力平衡
                - fitness_status: 体能状态评估
                - training_advice: 训练建议
                - days_analyzed: 分析天数
                - runs_count: 跑步次数
                - message: 提示信息（数据不足时）
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        lf = self.storage.read_parquet()

        if len(lf.collect_schema()) == 0:
            return {
                "message": "暂无跑步数据，请先导入 FIT 文件",
                "atl": 0.0,
                "ctl": 0.0,
                "tsb": 0.0,
                "fitness_status": "数据不足",
                "training_advice": "请先导入跑步数据以进行训练负荷分析",
                "days_analyzed": days,
                "runs_count": 0,
            }

        df = (
            lf.filter(pl.col("session_start_time").is_between(start_date, end_date))
            .sort("session_start_time")
            .collect()
        )

        if df.is_empty():
            return {
                "message": "暂无跑步数据，请先导入 FIT 文件",
                "atl": 0.0,
                "ctl": 0.0,
                "tsb": 0.0,
                "fitness_status": "数据不足",
                "training_advice": "请先导入跑步数据以进行训练负荷分析",
                "days_analyzed": days,
                "runs_count": 0,
            }

        tss_values = []
        for row in df.iter_rows(named=True):
            tss = self.training_load_analyzer.calculate_tss_for_run(
                distance_m=row.get("session_total_distance", 0),
                duration_s=row.get("session_total_timer_time", 0),
                avg_heart_rate=row.get("session_avg_heart_rate"),
            )
            tss_values.append(tss)

        valid_tss = [tss for tss in tss_values if tss > 0]

        if not valid_tss:
            return {
                "message": "暂无有效训练数据（心率数据缺失），无法计算训练负荷",
                "atl": 0.0,
                "ctl": 0.0,
                "tsb": 0.0,
                "fitness_status": "数据不足",
                "training_advice": "训练数据缺少心率信息，建议使用带有心率监测的设备记录训练",
                "days_analyzed": days,
                "runs_count": len(tss_values),
            }

        if len(valid_tss) < 7:
            message = f"数据量较少（{len(valid_tss)} 次训练），建议积累更多数据以获得更准确的分析"
        elif days < 42:
            message = (
                f"分析周期较短（{days} 天），建议使用 42 天以上数据以获得准确的 CTL"
            )
        else:
            message = None

        atl = self.training_load_analyzer.calculate_atl(valid_tss)
        ctl = self.training_load_analyzer.calculate_ctl(valid_tss)

        status_result = self.training_load_analyzer.evaluate_training_status(atl, ctl)

        result = {
            "atl": atl,
            "ctl": ctl,
            "tsb": status_result["tsb"],
            "fitness_status": status_result["fitness_status"],
            "training_advice": status_result["training_advice"],
            "days_analyzed": days,
            "runs_count": len(valid_tss),
            "total_runs": len(tss_values),
        }

        if message:
            result["message"] = message

        return result

    def _evaluate_fitness_status(
        self, tsb: float, _atl: float, _ctl: float
    ) -> tuple[str, str]:
        """
        根据训练压力平衡评估体能状态并生成训练建议

        TSB 解读：
        - TSB > 10: 恢复良好，体能充沛
        - TSB 0-10: 状态正常，保持训练
        - TSB -10-0: 轻度疲劳，注意恢复
        - TSB < -10: 过度训练，需要休息

        Args:
            tsb: 训练压力平衡 (CTL - ATL)
            atl: 急性训练负荷
            ctl: 慢性训练负荷

        Returns:
            tuple: (体能状态, 训练建议)
        """
        if tsb > 10:
            status = "恢复良好"
            advice = (
                "当前体能充沛，适合进行高强度训练或比赛。"
                "建议安排质量课（间歇跑、节奏跑）或长距离跑。"
                "注意把握巅峰期，可考虑参加比赛。"
            )
        elif tsb > 0:
            status = "状态正常"
            advice = (
                "当前状态良好，可以保持正常训练节奏。"
                "建议继续按训练计划执行，注意训练与恢复的平衡。"
                "可适度增加训练强度，但需监控身体反应。"
            )
        elif tsb > -10:
            status = "轻度疲劳"
            advice = (
                "当前有一定训练累积疲劳，属于正常训练状态。"
                "建议适当降低训练强度，增加恢复时间。"
                "保证充足睡眠和营养，可安排轻松跑或交叉训练。"
            )
        else:
            status = "过度训练"
            advice = (
                "警告：当前疲劳累积过多，存在过度训练风险！"
                "建议立即减少训练量，安排 2-3 天完全休息或轻松活动。"
                "密切监控身体状态，如持续疲劳建议咨询专业教练或医生。"
            )

        # 根据 CTL 补充建议
        if _ctl < 30:
            advice += " 体能基础较弱，建议循序渐进增加训练量。"
        elif _ctl > 80:
            advice += " 体能基础扎实，可保持当前训练水平。"

        return status, advice

    def _calculate_hr_zones(self, max_hr: int) -> dict[str, tuple]:
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

            if start_date or end_date:
                from datetime import datetime, timedelta

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
        self, df: pl.DataFrame, max_hr: int, zone_boundaries: dict[str, tuple]
    ) -> dict[str, Any]:
        """
        基于平均心率估算心率区间分布

        Args:
            df: 包含 avg_heart_rate 的 DataFrame
            max_hr: 最大心率
            zone_boundaries: 心率区间边界定义

        Returns:
            Dict[str, Any]: 心率区间分析结果
        """
        hr_col = (
            "session_avg_heart_rate"
            if "session_avg_heart_rate" in df.columns
            else "avg_heart_rate"
        )
        duration_col = (
            "session_total_timer_time"
            if "session_total_timer_time" in df.columns
            else "total_timer_time"
        )

        hr_df = df.filter(pl.col(hr_col).is_not_null() & (pl.col(hr_col) > 0))

        if hr_df.is_empty():
            return {
                "max_hr": max_hr,
                "zones": [],
                "total_time_in_hr": 0,
                "activities_count": df.height,
                "message": "暂无有效心率数据",
            }

        zone_times = dict.fromkeys(zone_boundaries.keys(), 0)
        total_time = 0

        for row in hr_df.iter_rows(named=True):
            avg_hr = row.get(hr_col, 0)
            duration = row.get(duration_col, 0)

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

    def generate_daily_report(self, age: int = 30) -> dict[str, Any]:
        """
        生成每日晨报内容

        包含：
        - 日期和问候语
        - 昨日训练摘要（如有）
        - 当前体能状态（ATL/CTL/TSB）
        - 训练建议
        - 本周训练计划预览

        Args:
            age: 年龄，用于计算最大心率和训练建议

        Returns:
            Dict[str, Any]: 晨报内容字典，包含：
                - date: 日期字符串
                - greeting: 问候语
                - yesterday_run: 昨日训练摘要（None表示无训练）
                - fitness_status: 体能状态数据
                - training_advice: 今日训练建议
                - weekly_plan: 本周训练计划预览
                - generated_at: 生成时间戳
        """
        from datetime import datetime, timedelta

        # 获取当前日期
        now = datetime.now()
        today = now.date()
        yesterday = today - timedelta(days=1)

        # 星期映射
        weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

        # 1. 生成日期和问候语
        date_str = f"{today.year}年{today.month}月{today.day}日 {weekday_names[today.weekday()]}"
        greeting = self._generate_greeting(now.hour, today.weekday())

        # 2. 获取昨日训练摘要
        yesterday_run = self._get_yesterday_run(yesterday)

        # 3. 获取体能状态
        fitness_status = self.get_training_load(days=42)

        # 4. 生成训练建议
        training_advice = self._generate_training_advice(
            fitness_status, yesterday_run, today.weekday(), age
        )

        # 5. 生成本周训练计划预览
        weekly_plan = self._generate_weekly_plan(today, fitness_status, age)

        return {
            "date": date_str,
            "greeting": greeting,
            "yesterday_run": yesterday_run,
            "fitness_status": {
                "atl": fitness_status.get("atl", 0.0),
                "ctl": fitness_status.get("ctl", 0.0),
                "tsb": fitness_status.get("tsb", 0.0),
                "status": fitness_status.get("fitness_status", "数据不足"),
            },
            "training_advice": training_advice,
            "weekly_plan": weekly_plan,
            "generated_at": now.isoformat(),
        }

    def _generate_greeting(self, hour: int, weekday: int) -> str:
        """
        根据时间和星期生成问候语

        Args:
            hour: 当前小时（0-23）
            weekday: 当前星期（0=周一，6=周日）

        Returns:
            str: 问候语
        """
        # 时间段问候
        if 5 <= hour < 9:
            time_greeting = "早上好"
        elif 9 <= hour < 12:
            time_greeting = "上午好"
        elif 12 <= hour < 14:
            time_greeting = "中午好"
        elif 14 <= hour < 18:
            time_greeting = "下午好"
        else:
            time_greeting = "晚上好"

        # 根据星期添加训练提示
        if weekday == 0:  # 周一
            return f"{time_greeting}！新的一周开始了，让我们制定训练计划吧。"
        elif weekday == 6:  # 周日
            return f"{time_greeting}！今天是休息日，好好恢复吧。"
        else:
            return f"{time_greeting}！今天是您的训练日。"

    def _get_yesterday_run(self, yesterday: date) -> dict[str, Any] | None:
        """
        获取昨日训练摘要

        Args:
            yesterday: 昨日日期对象

        Returns:
            Optional[Dict]: 昨日训练数据，无训练返回None
        """
        from datetime import datetime

        try:
            lf = self.storage.read_parquet()

            # 过滤昨日的数据
            start_of_yesterday = datetime.combine(yesterday, datetime.min.time())
            end_of_yesterday = datetime.combine(yesterday, datetime.max.time())

            df = lf.filter(
                pl.col("timestamp").is_between(start_of_yesterday, end_of_yesterday)
            ).collect()

            if df.is_empty():
                return None

            # 计算昨日训练汇总
            total_distance = df["session_total_distance"].sum()
            total_duration = df["session_total_timer_time"].sum()

            # 计算TSS
            tss_values = []
            for row in df.iter_rows(named=True):
                tss = self.calculate_tss_for_run(
                    distance_m=row.get("session_total_distance", 0),
                    duration_s=row.get("session_total_timer_time", 0),
                    avg_heart_rate=row.get("session_avg_heart_rate"),
                )
                tss_values.append(tss)
            total_tss = sum(tss_values)

            return {
                "distance_km": round(total_distance / 1000, 2),
                "duration_min": round(total_duration / 60, 1),
                "tss": round(total_tss, 1),
                "run_count": df.height,
            }
        except Exception:
            return None

    def _generate_training_advice(
        self,
        fitness_status: dict[str, Any],
        yesterday_run: dict[str, Any] | None,
        weekday: int,
        _age: int,
    ) -> str:
        """
        基于训练负荷数据生成训练建议

        Args:
            fitness_status: 体能状态数据
            yesterday_run: 昨日训练数据
            weekday: 当前星期
            age: 年龄

        Returns:
            str: 训练建议文本
        """
        tsb = fitness_status.get("tsb", 0.0)
        status = fitness_status.get("fitness_status", "数据不足")
        ctl = fitness_status.get("ctl", 0.0)

        advice_parts = []

        # 基于TSB状态生成建议
        if status == "数据不足":
            advice_parts.append("暂无足够数据生成个性化建议，请先导入更多训练数据。")
            advice_parts.append("建议开始规律训练，每次训练都记录心率数据。")
        elif tsb > 10:
            advice_parts.append("状态良好，可以进行中等强度训练。")
            if weekday in [1, 3, 5]:  # 周二、周四、周六
                advice_parts.append("建议进行 8-10 公里的节奏跑，保持心率在区间3。")
            elif weekday in [2, 4]:  # 周三、周五
                advice_parts.append("建议进行轻松跑 6-8 公里，保持心率在区间2。")
            else:
                advice_parts.append("可以进行长距离慢跑或交叉训练。")
        elif tsb > 0:
            advice_parts.append("状态正常，可以保持正常训练节奏。")
            advice_parts.append("建议进行 6-8 公里的轻松跑，注意监控身体反应。")
        elif tsb > -10:
            advice_parts.append("有一定训练累积疲劳，建议适当降低强度。")
            advice_parts.append("建议进行轻松跑或交叉训练，保证充足休息。")
        else:
            advice_parts.append("警告：疲劳累积过多，建议安排休息日。")
            advice_parts.append("建议进行 2-3 天轻松活动或完全休息。")

        # 考虑昨日训练情况
        if yesterday_run:
            if yesterday_run["tss"] > 100:
                advice_parts.append(
                    f"昨日训练强度较高（TSS: {yesterday_run['tss']}），注意恢复。"
                )
            elif yesterday_run["tss"] > 50:
                advice_parts.append("昨日进行了中等强度训练，今日可适度活动。")

        # 基于CTL补充建议
        if ctl < 30:
            advice_parts.append("体能基础较弱，建议循序渐进增加训练量。")
        elif ctl > 80:
            advice_parts.append("体能基础扎实，可保持当前训练水平。")

        return " ".join(advice_parts)

    def _generate_weekly_plan(
        self, today: date, fitness_status: dict[str, Any], _age: int
    ) -> list[dict[str, Any]]:
        """
        生成本周训练计划预览

        Args:
            today: 今日日期对象
            fitness_status: 体能状态数据
            age: 年龄

        Returns:
            List[Dict]: 每日训练计划列表
        """
        from datetime import timedelta

        weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        tsb = fitness_status.get("tsb", 0.0)
        ctl = fitness_status.get("ctl", 0.0)

        # 获取本周一的日期
        monday = today - timedelta(days=today.weekday())

        weekly_plan = []

        for i in range(7):
            current_date = monday + timedelta(days=i)
            weekday_name = weekday_names[i]
            is_today = current_date == today
            is_past = current_date < today

            # 根据TSB和星期生成计划
            plan = self._get_daily_plan(i, tsb, ctl, is_past)
            weekly_plan.append(
                {
                    "day": weekday_name,
                    "date": current_date.strftime("%m/%d"),
                    "plan": plan,
                    "is_today": is_today,
                    "is_past": is_past,
                }
            )

        return weekly_plan

    def _get_daily_plan(
        self, weekday: int, tsb: float, _ctl: float, is_past: bool
    ) -> str:
        """
        获取单日训练计划

        Args:
            weekday: 星期几（0=周一，6=周日）
            tsb: 训练压力平衡
            ctl: 慢性训练负荷
            is_past: 是否已过去

        Returns:
            str: 训练计划
        """
        if is_past:
            return "已完成"

        # 基于TSB调整训练计划
        if tsb < -10:
            # 过度训练状态，减少训练量
            plans = {
                0: "休息",
                1: "轻松跑 4km",
                2: "休息",
                3: "轻松跑 5km",
                4: "休息",
                5: "轻松跑 4km",
                6: "休息",
            }
        elif tsb < 0:
            # 轻度疲劳状态
            plans = {
                0: "休息",
                1: "轻松跑 6km",
                2: "节奏跑 8km",
                3: "轻松跑 5km",
                4: "间歇跑 6km",
                5: "轻松跑 6km",
                6: "休息",
            }
        else:
            # 状态良好
            plans = {
                0: "休息",
                1: "轻松跑 6km",
                2: "节奏跑 8km",
                3: "轻松跑 5km",
                4: "间歇跑 8km",
                5: "轻松跑 6km",
                6: "长距离跑 15km",
            }

        return plans.get(weekday, "休息")

    def get_training_load_trend(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        days: int | None = None,
    ) -> dict[str, Any]:
        """
        获取训练负荷趋势数据（每日 TSS、ATL、CTL、TSB）

        计算说明：
        - 按日期聚合每日 TSS 总和
        - 对每个日期，基于历史数据计算 ATL（7天 EWMA）、CTL（42天 EWMA）
        - TSB = CTL - ATL，反映当前体能状态
        - 提供体能状态评估和训练建议

        Args:
            start_date: 开始日期（格式：YYYY-MM-DD），可选
            end_date: 结束日期（格式：YYYY-MM-DD），可选
            days: 最近 N 天，优先级高于 start_date/end_date

        Returns:
            dict: 训练负荷趋势数据，包含：
                - trend_data: 每日训练负荷数据列表
                    - date: 日期
                    - tss: 当日 TSS 总和
                    - atl: 急性训练负荷
                    - ctl: 慢性训练负荷
                    - tsb: 训练压力平衡
                    - status: 体能状态
                - summary: 汇总信息
                    - current_atl: 当前 ATL
                    - current_ctl: 当前 CTL
                    - current_tsb: 当前 TSB
                    - status: 当前体能状态
                    - recommendation: 训练建议

        Raises:
            ValueError: 当日期格式无效时
        """
        from datetime import datetime, timedelta

        # 解析日期范围
        if days is not None:
            end_dt = datetime.now().replace(hour=23, minute=59, second=59)
            start_dt = (end_dt - timedelta(days=days - 1)).replace(
                hour=0, minute=0, second=0
            )
        else:
            if end_date:
                try:
                    end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(
                        hour=23, minute=59, second=59
                    )
                except ValueError as e:
                    raise ValueError(
                        f"结束日期格式无效: {end_date}，应为 YYYY-MM-DD"
                    ) from e
            else:
                end_dt = datetime.now().replace(hour=23, minute=59, second=59)

            if start_date:
                try:
                    start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(
                        hour=0, minute=0, second=0
                    )
                except ValueError as e:
                    raise ValueError(
                        f"开始日期格式无效: {start_date}，应为 YYYY-MM-DD"
                    ) from e
            else:
                # 默认最近 90 天
                start_dt = (end_dt - timedelta(days=89)).replace(
                    hour=0, minute=0, second=0
                )

        # 验证日期范围
        if start_dt > end_dt:
            raise ValueError("开始日期不能晚于结束日期")

        # 读取数据（需要额外读取 CTL 计算所需的 42 天历史数据）
        history_start = start_dt - timedelta(days=42)
        lf = self.storage.read_parquet()

        df = (
            lf.filter(pl.col("timestamp") >= history_start)
            .filter(pl.col("timestamp") <= end_dt)
            .sort("timestamp")
            .collect()
        )

        if df.is_empty():
            return {
                "trend_data": [],
                "summary": {
                    "current_atl": 0.0,
                    "current_ctl": 0.0,
                    "current_tsb": 0.0,
                    "status": "数据不足",
                    "recommendation": "暂无跑步数据，请先导入 FIT 文件",
                },
                "message": "暂无跑步数据",
                "days_analyzed": (end_dt - start_dt).days + 1,
            }

        tss_records = []
        for row in df.iter_rows(named=True):
            tss = self.calculate_tss_for_run(
                distance_m=row.get("session_total_distance", 0),
                duration_s=row.get("session_total_timer_time", 0),
                avg_heart_rate=row.get("session_avg_heart_rate"),
            )
            timestamp = row.get("timestamp")
            if timestamp and tss > 0:
                tss_records.append({"timestamp": timestamp, "tss": tss})

        # 如果没有有效的 TSS 数据
        if not tss_records:
            return {
                "trend_data": [],
                "summary": {
                    "current_atl": 0.0,
                    "current_ctl": 0.0,
                    "current_tsb": 0.0,
                    "status": "数据不足",
                    "recommendation": "训练数据缺少心率信息，建议使用带有心率监测的设备记录训练",
                },
                "message": "暂无有效训练数据（心率数据缺失）",
                "days_analyzed": (end_dt - start_dt).days + 1,
            }

        # 创建 TSS 数据 DataFrame
        tss_df = pl.DataFrame(tss_records)

        # 按日期分组聚合 TSS
        tss_df = tss_df.with_columns(
            pl.col("timestamp").dt.strftime("%Y-%m-%d").alias("date_str")
        )
        daily_tss = (
            tss_df.group_by("date_str")
            .agg(pl.col("tss").sum().alias("daily_tss"))
            .sort("date_str")
        )

        # 创建完整的日期序列（填充没有训练的日期）
        date_range = []
        current_date = start_dt.date()
        end_date_only = end_dt.date()
        while current_date <= end_date_only:
            date_range.append(current_date.strftime("%Y-%m-%d"))
            current_date += timedelta(days=1)

        # 创建日期 DataFrame 并左连接
        date_df = pl.DataFrame({"date_str": date_range})
        complete_daily = date_df.join(daily_tss, on="date_str", how="left").fill_null(
            0.0
        )

        # 计算累积的 ATL、CTL、TSB
        # 需要包含历史数据进行 EWMA 计算
        # 先获取历史 TSS 数据（在 start_date 之前的）
        history_tss = {}
        for record in tss_records:
            ts = record["timestamp"]
            date_key = ts.strftime("%Y-%m-%d")
            if ts < start_dt:
                if date_key not in history_tss:
                    history_tss[date_key] = 0.0
                history_tss[date_key] += record["tss"]

        # 排序历史 TSS（最早的在前）
        sorted_history = sorted(history_tss.items(), key=lambda x: x[0])
        historical_tss_values = [tss for _, tss in sorted_history]

        # 计算每日趋势
        trend_data = []
        cumulative_tss = historical_tss_values.copy()  # 累积的 TSS 列表

        for row in complete_daily.iter_rows(named=True):
            date_str = row["date_str"]
            daily_tss_value = row["daily_tss"]

            # 添加当日 TSS 到累积列表
            cumulative_tss.append(daily_tss_value)

            # 计算截至当日的 ATL、CTL
            atl = self.calculate_atl(cumulative_tss)
            ctl = self.calculate_ctl(cumulative_tss)
            tsb = ctl - atl

            # 评估体能状态
            status, _ = self._evaluate_fitness_status(tsb, atl, ctl)

            trend_data.append(
                {
                    "date": date_str,
                    "tss": round(daily_tss_value, 2),
                    "atl": atl,
                    "ctl": ctl,
                    "tsb": round(tsb, 2),
                    "status": status,
                }
            )

        # 获取最新数据作为汇总
        latest = trend_data[-1] if trend_data else None

        if latest:
            _, recommendation = self._evaluate_fitness_status(
                latest["tsb"], latest["atl"], latest["ctl"]
            )

            summary = {
                "current_atl": latest["atl"],
                "current_ctl": latest["ctl"],
                "current_tsb": latest["tsb"],
                "status": latest["status"],
                "recommendation": recommendation,
            }
        else:
            summary = {
                "current_atl": 0.0,
                "current_ctl": 0.0,
                "current_tsb": 0.0,
                "status": "数据不足",
                "recommendation": "暂无训练数据",
            }

        return {
            "trend_data": trend_data,
            "summary": summary,
            "days_analyzed": len(trend_data),
            "total_runs": len(tss_records),
        }

    def get_pace_distribution(self, year: int | None = None) -> dict[str, Any]:
        """
        获取配速分布统计

        Args:
            year: 年份，不指定则统计所有数据

        Returns:
            Dict[str, Any]: 配速分布数据
        """
        return self.statistics_aggregator.get_pace_distribution(year)
