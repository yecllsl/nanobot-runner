# JSON 导出器实现
# 将跑步数据导出为 JSON 格式，包含导出元数据

from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from src.core.base.exceptions import StorageError
from src.core.export.models import ExportConfig, ExportResult


class JsonExporter:
    """JSON 格式导出器

    将字典列表数据导出为 JSON 文件，支持：
    - UTF-8 编码（无 BOM）
    - 包含导出元数据（导出时间、记录数、版本信息）
    - 格式化输出（缩进2空格）
    """

    @property
    def format_name(self) -> str:
        """返回导出器格式名称"""
        return "json"

    def export(self, data: list[dict[str, Any]], config: ExportConfig) -> ExportResult:
        """将数据导出为 JSON 文件

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
                message=f"JSON导出失败：路径验证不通过 {config.output_path}",
                duration_ms=0,
            )

        try:
            # 确保父目录存在
            config.output_path.parent.mkdir(parents=True, exist_ok=True)

            # 构建导出数据结构（包含元数据）
            export_data = {
                "metadata": {
                    "export_time": datetime.now().isoformat(),
                    "record_count": len(data),
                    "format_version": "1.0",
                    "source": "nanobot-runner",
                },
                "data": data,
            }

            # 写入 JSON 文件
            with open(
                config.output_path,
                mode="w",
                encoding=config.encoding.replace("-sig", ""),  # JSON 不需要 BOM
            ) as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)

            duration_ms = int((time.perf_counter() - start_time) * 1000)

            return ExportResult(
                success=True,
                record_count=len(data),
                file_path=config.output_path,
                message=f"JSON导出成功：{len(data)} 条记录",
                duration_ms=duration_ms,
            )

        except PermissionError as e:
            raise StorageError(
                message=f"JSON导出失败：无写入权限 {config.output_path}",
                error_code="EXPORT_PERMISSION_DENIED",
            ) from e
        except OSError as e:
            raise StorageError(
                message=f"JSON导出失败：文件系统错误 {e}",
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

        # 确保路径可解析
        try:
            resolved = path.resolve()
            parent = resolved.parent
            if parent.exists() and not os.access(str(parent), os.W_OK):
                return False
        except (OSError, ValueError):
            return False

        return True
