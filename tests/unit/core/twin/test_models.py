from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from src.core.twin.models import (
    BodySignalDimension,
    DataQuality,
    FitnessDimension,
    HypotheticalPlan,
    IntensityDistribution,
    LoadDimension,
    PlanComparison,
    PlanComparisonMetrics,
    RiskDimension,
    RunnerStateVector,
    SimulationResult,
    SimulationWeekSnapshot,
    StateVectorCache,
    TrainingPatternDimension,
    TwinEngineError,
    WeeklyPlanSpec,
)


class TestDataQuality:
    def test_enum_values(self) -> None:
        assert DataQuality.SUFFICIENT.value == "sufficient"
        assert DataQuality.INSUFFICIENT.value == "insufficient"
        assert DataQuality.EMPTY.value == "empty"

    def test_all_members(self) -> None:
        members = list(DataQuality)
        assert len(members) == 3


class TestFitnessDimension:
    def test_creation(self) -> None:
        dim = FitnessDimension(vdot=45.0, vdot_trend=0.02, vo2max_estimate=52.0)
        assert dim.vdot == 45.0
        assert dim.vdot_trend == 0.02
        assert dim.vo2max_estimate == 52.0

    def test_none_optional(self) -> None:
        dim = FitnessDimension(vdot=45.0, vdot_trend=0.02)
        assert dim.vo2max_estimate is None

    def test_frozen(self) -> None:
        dim = FitnessDimension(vdot=45.0, vdot_trend=0.02)
        with pytest.raises(AttributeError):
            dim.vdot = 50.0  # type: ignore[misc]

    def test_to_dict(self) -> None:
        dim = FitnessDimension(vdot=45.0, vdot_trend=0.02, vo2max_estimate=52.0)
        d = dim.to_dict()
        assert d["vdot"] == 45.0
        assert d["vdot_trend"] == 0.02
        assert d["vo2max_estimate"] == 52.0


class TestLoadDimension:
    def test_creation(self) -> None:
        dim = LoadDimension(ctl=65.0, atl=50.0, tsb=15.0, acwr=0.77)
        assert dim.ctl == 65.0
        assert dim.atl == 50.0
        assert dim.tsb == 15.0
        assert dim.acwr == 0.77

    def test_to_dict(self) -> None:
        dim = LoadDimension(ctl=65.0, atl=50.0, tsb=15.0, acwr=0.77)
        d = dim.to_dict()
        assert d["ctl"] == 65.0
        assert d["atl"] == 50.0
        assert d["tsb"] == 15.0
        assert d["acwr"] == 0.77


class TestBodySignalDimension:
    def test_none_fields(self) -> None:
        dim = BodySignalDimension(fatigue_score=3.5, recovery_status="good")
        assert dim.resting_hr is None
        assert dim.hrv_rmssd is None

    def test_to_dict(self) -> None:
        dim = BodySignalDimension(
            fatigue_score=3.5,
            recovery_status="good",
            resting_hr=55.0,
            hrv_rmssd=45.0,
        )
        d = dim.to_dict()
        assert d["fatigue_score"] == 3.5
        assert d["recovery_status"] == "good"
        assert d["resting_hr"] == 55.0
        assert d["hrv_rmssd"] == 45.0


class TestRiskDimension:
    def test_creation(self) -> None:
        dim = RiskDimension(
            injury_risk_7d=5.0, injury_risk_28d=15.0, overtraining_risk="low"
        )
        assert dim.injury_risk_7d == 5.0
        assert dim.injury_risk_28d == 15.0
        assert dim.overtraining_risk == "low"

    def test_to_dict(self) -> None:
        dim = RiskDimension(
            injury_risk_7d=5.0, injury_risk_28d=15.0, overtraining_risk="low"
        )
        d = dim.to_dict()
        assert d["injury_risk_7d"] == 5.0
        assert d["injury_risk_28d"] == 15.0
        assert d["overtraining_risk"] == "low"


class TestIntensityDistribution:
    def test_creation(self) -> None:
        dist = IntensityDistribution(zone1_pct=80.0, zone2_pct=15.0, zone3_pct=5.0)
        assert dist.zone1_pct == 80.0
        assert dist.zone2_pct == 15.0
        assert dist.zone3_pct == 5.0

    def test_to_dict(self) -> None:
        dist = IntensityDistribution(zone1_pct=80.0, zone2_pct=15.0, zone3_pct=5.0)
        d = dist.to_dict()
        assert d["zone1_pct"] == 80.0
        assert d["zone2_pct"] == 15.0
        assert d["zone3_pct"] == 5.0


class TestTrainingPatternDimension:
    def test_with_intensity_distribution(self) -> None:
        intensity = IntensityDistribution(zone1_pct=80.0, zone2_pct=15.0, zone3_pct=5.0)
        dim = TrainingPatternDimension(
            weekly_volume_km=40.0,
            intensity_distribution=intensity,
            long_run_frequency=1,
        )
        assert dim.weekly_volume_km == 40.0
        assert dim.intensity_distribution.zone1_pct == 80.0
        assert dim.long_run_frequency == 1

    def test_to_dict(self) -> None:
        intensity = IntensityDistribution(zone1_pct=80.0, zone2_pct=15.0, zone3_pct=5.0)
        dim = TrainingPatternDimension(
            weekly_volume_km=40.0,
            intensity_distribution=intensity,
            long_run_frequency=1,
        )
        d = dim.to_dict()
        assert d["weekly_volume_km"] == 40.0
        assert d["intensity_distribution"]["zone1_pct"] == 80.0
        assert d["long_run_frequency"] == 1


class TestRunnerStateVector:
    def _make_state(self) -> RunnerStateVector:
        return RunnerStateVector(
            fitness=FitnessDimension(vdot=45.0, vdot_trend=0.02),
            load=LoadDimension(ctl=65.0, atl=50.0, tsb=15.0, acwr=0.77),
            body_signal=BodySignalDimension(fatigue_score=3.5, recovery_status="good"),
            risk=RiskDimension(
                injury_risk_7d=5.0, injury_risk_28d=15.0, overtraining_risk="low"
            ),
            training_pattern=TrainingPatternDimension(
                weekly_volume_km=40.0,
                intensity_distribution=IntensityDistribution(
                    zone1_pct=80.0, zone2_pct=15.0, zone3_pct=5.0
                ),
                long_run_frequency=1,
            ),
            snapshot_date="2026-05-12",
            data_quality=DataQuality.SUFFICIENT,
        )

    def test_creation(self) -> None:
        state = self._make_state()
        assert state.fitness.vdot == 45.0
        assert state.load.tsb == 15.0
        assert state.body_signal.fatigue_score == 3.5
        assert state.risk.injury_risk_7d == 5.0
        assert state.training_pattern.weekly_volume_km == 40.0

    def test_frozen(self) -> None:
        state = self._make_state()
        with pytest.raises(AttributeError):
            state.snapshot_date = "2026-06-01"  # type: ignore[misc]

    def test_to_dict_nested(self) -> None:
        state = self._make_state()
        d = state.to_dict()
        assert d["fitness"]["vdot"] == 45.0
        assert d["load"]["tsb"] == 15.0
        assert d["body_signal"]["fatigue_score"] == 3.5
        assert d["risk"]["injury_risk_7d"] == 5.0
        assert d["training_pattern"]["weekly_volume_km"] == 40.0
        assert d["snapshot_date"] == "2026-05-12"
        assert d["data_quality"] == "sufficient"


class TestWeeklyPlanSpec:
    def test_default_intensity_multiplier(self) -> None:
        spec = WeeklyPlanSpec(
            weekly_volume_km=40.0,
            easy_ratio=0.7,
            tempo_ratio=0.15,
            interval_ratio=0.15,
            long_run_km=20.0,
        )
        assert spec.intensity_multiplier == 1.0

    def test_to_dict(self) -> None:
        spec = WeeklyPlanSpec(
            weekly_volume_km=40.0,
            easy_ratio=0.7,
            tempo_ratio=0.15,
            interval_ratio=0.15,
            long_run_km=20.0,
            intensity_multiplier=1.1,
        )
        d = spec.to_dict()
        assert d["weekly_volume_km"] == 40.0
        assert d["intensity_multiplier"] == 1.1


class TestHypotheticalPlan:
    def test_source_plan_id(self) -> None:
        plan = HypotheticalPlan(
            name="全马破4计划",
            weeks=[
                WeeklyPlanSpec(
                    weekly_volume_km=40.0,
                    easy_ratio=0.7,
                    tempo_ratio=0.15,
                    interval_ratio=0.15,
                    long_run_km=20.0,
                )
            ],
            source="plan_id",
            plan_id="plan_001",
        )
        assert plan.source == "plan_id"
        assert plan.plan_id == "plan_001"

    def test_to_dict(self) -> None:
        plan = HypotheticalPlan(
            name="全马破4计划",
            weeks=[
                WeeklyPlanSpec(
                    weekly_volume_km=40.0,
                    easy_ratio=0.7,
                    tempo_ratio=0.15,
                    interval_ratio=0.15,
                    long_run_km=20.0,
                )
            ],
            source="plan_id",
            plan_id="plan_001",
        )
        d = plan.to_dict()
        assert d["name"] == "全马破4计划"
        assert d["source"] == "plan_id"
        assert d["plan_id"] == "plan_001"
        assert len(d["weeks"]) == 1

    def test_from_week_dicts(self) -> None:
        weeks = [
            {
                "weekly_volume_km": 40.0,
                "easy_ratio": 0.7,
                "tempo_ratio": 0.15,
                "interval_ratio": 0.15,
                "long_run_km": 20.0,
                "intensity_multiplier": 1.1,
            },
            {
                "weekly_volume_km": 50.0,
                "easy_ratio": 0.75,
                "tempo_ratio": 0.1,
                "interval_ratio": 0.15,
                "long_run_km": 25.0,
            },
        ]
        plan = HypotheticalPlan.from_week_dicts(
            "测试计划", weeks, source="cli", plan_id="p001"
        )
        assert plan.name == "测试计划"
        assert plan.source == "cli"
        assert plan.plan_id == "p001"
        assert len(plan.weeks) == 2
        assert plan.weeks[0].weekly_volume_km == 40.0
        assert plan.weeks[0].intensity_multiplier == 1.1
        assert plan.weeks[1].weekly_volume_km == 50.0
        assert plan.weeks[1].intensity_multiplier == 1.0

    def test_from_week_dicts_defaults(self) -> None:
        weeks = [{}]
        plan = HypotheticalPlan.from_week_dicts("空计划", weeks)
        assert plan.source == "cli"
        assert plan.plan_id == ""
        assert plan.weeks[0].weekly_volume_km == 0.0
        assert plan.weeks[0].easy_ratio == 0.7


class TestSimulationWeekSnapshot:
    def test_creation(self) -> None:
        state = RunnerStateVector(
            fitness=FitnessDimension(vdot=45.0, vdot_trend=0.02),
            load=LoadDimension(ctl=65.0, atl=50.0, tsb=15.0, acwr=0.77),
            body_signal=BodySignalDimension(fatigue_score=3.5, recovery_status="good"),
            risk=RiskDimension(
                injury_risk_7d=5.0, injury_risk_28d=15.0, overtraining_risk="low"
            ),
            training_pattern=TrainingPatternDimension(
                weekly_volume_km=40.0,
                intensity_distribution=IntensityDistribution(
                    zone1_pct=80.0, zone2_pct=15.0, zone3_pct=5.0
                ),
                long_run_frequency=1,
            ),
            snapshot_date="2026-05-12",
            data_quality=DataQuality.SUFFICIENT,
        )
        snap = SimulationWeekSnapshot(
            week_number=1,
            state=state,
            weekly_plan=WeeklyPlanSpec(
                weekly_volume_km=40.0,
                easy_ratio=0.7,
                tempo_ratio=0.15,
                interval_ratio=0.15,
                long_run_km=20.0,
            ),
            confidence=0.95,
        )
        assert snap.week_number == 1
        assert snap.confidence == 0.95

    def test_to_dict(self) -> None:
        state = RunnerStateVector(
            fitness=FitnessDimension(vdot=45.0, vdot_trend=0.02),
            load=LoadDimension(ctl=65.0, atl=50.0, tsb=15.0, acwr=0.77),
            body_signal=BodySignalDimension(fatigue_score=3.5, recovery_status="good"),
            risk=RiskDimension(
                injury_risk_7d=5.0, injury_risk_28d=15.0, overtraining_risk="low"
            ),
            training_pattern=TrainingPatternDimension(
                weekly_volume_km=40.0,
                intensity_distribution=IntensityDistribution(
                    zone1_pct=80.0, zone2_pct=15.0, zone3_pct=5.0
                ),
                long_run_frequency=1,
            ),
            snapshot_date="2026-05-12",
            data_quality=DataQuality.SUFFICIENT,
        )
        snap = SimulationWeekSnapshot(
            week_number=1,
            state=state,
            weekly_plan=WeeklyPlanSpec(
                weekly_volume_km=40.0,
                easy_ratio=0.7,
                tempo_ratio=0.15,
                interval_ratio=0.15,
                long_run_km=20.0,
            ),
            confidence=0.95,
        )
        d = snap.to_dict()
        assert d["week_number"] == 1
        assert d["confidence"] == 0.95
        assert "state" in d
        assert "weekly_plan" in d


class TestSimulationResult:
    def test_creation(self) -> None:
        initial = RunnerStateVector(
            fitness=FitnessDimension(vdot=45.0, vdot_trend=0.02),
            load=LoadDimension(ctl=65.0, atl=50.0, tsb=15.0, acwr=0.77),
            body_signal=BodySignalDimension(fatigue_score=3.5, recovery_status="good"),
            risk=RiskDimension(
                injury_risk_7d=5.0, injury_risk_28d=15.0, overtraining_risk="low"
            ),
            training_pattern=TrainingPatternDimension(
                weekly_volume_km=40.0,
                intensity_distribution=IntensityDistribution(
                    zone1_pct=80.0, zone2_pct=15.0, zone3_pct=5.0
                ),
                long_run_frequency=1,
            ),
            snapshot_date="2026-05-12",
            data_quality=DataQuality.SUFFICIENT,
        )
        result = SimulationResult(
            plan_name="全马破4计划",
            initial_state=initial,
            final_state=initial,
            snapshots=[],
            total_weeks=12,
            prediction_type="ml_enhanced",
            vdot_delta=1.5,
            peak_injury_risk=12.0,
            avg_tsb=5.0,
        )
        assert result.vdot_delta == 1.5
        assert result.total_weeks == 12

    def test_to_dict(self) -> None:
        initial = RunnerStateVector(
            fitness=FitnessDimension(vdot=45.0, vdot_trend=0.02),
            load=LoadDimension(ctl=65.0, atl=50.0, tsb=15.0, acwr=0.77),
            body_signal=BodySignalDimension(fatigue_score=3.5, recovery_status="good"),
            risk=RiskDimension(
                injury_risk_7d=5.0, injury_risk_28d=15.0, overtraining_risk="low"
            ),
            training_pattern=TrainingPatternDimension(
                weekly_volume_km=40.0,
                intensity_distribution=IntensityDistribution(
                    zone1_pct=80.0, zone2_pct=15.0, zone3_pct=5.0
                ),
                long_run_frequency=1,
            ),
            snapshot_date="2026-05-12",
            data_quality=DataQuality.SUFFICIENT,
        )
        result = SimulationResult(
            plan_name="全马破4计划",
            initial_state=initial,
            final_state=initial,
            snapshots=[],
            total_weeks=12,
            prediction_type="ml_enhanced",
            vdot_delta=1.5,
            peak_injury_risk=12.0,
            avg_tsb=5.0,
        )
        d = result.to_dict()
        assert d["vdot_delta"] == 1.5
        assert d["total_weeks"] == 12
        assert d["plan_name"] == "全马破4计划"


class TestPlanComparisonMetrics:
    def test_creation(self) -> None:
        m = PlanComparisonMetrics(
            plan_id="plan_001",
            plan_name="全马破4计划",
            vdot_delta=1.5,
            peak_injury_risk=12.0,
            avg_tsb=5.0,
            min_recovery_status="good",
            recommendation_score=0.85,
        )
        assert m.recommendation_score == 0.85

    def test_to_dict(self) -> None:
        m = PlanComparisonMetrics(
            plan_id="plan_001",
            plan_name="全马破4计划",
            vdot_delta=1.5,
            peak_injury_risk=12.0,
            avg_tsb=5.0,
            min_recovery_status="good",
            recommendation_score=0.85,
        )
        d = m.to_dict()
        assert d["recommendation_score"] == 0.85
        assert d["plan_id"] == "plan_001"


class TestPlanComparison:
    def test_creation(self) -> None:
        m1 = PlanComparisonMetrics(
            plan_id="plan_001",
            plan_name="全马破4计划",
            vdot_delta=1.5,
            peak_injury_risk=12.0,
            avg_tsb=5.0,
            min_recovery_status="good",
            recommendation_score=0.85,
        )
        m2 = PlanComparisonMetrics(
            plan_id="plan_002",
            plan_name="半马PB计划",
            vdot_delta=1.0,
            peak_injury_risk=8.0,
            avg_tsb=8.0,
            min_recovery_status="good",
            recommendation_score=0.75,
        )
        comp = PlanComparison(
            plans=[m1, m2],
            best_plan=m1,
            comparison_dimensions=["vdot_delta", "injury_risk", "tsb"],
            recommendation="推荐全马破4计划",
        )
        assert comp.best_plan.plan_id == "plan_001"

    def test_to_dict(self) -> None:
        m1 = PlanComparisonMetrics(
            plan_id="plan_001",
            plan_name="全马破4计划",
            vdot_delta=1.5,
            peak_injury_risk=12.0,
            avg_tsb=5.0,
            min_recovery_status="good",
            recommendation_score=0.85,
        )
        comp = PlanComparison(
            plans=[m1],
            best_plan=m1,
            comparison_dimensions=["vdot_delta"],
            recommendation="推荐全马破4计划",
        )
        d = comp.to_dict()
        assert d["best_plan"]["plan_id"] == "plan_001"
        assert len(d["plans"]) == 1


class TestStateVectorCache:
    def test_ttl_hours_default(self) -> None:
        state = RunnerStateVector(
            fitness=FitnessDimension(vdot=45.0, vdot_trend=0.02),
            load=LoadDimension(ctl=65.0, atl=50.0, tsb=15.0, acwr=0.77),
            body_signal=BodySignalDimension(fatigue_score=3.5, recovery_status="good"),
            risk=RiskDimension(
                injury_risk_7d=5.0, injury_risk_28d=15.0, overtraining_risk="low"
            ),
            training_pattern=TrainingPatternDimension(
                weekly_volume_km=40.0,
                intensity_distribution=IntensityDistribution(
                    zone1_pct=80.0, zone2_pct=15.0, zone3_pct=5.0
                ),
                long_run_frequency=1,
            ),
            snapshot_date="2026-05-12",
            data_quality=DataQuality.SUFFICIENT,
        )
        cache = StateVectorCache(state=state, created_at=datetime.now().isoformat())
        assert cache.ttl_hours == 24

    def test_is_expired_false(self) -> None:
        state = RunnerStateVector(
            fitness=FitnessDimension(vdot=45.0, vdot_trend=0.02),
            load=LoadDimension(ctl=65.0, atl=50.0, tsb=15.0, acwr=0.77),
            body_signal=BodySignalDimension(fatigue_score=3.5, recovery_status="good"),
            risk=RiskDimension(
                injury_risk_7d=5.0, injury_risk_28d=15.0, overtraining_risk="low"
            ),
            training_pattern=TrainingPatternDimension(
                weekly_volume_km=40.0,
                intensity_distribution=IntensityDistribution(
                    zone1_pct=80.0, zone2_pct=15.0, zone3_pct=5.0
                ),
                long_run_frequency=1,
            ),
            snapshot_date="2026-05-12",
            data_quality=DataQuality.SUFFICIENT,
        )
        cache = StateVectorCache(
            state=state, created_at=datetime.now().isoformat(), ttl_hours=24
        )
        assert cache.is_expired() is False

    def test_is_expired_true(self) -> None:
        state = RunnerStateVector(
            fitness=FitnessDimension(vdot=45.0, vdot_trend=0.02),
            load=LoadDimension(ctl=65.0, atl=50.0, tsb=15.0, acwr=0.77),
            body_signal=BodySignalDimension(fatigue_score=3.5, recovery_status="good"),
            risk=RiskDimension(
                injury_risk_7d=5.0, injury_risk_28d=15.0, overtraining_risk="low"
            ),
            training_pattern=TrainingPatternDimension(
                weekly_volume_km=40.0,
                intensity_distribution=IntensityDistribution(
                    zone1_pct=80.0, zone2_pct=15.0, zone3_pct=5.0
                ),
                long_run_frequency=1,
            ),
            snapshot_date="2026-05-12",
            data_quality=DataQuality.SUFFICIENT,
        )
        old_time = (datetime.now() - timedelta(hours=25)).isoformat()
        cache = StateVectorCache(state=state, created_at=old_time, ttl_hours=24)
        assert cache.is_expired() is True


class TestTwinEngineError:
    def test_message(self) -> None:
        err = TwinEngineError(message="计划不存在")
        assert err.message == "计划不存在"

    def test_error_code(self) -> None:
        err = TwinEngineError(message="计划不存在")
        assert err.error_code == "TWIN_ENGINE_ERROR"

    def test_inherits_nanobot_runner_error(self) -> None:
        from src.core.base.exceptions import NanobotRunnerError

        err = TwinEngineError(message="test")
        assert isinstance(err, NanobotRunnerError)

    def test_to_dict(self) -> None:
        err = TwinEngineError(
            message="计划不存在", recovery_suggestion="请检查计划ID是否正确"
        )
        d = err.to_dict()
        assert d["error"] == "计划不存在"
        assert d["error_code"] == "TWIN_ENGINE_ERROR"
        assert d["recovery_suggestion"] == "请检查计划ID是否正确"
