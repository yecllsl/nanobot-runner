# SessionRepository 单元测试
# 测试 Session 数据仓储层的聚合查询逻辑

from datetime import datetime, timedelta
from unittest.mock import Mock

import polars as pl
import pytest

from src.core.session_repository import (
    SessionDetail,
    SessionRepository,
    SessionSummary,
    SessionVdot,
)


def _make_session_df(
    count: int = 5, base_date: datetime = datetime(2025, 1, 1)
) -> pl.DataFrame:
    """构造测试用的Session DataFrame（使用group_by后的标准列名）"""
    rows = []
    for i in range(count):
        ts = base_date + timedelta(days=i)
        rows.append(
            {
                "session_start_time": ts,
                "session_start": ts,
                "session_total_distance": 5000.0 + i * 1000,
                "session_total_timer_time": 1800.0 + i * 300,
                "session_avg_heart_rate": 150.0 + i,
                "max_heart_rate": 175.0 + i,
                "total_calories": 300.0 + i * 10,
                "distance": 5000.0 + i * 1000,
                "duration": 1800.0 + i * 300,
                "avg_hr": 150.0 + i,
                "max_hr": 175.0 + i,
                "calories": 300.0 + i * 10,
            }
        )
    return pl.DataFrame(rows)


def _make_lazy_frame(df: pl.DataFrame) -> pl.LazyFrame:
    """将DataFrame包装为LazyFrame"""
    return df.lazy()


@pytest.fixture
def mock_storage():
    """创建Mock StorageManager"""
    storage = Mock()
    return storage


@pytest.fixture
def repo(mock_storage):
    """创建SessionRepository实例"""
    return SessionRepository(storage=mock_storage)


@pytest.fixture
def sample_df():
    """创建测试用DataFrame"""
    return _make_session_df()


@pytest.fixture
def sample_lf(sample_df):
    """创建测试用LazyFrame"""
    return _make_lazy_frame(sample_df)


class TestSessionDataClasses:
    """测试Session数据类"""

    def test_session_summary_creation(self):
        """测试SessionSummary创建"""
        summary = SessionSummary(
            timestamp="2025-01-01",
            distance_km=5.0,
            duration_min=30.0,
            avg_pace_sec_km=6.0,
            avg_heart_rate=150.0,
        )
        assert summary.timestamp == "2025-01-01"
        assert summary.distance_km == 5.0
        assert summary.duration_min == 30.0

    def test_session_summary_to_dict(self):
        """测试SessionSummary转换为字典"""
        summary = SessionSummary(
            timestamp="2025-01-01",
            distance_km=5.0,
            duration_min=30.0,
            avg_pace_sec_km=6.0,
            avg_heart_rate=150.0,
        )
        d = summary.to_dict()
        assert d["timestamp"] == "2025-01-01"
        assert d["distance_km"] == 5.0
        assert d["avg_heart_rate"] == 150.0

    def test_session_detail_creation(self):
        """测试SessionDetail创建"""
        detail = SessionDetail(
            timestamp="2025-01-01",
            distance_km=5.0,
            duration_min=30.0,
            avg_pace_sec_km=6.0,
            avg_heart_rate=150.0,
            distance_m=5000.0,
            duration_s=1800.0,
            max_heart_rate=175.0,
            calories=300.0,
        )
        assert detail.distance_m == 5000.0
        assert detail.duration_s == 1800.0
        assert detail.max_heart_rate == 175.0

    def test_session_detail_to_dict(self):
        """测试SessionDetail转换为字典"""
        detail = SessionDetail(
            timestamp="2025-01-01",
            distance_km=5.0,
            duration_min=30.0,
            avg_pace_sec_km=6.0,
            avg_heart_rate=150.0,
            distance_m=5000.0,
            duration_s=1800.0,
            max_heart_rate=175.0,
            calories=300.0,
        )
        d = detail.to_dict()
        assert d["distance_m"] == 5000.0
        assert d["duration_s"] == 1800.0
        assert d["max_heart_rate"] == 175.0
        assert d["calories"] == 300.0

    def test_session_vdot_creation(self):
        """测试SessionVdot创建"""
        vdot = SessionVdot(
            timestamp="2025-01-01",
            distance_m=5000.0,
            duration_s=1800.0,
            avg_heart_rate=150.0,
        )
        assert vdot.distance_m == 5000.0
        assert vdot.duration_s == 1800.0

    def test_session_vdot_to_dict(self):
        """测试SessionVdot转换为字典"""
        vdot = SessionVdot(
            timestamp="2025-01-01",
            distance_m=5000.0,
            duration_s=1800.0,
            avg_heart_rate=150.0,
        )
        d = vdot.to_dict()
        assert d["distance_m"] == 5000.0
        assert d["duration_s"] == 1800.0

    def test_session_summary_frozen(self):
        """测试SessionSummary不可变"""
        summary = SessionSummary(
            timestamp="2025-01-01",
            distance_km=5.0,
            duration_min=30.0,
            avg_pace_sec_km=6.0,
            avg_heart_rate=150.0,
        )
        with pytest.raises(AttributeError):
            summary.distance_km = 10.0


class TestSessionRepositoryInit:
    """测试SessionRepository初始化"""

    def test_init_with_storage(self, mock_storage):
        """测试使用StorageManager初始化"""
        repo = SessionRepository(storage=mock_storage)
        assert repo.storage is mock_storage

    def test_session_columns_defined(self, repo):
        """测试SESSION_COLUMNS常量定义"""
        assert "session_start_time" in repo.SESSION_COLUMNS
        assert "session_total_distance" in repo.SESSION_COLUMNS
        assert "session_total_timer_time" in repo.SESSION_COLUMNS


class TestBuildSessionLazy:
    """测试_build_session_lazy方法"""

    def test_build_lazy_returns_lazyframe(self, repo, mock_storage, sample_lf):
        """测试返回LazyFrame类型"""
        mock_storage.read_parquet.return_value = sample_lf
        result = repo._build_session_lazy()
        assert isinstance(result, pl.LazyFrame)

    def test_build_lazy_with_date_filter(self, repo, mock_storage, sample_lf):
        """测试日期过滤"""
        mock_storage.read_parquet.return_value = sample_lf
        start = datetime(2025, 1, 1)
        end = datetime(2025, 1, 3)
        result = repo._build_session_lazy(start_date=start, end_date=end)
        df = result.collect()
        assert all(start <= ts <= end for ts in df["session_start"].to_list())

    def test_build_lazy_with_distance_filter(self, repo, mock_storage, sample_lf):
        """测试距离过滤"""
        mock_storage.read_parquet.return_value = sample_lf
        result = repo._build_session_lazy(min_distance=6000.0)
        df = result.collect()
        assert all(d >= 6000.0 for d in df["distance"].to_list())

    def test_build_lazy_with_distance_range(self, repo, mock_storage, sample_lf):
        """测试距离范围过滤"""
        mock_storage.read_parquet.return_value = sample_lf
        result = repo._build_session_lazy(min_distance=5000.0, max_distance=8000.0)
        df = result.collect()
        for d in df["distance"].to_list():
            assert 5000.0 <= d <= 8000.0

    def test_build_lazy_descending(self, repo, mock_storage, sample_lf):
        """测试降序排序"""
        mock_storage.read_parquet.return_value = sample_lf
        result = repo._build_session_lazy(descending=True)
        df = result.collect()
        dates = df["session_start"].to_list()
        assert dates == sorted(dates, reverse=True)

    def test_build_lazy_ascending(self, repo, mock_storage, sample_lf):
        """测试升序排序"""
        mock_storage.read_parquet.return_value = sample_lf
        result = repo._build_session_lazy(descending=False)
        df = result.collect()
        dates = df["session_start"].to_list()
        assert dates == sorted(dates)

    def test_build_lazy_empty_data(self, repo, mock_storage):
        """测试空数据"""
        mock_storage.read_parquet.return_value = pl.LazyFrame()
        result = repo._build_session_lazy()
        df = result.collect()
        assert df.is_empty()


class TestAddComputedColumns:
    """测试_add_computed_columns方法"""

    def test_adds_distance_km(self, repo, sample_df):
        """测试添加distance_km列"""
        result = repo._add_computed_columns(sample_df)
        assert "distance_km" in result.columns
        expected = sample_df["distance"] / 1000
        assert result["distance_km"].round(2).to_list() == expected.round(2).to_list()

    def test_adds_duration_min(self, repo, sample_df):
        """测试添加duration_min列"""
        result = repo._add_computed_columns(sample_df)
        assert "duration_min" in result.columns
        expected = sample_df["duration"] / 60
        assert result["duration_min"].round(1).to_list() == expected.round(1).to_list()

    def test_adds_avg_pace(self, repo, sample_df):
        """测试添加avg_pace_sec_km列"""
        result = repo._add_computed_columns(sample_df)
        assert "avg_pace_sec_km" in result.columns
        for i in range(result.height):
            if sample_df["distance"][i] > 0:
                expected_pace = (sample_df["duration"][i] / 60) / (
                    sample_df["distance"][i] / 1000
                )
                assert abs(result["avg_pace_sec_km"][i] - round(expected_pace, 1)) < 0.1

    def test_avg_pace_none_when_zero_distance(self, repo):
        """测试距离为0时配速为None"""
        df = pl.DataFrame(
            {
                "distance": [0.0],
                "duration": [1800.0],
            }
        )
        result = repo._add_computed_columns(df)
        assert result["avg_pace_sec_km"][0] is None

    def test_empty_dataframe(self, repo):
        """测试空DataFrame"""
        df = pl.DataFrame(
            {
                "distance": pl.Series([], dtype=pl.Float64),
                "duration": pl.Series([], dtype=pl.Float64),
            }
        )
        result = repo._add_computed_columns(df)
        assert result.is_empty()


class TestGetSessions:
    """测试get_sessions方法"""

    def test_returns_dataframe(self, repo, mock_storage, sample_lf):
        """测试返回DataFrame"""
        mock_storage.read_parquet.return_value = sample_lf
        result = repo.get_sessions()
        assert isinstance(result, pl.DataFrame)

    def test_with_limit(self, repo, mock_storage, sample_lf):
        """测试数量限制"""
        mock_storage.read_parquet.return_value = sample_lf
        result = repo.get_sessions(limit=2)
        assert result.height <= 2

    def test_with_date_range(self, repo, mock_storage, sample_lf):
        """测试日期范围过滤"""
        mock_storage.read_parquet.return_value = sample_lf
        start = datetime(2025, 1, 1)
        end = datetime(2025, 1, 2)
        result = repo.get_sessions(start_date=start, end_date=end)
        for ts in result["session_start"].to_list():
            assert start <= ts <= end

    def test_with_distance_filter(self, repo, mock_storage, sample_lf):
        """测试距离过滤"""
        mock_storage.read_parquet.return_value = sample_lf
        result = repo.get_sessions(min_distance=7000.0)
        for d in result["distance"].to_list():
            assert d >= 7000.0

    def test_empty_data(self, repo, mock_storage):
        """测试空数据"""
        mock_storage.read_parquet.return_value = pl.LazyFrame()
        result = repo.get_sessions()
        assert result.is_empty()


class TestGetRecentSessions:
    """测试get_recent_sessions方法"""

    def test_returns_session_details(self, repo, mock_storage, sample_lf):
        """测试返回SessionDetail列表"""
        mock_storage.read_parquet.return_value = sample_lf
        result = repo.get_recent_sessions(limit=3)
        assert isinstance(result, list)
        assert all(isinstance(r, SessionDetail) for r in result)

    def test_limit_applied(self, repo, mock_storage, sample_lf):
        """测试数量限制"""
        mock_storage.read_parquet.return_value = sample_lf
        result = repo.get_recent_sessions(limit=2)
        assert len(result) <= 2

    def test_detail_fields_populated(self, repo, mock_storage, sample_lf):
        """测试详情字段填充"""
        mock_storage.read_parquet.return_value = sample_lf
        result = repo.get_recent_sessions(limit=1)
        if result:
            detail = result[0]
            assert detail.timestamp != ""
            assert detail.distance_km > 0
            assert detail.duration_min > 0
            assert detail.distance_m > 0
            assert detail.duration_s > 0

    def test_empty_data(self, repo, mock_storage):
        """测试空数据"""
        mock_storage.read_parquet.return_value = pl.LazyFrame()
        result = repo.get_recent_sessions()
        assert result == []


class TestGetSessionsForVdot:
    """测试get_sessions_for_vdot方法"""

    def test_returns_session_vdots(self, repo, mock_storage, sample_lf):
        """测试返回SessionVdot列表"""
        mock_storage.read_parquet.return_value = sample_lf
        result = repo.get_sessions_for_vdot()
        assert isinstance(result, list)
        assert all(isinstance(r, SessionVdot) for r in result)

    def test_vdot_fields(self, repo, mock_storage, sample_lf):
        """测试VDOT字段"""
        mock_storage.read_parquet.return_value = sample_lf
        result = repo.get_sessions_for_vdot(limit=2)
        if result:
            vdot = result[0]
            assert vdot.distance_m > 0
            assert vdot.duration_s > 0

    def test_with_limit(self, repo, mock_storage, sample_lf):
        """测试数量限制"""
        mock_storage.read_parquet.return_value = sample_lf
        result = repo.get_sessions_for_vdot(limit=2)
        assert len(result) <= 2

    def test_empty_data(self, repo, mock_storage):
        """测试空数据"""
        mock_storage.read_parquet.return_value = pl.LazyFrame()
        result = repo.get_sessions_for_vdot()
        assert result == []


class TestGetSessionsByDateRange:
    """测试get_sessions_by_date_range方法"""

    def test_returns_session_summaries(self, repo, mock_storage, sample_lf):
        """测试返回SessionSummary列表"""
        mock_storage.read_parquet.return_value = sample_lf
        start = datetime(2025, 1, 1)
        end = datetime(2025, 1, 5)
        result = repo.get_sessions_by_date_range(start, end)
        assert isinstance(result, list)
        assert all(isinstance(r, SessionSummary) for r in result)

    def test_date_range_filter(self, repo, mock_storage, sample_lf):
        """测试日期范围过滤"""
        mock_storage.read_parquet.return_value = sample_lf
        start = datetime(2025, 1, 1)
        end = datetime(2025, 1, 2)
        result = repo.get_sessions_by_date_range(start, end)
        assert len(result) >= 0

    def test_empty_data(self, repo, mock_storage):
        """测试空数据"""
        mock_storage.read_parquet.return_value = pl.LazyFrame()
        result = repo.get_sessions_by_date_range(
            datetime(2025, 1, 1), datetime(2025, 1, 2)
        )
        assert result == []


class TestGetSessionsByDistance:
    """测试get_sessions_by_distance方法"""

    def test_returns_session_summaries(self, repo, mock_storage, sample_lf):
        """测试返回SessionSummary列表"""
        mock_storage.read_parquet.return_value = sample_lf
        result = repo.get_sessions_by_distance(min_meters=5000.0)
        assert isinstance(result, list)
        assert all(isinstance(r, SessionSummary) for r in result)

    def test_distance_filter(self, repo, mock_storage, sample_lf):
        """测试距离过滤"""
        mock_storage.read_parquet.return_value = sample_lf
        result = repo.get_sessions_by_distance(min_meters=7000.0)
        for s in result:
            assert s.distance_km >= 7.0

    def test_with_max_distance(self, repo, mock_storage, sample_lf):
        """测试最大距离过滤"""
        mock_storage.read_parquet.return_value = sample_lf
        result = repo.get_sessions_by_distance(min_meters=5000.0, max_meters=7000.0)
        for s in result:
            assert 5.0 <= s.distance_km <= 7.0

    def test_empty_data(self, repo, mock_storage):
        """测试空数据"""
        mock_storage.read_parquet.return_value = pl.LazyFrame()
        result = repo.get_sessions_by_distance(min_meters=5000.0)
        assert result == []


class TestGetSessionCount:
    """测试get_session_count方法"""

    def test_returns_int(self, repo, mock_storage, sample_lf):
        """测试返回整数"""
        mock_storage.read_parquet.return_value = sample_lf
        result = repo.get_session_count()
        assert isinstance(result, int)

    def test_count_matches_data(self, repo, mock_storage, sample_lf):
        """测试计数与数据一致"""
        mock_storage.read_parquet.return_value = sample_lf
        result = repo.get_session_count()
        assert result == 5

    def test_count_with_date_filter(self, repo, mock_storage, sample_lf):
        """测试带日期过滤的计数"""
        mock_storage.read_parquet.return_value = sample_lf
        result = repo.get_session_count(
            start_date=datetime(2025, 1, 1), end_date=datetime(2025, 1, 2)
        )
        assert result >= 0

    def test_empty_data_count(self, repo, mock_storage):
        """测试空数据计数"""
        mock_storage.read_parquet.return_value = pl.LazyFrame()
        result = repo.get_session_count()
        assert result == 0


class TestGetTotalDistance:
    """测试get_total_distance方法"""

    def test_returns_float(self, repo, mock_storage, sample_lf):
        """测试返回浮点数"""
        mock_storage.read_parquet.return_value = sample_lf
        result = repo.get_total_distance()
        assert isinstance(result, float)

    def test_total_distance_positive(self, repo, mock_storage, sample_lf):
        """测试总距离为正"""
        mock_storage.read_parquet.return_value = sample_lf
        result = repo.get_total_distance()
        assert result > 0

    def test_empty_data(self, repo, mock_storage):
        """测试空数据"""
        mock_storage.read_parquet.return_value = pl.LazyFrame()
        result = repo.get_total_distance()
        assert result == 0.0


class TestGetTotalDuration:
    """测试get_total_duration方法"""

    def test_returns_float(self, repo, mock_storage, sample_lf):
        """测试返回浮点数"""
        mock_storage.read_parquet.return_value = sample_lf
        result = repo.get_total_duration()
        assert isinstance(result, float)

    def test_total_duration_positive(self, repo, mock_storage, sample_lf):
        """测试总时长为正"""
        mock_storage.read_parquet.return_value = sample_lf
        result = repo.get_total_duration()
        assert result > 0

    def test_empty_data(self, repo, mock_storage):
        """测试空数据"""
        mock_storage.read_parquet.return_value = pl.LazyFrame()
        result = repo.get_total_duration()
        assert result == 0.0


class TestDfToSessionDetails:
    """测试_df_to_session_details方法"""

    def test_empty_df_returns_empty_list(self, repo):
        """测试空DataFrame返回空列表"""
        df = pl.DataFrame()
        result = repo._df_to_session_details(df)
        assert result == []

    def test_converts_to_session_detail(self, repo, sample_df):
        """测试转换为SessionDetail"""
        result = repo._df_to_session_details(sample_df)
        assert len(result) == sample_df.height
        assert all(isinstance(r, SessionDetail) for r in result)


class TestDfToSessionSummaries:
    """测试_df_to_session_summaries方法"""

    def test_empty_df_returns_empty_list(self, repo):
        """测试空DataFrame返回空列表"""
        df = pl.DataFrame()
        result = repo._df_to_session_summaries(df)
        assert result == []

    def test_converts_to_session_summary(self, repo, sample_df):
        """测试转换为SessionSummary"""
        result = repo._df_to_session_summaries(sample_df)
        assert len(result) == sample_df.height
        assert all(isinstance(r, SessionSummary) for r in result)
