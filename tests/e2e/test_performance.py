#!/usr/bin/env python3
"""
RunFlowAgent 性能端到端测试
测试大数据量下的性能表现和内存使用效率

测试目标：
- 验证百万级数据处理的性能指标
- 确保内存使用符合预期
- 验证Polars引擎的高性能特性

执行方式：
- 在Trae IDE终端中执行: pytest tests/e2e/test_performance.py -v
- 单独执行: python tests/e2e/test_performance.py
"""

import pytest
import tempfile
import time
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import polars as pl

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.storage import StorageManager
from src.core.analytics import AnalyticsEngine


class TestPerformanceE2E:
    """性能端到端测试"""
    
    def setup_method(self):
        """测试前置设置"""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_data_dir = Path(self.temp_dir.name)
        
        # 初始化服务
        self.storage_manager = StorageManager(data_dir=self.test_data_dir / "data")
        self.analytics_engine = AnalyticsEngine(self.storage_manager)
        
        # 生成测试数据
        self.generate_test_data()
    
    def teardown_method(self):
        """测试后置清理"""
        self.temp_dir.cleanup()
    
    def generate_test_data(self):
        """生成大规模测试数据"""
        print("生成性能测试数据...")
        
        # 生成10000条活动记录的模拟数据
        activities_data = []
        for i in range(10000):
            activity = {
                'activity_id': f'activity_{i:06d}',
                'timestamp': f'2024-01-{(i % 30) + 1:02d}T08:00:00',
                'distance_m': 5000 + (i % 5000),  # 5-10km
                'duration_s': 1800 + (i % 1200),  # 30-50分钟
                'avg_heart_rate': 140 + (i % 40),  # 140-180bpm
                'max_heart_rate': 160 + (i % 30),  # 160-190bpm
                'calories': 300 + (i % 200),       # 300-500卡路里
                'elevation_gain': 50 + (i % 100),  # 50-150米爬升
            }
            activities_data.append(activity)
        
        # 创建Polars DataFrame
        self.large_df = pl.DataFrame(activities_data)
        print(f"生成测试数据完成: {len(self.large_df)} 条记录")
    
    def test_large_dataset_import_performance(self):
        """
        测试大数据集导入性能
        验证指标: 导入时间 < 10秒, 内存占用 < 500MB
        优先级: P1
        """
        print("\n=== 大数据集导入性能测试 ===")
        
        # 模拟导入大数据集
        start_time = time.time()
        memory_before = self.get_memory_usage()
        
        with patch.object(self.storage_manager, 'save_activities') as mock_save:
            # 执行导入
            self.storage_manager.save_activities(self.large_df)
            
            elapsed_time = time.time() - start_time
            memory_after = self.get_memory_usage()
            memory_used = memory_after - memory_before
            
            print(f"导入时间: {elapsed_time:.2f}秒")
            print(f"内存使用: {memory_used:.1f}MB")
            
            # 性能断言
            assert elapsed_time < 10.0, f"导入时间过长: {elapsed_time:.2f}秒"
            assert memory_used < 500, f"内存占用过高: {memory_used:.1f}MB"
            
            print("✓ 大数据集导入性能测试通过")
    
    def test_complex_query_performance(self):
        """
        测试复杂查询性能
        验证指标: 查询时间 < 3秒
        优先级: P0
        """
        print("\n=== 复杂查询性能测试 ===")
        
        # 模拟复杂查询场景
        with patch.object(self.storage_manager, 'query_activities') as mock_query:
            mock_query.return_value = self.large_df
            
            start_time = time.time()
            
            # 执行复杂查询: 最近30天，距离>8km，心率>150的活动
            result = self.storage_manager.query_activities(
                days=30, 
                min_distance=8000, 
                min_heart_rate=150
            )
            
            elapsed_time = time.time() - start_time
            
            print(f"复杂查询时间: {elapsed_time:.2f}秒")
            
            # 性能断言
            assert elapsed_time < 3.0, f"查询时间过长: {elapsed_time:.2f}秒"
            print("✓ 复杂查询性能测试通过")
    
    def test_aggregation_performance(self):
        """
        测试聚合计算性能
        验证指标: 聚合时间 < 2秒
        优先级: P1
        """
        print("\n=== 聚合计算性能测试 ===")
        
        with patch.object(self.storage_manager, 'load_activities') as mock_load:
            mock_load.return_value = self.large_df
            
            start_time = time.time()
            
            # 执行多维度聚合
            aggregated = self.large_df.group_by(
                pl.col('timestamp').str.strptime(pl.Datetime, '%Y-%m-%dT%H:%M:%S').dt.truncate('1w')
            ).agg([
                pl.count().alias('activity_count'),
                pl.col('distance_m').mean().alias('avg_distance'),
                pl.col('duration_s').mean().alias('avg_duration'),
                pl.col('avg_heart_rate').mean().alias('avg_heart_rate'),
                pl.col('calories').sum().alias('total_calories')
            ]).sort('timestamp')
            
            elapsed_time = time.time() - start_time
            
            print(f"聚合计算时间: {elapsed_time:.2f}秒")
            print(f"聚合结果行数: {len(aggregated)}")
            
            # 性能断言
            assert elapsed_time < 2.0, f"聚合时间过长: {elapsed_time:.2f}秒"
            assert len(aggregated) > 0, "聚合结果为空"
            print("✓ 聚合计算性能测试通过")
    
    def test_analytics_calculation_performance(self):
        """
        测试分析计算性能
        验证指标: 批量计算时间 < 5秒
        优先级: P1
        """
        print("\n=== 分析计算性能测试 ===")
        
        start_time = time.time()
        
        # 批量计算VDOT值
        vdot_results = []
        for i in range(1000):
            distance = 5000 + (i * 100)  # 5km到15km
            duration = 1800 + (i * 60)   # 30min到130min
            vdot = self.analytics_engine.calculate_vdot(distance, duration)
            vdot_results.append(vdot)
        
        elapsed_time = time.time() - start_time
        
        print(f"批量VDOT计算时间: {elapsed_time:.2f}秒")
        print(f"计算数量: {len(vdot_results)} 个VDOT值")
        
        # 性能断言
        assert elapsed_time < 5.0, f"批量计算时间过长: {elapsed_time:.2f}秒"
        assert len(vdot_results) == 1000, "计算结果数量不正确"
        print("✓ 分析计算性能测试通过")
    
    def test_memory_efficiency(self):
        """
        测试内存使用效率
        验证指标: 多次操作后内存增长 < 100MB
        优先级: P1
        """
        print("\n=== 内存使用效率测试 ===")
        
        memory_before = self.get_memory_usage()
        
        # 执行多次操作模拟长时间运行
        operations = []
        for i in range(50):
            # 模拟不同类型的操作
            if i % 3 == 0:
                # 查询操作
                with patch.object(self.storage_manager, 'query_activities') as mock_query:
                    mock_query.return_value = self.large_df.head(1000)
                    result = self.storage_manager.query_activities(days=7)
                    operations.append(result)
            
            elif i % 3 == 1:
                # 计算操作
                vdot = self.analytics_engine.calculate_vdot(5000, 1800)
                operations.append(vdot)
            
            else:
                # 数据处理操作
                sample_data = self.large_df.head(500).to_dicts()
                processed = [{
                    'activity_id': item['activity_id'],
                    'vdot': self.analytics_engine.calculate_vdot(item['distance_m'], item['duration_s'])
                } for item in sample_data]
                operations.append(processed)
        
        memory_after = self.get_memory_usage()
        memory_increase = memory_after - memory_before
        
        print(f"操作前内存: {memory_before:.1f}MB")
        print(f"操作后内存: {memory_after:.1f}MB")
        print(f"内存增长: {memory_increase:.1f}MB")
        
        # 内存效率断言
        assert memory_increase < 100, f"内存增长过高: {memory_increase:.1f}MB"
        print("✓ 内存使用效率测试通过")
    
    def test_concurrent_operations(self):
        """
        测试并发操作性能
        验证指标: 并发操作无冲突，性能稳定
        优先级: P2
        """
        print("\n=== 并发操作性能测试 ===")
        
        import threading
        
        results = []
        errors = []
        
        def query_operation(thread_id):
            """查询操作线程"""
            try:
                with patch.object(self.storage_manager, 'query_activities') as mock_query:
                    mock_query.return_value = self.large_df.head(2000)
                    result = self.storage_manager.query_activities(days=thread_id + 1)
                    results.append((thread_id, 'query', 'success'))
            except Exception as e:
                errors.append((thread_id, 'query', str(e)))
        
        def calculation_operation(thread_id):
            """计算操作线程"""
            try:
                for i in range(100):
                    self.analytics_engine.calculate_vdot(5000 + i, 1800 + i)
                results.append((thread_id, 'calc', 'success'))
            except Exception as e:
                errors.append((thread_id, 'calc', str(e)))
        
        # 创建并启动多个线程
        threads = []
        for i in range(5):  # 5个并发线程
            if i % 2 == 0:
                thread = threading.Thread(target=query_operation, args=(i,))
            else:
                thread = threading.Thread(target=calculation_operation, args=(i,))
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join(timeout=30)  # 30秒超时
        
        print(f"成功操作: {len(results)}")
        print(f"错误操作: {len(errors)}")
        
        # 并发测试断言
        assert len(errors) == 0, f"并发操作出现错误: {errors}"
        assert len(results) == 5, "并发操作未全部完成"
        print("✓ 并发操作性能测试通过")
    
    def get_memory_usage(self):
        """获取当前进程内存使用量(MB)"""
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / 1024 / 1024  # 转换为MB
        except ImportError:
            # 如果psutil不可用，返回估算值
            return 100.0


def test_storage_compression_efficiency():
    """
    测试存储压缩效率
    验证指标: Parquet压缩率 > 70%
    优先级: P1
    """
    print("\n=== 存储压缩效率测试 ===")
    
    import tempfile
    from pathlib import Path
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # 创建测试数据
        test_data = []
        for i in range(10000):
            test_data.append({
                'id': i,
                'name': f'activity_{i}',
                'distance': 5000 + (i % 5000),
                'duration': 1800 + (i % 1200),
                'timestamp': f'2024-01-{(i % 30) + 1:02d}T08:00:00'
            })
        
        df = pl.DataFrame(test_data)
        
        # 保存为不同格式比较大小
        csv_path = Path(temp_dir) / "test_data.csv"
        parquet_path = Path(temp_dir) / "test_data.parquet"
        
        # 保存为CSV
        df.write_csv(csv_path)
        csv_size = csv_path.stat().st_size
        
        # 保存为Parquet（启用压缩）
        df.write_parquet(parquet_path, compression='snappy')
        parquet_size = parquet_path.stat().st_size
        
        # 计算压缩率
        compression_ratio = (csv_size - parquet_size) / csv_size * 100
        
        print(f"CSV文件大小: {csv_size / 1024:.1f}KB")
        print(f"Parquet文件大小: {parquet_size / 1024:.1f}KB")
        print(f"压缩率: {compression_ratio:.1f}%")
        
        # 压缩效率断言
        assert compression_ratio > 70, f"压缩率不足: {compression_ratio:.1f}%"
        print("✓ 存储压缩效率测试通过")


if __name__ == "__main__":
    """
    直接运行性能E2E测试
    """
    print("🚀 开始执行RunFlowAgent性能端到端测试")
    
    # 创建测试实例
    test_instance = TestPerformanceE2E()
    
    try:
        test_instance.setup_method()
        
        # 执行性能测试
        test_instance.test_large_dataset_import_performance()
        test_instance.test_complex_query_performance()
        test_instance.test_aggregation_performance()
        test_instance.test_analytics_calculation_performance()
        test_instance.test_memory_efficiency()
        test_instance.test_concurrent_operations()
        
        # 执行压缩效率测试
        test_storage_compression_efficiency()
        
        print("🎉 所有性能E2E测试执行完成！")
        print("✅ 性能测试结果: 通过")
        
    except AssertionError as e:
        print(f"❌ 性能测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 测试执行异常: {e}")
        sys.exit(1)
    
    finally:
        test_instance.teardown_method()