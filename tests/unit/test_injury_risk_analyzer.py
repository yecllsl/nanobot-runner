# InjuryRiskAnalyzer 单元测试

from datetime import datetime

import pytest

from src.core.injury_risk_analyzer import InjuryRiskAnalyzer
from src.core.user_profile_manager import (
    FitnessLevel,
    InjuryRiskLevel,
    RunnerProfile,
    TrainingPattern,
)


@pytest.fixture
def injury_analyzer() -> InjuryRiskAnalyzer:
    """创建 InjuryRiskAnalyzer 实例"""
    return InjuryRiskAnalyzer()


@pytest.fixture
def sample_profile() -> RunnerProfile:
    """创建示例画像"""
    return RunnerProfile(
        user_id="test_user",
        profile_date=datetime.now(),
        total_activities=50,
        total_distance_km=500.0,
        total_duration_hours=50.0,
        avg_vdot=45.0,
        max_vdot=48.0,
        fitness_level=FitnessLevel.INTERMEDIATE,
        weekly_avg_distance_km=35.0,
        weekly_avg_duration_hours=4.0,
        training_pattern=TrainingPattern.LIGHT,
        avg_heart_rate=150,
        max_heart_rate=180,
        resting_heart_rate=60,
        injury_risk_level=InjuryRiskLevel.LOW,
        injury_risk_score=0.0,
        atl=50.0,
        ctl=60.0,
        tsb=10.0,
        consistency_score=80.0,
    )


class TestInjuryRiskAnalyzer:
    """InjuryRiskAnalyzer 测试类"""

    def test_calculate_injury_risk_low_risk(
        self, injury_analyzer: InjuryRiskAnalyzer, sample_profile: RunnerProfile
    ) -> None:
        """测试低风险评估"""
        result = injury_analyzer.calculate_injury_risk(
            sample_profile, age=30, resting_hr=60
        )

        assert result.risk_score < 30
        assert result.risk_level == InjuryRiskLevel.LOW
        assert isinstance(result.risk_factors, list)
        assert isinstance(result.recommendations, list)

    def test_calculate_injury_risk_high_atl_ctl_ratio(
        self, injury_analyzer: InjuryRiskAnalyzer, sample_profile: RunnerProfile
    ) -> None:
        """测试高 ATL/CTL 比率风险"""
        sample_profile.atl = 100.0
        sample_profile.ctl = 50.0

        result = injury_analyzer.calculate_injury_risk(
            sample_profile, age=30, resting_hr=60
        )

        assert result.risk_score >= 30
        assert any("训练负荷突增" in factor for factor in result.risk_factors)

    def test_calculate_injury_risk_low_consistency(
        self, injury_analyzer: InjuryRiskAnalyzer, sample_profile: RunnerProfile
    ) -> None:
        """测试低训练一致性风险"""
        sample_profile.consistency_score = 20.0

        result = injury_analyzer.calculate_injury_risk(
            sample_profile, age=30, resting_hr=60
        )

        assert result.risk_score >= 25
        assert any("不规律" in factor for factor in result.risk_factors)

    def test_calculate_injury_risk_high_fatigue(
        self, injury_analyzer: InjuryRiskAnalyzer, sample_profile: RunnerProfile
    ) -> None:
        """测试高疲劳累积风险"""
        sample_profile.tsb = -25.0

        result = injury_analyzer.calculate_injury_risk(
            sample_profile, age=30, resting_hr=60
        )

        assert result.risk_score >= 25
        assert any("疲劳累积严重" in factor for factor in result.risk_factors)

    def test_calculate_injury_risk_older_age(
        self, injury_analyzer: InjuryRiskAnalyzer, sample_profile: RunnerProfile
    ) -> None:
        """测试年龄因素风险"""
        result = injury_analyzer.calculate_injury_risk(
            sample_profile, age=55, resting_hr=60
        )

        assert any("年龄较大" in factor for factor in result.risk_factors)

    def test_calculate_injury_risk_high_intensity(
        self, injury_analyzer: InjuryRiskAnalyzer, sample_profile: RunnerProfile
    ) -> None:
        """测试高强度训练风险"""
        sample_profile.training_pattern = TrainingPattern.INTENSE

        result = injury_analyzer.calculate_injury_risk(
            sample_profile, age=30, resting_hr=60
        )

        assert any("训练强度过高" in factor for factor in result.risk_factors)

    def test_calculate_injury_risk_invalid_age(
        self, injury_analyzer: InjuryRiskAnalyzer, sample_profile: RunnerProfile
    ) -> None:
        """测试无效年龄"""
        with pytest.raises(ValueError, match="年龄必须在"):
            injury_analyzer.calculate_injury_risk(sample_profile, age=0, resting_hr=60)

    def test_calculate_injury_risk_invalid_resting_hr(
        self, injury_analyzer: InjuryRiskAnalyzer, sample_profile: RunnerProfile
    ) -> None:
        """测试无效静息心率"""
        with pytest.raises(ValueError, match="静息心率必须在"):
            injury_analyzer.calculate_injury_risk(sample_profile, age=30, resting_hr=0)

    def test_profile_updated_after_calculation(
        self, injury_analyzer: InjuryRiskAnalyzer, sample_profile: RunnerProfile
    ) -> None:
        """测试计算后画像更新"""
        sample_profile.atl = 100.0
        sample_profile.ctl = 50.0

        injury_analyzer.calculate_injury_risk(sample_profile, age=30, resting_hr=60)

        assert sample_profile.injury_risk_score > 0
        assert sample_profile.injury_risk_level in [
            InjuryRiskLevel.LOW,
            InjuryRiskLevel.MEDIUM,
            InjuryRiskLevel.HIGH,
        ]

    def test_get_risk_summary(
        self, injury_analyzer: InjuryRiskAnalyzer, sample_profile: RunnerProfile
    ) -> None:
        """测试获取风险摘要"""
        sample_profile.injury_risk_score = 35.0
        sample_profile.injury_risk_level = InjuryRiskLevel.MEDIUM

        summary = injury_analyzer.get_risk_summary(sample_profile)

        assert summary["risk_score"] == 35.0
        assert summary["risk_level"] == "中"
        assert summary["atl"] == sample_profile.atl
        assert summary["ctl"] == sample_profile.ctl
        assert summary["tsb"] == sample_profile.tsb

    def test_injury_risk_result_to_dict(
        self, injury_analyzer: InjuryRiskAnalyzer, sample_profile: RunnerProfile
    ) -> None:
        """测试结果转换为字典"""
        result = injury_analyzer.calculate_injury_risk(
            sample_profile, age=30, resting_hr=60
        )
        result_dict = result.to_dict()

        assert "risk_score" in result_dict
        assert "risk_level" in result_dict
        assert "risk_factors" in result_dict
        assert "recommendations" in result_dict

    def test_medium_risk_level(
        self, injury_analyzer: InjuryRiskAnalyzer, sample_profile: RunnerProfile
    ) -> None:
        """测试中等风险等级"""
        sample_profile.atl = 80.0
        sample_profile.ctl = 50.0
        sample_profile.consistency_score = 40.0
        sample_profile.tsb = -15.0

        result = injury_analyzer.calculate_injury_risk(
            sample_profile, age=30, resting_hr=60
        )

        assert 30 <= result.risk_score < 60
        assert result.risk_level == InjuryRiskLevel.MEDIUM

    def test_high_risk_level(
        self, injury_analyzer: InjuryRiskAnalyzer, sample_profile: RunnerProfile
    ) -> None:
        """测试高风险等级"""
        sample_profile.atl = 100.0
        sample_profile.ctl = 50.0
        sample_profile.consistency_score = 20.0
        sample_profile.tsb = -25.0
        sample_profile.training_pattern = TrainingPattern.INTENSE

        result = injury_analyzer.calculate_injury_risk(
            sample_profile, age=55, resting_hr=60
        )

        assert result.risk_score >= 60
        assert result.risk_level == InjuryRiskLevel.HIGH

    def test_low_atl_ctl_ratio(
        self, injury_analyzer: InjuryRiskAnalyzer, sample_profile: RunnerProfile
    ) -> None:
        """测试低 ATL/CTL 比率"""
        sample_profile.atl = 30.0
        sample_profile.ctl = 50.0

        result = injury_analyzer.calculate_injury_risk(
            sample_profile, age=30, resting_hr=60
        )

        assert any("训练量过低" in factor for factor in result.risk_factors)

    def test_no_recommendations_for_low_risk(
        self, injury_analyzer: InjuryRiskAnalyzer, sample_profile: RunnerProfile
    ) -> None:
        """测试低风险时添加默认建议"""
        sample_profile.atl = 50.0
        sample_profile.ctl = 60.0
        sample_profile.consistency_score = 90.0
        sample_profile.tsb = 10.0
        sample_profile.training_pattern = TrainingPattern.LIGHT

        result = injury_analyzer.calculate_injury_risk(
            sample_profile, age=25, resting_hr=60
        )

        assert result.risk_level == InjuryRiskLevel.LOW
        assert len(result.recommendations) > 0
