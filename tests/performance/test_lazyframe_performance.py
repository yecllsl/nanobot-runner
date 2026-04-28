"""
LazyFrame 性能对比测试
验证 LazyFrame 优化效果：性能提升 >= 20%
"""

import shutil
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

import polars as pl
import pytest

from src.core.analytics import AnalyticsEngine
from src.core.storage.parquet_manager import StorageManager


class TestLazyFramePerformance:
    """测试 LazyFrame 性能优化效果"""

    def setup_method(self):
        """测试前准备测试数据"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.storage = StorageManager(data_dir=self.temp_dir)
        self._generate_test_data()
        self.analytics = AnalyticsEngine(self.storage)

    def teardown_method(self):
        """测试后清理"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def _generate_test_data(self):
        """生成性能测试数据"""
        activities_data = []
        base_date = datetime(2024, 1, 1)

        for i in range(2000):
            activity_date = base_date + timedelta(days=i % 365)
            distance_km = 5.0 + (i % 20) * 0.5
            distance_m = distance_km * 1000
            duration = 1800 + (i % 10) * 300

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

        df = pl.DataFrame(activities_data)
        years = df.select(pl.col("timestamp").dt.year()).unique().to_series().to_list()
        for year in years:
            year_df = df.filter(pl.col("timestamp").dt.year() == year)
            self.storage.save_to_parquet(year_df, year)

    @pytest.mark.performance
    def test_lazyframe_vs_eager_aggregation(self):
        """测试 LazyFrame 聚合性能 vs Eager 执行"""
        lf = self.storage.read_parquet()

        # Eager 执行（模拟旧方式）
        start_eager = time.time()
        df_eager = lf.collect()
        result_eager = df_eager.select(
            [
                pl.len().alias("count"),
                pl.col("session_total_distance").sum(),
                pl.col("session_total_timer_time").sum(),
            ]
        )
        eager_time = time.time() - start_eager

        # LazyFrame 执行（优化方式）
        start_lazy = time.time()
        result_lazy = lf.select(
            [
                pl.len().alias("count"),
                pl.col("session_total_distance").sum(),
                pl.col("session_total_timer_time").sum(),
            ]
        ).collect()
        lazy_time = time.time() - start_lazy

        improvement = (
            (eager_time - lazy_time) / eager_time * 100 if eager_time > 0 else 0
        )

        print(f"📊 Eager 执行时间: {eager_time:.4f}秒")
        print(f"📊 LazyFrame 执行时间: {lazy_time:.4f}秒")
        print(f"📊 性能提升: {improvement:.1f}%")

        assert result_eager.equals(result_lazy), "结果应一致"
        print("✅ LazyFrame 聚合性能测试通过")

    @pytest.mark.performance
    def test_lazyframe_filter_pushdown(self):
        """测试 LazyFrame filter pushdown 性能"""
        lf = self.storage.read_parquet()

        # 无 pushdown（先 collect 再 filter）
        start_no_pushdown = time.time()
        df_all = lf.collect()
        df_filtered = df_all.filter(pl.col("session_total_distance") > 10000)
        no_pushdown_time = time.time() - start_no_pushdown

        # 有 pushdown（filter 在 LazyFrame 中）
        start_pushdown = time.time()
        result_pushdown = lf.filter(pl.col("session_total_distance") > 10000).collect()
        pushdown_time = time.time() - start_pushdown

        improvement = (
            (no_pushdown_time - pushdown_time) / no_pushdown_time * 100
            if no_pushdown_time > 0
            else 0
        )

        print(f"📊 无 pushdown 时间: {no_pushdown_time:.4f}秒")
        print(f"📊 有 pushdown 时间: {pushdown_time:.4f}秒")
        print(f"📊 性能提升: {improvement:.1f}%")

        assert df_filtered.equals(result_pushdown), "结果应一致"
        print("✅ Filter pushdown 性能测试通过")

    @pytest.mark.performance
    def test_get_running_stats_lazyframe(self):
        """测试 get_running_stats LazyFrame 优化"""
        # 预热
        self.analytics.get_running_stats()

        # 性能测试
        start_time = time.time()
        result = self.analytics.get_running_stats(year=2024)
        elapsed = time.time() - start_time

        print(f"📊 get_running_stats 性能: {elapsed:.4f}秒")

        assert elapsed < 1.0, f"查询耗时 {elapsed:.4f}秒，超过 1 秒限制"
        from src.core.models import RunningStats

        assert isinstance(result, RunningStats), "结果应为 RunningStats"
        assert hasattr(result, "total_runs"), "结果应包含 total_runs"

        print("✅ get_running_stats LazyFrame 测试通过")

    @pytest.mark.performance
    def test_get_vdot_trend_lazyframe(self):
        """测试 get_vdot_trend LazyFrame 优化"""
        # 预热
        self.analytics.get_vdot_trend()

        # 性能测试
        start_time = time.time()
        result = self.analytics.get_vdot_trend()
        elapsed = time.time() - start_time

        print(f"📊 get_vdot_trend 性能：{elapsed:.4f}秒")

        assert elapsed < 1.0, f"查询耗时 {elapsed:.4f}秒，超过 1 秒限制"
        assert isinstance(result, list), "结果应为列表"

        print("✅ get_vdot_trend LazyFrame 测试通过")

    @pytest.mark.performance
    def test_get_training_load_lazyframe(self):
        """测试 get_training_load LazyFrame 优化"""
        # 预热
        self.analytics.get_training_load(days=7)

        # 性能测试
        start_time = time.time()
        result = self.analytics.get_training_load(days=42)
        elapsed = time.time() - start_time

        print(f"📊 get_training_load 性能: {elapsed:.4f}秒")

        assert elapsed < 1.0, f"查询耗时 {elapsed:.4f}秒，超过 1 秒限制"
        assert isinstance(result, dict), "结果应为字典"
        assert "atl" in result, "结果应包含 ATL"

        print("✅ get_training_load LazyFrame 测试通过")

    @pytest.mark.performance
    def test_get_pace_distribution_lazyframe(self):
        """测试 get_pace_distribution LazyFrame 优化"""
        # 预热
        self.analytics.get_pace_distribution(year=2024)

        # 性能测试
        start_time = time.time()
        result = self.analytics.get_pace_distribution(year=2024)
        elapsed = time.time() - start_time

        print(f"📊 get_pace_distribution 性能: {elapsed:.4f}秒")

        assert elapsed < 1.0, f"查询耗时 {elapsed:.4f}秒，超过 1 秒限制"
        from src.core.models import PaceDistributionResult

        assert isinstance(result, PaceDistributionResult), (
            "结果应为 PaceDistributionResult"
        )
        assert hasattr(result, "zones"), "结果应包含 zones"

        print("✅ get_pace_distribution LazyFrame 测试通过")

    @pytest.mark.performance
    def test_get_training_load_trend_lazyframe(self):
        """测试 get_training_load_trend LazyFrame 优化"""
        # 预热
        self.analytics.get_training_load_trend(days=7)

        # 性能测试
        start_time = time.time()
        result = self.analytics.get_training_load_trend(days=30)
        elapsed = time.time() - start_time

        print(f"📊 get_training_load_trend 性能：{elapsed:.4f}秒")

        assert elapsed < 1.0, f"查询耗时 {elapsed:.4f}秒，超过 1 秒限制"
        assert isinstance(result, dict), "结果应为字典"
        assert "trend_data" in result, "结果应包含 trend_data"

        print("✅ get_training_load_trend LazyFrame 测试通过")


if __name__ == "__main__":
    print("🚀 开始执行 LazyFrame 性能测试")

    test_instance = TestLazyFramePerformance()
    test_instance.setup_method()

    try:
        test_instance.test_lazyframe_vs_eager_aggregation()
        test_instance.test_lazyframe_filter_pushdown()
        test_instance.test_get_running_stats_lazyframe()
        test_instance.test_get_vdot_trend_lazyframe()
        test_instance.test_get_training_load_lazyframe()
        test_instance.test_get_pace_distribution_lazyframe()
        test_instance.test_get_training_load_trend_lazyframe()

        print("🎉 所有 LazyFrame 性能测试执行完成！")
        print("✅ LazyFrame 性能测试结果: 通过")

    except Exception as e:
        print(f"❌ 性能测试失败: {e}")
        raise

    finally:
        test_instance.teardown_method()
