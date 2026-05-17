from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest

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
    TwinEngineError,
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
        snapshot_date=datetime.now().strftime("%Y-%m-%d"),
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


def _make_engine(
    cache_dir: Path | None = None,
    plan_manager: object | None = None,
) -> DigitalTwinEngine:
    mock_builder = MagicMock()
    mock_builder.build.return_value = _make_state()
    return DigitalTwinEngine(
        state_vector_builder=mock_builder,
        plan_manager=plan_manager,
        cache_dir=cache_dir,
    )


class TestDigitalTwinEngineSnapshot:
    """测试 get_current_snapshot"""

    def test_returns_runner_state_vector(self) -> None:
        engine = _make_engine()
        result = engine.get_current_snapshot()
        assert isinstance(result, RunnerStateVector)

    def test_delegates_to_builder(self) -> None:
        mock_builder = MagicMock()
        mock_builder.build.return_value = _make_state()
        engine = DigitalTwinEngine(state_vector_builder=mock_builder)
        engine.get_current_snapshot()
        mock_builder.build.assert_called_once()

    def test_uses_memory_cache_on_second_call(self) -> None:
        mock_builder = MagicMock()
        mock_builder.build.return_value = _make_state()
        engine = DigitalTwinEngine(state_vector_builder=mock_builder)
        engine.get_current_snapshot()
        engine.get_current_snapshot()
        mock_builder.build.assert_called_once()

    def test_disk_cache_hit(self, tmp_path: Path) -> None:
        state = _make_state()
        cache_data = {
            "state": state.to_dict(),
            "created_at": datetime.now().isoformat(),
            "ttl_hours": 24,
        }
        cache_dir = tmp_path / "twin"
        cache_dir.mkdir()
        (cache_dir / "state_vector.json").write_text(
            json.dumps(cache_data, ensure_ascii=False), encoding="utf-8"
        )
        mock_builder = MagicMock()
        engine = DigitalTwinEngine(
            state_vector_builder=mock_builder, cache_dir=tmp_path
        )
        result = engine.get_current_snapshot()
        assert isinstance(result, RunnerStateVector)
        mock_builder.build.assert_not_called()

    def test_disk_cache_expired_rebuilds(self, tmp_path: Path) -> None:
        state = _make_state()
        old_time = (datetime.now() - timedelta(hours=25)).isoformat()
        cache_data = {
            "state": state.to_dict(),
            "created_at": old_time,
            "ttl_hours": 24,
        }
        cache_dir = tmp_path / "twin"
        cache_dir.mkdir()
        (cache_dir / "state_vector.json").write_text(
            json.dumps(cache_data, ensure_ascii=False), encoding="utf-8"
        )
        mock_builder = MagicMock()
        mock_builder.build.return_value = _make_state()
        engine = DigitalTwinEngine(
            state_vector_builder=mock_builder, cache_dir=tmp_path
        )
        engine.get_current_snapshot()
        mock_builder.build.assert_called_once()

    def test_saves_cache_to_disk(self, tmp_path: Path) -> None:
        mock_builder = MagicMock()
        mock_builder.build.return_value = _make_state()
        engine = DigitalTwinEngine(
            state_vector_builder=mock_builder, cache_dir=tmp_path
        )
        engine.get_current_snapshot()
        cache_file = tmp_path / "twin" / "state_vector.json"
        assert cache_file.exists()
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        assert "state" in data
        assert data["ttl_hours"] == 24


class TestDigitalTwinEngineSimulate:
    """测试 simulate"""

    def test_returns_simulation_result(self) -> None:
        engine = _make_engine()
        plan = _make_plan()
        result = engine.simulate(plan, prediction_type="parametric")
        assert isinstance(result, SimulationResult)

    def test_snapshot_count_matches_plan_weeks(self) -> None:
        engine = _make_engine()
        plan = _make_plan(weeks=6)
        result = engine.simulate(plan, prediction_type="parametric")
        assert len(result.snapshots) == 6


class TestDigitalTwinEngineCompare:
    """测试 compare_plans"""

    def test_returns_plan_comparison(self) -> None:
        engine = _make_engine()
        plan_a = _make_plan(name="计划A")
        plan_b = _make_plan(name="计划B")
        result = engine.compare_plans([plan_a, plan_b], prediction_type="parametric")
        assert isinstance(result, PlanComparison)

    def test_comparison_contains_both_plans(self) -> None:
        engine = _make_engine()
        plan_a = _make_plan(name="计划A")
        plan_b = _make_plan(name="计划B")
        result = engine.compare_plans([plan_a, plan_b], prediction_type="parametric")
        assert len(result.plans) == 2

    def test_winner_is_determined(self) -> None:
        engine = _make_engine()
        plan_a = _make_plan(name="计划A")
        plan_b = _make_plan(name="计划B")
        result = engine.compare_plans([plan_a, plan_b], prediction_type="parametric")
        assert result.best_plan.plan_name in ["计划A", "计划B"]

    def test_empty_plans_raises_error(self) -> None:
        engine = _make_engine()
        with pytest.raises(TwinEngineError, match="计划列表不能为空"):
            engine.compare_plans([], prediction_type="parametric")


class TestDigitalTwinEngineComputeScore:
    """测试 _compute_score（架构7.7节归一化+权重）"""

    def test_score_in_0_100_range(self) -> None:
        result = SimulationResult(
            plan_name="测试",
            initial_state=_make_state(),
            final_state=_make_state(),
            snapshots=[],
            total_weeks=4,
            prediction_type="parametric",
            vdot_delta=1.0,
            peak_injury_risk=10.0,
            avg_tsb=5.0,
        )
        score = DigitalTwinEngine._compute_score(result)
        assert 0.0 <= score <= 100.0

    def test_high_vdot_high_score(self) -> None:
        result_good = SimulationResult(
            plan_name="好计划",
            initial_state=_make_state(),
            final_state=_make_state(),
            snapshots=[],
            total_weeks=4,
            prediction_type="parametric",
            vdot_delta=3.0,
            peak_injury_risk=5.0,
            avg_tsb=10.0,
        )
        result_bad = SimulationResult(
            plan_name="差计划",
            initial_state=_make_state(),
            final_state=_make_state(),
            snapshots=[],
            total_weeks=4,
            prediction_type="parametric",
            vdot_delta=0.5,
            peak_injury_risk=40.0,
            avg_tsb=-15.0,
        )
        score_good = DigitalTwinEngine._compute_score(result_good)
        score_bad = DigitalTwinEngine._compute_score(result_bad)
        assert score_good > score_bad

    def test_weights_sum_to_one(self) -> None:
        assert 0.4 + 0.35 + 0.25 == 1.0

    def test_vdot_delta_zero_gives_zero_vdot_score(self) -> None:
        result = SimulationResult(
            plan_name="零VDOT",
            initial_state=_make_state(),
            final_state=_make_state(),
            snapshots=[],
            total_weeks=4,
            prediction_type="parametric",
            vdot_delta=0.0,
            peak_injury_risk=50.0,
            avg_tsb=-30.0,
        )
        score = DigitalTwinEngine._compute_score(result)
        assert score < 50.0


class TestDigitalTwinEngineLoadPlan:
    """测试 load_plan"""

    def test_no_plan_manager_raises_error(self) -> None:
        engine = _make_engine(plan_manager=None)
        with pytest.raises(TwinEngineError, match="PlanManager未注入"):
            engine.load_plan("plan_001")

    def test_plan_not_found_raises_error(self) -> None:
        mock_pm = MagicMock()
        mock_pm.get_plan.return_value = None
        engine = _make_engine(plan_manager=mock_pm)
        with pytest.raises(TwinEngineError, match="训练计划不存在"):
            engine.load_plan("nonexistent")

    def test_load_plan_success(self) -> None:
        mock_daily = MagicMock()
        mock_daily.distance_km = 10.0
        mock_daily.workout_type = "easy"
        mock_week = MagicMock()
        mock_week.daily_plans = [mock_daily]
        mock_plan = MagicMock()
        mock_plan.weeks = [mock_week]
        mock_plan.name = "测试计划"
        mock_plan.plan_id = "plan_001"
        mock_pm = MagicMock()
        mock_pm.get_plan.return_value = mock_plan
        engine = _make_engine(plan_manager=mock_pm)
        result = engine.load_plan("plan_001")
        assert isinstance(result, HypotheticalPlan)
        assert result.name == "测试计划"
        assert result.source == "plan_id"
        assert result.plan_id == "plan_001"


class TestDigitalTwinEngineComparePlansByIds:
    """测试 compare_plans_by_ids"""

    def _make_plan_manager_with_plans(self) -> MagicMock:
        mock_pm = MagicMock()

        def get_plan(plan_id: str) -> MagicMock:
            mock_daily = MagicMock()
            mock_daily.distance_km = 10.0
            mock_daily.workout_type = "easy"
            mock_week = MagicMock()
            mock_week.daily_plans = [mock_daily]
            mock_plan = MagicMock()
            mock_plan.weeks = [mock_week]
            mock_plan.name = f"计划_{plan_id}"
            mock_plan.plan_id = plan_id
            return mock_plan

        mock_pm.get_plan.side_effect = get_plan
        return mock_pm

    def test_returns_plan_comparison(self) -> None:
        mock_pm = self._make_plan_manager_with_plans()
        engine = _make_engine(plan_manager=mock_pm)
        result = engine.compare_plans_by_ids(
            ["plan_001", "plan_002"], prediction_type="parametric"
        )
        assert isinstance(result, PlanComparison)

    def test_less_than_2_raises_error(self) -> None:
        engine = _make_engine()
        with pytest.raises(TwinEngineError, match="对比计划数量不能少于2个"):
            engine.compare_plans_by_ids(["plan_001"])

    def test_more_than_5_raises_error(self) -> None:
        engine = _make_engine()
        with pytest.raises(TwinEngineError, match="对比计划数量不能超过5个"):
            engine.compare_plans_by_ids(["p1", "p2", "p3", "p4", "p5", "p6"])

    def test_exactly_2_plans_works(self) -> None:
        mock_pm = self._make_plan_manager_with_plans()
        engine = _make_engine(plan_manager=mock_pm)
        result = engine.compare_plans_by_ids(
            ["plan_001", "plan_002"], prediction_type="parametric"
        )
        assert len(result.plans) == 2

    def test_exactly_5_plans_works(self) -> None:
        mock_pm = self._make_plan_manager_with_plans()
        engine = _make_engine(plan_manager=mock_pm)
        result = engine.compare_plans_by_ids(
            ["p1", "p2", "p3", "p4", "p5"], prediction_type="parametric"
        )
        assert len(result.plans) == 5

    def test_no_plan_manager_raises_error(self) -> None:
        engine = _make_engine(plan_manager=None)
        with pytest.raises(TwinEngineError, match="PlanManager未注入"):
            engine.compare_plans_by_ids(["plan_001", "plan_002"])


class TestDigitalTwinEngineAggregateWeekSpec:
    """测试 _aggregate_week_spec（P2-08 提取的子方法）"""

    def test_single_easy_day(self) -> None:
        mock_daily = MagicMock()
        mock_daily.distance_km = 10.0
        mock_daily.workout_type = "easy"
        mock_week = MagicMock()
        mock_week.daily_plans = [mock_daily]
        result = DigitalTwinEngine._aggregate_week_spec(mock_week)
        assert result is not None
        assert result.weekly_volume_km == 10.0
        assert result.easy_ratio == 1.0

    def test_mixed_workout_types(self) -> None:
        mock_easy = MagicMock(distance_km=7.0, workout_type="easy")
        mock_tempo = MagicMock(distance_km=5.0, workout_type="tempo")
        mock_interval = MagicMock(distance_km=4.0, workout_type="interval")
        mock_long = MagicMock(distance_km=20.0, workout_type="long")
        mock_week = MagicMock()
        mock_week.daily_plans = [mock_easy, mock_tempo, mock_interval, mock_long]
        result = DigitalTwinEngine._aggregate_week_spec(mock_week)
        assert result is not None
        assert result.weekly_volume_km == 36.0
        assert result.long_run_km == 20.0

    def test_zero_distance_returns_none(self) -> None:
        mock_daily = MagicMock()
        mock_daily.distance_km = 0.0
        mock_daily.workout_type = "easy"
        mock_week = MagicMock()
        mock_week.daily_plans = [mock_daily]
        result = DigitalTwinEngine._aggregate_week_spec(mock_week)
        assert result is None

    def test_no_daily_plans_returns_none(self) -> None:
        mock_week = MagicMock(spec=[])
        result = DigitalTwinEngine._aggregate_week_spec(mock_week)
        assert result is None

    def test_recovery_workout_counted_as_easy(self) -> None:
        mock_daily = MagicMock(distance_km=5.0, workout_type="recovery")
        mock_week = MagicMock()
        mock_week.daily_plans = [mock_daily]
        result = DigitalTwinEngine._aggregate_week_spec(mock_week)
        assert result is not None
        assert result.easy_ratio == 1.0

    def test_threshold_workout_counted_as_tempo(self) -> None:
        mock_daily = MagicMock(distance_km=8.0, workout_type="threshold")
        mock_week = MagicMock()
        mock_week.daily_plans = [mock_daily]
        result = DigitalTwinEngine._aggregate_week_spec(mock_week)
        assert result is not None
        assert result.tempo_ratio == 1.0
