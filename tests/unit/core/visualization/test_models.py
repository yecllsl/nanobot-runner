# 可视化数据模型单元测试
# 测试 ChartData / ChartConfig / DataSeries 的不可变性、类型正确性和多 series 支持

from dataclasses import FrozenInstanceError

import pytest

from src.core.visualization.models import ChartConfig, ChartData, DataSeries


class TestDataSeries:
    """DataSeries 数据模型测试类"""

    def test_create_basic(self):
        """测试基本构造"""
        series = DataSeries(
            name="VDOT",
            labels=["2024-01-01", "2024-01-02"],
            values=[45.0, 46.2],
        )
        assert series.name == "VDOT"
        assert series.labels == ["2024-01-01", "2024-01-02"]
        assert series.values == [45.0, 46.2]
        assert series.color is None

    def test_create_with_color(self):
        """测试带颜色构造"""
        series = DataSeries(
            name="CTL",
            labels=["周一", "周二"],
            values=[50.0, 52.0],
            color="blue",
        )
        assert series.color == "blue"

    def test_frozen_immutable(self):
        """测试 frozen dataclass 不可变性"""
        series = DataSeries(
            name="VDOT",
            labels=["2024-01-01"],
            values=[45.0],
        )
        with pytest.raises(FrozenInstanceError):
            series.name = "TSS"

    def test_field_types(self):
        """测试字段类型正确性"""
        series = DataSeries(
            name="测试",
            labels=["a", "b"],
            values=[1.0, 2.0],
            color="red",
        )
        assert isinstance(series.name, str)
        assert isinstance(series.labels, list)
        assert isinstance(series.values, list)
        assert isinstance(series.color, str)

    def test_empty_series(self):
        """测试空 series 边界场景"""
        series = DataSeries(
            name="Empty",
            labels=[],
            values=[],
        )
        assert series.labels == []
        assert series.values == []


class TestChartData:
    """ChartData 数据模型测试类"""

    def test_create_single_series(self):
        """测试单 series 构造"""
        series = DataSeries(
            name="VDOT",
            labels=["2024-01-01", "2024-01-02"],
            values=[45.0, 46.2],
        )
        chart = ChartData(
            title="VDOT 趋势",
            x_label="日期",
            y_label="VDOT",
            series=[series],
        )
        assert chart.title == "VDOT 趋势"
        assert len(chart.series) == 1

    def test_create_multi_series(self):
        """测试 ChartData 支持多 series"""
        series1 = DataSeries(
            name="CTL",
            labels=["周一", "周二", "周三"],
            values=[60.0, 61.0, 62.0],
            color="blue",
        )
        series2 = DataSeries(
            name="ATL",
            labels=["周一", "周二", "周三"],
            values=[50.0, 55.0, 48.0],
            color="red",
        )
        series3 = DataSeries(
            name="TSB",
            labels=["周一", "周二", "周三"],
            values=[10.0, 6.0, 14.0],
            color="green",
        )
        chart = ChartData(
            title="训练负荷趋势",
            x_label="日期",
            y_label="负荷值",
            series=[series1, series2, series3],
        )
        assert len(chart.series) == 3
        assert chart.series[0].name == "CTL"
        assert chart.series[1].name == "ATL"
        assert chart.series[2].name == "TSB"

    def test_frozen_immutable(self):
        """测试 frozen dataclass 不可变性"""
        series = DataSeries(name="VDOT", labels=["2024-01-01"], values=[45.0])
        chart = ChartData(
            title="趋势",
            x_label="日期",
            y_label="值",
            series=[series],
        )
        with pytest.raises(FrozenInstanceError):
            chart.title = "新标题"

    def test_empty_series_list(self):
        """测试空 series 列表边界场景"""
        chart = ChartData(
            title="空图表",
            x_label="x",
            y_label="y",
            series=[],
        )
        assert chart.series == []


class TestChartConfig:
    """ChartConfig 数据模型测试类"""

    def test_default_values(self):
        """测试默认值正确性"""
        config = ChartConfig()
        assert config.width is None
        assert config.height is None
        assert config.show_legend is True
        assert config.show_grid is True
        assert config.annotate_extremes is True
        assert config.theme == "default"

    def test_custom_values(self):
        """测试自定义值"""
        config = ChartConfig(
            width=100,
            height=30,
            show_legend=False,
            show_grid=False,
            annotate_extremes=False,
            theme="dark",
        )
        assert config.width == 100
        assert config.height == 30
        assert config.show_legend is False
        assert config.show_grid is False
        assert config.annotate_extremes is False
        assert config.theme == "dark"

    def test_frozen_immutable(self):
        """测试 frozen dataclass 不可变性"""
        config = ChartConfig(width=80)
        with pytest.raises(FrozenInstanceError):
            config.width = 120

    def test_partial_override(self):
        """测试部分字段覆盖"""
        config = ChartConfig(width=60)
        assert config.width == 60
        assert config.height is None
        assert config.show_legend is True
        assert config.theme == "default"
