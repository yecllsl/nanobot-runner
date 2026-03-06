"""
查询性能测试
验证架构设计要求的性能指标：所有查询接口响应时间 < 3 秒
"""

import pytest
import time
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

import polars as pl

from src.agents.tools import RunnerTools
from src.core.storage import StorageManager
from src.core.schema import ParquetSchema


class TestQueryPerformance:
    """测试查询性能"""
    
    def setup_method(self):
        """测试前准备测试数据"""
        # 创建临时目录用于测试
        self.temp_dir = Path(tempfile.mkdtemp())
        self.storage = StorageManager(data_dir=self.temp_dir)
        
        # 生成测试数据
        self._generate_test_data()
        
        self.tools = RunnerTools(self.storage)
    
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
                'activity_id': f'run_{activity_date.strftime("%Y%m%d")}_{i:04d}',
                'timestamp': activity_date,
                'source_file': f'test_{i}.fit',
                'filename': f'test_{i}.fit',
                'serial_number': f'TEST{i:04d}',
                'time_created': activity_date,
                'total_distance': distance_m,
                'total_timer_time': duration,
                'total_calories': 300 + (i % 10) * 50,
                'avg_heart_rate': 140 + (i % 20),
                'max_heart_rate': 160 + (i % 20),
                'record_count': 100 + (i % 50)
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


def test_performance_baseline():
    """性能基准测试 - 验证基础查询性能"""
    storage = StorageManager()
    tools = RunnerTools(storage)
    
    # 测试空数据查询性能
    start_time = time.time()
    result = tools.get_running_stats()
    elapsed = time.time() - start_time
    
    print(f"📊 空数据查询基准性能: {elapsed:.3f}秒")
    assert elapsed < 1.0, f"空数据查询耗时 {elapsed:.3f}秒，超过基准限制"
    
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
        
        print("🎉 所有性能测试执行完成！")
        print("✅ 性能测试结果: 通过")
        
    except Exception as e:
        print(f"❌ 性能测试失败: {e}")
        raise
    
    finally:
        test_instance.teardown_method()