"""
画像保鲜期与异常过滤单元测试

测试模块：src/core/profile.py
测试覆盖：
    - ProfileStaleStatus 枚举
    - AnomalyFilterRule 数据结构
    - ANOMALY_FILTER_RULES 常量
    - ProfileEngine.check_freshness() 方法
    - ProfileEngine.filter_anomaly_data() 方法
    - ProfileEngine._build_filter_condition() 方法
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock

import polars as pl
import pytest

from src.core.profile import (
    ANOMALY_FILTER_RULES,
    AnomalyFilterRule,
    ProfileEngine,
    ProfileStaleStatus,
    RunnerProfile,
)


class TestProfileStaleStatus:
    """测试 ProfileStaleStatus 枚举"""

    def test_enum_values(self):
        """测试枚举值"""
        assert ProfileStaleStatus.FRESH.value == "新鲜"
        assert ProfileStaleStatus.STALE.value == "过期"
        assert ProfileStaleStatus.MISSING.value == "缺失"

    def test_enum_names(self):
        """测试枚举名称"""
        assert ProfileStaleStatus.FRESH.name == "FRESH"
        assert ProfileStaleStatus.STALE.name == "STALE"
        assert ProfileStaleStatus.MISSING.name == "MISSING"


class TestAnomalyFilterRule:
    """测试 AnomalyFilterRule 数据结构"""

    def test_basic_rule(self):
        """测试基本规则创建"""
        rule = AnomalyFilterRule(
            field_name="avg_heart_rate",
            condition=">",
            threshold=220,
            action="filter",
        )
        assert rule.field_name == "avg_heart_rate"
        assert rule.condition == ">"
        assert rule.threshold == 220
        assert rule.action == "filter"
        assert rule.clip_value is None

    def test_rule_with_clip(self):
        """测试带截断值的规则"""
        rule = AnomalyFilterRule(
            field_name="pace_min_per_km",
            condition=">",
            threshold=20,
            action="clip",
            clip_value=20.0,
        )
        assert rule.action == "clip"
        assert rule.clip_value == 20.0

    def test_rule_with_description(self):
        """测试带描述信息的规则"""
        rule = AnomalyFilterRule(
            field_name="total_distance",
            condition="<",
            threshold=100,
            action="filter",
            description="过滤距离过短的数据",
        )
        assert rule.description == "过滤距离过短的数据"

    def test_rule_default_values(self):
        """测试默认值"""
        rule = AnomalyFilterRule(
            field_name="vdot",
            condition="<",
            threshold=20,
            action="filter",
        )
        assert rule.clip_value is None
        assert rule.description is None


class TestAnomalyFilterRulesConstant:
    """测试 ANOMALY_FILTER_RULES 常量"""

    def test_rules_not_empty(self):
        """测试规则列表不为空"""
        assert len(ANOMALY_FILTER_RULES) > 0

    def test_rules_are_anomaly_filter_rule(self):
        """测试所有规则都是 AnomalyFilterRule 类型"""
        for rule in ANOMALY_FILTER_RULES:
            assert isinstance(rule, AnomalyFilterRule)

    def test_heart_rate_rules_exist(self):
        """测试心率规则存在"""
        hr_rules = [
            r
            for r in ANOMALY_FILTER_RULES
            if r.field_name in ["avg_heart_rate", "max_heart_rate"]
        ]
        assert len(hr_rules) >= 4  # 至少 4 条心率规则

    def test_distance_rules_exist(self):
        """测试距离规则存在"""
        distance_rules = [
            r for r in ANOMALY_FILTER_RULES if r.field_name == "total_distance"
        ]
        assert len(distance_rules) >= 2  # 至少 2 条距离规则

    def test_time_rules_exist(self):
        """测试时长规则存在"""
        time_rules = [
            r for r in ANOMALY_FILTER_RULES if r.field_name == "total_timer_time"
        ]
        assert len(time_rules) >= 2  # 至少 2 条时长规则


class TestProfileEngineCheckFreshness:
    """测试 ProfileEngine.check_freshness() 方法"""

    @pytest.fixture
    def mock_storage(self):
        """模拟存储管理器"""
        storage = MagicMock()
        return storage

    @pytest.fixture
    def profile_engine(self, mock_storage):
        """创建 ProfileEngine 实例"""
        return ProfileEngine(mock_storage)

    def test_fresh_profile(self, profile_engine, mock_storage):
        """测试新鲜的画像（7 天内）"""
        # 创建 3 天前的画像
        fresh_profile = RunnerProfile(
            user_id="test_user",
            profile_date=datetime.now() - timedelta(days=3),
        )
        mock_storage.load_profile_json.return_value = fresh_profile

        result = profile_engine.check_freshness()

        assert result == ProfileStaleStatus.FRESH
        mock_storage.load_profile_json.assert_called_once()

    def test_stale_profile(self, profile_engine, mock_storage):
        """测试过期的画像（超过 7 天）"""
        # 创建 10 天前的画像
        stale_profile = RunnerProfile(
            user_id="test_user",
            profile_date=datetime.now() - timedelta(days=10),
        )
        mock_storage.load_profile_json.return_value = stale_profile

        result = profile_engine.check_freshness()

        assert result == ProfileStaleStatus.STALE

    def test_missing_profile(self, profile_engine, mock_storage):
        """测试缺失的画像"""
        mock_storage.load_profile_json.return_value = None

        result = profile_engine.check_freshness()

        assert result == ProfileStaleStatus.MISSING

    def test_fresh_profile_with_custom_days(self, profile_engine, mock_storage):
        """测试自定义保鲜期"""
        # 创建 5 天前的画像
        profile = RunnerProfile(
            user_id="test_user",
            profile_date=datetime.now() - timedelta(days=5),
        )
        mock_storage.load_profile_json.return_value = profile

        # 使用 3 天保鲜期，应该过期
        result = profile_engine.check_freshness(freshness_days=3)
        assert result == ProfileStaleStatus.STALE

        # 使用 7 天保鲜期，应该新鲜
        result = profile_engine.check_freshness(freshness_days=7)
        assert result == ProfileStaleStatus.FRESH

    def test_provided_profile_not_loaded(self, profile_engine, mock_storage):
        """测试提供 profile 对象时不加载"""
        profile = RunnerProfile(
            user_id="test_user",
            profile_date=datetime.now() - timedelta(days=2),
        )

        result = profile_engine.check_freshness(profile=profile)

        assert result == ProfileStaleStatus.FRESH
        mock_storage.load_profile_json.assert_not_called()

    def test_boundary_case_exactly_7_days(self, profile_engine, mock_storage):
        """测试边界情况：正好 7 天"""
        profile = RunnerProfile(
            user_id="test_user",
            profile_date=datetime.now() - timedelta(days=7),
        )
        mock_storage.load_profile_json.return_value = profile

        result = profile_engine.check_freshness(freshness_days=7)

        # 7 天应该算新鲜
        assert result == ProfileStaleStatus.FRESH

    def test_exception_handling(self, profile_engine, mock_storage):
        """测试异常处理"""
        mock_storage.load_profile_json.side_effect = Exception("加载失败")

        with pytest.raises(RuntimeError, match="检查画像保鲜期失败"):
            profile_engine.check_freshness()


class TestProfileEngineFilterAnomalyData:
    """测试 ProfileEngine.filter_anomaly_data() 方法"""

    @pytest.fixture
    def mock_storage(self):
        """模拟存储管理器"""
        storage = MagicMock()
        return storage

    @pytest.fixture
    def profile_engine(self, mock_storage):
        """创建 ProfileEngine 实例"""
        return ProfileEngine(mock_storage)

    @pytest.fixture
    def sample_activity_data(self):
        """样本活动数据"""
        return pl.DataFrame(
            {
                "activity_id": [1, 2, 3, 4, 5],
                "avg_heart_rate": [150, 25, 180, 230, 160],  # 25 和 230 是异常
                "max_heart_rate": [170, 40, 190, 240, 180],  # 40 是异常
                "total_distance": [5000, 50, 10000, 150000, 8000],  # 50 和 150000 是异常
                "total_timer_time": [1800, 30, 3600, 30000, 2400],  # 30 和 30000 是异常
            }
        ).lazy()

    def test_filter_heart_rate_anomaly(self, profile_engine, sample_activity_data):
        """测试心率异常过滤"""
        filtered = profile_engine.filter_anomaly_data(sample_activity_data)

        # 收集结果
        result_df = filtered.collect()

        # 应该过滤掉 avg_heart_rate < 30 或 > 220 的记录
        assert all(result_df["avg_heart_rate"] >= 30)
        assert all(result_df["avg_heart_rate"] <= 220)

    def test_filter_distance_anomaly(self, profile_engine, sample_activity_data):
        """测试距离异常过滤"""
        filtered = profile_engine.filter_anomaly_data(sample_activity_data)
        result_df = filtered.collect()

        # 应该过滤掉 total_distance < 100 或 > 100000 的记录
        assert all(result_df["total_distance"] >= 100)
        assert all(result_df["total_distance"] <= 100000)

    def test_filter_time_anomaly(self, profile_engine, sample_activity_data):
        """测试时长异常过滤"""
        filtered = profile_engine.filter_anomaly_data(sample_activity_data)
        result_df = filtered.collect()

        # 应该过滤掉 total_timer_time < 60 或 > 28800 的记录
        assert all(result_df["total_timer_time"] >= 60)
        assert all(result_df["total_timer_time"] <= 28800)

    def test_strict_mode_filters_more(self, profile_engine, sample_activity_data):
        """测试严格模式过滤更多数据"""
        # 非严格模式
        filtered_normal = profile_engine.filter_anomaly_data(
            sample_activity_data, strict_mode=False
        )
        # 严格模式
        filtered_strict = profile_engine.filter_anomaly_data(
            sample_activity_data, strict_mode=True
        )

        normal_count = filtered_normal.collect().height
        strict_count = filtered_strict.collect().height

        # 严格模式应该过滤掉更多或相等数量的数据
        assert strict_count <= normal_count

    def test_custom_rules(self, profile_engine, sample_activity_data):
        """测试自定义规则"""
        custom_rules = [
            AnomalyFilterRule(
                field_name="avg_heart_rate",
                condition=">",
                threshold=200,
                action="filter",
            )
        ]

        # 使用严格模式，确保自定义规则生效
        filtered = profile_engine.filter_anomaly_data(
            sample_activity_data, rules=custom_rules, strict_mode=True
        )
        result_df = filtered.collect()

        # 只应用自定义规则，应该过滤掉 avg_heart_rate > 200 的记录
        assert all(result_df["avg_heart_rate"] <= 200)

    def test_empty_dataframe(self, profile_engine):
        """测试空 DataFrame"""
        empty_data = pl.DataFrame(
            {
                "activity_id": pl.Series([], dtype=pl.Int64),
                "avg_heart_rate": pl.Series([], dtype=pl.Float64),
            }
        ).lazy()

        filtered = profile_engine.filter_anomaly_data(empty_data)
        result_df = filtered.collect()

        assert result_df.height == 0

    def test_missing_field_skipped(self, profile_engine, sample_activity_data):
        """测试缺失字段被跳过"""
        custom_rules = [
            AnomalyFilterRule(
                field_name="non_existent_field",
                condition=">",
                threshold=100,
                action="filter",
            )
        ]

        # 不应该抛出异常
        filtered = profile_engine.filter_anomaly_data(
            sample_activity_data, rules=custom_rules
        )
        result_df = filtered.collect()

        # 数据应该保持不变（除了默认规则）
        assert result_df.height > 0

    def test_clip_action(self, profile_engine):
        """测试截断动作"""
        data = pl.DataFrame(
            {
                "activity_id": [1, 2, 3],
                "pace_min_per_km": [5.0, 25.0, 8.0],  # 25.0 应该被截断到 20.0
            }
        ).lazy()

        custom_rules = [
            AnomalyFilterRule(
                field_name="pace_min_per_km",
                condition=">",
                threshold=20,
                action="clip",
                clip_value=20.0,
            )
        ]

        filtered = profile_engine.filter_anomaly_data(data, rules=custom_rules)
        result_df = filtered.collect()

        # 最大值应该是 20.0
        assert result_df["pace_min_per_km"].max() == 20.0

    def test_no_rules_returns_original_data(self, profile_engine, sample_activity_data):
        """测试无规则时返回原始数据"""
        filtered = profile_engine.filter_anomaly_data(sample_activity_data, rules=[])
        result_df = filtered.collect()
        original_df = sample_activity_data.collect()

        assert result_df.height == original_df.height

    def test_exception_on_empty_schema(self, profile_engine):
        """测试空 Schema 抛出异常"""
        # 创建没有列的 LazyFrame
        empty_schema_data = pl.DataFrame({}).lazy()

        # 异常会被包装成 RuntimeError
        with pytest.raises(RuntimeError, match="异常数据过滤失败"):
            profile_engine.filter_anomaly_data(empty_schema_data)

    def test_logging_on_filter(self, profile_engine, sample_activity_data, caplog):
        """测试过滤时记录日志"""
        import logging

        with caplog.at_level(logging.INFO):
            profile_engine.filter_anomaly_data(sample_activity_data)

        # 应该记录过滤信息
        assert "异常数据过滤完成" in caplog.text


class TestProfileEngineBuildFilterCondition:
    """测试 ProfileEngine._build_filter_condition() 方法"""

    @pytest.fixture
    def mock_storage(self):
        """模拟存储管理器"""
        storage = MagicMock()
        return storage

    @pytest.fixture
    def profile_engine(self, mock_storage):
        """创建 ProfileEngine 实例"""
        return ProfileEngine(mock_storage)

    def test_strict_mode_returns_condition(self, profile_engine):
        """测试严格模式返回条件"""
        rule = AnomalyFilterRule(
            field_name="avg_heart_rate",
            condition=">",
            threshold=150,
            action="filter",
        )

        condition = profile_engine._build_filter_condition(rule, strict_mode=True)

        assert condition is not None

    def test_non_strict_mode_severe_rule(self, profile_engine):
        """测试非严格模式下的严重规则"""
        rule = AnomalyFilterRule(
            field_name="avg_heart_rate",
            condition="<",
            threshold=30,
            action="filter",
        )

        condition = profile_engine._build_filter_condition(rule, strict_mode=False)

        # 严重规则应该返回条件
        assert condition is not None

    def test_non_strict_mode_non_severe_rule(self, profile_engine):
        """测试非严格模式下的非严重规则"""
        rule = AnomalyFilterRule(
            field_name="avg_heart_rate",
            condition="<",
            threshold=50,  # 非严重阈值
            action="filter",
        )

        condition = profile_engine._build_filter_condition(rule, strict_mode=False)

        # 非严重规则应该返回 None
        assert condition is None

    def test_unknown_field_in_non_strict_mode(self, profile_engine):
        """测试非严格模式下未知字段"""
        rule = AnomalyFilterRule(
            field_name="unknown_field",
            condition=">",
            threshold=100,
            action="filter",
        )

        condition = profile_engine._build_filter_condition(rule, strict_mode=False)

        # 未知字段应该返回条件（不在严重阈值列表中）
        assert condition is not None


class TestIntegration:
    """集成测试"""

    @pytest.fixture
    def mock_storage(self):
        """模拟存储管理器"""
        storage = MagicMock()
        return storage

    @pytest.fixture
    def profile_engine(self, mock_storage):
        """创建 ProfileEngine 实例"""
        return ProfileEngine(mock_storage)

    def test_freshness_and_filter_integration(self, profile_engine, mock_storage):
        """测试保鲜期检查和异常过滤集成"""
        # 创建新鲜画像
        fresh_profile = RunnerProfile(
            user_id="test_user",
            profile_date=datetime.now() - timedelta(days=2),
        )
        mock_storage.load_profile_json.return_value = fresh_profile

        # 检查保鲜期
        freshness = profile_engine.check_freshness()
        assert freshness == ProfileStaleStatus.FRESH

        # 创建带异常的数据
        data = pl.DataFrame(
            {
                "activity_id": [1, 2, 3],
                "avg_heart_rate": [150, 25, 180],  # 25 是异常
                "total_distance": [5000, 10000, 50],  # 50 是异常
            }
        ).lazy()

        # 过滤异常
        filtered = profile_engine.filter_anomaly_data(data)
        result_df = filtered.collect()

        # 验证结果
        assert result_df.height < 3  # 至少过滤掉一条
        assert all(result_df["avg_heart_rate"] >= 30)
        assert all(result_df["total_distance"] >= 100)

    def test_stale_profile_triggers_update_logic(self, profile_engine, mock_storage):
        """测试过期画像触发更新逻辑"""
        # 创建过期画像
        stale_profile = RunnerProfile(
            user_id="test_user",
            profile_date=datetime.now() - timedelta(days=10),
        )
        mock_storage.load_profile_json.return_value = stale_profile

        # 检查保鲜期
        freshness = profile_engine.check_freshness()
        assert freshness == ProfileStaleStatus.STALE

        # 实际应用中应该在这里触发画像更新逻辑
        # 本测试仅验证状态判断正确
