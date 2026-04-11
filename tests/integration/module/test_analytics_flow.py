# 模块集成测试：数据分析流程

import tempfile
from datetime import datetime
from pathlib import Path

import polars as pl

from src.agents.tools import RunnerTools
from src.core.analytics import AnalyticsEngine
from src.core.storage import StorageManager
from tests.conftest import create_mock_context


class TestAnalyticsIntegration:
    """数据分析流程集成测试"""

    def test_analytics_with_storage(self):
        """测试分析引擎与存储集成"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "data"
            data_dir.mkdir()

            # 初始化
            storage = StorageManager(data_dir=data_dir)
            engine = AnalyticsEngine(storage)

            # 创建测试数据
            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001", "test_002"],
                    "timestamp": [datetime(2024, 1, 1), datetime(2024, 1, 2)],
                    "session_start_time": [
                        datetime(2024, 1, 1, 6, 0),
                        datetime(2024, 1, 2, 6, 0),
                    ],
                    "session_total_distance": [5000.0, 10000.0],
                    "session_total_timer_time": [1800, 3600],
                    "session_avg_heart_rate": [140, 150],
                }
            )

            # 保存数据
            storage.save_to_parquet(test_data, 2024)

            # 获取摘要
            summary = engine.get_running_summary()

            assert summary.height == 1
            row = summary.row(0)
            assert row[0] == 2  # total_runs

    def test_vdot_trend_integration(self):
        """测试VDOT趋势计算（使用RunnerTools）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "data"
            data_dir.mkdir()

            storage = StorageManager(data_dir=data_dir)

            # 创建测试数据
            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001", "test_002"],
                    "timestamp": [datetime(2024, 1, 1), datetime(2024, 1, 2)],
                    "session_start_time": [
                        datetime(2024, 1, 1, 6, 0),
                        datetime(2024, 1, 2, 6, 0),
                    ],
                    "session_total_distance": [5000.0, 10000.0],
                    "session_total_timer_time": [1800, 3600],
                }
            )

            storage.save_to_parquet(test_data, 2024)

            # 创建真实的 AnalyticsEngine 而不是 Mock
            from src.core.analytics import AnalyticsEngine

            analytics = AnalyticsEngine(storage)

            # 创建包含真实 analytics 的 context
            context = create_mock_context(storage=storage, analytics=analytics)
            tools = RunnerTools(context=context)

            # 获取VDOT趋势
            vdot_trend = tools.get_vdot_trend(limit=10)

            assert len(vdot_trend) == 2
            # 确保 vdot 是数值类型
            assert isinstance(vdot_trend[0]["vdot"], (int, float))
            assert vdot_trend[0]["vdot"] > 0
