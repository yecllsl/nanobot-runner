# 图表渲染器协议定义
# 定义终端图表渲染的抽象接口

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.core.visualization.models import ChartConfig, ChartData


@runtime_checkable
class ChartRenderer(Protocol):
    """图表渲染器协议

    所有终端图表渲染实现必须遵循此协议。
    """

    def render_line_chart(
        self, data: ChartData, config: ChartConfig | None = None
    ) -> str:
        """渲染单线折线图

        Args:
            data: 图表数据
            config: 图表配置，可选

        Returns:
            终端可显示的图表字符串
        """
        ...

    def render_multi_line_chart(
        self, data: ChartData, config: ChartConfig | None = None
    ) -> str:
        """渲染多线折线图

        Args:
            data: 图表数据，可包含多个系列
            config: 图表配置，可选

        Returns:
            终端可显示的图表字符串
        """
        ...

    def render_bar_chart(
        self, data: ChartData, config: ChartConfig | None = None
    ) -> str:
        """渲染柱状图

        Args:
            data: 图表数据
            config: 图表配置，可选

        Returns:
            终端可显示的图表字符串
        """
        ...

    def render_stacked_bar_chart(
        self, data: ChartData, config: ChartConfig | None = None
    ) -> str:
        """渲染堆叠柱状图

        若底层渲染库不支持堆叠柱状图，不应抛出异常，
        应降级返回 Rich Table 格式的文本表示。

        Args:
            data: 图表数据，可包含多个系列
            config: 图表配置，可选

        Returns:
            终端可显示的图表字符串或 Rich Table 文本
        """
        ...
