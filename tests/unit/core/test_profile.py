# 用户画像引擎单元测试
# 测试 ProfileEngine 的所有核心功能

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import polars as pl
import pytest

from src.core.profile import (
    FitnessLevel,
    InjuryRiskLevel,
    ProfileEngine,
    RunnerProfile,
    TrainingPattern,
)


class TestRunnerProfile:
    """测试 RunnerProfile 数据类"""

    def test_create_default_profile(self):
        """测试创建默认画像"""
        profile = RunnerProfile(user_id="test_user", profile_date=datetime.now())

        assert profile.user_id == "test_user"
        assert profile.total_activities == 0
        assert profile.fitness_level == FitnessLevel.BEGINNER
        assert profile.training_pattern == TrainingPattern.REST
        assert profile.injury_risk_level == InjuryRiskLevel.LOW

    def test_create_profile_with_data(self):
        """测试创建带数据的画像"""
        profile = RunnerProfile(
            user_id="test_user",
            profile_date=datetime.now(),
            total_activities=50,
            total_distance_km=500.0,
            total_duration_hours=50.0,
            avg_vdot=45.5,
            fitness_level=FitnessLevel.INTERMEDIATE,
        )

        assert profile.total_activities == 50
        assert profile.total_distance_km == 500.0
        assert profile.avg_vdot == 45.5
        assert profile.fitness_level == FitnessLevel.INTERMEDIATE

    def test_to_dict(self):
        """测试转换为字典"""
        profile = RunnerProfile(
            user_id="test_user",
            profile_date=datetime(2024, 1, 1, 12, 0, 0),
            total_activities=10,
            total_distance_km=100.0,
            avg_vdot=40.0,
            fitness_level=FitnessLevel.INTERMEDIATE,
            training_pattern=TrainingPattern.LIGHT,
            injury_risk_level=InjuryRiskLevel.LOW,
        )

        result = profile.to_dict()

        assert result["user_id"] == "test_user"
        assert result["total_activities"] == 10
        assert result["total_distance_km"] == 100.0
        assert result["avg_vdot"] == 40.0
        assert result["fitness_level"] == "中级"
        assert result["training_pattern"] == "轻松型"
        assert result["injury_risk_level"] == "低"
        assert "profile_date" in result
        assert "notes" in result
        assert isinstance(result["notes"], list)

    def test_to_dict_rounding(self):
        """测试字典转换的数值舍入"""
        profile = RunnerProfile(
            user_id="test_user",
            profile_date=datetime.now(),
            total_distance_km=100.123456,
            avg_vdot=45.6789,
            injury_risk_score=30.999,
        )

        result = profile.to_dict()

        assert result["total_distance_km"] == 100.12
        assert result["avg_vdot"] == 45.68
        assert result["injury_risk_score"] == 31.0


class TestFitnessLevel:
    """测试 FitnessLevel 枚举"""

    def test_fitness_level_values(self):
        """测试体能水平枚举值"""
        assert FitnessLevel.BEGINNER.value == "初学者"
        assert FitnessLevel.INTERMEDIATE.value == "中级"
        assert FitnessLevel.ADVANCED.value == "进阶"
        assert FitnessLevel.ELITE.value == "精英"


class TestTrainingPattern:
    """测试 TrainingPattern 枚举"""

    def test_training_pattern_values(self):
        """测试训练模式枚举值"""
        assert TrainingPattern.REST.value == "休息型"
        assert TrainingPattern.LIGHT.value == "轻松型"
        assert TrainingPattern.MODERATE.value == "适度型"
        assert TrainingPattern.INTENSE.value == "高强度型"
        assert TrainingPattern.EXTREME.value == "极限型"


class TestInjuryRiskLevel:
    """测试 InjuryRiskLevel 枚举"""

    def test_injury_risk_level_values(self):
        """测试伤病风险枚举值"""
        assert InjuryRiskLevel.LOW.value == "低"
        assert InjuryRiskLevel.MEDIUM.value == "中"
        assert InjuryRiskLevel.HIGH.value == "高"


class TestProfileEngine:
    """测试 ProfileEngine 类"""

    @pytest.fixture
    def mock_storage(self):
        """创建模拟 StorageManager"""
        storage = Mock()
        return storage

    @pytest.fixture
    def engine(self, mock_storage):
        """创建 ProfileEngine 实例"""
        return ProfileEngine(mock_storage)

    def test_init(self, engine, mock_storage):
        """测试初始化"""
        assert engine.storage == mock_storage

    def test_get_fitness_level_beginner(self, engine):
        """测试初学者体能水平判断"""
        assert engine.get_fitness_level(25) == FitnessLevel.BEGINNER
        assert engine.get_fitness_level(29.9) == FitnessLevel.BEGINNER

    def test_get_fitness_level_intermediate(self, engine):
        """测试中级体能水平判断"""
        assert engine.get_fitness_level(30) == FitnessLevel.INTERMEDIATE
        assert engine.get_fitness_level(40) == FitnessLevel.INTERMEDIATE
        assert engine.get_fitness_level(44.9) == FitnessLevel.INTERMEDIATE

    def test_get_fitness_level_advanced(self, engine):
        """测试进阶体能水平判断"""
        assert engine.get_fitness_level(45) == FitnessLevel.ADVANCED
        assert engine.get_fitness_level(50) == FitnessLevel.ADVANCED
        assert engine.get_fitness_level(59.9) == FitnessLevel.ADVANCED

    def test_get_fitness_level_elite(self, engine):
        """测试精英体能水平判断"""
        assert engine.get_fitness_level(60) == FitnessLevel.ELITE
        assert engine.get_fitness_level(70) == FitnessLevel.ELITE

    def test_get_training_pattern_rest(self, engine):
        """测试休息型训练模式判断"""
        assert engine.get_training_pattern(0) == TrainingPattern.REST
        assert engine.get_training_pattern(5) == TrainingPattern.REST
        assert engine.get_training_pattern(9.9) == TrainingPattern.REST

    def test_get_training_pattern_light(self, engine):
        """测试轻松型训练模式判断"""
        assert engine.get_training_pattern(10) == TrainingPattern.LIGHT
        assert engine.get_training_pattern(20) == TrainingPattern.LIGHT
        assert engine.get_training_pattern(29.9) == TrainingPattern.LIGHT

    def test_get_training_pattern_moderate(self, engine):
        """测试适度型训练模式判断"""
        assert engine.get_training_pattern(30) == TrainingPattern.MODERATE
        assert engine.get_training_pattern(40) == TrainingPattern.MODERATE
        assert engine.get_training_pattern(49.9) == TrainingPattern.MODERATE

    def test_get_training_pattern_intense(self, engine):
        """测试高强度型训练模式判断"""
        assert engine.get_training_pattern(50) == TrainingPattern.INTENSE
        assert engine.get_training_pattern(60) == TrainingPattern.INTENSE
        assert engine.get_training_pattern(79.9) == TrainingPattern.INTENSE

    def test_get_training_pattern_extreme(self, engine):
        """测试极限型训练模式判断"""
        assert engine.get_training_pattern(80) == TrainingPattern.EXTREME
        assert engine.get_training_pattern(100) == TrainingPattern.EXTREME

    def test_build_profile_no_data(self, engine, mock_storage):
        """测试无数据时构建画像"""
        # 模拟空 LazyFrame
        mock_lf = Mock()
        mock_lf.collect_schema.return_value = []
        mock_storage.read_parquet.return_value = mock_lf

        profile = engine.build_profile(user_id="test_user", days=90)

        assert profile.user_id == "test_user"
        assert profile.total_activities == 0
        assert profile.data_quality_score == 0.0
        assert "暂无跑步数据" in profile.notes[0]

    def test_build_profile_invalid_days(self, engine):
        """测试无效天数参数"""
        with pytest.raises(ValueError, match="分析天数必须为正数"):
            engine.build_profile(days=0)

        with pytest.raises(ValueError, match="分析天数必须为正数"):
            engine.build_profile(days=-10)

    def test_build_profile_invalid_age(self, engine):
        """测试无效年龄参数"""
        with pytest.raises(ValueError, match="年龄必须在 1-120 之间"):
            engine.build_profile(age=0)

        with pytest.raises(ValueError, match="年龄必须在 1-120 之间"):
            engine.build_profile(age=150)

    def test_build_profile_invalid_resting_hr(self, engine):
        """测试无效静息心率参数"""
        with pytest.raises(ValueError, match="静息心率必须在合理范围内"):
            engine.build_profile(resting_hr=0)

        with pytest.raises(ValueError, match="静息心率必须在合理范围内"):
            engine.build_profile(resting_hr=250)

    def test_build_profile_with_data(self, engine, mock_storage):
        """测试有数据时构建画像"""
        # 创建模拟数据
        now = datetime.now()
        data = {
            "timestamp": [now - timedelta(days=i) for i in range(10)],
            "total_distance": [5000.0 + i * 100 for i in range(10)],
            "total_timer_time": [1800.0 + i * 60 for i in range(10)],
            "avg_heart_rate": [140 + i for i in range(10)],
            "max_heart_rate": [160 + i for i in range(10)],
        }
        mock_df = pl.DataFrame(data)
        mock_lf = mock_df.lazy()
        mock_storage.read_parquet.return_value = mock_lf

        profile = engine.build_profile(user_id="test_user", days=90)

        assert profile.user_id == "test_user"
        assert profile.total_activities == 10
        assert profile.total_distance_km > 0
        assert profile.total_duration_hours > 0
        assert profile.data_quality_score > 0

    def test_calculate_injury_risk_low_risk(self, engine):
        """测试低风险伤病风险评估"""
        profile = RunnerProfile(
            user_id="test_user",
            profile_date=datetime.now(),
            atl=30,
            ctl=40,
            tsb=10,
            consistency_score=80,
            training_pattern=TrainingPattern.MODERATE,
        )

        result = engine.calculate_injury_risk(profile, age=30, resting_hr=60)

        assert result["risk_score"] < 30
        assert result["risk_level"] == "低"
        assert isinstance(result["risk_factors"], list)
        assert isinstance(result["recommendations"], list)

    def test_calculate_injury_risk_medium_risk(self, engine):
        """测试中等风险伤病风险评估"""
        profile = RunnerProfile(
            user_id="test_user",
            profile_date=datetime.now(),
            atl=50,
            ctl=40,
            tsb=-10,
            consistency_score=50,
            training_pattern=TrainingPattern.INTENSE,
        )

        result = engine.calculate_injury_risk(profile, age=35, resting_hr=60)

        assert 30 <= result["risk_score"] < 60
        assert result["risk_level"] == "中"

    def test_calculate_injury_risk_high_risk(self, engine):
        """测试高风险伤病风险评估"""
        profile = RunnerProfile(
            user_id="test_user",
            profile_date=datetime.now(),
            atl=80,
            ctl=40,
            tsb=-40,
            consistency_score=20,
            training_pattern=TrainingPattern.EXTREME,
        )

        result = engine.calculate_injury_risk(profile, age=55, resting_hr=60)

        assert result["risk_score"] >= 60
        assert result["risk_level"] == "高"
        assert len(result["risk_factors"]) > 0

    def test_calculate_injury_risk_invalid_age(self, engine):
        """测试无效年龄参数"""
        profile = RunnerProfile(user_id="test_user", profile_date=datetime.now())

        with pytest.raises(ValueError, match="年龄必须在 1-120 之间"):
            engine.calculate_injury_risk(profile, age=0)

    def test_calculate_injury_risk_invalid_resting_hr(self, engine):
        """测试无效静息心率参数"""
        profile = RunnerProfile(user_id="test_user", profile_date=datetime.now())

        with pytest.raises(ValueError, match="静息心率必须在合理范围内"):
            engine.calculate_injury_risk(profile, age=30, resting_hr=250)

    def test_calculate_injury_risk_atl_ctl_ratio_high(self, engine):
        """测试 ATL/CTL 比率过高的风险"""
        profile = RunnerProfile(
            user_id="test_user",
            profile_date=datetime.now(),
            atl=90,
            ctl=40,
            tsb=-50,
            consistency_score=90,
            training_pattern=TrainingPattern.LIGHT,
        )

        result = engine.calculate_injury_risk(profile, age=30, resting_hr=60)

        assert "训练负荷突增" in " ".join(result["risk_factors"])

    def test_calculate_injury_risk_low_consistency(self, engine):
        """测试训练不规律的风险"""
        profile = RunnerProfile(
            user_id="test_user",
            profile_date=datetime.now(),
            atl=20,
            ctl=30,
            tsb=10,
            consistency_score=10,
            training_pattern=TrainingPattern.LIGHT,
        )

        result = engine.calculate_injury_risk(profile, age=30, resting_hr=60)

        assert "训练" in " ".join(result["risk_factors"])

    def test_calculate_injury_risk_age_factor(self, engine):
        """测试年龄因素的风险"""
        profile = RunnerProfile(
            user_id="test_user",
            profile_date=datetime.now(),
            atl=30,
            ctl=40,
            tsb=10,
            consistency_score=80,
            training_pattern=TrainingPattern.MODERATE,
        )

        # 年轻跑者
        result_young = engine.calculate_injury_risk(profile, age=25, resting_hr=60)

        # 年长跑者
        result_old = engine.calculate_injury_risk(profile, age=55, resting_hr=60)

        # 年长跑者风险应该更高
        assert result_old["risk_score"] > result_young["risk_score"]

    def test_analyze_running_time_preference_morning(self, engine):
        """测试早晨跑步偏好分析"""
        from datetime import timezone

        now = datetime.now(timezone.utc)
        timestamps = pl.Series([now.replace(hour=2, minute=0) for _ in range(10)])

        result = engine._analyze_running_time_preference(timestamps)
        assert result == "morning"

    def test_analyze_running_time_preference_afternoon(self, engine):
        """测试下午跑步偏好分析"""
        from datetime import timezone

        now = datetime.now(timezone.utc)
        timestamps = pl.Series([now.replace(hour=7, minute=0) for _ in range(10)])

        result = engine._analyze_running_time_preference(timestamps)
        assert result == "afternoon"

    def test_analyze_running_time_preference_evening(self, engine):
        """测试晚上跑步偏好分析"""
        from datetime import timezone

        now = datetime.now(timezone.utc)
        timestamps = pl.Series([now.replace(hour=15, minute=0) for _ in range(10)])

        result = engine._analyze_running_time_preference(timestamps)
        assert result == "evening"

    def test_calculate_consistency_score_no_data(self, engine):
        """测试无数据时一致性评分"""
        df = pl.DataFrame()
        score = engine._calculate_consistency_score(df, days=90)
        assert score == 0.0

    def test_calculate_consistency_score_regular(self, engine):
        """测试规律训练的一致性评分"""
        now = datetime.now()
        # 每隔一天跑步，非常规律（20 次跑步在 40 天内）
        timestamps = [now - timedelta(days=i * 2) for i in range(20)]
        timestamps.reverse()

        # 添加距离和时长数据
        df = pl.DataFrame(
            {
                "timestamp": timestamps,
                "total_distance": [5000.0] * 20,
                "total_timer_time": [1800.0] * 20,
            }
        )
        score = engine._calculate_consistency_score(df, days=90)

        # 规律训练应该有较高分数（至少>30）
        # 20 次跑步在 90 天内，每周约 1.5 次，基础分 = 1.5/5*60 = 18 分
        # 规律性评分应该很高（标准差小）
        assert score > 20  # 至少应该有基础分

    def test_calculate_consistency_score_irregular(self, engine):
        """测试不规律训练的一致性评分"""
        now = datetime.now()
        # 不规律的间隔
        intervals = [1, 5, 2, 10, 1, 3, 8, 2, 6, 1]
        timestamps = []
        current = now - timedelta(days=sum(intervals))
        for interval in intervals:
            current += timedelta(days=interval)
            timestamps.append(current)

        df = pl.DataFrame({"timestamp": timestamps})
        score = engine._calculate_consistency_score(df, days=90)

        assert score < 50  # 不规律训练分数较低

    def test_calculate_data_quality_no_data(self, engine):
        """测试无数据时数据质量评分"""
        mock_lf = Mock()
        mock_df = pl.DataFrame()
        mock_lf.collect.return_value = mock_df

        profile = RunnerProfile(user_id="test_user", profile_date=datetime.now())
        engine._calculate_data_quality(mock_lf, profile)

        assert profile.data_quality_score == 0.0

    def test_calculate_data_quality_with_data(self, engine):
        """测试有数据时数据质量评分"""
        now = datetime.now()
        data = {
            "timestamp": [now - timedelta(days=i) for i in range(20)],
            "total_distance": [5000.0 + i * 100 for i in range(20)],
            "total_timer_time": [1800.0 + i * 60 for i in range(20)],
            "avg_heart_rate": [140 + i for i in range(20)],
        }
        mock_df = pl.DataFrame(data)
        mock_lf = Mock()
        mock_lf.collect.return_value = mock_df

        profile = RunnerProfile(
            user_id="test_user", profile_date=datetime.now(), analysis_period_days=90
        )
        engine._calculate_data_quality(mock_lf, profile)

        assert profile.data_quality_score > 50  # 有数据应该有基本分数

    def test_calculate_data_quality_missing_hr(self, engine):
        """测试缺少心率数据时的数据质量评分"""
        now = datetime.now()
        data = {
            "timestamp": [now - timedelta(days=i) for i in range(20)],
            "total_distance": [5000.0 + i * 100 for i in range(20)],
            "total_timer_time": [1800.0 + i * 60 for i in range(20)],
            # 没有 avg_heart_rate 字段
        }
        mock_df = pl.DataFrame(data)
        mock_lf = Mock()
        mock_lf.collect.return_value = mock_df

        profile = RunnerProfile(
            user_id="test_user", profile_date=datetime.now(), analysis_period_days=90
        )
        engine._calculate_data_quality(mock_lf, profile)

        # 缺少心率数据，分数应该 <= 60 分（没有心率分的 40 分）
        assert profile.data_quality_score <= 60

    def test_is_empty_lazyframe_with_columns(self, engine):
        """测试检查有列的 LazyFrame"""
        df = pl.DataFrame({"col1": [1, 2, 3]})
        lf = df.lazy()

        assert not engine._is_empty_lazyframe(lf)

    def test_is_empty_lazyframe_without_columns(self, engine, mock_storage):
        """测试检查无列的 LazyFrame"""
        # 创建无列的 LazyFrame
        lf = pl.DataFrame().lazy()

        assert engine._is_empty_lazyframe(lf)

    def test_is_empty_lazyframe_empty_data(self, engine):
        """测试检查空数据的 LazyFrame"""
        df = pl.DataFrame({"col1": []})
        lf = df.lazy()

        assert engine._is_empty_lazyframe(lf)

    def test_create_empty_profile(self, engine):
        """测试创建空画像"""
        profile = engine._create_empty_profile(user_id="test_user", days=90)

        assert profile.user_id == "test_user"
        assert profile.total_activities == 0
        assert profile.analysis_period_days == 90
        assert profile.data_quality_score == 0.0
        assert len(profile.notes) > 0

    def test_calculate_basic_stats(self, engine):
        """测试基础统计计算"""
        now = datetime.now()
        data = {
            "timestamp": [now - timedelta(days=i) for i in range(5)],
            "total_distance": [5000.0, 6000.0, 5500.0, 7000.0, 6500.0],
            "total_timer_time": [1800.0, 2000.0, 1900.0, 2200.0, 2100.0],
        }
        df = pl.DataFrame(data)
        lf = df.lazy()

        profile = RunnerProfile(user_id="test_user", profile_date=datetime.now())
        engine._calculate_basic_stats(lf, profile)

        assert profile.total_activities == 5
        assert profile.total_distance_km > 0
        assert profile.total_duration_hours > 0
        assert profile.avg_pace_min_per_km > 0

    def test_calculate_vdot_metrics(self, engine, mock_storage):
        """测试 VDOT 指标计算"""
        now = datetime.now()
        data = {
            "timestamp": [now - timedelta(days=i) for i in range(5)],
            "total_distance": [5000.0, 6000.0, 5500.0, 7000.0, 6500.0],
            "total_timer_time": [1800.0, 2000.0, 1900.0, 2200.0, 2100.0],
        }
        mock_df = pl.DataFrame(data)
        mock_storage.read_parquet.return_value = mock_df.lazy()

        profile = RunnerProfile(user_id="test_user", profile_date=datetime.now())
        engine._calculate_vdot_metrics(mock_df.lazy(), profile)

        assert profile.avg_vdot > 0
        assert profile.max_vdot > 0
        assert profile.max_vdot >= profile.avg_vdot

    def test_calculate_training_pattern(self, engine):
        """测试训练模式计算"""
        now = datetime.now()
        # 创建 30 天数据，总跑量 200km
        data = {
            "timestamp": [now - timedelta(days=i) for i in range(30)],
            "total_distance": [7000.0 for _ in range(30)],  # 每次 7km，总共 210km
            "total_timer_time": [2100.0 for _ in range(30)],
        }
        df = pl.DataFrame(data)
        lf = df.lazy()

        profile = RunnerProfile(user_id="test_user", profile_date=datetime.now())
        profile.total_distance_km = 210.0  # 30 天 210km
        profile.total_duration_hours = 17.5

        engine._calculate_training_pattern(lf, profile, days=30)

        # 周平均跑量 = 210 / (30/7) = 49km，应该是适度型
        assert profile.weekly_avg_distance_km > 0
        assert profile.training_pattern in [
            TrainingPattern.MODERATE,
            TrainingPattern.INTENSE,
        ]

    def test_calculate_hr_metrics(self, engine):
        """测试心率指标计算"""
        now = datetime.now()
        data = {
            "timestamp": [now - timedelta(days=i) for i in range(10)],
            "avg_heart_rate": [140 + i for i in range(10)],
            "max_heart_rate": [160 + i for i in range(10)],
        }
        df = pl.DataFrame(data)
        lf = df.lazy()

        profile = RunnerProfile(user_id="test_user", profile_date=datetime.now())
        engine._calculate_hr_metrics(lf, profile)

        assert profile.avg_heart_rate is not None
        assert profile.max_heart_rate is not None
        assert profile.avg_heart_rate > 0
        assert profile.max_heart_rate > profile.avg_heart_rate

    def test_calculate_hr_metrics_missing_data(self, engine):
        """测试缺少心率数据时的心率指标计算"""
        data = {
            "timestamp": [],
            # 没有 avg_heart_rate 字段
        }
        df = pl.DataFrame(data)
        lf = df.lazy()

        profile = RunnerProfile(user_id="test_user", profile_date=datetime.now())
        engine._calculate_hr_metrics(lf, profile)

        # 心率指标应该保持为 None
        assert profile.avg_heart_rate is None
        assert profile.max_heart_rate is None

    def test_calculate_training_load(self, engine, mock_storage):
        """测试训练负荷计算"""
        now = datetime.now()
        data = {
            "timestamp": [now - timedelta(days=i) for i in range(10)],
            "total_distance": [5000.0 + i * 100 for i in range(10)],
            "total_timer_time": [1800.0 + i * 60 for i in range(10)],
            "avg_heart_rate": [140 + i for i in range(10)],
        }
        mock_df = pl.DataFrame(data)
        mock_storage.read_parquet.return_value = mock_df.lazy()

        profile = RunnerProfile(user_id="test_user", profile_date=datetime.now())
        engine._calculate_training_load(mock_df.lazy(), profile)

        # 有数据时应该有 ATL/CTL 值
        assert profile.atl >= 0
        assert profile.ctl >= 0

    def test_calculate_additional_metrics(self, engine):
        """测试其他指标计算"""
        now = datetime.now()
        data = {
            "timestamp": [
                now.replace(hour=7 + i % 3) - timedelta(days=i) for i in range(20)
            ],
            "total_distance": [5000.0 for _ in range(20)],
            "total_timer_time": [1800.0 for _ in range(20)],
        }
        df = pl.DataFrame(data)

        profile = RunnerProfile(user_id="test_user", profile_date=datetime.now())
        engine._calculate_additional_metrics(df, profile, days=90)

        assert profile.favorite_running_time in ["morning", "afternoon", "evening"]
        assert 0 <= profile.consistency_score <= 100


class TestProfileIntegration:
    """ProfileEngine 集成测试"""

    @pytest.fixture
    def mock_storage_with_data(self):
        """创建带模拟数据的 StorageManager"""
        storage = Mock()

        now = datetime.now()
        data = {
            "timestamp": [now - timedelta(days=i) for i in range(30)],
            "total_distance": [5000.0 + i * 100 for i in range(30)],
            "total_timer_time": [1800.0 + i * 60 for i in range(30)],
            "avg_heart_rate": [140 + (i % 10) for i in range(30)],
            "max_heart_rate": [160 + (i % 10) for i in range(30)],
        }
        mock_df = pl.DataFrame(data)
        storage.read_parquet.return_value = mock_df.lazy()

        return storage

    def test_build_profile_complete_workflow(self, mock_storage_with_data):
        """测试完整的画像构建工作流程"""
        engine = ProfileEngine(mock_storage_with_data)

        profile = engine.build_profile(
            user_id="test_user", days=30, age=30, resting_hr=60
        )

        # 验证基本信息
        assert profile.user_id == "test_user"
        assert profile.total_activities == 30
        assert profile.total_distance_km > 0
        assert profile.total_duration_hours > 0

        # 验证体能指标
        assert profile.avg_vdot > 0
        assert profile.max_vdot > 0
        assert profile.max_vdot >= profile.avg_vdot
        assert profile.fitness_level in FitnessLevel

        # 验证训练模式
        assert profile.weekly_avg_distance_km > 0
        assert profile.training_pattern in TrainingPattern

        # 验证心率指标
        assert profile.avg_heart_rate is not None
        assert profile.max_heart_rate is not None

        # 验证训练负荷
        assert profile.atl >= 0
        assert profile.ctl >= 0

        # 验证伤病风险
        assert 0 <= profile.injury_risk_score <= 100
        assert profile.injury_risk_level in InjuryRiskLevel

        # 验证其他指标
        assert profile.avg_pace_min_per_km > 0
        assert profile.favorite_running_time in ["morning", "afternoon", "evening"]
        assert 0 <= profile.consistency_score <= 100
        assert 0 <= profile.data_quality_score <= 100

        # 验证字典转换
        profile_dict = profile.to_dict()
        assert profile_dict["user_id"] == "test_user"
        assert "fitness_level" in profile_dict
        assert "training_pattern" in profile_dict
        assert "injury_risk_level" in profile_dict

    def test_injury_risk_assessment_workflow(self, mock_storage_with_data):
        """测试伤病风险评估工作流程"""
        engine = ProfileEngine(mock_storage_with_data)

        # 先构建画像
        profile = engine.build_profile(user_id="test_user", days=30)

        # 再评估伤病风险
        risk_result = engine.calculate_injury_risk(profile, age=30, resting_hr=60)

        assert "risk_score" in risk_result
        assert "risk_level" in risk_result
        assert "risk_factors" in risk_result
        assert "recommendations" in risk_result
        assert isinstance(risk_result["risk_factors"], list)
        assert isinstance(risk_result["recommendations"], list)
