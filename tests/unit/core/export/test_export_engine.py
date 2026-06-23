# ExportEngine 单元测试
# 覆盖导出引擎的核心方法：export_sessions, export_summary, _prepare_session_data 等

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.core.base.exceptions import NanobotRunnerError, StorageError
from src.core.export.engine import ExportEngine
from src.core.export.models import ExportConfig


@pytest.fixture
def mock_storage() -> MagicMock:
    """创建 mock StorageManager"""
    storage = MagicMock()
    storage.query_by_date_range.return_value = [
        {
            "session_total_distance": 10000.0,
            "session_total_timer_time": 3000.0,
            "session_avg_heart_rate": 155.0,
            "session_total_calories": 650.0,
            "session_start_time": "2026-06-10T07:00:00",
        },
        {
            "session_total_distance": 5000.0,
            "session_total_timer_time": 1500.0,
            "session_avg_heart_rate": 145.0,
            "session_total_calories": 320.0,
            "session_start_time": "2026-06-12T08:00:00",
        },
    ]
    return storage


@pytest.fixture
def mock_analytics() -> MagicMock:
    """创建 mock AnalyticsEngine"""
    analytics = MagicMock()
    analytics.calculate_vdot.return_value = 45.2
    analytics.calculate_tss_for_run.return_value = 85.0
    return analytics


@pytest.fixture
def engine(mock_storage: MagicMock, mock_analytics: MagicMock) -> ExportEngine:
    """创建测试用 ExportEngine"""
    return ExportEngine(storage=mock_storage, analytics=mock_analytics)


@pytest.fixture
def export_config(tmp_path: Path) -> ExportConfig:
    """创建测试用导出配置"""
    return ExportConfig(
        output_path=tmp_path / "test_export.csv",
        start_date=datetime(2026, 6, 1),
        end_date=datetime(2026, 6, 30),
        include_computed_fields=True,
    )


class TestExportSessions:
    """export_sessions 方法测试"""

    def test_export_sessions_unsupported_format_returns_error(
        self, engine: ExportEngine, export_config: ExportConfig
    ):
        """不支持的格式应返回失败结果"""
        result = engine.export_sessions(export_config, "xml")
        assert result.success is False
        assert "不支持的导出格式" in result.message

    def test_export_sessions_path_traversal_returns_error(self, engine: ExportEngine):
        """路径穿越应返回失败结果"""
        config = ExportConfig(output_path=Path("/tmp/../etc/passwd"))
        result = engine.export_sessions(config, "csv")
        assert result.success is False
        assert "路径穿越" in result.message

    def test_export_sessions_csv_success(
        self, engine: ExportEngine, export_config: ExportConfig
    ):
        """CSV 导出应成功"""
        result = engine.export_sessions(export_config, "csv")
        assert result.success is True
        assert result.record_count > 0

    def test_export_sessions_json_success(
        self, engine: ExportEngine, export_config: ExportConfig
    ):
        """JSON 导出应成功"""
        result = engine.export_sessions(export_config, "json")
        assert result.success is True

    def test_export_sessions_storage_error(
        self, engine: ExportEngine, mock_storage: MagicMock, export_config: ExportConfig
    ):
        """存储查询失败应返回错误"""
        mock_storage.query_by_date_range.side_effect = StorageError(
            message="查询失败", error_code="QUERY_ERROR"
        )
        result = engine.export_sessions(export_config, "csv")
        assert result.success is False
        assert "导出失败" in result.message


class TestExportSummary:
    """export_summary 方法测试"""

    def test_export_summary_unsupported_format(
        self, engine: ExportEngine, export_config: ExportConfig
    ):
        """不支持的格式应返回失败"""
        result = engine.export_summary(export_config, "xml", "monthly")
        assert result.success is False

    def test_export_summary_invalid_period(
        self, engine: ExportEngine, export_config: ExportConfig
    ):
        """无效周期应返回失败"""
        result = engine.export_summary(export_config, "csv", "daily")
        assert result.success is False
        assert "无效的汇总周期" in result.message

    def test_export_summary_monthly_success(
        self, engine: ExportEngine, export_config: ExportConfig
    ):
        """月度汇总导出应成功"""
        result = engine.export_summary(export_config, "csv", "monthly")
        assert result.success is True

    def test_export_summary_weekly_success(
        self, engine: ExportEngine, export_config: ExportConfig
    ):
        """周汇总导出应成功"""
        result = engine.export_summary(export_config, "csv", "weekly")
        assert result.success is True

    def test_export_summary_yearly_success(
        self, engine: ExportEngine, export_config: ExportConfig
    ):
        """年度汇总导出应成功"""
        result = engine.export_summary(export_config, "csv", "yearly")
        assert result.success is True

    def test_export_summary_path_traversal(self, engine: ExportEngine):
        """路径穿越应返回失败"""
        config = ExportConfig(output_path=Path("/tmp/../etc/passwd"))
        result = engine.export_summary(config, "csv", "monthly")
        assert result.success is False

    def test_export_summary_storage_error(
        self, engine: ExportEngine, mock_storage: MagicMock, export_config: ExportConfig
    ):
        """存储查询失败应返回错误"""
        mock_storage.query_by_date_range.side_effect = StorageError(
            message="查询失败", error_code="QUERY_ERROR"
        )
        result = engine.export_summary(export_config, "csv", "monthly")
        assert result.success is False
        assert "摘要导出失败" in result.message


class TestPrepareSessionData:
    """_prepare_session_data 方法测试"""

    def test_prepare_data_with_computed_fields(
        self, engine: ExportEngine, export_config: ExportConfig
    ):
        """启用计算字段时应包含 VDOT 和 TSS"""
        data = engine._prepare_session_data(export_config)
        assert len(data) > 0
        assert "session_vdot" in data[0]
        assert "session_training_stress_score" in data[0]

    def test_prepare_data_without_computed_fields(
        self, engine: ExportEngine, mock_storage: MagicMock, tmp_path: Path
    ):
        """禁用计算字段时应返回原始数据"""
        config = ExportConfig(
            output_path=tmp_path / "test.csv",
            include_computed_fields=False,
        )
        data = engine._prepare_session_data(config)
        assert len(data) > 0
        # 不应包含计算字段
        assert "session_vdot" not in data[0]

    def test_prepare_data_empty_sessions(
        self, engine: ExportEngine, mock_storage: MagicMock, tmp_path: Path
    ):
        """空数据应返回空列表"""
        mock_storage.query_by_date_range.return_value = []
        config = ExportConfig(output_path=tmp_path / "test.csv")
        data = engine._prepare_session_data(config)
        assert data == []

    def test_prepare_data_vdot_calculation_error(
        self,
        engine: ExportEngine,
        mock_analytics: MagicMock,
        export_config: ExportConfig,
    ):
        """VDOT 计算失败时应设为 None"""
        mock_analytics.calculate_vdot.side_effect = NanobotRunnerError("calc error")
        data = engine._prepare_session_data(export_config)
        assert len(data) > 0
        assert data[0].get("session_vdot") is None

    def test_prepare_data_tss_calculation_error(
        self,
        engine: ExportEngine,
        mock_analytics: MagicMock,
        export_config: ExportConfig,
    ):
        """TSS 计算失败时应设为 None"""
        mock_analytics.calculate_tss_for_run.side_effect = NanobotRunnerError(
            "calc error"
        )
        data = engine._prepare_session_data(export_config)
        assert len(data) > 0
        assert data[0].get("session_training_stress_score") is None

    def test_prepare_data_query_error_raises_storage_error(
        self, engine: ExportEngine, mock_storage: MagicMock, export_config: ExportConfig
    ):
        """查询失败应抛出 StorageError"""
        mock_storage.query_by_date_range.side_effect = NanobotRunnerError("db error")
        with pytest.raises(StorageError):
            engine._prepare_session_data(export_config)

    def test_prepare_data_short_distance_no_vdot(
        self, engine: ExportEngine, mock_storage: MagicMock, tmp_path: Path
    ):
        """距离 < 1500m 不应计算 VDOT"""
        mock_storage.query_by_date_range.return_value = [
            {
                "session_total_distance": 500.0,
                "session_total_timer_time": 300.0,
                "session_start_time": "2026-06-10T07:00:00",
            }
        ]
        config = ExportConfig(
            output_path=tmp_path / "test.csv",
            include_computed_fields=True,
        )
        data = engine._prepare_session_data(config)
        assert len(data) > 0
        assert "session_vdot" not in data[0]


class TestPrepareSummaryData:
    """_prepare_summary_data 方法测试"""

    def test_prepare_summary_monthly(
        self, engine: ExportEngine, export_config: ExportConfig
    ):
        """月度汇总应正确分组"""
        data = engine._prepare_summary_data(export_config, "monthly")
        assert len(data) > 0
        assert "period" in data[0]
        assert "total_distance_km" in data[0]
        assert "run_count" in data[0]

    def test_prepare_summary_weekly(
        self, engine: ExportEngine, export_config: ExportConfig
    ):
        """周汇总应使用 ISO 周格式"""
        data = engine._prepare_summary_data(export_config, "weekly")
        assert len(data) > 0
        assert "W" in data[0]["period"]

    def test_prepare_summary_yearly(
        self, engine: ExportEngine, export_config: ExportConfig
    ):
        """年度汇总应使用年份格式"""
        data = engine._prepare_summary_data(export_config, "yearly")
        assert len(data) > 0
        assert len(data[0]["period"]) == 4  # YYYY

    def test_prepare_summary_empty_sessions(
        self, engine: ExportEngine, mock_storage: MagicMock, export_config: ExportConfig
    ):
        """空数据应返回空列表"""
        mock_storage.query_by_date_range.return_value = []
        data = engine._prepare_summary_data(export_config, "monthly")
        assert data == []

    def test_prepare_summary_no_timestamp(
        self, engine: ExportEngine, mock_storage: MagicMock, export_config: ExportConfig
    ):
        """无时间戳的 session 应被跳过"""
        mock_storage.query_by_date_range.return_value = [
            {"session_total_distance": 5000.0, "session_total_timer_time": 1500.0}
        ]
        data = engine._prepare_summary_data(export_config, "monthly")
        assert data == []

    def test_prepare_summary_datetime_object(
        self, engine: ExportEngine, mock_storage: MagicMock, export_config: ExportConfig
    ):
        """datetime 对象作为时间戳应正确解析"""
        mock_storage.query_by_date_range.return_value = [
            {
                "session_total_distance": 5000.0,
                "session_total_timer_time": 1500.0,
                "session_total_calories": 300.0,
                "session_start_time": datetime(2026, 6, 10, 7, 0, 0),
            }
        ]
        data = engine._prepare_summary_data(export_config, "monthly")
        assert len(data) == 1
        assert data[0]["run_count"] == 1

    def test_prepare_summary_avg_heart_rate(
        self, engine: ExportEngine, mock_storage: MagicMock, export_config: ExportConfig
    ):
        """汇总应包含平均心率"""
        data = engine._prepare_summary_data(export_config, "monthly")
        assert len(data) > 0
        assert data[0].get("avg_heart_rate") is not None

    def test_prepare_summary_storage_error_raises(
        self, engine: ExportEngine, mock_storage: MagicMock, export_config: ExportConfig
    ):
        """存储查询失败应抛出 StorageError"""
        mock_storage.query_by_date_range.side_effect = OSError("disk error")
        with pytest.raises(StorageError):
            engine._prepare_summary_data(export_config, "monthly")


class TestValidatePath:
    """_validate_path 方法测试"""

    def test_valid_path_returns_true(self, engine: ExportEngine, tmp_path: Path):
        """正常路径应返回 True"""
        assert engine._validate_path(tmp_path / "output.csv") is True

    def test_path_traversal_returns_false(self, engine: ExportEngine):
        """路径穿越应返回 False"""
        assert engine._validate_path(Path("/tmp/../etc/passwd")) is False


class TestExtractFloat:
    """_extract_float 方法测试"""

    def test_primary_key_found(self, engine: ExportEngine):
        """主键存在时应返回对应值"""
        data = {"distance": 5000.0}
        assert engine._extract_float(data, "distance", "alt") == 5000.0

    def test_fallback_key_used(self, engine: ExportEngine):
        """主键不存在时应使用备用键"""
        data = {"alt": 3000.0}
        assert engine._extract_float(data, "distance", "alt") == 3000.0

    def test_both_missing_returns_none(self, engine: ExportEngine):
        """两个键都不存在应返回 None"""
        data = {}
        assert engine._extract_float(data, "distance", "alt") is None

    def test_invalid_value_returns_none(self, engine: ExportEngine):
        """无效值应返回 None"""
        data = {"distance": "not_a_number"}
        assert engine._extract_float(data, "distance", "alt") is None

    def test_none_value_returns_none(self, engine: ExportEngine):
        """None 值应返回 None"""
        data = {"distance": None}
        assert engine._extract_float(data, "distance", "alt") is None


class TestParseTimestamp:
    """_parse_timestamp 方法测试"""

    def test_none_returns_none(self, engine: ExportEngine):
        """None 应返回 None"""
        assert engine._parse_timestamp(None) is None

    def test_datetime_returns_self(self, engine: ExportEngine):
        """datetime 对象应直接返回"""
        dt = datetime(2026, 6, 10)
        assert engine._parse_timestamp(dt) == dt

    def test_iso_string_returns_datetime(self, engine: ExportEngine):
        """ISO 格式字符串应正确解析"""
        result = engine._parse_timestamp("2026-06-10T07:00:00")
        assert result is not None
        assert result.year == 2026

    def test_iso_string_with_z_suffix(self, engine: ExportEngine):
        """带 Z 后缀的 ISO 字符串应正确解析"""
        result = engine._parse_timestamp("2026-06-10T07:00:00Z")
        assert result is not None

    def test_invalid_string_returns_none(self, engine: ExportEngine):
        """无效字符串应返回 None"""
        assert engine._parse_timestamp("not-a-date") is None

    def test_unsupported_type_returns_none(self, engine: ExportEngine):
        """不支持的类型应返回 None"""
        assert engine._parse_timestamp(12345) is None


class TestGetExporter:
    """get_exporter 方法测试"""

    def test_get_csv_exporter(self, engine: ExportEngine):
        """应能获取 CSV 导出器"""
        exporter = engine.get_exporter("csv")
        assert exporter is not None
        assert exporter.format_name == "csv"

    def test_get_json_exporter(self, engine: ExportEngine):
        """应能获取 JSON 导出器"""
        exporter = engine.get_exporter("json")
        assert exporter is not None
        assert exporter.format_name == "json"

    def test_get_parquet_exporter(self, engine: ExportEngine):
        """应能获取 Parquet 导出器"""
        exporter = engine.get_exporter("parquet")
        assert exporter is not None
        assert exporter.format_name == "parquet"

    def test_get_unknown_exporter_returns_none(self, engine: ExportEngine):
        """未知格式应返回 None"""
        assert engine.get_exporter("xml") is None

    def test_case_insensitive(self, engine: ExportEngine):
        """格式名应不区分大小写"""
        assert engine.get_exporter("CSV") is not None
        assert engine.get_exporter("Json") is not None
