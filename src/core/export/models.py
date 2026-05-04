# 数据导出模块 - 模型定义
# 定义导出配置和结果的数据结构

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class ExportConfig:
    """导出配置

    Attributes:
        output_path: 输出文件路径
        start_date: 开始日期过滤（可选）
        end_date: 结束日期过滤（可选）
        include_computed_fields: 是否包含计算字段（TSS/VDOT等）
        encoding: 文件编码格式，默认带BOM的UTF-8（Excel兼容）
    """

    output_path: Path
    start_date: datetime | None = None
    end_date: datetime | None = None
    include_computed_fields: bool = True
    encoding: str = "utf-8-sig"


@dataclass(frozen=True)
class ExportResult:
    """导出结果

    Attributes:
        success: 是否导出成功
        record_count: 导出的记录数量
        file_path: 导出的文件路径（失败时为None）
        message: 结果描述信息
        duration_ms: 导出耗时（毫秒）
    """

    success: bool
    record_count: int
    file_path: Path | None
    message: str
    duration_ms: int
