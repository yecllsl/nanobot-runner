# 用户画像引擎
# 基于历史跑步数据构建用户画像，包括体能水平、训练模式、伤病风险等维度
# 双存储持久化：profile.json (结构化数据) + MEMORY.md (Agent 观察笔记)
#
# 拆分说明 (Task 20):
#   - RunnerProfile 数据类 → profile_schema.py（唯一真实来源）
#   - ProfileStorageManager → profile_storage.py（存储管理）
#   - ProfileEngine + ProfileStaleStatus → 本文件（核心编排）
#   - 所有公共 API 通过 re-exports 保持向后兼容

from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Any, cast

import polars as pl

from src.core.base.logger import get_logger
from src.core.base.profile_schema import RunnerProfile
from src.core.base.profile_storage import ProfileStorageManager
from src.core.calculators.injury_risk_analyzer import InjuryRiskAnalyzer
from src.core.calculators.training_history_analyzer import TrainingHistoryAnalyzer
from src.core.models import FitnessLevel, TrainingPattern
from src.core.models.anomaly_schema import ANOMALY_FILTER_RULES, AnomalyFilterRule
from src.core.models.training_plan import InjuryRiskLevel
from src.core.report.anomaly_filter import AnomalyDataFilter
from src.core.user_profile_manager import UserProfileManager

if TYPE_CHECKING:
    from src.core.base.context import AppContext

# Re-exports: 保持向后兼容，所有从 src.core.base.profile 导入的公共 API 不变
__all__ = [
    "ProfileEngine",
    "ProfileStaleStatus",
    "ProfileStorageManager",
    "RunnerProfile",
    "AnomalyFilterRule",
    "ANOMALY_FILTER_RULES",
    "InjuryRiskLevel",
]

logger = get_logger(__name__)


class ProfileStaleStatus(Enum):
    """画像保鲜期状态"""

    FRESH = "新鲜"  # <= 7 天
    STALE = "过期"  # > 7 天
    MISSING = "缺失"  # 无画像数据


class ProfileEngine:
    """用户画像引擎"""

    def __init__(self, context: AppContext) -> None:
        """
        初始化画像引擎

        Args:
            context: AppContext 实例
        """
        self.context = context
        self.storage = context.storage
        self.storage_manager = ProfileStorageManager()
        self.user_profile_manager = UserProfileManager(context.storage)
        self.injury_risk_analyzer = InjuryRiskAnalyzer()
        self.training_history_analyzer = TrainingHistoryAnalyzer(context.storage)
        self.anomaly_data_filter = AnomalyDataFilter()

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
        self.calculate_injury_risk(profile, age, resting_hr)
        # 结果已经通过 calculate_injury_risk 更新到 profile

    def calculate_injury_risk(
        self,
        profile: RunnerProfile,
        age: int = 30,
        resting_hr: int = 60,
    ) -> dict[str, Any]:
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
        result = self.injury_risk_analyzer.calculate_injury_risk(
            profile, age, resting_hr
        )

        return {
            "risk_score": result.risk_score,
            "risk_level": result.risk_level.value,
            "risk_factors": result.risk_factors,
            "recommendations": result.recommendations,
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

            if len(lf.collect_schema()) == 0:
                return lf

            lf = self._normalize_column_names(lf)

            if "timestamp" in lf.collect_schema().names():
                lf = lf.filter(pl.col("timestamp") >= start_date).filter(
                    pl.col("timestamp") <= end_date
                )

            return lf
        except Exception as e:
            raise RuntimeError(f"读取活动数据失败：{e}") from e

    def _normalize_column_names(self, lf: pl.LazyFrame) -> pl.LazyFrame:
        """
        规范化列名，将 session_ 前缀的列名映射为标准列名

        Args:
            lf: LazyFrame 对象

        Returns:
            pl.LazyFrame: 列名规范化后的 LazyFrame
        """
        schema = lf.collect_schema()
        columns = schema.names()

        column_mapping = {
            "session_total_distance": "total_distance",
            "session_total_timer_time": "total_timer_time",
            "session_avg_heart_rate": "avg_heart_rate",
            "session_max_heart_rate": "max_heart_rate",
            "session_avg_speed": "avg_speed",
            "session_max_speed": "max_speed",
            "session_avg_cadence": "avg_cadence",
            "session_max_cadence": "max_cadence",
            "session_avg_power": "avg_power",
            "session_max_power": "max_power",
            "session_total_calories": "total_calories",
            "session_total_ascent": "total_ascent",
            "session_total_descent": "total_descent",
            "session_start_time": "start_time",
        }

        rename_map = {}
        for old_name, new_name in column_mapping.items():
            if old_name in columns and new_name not in columns:
                rename_map[old_name] = new_name

        if rename_map:
            lf = lf.rename(rename_map)
            logger.debug(f"列名映射: {rename_map}")

        return lf

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

            if "start_time" in df.columns:
                activities = df.group_by("start_time").agg(
                    [
                        pl.col("total_distance").first(),
                        pl.col("total_timer_time").first(),
                    ]
                )
                profile.total_activities = activities.height
                profile.total_distance_km = (
                    float(activities["total_distance"].sum()) / 1000.0
                )
                profile.total_duration_hours = (
                    float(activities["total_timer_time"].sum()) / 3600.0
                )
            else:
                profile.total_activities = df.height
                profile.total_distance_km = float(df["total_distance"].sum()) / 1000.0
                profile.total_duration_hours = (
                    float(df["total_timer_time"].sum()) / 3600.0
                )

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
            analytics = self.context.analytics

            df = lf.collect()

            if df.is_empty():
                return

            if "start_time" in df.columns:
                activities = df.group_by("start_time").agg(
                    [
                        pl.col("total_distance").first(),
                        pl.col("total_timer_time").first(),
                    ]
                )
                activity_rows = activities.iter_rows(named=True)
            else:
                activity_rows = df.iter_rows(named=True)

            vdot_values: list[float] = []
            for row in activity_rows:
                distance_raw = row.get("total_distance")
                duration_raw = row.get("total_timer_time")
                distance = float(distance_raw) if distance_raw is not None else 0.0
                duration = float(duration_raw) if duration_raw is not None else 0.0

                if distance >= 1500 and duration > 0:
                    try:
                        vdot = analytics.calculate_vdot(distance, duration)
                        vdot_values.append(vdot)
                    except ValueError:
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
                profile.avg_heart_rate = (
                    float(cast(float, avg_hr)) if avg_hr is not None else None
                )
                profile.max_heart_rate = (
                    float(cast(float, max_hr)) if max_hr is not None else None
                )
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
            analytics = self.context.analytics

            df = lf.collect()

            if df.is_empty():
                return

            # 计算每次跑步的 TSS
            tss_values: list[float] = []
            for row in df.iter_rows(named=True):
                tss = analytics.calculate_tss_for_run(
                    distance_m=row.get("total_distance") or 0,
                    duration_s=row.get("total_timer_time") or 0,
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

            if "start_time" in df.columns:
                activities = df.group_by("start_time").agg(
                    [pl.col("start_time").first().alias("activity_start_time")]
                )
                profile.favorite_running_time = self._analyze_running_time_preference(
                    activities["activity_start_time"]
                )
            elif "timestamp" in df.columns:
                activities = df.group_by("timestamp").agg(
                    [pl.col("timestamp").first().alias("activity_start_time")]
                )
                profile.favorite_running_time = self._analyze_running_time_preference(
                    activities["activity_start_time"]
                )

            profile.consistency_score = self._calculate_consistency_score(df, days)
        except Exception as e:
            logger.warning(f"计算其他指标失败：{e}")

    def _analyze_running_time_preference(self, timestamps: pl.Series) -> str:
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
                intervals: list[float] = []
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
                    std_dev = (
                        float(cast(float, std_dev_value))
                        if std_dev_value is not None
                        else 0.0
                    )

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

    def check_freshness(
        self,
        profile: RunnerProfile | None = None,
        freshness_days: int = 7,
    ) -> ProfileStaleStatus:
        """
        检查画像保鲜期

        基于画像最后更新时间判断是否过期

        Args:
            profile: 画像对象，如果为 None 则尝试从 storage 加载
            freshness_days: 保鲜期天数，默认 7 天

        Returns:
            ProfileStaleStatus: 画像保鲜期状态

        Raises:
            RuntimeError: 当加载画像失败时
        """
        try:
            # 如果未提供 profile，尝试从 storage 加载
            if profile is None:
                profile = self.storage_manager.load_profile_json()

            # 检查是否存在画像
            if profile is None:
                logger.debug("画像不存在，状态为 MISSING")
                return ProfileStaleStatus.MISSING

            # 计算时间差
            now = datetime.now()
            time_diff = now - profile.profile_date

            # 判断是否过期
            if time_diff.total_seconds() <= freshness_days * 24 * 3600:
                logger.debug(f"画像新鲜（{time_diff.days} 天前更新）")
                return ProfileStaleStatus.FRESH
            else:
                logger.debug(
                    f"画像过期（{time_diff.days} 天前更新，阈值{freshness_days}天）"
                )
                return ProfileStaleStatus.STALE

        except Exception as e:
            logger.error(f"检查画像保鲜期失败：{e}")
            raise RuntimeError(f"检查画像保鲜期失败：{e}") from e

    def filter_anomaly_data(
        self,
        data: pl.LazyFrame,
        rules: list[AnomalyFilterRule] | None = None,
        strict_mode: bool = False,
    ) -> pl.LazyFrame:
        """
        过滤异常数据

        根据预定义的异常过滤规则过滤数据集中的异常记录

        Args:
            data: 输入的 LazyFrame 数据
            rules: 过滤规则列表，如果为 None 则使用 ANOMALY_FILTER_RULES
            strict_mode: 严格模式，如果为 True 则过滤掉任何触发规则的数据，
                        如果为 False 则仅过滤严重异常数据

        Returns:
            pl.LazyFrame: 过滤后的 LazyFrame

        Raises:
            ValueError: 当输入数据为空或规则无效时
            RuntimeError: 当过滤失败时

        Notes:
            - 支持两种过滤动作：filter（直接过滤）和 clip（截断到阈值）
            - 严格模式下，所有规则都会生效
            - 非严格模式下，仅严重异常数据会被过滤（如心率<30 或>220）
        """
        try:
            # 检查输入数据
            if len(data.collect_schema()) == 0:
                raise ValueError("输入数据为空")

            # 使用默认规则
            if rules is None:
                rules = ANOMALY_FILTER_RULES

            if not rules:
                logger.debug("未提供过滤规则，返回原始数据")
                return data

            # 逐条应用过滤规则
            filtered_data = data
            for rule in rules:
                filtered_data = self._apply_anomaly_rule(
                    filtered_data, rule, strict_mode
                )

            logger.info(
                f"异常数据过滤完成，原始行数：{data.collect().height}, "
                f"过滤后行数：{filtered_data.collect().height}"
            )
            return filtered_data

        except Exception as e:
            logger.error(f"异常数据过滤失败：{e}")
            raise RuntimeError(f"异常数据过滤失败：{e}") from e

    def _apply_anomaly_rule(
        self,
        filtered_data: pl.LazyFrame,
        rule: AnomalyFilterRule,
        strict_mode: bool,
    ) -> pl.LazyFrame:
        """应用单条异常过滤规则"""
        try:
            # 检查字段是否存在
            if rule.field_name not in filtered_data.collect_schema().names():
                logger.debug(
                    f"字段 {rule.field_name} 不存在，跳过规则：{rule.description}"
                )
                return filtered_data

            # 构建过滤条件
            condition = self._build_filter_condition(rule, strict_mode)
            if condition is None:
                return filtered_data

            # 应用过滤或截断
            if rule.action == "filter":
                return self._apply_filter_action(filtered_data, rule)
            elif rule.action == "clip":
                return self._apply_clip_action(filtered_data, rule)

            return filtered_data

        except Exception as e:
            logger.warning(f"应用规则失败（{rule.field_name}）: {e}")
            if strict_mode:
                raise
            return filtered_data

    def _apply_filter_action(
        self, filtered_data: pl.LazyFrame, rule: AnomalyFilterRule
    ) -> pl.LazyFrame:
        """应用filter动作：过滤掉不满足条件的数据"""
        col = pl.col(rule.field_name)
        threshold = rule.threshold

        # 根据条件构建反向过滤（保留满足条件的数据，过滤掉不满足的）
        if rule.condition == "<":
            filtered_data = filtered_data.filter(col >= threshold)
        elif rule.condition == ">":
            filtered_data = filtered_data.filter(col <= threshold)
        elif rule.condition == "<=":
            filtered_data = filtered_data.filter(col > threshold)
        elif rule.condition == ">=":
            filtered_data = filtered_data.filter(col < threshold)
        elif rule.condition == "==":
            filtered_data = filtered_data.filter(col != threshold)

        logger.debug(f"应用过滤规则：{rule.description}")
        return filtered_data

    def _apply_clip_action(
        self, filtered_data: pl.LazyFrame, rule: AnomalyFilterRule
    ) -> pl.LazyFrame:
        """应用clip动作：截断到阈值"""
        if rule.condition == ">" and rule.clip_value is not None:
            filtered_data = filtered_data.with_columns(
                pl.when(pl.col(rule.field_name) > rule.threshold)
                .then(rule.clip_value)
                .otherwise(pl.col(rule.field_name))
                .alias(rule.field_name)
            )
            logger.debug(f"应用截断规则：{rule.description}")

        return filtered_data

    def _build_filter_condition(
        self,
        rule: AnomalyFilterRule,
        strict_mode: bool,
    ) -> pl.Expr | None:
        """
        构建过滤条件表达式

        Args:
            rule: 过滤规则
            strict_mode: 严格模式

        Returns:
            Optional[pl.Expr]: 过滤条件表达式，如果为 None 表示不应用此规则
        """
        # 非严格模式下，仅应用严重异常规则
        if not strict_mode:
            # 严重异常阈值
            severe_thresholds: dict[str, list[tuple[int | float, str]]] = {
                "avg_heart_rate": [(30, "<"), (220, ">")],
                "max_heart_rate": [(50, "<"), (250, ">")],
                "total_distance": [(100, "<"), (100000, ">")],
                "total_timer_time": [(60, "<"), (28800, ">")],
            }

            if rule.field_name in severe_thresholds:
                thresholds = severe_thresholds[rule.field_name]
                if (rule.threshold, rule.condition) not in thresholds:
                    logger.debug(f"非严格模式，跳过非严重异常规则：{rule.field_name}")
                    return None

        # 构建条件表达式
        return pl.col(rule.field_name)
