# Export 命令端到端测试
# 测试 CLI -> Handler -> Engine -> 文件 完整链路
# 使用临时目录验证文件输出

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.cli.handlers.export_handler import ExportHandler
from src.core.export.engine import ExportEngine
from src.core.export.models import ExportConfig, ExportResult


class TestExportE2E:
    """Export 端到端测试类"""

    @pytest.fixture
    def sample_sessions(self):
        """提供脱敏的测试活动数据"""
        return [
            {
                "timestamp": "2024-01-01T06:00:00",
                "session_start_time": "2024-01-01T06:00:00",
                "session_total_distance": 5000.0,
                "session_total_timer_time": 1800.0,
                "session_avg_heart_rate": 150.0,
                "session_max_heart_rate": 175.0,
                "session_total_calories": 350.0,
            },
            {
                "timestamp": "2024-01-03T07:00:00",
                "session_start_time": "2024-01-03T07:00:00",
                "session_total_distance": 8000.0,
                "session_total_timer_time": 2700.0,
                "session_avg_heart_rate": 155.0,
                "session_max_heart_rate": 180.0,
                "session_total_calories": 520.0,
            },
            {
                "timestamp": "2024-01-05T06:30:00",
                "session_start_time": "2024-01-05T06:30:00",
                "session_total_distance": 10000.0,
                "session_total_timer_time": 3600.0,
                "session_avg_heart_rate": 148.0,
                "session_max_heart_rate": 172.0,
                "session_total_calories": 650.0,
            },
        ]

    @pytest.fixture
    def mock_storage(self, sample_sessions):
        """提供返回测试数据的 Mock StorageManager"""
        storage = MagicMock()
        storage.query_by_date_range.return_value = sample_sessions
        return storage

    @pytest.fixture
    def mock_analytics(self):
        """提供 Mock AnalyticsEngine"""
        analytics = MagicMock()
        analytics.calculate_vdot.return_value = 45.0
        analytics.calculate_tss_for_run.return_value = 80.0
        return analytics

    @pytest.fixture
    def engine(self, mock_storage, mock_analytics):
        """提供配置好的 ExportEngine"""
        return ExportEngine(storage=mock_storage, analytics=mock_analytics)

    @pytest.fixture
    def handler(self, engine):
        """提供配置好的 ExportHandler"""
        return ExportHandler(export_engine=engine)

    def test_export_sessions_csv_full_pipeline(self, handler, tmp_path):
        """测试 CSV 导出完整链路：Handler -> Engine -> 文件"""
        output_path = tmp_path / "runs.csv"
        config = ExportConfig(
            output_path=output_path,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
            include_computed_fields=False,
        )
        result = handler.handle_export_sessions(config, "csv")

        assert isinstance(result, ExportResult)
        assert result.success is True
        assert result.record_count == 3
        assert result.file_path == output_path
        assert output_path.exists()

        # 验证文件内容
        content = output_path.read_text(encoding="utf-8-sig")
        assert "timestamp" in content
        assert "2024-01-01" in content
        assert "5000.0" in content

    def test_export_sessions_json_full_pipeline(self, handler, tmp_path):
        """测试 JSON 导出完整链路"""
        import json

        output_path = tmp_path / "runs.json"
        config = ExportConfig(
            output_path=output_path,
            include_computed_fields=False,
        )
        result = handler.handle_export_sessions(config, "json")

        assert result.success is True
        assert result.record_count == 3
        assert output_path.exists()

        # 验证 JSON 结构和元数据
        content = json.loads(output_path.read_text(encoding="utf-8"))
        assert "metadata" in content
        assert "data" in content
        assert content["metadata"]["record_count"] == 3
        assert len(content["data"]) == 3

    def test_export_sessions_parquet_full_pipeline(self, handler, tmp_path):
        """测试 Parquet 导出完整链路"""
        output_path = tmp_path / "runs.parquet"
        config = ExportConfig(
            output_path=output_path,
            include_computed_fields=False,
        )
        result = handler.handle_export_sessions(config, "parquet")

        assert result.success is True
        assert result.record_count == 3
        assert output_path.exists()

        # 验证 Parquet 可用 Polars 读取
        import polars as pl

        df = pl.read_parquet(output_path)
        assert len(df) == 3

    def test_export_with_computed_fields(self, engine, tmp_path):
        """测试包含计算字段（VDOT/TSS）的导出"""
        output_path = tmp_path / "runs_with_computed.csv"
        config = ExportConfig(
            output_path=output_path,
            include_computed_fields=True,
        )
        result = engine.export_sessions(config, "csv")

        assert result.success is True
        content = output_path.read_text(encoding="utf-8-sig")
        # 计算字段应出现在导出内容中
        assert "session_vdot" in content or "session_training_stress_score" in content

    def test_export_summary_weekly(self, handler, tmp_path):
        """测试按周汇总导出"""
        output_path = tmp_path / "weekly_summary.csv"
        config = ExportConfig(
            output_path=output_path,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
            include_computed_fields=False,
        )
        result = handler.handle_export_summary(
            config, period="weekly", format_name="csv"
        )

        assert result.success is True
        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8-sig")
        # CSV 汇总字段包含 run_count / total_distance_km / avg_heart_rate 等
        assert (
            "run_count" in content
            or "total_distance" in content
            or "avg_heart_rate" in content
        )

    def test_export_summary_monthly(self, handler, tmp_path):
        """测试按月汇总导出"""
        output_path = tmp_path / "monthly_summary.json"
        config = ExportConfig(
            output_path=output_path,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 3, 31),
            include_computed_fields=False,
        )
        result = handler.handle_export_summary(
            config, period="monthly", format_name="json"
        )

        assert result.success is True
        assert output_path.exists()

    def test_export_summary_yearly(self, handler, tmp_path):
        """测试按年汇总导出"""
        output_path = tmp_path / "yearly_summary.csv"
        config = ExportConfig(
            output_path=output_path,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            include_computed_fields=False,
        )
        result = handler.handle_export_summary(
            config, period="yearly", format_name="csv"
        )

        assert result.success is True
        assert output_path.exists()

    def test_export_invalid_format(self, handler, tmp_path):
        """测试无效格式返回失败"""
        output_path = tmp_path / "runs.xyz"
        config = ExportConfig(output_path=output_path)
        result = handler.handle_export_sessions(config, "xyz")

        assert result.success is False
        assert "不支持的导出格式" in result.message

    def test_export_path_traversal_rejected(self, handler):
        """测试路径穿越被阻止"""
        config = ExportConfig(output_path=Path("../secret.csv"))
        result = handler.handle_export_sessions(config, "csv")

        assert result.success is False
        assert "路径包含路径穿越" in result.message

    def test_export_empty_data(self, tmp_path):
        """测试空数据导出"""
        storage = MagicMock()
        storage.query_by_date_range.return_value = []
        analytics = MagicMock()
        engine = ExportEngine(storage=storage, analytics=analytics)
        handler = ExportHandler(export_engine=engine)

        output_path = tmp_path / "empty.csv"
        config = ExportConfig(output_path=output_path, include_computed_fields=False)
        result = handler.handle_export_sessions(config, "csv")

        assert result.success is True
        assert result.record_count == 0
        # CsvExporter 对空数据直接返回成功，不创建文件
        # 因此不强制断言文件存在

    def test_export_date_range_filter(self, engine, mock_storage, tmp_path):
        """测试日期范围过滤被正确传递"""
        output_path = tmp_path / "filtered.csv"
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 15)
        config = ExportConfig(
            output_path=output_path,
            start_date=start,
            end_date=end,
            include_computed_fields=False,
        )
        result = engine.export_sessions(config, "csv")

        assert result.success is True
        mock_storage.query_by_date_range.assert_called_once_with(
            start_date=start,
            end_date=end,
        )

    def test_cli_format_choices(self):
        """测试 CLI 支持的格式选项"""
        from src.cli.commands.export import (
            SESSION_FORMAT_CHOICES,
            SUMMARY_FORMAT_CHOICES,
        )

        assert "csv" in SESSION_FORMAT_CHOICES
        assert "json" in SESSION_FORMAT_CHOICES
        assert "parquet" in SESSION_FORMAT_CHOICES
        assert "csv" in SUMMARY_FORMAT_CHOICES
        assert "json" in SUMMARY_FORMAT_CHOICES

    def test_cli_period_choices(self):
        """测试 CLI 支持的周期选项"""
        from src.cli.commands.export import PERIOD_CHOICES

        assert "weekly" in PERIOD_CHOICES
        assert "monthly" in PERIOD_CHOICES
        assert "yearly" in PERIOD_CHOICES
