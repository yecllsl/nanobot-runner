# Plotext 图表渲染器实现
# 使用 plotext 库在终端中渲染图表

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

from rich.table import Table

from src.core.base.exceptions import NanobotRunnerError
from src.core.visualization.models import ChartConfig, ChartData

if TYPE_CHECKING:
    pass


def _get_terminal_width(config: ChartConfig | None) -> int:
    """获取终端宽度，限制在 60-120 列范围内

    Args:
        config: 图表配置，若包含 width 则优先使用

    Returns:
        计算后的终端宽度
    """
    if config is not None and config.width is not None:
        return max(60, min(120, config.width))
    try:
        cols, _ = shutil.get_terminal_size()
    except OSError:
        cols = 80
    return max(60, min(120, cols))


def _get_terminal_height(config: ChartConfig | None) -> int:
    """获取终端高度，默认 20 行

    Args:
        config: 图表配置，若包含 height 则优先使用

    Returns:
        计算后的终端高度
    """
    if config is not None and config.height is not None:
        return max(10, config.height)
    try:
        _, rows = shutil.get_terminal_size()
    except OSError:
        rows = 20
    return max(10, rows // 2)


def _has_data(data: ChartData) -> bool:
    """检查图表数据是否有效且非空"""
    if not data.series:
        return False
    return all(s.labels and s.values for s in data.series)


def _annotate_extremes(labels: list[str], values: list[float]) -> dict[int, str]:
    """标注极值点（最高值和最低值）

    Args:
        labels: 数据标签列表
        values: 数据值列表

    Returns:
        索引到标注文本的映射
    """
    if not values:
        return {}

    annotations: dict[int, str] = {}
    min_idx = min(range(len(values)), key=lambda i: values[i])
    max_idx = max(range(len(values)), key=lambda i: values[i])
    annotations[min_idx] = f"最低: {labels[min_idx]}={values[min_idx]}"
    annotations[max_idx] = f"最高: {labels[max_idx]}={values[max_idx]}"
    return annotations


def _fallback_stacked_bar_as_table(data: ChartData, config: ChartConfig | None) -> str:
    """堆叠柱状图降级为 Rich Table 文本表示

    当底层渲染库不支持堆叠柱状图时，使用 Rich Table 展示各系列数据。

    Args:
        data: 图表数据
        config: 图表配置，可选

    Returns:
        Rich Table 格式的文本字符串
    """
    table = Table(title=data.title if data.title else "堆叠数据")
    table.add_column(data.x_label, style="cyan")

    # 收集所有标签
    all_labels: list[str] = []
    if data.series:
        all_labels = data.series[0].labels[:]

    # 添加各系列列
    for s in data.series:
        table.add_column(s.name, justify="right")

    # 按行填充数据
    for i, label in enumerate(all_labels):
        row_values = []
        for s in data.series:
            if i < len(s.values):
                row_values.append(f"{s.values[i]:.2f}")
            else:
                row_values.append("-")
        table.add_row(str(label), *row_values)

    # 使用 Rich Console 捕获输出为字符串
    from rich.console import Console

    console = Console(force_terminal=True, width=_get_terminal_width(config))
    with console.capture() as capture:
        console.print(table)
    return capture.get()


class PlotextRenderer:
    """基于 plotext 的终端图表渲染器"""

    def render_line_chart(
        self, data: ChartData, config: ChartConfig | None = None
    ) -> str:
        """渲染单线折线图

        使用 plotext 绘制单线折线图，自动适配终端宽度，
        并在最高/最低值处进行标注。

        Args:
            data: 图表数据，应包含单个系列
            config: 图表配置，可选

        Returns:
            终端可显示的图表字符串
        """
        if not _has_data(data):
            return "暂无数据"

        import plotext as plt

        plt.clear_figure()
        width = _get_terminal_width(config)
        height = _get_terminal_height(config)
        plt.plotsize(width, height)

        series = data.series[0]
        plt.plot(series.labels, series.values, label=series.name)
        plt.title(data.title)
        plt.xlabel(data.x_label)
        plt.ylabel(data.y_label)

        if config is not None and config.show_legend:
            plt.legend()

        # 极值标注（根据配置决定是否启用）
        if config is None or config.annotate_extremes:
            annotations = _annotate_extremes(series.labels, series.values)
            for idx, text in annotations.items():
                plt.annotate(text, idx, series.values[idx])

        return plt.build()

    def render_multi_line_chart(
        self, data: ChartData, config: ChartConfig | None = None
    ) -> str:
        """渲染多线折线图

        支持多个数据系列，使用不同颜色区分。

        Args:
            data: 图表数据，可包含多个系列
            config: 图表配置，可选

        Returns:
            终端可显示的图表字符串
        """
        if not _has_data(data):
            return "暂无数据"

        import plotext as plt

        plt.clear_figure()
        width = _get_terminal_width(config)
        height = _get_terminal_height(config)
        plt.plotsize(width, height)

        for s in data.series:
            kwargs: dict[str, object] = {"label": s.name}
            if s.color is not None:
                kwargs["color"] = s.color
            plt.plot(s.labels, s.values, **kwargs)

        plt.title(data.title)
        plt.xlabel(data.x_label)
        plt.ylabel(data.y_label)

        if config is not None and config.show_legend:
            plt.legend()

        return plt.build()

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
        if not _has_data(data):
            return "暂无数据"

        import plotext as plt

        plt.clear_figure()
        width = _get_terminal_width(config)
        height = _get_terminal_height(config)
        plt.plotsize(width, height)

        series = data.series[0]
        plt.bar(series.labels, series.values, label=series.name)
        plt.title(data.title)
        plt.xlabel(data.x_label)
        plt.ylabel(data.y_label)

        if config is not None and config.show_legend:
            plt.legend()

        return plt.build()

    def render_stacked_bar_chart(
        self, data: ChartData, config: ChartConfig | None = None
    ) -> str:
        """渲染堆叠柱状图

        尝试使用 plotext.bar() 实现堆叠效果；
        若 plotext 不支持堆叠（如无法传入多组数据），
        则降级为 Rich Table 文本表示，不抛出异常。

        Args:
            data: 图表数据，可包含多个系列
            config: 图表配置，可选

        Returns:
            终端可显示的图表字符串或 Rich Table 文本
        """
        if not _has_data(data):
            return "暂无数据"

        import plotext as plt

        plt.clear_figure()
        width = _get_terminal_width(config)
        height = _get_terminal_height(config)
        plt.plotsize(width, height)

        # plotext 的 bar 支持多组数据时可通过嵌套列表实现堆叠效果
        # 若不支持则捕获异常降级为表格
        try:
            labels = data.series[0].labels
            values_list = [s.values for s in data.series]
            names = [s.name for s in data.series]

            # 检查各系列长度是否一致
            if any(len(v) != len(labels) for v in values_list):
                raise NanobotRunnerError(
                    message="堆叠柱状图各系列数据长度不一致",
                    error_code="VALIDATION_ERROR",
                    recovery_suggestion="请确保所有系列的数据点数量相同",
                )

            # plotext 5.x 支持多组 bar 数据通过嵌套列表传入
            plt.bar(labels, values_list, label=names)
            plt.title(data.title)
            plt.xlabel(data.x_label)
            plt.ylabel(data.y_label)

            if config is not None and config.show_legend:
                plt.legend()

            return plt.build()
        except (TypeError, ValueError, NanobotRunnerError):
            # 降级为 Rich Table，不抛异常
            return _fallback_stacked_bar_as_table(data, config)
