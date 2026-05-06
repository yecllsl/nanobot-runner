# VizHandler 单元测试
# 测试可视化业务逻辑处理器，包含 BUG-002 修复验证

from unittest.mock import Mock

import pytest

from src.cli.handlers.viz_handler import VizHandler
from src.core.models import VdotTrendItem
from src.core.visualization.models import ChartData, DataSeries


@pytest.fixture
def mock_renderer():
    """创建 Mock 图表渲染器"""
    renderer = Mock()
    renderer.render_line_chart.return_value = "mock line chart"
    renderer.render_multi_line_chart.return_value = "mock multi line chart"
    renderer.render_stacked_bar_chart.return_value = "mock stacked bar chart"
    return renderer


@pytest.fixture
def mock_analytics():
    """创建 Mock 分析引擎"""
    return Mock()


@pytest.fixture
def handler(mock_renderer, mock_analytics):
    """创建 VizHandler 实例"""
    return VizHandler(chart_renderer=mock_renderer, analytics=mock_analytics)


class TestConvertVdotToChartData:
    """测试 VDOT 趋势数据转换（含 BUG-002 修复验证）"""

    def test_single_item_per_day(self, handler):
        """测试每天一条记录的正常情况"""
        trend_data = [
            VdotTrendItem(
                date="2024-01-01", vdot=40.0, distance=5000.0, duration=1800.0
            ),
            VdotTrendItem(
                date="2024-01-02", vdot=41.0, distance=6000.0, duration=2100.0
            ),
            VdotTrendItem(
                date="2024-01-03", vdot=42.0, distance=7000.0, duration=2400.0
            ),
        ]

        result = handler._convert_vdot_to_chart_data(trend_data)

        assert isinstance(result, ChartData)
        assert len(result.series) == 1
        assert result.series[0].labels == ["2024-01-01", "2024-01-02", "2024-01-03"]
        assert result.series[0].values == [40.0, 41.0, 42.0]

    def test_duplicate_dates_aggregated(self, handler):
        """测试同一天多条记录按日期聚合去重（BUG-002 修复验证）"""
        trend_data = [
            VdotTrendItem(
                date="2024-01-01", vdot=40.0, distance=5000.0, duration=1800.0
            ),
            VdotTrendItem(
                date="2024-01-01", vdot=42.0, distance=8000.0, duration=2880.0
            ),
            VdotTrendItem(
                date="2024-01-02", vdot=41.0, distance=6000.0, duration=2100.0
            ),
            VdotTrendItem(
                date="2024-01-02", vdot=43.0, distance=9000.0, duration=3000.0
            ),
        ]

        result = handler._convert_vdot_to_chart_data(trend_data)

        assert len(result.series[0].labels) == 2
        assert result.series[0].labels == ["2024-01-01", "2024-01-02"]
        assert result.series[0].values == [41.0, 42.0]

    def test_empty_trend_data(self, handler):
        """测试空趋势数据"""
        result = handler._convert_vdot_to_chart_data([])

        assert isinstance(result, ChartData)
        assert len(result.series) == 1
        assert result.series[0].labels == []
        assert result.series[0].values == []

    def test_sorted_labels(self, handler):
        """测试日期标签按顺序排列"""
        trend_data = [
            VdotTrendItem(
                date="2024-01-03", vdot=42.0, distance=7000.0, duration=2400.0
            ),
            VdotTrendItem(
                date="2024-01-01", vdot=40.0, distance=5000.0, duration=1800.0
            ),
            VdotTrendItem(
                date="2024-01-02", vdot=41.0, distance=6000.0, duration=2100.0
            ),
        ]

        result = handler._convert_vdot_to_chart_data(trend_data)

        assert result.series[0].labels == ["2024-01-01", "2024-01-02", "2024-01-03"]


class TestHandleVdot:
    """测试 VDOT 图表处理"""

    def test_handle_vdot_no_data(self, handler, mock_analytics):
        """测试无 VDOT 数据时的提示"""
        mock_analytics.get_vdot_trend.return_value = []

        result = handler.handle_vdot(30)

        assert "暂无" in result

    def test_handle_vdot_with_data(self, handler, mock_analytics):
        """测试有 VDOT 数据时正常渲染"""
        mock_analytics.get_vdot_trend.return_value = [
            VdotTrendItem(
                date="2024-01-01", vdot=40.0, distance=5000.0, duration=1800.0
            ),
        ]

        result = handler.handle_vdot(30)

        assert result == "mock line chart"


class TestHandleLoad:
    """测试训练负荷图表处理"""

    def test_handle_load_no_data(self, handler, mock_analytics):
        """测试无训练负数据时的提示"""
        mock_analytics.get_training_load_trend.return_value = {
            "trend_data": [],
            "message": "暂无训练负荷数据",
        }

        result = handler.handle_load(30)

        assert "暂无" in result


class TestRenderWithFallback:
    """测试渲染降级策略"""

    def test_render_success(self, handler, mock_renderer):
        """测试正常渲染成功"""
        data = ChartData(
            title="Test",
            x_label="x",
            y_label="y",
            series=[DataSeries(name="S", labels=["a"], values=[1.0])],
        )

        result = handler._render_with_fallback(data, mock_renderer.render_line_chart)

        assert result == "mock line chart"

    def test_render_fallback_to_table(self, handler, mock_renderer):
        """测试渲染失败时降级为文字表格"""
        mock_renderer.render_line_chart.side_effect = Exception("render error")
        data = ChartData(
            title="Test",
            x_label="x",
            y_label="y",
            series=[DataSeries(name="S", labels=["a"], values=[1.0])],
        )

        result = handler._render_with_fallback(data, mock_renderer.render_line_chart)

        assert "Test" in result
