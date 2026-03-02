# 分析引擎单元测试
# 测试数据分析功能

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile

import polars as pl

from src.core.analytics import AnalyticsEngine


class TestAnalyticsEngine:
    """测试分析引擎"""

    def test_init(self):
        """测试初始化"""
        mock_storage = Mock()
        engine = AnalyticsEngine(mock_storage)
        assert engine.storage == mock_storage

    def test_calculate_vdot_success(self):
        """测试成功计算VDOT"""
        engine = AnalyticsEngine(Mock())
        
        # 5公里（5000米）用时1800秒（30分钟）
        vdot = engine.calculate_vdot(5000, 1800)
        
        assert vdot > 0
        assert isinstance(vdot, float)

    def test_calculate_vdot_zero_distance(self):
        """测试零距离VDOT计算"""
        engine = AnalyticsEngine(Mock())
        
        vdot = engine.calculate_vdot(0, 1800)
        
        assert vdot == 0.0

    def test_calculate_vdot_zero_time(self):
        """测试零时间VDOT计算"""
        engine = AnalyticsEngine(Mock())
        
        vdot = engine.calculate_vdot(5000, 0)
        
        assert vdot == 0.0

    def test_calculate_vdot_negative_distance(self):
        """测试负距离VDOT计算"""
        engine = AnalyticsEngine(Mock())
        
        vdot = engine.calculate_vdot(-5000, 1800)
        
        assert vdot == 0.0

    def test_calculate_vdot_negative_time(self):
        """测试负时间VDOT计算"""
        engine = AnalyticsEngine(Mock())
        
        vdot = engine.calculate_vdot(5000, -1800)
        
        assert vdot == 0.0

    def test_calculate_tss_success(self):
        """测试成功计算TSS"""
        engine = AnalyticsEngine(Mock())
        
        heart_rate_data = pl.Series([140, 145, 150, 155, 160])
        tss = engine.calculate_tss(heart_rate_data, 3600)
        
        assert tss > 0
        assert isinstance(tss, float)

    def test_calculate_tss_empty_data(self):
        """测试空数据TSS计算"""
        engine = AnalyticsEngine(Mock())
        
        heart_rate_data = pl.Series([])
        tss = engine.calculate_tss(heart_rate_data, 3600)
        
        assert tss == 0.0

    def test_calculate_tss_zero_duration(self):
        """测试零时长TSS计算"""
        engine = AnalyticsEngine(Mock())
        
        heart_rate_data = pl.Series([140, 145, 150])
        tss = engine.calculate_tss(heart_rate_data, 0)
        
        assert tss == 0.0

    def test_calculate_tss_low_heart_rate(self):
        """测试低心率TSS计算"""
        engine = AnalyticsEngine(Mock())
        
        heart_rate_data = pl.Series([60, 65, 70])  # 接近休息心率
        tss = engine.calculate_tss(heart_rate_data, 3600)
        
        # 当avg_hr=65时，ift=(65-60)/(190-60)≈0.038，tss≈3.85
        assert tss > 0
        assert tss < 10

    def test_get_running_summary_success(self):
        """测试成功获取跑步摘要"""
        mock_storage = Mock()
        engine = AnalyticsEngine(mock_storage)
        
        mock_df = pl.DataFrame({
            "distance": [5000.0, 10000.0],
            "duration": [1800, 3600],
            "heart_rate": [140, 150]
        })
        
        mock_lf = Mock()
        mock_lf.collect.return_value = mock_df
        
        with patch.object(mock_storage, 'read_parquet', return_value=mock_lf):
            summary = engine.get_running_summary()
            
            assert summary.height == 1
            assert summary["total_runs"][0] == 2
            assert summary["total_distance"][0] == 15000.0

    def test_get_running_summary_empty(self):
        """测试空数据跑步摘要"""
        mock_storage = Mock()
        engine = AnalyticsEngine(mock_storage)
        
        mock_df = pl.DataFrame()
        
        mock_lf = Mock()
        mock_lf.collect.return_value = mock_df
        
        with patch.object(mock_storage, 'read_parquet', return_value=mock_lf):
            summary = engine.get_running_summary()
            
            assert summary.height == 0

    def test_get_running_summary_with_date_filter(self):
        """测试带日期过滤的跑步摘要"""
        mock_storage = Mock()
        engine = AnalyticsEngine(mock_storage)
        
        mock_df = pl.DataFrame({
            "distance": [5000.0],
            "duration": [1800],
            "heart_rate": [140]
        })
        
        mock_lf = Mock()
        mock_lf.collect.return_value = mock_df
        mock_lf.filter.return_value = mock_lf
        
        with patch.object(mock_storage, 'read_parquet', return_value=mock_lf):
            summary = engine.get_running_summary(start_date="2024-01-01", end_date="2024-12-31")
            
            assert summary.height == 1

    def test_analyze_hr_drift_success(self):
        """测试成功分析心率漂移"""
        engine = AnalyticsEngine(Mock())
        
        heart_rate = [140, 142, 145, 148, 150, 152, 155, 158, 160, 162, 165, 168]
        pace = [5.0, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9, 6.0, 6.1]
        
        result = engine.analyze_hr_drift(heart_rate, pace)
        
        assert "correlation" in result
        assert "hr_drift" in result
        assert "has_drift" in result
        assert isinstance(result["correlation"], float)

    def test_analyze_hr_drift_insufficient_data(self):
        """测试数据量不足的心率漂移分析"""
        engine = AnalyticsEngine(Mock())
        
        heart_rate = [140, 142, 145]  # 少于10个数据点
        pace = [5.0, 5.1, 5.2]
        
        result = engine.analyze_hr_drift(heart_rate, pace)
        
        assert result["error"] == "数据量不足"

    def test_analyze_hr_drift_empty_data(self):
        """测试空数据的心率漂移分析"""
        engine = AnalyticsEngine(Mock())
        
        result = engine.analyze_hr_drift([], [])
        
        assert result["error"] == "数据量不足"

    def test_calculate_atl_ctl_success(self):
        """测试成功计算ATL和CTL"""
        engine = AnalyticsEngine(Mock())
        
        tss_data = [50, 60, 70, 80, 90, 100]
        
        result = engine.calculate_atl_ctl(tss_data, window_size=42)
        
        assert "atl" in result
        assert "ctl" in result
        assert len(result["atl"]) == 6
        assert len(result["ctl"]) == 6

    def test_calculate_atl_ctl_empty_data(self):
        """测试空数据ATL和CTL计算"""
        engine = AnalyticsEngine(Mock())
        
        result = engine.calculate_atl_ctl([], window_size=42)
        
        assert result["atl"] == []
        assert result["ctl"] == []

    def test_calculate_atl_ctl_single_value(self):
        """测试单值ATL和CTL计算"""
        engine = AnalyticsEngine(Mock())
        
        result = engine.calculate_atl_ctl([50], window_size=42)
        
        assert len(result["atl"]) == 1
        assert len(result["ctl"]) == 1
        assert result["atl"][0] == 50.0
        assert result["ctl"][0] == 50.0
