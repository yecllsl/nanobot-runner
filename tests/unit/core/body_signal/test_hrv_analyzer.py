# HRV分析器单元测试
# v0.19.0 新增

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import polars as pl
import pytest

from src.core.body_signal.hrv_analyzer import HRVAnalyzer
from src.core.body_signal.models import DataQuality, HRVDataSource
from src.core.config.body_signal_config import BodySignalConfig


@pytest.fixture
def mock_storage():
    """创建Mock存储"""
    storage = MagicMock()
    return storage


@pytest.fixture
def mock_session_repo(mock_storage):
    """创建Mock SessionRepository"""
    repo = MagicMock()
    repo.storage = mock_storage
    return repo


@pytest.fixture
def sample_hr_data():
    """创建样本心率数据"""
    base_time = datetime(2024, 1, 1, 8, 0, 0)
    timestamps = [base_time + timedelta(minutes=i) for i in range(30)]
    heart_rates = [60 + i % 10 for i in range(30)]  # 60-69 bpm

    return pl.DataFrame(
        {
            "timestamp": timestamps,
            "heart_rate": heart_rates,
            "session_start_time": [base_time] * 30,
            "session_total_distance": [5000.0] * 30,
            "session_total_timer_time": [1800.0] * 30,
        }
    )


class TestHRVAnalyzer:
    """HRV分析器测试类"""

    def test_init(self, mock_session_repo):
        """测试初始化"""
        config = BodySignalConfig()
        analyzer = HRVAnalyzer(mock_session_repo, config)

        assert analyzer.session_repo == mock_session_repo
        assert analyzer.config == config

    def test_init_default_config(self, mock_session_repo):
        """测试默认配置初始化"""
        analyzer = HRVAnalyzer(mock_session_repo)

        assert isinstance(analyzer.config, BodySignalConfig)

    def test_analyze_hrv_empty_data(self, mock_session_repo):
        """测试空数据分析"""
        lf = pl.DataFrame(
            {
                "timestamp": [],
                "heart_rate": [],
            }
        ).lazy()
        mock_session_repo.storage.read_parquet.return_value = lf

        analyzer = HRVAnalyzer(mock_session_repo)
        result = analyzer.analyze_hrv(days=30)

        assert result.data_quality == DataQuality.EMPTY
        assert result.resting_hr_trend == []

    def test_analyze_hrv_no_hr_column(self, mock_session_repo):
        """测试无心率列"""
        lf = pl.DataFrame(
            {
                "timestamp": [datetime.now()],
                "speed": [3.0],
            }
        ).lazy()
        mock_session_repo.storage.read_parquet.return_value = lf

        analyzer = HRVAnalyzer(mock_session_repo)
        result = analyzer.analyze_hrv(days=30)

        assert result.data_quality == DataQuality.EMPTY

    def test_get_resting_hr_trend(self, mock_session_repo):
        """测试静息心率趋势计算"""
        # 创建3天的心率数据（使用过去时间，确保在过滤范围内）
        base_time = datetime.now() - timedelta(days=1)
        timestamps = []
        heart_rates = []
        session_starts = []

        for day in range(3):
            day_start = base_time - timedelta(days=day)
            for minute in range(60):
                timestamps.append(day_start + timedelta(minutes=minute))
                # 模拟静息心率约55-65，活动心率约120-150
                if minute < 10:
                    heart_rates.append(55 + minute)
                else:
                    heart_rates.append(120 + minute % 30)
                session_starts.append(day_start)

        lf = pl.DataFrame(
            {
                "timestamp": timestamps,
                "heart_rate": heart_rates,
                "session_start_time": session_starts,
            }
        ).lazy()
        mock_session_repo.storage.read_parquet.return_value = lf

        analyzer = HRVAnalyzer(mock_session_repo)
        trend = analyzer.get_resting_hr_trend(days=7)

        # 应有3天的数据
        assert len(trend) == 3
        # 静息心率应取最低10%均值，约55-60
        assert all(50 <= p.resting_hr <= 70 for p in trend)

    def test_get_resting_hr_trend_single_point(self, mock_session_repo):
        """测试单点数据时deviation_pct返回0.0"""
        base_time = datetime.now() - timedelta(days=1)
        timestamps = [base_time + timedelta(minutes=i) for i in range(10)]
        heart_rates = [60] * 10

        lf = pl.DataFrame(
            {
                "timestamp": timestamps,
                "heart_rate": heart_rates,
                "session_start_time": [base_time] * 10,
            }
        ).lazy()
        mock_session_repo.storage.read_parquet.return_value = lf

        analyzer = HRVAnalyzer(mock_session_repo)
        trend = analyzer.get_resting_hr_trend(days=7)

        # 单点数据应被正确识别
        assert len(trend) == 1
        assert trend[0].deviation_pct == 0.0

    def test_analyze_hr_recovery(self, mock_session_repo):
        """测试心率恢复分析"""
        base_time = datetime(2024, 1, 1, 8, 0, 0)
        timestamps = [base_time + timedelta(minutes=i) for i in range(20)]
        heart_rates = list(range(150, 130, -1))  # 递减心率

        lf = pl.DataFrame(
            {
                "timestamp": timestamps,
                "heart_rate": heart_rates,
                "session_start_time": [base_time] * 20,
            }
        ).lazy()
        mock_session_repo.storage.read_parquet.return_value = lf

        analyzer = HRVAnalyzer(mock_session_repo)
        result = analyzer.analyze_hr_recovery()

        assert result.data_quality == DataQuality.SUFFICIENT
        assert result.hr_end > 0

    def test_check_hr_drift(self, mock_session_repo):
        """测试心率漂移检测"""
        base_time = datetime(2024, 1, 1, 8, 0, 0)
        timestamps = [base_time + timedelta(minutes=i) for i in range(30)]
        # 心率递增模拟漂移
        heart_rates = [140 + i * 2 for i in range(30)]
        speeds = [3.0] * 30  # 恒定速度

        lf = pl.DataFrame(
            {
                "timestamp": timestamps,
                "heart_rate": heart_rates,
                "speed": speeds,
                "session_start_time": [base_time] * 30,
            }
        ).lazy()
        mock_session_repo.storage.read_parquet.return_value = lf

        analyzer = HRVAnalyzer(mock_session_repo)
        result = analyzer.check_hr_drift()

        # 漂移率应大于0
        assert result.drift_rate >= 0

    def test_estimate_hrv_metrics_no_rr(self, mock_session_repo):
        """测试无RR间期数据时返回HR_ESTIMATE"""
        lf = pl.DataFrame(
            {
                "timestamp": [datetime.now()],
                "heart_rate": [60],
            }
        ).lazy()
        mock_session_repo.storage.read_parquet.return_value = lf

        analyzer = HRVAnalyzer(mock_session_repo)
        result = analyzer.estimate_hrv_metrics()

        assert result["estimated_rmssd"] is None
        assert result["estimated_sdnn"] is None
        assert result["data_source"] == HRVDataSource.HR_ESTIMATE.value

    def test_estimate_hrv_metrics_with_rr(self, mock_session_repo):
        """测试有RR间期数据时计算RMSSD/SDNN"""
        lf = pl.DataFrame(
            {
                "timestamp": [datetime.now() + timedelta(seconds=i) for i in range(10)],
                "heart_rate": [60] * 10,
                "rr_interval": [800 + i * 10 for i in range(10)],
            }
        ).lazy()
        mock_session_repo.storage.read_parquet.return_value = lf

        analyzer = HRVAnalyzer(mock_session_repo)
        result = analyzer.estimate_hrv_metrics()

        assert result["estimated_rmssd"] is not None
        assert result["estimated_sdnn"] is not None
        assert result["data_source"] == HRVDataSource.RR_INTERVAL.value

    def test_evaluate_data_quality_empty(self, mock_session_repo):
        """测试空数据质量评估"""
        analyzer = HRVAnalyzer(mock_session_repo)
        quality = analyzer._evaluate_data_quality([], 30)

        assert quality == DataQuality.EMPTY

    def test_evaluate_data_quality_insufficient(self, mock_session_repo):
        """测试数据不足质量评估"""
        from src.core.body_signal.models import RestingHRPoint

        analyzer = HRVAnalyzer(mock_session_repo)
        trend = [
            RestingHRPoint("2024-01-01", 60.0, 0.0),
            RestingHRPoint("2024-01-02", 61.0, 1.0),
        ]
        quality = analyzer._evaluate_data_quality(trend, 30)

        assert quality == DataQuality.INSUFFICIENT

    def test_evaluate_data_quality_sufficient(self, mock_session_repo):
        """测试数据充足质量评估"""
        from src.core.body_signal.models import RestingHRPoint

        analyzer = HRVAnalyzer(mock_session_repo)
        trend = [
            RestingHRPoint(f"2024-01-{i:02d}", 60.0 + i * 0.5, i * 0.5)
            for i in range(1, 8)
        ]
        quality = analyzer._evaluate_data_quality(trend, 30)

        assert quality == DataQuality.SUFFICIENT
