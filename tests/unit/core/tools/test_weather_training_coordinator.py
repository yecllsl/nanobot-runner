# 天气+训练协同模块单元测试
# 验证WeatherTrainingCoordinator的协同建议生成功能

import pytest

from src.core.tools.weather_training_coordinator import (
    TrainingData,
    WeatherData,
    WeatherTrainingAdvice,
    WeatherTrainingCoordinator,
)


class TestWeatherTrainingCoordinator:
    """天气+训练协同协调器测试"""

    @pytest.fixture
    def coordinator(self) -> WeatherTrainingCoordinator:
        """创建协调器实例"""
        return WeatherTrainingCoordinator()

    # ========== WeatherData 测试 ==========

    def test_weather_data_creation(self) -> None:
        """测试天气数据创建"""
        weather = WeatherData(
            temperature=25.0,
            humidity=60.0,
            weather="晴",
            wind="东南风3级",
            location="北京",
            precipitation=10.0,
            uv_index=5.0,
        )

        assert weather.temperature == 25.0
        assert weather.humidity == 60.0
        assert weather.weather == "晴"
        assert weather.wind == "东南风3级"
        assert weather.location == "北京"
        assert weather.precipitation == 10.0
        assert weather.uv_index == 5.0

    def test_weather_data_frozen(self) -> None:
        """测试天气数据不可变"""
        weather = WeatherData(temperature=25.0, humidity=60.0, weather="晴")

        with pytest.raises(AttributeError):
            weather.temperature = 30.0  # type: ignore

    # ========== TrainingData 测试 ==========

    def test_training_data_creation(self) -> None:
        """测试训练数据创建"""
        training = TrainingData(
            recent_distance_km=50.0,
            avg_vdot=45.0,
            training_load=40.0,
            recovery_status="良好",
            last_run_date="2026-04-20",
        )

        assert training.recent_distance_km == 50.0
        assert training.avg_vdot == 45.0
        assert training.training_load == 40.0
        assert training.recovery_status == "良好"
        assert training.last_run_date == "2026-04-20"

    def test_training_data_frozen(self) -> None:
        """测试训练数据不可变"""
        training = TrainingData(
            recent_distance_km=50.0,
            avg_vdot=45.0,
            training_load=40.0,
            recovery_status="良好",
            last_run_date="2026-04-20",
        )

        with pytest.raises(AttributeError):
            training.recent_distance_km = 60.0  # type: ignore

    # ========== WeatherTrainingAdvice 测试 ==========

    def test_advice_creation(self) -> None:
        """测试建议创建"""
        advice = WeatherTrainingAdvice(
            advice_type="training",
            content="高温天气,建议避开中午时段训练",
            priority="high",
            reason="当前温度32°C,超过30°C高温警戒线",
            weather_impact="高温会增加脱水和中暑风险",
            training_impact="心率会偏高,体感评分可能上升",
        )

        assert advice.advice_type == "training"
        assert advice.content == "高温天气,建议避开中午时段训练"
        assert advice.priority == "high"
        assert advice.reason == "当前温度32°C,超过30°C高温警戒线"

    def test_advice_frozen(self) -> None:
        """测试建议不可变"""
        advice = WeatherTrainingAdvice(
            advice_type="training",
            content="测试建议",
            priority="medium",
            reason="测试原因",
            weather_impact="测试天气影响",
            training_impact="测试训练影响",
        )

        with pytest.raises(AttributeError):
            advice.priority = "high"  # type: ignore

    # ========== generate_advice 测试 ==========

    def test_generate_advice_high_temperature(
        self, coordinator: WeatherTrainingCoordinator
    ) -> None:
        """测试高温天气建议生成"""
        weather = WeatherData(temperature=32.0, humidity=50.0, weather="晴")
        training = TrainingData(
            recent_distance_km=40.0,
            avg_vdot=45.0,
            training_load=40.0,
            recovery_status="良好",
            last_run_date="2026-04-20",
        )

        advices = coordinator.generate_advice(weather, training)

        # 应该生成高温相关建议
        assert len(advices) > 0
        high_temp_advices = [a for a in advices if "高温" in a.content]
        assert len(high_temp_advices) > 0

        # 验证高温建议的优先级
        for advice in high_temp_advices:
            assert advice.priority == "high"
            assert advice.advice_type in ["safety", "nutrition"]

    def test_generate_advice_low_temperature(
        self, coordinator: WeatherTrainingCoordinator
    ) -> None:
        """测试低温天气建议生成"""
        weather = WeatherData(temperature=3.0, humidity=40.0, weather="晴")
        training = TrainingData(
            recent_distance_km=40.0,
            avg_vdot=45.0,
            training_load=40.0,
            recovery_status="良好",
            last_run_date="2026-04-20",
        )

        advices = coordinator.generate_advice(weather, training)

        # 应该生成低温相关建议
        low_temp_advices = [a for a in advices if "低温" in a.content]
        assert len(low_temp_advices) > 0

        # 验证低温建议的优先级
        for advice in low_temp_advices:
            assert advice.priority == "high"
            assert advice.advice_type == "safety"

    def test_generate_advice_high_precipitation(
        self, coordinator: WeatherTrainingCoordinator
    ) -> None:
        """测试降雨天气建议生成"""
        weather = WeatherData(
            temperature=20.0, humidity=80.0, weather="雨", precipitation=70.0
        )
        training = TrainingData(
            recent_distance_km=40.0,
            avg_vdot=45.0,
            training_load=40.0,
            recovery_status="良好",
            last_run_date="2026-04-20",
        )

        advices = coordinator.generate_advice(weather, training)

        # 应该生成降雨相关建议
        rain_advices = [a for a in advices if "降雨" in a.content or "雨" in a.content]
        assert len(rain_advices) > 0

        # 验证降雨建议的优先级
        for advice in rain_advices:
            assert advice.priority == "medium"
            assert advice.advice_type == "training"

    def test_generate_advice_high_humidity(
        self, coordinator: WeatherTrainingCoordinator
    ) -> None:
        """测试高湿度天气建议生成"""
        weather = WeatherData(temperature=25.0, humidity=85.0, weather="阴")
        training = TrainingData(
            recent_distance_km=40.0,
            avg_vdot=45.0,
            training_load=40.0,
            recovery_status="良好",
            last_run_date="2026-04-20",
        )

        advices = coordinator.generate_advice(weather, training)

        # 应该生成高湿度相关建议
        humidity_advices = [a for a in advices if "湿度" in a.content]
        assert len(humidity_advices) > 0

        # 验证高湿度建议的优先级
        for advice in humidity_advices:
            assert advice.priority == "medium"

    def test_generate_advice_strong_wind(
        self, coordinator: WeatherTrainingCoordinator
    ) -> None:
        """测试强风天气建议生成"""
        weather = WeatherData(
            temperature=20.0, humidity=50.0, weather="晴", wind="7级大风"
        )
        training = TrainingData(
            recent_distance_km=40.0,
            avg_vdot=45.0,
            training_load=40.0,
            recovery_status="良好",
            last_run_date="2026-04-20",
        )

        advices = coordinator.generate_advice(weather, training)

        # 应该生成强风相关建议
        wind_advices = [a for a in advices if "风力" in a.content or "风" in a.content]
        assert len(wind_advices) > 0

        # 验证强风建议的优先级
        for advice in wind_advices:
            assert advice.priority == "medium"

    def test_generate_advice_high_uv_index(
        self, coordinator: WeatherTrainingCoordinator
    ) -> None:
        """测试高紫外线天气建议生成"""
        weather = WeatherData(
            temperature=25.0, humidity=50.0, weather="晴", uv_index=8.0
        )
        training = TrainingData(
            recent_distance_km=40.0,
            avg_vdot=45.0,
            training_load=40.0,
            recovery_status="良好",
            last_run_date="2026-04-20",
        )

        advices = coordinator.generate_advice(weather, training)

        # 应该生成紫外线相关建议
        uv_advices = [a for a in advices if "紫外线" in a.content]
        assert len(uv_advices) > 0

        # 验证紫外线建议的优先级
        for advice in uv_advices:
            assert advice.priority == "low"

    def test_generate_advice_high_volume_high_temp(
        self, coordinator: WeatherTrainingCoordinator
    ) -> None:
        """测试高跑量+高温组合建议"""
        weather = WeatherData(temperature=28.0, humidity=60.0, weather="晴")
        training = TrainingData(
            recent_distance_km=70.0,  # 高跑量
            avg_vdot=45.0,
            training_load=45.0,
            recovery_status="良好",
            last_run_date="2026-04-20",
        )

        advices = coordinator.generate_advice(weather, training)

        # 应该生成恢复相关建议
        recovery_advices = [a for a in advices if a.advice_type == "recovery"]
        assert len(recovery_advices) > 0

        # 验证恢复建议的优先级
        for advice in recovery_advices:
            assert advice.priority == "high"

    def test_generate_advice_high_load_high_temp(
        self, coordinator: WeatherTrainingCoordinator
    ) -> None:
        """测试高训练负荷+高温组合建议"""
        weather = WeatherData(temperature=30.0, humidity=60.0, weather="晴")
        training = TrainingData(
            recent_distance_km=50.0,
            avg_vdot=45.0,
            training_load=55.0,  # 高训练负荷
            recovery_status="良好",
            last_run_date="2026-04-20",
        )

        advices = coordinator.generate_advice(weather, training)

        # 应该生成训练调整建议
        training_advices = [
            a for a in advices if a.advice_type == "training" and "负荷" in a.reason
        ]
        assert len(training_advices) > 0

        # 验证训练建议的优先级
        for advice in training_advices:
            assert advice.priority == "high"

    def test_generate_advice_fatigue_bad_weather(
        self, coordinator: WeatherTrainingCoordinator
    ) -> None:
        """测试疲劳状态+恶劣天气组合建议"""
        weather = WeatherData(temperature=20.0, humidity=80.0, weather="雨")
        training = TrainingData(
            recent_distance_km=50.0,
            avg_vdot=45.0,
            training_load=55.0,
            recovery_status="疲劳",  # 疲劳状态
            last_run_date="2026-04-20",
        )

        advices = coordinator.generate_advice(weather, training)

        # 应该生成恢复建议
        recovery_advices = [a for a in advices if a.advice_type == "recovery"]
        assert len(recovery_advices) > 0

        # 验证恢复建议的优先级
        for advice in recovery_advices:
            assert advice.priority == "high"

    def test_generate_advice_good_weather(
        self, coordinator: WeatherTrainingCoordinator
    ) -> None:
        """测试良好天气建议生成"""
        weather = WeatherData(temperature=20.0, humidity=50.0, weather="晴")
        training = TrainingData(
            recent_distance_km=40.0,
            avg_vdot=45.0,
            training_load=35.0,
            recovery_status="良好",
            last_run_date="2026-04-20",
        )

        advices = coordinator.generate_advice(weather, training)

        # 应该生成默认建议
        assert len(advices) > 0
        assert any("天气条件良好" in a.content for a in advices)

    # ========== analyze_weather_impact 测试 ==========

    def test_analyze_weather_impact_high(
        self, coordinator: WeatherTrainingCoordinator
    ) -> None:
        """测试高影响天气分析"""
        weather = WeatherData(temperature=32.0, humidity=85.0, weather="晴")

        impact = coordinator.analyze_weather_impact(weather)

        assert impact["impact_level"] == "high"
        assert len(impact["impact_factors"]) > 0
        assert "高温" in impact["impact_factors"]
        assert "高湿度" in impact["impact_factors"]

    def test_analyze_weather_impact_medium(
        self, coordinator: WeatherTrainingCoordinator
    ) -> None:
        """测试中等影响天气分析"""
        weather = WeatherData(temperature=25.0, humidity=85.0, weather="阴")

        impact = coordinator.analyze_weather_impact(weather)

        assert impact["impact_level"] == "medium"
        assert "高湿度" in impact["impact_factors"]

    def test_analyze_weather_impact_low(
        self, coordinator: WeatherTrainingCoordinator
    ) -> None:
        """测试低影响天气分析"""
        weather = WeatherData(temperature=20.0, humidity=50.0, weather="晴")

        impact = coordinator.analyze_weather_impact(weather)

        assert impact["impact_level"] == "low"
        assert len(impact["impact_factors"]) == 0

    # ========== format_advice_for_display 测试 ==========

    def test_format_advice_for_display(
        self, coordinator: WeatherTrainingCoordinator
    ) -> None:
        """测试建议格式化显示"""
        advices = [
            WeatherTrainingAdvice(
                advice_type="safety",
                content="高温天气,建议避开中午时段训练",
                priority="high",
                reason="当前温度32°C",
                weather_impact="高温风险",
                training_impact="心率偏高",
            ),
            WeatherTrainingAdvice(
                advice_type="training",
                content="湿度较高,建议降低训练强度",
                priority="medium",
                reason="当前湿度85%",
                weather_impact="散热困难",
                training_impact="体感更累",
            ),
        ]

        formatted = coordinator.format_advice_for_display(advices)

        # 验证格式化输出包含关键信息
        assert "## 天气+训练综合建议" in formatted
        assert "高温天气,建议避开中午时段训练" in formatted
        assert "湿度较高,建议降低训练强度" in formatted
        assert "**类型**: safety" in formatted
        assert "**优先级**: high" in formatted
        assert "**原因**: 当前温度32°C" in formatted

    def test_format_advice_for_display_empty(
        self, coordinator: WeatherTrainingCoordinator
    ) -> None:
        """测试空建议格式化"""
        formatted = coordinator.format_advice_for_display([])
        assert formatted == "暂无训练建议"

    def test_format_advice_priority_order(
        self, coordinator: WeatherTrainingCoordinator
    ) -> None:
        """测试建议按优先级排序"""
        advices = [
            WeatherTrainingAdvice(
                advice_type="training",
                content="低优先级建议",
                priority="low",
                reason="测试",
                weather_impact="测试",
                training_impact="测试",
            ),
            WeatherTrainingAdvice(
                advice_type="safety",
                content="高优先级建议",
                priority="high",
                reason="测试",
                weather_impact="测试",
                training_impact="测试",
            ),
            WeatherTrainingAdvice(
                advice_type="training",
                content="中优先级建议",
                priority="medium",
                reason="测试",
                weather_impact="测试",
                training_impact="测试",
            ),
        ]

        formatted = coordinator.format_advice_for_display(advices)

        # 验证高优先级建议排在前面
        high_index = formatted.find("高优先级建议")
        medium_index = formatted.find("中优先级建议")
        low_index = formatted.find("低优先级建议")

        assert high_index < medium_index < low_index
