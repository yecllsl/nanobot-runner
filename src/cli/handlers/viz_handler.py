# 可视化处理 Handler
# 负责图表渲染的业务逻辑调用

from __future__ import annotations

from datetime import datetime
from typing import Any

from rich.table import Table

from src.core.analytics import AnalyticsEngine
from src.core.models import HRZoneResult, VdotTrendItem
from src.core.visualization.models import ChartConfig, ChartData, DataSeries
from src.core.visualization.renderer import ChartRenderer


class VizHandler:
    """可视化业务逻辑处理器

    负责将分析数据转换为图表并渲染，支持降级策略。
    """

    def __init__(
        self,
        chart_renderer: ChartRenderer,
        analytics: AnalyticsEngine,
    ) -> None:
        """初始化可视化处理器

        Args:
            chart_renderer: 图表渲染器实例
            analytics: 分析引擎实例
        """
        self.chart_renderer = chart_renderer
        self.analytics = analytics

    def handle_vdot(self, days: int) -> str:
        """处理 VDOT 趋势图表渲染

        获取最近 N 天的 VDOT 趋势数据，渲染为单线折线图。
        渲染失败时降级为纯文字表格。

        Args:
            days: 统计天数

        Returns:
            终端可显示的图表字符串或表格文本
        """
        try:
            trend_data: list[VdotTrendItem] = self.analytics.get_vdot_trend(days)

            if not trend_data:
                return "暂无 VDOT 数据，请先导入跑步数据。"

            chart_data = self._convert_vdot_to_chart_data(trend_data)
            return self._render_with_fallback(
                chart_data,
                self.chart_renderer.render_line_chart,
            )
        except Exception as e:
            return f"VDOT 图表渲染失败: {e}"

    def handle_load(self, days: int) -> str:
        """处理训练负荷趋势图表渲染

        获取最近 N 天的训练负荷趋势（CTL/ATL/TSB），渲染为多线折线图。

        Args:
            days: 统计天数

        Returns:
            终端可显示的图表字符串或表格文本
        """
        try:
            result: dict[str, Any] = self.analytics.get_training_load_trend(days=days)
            trend_data: list[dict[str, Any]] = result.get("trend_data", [])

            if not trend_data:
                message = result.get("message", "暂无训练负荷数据")
                return f"{message}，请先导入跑步数据。"

            chart_data = self._convert_load_to_chart_data(trend_data)
            return self._render_with_fallback(
                chart_data,
                self.chart_renderer.render_multi_line_chart,
            )
        except Exception as e:
            return f"训练负荷图表渲染失败: {e}"

    def handle_hr_zones(
        self,
        start: datetime,
        end: datetime,
        age: int,
    ) -> str:
        """处理心率区间分布图表渲染

        获取指定日期范围内的心率区间分布数据，渲染为堆叠柱状图。

        Args:
            start: 开始日期时间
            end: 结束日期时间
            age: 年龄，用于计算最大心率

        Returns:
            终端可显示的图表字符串或表格文本
        """
        try:
            start_str = start.strftime("%Y-%m-%d")
            end_str = end.strftime("%Y-%m-%d")

            hr_result: HRZoneResult = self.analytics.get_heart_rate_zones(
                age=age,
                start_date=start_str,
                end_date=end_str,
            )

            if not hr_result.zones:
                return f"{hr_result.message}，无法渲染心率区间图表。"

            chart_data = self._convert_hr_zones_to_chart_data(hr_result)
            return self._render_with_fallback(
                chart_data,
                self.chart_renderer.render_stacked_bar_chart,
            )
        except Exception as e:
            return f"心率区间图表渲染失败: {e}"

    def _render_with_fallback(
        self,
        data: ChartData,
        render_func: Any,
    ) -> str:
        """渲染图表，失败时降级为纯文字表格

        Args:
            data: 图表数据
            render_func: 渲染函数

        Returns:
            终端可显示的字符串
        """
        try:
            return render_func(data, ChartConfig())
        except Exception:
            # 降级为 Rich Table 纯文字表格
            return self._render_text_table(data)

    def _render_text_table(self, data: ChartData) -> str:
        """将图表数据渲染为纯文字表格（降级策略）

        Args:
            data: 图表数据

        Returns:
            Rich Table 格式的文本字符串
        """
        table = Table(title=data.title)
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
            row_values: list[str] = []
            for s in data.series:
                if i < len(s.values):
                    row_values.append(f"{s.values[i]:.2f}")
                else:
                    row_values.append("-")
            table.add_row(label, *row_values)

        # 使用 Rich Console 捕获输出为字符串
        from rich.console import Console

        from src.core.visualization.plotext_renderer import _get_terminal_width

        console = Console(force_terminal=True, width=_get_terminal_width(None))
        with console.capture() as capture:
            console.print(table)
        return capture.get()

    def _convert_vdot_to_chart_data(
        self,
        trend_data: list[VdotTrendItem],
    ) -> ChartData:
        """将 VDOT 趋势数据转换为图表数据

        Args:
            trend_data: VDOT 趋势数据列表

        Returns:
            ChartData 实例（单 series）
        """
        labels = [item.date for item in trend_data]
        values = [item.vdot for item in trend_data]

        return ChartData(
            title=f"VDOT 趋势 (最近 {len(trend_data)} 天)",
            x_label="日期",
            y_label="VDOT",
            series=[
                DataSeries(
                    name="VDOT",
                    labels=labels,
                    values=values,
                    color="blue",
                ),
            ],
        )

    def _convert_load_to_chart_data(
        self,
        trend_data: list[dict[str, Any]],
    ) -> ChartData:
        """将训练负荷趋势数据转换为图表数据

        Args:
            trend_data: 训练负荷趋势数据列表

        Returns:
            ChartData 实例（CTL/ATL/TSB 三个 series）
        """
        labels = [item["date"] for item in trend_data]
        ctl_values = [item["ctl"] for item in trend_data]
        atl_values = [item["atl"] for item in trend_data]
        tsb_values = [item["tsb"] for item in trend_data]

        return ChartData(
            title=f"训练负荷趋势 (最近 {len(trend_data)} 天)",
            x_label="日期",
            y_label="负荷值",
            series=[
                DataSeries(
                    name="CTL (慢性训练负荷)",
                    labels=labels,
                    values=ctl_values,
                    color="blue",
                ),
                DataSeries(
                    name="ATL (急性训练负荷)",
                    labels=labels,
                    values=atl_values,
                    color="red",
                ),
                DataSeries(
                    name="TSB (训练压力平衡)",
                    labels=labels,
                    values=tsb_values,
                    color="green",
                ),
            ],
        )

    def _convert_hr_zones_to_chart_data(
        self,
        hr_result: HRZoneResult,
    ) -> ChartData:
        """将心率区间结果转换为图表数据

        Args:
            hr_result: 心率区间分析结果

        Returns:
            ChartData 实例（Z1-Z5 五个 series）
        """
        # 对于心率区间，我们按区间名称作为 x 轴标签
        # 每个 series 代表一个统计维度（时长、百分比）
        # 这里使用堆叠柱状图展示各区间时长
        zones = hr_result.zones

        labels = [z["zone"] for z in zones]
        time_values = [float(z.get("time_seconds", 0)) for z in zones]

        return ChartData(
            title=f"心率区间分布 (最大心率: {hr_result.max_hr} bpm)",
            x_label="心率区间",
            y_label="时长 (秒)",
            series=[
                DataSeries(
                    name="时长 (秒)",
                    labels=labels,
                    values=time_values,
                    color="blue",
                ),
            ],
        )
