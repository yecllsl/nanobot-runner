# create_composite_hook集成测试
# 测试DecisionLogHook在create_composite_hook中的注册行为

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.core.evolution.decision_log_hook import DecisionLogHook
from src.core.transparency import create_composite_hook
from src.core.transparency.error_handling_hook import ErrorHandlingHook
from src.core.transparency.progress_hook import ProgressDisplayHook
from src.core.transparency.streaming_hook import StreamingHook

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_evolution_engine() -> MagicMock:
    """创建模拟的进化引擎实例"""
    engine = MagicMock()
    engine.log_decision = MagicMock()
    engine.decision_logger = MagicMock()
    engine.decision_logger.runner_state_fields = ["ctl", "atl", "tsb"]
    return engine


# ---------------------------------------------------------------------------
# 测试用例
# ---------------------------------------------------------------------------


class TestCompositeHookWithDecisionLog:
    """create_composite_hook中DecisionLogHook注册行为测试"""

    def test_includes_decision_log_hook_when_evolution_engine_provided(
        self, mock_evolution_engine: MagicMock
    ) -> None:
        """传入evolution_engine时，Hook列表应包含DecisionLogHook"""
        hooks = create_composite_hook(evolution_engine=mock_evolution_engine)

        decision_hooks = [h for h in hooks if isinstance(h, DecisionLogHook)]
        assert len(decision_hooks) == 1, "应恰好包含一个DecisionLogHook"

    def test_no_decision_log_hook_when_evolution_engine_not_provided(self) -> None:
        """不传evolution_engine时，Hook列表不应包含DecisionLogHook"""
        hooks = create_composite_hook()

        decision_hooks = [h for h in hooks if isinstance(h, DecisionLogHook)]
        assert len(decision_hooks) == 0, "不应包含DecisionLogHook"

    def test_preserves_original_hooks_when_evolution_engine_provided(
        self, mock_evolution_engine: MagicMock
    ) -> None:
        """传入evolution_engine时，原有Hook应全部保留"""
        hooks = create_composite_hook(evolution_engine=mock_evolution_engine)

        # 验证基础Hook全部存在
        hook_types = [type(h) for h in hooks]
        assert StreamingHook in hook_types, "应包含StreamingHook"
        assert ErrorHandlingHook in hook_types, "应包含ErrorHandlingHook"
        assert ProgressDisplayHook in hook_types, "应包含ProgressDisplayHook"

    def test_decision_log_hook_carries_correct_session_key(
        self, mock_evolution_engine: MagicMock
    ) -> None:
        """DecisionLogHook应携带正确的session_key"""
        session_key = "test-session-2024"
        hooks = create_composite_hook(
            evolution_engine=mock_evolution_engine,
            session_key=session_key,
        )

        decision_hooks = [h for h in hooks if isinstance(h, DecisionLogHook)]
        assert len(decision_hooks) == 1
        assert decision_hooks[0]._session_key == session_key, (
            f"session_key应为'{session_key}'"
        )

    def test_decision_log_hook_default_session_key(
        self, mock_evolution_engine: MagicMock
    ) -> None:
        """不传session_key时，DecisionLogHook应使用默认空字符串"""
        hooks = create_composite_hook(evolution_engine=mock_evolution_engine)

        decision_hooks = [h for h in hooks if isinstance(h, DecisionLogHook)]
        assert len(decision_hooks) == 1
        assert decision_hooks[0]._session_key == "", "默认session_key应为空字符串"

    def test_hook_registration_order(self, mock_evolution_engine: MagicMock) -> None:
        """Hook注册顺序应为: StreamingHook -> ErrorHandlingHook -> ProgressDisplayHook -> DecisionLogHook"""
        hooks = create_composite_hook(evolution_engine=mock_evolution_engine)

        hook_types = [type(h) for h in hooks]
        # 找到各Hook的位置索引
        streaming_idx = hook_types.index(StreamingHook)
        error_idx = hook_types.index(ErrorHandlingHook)
        progress_idx = hook_types.index(ProgressDisplayHook)
        decision_idx = hook_types.index(DecisionLogHook)

        assert streaming_idx < error_idx < progress_idx < decision_idx, (
            "Hook注册顺序应为 StreamingHook < ErrorHandlingHook < ProgressDisplayHook < DecisionLogHook"
        )

    def test_evolution_engine_none_does_not_add_hook(self) -> None:
        """evolution_engine为None时，不应添加DecisionLogHook"""
        hooks = create_composite_hook(evolution_engine=None)

        decision_hooks = [h for h in hooks if isinstance(h, DecisionLogHook)]
        assert len(decision_hooks) == 0, (
            "evolution_engine=None时不应添加DecisionLogHook"
        )

    def test_base_hooks_always_present(self) -> None:
        """无论是否传入evolution_engine，基础Hook（前3个）始终存在"""
        hooks_without = create_composite_hook()
        hooks_with = create_composite_hook(
            evolution_engine=MagicMock(),
        )

        # 基础Hook类型
        base_types = {StreamingHook, ErrorHandlingHook, ProgressDisplayHook}

        types_without = {type(h) for h in hooks_without}
        types_with = {type(h) for h in hooks_with}

        assert base_types.issubset(types_without), (
            "不传evolution_engine时基础Hook应全部存在"
        )
        assert base_types.issubset(types_with), (
            "传入evolution_engine时基础Hook应全部存在"
        )
