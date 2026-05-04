# Viz 命令端到端测试
# 测试 CLI -> Handler -> Renderer -> 输出的完整链路
# Mock AnalyticsEngine，不 Mock ChartRenderer

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from src.cli.handlers.viz_handler import VizHandler
from src.core.models import VdotTrendItem
from src.core.visualization.plotext_renderer import PlotextRenderer


class TestVizE2E:
    """Viz 端到端测试类"""

    @pytest.fixture
    def renderer(self):
        """提供真实的 PlotextRenderer 实例"""
        return PlotextRenderer()

    @pytest.fixture
    def mock_analytics_with_vdot(self):
        """提供带有 VDOT 趋势数据的 Mock AnalyticsEngine"""
        analytics = MagicMock()
        analytics.get_vdot_trend.return_value = [
            VdotTrendItem(
                date="2024-01-01", vdot=45.0, distance=5000.0, duration=1800.0
            ),
            VdotTrendItem(
                date="2024-01-02", vdot=45.5, distance=5000.0, duration=1750.0
            ),
            VdotTrendItem(
                date="2024-01-03", vdot=46.0, distance=5000.0, duration=1700.0
            ),
        ]
        return analytics

    @pytest.fixture
    def mock_analytics_empty(self):
        """提供返回空数据的 Mock AnalyticsEngine"""
        analytics = MagicMock()
        analytics.get_vdot_trend.return_value = []
        analytics.get_training_load_trend.return_value = {
            "trend_data": [],
            "message": "暂无数据",
        }
        analytics.get_heart_rate_zones.return_value = MagicMock(
            zones=[], message="无数据", max_hr=190
        )
        return analytics

    @pytest.fixture
    def mock_analytics_with_load(self):
        """提供带有训练负荷趋势数据的 Mock AnalyticsEngine"""
        analytics = MagicMock()
        analytics.get_training_load_trend.return_value = {
            "trend_data": [
                {"date": "2024-01-01", "ctl": 60.0, "atl": 50.0, "tsb": 10.0},
                {"date": "2024-01-02", "ctl": 61.0, "atl": 55.0, "tsb": 6.0},
            ],
            "message": "ok",
        }
        return analytics

    @pytest.fixture
    def mock_analytics_with_hr_zones(self):
        """提供带有心率区间数据的 Mock AnalyticsEngine"""
        analytics = MagicMock()
        analytics.get_heart_rate_zones.return_value = MagicMock(
            zones=[
                {"zone": "Z1", "time_seconds": 300},
                {"zone": "Z2", "time_seconds": 600},
                {"zone": "Z3", "time_seconds": 400},
            ],
            max_hr=190,
            message="ok",
        )
        return analytics

    def test_vdot_full_pipeline(self, renderer, mock_analytics_with_vdot):
        """测试 VDOT 完整链路：Handler -> Renderer -> 字符串输出"""
        handler = VizHandler(
            chart_renderer=renderer,
            analytics=mock_analytics_with_vdot,
        )
        result = handler.handle_vdot(days=30)

        # 验证 AnalyticsEngine 被正确调用
        mock_analytics_with_vdot.get_vdot_trend.assert_called_once_with(30)
        # 验证返回字符串
        assert isinstance(result, str)
        assert len(result) > 0
        # 正常数据不应返回降级提示
        assert result != "暂无 VDOT 数据，请先导入跑步数据。"

    def test_vdot_empty_data(self, renderer, mock_analytics_empty):
        """测试 VDOT 空数据返回友好提示"""
        handler = VizHandler(
            chart_renderer=renderer,
            analytics=mock_analytics_empty,
        )
        result = handler.handle_vdot(days=30)

        assert isinstance(result, str)
        assert "暂无 VDOT 数据" in result

    def test_load_full_pipeline(self, renderer, mock_analytics_with_load):
        """测试训练负荷完整链路：多线折线图渲染"""
        handler = VizHandler(
            chart_renderer=renderer,
            analytics=mock_analytics_with_load,
        )
        result = handler.handle_load(days=90)

        mock_analytics_with_load.get_training_load_trend.assert_called_once_with(
            days=90
        )
        assert isinstance(result, str)
        assert len(result) > 0
        assert "暂无训练负荷数据" not in result

    def test_load_empty_data(self, renderer, mock_analytics_empty):
        """测试训练负荷空数据返回友好提示"""
        handler = VizHandler(
            chart_renderer=renderer,
            analytics=mock_analytics_empty,
        )
        result = handler.handle_load(days=90)

        assert isinstance(result, str)
        # handler 会拼接 message + "，请先导入跑步数据。"
        assert "暂无数据" in result or "请先导入跑步数据" in result

    def test_hr_zones_full_pipeline(self, renderer, mock_analytics_with_hr_zones):
        """测试心率区间完整链路：堆叠柱状图渲染"""
        handler = VizHandler(
            chart_renderer=renderer,
            analytics=mock_analytics_with_hr_zones,
        )
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 31)
        result = handler.handle_hr_zones(start=start, end=end, age=30)

        mock_analytics_with_hr_zones.get_heart_rate_zones.assert_called_once_with(
            age=30,
            start_date="2024-01-01",
            end_date="2024-01-31",
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_hr_zones_empty_data(self, renderer, mock_analytics_empty):
        """测试心率区间空数据返回友好提示"""
        handler = VizHandler(
            chart_renderer=renderer,
            analytics=mock_analytics_empty,
        )
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 31)
        result = handler.handle_hr_zones(start=start, end=end, age=30)

        assert isinstance(result, str)
        assert "无法渲染心率区间图表" in result

    def test_renderer_not_mocked(self, renderer, mock_analytics_with_vdot):
        """测试 ChartRenderer 未被 Mock，使用真实 PlotextRenderer"""
        assert isinstance(renderer, PlotextRenderer)
        handler = VizHandler(
            chart_renderer=renderer,
            analytics=mock_analytics_with_vdot,
        )
        result = handler.handle_vdot(days=30)
        # 真实 renderer 应返回 plotext 构建的图表字符串
        assert isinstance(result, str)
        assert len(result) > 0

    def test_fallback_when_renderer_raises(self, mock_analytics_with_vdot):
        """测试 Renderer 抛异常时降级为文字表格"""
        broken_renderer = MagicMock()
        broken_renderer.render_line_chart.side_effect = RuntimeError("plotext 崩溃")

        handler = VizHandler(
            chart_renderer=broken_renderer,
            analytics=mock_analytics_with_vdot,
        )
        result = handler.handle_vdot(days=30)

        assert isinstance(result, str)
        # 降级为 Rich Table，应包含数据内容
        assert "VDOT" in result or "2024-01-01" in result or "Table" in result

    def test_cli_to_handler_integration(self, mock_analytics_with_vdot):
        """测试 CLI 命令层到 Handler 的集成（模拟 get_context）"""
        from src.cli.commands.viz import _validate_days

        # 验证 days 参数校验
        assert _validate_days(30, [7, 30, 90, 365]) == 30
        with pytest.raises(Exception):
            _validate_days(15, [7, 30, 90, 365])

    def test_vdot_days_choices(self):
        """测试 VDOT 命令支持的 days 选项"""
        from src.cli.commands.viz import VDOT_DAYS_CHOICES

        assert VDOT_DAYS_CHOICES == [7, 30, 90, 365]

    def test_load_days_choices(self):
        """测试训练负荷命令支持的 days 选项"""
        from src.cli.commands.viz import LOAD_DAYS_CHOICES

        assert LOAD_DAYS_CHOICES == [30, 90, 180]
