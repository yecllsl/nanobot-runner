# CSV 导出器实现
# 将跑步数据导出为 CSV 格式，支持 Excel 兼容的 UTF-8 BOM 编码

from __future__ import annotations

import csv
import os
import stat
import time
from pathlib import Path
from typing import Any

from src.core.base.exceptions import StorageError
from src.core.export.models import ExportConfig, ExportResult

# CSV 字段白名单：不导出内部指纹等敏感字段
CSV_FIELD_WHITELIST: set[str] = {
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
    "session_training_stress_score",
    "session_vdot",
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

# 内部字段黑名单（绝对不允许导出）
CSV_FIELD_BLACKLIST: set[str] = {
    "sha256",
    "file_hash",
    "fingerprint",
    "internal_id",
    "_raw_bytes",
    "_internal_metadata",
}


class CsvExporter:
    """CSV 格式导出器

    将字典列表数据导出为 CSV 文件，支持：
    - UTF-8 BOM 编码（Excel 兼容）
    - 字段白名单过滤（不导出内部指纹等敏感字段）
    - 文件权限设置（仅当前用户可读写）
    """

    @property
    def format_name(self) -> str:
        """返回导出器格式名称"""
        return "csv"

    def export(self, data: list[dict[str, Any]], config: ExportConfig) -> ExportResult:
        """将数据导出为 CSV 文件

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
                message=f"CSV导出失败：路径验证不通过 {config.output_path}",
                duration_ms=0,
            )

        if not data:
            return ExportResult(
                success=True,
                record_count=0,
                file_path=config.output_path,
                message="CSV导出成功：数据为空",
                duration_ms=0,
            )

        try:
            # 过滤字段：移除黑名单字段，仅保留白名单字段（如果存在）
            filtered_data = self._filter_fields(data)

            # 确保父目录存在
            config.output_path.parent.mkdir(parents=True, exist_ok=True)

            # 写入 CSV 文件
            with open(
                config.output_path,
                mode="w",
                newline="",
                encoding=config.encoding,
            ) as f:
                if filtered_data:
                    fieldnames = list(filtered_data[0].keys())
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(filtered_data)

            # 设置文件权限：仅当前用户可读写（Windows 下通过 ACL 模拟）
            self._set_file_permissions(config.output_path)

            duration_ms = int((time.perf_counter() - start_time) * 1000)

            return ExportResult(
                success=True,
                record_count=len(filtered_data),
                file_path=config.output_path,
                message=f"CSV导出成功：{len(filtered_data)} 条记录",
                duration_ms=duration_ms,
            )

        except PermissionError as e:
            raise StorageError(
                message=f"CSV导出失败：无写入权限 {config.output_path}",
                error_code="EXPORT_PERMISSION_DENIED",
            ) from e
        except OSError as e:
            raise StorageError(
                message=f"CSV导出失败：文件系统错误 {e}",
                error_code="EXPORT_OS_ERROR",
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

        # 确保路径是绝对路径或相对当前目录
        try:
            resolved = path.resolve()
            # 路径必须可写（父目录存在或可创建）
            parent = resolved.parent
            if parent.exists() and not os.access(str(parent), os.W_OK):
                return False
        except (OSError, ValueError):
            return False

        return True

    def _filter_fields(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """过滤数据字段，移除敏感内部字段

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
                # 跳过黑名单字段
                if key in CSV_FIELD_BLACKLIST:
                    continue

                # 如果字段在白名单中，或白名单为空则保留所有非黑名单字段
                if key in CSV_FIELD_WHITELIST:
                    filtered_row[key] = value

            if filtered_row:
                filtered.append(filtered_row)

        return filtered

    def _set_file_permissions(self, path: Path) -> None:
        """设置文件权限为仅当前用户可读写

        Windows 下通过 stat 设置只读属性模拟，
        Unix 下通过 chmod 600 实现。

        Args:
            path: 目标文件路径
        """
        try:
            if os.name == "posix":
                # Unix/Linux/macOS: rw-------
                os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
            else:
                # Windows: 移除其他用户的写入权限
                os.chmod(
                    path,
                    stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH,
                )
        except (OSError, PermissionError):
            # 权限设置失败不影响导出成功
            pass
