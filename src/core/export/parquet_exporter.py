# Parquet 导出器实现
# 将跑步数据导出为 Parquet 格式，仅导出原始字段（不含计算值）

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import polars as pl

from src.core.base.exceptions import StorageError
from src.core.export.models import ExportConfig, ExportResult

# 原始字段列表：仅导出从 FIT 文件解析的原始数据，不含 TSS/VDOT 等计算值
RAW_FIELDS: set[str] = {
    "timestamp",
    "session_start_time",
    "session_total_distance",
    "session_total_timer_time",
    "session_avg_heart_rate",
    "session_max_heart_rate",
    "session_avg_pace",
    "session_avg_cadence",
    "session_total_calories",
    "session_avg_power",
    "session_max_power",
    "date",
    "distance",
    "duration",
    "avg_heart_rate",
    "max_heart_rate",
    "avg_pace",
    "avg_cadence",
    "calories",
    "avg_power",
    "max_power",
    "elevation_gain",
    "elevation_loss",
    "temperature",
    "weather",
    "notes",
}

# 计算字段列表：Parquet 导出时排除
COMPUTED_FIELDS: set[str] = {
    "session_training_stress_score",
    "session_vdot",
    "tss",
    "vdot",
    "training_stress_score",
    "atl",
    "ctl",
    "tsb",
}

# 内部字段黑名单
INTERNAL_FIELDS: set[str] = {
    "sha256",
    "file_hash",
    "fingerprint",
    "internal_id",
    "_raw_bytes",
    "_internal_metadata",
}


class ParquetExporter:
    """Parquet 格式导出器

    将字典列表数据导出为 Parquet 文件，特点：
    - 仅导出原始字段（不含 TSS/VDOT 等计算值）
    - 使用 Polars 引擎写入，保证数据一致性
    - 适合作为数据备份或跨系统传输
    """

    @property
    def format_name(self) -> str:
        """返回导出器格式名称"""
        return "parquet"

    def export(self, data: list[dict[str, Any]], config: ExportConfig) -> ExportResult:
        """将数据导出为 Parquet 文件

        Args:
            data: 要导出的字典数据列表
            config: 导出配置

        Returns:
            ExportResult: 导出结果

        Raises:
            ValidationError: 当路径验证失败时
            StorageError: 当写入文件失败时
        """
        start_time = time.perf_counter()

        # 验证输出路径
        if not self.validate_output_path(config.output_path):
            return ExportResult(
                success=False,
                record_count=0,
                file_path=None,
                message=f"Parquet导出失败：路径验证不通过 {config.output_path}",
                duration_ms=0,
            )

        if not data:
            # 写入空 DataFrame（保留 schema）
            empty_df = pl.DataFrame()
            try:
                config.output_path.parent.mkdir(parents=True, exist_ok=True)
                empty_df.write_parquet(config.output_path)
                return ExportResult(
                    success=True,
                    record_count=0,
                    file_path=config.output_path,
                    message="Parquet导出成功：数据为空",
                    duration_ms=0,
                )
            except Exception as e:
                raise StorageError(
                    message=f"Parquet导出失败：写入空文件错误 {e}",
                    error_code="EXPORT_PARQUET_ERROR",
                ) from e

        try:
            # 过滤字段：仅保留原始字段，排除计算字段和内部字段
            filtered_data = self._filter_raw_fields(data)

            # 确保父目录存在
            config.output_path.parent.mkdir(parents=True, exist_ok=True)

            # 使用 Polars 写入 Parquet
            df = pl.DataFrame(filtered_data)
            df.write_parquet(config.output_path)

            duration_ms = int((time.perf_counter() - start_time) * 1000)

            return ExportResult(
                success=True,
                record_count=len(filtered_data),
                file_path=config.output_path,
                message=f"Parquet导出成功：{len(filtered_data)} 条记录",
                duration_ms=duration_ms,
            )

        except PermissionError as e:
            raise StorageError(
                message=f"Parquet导出失败：无写入权限 {config.output_path}",
                error_code="EXPORT_PERMISSION_DENIED",
            ) from e
        except OSError as e:
            raise StorageError(
                message=f"Parquet导出失败：文件系统错误 {e}",
                error_code="EXPORT_OS_ERROR",
            ) from e
        except Exception as e:
            raise StorageError(
                message=f"Parquet导出失败：Polars写入错误 {e}",
                error_code="EXPORT_PARQUET_ERROR",
            ) from e

    def validate_output_path(self, path: Path) -> bool:
        """校验输出路径安全性

        拒绝包含路径穿越（../）的路径

        Args:
            path: 待校验的路径

        Returns:
            bool: 路径是否安全
        """
        # 检查路径穿越
        if ".." in path.parts:
            return False

        # 确保路径可解析
        try:
            resolved = path.resolve()
            parent = resolved.parent
            if parent.exists() and not os.access(str(parent), os.W_OK):
                return False
        except (OSError, ValueError):
            return False

        return True

    def _filter_raw_fields(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """过滤数据，仅保留原始字段

        排除计算字段（TSS/VDOT）和内部敏感字段

        Args:
            data: 原始数据列表

        Returns:
            List[Dict]: 过滤后的数据列表
        """
        if not data:
            return []

        filtered: list[dict[str, Any]] = []

        for row in data:
            filtered_row: dict[str, Any] = {}
            for key, value in row.items():
                # 跳过内部字段和计算字段
                if key in INTERNAL_FIELDS or key in COMPUTED_FIELDS:
                    continue

                # 仅保留原始字段
                if key in RAW_FIELDS:
                    filtered_row[key] = value

            # 如果行数据为空但原始行不为空，保留原始行（避免数据丢失）
            if not filtered_row and row:
                # 回退：排除已知黑名单后保留所有字段
                filtered_row = {
                    k: v
                    for k, v in row.items()
                    if k not in INTERNAL_FIELDS and k not in COMPUTED_FIELDS
                }

            if filtered_row:
                filtered.append(filtered_row)

        return filtered
