# RacePredictionEngine 单元测试
# 测试比赛预测引擎功能

from unittest.mock import patch

import pytest

from src.core.calculators.race_prediction import RacePrediction, RacePredictionEngine


@pytest.fixture
def prediction_engine() -> RacePredictionEngine:
    """创建 RacePredictionEngine 实例"""
    return RacePredictionEngine()


class TestRacePrediction:
    """RacePrediction 数据类测试"""

    def test_to_dict_success(self) -> None:
        """测试转换为字典"""
        prediction = RacePrediction(
            distance_km=10.0,
            predicted_time_seconds=2400.0,
            confidence=0.85,
            best_case_seconds=2300.0,
            worst_case_seconds=2500.0,
            predicted_vdot=45.0,
            training_weeks=12,
        )

        result = prediction.to_dict()

        assert result["distance_km"] == 10.0
        assert result["predicted_time_seconds"] == 2400
        assert result["confidence"] == 0.85
        assert result["best_case_seconds"] == 2300
        assert result["worst_case_seconds"] == 2500
        assert result["predicted_vdot"] == 45.0
        assert result["training_weeks"] == 12

    def test_format_time_under_hour(self) -> None:
        """测试格式化时间（小于1小时）"""
        assert RacePrediction._format_time(2400) == "40:00"
        assert RacePrediction._format_time(3661) == "1:01:01"

    def test_format_time_over_hour(self) -> None:
        """测试格式化时间（大于1小时）"""
        assert RacePrediction._format_time(3600) == "1:00:00"
        assert RacePrediction._format_time(7325) == "2:02:05"

    def test_to_dict_with_none_values(self) -> None:
        """测试包含 None 值的转换"""
        prediction = RacePrediction(
            distance_km=5.0,
            predicted_time_seconds=1200.0,
            confidence=0.9,
        )

        result = prediction.to_dict()

        assert result["best_case_seconds"] is None
        assert result["worst_case_seconds"] is None
        assert result["predicted_vdot"] is None
        assert result["training_weeks"] is None


class TestRacePredictionEngine:
    """RacePredictionEngine 测试类"""

    def test_vdot_to_time_5k(self, prediction_engine: RacePredictionEngine) -> None:
        """测试 5K 预测时间"""
        time_40 = prediction_engine.vdot_to_time(40, 5.0)
        time_50 = prediction_engine.vdot_to_time(50, 5.0)

        assert time_40 > time_50
        assert 500 < time_40 < 2000
        assert 400 < time_50 < 1500

    def test_vdot_to_time_10k(self, prediction_engine: RacePredictionEngine) -> None:
        """测试 10K 预测时间"""
        time_45 = prediction_engine.vdot_to_time(45, 10.0)

        assert 1000 < time_45 < 4000

    def test_vdot_to_time_half_marathon(
        self, prediction_engine: RacePredictionEngine
    ) -> None:
        """测试半马预测时间"""
        time_50 = prediction_engine.vdot_to_time(50, 21.0975)

        assert 2000 < time_50 < 8000

    def test_vdot_to_time_full_marathon(
        self, prediction_engine: RacePredictionEngine
    ) -> None:
        """测试全马预测时间"""
        time_45 = prediction_engine.vdot_to_time(45, 42.195)

        assert 4000 < time_45 < 20000

    def test_vdot_to_time_invalid_vdot(
        self, prediction_engine: RacePredictionEngine
    ) -> None:
        """测试无效 VDOT 值"""
        with pytest.raises(ValueError, match="VDOT 值必须为正数"):
            prediction_engine.vdot_to_time(0, 10.0)

        with pytest.raises(ValueError, match="VDOT 值必须为正数"):
            prediction_engine.vdot_to_time(-5, 10.0)

    def test_vdot_to_time_invalid_distance(
        self, prediction_engine: RacePredictionEngine
    ) -> None:
        """测试无效距离"""
        with pytest.raises(ValueError, match="距离必须为正数"):
            prediction_engine.vdot_to_time(45, 0)

        with pytest.raises(ValueError, match="距离必须为正数"):
            prediction_engine.vdot_to_time(45, -10)

    def test_vdot_to_time_ultra_distance(
        self, prediction_engine: RacePredictionEngine
    ) -> None:
        """测试超马距离预测"""
        time_50k = prediction_engine.vdot_to_time(50, 50.0)

        assert time_50k > 0
        assert time_50k > prediction_engine.vdot_to_time(50, 42.195)

    def test_time_to_vdot_5k(self, prediction_engine: RacePredictionEngine) -> None:
        """测试根据 5K 时间反推 VDOT"""
        vdot = prediction_engine.time_to_vdot(1340, 5.0)

        assert 20 < vdot < 85

    def test_time_to_vdot_10k(self, prediction_engine: RacePredictionEngine) -> None:
        """测试根据 10K 时间反推 VDOT"""
        vdot = prediction_engine.time_to_vdot(2500, 10.0)

        assert 20 < vdot < 85

    def test_time_to_vdot_half_marathon(
        self, prediction_engine: RacePredictionEngine
    ) -> None:
        """测试根据半马时间反推 VDOT"""
        vdot = prediction_engine.time_to_vdot(5400, 21.0975)

        assert 20 < vdot < 85

    def test_time_to_vdot_invalid_time(
        self, prediction_engine: RacePredictionEngine
    ) -> None:
        """测试无效时间"""
        with pytest.raises(ValueError, match="时间必须为正数"):
            prediction_engine.time_to_vdot(0, 10.0)

        with pytest.raises(ValueError, match="时间必须为正数"):
            prediction_engine.time_to_vdot(-100, 10.0)

    def test_time_to_vdot_invalid_distance(
        self, prediction_engine: RacePredictionEngine
    ) -> None:
        """测试无效距离"""
        with pytest.raises(ValueError, match="距离必须为正数"):
            prediction_engine.time_to_vdot(2400, 0)

    def test_predict_vdot_at_race_no_trend(
        self, prediction_engine: RacePredictionEngine
    ) -> None:
        """测试无趋势时的 VDOT 预测"""
        current_vdot = 45.0
        vdot_trend: list[float] = []

        predicted = prediction_engine.predict_vdot_at_race(current_vdot, vdot_trend, 4)

        assert predicted == current_vdot

    def test_predict_vdot_at_race_with_trend(
        self, prediction_engine: RacePredictionEngine
    ) -> None:
        """测试有趋势时的 VDOT 预测"""
        current_vdot = 45.0
        vdot_trend = [42.0, 43.0, 44.0, 45.0]

        predicted = prediction_engine.predict_vdot_at_race(current_vdot, vdot_trend, 4)

        assert predicted >= current_vdot

    def test_predict_vdot_at_race_zero_weeks(
        self, prediction_engine: RacePredictionEngine
    ) -> None:
        """测试零周时的 VDOT 预测"""
        current_vdot = 45.0
        vdot_trend = [42.0, 43.0, 44.0]

        predicted = prediction_engine.predict_vdot_at_race(current_vdot, vdot_trend, 0)

        assert predicted == current_vdot

    def test_vdot_to_time_warning_for_out_of_range(
        self, prediction_engine: RacePredictionEngine
    ) -> None:
        """测试 VDOT 超出范围时的警告"""
        with patch("src.core.calculators.race_prediction.logger") as mock_logger:
            prediction_engine.vdot_to_time(10, 10.0)
            mock_logger.warning.assert_called_once()

            mock_logger.reset_mock()
            prediction_engine.vdot_to_time(90, 10.0)
            mock_logger.warning.assert_called_once()

    def test_predict_success(self, prediction_engine: RacePredictionEngine) -> None:
        """测试比赛预测成功"""
        prediction = prediction_engine.predict(
            current_vdot=45.0,
            distance_km=10.0,
            weeks_to_race=4,
        )

        assert prediction.distance_km == 10.0
        assert prediction.predicted_time_seconds > 0
        assert 0 < prediction.confidence <= 1
        assert prediction.predicted_vdot is not None

    def test_predict_with_trend(self, prediction_engine: RacePredictionEngine) -> None:
        """测试带趋势的比赛预测"""
        vdot_trend = [42.0, 43.0, 44.0, 45.0]
        prediction = prediction_engine.predict(
            current_vdot=45.0,
            distance_km=21.0975,
            weeks_to_race=8,
            vdot_trend=vdot_trend,
        )

        assert prediction.distance_km == 21.0975
        assert prediction.predicted_time_seconds > 0
        assert prediction.training_weeks == 8

    def test_predict_all_distances(
        self, prediction_engine: RacePredictionEngine
    ) -> None:
        """测试预测所有标准距离"""
        predictions = prediction_engine.predict_all_distances(current_vdot=45.0)

        assert "5K" in predictions
        assert "10K" in predictions
        assert "半马" in predictions
        assert "全马" in predictions

        assert predictions["5K"].distance_km == 5.0
        assert predictions["10K"].distance_km == 10.0
        assert predictions["半马"].distance_km == 21.0975
        assert predictions["全马"].distance_km == 42.195

    def test_predict_all_distances_with_trend(
        self, prediction_engine: RacePredictionEngine
    ) -> None:
        """测试带趋势预测所有标准距离"""
        vdot_trend = [43.0, 44.0, 45.0]
        predictions = prediction_engine.predict_all_distances(
            current_vdot=45.0, vdot_trend=vdot_trend, weeks_to_race=4
        )

        for pred in predictions.values():
            assert pred.training_weeks == 4

    def test_vdot_to_time_consistency(
        self, prediction_engine: RacePredictionEngine
    ) -> None:
        """测试 VDOT 转时间的反向一致性"""
        vdot = 45.0
        distance = 10.0

        time_seconds = prediction_engine.vdot_to_time(vdot, distance)
        calculated_vdot = prediction_engine.time_to_vdot(time_seconds, distance)

        assert abs(calculated_vdot - vdot) < 1.0

    def test_vdot_to_time_different_distances(
        self, prediction_engine: RacePredictionEngine
    ) -> None:
        """测试相同 VDOT 不同距离的时间预测"""
        vdot = 50.0

        time_5k = prediction_engine.vdot_to_time(vdot, 5.0)
        time_10k = prediction_engine.vdot_to_time(vdot, 10.0)
        time_half = prediction_engine.vdot_to_time(vdot, 21.0975)
        time_full = prediction_engine.vdot_to_time(vdot, 42.195)

        assert time_5k < time_10k < time_half < time_full

    def test_predict_confidence_range(
        self, prediction_engine: RacePredictionEngine
    ) -> None:
        """测试预测置信度范围"""
        prediction = prediction_engine.predict(
            current_vdot=45.0,
            distance_km=10.0,
            weeks_to_race=0,
        )

        assert 0 < prediction.confidence <= 1

        prediction_with_trend = prediction_engine.predict(
            current_vdot=45.0,
            distance_km=10.0,
            weeks_to_race=8,
            vdot_trend=[43.0, 44.0, 45.0],
        )

        assert prediction_with_trend.confidence >= prediction.confidence
