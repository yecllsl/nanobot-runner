# 导出处理 Handler
# 负责数据导出业务的逻辑调用

from __future__ import annotations

from src.core.export.engine import ExportEngine
from src.core.export.models import ExportConfig, ExportResult


class ExportHandler:
    """导出业务逻辑处理器

    负责协调导出引擎，处理会话数据和摘要数据的导出请求。
    """

    def __init__(self, export_engine: ExportEngine) -> None:
        """初始化导出处理器

        Args:
            export_engine: 导出引擎实例
        """
        self.export_engine = export_engine

    def handle_export_sessions(
        self,
        config: ExportConfig,
        format_name: str,
    ) -> ExportResult:
        """处理跑步活动数据导出

        调用导出引擎导出指定日期范围内的活动数据。

        Args:
            config: 导出配置（含日期范围、输出路径等）
            format_name: 导出格式名称（csv/json/parquet）

        Returns:
            ExportResult: 导出结果，包含成功状态、记录数、文件路径等信息
        """
        return self.export_engine.export_sessions(config, format_name)

    def handle_export_summary(
        self,
        config: ExportConfig,
        period: str,
        format_name: str,
    ) -> ExportResult:
        """处理跑步摘要数据导出

        按指定周期（weekly/monthly/yearly）汇总数据后导出。

        Args:
            config: 导出配置
            period: 汇总周期（weekly/monthly/yearly）
            format_name: 导出格式名称（csv/json）

        Returns:
            ExportResult: 导出结果
        """
        return self.export_engine.export_summary(config, format_name, period)
