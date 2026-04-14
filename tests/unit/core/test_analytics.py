# AnalyticsEngine单元测试
# 测试数据分析引擎的核心功能

from datetime import datetime, timedelta
from unittest.mock import Mock

import polars as pl
import pytest

from src.core.analytics import (
    AnalyticsEngine,
    _resolve_col,
)


class TestResolveCol:
    """列名解析测试"""

    def test_resolve_col_first_candidate(self):
        """测试第一个候选列存在"""
        df = pl.DataFrame({"distance": [1000], "duration": [300]})

        result = _resolve_col(df, "distance", "total_distance")

        assert result == "distance"

    def test_resolve_col_second_candidate(self):
        """测试第二个候选列存在"""
        df = pl.DataFrame({"total_distance": [1000], "duration": [300]})

        result = _resolve_col(df, "distance", "total_distance")

        assert result == "total_distance"

    def test_resolve_col_not_found(self):
        """测试所有候选列均不存在"""
        df = pl.DataFrame({"other": [1000]})

        with pytest.raises(RuntimeError, match="DataFrame中未找到候选列"):
            _resolve_col(df, "distance", "total_distance")


class TestCalculateTssForRun:
    """单次跑步TSS计算测试"""

    @pytest.fixture
    def engine(self):
        """创建AnalyticsEngine实例"""
        mock_storage = Mock()
        mock_storage.read_parquet.return_value = pl.LazyFrame()
        return AnalyticsEngine(mock_storage)

    def test_calculate_tss_for_run_normal(self, engine):
        """测试正常TSS计算"""
        tss = engine.calculate_tss_for_run(
            distance_m=5000.0,
            duration_s=1800.0,
            avg_heart_rate=150.0,
            age=30,
            rest_hr=60,
        )

        assert 0 < tss < 500
        assert isinstance(tss, float)

    def test_calculate_tss_for_run_zero_duration(self, engine):
        """测试零时长"""
        tss = engine.calculate_tss_for_run(
            distance_m=5000.0,
            duration_s=0,
            avg_heart_rate=150.0,
        )

        assert tss == 0.0

    def test_calculate_tss_for_run_zero_distance(self, engine):
        """测试零距离"""
        tss = engine.calculate_tss_for_run(
            distance_m=0,
            duration_s=1800.0,
            avg_heart_rate=150.0,
        )

        assert tss == 0.0

    def test_calculate_tss_for_run_none_heart_rate(self, engine):
        """测试心率数据缺失"""
        tss = engine.calculate_tss_for_run(
            distance_m=5000.0,
            duration_s=1800.0,
            avg_heart_rate=None,
        )

        assert tss == 0.0

    def test_calculate_tss_for_run_none_distance(self, engine):
        """测试距离为None"""
        tss = engine.calculate_tss_for_run(
            distance_m=None,
            duration_s=1800.0,
            avg_heart_rate=150.0,
        )

        assert tss == 0.0

    def test_calculate_tss_for_run_none_duration(self, engine):
        """测试时长为None"""
        tss = engine.calculate_tss_for_run(
            distance_m=5000.0,
            duration_s=None,
            avg_heart_rate=150.0,
        )

        assert tss == 0.0

    def test_calculate_tss_for_run_high_heart_rate(self, engine):
        """测试高心率（超过最大心率）"""
        tss = engine.calculate_tss_for_run(
            distance_m=5000.0,
            duration_s=1800.0,
            avg_heart_rate=200.0,
            age=30,
        )

        assert tss > 0

    def test_calculate_tss_for_run_low_heart_rate(self, engine):
        """测试低心率（低于静息心率）"""
        tss = engine.calculate_tss_for_run(
            distance_m=5000.0,
            duration_s=1800.0,
            avg_heart_rate=50.0,
            rest_hr=60,
        )

        assert tss == 0.0

    def test_calculate_tss_for_run_equal_rest_hr(self, engine):
        """测试心率等于静息心率"""
        tss = engine.calculate_tss_for_run(
            distance_m=5000.0,
            duration_s=1800.0,
            avg_heart_rate=60.0,
            rest_hr=60,
        )

        assert tss == 0.0

    def test_calculate_tss_for_run_rest_hr_equals_max_hr(self, engine):
        """测试静息心率等于最大心率"""
        tss = engine.calculate_tss_for_run(
            distance_m=5000.0,
            duration_s=1800.0,
            avg_heart_rate=150.0,
            age=30,
            rest_hr=190,
        )

        assert tss == 0.0

    def test_calculate_tss_for_run_intense_workout(self, engine):
        """测试高强度训练"""
        tss = engine.calculate_tss_for_run(
            distance_m=10000.0,
            duration_s=3600.0,
            avg_heart_rate=170.0,
            age=30,
            rest_hr=60,
        )

        assert tss > 50

    def test_calculate_tss_for_run_easy_workout(self, engine):
        """测试轻松训练"""
        tss = engine.calculate_tss_for_run(
            distance_m=5000.0,
            duration_s=1800.0,
            avg_heart_rate=120.0,
            age=30,
            rest_hr=60,
        )

        assert tss > 0
        assert tss < 100


class TestEvaluateFitnessStatus:
    """体能状态评估测试"""

    @pytest.fixture
    def engine(self):
        """创建AnalyticsEngine实例"""
        mock_storage = Mock()
        mock_storage.read_parquet.return_value = pl.LazyFrame()
        return AnalyticsEngine(mock_storage)

    def test_evaluate_fitness_status_excellent(self, engine):
        """测试体能充沛状态"""
        status, advice = engine._evaluate_fitness_status(tsb=15.0, _atl=50.0, _ctl=65.0)

        assert status == "恢复良好"
        assert "体能充沛" in advice

    def test_evaluate_fitness_status_normal(self, engine):
        """测试状态正常"""
        status, advice = engine._evaluate_fitness_status(tsb=5.0, _atl=55.0, _ctl=60.0)

        assert status == "状态正常"
        assert "状态良好" in advice

    def test_evaluate_fitness_status_mild_fatigue(self, engine):
        """测试轻度疲劳"""
        status, advice = engine._evaluate_fitness_status(tsb=-5.0, _atl=65.0, _ctl=60.0)

        assert status == "轻度疲劳"
        assert "疲劳" in advice

    def test_evaluate_fitness_status_over_training(self, engine):
        """测试过度训练"""
        status, advice = engine._evaluate_fitness_status(
            tsb=-15.0, _atl=75.0, _ctl=60.0
        )

        assert status == "过度训练"
        assert "过度训练" in advice

    def test_evaluate_fitness_status_low_ctl(self, engine):
        """测试低CTL体能基础"""
        status, advice = engine._evaluate_fitness_status(tsb=10.0, _atl=20.0, _ctl=25.0)

        assert "体能基础较弱" in advice

    def test_evaluate_fitness_status_high_ctl(self, engine):
        """测试高CTL体能基础"""
        status, advice = engine._evaluate_fitness_status(tsb=10.0, _atl=70.0, _ctl=85.0)

        assert "体能基础扎实" in advice


class TestCalculateHrZones:
    """心率区间计算测试"""

    @pytest.fixture
    def engine(self):
        """创建AnalyticsEngine实例"""
        mock_storage = Mock()
        mock_storage.read_parquet.return_value = pl.LazyFrame()
        return AnalyticsEngine(mock_storage)

    def test_calculate_hr_zones(self, engine):
        """测试心率区间计算"""
        max_hr = 200

        zones = engine._calculate_hr_zones(max_hr)

        assert "zone1" in zones
        assert "zone2" in zones
        assert "zone3" in zones
        assert "zone4" in zones
        assert "zone5" in zones

        assert zones["zone1"] == (100, 120)
        assert zones["zone2"] == (120, 140)
        assert zones["zone3"] == (140, 160)
        assert zones["zone4"] == (160, 180)
        assert zones["zone5"] == (180, 200)

    def test_calculate_hr_zones_different_max_hr(self, engine):
        """测试不同最大心率"""
        max_hr = 180

        zones = engine._calculate_hr_zones(max_hr)

        assert zones["zone1"][0] == 90
        assert zones["zone5"][1] == 180


class TestCalculateZoneTime:
    """区间时长计算测试"""

    @pytest.fixture
    def engine(self):
        """创建AnalyticsEngine实例"""
        mock_storage = Mock()
        mock_storage.read_parquet.return_value = pl.LazyFrame()
        return AnalyticsEngine(mock_storage)

    def test_calculate_zone_time(self, engine):
        """测试区间时长计算"""
        heart_rate_data = [100, 110, 120, 130, 140, 150, 160, 170, 180, 190]
        hr_zones = {
            "zone1": (100, 120),
            "zone2": (120, 140),
            "zone3": (140, 160),
            "zone4": (160, 180),
            "zone5": (180, 200),
        }

        zone_time = engine._calculate_zone_time(heart_rate_data, hr_zones)

        assert zone_time["zone1"] == 2
        assert zone_time["zone2"] == 2
        assert zone_time["zone3"] == 2
        assert zone_time["zone4"] == 2
        assert zone_time["zone5"] == 2

    def test_calculate_zone_time_empty(self, engine):
        """测试空心率数据"""
        zone_time = engine._calculate_zone_time([], {})

        assert zone_time == {"zone1": 0, "zone2": 0, "zone3": 0, "zone4": 0, "zone5": 0}

    def test_calculate_zone_time_below_zone1(self, engine):
        """测试低于区间1的心率"""
        heart_rate_data = [80, 90, 95]
        hr_zones = {
            "zone1": (100, 120),
            "zone2": (120, 140),
            "zone3": (140, 160),
            "zone4": (160, 180),
            "zone5": (180, 200),
        }

        zone_time = engine._calculate_zone_time(heart_rate_data, hr_zones)

        assert zone_time["zone1"] == 0


class TestCalculateAerobicEffect:
    """有氧效果计算测试"""

    @pytest.fixture
    def engine(self):
        """创建AnalyticsEngine实例"""
        mock_storage = Mock()
        mock_storage.read_parquet.return_value = pl.LazyFrame()
        return AnalyticsEngine(mock_storage)

    def test_calculate_aerobic_effect_normal(self, engine):
        """测试正常有氧效果计算"""
        zone_time = {
            "zone1": 300,
            "zone2": 600,
            "zone3": 600,
            "zone4": 300,
            "zone5": 0,
        }
        total_duration = 1800

        effect = engine._calculate_aerobic_effect(zone_time, total_duration)

        assert 1.0 <= effect <= 5.0

    def test_calculate_aerobic_effect_zero_duration(self, engine):
        """测试零时长"""
        zone_time = {"zone1": 0, "zone2": 0, "zone3": 0, "zone4": 0, "zone5": 0}

        effect = engine._calculate_aerobic_effect(zone_time, 0)

        assert effect == 1.0

    def test_calculate_aerobic_effect_high(self, engine):
        """测试高有氧效果"""
        zone_time = {
            "zone1": 0,
            "zone2": 1800,
            "zone3": 1800,
            "zone4": 0,
            "zone5": 0,
        }
        total_duration = 3600

        effect = engine._calculate_aerobic_effect(zone_time, total_duration)

        assert effect >= 3.0


class TestCalculateAnaerobicEffect:
    """无氧效果计算测试"""

    @pytest.fixture
    def engine(self):
        """创建AnalyticsEngine实例"""
        mock_storage = Mock()
        mock_storage.read_parquet.return_value = pl.LazyFrame()
        return AnalyticsEngine(mock_storage)

    def test_calculate_anaerobic_effect_normal(self, engine):
        """测试正常无氧效果计算"""
        zone_time = {
            "zone1": 300,
            "zone2": 600,
            "zone3": 600,
            "zone4": 300,
            "zone5": 0,
        }
        total_duration = 1800

        effect = engine._calculate_anaerobic_effect(zone_time, total_duration)

        assert 1.0 <= effect <= 5.0

    def test_calculate_anaerobic_effect_zero_duration(self, engine):
        """测试零时长"""
        zone_time = {"zone1": 0, "zone2": 0, "zone3": 0, "zone4": 0, "zone5": 0}

        effect = engine._calculate_anaerobic_effect(zone_time, 0)

        assert effect == 1.0

    def test_calculate_anaerobic_effect_high(self, engine):
        """测试高无氧效果"""
        zone_time = {
            "zone1": 0,
            "zone2": 0,
            "zone3": 0,
            "zone4": 1800,
            "zone5": 1800,
        }
        total_duration = 3600

        effect = engine._calculate_anaerobic_effect(zone_time, total_duration)

        assert effect >= 3.0


class TestCalculateAvgPace:
    """平均配速计算测试"""

    @pytest.fixture
    def engine(self):
        """创建AnalyticsEngine实例"""
        mock_storage = Mock()
        mock_storage.read_parquet.return_value = pl.LazyFrame()
        return AnalyticsEngine(mock_storage)

    def test_calculate_avg_pace_normal(self, engine):
        """测试正常配速计算"""
        df = pl.DataFrame(
            {
                "distance": [5000.0, 10000.0],
                "duration": [1500.0, 3000.0],
            }
        )

        pace = engine._calculate_avg_pace(df)

        assert pace == "5:00"

    def test_calculate_avg_pace_zero_distance(self, engine):
        """测试零距离"""
        df = pl.DataFrame(
            {
                "distance": [0.0],
                "duration": [1500.0],
            }
        )

        pace = engine._calculate_avg_pace(df)

        assert pace == "0:00"

    def test_calculate_avg_pace_from_values(self, engine):
        """测试从数值计算配速"""
        pace = engine._calculate_avg_pace_from_values(
            total_distance=5000.0, total_duration=1500.0
        )

        assert pace == "5:00"

    def test_calculate_avg_pace_from_values_zero_distance(self, engine):
        """测试从数值计算配速（零距离）"""
        pace = engine._calculate_avg_pace_from_values(
            total_distance=0.0, total_duration=1500.0
        )

        assert pace == "0:00"


class TestGetVdotTrend:
    """VDOT趋势分析测试"""

    @pytest.fixture
    def mock_storage(self):
        """创建mock StorageManager"""
        storage = Mock()
        now = datetime.now()
        storage.read_parquet.return_value = pl.LazyFrame(
            {
                "timestamp": [
                    now - timedelta(days=2),
                    now - timedelta(days=1),
                    now,
                ],
                "session_total_distance": [5000.0, 10000.0, 8000.0],
                "session_total_timer_time": [1800.0, 3600.0, 2700.0],
            }
        )
        return storage

    @pytest.fixture
    def engine(self, mock_storage):
        """创建AnalyticsEngine实例"""
        return AnalyticsEngine(mock_storage)

    def test_get_vdot_trend(self, engine):
        """测试获取VDOT趋势"""
        trend = engine.get_vdot_trend(days=30)

        assert len(trend) == 3
        assert all(hasattr(t, "date") for t in trend)
        assert all(hasattr(t, "vdot") for t in trend)
        assert all(hasattr(t, "distance") for t in trend)
        assert all(hasattr(t, "duration") for t in trend)

    def test_get_vdot_trend_empty(self):
        """测试空数据的VDOT趋势"""
        mock_storage = Mock()
        mock_storage.read_parquet.return_value = pl.LazyFrame()
        engine = AnalyticsEngine(mock_storage)

        trend = engine.get_vdot_trend(days=30)

        assert trend == []

    def test_get_vdot_trend_with_alternative_columns(self):
        """测试使用替代列名"""
        mock_storage = Mock()
        now = datetime.now()
        mock_storage.read_parquet.return_value = pl.LazyFrame(
            {
                "timestamp": [now],
                "total_distance": [5000.0],
                "total_timer_time": [1800.0],
            }
        )
        engine = AnalyticsEngine(mock_storage)

        trend = engine.get_vdot_trend(days=30)

        assert len(trend) == 1


class TestGetTrainingLoad:
    """训练负荷分析测试"""

    @pytest.fixture
    def mock_storage_with_data(self):
        """创建包含数据的mock StorageManager"""
        storage = Mock()
        now = datetime.now()
        dates = [now - timedelta(days=i) for i in range(30)]

        storage.read_parquet.return_value = pl.LazyFrame(
            {
                "session_start_time": dates,
                "session_total_distance": [5000.0] * 30,
                "session_total_timer_time": [1800.0] * 30,
                "session_avg_heart_rate": [150.0] * 30,
            }
        )
        return storage

    @pytest.fixture
    def mock_storage_empty(self):
        """创建空数据的mock StorageManager"""
        storage = Mock()
        storage.read_parquet.return_value = pl.LazyFrame()
        return storage

    def test_get_training_load_with_data(self, mock_storage_with_data):
        """测试有数据的训练负荷分析"""
        engine = AnalyticsEngine(mock_storage_with_data)

        result = engine.get_training_load(days=30)

        assert "atl" in result
        assert "ctl" in result
        assert "tsb" in result
        assert "fitness_status" in result
        assert "training_advice" in result
        assert result["atl"] >= 0
        assert result["ctl"] >= 0

    def test_get_training_load_empty(self, mock_storage_empty):
        """测试空数据的训练负荷分析"""
        engine = AnalyticsEngine(mock_storage_empty)

        result = engine.get_training_load(days=30)

        assert result["atl"] == 0.0
        assert result["ctl"] == 0.0
        assert result["tsb"] == 0.0
        assert result["fitness_status"] == "数据不足"
        assert "message" in result

    def test_get_training_load_no_heart_rate(self):
        """测试无心率数据的训练负荷分析"""
        mock_storage = Mock()
        now = datetime.now()
        mock_storage.read_parquet.return_value = pl.LazyFrame(
            {
                "session_start_time": [now - timedelta(days=i) for i in range(10)],
                "session_total_distance": [5000.0] * 10,
                "session_total_timer_time": [1800.0] * 10,
                "session_avg_heart_rate": [0.0] * 10,
            }
        )
        engine = AnalyticsEngine(mock_storage)

        result = engine.get_training_load(days=30)

        assert "atl" in result
        assert "ctl" in result
        assert "tsb" in result
        assert "fitness_status" in result

    def test_get_training_load_insufficient_data(self):
        """测试数据量不足的训练负荷分析"""
        mock_storage = Mock()
        now = datetime.now()
        mock_storage.read_parquet.return_value = pl.LazyFrame(
            {
                "session_start_time": [now - timedelta(days=i) for i in range(5)],
                "session_total_distance": [5000.0] * 5,
                "session_total_timer_time": [1800.0] * 5,
                "session_avg_heart_rate": [150.0] * 5,
            }
        )
        engine = AnalyticsEngine(mock_storage)

        result = engine.get_training_load(days=30)

        assert "message" in result
        assert "数据量较少" in result["message"]


class TestAnalyticsEngineDelegation:
    """AnalyticsEngine委托测试"""

    @pytest.fixture
    def engine(self):
        """创建AnalyticsEngine实例"""
        mock_storage = Mock()
        mock_storage.read_parquet.return_value = pl.LazyFrame()
        return AnalyticsEngine(mock_storage)

    def test_calculate_vdot_delegation(self, engine):
        """测试VDOT计算委托"""
        vdot = engine.calculate_vdot(5000.0, 1800.0)

        assert vdot > 0

    def test_calculate_tss_delegation(self, engine):
        """测试TSS计算委托"""
        hr_data = pl.Series([150, 155, 160, 155, 150])
        tss = engine.calculate_tss(hr_data, 3600)

        assert tss > 0

    def test_calculate_atl_delegation(self, engine):
        """测试ATL计算委托"""
        tss_values = [100.0] * 7
        atl = engine.calculate_atl(tss_values)

        assert atl > 0

    def test_calculate_ctl_delegation(self, engine):
        """测试CTL计算委托"""
        tss_values = [100.0] * 42
        ctl = engine.calculate_ctl(tss_values)

        assert ctl > 0

    def test_calculate_atl_ctl_delegation(self, engine):
        """测试ATL/CTL计算委托"""
        tss_values = [100.0] * 42
        result = engine.calculate_atl_ctl(tss_values)

        assert "atl" in result
        assert "ctl" in result

    def test_analyze_hr_drift_delegation(self, engine):
        """测试心率漂移分析委托"""
        heart_rate = [140, 145, 150, 155, 160, 165, 170, 175, 180, 185]
        pace = [5.5, 5.4, 5.3, 5.2, 5.1, 5.0, 4.9, 4.8, 4.7, 4.6]

        result = engine.analyze_hr_drift(heart_rate, pace)

        assert hasattr(result, "drift") or result.error is not None
