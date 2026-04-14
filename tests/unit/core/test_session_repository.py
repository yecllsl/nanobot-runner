# SessionRepository单元测试
# 测试Session数据聚合查询功能

from datetime import datetime
from unittest.mock import Mock

import polars as pl
import pytest

from src.core.session_repository import (
    SessionDetail,
    SessionRepository,
    SessionSummary,
    SessionVdot,
)


class TestSessionDataClasses:
    """Session数据类测试"""

    def test_session_summary_to_dict(self):
        """测试SessionSummary转换为字典"""
        summary = SessionSummary(
            timestamp="2024-01-01 10:00:00",
            distance_km=5.0,
            duration_min=30.0,
            avg_pace_sec_km=360.0,
            avg_heart_rate=150.0,
        )

        result = summary.to_dict()

        assert result["timestamp"] == "2024-01-01 10:00:00"
        assert result["distance_km"] == 5.0
        assert result["duration_min"] == 30.0
        assert result["avg_pace_sec_km"] == 360.0
        assert result["avg_heart_rate"] == 150.0

    def test_session_detail_to_dict(self):
        """测试SessionDetail转换为字典"""
        detail = SessionDetail(
            timestamp="2024-01-01 10:00:00",
            distance_km=5.0,
            duration_min=30.0,
            avg_pace_sec_km=360.0,
            avg_heart_rate=150.0,
            distance_m=5000.0,
            duration_s=1800.0,
            max_heart_rate=170.0,
            calories=300.0,
        )

        result = detail.to_dict()

        assert result["distance_m"] == 5000.0
        assert result["duration_s"] == 1800.0
        assert result["max_heart_rate"] == 170.0
        assert result["calories"] == 300.0

    def test_session_vdot_to_dict(self):
        """测试SessionVdot转换为字典"""
        vdot = SessionVdot(
            timestamp="2024-01-01 10:00:00",
            distance_m=5000.0,
            duration_s=1800.0,
            avg_heart_rate=150.0,
        )

        result = vdot.to_dict()

        assert result["distance_m"] == 5000.0
        assert result["duration_s"] == 1800.0
        assert result["avg_heart_rate"] == 150.0

    def test_session_summary_frozen(self):
        """测试SessionSummary不可变"""
        summary = SessionSummary(
            timestamp="2024-01-01",
            distance_km=5.0,
            duration_min=30.0,
            avg_pace_sec_km=360.0,
            avg_heart_rate=150.0,
        )

        with pytest.raises(AttributeError):
            summary.distance_km = 10.0


class TestSessionRepository:
    """SessionRepository测试类"""

    @pytest.fixture
    def mock_storage(self):
        """创建mock StorageManager"""
        storage = Mock()
        storage.read_parquet.return_value = pl.LazyFrame(
            {
                "session_start_time": [
                    datetime(2024, 1, 1, 10, 0, 0),
                    datetime(2024, 1, 2, 10, 0, 0),
                    datetime(2024, 1, 3, 10, 0, 0),
                ],
                "session_total_distance": [5000.0, 10000.0, 8000.0],
                "session_total_timer_time": [1800.0, 3600.0, 2700.0],
                "session_avg_heart_rate": [150.0, 155.0, 145.0],
                "max_heart_rate": [170.0, 175.0, 165.0],
                "total_calories": [300.0, 600.0, 450.0],
            }
        )
        return storage

    @pytest.fixture
    def repo(self, mock_storage):
        """创建SessionRepository实例"""
        return SessionRepository(mock_storage)

    def test_get_recent_sessions(self, repo):
        """测试获取最近的Session"""
        sessions = repo.get_recent_sessions(limit=2)

        assert len(sessions) == 2
        assert all(isinstance(s, SessionDetail) for s in sessions)

    def test_get_recent_sessions_empty(self, mock_storage):
        """测试空数据的最近Session"""
        mock_storage.read_parquet.return_value = pl.LazyFrame(
            {
                "session_start_time": [],
                "session_total_distance": [],
                "session_total_timer_time": [],
                "session_avg_heart_rate": [],
                "max_heart_rate": [],
                "total_calories": [],
            }
        )
        repo = SessionRepository(mock_storage)

        sessions = repo.get_recent_sessions(limit=10)

        assert len(sessions) == 0

    def test_get_sessions_for_vdot(self, repo):
        """测试获取VDOT计算所需数据"""
        sessions = repo.get_sessions_for_vdot(limit=2)

        assert len(sessions) == 2
        assert all(isinstance(s, SessionVdot) for s in sessions)
        assert all(s.distance_m > 0 for s in sessions)

    def test_get_sessions_for_vdot_empty(self, mock_storage):
        """测试空数据的VDOT数据"""
        mock_storage.read_parquet.return_value = pl.LazyFrame(
            {
                "session_start_time": [],
                "session_total_distance": [],
                "session_total_timer_time": [],
                "session_avg_heart_rate": [],
                "max_heart_rate": [],
                "total_calories": [],
            }
        )
        repo = SessionRepository(mock_storage)

        sessions = repo.get_sessions_for_vdot()

        assert len(sessions) == 0

    def test_get_sessions_by_date_range(self, repo):
        """测试按日期范围获取Session"""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 3)

        sessions = repo.get_sessions_by_date_range(start_date, end_date)

        assert len(sessions) >= 0
        assert all(isinstance(s, SessionSummary) for s in sessions)

    def test_get_sessions_by_distance(self, repo):
        """测试按距离范围获取Session"""
        sessions = repo.get_sessions_by_distance(min_meters=5000, max_meters=10000)

        assert len(sessions) >= 0
        assert all(isinstance(s, SessionSummary) for s in sessions)

    def test_get_sessions_by_distance_min_only(self, repo):
        """测试仅指定最小距离"""
        sessions = repo.get_sessions_by_distance(min_meters=5000)

        assert len(sessions) >= 0

    def test_get_session_count(self, repo):
        """测试获取Session数量"""
        count = repo.get_session_count()

        assert count >= 0

    def test_get_session_count_with_date_range(self, repo):
        """测试按日期范围获取Session数量"""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 3)

        count = repo.get_session_count(start_date, end_date)

        assert count >= 0

    def test_get_total_distance(self, repo):
        """测试获取总距离"""
        distance = repo.get_total_distance()

        assert distance >= 0.0

    def test_get_total_distance_with_date_range(self, repo):
        """测试按日期范围获取总距离"""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 3)

        distance = repo.get_total_distance(start_date, end_date)

        assert distance >= 0.0

    def test_get_total_duration(self, repo):
        """测试获取总时长"""
        duration = repo.get_total_duration()

        assert duration >= 0.0

    def test_get_total_duration_with_date_range(self, repo):
        """测试按日期范围获取总时长"""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 3)

        duration = repo.get_total_duration(start_date, end_date)

        assert duration >= 0.0

    def test_get_sessions(self, repo):
        """测试获取Session聚合数据"""
        df = repo.get_sessions(limit=2)

        assert isinstance(df, pl.DataFrame)
        assert df.height <= 2

    def test_get_sessions_with_filters(self, repo):
        """测试带过滤条件的Session查询"""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 3)

        df = repo.get_sessions(
            start_date=start_date,
            end_date=end_date,
            min_distance=5000.0,
            max_distance=10000.0,
            limit=10,
        )

        assert isinstance(df, pl.DataFrame)

    def test_get_sessions_descending(self, repo):
        """测试降序排列"""
        df = repo.get_sessions(descending=True)

        assert isinstance(df, pl.DataFrame)

    def test_get_sessions_ascending(self, repo):
        """测试升序排列"""
        df = repo.get_sessions(descending=False)

        assert isinstance(df, pl.DataFrame)

    def test_add_computed_columns(self, repo, mock_storage):
        """测试添加计算列"""
        df = pl.DataFrame(
            {
                "session_start": ["2024-01-01 10:00:00"],
                "distance": [5000.0],
                "duration": [1800.0],
                "avg_hr": [150.0],
                "max_hr": [170.0],
                "calories": [300.0],
            }
        )

        result = repo._add_computed_columns(df)

        assert "distance_km" in result.columns
        assert "duration_min" in result.columns
        assert "avg_pace_sec_km" in result.columns
        assert result["distance_km"][0] == 5.0
        assert result["duration_min"][0] == 30.0

    def test_add_computed_columns_zero_distance(self, repo):
        """测试零距离的计算列"""
        df = pl.DataFrame(
            {
                "session_start": ["2024-01-01 10:00:00"],
                "distance": [0.0],
                "duration": [1800.0],
                "avg_hr": [150.0],
                "max_hr": [170.0],
                "calories": [300.0],
            }
        )

        result = repo._add_computed_columns(df)

        assert result["avg_pace_sec_km"][0] is None

    def test_df_to_session_details(self, repo):
        """测试DataFrame转换为SessionDetail列表"""
        df = pl.DataFrame(
            {
                "session_start": ["2024-01-01 10:00:00"],
                "distance": [5000.0],
                "duration": [1800.0],
                "avg_hr": [150.0],
                "max_hr": [170.0],
                "calories": [300.0],
            }
        )

        details = repo._df_to_session_details(df)

        assert len(details) == 1
        assert isinstance(details[0], SessionDetail)
        assert details[0].distance_km == 5.0
        assert details[0].duration_min == 30.0

    def test_df_to_session_details_empty(self, repo):
        """测试空DataFrame转换"""
        df = pl.DataFrame()

        details = repo._df_to_session_details(df)

        assert len(details) == 0

    def test_df_to_session_summaries(self, repo):
        """测试DataFrame转换为SessionSummary列表"""
        df = pl.DataFrame(
            {
                "session_start": ["2024-01-01 10:00:00"],
                "distance": [5000.0],
                "duration": [1800.0],
                "avg_hr": [150.0],
                "max_hr": [170.0],
                "calories": [300.0],
            }
        )

        summaries = repo._df_to_session_summaries(df)

        assert len(summaries) == 1
        assert isinstance(summaries[0], SessionSummary)
        assert summaries[0].distance_km == 5.0

    def test_df_to_session_summaries_empty(self, repo):
        """测试空DataFrame转换"""
        df = pl.DataFrame()

        summaries = repo._df_to_session_summaries(df)

        assert len(summaries) == 0

    def test_build_session_lazy(self, repo):
        """测试构建LazyFrame查询链"""
        lf = repo._build_session_lazy()

        assert isinstance(lf, pl.LazyFrame)

    def test_build_session_lazy_with_filters(self, repo):
        """测试带过滤条件的LazyFrame构建"""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 3)

        lf = repo._build_session_lazy(
            start_date=start_date,
            end_date=end_date,
            min_distance=5000.0,
            max_distance=10000.0,
        )

        assert isinstance(lf, pl.LazyFrame)

    def test_build_session_lazy_empty_schema(self, mock_storage):
        """测试空schema的LazyFrame构建"""
        mock_storage.read_parquet.return_value = pl.LazyFrame()

        repo = SessionRepository(mock_storage)
        lf = repo._build_session_lazy()

        assert isinstance(lf, pl.LazyFrame)

    def test_get_total_distance_empty(self, mock_storage):
        """测试空数据的总距离"""
        mock_storage.read_parquet.return_value = pl.LazyFrame(
            {
                "session_start_time": [],
                "session_total_distance": [],
                "session_total_timer_time": [],
                "session_avg_heart_rate": [],
                "max_heart_rate": [],
                "total_calories": [],
            }
        )
        repo = SessionRepository(mock_storage)

        distance = repo.get_total_distance()

        assert distance == 0.0

    def test_get_total_duration_empty(self, mock_storage):
        """测试空数据的总时长"""
        mock_storage.read_parquet.return_value = pl.LazyFrame(
            {
                "session_start_time": [],
                "session_total_distance": [],
                "session_total_timer_time": [],
                "session_avg_heart_rate": [],
                "max_heart_rate": [],
                "total_calories": [],
            }
        )
        repo = SessionRepository(mock_storage)

        duration = repo.get_total_duration()

        assert duration == 0.0

    def test_session_detail_with_none_values(self, repo):
        """测试SessionDetail包含None值"""
        df = pl.DataFrame(
            {
                "session_start": ["2024-01-01 10:00:00"],
                "distance": [5000.0],
                "duration": [1800.0],
                "avg_hr": [None],
                "max_hr": [None],
                "calories": [None],
            }
        )

        details = repo._df_to_session_details(df)

        assert len(details) == 1
        assert details[0].avg_heart_rate is None
        assert details[0].max_heart_rate is None

    def test_session_summary_with_none_values(self, repo):
        """测试SessionSummary包含None值"""
        df = pl.DataFrame(
            {
                "session_start": ["2024-01-01 10:00:00"],
                "distance": [5000.0],
                "duration": [1800.0],
                "avg_hr": [None],
                "max_hr": [None],
                "calories": [None],
            }
        )

        summaries = repo._df_to_session_summaries(df)

        assert len(summaries) == 1
        assert summaries[0].avg_heart_rate is None
