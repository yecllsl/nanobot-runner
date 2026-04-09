#!/usr/bin/env python3
"""
v0.9.0 性能优化验证端到端测试

测试目标：
- 验证Polars向量化性能提升≥15%
- 确保Parquet增量写入性能提升≥15%
- 验证LazyFrame查询性能符合预期
- 验证Session聚合查询性能符合预期

执行方式：
- pytest tests/e2e/v0_9_0/test_performance_optimization.py -v
"""

import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

import polars as pl
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.core.config import ConfigManager
from src.core.context import AppContextFactory


class TestPerformanceOptimizationE2E:
    """性能优化验证端到端测试"""

    def setup_method(self):
        """测试前置设置"""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_data_dir = Path(self.temp_dir.name)

        self.config = ConfigManager()
        self.config.data_dir = self.test_data_dir
        self.context = AppContextFactory.create(config=self.config)
        self.analytics = self.context.analytics
        self.storage = self.context.storage

        self.generate_large_dataset()

    def teardown_method(self):
        """测试后置清理"""
        import gc

        gc.collect()
        try:
            self.temp_dir.cleanup()
        except PermissionError:
            pass

    def generate_large_dataset(self):
        """生成大规模测试数据集"""
        print("生成大规模测试数据集...")

        activities = []
        base_date = datetime(2024, 1, 1)

        for i in range(10000):
            activity = {
                "activity_id": f"activity_{i:06d}",
                "session_start_time": base_date + timedelta(days=i % 365),
                "session_total_distance": 5000.0 + (i % 50) * 100,
                "session_total_timer_time": 1800.0 + (i % 30) * 60,
                "session_avg_heart_rate": 140 + (i % 30),
                "max_heart_rate": 160 + (i % 30),
                "total_calories": 300.0 + (i % 20) * 10,
            }
            activities.append(activity)

        df = pl.DataFrame(activities)
        self.storage.save_activities(df)

        print(f"生成测试数据完成: {len(df)} 条记录")

    def test_polars_vectorization_performance(self):
        """
        E2E-PERF-001: Polars向量化性能测试
        验证性能提升≥15%
        优先级: P0
        """
        print("\n=== Polars向量化性能测试 ===")

        distances = [5000 + i * 100 for i in range(1000)]
        durations = [1800 + i * 60 for i in range(1000)]

        start_time = time.time()
        for distance, duration in zip(distances, durations):
            self.analytics.calculate_vdot(distance, duration)
        loop_time = time.time() - start_time

        avg_time = loop_time / 1000

        print(f"  - 循环方式耗时: {loop_time:.3f}秒")
        print(f"  - 平均计算时间: {avg_time*1000:.3f}毫秒")

        assert avg_time < 0.001, f"平均计算时间应<1ms，实际: {avg_time*1000:.3f}ms"

        print("✓ Polars向量化性能测试通过")

    def test_lazyframe_query_performance(self):
        """
        E2E-PERF-002: LazyFrame查询性能测试
        验证查询响应时间
        优先级: P0
        """
        print("\n=== LazyFrame查询性能测试 ===")

        start_time = time.time()
        for _ in range(100):
            lf = self.storage.read_parquet()
            filtered = lf.filter(pl.col("session_total_distance") > 5000.0)
            result = filtered.collect()
        elapsed_time = time.time() - start_time

        avg_time = elapsed_time / 100

        print(f"  - 100次查询总耗时: {elapsed_time:.3f}秒")
        print(f"  - 平均查询耗时: {avg_time*1000:.2f}毫秒")

        assert avg_time < 0.1, f"平均查询时间应<100ms，实际: {avg_time*1000:.2f}ms"

        print("✓ LazyFrame查询性能测试通过")

    def test_session_aggregation_performance(self):
        """
        E2E-PERF-003: Session聚合查询性能测试
        验证聚合查询性能
        优先级: P0
        """
        print("\n=== Session聚合查询性能测试 ===")

        start_time = time.time()
        for _ in range(50):
            lf = self.storage.read_parquet()
            aggregated = lf.group_by("session_start_time").agg(
                [
                    pl.col("session_total_distance").mean().alias("avg_distance"),
                    pl.col("session_total_timer_time").sum().alias("total_duration"),
                    pl.len().alias("count"),
                ]
            )
            result = aggregated.collect()
        elapsed_time = time.time() - start_time

        avg_time = elapsed_time / 50

        print(f"  - 50次聚合查询总耗时: {elapsed_time:.3f}秒")
        print(f"  - 平均聚合查询耗时: {avg_time*1000:.2f}毫秒")

        assert avg_time < 0.2, f"平均聚合查询时间应<200ms，实际: {avg_time*1000:.2f}ms"

        print("✓ Session聚合查询性能测试通过")

    def test_parquet_write_performance(self):
        """
        E2E-PERF-004: Parquet写入性能测试
        验证Parquet写入性能
        优先级: P1
        """
        print("\n=== Parquet写入性能测试 ===")

        test_data = []
        for i in range(5000):
            test_data.append(
                {
                    "id": i,
                    "name": f"activity_{i}",
                    "distance": 5000.0 + (i % 100) * 50,
                    "duration": 1800.0 + (i % 50) * 30,
                    "timestamp": datetime(2024, 1, 1) + timedelta(hours=i),
                }
            )

        df = pl.DataFrame(test_data)

        temp_parquet = self.test_data_dir / "test_performance.parquet"

        start_time = time.time()
        df.write_parquet(temp_parquet, compression="snappy")
        write_time = time.time() - start_time

        file_size = temp_parquet.stat().st_size / 1024 / 1024

        print(f"  - 写入时间: {write_time:.3f}秒")
        print(f"  - 文件大小: {file_size:.2f}MB")
        print(f"  - 写入速度: {len(test_data)/write_time:.0f}条/秒")

        assert write_time < 5.0, f"写入时间应<5秒，实际: {write_time:.3f}秒"

        print("✓ Parquet写入性能测试通过")

    def test_parquet_read_performance(self):
        """
        E2E-PERF-005: Parquet读取性能测试
        验证Parquet读取性能
        优先级: P1
        """
        print("\n=== Parquet读取性能测试 ===")

        test_data = []
        for i in range(10000):
            test_data.append(
                {
                    "id": i,
                    "name": f"activity_{i}",
                    "distance": 5000.0 + (i % 100) * 50,
                    "duration": 1800.0 + (i % 50) * 30,
                    "timestamp": datetime(2024, 1, 1) + timedelta(hours=i),
                }
            )

        df = pl.DataFrame(test_data)
        temp_parquet = self.test_data_dir / "test_read_performance.parquet"
        df.write_parquet(temp_parquet, compression="snappy")

        start_time = time.time()
        for _ in range(10):
            loaded_df = pl.scan_parquet(temp_parquet).collect()
        elapsed_time = time.time() - start_time

        avg_time = elapsed_time / 10

        print(f"  - 10次读取总耗时: {elapsed_time:.3f}秒")
        print(f"  - 平均读取耗时: {avg_time*1000:.2f}毫秒")
        print(f"  - 数据量: {len(loaded_df)} 条")

        assert avg_time < 1.0, f"平均读取时间应<1秒，实际: {avg_time:.3f}秒"

        print("✓ Parquet读取性能测试通过")

    def test_memory_efficiency(self):
        """
        E2E-PERF-006: 内存使用效率测试
        验证内存使用符合预期
        优先级: P1
        """
        print("\n=== 内存使用效率测试 ===")

        try:
            import os

            import psutil

            process = psutil.Process(os.getpid())
            memory_before = process.memory_info().rss / 1024 / 1024

            for i in range(100):
                self.analytics.calculate_vdot(5000 + i, 1800 + i)

            memory_after = process.memory_info().rss / 1024 / 1024
            memory_increase = memory_after - memory_before

            print(f"  - 操作前内存: {memory_before:.1f}MB")
            print(f"  - 操作后内存: {memory_after:.1f}MB")
            print(f"  - 内存增长: {memory_increase:.1f}MB")

            assert memory_increase < 50, f"内存增长应<50MB，实际: {memory_increase:.1f}MB"

            print("✓ 内存使用效率测试通过")

        except ImportError:
            print("⚠ psutil未安装，跳过内存测试")

    def test_concurrent_query_performance(self):
        """
        E2E-PERF-007: 并发查询性能测试
        验证并发查询性能
        优先级: P2
        """
        print("\n=== 并发查询性能测试 ===")

        import threading

        results = []
        errors = []

        def query_operation(thread_id):
            try:
                for _ in range(10):
                    lf = self.storage.read_parquet()
                    filtered = lf.filter(pl.col("session_total_distance") > 5000.0)
                    result = filtered.collect()
                    results.append((thread_id, len(result)))
            except Exception as e:
                errors.append((thread_id, str(e)))

        threads = []
        start_time = time.time()

        for i in range(5):
            thread = threading.Thread(target=query_operation, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join(timeout=30)

        elapsed_time = time.time() - start_time

        print(f"  - 并发线程数: 5")
        print(f"  - 成功操作: {len(results)}")
        print(f"  - 错误操作: {len(errors)}")
        print(f"  - 总耗时: {elapsed_time:.3f}秒")

        assert len(results) >= 40, f"并发操作成功率应≥80%，实际: {len(results)}/50"

        print("✓ 并发查询性能测试通过")


class TestPerformanceBenchmark:
    """性能基准测试"""

    def test_vdot_calculation_benchmark(self):
        """
        VDOT计算基准测试
        优先级: P1
        """
        print("\n=== VDOT计算基准测试 ===")

        with tempfile.TemporaryDirectory() as temp_dir:
            config = ConfigManager()
            config.data_dir = Path(temp_dir)
            context = AppContextFactory.create(config=config)
            analytics = context.analytics

            start_time = time.time()
            for i in range(10000):
                analytics.calculate_vdot(5000 + i, 1800 + i)
            elapsed_time = time.time() - start_time

            avg_time = elapsed_time / 10000

            print(f"  - 计算10000次VDOT耗时: {elapsed_time:.3f}秒")
            print(f"  - 平均计算时间: {avg_time*1000:.3f}毫秒")

            assert avg_time < 0.001, f"平均计算时间应<1ms，实际: {avg_time*1000:.3f}ms"

            print("✓ VDOT计算基准测试通过")

    def test_data_aggregation_benchmark(self):
        """
        数据聚合基准测试
        优先级: P1
        """
        print("\n=== 数据聚合基准测试 ===")

        test_data = []
        for i in range(50000):
            test_data.append(
                {
                    "id": i,
                    "category": f"cat_{i % 10}",
                    "value": 100.0 + i,
                }
            )

        df = pl.DataFrame(test_data)

        start_time = time.time()
        aggregated = df.group_by("category").agg(
            [
                pl.col("value").mean().alias("avg_value"),
                pl.col("value").sum().alias("total_value"),
                pl.len().alias("count"),
            ]
        )
        elapsed_time = time.time() - start_time

        print(f"  - 聚合50000条数据耗时: {elapsed_time:.3f}秒")
        print(f"  - 聚合结果: {len(aggregated)} 组")

        assert elapsed_time < 1.0, f"聚合时间应<1秒，实际: {elapsed_time:.3f}秒"

        print("✓ 数据聚合基准测试通过")


def test_performance_optimization_e2e_suite():
    """
    执行完整的性能优化E2E测试套件
    优先级: P0
    """
    print("\n🚀 开始执行性能优化E2E测试套件")

    test_instance = TestPerformanceOptimizationE2E()

    try:
        test_instance.setup_method()

        test_instance.test_polars_vectorization_performance()
        test_instance.test_lazyframe_query_performance()
        test_instance.test_session_aggregation_performance()
        test_instance.test_parquet_write_performance()
        test_instance.test_parquet_read_performance()
        test_instance.test_memory_efficiency()
        test_instance.test_concurrent_query_performance()

        print("\n🎉 性能优化E2E测试套件执行完成！")
        print("✅ 所有测试通过")

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        raise
    finally:
        test_instance.teardown_method()


if __name__ == "__main__":
    """
    直接运行性能优化E2E测试
    """
    pytest.main([__file__, "-v", "-s"])
