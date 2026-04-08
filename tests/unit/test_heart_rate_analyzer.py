# HeartRateAnalyzer 单元测试

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import polars as pl
import pytest

from src.core.heart_rate_analyzer import HeartRateAnalyzer


class TestHeartRateAnalyzer:
    """测试 HeartRateAnalyzer 类"""

    @pytest.fixture
    def mock_storage(self):
        """创建模拟的 StorageManager"""
        storage = MagicMock()
        return storage

    @pytest.fixture
    def hr_analyzer(self, mock_storage):
        """创建 HeartRateAnalyzer 实例"""
        return HeartRateAnalyzer(mock_storage)

    def test_analyze_hr_drift_success(self, hr_analyzer):
        """测试心率漂移分析成功"""
        heart_rate = [150, 152, 155, 158, 160, 162, 165, 168, 170, 172, 174, 176]
        pace = [300, 298, 295, 293, 290, 288, 285, 283, 280, 278, 275, 273]
        result = hr_analyzer.analyze_hr_drift(heart_rate, pace)
        assert "drift" in result
        assert "drift_rate" in result
        assert "correlation" in result
        assert "assessment" in result

    def test_analyze_hr_drift_empty_data(self, hr_analyzer):
        """测试空数据"""
        result = hr_analyzer.analyze_hr_drift([], [])
        assert "error" in result

    def test_analyze_hr_drift_insufficient_data(self, hr_analyzer):
        """测试数据量不足"""
        heart_rate = [150, 152]
        pace = [300, 298]
        result = hr_analyzer.analyze_hr_drift(heart_rate, pace)
        assert "error" in result

    def test_calculate_hr_zones(self, hr_analyzer):
        """测试心率区间计算"""
        zones = hr_analyzer._calculate_hr_zones(max_hr=180)
        assert "zone1" in zones
        assert "zone2" in zones
        assert "zone3" in zones
        assert "zone4" in zones
        assert "zone5" in zones
        assert zones["zone1"] == (90, 108)
        assert zones["zone5"] == (162, 180)

    def test_calculate_zone_time(self, hr_analyzer):
        """测试区间时长计算"""
        hr_zones = {
            "zone1": (90, 108),
            "zone2": (108, 126),
            "zone3": (126, 144),
            "zone4": (144, 162),
            "zone5": (162, 180),
        }
        heart_rate_data = [100, 110, 120, 130, 140, 150, 160, 170]
        zone_time = hr_analyzer._calculate_zone_time(heart_rate_data, hr_zones)
        assert zone_time["zone1"] == 1
        assert zone_time["zone2"] == 2
        assert zone_time["zone3"] == 2
        assert zone_time["zone4"] == 2
        assert zone_time["zone5"] == 1

    def test_calculate_aerobic_effect(self, hr_analyzer):
        """测试有氧效果计算"""
        zone_time = {
            "zone1": 100,
            "zone2": 200,
            "zone3": 300,
            "zone4": 100,
            "zone5": 50,
        }
        effect = hr_analyzer._calculate_aerobic_effect(zone_time, 750)
        assert 1.0 <= effect <= 5.0

    def test_calculate_anaerobic_effect(self, hr_analyzer):
        """测试无氧效果计算"""
        zone_time = {
            "zone1": 100,
            "zone2": 200,
            "zone3": 300,
            "zone4": 100,
            "zone5": 50,
        }
        effect = hr_analyzer._calculate_anaerobic_effect(zone_time, 750)
        assert 1.0 <= effect <= 5.0

    def test_calculate_recovery_time(self, hr_analyzer):
        """测试恢复时间计算"""
        recovery = hr_analyzer._calculate_recovery_time(
            aerobic_effect=3.0,
            anaerobic_effect=2.5,
            duration_s=3600,
            avg_heart_rate=150,
            max_hr=180,
        )
        assert isinstance(recovery, int)
        assert 6 <= recovery <= 72

    def test_get_training_effect_success(self, hr_analyzer):
        """测试训练效果评估成功"""
        heart_rate_data = [140, 145, 150, 155, 160, 158, 152, 148]
        result = hr_analyzer.get_training_effect(
            heart_rate_data=heart_rate_data, duration_s=3600, age=30
        )
        assert "aerobic_effect" in result
        assert "anaerobic_effect" in result
        assert "recovery_time_hours" in result
        assert "hr_zones" in result
        assert "zone_time" in result
        assert "avg_heart_rate" in result

    def test_get_training_effect_invalid_duration(self, hr_analyzer):
        """测试无效时长"""
        with pytest.raises(ValueError, match="训练时长必须为正数"):
            hr_analyzer.get_training_effect(
                heart_rate_data=[150, 155], duration_s=0, age=30
            )

    def test_get_training_effect_invalid_age(self, hr_analyzer):
        """测试无效年龄"""
        with pytest.raises(ValueError, match="年龄必须在1-120之间"):
            hr_analyzer.get_training_effect(
                heart_rate_data=[150, 155], duration_s=3600, age=0
            )

    def test_get_training_effect_no_hr_data(self, hr_analyzer):
        """测试无心率数据"""
        with pytest.raises(ValueError, match="心率数据不能为空"):
            hr_analyzer.get_training_effect(heart_rate_data=[], duration_s=3600, age=30)

    def test_get_heart_rate_zones_empty_storage(self, hr_analyzer, mock_storage):
        """测试空存储"""
        mock_storage.read_parquet.return_value = pl.LazyFrame()
        result = hr_analyzer.get_heart_rate_zones(age=30)
        assert result["max_hr"] == 190
        assert result["zones"] == []
        assert result["activities_count"] == 0

    def test_get_heart_rate_zones_success(self, hr_analyzer, mock_storage):
        """测试成功获取心率区间"""
        now = datetime.now()
        df = pl.DataFrame(
            {
                "timestamp": [now - timedelta(days=1)],
                "session_avg_heart_rate": [155.0],
            }
        )
        mock_storage.read_parquet.return_value = df.lazy()

        result = hr_analyzer.get_heart_rate_zones(age=30)
        assert "max_hr" in result
        assert "zones" in result
        assert "total_time_in_hr" in result
        assert result["max_hr"] == 190

    def test_get_heart_rate_zones_invalid_age(self, hr_analyzer):
        """测试无效年龄"""
        with pytest.raises(ValueError, match="年龄必须在 1-120 范围内"):
            hr_analyzer.get_heart_rate_zones(age=0)

    def test_calculate_zones_from_avg_hr(self, hr_analyzer):
        """测试使用平均心率估算区间"""
        df = pl.DataFrame(
            {
                "session_avg_heart_rate": [140, 150, 160, 170],
            }
        )
        zone_boundaries = {
            "Z1": (0.50, 0.60, "恢复区"),
            "Z2": (0.60, 0.70, "有氧区"),
            "Z3": (0.70, 0.80, "节奏区"),
            "Z4": (0.80, 0.90, "阈值区"),
            "Z5": (0.90, 1.00, "无氧区"),
        }
        result = hr_analyzer._calculate_zones_from_avg_hr(df, 180, zone_boundaries)
        assert "max_hr" in result
        assert "zones" in result
        assert result["max_hr"] == 180


class TestHeartRateAnalyzerVectorized:
    """心率分析器向量化方法测试类"""

    @pytest.fixture
    def mock_storage(self):
        """创建模拟的 StorageManager"""
        storage = MagicMock()
        return storage

    @pytest.fixture
    def hr_analyzer(self, mock_storage):
        """创建 HeartRateAnalyzer 实例"""
        return HeartRateAnalyzer(mock_storage)

    def test_analyze_hr_drift_vectorized_basic(
        self, hr_analyzer: HeartRateAnalyzer
    ) -> None:
        """测试向量化心率漂移分析 - 基本场景"""
        heart_rate = pl.Series(
            [150, 152, 155, 158, 160, 162, 165, 168, 170, 172, 174, 176]
        )
        pace = pl.Series([300, 298, 295, 293, 290, 288, 285, 283, 280, 278, 275, 273])

        result = hr_analyzer.analyze_hr_drift_vectorized(heart_rate, pace)

        assert "drift" in result
        assert "drift_rate" in result
        assert "correlation" in result
        assert "assessment" in result

    def test_analyze_hr_drift_vectorized_empty_data(
        self, hr_analyzer: HeartRateAnalyzer
    ) -> None:
        """测试向量化心率漂移分析 - 空数据"""
        heart_rate = pl.Series([])
        pace = pl.Series([])

        result = hr_analyzer.analyze_hr_drift_vectorized(heart_rate, pace)

        assert "error" in result

    def test_analyze_hr_drift_vectorized_insufficient_data(
        self, hr_analyzer: HeartRateAnalyzer
    ) -> None:
        """测试向量化心率漂移分析 - 数据量不足"""
        heart_rate = pl.Series([150, 152])
        pace = pl.Series([300, 298])

        result = hr_analyzer.analyze_hr_drift_vectorized(heart_rate, pace)

        assert "error" in result

    def test_analyze_hr_drift_vectorized_with_null_values(
        self, hr_analyzer: HeartRateAnalyzer
    ) -> None:
        """测试向量化心率漂移分析 - 包含空值"""
        heart_rate = pl.Series(
            [
                150,
                None,
                155,
                158,
                None,
                162,
                165,
                168,
                170,
                172,
                174,
                176,
                178,
                180,
                182,
                184,
            ]
        )
        pace = pl.Series(
            [
                300,
                298,
                None,
                293,
                290,
                288,
                285,
                None,
                280,
                278,
                275,
                273,
                270,
                268,
                265,
                263,
            ]
        )

        result = hr_analyzer.analyze_hr_drift_vectorized(heart_rate, pace)

        assert "drift" in result

    def test_analyze_hr_drift_vectorized_consistency(
        self, hr_analyzer: HeartRateAnalyzer
    ) -> None:
        """测试向量化与标量版本一致性"""
        heart_rate_list = [150, 152, 155, 158, 160, 162, 165, 168, 170, 172, 174, 176]
        pace_list = [300, 298, 295, 293, 290, 288, 285, 283, 280, 278, 275, 273]

        scalar_result = hr_analyzer.analyze_hr_drift(heart_rate_list, pace_list)

        heart_rate_series = pl.Series(heart_rate_list)
        pace_series = pl.Series(pace_list)
        vectorized_result = hr_analyzer.analyze_hr_drift_vectorized(
            heart_rate_series, pace_series
        )

        assert abs(scalar_result["drift"] - vectorized_result["drift"]) < 0.1
        assert abs(scalar_result["drift_rate"] - vectorized_result["drift_rate"]) < 0.1

    def test_calculate_zone_time_vectorized_basic(
        self, hr_analyzer: HeartRateAnalyzer
    ) -> None:
        """测试向量化区间时长计算 - 基本场景"""
        hr_zones = {
            "zone1": (90, 108),
            "zone2": (108, 126),
            "zone3": (126, 144),
            "zone4": (144, 162),
            "zone5": (162, 180),
        }
        heart_rate_series = pl.Series([100, 110, 120, 130, 140, 150, 160, 170])

        zone_time = hr_analyzer._calculate_zone_time_vectorized(
            heart_rate_series, hr_zones
        )

        assert zone_time["zone1"] == 1
        assert zone_time["zone2"] == 2
        assert zone_time["zone3"] == 2
        assert zone_time["zone4"] == 2
        assert zone_time["zone5"] == 1

    def test_calculate_zone_time_vectorized_empty_data(
        self, hr_analyzer: HeartRateAnalyzer
    ) -> None:
        """测试向量化区间时长计算 - 空数据"""
        hr_zones = {
            "zone1": (90, 108),
            "zone2": (108, 126),
            "zone3": (126, 144),
            "zone4": (144, 162),
            "zone5": (162, 180),
        }
        heart_rate_series = pl.Series([])

        zone_time = hr_analyzer._calculate_zone_time_vectorized(
            heart_rate_series, hr_zones
        )

        assert zone_time["zone1"] == 0
        assert zone_time["zone2"] == 0
        assert zone_time["zone3"] == 0
        assert zone_time["zone4"] == 0
        assert zone_time["zone5"] == 0

    def test_calculate_zone_time_vectorized_with_null_values(
        self, hr_analyzer: HeartRateAnalyzer
    ) -> None:
        """测试向量化区间时长计算 - 包含空值"""
        hr_zones = {
            "zone1": (90, 108),
            "zone2": (108, 126),
            "zone3": (126, 144),
            "zone4": (144, 162),
            "zone5": (162, 180),
        }
        heart_rate_series = pl.Series([100, None, 120, 130, None, 150, 160, 170])

        zone_time = hr_analyzer._calculate_zone_time_vectorized(
            heart_rate_series, hr_zones
        )

        assert zone_time["zone1"] == 1
        assert zone_time["zone2"] == 1
        assert zone_time["zone3"] == 1
        assert zone_time["zone4"] == 2
        assert zone_time["zone5"] == 1

    def test_calculate_zone_time_vectorized_consistency(
        self, hr_analyzer: HeartRateAnalyzer
    ) -> None:
        """测试向量化与标量版本一致性"""
        hr_zones = {
            "zone1": (90, 108),
            "zone2": (108, 126),
            "zone3": (126, 144),
            "zone4": (144, 162),
            "zone5": (162, 180),
        }
        heart_rate_list = [100, 110, 120, 130, 140, 150, 160, 170]
        heart_rate_series = pl.Series(heart_rate_list)

        scalar_result = hr_analyzer._calculate_zone_time(heart_rate_list, hr_zones)
        vectorized_result = hr_analyzer._calculate_zone_time_vectorized(
            heart_rate_series, hr_zones
        )

        assert scalar_result == vectorized_result

    def test_performance_comparison(self, hr_analyzer: HeartRateAnalyzer) -> None:
        """测试向量化方法性能（简单对比）"""
        import time

        n_points = 1000
        heart_rate_list = [100 + (i % 80) for i in range(n_points)]
        pace_list = [300 - (i % 20) for i in range(n_points)]
        heart_rate_series = pl.Series(heart_rate_list)
        pace_series = pl.Series(pace_list)

        start_scalar = time.perf_counter()
        for _ in range(10):
            hr_analyzer.analyze_hr_drift(heart_rate_list, pace_list)
        scalar_time = time.perf_counter() - start_scalar

        start_vectorized = time.perf_counter()
        for _ in range(10):
            hr_analyzer.analyze_hr_drift_vectorized(heart_rate_series, pace_series)
        vectorized_time = time.perf_counter() - start_vectorized

        print(f"\n标量版本: {scalar_time:.4f}s")
        print(f"向量化版本: {vectorized_time:.4f}s")
        print(f"性能提升: {(scalar_time / vectorized_time - 1) * 100:.1f}%")

        assert vectorized_time <= scalar_time * 2
