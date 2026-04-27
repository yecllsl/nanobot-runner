# 天气+训练协同工具单元测试
# 验证GetWeatherTrainingAdviceTool的协同功能

import json
from unittest.mock import MagicMock

import pytest

from src.agents.tools import GetWeatherTrainingAdviceTool, RunnerTools


class TestGetWeatherTrainingAdviceTool:
    """天气+训练协同工具测试"""

    @pytest.fixture
    def mock_runner_tools(self) -> RunnerTools:
        """创建模拟的RunnerTools实例"""
        mock_context = MagicMock()
        mock_storage = MagicMock()
        mock_analytics = MagicMock()
        mock_profile_storage = MagicMock()

        # 配置模拟返回值
        mock_profile_storage.load_profile_json.return_value = None
        mock_storage.read_parquet.return_value = MagicMock()
        mock_analytics.get_running_summary.return_value = MagicMock(height=0)
        mock_analytics.get_training_load.return_value = {}

        mock_context.storage = mock_storage
        mock_context.analytics = mock_analytics
        mock_context.profile_storage = mock_profile_storage

        return RunnerTools(context=mock_context)

    @pytest.fixture
    def tool(self, mock_runner_tools: RunnerTools) -> GetWeatherTrainingAdviceTool:
        """创建工具实例"""
        return GetWeatherTrainingAdviceTool(mock_runner_tools)

    # ========== 工具属性测试 ==========

    def test_tool_name(self, tool: GetWeatherTrainingAdviceTool) -> None:
        """测试工具名称"""
        assert tool.name == "get_weather_training_advice"

    def test_tool_description(self, tool: GetWeatherTrainingAdviceTool) -> None:
        """测试工具描述"""
        assert "天气+训练综合建议" in tool.description
        assert "今天适合跑步吗" in tool.description

    def test_tool_parameters(self, tool: GetWeatherTrainingAdviceTool) -> None:
        """测试工具参数定义"""
        params = tool.parameters

        assert params["type"] == "object"
        assert "temperature" in params["properties"]
        assert "humidity" in params["properties"]
        assert "weather" in params["properties"]
        assert "wind" in params["properties"]
        assert "precipitation" in params["properties"]
        assert "uv_index" in params["properties"]

        # 验证必填参数
        assert "temperature" in params["required"]
        assert "humidity" in params["required"]
        assert "weather" in params["required"]

    # ========== 工具执行测试 ==========

    @pytest.mark.asyncio
    async def test_execute_with_basic_params(
        self, tool: GetWeatherTrainingAdviceTool
    ) -> None:
        """测试基本参数执行"""
        result_json = await tool.execute(
            temperature=25.0,
            humidity=60.0,
            weather="晴",
        )

        result = json.loads(result_json)
        assert result["success"] is True
        assert "data" in result
        assert "advices" in result["data"]
        assert "total_count" in result["data"]
        assert "weather_impact" in result["data"]

    @pytest.mark.asyncio
    async def test_execute_with_all_params(
        self, tool: GetWeatherTrainingAdviceTool
    ) -> None:
        """测试完整参数执行"""
        result_json = await tool.execute(
            temperature=32.0,
            humidity=85.0,
            weather="晴",
            wind="7级大风",
            precipitation=70.0,
            uv_index=8.0,
        )

        result = json.loads(result_json)
        assert result["success"] is True
        assert result["data"]["total_count"] > 0

        # 验证建议包含多种类型
        advice_types = {a["advice_type"] for a in result["data"]["advices"]}
        assert len(advice_types) > 1  # 应该有多种类型的建议

    @pytest.mark.asyncio
    async def test_execute_high_temperature_scenario(
        self, tool: GetWeatherTrainingAdviceTool
    ) -> None:
        """测试高温场景"""
        result_json = await tool.execute(
            temperature=35.0,
            humidity=50.0,
            weather="晴",
        )

        result = json.loads(result_json)
        assert result["success"] is True

        # 验证包含高温相关建议
        high_temp_advices = [
            a for a in result["data"]["advices"] if "高温" in a["content"]
        ]
        assert len(high_temp_advices) > 0

        # 验证高温建议的优先级
        for advice in high_temp_advices:
            assert advice["priority"] == "high"

    @pytest.mark.asyncio
    async def test_execute_low_temperature_scenario(
        self, tool: GetWeatherTrainingAdviceTool
    ) -> None:
        """测试低温场景"""
        result_json = await tool.execute(
            temperature=2.0,
            humidity=40.0,
            weather="晴",
        )

        result = json.loads(result_json)
        assert result["success"] is True

        # 验证包含低温相关建议
        low_temp_advices = [
            a for a in result["data"]["advices"] if "低温" in a["content"]
        ]
        assert len(low_temp_advices) > 0

    @pytest.mark.asyncio
    async def test_execute_rain_scenario(
        self, tool: GetWeatherTrainingAdviceTool
    ) -> None:
        """测试降雨场景"""
        result_json = await tool.execute(
            temperature=20.0,
            humidity=80.0,
            weather="雨",
            precipitation=80.0,
        )

        result = json.loads(result_json)
        assert result["success"] is True

        # 验证包含降雨相关建议
        rain_advices = [
            a
            for a in result["data"]["advices"]
            if "降雨" in a["content"] or "雨" in a["content"]
        ]
        assert len(rain_advices) > 0

    @pytest.mark.asyncio
    async def test_execute_good_weather_scenario(
        self, tool: GetWeatherTrainingAdviceTool
    ) -> None:
        """测试良好天气场景"""
        result_json = await tool.execute(
            temperature=20.0,
            humidity=50.0,
            weather="晴",
        )

        result = json.loads(result_json)
        assert result["success"] is True

        # 验证包含良好天气建议
        good_weather_advices = [
            a for a in result["data"]["advices"] if "天气条件良好" in a["content"]
        ]
        assert len(good_weather_advices) > 0

    @pytest.mark.asyncio
    async def test_execute_weather_impact_analysis(
        self, tool: GetWeatherTrainingAdviceTool
    ) -> None:
        """测试天气影响分析"""
        result_json = await tool.execute(
            temperature=32.0,
            humidity=85.0,
            weather="晴",
        )

        result = json.loads(result_json)
        assert result["success"] is True

        # 验证天气影响分析
        weather_impact = result["data"]["weather_impact"]
        assert "impact_level" in weather_impact
        assert "impact_factors" in weather_impact
        assert "recommendation" in weather_impact

        # 验证高影响场景
        assert weather_impact["impact_level"] == "high"
        assert "高温" in weather_impact["impact_factors"]
        assert "高湿度" in weather_impact["impact_factors"]

    @pytest.mark.asyncio
    async def test_execute_formatted_advice(
        self, tool: GetWeatherTrainingAdviceTool
    ) -> None:
        """测试格式化建议输出"""
        result_json = await tool.execute(
            temperature=25.0,
            humidity=60.0,
            weather="晴",
        )

        result = json.loads(result_json)
        assert result["success"] is True

        # 验证格式化建议
        formatted_advice = result["data"]["formatted_advice"]
        assert "## 天气+训练综合建议" in formatted_advice

    @pytest.mark.asyncio
    async def test_execute_with_default_params(
        self, tool: GetWeatherTrainingAdviceTool
    ) -> None:
        """测试默认参数执行"""
        result_json = await tool.execute()

        result = json.loads(result_json)
        assert result["success"] is True

    # ========== RunnerTools方法测试 ==========

    def test_get_weather_training_advice_method(
        self, mock_runner_tools: RunnerTools
    ) -> None:
        """测试RunnerTools的get_weather_training_advice方法"""
        result = mock_runner_tools.get_weather_training_advice(
            temperature=25.0,
            humidity=60.0,
            weather="晴",
        )

        assert result["success"] is True
        assert "data" in result
        assert "advices" in result["data"]

    def test_build_training_data_summary(self, mock_runner_tools: RunnerTools) -> None:
        """测试训练数据摘要构建"""
        from src.core.tools.weather_training_coordinator import TrainingData

        # 模拟profile数据
        mock_profile = MagicMock()
        mock_profile.to_dict.return_value = {
            "estimated_vdot": 45.0,
            "weekly_avg_distance": 40.0,
        }

        training_data = mock_runner_tools._build_training_data_summary(mock_profile)

        assert isinstance(training_data, TrainingData)
        assert training_data.recent_distance_km >= 0
        assert training_data.recovery_status in ["良好", "一般", "疲劳"]

    # ========== 错误处理测试 ==========

    @pytest.mark.asyncio
    async def test_execute_with_invalid_params(
        self, tool: GetWeatherTrainingAdviceTool
    ) -> None:
        """测试无效参数处理"""
        # 工具应该能处理各种参数,不会因为参数无效而崩溃
        result_json = await tool.execute(
            temperature=-100.0,  # 极端温度
            humidity=150.0,  # 超出范围的湿度
            weather="",  # 空天气
        )

        result = json.loads(result_json)
        # 工具应该能正常返回结果,不会崩溃
        assert "success" in result

    @pytest.mark.asyncio
    async def test_execute_with_missing_optional_params(
        self, tool: GetWeatherTrainingAdviceTool
    ) -> None:
        """测试缺少可选参数"""
        result_json = await tool.execute(
            temperature=25.0,
            humidity=60.0,
            weather="晴",
            # 不提供可选参数
        )

        result = json.loads(result_json)
        assert result["success"] is True

    # ========== 多技能协同测试 ==========

    @pytest.mark.asyncio
    async def test_multi_skill_coordination(
        self, mock_runner_tools: RunnerTools
    ) -> None:
        """测试多技能协同能力

        验证工具能够同时整合天气数据和训练数据,
        生成综合建议,实现多技能协同。
        """
        tool = GetWeatherTrainingAdviceTool(mock_runner_tools)

        # 模拟天气数据
        weather_params = {
            "temperature": 30.0,
            "humidity": 75.0,
            "weather": "晴",
            "wind": "东南风3级",
            "precipitation": 20.0,
            "uv_index": 6.0,
        }

        # 执行工具
        result_json = await tool.execute(**weather_params)
        result = json.loads(result_json)

        # 验证协同能力
        assert result["success"] is True
        assert result["data"]["total_count"] > 0

        # 验证建议包含天气和训练两个维度的分析
        for advice in result["data"]["advices"]:
            assert "weather_impact" in advice
            assert "training_impact" in advice
            assert advice["weather_impact"] != ""
            assert advice["training_impact"] != ""

        # 验证天气影响分析
        weather_impact = result["data"]["weather_impact"]
        assert weather_impact["impact_level"] in ["low", "medium", "high"]
        assert isinstance(weather_impact["impact_factors"], list)

    @pytest.mark.asyncio
    async def test_coordination_with_training_data(
        self, mock_runner_tools: RunnerTools
    ) -> None:
        """测试与训练数据的协同

        验证工具能够结合训练数据生成个性化建议。
        """
        # 模拟训练数据
        mock_runner_tools.get_recent_runs = MagicMock(
            return_value=[{"distance_km": 10.0, "timestamp": "2026-04-20T08:00:00"}]
        )
        mock_runner_tools.get_vdot_trend = MagicMock(return_value=[{"vdot": 45.0}])
        mock_runner_tools.get_training_load = MagicMock(return_value={"ctl": 45.0})

        tool = GetWeatherTrainingAdviceTool(mock_runner_tools)

        # 执行工具
        result_json = await tool.execute(
            temperature=28.0,
            humidity=60.0,
            weather="晴",
        )
        result = json.loads(result_json)

        # 验证协同成功
        assert result["success"] is True
        assert result["data"]["total_count"] > 0
