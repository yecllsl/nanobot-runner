# InjuryRiskAnalyzer单元测试
# 测试伤病风险分析器的核心功能

from datetime import datetime

import pytest

from src.core.calculators.injury_risk_analyzer import (
    InjuryRiskAnalyzer,
    InjuryRiskResult,
)
from src.core.models import InjuryRiskLevel, TrainingPattern
from src.core.user_profile_manager import RunnerProfile


class TestInjuryRiskResult:
    """InjuryRiskResult数据类测试"""

    def test_injury_risk_result_creation(self):
        """测试创建InjuryRiskResult"""
        result = InjuryRiskResult(
            risk_score=45.0,
            risk_level=InjuryRiskLevel.MEDIUM,
            risk_factors=["训练负荷较高"],
            recommendations=["降低训练强度"],
        )

        assert result.risk_score == 45.0
        assert result.risk_level == InjuryRiskLevel.MEDIUM
        assert len(result.risk_factors) == 1
        assert len(result.recommendations) == 1

    def test_injury_risk_result_to_dict(self):
        """测试转换为字典"""
        result = InjuryRiskResult(
            risk_score=45.0,
            risk_level=InjuryRiskLevel.MEDIUM,
            risk_factors=["训练负荷较高", "训练不规律"],
            recommendations=["降低训练强度", "制定固定训练计划"],
        )

        result_dict = result.to_dict()

        assert result_dict["risk_score"] == 45.0
        assert result_dict["risk_level"] == "medium"
        assert len(result_dict["risk_factors"]) == 2
        assert len(result_dict["recommendations"]) == 2


class TestCalculateInjuryRisk:
    """calculate_injury_risk方法测试"""

    @pytest.fixture
    def analyzer(self):
        """创建InjuryRiskAnalyzer实例"""
        return InjuryRiskAnalyzer()

    @pytest.fixture
    def normal_profile(self):
        """创建正常画像"""
        profile = RunnerProfile(
            user_id="test_user",
            profile_date=datetime(2024, 1, 1),
            atl=50.0,
            ctl=60.0,
            tsb=10.0,
            consistency_score=70.0,
            training_pattern=TrainingPattern.MODERATE,
        )
        return profile

    def test_calculate_injury_risk_normal(self, analyzer, normal_profile):
        """测试正常风险评估"""
        result = analyzer.calculate_injury_risk(normal_profile, age=30, resting_hr=60)

        assert isinstance(result, InjuryRiskResult)
        assert result.risk_score >= 0
        assert result.risk_level in [
            InjuryRiskLevel.LOW,
            InjuryRiskLevel.MEDIUM,
            InjuryRiskLevel.HIGH,
        ]
        assert isinstance(result.risk_factors, list)
        assert isinstance(result.recommendations, list)

    def test_calculate_injury_risk_invalid_age(self, analyzer, normal_profile):
        """测试无效年龄"""
        with pytest.raises(ValueError, match="年龄必须在"):
            analyzer.calculate_injury_risk(normal_profile, age=0)

    def test_calculate_injury_risk_invalid_age_high(self, analyzer, normal_profile):
        """测试无效年龄（过高）"""
        with pytest.raises(ValueError, match="年龄必须在"):
            analyzer.calculate_injury_risk(normal_profile, age=150)

    def test_calculate_injury_risk_invalid_resting_hr(self, analyzer, normal_profile):
        """测试无效静息心率"""
        with pytest.raises(ValueError, match="静息心率必须在"):
            analyzer.calculate_injury_risk(normal_profile, resting_hr=0)

    def test_calculate_injury_risk_updates_profile(self, analyzer, normal_profile):
        """测试风险评估更新画像"""
        result = analyzer.calculate_injury_risk(normal_profile, age=30, resting_hr=60)

        assert normal_profile.injury_risk_score == result.risk_score
        assert normal_profile.injury_risk_level == result.risk_level


class TestEvaluateTrainingLoad:
    """训练负荷评估测试"""

    @pytest.fixture
    def analyzer(self):
        """创建InjuryRiskAnalyzer实例"""
        return InjuryRiskAnalyzer()

    @pytest.fixture
    def profile_template(self):
        """创建画像模板"""

        def _create_profile(atl: float, ctl: float):
            profile = RunnerProfile(
                user_id="test_user",
                profile_date=datetime(2024, 1, 1),
                atl=atl,
                ctl=ctl,
                tsb=0.0,
                consistency_score=70.0,
                training_pattern=TrainingPattern.MODERATE,
            )
            return profile

        return _create_profile

    def test_high_training_load_spike(self, analyzer, profile_template):
        """测试训练负荷突增（ATL/CTL > 1.5）"""
        profile = profile_template(atl=91.0, ctl=60.0)
        result = analyzer.calculate_injury_risk(profile, age=30, resting_hr=60)

        assert result.risk_score >= 30
        assert any("训练负荷突增" in factor for factor in result.risk_factors)
        assert any("降低训练强度" in rec for rec in result.recommendations)

    def test_moderate_training_load(self, analyzer, profile_template):
        """测试训练负荷较高（ATL/CTL > 1.2）"""
        profile = profile_template(atl=75.0, ctl=60.0)
        result = analyzer.calculate_injury_risk(profile, age=30, resting_hr=60)

        assert result.risk_score >= 15
        assert any("训练负荷较高" in factor for factor in result.risk_factors)

    def test_low_training_load(self, analyzer, profile_template):
        """测试训练负荷过低（ATL/CTL < 0.8）"""
        profile = profile_template(atl=45.0, ctl=60.0)
        result = analyzer.calculate_injury_risk(profile, age=30, resting_hr=60)

        assert result.risk_score >= 10
        assert any("训练量过低" in factor for factor in result.risk_factors)

    def test_normal_training_load(self, analyzer, profile_template):
        """测试正常训练负荷"""
        profile = profile_template(atl=60.0, ctl=60.0)
        result = analyzer.calculate_injury_risk(profile, age=30, resting_hr=60)

        assert "训练负荷" not in str(result.risk_factors)


class TestEvaluateConsistency:
    """训练一致性评估测试"""

    @pytest.fixture
    def analyzer(self):
        """创建InjuryRiskAnalyzer实例"""
        return InjuryRiskAnalyzer()

    @pytest.fixture
    def profile_template(self):
        """创建画像模板"""

        def _create_profile(consistency_score: float):
            profile = RunnerProfile(
                user_id="test_user",
                profile_date=datetime(2024, 1, 1),
                atl=50.0,
                ctl=60.0,
                tsb=10.0,
                consistency_score=consistency_score,
                training_pattern=TrainingPattern.MODERATE,
            )
            return profile

        return _create_profile

    def test_very_low_consistency(self, analyzer, profile_template):
        """测试训练非常不规律（< 30）"""
        profile = profile_template(consistency_score=20.0)
        result = analyzer.calculate_injury_risk(profile, age=30, resting_hr=60)

        assert result.risk_score >= 25
        assert any("训练非常不规律" in factor for factor in result.risk_factors)
        assert any("规律的训练习惯" in rec for rec in result.recommendations)

    def test_low_consistency(self, analyzer, profile_template):
        """测试训练不够规律（< 60）"""
        profile = profile_template(consistency_score=40.0)
        result = analyzer.calculate_injury_risk(profile, age=30, resting_hr=60)

        assert result.risk_score >= 12
        assert any("训练不够规律" in factor for factor in result.risk_factors)

    def test_good_consistency(self, analyzer, profile_template):
        """测试训练规律"""
        profile = profile_template(consistency_score=80.0)
        result = analyzer.calculate_injury_risk(profile, age=30, resting_hr=60)

        assert "训练" not in str(result.risk_factors) or all(
            "不规律" not in factor for factor in result.risk_factors
        )


class TestEvaluateRecovery:
    """恢复情况评估测试"""

    @pytest.fixture
    def analyzer(self):
        """创建InjuryRiskAnalyzer实例"""
        return InjuryRiskAnalyzer()

    @pytest.fixture
    def profile_template(self):
        """创建画像模板"""

        def _create_profile(tsb: float):
            profile = RunnerProfile(
                user_id="test_user",
                profile_date=datetime(2024, 1, 1),
                atl=50.0,
                ctl=60.0,
                tsb=tsb,
                consistency_score=70.0,
                training_pattern=TrainingPattern.MODERATE,
            )
            return profile

        return _create_profile

    def test_severe_fatigue(self, analyzer, profile_template):
        """测试疲劳累积严重（TSB < -20）"""
        profile = profile_template(tsb=-25.0)
        result = analyzer.calculate_injury_risk(profile, age=30, resting_hr=60)

        assert result.risk_score >= 25
        assert any("疲劳累积严重" in factor for factor in result.risk_factors)
        assert any("立即安排休息" in rec for rec in result.recommendations)

    def test_moderate_fatigue(self, analyzer, profile_template):
        """测试有一定疲劳累积（TSB < -10）"""
        profile = profile_template(tsb=-15.0)
        result = analyzer.calculate_injury_risk(profile, age=30, resting_hr=60)

        assert result.risk_score >= 12
        assert any("有一定疲劳累积" in factor for factor in result.risk_factors)

    def test_good_recovery(self, analyzer, profile_template):
        """测试恢复良好"""
        profile = profile_template(tsb=10.0)
        result = analyzer.calculate_injury_risk(profile, age=30, resting_hr=60)

        assert "疲劳" not in str(result.risk_factors)


class TestEvaluateAge:
    """年龄因素评估测试"""

    @pytest.fixture
    def analyzer(self):
        """创建InjuryRiskAnalyzer实例"""
        return InjuryRiskAnalyzer()

    @pytest.fixture
    def profile(self):
        """创建画像"""
        profile = RunnerProfile(
            user_id="test_user",
            profile_date=datetime(2024, 1, 1),
            atl=50.0,
            ctl=60.0,
            tsb=10.0,
            consistency_score=70.0,
            training_pattern=TrainingPattern.MODERATE,
        )
        return profile

    def test_older_runner(self, analyzer, profile):
        """测试年龄较大（> 50）"""
        result = analyzer.calculate_injury_risk(profile, age=55, resting_hr=60)

        assert result.risk_score >= 10
        assert any("年龄较大" in factor for factor in result.risk_factors)
        assert any("热身和拉伸" in rec for rec in result.recommendations)

    def test_middle_aged_runner(self, analyzer, profile):
        """测试中年跑者（> 40）"""
        result = analyzer.calculate_injury_risk(profile, age=45, resting_hr=60)

        assert result.risk_score >= 5
        assert any("中年跑者" in factor for factor in result.risk_factors)

    def test_young_runner(self, analyzer, profile):
        """测试年轻跑者"""
        result = analyzer.calculate_injury_risk(profile, age=25, resting_hr=60)

        assert "年龄" not in str(result.risk_factors)


class TestEvaluateIntensity:
    """训练强度评估测试"""

    @pytest.fixture
    def analyzer(self):
        """创建InjuryRiskAnalyzer实例"""
        return InjuryRiskAnalyzer()

    @pytest.fixture
    def profile_template(self):
        """创建画像模板"""

        def _create_profile(training_pattern: TrainingPattern):
            profile = RunnerProfile(
                user_id="test_user",
                profile_date=datetime(2024, 1, 1),
                atl=50.0,
                ctl=60.0,
                tsb=10.0,
                consistency_score=70.0,
                training_pattern=training_pattern,
            )
            return profile

        return _create_profile

    def test_intense_training(self, analyzer, profile_template):
        """测试高强度训练"""
        profile = profile_template(TrainingPattern.INTENSE)
        result = analyzer.calculate_injury_risk(profile, age=30, resting_hr=60)

        assert result.risk_score >= 10
        assert any("训练强度过高" in factor for factor in result.risk_factors)

    def test_extreme_training(self, analyzer, profile_template):
        """测试极限训练"""
        profile = profile_template(TrainingPattern.EXTREME)
        result = analyzer.calculate_injury_risk(profile, age=30, resting_hr=60)

        assert result.risk_score >= 10
        assert any("训练强度过高" in factor for factor in result.risk_factors)

    def test_moderate_training(self, analyzer, profile_template):
        """测试适度训练"""
        profile = profile_template(TrainingPattern.MODERATE)
        result = analyzer.calculate_injury_risk(profile, age=30, resting_hr=60)

        assert "训练强度过高" not in str(result.risk_factors)


class TestDetermineRiskLevel:
    """风险等级判断测试"""

    @pytest.fixture
    def analyzer(self):
        """创建InjuryRiskAnalyzer实例"""
        return InjuryRiskAnalyzer()

    @pytest.fixture
    def profile_template(self):
        """创建画像模板"""

        def _create_profile(
            atl: float = 50.0,
            ctl: float = 60.0,
            tsb: float = 10.0,
            consistency_score: float = 70.0,
            training_pattern: TrainingPattern = TrainingPattern.MODERATE,
        ):
            profile = RunnerProfile(
                user_id="test_user",
                profile_date=datetime(2024, 1, 1),
                atl=atl,
                ctl=ctl,
                tsb=tsb,
                consistency_score=consistency_score,
                training_pattern=training_pattern,
            )
            return profile

        return _create_profile

    def test_low_risk(self, analyzer, profile_template):
        """测试低风险（< 30）"""
        profile = profile_template()
        result = analyzer.calculate_injury_risk(profile, age=25, resting_hr=60)

        assert result.risk_level == InjuryRiskLevel.LOW
        assert result.risk_score < 30

    def test_medium_risk(self, analyzer, profile_template):
        """测试中等风险（30-60）"""
        profile = profile_template(
            atl=90.0, ctl=60.0, consistency_score=40.0, tsb=-15.0
        )
        result = analyzer.calculate_injury_risk(profile, age=30, resting_hr=60)

        assert result.risk_level == InjuryRiskLevel.MEDIUM
        assert 30 <= result.risk_score < 60

    def test_high_risk(self, analyzer, profile_template):
        """测试高风险（>= 60）"""
        profile = profile_template(
            atl=100.0,
            ctl=60.0,
            consistency_score=20.0,
            tsb=-25.0,
            training_pattern=TrainingPattern.EXTREME,
        )
        result = analyzer.calculate_injury_risk(profile, age=55, resting_hr=60)

        assert result.risk_level == InjuryRiskLevel.HIGH
        assert result.risk_score >= 60


class TestGetRiskSummary:
    """get_risk_summary方法测试"""

    @pytest.fixture
    def analyzer(self):
        """创建InjuryRiskAnalyzer实例"""
        return InjuryRiskAnalyzer()

    def test_get_risk_summary(self, analyzer):
        """测试获取风险摘要"""
        profile = RunnerProfile(
            user_id="test_user",
            profile_date=datetime(2024, 1, 1),
            atl=50.0,
            ctl=60.0,
            tsb=10.0,
            consistency_score=70.0,
            injury_risk_score=25.0,
            injury_risk_level=InjuryRiskLevel.LOW,
        )

        summary = analyzer.get_risk_summary(profile)

        assert summary["risk_score"] == 25.0
        assert summary["risk_level"] == "low"
        assert summary["atl"] == 50.0
        assert summary["ctl"] == 60.0
        assert summary["tsb"] == 10.0
        assert summary["consistency_score"] == 70.0


class TestIntegration:
    """集成测试"""

    @pytest.fixture
    def analyzer(self):
        """创建InjuryRiskAnalyzer实例"""
        return InjuryRiskAnalyzer()

    def test_comprehensive_risk_assessment(self, analyzer):
        """测试综合风险评估"""
        profile = RunnerProfile(
            user_id="test_user",
            profile_date=datetime(2024, 1, 1),
            atl=90.0,
            ctl=60.0,
            tsb=-25.0,
            consistency_score=25.0,
            training_pattern=TrainingPattern.EXTREME,
        )

        result = analyzer.calculate_injury_risk(profile, age=55, resting_hr=60)

        assert result.risk_level == InjuryRiskLevel.HIGH
        assert result.risk_score >= 60
        assert len(result.risk_factors) >= 4
        assert len(result.recommendations) >= 4

        assert profile.injury_risk_score == result.risk_score
        assert profile.injury_risk_level == result.risk_level

    def test_healthy_runner_assessment(self, analyzer):
        """测试健康跑者评估"""
        profile = RunnerProfile(
            user_id="test_user",
            profile_date=datetime(2024, 1, 1),
            atl=55.0,
            ctl=60.0,
            tsb=5.0,
            consistency_score=80.0,
            training_pattern=TrainingPattern.MODERATE,
        )

        result = analyzer.calculate_injury_risk(profile, age=25, resting_hr=60)

        assert result.risk_level == InjuryRiskLevel.LOW
        assert result.risk_score < 30
        assert len(result.risk_factors) == 0
        assert len(result.recommendations) >= 1
