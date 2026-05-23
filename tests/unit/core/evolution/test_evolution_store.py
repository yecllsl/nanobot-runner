# EvolutionStore 存储层单元测试
# 覆盖决策日志/结果记录的保存、查询、配对、持久化等场景
# 适配Parquet按月分片存储

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from src.core.evolution.evolution_store import EvolutionStore
from src.core.evolution.models import CalibrationProfile, DecisionLog, OutcomeRecord
from src.core.transparency.models import DecisionType


def _make_decision(
    decision_id: str = "dec_001",
    timestamp: datetime | None = None,
    decision_type: DecisionType = DecisionType.TRAINING_ADVICE,
    execution_status: str = "pending",
    session_key: str = "session_001",
) -> DecisionLog:
    """创建测试用DecisionLog辅助函数"""
    return DecisionLog(
        decision_id=decision_id,
        timestamp=timestamp or datetime(2026, 5, 1, 10, 0, 0),
        runner_state={"vdot": 45.0, "ctl": 50.0, "atl": 40.0, "tsb": 10.0},
        decision_type=decision_type,
        tool_call_chain=[{"tool": "suggest_training", "arguments": {}}],
        prediction_snapshot=None,
        recommendation_text="建议轻松跑",
        execution_status=execution_status,
        recommendation_accepted=None,
        session_key=session_key,
    )


def _make_outcome(
    outcome_id: str = "out_001",
    decision_id: str = "dec_001",
    outcome_timestamp: datetime | None = None,
    actual_vdot: float | None = None,
    actual_injury: bool = False,
    prediction_error: float | None = None,
    prediction_direction: str | None = None,
) -> OutcomeRecord:
    """创建测试用OutcomeRecord辅助函数"""
    return OutcomeRecord(
        outcome_id=outcome_id,
        decision_id=decision_id,
        outcome_timestamp=outcome_timestamp or datetime(2026, 5, 2, 8, 0, 0),
        actual_vdot=actual_vdot,
        actual_injury=actual_injury,
        execution_fidelity=None,
        user_feedback_score=None,
        user_feedback_text=None,
        prediction_error=prediction_error,
        prediction_direction=prediction_direction,
        session_id=None,
    )


class TestSaveAndGetDecision:
    """保存并获取决策日志"""

    def test_save_and_get_decision(self, tmp_path):
        """保存决策日志后，能通过ID获取"""
        store = EvolutionStore(tmp_path)
        decision = _make_decision("dec_001")

        store.save_decision(decision)

        result = store.get_decision_by_id("dec_001")
        assert result is not None
        assert result.decision_id == "dec_001"
        assert result.decision_type == DecisionType.TRAINING_ADVICE
        assert result.execution_status == "pending"
        assert result.recommendation_text == "建议轻松跑"

    def test_get_nonexistent_decision_returns_none(self, tmp_path):
        """获取不存在的决策返回None"""
        store = EvolutionStore(tmp_path)

        result = store.get_decision_by_id("nonexistent_id")
        assert result is None


class TestQueryDecisions:
    """决策日志查询"""

    def test_query_by_date_range(self, tmp_path):
        """按日期范围查询决策"""
        store = EvolutionStore(tmp_path)
        d1 = _make_decision("dec_001", timestamp=datetime(2026, 5, 1))
        d2 = _make_decision("dec_002", timestamp=datetime(2026, 5, 10))
        d3 = _make_decision("dec_003", timestamp=datetime(2026, 5, 20))

        store.save_decision(d1)
        store.save_decision(d2)
        store.save_decision(d3)

        results = store.query_decisions(
            start_date=datetime(2026, 5, 5),
            end_date=datetime(2026, 5, 15),
        )
        assert len(results) == 1
        assert results[0].decision_id == "dec_002"

    def test_query_by_decision_type(self, tmp_path):
        """按决策类型查询"""
        store = EvolutionStore(tmp_path)
        d1 = _make_decision("dec_001", decision_type=DecisionType.TRAINING_ADVICE)
        d2 = _make_decision("dec_002", decision_type=DecisionType.PLAN_ADJUSTMENT)
        d3 = _make_decision("dec_003", decision_type=DecisionType.TRAINING_ADVICE)

        store.save_decision(d1)
        store.save_decision(d2)
        store.save_decision(d3)

        results = store.query_decisions(decision_type=DecisionType.TRAINING_ADVICE)
        assert len(results) == 2
        assert all(r.decision_type == DecisionType.TRAINING_ADVICE for r in results)

    def test_query_by_execution_status(self, tmp_path):
        """按执行状态查询"""
        store = EvolutionStore(tmp_path)
        d1 = _make_decision("dec_001", execution_status="executed")
        d2 = _make_decision("dec_002", execution_status="pending")
        d3 = _make_decision("dec_003", execution_status="executed")

        store.save_decision(d1)
        store.save_decision(d2)
        store.save_decision(d3)

        results = store.query_decisions(execution_status="executed")
        assert len(results) == 2
        assert all(r.execution_status == "executed" for r in results)

    def test_query_with_limit(self, tmp_path):
        """查询数量限制"""
        store = EvolutionStore(tmp_path)
        for i in range(5):
            d = _make_decision(
                f"dec_{i:03d}",
                timestamp=datetime(2026, 5, i + 1),
            )
            store.save_decision(d)

        results = store.query_decisions(limit=2)
        assert len(results) == 2

    def test_query_results_ordered_by_timestamp_desc(self, tmp_path):
        """查询结果按时间倒序排列"""
        store = EvolutionStore(tmp_path)
        d1 = _make_decision("dec_001", timestamp=datetime(2026, 5, 1))
        d2 = _make_decision("dec_002", timestamp=datetime(2026, 5, 15))
        d3 = _make_decision("dec_003", timestamp=datetime(2026, 5, 8))

        store.save_decision(d1)
        store.save_decision(d2)
        store.save_decision(d3)

        results = store.query_decisions()
        assert len(results) == 3
        assert results[0].decision_id == "dec_002"
        assert results[1].decision_id == "dec_003"
        assert results[2].decision_id == "dec_001"

    def test_query_empty_store(self, tmp_path):
        """空存储查询返回空列表"""
        store = EvolutionStore(tmp_path)
        results = store.query_decisions()
        assert results == []


class TestSaveAndQueryOutcomes:
    """结果记录保存与查询"""

    def test_save_and_query_outcome(self, tmp_path):
        """保存并查询结果记录"""
        store = EvolutionStore(tmp_path)
        outcome = _make_outcome(
            outcome_id="out_001",
            decision_id="dec_001",
            outcome_timestamp=datetime(2026, 5, 2),
            actual_vdot=46.0,
            prediction_error=0.03,
            prediction_direction="overestimate",
        )

        store.save_outcome(outcome)

        results = store.query_outcomes(decision_id="dec_001")
        assert len(results) == 1
        assert results[0].outcome_id == "out_001"
        assert results[0].actual_vdot == 46.0
        assert results[0].prediction_direction == "overestimate"

    def test_query_outcomes_by_date_range(self, tmp_path):
        """按日期范围查询结果记录"""
        store = EvolutionStore(tmp_path)
        o1 = _make_outcome("out_001", outcome_timestamp=datetime(2026, 5, 1))
        o2 = _make_outcome("out_002", outcome_timestamp=datetime(2026, 5, 10))
        o3 = _make_outcome("out_003", outcome_timestamp=datetime(2026, 5, 20))

        store.save_outcome(o1)
        store.save_outcome(o2)
        store.save_outcome(o3)

        results = store.query_outcomes(
            start_date=datetime(2026, 5, 5),
            end_date=datetime(2026, 5, 15),
        )
        assert len(results) == 1
        assert results[0].outcome_id == "out_002"

    def test_query_outcomes_ordered_by_timestamp_desc(self, tmp_path):
        """查询结果按时间倒序排列"""
        store = EvolutionStore(tmp_path)
        o1 = _make_outcome("out_001", outcome_timestamp=datetime(2026, 5, 1))
        o2 = _make_outcome("out_002", outcome_timestamp=datetime(2026, 5, 15))
        o3 = _make_outcome("out_003", outcome_timestamp=datetime(2026, 5, 8))

        store.save_outcome(o1)
        store.save_outcome(o2)
        store.save_outcome(o3)

        results = store.query_outcomes()
        assert results[0].outcome_id == "out_002"
        assert results[1].outcome_id == "out_003"
        assert results[2].outcome_id == "out_001"


class TestDecisionOutcomePairs:
    """决策-结果配对"""

    def test_get_decision_outcome_pairs(self, tmp_path):
        """获取决策-结果配对"""
        store = EvolutionStore(tmp_path)

        d1 = _make_decision("dec_001", timestamp=datetime(2026, 5, 1))
        d2 = _make_decision("dec_002", timestamp=datetime(2026, 5, 5))
        store.save_decision(d1)
        store.save_decision(d2)

        o1 = _make_outcome(
            "out_001",
            decision_id="dec_001",
            outcome_timestamp=datetime(2026, 5, 2),
        )
        store.save_outcome(o1)

        pairs = store.get_decision_outcome_pairs()
        assert len(pairs) == 1
        assert pairs[0][0].decision_id == "dec_001"
        assert pairs[0][1].outcome_id == "out_001"

    def test_get_pairs_with_date_filter(self, tmp_path):
        """带日期过滤的决策-结果配对"""
        store = EvolutionStore(tmp_path)

        d1 = _make_decision("dec_001", timestamp=datetime(2026, 5, 1))
        d2 = _make_decision("dec_002", timestamp=datetime(2026, 5, 15))
        store.save_decision(d1)
        store.save_decision(d2)

        o1 = _make_outcome(
            "out_001",
            decision_id="dec_001",
            outcome_timestamp=datetime(2026, 5, 2),
        )
        o2 = _make_outcome(
            "out_002",
            decision_id="dec_002",
            outcome_timestamp=datetime(2026, 5, 16),
        )
        store.save_outcome(o1)
        store.save_outcome(o2)

        pairs = store.get_decision_outcome_pairs(
            start_date=datetime(2026, 5, 10),
        )
        assert len(pairs) == 1
        assert pairs[0][0].decision_id == "dec_002"

    def test_pairs_ordered_by_decision_timestamp_desc(self, tmp_path):
        """配对按决策时间倒序排列"""
        store = EvolutionStore(tmp_path)

        d1 = _make_decision("dec_001", timestamp=datetime(2026, 5, 1))
        d2 = _make_decision("dec_002", timestamp=datetime(2026, 5, 10))
        store.save_decision(d1)
        store.save_decision(d2)

        o1 = _make_outcome(
            "out_001", decision_id="dec_001", outcome_timestamp=datetime(2026, 5, 2)
        )
        o2 = _make_outcome(
            "out_002", decision_id="dec_002", outcome_timestamp=datetime(2026, 5, 11)
        )
        store.save_outcome(o1)
        store.save_outcome(o2)

        pairs = store.get_decision_outcome_pairs()
        assert len(pairs) == 2
        assert pairs[0][0].decision_id == "dec_002"
        assert pairs[1][0].decision_id == "dec_001"


class TestUpdateDecision:
    """决策日志更新"""

    def test_update_decision_execution_status(self, tmp_path):
        """更新决策的执行状态"""
        store = EvolutionStore(tmp_path)
        from dataclasses import replace

        decision = _make_decision("dec_001", execution_status="pending")
        store.save_decision(decision)

        updated = replace(
            decision, execution_status="executed", recommendation_accepted=True
        )
        result = store.update_decision(updated)

        assert result is True
        found = store.get_decision_by_id("dec_001")
        assert found is not None
        assert found.execution_status == "executed"
        assert found.recommendation_accepted is True

    def test_update_preserves_other_fields(self, tmp_path):
        """更新后其他字段保持不变"""
        store = EvolutionStore(tmp_path)
        from dataclasses import replace

        decision = _make_decision("dec_001", execution_status="pending")
        store.save_decision(decision)

        updated = replace(decision, execution_status="skipped")
        store.update_decision(updated)

        found = store.get_decision_by_id("dec_001")
        assert found is not None
        assert found.decision_id == "dec_001"
        assert found.decision_type == decision.decision_type
        assert found.recommendation_text == decision.recommendation_text
        assert found.session_key == decision.session_key

    def test_update_nonexistent_decision_returns_false(self, tmp_path):
        """更新不存在的决策返回False"""
        store = EvolutionStore(tmp_path)
        decision = _make_decision("dec_nonexistent")

        result = store.update_decision(decision)
        assert result is False


class TestPersistence:
    """跨实例持久化"""

    def test_data_persists_across_instances(self, tmp_path):
        """数据在不同EvolutionStore实例间持久化"""
        store1 = EvolutionStore(tmp_path)
        decision = _make_decision("dec_persist")
        outcome = _make_outcome(
            "out_persist",
            decision_id="dec_persist",
            outcome_timestamp=datetime(2026, 5, 2),
        )
        store1.save_decision(decision)
        store1.save_outcome(outcome)

        store2 = EvolutionStore(tmp_path)
        result = store2.get_decision_by_id("dec_persist")
        assert result is not None
        assert result.decision_id == "dec_persist"

        outcomes = store2.query_outcomes(decision_id="dec_persist")
        assert len(outcomes) == 1
        assert outcomes[0].outcome_id == "out_persist"

    def test_parquet_file_structure(self, tmp_path):
        """验证Parquet文件按月分片存储"""
        store = EvolutionStore(tmp_path)

        d1 = _make_decision("dec_05", timestamp=datetime(2026, 5, 1))
        d2 = _make_decision("dec_06", timestamp=datetime(2026, 6, 1))
        store.save_decision(d1)
        store.save_decision(d2)

        may_file = tmp_path / "decisions" / "2026-05" / "decisions_2026-05.parquet"
        june_file = tmp_path / "decisions" / "2026-06" / "decisions_2026-06.parquet"

        assert may_file.exists()
        assert june_file.exists()

    def test_outcome_file_structure(self, tmp_path):
        """验证结果记录Parquet文件按月分片存储"""
        store = EvolutionStore(tmp_path)

        o1 = _make_outcome("out_05", outcome_timestamp=datetime(2026, 5, 1))
        o2 = _make_outcome("out_06", outcome_timestamp=datetime(2026, 6, 1))
        store.save_outcome(o1)
        store.save_outcome(o2)

        may_file = tmp_path / "outcomes" / "2026-05" / "outcomes_2026-05.parquet"
        june_file = tmp_path / "outcomes" / "2026-06" / "outcomes_2026-06.parquet"

        assert may_file.exists()
        assert june_file.exists()

    def test_chinese_text_preserved(self, tmp_path):
        """验证中文文本在Parquet存储后正确保留"""
        store = EvolutionStore(tmp_path)
        decision = DecisionLog(
            decision_id="dec_cn",
            timestamp=datetime(2026, 5, 1, 10, 0, 0),
            runner_state={"vdot": 45.0},
            decision_type=DecisionType.RECOVERY_SUGGESTION,
            tool_call_chain=[],
            prediction_snapshot=None,
            recommendation_text="建议休息一天，补充水分",
            execution_status="executed",
            recommendation_accepted=True,
            session_key="session_cn",
        )
        store.save_decision(decision)

        result = store.get_decision_by_id("dec_cn")
        assert result is not None
        assert result.recommendation_text == "建议休息一天，补充水分"

    def test_runner_state_preserved(self, tmp_path):
        """验证runner_state字典在Parquet存储后正确保留"""
        store = EvolutionStore(tmp_path)
        decision = _make_decision("dec_state")
        store.save_decision(decision)

        result = store.get_decision_by_id("dec_state")
        assert result is not None
        assert result.runner_state == {
            "vdot": 45.0,
            "ctl": 50.0,
            "atl": 40.0,
            "tsb": 10.0,
        }

    def test_tool_call_chain_preserved(self, tmp_path):
        """验证tool_call_chain列表在Parquet存储后正确保留"""
        store = EvolutionStore(tmp_path)
        decision = DecisionLog(
            decision_id="dec_chain",
            timestamp=datetime(2026, 5, 1, 10, 0, 0),
            runner_state={"vdot": 45.0},
            decision_type=DecisionType.TRAINING_ADVICE,
            tool_call_chain=[
                {"tool": "get_vdot", "arguments": {"days": 30}},
                {"tool": "suggest_training", "arguments": {"type": "easy"}},
            ],
            prediction_snapshot=None,
            recommendation_text="建议轻松跑",
            execution_status="pending",
            recommendation_accepted=None,
            session_key="session_chain",
        )
        store.save_decision(decision)

        result = store.get_decision_by_id("dec_chain")
        assert result is not None
        assert len(result.tool_call_chain) == 2
        assert result.tool_call_chain[0]["tool"] == "get_vdot"
        assert result.tool_call_chain[1]["arguments"] == {"type": "easy"}


class TestEvolutionStoreV024:
    """EvolutionStore v0.24校准/参数持久化方法测试"""

    def test_save_and_load_calibration_profile(self, tmp_path):
        store = EvolutionStore(tmp_path)
        profile = CalibrationProfile(
            model_type="vdot",
            scale=0.95,
            last_updated=datetime(2026, 5, 20, 10, 0, 0),
            sample_count=15,
            mae_before=2.5,
            mae_after=1.8,
        )
        store.save_calibration_profile(profile)
        loaded = store.load_calibration_profile("vdot")
        assert loaded is not None
        assert loaded.model_type == "vdot"
        assert loaded.scale == 0.95
        assert loaded.sample_count == 15

    def test_load_calibration_profile_not_found(self, tmp_path):
        store = EvolutionStore(tmp_path)
        result = store.load_calibration_profile("nonexistent")
        assert result is None

    def test_save_calibration_creates_directory(self, tmp_path):
        store = EvolutionStore(tmp_path)
        profile = CalibrationProfile(model_type="vdot")
        store.save_calibration_profile(profile)
        assert (tmp_path / "calibrations").exists()

    def test_get_prediction_actual_pairs_vdot(self, tmp_path):
        store = EvolutionStore(tmp_path)
        decision = DecisionLog(
            decision_id="dec_001",
            timestamp=datetime(2026, 5, 1, 10, 0, 0),
            runner_state={"vdot": 45.0},
            decision_type=DecisionType.TRAINING_ADVICE,
            tool_call_chain=[],
            prediction_snapshot={"predicted_vdot": 46.0},
            recommendation_text=None,
            execution_status="executed",
            recommendation_accepted=None,
            session_key="",
        )
        outcome = OutcomeRecord(
            outcome_id="out_001",
            decision_id="dec_001",
            outcome_timestamp=datetime(2026, 5, 8, 10, 0, 0),
            actual_vdot=46.5,
            actual_injury=False,
            execution_fidelity=0.85,
            user_feedback_score=None,
            user_feedback_text=None,
            prediction_error=None,
            prediction_direction=None,
            session_id=None,
        )
        store.save_decision(decision)
        store.save_outcome(outcome)
        pairs = store.get_prediction_actual_pairs("vdot", min_count=1)
        assert len(pairs) == 1
        assert pairs[0] == (46.0, 46.5)

    def test_get_prediction_actual_pairs_insufficient_data(self, tmp_path):
        store = EvolutionStore(tmp_path)
        pairs = store.get_prediction_actual_pairs("vdot", min_count=10)
        assert pairs == []

    def test_get_prediction_actual_pairs_injury(self, tmp_path):
        store = EvolutionStore(tmp_path)
        decision = DecisionLog(
            decision_id="dec_002",
            timestamp=datetime(2026, 5, 1, 10, 0, 0),
            runner_state={"vdot": 45.0},
            decision_type=DecisionType.RECOVERY_SUGGESTION,
            tool_call_chain=[],
            prediction_snapshot={"injury_risk_probability": 0.3},
            recommendation_text=None,
            execution_status="executed",
            recommendation_accepted=None,
            session_key="",
        )
        outcome = OutcomeRecord(
            outcome_id="out_002",
            decision_id="dec_002",
            outcome_timestamp=datetime(2026, 5, 8, 10, 0, 0),
            actual_vdot=None,
            actual_injury=True,
            execution_fidelity=None,
            user_feedback_score=None,
            user_feedback_text=None,
            prediction_error=None,
            prediction_direction=None,
            session_id=None,
        )
        store.save_decision(decision)
        store.save_outcome(outcome)
        pairs = store.get_prediction_actual_pairs("injury", min_count=1)
        assert len(pairs) == 1
        assert pairs[0] == (0.3, 1.0)

    def test_save_and_load_model_params(self, tmp_path):
        store = EvolutionStore(tmp_path)
        params = {"tau_fitness": 44.0, "k1": 0.00361}
        store.save_model_params("vdot", params)
        loaded = store.load_model_params("vdot")
        assert loaded is not None
        assert loaded["tau_fitness"] == 44.0
        assert loaded["k1"] == 0.00361

    def test_load_model_params_not_found(self, tmp_path):
        store = EvolutionStore(tmp_path)
        result = store.load_model_params("nonexistent")
        assert result is None


class TestEvolutionStoreV025:
    """EvolutionStore v0.25扩展方法测试"""

    def test_save_and_load_prompt_tuning_params(self, tmp_path: Path) -> None:
        """测试提示调优参数读写"""
        from src.core.evolution.evolution_store import EvolutionStore
        from src.core.evolution.models import PromptTuningParams

        store = EvolutionStore(tmp_path)
        params = PromptTuningParams(
            tone_intensity=0.6,
            detail_level_score=0.4,
            recommendation_aggressiveness=0.7,
            data_driven_weight=0.3,
            update_count=3,
        )
        store.save_prompt_tuning_params(params)
        loaded = store.load_prompt_tuning_params()
        assert loaded is not None
        assert loaded.tone_intensity == 0.6
        assert loaded.recommendation_aggressiveness == 0.7
        assert loaded.update_count == 3

    def test_load_prompt_tuning_params_file_not_exist(self, tmp_path: Path) -> None:
        """测试加载不存在的提示调优参数返回None"""
        from src.core.evolution.evolution_store import EvolutionStore

        store = EvolutionStore(tmp_path)
        result = store.load_prompt_tuning_params()
        assert result is None

    def test_save_and_load_trigger_state(self, tmp_path: Path) -> None:
        """测试触发器状态读写"""
        from src.core.evolution.evolution_store import EvolutionStore

        store = EvolutionStore(tmp_path)
        store.save_trigger_state("last_incremental_count", 156)
        store.save_trigger_state("last_monthly_report", "2026-05")
        value = store.load_trigger_state("last_incremental_count")
        assert value == 156
        month = store.load_trigger_state("last_monthly_report")
        assert month == "2026-05"

    def test_load_trigger_state_key_not_exist(self, tmp_path: Path) -> None:
        """测试加载不存在的触发器状态键返回None"""
        from src.core.evolution.evolution_store import EvolutionStore

        store = EvolutionStore(tmp_path)
        store.save_trigger_state("some_key", "some_value")
        result = store.load_trigger_state("nonexistent_key")
        assert result is None

    def test_load_trigger_state_file_not_exist(self, tmp_path: Path) -> None:
        """测试trigger_state.json不存在时返回None"""
        from src.core.evolution.evolution_store import EvolutionStore

        store = EvolutionStore(tmp_path)
        result = store.load_trigger_state("last_incremental_count")
        assert result is None

    def test_count_decisions_empty(self, tmp_path: Path) -> None:
        """测试空数据目录下count_decisions返回0"""
        from src.core.evolution.evolution_store import EvolutionStore

        store = EvolutionStore(tmp_path)
        assert store.count_decisions() == 0

    def test_count_decisions_with_data(self, tmp_path: Path) -> None:
        """测试有数据时count_decisions返回正确计数"""
        from src.core.evolution.evolution_store import EvolutionStore
        from src.core.evolution.models import DecisionLog
        from src.core.transparency.models import DecisionType

        store = EvolutionStore(tmp_path)
        now = datetime.now()
        for i in range(5):
            decision = DecisionLog(
                decision_id=f"dec_{i:03d}",
                timestamp=now,
                runner_state={"vdot": 45.0},
                decision_type=DecisionType.TRAINING_ADVICE,
                tool_call_chain=[],
                prediction_snapshot=None,
                recommendation_text="test",
                execution_status="executed",
                recommendation_accepted=True,
                session_key="test_session",
            )
            store.save_decision(decision)
        assert store.count_decisions() == 5

    def test_get_decision_outcome_pairs_days_parameter(self, tmp_path: Path) -> None:
        """测试get_decision_outcome_pairs的days参数限制查询范围"""
        from src.core.evolution.evolution_store import EvolutionStore
        from src.core.evolution.models import DecisionLog, OutcomeRecord
        from src.core.transparency.models import DecisionType

        store = EvolutionStore(tmp_path)
        now = datetime.now()
        decision = DecisionLog(
            decision_id="dec_days_001",
            timestamp=now,
            runner_state={"vdot": 45.0},
            decision_type=DecisionType.TRAINING_ADVICE,
            tool_call_chain=[],
            prediction_snapshot=None,
            recommendation_text="test",
            execution_status="executed",
            recommendation_accepted=True,
            session_key="test_session",
        )
        store.save_decision(decision)
        outcome = OutcomeRecord(
            outcome_id="out_days_001",
            decision_id="dec_days_001",
            outcome_timestamp=now,
            actual_vdot=45.5,
            actual_injury=False,
            execution_fidelity=0.9,
            user_feedback_score=4,
            user_feedback_text=None,
            prediction_error=0.01,
            prediction_direction="over",
            session_id="test_session",
        )
        store.save_outcome(outcome)
        pairs = store.get_decision_outcome_pairs(days=90)
        assert len(pairs) >= 1
        pairs_recent = store.get_decision_outcome_pairs(days=1)
        assert len(pairs_recent) >= 1

    def test_get_prediction_actual_pairs_days_parameter(self, tmp_path: Path) -> None:
        """测试get_prediction_actual_pairs的days参数"""
        from src.core.evolution.evolution_store import EvolutionStore
        from src.core.evolution.models import DecisionLog, OutcomeRecord
        from src.core.transparency.models import DecisionType

        store = EvolutionStore(tmp_path)
        now = datetime.now()
        decision = DecisionLog(
            decision_id="dec_pred_001",
            timestamp=now,
            runner_state={"vdot": 45.0},
            decision_type=DecisionType.TRAINING_ADVICE,
            tool_call_chain=[],
            prediction_snapshot={"predicted_vdot": 45.2},
            recommendation_text="test",
            execution_status="executed",
            recommendation_accepted=True,
            session_key="test_session",
        )
        store.save_decision(decision)
        outcome = OutcomeRecord(
            outcome_id="out_pred_001",
            decision_id="dec_pred_001",
            outcome_timestamp=now,
            actual_vdot=45.5,
            actual_injury=False,
            execution_fidelity=0.9,
            user_feedback_score=4,
            user_feedback_text=None,
            prediction_error=0.01,
            prediction_direction="over",
            session_id="test_session",
        )
        store.save_outcome(outcome)
        pairs = store.get_prediction_actual_pairs("vdot", min_count=1, days=90)
        assert len(pairs) >= 1

    def test_tuning_dir_auto_created(self, tmp_path: Path) -> None:
        """测试tuning/目录在首次写入时自动创建"""
        from src.core.evolution.evolution_store import EvolutionStore
        from src.core.evolution.models import PromptTuningParams

        store = EvolutionStore(tmp_path)
        tuning_dir = tmp_path / "tuning"
        assert not tuning_dir.exists()
        params = PromptTuningParams.default()
        store.save_prompt_tuning_params(params)
        assert tuning_dir.exists()
