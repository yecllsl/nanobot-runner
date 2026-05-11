from __future__ import annotations

from unittest.mock import MagicMock

from src.core.twin.digital_twin_engine import DigitalTwinEngine
from src.core.twin.models import (
    BodySignalDimension,
    DataQuality,
    FitnessDimension,
    HypotheticalPlan,
    IntensityDistribution,
    LoadDimension,
    PlanComparison,
    RiskDimension,
    RunnerStateVector,
    SimulationResult,
    TrainingPatternDimension,
    WeeklyPlanSpec,
)


def _make_state() -> RunnerStateVector:
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


def _make_plan(name: str = "测试计划", weeks: int = 4) -> HypotheticalPlan:
    return HypotheticalPlan(
        name=name,
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


class TestDigitalTwinEngineSnapshot:
    """测试 get_current_snapshot"""

    def test_returns_runner_state_vector(self) -> None:
        mock_builder = MagicMock()
        mock_builder.build.return_value = _make_state()
        engine = DigitalTwinEngine(state_vector_builder=mock_builder)
        result = engine.get_current_snapshot()
        assert isinstance(result, RunnerStateVector)

    def test_delegates_to_builder(self) -> None:
        mock_builder = MagicMock()
        mock_builder.build.return_value = _make_state()
        engine = DigitalTwinEngine(state_vector_builder=mock_builder)
        engine.get_current_snapshot()
        mock_builder.build.assert_called_once()


class TestDigitalTwinEngineSimulate:
    """测试 simulate"""

    def test_returns_simulation_result(self) -> None:
        mock_builder = MagicMock()
        mock_builder.build.return_value = _make_state()
        engine = DigitalTwinEngine(state_vector_builder=mock_builder)
        plan = _make_plan()
        result = engine.simulate(plan, prediction_type="parametric")
        assert isinstance(result, SimulationResult)

    def test_snapshot_count_matches_plan_weeks(self) -> None:
        mock_builder = MagicMock()
        mock_builder.build.return_value = _make_state()
        engine = DigitalTwinEngine(state_vector_builder=mock_builder)
        plan = _make_plan(weeks=6)
        result = engine.simulate(plan, prediction_type="parametric")
        assert len(result.snapshots) == 6


class TestDigitalTwinEngineCompare:
    """测试 compare_plans"""

    def test_returns_plan_comparison(self) -> None:
        mock_builder = MagicMock()
        mock_builder.build.return_value = _make_state()
        engine = DigitalTwinEngine(state_vector_builder=mock_builder)
        plan_a = _make_plan(name="计划A")
        plan_b = _make_plan(name="计划B")
        result = engine.compare_plans([plan_a, plan_b], prediction_type="parametric")
        assert isinstance(result, PlanComparison)

    def test_comparison_contains_both_plans(self) -> None:
        mock_builder = MagicMock()
        mock_builder.build.return_value = _make_state()
        engine = DigitalTwinEngine(state_vector_builder=mock_builder)
        plan_a = _make_plan(name="计划A")
        plan_b = _make_plan(name="计划B")
        result = engine.compare_plans([plan_a, plan_b], prediction_type="parametric")
        assert len(result.plans) == 2

    def test_winner_is_determined(self) -> None:
        mock_builder = MagicMock()
        mock_builder.build.return_value = _make_state()
        engine = DigitalTwinEngine(state_vector_builder=mock_builder)
        plan_a = _make_plan(name="计划A")
        plan_b = _make_plan(name="计划B")
        result = engine.compare_plans([plan_a, plan_b], prediction_type="parametric")
        assert result.best_plan.plan_name in ["计划A", "计划B"]
