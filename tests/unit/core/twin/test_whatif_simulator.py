from __future__ import annotations

from unittest.mock import MagicMock

from src.core.twin.models import (
    BodySignalDimension,
    DataQuality,
    FitnessDimension,
    HypotheticalPlan,
    IntensityDistribution,
    LoadDimension,
    RiskDimension,
    RunnerStateVector,
    SimulationResult,
    TrainingPatternDimension,
    WeeklyPlanSpec,
)
from src.core.twin.whatif_simulator import WhatIfSimulator


def _make_state(
    vdot: float = 45.0,
    ctl: float = 65.0,
    atl: float = 50.0,
) -> RunnerStateVector:
    return RunnerStateVector(
        fitness=FitnessDimension(vdot=vdot, vdot_trend=0.02),
        load=LoadDimension(
            ctl=ctl, atl=atl, tsb=ctl - atl, acwr=atl / ctl if ctl > 0 else 0.0
        ),
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


def _make_plan(weeks: int = 4) -> HypotheticalPlan:
    return HypotheticalPlan(
        name="测试计划",
        weeks=[
            WeeklyPlanSpec(
                weekly_volume_km=40.0,
                easy_ratio=0.7,
                tempo_ratio=0.15,
                interval_ratio=0.15,
                long_run_km=20.0,
            )
            for _ in range(weeks)
        ],
        source="plan_id",
        plan_id="plan_001",
    )


class TestEstimateWeeklyTss:
    def test_basic_estimation(self) -> None:
        sim = WhatIfSimulator()
        plan = WeeklyPlanSpec(
            weekly_volume_km=40.0,
            easy_ratio=0.7,
            tempo_ratio=0.15,
            interval_ratio=0.15,
            long_run_km=20.0,
        )
        tss = sim.estimate_weekly_tss(plan)
        assert tss > 0

    def test_zero_volume(self) -> None:
        sim = WhatIfSimulator()
        plan = WeeklyPlanSpec(
            weekly_volume_km=0.0,
            easy_ratio=0.7,
            tempo_ratio=0.15,
            interval_ratio=0.15,
            long_run_km=0.0,
        )
        tss = sim.estimate_weekly_tss(plan)
        assert tss == 0.0

    def test_intensity_multiplier(self) -> None:
        sim = WhatIfSimulator()
        plan_base = WeeklyPlanSpec(
            weekly_volume_km=40.0,
            easy_ratio=0.7,
            tempo_ratio=0.15,
            interval_ratio=0.15,
            long_run_km=20.0,
            intensity_multiplier=1.0,
        )
        plan_high = WeeklyPlanSpec(
            weekly_volume_km=40.0,
            easy_ratio=0.7,
            tempo_ratio=0.15,
            interval_ratio=0.15,
            long_run_km=20.0,
            intensity_multiplier=1.2,
        )
        tss_base = sim.estimate_weekly_tss(plan_base)
        tss_high = sim.estimate_weekly_tss(plan_high)
        assert tss_high > tss_base


class TestSimulateWeek:
    def test_returns_runner_state_vector(self) -> None:
        sim = WhatIfSimulator()
        state = _make_state()
        plan = WeeklyPlanSpec(
            weekly_volume_km=40.0,
            easy_ratio=0.7,
            tempo_ratio=0.15,
            interval_ratio=0.15,
            long_run_km=20.0,
        )
        result = sim.simulate_week(state, plan, "parametric")
        assert isinstance(result, RunnerStateVector)

    def test_load_updates(self) -> None:
        sim = WhatIfSimulator()
        state = _make_state(ctl=65.0, atl=50.0)
        plan = WeeklyPlanSpec(
            weekly_volume_km=40.0,
            easy_ratio=0.7,
            tempo_ratio=0.15,
            interval_ratio=0.15,
            long_run_km=20.0,
        )
        result = sim.simulate_week(state, plan, "parametric")
        assert result.load.ctl != 65.0 or result.load.atl != 50.0

    def test_uses_banister_model_when_injected(self) -> None:
        mock_banister = MagicMock()
        mock_banister.predict_performance.return_value = 46.5
        sim = WhatIfSimulator(banister_model=mock_banister)
        state = _make_state()
        plan = WeeklyPlanSpec(
            weekly_volume_km=40.0,
            easy_ratio=0.7,
            tempo_ratio=0.15,
            interval_ratio=0.15,
            long_run_km=20.0,
        )
        result = sim.simulate_week(state, plan, "parametric")
        assert isinstance(result, RunnerStateVector)


class TestSimulate:
    def test_snapshot_count(self) -> None:
        sim = WhatIfSimulator()
        state = _make_state()
        plan = _make_plan(weeks=4)
        result = sim.simulate(state, plan, "parametric")
        assert len(result.snapshots) == 4

    def test_week_numbers(self) -> None:
        sim = WhatIfSimulator()
        state = _make_state()
        plan = _make_plan(weeks=4)
        result = sim.simulate(state, plan, "parametric")
        assert [s.week_number for s in result.snapshots] == [1, 2, 3, 4]

    def test_confidence_decay_l1(self) -> None:
        sim = WhatIfSimulator()
        state = _make_state()
        plan = _make_plan(weeks=4)
        result = sim.simulate(state, plan, "ml_enhanced")
        confidences = [s.confidence for s in result.snapshots]
        assert confidences[0] > confidences[-1]

    def test_confidence_decay_l3(self) -> None:
        sim = WhatIfSimulator()
        state = _make_state()
        plan = _make_plan(weeks=4)
        result = sim.simulate(state, plan, "basic")
        confidences = [s.confidence for s in result.snapshots]
        assert confidences[0] > confidences[-1]

    def test_l3_decays_faster_than_l1(self) -> None:
        sim = WhatIfSimulator()
        state = _make_state()
        plan = _make_plan(weeks=8)
        result_l1 = sim.simulate(state, plan, "ml_enhanced")
        result_l3 = sim.simulate(state, plan, "basic")
        last_conf_l1 = result_l1.snapshots[-1].confidence
        last_conf_l3 = result_l3.snapshots[-1].confidence
        assert last_conf_l1 > last_conf_l3

    def test_basic_mode(self) -> None:
        sim = WhatIfSimulator()
        state = _make_state()
        plan = _make_plan(weeks=4)
        result = sim.simulate(state, plan, "basic")
        assert isinstance(result, SimulationResult)
        assert result.prediction_type == "basic"

    def test_instance_with_prediction_engine(self) -> None:
        mock_pe = MagicMock()
        sim = WhatIfSimulator(prediction_engine=mock_pe)
        state = _make_state()
        plan = _make_plan(weeks=4)
        result = sim.simulate(state, plan, "ml_enhanced")
        assert isinstance(result, SimulationResult)
