"""
IntentParser 单元测试
"""

import pytest

from src.core.exceptions import ValidationError
from src.core.models import IntentResult
from src.core.plan.intent_parser import IntentParser


class TestIntentParser:
    """IntentParser 测试类"""

    def setup_method(self):
        """每个测试方法前的设置"""
        self.parser = IntentParser()

    def test_parse_slash_command_create_plan(self):
        """测试解析创建计划的斜杠命令"""
        result = self.parser.parse("/create 准备参加半马，目标2小时完赛")

        assert isinstance(result, IntentResult)
        assert result.intent == IntentParser.INTENT_CREATE_PLAN
        assert result.confidence == 1.0
        assert result.input_type == "slash_command"
        assert "goal_distance_km" in result.parameters

    def test_parse_slash_command_query_plan(self):
        """测试解析查询计划的斜杠命令"""
        result = self.parser.parse("/query")

        assert isinstance(result, IntentResult)
        assert result.intent == IntentParser.INTENT_QUERY_PLAN
        assert result.confidence == 1.0
        assert result.input_type == "slash_command"

    def test_parse_natural_language_create_plan(self):
        """测试解析自然语言创建计划"""
        result = self.parser.parse("帮我制定一个半马训练计划")

        assert isinstance(result, IntentResult)
        assert result.intent == IntentParser.INTENT_CREATE_PLAN
        assert result.confidence > 0.5
        assert result.input_type == "natural_language"

    def test_parse_natural_language_query_plan(self):
        """测试解析自然语言查询计划"""
        result = self.parser.parse("查看我的训练计划")

        assert isinstance(result, IntentResult)
        assert result.intent == IntentParser.INTENT_QUERY_PLAN
        assert result.confidence > 0.5
        assert result.input_type == "natural_language"

    def test_parse_empty_input(self):
        """测试解析空输入"""
        with pytest.raises(ValidationError):
            self.parser.parse("")

    def test_parse_whitespace_input(self):
        """测试解析空白输入"""
        with pytest.raises(ValidationError):
            self.parser.parse("   ")

    def test_extract_distance_parameter(self):
        """测试提取距离参数"""
        result = self.parser.parse("帮我制定半马训练计划")
        assert result.intent == IntentParser.INTENT_CREATE_PLAN
        assert result.parameters.get("goal_distance_km") == 21.0975

        result = self.parser.parse("帮我生成全马训练计划")
        assert result.intent == IntentParser.INTENT_CREATE_PLAN
        assert result.parameters.get("goal_distance_km") == 42.195

        result = self.parser.parse("/create 10公里比赛")
        assert result.intent == IntentParser.INTENT_CREATE_PLAN
        assert result.parameters.get("goal_distance_km") == 10.0

    def test_extract_date_parameter(self):
        """测试提取日期参数"""
        result = self.parser.parse("制定训练计划，目标日期2026-05-01")
        assert "goal_date" in result.parameters

    def test_extract_time_parameter(self):
        """测试提取时间参数"""
        result = self.parser.parse("/create 目标完赛时间2:30:00")
        assert result.intent == IntentParser.INTENT_CREATE_PLAN
        assert "target_time" in result.parameters

    def test_unknown_command(self):
        """测试未知命令"""
        result = self.parser.parse("/unknown_command")

        assert isinstance(result, IntentResult)
        assert result.intent == IntentParser.INTENT_UNKNOWN
        assert result.confidence == 0.0
