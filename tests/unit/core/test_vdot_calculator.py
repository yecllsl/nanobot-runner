# VDOT计算器单元测试
# 测试VDOT计算、比赛预测等功能

import polars as pl
import pytest

from src.core.vdot_calculator import VDOTCalculator


class TestVDOTCalculator:
    """VDOT计算器测试类"""

    @pytest.fixture
    def calculator(self):
        """创建VDOT计算器实例"""
        return VDOTCalculator()

    def test_calculate_vdot_5k(self, calculator):
        """测试5公里VDOT计算"""
        distance = 5000
        time_s = 1200
        vdot = calculator.calculate_vdot(distance, time_s)
        assert vdot > 0
        assert 50 <= vdot <= 70

    def test_calculate_vdot_10k(self, calculator):
        """测试10公里VDOT计算"""
        distance = 10000
        time_s = 2700
        vdot = calculator.calculate_vdot(distance, time_s)
        assert vdot > 0
        assert 50 <= vdot <= 70

    def test_calculate_vdot_half_marathon(self, calculator):
        """测试半马VDOT计算"""
        distance = 21097.5
        time_s = 6000
        vdot = calculator.calculate_vdot(distance, time_s)
        assert vdot > 0
        assert 50 <= vdot <= 70

    def test_calculate_vdot_marathon(self, calculator):
        """测试全马VDOT计算"""
        distance = 42195
        time_s = 12600
        vdot = calculator.calculate_vdot(distance, time_s)
        assert vdot > 0
        assert 50 <= vdot <= 70

    def test_calculate_vdot_zero_distance(self, calculator):
        """测试零距离"""
        vdot = calculator.calculate_vdot(0, 1200)
        assert vdot == 0.0

    def test_calculate_vdot_zero_time(self, calculator):
        """测试零时间"""
        vdot = calculator.calculate_vdot(5000, 0)
        assert vdot == 0.0

    def test_calculate_vdot_negative_distance(self, calculator):
        """测试负距离"""
        vdot = calculator.calculate_vdot(-5000, 1200)
        assert vdot == 0.0

    def test_calculate_vdot_negative_time(self, calculator):
        """测试负时间"""
        vdot = calculator.calculate_vdot(5000, -1200)
        assert vdot == 0.0

    def test_calculate_vdot_none_distance(self, calculator):
        """测试None距离"""
        vdot = calculator.calculate_vdot(None, 1200)
        assert vdot == 0.0

    def test_calculate_vdot_none_time(self, calculator):
        """测试None时间"""
        vdot = calculator.calculate_vdot(5000, None)
        assert vdot == 0.0

    def test_calculate_vdot_short_distance(self, calculator):
        """测试短距离（<1500m）不计算"""
        vdot = calculator.calculate_vdot(1400, 300)
        assert vdot == 0.0

    def test_calculate_vdot_exactly_1500m(self, calculator):
        """测试恰好1500m距离"""
        vdot = calculator.calculate_vdot(1500, 300)
        assert vdot > 0

    def test_calculate_vdot_batch(self, calculator):
        """测试批量VDOT计算"""
        df = pl.DataFrame(
            {
                "session_total_distance": [5000.0, 10000.0, 21097.5, 1400.0],
                "session_total_timer_time": [1200.0, 2700.0, 6000.0, 300.0],
            }
        )

        vdot_series = calculator.calculate_vdot_batch(df)

        assert len(vdot_series) == 4
        assert vdot_series[0] > 0
        assert vdot_series[1] > 0
        assert vdot_series[2] > 0
        assert vdot_series[3] == 0.0

    def test_calculate_vdot_batch_empty(self, calculator):
        """测试空DataFrame批量计算"""
        df = pl.DataFrame(
            {
                "session_total_distance": [],
                "session_total_timer_time": [],
            }
        )

        vdot_series = calculator.calculate_vdot_batch(df)
        assert len(vdot_series) == 0

    def test_calculate_vdot_batch_with_nulls(self, calculator):
        """测试包含null值的批量计算"""
        df = pl.DataFrame(
            {
                "session_total_distance": [5000.0, None, 10000.0],
                "session_total_timer_time": [1200.0, 2700.0, None],
            }
        )

        vdot_series = calculator.calculate_vdot_batch(df)

        assert len(vdot_series) == 3
        assert vdot_series[0] > 0
        assert vdot_series[1] == 0.0
        assert vdot_series[2] == 0.0

    def test_calculate_vdot_from_series(self, calculator):
        """测试从Series批量计算VDOT"""
        distance_series = pl.Series([5000.0, 10000.0, 21097.5])
        time_series = pl.Series([1200.0, 2700.0, 6000.0])

        vdot_series = calculator.calculate_vdot_from_series(
            distance_series, time_series
        )

        assert len(vdot_series) == 3
        assert all(vdot > 0 for vdot in vdot_series)

    def test_vdot_to_time(self, calculator):
        """测试根据VDOT预测用时"""
        vdot = 45.0
        distance_m = 5000

        time_s = calculator.vdot_to_time(vdot, distance_m)

        assert time_s > 0
        assert 1500 <= time_s <= 2000

    def test_vdot_to_time_invalid_vdot(self, calculator):
        """测试无效VDOT预测用时"""
        with pytest.raises(ValueError, match="VDOT和距离必须为正数"):
            calculator.vdot_to_time(0, 5000)

    def test_vdot_to_time_invalid_distance(self, calculator):
        """测试无效距离预测用时"""
        with pytest.raises(ValueError, match="VDOT和距离必须为正数"):
            calculator.vdot_to_time(45.0, 0)

    def test_vdot_to_time_negative_vdot(self, calculator):
        """测试负VDOT预测用时"""
        with pytest.raises(ValueError, match="VDOT和距离必须为正数"):
            calculator.vdot_to_time(-45.0, 5000)

    def test_vdot_to_time_negative_distance(self, calculator):
        """测试负距离预测用时"""
        with pytest.raises(ValueError, match="VDOT和距离必须为正数"):
            calculator.vdot_to_time(45.0, -5000)

    def test_vdot_to_time_batch(self, calculator):
        """测试批量预测用时"""
        vdot_series = pl.Series([45.0, 50.0, 40.0])
        distance_m = 5000

        time_series = calculator.vdot_to_time_batch(vdot_series, distance_m)

        assert len(time_series) == 3
        assert all(time > 0 for time in time_series)

    def test_get_race_predictions(self, calculator):
        """测试获取比赛预测"""
        vdot = 45.0

        predictions = calculator.get_race_predictions(vdot)

        assert "5K" in predictions
        assert "10K" in predictions
        assert "半马" in predictions
        assert "全马" in predictions

        assert predictions["5K"] > 0
        assert predictions["10K"] > predictions["5K"]
        assert predictions["半马"] > predictions["10K"]
        assert predictions["全马"] > predictions["半马"]

    def test_get_race_predictions_batch(self, calculator):
        """测试批量获取比赛预测"""
        vdot_series = pl.Series([45.0, 50.0, 40.0])

        predictions = calculator.get_race_predictions_batch(vdot_series)

        assert "5K" in predictions
        assert "10K" in predictions
        assert "半马" in predictions
        assert "全马" in predictions

        for distance in ["5K", "10K", "半马", "全马"]:
            assert len(predictions[distance]) == 3
            assert all(time > 0 for time in predictions[distance])

    def test_vdot_consistency(self, calculator):
        """测试VDOT计算的一致性"""
        distance = 5000
        time_s = 1200

        vdot = calculator.calculate_vdot(distance, time_s)

        predicted_time = calculator.vdot_to_time(vdot, distance)

        time_diff = abs(predicted_time - time_s)
        assert time_diff < 120

    def test_vdot_batch_consistency(self, calculator):
        """测试批量VDOT计算的一致性"""
        df = pl.DataFrame(
            {
                "session_total_distance": [5000.0, 10000.0, 21097.5],
                "session_total_timer_time": [1200.0, 2700.0, 6000.0],
            }
        )

        vdot_series = calculator.calculate_vdot_batch(df)

        for i in range(len(df)):
            single_vdot = calculator.calculate_vdot(
                df["session_total_distance"][i], df["session_total_timer_time"][i]
            )
            assert abs(vdot_series[i] - single_vdot) < 0.01

    def test_calculate_vdot_high_performance(self, calculator):
        """测试高水平跑者VDOT"""
        distance = 5000
        time_s = 900
        vdot = calculator.calculate_vdot(distance, time_s)
        assert vdot > 50

    def test_calculate_vdot_low_performance(self, calculator):
        """测试低水平跑者VDOT"""
        distance = 5000
        time_s = 2400
        vdot = calculator.calculate_vdot(distance, time_s)
        assert 20 <= vdot <= 40

    def test_calculate_vdot_very_slow(self, calculator):
        """测试极慢配速VDOT"""
        distance = 5000
        time_s = 3600
        vdot = calculator.calculate_vdot(distance, time_s)
        assert vdot >= 0
