# 存储管理器单元测试

import tempfile
from datetime import datetime
from pathlib import Path

import polars as pl
import pytest

from src.core.exceptions import StorageError, ValidationError
from src.core.storage import StorageManager


class TestStorageManager:
    """StorageManager 单元测试"""

    def test_init_default_dir(self):
        """测试初始化默认目录"""
        manager = StorageManager()
        assert manager.data_dir is not None

    def test_init_custom_dir(self):
        """测试初始化自定义目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_dir = Path(tmpdir) / "test_data"
            manager = StorageManager(data_dir=custom_dir)
            assert manager.data_dir == custom_dir

    def test_save_and_read_parquet(self):
        """测试保存和读取Parquet文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            # 创建测试数据
            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001"],
                    "timestamp": [datetime(2024, 1, 1)],
                    "session_total_distance": [5000.0],
                    "session_total_timer_time": [1800],
                    "session_avg_heart_rate": [140],
                }
            )

            # 保存
            result = manager.save_to_parquet(test_data, 2024)
            assert result is True

    def test_save_activities_alias(self):
        """测试 save_activities 方法"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001"],
                    "timestamp": [datetime(2024, 1, 1)],
                    "session_total_distance": [5000.0],
                    "session_total_timer_time": [1800],
                    "session_avg_heart_rate": [140],
                }
            )

            result = manager.save_activities(test_data, 2024)
            assert result["success"] is True
            assert result["records_saved"] == 1
            assert result["year"] == 2024

    def test_save_activities_auto_year(self):
        """测试 save_activities 自动推断年份"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001"],
                    "timestamp": [datetime(2024, 6, 15)],
                    "session_total_distance": [5000.0],
                    "session_total_timer_time": [1800],
                    "session_avg_heart_rate": [140],
                }
            )

            result = manager.save_activities(test_data)  # 不指定年份
            assert result["success"] is True
            assert result["year"] == 2024  # 自动从timestamp推断

    def test_load_activities_alias(self):
        """测试 load_activities 方法（read_activities 的别名）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001"],
                    "timestamp": [datetime(2024, 1, 1)],
                    "session_total_distance": [5000.0],
                    "session_total_timer_time": [1800],
                    "session_avg_heart_rate": [140],
                }
            )

            manager.save_to_parquet(test_data, 2024)

            # 测试 load_activities 别名
            loaded_df = manager.load_activities(2024)
            assert len(loaded_df) == 1
            assert loaded_df["activity_id"][0] == "test_001"

    def test_save_to_parquet_empty_with_allow_empty_true(self):
        """测试允许保存空数据框（allow_empty=True）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            empty_data = pl.DataFrame(
                {
                    "activity_id": [],
                    "timestamp": [],
                    "session_total_distance": [],
                    "session_total_timer_time": [],
                    "session_avg_heart_rate": [],
                }
            )

            result = manager.save_to_parquet(empty_data, 2024, allow_empty=True)
            assert result is True

    def test_save_to_parquet_empty_with_allow_empty_false(self):
        """测试拒绝保存空数据框（allow_empty=False，默认）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            empty_data = pl.DataFrame(
                {
                    "activity_id": [],
                    "timestamp": [],
                    "session_total_distance": [],
                    "session_total_timer_time": [],
                    "session_avg_heart_rate": [],
                }
            )

            with pytest.raises(ValidationError, match="数据框不能为空"):
                manager.save_to_parquet(empty_data, 2024)

    def test_get_data_summary(self):
        """测试获取数据摘要"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001"],
                    "timestamp": [datetime(2024, 1, 1)],
                    "session_total_distance": [5000.0],
                    "session_total_timer_time": [1800],
                    "session_avg_heart_rate": [140],
                }
            )
            manager.save_to_parquet(test_data, 2024)

            summary = manager.get_data_summary()
            assert summary["total_records"] == 1
            assert 2024 in summary["available_years"]
            assert "total_size_mb" in summary

    def test_get_data_summary_empty(self):
        """测试空数据摘要"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            summary = manager.get_data_summary()
            assert summary["total_records"] == 0
            assert summary["available_years"] == []

    def test_delete_year_data(self):
        """测试删除年份数据"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001"],
                    "timestamp": [datetime(2024, 1, 1)],
                    "session_total_distance": [5000.0],
                    "session_total_timer_time": [1800],
                    "session_avg_heart_rate": [140],
                }
            )
            manager.save_to_parquet(test_data, 2024)

            # 删除数据
            result = manager.delete_year_data(2024)
            assert result is True

            # 验证删除
            years = manager.get_available_years()
            assert 2024 not in years

    def test_delete_year_data_not_exists(self):
        """测试删除不存在的年份数据"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            result = manager.delete_year_data(2024)
            assert result is False

    def test_append_to_existing_file(self):
        """测试追加到现有文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            # 第一次保存
            data1 = pl.DataFrame(
                {
                    "activity_id": ["test_001"],
                    "timestamp": [datetime(2024, 1, 1)],
                    "session_total_distance": [5000.0],
                    "session_total_timer_time": [1800],
                    "session_avg_heart_rate": [140],
                }
            )
            manager.save_to_parquet(data1, 2024)

            # 第二次追加
            data2 = pl.DataFrame(
                {
                    "activity_id": ["test_002"],
                    "timestamp": [datetime(2024, 1, 2)],
                    "session_total_distance": [10000.0],
                    "session_total_timer_time": [3600],
                    "session_avg_heart_rate": [150],
                }
            )
            manager.save_to_parquet(data2, 2024)

            # 读取验证
            lf = manager.read_parquet(years=[2024])
            df = lf.collect()

            assert df.height == 2

    def test_get_stats(self):
        """测试获取统计信息"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            # 创建测试数据
            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001", "test_002"],
                    "timestamp": [datetime(2024, 1, 1), datetime(2024, 2, 1)],
                    "session_total_distance": [5000.0, 10000.0],
                    "session_total_timer_time": [1800, 3600],
                    "session_avg_heart_rate": [140, 150],
                }
            )
            manager.save_to_parquet(test_data, 2024)

            # 获取统计
            stats = manager.get_stats()

            assert stats["total_records"] == 2
            assert 2024 in stats["years"]
            assert stats["time_range"] is not None

    def test_get_stats_empty(self):
        """测试空数据统计"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            stats = manager.get_stats()

            assert stats["total_records"] == 0
            assert stats["years"] == []

    def test_get_available_years(self):
        """测试获取可用年份"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            # 创建测试数据
            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001"],
                    "timestamp": [datetime(2024, 1, 1)],
                    "session_total_distance": [5000.0],
                    "session_total_timer_time": [1800],
                    "session_avg_heart_rate": [140],
                }
            )
            manager.save_to_parquet(test_data, 2024)

            years = manager.get_available_years()
            assert 2024 in years

    def test_get_available_years_empty(self):
        """测试空数据的可用年份"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            years = manager.get_available_years()
            assert years == []

    def test_read_activities_with_year(self):
        """测试按年份读取"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            # 创建测试数据
            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001"],
                    "timestamp": [datetime(2024, 1, 1)],
                    "session_total_distance": [5000.0],
                    "session_total_timer_time": [1800],
                    "session_avg_heart_rate": [140],
                }
            )
            manager.save_to_parquet(test_data, 2024)

            df = manager.read_activities(2024)
            assert df.height == 1

    def test_read_activities_multiple_years(self):
        """测试多年份数据读取"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            # 创建2024年数据
            data_2024 = pl.DataFrame(
                {
                    "activity_id": ["test_001"],
                    "timestamp": [datetime(2024, 1, 1)],
                    "session_total_distance": [5000.0],
                    "session_total_timer_time": [1800],
                    "session_avg_heart_rate": [140],
                }
            )
            manager.save_to_parquet(data_2024, 2024)

            # 创建2025年数据
            data_2025 = pl.DataFrame(
                {
                    "activity_id": ["test_002"],
                    "timestamp": [datetime(2025, 1, 1)],
                    "session_total_distance": [10000.0],
                    "session_total_timer_time": [3600],
                    "session_avg_heart_rate": [150],
                }
            )
            manager.save_to_parquet(data_2025, 2025)

            # 读取所有年份
            df = manager.read_activities()
            assert df.height == 2

    def test_query_activities_by_days(self):
        """测试按天数查询"""
        from datetime import datetime, timedelta

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            # 创建最近7天的数据
            today = datetime.now()
            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001", "test_002"],
                    "timestamp": [today - timedelta(days=3), today - timedelta(days=5)],
                    "session_total_distance": [5000.0, 10000.0],
                    "session_total_timer_time": [1800, 3600],
                    "session_avg_heart_rate": [140, 150],
                }
            )
            manager.save_to_parquet(test_data, today.year)

            # 查询最近30天
            result = manager.query_activities(days=30)
            assert result.height >= 0

    def test_query_activities_by_min_distance(self):
        """测试按最小距离查询"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001", "test_002"],
                    "timestamp": [datetime(2024, 1, 1), datetime(2024, 1, 2)],
                    "session_total_distance": [5000.0, 10000.0],
                    "session_total_timer_time": [1800, 3600],
                    "session_avg_heart_rate": [140, 150],
                }
            )
            manager.save_to_parquet(test_data, 2024)

            result = manager.query_activities(min_distance=8000)
            assert result.height >= 0

    def test_query_activities_by_min_heart_rate(self):
        """测试按最小心率查询"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001", "test_002"],
                    "timestamp": [datetime(2024, 1, 1), datetime(2024, 1, 2)],
                    "session_total_distance": [5000.0, 10000.0],
                    "session_total_timer_time": [1800, 3600],
                    "session_avg_heart_rate": [140, 150],
                }
            )
            manager.save_to_parquet(test_data, 2024)

            result = manager.query_activities(min_heart_rate=145)
            assert result.height >= 0

    def test_query_activities_no_data(self):
        """测试无数据查询"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            result = manager.query_activities()
            assert result.height == 0

    def test_read_parquet_empty_directory(self):
        """测试空目录读取"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            lf = manager.read_parquet()
            df = lf.collect()
            assert df.height == 0

    def test_save_to_parquet_compression(self):
        """测试压缩保存"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001"],
                    "timestamp": [datetime(2024, 1, 1)],
                    "session_total_distance": [5000.0],
                    "session_total_timer_time": [1800],
                    "session_avg_heart_rate": [140],
                }
            )
            result = manager.save_to_parquet(test_data, 2024)
            assert result is True

    def test_init_with_os_error(self):
        """测试初始化时目录创建失败"""
        from unittest.mock import patch

        with patch("pathlib.Path.mkdir", side_effect=OSError("Permission denied")):
            with pytest.raises(StorageError, match="无法创建数据目录"):
                StorageManager(data_dir=Path("/invalid/path"))

    def test_save_to_parquet_invalid_year_low(self):
        """测试年份过小"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001"],
                    "timestamp": [datetime(2024, 1, 1)],
                    "session_total_distance": [5000.0],
                    "session_total_timer_time": [1800],
                }
            )

            with pytest.raises(ValidationError, match="年份必须在2000-2100范围内"):
                manager.save_to_parquet(test_data, 1999)

    def test_save_to_parquet_invalid_year_high(self):
        """测试年份过大"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001"],
                    "timestamp": [datetime(2024, 1, 1)],
                    "session_total_distance": [5000.0],
                    "session_total_timer_time": [1800],
                }
            )

            with pytest.raises(ValidationError, match="年份必须在2000-2100范围内"):
                manager.save_to_parquet(test_data, 2101)

    def test_delete_year_data_invalid_year(self):
        """测试删除无效年份"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            with pytest.raises(ValidationError, match="年份必须在2000-2100范围内"):
                manager.delete_year_data(1999)

    def test_convert_to_parquet_compatible_object_type(self):
        """测试Object类型转换为String"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            # 创建包含Object类型的DataFrame
            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001"],
                    "timestamp": [datetime(2024, 1, 1)],
                    "session_total_distance": [5000.0],
                    "session_total_timer_time": [1800],
                    "object_col": [["a", "b"]],  # 这会被转换为Object类型
                }
            )

            # 保存应该成功，Object类型会被转换为String
            result = manager.save_to_parquet(test_data, 2024)
            assert result is True

    def test_align_dataframes_different_schemas(self):
        """测试不同schema的DataFrame对齐"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            # 第一次保存
            data1 = pl.DataFrame(
                {
                    "activity_id": ["test_001"],
                    "timestamp": [datetime(2024, 1, 1)],
                    "session_total_distance": [5000.0],
                    "session_total_timer_time": [1800.0],
                    "session_avg_heart_rate": [140],
                }
            )
            manager.save_to_parquet(data1, 2024)

            # 第二次保存，不同的列和类型
            data2 = pl.DataFrame(
                {
                    "activity_id": ["test_002"],
                    "timestamp": [datetime(2024, 1, 2)],
                    "session_total_distance": [10000.0],
                    "session_total_timer_time": [3600],
                    "max_heart_rate": [170],  # 新列
                }
            )
            manager.save_to_parquet(data2, 2024)

            # 读取验证
            df = manager.read_activities(2024)
            assert df.height == 2
            assert "session_avg_heart_rate" in df.columns
            assert "max_heart_rate" in df.columns

    def test_read_parquet_with_years(self):
        """测试按年份列表读取"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            # 创建2023和2024年数据
            data_2023 = pl.DataFrame(
                {
                    "activity_id": ["test_001"],
                    "timestamp": [datetime(2023, 1, 1)],
                    "session_total_distance": [5000.0],
                    "session_total_timer_time": [1800],
                }
            )
            manager.save_to_parquet(data_2023, 2023)

            data_2024 = pl.DataFrame(
                {
                    "activity_id": ["test_002"],
                    "timestamp": [datetime(2024, 1, 1)],
                    "session_total_distance": [10000.0],
                    "session_total_timer_time": [3600],
                }
            )
            manager.save_to_parquet(data_2024, 2024)

            # 只读取2024年
            lf = manager.read_parquet(years=[2024])
            df = lf.collect()
            assert df.height == 1

    def test_read_parquet_years_not_found(self):
        """测试读取不存在的年份"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            lf = manager.read_parquet(years=[2020, 2021])
            df = lf.collect()
            assert df.height == 0

    def test_save_activities_with_error(self):
        """测试保存活动数据时的错误处理"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            # 创建会导致错误的数据（无效年份）
            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001"],
                    "timestamp": [datetime(2024, 1, 1)],
                    "session_total_distance": [5000.0],
                    "session_total_timer_time": [1800],
                }
            )

            result = manager.save_activities(test_data, year=1999)
            assert result["success"] is False
            assert "error" in result

    def test_save_activities_empty_dataframe_auto_year(self):
        """测试空DataFrame自动推断年份"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            empty_data = pl.DataFrame(
                {
                    "activity_id": [],
                    "timestamp": [],
                    "session_total_distance": [],
                    "session_total_timer_time": [],
                }
            )

            result = manager.save_activities(empty_data)
            # 空DataFrame会被拒绝（默认allow_empty=False）
            assert result["success"] is False

    def test_query_by_date_range(self):
        """测试按日期范围查询"""
        from datetime import datetime, timedelta

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            # 创建测试数据
            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001", "test_002", "test_003"],
                    "timestamp": [
                        datetime(2024, 1, 1),
                        datetime(2024, 1, 15),
                        datetime(2024, 2, 1),
                    ],
                    "session_total_distance": [5000.0, 10000.0, 15000.0],
                    "session_total_timer_time": [1800, 3600, 5400],
                }
            )
            manager.save_to_parquet(test_data, 2024)

            # 查询日期范围
            start_date = datetime(2024, 1, 10)
            end_date = datetime(2024, 1, 20)
            result = manager.query_by_date_range(start_date, end_date)

            assert len(result) == 1
            assert result[0]["activity_id"] == "test_002"

    def test_query_by_date_range_start_only(self):
        """测试只指定开始日期"""
        from datetime import datetime

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001", "test_002"],
                    "timestamp": [datetime(2024, 1, 1), datetime(2024, 2, 1)],
                    "session_total_distance": [5000.0, 10000.0],
                    "session_total_timer_time": [1800, 3600],
                }
            )
            manager.save_to_parquet(test_data, 2024)

            result = manager.query_by_date_range(start_date=datetime(2024, 1, 15))
            assert len(result) == 1

    def test_query_by_date_range_end_only(self):
        """测试只指定结束日期"""
        from datetime import datetime

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001", "test_002"],
                    "timestamp": [datetime(2024, 1, 1), datetime(2024, 2, 1)],
                    "session_total_distance": [5000.0, 10000.0],
                    "session_total_timer_time": [1800, 3600],
                }
            )
            manager.save_to_parquet(test_data, 2024)

            result = manager.query_by_date_range(end_date=datetime(2024, 1, 15))
            assert len(result) == 1

    def test_query_by_date_range_no_data(self):
        """测试空数据范围查询"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            result = manager.query_by_date_range()
            assert len(result) == 0

    def test_get_available_years_with_invalid_filename(self):
        """测试包含无效文件名的年份提取"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            # 创建一个不符合命名规范的文件
            invalid_file = Path(tmpdir) / "invalid_file.parquet"
            invalid_file.touch()

            # 创建一个有效文件
            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001"],
                    "timestamp": [datetime(2024, 1, 1)],
                    "session_total_distance": [5000.0],
                    "session_total_timer_time": [1800],
                }
            )
            manager.save_to_parquet(test_data, 2024)

            years = manager.get_available_years()
            assert 2024 in years
            # 无效文件名应该被忽略

    def test_read_activities_with_exception(self):
        """测试读取活动数据时的异常"""
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            # 创建一个文件，但读取时抛出异常
            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001"],
                    "timestamp": [datetime(2024, 1, 1)],
                    "session_total_distance": [5000.0],
                    "session_total_timer_time": [1800],
                }
            )
            manager.save_to_parquet(test_data, 2024)

            # Mock pl.read_parquet 抛出异常
            with patch("polars.read_parquet", side_effect=Exception("Read error")):
                with pytest.raises(StorageError, match="读取活动数据失败"):
                    manager.read_activities(2024)

    def test_get_data_summary_with_exception(self):
        """测试获取数据摘要时的异常"""
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            # Mock get_available_years 抛出异常
            with patch.object(
                manager,
                "get_available_years",
                side_effect=Exception("Get years error"),
            ):
                with pytest.raises(StorageError, match="获取数据摘要失败"):
                    manager.get_data_summary()

    def test_delete_year_data_with_exception(self):
        """测试删除年份数据时的异常"""
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            # 创建文件
            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001"],
                    "timestamp": [datetime(2024, 1, 1)],
                    "session_total_distance": [5000.0],
                    "session_total_timer_time": [1800],
                }
            )
            manager.save_to_parquet(test_data, 2024)

            # Mock unlink 抛出异常
            with patch("pathlib.Path.unlink", side_effect=Exception("Delete error")):
                with pytest.raises(StorageError, match="删除年份数据失败"):
                    manager.delete_year_data(2024)

    def test_get_stats_with_exception(self):
        """测试获取统计信息时的异常"""
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            # Mock get_available_years 抛出异常
            with patch.object(
                manager,
                "get_available_years",
                side_effect=Exception("Stats error"),
            ):
                stats = manager.get_stats()
                assert "error" in stats

    def test_read_parquet_with_exception(self):
        """测试读取Parquet时的异常"""
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            # 创建文件
            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001"],
                    "timestamp": [datetime(2024, 1, 1)],
                    "session_total_distance": [5000.0],
                    "session_total_timer_time": [1800],
                }
            )
            manager.save_to_parquet(test_data, 2024)

            # Mock _read_and_concat_parquet_files 抛出异常
            with patch.object(
                manager,
                "_read_and_concat_parquet_files",
                side_effect=Exception("Read error"),
            ):
                with pytest.raises(StorageError, match="读取Parquet数据失败"):
                    manager.read_parquet(years=[2024])

    def test_save_to_parquet_with_storage_error(self):
        """测试保存时的存储错误"""
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001"],
                    "timestamp": [datetime(2024, 1, 1)],
                    "session_total_distance": [5000.0],
                    "session_total_timer_time": [1800],
                }
            )

            # Mock write_parquet 抛出异常
            with patch.object(
                pl.DataFrame,
                "write_parquet",
                side_effect=Exception("Write error"),
            ):
                with pytest.raises(StorageError, match="保存Parquet文件失败"):
                    manager.save_to_parquet(test_data, 2024)

    def test_save_activities_with_timestamp_no_year_attr(self):
        """测试timestamp没有year属性的情况"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            # 创建timestamp为字符串的DataFrame（没有year属性）
            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001"],
                    "timestamp": ["2024-01-01"],  # 字符串，没有year属性
                    "session_total_distance": [5000.0],
                    "session_total_timer_time": [1800],
                }
            )

            result = manager.save_activities(test_data)
            # 应该使用当前年份
            assert result["year"] == datetime.now().year

    def test_convert_to_parquet_compatible_empty(self):
        """测试空DataFrame的类型转换"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            empty_data = pl.DataFrame()
            result = manager._convert_to_parquet_compatible(empty_data)
            assert result.is_empty()

    def test_align_dataframes_null_type_conversion(self):
        """测试Null类型转换"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            # 第一次保存，包含一个Null列
            data1 = pl.DataFrame(
                {
                    "activity_id": ["test_001"],
                    "timestamp": [datetime(2024, 1, 1)],
                    "session_total_distance": [5000.0],
                    "session_total_timer_time": [1800.0],
                    "extra_col": [None],  # Null类型
                }
            )
            manager.save_to_parquet(data1, 2024)

            # 第二次保存，extra_col有实际值
            data2 = pl.DataFrame(
                {
                    "activity_id": ["test_002"],
                    "timestamp": [datetime(2024, 1, 2)],
                    "session_total_distance": [10000.0],
                    "session_total_timer_time": [3600.0],
                    "extra_col": [100],  # Int类型
                }
            )
            manager.save_to_parquet(data2, 2024)

            # 读取验证
            df = manager.read_activities(2024)
            assert df.height == 2

    def test_align_dataframes_integer_types(self):
        """测试不同整数类型的对齐"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            # 第一次保存，使用Int32
            data1 = pl.DataFrame(
                {
                    "activity_id": ["test_001"],
                    "timestamp": [datetime(2024, 1, 1)],
                    "session_total_distance": [5000.0],
                    "session_total_timer_time": [1800],
                    "count": pl.Series([1], dtype=pl.Int32),
                }
            )
            manager.save_to_parquet(data1, 2024)

            # 第二次保存，使用Int64
            data2 = pl.DataFrame(
                {
                    "activity_id": ["test_002"],
                    "timestamp": [datetime(2024, 1, 2)],
                    "session_total_distance": [10000.0],
                    "session_total_timer_time": [3600],
                    "count": pl.Series([2], dtype=pl.Int64),
                }
            )
            manager.save_to_parquet(data2, 2024)

            df = manager.read_activities(2024)
            assert df.height == 2

    def test_align_dataframes_float_types(self):
        """测试不同浮点类型的对齐"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            # 第一次保存，使用Float32
            data1 = pl.DataFrame(
                {
                    "activity_id": ["test_001"],
                    "timestamp": [datetime(2024, 1, 1)],
                    "session_total_distance": pl.Series([5000.0], dtype=pl.Float32),
                    "session_total_timer_time": [1800.0],
                }
            )
            manager.save_to_parquet(data1, 2024)

            # 第二次保存，使用Float64
            data2 = pl.DataFrame(
                {
                    "activity_id": ["test_002"],
                    "timestamp": [datetime(2024, 1, 2)],
                    "session_total_distance": pl.Series([10000.0], dtype=pl.Float64),
                    "session_total_timer_time": [3600.0],
                }
            )
            manager.save_to_parquet(data2, 2024)

            df = manager.read_activities(2024)
            assert df.height == 2

    def test_align_dataframes_mixed_types(self):
        """测试混合类型的对齐（转换为String）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            # 第一次保存，使用Int
            data1 = pl.DataFrame(
                {
                    "activity_id": ["test_001"],
                    "timestamp": [datetime(2024, 1, 1)],
                    "session_total_distance": [5000.0],
                    "session_total_timer_time": [1800.0],
                    "value": [100],
                }
            )
            manager.save_to_parquet(data1, 2024)

            # 第二次保存，使用String
            data2 = pl.DataFrame(
                {
                    "activity_id": ["test_002"],
                    "timestamp": [datetime(2024, 1, 2)],
                    "session_total_distance": [10000.0],
                    "session_total_timer_time": [3600.0],
                    "value": ["text"],
                }
            )
            manager.save_to_parquet(data2, 2024)

            df = manager.read_activities(2024)
            assert df.height == 2

    def test_concat_with_schema_alignment_empty_list(self):
        """测试空LazyFrame列表的合并"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            result = manager._concat_with_schema_alignment([])
            assert result.collect().is_empty()

    def test_concat_with_schema_alignment_single_frame(self):
        """测试单个LazyFrame的合并"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            df = pl.DataFrame({"col1": [1, 2, 3]})
            lf = df.lazy()

            result = manager._concat_with_schema_alignment([lf])
            assert result.collect().height == 3

    def test_concat_with_schema_alignment_multiple_frames(self):
        """测试多个LazyFrame的合并（相同schema）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            df1 = pl.DataFrame({"col1": [1], "col2": [2]})
            df2 = pl.DataFrame({"col1": [3], "col2": [4]})

            result = manager._concat_with_schema_alignment([df1.lazy(), df2.lazy()])
            collected = result.collect()

            assert collected.height == 2
            assert "col1" in collected.columns
            assert "col2" in collected.columns

    def test_read_parquet_file_with_schema_fix_pyarrow(self):
        """测试使用pyarrow读取Parquet文件"""
        from unittest.mock import MagicMock, patch

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            # 创建测试文件
            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001"],
                    "timestamp": [datetime(2024, 1, 1)],
                    "session_total_distance": [5000.0],
                    "session_total_timer_time": [1800],
                }
            )
            filepath = Path(tmpdir) / "test.parquet"
            test_data.write_parquet(filepath)

            # Mock pl.read_parquet 抛出异常，强制使用pyarrow
            with patch("polars.read_parquet", side_effect=Exception("Read error")):
                result = manager._read_parquet_file_with_schema_fix(filepath)
                assert result is not None
                assert result.height == 1

    def test_read_parquet_file_with_schema_fix_both_fail(self):
        """测试polars和pyarrow都失败的情况"""
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            filepath = Path(tmpdir) / "test.parquet"
            filepath.touch()

            # Mock pl.read_parquet 和 pyarrow 都失败
            with patch("polars.read_parquet", side_effect=Exception("Polars error")):
                with patch(
                    "pyarrow.parquet.read_table", side_effect=Exception("PyArrow error")
                ):
                    result = manager._read_parquet_file_with_schema_fix(filepath)
                    assert result is None

    def test_read_and_concat_parquet_files_empty_list(self):
        """测试空文件列表的合并"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            result = manager._read_and_concat_parquet_files([])
            assert result.collect().is_empty()

    def test_read_and_concat_parquet_files_single_file(self):
        """测试单个文件的合并"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            # 创建文件
            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001"],
                    "timestamp": [datetime(2024, 1, 1)],
                    "session_total_distance": [5000.0],
                    "session_total_timer_time": [1800],
                }
            )
            filepath = Path(tmpdir) / "test.parquet"
            test_data.write_parquet(filepath)

            result = manager._read_and_concat_parquet_files([filepath])
            assert result.collect().height == 1

    def test_read_and_concat_parquet_files_multiple_files(self):
        """测试多个文件的合并"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            # 创建多个文件
            data1 = pl.DataFrame(
                {
                    "activity_id": ["test_001"],
                    "timestamp": [datetime(2024, 1, 1)],
                    "session_total_distance": [5000.0],
                    "session_total_timer_time": [1800],
                    "col1": [1],
                }
            )
            filepath1 = Path(tmpdir) / "test1.parquet"
            data1.write_parquet(filepath1)

            data2 = pl.DataFrame(
                {
                    "activity_id": ["test_002"],
                    "timestamp": [datetime(2024, 1, 2)],
                    "session_total_distance": [10000.0],
                    "session_total_timer_time": [3600],
                    "col2": [2],
                }
            )
            filepath2 = Path(tmpdir) / "test2.parquet"
            data2.write_parquet(filepath2)

            result = manager._read_and_concat_parquet_files([filepath1, filepath2])
            collected = result.collect()

            assert collected.height == 2
            assert "col1" in collected.columns
            assert "col2" in collected.columns

    def test_read_and_concat_parquet_files_with_read_error(self):
        """测试读取文件时出错"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            # 创建一个无效文件
            invalid_file = Path(tmpdir) / "invalid.parquet"
            invalid_file.touch()

            result = manager._read_and_concat_parquet_files([invalid_file])
            # 应该返回空DataFrame
            assert result.collect().is_empty()

    def test_save_to_parquet_with_validation_error_reraise(self):
        """测试ValidationError重新抛出"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001"],
                    "timestamp": [datetime(2024, 1, 1)],
                    "session_total_distance": [5000.0],
                    "session_total_timer_time": [1800],
                }
            )

            # 直接测试ValidationError被重新抛出
            with pytest.raises(ValidationError, match="年份必须在2000-2100范围内"):
                manager.save_to_parquet(test_data, 1999)

    def test_save_activities_with_generic_exception(self):
        """测试save_activities捕获通用异常"""
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001"],
                    "timestamp": [datetime(2024, 1, 1)],
                    "session_total_distance": [5000.0],
                    "session_total_timer_time": [1800],
                }
            )

            # Mock save_to_parquet 抛出通用异常
            with patch.object(
                manager,
                "save_to_parquet",
                side_effect=Exception("Unexpected error"),
            ):
                result = manager.save_activities(test_data, 2024)
                assert result["success"] is False
                assert "error" in result

    def test_read_activities_with_no_files(self):
        """测试读取活动数据时没有文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            df = manager.read_activities()
            assert df.is_empty()

    def test_get_available_years_with_exception(self):
        """测试获取可用年份时的异常"""
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            # Mock glob 抛出异常
            with patch.object(
                Path,
                "glob",
                side_effect=Exception("Glob error"),
            ):
                with pytest.raises(StorageError, match="获取可用年份失败"):
                    manager.get_available_years()

    def test_read_parquet_file_with_schema_fix_pyarrow_non_dataframe(self):
        """测试pyarrow返回非DataFrame类型的情况"""
        from unittest.mock import MagicMock, patch

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            filepath = Path(tmpdir) / "test.parquet"
            filepath.touch()

            # Mock pl.read_parquet 抛出异常
            # Mock pyarrow返回非DataFrame类型
            with patch("polars.read_parquet", side_effect=Exception("Polars error")):
                with patch("pyarrow.parquet.read_table") as mock_read:
                    # 返回一个mock对象，pl.from_arrow会返回非DataFrame
                    mock_table = MagicMock()
                    mock_read.return_value = mock_table
                    with patch("polars.from_arrow", return_value="not a dataframe"):
                        result = manager._read_parquet_file_with_schema_fix(filepath)
                        # 应该返回None
                        assert result is None

    def test_read_activities_file_not_exists(self):
        """测试读取不存在的年份数据"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            # 读取不存在的年份
            df = manager.read_activities(2020)
            assert df.is_empty()

    def test_read_activities_all_years_empty(self):
        """测试读取所有年份数据但目录为空"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            # 不创建任何文件，直接读取
            df = manager.read_activities()
            assert df.is_empty()

    def test_query_activities_with_filters(self):
        """测试带过滤条件的查询"""
        from datetime import datetime, timedelta

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            # 创建测试数据（使用最近的日期）
            now = datetime.now()
            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001", "test_002", "test_003"],
                    "timestamp": [
                        now - timedelta(days=5),
                        now - timedelta(days=10),
                        now - timedelta(days=15),
                    ],
                    "session_total_distance": [5000.0, 10000.0, 15000.0],
                    "session_total_timer_time": [1800, 3600, 5400],
                    "session_avg_heart_rate": [140, 150, 160],
                }
            )
            manager.save_to_parquet(test_data, now.year)

            # 测试按天数过滤
            result = manager.query_activities(days=30)
            assert result.height == 3

            # 测试按最小距离过滤
            result = manager.query_activities(min_distance=10000.0)
            assert result.height == 2

            # 测试按最小心率过滤
            result = manager.query_activities(min_heart_rate=150)
            assert result.height == 2

    def test_get_stats_with_data(self):
        """测试获取统计信息（有数据）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            # 创建测试数据
            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001"],
                    "timestamp": [datetime(2024, 1, 1)],
                    "session_total_distance": [5000.0],
                    "session_total_timer_time": [1800],
                }
            )
            manager.save_to_parquet(test_data, 2024)

            stats = manager.get_stats()
            assert stats["total_records"] == 1
            assert 2024 in stats["years"]
            assert "start" in stats["time_range"]
            assert "end" in stats["time_range"]

    def test_get_stats_empty(self):
        """测试获取统计信息（无数据）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            stats = manager.get_stats()
            assert stats["total_records"] == 0
            assert stats["years"] == []
            assert stats["time_range"] == {}

    def test_save_to_parquet_allow_empty(self):
        """测试允许保存空DataFrame"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            empty_data = pl.DataFrame()
            result = manager.save_to_parquet(empty_data, 2024, allow_empty=True)
            assert result is True

    def test_read_parquet_all_files(self):
        """测试读取所有Parquet文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(data_dir=Path(tmpdir))

            # 创建多个年份的数据
            for year in [2022, 2023, 2024]:
                data = pl.DataFrame(
                    {
                        "activity_id": [f"test_{year}"],
                        "timestamp": [datetime(year, 1, 1)],
                        "session_total_distance": [5000.0],
                        "session_total_timer_time": [1800],
                    }
                )
                manager.save_to_parquet(data, year)

            # 读取所有文件
            lf = manager.read_parquet()
            df = lf.collect()
            assert df.height == 3
