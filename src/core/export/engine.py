# 导出引擎
# 管理数据导出流程，协调不同格式的导出器

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from src.core.base.exceptions import StorageError
from src.core.export.csv_exporter import CsvExporter
from src.core.export.json_exporter import JsonExporter
from src.core.export.models import ExportConfig, ExportResult
from src.core.export.parquet_exporter import ParquetExporter

if TYPE_CHECKING:
    from src.core.analytics import AnalyticsEngine
    from src.core.storage.parquet_manager import StorageManager

# 批量处理大小：分批计算 TSS/VDOT 以避免内存占用过大
BATCH_SIZE: int = 100


@runtime_checkable
class DataExporter(Protocol):
    """数据导出器协议

    所有导出器必须实现此协议，包括：
    - format_name: 格式名称属性
    - export: 执行导出操作
    - validate_output_path: 校验输出路径安全性
    """

    @property
    def format_name(self) -> str:
        """导出器格式名称（如 'csv', 'json', 'parquet'）"""
        ...

    def export(self, data: list[dict[str, Any]], config: ExportConfig) -> ExportResult:
        """将数据导出为指定格式

        Args:
            data: 要导出的字典数据列表
            config: 导出配置

        Returns:
            ExportResult: 导出结果
        """
        ...

    def validate_output_path(self, path: Path) -> bool:
        """校验输出路径安全性

        Args:
            path: 待校验的路径

        Returns:
            bool: 路径是否安全
        """
        ...


class ExportEngine:
    """导出引擎

    管理数据导出流程，支持多种导出格式：
    - CSV: Excel 兼容格式，带字段过滤
    - JSON: 结构化数据，含元数据
    - Parquet: 仅原始字段，适合数据备份

    通过依赖注入接收 StorageManager 和 AnalyticsEngine，
    不直接实例化核心组件。
    """

    def __init__(
        self,
        storage: StorageManager,
        analytics: AnalyticsEngine,
    ) -> None:
        """初始化导出引擎

        Args:
            storage: 存储管理器实例
            analytics: 分析引擎实例
        """
        self.storage = storage
        self.analytics = analytics
        self._exporters: dict[str, DataExporter] = {}
        self._register_default_exporters()

    def _register_default_exporters(self) -> None:
        """注册默认导出器（CSV/JSON/Parquet）"""
        csv_exporter = CsvExporter()
        json_exporter = JsonExporter()
        parquet_exporter = ParquetExporter()

        self._exporters[csv_exporter.format_name] = csv_exporter
        self._exporters[json_exporter.format_name] = json_exporter
        self._exporters[parquet_exporter.format_name] = parquet_exporter

    def get_exporter(self, format_name: str) -> DataExporter | None:
        """获取指定格式的导出器

        Args:
            format_name: 格式名称（csv/json/parquet）

        Returns:
            DataExporter | None: 导出器实例，未找到时返回 None
        """
        return self._exporters.get(format_name.lower())

    def export_sessions(
        self,
        config: ExportConfig,
        format_name: str,
    ) -> ExportResult:
        """导出跑步活动数据

        根据日期范围查询活动数据，可选计算 TSS/VDOT，
        然后导出为指定格式。

        Args:
            config: 导出配置（含日期范围、输出路径等）
            format_name: 导出格式名称

        Returns:
            ExportResult: 导出结果

        Raises:
            ValidationError: 当格式不支持或路径无效时
            StorageError: 当数据查询或导出失败时
        """
        start_time = time.perf_counter()

        # 获取导出器
        exporter = self.get_exporter(format_name)
        if exporter is None:
            available = ", ".join(self._exporters.keys())
            return ExportResult(
                success=False,
                record_count=0,
                file_path=None,
                message=f"不支持的导出格式 '{format_name}'，可用格式：{available}",
                duration_ms=0,
            )

        # 验证路径
        if not self._validate_path(config.output_path):
            return ExportResult(
                success=False,
                record_count=0,
                file_path=None,
                message=f"导出失败：路径包含路径穿越或不安全 {config.output_path}",
                duration_ms=0,
            )

        try:
            # 准备数据
            data = self._prepare_session_data(config)

            # 执行导出
            result = exporter.export(data, config)

            # 如果导出成功，更新耗时
            if result.success:
                total_duration_ms = int((time.perf_counter() - start_time) * 1000)
                return ExportResult(
                    success=True,
                    record_count=result.record_count,
                    file_path=result.file_path,
                    message=result.message,
                    duration_ms=total_duration_ms,
                )

            return result

        except (StorageError, ValueError, OSError) as e:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            return ExportResult(
                success=False,
                record_count=0,
                file_path=None,
                message=f"导出失败：{e}",
                duration_ms=duration_ms,
            )

    def export_summary(
        self,
        config: ExportConfig,
        format_name: str,
        period: str,
    ) -> ExportResult:
        """导出跑步摘要数据

        按指定周期（weekly/monthly/yearly）汇总数据后导出。

        Args:
            config: 导出配置
            format_name: 导出格式名称
            period: 汇总周期（weekly/monthly/yearly）

        Returns:
            ExportResult: 导出结果

        Raises:
            ValidationError: 当周期参数无效时
            StorageError: 当数据查询或导出失败时
        """
        start_time = time.perf_counter()

        # 获取导出器
        exporter = self.get_exporter(format_name)
        if exporter is None:
            available = ", ".join(self._exporters.keys())
            return ExportResult(
                success=False,
                record_count=0,
                file_path=None,
                message=f"不支持的导出格式 '{format_name}'，可用格式：{available}",
                duration_ms=0,
            )

        # 验证路径
        if not self._validate_path(config.output_path):
            return ExportResult(
                success=False,
                record_count=0,
                file_path=None,
                message=f"导出失败：路径包含路径穿越或不安全 {config.output_path}",
                duration_ms=0,
            )

        # 验证周期参数
        valid_periods = {"weekly", "monthly", "yearly"}
        if period.lower() not in valid_periods:
            return ExportResult(
                success=False,
                record_count=0,
                file_path=None,
                message=f"无效的汇总周期 '{period}'，可用：weekly, monthly, yearly",
                duration_ms=0,
            )

        try:
            # 准备汇总数据
            data = self._prepare_summary_data(config, period.lower())

            # 执行导出
            result = exporter.export(data, config)

            if result.success:
                total_duration_ms = int((time.perf_counter() - start_time) * 1000)
                return ExportResult(
                    success=True,
                    record_count=result.record_count,
                    file_path=result.file_path,
                    message=result.message,
                    duration_ms=total_duration_ms,
                )

            return result

        except (StorageError, ValueError, OSError) as e:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            return ExportResult(
                success=False,
                record_count=0,
                file_path=None,
                message=f"摘要导出失败：{e}",
                duration_ms=duration_ms,
            )

    def _prepare_session_data(self, config: ExportConfig) -> list[dict[str, Any]]:
        """准备活动数据用于导出

        通过 StorageManager 按日期范围查询数据，
        根据配置分批计算 TSS/VDOT。

        Args:
            config: 导出配置

        Returns:
            List[Dict]: 准备好的数据列表

        Raises:
            StorageError: 当数据查询失败时
        """
        # 从存储查询数据
        try:
            sessions = self.storage.query_by_date_range(
                start_date=config.start_date,
                end_date=config.end_date,
            )
        except Exception as e:
            raise StorageError(
                message=f"查询活动数据失败：{e}",
                error_code="EXPORT_QUERY_ERROR",
            ) from e

        if not sessions:
            return []

        # 如果不需要计算字段，直接返回原始数据
        if not config.include_computed_fields:
            return sessions

        # 分批计算 TSS/VDOT
        result_data: list[dict[str, Any]] = []

        for i in range(0, len(sessions), BATCH_SIZE):
            batch = sessions[i : i + BATCH_SIZE]

            for session in batch:
                # 复制原始数据，避免修改源数据
                enriched_session = dict(session)

                # 提取计算所需字段
                distance = self._extract_float(
                    session, "session_total_distance", "distance"
                )
                duration = self._extract_float(
                    session, "session_total_timer_time", "duration"
                )
                avg_hr = self._extract_float(
                    session, "session_avg_heart_rate", "avg_heart_rate"
                )

                # 计算 VDOT（距离 >= 1500m 时计算）
                if distance is not None and duration is not None and distance >= 1500:
                    try:
                        vdot = self.analytics.calculate_vdot(distance, duration)
                        enriched_session["session_vdot"] = round(vdot, 2)
                    except Exception:
                        enriched_session["session_vdot"] = None

                # 计算 TSS
                if distance is not None and duration is not None:
                    try:
                        tss = self.analytics.calculate_tss_for_run(
                            distance_m=distance,
                            duration_s=duration,
                            avg_heart_rate=avg_hr,
                        )
                        enriched_session["session_training_stress_score"] = tss
                    except Exception:
                        enriched_session["session_training_stress_score"] = None

                result_data.append(enriched_session)

        return result_data

    def _prepare_summary_data(
        self, config: ExportConfig, period: str
    ) -> list[dict[str, Any]]:
        """准备汇总数据用于导出

        按指定周期对数据进行分组汇总。
        直接查询原始数据，跳过 TSS/VDOT 计算。

        Args:
            config: 导出配置
            period: 汇总周期（weekly/monthly/yearly）

        Returns:
            List[Dict]: 汇总后的数据列表
        """
        # 直接查询原始数据，跳过不必要的 TSS/VDOT 计算
        try:
            sessions = self.storage.query_by_date_range(
                start_date=config.start_date,
                end_date=config.end_date,
            )
        except (StorageError, OSError) as e:
            raise StorageError(
                message=f"查询汇总数据失败：{e}",
                error_code="EXPORT_QUERY_ERROR",
            ) from e

        if not sessions:
            return []

        # 按周期分组汇总
        summary_map: dict[str, dict[str, Any]] = {}

        for session in sessions:
            # 提取并解析时间戳
            ts = session.get("session_start_time") or session.get("timestamp")
            dt = self._parse_timestamp(ts)
            if dt is None:
                continue

            # 根据周期确定分组键
            if period == "weekly":
                # ISO 周格式：2024-W01
                group_key = dt.strftime("%Y-W%W")
            elif period == "monthly":
                group_key = dt.strftime("%Y-%m")
            else:  # yearly
                group_key = dt.strftime("%Y")

            if group_key not in summary_map:
                summary_map[group_key] = {
                    "period": group_key,
                    "total_distance": 0.0,
                    "total_duration": 0.0,
                    "run_count": 0,
                    "avg_heart_rate_sum": 0.0,
                    "avg_heart_rate_count": 0,
                    "total_calories": 0.0,
                }

            # 累加数据
            summary = summary_map[group_key]
            distance = (
                self._extract_float(session, "session_total_distance", "distance") or 0
            )
            duration = (
                self._extract_float(session, "session_total_timer_time", "duration")
                or 0
            )
            avg_hr = self._extract_float(
                session, "session_avg_heart_rate", "avg_heart_rate"
            )
            calories = (
                self._extract_float(session, "session_total_calories", "calories") or 0
            )

            summary["total_distance"] += distance
            summary["total_duration"] += duration
            summary["run_count"] += 1
            summary["total_calories"] += calories

            if avg_hr is not None and avg_hr > 0:
                summary["avg_heart_rate_sum"] += avg_hr
                summary["avg_heart_rate_count"] += 1

        # 计算平均值并格式化结果
        result: list[dict[str, Any]] = []
        for group_key in sorted(summary_map.keys()):
            summary = summary_map[group_key]

            avg_hr = (
                summary["avg_heart_rate_sum"] / summary["avg_heart_rate_count"]
                if summary["avg_heart_rate_count"] > 0
                else None
            )

            result.append(
                {
                    "period": summary["period"],
                    "total_distance_km": round(summary["total_distance"] / 1000, 2),
                    "total_duration_min": round(summary["total_duration"] / 60, 1),
                    "run_count": summary["run_count"],
                    "avg_heart_rate": round(avg_hr, 1) if avg_hr else None,
                    "total_calories": round(summary["total_calories"], 1),
                    "avg_distance_km": round(
                        summary["total_distance"] / 1000 / summary["run_count"], 2
                    )
                    if summary["run_count"] > 0
                    else 0,
                }
            )

        return result

    def _validate_path(self, path: Path) -> bool:
        """验证路径安全性

        拒绝包含路径穿越（../）的路径

        Args:
            path: 待验证的路径

        Returns:
            bool: 路径是否安全
        """
        # 检查路径穿越
        if ".." in path.parts:
            return False

        # 确保路径可解析
        try:
            path.resolve()
        except (OSError, ValueError):
            return False

        return True

    def _extract_float(
        self, data: dict[str, Any], primary_key: str, fallback_key: str
    ) -> float | None:
        """从字典中提取浮点数值

        优先使用主键，不存在时使用备用键

        Args:
            data: 数据字典
            primary_key: 主键名
            fallback_key: 备用键名

        Returns:
            float | None: 提取的数值，失败时返回 None
        """
        value = data.get(primary_key)
        if value is None:
            value = data.get(fallback_key)
        if value is None:
            return None

        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def _parse_timestamp(self, ts: Any) -> datetime | None:
        """解析时间戳为 datetime 对象

        支持字符串（ISO 格式）和 datetime 对象，
        其他类型或解析失败时返回 None。

        Args:
            ts: 时间戳值，可以是 str、datetime 或其他类型

        Returns:
            datetime | None: 解析后的 datetime 对象，失败时返回 None
        """
        if ts is None:
            return None

        if isinstance(ts, datetime):
            return ts

        if isinstance(ts, str):
            try:
                return datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except ValueError:
                return None

        return None
