from __future__ import annotations

from datetime import datetime

from src.core.evolution.config import EvolutionConfig
from src.core.evolution.evolution_store import EvolutionStore
from src.core.evolution.models import DecisionLog, OutcomeRecord, TrainingTypeResponse
from src.core.evolution.response_analyzer import ResponseAnalyzer
from src.core.transparency.models import DecisionType


class TestResponseAnalyzer:
    """ResponseAnalyzer 训练响应性分析器测试"""

    def _create_store_with_pairs(
        self, tmp_path, pairs_data: list[dict]
    ) -> EvolutionStore:
        store = EvolutionStore(tmp_path)
        for i, pd in enumerate(pairs_data):
            decision = DecisionLog(
                decision_id=f"dec_{i:03d}",
                timestamp=datetime(2026, 1, 1 + i, 10, 0, 0),
                runner_state={"vdot": pd.get("vdot", 45.0)},
                decision_type=DecisionType.TRAINING_ADVICE,
                tool_call_chain=pd.get("tool_call_chain", []),
                prediction_snapshot=pd.get("prediction_snapshot"),
                recommendation_text=pd.get("recommendation_text"),
                execution_status="executed",
                recommendation_accepted=None,
                session_key="",
            )
            outcome = OutcomeRecord(
                outcome_id=f"out_{i:03d}",
                decision_id=f"dec_{i:03d}",
                outcome_timestamp=datetime(2026, 1, 5 + i, 10, 0, 0),
                actual_vdot=pd.get("actual_vdot"),
                actual_injury=False,
                execution_fidelity=pd.get("fidelity", 0.85),
                user_feedback_score=None,
                user_feedback_text=None,
                prediction_error=None,
                prediction_direction=None,
                session_id=None,
            )
            store.save_decision(decision)
            store.save_outcome(outcome)
        return store

    def test_analyze_with_sufficient_data(self, tmp_path):
        pairs_data = [
            {
                "vdot": 45.0,
                "actual_vdot": 45.5,
                "fidelity": 0.9,
                "recommendation_text": "建议执行间歇跑训练",
                "tool_call_chain": [
                    {
                        "tool": "predict_training_response",
                        "arguments": {"session_type": "interval"},
                    }
                ],
            },
            {
                "vdot": 45.5,
                "actual_vdot": 45.8,
                "fidelity": 0.85,
                "recommendation_text": "建议执行间歇跑训练",
                "tool_call_chain": [
                    {
                        "tool": "predict_training_response",
                        "arguments": {"session_type": "interval"},
                    }
                ],
            },
            {
                "vdot": 45.0,
                "actual_vdot": 45.1,
                "fidelity": 0.8,
                "recommendation_text": "轻松跑恢复",
                "tool_call_chain": [
                    {
                        "tool": "predict_training_response",
                        "arguments": {"session_type": "easy"},
                    }
                ],
            },
        ] * 3
        store = self._create_store_with_pairs(tmp_path, pairs_data)
        config = EvolutionConfig(response_min_samples_per_type=3)
        analyzer = ResponseAnalyzer(store, config)
        report = analyzer.analyze(months=6)
        assert report.data_sufficient is True
        assert report.total_pairs > 0
        assert report.eligible_pairs > 0
        assert len(report.training_responses) > 0
        assert report.best_type is not None

    def test_analyze_insufficient_data(self, tmp_path):
        store = EvolutionStore(tmp_path)
        config = EvolutionConfig(response_min_samples_per_type=10)
        analyzer = ResponseAnalyzer(store, config)
        report = analyzer.analyze(months=6)
        assert report.data_sufficient is False
        assert report.total_pairs == 0

    def test_infer_training_type_from_tool_call_chain(self, tmp_path):
        store = EvolutionStore(tmp_path)
        analyzer = ResponseAnalyzer(store)
        decision = DecisionLog(
            decision_id="dec_test",
            timestamp=datetime(2026, 5, 1, 10, 0, 0),
            runner_state={"vdot": 45.0},
            decision_type=DecisionType.TRAINING_ADVICE,
            tool_call_chain=[
                {
                    "tool": "predict_training_response",
                    "arguments": {"session_type": "threshold"},
                }
            ],
            prediction_snapshot=None,
            recommendation_text="建议执行长距离跑",
            execution_status="executed",
            recommendation_accepted=None,
            session_key="",
        )
        assert analyzer._infer_training_type(decision) == "threshold"

    def test_infer_training_type_from_recommendation_text(self, tmp_path):
        store = EvolutionStore(tmp_path)
        analyzer = ResponseAnalyzer(store)
        decision = DecisionLog(
            decision_id="dec_test",
            timestamp=datetime(2026, 5, 1, 10, 0, 0),
            runner_state={"vdot": 45.0},
            decision_type=DecisionType.TRAINING_ADVICE,
            tool_call_chain=[],
            prediction_snapshot=None,
            recommendation_text="建议执行间歇跑训练",
            execution_status="executed",
            recommendation_accepted=None,
            session_key="",
        )
        assert analyzer._infer_training_type(decision) == "interval"

    def test_infer_training_type_recovery_priority_over_easy(self, tmp_path):
        store = EvolutionStore(tmp_path)
        analyzer = ResponseAnalyzer(store)
        decision = DecisionLog(
            decision_id="dec_test",
            timestamp=datetime(2026, 5, 1, 10, 0, 0),
            runner_state={"vdot": 45.0},
            decision_type=DecisionType.TRAINING_ADVICE,
            tool_call_chain=[],
            prediction_snapshot=None,
            recommendation_text="恢复跑轻松跑",
            execution_status="executed",
            recommendation_accepted=None,
            session_key="",
        )
        assert analyzer._infer_training_type(decision) == "recovery"

    def test_infer_training_type_unknown_fallback(self, tmp_path):
        store = EvolutionStore(tmp_path)
        analyzer = ResponseAnalyzer(store)
        decision = DecisionLog(
            decision_id="dec_test",
            timestamp=datetime(2026, 5, 1, 10, 0, 0),
            runner_state={"vdot": 45.0},
            decision_type=DecisionType.TRAINING_ADVICE,
            tool_call_chain=[],
            prediction_snapshot=None,
            recommendation_text="保持运动习惯",
            execution_status="executed",
            recommendation_accepted=None,
            session_key="",
        )
        assert analyzer._infer_training_type(decision) == "unknown"

    def test_calculate_response_score(self, tmp_path):
        store = EvolutionStore(tmp_path)
        analyzer = ResponseAnalyzer(store)
        score = analyzer._calculate_response_score(0.5, 1.0)
        assert score == 1.0
        score_zero = analyzer._calculate_response_score(0.0, 0.0)
        assert score_zero == 0.0

    def test_build_profile_summary(self, tmp_path):
        store = EvolutionStore(tmp_path)
        analyzer = ResponseAnalyzer(store)
        responses = [
            TrainingTypeResponse("interval", 10, 0.3, 0.85, 0.72),
            TrainingTypeResponse("easy", 8, 0.1, 0.9, 0.5),
        ]
        summary = analyzer._build_profile_summary(responses)
        assert "interval" in summary
        assert len(summary) > 0
