# ProfileEngine单元测试
# 测试用户画像引擎的核心功能

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

import polars as pl
import pytest

from src.core.models import FitnessLevel
from src.core.profile import (
    AnomalyFilterRule,
    ProfileEngine,
    ProfileStaleStatus,
    RunnerProfile,
)
from src.core.user_profile_manager import InjuryRiskLevel, TrainingPattern


class TestRunnerProfile:
    """RunnerProfile数据类测试"""

    def test_runner_profile_to_dict(self):
        """测试RunnerProfile转换为字典"""
        profile = RunnerProfile(
            user_id="test_user",
            profile_date=datetime(2024, 1, 1),
            total_activities=10,
            total_distance_km=50.0,
            total_duration_hours=5.0,
            avg_vdot=40.0,
            max_vdot=45.0,
            fitness_level=FitnessLevel.INTERMEDIATE,
        )

        result = profile.to_dict()

        assert result["user_id"] == "test_user"
        assert result["total_activities"] == 10
        assert result["total_distance_km"] == 50.0
        assert result["avg_vdot"] == 40.0
        assert result["fitness_level"] == "intermediate"

    def test_runner_profile_default_values(self):
        """测试RunnerProfile默认值"""
        profile = RunnerProfile(user_id="test_user", profile_date=datetime(2024, 1, 1))

        assert profile.total_activities == 0
        assert profile.total_distance_km == 0.0
        assert profile.avg_vdot == 0.0
        assert profile.fitness_level == FitnessLevel.BEGINNER
        assert profile.training_pattern == TrainingPattern.REST
        assert profile.injury_risk_level == InjuryRiskLevel.LOW


class TestGetFitnessLevel:
    """体能水平判断测试"""

    @pytest.fixture
    def engine(self):
        """创建ProfileEngine实例"""
        mock_context = Mock()
        mock_storage = Mock()
        mock_storage.read_parquet.return_value = pl.LazyFrame()
        mock_context.storage = mock_storage
        mock_context.analytics = Mock()
        return ProfileEngine(mock_context)

    def test_get_fitness_level_beginner(self, engine):
        """测试初学者水平"""
        level = engine.get_fitness_level(25.0)
        assert level == FitnessLevel.BEGINNER

    def test_get_fitness_level_intermediate(self, engine):
        """测试中级水平"""
        level = engine.get_fitness_level(35.0)
        assert level == FitnessLevel.INTERMEDIATE

    def test_get_fitness_level_advanced(self, engine):
        """测试进阶水平"""
        level = engine.get_fitness_level(50.0)
        assert level == FitnessLevel.ADVANCED

    def test_get_fitness_level_elite(self, engine):
        """测试精英水平"""
        level = engine.get_fitness_level(65.0)
        assert level == FitnessLevel.ELITE

    def test_get_fitness_level_boundary_beginner(self, engine):
        """测试初学者边界值"""
        level = engine.get_fitness_level(29.9)
        assert level == FitnessLevel.BEGINNER

    def test_get_fitness_level_boundary_intermediate(self, engine):
        """测试中级边界值"""
        level = engine.get_fitness_level(30.0)
        assert level == FitnessLevel.INTERMEDIATE

    def test_get_fitness_level_boundary_advanced(self, engine):
        """测试进阶边界值"""
        level = engine.get_fitness_level(45.0)
        assert level == FitnessLevel.ADVANCED

    def test_get_fitness_level_boundary_elite(self, engine):
        """测试精英边界值"""
        level = engine.get_fitness_level(60.0)
        assert level == FitnessLevel.ELITE


class TestGetTrainingPattern:
    """训练模式判断测试"""

    @pytest.fixture
    def engine(self):
        """创建ProfileEngine实例"""
        mock_context = Mock()
        mock_storage = Mock()
        mock_storage.read_parquet.return_value = pl.LazyFrame()
        mock_context.storage = mock_storage
        mock_context.analytics = Mock()
        return ProfileEngine(mock_context)

    def test_get_training_pattern_rest(self, engine):
        """测试休息型"""
        pattern = engine.get_training_pattern(5.0)
        assert pattern == TrainingPattern.REST

    def test_get_training_pattern_light(self, engine):
        """测试轻松型"""
        pattern = engine.get_training_pattern(20.0)
        assert pattern == TrainingPattern.LIGHT

    def test_get_training_pattern_moderate(self, engine):
        """测试适度型"""
        pattern = engine.get_training_pattern(40.0)
        assert pattern == TrainingPattern.MODERATE

    def test_get_training_pattern_intense(self, engine):
        """测试高强度型"""
        pattern = engine.get_training_pattern(65.0)
        assert pattern == TrainingPattern.INTENSE

    def test_get_training_pattern_extreme(self, engine):
        """测试极限型"""
        pattern = engine.get_training_pattern(90.0)
        assert pattern == TrainingPattern.EXTREME

    def test_get_training_pattern_boundary_rest(self, engine):
        """测试休息型边界值"""
        pattern = engine.get_training_pattern(9.9)
        assert pattern == TrainingPattern.REST

    def test_get_training_pattern_boundary_light(self, engine):
        """测试轻松型边界值"""
        pattern = engine.get_training_pattern(10.0)
        assert pattern == TrainingPattern.LIGHT

    def test_get_training_pattern_boundary_moderate(self, engine):
        """测试适度型边界值"""
        pattern = engine.get_training_pattern(30.0)
        assert pattern == TrainingPattern.MODERATE

    def test_get_training_pattern_boundary_intense(self, engine):
        """测试高强度型边界值"""
        pattern = engine.get_training_pattern(50.0)
        assert pattern == TrainingPattern.INTENSE

    def test_get_training_pattern_boundary_extreme(self, engine):
        """测试极限型边界值"""
        pattern = engine.get_training_pattern(80.0)
        assert pattern == TrainingPattern.EXTREME


class TestBuildProfile:
    """构建用户画像测试"""

    @pytest.fixture
    def mock_context(self):
        """创建mock AppContext"""
        mock_context = Mock()
        mock_storage = Mock()

        now = datetime.now()
        mock_storage.read_parquet.return_value = pl.LazyFrame(
            {
                "timestamp": [now - timedelta(days=i) for i in range(10)],
                "session_total_distance": [5000.0] * 10,
                "session_total_timer_time": [1800.0] * 10,
                "session_avg_heart_rate": [150.0] * 10,
                "session_max_heart_rate": [170.0] * 10,
            }
        )

        mock_context.storage = mock_storage
        mock_context.analytics = Mock()
        mock_context.analytics.calculate_vdot.return_value = 40.0
        mock_context.analytics.calculate_tss_for_run.return_value = 50.0
        mock_context.analytics.calculate_atl_ctl.return_value = {
            "atl": 50.0,
            "ctl": 60.0,
        }
        return mock_context

    @pytest.fixture
    def engine(self, mock_context):
        """创建ProfileEngine实例"""
        return ProfileEngine(mock_context)

    def test_build_profile_normal(self, engine):
        """测试正常构建画像"""
        profile = engine.build_profile(user_id="test_user", days=30)

        assert profile.user_id == "test_user"
        assert profile.total_activities > 0
        assert profile.total_distance_km > 0
        assert profile.analysis_period_days == 30

    def test_build_profile_invalid_days(self, engine):
        """测试无效天数"""
        with pytest.raises(ValueError, match="分析天数必须为正数"):
            engine.build_profile(days=0)

    def test_build_profile_invalid_age(self, engine):
        """测试无效年龄"""
        with pytest.raises(ValueError, match="年龄必须在"):
            engine.build_profile(age=0)

    def test_build_profile_invalid_resting_hr(self, engine):
        """测试无效静息心率"""
        with pytest.raises(ValueError, match="静息心率必须在合理范围内"):
            engine.build_profile(resting_hr=0)

    def test_build_profile_empty_data(self):
        """测试空数据构建画像"""
        mock_context = Mock()
        mock_storage = Mock()
        mock_storage.read_parquet.return_value = pl.LazyFrame()
        mock_context.storage = mock_storage
        mock_context.analytics = Mock()
        engine = ProfileEngine(mock_context)

        profile = engine.build_profile(user_id="test_user", days=30)

        assert profile.user_id == "test_user"
        assert profile.total_activities == 0
        assert profile.data_quality_score == 0.0
        assert "暂无跑步数据" in profile.notes[0]


class TestCalculateInjuryRisk:
    """伤病风险计算测试"""

    @pytest.fixture
    def engine(self):
        """创建ProfileEngine实例"""
        mock_context = Mock()
        mock_storage = Mock()
        mock_storage.read_parquet.return_value = pl.LazyFrame()
        mock_context.storage = mock_storage
        mock_context.analytics = Mock()
        return ProfileEngine(mock_context)

    def test_calculate_injury_risk(self, engine):
        """测试伤病风险计算"""
        profile = RunnerProfile(
            user_id="test_user",
            profile_date=datetime.now(),
            atl=50.0,
            ctl=60.0,
            consistency_score=80.0,
        )

        result = engine.calculate_injury_risk(profile, age=30, resting_hr=60)

        assert "risk_score" in result
        assert "risk_level" in result
        assert "risk_factors" in result
        assert "recommendations" in result


class TestCheckFreshness:
    """画像保鲜期检查测试"""

    @pytest.fixture
    def engine(self):
        """创建ProfileEngine实例"""
        mock_context = Mock()
        mock_storage = Mock()
        mock_storage.read_parquet.return_value = pl.LazyFrame()
        mock_context.storage = mock_storage
        mock_context.analytics = Mock()
        return ProfileEngine(mock_context)

    def test_check_freshness_fresh(self, engine):
        """测试新鲜画像"""
        profile = RunnerProfile(
            user_id="test_user", profile_date=datetime.now() - timedelta(days=3)
        )

        status = engine.check_freshness(profile)

        assert status == ProfileStaleStatus.FRESH

    def test_check_freshness_stale(self, engine):
        """测试过期画像"""
        profile = RunnerProfile(
            user_id="test_user", profile_date=datetime.now() - timedelta(days=10)
        )

        status = engine.check_freshness(profile)

        assert status == ProfileStaleStatus.STALE

    def test_check_freshness_missing(self, engine):
        """测试缺失画像"""
        with patch.object(
            engine.storage_manager, "load_profile_json", return_value=None
        ):
            status = engine.check_freshness()

        assert status == ProfileStaleStatus.MISSING

    def test_check_freshness_custom_days(self, engine):
        """测试自定义保鲜期"""
        profile = RunnerProfile(
            user_id="test_user", profile_date=datetime.now() - timedelta(days=5)
        )

        status = engine.check_freshness(profile, freshness_days=3)

        assert status == ProfileStaleStatus.STALE


class TestAnalyzeRunningTimePreference:
    """跑步时间偏好分析测试"""

    @pytest.fixture
    def engine(self):
        """创建ProfileEngine实例"""
        mock_context = Mock()
        mock_storage = Mock()
        mock_storage.read_parquet.return_value = pl.LazyFrame()
        mock_context.storage = mock_storage
        mock_context.analytics = Mock()
        return ProfileEngine(mock_context)

    def test_analyze_running_time_preference_morning(self, engine):
        """测试晨跑偏好"""

        utc = UTC
        timestamps = pl.Series(
            [
                datetime(2024, 1, 1, 0, 0, tzinfo=utc),
                datetime(2024, 1, 2, 1, 0, tzinfo=utc),
                datetime(2024, 1, 3, 2, 0, tzinfo=utc),
            ]
        )

        result = engine._analyze_running_time_preference(timestamps)

        assert result == "morning"

    def test_analyze_running_time_preference_afternoon(self, engine):
        """测试下午跑偏好"""

        utc = UTC
        timestamps = pl.Series(
            [
                datetime(2024, 1, 1, 6, 0, tzinfo=utc),
                datetime(2024, 1, 2, 7, 0, tzinfo=utc),
                datetime(2024, 1, 3, 8, 0, tzinfo=utc),
            ]
        )

        result = engine._analyze_running_time_preference(timestamps)

        assert result == "afternoon"

    def test_analyze_running_time_preference_evening(self, engine):
        """测试夜跑偏好"""

        utc = UTC
        timestamps = pl.Series(
            [
                datetime(2024, 1, 1, 14, 0, tzinfo=utc),
                datetime(2024, 1, 2, 15, 0, tzinfo=utc),
                datetime(2024, 1, 3, 16, 0, tzinfo=utc),
            ]
        )

        result = engine._analyze_running_time_preference(timestamps)

        assert result == "evening"


class TestCalculateConsistencyScore:
    """训练一致性评分测试"""

    @pytest.fixture
    def engine(self):
        """创建ProfileEngine实例"""
        mock_context = Mock()
        mock_storage = Mock()
        mock_storage.read_parquet.return_value = pl.LazyFrame()
        mock_context.storage = mock_storage
        mock_context.analytics = Mock()
        return ProfileEngine(mock_context)

    def test_calculate_consistency_score_empty(self, engine):
        """测试空数据"""
        df = pl.DataFrame()
        score = engine._calculate_consistency_score(df, 30)

        assert score == 0.0

    def test_calculate_consistency_score_single_run(self, engine):
        """测试单次跑步"""
        df = pl.DataFrame({"timestamp": [datetime.now()]})
        score = engine._calculate_consistency_score(df, 30)

        assert 0 <= score <= 100

    def test_calculate_consistency_score_regular(self, engine):
        """测试规律训练"""
        now = datetime.now()
        timestamps = [now - timedelta(days=i) for i in range(10)]
        df = pl.DataFrame({"timestamp": timestamps})
        score = engine._calculate_consistency_score(df, 30)

        assert score > 0


class TestCalculateDataQuality:
    """数据质量评分测试"""

    @pytest.fixture
    def engine(self):
        """创建ProfileEngine实例"""
        mock_context = Mock()
        mock_storage = Mock()
        mock_storage.read_parquet.return_value = pl.LazyFrame()
        mock_context.storage = mock_storage
        mock_context.analytics = Mock()
        return ProfileEngine(mock_context)

    def test_calculate_data_quality_empty(self, engine):
        """测试空数据"""
        lf = pl.LazyFrame()
        profile = RunnerProfile(
            user_id="test_user", profile_date=datetime.now(), analysis_period_days=30
        )

        engine._calculate_data_quality(lf, profile)

        assert profile.data_quality_score == 0.0

    def test_calculate_data_quality_with_data(self, engine):
        """测试有数据"""
        lf = pl.LazyFrame(
            {
                "total_distance": [5000.0] * 10,
                "total_timer_time": [1800.0] * 10,
                "avg_heart_rate": [150.0] * 10,
            }
        )
        profile = RunnerProfile(
            user_id="test_user", profile_date=datetime.now(), analysis_period_days=90
        )

        engine._calculate_data_quality(lf, profile)

        assert 0 <= profile.data_quality_score <= 100


class TestFilterAnomalyData:
    """异常数据过滤测试"""

    @pytest.fixture
    def engine(self):
        """创建ProfileEngine实例"""
        mock_context = Mock()
        mock_storage = Mock()
        mock_storage.read_parquet.return_value = pl.LazyFrame()
        mock_context.storage = mock_storage
        mock_context.analytics = Mock()
        return ProfileEngine(mock_context)

    def test_filter_anomaly_data_empty(self, engine):
        """测试空数据"""
        lf = pl.LazyFrame()

        with pytest.raises((ValueError, RuntimeError)):
            engine.filter_anomaly_data(lf)

    def test_filter_anomaly_data_normal(self, engine):
        """测试正常数据"""
        lf = pl.LazyFrame(
            {
                "avg_heart_rate": [150.0, 160.0, 140.0],
                "total_distance": [5000.0, 10000.0, 8000.0],
            }
        )

        result = engine.filter_anomaly_data(lf)

        assert isinstance(result, pl.LazyFrame)

    def test_filter_anomaly_data_with_custom_rules(self, engine):
        """测试自定义规则"""
        lf = pl.LazyFrame(
            {
                "avg_heart_rate": [150.0, 160.0, 140.0],
            }
        )

        rules = [
            AnomalyFilterRule(
                field_name="avg_heart_rate",
                condition=">",
                threshold=155,
                action="filter",
                description="测试规则",
            )
        ]

        result = engine.filter_anomaly_data(lf, rules=rules)

        assert isinstance(result, pl.LazyFrame)


class TestNormalizeColumnNames:
    """列名规范化测试"""

    @pytest.fixture
    def engine(self):
        """创建ProfileEngine实例"""
        mock_context = Mock()
        mock_storage = Mock()
        mock_storage.read_parquet.return_value = pl.LazyFrame()
        mock_context.storage = mock_storage
        mock_context.analytics = Mock()
        return ProfileEngine(mock_context)

    def test_normalize_column_names_with_session_prefix(self, engine):
        """测试带session_前缀的列名"""
        lf = pl.LazyFrame(
            {
                "session_total_distance": [5000.0],
                "session_total_timer_time": [1800.0],
            }
        )

        result = engine._normalize_column_names(lf)
        columns = result.collect_schema().names()

        assert "total_distance" in columns
        assert "total_timer_time" in columns

    def test_normalize_column_names_already_normalized(self, engine):
        """测试已规范化的列名"""
        lf = pl.LazyFrame(
            {
                "total_distance": [5000.0],
                "total_timer_time": [1800.0],
            }
        )

        result = engine._normalize_column_names(lf)
        columns = result.collect_schema().names()

        assert "total_distance" in columns
        assert "total_timer_time" in columns


class TestIsEmptyLazyFrame:
    """空LazyFrame检查测试"""

    @pytest.fixture
    def engine(self):
        """创建ProfileEngine实例"""
        mock_context = Mock()
        mock_storage = Mock()
        mock_storage.read_parquet.return_value = pl.LazyFrame()
        mock_context.storage = mock_storage
        mock_context.analytics = Mock()
        return ProfileEngine(mock_context)

    def test_is_empty_lazyframe_empty(self, engine):
        """测试空LazyFrame"""
        lf = pl.LazyFrame()
        result = engine._is_empty_lazyframe(lf)

        assert result is True

    def test_is_empty_lazyframe_with_data(self, engine):
        """测试有数据的LazyFrame"""
        lf = pl.LazyFrame({"col": [1, 2, 3]})
        result = engine._is_empty_lazyframe(lf)

        assert result is False

    def test_is_empty_lazyframe_empty_rows(self, engine):
        """测试无行的LazyFrame"""
        lf = pl.LazyFrame({"col": []})
        result = engine._is_empty_lazyframe(lf)

        assert result is True
