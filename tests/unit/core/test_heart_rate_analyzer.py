# 心率分析器单元测试
# 测试心率漂移、训练效果、心率区间等功能

from unittest.mock import Mock

import polars as pl
import pytest

from src.core.heart_rate_analyzer import HeartRateAnalyzer


class TestHeartRateAnalyzer:
    """心率分析器测试类"""

    @pytest.fixture
    def mock_storage(self):
        """创建 mock StorageManager"""
        storage = Mock()
        storage.read_parquet.return_value = pl.LazyFrame(
            {
                "timestamp": ["2024-01-01"],
                "session_avg_heart_rate": [150],
                "session_total_timer_time": [3600],
            }
        )
        return storage

    @pytest.fixture
    def analyzer(self, mock_storage):
        """创建心率分析器实例"""
        return HeartRateAnalyzer(mock_storage)

    def test_analyze_hr_drift_normal(self, analyzer):
        """测试正常心率漂移分析"""
        heart_rate = [140, 142, 145, 148, 150, 152, 155, 158, 160, 162]
        pace = [5.5, 5.4, 5.3, 5.2, 5.1, 5.0, 4.9, 4.8, 4.7, 4.6]

        result = analyzer.analyze_hr_drift(heart_rate, pace)

        assert hasattr(result, "drift")
        assert hasattr(result, "drift_rate")
        assert hasattr(result, "correlation")
        assert hasattr(result, "assessment")
        assert result.drift > 0

    def test_analyze_hr_drift_empty_hr(self, analyzer):
        """测试空心率数据"""
        result = analyzer.analyze_hr_drift([], [5.0, 5.1])

        assert result.error is not None
        assert result.error == "数据量不足"

    def test_analyze_hr_drift_empty_pace(self, analyzer):
        """测试空配速数据"""
        result = analyzer.analyze_hr_drift([150, 155], [])

        assert result.error is not None
        assert result.error == "数据量不足"

    def test_analyze_hr_drift_insufficient_data(self, analyzer):
        """测试数据量不足"""
        heart_rate = [150, 155, 160]
        pace = [5.0, 5.1, 5.2]

        result = analyzer.analyze_hr_drift(heart_rate, pace)

        assert result.error is not None
        assert result.error == "数据量不足"

    def test_analyze_hr_drift_with_none_values(self, analyzer):
        """测试包含None值的数据"""
        heart_rate = [140, None, 145, 148, None, 152, 155, 158, 160, 162, 164, 166]
        pace = [5.5, 5.4, None, 5.2, 5.1, 5.0, 4.9, None, 4.7, 4.6, 4.5, 4.4]

        result = analyzer.analyze_hr_drift(heart_rate, pace)

        assert hasattr(result, "drift") or result.error is not None

    def test_analyze_hr_drift_vectorized(self, analyzer):
        """测试向量化心率漂移分析"""
        heart_rate = pl.Series([140, 142, 145, 148, 150, 152, 155, 158, 160, 162])
        pace = pl.Series([5.5, 5.4, 5.3, 5.2, 5.1, 5.0, 4.9, 4.8, 4.7, 4.6])

        result = analyzer.analyze_hr_drift_vectorized(heart_rate, pace)

        assert "drift" in result
        assert "drift_rate" in result
        assert "correlation" in result
        assert "assessment" in result

    def test_analyze_hr_drift_vectorized_empty(self, analyzer):
        """测试向量化分析空数据"""
        heart_rate = pl.Series([])
        pace = pl.Series([])

        result = analyzer.analyze_hr_drift_vectorized(heart_rate, pace)

        assert "error" in result
        assert result["error"] == "数据量不足"

    def test_analyze_hr_drift_vectorized_insufficient(self, analyzer):
        """测试向量化分析数据不足"""
        heart_rate = pl.Series([150, 155, 160])
        pace = pl.Series([5.0, 5.1, 5.2])

        result = analyzer.analyze_hr_drift_vectorized(heart_rate, pace)

        assert "error" in result
        assert result["error"] == "数据量不足"

    def test_analyze_hr_drift_batch(self, analyzer):
        """测试批量心率漂移分析"""
        df = pl.DataFrame(
            {
                "heart_rate": [
                    [140, 142, 145, 148, 150, 152, 155, 158, 160, 162],
                    [145, 147, 150, 153, 156, 159, 162, 165, 168, 171],
                ],
                "pace": [
                    [5.5, 5.4, 5.3, 5.2, 5.1, 5.0, 4.9, 4.8, 4.7, 4.6],
                    [5.2, 5.1, 5.0, 4.9, 4.8, 4.7, 4.6, 4.5, 4.4, 4.3],
                ],
            }
        )

        results = analyzer.analyze_hr_drift_batch(df)

        assert len(results) == 2
        assert all("drift" in r or "error" in r for r in results)

    def test_analyze_hr_drift_batch_missing_columns(self, analyzer):
        """测试批量分析缺少列"""
        df = pl.DataFrame({"other_col": [1, 2, 3]})

        results = analyzer.analyze_hr_drift_batch(df)

        assert len(results) == 1
        assert "error" in results[0]

    def test_analyze_hr_drift_batch_with_none(self, analyzer):
        """测试批量分析包含None"""
        df = pl.DataFrame(
            {
                "heart_rate": [
                    None,
                    [140, 142, 145, 148, 150, 152, 155, 158, 160, 162],
                ],
                "pace": [None, [5.5, 5.4, 5.3, 5.2, 5.1, 5.0, 4.9, 4.8, 4.7, 4.6]],
            }
        )

        results = analyzer.analyze_hr_drift_batch(df)

        assert len(results) == 2
        assert "error" in results[0]

    def test_calculate_hr_zones(self, analyzer):
        """测试心率区间计算"""
        max_hr = 180

        zones = analyzer._calculate_hr_zones(max_hr)

        assert "zone1" in zones
        assert "zone2" in zones
        assert "zone3" in zones
        assert "zone4" in zones
        assert "zone5" in zones
        assert zones["zone1"][0] < zones["zone1"][1]

    def test_calculate_zone_time(self, analyzer):
        """测试心率区间时长计算"""
        heart_rate_data = [90, 100, 110, 120, 130, 140, 150, 160, 170, 180]
        max_hr = 180
        hr_zones = analyzer._calculate_hr_zones(max_hr)

        zone_time = analyzer._calculate_zone_time(heart_rate_data, hr_zones)

        assert "zone1" in zone_time
        assert "zone2" in zone_time
        assert "zone3" in zone_time
        assert "zone4" in zone_time
        assert "zone5" in zone_time
        assert sum(zone_time.values()) <= len(heart_rate_data)

    def test_calculate_zone_time_empty(self, analyzer):
        """测试空心率数据的区间时长"""
        hr_zones = analyzer._calculate_hr_zones(180)

        zone_time = analyzer._calculate_zone_time([], hr_zones)

        assert all(v == 0 for v in zone_time.values())

    def test_calculate_zone_time_vectorized(self, analyzer):
        """测试向量化心率区间时长计算"""
        heart_rate_series = pl.Series([90, 100, 110, 120, 130, 140, 150, 160, 170, 180])
        max_hr = 180
        hr_zones = analyzer._calculate_hr_zones(max_hr)

        zone_time = analyzer._calculate_zone_time_vectorized(
            heart_rate_series, hr_zones
        )

        assert "zone1" in zone_time
        assert "zone2" in zone_time
        assert "zone3" in zone_time
        assert "zone4" in zone_time
        assert "zone5" in zone_time

    def test_calculate_zone_time_vectorized_empty(self, analyzer):
        """测试向量化空数据"""
        heart_rate_series = pl.Series([])
        hr_zones = analyzer._calculate_hr_zones(180)

        zone_time = analyzer._calculate_zone_time_vectorized(
            heart_rate_series, hr_zones
        )

        assert all(v == 0 for v in zone_time.values())

    def test_calculate_aerobic_effect(self, analyzer):
        """测试有氧效果计算"""
        zone_time = {"zone1": 100, "zone2": 200, "zone3": 150, "zone4": 50, "zone5": 0}
        total_duration = 500

        effect = analyzer._calculate_aerobic_effect(zone_time, total_duration)

        assert 1.0 <= effect <= 5.0

    def test_calculate_aerobic_effect_zero_duration(self, analyzer):
        """测试零时长的有氧效果"""
        zone_time = {"zone1": 100, "zone2": 200, "zone3": 150, "zone4": 50, "zone5": 0}

        effect = analyzer._calculate_aerobic_effect(zone_time, 0)

        assert effect == 1.0

    def test_calculate_anaerobic_effect(self, analyzer):
        """测试无氧效果计算"""
        zone_time = {"zone1": 100, "zone2": 200, "zone3": 150, "zone4": 50, "zone5": 0}
        total_duration = 500

        effect = analyzer._calculate_anaerobic_effect(zone_time, total_duration)

        assert 1.0 <= effect <= 5.0

    def test_calculate_anaerobic_effect_zero_duration(self, analyzer):
        """测试零时长的无氧效果"""
        zone_time = {"zone1": 100, "zone2": 200, "zone3": 150, "zone4": 50, "zone5": 0}

        effect = analyzer._calculate_anaerobic_effect(zone_time, 0)

        assert effect == 1.0

    def test_calculate_recovery_time(self, analyzer):
        """测试恢复时间计算"""
        aerobic_effect = 3.5
        anaerobic_effect = 2.5
        duration_s = 3600
        avg_heart_rate = 150
        max_hr = 180

        recovery = analyzer._calculate_recovery_time(
            aerobic_effect, anaerobic_effect, duration_s, avg_heart_rate, max_hr
        )

        assert 6 <= recovery <= 72

    def test_get_training_effect(self, analyzer):
        """测试训练效果评估"""
        heart_rate_data = [140] * 600 + [150] * 600 + [160] * 600
        duration_s = 1800
        age = 30

        result = analyzer.get_training_effect(heart_rate_data, duration_s, age)

        assert "aerobic_effect" in result
        assert "anaerobic_effect" in result
        assert "recovery_time_hours" in result
        assert "hr_zones" in result
        assert "zone_time" in result
        assert "avg_heart_rate" in result
        assert 1.0 <= result["aerobic_effect"] <= 5.0
        assert 1.0 <= result["anaerobic_effect"] <= 5.0

    def test_get_training_effect_with_avg_hr(self, analyzer):
        """测试提供平均心率的训练效果"""
        heart_rate_data = [140] * 600 + [150] * 600 + [160] * 600
        duration_s = 1800
        age = 30
        avg_heart_rate = 150

        result = analyzer.get_training_effect(
            heart_rate_data, duration_s, age, avg_heart_rate
        )

        assert result["avg_heart_rate"] == 150

    def test_get_training_effect_invalid_duration(self, analyzer):
        """测试无效时长"""
        heart_rate_data = [140, 145, 150]

        with pytest.raises(ValueError, match="训练时长必须为正数"):
            analyzer.get_training_effect(heart_rate_data, 0, 30)

    def test_get_training_effect_invalid_age(self, analyzer):
        """测试无效年龄"""
        heart_rate_data = [140, 145, 150]

        with pytest.raises(ValueError, match="年龄必须在1-120之间"):
            analyzer.get_training_effect(heart_rate_data, 1800, 0)

    def test_get_training_effect_empty_hr(self, analyzer):
        """测试空心率数据"""
        with pytest.raises(ValueError, match="心率数据不能为空"):
            analyzer.get_training_effect([], 1800, 30)

    def test_get_heart_rate_zones(self, analyzer, mock_storage):
        """测试心率区间分布"""
        mock_storage.read_parquet.return_value = pl.LazyFrame(
            {
                "timestamp": ["2024-01-01", "2024-01-02"],
                "session_avg_heart_rate": [150, 160],
                "session_total_timer_time": [3600, 4200],
            }
        )

        result = analyzer.get_heart_rate_zones(age=30)

        assert "max_hr" in result
        assert "zones" in result
        assert result["max_hr"] == 190

    def test_get_heart_rate_zones_invalid_age(self, analyzer):
        """测试无效年龄"""
        with pytest.raises(ValueError, match="年龄必须在 1-120 范围内"):
            analyzer.get_heart_rate_zones(age=0)

    def test_get_heart_rate_zones_empty_data(self, analyzer, mock_storage):
        """测试空数据的心率区间"""
        mock_storage.read_parquet.return_value = pl.LazyFrame(
            {
                "timestamp": [],
                "session_avg_heart_rate": [],
                "session_total_timer_time": [],
            }
        )

        result = analyzer.get_heart_rate_zones(age=30)

        assert result["max_hr"] == 190
        assert result["activities_count"] == 0

    def test_hr_drift_assessment_positive(self, analyzer):
        """测试正向心率漂移评估"""
        heart_rate = [140, 145, 150, 155, 160, 165, 170, 175, 180, 185]
        pace = [5.5, 5.4, 5.3, 5.2, 5.1, 5.0, 4.9, 4.8, 4.7, 4.6]

        result = analyzer.analyze_hr_drift(heart_rate, pace)

        assert hasattr(result, "assessment")
        assert result.drift > 0

    def test_hr_drift_assessment_negative(self, analyzer):
        """测试负向心率漂移评估"""
        heart_rate = [180, 175, 170, 165, 160, 155, 150, 145, 140, 135]
        pace = [4.6, 4.7, 4.8, 4.9, 5.0, 5.1, 5.2, 5.3, 5.4, 5.5]

        result = analyzer.analyze_hr_drift(heart_rate, pace)

        assert hasattr(result, "assessment")
        assert result.drift < 0

    def test_hr_drift_consistency(self, analyzer):
        """测试心率漂移计算一致性"""
        heart_rate = [140, 142, 145, 148, 150, 152, 155, 158, 160, 162]
        pace = [5.5, 5.4, 5.3, 5.2, 5.1, 5.0, 4.9, 4.8, 4.7, 4.6]

        result_list = analyzer.analyze_hr_drift(heart_rate, pace)

        hr_series = pl.Series(heart_rate)
        pace_series = pl.Series(pace)
        result_vectorized = analyzer.analyze_hr_drift_vectorized(hr_series, pace_series)

        assert abs(result_list.drift - result_vectorized["drift"]) < 1.0

    def test_calculate_zones_from_avg_hr(self, analyzer):
        """测试从平均心率估算区间"""
        df = pl.DataFrame(
            {
                "session_avg_heart_rate": [100, 120, 140, 160, 180],
                "session_total_timer_time": [3600, 3600, 3600, 3600, 3600],
            }
        )

        max_hr = 190
        zone_boundaries = {
            "Z1": (0.50, 0.60, "恢复区"),
            "Z2": (0.60, 0.70, "有氧区"),
            "Z3": (0.70, 0.80, "节奏区"),
            "Z4": (0.80, 0.90, "阈值区"),
            "Z5": (0.90, 1.00, "无氧区"),
        }

        result = analyzer._calculate_zones_from_avg_hr(df, max_hr, zone_boundaries)

        assert "max_hr" in result
        assert "zones" in result
        assert len(result["zones"]) == 5
