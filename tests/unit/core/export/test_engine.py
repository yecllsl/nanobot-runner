# 导出引擎单元测试
# 测试 ExportEngine 构造、路径校验、导出器获取、数据准备和分批逻辑

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

from src.core.export.csv_exporter import CsvExporter
from src.core.export.engine import BATCH_SIZE, ExportEngine
from src.core.export.json_exporter import JsonExporter
from src.core.export.models import ExportConfig, ExportResult
from src.core.export.parquet_exporter import ParquetExporter


class TestExportEngineConstructor:
    """构造函数测试类"""

    def test_receives_storage_and_analytics(self):
        """测试构造函数接收 storage + analytics"""
        storage = MagicMock()
        analytics = MagicMock()
        engine = ExportEngine(storage=storage, analytics=analytics)
        assert engine.storage is storage
        assert engine.analytics is analytics

    def test_registers_default_exporters(self):
        """测试默认注册 CSV/JSON/Parquet 导出器"""
        engine = ExportEngine(storage=MagicMock(), analytics=MagicMock())
        assert engine.get_exporter("csv") is not None
        assert engine.get_exporter("json") is not None
        assert engine.get_exporter("parquet") is not None


class TestValidatePath:
    """_validate_path 测试类"""

    def test_rejects_path_traversal(self):
        """测试拒绝 ../ 路径穿越"""
        engine = ExportEngine(storage=MagicMock(), analytics=MagicMock())
        assert engine._validate_path(Path("../etc/passwd")) is False
        assert engine._validate_path(Path("foo/../../bar")) is False

    def test_accepts_safe_relative_path(self):
        """测试接受安全的相对路径"""
        engine = ExportEngine(storage=MagicMock(), analytics=MagicMock())
        assert engine._validate_path(Path("./output.csv")) is True
        assert engine._validate_path(Path("data/export.csv")) is True

    def test_accepts_safe_absolute_path(self):
        """测试接受安全的绝对路径"""
        engine = ExportEngine(storage=MagicMock(), analytics=MagicMock())
        assert engine._validate_path(Path("/tmp/output.csv")) is True

    def test_rejects_unresolvable_path(self):
        """测试拒绝无法解析的路径"""
        engine = ExportEngine(storage=MagicMock(), analytics=MagicMock())
        # 使用包含空字节的非法路径触发 resolve 异常
        assert engine._validate_path(Path("\x00invalid")) is False


class TestGetExporter:
    """get_exporter 测试类"""

    def test_get_csv_exporter(self):
        """测试 get_exporter('csv') 返回 CsvExporter 实例"""
        engine = ExportEngine(storage=MagicMock(), analytics=MagicMock())
        exporter = engine.get_exporter("csv")
        assert isinstance(exporter, CsvExporter)

    def test_get_json_exporter(self):
        """测试 get_exporter('json') 返回 JsonExporter 实例"""
        engine = ExportEngine(storage=MagicMock(), analytics=MagicMock())
        exporter = engine.get_exporter("json")
        assert isinstance(exporter, JsonExporter)

    def test_get_parquet_exporter(self):
        """测试 get_exporter('parquet') 返回 ParquetExporter 实例"""
        engine = ExportEngine(storage=MagicMock(), analytics=MagicMock())
        exporter = engine.get_exporter("parquet")
        assert isinstance(exporter, ParquetExporter)

    def test_case_insensitive(self):
        """测试格式名称大小写不敏感"""
        engine = ExportEngine(storage=MagicMock(), analytics=MagicMock())
        assert isinstance(engine.get_exporter("CSV"), CsvExporter)
        assert isinstance(engine.get_exporter("Json"), JsonExporter)

    def test_unsupported_format_returns_none(self):
        """测试不支持的格式返回 None"""
        engine = ExportEngine(storage=MagicMock(), analytics=MagicMock())
        assert engine.get_exporter("xlsx") is None
        assert engine.get_exporter("pdf") is None


class TestPrepareSessionData:
    """_prepare_session_data 测试类"""

    def test_uses_query_by_date_range(self):
        """测试使用 storage.query_by_date_range() 查询数据"""
        storage = MagicMock()
        storage.query_by_date_range.return_value = []
        engine = ExportEngine(storage=storage, analytics=MagicMock())

        config = ExportConfig(
            output_path=Path("test.csv"),
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
        )
        result = engine._prepare_session_data(config)

        storage.query_by_date_range.assert_called_once_with(
            start_date=config.start_date,
            end_date=config.end_date,
        )
        assert result == []

    def test_returns_empty_when_no_sessions(self):
        """测试无数据时返回空列表"""
        storage = MagicMock()
        storage.query_by_date_range.return_value = []
        engine = ExportEngine(storage=storage, analytics=MagicMock())

        config = ExportConfig(output_path=Path("test.csv"))
        result = engine._prepare_session_data(config)
        assert result == []

    def test_no_computed_fields_returns_raw(self):
        """测试不需要计算字段时直接返回原始数据"""
        raw_data = [{"timestamp": "2024-01-01", "distance": 5000.0}]
        storage = MagicMock()
        storage.query_by_date_range.return_value = raw_data
        engine = ExportEngine(storage=storage, analytics=MagicMock())

        config = ExportConfig(
            output_path=Path("test.csv"),
            include_computed_fields=False,
        )
        result = engine._prepare_session_data(config)
        assert result == raw_data

    def test_batch_calculation_logic(self):
        """测试分批计算逻辑正确（BATCH_SIZE=100）"""
        # 构造 250 条数据，验证分 3 批处理
        sessions = [
            {
                "session_total_distance": 5000.0,
                "session_total_timer_time": 1800.0,
                "session_avg_heart_rate": 150.0,
            }
            for _ in range(250)
        ]
        storage = MagicMock()
        storage.query_by_date_range.return_value = sessions
        analytics = MagicMock()
        analytics.calculate_vdot.return_value = 45.0
        analytics.calculate_tss_for_run.return_value = 80.0

        engine = ExportEngine(storage=storage, analytics=analytics)
        config = ExportConfig(
            output_path=Path("test.csv"),
            include_computed_fields=True,
        )
        result = engine._prepare_session_data(config)

        assert len(result) == 250
        # 验证 VDOT 和 TSS 被计算并附加
        assert result[0]["session_vdot"] == 45.0
        assert result[0]["session_training_stress_score"] == 80.0
        # 验证 calculate_vdot 被调用了 250 次（因为距离>=1500）
        assert analytics.calculate_vdot.call_count == 250

    def test_batch_size_constant(self):
        """测试 BATCH_SIZE 为 100"""
        assert BATCH_SIZE == 100

    def test_short_distance_no_vdot(self):
        """测试距离 <1500m 时不计算 VDOT"""
        sessions = [
            {
                "session_total_distance": 1000.0,
                "session_total_timer_time": 300.0,
                "session_avg_heart_rate": 140.0,
            }
        ]
        storage = MagicMock()
        storage.query_by_date_range.return_value = sessions
        analytics = MagicMock()
        analytics.calculate_tss_for_run.return_value = 50.0

        engine = ExportEngine(storage=storage, analytics=analytics)
        config = ExportConfig(
            output_path=Path("test.csv"),
            include_computed_fields=True,
        )
        result = engine._prepare_session_data(config)

        # 距离 <1500m 时不会调用 calculate_vdot，因此 enriched_session 中没有 session_vdot 键
        assert "session_vdot" not in result[0]
        analytics.calculate_vdot.assert_not_called()

    def test_extract_float_fallback(self):
        """测试 _extract_float 备用键逻辑"""
        engine = ExportEngine(storage=MagicMock(), analytics=MagicMock())
        # 主键存在
        assert engine._extract_float({"a": 1.0}, "a", "b") == 1.0
        # 主键不存在，备用键存在
        assert engine._extract_float({"b": 2.0}, "a", "b") == 2.0
        # 都不存在
        assert engine._extract_float({}, "a", "b") is None
        # 值为 None
        assert engine._extract_float({"a": None}, "a", "b") is None
        # 值无法转为 float
        assert engine._extract_float({"a": "not_a_number"}, "a", "b") is None


class TestParseTimestamp:
    """_parse_timestamp 测试类"""

    def test_parse_iso_string(self):
        """测试解析 ISO 格式字符串"""
        engine = ExportEngine(storage=MagicMock(), analytics=MagicMock())
        result = engine._parse_timestamp("2024-01-15T08:30:00")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_parse_iso_string_with_z(self):
        """测试解析带 Z 后缀的 ISO 字符串"""
        engine = ExportEngine(storage=MagicMock(), analytics=MagicMock())
        result = engine._parse_timestamp("2024-01-15T08:30:00Z")
        assert result is not None
        assert result.year == 2024

    def test_parse_datetime_object(self):
        """测试直接传入 datetime 对象"""
        engine = ExportEngine(storage=MagicMock(), analytics=MagicMock())
        dt = datetime(2024, 6, 15, 10, 0, 0)
        result = engine._parse_timestamp(dt)
        assert result is dt

    def test_parse_none_returns_none(self):
        """测试 None 输入返回 None"""
        engine = ExportEngine(storage=MagicMock(), analytics=MagicMock())
        assert engine._parse_timestamp(None) is None

    def test_parse_invalid_string_returns_none(self):
        """测试无效字符串返回 None"""
        engine = ExportEngine(storage=MagicMock(), analytics=MagicMock())
        assert engine._parse_timestamp("not-a-date") is None

    def test_parse_unsupported_type_returns_none(self):
        """测试不支持的类型返回 None"""
        engine = ExportEngine(storage=MagicMock(), analytics=MagicMock())
        assert engine._parse_timestamp(12345) is None


class TestPrepareSummaryData:
    """_prepare_summary_data 测试类"""

    def test_queries_raw_data_directly(self):
        """测试直接查询原始数据，不触发 TSS/VDOT 计算"""
        storage = MagicMock()
        storage.query_by_date_range.return_value = [
            {
                "session_start_time": "2024-01-15T08:00:00",
                "session_total_distance": 5000.0,
                "session_total_timer_time": 1800.0,
                "session_avg_heart_rate": 150.0,
                "session_total_calories": 300.0,
            }
        ]
        analytics = MagicMock()
        engine = ExportEngine(storage=storage, analytics=analytics)

        config = ExportConfig(output_path=Path("test.csv"))
        result = engine._prepare_summary_data(config, "monthly")

        # 验证直接调用 storage 而非 _prepare_session_data
        storage.query_by_date_range.assert_called_once()
        # 验证不触发 TSS/VDOT 计算
        analytics.calculate_vdot.assert_not_called()
        analytics.calculate_tss_for_run.assert_not_called()
        assert len(result) == 1

    def test_monthly_grouping(self):
        """测试按月分组汇总"""
        storage = MagicMock()
        storage.query_by_date_range.return_value = [
            {
                "session_start_time": "2024-01-10T08:00:00",
                "session_total_distance": 5000.0,
                "session_total_timer_time": 1800.0,
                "session_total_calories": 300.0,
            },
            {
                "session_start_time": "2024-01-20T08:00:00",
                "session_total_distance": 8000.0,
                "session_total_timer_time": 2400.0,
                "session_total_calories": 500.0,
            },
            {
                "session_start_time": "2024-02-05T08:00:00",
                "session_total_distance": 6000.0,
                "session_total_timer_time": 2000.0,
                "session_total_calories": 400.0,
            },
        ]
        engine = ExportEngine(storage=storage, analytics=MagicMock())

        config = ExportConfig(output_path=Path("test.csv"))
        result = engine._prepare_summary_data(config, "monthly")

        assert len(result) == 2
        assert result[0]["period"] == "2024-01"
        assert result[0]["run_count"] == 2
        assert result[1]["period"] == "2024-02"
        assert result[1]["run_count"] == 1


class TestExportSessions:
    """export_sessions 集成测试类"""

    def test_unsupported_format(self):
        """测试不支持的格式返回失败结果"""
        engine = ExportEngine(storage=MagicMock(), analytics=MagicMock())
        config = ExportConfig(output_path=Path("test.xyz"))
        result = engine.export_sessions(config, "xyz")
        assert isinstance(result, ExportResult)
        assert result.success is False
        assert "不支持的导出格式" in result.message

    def test_invalid_path(self):
        """测试无效路径返回失败结果"""
        engine = ExportEngine(storage=MagicMock(), analytics=MagicMock())
        config = ExportConfig(output_path=Path("../secret.csv"))
        result = engine.export_sessions(config, "csv")
        assert result.success is False
        assert "路径包含路径穿越" in result.message

    def test_success_flow(self, tmp_path):
        """测试成功导出流程"""
        storage = MagicMock()
        storage.query_by_date_range.return_value = [
            {"timestamp": "2024-01-01", "distance": 5000.0}
        ]
        engine = ExportEngine(storage=storage, analytics=MagicMock())

        output_path = tmp_path / "output.csv"
        config = ExportConfig(output_path=output_path, include_computed_fields=False)
        result = engine.export_sessions(config, "csv")

        assert result.success is True
        assert result.record_count == 1
        assert result.file_path == output_path
        assert output_path.exists()
