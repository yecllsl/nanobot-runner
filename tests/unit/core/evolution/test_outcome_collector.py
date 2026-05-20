# OutcomeCollector 结果回填收集器单元测试
# 覆盖fidelity计算、预测误差、用户反馈、反馈提示、结果查询等场景

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from src.core.evolution.decision_logger import DecisionLogger
from src.core.evolution.evolution_store import EvolutionStore
from src.core.evolution.models import (
    DecisionLog,
    PredictionAccuracyStats,
)
from src.core.evolution.outcome_collector import (
    OutcomeCollector,
    PlanExecutionData,
    PlanExecutionDataAdapter,
    calculate_fidelity,
    calculate_prediction_error,
)
from src.core.plan.ask_user_confirm import ConfirmPrompt, ConfirmScenario
from src.core.transparency.models import DecisionType

# ============================================================
# 辅助函数
# ============================================================


def _make_decision(
    decision_id: str = "dec_001",
    timestamp: datetime | None = None,
    decision_type: DecisionType = DecisionType.TRAINING_ADVICE,
    execution_status: str = "pending",
    prediction_snapshot: dict | None = None,
    tool_call_chain: list[dict] | None = None,
    recommendation_text: str | None = "建议轻松跑",
    session_key: str = "session_001",
) -> DecisionLog:
    """创建测试用DecisionLog辅助函数"""
    return DecisionLog(
        decision_id=decision_id,
        timestamp=timestamp or datetime(2026, 5, 1, 10, 0, 0),
        runner_state={"vdot": 45.0, "ctl": 50.0, "atl": 40.0, "tsb": 10.0},
        decision_type=decision_type,
        tool_call_chain=tool_call_chain
        or [{"tool": "suggest_training", "arguments": {}}],
        prediction_snapshot=prediction_snapshot,
        recommendation_text=recommendation_text,
        execution_status=execution_status,
        recommendation_accepted=None,
        session_key=session_key,
    )


def _make_collector(
    tmp_path,
    plan_adapter: PlanExecutionDataAdapter | None = None,
) -> tuple[EvolutionStore, DecisionLogger, OutcomeCollector]:
    """创建测试用OutcomeCollector辅助函数

    Returns:
        tuple: (store, logger, collector)
    """
    store = EvolutionStore(tmp_path)
    logger = DecisionLogger(store)
    collector = OutcomeCollector(store, logger, plan_adapter=plan_adapter)
    return store, logger, collector


# ============================================================
# calculate_fidelity 函数测试
# ============================================================


class TestCalculateFidelity:
    """calculate_fidelity函数测试"""

    def test_perfect_execution_returns_one(self):
        """完美执行时fidelity为1.0"""
        data = PlanExecutionData(
            planned_volume_km=40.0,
            actual_volume_km=40.0,
            planned_duration_min=300,
            actual_duration_min=300,
            completion_rate=1.0,
        )
        assert calculate_fidelity(data) == 1.0

    def test_partial_deviation_between_zero_and_one(self):
        """部分偏差时fidelity在0和1之间"""
        data = PlanExecutionData(
            planned_volume_km=40.0,
            actual_volume_km=36.0,
            planned_duration_min=300,
            actual_duration_min=330,
            completion_rate=0.9,
        )
        fidelity = calculate_fidelity(data)
        assert 0.0 < fidelity < 1.0

    def test_large_deviation_clamped_to_zero(self):
        """大偏差时fidelity限制为0"""
        data = PlanExecutionData(
            planned_volume_km=40.0,
            actual_volume_km=0.0,
            planned_duration_min=300,
            actual_duration_min=0,
            completion_rate=0.0,
        )
        fidelity = calculate_fidelity(data)
        assert fidelity == 0.0

    def test_volume_deviation_weight_0_55(self):
        """跑量偏差权重0.55验证"""
        # 仅跑量偏差，时长完美
        data = PlanExecutionData(
            planned_volume_km=40.0,
            actual_volume_km=36.0,  # 偏差10%
            planned_duration_min=300,
            actual_duration_min=300,
            completion_rate=0.9,
        )
        # fidelity = 1 - (0.55 * 0.1 + 0.45 * 0) = 1 - 0.055 = 0.945
        assert calculate_fidelity(data) == pytest.approx(0.945)

    def test_duration_deviation_weight_0_45(self):
        """时长偏差权重0.45验证"""
        # 仅时长偏差，跑量完美
        data = PlanExecutionData(
            planned_volume_km=40.0,
            actual_volume_km=40.0,
            planned_duration_min=300,
            actual_duration_min=330,  # 偏差10%
            completion_rate=1.0,
        )
        # fidelity = 1 - (0.55 * 0 + 0.45 * 0.1) = 1 - 0.045 = 0.955
        assert calculate_fidelity(data) == pytest.approx(0.955)

    def test_zero_planned_volume_returns_one(self):
        """计划跑量为0时返回1.0（无偏差）"""
        data = PlanExecutionData(
            planned_volume_km=0.0,
            actual_volume_km=10.0,
            planned_duration_min=300,
            actual_duration_min=300,
            completion_rate=0.0,
        )
        assert calculate_fidelity(data) == 1.0

    def test_zero_planned_duration_returns_one(self):
        """计划时长为0时返回1.0（无偏差）"""
        data = PlanExecutionData(
            planned_volume_km=40.0,
            actual_volume_km=40.0,
            planned_duration_min=0,
            actual_duration_min=300,
            completion_rate=1.0,
        )
        assert calculate_fidelity(data) == 1.0

    def test_both_planned_zero_returns_one(self):
        """计划跑量和时长均为0时返回1.0"""
        data = PlanExecutionData(
            planned_volume_km=0.0,
            actual_volume_km=0.0,
            planned_duration_min=0,
            actual_duration_min=0,
            completion_rate=0.0,
        )
        assert calculate_fidelity(data) == 1.0


# ============================================================
# calculate_prediction_error 函数测试
# ============================================================


class TestCalculatePredictionError:
    """calculate_prediction_error函数测试"""

    def test_accurate_prediction(self):
        """准确预测：误差0，方向accurate"""
        error, direction = calculate_prediction_error(45.0, 45.0)
        assert error == 0.0
        assert direction == "accurate"

    def test_overestimate(self):
        """高估：预测值超过实际值5%以上"""
        error, direction = calculate_prediction_error(50.0, 45.0)
        assert error == pytest.approx(100.0 * 5.0 / 45.0)
        assert direction == "overestimate"

    def test_underestimate(self):
        """低估：预测值低于实际值5%以上"""
        error, direction = calculate_prediction_error(40.0, 45.0)
        assert error == pytest.approx(100.0 * 5.0 / 45.0)
        assert direction == "underestimate"

    def test_within_5_percent_is_accurate(self):
        """5%以内视为accurate"""
        # 预测值 = 实际值 * 1.04，在5%阈值内
        error, direction = calculate_prediction_error(46.8, 45.0)
        assert direction == "accurate"

    def test_exactly_5_percent_over_is_accurate(self):
        """恰好5%高估仍为accurate（>1.05才为overestimate）"""
        error, direction = calculate_prediction_error(47.25, 45.0)  # 45 * 1.05 = 47.25
        assert direction == "accurate"

    def test_slightly_over_5_percent_is_overestimate(self):
        """略超5%即为overestimate"""
        error, direction = calculate_prediction_error(47.26, 45.0)  # > 45 * 1.05
        assert direction == "overestimate"

    def test_exactly_5_percent_under_is_accurate(self):
        """恰好5%低估仍为accurate（<0.95才为underestimate）"""
        error, direction = calculate_prediction_error(42.75, 45.0)  # 45 * 0.95 = 42.75
        assert direction == "accurate"

    def test_slightly_under_5_percent_is_underestimate(self):
        """略低于5%即为underestimate"""
        error, direction = calculate_prediction_error(42.74, 45.0)  # < 45 * 0.95
        assert direction == "underestimate"

    def test_zero_actual_and_zero_predicted(self):
        """实际值和预测值均为0时，误差0，方向accurate"""
        error, direction = calculate_prediction_error(0.0, 0.0)
        assert error == 0.0
        assert direction == "accurate"

    def test_zero_actual_positive_predicted(self):
        """实际值为0、预测值为正时，误差100%，方向overestimate"""
        error, direction = calculate_prediction_error(45.0, 0.0)
        assert error == 100.0
        assert direction == "overestimate"

    def test_zero_actual_negative_predicted(self):
        """实际值为0、预测值为负时，误差100%，方向underestimate"""
        error, direction = calculate_prediction_error(-1.0, 0.0)
        assert error == 100.0
        assert direction == "underestimate"


# ============================================================
# check_plan_execution 方法测试
# ============================================================


class TestCheckPlanExecution:
    """check_plan_execution方法测试"""

    def test_with_execution_data_calculates_fidelity(self, tmp_path):
        """有执行数据时计算fidelity"""
        store, logger, _ = _make_collector(tmp_path)

        # 创建带plan_id的决策
        decision = _make_decision(
            "dec_plan_001",
            tool_call_chain=[
                {"tool": "adjust_plan", "arguments": {"plan_id": "plan_001"}}
            ],
        )
        logger.log_decision(decision)

        # Mock plan_adapter返回执行数据
        plan_adapter = MagicMock(spec=PlanExecutionDataAdapter)
        plan_adapter.get_execution_data.return_value = PlanExecutionData(
            planned_volume_km=40.0,
            actual_volume_km=38.0,
            planned_duration_min=300,
            actual_duration_min=310,
            completion_rate=0.95,
        )

        collector = OutcomeCollector(store, logger, plan_adapter=plan_adapter)
        outcome = collector.check_plan_execution("dec_plan_001")

        assert outcome.decision_id == "dec_plan_001"
        assert outcome.execution_fidelity is not None
        assert 0.0 < outcome.execution_fidelity <= 1.0
        # 验证plan_adapter被正确调用
        plan_adapter.get_execution_data.assert_called_once_with("plan_001")

    def test_no_plan_adapter_fidelity_is_none(self, tmp_path):
        """无plan_adapter时fidelity为None"""
        store, logger, collector = _make_collector(tmp_path, plan_adapter=None)

        decision = _make_decision("dec_plan_002")
        logger.log_decision(decision)

        outcome = collector.check_plan_execution("dec_plan_002")

        assert outcome.decision_id == "dec_plan_002"
        assert outcome.execution_fidelity is None

    def test_plan_adapter_returns_none_fidelity_is_none(self, tmp_path):
        """plan_adapter返回None时fidelity为None"""
        store, logger, _ = _make_collector(tmp_path)

        decision = _make_decision(
            "dec_plan_003",
            tool_call_chain=[
                {"tool": "adjust_plan", "arguments": {"plan_id": "plan_003"}}
            ],
        )
        logger.log_decision(decision)

        plan_adapter = MagicMock(spec=PlanExecutionDataAdapter)
        plan_adapter.get_execution_data.return_value = None

        collector = OutcomeCollector(store, logger, plan_adapter=plan_adapter)
        outcome = collector.check_plan_execution("dec_plan_003")

        assert outcome.execution_fidelity is None

    def test_no_plan_id_in_decision_fidelity_is_none(self, tmp_path):
        """决策中无plan_id时fidelity为None"""
        store, logger, _ = _make_collector(tmp_path)

        # tool_call_chain中无plan_id
        decision = _make_decision(
            "dec_plan_004",
            tool_call_chain=[
                {"tool": "suggest_training", "arguments": {"intensity": "easy"}}
            ],
        )
        logger.log_decision(decision)

        plan_adapter = MagicMock(spec=PlanExecutionDataAdapter)

        collector = OutcomeCollector(store, logger, plan_adapter=plan_adapter)
        outcome = collector.check_plan_execution("dec_plan_004")

        assert outcome.execution_fidelity is None
        # plan_adapter不应被调用
        plan_adapter.get_execution_data.assert_not_called()

    def test_nonexistent_decision_raises_value_error(self, tmp_path):
        """决策不存在时抛出ValueError"""
        store, logger, collector = _make_collector(tmp_path)

        with pytest.raises(ValueError, match="决策不存在"):
            collector.check_plan_execution("nonexistent_id")


# ============================================================
# check_prediction_accuracy 方法测试
# ============================================================


class TestCheckPredictionAccuracy:
    """check_prediction_accuracy方法测试"""

    def test_accurate_prediction(self, tmp_path):
        """准确预测：方向为accurate"""
        store, logger, collector = _make_collector(tmp_path)

        decision = _make_decision(
            "dec_pred_001",
            prediction_snapshot={"predicted_vdot": 45.0},
        )
        logger.log_decision(decision)

        outcome, stats = collector.check_prediction_accuracy("dec_pred_001", 45.0)

        assert outcome.actual_vdot == 45.0
        assert outcome.prediction_error == 0.0
        assert outcome.prediction_direction == "accurate"
        assert isinstance(stats, PredictionAccuracyStats)

    def test_overestimate(self, tmp_path):
        """高估预测：方向为overestimate"""
        store, logger, collector = _make_collector(tmp_path)

        decision = _make_decision(
            "dec_pred_002",
            prediction_snapshot={"predicted_vdot": 50.0},
        )
        logger.log_decision(decision)

        outcome, stats = collector.check_prediction_accuracy("dec_pred_002", 45.0)

        assert outcome.prediction_direction == "overestimate"
        assert outcome.prediction_error > 0
        assert outcome.actual_vdot == 45.0

    def test_underestimate(self, tmp_path):
        """低估预测：方向为underestimate"""
        store, logger, collector = _make_collector(tmp_path)

        decision = _make_decision(
            "dec_pred_003",
            prediction_snapshot={"predicted_vdot": 40.0},
        )
        logger.log_decision(decision)

        outcome, stats = collector.check_prediction_accuracy("dec_pred_003", 45.0)

        assert outcome.prediction_direction == "underestimate"
        assert outcome.prediction_error > 0

    def test_no_prediction_snapshot_error_is_none(self, tmp_path):
        """无预测快照时误差和方向为None"""
        store, logger, collector = _make_collector(tmp_path)

        decision = _make_decision("dec_pred_004", prediction_snapshot=None)
        logger.log_decision(decision)

        outcome, stats = collector.check_prediction_accuracy("dec_pred_004", 45.0)

        assert outcome.prediction_error is None
        assert outcome.prediction_direction is None
        assert outcome.actual_vdot == 45.0

    def test_prediction_snapshot_without_predicted_vdot(self, tmp_path):
        """预测快照中无predicted_vdot时误差为None"""
        store, logger, collector = _make_collector(tmp_path)

        decision = _make_decision(
            "dec_pred_005",
            prediction_snapshot={"other_field": 42.0},
        )
        logger.log_decision(decision)

        outcome, stats = collector.check_prediction_accuracy("dec_pred_005", 45.0)

        assert outcome.prediction_error is None
        assert outcome.prediction_direction is None

    def test_accuracy_stats_computed(self, tmp_path):
        """精度统计正确计算"""
        store, logger, collector = _make_collector(tmp_path)

        decision = _make_decision(
            "dec_pred_stats",
            prediction_snapshot={"predicted_vdot": 50.0},
        )
        logger.log_decision(decision)

        _, stats = collector.check_prediction_accuracy("dec_pred_stats", 45.0)

        assert stats.total_pairs >= 1
        assert stats.mae > 0
        assert stats.overestimate_rate > 0

    def test_nonexistent_decision_raises_value_error(self, tmp_path):
        """决策不存在时抛出ValueError"""
        store, logger, collector = _make_collector(tmp_path)

        with pytest.raises(ValueError, match="决策不存在"):
            collector.check_prediction_accuracy("nonexistent_id", 45.0)


# ============================================================
# record_feedback 方法测试
# ============================================================


class TestRecordFeedback:
    """record_feedback方法测试"""

    def test_record_score_and_text(self, tmp_path):
        """记录评分和文本"""
        store, logger, collector = _make_collector(tmp_path)

        decision = _make_decision("dec_fb_001")
        logger.log_decision(decision)

        outcome = collector.record_feedback("dec_fb_001", score=4, text="很有帮助")

        assert outcome.user_feedback_score == 4
        assert outcome.user_feedback_text == "很有帮助"
        assert outcome.decision_id == "dec_fb_001"

    def test_record_score_only(self, tmp_path):
        """仅记录评分，文本为None"""
        store, logger, collector = _make_collector(tmp_path)

        decision = _make_decision("dec_fb_002")
        logger.log_decision(decision)

        outcome = collector.record_feedback("dec_fb_002", score=3)

        assert outcome.user_feedback_score == 3
        assert outcome.user_feedback_text is None

    def test_nonexistent_decision_raises_value_error(self, tmp_path):
        """决策不存在时抛出ValueError"""
        store, logger, collector = _make_collector(tmp_path)

        with pytest.raises(ValueError, match="决策不存在"):
            collector.record_feedback("nonexistent_id", score=3)


# ============================================================
# generate_feedback_prompt 方法测试
# ============================================================


class TestGenerateFeedbackPrompt:
    """generate_feedback_prompt方法测试"""

    def test_generates_confirm_prompt(self, tmp_path):
        """生成ConfirmPrompt"""
        store, logger, collector = _make_collector(tmp_path)

        decision = _make_decision("dec_prompt_001")
        logger.log_decision(decision)

        prompt = collector.generate_feedback_prompt("dec_prompt_001")

        assert isinstance(prompt, ConfirmPrompt)
        assert prompt.scenario == ConfirmScenario.DECISION_FEEDBACK
        assert len(prompt.options) == 5
        assert prompt.metadata["decision_id"] == "dec_prompt_001"

    def test_prompt_contains_decision_info(self, tmp_path):
        """提示包含决策信息"""
        store, logger, collector = _make_collector(tmp_path)

        decision = _make_decision(
            "dec_prompt_002",
            recommendation_text="建议进行间歇训练",
        )
        logger.log_decision(decision)

        prompt = collector.generate_feedback_prompt("dec_prompt_002")

        assert "dec_prompt_002" in prompt.message
        assert "建议进行间歇训练" in prompt.message

    def test_prompt_options_are_1_to_5(self, tmp_path):
        """提示选项为1-5分"""
        store, logger, collector = _make_collector(tmp_path)

        decision = _make_decision("dec_prompt_003")
        logger.log_decision(decision)

        prompt = collector.generate_feedback_prompt("dec_prompt_003")

        keys = [opt.key for opt in prompt.options]
        assert keys == ["1", "2", "3", "4", "5"]
        assert prompt.default_key == "3"

    def test_nonexistent_decision_raises_value_error(self, tmp_path):
        """决策不存在时抛出ValueError"""
        store, logger, collector = _make_collector(tmp_path)

        with pytest.raises(ValueError, match="决策不存在"):
            collector.generate_feedback_prompt("nonexistent_id")


# ============================================================
# get_outcome_by_decision_id 方法测试
# ============================================================


class TestGetOutcomeByDecisionId:
    """get_outcome_by_decision_id方法测试"""

    def test_returns_outcome_when_exists(self, tmp_path):
        """存在时返回结果记录"""
        store, logger, collector = _make_collector(tmp_path)

        decision = _make_decision("dec_get_001")
        logger.log_decision(decision)

        # 先记录反馈以创建outcome
        collector.record_feedback("dec_get_001", score=4)

        outcome = collector.get_outcome_by_decision_id("dec_get_001")
        assert outcome is not None
        assert outcome.decision_id == "dec_get_001"
        assert outcome.user_feedback_score == 4

    def test_returns_none_when_not_exists(self, tmp_path):
        """不存在时返回None"""
        store, logger, collector = _make_collector(tmp_path)

        outcome = collector.get_outcome_by_decision_id("nonexistent")
        assert outcome is None
