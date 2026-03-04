#!/usr/bin/env python3
"""
RunFlowAgent 真实场景集成测试
基于开发工程师交付的完整代码包，测试真实业务流程

测试目标：
- 验证模块间接口交互的正确性
- 测试数据流转的完整性
- 验证业务逻辑的端到端正确性
- 发现潜在bug和性能问题
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
from src.core.importer import ImportService
from src.core.indexer import IndexManager
from src.core.parser import FitParser
from src.core.schema import ParquetSchema
from src.core.storage import StorageManager


class TestRealWorkflow:
    """真实业务流程集成测试"""

    def setup_method(self):
        """测试前置设置"""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_data_dir = Path(self.temp_dir.name)

        # 初始化所有服务
        self.storage_manager = StorageManager(data_dir=self.test_data_dir / "data")
        self.index_manager = IndexManager(index_file=self.test_data_dir / "index.json")
        self.analytics_engine = AnalyticsEngine(self.storage_manager)
        self.schema = ParquetSchema()

        # 创建模拟的真实FIT文件数据
        self.create_realistic_test_data()

    def teardown_method(self):
        """测试后置清理"""
        self.temp_dir.cleanup()

    def create_realistic_test_data(self):
        """创建真实的测试数据"""
        # 创建模拟的跑步活动数据
        activities_data = []

        # 生成7天的跑步数据
        for i in range(7):
            activity = {
                "activity_id": f"run_202401{i+1:02d}",
                "timestamp": datetime(2024, 1, i + 1, 8, 0, 0),  # 使用datetime类型
                "source_file": f"test_{i}.fit",
                "filename": f"test_{i}.fit",
                "serial_number": f"TEST{i:04d}",
                "time_created": datetime(2024, 1, i + 1, 8, 0, 0),  # 使用datetime类型
                "total_distance": float(5000 + i * 1000),  # 5km到11km，转换为float
                "total_timer_time": float(1800 + i * 300),  # 30min到48min，转换为float
                "total_calories": int(300 + i * 50),  # 300cal到600cal，转换为int
                "avg_heart_rate": int(140 + i * 5),  # 140bpm到170bpm，转换为int
                "max_heart_rate": int(160 + i * 5),  # 160bpm到190bpm，转换为int
                "record_count": int(100 + i * 20),  # 记录数
                "sport": "running",
                "total_elapsed_time": 1820 + i * 300,
                "avg_speed": 2.7 + i * 0.1,  # 2.7m/s到3.3m/s
                "max_speed": 3.5 + i * 0.1,  # 3.5m/s到4.1m/s
                "total_ascent": 50 + i * 10,  # 50m到110m
                "total_descent": 45 + i * 10,  # 45m到105m
                "avg_cadence": 170 + i * 2,  # 170spm到182spm
                "max_cadence": 185 + i * 2,  # 185spm到197spm
                "training_effect": 3.0 + i * 0.2,  # 3.0到4.2
                "avg_temperature": 20 + i,  # 20°C到26°C
                "year": 2024,  # 添加年份字段
            }
            activities_data.append(activity)

        # 创建Polars DataFrame
        self.real_activities_df = pl.DataFrame(activities_data)

        print(f"✅ 创建真实测试数据: {len(self.real_activities_df)} 条记录")

    def test_storage_integration(self):
        """测试存储模块集成"""
        print("\n=== 测试存储模块集成 ===")

        # 测试数据保存
        result = self.storage_manager.save_activities(self.real_activities_df)
        assert result["success"] is True
        assert result["records_saved"] == len(self.real_activities_df)
        print("✓ 数据保存测试通过")

        # 测试数据读取
        loaded_df = self.storage_manager.load_activities()
        assert len(loaded_df) == len(self.real_activities_df)
        print("✓ 数据读取测试通过")

        # 测试统计信息
        stats = self.storage_manager.get_stats()
        assert stats["total_records"] == len(self.real_activities_df)
        print("✓ 统计信息测试通过")

    def test_analytics_integration(self):
        """测试分析引擎集成"""
        print("\n=== 测试分析引擎集成 ===")

        # 先保存数据
        self.storage_manager.save_activities(self.real_activities_df)

        # 测试VDOT计算
        vdot_result = self.analytics_engine.calculate_vdot(5000, 1800)
        assert isinstance(vdot_result, float)
        assert vdot_result > 0
        print(f"✓ VDOT计算测试通过: {vdot_result}")

        # 测试跑步摘要
        summary = self.analytics_engine.get_running_summary()
        assert "total_runs" in summary
        assert "total_distance" in summary
        print("✓ 跑步摘要测试通过")

        # 测试趋势分析
        trend = self.analytics_engine.get_vdot_trend(days=7)
        assert isinstance(trend, dict)
        print("✓ 趋势分析测试通过")

    def test_schema_validation(self):
        """测试Schema验证"""
        print("\n=== 测试Schema验证 ===")

        # 测试Schema获取
        schema = self.schema.get_schema()
        assert len(schema) > 0
        print("✓ Schema获取测试通过")

        # 测试必填字段
        required_fields = self.schema.get_required_fields()
        assert len(required_fields) > 0
        print("✓ 必填字段测试通过")

        # 测试数据验证
        validation_result = self.schema.validate_dataframe(self.real_activities_df)
        assert validation_result["valid"] is True
        print("✓ 数据验证测试通过")

    def test_indexer_integration(self):
        """测试索引器集成"""
        print("\n=== 测试索引器集成 ===")

        # 测试指纹生成
        test_metadata = {
            "serial_number": "TEST12345",
            "time_created": "2024-01-01T08:00:00",
            "total_distance": 5000,
            "filename": "test.fit",
        }

        fingerprint = self.index_manager.generate_fingerprint(test_metadata)
        assert len(fingerprint) > 0
        print("✓ 指纹生成测试通过")

        # 测试重复检测
        exists = self.index_manager.exists(fingerprint)
        assert exists is False
        print("✓ 重复检测测试通过")

        # 测试添加索引
        result = self.index_manager.add(fingerprint, test_metadata)
        assert result is True
        print("✓ 索引添加测试通过")

        # 测试重复添加
        result = self.index_manager.add(fingerprint, test_metadata)
        assert result is False
        print("✓ 重复添加测试通过")

    def test_full_data_flow(self):
        """测试完整数据流"""
        print("\n=== 测试完整数据流 ===")

        # 模拟完整的数据处理流程
        start_time = time.time()

        # 1. 数据验证
        validation_result = self.schema.validate_dataframe(self.real_activities_df)
        assert validation_result["valid"] is True

        # 2. 数据保存
        save_result = self.storage_manager.save_activities(self.real_activities_df)
        assert save_result["success"] is True

        # 3. 数据分析
        summary = self.analytics_engine.get_running_summary()
        assert summary["total_runs"].item() == len(self.real_activities_df)

        # 4. 性能验证
        elapsed_time = time.time() - start_time
        assert elapsed_time < 5.0  # 完整流程应在5秒内完成

        print(f"✓ 完整数据流测试通过，耗时: {elapsed_time:.2f}秒")

    def test_error_handling_scenarios(self):
        """测试错误处理场景"""
        print("\n=== 测试错误处理场景 ===")

        # 测试空数据处理
        empty_df = pl.DataFrame()

        # 空数据保存
        save_result = self.storage_manager.save_activities(empty_df)
        assert save_result["success"] is False
        print("✓ 空数据处理测试通过")

        # 测试无效数据验证
        invalid_data = {"invalid_column": [1, 2, 3]}
        invalid_df = pl.DataFrame(invalid_data)

        validation_result = self.schema.validate_dataframe(invalid_df)
        assert validation_result["valid"] is False
        print("✓ 无效数据验证测试通过")

        # 测试边界值计算
        zero_vdot = self.analytics_engine.calculate_vdot(0, 1800)
        assert zero_vdot == 0.0
        print("✓ 边界值计算测试通过")


def test_cli_integration():
    """测试CLI集成"""
    print("\n=== 测试CLI集成 ===")

    import subprocess

    # 测试stats命令
    result = subprocess.run(
        [sys.executable, "-m", "src.cli", "stats"],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0
    assert "总记录数" in result.stdout or "total_records" in result.stdout
    print("✓ CLI stats命令测试通过")

    # 测试version命令
    result = subprocess.run(
        [sys.executable, "-m", "src.cli", "version"],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0
    assert "0.1.0" in result.stdout
    print("✓ CLI version命令测试通过")


def test_performance_benchmarks():
    """测试性能基准"""
    print("\n=== 测试性能基准 ===")

    # 初始化测试实例
    test_instance = TestRealWorkflow()
    test_instance.setup_method()

    try:
        # 大数据量性能测试
        large_activities_data = []
        for i in range(1000):  # 1000条记录
            activity = {
                "activity_id": f"run_{i:06d}",
                "timestamp": f"2024-01-{(i % 30) + 1:02d}T08:00:00",
                "total_distance": 5000 + (i % 5000),
                "total_timer_time": 1800 + (i % 1200),
                "avg_heart_rate": 140 + (i % 40),
            }
            large_activities_data.append(activity)

        large_df = pl.DataFrame(large_activities_data)

        # 性能测试：数据保存
        start_time = time.time()
        test_instance.storage_manager.save_activities(large_df)
        save_time = time.time() - start_time

        assert save_time < 10.0  # 1000条记录保存应在10秒内
        print(f"✓ 大数据量保存性能测试通过: {save_time:.2f}秒")

        # 性能测试：数据查询
        start_time = time.time()
        stats = test_instance.storage_manager.get_stats()
        query_time = time.time() - start_time

        assert query_time < 3.0  # 统计查询应在3秒内
        print(f"✓ 大数据量查询性能测试通过: {query_time:.2f}秒")

    finally:
        test_instance.teardown_method()


if __name__ == "__main__":
    """
    直接运行真实场景集成测试
    """
    print("🚀 开始执行RunFlowAgent真实场景集成测试")

    # 创建测试实例
    test_instance = TestRealWorkflow()

    try:
        test_instance.setup_method()

        # 执行测试用例
        test_instance.test_storage_integration()
        test_instance.test_analytics_integration()
        test_instance.test_schema_validation()
        test_instance.test_indexer_integration()
        test_instance.test_full_data_flow()
        test_instance.test_error_handling_scenarios()

        # 执行CLI集成测试
        test_cli_integration()

        # 执行性能基准测试
        test_performance_benchmarks()

        print("\n🎉 所有真实场景集成测试执行完成！")
        print("✅ 测试结果: 通过")

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 测试执行异常: {e}")
        sys.exit(1)

    finally:
        test_instance.teardown_method()
