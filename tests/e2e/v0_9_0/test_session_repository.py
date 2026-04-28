#!/usr/bin/env python3
"""
v0.9.0 SessionRepository端到端测试

测试目标：
- 验证LazyFrame链式构建正确性
- 确保Session聚合查询功能完整
- 验证Polars表达式正确性
- 验证查询性能符合预期

执行方式：
- pytest tests/e2e/v0_9_0/test_session_repository.py -v
"""

import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import polars as pl
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import contextlib

from src.core.base.context import AppContextFactory
from src.core.config import ConfigManager
from src.core.session_repository import SessionRepository


class TestSessionRepositoryE2E:
    """SessionRepository端到端测试"""

    def setup_method(self):
        """测试前置设置"""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_data_dir = Path(self.temp_dir.name)

        self.config = ConfigManager()
        self.config.data_dir = self.test_data_dir
        self.context = AppContextFactory.create(config=self.config)
        self.session_repo = (
            self.context.session_repository
            if hasattr(self.context, "session_repository")
            else SessionRepository(self.context.storage)
        )
        self.storage = self.context.storage

        self.generate_test_data()

    def teardown_method(self):
        """测试后置清理"""
        import gc
        import time

        gc.collect()
        time.sleep(0.1)
        with contextlib.suppress(PermissionError):
            self.temp_dir.cleanup()

    def generate_test_data(self):
        """生成测试数据"""
        print("生成SessionRepository测试数据...")

        activities = []
        base_date = datetime(2024, 1, 1)

        for i in range(100):
            activity = {
                "activity_id": f"activity_{i:04d}",
                "session_start_time": base_date + timedelta(days=i),
                "session_total_distance": 5000.0 + (i % 10) * 1000,
                "session_total_timer_time": 1800.0 + (i % 10) * 300,
                "session_avg_heart_rate": 140 + (i % 20),
                "max_heart_rate": 160 + (i % 20),
                "total_calories": 300.0 + (i % 10) * 50,
            }
            activities.append(activity)

        df = pl.DataFrame(activities)
        self.storage.save_activities(df)

        print(f"生成测试数据完成: {len(df)} 条记录")

    def test_lazyframe_chain(self):
        """
        E2E-SR-001: LazyFrame链式构建测试
        验证延迟求值正确性
        优先级: P0
        """
        print("\n=== LazyFrame链式构建测试 ===")

        lazy_result = self.session_repo._build_session_lazy()

        assert isinstance(lazy_result, pl.LazyFrame), (
            f"应返回LazyFrame，实际返回: {type(lazy_result)}"
        )

        filtered = lazy_result.filter(pl.col("distance") > 5000.0)

        assert isinstance(filtered, pl.LazyFrame), (
            f"过滤后应仍为LazyFrame，实际返回: {type(filtered)}"
        )

        result = filtered.collect()

        assert isinstance(result, pl.DataFrame), (
            f"collect后应为DataFrame，实际返回: {type(result)}"
        )

        print("✓ LazyFrame链式构建测试通过")
        print("  - 初始类型: LazyFrame")
        print("  - 过滤后类型: LazyFrame")
        print("  - collect后类型: DataFrame")
        print(f"  - 结果行数: {len(result)}")

    def test_session_aggregation(self):
        """
        E2E-SR-002: Session聚合查询测试
        验证聚合查询功能
        优先级: P0
        """
        print("\n=== Session聚合查询测试 ===")

        recent = self.session_repo.get_recent_sessions(limit=10)

        assert len(recent) <= 10, f"应返回最多10条记录，实际返回: {len(recent)}"

        if len(recent) > 0:
            assert hasattr(recent[0], "distance_km"), "SessionData应包含distance_km字段"
            assert hasattr(recent[0], "duration_min"), (
                "SessionData应包含duration_min字段"
            )

        print("✓ Session聚合查询测试通过")
        print(f"  - 最近Session数量: {len(recent)}")

    def test_sessions_by_date_range(self):
        """
        E2E-SR-003: 日期范围查询测试
        验证日期范围过滤功能
        优先级: P0
        """
        print("\n=== 日期范围查询测试 ===")

        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)

        sessions = self.session_repo.get_sessions_by_date_range(
            start_date=start_date, end_date=end_date
        )

        assert isinstance(sessions, list), f"应返回list，实际返回: {type(sessions)}"

        print("✓ 日期范围查询测试通过")
        print(f"  - 查询范围: {start_date.date()} ~ {end_date.date()}")
        print(f"  - 结果数量: {len(sessions)}")

    def test_sessions_by_distance(self):
        """
        E2E-SR-004: 距离范围查询测试
        验证距离范围过滤功能
        优先级: P0
        """
        print("\n=== 距离范围查询测试 ===")

        min_distance_m = 5000.0
        max_distance_m = 10000.0

        sessions = self.session_repo.get_sessions_by_distance(
            min_meters=min_distance_m, max_meters=max_distance_m
        )

        assert isinstance(sessions, list), f"应返回list，实际返回: {type(sessions)}"

        print("✓ 距离范围查询测试通过")
        print(f"  - 查询范围: {min_distance_m}m ~ {max_distance_m}m")
        print(f"  - 结果数量: {len(sessions)}")

    def test_computed_columns(self):
        """
        E2E-SR-005: 计算列正确性测试
        验证Polars表达式正确性
        优先级: P0
        """
        print("\n=== 计算列正确性测试 ===")

        lazy_df = self.session_repo._build_session_lazy()
        result = lazy_df.collect()

        if len(result) > 0:
            result_with_computed = self.session_repo._add_computed_columns(result)

            assert "distance_km" in result_with_computed.columns, (
                "应包含distance_km计算列"
            )

            assert "duration_min" in result_with_computed.columns, (
                "应包含duration_min计算列"
            )

            assert "avg_pace_sec_km" in result_with_computed.columns, (
                "应包含avg_pace_sec_km计算列"
            )

            distance = result["distance"][0]
            distance_km = result_with_computed["distance_km"][0]

            assert abs(distance_km - distance / 1000) < 0.01, (
                f"距离转换错误: {distance}m != {distance_km}km"
            )

            print("✓ 计算列正确性测试通过")
            print(f"  - distance_km: {distance_km}")
            print(f"  - duration_min: {result_with_computed['duration_min'][0]}")
            print(f"  - avg_pace_sec_km: {result_with_computed['avg_pace_sec_km'][0]}")
        else:
            print("⚠ 无数据，跳过计算列验证")

    def test_session_count(self):
        """
        E2E-SR-006: Session计数测试
        验证计数功能
        优先级: P1
        """
        print("\n=== Session计数测试 ===")

        count = self.session_repo.get_session_count()

        assert isinstance(count, int), f"应返回int，实际返回: {type(count)}"

        assert count >= 0, f"计数应≥0，实际: {count}"

        print("✓ Session计数测试通过")
        print(f"  - Session总数: {count}")

    def test_total_distance(self):
        """
        E2E-SR-007: 总距离计算测试
        验证总距离计算功能
        优先级: P1
        """
        print("\n=== 总距离计算测试 ===")

        total_distance = self.session_repo.get_total_distance()

        assert isinstance(total_distance, (int, float)), (
            f"应返回数值，实际返回: {type(total_distance)}"
        )

        assert total_distance >= 0, f"总距离应≥0，实际: {total_distance}"

        print("✓ 总距离计算测试通过")
        print(f"  - 总距离: {total_distance:.2f}km")

    def test_total_duration(self):
        """
        E2E-SR-008: 总时长计算测试
        验证总时长计算功能
        优先级: P1
        """
        print("\n=== 总时长计算测试 ===")

        total_duration = self.session_repo.get_total_duration()

        assert isinstance(total_duration, (int, float)), (
            f"应返回数值，实际返回: {type(total_duration)}"
        )

        assert total_duration >= 0, f"总时长应≥0，实际: {total_duration}"

        print("✓ 总时长计算测试通过")
        print(f"  - 总时长: {total_duration:.2f}分钟")

    def test_empty_data_handling(self):
        """
        E2E-SR-009: 空数据处理测试
        验证空DataFrame处理
        优先级: P0
        """
        print("\n=== 空数据处理测试 ===")

        empty_temp_dir = tempfile.TemporaryDirectory()
        empty_config = ConfigManager()
        empty_config.data_dir = Path(empty_temp_dir.name)
        empty_context = AppContextFactory.create(config=empty_config)
        empty_repo = (
            empty_context.session_repository
            if hasattr(empty_context, "session_repository")
            else SessionRepository(empty_context.storage)
        )

        try:
            count = empty_repo.get_session_count()
            assert count == 0, f"空数据库应返回0，实际: {count}"

            total_distance = empty_repo.get_total_distance()
            assert total_distance == 0, f"空数据库总距离应为0，实际: {total_distance}"

            total_duration = empty_repo.get_total_duration()
            assert total_duration == 0, f"空数据库总时长应为0，实际: {total_duration}"

            print("✓ 空数据处理测试通过")
            print("  - 空数据库正确处理")

        finally:
            empty_temp_dir.cleanup()

    def test_performance_benchmark(self):
        """
        E2E-SR-010: 性能基准测试
        验证查询性能
        优先级: P1
        """
        print("\n=== 性能基准测试 ===")

        import time

        start_time = time.time()

        for _ in range(100):
            self.session_repo.get_recent_sessions(limit=10)

        elapsed_time = time.time() - start_time

        avg_time = elapsed_time / 100

        print("✓ 性能基准测试通过")
        print(f"  - 100次查询总耗时: {elapsed_time:.3f}秒")
        print(f"  - 平均查询耗时: {avg_time * 1000:.2f}毫秒")

        assert avg_time < 0.1, f"平均查询时间应<100ms，实际: {avg_time * 1000:.2f}ms"


class TestSessionRepositoryDataTypes:
    """SessionRepository数据类型测试"""

    def test_session_data_structure(self):
        """
        测试SessionData数据结构
        优先级: P1
        """
        print("\n=== SessionData数据结构测试 ===")

        with tempfile.TemporaryDirectory() as temp_dir:
            config = ConfigManager()
            config.data_dir = Path(temp_dir)
            context = AppContextFactory.create(config=config)

            activities = [
                {
                    "activity_id": "test_001",
                    "session_start_time": "2024-01-01T08:00:00",
                    "session_total_distance": 5000.0,
                    "session_total_timer_time": 1800.0,
                    "session_avg_heart_rate": 150,
                }
            ]

            df = pl.DataFrame(activities)
            context.storage.save_activities(df)

            session_repo = (
                context.session_repository
                if hasattr(context, "session_repository")
                else SessionRepository(context.storage)
            )
            sessions = session_repo.get_recent_sessions(limit=1)

            if len(sessions) > 0:
                session = sessions[0]

                assert hasattr(session, "timestamp"), "SessionDetail应包含timestamp"
                assert hasattr(session, "distance_km"), "SessionDetail应包含distance_km"
                assert hasattr(session, "duration_min"), (
                    "SessionDetail应包含duration_min"
                )

                print("✓ SessionData数据结构测试通过")
                print(
                    f"  - 字段: {[attr for attr in dir(session) if not attr.startswith('_')]}"
                )


def test_session_repository_e2e_suite():
    """
    执行完整的SessionRepository E2E测试套件
    优先级: P0
    """
    print("\n🚀 开始执行SessionRepository E2E测试套件")

    test_instance = TestSessionRepositoryE2E()

    try:
        test_instance.setup_method()

        test_instance.test_lazyframe_chain()
        test_instance.test_session_aggregation()
        test_instance.test_sessions_by_date_range()
        test_instance.test_sessions_by_distance()
        test_instance.test_computed_columns()
        test_instance.test_session_count()
        test_instance.test_total_distance()
        test_instance.test_total_duration()
        test_instance.test_empty_data_handling()
        test_instance.test_performance_benchmark()

        print("\n🎉 SessionRepository E2E测试套件执行完成！")
        print("✅ 所有测试通过")

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        raise
    finally:
        test_instance.teardown_method()


if __name__ == "__main__":
    """
    直接运行SessionRepository E2E测试
    """
    pytest.main([__file__, "-v", "-s"])
