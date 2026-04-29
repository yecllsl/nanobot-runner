# AnomalyDataFilter 单元测试

from datetime import datetime

import polars as pl
import pytest

from src.core.report.anomaly_filter import (
    ANOMALY_FILTER_RULES,
    AnomalyDataFilter,
    AnomalyFilterRule,
)


@pytest.fixture
def anomaly_filter() -> AnomalyDataFilter:
    """创建 AnomalyDataFilter 实例"""
    return AnomalyDataFilter()


@pytest.fixture
def sample_data() -> pl.DataFrame:
    """创建示例数据"""
    return pl.DataFrame(
        {
            "timestamp": [datetime(2026, 1, i, 8, 0, 0) for i in range(1, 11)],
            "avg_heart_rate": [150, 160, 20, 170, 250, 140, 155, 165, 175, 145],
            "max_heart_rate": [180, 190, 40, 200, 260, 170, 185, 195, 205, 175],
            "total_distance": [
                5000,
                6000,
                50,
                7000,
                150000,
                4000,
                5500,
                6500,
                7500,
                4500,
            ],
            "total_timer_time": [
                1800,
                2100,
                30,
                2400,
                30000,
                1500,
                1950,
                2250,
                2550,
                1650,
            ],
        }
    )


class TestAnomalyDataFilter:
    """AnomalyDataFilter 测试类"""

    def test_filter_anomaly_data_default_rules(
        self, anomaly_filter: AnomalyDataFilter, sample_data: pl.DataFrame
    ) -> None:
        """测试使用默认规则过滤异常数据"""
        lf = sample_data.lazy()

        result = anomaly_filter.filter_anomaly_data(lf)
        result_df = result.collect()

        assert result_df.height < sample_data.height

    def test_filter_anomaly_data_strict_mode(
        self, anomaly_filter: AnomalyDataFilter, sample_data: pl.DataFrame
    ) -> None:
        """测试严格模式过滤"""
        lf = sample_data.lazy()

        result_normal = anomaly_filter.filter_anomaly_data(lf, strict_mode=False)
        result_strict = anomaly_filter.filter_anomaly_data(lf, strict_mode=True)

        assert result_strict.collect().height <= result_normal.collect().height

    def test_filter_anomaly_data_custom_rules(self, sample_data: pl.DataFrame) -> None:
        """测试使用自定义规则过滤"""
        custom_rules = [
            AnomalyFilterRule(
                field_name="avg_heart_rate",
                condition=">",
                threshold=200,
                action="filter",
                description="心率过高",
            )
        ]
        custom_filter = AnomalyDataFilter(rules=custom_rules)
        lf = sample_data.lazy()

        result = custom_filter.filter_anomaly_data(lf, strict_mode=True)
        result_df = result.collect()

        assert all(result_df["avg_heart_rate"] <= 200)

    def test_filter_anomaly_data_empty_input(
        self, anomaly_filter: AnomalyDataFilter
    ) -> None:
        """测试空数据输入"""
        lf = pl.DataFrame().lazy()

        with pytest.raises(ValueError, match="输入数据为空"):
            anomaly_filter.filter_anomaly_data(lf)

    def test_get_filter_summary(
        self, anomaly_filter: AnomalyDataFilter, sample_data: pl.DataFrame
    ) -> None:
        """测试获取过滤摘要"""
        lf = sample_data.lazy()

        summary = anomaly_filter.get_filter_summary(lf)

        assert "original_count" in summary
        assert "filtered_count" in summary
        assert "removed_count" in summary
        assert "removal_rate" in summary
        assert summary["original_count"] == sample_data.height

    def test_get_filter_summary_empty(self, anomaly_filter: AnomalyDataFilter) -> None:
        """测试空数据的过滤摘要"""
        lf = pl.DataFrame().lazy()

        summary = anomaly_filter.get_filter_summary(lf)

        assert summary["original_count"] == 0
        assert summary["filtered_count"] == 0

    def test_add_custom_rule(self, anomaly_filter: AnomalyDataFilter) -> None:
        """测试添加自定义规则"""
        initial_count = len(anomaly_filter.rules)

        new_rule = AnomalyFilterRule(
            field_name="custom_field",
            condition=">",
            threshold=100,
            action="filter",
            description="自定义规则",
        )
        anomaly_filter.add_custom_rule(new_rule)

        assert len(anomaly_filter.rules) == initial_count + 1

    def test_remove_rule(self, anomaly_filter: AnomalyDataFilter) -> None:
        """测试移除规则"""
        initial_count = len(anomaly_filter.rules)

        result = anomaly_filter.remove_rule("avg_heart_rate", "<", 30)

        assert result is True
        assert len(anomaly_filter.rules) == initial_count - 1

    def test_remove_rule_not_found(self, anomaly_filter: AnomalyDataFilter) -> None:
        """测试移除不存在的规则"""
        result = anomaly_filter.remove_rule("nonexistent", ">", 999)

        assert result is False

    def test_filter_with_missing_column(
        self, anomaly_filter: AnomalyDataFilter
    ) -> None:
        """测试过滤不存在的列"""
        df = pl.DataFrame(
            {
                "timestamp": [datetime(2026, 1, 1, 8, 0, 0)],
                "avg_heart_rate": [150],
            }
        )
        lf = df.lazy()

        result = anomaly_filter.filter_anomaly_data(lf)
        result_df = result.collect()

        assert result_df.height == 1

    def test_default_rules_exist(self) -> None:
        """测试默认规则存在"""
        assert len(ANOMALY_FILTER_RULES) > 0

        field_names = [rule.field_name for rule in ANOMALY_FILTER_RULES]
        assert "avg_heart_rate" in field_names
        assert "max_heart_rate" in field_names
        assert "total_distance" in field_names
        assert "total_timer_time" in field_names

    def test_filter_preserves_valid_data(
        self, anomaly_filter: AnomalyDataFilter
    ) -> None:
        """测试保留有效数据"""
        df = pl.DataFrame(
            {
                "timestamp": [datetime(2026, 1, i, 8, 0, 0) for i in range(1, 6)],
                "avg_heart_rate": [140, 150, 160, 145, 155],
                "max_heart_rate": [170, 180, 190, 175, 185],
                "total_distance": [5000, 6000, 7000, 5500, 6500],
                "total_timer_time": [1800, 2100, 2400, 1950, 2250],
            }
        )
        lf = df.lazy()

        result = anomaly_filter.filter_anomaly_data(lf)
        result_df = result.collect()

        assert result_df.height == df.height

    def test_filter_removes_all_invalid_data(
        self, anomaly_filter: AnomalyDataFilter
    ) -> None:
        """测试移除所有无效数据"""
        df = pl.DataFrame(
            {
                "timestamp": [datetime(2026, 1, i, 8, 0, 0) for i in range(1, 4)],
                "avg_heart_rate": [20, 250, 300],
                "max_heart_rate": [30, 280, 320],
                "total_distance": [50, 200000, 300000],
                "total_timer_time": [10, 40000, 50000],
            }
        )
        lf = df.lazy()

        result = anomaly_filter.filter_anomaly_data(lf)
        result_df = result.collect()

        assert result_df.height == 0
