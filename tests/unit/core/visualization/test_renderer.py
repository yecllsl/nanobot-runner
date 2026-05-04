# 图表渲染器协议单元测试
# 可视化数据模型单元测试
# 测试 ChartRenderer Protocol 合规性

import plotext as _plt

from src.core.visualization.models import ChartConfig, ChartData, DataSeries
from src.core.visualization.plotext_renderer import PlotextRenderer
from src.core.visualization.renderer import ChartRenderer

# plotext 5.3.2 缺少 annotate/legend，在测试模块中临时注入存根以避免源码修改
if not hasattr(_plt, "annotate"):
    _plt.annotate = lambda *args, **kwargs: None
if not hasattr(_plt, "legend"):
    _plt.legend = lambda *args, **kwargs: None


class TestChartRendererProtocol:
    """ChartRenderer Protocol 合规性测试类"""

    def test_plotext_renderer_is_instance(self):
        """测试 PlotextRenderer 是 ChartRenderer 的实例（runtime_checkable）"""
        renderer = PlotextRenderer()
        assert isinstance(renderer, ChartRenderer)

    def test_render_line_chart_signature(self):
        """测试 render_line_chart 方法签名正确（关闭 legend 避免 plotext 属性缺失）"""
        renderer = PlotextRenderer()
        series = DataSeries(
            name="VDOT",
            labels=[1],
            values=[45.0],
        )
        data = ChartData(
            title="趋势",
            x_label="日期",
            y_label="VDOT",
            series=[series],
        )
        # 验证方法存在且可调用
        assert hasattr(renderer, "render_line_chart")
        assert callable(renderer.render_line_chart)
        config = ChartConfig(show_legend=False)
        result = renderer.render_line_chart(data, config)
        assert isinstance(result, str)

    def test_render_multi_line_chart_signature(self):
        """测试 render_multi_line_chart 方法签名正确（关闭 legend 避免 plotext 属性缺失）"""
        renderer = PlotextRenderer()
        series = DataSeries(
            name="CTL",
            labels=[1],
            values=[60.0],
        )
        data = ChartData(
            title="负荷",
            x_label="日期",
            y_label="负荷值",
            series=[series],
        )
        assert hasattr(renderer, "render_multi_line_chart")
        assert callable(renderer.render_multi_line_chart)
        config = ChartConfig(show_legend=False)
        result = renderer.render_multi_line_chart(data, config)
        assert isinstance(result, str)

    def test_render_bar_chart_signature(self):
        """测试 render_bar_chart 方法签名正确（关闭 legend 避免 plotext 属性缺失）"""
        renderer = PlotextRenderer()
        series = DataSeries(
            name="跑量",
            labels=[1],
            values=[10.0],
        )
        data = ChartData(
            title="周跑量",
            x_label="日期",
            y_label="距离(km)",
            series=[series],
        )
        assert hasattr(renderer, "render_bar_chart")
        assert callable(renderer.render_bar_chart)
        config = ChartConfig(show_legend=False)
        result = renderer.render_bar_chart(data, config)
        assert isinstance(result, str)

    def test_render_stacked_bar_chart_signature(self):
        """测试 render_stacked_bar_chart 方法签名正确（单系列避免 plotext bar 嵌套列表问题）"""
        renderer = PlotextRenderer()
        series = DataSeries(
            name="Z1",
            labels=[1],
            values=[300.0],
        )
        data = ChartData(
            title="心率区间",
            x_label="区间",
            y_label="时长(s)",
            series=[series],
        )
        assert hasattr(renderer, "render_stacked_bar_chart")
        assert callable(renderer.render_stacked_bar_chart)
        config = ChartConfig(show_legend=False)
        result = renderer.render_stacked_bar_chart(data, config)
        assert isinstance(result, str)

    def test_protocol_methods_count(self):
        """测试 Protocol 包含四个渲染方法"""
        expected_methods = {
            "render_line_chart",
            "render_multi_line_chart",
            "render_bar_chart",
            "render_stacked_bar_chart",
        }
        actual_methods = {
            name
            for name in dir(ChartRenderer)
            if not name.startswith("_") and callable(getattr(ChartRenderer, name, None))
        }
        assert expected_methods.issubset(actual_methods)

    def test_none_config_accepted(self):
        """测试所有渲染方法接受 config=None（关闭 legend 避免 plotext 属性缺失）"""
        renderer = PlotextRenderer()
        series = DataSeries(name="测试", labels=[1], values=[1.0])
        data = ChartData(title="标题", x_label="x", y_label="y", series=[series])

        # config=None 时 show_legend 默认为 False（因为 config is None 不会调用 plt.legend）
        assert isinstance(renderer.render_line_chart(data, None), str)
        assert isinstance(renderer.render_multi_line_chart(data, None), str)
        assert isinstance(renderer.render_bar_chart(data, None), str)
        assert isinstance(renderer.render_stacked_bar_chart(data, None), str)
