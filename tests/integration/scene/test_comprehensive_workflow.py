#!/usr/bin/env python3
"""
RunFlowAgent 全面集成测试
基于实际代码接口，测试模块间交互和数据流转
"""

import json

# 添加项目根目录到Python路径
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import polars as pl
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.core.analytics import AnalyticsEngine
from src.core.indexer import IndexManager
from src.core.schema import ParquetSchema
from src.core.storage import StorageManager


class TestComprehensiveWorkflow:
    """全面集成测试"""

    def setup_method(self):
        """测试前置设置"""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_data_dir = Path(self.temp_dir.name)

        # 初始化服务
        self.storage_manager = StorageManager(data_dir=self.test_data_dir / "data")
        self.index_manager = IndexManager(index_file=self.test_data_dir / "index.json")
        self.analytics_engine = AnalyticsEngine(self.storage_manager)
        self.schema = ParquetSchema()

        # 创建测试数据
        self.create_test_data()

    def teardown_method(self):
        """测试后置清理"""
        self.temp_dir.cleanup()

    def create_test_data(self):
        """创建测试数据"""
        # 创建符合Schema的测试数据
        activities_data = []

        for i in range(5):
            activity = {
                "activity_id": f"run_202401{i+1:02d}",
                "timestamp": datetime(2024, 1, i + 1, 8, 0, 0),  # 使用datetime类型
                "source_file": f"test_{i}.fit",
                "filename": f"test_{i}.fit",
                "serial_number": f"TEST{i:04d}",
                "time_created": datetime(2024, 1, i + 1, 8, 0, 0),  # 使用datetime类型
                "total_distance": 5000.0 + i * 1000,
                "total_timer_time": 1800.0 + i * 300,
                "total_calories": 300 + i * 50,
                "avg_heart_rate": 140 + i * 5,
                "max_heart_rate": 160 + i * 5,
                "record_count": 100 + i * 20,
            }
            activities_data.append(activity)

        self.test_df = pl.DataFrame(activities_data)
        print(f"✅ 创建测试数据: {len(self.test_df)} 条记录")

    def test_storage_operations(self):
        """测试存储操作"""
        print("\n=== 测试存储操作 ===")

        # 测试数据保存
        result = self.storage_manager.save_to_parquet(self.test_df, 2024)
        assert result is True
        print("✓ 数据保存测试通过")

        # 测试数据读取
        lazy_frame = self.storage_manager.read_parquet([2024])
        df = lazy_frame.collect()
        assert len(df) == len(self.test_df)
        print("✓ 数据读取测试通过")

        # 测试统计信息
        stats = self.storage_manager.get_stats()
        assert stats["total_records"] == len(self.test_df)
        print("✓ 统计信息测试通过")

    def test_analytics_calculations(self):
        """测试分析计算"""
        print("\n=== 测试分析计算 ===")

        # 测试VDOT计算
        vdot = self.analytics_engine.calculate_vdot(5000, 1800)
        assert isinstance(vdot, float)
        assert vdot > 0
        print(f"✓ VDOT计算测试通过: {vdot}")

        # 测试TSS计算
        heart_rate_data = pl.Series([140, 145, 150, 155, 160])
        tss = self.analytics_engine.calculate_tss(heart_rate_data, 1800)
        assert isinstance(tss, float)
        print(f"✓ TSS计算测试通过: {tss}")

        # 测试ATL计算
        atl = self.analytics_engine.calculate_atl([50, 60, 70, 80, 90])
        assert isinstance(atl, float)
        print(f"✓ ATL计算测试通过: {atl}")

        # 测试CTL计算
        ctl = self.analytics_engine.calculate_ctl([40, 45, 50, 55, 60] * 8)  # 40天数据
        assert isinstance(ctl, float)
        print(f"✓ CTL计算测试通过: {ctl}")

    def test_indexer_operations(self):
        """测试索引器操作"""
        print("\n=== 测试索引器操作 ===")

        # 测试指纹生成
        metadata = {
            "serial_number": "TEST12345",
            "time_created": "2024-01-01T08:00:00",
            "total_distance": 5000,
            "filename": "test.fit",
        }

        fingerprint = self.index_manager.generate_fingerprint(metadata)
        assert len(fingerprint) > 0
        print("✓ 指纹生成测试通过")

        # 测试重复检测
        exists = self.index_manager.exists(fingerprint)
        assert exists is False
        print("✓ 重复检测测试通过")

        # 测试索引添加
        result = self.index_manager.add(fingerprint, metadata)
        assert result is True
        print("✓ 索引添加测试通过")

        # 测试重复添加
        result = self.index_manager.add(fingerprint, metadata)
        assert result is False
        print("✓ 重复添加测试通过")

    def test_schema_operations(self):
        """测试Schema操作"""
        print("\n=== 测试Schema操作 ===")

        # 测试Schema获取
        schema = self.schema.get_schema()
        assert len(schema) > 0
        print("✓ Schema获取测试通过")

        # 测试必填字段
        required_fields = self.schema.get_required_fields()
        assert len(required_fields) > 0
        print("✓ 必填字段测试通过")

        # 测试默认值
        default_values = self.schema.get_default_values()
        assert len(default_values) > 0
        print("✓ 默认值测试通过")

    def test_error_handling(self):
        """测试错误处理"""
        print("\n=== 测试错误处理 ===")

        # 测试空数据保存 - 应该抛出 ValueError
        empty_df = pl.DataFrame()
        with pytest.raises(ValueError, match="数据框不能为空"):
            self.storage_manager.save_to_parquet(empty_df, 2024)
        print("✓ 空数据处理测试通过")

        # 测试边界值计算 - 零距离应该抛出 ValueError
        with pytest.raises(ValueError, match="距离和时间必须为正数"):
            self.analytics_engine.calculate_vdot(0, 1800)
        print("✓ 边界值计算测试通过")

        # 测试无效年份读取
        lazy_frame = self.storage_manager.read_parquet([9999])  # 不存在的年份
        df = lazy_frame.collect()
        assert len(df) == 0
        print("✓ 无效年份读取测试通过")

    def test_performance(self):
        """测试性能"""
        print("\n=== 测试性能 ===")

        # 大数据量性能测试
        large_data = []
        for i in range(100):
            activity = {
                "activity_id": f"run_{i:06d}",
                "timestamp": f"2024-01-{(i % 30) + 1:02d}T08:00:00",
                "source_file": f"test_{i}.fit",
                "filename": f"test_{i}.fit",
                "serial_number": f"TEST{i:04d}",
                "time_created": f"2024-01-{(i % 30) + 1:02d}T08:00:00",
                "total_distance": 5000.0 + (i % 5000),
                "total_timer_time": 1800.0 + (i % 1200),
                "total_calories": 300 + (i % 200),
                "avg_heart_rate": 140 + (i % 40),
                "max_heart_rate": 160 + (i % 30),
                "record_count": 100 + (i % 100),
            }
            large_data.append(activity)

        large_df = pl.DataFrame(large_data)

        # 保存性能测试
        start_time = time.time()
        result = self.storage_manager.save_to_parquet(large_df, 2024)
        save_time = time.time() - start_time

        assert result is True
        assert save_time < 5.0
        print(f"✓ 保存性能测试通过: {save_time:.2f}秒")

        # 读取性能测试
        start_time = time.time()
        lazy_frame = self.storage_manager.read_parquet([2024])
        df = lazy_frame.collect()
        read_time = time.time() - start_time

        assert len(df) == len(large_df)
        assert read_time < 3.0
        print(f"✓ 读取性能测试通过: {read_time:.2f}秒")


def test_cli_commands():
    """测试CLI命令"""
    print("\n=== 测试CLI命令 ===")

    import subprocess

    # 测试stats命令
    result = subprocess.run(
        [sys.executable, "-m", "src.cli", "stats"],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0
    print("✓ CLI stats命令测试通过")

    # 测试version命令
    result = subprocess.run(
        [sys.executable, "-m", "src.cli", "version"],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0
    assert "v0.3.0" in result.stdout or "Nanobot Runner" in result.stdout
    print("✓ CLI version命令测试通过")


if __name__ == "__main__":
    """
    直接运行全面集成测试
    """
    print("🚀 开始执行RunFlowAgent全面集成测试")

    # 创建测试实例
    test_instance = TestComprehensiveWorkflow()

    try:
        test_instance.setup_method()

        # 执行测试用例
        test_instance.test_storage_operations()
        test_instance.test_analytics_calculations()
        test_instance.test_indexer_operations()
        test_instance.test_schema_operations()
        test_instance.test_error_handling()
        test_instance.test_performance()

        # 执行CLI测试
        test_cli_commands()

        print("\n🎉 所有全面集成测试执行完成！")
        print("✅ 测试结果: 通过")

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 测试执行异常: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    finally:
        test_instance.teardown_method()
