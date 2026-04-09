# VDOTCalculator 单元测试

import polars as pl
import pytest

from src.core.vdot_calculator import VDOTCalculator


@pytest.fixture
def vdot_calculator() -> VDOTCalculator:
    """创建 VDOTCalculator 实例"""
    return VDOTCalculator()


class TestVDOTCalculator:
    """VDOTCalculator 测试类"""

    def test_calculate_vdot_5k(self, vdot_calculator: VDOTCalculator) -> None:
        """测试 5 公里 VDOT 计算"""
        distance_m = 5000
        time_s = 1200

        vdot = vdot_calculator.calculate_vdot(distance_m, time_s)

        assert 20 < vdot < 85

    def test_calculate_vdot_10k(self, vdot_calculator: VDOTCalculator) -> None:
        """测试 10 公里 VDOT 计算"""
        distance_m = 10000
        time_s = 2400

        vdot = vdot_calculator.calculate_vdot(distance_m, time_s)

        assert 20 < vdot < 85

    def test_calculate_vdot_marathon(self, vdot_calculator: VDOTCalculator) -> None:
        """测试马拉松 VDOT 计算"""
        distance_m = 42195
        time_s = 10800

        vdot = vdot_calculator.calculate_vdot(distance_m, time_s)

        assert 20 < vdot < 85

    def test_calculate_vdot_invalid_distance(
        self, vdot_calculator: VDOTCalculator
    ) -> None:
        """测试无效距离"""
        with pytest.raises(ValueError, match="距离和时间必须为正数"):
            vdot_calculator.calculate_vdot(-1000, 1200)

    def test_calculate_vdot_invalid_time(self, vdot_calculator: VDOTCalculator) -> None:
        """测试无效时间"""
        with pytest.raises(ValueError, match="距离和时间必须为正数"):
            vdot_calculator.calculate_vdot(5000, -1200)

    def test_calculate_vdot_short_distance(
        self, vdot_calculator: VDOTCalculator
    ) -> None:
        """测试短距离（<1500m）返回 0"""
        distance_m = 1000
        time_s = 300

        vdot = vdot_calculator.calculate_vdot(distance_m, time_s)

        assert vdot == 0.0

    def test_vdot_to_time_5k(self, vdot_calculator: VDOTCalculator) -> None:
        """测试 VDOT 转换为 5K 时间"""
        vdot = 50

        time_s = vdot_calculator.vdot_to_time(vdot, 5000)

        assert 1400 < time_s < 1600

    def test_vdot_to_time_marathon(self, vdot_calculator: VDOTCalculator) -> None:
        """测试 VDOT 转换为马拉松时间"""
        vdot = 50

        time_s = vdot_calculator.vdot_to_time(vdot, 42195)

        assert 10000 < time_s < 15000

    def test_vdot_to_time_invalid_vdot(self, vdot_calculator: VDOTCalculator) -> None:
        """测试无效 VDOT"""
        with pytest.raises(ValueError, match="VDOT和距离必须为正数"):
            vdot_calculator.vdot_to_time(-50, 5000)

    def test_vdot_to_time_invalid_distance(
        self, vdot_calculator: VDOTCalculator
    ) -> None:
        """测试无效距离"""
        with pytest.raises(ValueError, match="VDOT和距离必须为正数"):
            vdot_calculator.vdot_to_time(50, -5000)

    def test_get_race_predictions(self, vdot_calculator: VDOTCalculator) -> None:
        """测试比赛预测"""
        vdot = 50

        predictions = vdot_calculator.get_race_predictions(vdot)

        assert "5K" in predictions
        assert "10K" in predictions
        assert "半马" in predictions
        assert "全马" in predictions

        assert predictions["10K"] > predictions["5K"]
        assert predictions["半马"] > predictions["10K"]
        assert predictions["全马"] > predictions["半马"]

    def test_vdot_consistency(self, vdot_calculator: VDOTCalculator) -> None:
        """测试 VDOT 计算的一致性"""
        distance_m = 10000
        time_s = 2400

        vdot1 = vdot_calculator.calculate_vdot(distance_m, time_s)
        vdot2 = vdot_calculator.calculate_vdot(distance_m, time_s)

        assert vdot1 == vdot2

    def test_vdot_different_performances(self, vdot_calculator: VDOTCalculator) -> None:
        """测试不同表现的 VDOT 差异"""
        distance_m = 10000

        vdot_fast = vdot_calculator.calculate_vdot(distance_m, 1800)
        vdot_slow = vdot_calculator.calculate_vdot(distance_m, 3600)

        assert vdot_fast > vdot_slow


class TestVDOTCalculatorVectorized:
    """VDOT 向量化方法测试类"""

    def test_calculate_vdot_batch_basic(self, vdot_calculator: VDOTCalculator) -> None:
        """测试批量 VDOT 计算 - 基本场景"""
        df = pl.DataFrame(
            {
                "session_total_distance": [5000.0, 10000.0, 21097.5, 42195.0],
                "session_total_timer_time": [1200.0, 2400.0, 5400.0, 10800.0],
            }
        )

        vdot_series = vdot_calculator.calculate_vdot_batch(df)

        assert vdot_series.len() == 4
        assert all(20 < v < 85 for v in vdot_series)

    def test_calculate_vdot_batch_with_short_distance(
        self, vdot_calculator: VDOTCalculator
    ) -> None:
        """测试批量 VDOT 计算 - 包含短距离"""
        df = pl.DataFrame(
            {
                "session_total_distance": [1000.0, 5000.0, 10000.0],
                "session_total_timer_time": [300.0, 1200.0, 2400.0],
            }
        )

        vdot_series = vdot_calculator.calculate_vdot_batch(df)

        assert vdot_series.len() == 3
        assert vdot_series[0] == 0.0
        assert vdot_series[1] > 0
        assert vdot_series[2] > 0

    def test_calculate_vdot_batch_with_invalid_values(
        self, vdot_calculator: VDOTCalculator
    ) -> None:
        """测试批量 VDOT 计算 - 包含无效值"""
        df = pl.DataFrame(
            {
                "session_total_distance": [5000.0, -1000.0, 10000.0],
                "session_total_timer_time": [1200.0, 2400.0, -100.0],
            }
        )

        vdot_series = vdot_calculator.calculate_vdot_batch(df)

        assert vdot_series.len() == 3
        assert vdot_series[0] > 0
        assert vdot_series[1] == 0.0
        assert vdot_series[2] == 0.0

    def test_calculate_vdot_from_series(self, vdot_calculator: VDOTCalculator) -> None:
        """测试从 Series 计算 VDOT"""
        distance_series = pl.Series([5000.0, 10000.0, 15000.0])
        time_series = pl.Series([1200.0, 2400.0, 3600.0])

        vdot_series = vdot_calculator.calculate_vdot_from_series(
            distance_series, time_series
        )

        assert vdot_series.len() == 3
        assert all(v > 0 for v in vdot_series)

    def test_vdot_to_time_batch(self, vdot_calculator: VDOTCalculator) -> None:
        """测试批量预测用时"""
        vdot_series = pl.Series([45.0, 50.0, 55.0])
        distance_m = 5000

        time_series = vdot_calculator.vdot_to_time_batch(vdot_series, distance_m)

        assert time_series.len() == 3
        assert all(t > 0 for t in time_series)

    def test_vdot_to_time_batch_consistency(
        self, vdot_calculator: VDOTCalculator
    ) -> None:
        """测试批量预测与标量版本一致性"""
        vdot_values = [45.0, 50.0, 55.0]
        vdot_series = pl.Series(vdot_values)
        distance_m = 5000

        scalar_times = [
            vdot_calculator.vdot_to_time(v, distance_m) for v in vdot_values
        ]
        batch_times = vdot_calculator.vdot_to_time_batch(vdot_series, distance_m)

        for scalar, batch in zip(scalar_times, batch_times):
            assert abs(scalar - batch) < 0.1

    def test_get_race_predictions_batch(self, vdot_calculator: VDOTCalculator) -> None:
        """测试批量比赛预测"""
        vdot_series = pl.Series([45.0, 50.0, 55.0])

        predictions = vdot_calculator.get_race_predictions_batch(vdot_series)

        assert "5K" in predictions
        assert "10K" in predictions
        assert "半马" in predictions
        assert "全马" in predictions

        assert predictions["5K"].len() == 3
        assert predictions["10K"].len() == 3

    def test_vdot_batch_consistency_with_scalar(
        self, vdot_calculator: VDOTCalculator
    ) -> None:
        """测试批量计算与标量版本一致性"""
        distances = [5000.0, 10000.0, 21097.5]
        times = [1200.0, 2400.0, 5400.0]

        df = pl.DataFrame(
            {"session_total_distance": distances, "session_total_timer_time": times}
        )

        batch_vdots = vdot_calculator.calculate_vdot_batch(df)

        for i, (d, t) in enumerate(zip(distances, times)):
            scalar_vdot = vdot_calculator.calculate_vdot(d, t)
            assert abs(batch_vdots[i] - scalar_vdot) < 0.1

    def test_batch_race_prediction(self, vdot_calculator: VDOTCalculator) -> None:
        """测试批量比赛预测"""
        vdot_series = pl.Series([45.0, 50.0, 55.0])

        predictions = vdot_calculator.get_race_predictions_batch(vdot_series)

        assert "5K" in predictions
        assert "10K" in predictions
        assert "半马" in predictions
        assert "全马" in predictions

        assert predictions["5K"].len() == 3
        assert predictions["10K"].len() == 3

    def test_calculate_vdot_batch_empty(self, vdot_calculator: VDOTCalculator) -> None:
        """测试批量 VDOT 计算 - 空数据"""
        df = pl.DataFrame(
            {
                "session_total_distance": [],
                "session_total_timer_time": [],
            }
        )

        vdot_series = vdot_calculator.calculate_vdot_batch(df)

        assert vdot_series.len() == 0

    def test_calculate_vdot_batch_with_nulls(
        self, vdot_calculator: VDOTCalculator
    ) -> None:
        """测试批量 VDOT 计算 - 包含空值"""
        df = pl.DataFrame(
            {
                "session_total_distance": [5000.0, None, 10000.0],
                "session_total_timer_time": [1200.0, 2400.0, None],
            }
        )

        vdot_series = vdot_calculator.calculate_vdot_batch(df)

        assert vdot_series.len() == 3
        assert vdot_series[0] > 0
        assert vdot_series[1] == 0.0
        assert vdot_series[2] == 0.0
