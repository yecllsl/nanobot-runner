# RacePrediction单元测试
# 测试比赛预测引擎的核心功能

import pytest

from src.core.race_prediction import RacePrediction, RacePredictionEngine


class TestRacePredictionDataClass:
    """RacePrediction数据类测试"""

    def test_race_prediction_creation(self):
        """测试创建RacePrediction"""
        prediction = RacePrediction(
            distance_km=10.0,
            predicted_time_seconds=2400.0,
            confidence=0.85,
            best_case_seconds=2280.0,
            worst_case_seconds=2520.0,
            predicted_vdot=45.0,
            training_weeks=8,
        )

        assert prediction.distance_km == 10.0
        assert prediction.predicted_time_seconds == 2400.0
        assert prediction.confidence == 0.85
        assert prediction.best_case_seconds == 2280.0
        assert prediction.worst_case_seconds == 2520.0
        assert prediction.predicted_vdot == 45.0
        assert prediction.training_weeks == 8

    def test_race_prediction_to_dict(self):
        """测试转换为字典"""
        prediction = RacePrediction(
            distance_km=10.0,
            predicted_time_seconds=2400.0,
            confidence=0.85,
            best_case_seconds=2280.0,
            worst_case_seconds=2520.0,
            predicted_vdot=45.0,
            training_weeks=8,
        )

        result = prediction.to_dict()

        assert result["distance_km"] == 10.0
        assert result["predicted_time_seconds"] == 2400.0
        assert result["predicted_time_formatted"] == "40:00"
        assert result["confidence"] == 0.85
        assert result["best_case_seconds"] == 2280.0
        assert result["best_case_formatted"] == "38:00"
        assert result["worst_case_seconds"] == 2520.0
        assert result["worst_case_formatted"] == "42:00"
        assert result["predicted_vdot"] == 45.0
        assert result["training_weeks"] == 8

    def test_format_time_minutes_only(self):
        """测试时间格式化（仅分钟）"""
        assert RacePrediction._format_time(2400.0) == "40:00"
        assert RacePrediction._format_time(1800.0) == "30:00"

    def test_format_time_with_hours(self):
        """测试时间格式化（包含小时）"""
        assert RacePrediction._format_time(7200.0) == "2:00:00"
        assert RacePrediction._format_time(10800.0) == "3:00:00"


class TestVdotToTime:
    """vdot_to_time方法测试"""

    @pytest.fixture
    def engine(self):
        """创建RacePredictionEngine实例"""
        return RacePredictionEngine()

    def test_vdot_to_time_5k(self, engine):
        """测试5K距离的VDOT转换"""
        time_seconds = engine.vdot_to_time(40.0, 5.0)

        assert 600 < time_seconds < 900

    def test_vdot_to_time_10k(self, engine):
        """测试10K距离的VDOT转换"""
        time_seconds = engine.vdot_to_time(45.0, 10.0)

        assert 1000 < time_seconds < 1500

    def test_vdot_to_time_half_marathon(self, engine):
        """测试半马距离的VDOT转换"""
        time_seconds = engine.vdot_to_time(50.0, 21.0975)

        assert 2000 < time_seconds < 3000

    def test_vdot_to_time_full_marathon(self, engine):
        """测试全马距离的VDOT转换"""
        time_seconds = engine.vdot_to_time(45.0, 42.195)

        assert 5000 < time_seconds < 7000

    def test_vdot_to_time_invalid_vdot(self, engine):
        """测试无效VDOT值"""
        with pytest.raises(ValueError, match="VDOT 值必须为正数"):
            engine.vdot_to_time(0.0, 10.0)

    def test_vdot_to_time_invalid_distance(self, engine):
        """测试无效距离"""
        with pytest.raises(ValueError, match="距离必须为正数"):
            engine.vdot_to_time(40.0, 0.0)

    def test_vdot_to_time_ultra_distance(self, engine):
        """测试超马距离"""
        time_seconds = engine.vdot_to_time(40.0, 50.0)

        assert time_seconds > 0


class TestTimeToVdot:
    """time_to_vdot方法测试"""

    @pytest.fixture
    def engine(self):
        """创建RacePredictionEngine实例"""
        return RacePredictionEngine()

    def test_time_to_vdot_5k(self, engine):
        """测试5K时间反推VDOT"""
        vdot = engine.time_to_vdot(1340.0, 5.0)

        assert 25 < vdot < 35

    def test_time_to_vdot_10k(self, engine):
        """测试10K时间反推VDOT"""
        vdot = engine.time_to_vdot(2500.0, 10.0)

        assert 25 < vdot < 35

    def test_time_to_vdot_consistency(self, engine):
        """测试VDOT转换一致性"""
        original_vdot = 45.0
        distance = 10.0

        time_seconds = engine.vdot_to_time(original_vdot, distance)
        calculated_vdot = engine.time_to_vdot(time_seconds, distance)

        assert abs(calculated_vdot - original_vdot) < 1.0

    def test_time_to_vdot_invalid_time(self, engine):
        """测试无效时间"""
        with pytest.raises(ValueError, match="时间必须为正数"):
            engine.time_to_vdot(0.0, 10.0)

    def test_time_to_vdot_invalid_distance(self, engine):
        """测试无效距离"""
        with pytest.raises(ValueError, match="距离必须为正数"):
            engine.time_to_vdot(2400.0, 0.0)


class TestPredictVdotAtRace:
    """predict_vdot_at_race方法测试"""

    @pytest.fixture
    def engine(self):
        """创建RacePredictionEngine实例"""
        return RacePredictionEngine()

    def test_predict_vdot_no_trend(self, engine):
        """测试无趋势数据的VDOT预测"""
        predicted = engine.predict_vdot_at_race(45.0, [], weeks=4)

        assert predicted == 45.0

    def test_predict_vdot_with_trend(self, engine):
        """测试有趋势数据的VDOT预测"""
        vdot_trend = [42.0, 43.0, 44.0, 45.0]
        predicted = engine.predict_vdot_at_race(45.0, vdot_trend, weeks=4)

        assert predicted > 45.0

    def test_predict_vdot_invalid_current(self, engine):
        """测试无效当前VDOT"""
        with pytest.raises(ValueError, match="当前 VDOT 值必须为正数"):
            engine.predict_vdot_at_race(0.0, [40.0, 41.0])


class TestCalculateConfidence:
    """calculate_confidence方法测试"""

    @pytest.fixture
    def engine(self):
        """创建RacePredictionEngine实例"""
        return RacePredictionEngine()

    def test_calculate_confidence_no_trend(self, engine):
        """测试无趋势数据的置信度"""
        confidence = engine.calculate_confidence([], training_consistency=1.0)

        assert confidence == 0.5

    def test_calculate_confidence_stable_trend(self, engine):
        """测试稳定趋势的置信度"""
        vdot_trend = [45.0, 45.1, 45.0, 45.1]
        confidence = engine.calculate_confidence(vdot_trend, training_consistency=0.9)

        assert confidence > 0.8

    def test_calculate_confidence_unstable_trend(self, engine):
        """测试不稳定趋势的置信度"""
        vdot_trend = [40.0, 45.0, 42.0, 48.0]
        confidence = engine.calculate_confidence(vdot_trend, training_consistency=0.6)

        assert confidence < 0.8


class TestPredict:
    """predict方法测试"""

    @pytest.fixture
    def engine(self):
        """创建RacePredictionEngine实例"""
        return RacePredictionEngine()

    def test_predict_basic(self, engine):
        """测试基本预测"""
        prediction = engine.predict(
            distance_km=10.0,
            current_vdot=45.0,
            weeks_to_race=0,
        )

        assert prediction.distance_km == 10.0
        assert prediction.predicted_time_seconds > 0
        assert 0 <= prediction.confidence <= 1
        assert prediction.best_case_seconds is not None
        assert prediction.worst_case_seconds is not None

    def test_predict_with_trend(self, engine):
        """测试带趋势的预测"""
        vdot_trend = [42.0, 43.0, 44.0, 45.0]
        prediction = engine.predict(
            distance_km=10.0,
            current_vdot=45.0,
            vdot_trend=vdot_trend,
            weeks_to_race=4,
            training_consistency=0.8,
        )

        assert prediction.predicted_vdot > 45.0
        assert prediction.training_weeks == 4

    def test_predict_invalid_distance(self, engine):
        """测试无效距离"""
        with pytest.raises(ValueError, match="目标距离必须为正数"):
            engine.predict(distance_km=0.0, current_vdot=45.0)

    def test_predict_invalid_vdot(self, engine):
        """测试无效VDOT"""
        with pytest.raises(ValueError, match="VDOT 值必须为正数"):
            engine.predict(distance_km=10.0, current_vdot=0.0)

    def test_predict_invalid_consistency(self, engine):
        """测试无效训练一致性"""
        with pytest.raises(ValueError, match="训练一致性必须在 0-1 之间"):
            engine.predict(
                distance_km=10.0, current_vdot=45.0, training_consistency=1.5
            )


class TestPredictAllDistances:
    """predict_all_distances方法测试"""

    @pytest.fixture
    def engine(self):
        """创建RacePredictionEngine实例"""
        return RacePredictionEngine()

    def test_predict_all_distances(self, engine):
        """测试预测所有标准距离"""
        predictions = engine.predict_all_distances(current_vdot=45.0)

        assert "5K" in predictions
        assert "10K" in predictions
        assert "半马" in predictions
        assert "全马" in predictions

        assert predictions["5K"].distance_km == 5.0
        assert predictions["10K"].distance_km == 10.0
        assert predictions["半马"].distance_km == 21.0975
        assert predictions["全马"].distance_km == 42.195

    def test_predict_all_distances_with_trend(self, engine):
        """测试带趋势预测所有距离"""
        vdot_trend = [43.0, 44.0, 45.0]
        predictions = engine.predict_all_distances(
            current_vdot=45.0,
            vdot_trend=vdot_trend,
            weeks_to_race=8,
        )

        assert len(predictions) == 4


class TestGetPredictionSummary:
    """get_prediction_summary方法测试"""

    @pytest.fixture
    def engine(self):
        """创建RacePredictionEngine实例"""
        return RacePredictionEngine()

    def test_get_prediction_summary_basic(self, engine):
        """测试基本预测摘要"""
        summary = engine.get_prediction_summary(current_vdot=45.0)

        assert summary["current_vdot"] == 45.0
        assert "predictions" in summary
        assert "average_confidence" in summary
        assert "vdot_trend" in summary
        assert "training_consistency" in summary
        assert "weeks_to_race" in summary
        assert "generated_at" in summary

    def test_get_prediction_summary_with_trend(self, engine):
        """测试带趋势的预测摘要"""
        vdot_trend = [42.0, 43.0, 44.0, 45.0]
        summary = engine.get_prediction_summary(
            current_vdot=45.0,
            vdot_trend=vdot_trend,
            weeks_to_race=4,
            training_consistency=0.85,
        )

        assert summary["vdot_trend"] == "上升"
        assert summary["training_consistency"] == "优秀"
        assert summary["weeks_to_race"] == 4

    def test_get_prediction_summary_declining_trend(self, engine):
        """测试下降趋势"""
        vdot_trend = [48.0, 47.0, 46.0, 45.0]
        summary = engine.get_prediction_summary(
            current_vdot=45.0, vdot_trend=vdot_trend
        )

        assert summary["vdot_trend"] == "下降"

    def test_get_prediction_summary_stable_trend(self, engine):
        """测试稳定趋势"""
        vdot_trend = [44.5, 45.0, 44.8, 45.2]
        summary = engine.get_prediction_summary(
            current_vdot=45.0, vdot_trend=vdot_trend
        )

        assert summary["vdot_trend"] == "稳定"


class TestCalculateRacePace:
    """calculate_race_pace方法测试"""

    @pytest.fixture
    def engine(self):
        """创建RacePredictionEngine实例"""
        return RacePredictionEngine()

    def test_calculate_race_pace_10k(self, engine):
        """测试10K配速计算"""
        pace_info = engine.calculate_race_pace(vdot=45.0, distance_km=10.0)

        assert pace_info["vdot"] == 45.0
        assert pace_info["distance_km"] == 10.0
        assert pace_info["predicted_time_seconds"] > 0
        assert pace_info["pace_min_per_km"] > 0
        assert pace_info["pace_formatted"] is not None

    def test_calculate_race_pace_marathon(self, engine):
        """测试全马配速计算"""
        pace_info = engine.calculate_race_pace(vdot=45.0, distance_km=42.195)

        assert abs(pace_info["distance_km"] - 42.195) < 0.01
        assert pace_info["pace_sec_per_km"] > 0

    def test_calculate_race_pace_invalid_vdot(self, engine):
        """测试无效VDOT"""
        with pytest.raises(ValueError, match="VDOT 和距离必须为正数"):
            engine.calculate_race_pace(vdot=0.0, distance_km=10.0)

    def test_calculate_race_pace_invalid_distance(self, engine):
        """测试无效距离"""
        with pytest.raises(ValueError, match="VDOT 和距离必须为正数"):
            engine.calculate_race_pace(vdot=45.0, distance_km=0.0)


class TestIntegration:
    """集成测试"""

    @pytest.fixture
    def engine(self):
        """创建RacePredictionEngine实例"""
        return RacePredictionEngine()

    def test_full_prediction_workflow(self, engine):
        """测试完整预测流程"""
        vdot_trend = [42.0, 43.0, 44.0, 45.0]

        summary = engine.get_prediction_summary(
            current_vdot=45.0,
            vdot_trend=vdot_trend,
            weeks_to_race=8,
            training_consistency=0.85,
        )

        assert summary["current_vdot"] == 45.0
        assert len(summary["predictions"]) == 4
        assert summary["vdot_trend"] == "上升"
        assert summary["training_consistency"] == "优秀"

    def test_vdot_time_roundtrip(self, engine):
        """测试VDOT和时间的往返转换"""
        original_vdot = 50.0
        distance = 21.0975

        time_seconds = engine.vdot_to_time(original_vdot, distance)
        calculated_vdot = engine.time_to_vdot(time_seconds, distance)

        assert abs(calculated_vdot - original_vdot) < 0.5

    def test_prediction_consistency(self, engine):
        """测试预测一致性"""
        prediction1 = engine.predict(distance_km=10.0, current_vdot=45.0)
        prediction2 = engine.predict(distance_km=10.0, current_vdot=45.0)

        assert prediction1.predicted_time_seconds == prediction2.predicted_time_seconds
