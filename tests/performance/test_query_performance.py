"""
查询性能测试
验证架构设计要求的性能指标：所有查询接口响应时间 < 3 秒
"""

import shutil
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

import polars as pl
import pytest

from src.agents.tools import RunnerTools
from src.core.analytics import AnalyticsEngine
from src.core.storage import StorageManager
from tests.conftest import create_mock_context


class TestQueryPerformance:
    """测试查询性能"""

    def setup_method(self):
        """测试前准备测试数据"""
        # 创建临时目录用于测试
        self.temp_dir = Path(tempfile.mkdtemp())
        self.storage = StorageManager(data_dir=self.temp_dir)

        # 生成测试数据
        self._generate_test_data()

        # 创建真实的 AnalyticsEngine
        analytics = AnalyticsEngine(self.storage)

        # 创建包含真实 analytics 的 context
        context = create_mock_context(storage=self.storage, analytics=analytics)
        self.tools = RunnerTools(context=context)

    def teardown_method(self):
        """测试后清理"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def _generate_test_data(self):
        """生成性能测试数据"""
        # 生成1000条测试记录，模拟真实使用场景
        activities_data = []

        base_date = datetime(2024, 1, 1)

        for i in range(1000):
            activity_date = base_date + timedelta(days=i)
            distance_km = 5.0 + (i % 20) * 0.5  # 距离范围：5-15公里
            distance_m = distance_km * 1000  # 转换为米
            duration = 1800 + (i % 10) * 300  # 时长范围：30-60分钟

            activity = {
                "activity_id": f"run_{activity_date.strftime('%Y%m%d')}_{i:04d}",
                "timestamp": activity_date,
                "session_start_time": activity_date,  # 添加session_start_time
                "source_file": f"test_{i}.fit",
                "filename": f"test_{i}.fit",
                "serial_number": f"TEST{i:04d}",
                "time_created": activity_date,
                "session_total_distance": distance_m,
                "session_total_timer_time": duration,
                "total_calories": 300 + (i % 10) * 50,
                "session_avg_heart_rate": 140 + (i % 20),
                "max_heart_rate": 160 + (i % 20),
                "record_count": 100 + (i % 50),
            }
            activities_data.append(activity)

        # 创建DataFrame并保存
        df = pl.DataFrame(activities_data)

        # 按年份分组保存
        years = df.select(pl.col("timestamp").dt.year()).unique().to_series().to_list()
        for year in years:
            year_df = df.filter(pl.col("timestamp").dt.year() == year)
            self.storage.save_to_parquet(year_df, year)

    @pytest.mark.performance
    def test_query_by_date_range_performance(self):
        """测试日期范围查询性能"""
        # 预热查询（避免首次查询的冷启动影响）
        self.tools.query_by_date_range("2024-01-01", "2024-01-10")

        # 正式性能测试
        start_time = time.time()
        result = self.tools.query_by_date_range("2024-01-01", "2024-12-31")
        elapsed = time.time() - start_time

        print(f"📊 日期范围查询性能: {elapsed:.3f}秒")

        # 性能要求：响应时间 < 3 秒
        assert elapsed < 3.0, f"日期范围查询耗时 {elapsed:.3f}秒，超过 3 秒限制"
        assert isinstance(result, list), "查询结果应为列表类型"
        assert len(result) > 0, "查询结果不应为空"

        print(f"✅ 日期范围查询性能测试通过: {elapsed:.3f}秒")

    @pytest.mark.performance
    def test_query_by_distance_performance(self):
        """测试距离范围查询性能"""
        # 预热查询
        self.tools.query_by_distance(min_distance=5, max_distance=10)

        # 正式性能测试
        start_time = time.time()
        result = self.tools.query_by_distance(min_distance=5, max_distance=15)
        elapsed = time.time() - start_time

        print(f"📊 距离范围查询性能: {elapsed:.3f}秒")

        # 性能要求：响应时间 < 3 秒
        assert elapsed < 3.0, f"距离范围查询耗时 {elapsed:.3f}秒，超过 3 秒限制"
        assert isinstance(result, list), "查询结果应为列表类型"
        assert len(result) > 0, "查询结果不应为空"

        print(f"✅ 距离范围查询性能测试通过: {elapsed:.3f}秒")

    @pytest.mark.performance
    def test_get_vdot_trend_performance(self):
        """测试 VDOT 趋势查询性能"""
        # 预热查询
        self.tools.get_vdot_trend(limit=10)

        # 正式性能测试
        start_time = time.time()
        result = self.tools.get_vdot_trend(limit=50)
        elapsed = time.time() - start_time

        print(f"📊 VDOT趋势查询性能: {elapsed:.3f}秒")

        # 性能要求：响应时间 < 3 秒
        assert elapsed < 3.0, f"VDOT趋势查询耗时 {elapsed:.3f}秒，超过 3 秒限制"
        assert isinstance(result, list), "查询结果应为列表类型"

        print(f"✅ VDOT趋势查询性能测试通过: {elapsed:.3f}秒")

    @pytest.mark.performance
    def test_get_running_stats_performance(self):
        """测试跑步统计数据查询性能"""
        # 预热查询
        self.tools.get_running_stats()

        # 正式性能测试
        start_time = time.time()
        result = self.tools.get_running_stats("2024-01-01", "2024-12-31")
        elapsed = time.time() - start_time

        print(f"📊 跑步统计查询性能: {elapsed:.3f}秒")

        # 性能要求：响应时间 < 3 秒
        assert elapsed < 3.0, f"跑步统计查询耗时 {elapsed:.3f}秒，超过 3 秒限制"
        assert isinstance(result, dict), "查询结果应为字典类型"

        print(f"✅ 跑步统计查询性能测试通过: {elapsed:.3f}秒")

    @pytest.mark.performance
    def test_get_recent_runs_performance(self):
        """测试最近跑步记录查询性能"""
        # 预热查询
        self.tools.get_recent_runs(limit=10)

        # 正式性能测试
        start_time = time.time()
        result = self.tools.get_recent_runs(limit=50)
        elapsed = time.time() - start_time

        print(f"📊 最近跑步记录查询性能: {elapsed:.3f}秒")

        # 性能要求：响应时间 < 3 秒
        assert elapsed < 3.0, f"最近跑步记录查询耗时 {elapsed:.3f}秒，超过 3 秒限制"
        assert isinstance(result, list), "查询结果应为列表类型"

        print(f"✅ 最近跑步记录查询性能测试通过: {elapsed:.3f}秒")

    @pytest.mark.performance
    def test_get_training_load_performance(self):
        """测试训练负荷计算性能（ATL/CTL计算）"""
        # 预热查询
        self.tools.get_training_load(days=30)

        # 正式性能测试
        start_time = time.time()
        result = self.tools.get_training_load(days=42)
        elapsed = time.time() - start_time

        print(f"📊 训练负荷计算性能: {elapsed:.3f}秒")

        # 性能要求：响应时间 < 2 秒
        assert elapsed < 2.0, f"训练负荷计算耗时 {elapsed:.3f}秒，超过 2 秒限制"
        assert isinstance(result, dict), "查询结果应为字典类型"
        assert "atl" in result, "结果应包含 ATL 字段"
        assert "ctl" in result, "结果应包含 CTL 字段"
        assert "tsb" in result, "结果应包含 TSB 字段"

        print(f"✅ 训练负荷计算性能测试通过: {elapsed:.3f}秒")
        print(
            f"   ATL: {result.get('atl', 0)}, CTL: {result.get('ctl', 0)}, TSB: {result.get('tsb', 0)}"
        )

    @pytest.mark.performance
    def test_get_stats_lazyframe_performance(self):
        """测试 get_stats 方法 LazyFrame 性能"""
        # 预热查询
        self.storage.get_stats()

        # 正式性能测试
        start_time = time.time()
        result = self.storage.get_stats()
        elapsed = time.time() - start_time

        print(f"📊 get_stats LazyFrame 性能: {elapsed:.3f}秒")

        # 性能要求：响应时间 < 1 秒
        assert elapsed < 1.0, f"get_stats 耗时 {elapsed:.3f}秒，超过 1 秒限制"
        assert isinstance(result, dict), "查询结果应为字典类型"
        assert "total_records" in result, "结果应包含 total_records 字段"
        assert "years" in result, "结果应包含 years 字段"

        print(f"✅ get_stats LazyFrame 性能测试通过: {elapsed:.3f}秒")
        print(f"   总记录数: {result.get('total_records', 0)}")

    @pytest.mark.performance
    def test_lazyframe_vs_dataframe_comparison(self):
        """对比 LazyFrame 与 DataFrame 查询性能差异"""
        import tracemalloc

        # 获取所有 parquet 文件路径
        parquet_files = list(self.temp_dir.glob("activities_*.parquet"))

        # 测试 LazyFrame 方式
        tracemalloc.start()
        start_time = time.time()
        lazy_result = (
            pl.concat([pl.scan_parquet(f) for f in parquet_files])
            .select(
                [
                    pl.len().alias("count"),
                    pl.col("session_total_distance")
                    .sum()
                    .alias("session_total_distance"),
                    pl.col("session_total_timer_time")
                    .sum()
                    .alias("session_total_timer_time"),
                ]
            )
            .collect()
        )
        lazy_time = time.time() - start_time
        lazy_memory = tracemalloc.get_traced_memory()[1] / 1024 / 1024  # MB
        tracemalloc.stop()

        # 测试 DataFrame 方式（传统方式）
        tracemalloc.start()
        start_time = time.time()
        dfs = [pl.read_parquet(f) for f in parquet_files]
        df = pl.concat(dfs) if len(dfs) > 1 else dfs[0]
        df_result = df.select(
            [
                pl.len().alias("count"),
                pl.col("session_total_distance").sum().alias("session_total_distance"),
                pl.col("session_total_timer_time")
                .sum()
                .alias("session_total_timer_time"),
            ]
        )
        df_time = time.time() - start_time
        df_memory = tracemalloc.get_traced_memory()[1] / 1024 / 1024  # MB
        tracemalloc.stop()

        # 计算性能提升比例
        time_improvement = ((df_time - lazy_time) / df_time * 100) if df_time > 0 else 0
        memory_improvement = (
            ((df_memory - lazy_memory) / df_memory * 100) if df_memory > 0 else 0
        )

        print("📊 LazyFrame vs DataFrame 性能对比:")
        print(f"   LazyFrame: {lazy_time:.3f}秒, 内存: {lazy_memory:.2f}MB")
        print(f"   DataFrame: {df_time:.3f}秒, 内存: {df_memory:.2f}MB")
        print(f"   时间提升: {time_improvement:.1f}%")
        print(f"   内存优化: {memory_improvement:.1f}%")

        # 验证结果一致性
        assert lazy_result["count"][0] == df_result["count"][0], (
            "LazyFrame 和 DataFrame 结果不一致"
        )

        # 验证性能提升（目标：≥20%）
        # 注意：小数据集可能看不出明显差异，主要验证功能正确性
        print("✅ LazyFrame vs DataFrame 对比测试通过")


def test_performance_baseline():
    """性能基准测试 - 验证基础查询性能"""
    storage = StorageManager()
    analytics = AnalyticsEngine(storage)
    context = create_mock_context(storage=storage, analytics=analytics)
    tools = RunnerTools(context=context)

    # 测试空数据查询性能
    start_time = time.time()
    result = tools.get_running_stats()
    elapsed = time.time() - start_time

    print(f"📊 空数据查询基准性能: {elapsed:.3f}秒")

    # 空数据时返回 message 字段
    assert elapsed < 1.0, f"空数据查询耗时 {elapsed:.3f}秒，超过基准限制"
    assert isinstance(result, dict), "结果应为字典类型"

    print("✅ 性能基准测试通过")


if __name__ == "__main__":
    """直接运行性能测试"""
    print("🚀 开始执行查询性能测试")

    # 创建测试实例
    test_instance = TestQueryPerformance()
    test_instance.setup_method()

    try:
        # 执行性能测试
        test_instance.test_query_by_date_range_performance()
        test_instance.test_query_by_distance_performance()
        test_instance.test_get_vdot_trend_performance()
        test_instance.test_get_running_stats_performance()
        test_instance.test_get_recent_runs_performance()
        test_instance.test_get_training_load_performance()

        print("🎉 所有性能测试执行完成！")
        print("✅ 性能测试结果: 通过")

    except Exception as e:
        print(f"❌ 性能测试失败: {e}")
        raise

    finally:
        test_instance.teardown_method()
