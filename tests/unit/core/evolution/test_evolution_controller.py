"""EvolutionController单元测试"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from src.core.evolution.config import EvolutionConfig
from src.core.evolution.evolution_controller import EvolutionController
from src.core.evolution.models import (
    EvolutionAction,
    PromptTuningParams,
    TriggerCheckResult,
)


@pytest.fixture
def mock_store() -> MagicMock:
    """创建Mock EvolutionStore"""
    store = MagicMock()
    store.get_prediction_actual_pairs.return_value = []
    store.get_decision_outcome_pairs.return_value = []
    store.count_decisions.return_value = 0
    store.load_trigger_state.return_value = None
    store.save_trigger_state.return_value = None
    store.save_model_params.return_value = None
    return store


@pytest.fixture
def mock_calibration_engine() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_model_evolver() -> MagicMock:
    evolver = MagicMock()
    evolver.evolve_model.return_value = MagicMock(
        mae_before=0.05, mae_after=0.03, _raw_param_changes={"tau_fitness": 42}
    )
    evolver.apply_params_to_instance.return_value = None
    return evolver


@pytest.fixture
def mock_prompt_tuner() -> MagicMock:
    tuner = MagicMock()
    tuner.auto_adjust_on_rejection.return_value = PromptTuningParams.default()
    tuner.get_params.return_value = PromptTuningParams.default()
    return tuner


@pytest.fixture
def mock_evolution_reporter() -> MagicMock:
    reporter = MagicMock()
    reporter.generate_report.return_value = MagicMock(month="2026-05")
    return reporter


@pytest.fixture
def controller(
    mock_store: MagicMock,
    mock_calibration_engine: MagicMock,
    mock_model_evolver: MagicMock,
    mock_prompt_tuner: MagicMock,
    mock_evolution_reporter: MagicMock,
) -> EvolutionController:
    config = EvolutionConfig(data_dir="/tmp/test_evolution")
    return EvolutionController(
        store=mock_store,
        calibration_engine=mock_calibration_engine,
        model_evolver=mock_model_evolver,
        prompt_tuner=mock_prompt_tuner,
        evolution_reporter=mock_evolution_reporter,
        config=config,
    )


class TestCheckTriggers:
    """check_triggers()测试"""

    def test_no_triggers_when_insufficient_data(
        self, controller: EvolutionController, mock_store: MagicMock
    ) -> None:
        """数据不足时无触发"""
        mock_store.get_prediction_actual_pairs.return_value = []
        mock_store.get_decision_outcome_pairs.return_value = []
        mock_store.count_decisions.return_value = 0
        # 当月已生成报告，不会触发月度复盘
        current_month = datetime.now().strftime("%Y-%m")
        mock_store.load_trigger_state.side_effect = lambda key: (
            current_month if key == "last_monthly_report" else None
        )

        result = controller.check_triggers()
        assert isinstance(result, TriggerCheckResult)
        assert len(result.triggered_actions) == 0
        assert len(result.skipped_conditions) > 0

    def test_vdot_error_trigger(
        self, controller: EvolutionController, mock_store: MagicMock
    ) -> None:
        """VDOT预测误差连续3次>5%时触发retrain_model"""
        mock_store.get_prediction_actual_pairs.return_value = [
            (47.5, 45.0),  # 误差5.6%
            (48.0, 45.0),  # 误差6.7%
            (47.0, 44.5),  # 误差5.6%
        ]
        mock_store.get_decision_outcome_pairs.return_value = []

        result = controller.check_triggers()
        vdot_actions = [
            a for a in result.triggered_actions if a.action_type == "retrain_model"
        ]
        assert len(vdot_actions) == 1
        assert vdot_actions[0].target_model_type == "vdot"
        assert vdot_actions[0].priority == "high"

    def test_rejection_trigger(
        self, controller: EvolutionController, mock_store: MagicMock
    ) -> None:
        """连续2次拒绝推荐时触发adjust_strategy"""
        mock_store.get_prediction_actual_pairs.return_value = []
        mock_outcome_1 = MagicMock(recommendation_accepted=False)
        mock_outcome_2 = MagicMock(recommendation_accepted=False)
        mock_store.get_decision_outcome_pairs.return_value = [
            (MagicMock(), mock_outcome_1),
            (MagicMock(), mock_outcome_2),
        ]

        result = controller.check_triggers()
        rejection_actions = [
            a for a in result.triggered_actions if a.action_type == "adjust_strategy"
        ]
        assert len(rejection_actions) == 1
        assert rejection_actions[0].target_model_type == "prompt"

    def test_new_data_trigger(
        self, controller: EvolutionController, mock_store: MagicMock
    ) -> None:
        """新数据积累>=50条时触发incremental_learn"""
        mock_store.get_prediction_actual_pairs.return_value = []
        mock_store.get_decision_outcome_pairs.return_value = []
        mock_store.count_decisions.return_value = 100
        mock_store.load_trigger_state.return_value = 30  # 上次30条，新增70条

        result = controller.check_triggers()
        new_data_actions = [
            a for a in result.triggered_actions if a.action_type == "incremental_learn"
        ]
        assert len(new_data_actions) == 1
        assert new_data_actions[0].target_model_type == "all"

    def test_monthly_review_trigger(
        self, controller: EvolutionController, mock_store: MagicMock
    ) -> None:
        """当月未生成报告时触发generate_report"""
        mock_store.get_prediction_actual_pairs.return_value = []
        mock_store.get_decision_outcome_pairs.return_value = []
        mock_store.count_decisions.return_value = 0
        mock_store.load_trigger_state.return_value = None

        result = controller.check_triggers()
        monthly_actions = [
            a for a in result.triggered_actions if a.action_type == "generate_report"
        ]
        assert len(monthly_actions) == 1
        assert monthly_actions[0].priority == "low"

    def test_check_triggers_performance_budget(
        self, controller: EvolutionController, mock_store: MagicMock
    ) -> None:
        """check_triggers()性能预算<50ms"""
        import time

        mock_store.get_prediction_actual_pairs.return_value = []
        mock_store.get_decision_outcome_pairs.return_value = []
        mock_store.count_decisions.return_value = 0

        start = time.monotonic()
        controller.check_triggers()
        elapsed_ms = (time.monotonic() - start) * 1000
        assert elapsed_ms < 50, f"check_triggers()耗时{elapsed_ms:.1f}ms超过50ms预算"


class TestExecuteAction:
    """execute_action()测试"""

    def test_execute_retrain_model_persist_first(
        self,
        controller: EvolutionController,
        mock_model_evolver: MagicMock,
        mock_store: MagicMock,
    ) -> None:
        """retrain_model动作先持久化后生效"""
        action = EvolutionAction(
            action_id="test_exec_001",
            action_type="retrain_model",
            trigger_reason="VDOT误差",
            trigger_condition={},
            target_model_type="vdot",
            priority="high",
            created_at=datetime.now(),
        )

        result = controller.execute_action(action)
        assert result.executed is True
        mock_store.save_model_params.assert_called_once()
        mock_model_evolver.apply_params_to_instance.assert_called_once_with("vdot")

    def test_execute_retrain_model_persist_failure(
        self,
        controller: EvolutionController,
        mock_model_evolver: MagicMock,
        mock_store: MagicMock,
    ) -> None:
        """retrain_model持久化失败时不修改实例属性"""
        mock_store.save_model_params.side_effect = OSError("磁盘写入失败")

        action = EvolutionAction(
            action_id="test_exec_002",
            action_type="retrain_model",
            trigger_reason="VDOT误差",
            trigger_condition={},
            target_model_type="vdot",
            priority="high",
            created_at=datetime.now(),
        )

        result = controller.execute_action(action)
        assert result.executed is True
        assert "持久化失败" in str(result.execution_result)
        mock_model_evolver.apply_params_to_instance.assert_not_called()

    def test_execute_adjust_strategy(
        self,
        controller: EvolutionController,
        mock_prompt_tuner: MagicMock,
    ) -> None:
        """adjust_strategy动作调用PromptTuner"""
        action = EvolutionAction(
            action_id="test_exec_003",
            action_type="adjust_strategy",
            trigger_reason="连续拒绝",
            trigger_condition={},
            target_model_type="prompt",
            priority="medium",
            created_at=datetime.now(),
        )

        result = controller.execute_action(action)
        assert result.executed is True
        mock_prompt_tuner.auto_adjust_on_rejection.assert_called_once()

    def test_execute_incremental_learn_updates_trigger_state(
        self,
        controller: EvolutionController,
        mock_model_evolver: MagicMock,
        mock_store: MagicMock,
    ) -> None:
        """incremental_learn完成后更新trigger_state"""
        mock_store.count_decisions.return_value = 100

        action = EvolutionAction(
            action_id="test_exec_004",
            action_type="incremental_learn",
            trigger_reason="新数据积累",
            trigger_condition={},
            target_model_type="all",
            priority="medium",
            created_at=datetime.now(),
        )

        result = controller.execute_action(action)
        assert result.executed is True
        mock_store.save_trigger_state.assert_called_with("last_incremental_count", 100)

    def test_execute_generate_report(
        self,
        controller: EvolutionController,
        mock_evolution_reporter: MagicMock,
    ) -> None:
        """generate_report动作调用EvolutionReporter"""
        action = EvolutionAction(
            action_id="test_exec_005",
            action_type="generate_report",
            trigger_reason="月度复盘",
            trigger_condition={},
            target_model_type="none",
            priority="low",
            created_at=datetime.now(),
        )

        result = controller.execute_action(action)
        assert result.executed is True
        mock_evolution_reporter.generate_report.assert_called_once()


class TestLoadLastIncrementalCount:
    """_load_last_incremental_count()测试"""

    def test_returns_zero_when_no_state(
        self, controller: EvolutionController, mock_store: MagicMock
    ) -> None:
        """首次调用时返回0"""
        mock_store.load_trigger_state.return_value = None
        assert controller._load_last_incremental_count() == 0

    def test_returns_stored_value(
        self, controller: EvolutionController, mock_store: MagicMock
    ) -> None:
        """返回已存储的值"""
        mock_store.load_trigger_state.return_value = 156
        assert controller._load_last_incremental_count() == 156

    def test_returns_zero_for_non_int_value(
        self, controller: EvolutionController, mock_store: MagicMock
    ) -> None:
        """存储值非int时返回0"""
        mock_store.load_trigger_state.return_value = "invalid"
        assert controller._load_last_incremental_count() == 0
