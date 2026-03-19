# 用户画像引擎
# 基于历史跑步数据构建用户画像，包括体能水平、训练模式、伤病风险等维度

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

import polars as pl

from src.core.logger import get_logger

logger = get_logger(__name__)


class FitnessLevel(Enum):
    """体能水平等级"""

    BEGINNER = "初学者"  # VDOT < 30
    INTERMEDIATE = "中级"  # VDOT 30-45
    ADVANCED = "进阶"  # VDOT 45-60
    ELITE = "精英"  # VDOT >= 60


class TrainingPattern(Enum):
    """训练模式类型"""

    REST = "休息型"  # 周跑量 < 10km
    LIGHT = "轻松型"  # 周跑量 10-30km
    MODERATE = "适度型"  # 周跑量 30-50km
    INTENSE = "高强度型"  # 周跑量 50-80km
    EXTREME = "极限型"  # 周跑量 >= 80km


class InjuryRiskLevel(Enum):
    """伤病风险等级"""

    LOW = "低"  # 风险评分 < 30
    MEDIUM = "中"  # 风险评分 30-60
    HIGH = "高"  # 风险评分 > 60


@dataclass
class RunnerProfile:
    """跑者画像数据结构"""

    # 基本信息
    user_id: str
    profile_date: datetime
    total_activities: int = 0
    total_distance_km: float = 0.0
    total_duration_hours: float = 0.0

    # 体能指标
    avg_vdot: float = 0.0
    max_vdot: float = 0.0
    fitness_level: FitnessLevel = FitnessLevel.BEGINNER

    # 训练模式指标
    weekly_avg_distance_km: float = 0.0
    weekly_avg_duration_hours: float = 0.0
    training_pattern: TrainingPattern = TrainingPattern.REST

    # 心率指标
    avg_heart_rate: Optional[float] = None
    max_heart_rate: Optional[float] = None
    resting_heart_rate: Optional[float] = None

    # 伤病风险
    injury_risk_level: InjuryRiskLevel = InjuryRiskLevel.LOW
    injury_risk_score: float = 0.0

    # 训练负荷
    atl: float = 0.0  # 急性训练负荷
    ctl: float = 0.0  # 慢性训练负荷
    tsb: float = 0.0  # 训练压力平衡

    # 其他指标
    avg_pace_min_per_km: float = 0.0
    favorite_running_time: str = "morning"  # morning, afternoon, evening
    consistency_score: float = 0.0  # 训练一致性评分 (0-100)

    # 元数据
    data_quality_score: float = 0.0  # 数据质量评分 (0-100)
    analysis_period_days: int = 0
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "user_id": self.user_id,
            "profile_date": self.profile_date.isoformat(),
            "total_activities": self.total_activities,
            "total_distance_km": round(self.total_distance_km, 2),
            "total_duration_hours": round(self.total_duration_hours, 2),
            "avg_vdot": round(self.avg_vdot, 2),
            "max_vdot": round(self.max_vdot, 2),
            "fitness_level": self.fitness_level.value,
            "weekly_avg_distance_km": round(self.weekly_avg_distance_km, 2),
            "weekly_avg_duration_hours": round(self.weekly_avg_duration_hours, 2),
            "training_pattern": self.training_pattern.value,
            "avg_heart_rate": self.avg_heart_rate,
            "max_heart_rate": self.max_heart_rate,
            "resting_heart_rate": self.resting_heart_rate,
            "injury_risk_level": self.injury_risk_level.value,
            "injury_risk_score": round(self.injury_risk_score, 2),
            "atl": round(self.atl, 2),
            "ctl": round(self.ctl, 2),
            "tsb": round(self.tsb, 2),
            "avg_pace_min_per_km": round(self.avg_pace_min_per_km, 2),
            "favorite_running_time": self.favorite_running_time,
            "consistency_score": round(self.consistency_score, 2),
            "data_quality_score": round(self.data_quality_score, 2),
            "analysis_period_days": self.analysis_period_days,
            "notes": self.notes,
        }


class ProfileEngine:
    """用户画像引擎"""

    def __init__(self, storage_manager) -> None:
        """
        初始化画像引擎

        Args:
            storage_manager: StorageManager 实例
        """
        self.storage = storage_manager

    def build_profile(
        self,
        user_id: str = "default_user",
        days: int = 90,
        age: int = 30,
        resting_hr: int = 60,
    ) -> RunnerProfile:
        """
        基于历史数据构建用户画像

        Args:
            user_id: 用户 ID
            days: 分析天数，默认 90 天
            age: 年龄，用于计算最大心率
            resting_hr: 静息心率

        Returns:
            RunnerProfile: 用户画像对象

        Raises:
            ValueError: 当参数无效时
            RuntimeError: 当数据读取失败时
        """
        # 参数验证
        if days <= 0:
            raise ValueError("分析天数必须为正数")
        if age <= 0 or age > 120:
            raise ValueError("年龄必须在 1-120 之间")
        if resting_hr <= 0 or resting_hr > 200:
            raise ValueError("静息心率必须在合理范围内")

        # 读取数据
        lf = self._load_activity_data(days)

        # 检查是否有数据
        if self._is_empty_lazyframe(lf):
            return self._create_empty_profile(user_id, days)

        # 收集数据
        profile = RunnerProfile(user_id=user_id, profile_date=datetime.now())
        profile.analysis_period_days = days

        # 计算基础统计
        self._calculate_basic_stats(lf, profile)

        # 计算 VDOT 指标
        self._calculate_vdot_metrics(lf, profile)

        # 计算训练模式
        self._calculate_training_pattern(lf, profile, days)

        # 计算心率指标
        self._calculate_hr_metrics(lf, profile)

        # 计算训练负荷
        self._calculate_training_load(lf, profile)

        # 计算伤病风险（使用内部方法）
        self._calculate_injury_risk_internal(profile, age, resting_hr)

        # 计算其他指标
        self._calculate_additional_metrics(lf, profile, days)

        # 计算数据质量评分
        self._calculate_data_quality(lf, profile)

        return profile

    def get_fitness_level(self, avg_vdot: float) -> FitnessLevel:
        """
        根据平均 VDOT 值判断体能水平

        Args:
            avg_vdot: 平均 VDOT 值

        Returns:
            FitnessLevel: 体能水平等级

        Notes:
            - VDOT < 30: 初学者
            - VDOT 30-45: 中级
            - VDOT 45-60: 进阶
            - VDOT >= 60: 精英
        """
        if avg_vdot < 30:
            return FitnessLevel.BEGINNER
        elif avg_vdot < 45:
            return FitnessLevel.INTERMEDIATE
        elif avg_vdot < 60:
            return FitnessLevel.ADVANCED
        else:
            return FitnessLevel.ELITE

    def get_training_pattern(self, weekly_avg_distance_km: float) -> TrainingPattern:
        """
        根据周平均跑量判断训练模式

        Args:
            weekly_avg_distance_km: 周平均跑量（公里）

        Returns:
            TrainingPattern: 训练模式类型

        Notes:
            - < 10km: 休息型
            - 10-30km: 轻松型
            - 30-50km: 适度型
            - 50-80km: 高强度型
            - >= 80km: 极限型
        """
        if weekly_avg_distance_km < 10:
            return TrainingPattern.REST
        elif weekly_avg_distance_km < 30:
            return TrainingPattern.LIGHT
        elif weekly_avg_distance_km < 50:
            return TrainingPattern.MODERATE
        elif weekly_avg_distance_km < 80:
            return TrainingPattern.INTENSE
        else:
            return TrainingPattern.EXTREME

    def _calculate_injury_risk_internal(
        self,
        profile: RunnerProfile,
        age: int,
        resting_hr: int,
    ) -> None:
        """
        内部方法：计算伤病风险并更新画像

        Args:
            profile: 跑者画像对象
            age: 年龄
            resting_hr: 静息心率
        """
        result = self.calculate_injury_risk(profile, age, resting_hr)
        # 结果已经通过 calculate_injury_risk 更新到 profile

    def calculate_injury_risk(
        self,
        profile: RunnerProfile,
        age: int = 30,
        resting_hr: int = 60,
    ) -> Dict[str, Any]:
        """
        计算伤病风险评分

        风险评估维度：
        1. 训练负荷突变（ATL/CTL 比率）
        2. 训练一致性
        3. 心率漂移
        4. 恢复情况（TSB）
        5. 年龄因素

        Args:
            profile: 跑者画像对象
            age: 年龄
            resting_hr: 静息心率

        Returns:
            dict: 伤病风险评估结果，包含：
                - risk_score: 风险评分 (0-100)
                - risk_level: 风险等级 (低/中/高)
                - risk_factors: 风险因素列表
                - recommendations: 建议列表

        Raises:
            ValueError: 当参数无效时
        """
        # 参数验证
        if age <= 0 or age > 120:
            raise ValueError("年龄必须在 1-120 之间")
        if resting_hr <= 0 or resting_hr > 200:
            raise ValueError("静息心率必须在合理范围内")

        risk_score = 0.0
        risk_factors = []
        recommendations = []

        # 1. 训练负荷突变（ATL/CTL 比率，占比 30%）
        if profile.ctl > 0:
            atl_ctl_ratio = profile.atl / profile.ctl
            if atl_ctl_ratio > 1.5:
                risk_score += 30
                risk_factors.append("训练负荷突增（ATL/CTL > 1.5）")
                recommendations.append("立即降低训练强度，避免过度训练")
            elif atl_ctl_ratio > 1.2:
                risk_score += 15
                risk_factors.append("训练负荷较高（ATL/CTL > 1.2）")
                recommendations.append("注意监控身体反应，适度调整训练")
            elif atl_ctl_ratio < 0.8:
                risk_score += 10
                risk_factors.append("训练量过低，体能可能下降")
                recommendations.append("逐步增加训练量，保持体能")

        # 2. 训练一致性（占比 25%）
        if profile.consistency_score < 30:
            risk_score += 25
            risk_factors.append("训练非常不规律")
            recommendations.append("建立规律的训练习惯，避免三天打鱼两天晒网")
        elif profile.consistency_score < 60:
            risk_score += 12
            risk_factors.append("训练不够规律")
            recommendations.append("制定固定训练计划，提高训练一致性")

        # 3. 恢复情况（TSB，占比 25%）
        if profile.tsb < -20:
            risk_score += 25
            risk_factors.append("疲劳累积严重（TSB < -20）")
            recommendations.append("立即安排休息，至少 2-3 天完全恢复")
        elif profile.tsb < -10:
            risk_score += 12
            risk_factors.append("有一定疲劳累积（TSB < -10）")
            recommendations.append("降低训练强度，增加恢复时间")

        # 4. 年龄因素（占比 10%）
        if age > 50:
            risk_score += 10
            risk_factors.append("年龄较大，恢复能力下降")
            recommendations.append("增加热身和拉伸时间，注重恢复")
        elif age > 40:
            risk_score += 5
            risk_factors.append("中年跑者，需注意恢复")
            recommendations.append("保证充足睡眠，适度训练")

        # 5. 训练强度（占比 10%）
        if profile.training_pattern in [
            TrainingPattern.INTENSE,
            TrainingPattern.EXTREME,
        ]:
            risk_score += 10
            risk_factors.append("训练强度过高")
            recommendations.append("安排轻松周，降低训练量")

        # 确定风险等级
        if risk_score < 30:
            risk_level = InjuryRiskLevel.LOW
            if not recommendations:
                recommendations.append("保持当前训练节奏，注意监控身体状态")
        elif risk_score < 60:
            risk_level = InjuryRiskLevel.MEDIUM
        else:
            risk_level = InjuryRiskLevel.HIGH

        # 更新画像
        profile.injury_risk_score = round(risk_score, 2)
        profile.injury_risk_level = risk_level

        return {
            "risk_score": round(risk_score, 2),
            "risk_level": risk_level.value,
            "risk_factors": risk_factors,
            "recommendations": recommendations,
        }

    def _load_activity_data(self, days: int) -> pl.LazyFrame:
        """
        加载指定天数的活动数据

        Args:
            days: 分析天数

        Returns:
            pl.LazyFrame: 活动数据 LazyFrame
        """
        from datetime import datetime, timedelta

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        try:
            lf = self.storage.read_parquet()

            # 检查 LazyFrame 是否有列（空 LazyFrame 没有列）
            if len(lf.collect_schema()) == 0:
                return lf

            # 过滤日期范围
            lf = lf.filter(pl.col("timestamp") >= start_date).filter(
                pl.col("timestamp") <= end_date
            )

            return lf
        except Exception as e:
            raise RuntimeError(f"读取活动数据失败：{e}") from e

    def _is_empty_lazyframe(self, lf: pl.LazyFrame) -> bool:
        """
        检查 LazyFrame 是否为空

        Args:
            lf: LazyFrame 对象

        Returns:
            bool: 是否为空
        """
        try:
            # 检查是否有列
            if len(lf.collect_schema()) == 0:
                return True

            # 检查是否有数据
            df = lf.collect()
            return df.is_empty()
        except Exception:
            return True

    def _create_empty_profile(self, user_id: str, days: int) -> RunnerProfile:
        """
        创建空画像（无数据时）

        Args:
            user_id: 用户 ID
            days: 分析天数

        Returns:
            RunnerProfile: 空画像对象
        """
        profile = RunnerProfile(user_id=user_id, profile_date=datetime.now())
        profile.analysis_period_days = days
        profile.data_quality_score = 0.0
        profile.notes.append("暂无跑步数据，请先导入 FIT 文件")
        return profile

    def _calculate_basic_stats(self, lf: pl.LazyFrame, profile: RunnerProfile) -> None:
        """
        计算基础统计数据

        Args:
            lf: LazyFrame 对象
            profile: 画像对象
        """
        try:
            df = lf.collect()

            if df.is_empty():
                return

            profile.total_activities = df.height
            profile.total_distance_km = float(df["total_distance"].sum()) / 1000.0
            profile.total_duration_hours = float(df["total_timer_time"].sum()) / 3600.0

            # 计算平均配速
            if profile.total_distance_km > 0 and profile.total_duration_hours > 0:
                profile.avg_pace_min_per_km = (
                    profile.total_duration_hours * 60
                ) / profile.total_distance_km
        except Exception as e:
            logger.warning(f"计算基础统计失败：{e}")

    def _calculate_vdot_metrics(self, lf: pl.LazyFrame, profile: RunnerProfile) -> None:
        """
        计算 VDOT 指标

        Args:
            lf: LazyFrame 对象
            profile: 画像对象
        """
        try:
            from src.core.analytics import AnalyticsEngine

            # 创建临时 AnalyticsEngine 实例
            analytics = AnalyticsEngine(self.storage)

            df = lf.collect()

            if df.is_empty():
                return

            vdot_values = []
            for row in df.iter_rows(named=True):
                distance = row.get("total_distance", 0)
                duration = row.get("total_timer_time", 0)

                if distance > 0 and duration > 0:
                    try:
                        vdot = analytics.calculate_vdot(distance, duration)
                        vdot_values.append(vdot)
                    except ValueError:
                        # VDOT 计算失败，跳过
                        pass

            if vdot_values:
                profile.avg_vdot = sum(vdot_values) / len(vdot_values)
                profile.max_vdot = max(vdot_values)
                profile.fitness_level = self.get_fitness_level(profile.avg_vdot)
        except Exception as e:
            logger.warning(f"计算 VDOT 指标失败：{e}")

    def _calculate_training_pattern(
        self, lf: pl.LazyFrame, profile: RunnerProfile, days: int
    ) -> None:
        """
        计算训练模式

        Args:
            lf: LazyFrame 对象
            profile: 画像对象
            days: 分析天数
        """
        try:
            df = lf.collect()

            if df.is_empty():
                return

            # 计算周数
            weeks = max(days / 7, 1)

            # 计算周平均跑量
            profile.weekly_avg_distance_km = profile.total_distance_km / weeks
            profile.weekly_avg_duration_hours = profile.total_duration_hours / weeks

            # 判断训练模式
            profile.training_pattern = self.get_training_pattern(
                profile.weekly_avg_distance_km
            )
        except Exception as e:
            logger.warning(f"计算训练模式失败：{e}")

    def _calculate_hr_metrics(self, lf: pl.LazyFrame, profile: RunnerProfile) -> None:
        """
        计算心率指标

        Args:
            lf: LazyFrame 对象
            profile: 画像对象
        """
        try:
            df = lf.collect()

            if df.is_empty():
                return

            # 检查是否有心率字段
            if "avg_heart_rate" not in df.columns:
                return

            # 过滤有效心率数据
            hr_df = df.filter(
                (pl.col("avg_heart_rate").is_not_null())
                & (pl.col("avg_heart_rate") > 0)
            )

            if not hr_df.is_empty():
                avg_hr = hr_df["avg_heart_rate"].mean()
                max_hr = hr_df["max_heart_rate"].max()
                profile.avg_heart_rate = float(avg_hr) if avg_hr is not None else None  # type: ignore[arg-type]
                profile.max_heart_rate = float(max_hr) if max_hr is not None else None  # type: ignore[arg-type]
        except Exception as e:
            logger.warning(f"计算心率指标失败：{e}")

    def _calculate_training_load(
        self, lf: pl.LazyFrame, profile: RunnerProfile
    ) -> None:
        """
        计算训练负荷（ATL/CTL/TSB）

        Args:
            lf: LazyFrame 对象
            profile: 画像对象
        """
        try:
            from src.core.analytics import AnalyticsEngine

            # 创建临时 AnalyticsEngine 实例
            analytics = AnalyticsEngine(self.storage)

            df = lf.collect()

            if df.is_empty():
                return

            # 计算每次跑步的 TSS
            tss_values = []
            for row in df.iter_rows(named=True):
                tss = analytics.calculate_tss_for_run(
                    distance_m=row.get("total_distance", 0),
                    duration_s=row.get("total_timer_time", 0),
                    avg_heart_rate=row.get("avg_heart_rate"),
                )
                if tss > 0:
                    tss_values.append(tss)

            if tss_values:
                # 计算 ATL 和 CTL
                load_data = analytics.calculate_atl_ctl(tss_values)
                profile.atl = load_data.get("atl", 0.0)
                profile.ctl = load_data.get("ctl", 0.0)
                profile.tsb = profile.ctl - profile.atl
        except Exception as e:
            logger.warning(f"计算训练负荷失败：{e}")

    def _calculate_additional_metrics(
        self, lf: pl.LazyFrame, profile: RunnerProfile, days: int
    ) -> None:
        """
        计算其他指标（训练时间偏好、一致性等）

        Args:
            lf: LazyFrame 对象
            profile: 画像对象
            days: 分析天数
        """
        try:
            df = lf.collect()

            if df.is_empty():
                return

            # 分析训练时间偏好
            if "timestamp" in df.columns:
                profile.favorite_running_time = self._analyze_running_time_preference(
                    df["timestamp"]
                )

            # 计算训练一致性
            profile.consistency_score = self._calculate_consistency_score(df, days)
        except Exception as e:
            logger.warning(f"计算其他指标失败：{e}")

    def _analyze_running_time_preference(self, timestamps: pl.Series) -> str:
        """
        分析跑步时间偏好

        Args:
            timestamps: 时间戳序列

        Returns:
            str: 偏好时间段（morning/afternoon/evening）
        """
        try:
            # 提取小时
            hours = timestamps.dt.hour()

            # 统计各时段跑步次数
            morning_count = ((hours >= 5) & (hours < 12)).sum()
            afternoon_count = ((hours >= 12) & (hours < 18)).sum()
            evening_count = ((hours >= 18) | (hours < 5)).sum()

            # 判断偏好
            if morning_count >= afternoon_count and morning_count >= evening_count:
                return "morning"
            elif afternoon_count >= evening_count:
                return "afternoon"
            else:
                return "evening"
        except Exception:
            return "morning"

    def _calculate_consistency_score(self, df: pl.DataFrame, days: int) -> float:
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

            # 计算每周跑步天数
            weeks = max(days / 7, 1)
            total_runs = df.height
            runs_per_week = total_runs / weeks

            # 基础分：基于每周跑步次数（满分 60 分）
            base_score = min(runs_per_week / 5 * 60, 60)

            # 规律性评分（满分 40 分）
            if total_runs >= 2:
                # 计算训练间隔的标准差
                timestamps = df["timestamp"].sort()
                intervals = []
                for i in range(1, len(timestamps)):
                    # Polars 的 timedelta 直接转换为秒
                    delta = timestamps[i] - timestamps[i - 1]
                    # 转换为天数（delta 是 timedelta 对象）
                    if hasattr(delta, "total_seconds"):
                        interval_days = delta.total_seconds() / 86400
                    else:
                        # Polars 表达式的情况
                        interval_days = delta.dt.total_seconds() / 86400
                    intervals.append(interval_days)

                if intervals:
                    intervals_series = pl.Series(intervals)
                    std_dev_value = intervals_series.std()
                    std_dev = float(std_dev_value) if std_dev_value is not None else 0.0  # type: ignore[arg-type]

                    # 标准差越小，规律性越好（满分 40 分）
                    # 标准差 0 天 = 40 分，标准差 3 天 = 0 分
                    regularity_score = max(40 - (std_dev / 3 * 40), 0)
                else:
                    regularity_score = 0
            else:
                regularity_score = 0

            consistency_score = base_score + regularity_score
            return min(max(consistency_score, 0), 100)
        except Exception:
            return 0.0

    def _calculate_data_quality(self, lf: pl.LazyFrame, profile: RunnerProfile) -> None:
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

            # 1. 数据量充足度（满分 40 分）
            # 90 天内至少 10 次跑步为满分
            runs_per_90_days = df.height / max(profile.analysis_period_days / 90, 1)
            quantity_score = min(runs_per_90_days / 10 * 40, 40)
            score += quantity_score

            # 2. 心率数据覆盖率（满分 40 分）
            if "avg_heart_rate" in df.columns:
                hr_df = df.filter(
                    (pl.col("avg_heart_rate").is_not_null())
                    & (pl.col("avg_heart_rate") > 0)
                )
                hr_ratio = hr_df.height / df.height
                hr_score = hr_ratio * 40
                score += hr_score

            # 3. 距离数据完整性（满分 20 分）
            distance_df = df.filter(
                (pl.col("total_distance").is_not_null())
                & (pl.col("total_distance") > 0)
            )
            distance_ratio = distance_df.height / df.height
            distance_score = distance_ratio * 20
            score += distance_score

            profile.data_quality_score = min(max(score, 0), 100)
        except Exception as e:
            logger.warning(f"计算数据质量评分失败：{e}")
            profile.data_quality_score = 0.0
