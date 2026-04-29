# 训练负荷分析器单元测试
# 测试TSS、ATL、CTL、TSB计算等功能

import polars as pl
import pytest

from src.core.calculators.training_load_analyzer import TrainingLoadAnalyzer


class TestTrainingLoadAnalyzer:
    """训练负荷分析器测试类"""

    @pytest.fixture
    def analyzer(self):
        """创建训练负荷分析器实例"""
        return TrainingLoadAnalyzer()

    def test_calculate_tss_normal(self, analyzer):
        """测试正常TSS计算"""
        hr_data = pl.Series([150, 155, 160, 155, 150])
        duration_s = 3600

        tss = analyzer.calculate_tss(hr_data, duration_s)

        assert tss > 0
        assert tss <= 100

    def test_calculate_tss_empty_hr(self, analyzer):
        """测试空心率数据"""
        hr_data = pl.Series([])
        duration_s = 3600

        with pytest.raises(ValueError, match="心率数据不能为空"):
            analyzer.calculate_tss(hr_data, duration_s)

    def test_calculate_tss_zero_duration(self, analyzer):
        """测试零时长"""
        hr_data = pl.Series([150, 155, 160])
        duration_s = 0

        with pytest.raises(ValueError, match="心率数据不能为空"):
            analyzer.calculate_tss(hr_data, duration_s)

    def test_calculate_tss_negative_duration(self, analyzer):
        """测试负时长"""
        hr_data = pl.Series([150, 155, 160])
        duration_s = -100

        with pytest.raises(ValueError, match="心率数据不能为空"):
            analyzer.calculate_tss(hr_data, duration_s)

    def test_calculate_tss_for_run_with_hr(self, analyzer):
        """测试带心率的跑步TSS计算"""
        distance_m = 5000
        duration_s = 1500
        avg_heart_rate = 150

        tss = analyzer.calculate_tss_for_run(distance_m, duration_s, avg_heart_rate)

        assert tss > 0

    def test_calculate_tss_for_run_without_hr(self, analyzer):
        """测试不带心率的跑步TSS计算"""
        distance_m = 5000
        duration_s = 1500

        tss = analyzer.calculate_tss_for_run(distance_m, duration_s)

        assert tss > 0

    def test_calculate_tss_for_run_none_distance(self, analyzer):
        """测试None距离"""
        tss = analyzer.calculate_tss_for_run(None, 1500)
        assert tss == 0.0

    def test_calculate_tss_for_run_none_duration(self, analyzer):
        """测试None时长"""
        tss = analyzer.calculate_tss_for_run(5000, None)
        assert tss == 0.0

    def test_calculate_tss_for_run_zero_distance(self, analyzer):
        """测试零距离"""
        tss = analyzer.calculate_tss_for_run(0, 1500)
        assert tss == 0.0

    def test_calculate_tss_for_run_zero_duration(self, analyzer):
        """测试零时长"""
        tss = analyzer.calculate_tss_for_run(5000, 0)
        assert tss == 0.0

    def test_calculate_tss_batch(self, analyzer):
        """测试批量TSS计算"""
        df = pl.DataFrame(
            {
                "session_total_distance": [5000.0, 10000.0, 5000.0],
                "session_total_timer_time": [1500.0, 3000.0, 1800.0],
                "session_avg_heart_rate": [150.0, 155.0, 145.0],
            }
        )

        tss_series = analyzer.calculate_tss_batch(df)

        assert len(tss_series) == 3
        assert all(tss > 0 for tss in tss_series)

    def test_calculate_tss_batch_empty(self, analyzer):
        """测试空DataFrame批量计算"""
        df = pl.DataFrame(
            {
                "session_total_distance": [],
                "session_total_timer_time": [],
                "session_avg_heart_rate": [],
            }
        )

        tss_series = analyzer.calculate_tss_batch(df)
        assert len(tss_series) == 0

    def test_calculate_tss_batch_with_nulls(self, analyzer):
        """测试包含null值的批量计算"""
        df = pl.DataFrame(
            {
                "session_total_distance": [5000.0, None, 10000.0],
                "session_total_timer_time": [1500.0, 3000.0, None],
                "session_avg_heart_rate": [150.0, 155.0, None],
            }
        )

        tss_series = analyzer.calculate_tss_batch(df)

        assert len(tss_series) == 3

    def test_calculate_ewma_basic(self, analyzer):
        """测试EWMA基础计算"""
        tss_values = [100.0, 80.0, 60.0, 40.0, 20.0]

        ewma = analyzer._calculate_ewma(tss_values, 7.0)

        assert ewma > 0
        assert ewma <= max(tss_values)

    def test_calculate_ewma_empty(self, analyzer):
        """测试空列表EWMA"""
        ewma = analyzer._calculate_ewma([], 7.0)
        assert ewma == 0.0

    def test_calculate_ewma_single_value(self, analyzer):
        """测试单值EWMA"""
        ewma = analyzer._calculate_ewma([100.0], 7.0)
        assert ewma == 100.0

    def test_calculate_ewma_vectorized(self, analyzer):
        """测试向量化EWMA"""
        tss_series = pl.Series([100.0, 80.0, 60.0, 40.0, 20.0])

        ewma = analyzer.calculate_ewma_vectorized(tss_series, 7.0)

        assert ewma > 0

    def test_calculate_ewma_vectorized_empty(self, analyzer):
        """测试空Series向量化EWMA"""
        tss_series = pl.Series([])

        ewma = analyzer.calculate_ewma_vectorized(tss_series, 7.0)
        assert ewma == 0.0

    def test_calculate_atl(self, analyzer):
        """测试ATL计算"""
        tss_values = [100.0, 80.0, 60.0, 40.0, 20.0, 50.0, 70.0]

        atl = analyzer.calculate_atl(tss_values)

        assert atl > 0

    def test_calculate_atl_empty(self, analyzer):
        """测试空列表ATL"""
        atl = analyzer.calculate_atl([])
        assert atl == 0.0

    def test_calculate_ctl(self, analyzer):
        """测试CTL计算"""
        tss_values = [100.0, 80.0, 60.0, 40.0, 20.0, 50.0, 70.0] * 6

        ctl = analyzer.calculate_ctl(tss_values)

        assert ctl > 0

    def test_calculate_ctl_empty(self, analyzer):
        """测试空列表CTL"""
        ctl = analyzer.calculate_ctl([])
        assert ctl == 0.0

    def test_calculate_atl_ctl(self, analyzer):
        """测试ATL/CTL联合计算"""
        tss_values = [100.0, 80.0, 60.0, 40.0, 20.0, 50.0, 70.0]

        result = analyzer.calculate_atl_ctl(tss_values)

        assert "atl" in result
        assert "ctl" in result
        assert result["atl"] >= 0
        assert result["ctl"] >= 0

    def test_calculate_atl_ctl_empty(self, analyzer):
        """测试空列表ATL/CTL"""
        result = analyzer.calculate_atl_ctl([])

        assert result["atl"] == 0.0
        assert result["ctl"] == 0.0

    def test_calculate_atl_ctl_vectorized(self, analyzer):
        """测试向量化ATL/CTL计算"""
        tss_series = pl.Series([100.0, 80.0, 60.0, 40.0, 20.0, 50.0, 70.0])

        result = analyzer.calculate_atl_ctl_vectorized(tss_series, 7, 42)

        assert "atl" in result
        assert "ctl" in result

    def test_calculate_atl_ctl_vectorized_empty(self, analyzer):
        """测试空Series向量化ATL/CTL"""
        tss_series = pl.Series([])

        result = analyzer.calculate_atl_ctl_vectorized(tss_series, 7, 42)

        assert result["atl"] == 0.0
        assert result["ctl"] == 0.0

    def test_calculate_training_load_from_dataframe(self, analyzer):
        """测试从DataFrame计算训练负荷"""
        df = pl.DataFrame(
            {
                "session_total_distance": [5000.0, 10000.0, 5000.0],
                "session_total_timer_time": [1500.0, 3000.0, 1800.0],
                "session_avg_heart_rate": [150.0, 155.0, 145.0],
            }
        )

        result = analyzer.calculate_training_load_from_dataframe(df)

        assert "atl" in result
        assert "ctl" in result
        assert "tsb" in result
        assert "fitness_status" in result

    def test_calculate_training_load_from_dataframe_empty(self, analyzer):
        """测试空DataFrame训练负荷"""
        df = pl.DataFrame(
            {
                "session_total_distance": [],
                "session_total_timer_time": [],
                "session_avg_heart_rate": [],
            }
        )

        result = analyzer.calculate_training_load_from_dataframe(df)

        assert result["atl"] == 0.0
        assert result["ctl"] == 0.0
        assert result["fitness_status"] == "数据不足"

    def test_update_atl_incremental(self, analyzer):
        """测试ATL增量更新"""
        analyzer.reset_incremental_state()

        atl1 = analyzer.update_atl_incremental(100.0)
        atl2 = analyzer.update_atl_incremental(80.0)

        assert atl1 > 0
        assert atl2 > 0

    def test_update_ctl_incremental(self, analyzer):
        """测试CTL增量更新"""
        analyzer.reset_incremental_state()

        ctl1 = analyzer.update_ctl_incremental(100.0)
        ctl2 = analyzer.update_ctl_incremental(80.0)

        assert ctl1 > 0
        assert ctl2 > 0

    def test_update_atl_ctl_incremental(self, analyzer):
        """测试ATL/CTL联合增量更新"""
        analyzer.reset_incremental_state()

        result = analyzer.update_atl_ctl_incremental(100.0)

        assert "atl" in result
        assert "ctl" in result

    def test_reset_incremental_state(self, analyzer):
        """测试重置增量状态"""
        analyzer.update_atl_incremental(100.0)
        analyzer.update_ctl_incremental(80.0)

        analyzer.reset_incremental_state()

        state = analyzer.get_incremental_state()
        assert state["atl"] == 0.0
        assert state["ctl"] == 0.0

    def test_initialize_incremental_state(self, analyzer):
        """测试初始化增量状态"""
        analyzer.initialize_incremental_state(50.0, 60.0)

        state = analyzer.get_incremental_state()
        assert state["atl"] == 50.0
        assert state["ctl"] == 60.0
        assert state["atl_initialized"] is True
        assert state["ctl_initialized"] is True

    def test_get_incremental_state(self, analyzer):
        """测试获取增量状态"""
        state = analyzer.get_incremental_state()

        assert "atl" in state
        assert "ctl" in state
        assert "atl_initialized" in state
        assert "ctl_initialized" in state

    def test_evaluate_training_status_recovery(self, analyzer):
        """测试恢复良好状态"""
        atl = 30.0
        ctl = 50.0

        result = analyzer.evaluate_training_status(atl, ctl)

        assert result["tsb"] == 20.0
        assert result["fitness_status"] == "恢复良好"

    def test_evaluate_training_status_normal(self, analyzer):
        """测试状态正常"""
        atl = 40.0
        ctl = 50.0

        result = analyzer.evaluate_training_status(atl, ctl)

        assert result["tsb"] == 10.0
        assert result["fitness_status"] == "状态正常"

    def test_evaluate_training_status_fatigue(self, analyzer):
        """测试轻度疲劳"""
        atl = 55.0
        ctl = 50.0

        result = analyzer.evaluate_training_status(atl, ctl)

        assert result["tsb"] == -5.0
        assert result["fitness_status"] == "轻度疲劳"

    def test_evaluate_training_status_over_training(self, analyzer):
        """测试过度训练"""
        atl = 80.0
        ctl = 60.0

        result = analyzer.evaluate_training_status(atl, ctl)

        assert result["tsb"] == -20.0
        assert result["fitness_status"] == "过度训练"

    def test_atl_ctl_consistency(self, analyzer):
        """测试ATL/CTL计算一致性"""
        tss_values = [100.0, 80.0, 60.0, 40.0, 20.0, 50.0, 70.0]

        atl = analyzer.calculate_atl(tss_values)
        ctl = analyzer.calculate_ctl(tss_values)

        tss_series = pl.Series(tss_values)
        vectorized = analyzer.calculate_atl_ctl_vectorized(tss_series, 7, 42)

        assert abs(atl - vectorized["atl"]) < 1.0
        assert abs(ctl - vectorized["ctl"]) < 1.0

    def test_incremental_vs_batch(self, analyzer):
        """测试增量计算与批量计算一致性"""
        tss_values = [100.0, 80.0, 60.0, 40.0, 20.0]

        batch_atl_ctl = analyzer.calculate_atl_ctl(tss_values)

        analyzer.reset_incremental_state()
        for tss in tss_values:
            result = analyzer.update_atl_ctl_incremental(tss)

        incremental_state = analyzer.get_incremental_state()

        assert abs(batch_atl_ctl["atl"] - incremental_state["atl"]) < 30.0

    def test_tss_batch_with_different_ages(self, analyzer):
        """测试不同年龄的批量TSS计算"""
        df = pl.DataFrame(
            {
                "session_total_distance": [5000.0, 10000.0],
                "session_total_timer_time": [1500.0, 3000.0],
                "session_avg_heart_rate": [150.0, 155.0],
            }
        )

        tss_20 = analyzer.calculate_tss_batch(df, age=20)
        tss_40 = analyzer.calculate_tss_batch(df, age=40)

        assert len(tss_20) == len(tss_40)

    def test_tss_batch_with_different_rest_hr(self, analyzer):
        """测试不同静息心率的批量TSS计算"""
        df = pl.DataFrame(
            {
                "session_total_distance": [5000.0, 10000.0],
                "session_total_timer_time": [1500.0, 3000.0],
                "session_avg_heart_rate": [150.0, 155.0],
            }
        )

        tss_50 = analyzer.calculate_tss_batch(df, rest_hr=50)
        tss_70 = analyzer.calculate_tss_batch(df, rest_hr=70)

        assert len(tss_50) == len(tss_70)
