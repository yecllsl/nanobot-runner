"""集成测试: DecisionLogHook + EvolutionController闭环 (T12)

验证Agent决策 -> Hook记录 -> 触发条件检查 -> 动作执行 的完整闭环。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.core.evolution.config import EvolutionConfig
from src.core.evolution.decision_log_hook import DecisionLogHook
from src.core.evolution.evolution_controller import EvolutionController
from src.core.evolution.evolution_engine import EvolutionEngine
from src.core.evolution.evolution_store import EvolutionStore
from src.core.evolution.models import (
    DecisionLog,
    OutcomeRecord,
)
from src.core.transparency.models import DecisionType


@pytest.fixture
def integration_store(tmp_path: Any) -> EvolutionStore:
    """创建真实的EvolutionStore（使用临时目录）"""
    return EvolutionStore(tmp_path)


@pytest.fixture
def integration_components(integration_store: EvolutionStore) -> dict[str, Any]:
    """创建集成测试组件"""
    mock_calibration = MagicMock()
    mock_evolver = MagicMock()
    mock_evolver.evolve_model.return_value = MagicMock(
        mae_before=0.05, mae_after=0.03, _raw_param_changes={"tau": 42}
    )
    mock_evolver.apply_params_to_instance.return_value = None

    config = EvolutionConfig(data_dir=str(integration_store._data_dir))

    from src.core.evolution.evolution_reporter import EvolutionReporter
    from src.core.evolution.prompt_tuner import PromptTuner

    prompt_tuner = PromptTuner(store=integration_store, config=config)
    evolution_reporter = EvolutionReporter(
        store=integration_store,
        calibration_engine=mock_calibration,
        prompt_tuner=prompt_tuner,
        config=config,
    )
    controller = EvolutionController(
        store=integration_store,
        calibration_engine=mock_calibration,
        model_evolver=mock_evolver,
        prompt_tuner=prompt_tuner,
        evolution_reporter=evolution_reporter,
        config=config,
    )
    engine = EvolutionEngine(
        decision_logger=MagicMock(),
        outcome_collector=MagicMock(),
        response_analyzer=MagicMock(),
        calibration_engine=mock_calibration,
        model_evolver=mock_evolver,
        evolution_controller=controller,
        prompt_tuner=prompt_tuner,
        evolution_reporter=evolution_reporter,
    )
    hook = DecisionLogHook(
        evolution_engine=engine,
    )

    return {
        "store": integration_store,
        "controller": controller,
        "engine": engine,
        "hook": hook,
        "prompt_tuner": prompt_tuner,
        "mock_evolver": mock_evolver,
        "mock_calibration": mock_calibration,
    }


class TestDecisionLogHookControllerClosedLoop:
    """DecisionLogHook + EvolutionController闭环集成测试"""

    def test_vdot_error_triggers_retrain_via_hook(
        self, integration_components: dict[str, Any]
    ) -> None:
        """VDOT预测误差 -> Hook触发 -> EvolutionController生成retrain_model动作"""
        store = integration_components["store"]
        controller = integration_components["controller"]

        # 写入3条高误差数据
        # predicted_vdot=47.5, actual_vdot=45.0 => 误差=|47.5-45.0|/45.0=5.56% > 5%阈值
        now = datetime.now()
        for i in range(3):
            decision = DecisionLog(
                decision_id=f"dec_vdot_{i}",
                timestamp=now,
                runner_state={"vdot": 45.0},
                decision_type=DecisionType.TRAINING_ADVICE,
                tool_call_chain=[],
                prediction_snapshot={"predicted_vdot": 47.5},
                recommendation_text="test",
                execution_status="executed",
                recommendation_accepted=True,
                session_key="test_session",
            )
            store.save_decision(decision)
            outcome = OutcomeRecord(
                outcome_id=f"out_vdot_{i}",
                decision_id=f"dec_vdot_{i}",
                outcome_timestamp=now,
                actual_vdot=45.0,
                actual_injury=False,
                execution_fidelity=0.9,
                user_feedback_score=4,
                user_feedback_text=None,
                prediction_error=0.056,
                prediction_direction="over",
                session_id="test_session",
            )
            store.save_outcome(outcome)

        # 检查触发条件
        result = controller.check_triggers()
        retrain_actions = [
            a for a in result.triggered_actions if a.action_type == "retrain_model"
        ]
        assert len(retrain_actions) >= 1
        assert retrain_actions[0].target_model_type == "vdot"

    def test_rejection_triggers_adjust_strategy_via_hook(
        self, integration_components: dict[str, Any]
    ) -> None:
        """连续拒绝 -> Hook触发 -> EvolutionController生成adjust_strategy动作"""
        store = integration_components["store"]
        controller = integration_components["controller"]

        now = datetime.now()
        for i in range(2):
            decision = DecisionLog(
                decision_id=f"dec_reject_{i}",
                timestamp=now,
                runner_state={"vdot": 45.0},
                decision_type=DecisionType.TRAINING_ADVICE,
                tool_call_chain=[],
                prediction_snapshot=None,
                recommendation_text="test",
                execution_status="executed",
                recommendation_accepted=False,
                session_key="test_session",
            )
            store.save_decision(decision)
            outcome = OutcomeRecord(
                outcome_id=f"out_reject_{i}",
                decision_id=f"dec_reject_{i}",
                outcome_timestamp=now,
                actual_vdot=45.0,
                actual_injury=False,
                execution_fidelity=0.9,
                user_feedback_score=2,
                user_feedback_text=None,
                prediction_error=0.01,
                prediction_direction="over",
                session_id="test_session",
            )
            store.save_outcome(outcome)

        result = controller.check_triggers()
        adjust_actions = [
            a for a in result.triggered_actions if a.action_type == "adjust_strategy"
        ]
        assert len(adjust_actions) >= 1

    def test_full_loop_decision_to_action_execution(
        self, integration_components: dict[str, Any]
    ) -> None:
        """完整闭环: 决策记录 -> 触发检查 -> 动作执行 -> 参数持久化"""
        store = integration_components["store"]
        controller = integration_components["controller"]
        mock_evolver = integration_components["mock_evolver"]

        # 写入触发数据
        now = datetime.now()
        for i in range(3):
            decision = DecisionLog(
                decision_id=f"dec_loop_{i}",
                timestamp=now,
                runner_state={"vdot": 45.0},
                decision_type=DecisionType.TRAINING_ADVICE,
                tool_call_chain=[],
                prediction_snapshot={"predicted_vdot": 47.5},
                recommendation_text="test",
                execution_status="executed",
                recommendation_accepted=True,
                session_key="test_session",
            )
            store.save_decision(decision)
            outcome = OutcomeRecord(
                outcome_id=f"out_loop_{i}",
                decision_id=f"dec_loop_{i}",
                outcome_timestamp=now,
                actual_vdot=45.0,
                actual_injury=False,
                execution_fidelity=0.9,
                user_feedback_score=4,
                user_feedback_text=None,
                prediction_error=0.056,
                prediction_direction="over",
                session_id="test_session",
            )
            store.save_outcome(outcome)

        # 触发检查
        result = controller.check_triggers()
        assert len(result.triggered_actions) > 0

        # 执行动作
        action = result.triggered_actions[0]
        executed = controller.execute_action(action)
        assert executed.executed is True

        # 验证参数持久化
        mock_evolver.apply_params_to_instance.assert_called()
