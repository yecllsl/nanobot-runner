# Agent工具集单元测试

import pytest
from unittest.mock import MagicMock, patch

from src.agents.tools import RunnerTools, TOOL_DESCRIPTIONS


class TestRunnerTools:
    """RunnerTools 单元测试"""
    
    def test_init(self):
        """测试初始化"""
        tools = RunnerTools()
        assert tools is not None
    
    def test_get_running_stats_empty(self):
        """测试空数据统计"""
        with patch('src.core.storage.StorageManager') as MockStorage:
            mock_storage = MagicMock()
            MockStorage.return_value = mock_storage
            
            tools = RunnerTools(storage=mock_storage)
            
            # 模拟空数据
            mock_storage.read_parquet.return_value.collect.return_value.height = 0
            
            result = tools.get_running_stats()
            
            assert "message" in result
    
    def test_get_recent_runs(self):
        """测试获取最近跑步记录"""
        with patch('src.core.storage.StorageManager') as MockStorage:
            mock_storage = MagicMock()
            MockStorage.return_value = mock_storage
            
            tools = RunnerTools(storage=mock_storage)
            
            # 模拟数据
            mock_lf = MagicMock()
            mock_storage.read_parquet.return_value = mock_lf
            
            mock_df = MagicMock()
            mock_df.sort.return_value = mock_df
            mock_df.limit.return_value = mock_df
            mock_df.collect.return_value = mock_df
            mock_df.iter_rows.return_value = []
            
            result = tools.get_recent_runs(limit=5)
            
            assert isinstance(result, list)
    
    def test_calculate_vdot_for_run(self):
        """测试计算VDOT"""
        tools = RunnerTools()
        
        vdot = tools.calculate_vdot_for_run(5000, 1200)
        
        assert vdot > 0
        assert vdot < 100
    
    def test_tool_descriptions(self):
        """测试工具描述"""
        assert len(TOOL_DESCRIPTIONS) > 0
        
        # 检查关键工具
        assert "get_running_stats" in TOOL_DESCRIPTIONS
        assert "get_recent_runs" in TOOL_DESCRIPTIONS
        assert "calculate_vdot_for_run" in TOOL_DESCRIPTIONS
