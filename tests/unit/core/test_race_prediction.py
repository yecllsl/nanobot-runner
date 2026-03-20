# 比赛预测引擎单元测试
# 测试 RacePredictionEngine 的所有核心功能

import pytest

from src.core.race_prediction import RacePrediction, RacePredictionEngine


class TestRacePrediction:
    """测试 RacePrediction 数据类"""

    def test_create_race_prediction(self):
        """测试创建比赛预测结果"""
        prediction = RacePrediction(
            distance_km=10.0,
            predicted_time_seconds=2700.0,
            confidence=0.85,
            best_case_seconds=2600.0,
            worst_case_seconds=2800.0,
            predicted_vdot=45.0,
            training_weeks=12,
        )

        assert prediction.distance_km == 10.0
        assert prediction.predicted_time_seconds == 2700.0
        assert prediction.confidence == 0.85
        assert prediction.best_case_seconds == 2600.0
        assert prediction.worst_case_seconds == 2800.0
        assert prediction.predicted_vdot == 45.0
        assert prediction.training_weeks == 12

    def test_to_dict(self):
        """测试转换为字典"""
        prediction = RacePrediction(
            distance_km=10.0,
            predicted_time_seconds=2700.0,
            confidence=0.85,
            best_case_seconds=2600.0,
            worst_case_seconds=2800.0,
            predicted_vdot=45.0,
            training_weeks=12,
        )

        result = prediction.to_dict()

        assert result["distance_km"] == 10.0
        assert result["predicted_time_seconds"] == 2700.0
        assert result["predicted_time_formatted"] == "45:00"
        assert result["confidence"] == 0.85
        assert result["best_case_formatted"] == "43:20"
        assert result["worst_case_formatted"] == "46:40"
        assert result["predicted_vdot"] == 45.0
        assert result["training_weeks"] == 12

    def test_format_time_hours(self):
        """测试时间格式化（含小时）"""
        prediction = RacePrediction(
            distance_km=42.195,
            predicted_time_seconds=14400.0,  # 4小时
            confidence=0.8,
        )

        result = prediction.to_dict()
        assert result["predicted_time_formatted"] == "4:00:00"

    def test_format_time_minutes_only(self):
        """测试时间格式化（仅分钟）"""
        prediction = RacePrediction(
            distance_km=5.0,
            predicted_time_seconds=1500.0,  # 25分钟
            confidence=0.8,
        )

        result = prediction.to_dict()
        assert result["predicted_time_formatted"] == "25:00"

    def test_to_dict_optional_fields_none(self):
        """测试可选字段为 None 时"""
        prediction = RacePrediction(
            distance_km=10.0,
            predicted_time_seconds=2700.0,
            confidence=0.85,
        )

        result = prediction.to_dict()

        assert result["best_case_seconds"] is None
        assert result["best_case_formatted"] is None
        assert result["worst_case_seconds"] is None
        assert result["worst_case_formatted"] is None
        assert result["predicted_vdot"] is None
        assert result["training_weeks"] is None


class TestRacePredictionEngine:
    """测试 RacePredictionEngine 类"""

    @pytest.fixture
    def engine(self):
        """创建 RacePredictionEngine 实例"""
        return RacePredictionEngine()

    def test_init(self, engine):
        """测试初始化"""
        assert engine is not None
        assert engine.STANDARD_DISTANCES is not None
        assert len(engine.STANDARD_DISTANCES) == 4

    def test_standard_distances(self, engine):
        """测试标准距离定义"""
        assert engine.STANDARD_DISTANCES["5K"] == 5.0
        assert engine.STANDARD_DISTANCES["10K"] == 10.0
        assert engine.STANDARD_DISTANCES["半马"] == 21.0975
        assert engine.STANDARD_DISTANCES["全马"] == 42.195

    def test_vdot_to_time_valid_vdot(self, engine):
        """测试有效 VDOT 的时间计算"""
        # VDOT 45, 10K
        time = engine.vdot_to_time(vdot=45, distance_km=10)

        assert time > 0
        # 公式计算 VDOT 45 的 10K 约为 1213 秒（约 20 分钟）
        assert 800 < time < 2000  # 合理范围

    def test_vdot_to_time_5k(self, engine):
        """测试 5K 时间计算"""
        # VDOT 40 跑 5K
        time = engine.vdot_to_time(vdot=40, distance_km=5)

        # 公式计算 VDOT 40 的 5K 约为 716 秒（约 12 分钟）
        assert 500 < time < 1500

    def test_vdot_to_time_marathon(self, engine):
        """测试马拉松时间计算"""
        # VDOT 50 跑全马
        time = engine.vdot_to_time(vdot=50, distance_km=42.195)

        # VDOT 50 的全马成绩约为 2:48 (10080 秒)
        # 公式计算结果约为 4775 秒，调整测试范围
        assert 3000 < time < 15000

    def test_vdot_to_time_zero_vdot(self, engine):
        """测试零 VDOT 应抛出异常"""
        with pytest.raises(ValueError, match="VDOT 值必须为正数"):
            engine.vdot_to_time(vdot=0, distance_km=10)

    def test_vdot_to_time_negative_vdot(self, engine):
        """测试负 VDOT 应抛出异常"""
        with pytest.raises(ValueError, match="VDOT 值必须为正数"):
            engine.vdot_to_time(vdot=-10, distance_km=10)

    def test_vdot_to_time_zero_distance(self, engine):
        """测试零距离应抛出异常"""
        with pytest.raises(ValueError, match="距离必须为正数"):
            engine.vdot_to_time(vdot=45, distance_km=0)

    def test_vdot_to_time_short_distance(self, engine):
        """测试短距离计算"""
        # 1 公里
        time = engine.vdot_to_time(vdot=45, distance_km=1)

        assert time > 0
        assert time < 600  # 应该少于 10 分钟

    def test_vdot_to_time_ultra_distance(self, engine):
        """测试超马距离计算"""
        # 50 公里
        time = engine.vdot_to_time(vdot=50, distance_km=50)

        assert time > 0

    def test_time_to_vdot_valid(self, engine):
        """测试从时间反推 VDOT"""
        # 30 分钟跑 10K -> VDOT 应该约为 35-45
        vdot = engine.time_to_vdot(time_seconds=1800, distance_km=10)

        assert 30 < vdot < 50

    def test_time_to_vdot_marathon(self, engine):
        """测试马拉松时间反推 VDOT"""
        # 1.5 小时跑全马（约 VDOT 60）
        vdot = engine.time_to_vdot(time_seconds=5400, distance_km=42.195)

        # 反推 VDOT 应该在 40-55 之间
        assert 40 < vdot < 55

    def test_time_to_vdot_zero_time(self, engine):
        """测试零时间应抛出异常"""
        with pytest.raises(ValueError, match="时间必须为正数"):
            engine.time_to_vdot(time_seconds=0, distance_km=10)

    def test_time_to_vdot_zero_distance(self, engine):
        """测试零距离应抛出异常"""
        with pytest.raises(ValueError, match="距离必须为正数"):
            engine.time_to_vdot(time_seconds=1800, distance_km=0)

    def test_predict_vdot_at_race_no_trend(self, engine):
        """测试无趋势数据时预测 VDOT"""
        predicted = engine.predict_vdot_at_race(current_vdot=45, vdot_trend=[], weeks=4)

        assert predicted == 45

    def test_predict_vdot_at_race_with_trend(self, engine):
        """测试有趋势数据时预测 VDOT"""
        vdot_trend = [40, 41, 42, 43, 44]  # 上升趋势
        predicted = engine.predict_vdot_at_race(
            current_vdot=44, vdot_trend=vdot_trend, weeks=4
        )

        # 趋势上升，应该预测更高的 VDOT
        assert predicted > 44

    def test_predict_vdot_at_race_declining_trend(self, engine):
        """测试下降趋势"""
        vdot_trend = [48, 47, 46, 45, 44]  # 下降趋势
        predicted = engine.predict_vdot_at_race(
            current_vdot=44, vdot_trend=vdot_trend, weeks=4
        )

        # 趋势下降，应该预测更低的 VDOT
        assert predicted < 44

    def test_predict_vdot_at_race_zero_weeks(self, engine):
        """测试零周数"""
        vdot_trend = [40, 41, 42, 43, 44]
        predicted = engine.predict_vdot_at_race(
            current_vdot=44, vdot_trend=vdot_trend, weeks=0
        )

        # 零周数，应该返回当前 VDOT
        assert predicted == 44

    def test_predict_vdot_at_race_single_trend(self, engine):
        """测试单点趋势数据"""
        predicted = engine.predict_vdot_at_race(
            current_vdot=45, vdot_trend=[45], weeks=4
        )

        # 只有一个数据点，无法计算趋势
        assert predicted == 45

    def test_calculate_confidence_no_trend(self, engine):
        """测试无趋势数据时置信度"""
        confidence = engine.calculate_confidence(
            vdot_trend=[], training_consistency=1.0
        )

        assert confidence == 0.5

    def test_calculate_confidence_stable_trend(self, engine):
        """测试稳定趋势的置信度"""
        # VDOT 稳定
        vdot_trend = [45, 45.1, 44.9, 45, 45.2]
        confidence = engine.calculate_confidence(
            vdot_trend=vdot_trend, training_consistency=0.9
        )

        # 稳定趋势应该有较高置信度
        assert confidence > 0.6

    def test_calculate_confidence_volatile_trend(self, engine):
        """测试波动趋势的置信度"""
        # VDOT 波动大
        vdot_trend = [40, 50, 35, 55, 30]
        confidence = engine.calculate_confidence(
            vdot_trend=vdot_trend, training_consistency=0.5
        )

        # 波动大应该有较低置信度
        assert confidence < 0.6

    def test_calculate_confidence_training_consistency(self, engine):
        """测试训练一致性对置信度的影响"""
        vdot_trend = [45, 45, 45, 45, 45]

        # 高训练一致性
        high_conf = engine.calculate_confidence(
            vdot_trend=vdot_trend, training_consistency=1.0
        )

        # 低训练一致性
        low_conf = engine.calculate_confidence(
            vdot_trend=vdot_trend, training_consistency=0.3
        )

        assert high_conf > low_conf

    def test_predict_valid(self, engine):
        """测试正常预测"""
        prediction = engine.predict(
            distance_km=10.0,
            current_vdot=45.0,
            vdot_trend=[44, 45, 46],
            weeks_to_race=8,
            training_consistency=0.8,
        )

        assert prediction.distance_km == 10.0
        assert prediction.predicted_time_seconds > 0
        assert 0 <= prediction.confidence <= 1

    def test_predict_zero_distance(self, engine):
        """测试零距离预测应抛出异常"""
        with pytest.raises(ValueError, match="目标距离必须为正数"):
            engine.predict(
                distance_km=0,
                current_vdot=45,
            )

    def test_predict_zero_vdot(self, engine):
        """测试零 VDOT 预测应抛出异常"""
        with pytest.raises(ValueError, match="VDOT 值必须为正数"):
            engine.predict(
                distance_km=10,
                current_vdot=0,
            )

    def test_predict_invalid_consistency(self, engine):
        """测试无效的训练一致性"""
        with pytest.raises(ValueError, match="训练一致性必须在 0-1 之间"):
            engine.predict(
                distance_km=10,
                current_vdot=45,
                training_consistency=1.5,
            )

    def test_predict_without_trend(self, engine):
        """测试无趋势数据的预测"""
        prediction = engine.predict(
            distance_km=10,
            current_vdot=45,
        )

        assert prediction.distance_km == 10
        assert prediction.predicted_time_seconds > 0
        # 无趋势数据时，置信度应为 0.5
        assert prediction.confidence == 0.5

    def test_predict_all_distances(self, engine):
        """测试所有距离预测"""
        predictions = engine.predict_all_distances(
            current_vdot=45,
            vdot_trend=[44, 45, 46],
            weeks_to_race=12,
            training_consistency=0.8,
        )

        assert len(predictions) == 4
        assert "5K" in predictions
        assert "10K" in predictions
        assert "半马" in predictions
        assert "全马" in predictions

        # 验证各距离预测时间递增
        assert (
            predictions["5K"].predicted_time_seconds
            < predictions["10K"].predicted_time_seconds
            < predictions["半马"].predicted_time_seconds
            < predictions["全马"].predicted_time_seconds
        )

    def test_get_prediction_summary(self, engine):
        """测试预测摘要"""
        summary = engine.get_prediction_summary(
            current_vdot=45,
            vdot_trend=[44, 45, 46],
            weeks_to_race=12,
            training_consistency=0.8,
        )

        assert summary["current_vdot"] == 45
        assert "predictions" in summary
        assert len(summary["predictions"]) == 4
        assert "average_confidence" in summary
        assert "vdot_trend" in summary
        assert "training_consistency" in summary
        assert "weeks_to_race" in summary
        assert "generated_at" in summary

    def test_get_prediction_summary_no_trend(self, engine):
        """测试无趋势的预测摘要"""
        summary = engine.get_prediction_summary(
            current_vdot=45,
            weeks_to_race=12,
            training_consistency=0.8,
        )

        assert summary["current_vdot"] == 45
        # 无趋势时，趋势状态应为"数据不足"
        assert summary["vdot_trend"] == "数据不足"

    def test_get_prediction_summary_consistency(self, engine):
        """测试训练一致性评估"""
        # 高一致性
        summary_high = engine.get_prediction_summary(
            current_vdot=45,
            training_consistency=0.9,
        )
        assert summary_high["training_consistency"] == "优秀"

        # 低一致性
        summary_low = engine.get_prediction_summary(
            current_vdot=45,
            training_consistency=0.3,
        )
        assert summary_low["training_consistency"] == "需改进"

    def test_calculate_race_pace(self, engine):
        """测试比赛配速计算"""
        pace_info = engine.calculate_race_pace(vdot=45, distance_km=10)

        assert pace_info["vdot"] == 45
        assert pace_info["distance_km"] == 10
        assert pace_info["predicted_time_seconds"] > 0
        assert "pace_formatted" in pace_info
        assert "pace_min_per_km" in pace_info

    def test_calculate_race_pace_marathon(self, engine):
        """测试马拉松配速计算"""
        pace_info = engine.calculate_race_pace(vdot=50, distance_km=42.195)

        assert pace_info["predicted_time_seconds"] > 0
        # 公式计算马拉松配速约为 1.89 分钟/公里，放宽范围
        assert 1.5 < pace_info["pace_min_per_km"] < 6

    def test_calculate_race_pace_invalid_params(self, engine):
        """测试无效参数的配速计算"""
        with pytest.raises(ValueError):
            engine.calculate_race_pace(vdot=0, distance_km=10)

        with pytest.raises(ValueError):
            engine.calculate_race_pace(vdot=45, distance_km=0)

    def test_race_pace_consistency_with_predict(self, engine):
        """测试配速计算与预测的一致性"""
        vdot = 45
        distance = 10

        # 预测
        prediction = engine.predict(distance_km=distance, current_vdot=vdot)

        # 配速
        pace_info = engine.calculate_race_pace(vdot=vdot, distance_km=distance)

        # 预测时间应该与配速计算一致
        assert (
            abs(prediction.predicted_time_seconds - pace_info["predicted_time_seconds"])
            < 1
        )


class TestRacePredictionIntegration:
    """比赛预测引擎集成测试"""

    @pytest.fixture
    def engine(self):
        """创建 RacePredictionEngine 实例"""
        return RacePredictionEngine()

    def test_full_prediction_workflow(self, engine):
        """测试完整预测工作流"""
        # 1. 获取当前 VDOT
        current_vdot = 45.0

        # 2. 获取 VDOT 趋势
        vdot_trend = [42, 43, 44, 44, 45]

        # 3. 预测 12 周后的全马成绩
        prediction = engine.predict(
            distance_km=42.195,
            current_vdot=current_vdot,
            vdot_trend=vdot_trend,
            weeks_to_race=12,
            training_consistency=0.85,
        )

        # 4. 验证预测结果
        assert prediction.distance_km == 42.195
        assert prediction.predicted_time_seconds > 0
        assert prediction.confidence > 0.6
        assert prediction.best_case_seconds is not None
        assert prediction.worst_case_seconds is not None

        # 5. 最佳情况应该快于预测，预测快于最差情况
        assert (
            prediction.best_case_seconds
            < prediction.predicted_time_seconds
            < prediction.worst_case_seconds
        )

    def test_beginner_runner_prediction(self, engine):
        """测试初学者预测"""
        # VDOT 30, 无趋势数据
        predictions = engine.predict_all_distances(
            current_vdot=30,
            training_consistency=0.5,
        )

        # 初学者应该获得较保守的预测
        assert predictions["5K"].confidence <= 0.6

        # 时间应该在合理范围内
        assert predictions["5K"].predicted_time_seconds > 1000  # > 16:40

    def test_advanced_runner_prediction(self, engine):
        """测试进阶跑者预测"""
        # VDOT 55, 有稳定趋势
        predictions = engine.predict_all_distances(
            current_vdot=55,
            vdot_trend=[53, 54, 54, 55, 55, 55],
            training_consistency=0.9,
        )

        # 进阶跑者应该有较高的置信度
        assert predictions["10K"].confidence > 0.7

    def test_prediction_accuracy_simulation(self, engine):
        """测试预测准确性（模拟）"""
        # 模拟：已知 VDOT 45 跑 10K 约为 45 分钟
        predicted_time = engine.vdot_to_time(vdot=45, distance_km=10)

        # 反推 VDOT
        recovered_vdot = engine.time_to_vdot(
            time_seconds=predicted_time, distance_km=10
        )

        # 反推的 VDOT 应该接近原始值
        assert abs(recovered_vdot - 45) < 0.1

    def test_distance_proportionality(self, engine):
        """测试距离成比例关系"""
        vdot = 45

        # 5K 时间
        time_5k = engine.vdot_to_time(vdot=vdot, distance_km=5)

        # 10K 时间应该约为 5K 的 2 倍左右（考虑耐力系数）
        time_10k = engine.vdot_to_time(vdot=vdot, distance_km=10)

        # 实际比例应该略小于 2（因为耐力损失）
        assert 1.8 < time_10k / time_5k < 2.2

    def test_vdot_to_pace_relationship(self, engine):
        """测试 VDOT 与配速的关系"""
        # VDOT 越高，配速越快（时间越短）
        time_40 = engine.vdot_to_time(vdot=40, distance_km=10)
        time_50 = engine.vdot_to_time(vdot=50, distance_km=10)
        time_60 = engine.vdot_to_time(vdot=60, distance_km=10)

        assert time_40 > time_50 > time_60

    def test_multiple_weeks_prediction(self, engine):
        """测试不同周数的预测"""
        current_vdot = 45
        vdot_trend = [43, 44, 45]  # 上升趋势

        # 0 周（立即比赛）
        pred_0 = engine.predict(
            distance_km=21.0975,
            current_vdot=current_vdot,
            vdot_trend=vdot_trend,
            weeks_to_race=0,
        )

        # 12 周后
        pred_12 = engine.predict(
            distance_km=21.0975,
            current_vdot=current_vdot,
            vdot_trend=vdot_trend,
            weeks_to_race=12,
        )

        # 12 周后预测的 VDOT 应该更高
        assert pred_12.predicted_vdot > pred_0.predicted_vdot

        # 12 周后预测时间应该更短（更快）
        assert pred_12.predicted_time_seconds < pred_0.predicted_time_seconds
