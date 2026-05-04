# 可视化数据模型
# 定义图表渲染所需的数据结构

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DataSeries:
    """图表数据系列"""

    name: str
    labels: list[str]
    values: list[float]
    color: str | None = None


@dataclass(frozen=True)
class ChartData:
    """图表数据"""

    title: str
    x_label: str
    y_label: str
    series: list[DataSeries]


@dataclass(frozen=True)
class ChartConfig:
    """图表配置"""

    width: int | None = None
    height: int | None = None
    show_legend: bool = True
    show_grid: bool = True
    annotate_extremes: bool = True
    theme: str = "default"
