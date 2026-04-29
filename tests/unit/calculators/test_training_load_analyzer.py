# TrainingLoadAnalyzer 单元测试


import polars as pl
import pytest

from src.core.calculators.training_load_analyzer import (
    ATL_TIME_CONSTANT,
    TrainingLoadAnalyzer,
)


@pytest.fixture
def training_load_analyzer() -> TrainingLoadAnalyzer:
    """创建 TrainingLoadAnalyzer 实例"""
    return TrainingLoadAnalyzer()


class TestTrainingLoadAnalyzer:
    """TrainingLoadAnalyzer 测试类"""

    def test_calculate_tss_success(
        self, training_load_analyzer: TrainingLoadAnalyzer
    ) -> None:
        """测试 TSS 计算"""
        heart_rate_data = pl.Series([150, 155, 160, 158, 152])
        duration_s = 3600

        tss = training_load_analyzer.calculate_tss(heart_rate_data, duration_s)

        assert tss > 0
        assert isinstance(tss, float)

    def test_calculate_tss_invalid_input(
        self, training_load_analyzer: TrainingLoadAnalyzer
    ) -> None:
        """测试无效输入的 TSS 计算"""
        heart_rate_data = pl.Series([])
        duration_s = 3600

        with pytest.raises(ValueError, match="心率数据不能为空"):
            training_load_analyzer.calculate_tss(heart_rate_data, duration_s)

    def test_calculate_tss_for_run_with_hr(
        self, training_load_analyzer: TrainingLoadAnalyzer
    ) -> None:
        """测试带心率的单次跑步 TSS 计算"""
        distance_m = 10000
        duration_s = 3600
        avg_heart_rate = 160

        tss = training_load_analyzer.calculate_tss_for_run(
            distance_m, duration_s, avg_heart_rate
        )

        assert tss > 0

    def test_calculate_tss_for_run_without_hr(
        self, training_load_analyzer: TrainingLoadAnalyzer
    ) -> None:
        """测试不带心率的单次跑步 TSS 计算"""
        distance_m = 10000
        duration_s = 3600

        tss = training_load_analyzer.calculate_tss_for_run(distance_m, duration_s)

        assert tss > 0

    def test_calculate_tss_for_run_invalid_distance(
        self, training_load_analyzer: TrainingLoadAnalyzer
    ) -> None:
        """测试无效距离的 TSS 计算"""
        distance_m = 0
        duration_s = 3600

        tss = training_load_analyzer.calculate_tss_for_run(distance_m, duration_s)

        assert tss == 0.0

    def test_calculate_ewma_empty_list(
        self, training_load_analyzer: TrainingLoadAnalyzer
    ) -> None:
        """测试空列表的 EWMA 计算"""
        tss_values = []

        result = training_load_analyzer._calculate_ewma(tss_values, 7.0)

        assert result == 0.0

    def test_calculate_ewma_single_value(
        self, training_load_analyzer: TrainingLoadAnalyzer
    ) -> None:
        """测试单个值的 EWMA 计算"""
        tss_values = [100.0]

        result = training_load_analyzer._calculate_ewma(tss_values, 7.0)

        assert result == 100.0

    def test_calculate_ewma_multiple_values(
        self, training_load_analyzer: TrainingLoadAnalyzer
    ) -> None:
        """测试多个值的 EWMA 计算"""
        tss_values = [100.0, 150.0, 200.0]

        result = training_load_analyzer._calculate_ewma(tss_values, 7.0)

        assert result > 0
        assert isinstance(result, float)

    def test_calculate_atl(self, training_load_analyzer: TrainingLoadAnalyzer) -> None:
        """测试 ATL 计算"""
        tss_values = [100.0, 120.0, 150.0, 130.0, 110.0, 140.0, 160.0]

        atl = training_load_analyzer.calculate_atl(tss_values)

        assert atl > 0
        assert isinstance(atl, float)

    def test_calculate_ctl(self, training_load_analyzer: TrainingLoadAnalyzer) -> None:
        """测试 CTL 计算"""
        tss_values = [100.0, 120.0, 150.0, 130.0, 110.0, 140.0, 160.0]

        ctl = training_load_analyzer.calculate_ctl(tss_values)

        assert ctl > 0
        assert isinstance(ctl, float)

    def test_calculate_atl_ctl(
        self, training_load_analyzer: TrainingLoadAnalyzer
    ) -> None:
        """测试 ATL/CTL 联合计算"""
        tss_values = [100.0, 120.0, 150.0, 130.0, 110.0, 140.0, 160.0]

        result = training_load_analyzer.calculate_atl_ctl(tss_values)

        assert "atl" in result
        assert "ctl" in result
        assert result["atl"] > 0
        assert result["ctl"] > 0

    def test_calculate_atl_ctl_empty_list(
        self, training_load_analyzer: TrainingLoadAnalyzer
    ) -> None:
        """测试空列表的 ATL/CTL 计算"""
        tss_values = []

        result = training_load_analyzer.calculate_atl_ctl(tss_values)

        assert result["atl"] == 0.0
        assert result["ctl"] == 0.0

    def test_evaluate_fitness_status_good(
        self, training_load_analyzer: TrainingLoadAnalyzer
    ) -> None:
        """测试良好体能状态评估"""
        status, advice = training_load_analyzer._evaluate_fitness_status(
            15.0, 100.0, 115.0
        )

        assert status == "恢复良好"
        assert "体能充沛" in advice

    def test_evaluate_fitness_status_normal(
        self, training_load_analyzer: TrainingLoadAnalyzer
    ) -> None:
        """测试正常体能状态评估"""
        status, advice = training_load_analyzer._evaluate_fitness_status(
            5.0, 100.0, 105.0
        )

        assert status == "状态正常"
        assert "良好" in advice

    def test_evaluate_fitness_status_fatigued(
        self, training_load_analyzer: TrainingLoadAnalyzer
    ) -> None:
        """测试轻度疲劳状态评估"""
        status, advice = training_load_analyzer._evaluate_fitness_status(
            -5.0, 105.0, 100.0
        )

        assert status == "轻度疲劳"
        assert "疲劳" in advice

    def test_evaluate_fitness_status_overtrained(
        self, training_load_analyzer: TrainingLoadAnalyzer
    ) -> None:
        """测试过度训练状态评估"""
        status, advice = training_load_analyzer._evaluate_fitness_status(
            -15.0, 115.0, 100.0
        )

        assert status == "过度训练"
        assert "过度训练" in advice

    def test_evaluate_training_status(
        self, training_load_analyzer: TrainingLoadAnalyzer
    ) -> None:
        """测试训练状态评估"""
        atl = 100.0
        ctl = 115.0

        result = training_load_analyzer.evaluate_training_status(atl, ctl)

        assert "tsb" in result
        assert "fitness_status" in result
        assert "training_advice" in result
        assert result["tsb"] == 15.0

    def test_ewma_weight_distribution(
        self, training_load_analyzer: TrainingLoadAnalyzer
    ) -> None:
        """测试 EWMA 权重分布"""
        tss_values = [100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0]

        atl = training_load_analyzer.calculate_atl(tss_values)
        ctl = training_load_analyzer.calculate_ctl(tss_values)

        assert abs(atl - 100.0) < 1.0
        assert abs(ctl - 100.0) < 1.0


class TestTrainingLoadAnalyzerVectorized:
    """向量化方法测试类"""

    def test_calculate_tss_batch_basic(
        self, training_load_analyzer: TrainingLoadAnalyzer
    ) -> None:
        """测试批量 TSS 计算 - 基本场景"""
        df = pl.DataFrame(
            {
                "session_total_distance": [5000.0, 10000.0, 15000.0],
                "session_total_timer_time": [1800.0, 3600.0, 5400.0],
                "session_avg_heart_rate": [150.0, 160.0, 170.0],
            }
        )

        tss_series = training_load_analyzer.calculate_tss_batch(df)

        assert tss_series.len() == 3
        assert all(tss > 0 for tss in tss_series)

    def test_calculate_tss_batch_with_missing_hr(
        self, training_load_analyzer: TrainingLoadAnalyzer
    ) -> None:
        """测试批量 TSS 计算 - 缺失心率"""
        df = pl.DataFrame(
            {
                "session_total_distance": [5000.0, 10000.0, 15000.0],
                "session_total_timer_time": [1800.0, 3600.0, 5400.0],
                "session_avg_heart_rate": [150.0, None, 170.0],
            }
        )

        tss_series = training_load_analyzer.calculate_tss_batch(df)

        assert tss_series.len() == 3
        assert tss_series[0] > 0
        assert tss_series[1] == 0.0
        assert tss_series[2] > 0

    def test_calculate_tss_batch_with_zero_duration(
        self, training_load_analyzer: TrainingLoadAnalyzer
    ) -> None:
        """测试批量 TSS 计算 - 零时长"""
        df = pl.DataFrame(
            {
                "session_total_distance": [5000.0, 0.0, 15000.0],
                "session_total_timer_time": [1800.0, 3600.0, 0.0],
                "session_avg_heart_rate": [150.0, 160.0, 170.0],
            }
        )

        tss_series = training_load_analyzer.calculate_tss_batch(df)

        assert tss_series.len() == 3
        assert tss_series[0] > 0
        assert tss_series[1] == 0.0
        assert tss_series[2] == 0.0

    def test_calculate_ewma_vectorized_empty(
        self, training_load_analyzer: TrainingLoadAnalyzer
    ) -> None:
        """测试向量化 EWMA - 空序列"""
        tss_series = pl.Series([], dtype=pl.Float64)

        result = training_load_analyzer.calculate_ewma_vectorized(
            tss_series, ATL_TIME_CONSTANT
        )

        assert result == 0.0

    def test_calculate_ewma_vectorized_single_value(
        self, training_load_analyzer: TrainingLoadAnalyzer
    ) -> None:
        """测试向量化 EWMA - 单个值"""
        tss_series = pl.Series([100.0])

        result = training_load_analyzer.calculate_ewma_vectorized(
            tss_series, ATL_TIME_CONSTANT
        )

        assert result == 100.0

    def test_calculate_ewma_vectorized_multiple_values(
        self, training_load_analyzer: TrainingLoadAnalyzer
    ) -> None:
        """测试向量化 EWMA - 多个值"""
        tss_series = pl.Series([100.0, 150.0, 200.0])

        result = training_load_analyzer.calculate_ewma_vectorized(
            tss_series, ATL_TIME_CONSTANT
        )

        assert result > 0
        assert isinstance(result, float)

    def test_calculate_ewma_vectorized_consistency(
        self, training_load_analyzer: TrainingLoadAnalyzer
    ) -> None:
        """测试向量化 EWMA 与标量版本一致性"""
        tss_values = [100.0, 120.0, 150.0, 130.0, 110.0, 140.0, 160.0]
        tss_series = pl.Series(tss_values)

        scalar_result = training_load_analyzer._calculate_ewma(
            tss_values, ATL_TIME_CONSTANT
        )
        vectorized_result = training_load_analyzer.calculate_ewma_vectorized(
            tss_series, ATL_TIME_CONSTANT
        )

        assert abs(scalar_result - vectorized_result) < 0.1

    def test_calculate_atl_ctl_vectorized(
        self, training_load_analyzer: TrainingLoadAnalyzer
    ) -> None:
        """测试向量化 ATL/CTL 计算"""
        tss_series = pl.Series([100.0, 120.0, 150.0, 130.0, 110.0, 140.0, 160.0])

        result = training_load_analyzer.calculate_atl_ctl_vectorized(tss_series)

        assert "atl" in result
        assert "ctl" in result
        assert result["atl"] > 0
        assert result["ctl"] > 0

    def test_calculate_atl_ctl_vectorized_empty(
        self, training_load_analyzer: TrainingLoadAnalyzer
    ) -> None:
        """测试向量化 ATL/CTL 计算 - 空序列"""
        tss_series = pl.Series([], dtype=pl.Float64)

        result = training_load_analyzer.calculate_atl_ctl_vectorized(tss_series)

        assert result["atl"] == 0.0
        assert result["ctl"] == 0.0

    def test_calculate_training_load_from_dataframe(
        self, training_load_analyzer: TrainingLoadAnalyzer
    ) -> None:
        """测试从 DataFrame 计算训练负荷"""
        df = pl.DataFrame(
            {
                "session_total_distance": [
                    5000.0,
                    10000.0,
                    15000.0,
                    8000.0,
                    12000.0,
                ],
                "session_total_timer_time": [
                    1800.0,
                    3600.0,
                    5400.0,
                    2700.0,
                    4200.0,
                ],
                "session_avg_heart_rate": [150.0, 160.0, 170.0, 155.0, 165.0],
            }
        )

        result = training_load_analyzer.calculate_training_load_from_dataframe(df)

        assert "atl" in result
        assert "ctl" in result
        assert "tsb" in result
        assert "fitness_status" in result
        assert "training_advice" in result
        assert "runs_count" in result
        assert result["runs_count"] == 5

    def test_calculate_training_load_from_dataframe_empty(
        self, training_load_analyzer: TrainingLoadAnalyzer
    ) -> None:
        """测试从 DataFrame 计算训练负荷 - 空数据"""
        df = pl.DataFrame(
            {
                "session_total_distance": [],
                "session_total_timer_time": [],
                "session_avg_heart_rate": [],
            }
        )

        result = training_load_analyzer.calculate_training_load_from_dataframe(df)

        assert result["atl"] == 0.0
        assert result["ctl"] == 0.0
        assert result["fitness_status"] == "数据不足"

    def test_calculate_training_load_from_dataframe_no_valid_tss(
        self, training_load_analyzer: TrainingLoadAnalyzer
    ) -> None:
        """测试从 DataFrame 计算训练负荷 - 无有效 TSS"""
        df = pl.DataFrame(
            {
                "session_total_distance": [5000.0, 10000.0],
                "session_total_timer_time": [1800.0, 3600.0],
                "session_avg_heart_rate": [None, None],
            }
        )

        result = training_load_analyzer.calculate_training_load_from_dataframe(df)

        assert result["atl"] == 0.0
        assert result["ctl"] == 0.0
        assert result["fitness_status"] == "数据不足"

    def test_performance_comparison(
        self, training_load_analyzer: TrainingLoadAnalyzer
    ) -> None:
        """测试向量化方法性能（简单对比）"""
        import time

        n_runs = 100
        tss_values = [100.0 + i * 5 for i in range(n_runs)]
        tss_series = pl.Series(tss_values)

        start_scalar = time.perf_counter()
        for _ in range(10):
            training_load_analyzer._calculate_ewma(tss_values, ATL_TIME_CONSTANT)
        scalar_time = time.perf_counter() - start_scalar

        start_vectorized = time.perf_counter()
        for _ in range(10):
            training_load_analyzer.calculate_ewma_vectorized(
                tss_series, ATL_TIME_CONSTANT
            )
        vectorized_time = time.perf_counter() - start_vectorized

        print(f"\n标量版本: {scalar_time:.4f}s")
        print(f"向量化版本: {vectorized_time:.4f}s")
        print(f"性能提升: {(scalar_time / vectorized_time - 1) * 100:.1f}%")

        assert vectorized_time <= scalar_time * 2


class TestTrainingLoadAnalyzerIncremental:
    """增量 EWMA 方法测试类"""

    def test_update_atl_incremental_first_value(
        self, training_load_analyzer: TrainingLoadAnalyzer
    ) -> None:
        """测试增量更新 ATL - 第一个值"""
        training_load_analyzer.reset_incremental_state()

        atl = training_load_analyzer.update_atl_incremental(100.0)

        assert atl == 100.0

    def test_update_atl_incremental_multiple_values(
        self, training_load_analyzer: TrainingLoadAnalyzer
    ) -> None:
        """测试增量更新 ATL - 多个值"""
        training_load_analyzer.reset_incremental_state()

        atl1 = training_load_analyzer.update_atl_incremental(100.0)
        atl2 = training_load_analyzer.update_atl_incremental(120.0)
        atl3 = training_load_analyzer.update_atl_incremental(150.0)

        assert atl1 == 100.0
        assert atl2 > 100.0
        assert atl3 > atl2

    def test_update_ctl_incremental_first_value(
        self, training_load_analyzer: TrainingLoadAnalyzer
    ) -> None:
        """测试增量更新 CTL - 第一个值"""
        training_load_analyzer.reset_incremental_state()

        ctl = training_load_analyzer.update_ctl_incremental(100.0)

        assert ctl == 100.0

    def test_update_ctl_incremental_multiple_values(
        self, training_load_analyzer: TrainingLoadAnalyzer
    ) -> None:
        """测试增量更新 CTL - 多个值"""
        training_load_analyzer.reset_incremental_state()

        ctl1 = training_load_analyzer.update_ctl_incremental(100.0)
        ctl2 = training_load_analyzer.update_ctl_incremental(120.0)
        ctl3 = training_load_analyzer.update_ctl_incremental(150.0)

        assert ctl1 == 100.0
        assert ctl2 > 100.0
        assert ctl3 > ctl2

    def test_update_atl_ctl_incremental(
        self, training_load_analyzer: TrainingLoadAnalyzer
    ) -> None:
        """测试增量更新 ATL 和 CTL"""
        training_load_analyzer.reset_incremental_state()

        result = training_load_analyzer.update_atl_ctl_incremental(100.0)

        assert "atl" in result
        assert "ctl" in result
        assert result["atl"] == 100.0
        assert result["ctl"] == 100.0

    def test_reset_incremental_state(
        self, training_load_analyzer: TrainingLoadAnalyzer
    ) -> None:
        """测试重置增量状态"""
        training_load_analyzer.update_atl_incremental(100.0)
        training_load_analyzer.update_ctl_incremental(100.0)

        training_load_analyzer.reset_incremental_state()

        state = training_load_analyzer.get_incremental_state()
        assert state["atl"] == 0.0
        assert state["ctl"] == 0.0
        assert state["atl_initialized"] is False
        assert state["ctl_initialized"] is False

    def test_initialize_incremental_state(
        self, training_load_analyzer: TrainingLoadAnalyzer
    ) -> None:
        """测试初始化增量状态"""
        training_load_analyzer.reset_incremental_state()

        training_load_analyzer.initialize_incremental_state(50.0, 60.0)

        state = training_load_analyzer.get_incremental_state()
        assert state["atl"] == 50.0
        assert state["ctl"] == 60.0
        assert state["atl_initialized"] is True
        assert state["ctl_initialized"] is True

    def test_get_incremental_state(
        self, training_load_analyzer: TrainingLoadAnalyzer
    ) -> None:
        """测试获取增量状态"""
        training_load_analyzer.reset_incremental_state()
        training_load_analyzer.update_atl_incremental(100.0)

        state = training_load_analyzer.get_incremental_state()

        assert "atl" in state
        assert "ctl" in state
        assert "atl_initialized" in state
        assert "ctl_initialized" in state
        assert state["atl_initialized"] is True

    def test_incremental_performance(
        self, training_load_analyzer: TrainingLoadAnalyzer
    ) -> None:
        """测试增量计算性能"""
        import time

        n_runs = 100
        tss_values = [100.0 + i * 5 for i in range(n_runs)]

        training_load_analyzer.reset_incremental_state()
        start_incremental = time.perf_counter()
        for tss in tss_values:
            training_load_analyzer.update_atl_incremental(tss)
            training_load_analyzer.update_ctl_incremental(tss)
        incremental_time = time.perf_counter() - start_incremental

        start_batch = time.perf_counter()
        for _ in range(10):
            training_load_analyzer.calculate_atl(tss_values)
            training_load_analyzer.calculate_ctl(tss_values)
        batch_time = time.perf_counter() - start_batch

        print(f"\n增量计算: {incremental_time:.4f}s")
        print(f"批量计算(10次): {batch_time:.4f}s")
        print(f"性能提升: {(batch_time / incremental_time - 1) * 100:.1f}%")

        assert incremental_time < batch_time
