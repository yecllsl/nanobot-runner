from __future__ import annotations

from datetime import datetime

import pytest

from src.core.evolution.models import (
    CalibrationProfile,
    CalibrationReport,
    DecisionLog,
    ModelEvolutionResult,
    OutcomeRecord,
    ParameterChange,
    PredictionAccuracyStats,
    TrainingResponseReport,
    TrainingTypeResponse,
)
from src.core.transparency.models import DecisionType


class TestDecisionLog:
    """DecisionLog 数据模型测试"""

    def test_create_decision_log_with_required_fields(self):
        """测试创建DecisionLog（仅必填字段）"""
        log = DecisionLog(
            decision_id="dec_001",
            timestamp=datetime(2026, 5, 1, 10, 0, 0),
            runner_state={
                "vdot": 45.0,
                "ctl": 50.0,
                "atl": 40.0,
                "tsb": 10.0,
                "fatigue_score": 3.0,
            },
            decision_type=DecisionType.PLAN_ADJUSTMENT,
            tool_call_chain=[
                {"tool": "generate_training_plan", "arguments": {"goal": "全马破4"}}
            ],
            prediction_snapshot=None,
            recommendation_text="建议执行5周训练计划",
            execution_status="pending",
            recommendation_accepted=None,
            session_key="session_001",
        )
        assert log.decision_id == "dec_001"
        assert log.decision_type == DecisionType.PLAN_ADJUSTMENT
        assert log.execution_status == "pending"
        assert log.prediction_snapshot is None
        assert log.recommendation_accepted is None

    def test_decision_log_is_frozen(self):
        """测试DecisionLog不可变"""
        log = DecisionLog(
            decision_id="dec_002",
            timestamp=datetime(2026, 5, 1, 10, 0, 0),
            runner_state={"vdot": 45.0},
            decision_type=DecisionType.TRAINING_ADVICE,
            tool_call_chain=[],
            prediction_snapshot=None,
            recommendation_text=None,
            execution_status="pending",
            recommendation_accepted=None,
            session_key="",
        )
        with pytest.raises(AttributeError):
            log.decision_id = "dec_003"  # type: ignore[misc]

    def test_decision_log_to_dict(self):
        """测试DecisionLog序列化为字典"""
        log = DecisionLog(
            decision_id="dec_004",
            timestamp=datetime(2026, 5, 1, 10, 0, 0),
            runner_state={"vdot": 45.0},
            decision_type=DecisionType.RECOVERY_SUGGESTION,
            tool_call_chain=[{"tool": "suggest_recovery", "arguments": {}}],
            prediction_snapshot={"predicted_vdot": 46.0},
            recommendation_text="建议休息",
            execution_status="executed",
            recommendation_accepted=True,
            session_key="session_002",
        )
        d = log.to_dict()
        assert d["decision_id"] == "dec_004"
        assert d["decision_type"] == "recovery_suggestion"
        assert d["execution_status"] == "executed"
        assert d["prediction_snapshot"] == {"predicted_vdot": 46.0}
        assert d["recommendation_accepted"] is True

    def test_decision_log_from_dict(self):
        """测试DecisionLog从字典反序列化"""
        data = {
            "decision_id": "dec_005",
            "timestamp": "2026-05-01T10:00:00",
            "runner_state": {"vdot": 45.0},
            "decision_type": "plan_adjustment",
            "tool_call_chain": [],
            "prediction_snapshot": None,
            "recommendation_text": None,
            "execution_status": "pending",
            "recommendation_accepted": None,
            "session_key": "",
        }
        log = DecisionLog.from_dict(data)
        assert log.decision_id == "dec_005"
        assert log.decision_type == DecisionType.PLAN_ADJUSTMENT
        assert log.execution_status == "pending"

    def test_execution_status_string_values(self):
        """测试execution_status使用字符串而非枚举"""
        valid_statuses = ["pending", "executed", "skipped", "modified", "failed"]
        for status in valid_statuses:
            log = DecisionLog(
                decision_id=f"dec_status_{status}",
                timestamp=datetime(2026, 5, 1, 10, 0, 0),
                runner_state={"vdot": 45.0},
                decision_type=DecisionType.GENERAL,
                tool_call_chain=[],
                prediction_snapshot=None,
                recommendation_text=None,
                execution_status=status,
                recommendation_accepted=None,
                session_key="",
            )
            assert log.execution_status == status


class TestOutcomeRecord:
    """OutcomeRecord 数据模型测试"""

    def test_create_outcome_record_with_required_fields(self):
        """测试创建OutcomeRecord（仅必填字段）"""
        record = OutcomeRecord(
            outcome_id="out_001",
            decision_id="dec_001",
            outcome_timestamp=datetime(2026, 5, 2, 8, 0, 0),
            actual_vdot=None,
            actual_injury=False,
            execution_fidelity=None,
            user_feedback_score=None,
            user_feedback_text=None,
            prediction_error=None,
            prediction_direction=None,
            session_id=None,
        )
        assert record.outcome_id == "out_001"
        assert record.decision_id == "dec_001"
        assert record.actual_vdot is None
        assert record.actual_injury is False

    def test_outcome_record_is_frozen(self):
        """测试OutcomeRecord不可变"""
        record = OutcomeRecord(
            outcome_id="out_002",
            decision_id="dec_002",
            outcome_timestamp=datetime(2026, 5, 2, 8, 0, 0),
            actual_vdot=None,
            actual_injury=False,
            execution_fidelity=None,
            user_feedback_score=None,
            user_feedback_text=None,
            prediction_error=None,
            prediction_direction=None,
            session_id=None,
        )
        with pytest.raises(AttributeError):
            record.outcome_id = "out_003"  # type: ignore[misc]

    def test_outcome_record_to_dict(self):
        """测试OutcomeRecord序列化为字典"""
        record = OutcomeRecord(
            outcome_id="out_003",
            decision_id="dec_003",
            outcome_timestamp=datetime(2026, 5, 2, 8, 0, 0),
            actual_vdot=46.0,
            actual_injury=False,
            execution_fidelity=0.85,
            user_feedback_score=4,
            user_feedback_text="很好",
            prediction_error=0.03,
            prediction_direction="overestimate",
            session_id="session_001",
        )
        d = record.to_dict()
        assert d["outcome_id"] == "out_003"
        assert d["prediction_direction"] == "overestimate"
        assert d["execution_fidelity"] == 0.85
        assert "error_direction" not in d

    def test_outcome_record_from_dict(self):
        """测试OutcomeRecord从字典反序列化"""
        data = {
            "outcome_id": "out_004",
            "decision_id": "dec_004",
            "outcome_timestamp": "2026-05-02T08:00:00",
            "actual_vdot": 46.0,
            "actual_injury": False,
            "execution_fidelity": 0.85,
            "user_feedback_score": 4,
            "user_feedback_text": "很好",
            "prediction_error": 0.03,
            "prediction_direction": "overestimate",
            "session_id": "session_001",
        }
        record = OutcomeRecord.from_dict(data)
        assert record.outcome_id == "out_004"
        assert record.prediction_direction == "overestimate"

    def test_prediction_direction_field_name_not_error_direction(self):
        """测试字段名为prediction_direction而非error_direction（评审遗留NP-03）"""
        record = OutcomeRecord(
            outcome_id="out_005",
            decision_id="dec_005",
            outcome_timestamp=datetime(2026, 5, 2, 8, 0, 0),
            actual_vdot=None,
            actual_injury=False,
            execution_fidelity=None,
            user_feedback_score=None,
            user_feedback_text=None,
            prediction_error=0.05,
            prediction_direction="underestimate",
            session_id=None,
        )
        assert hasattr(record, "prediction_direction")
        assert not hasattr(record, "error_direction")
        d = record.to_dict()
        assert "prediction_direction" in d
        assert "error_direction" not in d


class TestPredictionAccuracyStats:
    """PredictionAccuracyStats 数据模型测试"""

    def test_create_prediction_accuracy_stats(self):
        """测试创建PredictionAccuracyStats"""
        stats = PredictionAccuracyStats(
            mae=0.04,
            total_pairs=10,
            overestimate_rate=0.6,
            underestimate_rate=0.4,
        )
        assert stats.mae == 0.04
        assert stats.total_pairs == 10
        assert stats.overestimate_rate == 0.6
        assert stats.underestimate_rate == 0.4

    def test_prediction_accuracy_stats_to_dict(self):
        """测试PredictionAccuracyStats序列化"""
        stats = PredictionAccuracyStats(
            mae=0.04,
            total_pairs=10,
            overestimate_rate=0.6,
            underestimate_rate=0.4,
        )
        d = stats.to_dict()
        assert d["mae"] == 0.04
        assert d["total_pairs"] == 10
        assert d["overestimate_rate"] == 0.6
        assert d["underestimate_rate"] == 0.4


class TestTrainingTypeResponse:
    """TrainingTypeResponse 数据模型测试"""

    def test_create_training_type_response(self):
        resp = TrainingTypeResponse(
            training_type="interval",
            sample_count=10,
            avg_vdot_delta=0.3,
            avg_fidelity=0.85,
            response_score=0.72,
        )
        assert resp.training_type == "interval"
        assert resp.sample_count == 10
        assert resp.avg_vdot_delta == 0.3
        assert resp.avg_fidelity == 0.85
        assert resp.response_score == 0.72

    def test_training_type_response_is_frozen(self):
        resp = TrainingTypeResponse(
            training_type="threshold",
            sample_count=5,
            avg_vdot_delta=0.1,
            avg_fidelity=0.9,
            response_score=0.5,
        )
        with pytest.raises(AttributeError):
            resp.training_type = "easy"  # type: ignore[misc]

    def test_training_type_response_to_dict(self):
        resp = TrainingTypeResponse(
            training_type="long",
            sample_count=8,
            avg_vdot_delta=0.2,
            avg_fidelity=0.75,
            response_score=0.6,
        )
        d = resp.to_dict()
        assert d["training_type"] == "long"
        assert d["sample_count"] == 8
        assert d["avg_vdot_delta"] == 0.2
        assert d["avg_fidelity"] == 0.75
        assert d["response_score"] == 0.6


class TestTrainingResponseReport:
    """TrainingResponseReport 数据模型测试"""

    def test_create_training_response_report(self):
        responses = [
            TrainingTypeResponse("interval", 10, 0.3, 0.85, 0.72),
            TrainingTypeResponse("easy", 8, 0.1, 0.9, 0.5),
        ]
        report = TrainingResponseReport(
            report_id="rpt_001",
            timestamp=datetime(2026, 5, 20, 10, 0, 0),
            analysis_months=6,
            total_pairs=20,
            eligible_pairs=18,
            training_responses=responses,
            best_type="interval",
            worst_type="easy",
            profile_summary="间歇训练效果最佳",
            data_sufficient=True,
        )
        assert report.report_id == "rpt_001"
        assert report.analysis_months == 6
        assert len(report.training_responses) == 2
        assert report.best_type == "interval"
        assert report.worst_type == "easy"
        assert report.data_sufficient is True

    def test_training_response_report_to_dict(self):
        responses = [TrainingTypeResponse("interval", 10, 0.3, 0.85, 0.72)]
        report = TrainingResponseReport(
            report_id="rpt_002",
            timestamp=datetime(2026, 5, 20, 10, 0, 0),
            analysis_months=6,
            total_pairs=20,
            eligible_pairs=18,
            training_responses=responses,
            best_type="interval",
            worst_type=None,
            profile_summary="数据不足",
            data_sufficient=False,
        )
        d = report.to_dict()
        assert d["report_id"] == "rpt_002"
        assert len(d["training_responses"]) == 1
        assert d["worst_type"] is None

    def test_training_response_report_from_dict(self):
        data = {
            "report_id": "rpt_003",
            "timestamp": "2026-05-20T10:00:00",
            "analysis_months": 6,
            "total_pairs": 20,
            "eligible_pairs": 18,
            "training_responses": [
                {
                    "training_type": "interval",
                    "sample_count": 10,
                    "avg_vdot_delta": 0.3,
                    "avg_fidelity": 0.85,
                    "response_score": 0.72,
                }
            ],
            "best_type": "interval",
            "worst_type": None,
            "profile_summary": "测试",
            "data_sufficient": True,
        }
        report = TrainingResponseReport.from_dict(data)
        assert report.report_id == "rpt_003"
        assert len(report.training_responses) == 1
        assert report.training_responses[0].training_type == "interval"


class TestCalibrationProfile:
    """CalibrationProfile 数据模型测试"""

    def test_create_calibration_profile(self):
        profile = CalibrationProfile(
            model_type="vdot",
            scale=1.05,
            last_updated=datetime(2026, 5, 20, 10, 0, 0),
            sample_count=15,
            mae_before=2.5,
            mae_after=1.8,
        )
        assert profile.model_type == "vdot"
        assert profile.scale == 1.05
        assert profile.sample_count == 15

    def test_calibration_profile_default_scale(self):
        profile = CalibrationProfile(
            model_type="vdot",
            last_updated=datetime(2026, 5, 20, 10, 0, 0),
            sample_count=0,
        )
        assert profile.scale == 1.0
        assert profile.mae_before is None
        assert profile.mae_after is None

    def test_calibration_profile_no_bias_field(self):
        """测试CalibrationProfile无bias字段（评审MEDIUM-1整改）"""
        profile = CalibrationProfile(
            model_type="vdot",
            last_updated=datetime(2026, 5, 20, 10, 0, 0),
            sample_count=0,
        )
        assert not hasattr(profile, "bias")
        d = profile.to_dict()
        assert "bias" not in d

    def test_calibration_profile_default_class_method(self):
        profile = CalibrationProfile.default("vdot")
        assert profile.model_type == "vdot"
        assert profile.scale == 1.0
        assert profile.sample_count == 0

    def test_calibration_profile_to_dict_and_from_dict(self):
        profile = CalibrationProfile(
            model_type="injury",
            scale=0.95,
            last_updated=datetime(2026, 5, 20, 10, 0, 0),
            sample_count=20,
            mae_before=3.0,
            mae_after=2.2,
        )
        d = profile.to_dict()
        restored = CalibrationProfile.from_dict(d)
        assert restored.model_type == "injury"
        assert restored.scale == 0.95
        assert restored.sample_count == 20


class TestCalibrationReport:
    """CalibrationReport 数据模型测试"""

    def test_create_calibration_report(self):
        report = CalibrationReport(
            model_type="vdot",
            timestamp=datetime(2026, 5, 20, 10, 0, 0),
            direction="overestimate",
            magnitude=0.08,
            scale_before=1.0,
            scale_after=0.95,
            mae_before=2.5,
            mae_after=1.8,
            improvement_pct=28.0,
            sample_count=15,
        )
        assert report.model_type == "vdot"
        assert report.direction == "overestimate"
        assert report.scale_after == 0.95
        assert report.improvement_pct == 28.0

    def test_calibration_report_no_bias_fields(self):
        """测试CalibrationReport无bias_before/bias_after字段"""
        report = CalibrationReport(
            model_type="vdot",
            timestamp=datetime(2026, 5, 20, 10, 0, 0),
            direction="none",
            magnitude=0.0,
            scale_before=1.0,
            scale_after=1.0,
            mae_before=1.0,
            mae_after=1.0,
            improvement_pct=0.0,
            sample_count=10,
        )
        assert not hasattr(report, "bias_before")
        assert not hasattr(report, "bias_after")
        d = report.to_dict()
        assert "bias_before" not in d
        assert "bias_after" not in d

    def test_calibration_report_from_dict(self):
        data = {
            "model_type": "vdot",
            "timestamp": "2026-05-20T10:00:00",
            "direction": "underestimate",
            "magnitude": 0.06,
            "scale_before": 1.0,
            "scale_after": 1.04,
            "mae_before": 2.0,
            "mae_after": 1.5,
            "improvement_pct": 25.0,
            "sample_count": 12,
        }
        report = CalibrationReport.from_dict(data)
        assert report.direction == "underestimate"
        assert report.scale_after == 1.04


class TestParameterChange:
    """ParameterChange 数据模型测试"""

    def test_create_parameter_change(self):
        change = ParameterChange(
            name="tau_fitness",
            old_value=42.0,
            new_value=44.0,
            change_pct=4.76,
        )
        assert change.name == "tau_fitness"
        assert change.old_value == 42.0
        assert change.new_value == 44.0
        assert change.change_pct == 4.76

    def test_parameter_change_to_dict(self):
        change = ParameterChange(
            name="k1",
            old_value=0.0038,
            new_value=0.00361,
            change_pct=-5.0,
        )
        d = change.to_dict()
        assert d["name"] == "k1"
        assert d["change_pct"] == -5.0


class TestModelEvolutionResult:
    """ModelEvolutionResult 数据模型测试"""

    def test_create_model_evolution_result(self):
        changes = [
            ParameterChange("tau_fitness", 42.0, 44.0, 4.76),
            ParameterChange("k1", 0.0038, 0.00361, -5.0),
        ]
        cal_report = CalibrationReport(
            model_type="vdot",
            timestamp=datetime(2026, 5, 20, 10, 0, 0),
            direction="overestimate",
            magnitude=0.08,
            scale_before=1.0,
            scale_after=0.95,
            mae_before=2.5,
            mae_after=1.8,
            improvement_pct=28.0,
            sample_count=15,
        )
        result = ModelEvolutionResult(
            model_type="vdot",
            timestamp=datetime(2026, 5, 20, 10, 0, 0),
            parameter_changes=changes,
            mae_before=2.5,
            mae_after=1.8,
            improvement_pct=28.0,
            calibration_report=cal_report,
        )
        assert result.model_type == "vdot"
        assert len(result.parameter_changes) == 2
        assert result.calibration_report is not None

    def test_model_evolution_result_without_calibration(self):
        result = ModelEvolutionResult(
            model_type="vdot",
            timestamp=datetime(2026, 5, 20, 10, 0, 0),
            parameter_changes=[],
            mae_before=0.0,
            mae_after=0.0,
            improvement_pct=0.0,
            calibration_report=None,
        )
        assert result.calibration_report is None
        assert result.parameter_changes == []

    def test_model_evolution_result_from_dict(self):
        data = {
            "model_type": "vdot",
            "timestamp": "2026-05-20T10:00:00",
            "parameter_changes": [
                {
                    "name": "tau_fitness",
                    "old_value": 42.0,
                    "new_value": 44.0,
                    "change_pct": 4.76,
                }
            ],
            "mae_before": 2.5,
            "mae_after": 1.8,
            "improvement_pct": 28.0,
            "calibration_report": None,
        }
        result = ModelEvolutionResult.from_dict(data)
        assert result.model_type == "vdot"
        assert len(result.parameter_changes) == 1
        assert result.parameter_changes[0].name == "tau_fitness"


# === v0.25 数据模型测试 ===


class TestEvolutionAction:
    """EvolutionAction数据模型测试"""

    def test_create_evolution_action(self) -> None:
        """测试创建EvolutionAction实例"""
        from src.core.evolution.models import EvolutionAction

        now = datetime.now()
        action = EvolutionAction(
            action_id="test_001",
            action_type="retrain_model",
            trigger_reason="VDOT预测误差连续3次>5%",
            trigger_condition={"consecutive_errors": 3, "threshold": 0.05},
            target_model_type="vdot",
            priority="high",
            created_at=now,
        )
        assert action.action_id == "test_001"
        assert action.action_type == "retrain_model"
        assert action.trigger_reason == "VDOT预测误差连续3次>5%"
        assert action.trigger_condition == {"consecutive_errors": 3, "threshold": 0.05}
        assert action.target_model_type == "vdot"
        assert action.priority == "high"
        assert action.created_at == now
        assert action.executed is False
        assert action.executed_at is None
        assert action.execution_result is None

    def test_evolution_action_to_dict(self) -> None:
        """测试EvolutionAction序列化"""
        from src.core.evolution.models import EvolutionAction

        now = datetime.now()
        action = EvolutionAction(
            action_id="test_002",
            action_type="adjust_strategy",
            trigger_reason="用户连续2次拒绝推荐",
            trigger_condition={"consecutive_rejections": 2},
            target_model_type="prompt",
            priority="medium",
            created_at=now,
            executed=True,
            executed_at=now,
            execution_result="推荐策略已调整",
        )
        d = action.to_dict()
        assert d["action_id"] == "test_002"
        assert d["action_type"] == "adjust_strategy"
        assert d["executed"] is True
        assert d["execution_result"] == "推荐策略已调整"
        assert d["created_at"] == now.isoformat()

    def test_evolution_action_from_dict(self) -> None:
        """测试EvolutionAction反序列化"""
        from src.core.evolution.models import EvolutionAction

        now = datetime.now()
        data = {
            "action_id": "test_003",
            "action_type": "incremental_learn",
            "trigger_reason": "新数据积累50条>=50",
            "trigger_condition": {"new_count": 50, "threshold": 50},
            "target_model_type": "all",
            "priority": "medium",
            "created_at": now.isoformat(),
            "executed": False,
            "executed_at": None,
            "execution_result": None,
        }
        action = EvolutionAction.from_dict(data)
        assert action.action_id == "test_003"
        assert action.action_type == "incremental_learn"
        assert action.executed is False

    def test_evolution_action_frozen(self) -> None:
        """测试EvolutionAction不可变性"""
        from src.core.evolution.models import EvolutionAction

        action = EvolutionAction(
            action_id="test_004",
            action_type="generate_report",
            trigger_reason="月度复盘",
            trigger_condition={},
            target_model_type="none",
            priority="low",
            created_at=datetime.now(),
        )
        with pytest.raises(AttributeError):
            action.executed = True  # type: ignore[misc]

    def test_evolution_action_execution_result_dict_type(self) -> None:
        """测试EvolutionAction.execution_result支持dict类型（H-02整改）"""
        from src.core.evolution.models import EvolutionAction

        result_data = {"vdot": {"success": True, "mae_before": 0.05, "mae_after": 0.03}}
        action = EvolutionAction(
            action_id="test_005",
            action_type="incremental_learn",
            trigger_reason="新数据积累",
            trigger_condition={},
            target_model_type="all",
            priority="medium",
            created_at=datetime.now(),
            executed=True,
            execution_result=result_data,
        )
        assert isinstance(action.execution_result, dict)
        assert action.execution_result["vdot"]["success"] is True


class TestTriggerCheckResult:
    """TriggerCheckResult数据模型测试"""

    def test_create_trigger_check_result(self) -> None:
        """测试创建TriggerCheckResult实例"""
        from src.core.evolution.models import EvolutionAction, TriggerCheckResult

        now = datetime.now()
        action = EvolutionAction(
            action_id="test_010",
            action_type="retrain_model",
            trigger_reason="VDOT误差",
            trigger_condition={},
            target_model_type="vdot",
            priority="high",
            created_at=now,
        )
        result = TriggerCheckResult(
            checked_at=now,
            triggered_actions=[action],
            skipped_conditions=[{"rule": "TR-03", "reason": "新数据不足50条"}],
        )
        assert result.checked_at == now
        assert len(result.triggered_actions) == 1
        assert len(result.skipped_conditions) == 1

    def test_trigger_check_result_to_dict(self) -> None:
        """测试TriggerCheckResult序列化"""
        from src.core.evolution.models import TriggerCheckResult

        now = datetime.now()
        result = TriggerCheckResult(
            checked_at=now,
            triggered_actions=[],
            skipped_conditions=[],
        )
        d = result.to_dict()
        assert d["checked_at"] == now.isoformat()
        assert d["triggered_actions"] == []
        assert d["skipped_conditions"] == []


class TestPromptTuningParams:
    """PromptTuningParams数据模型测试"""

    def test_default_params(self) -> None:
        """测试默认参数（全部0.5）"""
        from src.core.evolution.models import PromptTuningParams

        params = PromptTuningParams.default()
        assert params.tone_intensity == 0.5
        assert params.detail_level_score == 0.5
        assert params.recommendation_aggressiveness == 0.5
        assert params.data_driven_weight == 0.5
        assert params.update_count == 0

    def test_with_updates_basic(self) -> None:
        """测试with_updates基本更新"""
        from src.core.evolution.models import PromptTuningParams

        params = PromptTuningParams.default()
        updated = params.with_updates(tone=0.7, aggressive=0.3)
        assert updated.tone_intensity == 0.7
        assert updated.recommendation_aggressiveness == 0.3
        assert updated.detail_level_score == 0.5  # 未修改
        assert updated.data_driven_weight == 0.5  # 未修改
        assert updated.update_count == 1

    def test_with_updates_clamp_to_range(self) -> None:
        """测试with_updates将参数clamp到[0.0, 1.0]"""
        from src.core.evolution.models import PromptTuningParams

        params = PromptTuningParams.default()
        # 超上限
        updated = params.with_updates(tone=1.5, aggressive=2.0)
        assert updated.tone_intensity == 1.0
        assert updated.recommendation_aggressiveness == 1.0
        # 超下限
        updated2 = params.with_updates(detail=-0.5, data_driven=-1.0)
        assert updated2.detail_level_score == 0.0
        assert updated2.data_driven_weight == 0.0

    def test_with_updates_none_preserves(self) -> None:
        """测试with_updates传入None保持原值"""
        from src.core.evolution.models import PromptTuningParams

        params = PromptTuningParams(tone_intensity=0.7, detail_level_score=0.3)
        updated = params.with_updates(tone=None, detail=None)
        assert updated.tone_intensity == 0.7
        assert updated.detail_level_score == 0.3

    def test_to_dict_from_dict_roundtrip(self) -> None:
        """测试序列化/反序列化往返"""
        from src.core.evolution.models import PromptTuningParams

        params = PromptTuningParams(
            tone_intensity=0.6,
            detail_level_score=0.4,
            recommendation_aggressiveness=0.7,
            data_driven_weight=0.3,
            update_count=5,
        )
        d = params.to_dict()
        restored = PromptTuningParams.from_dict(d)
        assert restored.tone_intensity == 0.6
        assert restored.detail_level_score == 0.4
        assert restored.recommendation_aggressiveness == 0.7
        assert restored.data_driven_weight == 0.3
        assert restored.update_count == 5

    def test_frozen_immutability(self) -> None:
        """测试不可变性"""
        from src.core.evolution.models import PromptTuningParams

        params = PromptTuningParams.default()
        with pytest.raises(AttributeError):
            params.tone_intensity = 0.8  # type: ignore[misc]


class TestEvolutionReport:
    """EvolutionReport数据模型测试"""

    def test_create_evolution_report(self) -> None:
        """测试创建EvolutionReport实例"""
        from src.core.evolution.models import EvolutionReport

        now = datetime.now()
        report = EvolutionReport(
            report_id="rpt_001",
            month="2026-05",
            generated_at=now,
            total_decisions=42,
            prediction_accuracy_trend=[{"date": "2026-05-01", "mae": 0.05}],
            decision_acceptance_rate=0.75,
            model_versions={"vdot": "v1.2", "injury": "v1.0"},
            personalization_degree=0.35,
            evolution_actions_count=3,
            last_evolution_time=now,
            calibration_summary={"vdot": {"scale": 0.97}},
            prompt_tuning_summary={"tone_intensity": 0.6},
            recommendations=["建议增加VDOT预测校准频率"],
        )
        assert report.report_id == "rpt_001"
        assert report.month == "2026-05"
        assert report.total_decisions == 42
        assert report.personalization_degree == 0.35
        assert len(report.recommendations) == 1

    def test_evolution_report_to_dict(self) -> None:
        """测试EvolutionReport序列化"""
        from src.core.evolution.models import EvolutionReport

        now = datetime.now()
        report = EvolutionReport(
            report_id="rpt_002",
            month="2026-04",
            generated_at=now,
            total_decisions=0,
            prediction_accuracy_trend=[],
            decision_acceptance_rate=0.0,
            model_versions={},
            personalization_degree=0.0,
            evolution_actions_count=0,
            last_evolution_time=None,
            calibration_summary={},
            prompt_tuning_summary={},
            recommendations=[],
        )
        d = report.to_dict()
        assert d["report_id"] == "rpt_002"
        assert d["month"] == "2026-04"
        assert d["last_evolution_time"] is None

    def test_evolution_report_from_dict(self) -> None:
        """测试EvolutionReport反序列化"""
        from src.core.evolution.models import EvolutionReport

        now = datetime.now()
        data = {
            "report_id": "rpt_003",
            "month": "2026-03",
            "generated_at": now.isoformat(),
            "total_decisions": 10,
            "prediction_accuracy_trend": [],
            "decision_acceptance_rate": 0.5,
            "model_versions": {},
            "personalization_degree": 0.1,
            "evolution_actions_count": 1,
            "last_evolution_time": now.isoformat(),
            "calibration_summary": {},
            "prompt_tuning_summary": {},
            "recommendations": [],
        }
        report = EvolutionReport.from_dict(data)
        assert report.report_id == "rpt_003"
        assert report.total_decisions == 10

    def test_evolution_report_frozen(self) -> None:
        """测试EvolutionReport不可变性"""
        from src.core.evolution.models import EvolutionReport

        report = EvolutionReport(
            report_id="rpt_004",
            month="2026-05",
            generated_at=datetime.now(),
            total_decisions=0,
            prediction_accuracy_trend=[],
            decision_acceptance_rate=0.0,
            model_versions={},
            personalization_degree=0.0,
            evolution_actions_count=0,
            last_evolution_time=None,
            calibration_summary={},
            prompt_tuning_summary={},
            recommendations=[],
        )
        with pytest.raises(AttributeError):
            report.total_decisions = 100  # type: ignore[misc]
