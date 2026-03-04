# FIT文件解析器单元测试
# 测试FIT文件解析功能

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import polars as pl
import pytest

from src.core.parser import FitParser


class MockFitMessage:
    """Mock FIT消息"""

    def __init__(self, name, data_list):
        self.name = name
        self._data_list = data_list

    def __iter__(self):
        return iter(self._data_list)


class MockFitData:
    """Mock FIT数据"""

    def __init__(self, name, value):
        self.name = name
        self.value = value


class TestFitParser:
    """测试FIT解析器"""

    def test_init(self):
        """测试初始化"""
        parser = FitParser()
        assert parser is not None

    def test_parse_file_success(self):
        """测试成功解析FIT文件"""
        parser = FitParser()

        # Mock fitparse.FitFile
        mock_record = MockFitMessage(
            "record",
            [
                MockFitData("timestamp", "2024-01-01"),
                MockFitData("distance", 5000.0),
                MockFitData("duration", 1800),
                MockFitData("heart_rate", 140),
            ],
        )

        mock_session = MockFitMessage(
            "session",
            [
                MockFitData("total_distance", 5000.0),
                MockFitData("total_elapsed_time", 1800),
            ],
        )

        mock_fit_file = Mock()
        mock_fit_file.get_messages.side_effect = lambda msg_type: {
            "record": [mock_record],
            "session": [mock_session],
        }.get(msg_type, [])

        with patch("fitparse.FitFile", return_value=mock_fit_file):
            with tempfile.NamedTemporaryFile(suffix=".fit", delete=False) as f:
                temp_path = Path(f.name)

            try:
                result = parser.parse_file(temp_path)

                assert result is not None
                assert isinstance(result, pl.DataFrame)
                assert result.height == 1
                assert "source_file" in result.columns
                assert "filename" in result.columns
            finally:
                os.unlink(temp_path)

    def test_parse_file_no_records(self):
        """测试没有记录数据的FIT文件"""
        parser = FitParser()

        mock_fit_file = Mock()
        mock_fit_file.get_messages.return_value = []

        with patch("fitparse.FitFile", return_value=mock_fit_file):
            with tempfile.NamedTemporaryFile(suffix=".fit", delete=False) as f:
                temp_path = Path(f.name)

            try:
                result = parser.parse_file(temp_path)

                assert result is None
            finally:
                os.unlink(temp_path)

    def test_parse_file_fit_parse_error(self):
        """测试FIT解析错误"""
        parser = FitParser()

        with patch("fitparse.FitFile", side_effect=Exception("Parse error")):
            with tempfile.NamedTemporaryFile(suffix=".fit", delete=False) as f:
                temp_path = Path(f.name)

            try:
                result = parser.parse_file(temp_path)

                assert result is None
            finally:
                os.unlink(temp_path)

    def test_parse_file_generic_error(self):
        """测试通用错误"""
        parser = FitParser()

        with patch("fitparse.FitFile", side_effect=Exception("Unknown error")):
            with tempfile.NamedTemporaryFile(suffix=".fit", delete=False) as f:
                temp_path = Path(f.name)

            try:
                result = parser.parse_file(temp_path)

                assert result is None
            finally:
                os.unlink(temp_path)

    def test_parse_file_metadata_success(self):
        """测试成功解析元数据"""
        parser = FitParser()

        mock_file_id = MockFitMessage(
            "file_id",
            [
                MockFitData("serial_number", "12345"),
                MockFitData("time_created", "2024-01-01"),
                MockFitData("total_distance", 5000),
            ],
        )

        mock_fit_file = Mock()
        mock_fit_file.get_messages.side_effect = lambda msg_type: {
            "file_id": [mock_file_id]
        }.get(msg_type, [])

        with patch("fitparse.FitFile", return_value=mock_fit_file):
            with tempfile.NamedTemporaryFile(suffix=".fit", delete=False) as f:
                temp_path = Path(f.name)

            try:
                result = parser.parse_file_metadata(temp_path)

                assert result["serial_number"] == "12345"
                assert result["time_created"] == "2024-01-01"
                assert result["total_distance"] == 5000
                assert result["filename"] == temp_path.stem
                assert result["filepath"] == str(temp_path)
            finally:
                os.unlink(temp_path)

    def test_parse_file_metadata_missing_fields(self):
        """测试缺少字段的元数据解析"""
        parser = FitParser()

        mock_file_id = MockFitMessage(
            "file_id", [MockFitData("serial_number", "12345")]
        )

        mock_fit_file = Mock()
        mock_fit_file.get_messages.side_effect = lambda msg_type: {
            "file_id": [mock_file_id]
        }.get(msg_type, [])

        with patch("fitparse.FitFile", return_value=mock_fit_file):
            with tempfile.NamedTemporaryFile(suffix=".fit", delete=False) as f:
                temp_path = Path(f.name)

            try:
                result = parser.parse_file_metadata(temp_path)

                assert result["serial_number"] == "12345"
                assert result["time_created"] is None
                assert result["total_distance"] is None
            finally:
                os.unlink(temp_path)

    def test_parse_file_metadata_error(self):
        """测试元数据解析错误"""
        parser = FitParser()

        with patch("fitparse.FitFile", side_effect=Exception("Parse error")):
            with tempfile.NamedTemporaryFile(suffix=".fit", delete=False) as f:
                temp_path = Path(f.name)

            try:
                result = parser.parse_file_metadata(temp_path)

                # 错误时应返回默认值
                assert result is not None
                assert result["filepath"] == str(temp_path)
            finally:
                os.unlink(temp_path)


class TestFitParserAdvanced:
    """测试FIT解析器高级功能"""

    def test_parse_file_multiple_records(self):
        """测试多条记录的FIT文件"""
        parser = FitParser()

        records = [
            MockFitMessage(
                "record",
                [
                    MockFitData("timestamp", "2024-01-01 12:00:00"),
                    MockFitData("distance", 50.0),
                    MockFitData("duration", 60.0),
                    MockFitData("heart_rate", 140),
                ],
            ),
            MockFitMessage(
                "record",
                [
                    MockFitData("timestamp", "2024-01-01 12:01:00"),
                    MockFitData("distance", 100.0),
                    MockFitData("duration", 120.0),
                    MockFitData("heart_rate", 145),
                ],
            ),
            MockFitMessage(
                "record",
                [
                    MockFitData("timestamp", "2024-01-01 12:02:00"),
                    MockFitData("distance", 150.0),
                    MockFitData("duration", 180.0),
                    MockFitData("heart_rate", 150),
                ],
            ),
        ]

        mock_session = MockFitMessage(
            "session",
            [
                MockFitData("total_distance", 200.0),
                MockFitData("total_elapsed_time", 180),
            ],
        )

        mock_fit_file = Mock()
        mock_fit_file.get_messages.side_effect = lambda msg_type: {
            "record": records,
            "session": [mock_session],
        }.get(msg_type, [])

        with patch("fitparse.FitFile", return_value=mock_fit_file):
            with tempfile.NamedTemporaryFile(suffix=".fit", delete=False) as f:
                temp_path = Path(f.name)

            try:
                result = parser.parse_file(temp_path)

                assert result is not None
                assert result.height == 3
                assert result.select(pl.col("distance").max()).item() == 150.0
            finally:
                os.unlink(temp_path)

    def test_parse_file_with_session_data(self):
        """测试带会话数据的FIT文件"""
        parser = FitParser()

        mock_record = MockFitMessage(
            "record",
            [
                MockFitData("timestamp", "2024-01-01"),
                MockFitData("distance", 5000.0),
                MockFitData("duration", 1800),
                MockFitData("heart_rate", 140),
            ],
        )

        mock_session = MockFitMessage(
            "session",
            [
                MockFitData("total_distance", 5000.0),
                MockFitData("total_elapsed_time", 1800),
                MockFitData("avg_heart_rate", 140),
                MockFitData("max_heart_rate", 160),
                MockFitData("total_calories", 300),
            ],
        )

        mock_fit_file = Mock()
        mock_fit_file.get_messages.side_effect = lambda msg_type: {
            "record": [mock_record],
            "session": [mock_session],
        }.get(msg_type, [])

        with patch("fitparse.FitFile", return_value=mock_fit_file):
            with tempfile.NamedTemporaryFile(suffix=".fit", delete=False) as f:
                temp_path = Path(f.name)

            try:
                result = parser.parse_file(temp_path)

                assert result is not None
                assert "avg_heart_rate" in result.columns
                assert result.select(pl.col("avg_heart_rate").first()).item() == 140
            finally:
                os.unlink(temp_path)

    def test_parse_file_empty_session(self):
        """测试空会话数据的FIT文件"""
        parser = FitParser()

        mock_record = MockFitMessage(
            "record",
            [
                MockFitData("timestamp", "2024-01-01"),
                MockFitData("distance", 5000.0),
                MockFitData("duration", 1800),
                MockFitData("heart_rate", 140),
            ],
        )

        mock_session = MockFitMessage("session", [])

        mock_fit_file = Mock()
        mock_fit_file.get_messages.side_effect = lambda msg_type: {
            "record": [mock_record],
            "session": [mock_session],
        }.get(msg_type, [])

        with patch("fitparse.FitFile", return_value=mock_fit_file):
            with tempfile.NamedTemporaryFile(suffix=".fit", delete=False) as f:
                temp_path = Path(f.name)

            try:
                result = parser.parse_file(temp_path)

                assert result is not None
                assert result.height == 1
            finally:
                os.unlink(temp_path)

    def test_parse_file_missing_session(self):
        """测试缺少会话数据的FIT文件"""
        parser = FitParser()

        mock_record = MockFitMessage(
            "record",
            [
                MockFitData("timestamp", "2024-01-01"),
                MockFitData("distance", 5000.0),
                MockFitData("duration", 1800),
                MockFitData("heart_rate", 140),
            ],
        )

        mock_fit_file = Mock()
        mock_fit_file.get_messages.side_effect = lambda msg_type: {
            "record": [mock_record],
            "session": [],
        }.get(msg_type, [])

        with patch("fitparse.FitFile", return_value=mock_fit_file):
            with tempfile.NamedTemporaryFile(suffix=".fit", delete=False) as f:
                temp_path = Path(f.name)

            try:
                result = parser.parse_file(temp_path)

                assert result is not None
                assert result.height == 1
            finally:
                os.unlink(temp_path)

    def test_parse_file_metadata_all_fields(self):
        """测试包含所有字段的元数据"""
        parser = FitParser()

        mock_file_id = MockFitMessage(
            "file_id",
            [
                MockFitData("serial_number", "TEST123"),
                MockFitData("time_created", "2024-06-15"),
                MockFitData("total_distance", 10000),
                MockFitData("total_timer_time", 3600),
                MockFitData("num_sessions", 1),
                MockFitData("type", "activity"),
            ],
        )

        mock_fit_file = Mock()
        mock_fit_file.get_messages.side_effect = lambda msg_type: {
            "file_id": [mock_file_id]
        }.get(msg_type, [])

        with patch("fitparse.FitFile", return_value=mock_fit_file):
            with tempfile.NamedTemporaryFile(suffix=".fit", delete=False) as f:
                temp_path = Path(f.name)

            try:
                result = parser.parse_file_metadata(temp_path)

                assert result["serial_number"] == "TEST123"
                assert result["time_created"] == "2024-06-15"
                assert result["total_distance"] == 10000
                assert result["filename"] == temp_path.stem
            finally:
                os.unlink(temp_path)

    def test_parse_file_with_power_data(self):
        """测试包含功率数据的FIT文件"""
        parser = FitParser()

        mock_record = MockFitMessage(
            "record",
            [
                MockFitData("timestamp", "2024-01-01"),
                MockFitData("distance", 5000.0),
                MockFitData("duration", 1800),
                MockFitData("heart_rate", 140),
                MockFitData("power", 200),
            ],
        )

        mock_session = MockFitMessage(
            "session",
            [
                MockFitData("total_distance", 5000.0),
                MockFitData("total_elapsed_time", 1800),
            ],
        )

        mock_fit_file = Mock()
        mock_fit_file.get_messages.side_effect = lambda msg_type: {
            "record": [mock_record],
            "session": [mock_session],
        }.get(msg_type, [])

        with patch("fitparse.FitFile", return_value=mock_fit_file):
            with tempfile.NamedTemporaryFile(suffix=".fit", delete=False) as f:
                temp_path = Path(f.name)

            try:
                result = parser.parse_file(temp_path)

                assert result is not None
                assert "power" in result.columns
            finally:
                os.unlink(temp_path)

    def test_parse_file_with_cadence_data(self):
        """测试包含步频数据的FIT文件"""
        parser = FitParser()

        mock_record = MockFitMessage(
            "record",
            [
                MockFitData("timestamp", "2024-01-01"),
                MockFitData("distance", 5000.0),
                MockFitData("duration", 1800),
                MockFitData("heart_rate", 140),
                MockFitData("cadence", 85),
            ],
        )

        mock_session = MockFitMessage(
            "session",
            [
                MockFitData("total_distance", 5000.0),
                MockFitData("total_elapsed_time", 1800),
            ],
        )

        mock_fit_file = Mock()
        mock_fit_file.get_messages.side_effect = lambda msg_type: {
            "record": [mock_record],
            "session": [mock_session],
        }.get(msg_type, [])

        with patch("fitparse.FitFile", return_value=mock_fit_file):
            with tempfile.NamedTemporaryFile(suffix=".fit", delete=False) as f:
                temp_path = Path(f.name)

            try:
                result = parser.parse_file(temp_path)

                assert result is not None
                assert "cadence" in result.columns
            finally:
                os.unlink(temp_path)

    def test_parse_file_with_position_data(self):
        """测试包含位置数据的FIT文件"""
        parser = FitParser()

        mock_record = MockFitMessage(
            "record",
            [
                MockFitData("timestamp", "2024-01-01"),
                MockFitData("distance", 5000.0),
                MockFitData("duration", 1800),
                MockFitData("heart_rate", 140),
                MockFitData("position_lat", 39.9042),
                MockFitData("position_long", 116.4074),
                MockFitData("altitude", 50.0),
            ],
        )

        mock_session = MockFitMessage(
            "session",
            [
                MockFitData("total_distance", 5000.0),
                MockFitData("total_elapsed_time", 1800),
            ],
        )

        mock_fit_file = Mock()
        mock_fit_file.get_messages.side_effect = lambda msg_type: {
            "record": [mock_record],
            "session": [mock_session],
        }.get(msg_type, [])

        with patch("fitparse.FitFile", return_value=mock_fit_file):
            with tempfile.NamedTemporaryFile(suffix=".fit", delete=False) as f:
                temp_path = Path(f.name)

            try:
                result = parser.parse_file(temp_path)

                assert result is not None
                assert "position_lat" in result.columns
                assert "position_long" in result.columns
            finally:
                os.unlink(temp_path)

    def test_parse_file_metadata_with_special_filename(self):
        """测试包含特殊字符的文件名"""
        parser = FitParser()

        mock_file_id = MockFitMessage(
            "file_id",
            [
                MockFitData("serial_number", "TEST123"),
                MockFitData("time_created", "2024-01-01"),
                MockFitData("total_distance", 5000),
            ],
        )

        mock_fit_file = Mock()
        mock_fit_file.get_messages.side_effect = lambda msg_type: {
            "file_id": [mock_file_id]
        }.get(msg_type, [])

        with patch("fitparse.FitFile", return_value=mock_fit_file):
            with tempfile.NamedTemporaryFile(
                suffix=".fit", delete=False, prefix="test-run_"
            ) as f:
                temp_path = Path(f.name)

            try:
                result = parser.parse_file_metadata(temp_path)

                assert result["filename"] == temp_path.stem
                assert "test-run_" in result["filename"]
            finally:
                os.unlink(temp_path)
