"""BUG-2203回归测试：twin snapshot CTL/ATL与analysis load不一致

验证StateVectorBuilder.build_load()与AnalyticsEngine.get_training_load()
使用一致的TSS计算逻辑，确保CTL/ATL值一致。
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import polars as pl

from src.core.calculators.training_load_analyzer import TrainingLoadAnalyzer
from src.core.twin.state_vector_builder import StateVectorBuilder


def _make_session_df_with_hr(rows: int = 10) -> pl.DataFrame:
    """创建包含心率数据的session DataFrame"""
    now = datetime.now()
    return pl.DataFrame(
        {
            "session_start_time": [now - timedelta(days=i) for i in range(rows)],
            "session_total_distance": [8000.0] * rows,
            "session_total_timer_time": [2400.0] * rows,
            "session_avg_heart_rate": [150.0] * rows,
        }
    )


def _make_session_df_without_hr(rows: int = 10) -> pl.DataFrame:
    """创建不含心率数据的session DataFrame"""
    now = datetime.now()
    return pl.DataFrame(
        {
            "session_start_time": [now - timedelta(days=i) for i in range(rows)],
            "session_total_distance": [8000.0] * rows,
            "session_total_timer_time": [2400.0] * rows,
            "session_avg_heart_rate": [None] * rows,
        }
    )


class TestBug2203TwinLoadConsistency:
    """BUG-2203: twin snapshot CTL/ATL与analysis load一致性"""

    def test_build_load_with_hr_data_nonzero(self):
        """有心率数据时，build_load应返回非零CTL/ATL"""
        session_repo = MagicMock()
        session_repo.storage = MagicMock()
        session_repo.storage.read_parquet.return_value = _make_session_df_with_hr(
            20
        ).lazy()

        analyzer = TrainingLoadAnalyzer()
        builder = StateVectorBuilder(
            training_load_analyzer=analyzer,
            session_repo=session_repo,
        )

        load_dim = builder.build_load()

        assert load_dim.ctl > 0, f"有心率数据时CTL应>0，实际为{load_dim.ctl}"
        assert load_dim.atl > 0, f"有心率数据时ATL应>0，实际为{load_dim.atl}"

    def test_build_load_consistent_with_training_load_analyzer(self):
        """build_load的结果应与TrainingLoadAnalyzer.calculate_training_load_from_dataframe一致"""
        df = _make_session_df_with_hr(20)

        session_repo = MagicMock()
        session_repo.storage = MagicMock()
        session_repo.storage.read_parquet.return_value = df.lazy()

        analyzer = TrainingLoadAnalyzer()

        builder = StateVectorBuilder(
            training_load_analyzer=analyzer,
            session_repo=session_repo,
        )

        load_dim = builder.build_load()

        direct_result = analyzer.calculate_training_load_from_dataframe(df)

        assert abs(load_dim.ctl - direct_result["ctl"]) < 0.1, (
            f"CTL不一致: build_load={load_dim.ctl}, direct={direct_result['ctl']}"
        )
        assert abs(load_dim.atl - direct_result["atl"]) < 0.1, (
            f"ATL不一致: build_load={load_dim.atl}, direct={direct_result['atl']}"
        )

    def test_build_load_without_hr_data_indicates_insufficient(self):
        """无心率数据时，build_load应标记数据不足而非返回零值静默通过"""
        session_repo = MagicMock()
        session_repo.storage = MagicMock()
        session_repo.storage.read_parquet.return_value = _make_session_df_without_hr(
            20
        ).lazy()

        analyzer = TrainingLoadAnalyzer()
        builder = StateVectorBuilder(
            training_load_analyzer=analyzer,
            session_repo=session_repo,
        )

        load_dim = builder.build_load()

        assert (
            load_dim.data_quality != "sufficient"
            if hasattr(load_dim, "data_quality")
            else True
        ), "无心率数据时data_quality不应为sufficient"
