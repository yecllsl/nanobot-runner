"""集成测试: EvolutionReporter全链路 (T14)

验证数据积累 -> 报告生成 -> 报告内容完整性 的完整链路。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.core.evolution.config import EvolutionConfig
from src.core.evolution.evolution_reporter import EvolutionReporter
from src.core.evolution.evolution_store import EvolutionStore
from src.core.evolution.models import (
    DecisionLog,
    EvolutionReport,
)
from src.core.evolution.prompt_tuner import PromptTuner
from src.core.transparency.models import DecisionType


@pytest.fixture
def reporter_with_real_store(
    tmp_path: Any,
) -> tuple[EvolutionReporter, EvolutionStore, PromptTuner]:
    """创建使用真实Store的EvolutionReporter"""
    store = EvolutionStore(tmp_path)
    config = EvolutionConfig(data_dir=str(tmp_path))
    mock_calibration = MagicMock()
    prompt_tuner = PromptTuner(store=store, config=config)
    reporter = EvolutionReporter(
        store=store,
        calibration_engine=mock_calibration,
        prompt_tuner=prompt_tuner,
        config=config,
    )
    return reporter, store, prompt_tuner


class TestEvolutionReporterFullChain:
    """EvolutionReporter全链路集成测试"""

    def test_generate_report_with_data(
        self,
        reporter_with_real_store: tuple[EvolutionReporter, EvolutionStore, PromptTuner],
    ) -> None:
        """有数据时生成完整报告"""
        reporter, store, _ = reporter_with_real_store

        # 写入决策数据
        now = datetime.now()
        for i in range(5):
            decision = DecisionLog(
                decision_id=f"dec_rpt_{i}",
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

        report = reporter.generate_report()
        assert isinstance(report, EvolutionReport)
        assert report.total_decisions >= 5
        assert report.month == now.strftime("%Y-%m")
        assert len(report.recommendations) > 0

    def test_generate_report_empty_data(
        self,
        reporter_with_real_store: tuple[EvolutionReporter, EvolutionStore, PromptTuner],
    ) -> None:
        """无数据时生成空报告"""
        reporter, _, _ = reporter_with_real_store
        report = reporter.generate_report()
        assert report.total_decisions == 0
        assert report.decision_acceptance_rate == 0.0

    def test_report_personalization_degree(
        self,
        reporter_with_real_store: tuple[EvolutionReporter, EvolutionStore, PromptTuner],
    ) -> None:
        """报告个性化程度计算"""
        reporter, _, tuner = reporter_with_real_store

        # 默认参数 -> 个性化程度=0
        report = reporter.generate_report()
        assert report.personalization_degree == 0.0

        # 调整参数后 -> 个性化程度>0
        tuner.update_params(tone=0.8, aggressive=0.2)
        report2 = reporter.generate_report()
        assert report2.personalization_degree > 0

    def test_report_monthly_trigger_state(
        self,
        reporter_with_real_store: tuple[EvolutionReporter, EvolutionStore, PromptTuner],
    ) -> None:
        """报告生成后更新trigger_state"""
        reporter, store, _ = reporter_with_real_store

        now = datetime.now()
        current_month = now.strftime("%Y-%m")

        reporter.generate_report()
        state = store.load_trigger_state("last_monthly_report")
        assert state == current_month

    def test_report_specified_month(
        self,
        reporter_with_real_store: tuple[EvolutionReporter, EvolutionStore, PromptTuner],
    ) -> None:
        """指定月份生成报告"""
        reporter, _, _ = reporter_with_real_store
        report = reporter.generate_report(month="2026-03")
        assert report.month == "2026-03"
