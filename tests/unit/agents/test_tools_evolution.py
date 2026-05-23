# 决策追踪Agent工具单元测试
# v0.23.0 新增

import asyncio
import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.agents.tools import (
    TOOL_DESCRIPTIONS,
    RunnerTools,
    create_tools,
)
from src.agents.tools_evolution import (
    AdjustPromptParamsTool as AdjustPromptParamsToolDirect,
)
from src.agents.tools_evolution import (
    CheckEvolutionTriggersTool as CheckEvolutionTriggersToolDirect,
)
from src.agents.tools_evolution import (
    CheckPlanExecutionTool as CheckPlanExecutionToolDirect,
)
from src.agents.tools_evolution import (
    CheckPredictionAccuracyTool as CheckPredictionAccuracyToolDirect,
)
from src.agents.tools_evolution import (
    GetDecisionHistoryTool as GetDecisionHistoryToolDirect,
)
from src.agents.tools_evolution import (
    GetEvolutionReportTool as GetEvolutionReportToolDirect,
)
from src.agents.tools_evolution import (
    RecordFeedbackTool,
)
from src.core.base.exceptions import NanobotRunnerError
from src.core.evolution.models import (
    DecisionLog,
    EvolutionReport,
    OutcomeRecord,
    PredictionAccuracyStats,
    PromptTuningParams,
    TriggerCheckResult,
)
from src.core.transparency.models import DecisionType

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_context():
    """创建 Mock 应用上下文"""
    context = MagicMock()
    context.storage = MagicMock()
    context.analytics = MagicMock()
    context.profile_storage = MagicMock()
    context.session_repo = MagicMock()
    return context


@pytest.fixture
def runner_tools(mock_context):
    """创建 RunnerTools 实例"""
    return RunnerTools(context=mock_context)


@pytest.fixture
def mock_evolution_engine():
    """创建 Mock EvolutionEngine"""
    engine = MagicMock()
    return engine


def _make_outcome(
    decision_id: str = "dec_test001",
    score: int | None = None,
    fidelity: float | None = None,
    prediction_error: float | None = None,
    prediction_direction: str | None = None,
) -> OutcomeRecord:
    """构造测试用 OutcomeRecord"""
    return OutcomeRecord(
        outcome_id="out_test001",
        decision_id=decision_id,
        outcome_timestamp=datetime(2026, 5, 20, 10, 0, 0),
        actual_vdot=None,
        actual_injury=False,
        execution_fidelity=fidelity,
        user_feedback_score=score,
        user_feedback_text=None,
        prediction_error=prediction_error,
        prediction_direction=prediction_direction,
        session_id=None,
    )


def _make_decision_log(decision_id: str = "dec_test001") -> DecisionLog:
    """构造测试用 DecisionLog"""
    return DecisionLog(
        decision_id=decision_id,
        timestamp=datetime(2026, 5, 20, 10, 0, 0),
        runner_state={"vdot": 45.0, "ctl": 50.0},
        decision_type=DecisionType.TRAINING_ADVICE,
        tool_call_chain=[],
        prediction_snapshot=None,
        recommendation_text="建议轻松跑5公里",
        execution_status="pending",
        recommendation_accepted=None,
        session_key="session_001",
    )


# ---------------------------------------------------------------------------
# 工具类属性测试
# ---------------------------------------------------------------------------


class TestToolProperties:
    """工具类属性测试"""

    def test_record_feedback_tool_name(self, runner_tools):
        """测试 RecordFeedbackTool 名称"""
        tool = RecordFeedbackTool(runner_tools)
        assert tool.name == "record_decision_feedback"

    def test_record_feedback_tool_description(self, runner_tools):
        """测试 RecordFeedbackTool 描述"""
        tool = RecordFeedbackTool(runner_tools)
        assert "反馈评分" in tool.description

    def test_record_feedback_tool_parameters(self, runner_tools):
        """测试 RecordFeedbackTool 参数"""
        tool = RecordFeedbackTool(runner_tools)
        params = tool.parameters
        assert "decision_id" in params["properties"]
        assert "score" in params["properties"]
        assert "decision_id" in params["required"]
        assert "score" in params["required"]

    def test_check_plan_execution_tool_name(self, runner_tools):
        """测试 CheckPlanExecutionTool 名称"""
        tool = CheckPlanExecutionToolDirect(runner_tools)
        assert tool.name == "check_plan_execution"

    def test_check_plan_execution_tool_parameters(self, runner_tools):
        """测试 CheckPlanExecutionTool 参数"""
        tool = CheckPlanExecutionToolDirect(runner_tools)
        params = tool.parameters
        assert "decision_id" in params["properties"]
        assert "decision_id" in params["required"]

    def test_check_prediction_accuracy_tool_name(self, runner_tools):
        """测试 CheckPredictionAccuracyTool 名称"""
        tool = CheckPredictionAccuracyToolDirect(runner_tools)
        assert tool.name == "check_prediction_accuracy"

    def test_check_prediction_accuracy_tool_parameters(self, runner_tools):
        """测试 CheckPredictionAccuracyTool 参数"""
        tool = CheckPredictionAccuracyToolDirect(runner_tools)
        params = tool.parameters
        assert "decision_id" in params["properties"]
        assert "actual_vdot" in params["properties"]
        assert "decision_id" in params["required"]

    def test_get_decision_history_tool_name(self, runner_tools):
        """测试 GetDecisionHistoryTool 名称"""
        tool = GetDecisionHistoryToolDirect(runner_tools)
        assert tool.name == "get_decision_history"

    def test_get_decision_history_tool_parameters(self, runner_tools):
        """测试 GetDecisionHistoryTool 参数"""
        tool = GetDecisionHistoryToolDirect(runner_tools)
        params = tool.parameters
        assert "start_date" in params["properties"]
        assert "end_date" in params["properties"]
        assert "type" in params["properties"]
        assert "limit" in params["properties"]


# ---------------------------------------------------------------------------
# RunnerTools 方法测试
# ---------------------------------------------------------------------------


class TestRecordDecisionFeedback:
    """record_decision_feedback 方法测试"""

    @patch("src.core.base.context.get_context")
    def test_success(self, mock_get_ctx, runner_tools, mock_evolution_engine):
        """测试记录反馈成功"""
        mock_ctx = MagicMock()
        mock_ctx.evolution_engine = mock_evolution_engine
        mock_get_ctx.return_value = mock_ctx

        outcome = _make_outcome(score=4)
        mock_evolution_engine.record_feedback.return_value = outcome

        result = runner_tools.record_decision_feedback(
            decision_id="dec_test001", score=4, text="不错", accepted=True
        )

        assert result["success"] is True
        assert result["data"]["user_feedback_score"] == 4
        mock_evolution_engine.record_feedback.assert_called_once_with(
            "dec_test001", 4, "不错", True
        )

    @patch("src.core.base.context.get_context")
    def test_minimal_params(self, mock_get_ctx, runner_tools, mock_evolution_engine):
        """测试仅必填参数"""
        mock_ctx = MagicMock()
        mock_ctx.evolution_engine = mock_evolution_engine
        mock_get_ctx.return_value = mock_ctx

        outcome = _make_outcome(score=3)
        mock_evolution_engine.record_feedback.return_value = outcome

        result = runner_tools.record_decision_feedback(
            decision_id="dec_test001", score=3
        )

        assert result["success"] is True
        mock_evolution_engine.record_feedback.assert_called_once_with(
            "dec_test001", 3, None, None
        )

    @patch("src.core.base.context.get_context")
    def test_error_decision_not_found(
        self, mock_get_ctx, runner_tools, mock_evolution_engine
    ):
        """测试决策不存在"""
        mock_ctx = MagicMock()
        mock_ctx.evolution_engine = mock_evolution_engine
        mock_get_ctx.return_value = mock_ctx

        mock_evolution_engine.record_feedback.side_effect = ValueError(
            "决策不存在: dec_missing"
        )

        result = runner_tools.record_decision_feedback(
            decision_id="dec_missing", score=1
        )

        assert result["success"] is False
        assert "决策不存在" in result["error"]


class TestCheckPlanExecution:
    """check_plan_execution 方法测试"""

    @patch("src.core.base.context.get_context")
    def test_success(self, mock_get_ctx, runner_tools, mock_evolution_engine):
        """测试检查计划执行成功"""
        mock_ctx = MagicMock()
        mock_ctx.evolution_engine = mock_evolution_engine
        mock_get_ctx.return_value = mock_ctx

        outcome = _make_outcome(fidelity=0.85)
        mock_evolution_engine.check_plan_execution.return_value = outcome

        result = runner_tools.check_plan_execution(decision_id="dec_test001")

        assert result["success"] is True
        assert result["data"]["execution_fidelity"] == 0.85
        # 不含intensity_deviation（评审遗留NP-02）
        assert "intensity_deviation" not in result["data"]

    @patch("src.core.base.context.get_context")
    def test_no_fidelity(self, mock_get_ctx, runner_tools, mock_evolution_engine):
        """测试无执行数据时fidelity为None"""
        mock_ctx = MagicMock()
        mock_ctx.evolution_engine = mock_evolution_engine
        mock_get_ctx.return_value = mock_ctx

        outcome = _make_outcome(fidelity=None)
        mock_evolution_engine.check_plan_execution.return_value = outcome

        result = runner_tools.check_plan_execution(decision_id="dec_test001")

        assert result["success"] is True
        assert result["data"]["execution_fidelity"] is None


class TestCheckPredictionAccuracy:
    """check_prediction_accuracy 方法测试"""

    @patch("src.core.base.context.get_context")
    def test_success(self, mock_get_ctx, runner_tools, mock_evolution_engine):
        """测试检查预测精度成功"""
        mock_ctx = MagicMock()
        mock_ctx.evolution_engine = mock_evolution_engine
        mock_get_ctx.return_value = mock_ctx

        outcome = OutcomeRecord(
            outcome_id="out_test001",
            decision_id="dec_test001",
            outcome_timestamp=datetime(2026, 5, 20, 10, 0, 0),
            actual_vdot=46.0,
            actual_injury=False,
            execution_fidelity=None,
            user_feedback_score=None,
            user_feedback_text=None,
            prediction_error=3.5,
            prediction_direction="overestimate",
            session_id=None,
        )
        stats = PredictionAccuracyStats(
            mae=2.8, total_pairs=10, overestimate_rate=0.3, underestimate_rate=0.2
        )
        mock_evolution_engine.check_prediction_accuracy.return_value = (outcome, stats)

        result = runner_tools.check_prediction_accuracy(
            decision_id="dec_test001", actual_vdot=46.0
        )

        assert result["success"] is True
        # 使用prediction_direction（非error_direction，评审遗留NP-03）
        assert result["data"]["prediction_direction"] == "overestimate"
        assert result["data"]["prediction_error"] == 3.5
        assert result["data"]["mae"] == 2.8
        assert result["data"]["total_pairs"] == 10

    @patch("src.core.base.context.get_context")
    def test_actual_vdot_zero_uses_latest(
        self, mock_get_ctx, runner_tools, mock_evolution_engine
    ):
        """测试actual_vdot为0时从最新session获取"""
        mock_ctx = MagicMock()
        mock_ctx.evolution_engine = mock_evolution_engine
        mock_get_ctx.return_value = mock_ctx

        # Mock _get_latest_vdot 返回45.0
        runner_tools._get_latest_vdot = MagicMock(return_value=45.0)

        outcome = OutcomeRecord(
            outcome_id="out_test002",
            decision_id="dec_test002",
            outcome_timestamp=datetime(2026, 5, 20, 10, 0, 0),
            actual_vdot=45.0,
            actual_injury=False,
            execution_fidelity=None,
            user_feedback_score=None,
            user_feedback_text=None,
            prediction_error=1.0,
            prediction_direction="accurate",
            session_id=None,
        )
        stats = PredictionAccuracyStats(
            mae=1.0, total_pairs=5, overestimate_rate=0.1, underestimate_rate=0.1
        )
        mock_evolution_engine.check_prediction_accuracy.return_value = (outcome, stats)

        result = runner_tools.check_prediction_accuracy(
            decision_id="dec_test002", actual_vdot=0.0
        )

        assert result["success"] is True
        # 验证_get_latest_vdot被调用
        runner_tools._get_latest_vdot.assert_called_once()


class TestGetDecisionHistory:
    """get_decision_history 方法测试"""

    @patch("src.core.base.context.get_context")
    def test_success_no_filters(
        self, mock_get_ctx, runner_tools, mock_evolution_engine
    ):
        """测试无过滤条件查询"""
        mock_ctx = MagicMock()
        mock_ctx.evolution_engine = mock_evolution_engine
        mock_get_ctx.return_value = mock_ctx

        decisions = [_make_decision_log("dec_001"), _make_decision_log("dec_002")]
        mock_evolution_engine.get_decision_history.return_value = decisions

        result = runner_tools.get_decision_history()

        assert result["success"] is True
        assert len(result["data"]) == 2
        assert result["data"][0]["decision_id"] == "dec_001"

    @patch("src.core.base.context.get_context")
    def test_with_date_filter(self, mock_get_ctx, runner_tools, mock_evolution_engine):
        """测试带日期过滤查询"""
        mock_ctx = MagicMock()
        mock_ctx.evolution_engine = mock_evolution_engine
        mock_get_ctx.return_value = mock_ctx

        mock_evolution_engine.get_decision_history.return_value = []

        result = runner_tools.get_decision_history(
            start_date="2026-01-01", end_date="2026-05-20"
        )

        assert result["success"] is True
        # 验证引擎被调用时传入了datetime对象
        call_args = mock_evolution_engine.get_decision_history.call_args
        assert call_args.kwargs["start_date"] is not None
        assert call_args.kwargs["end_date"] is not None

    @patch("src.core.base.context.get_context")
    def test_with_type_filter(self, mock_get_ctx, runner_tools, mock_evolution_engine):
        """测试带决策类型过滤查询"""
        mock_ctx = MagicMock()
        mock_ctx.evolution_engine = mock_evolution_engine
        mock_get_ctx.return_value = mock_ctx

        mock_evolution_engine.get_decision_history.return_value = []

        result = runner_tools.get_decision_history(decision_type_str="training_advice")

        assert result["success"] is True
        call_args = mock_evolution_engine.get_decision_history.call_args
        assert call_args.kwargs["decision_type"] == DecisionType.TRAINING_ADVICE

    def test_invalid_start_date(self, runner_tools):
        """测试无效起始日期格式"""
        result = runner_tools.get_decision_history(start_date="not-a-date")

        assert result["success"] is False
        assert "起始日期格式错误" in result["error"]

    def test_invalid_end_date(self, runner_tools):
        """测试无效结束日期格式"""
        result = runner_tools.get_decision_history(end_date="2026/05/20")

        assert result["success"] is False
        assert "结束日期格式错误" in result["error"]

    def test_invalid_decision_type(self, runner_tools):
        """测试无效决策类型"""
        result = runner_tools.get_decision_history(decision_type_str="invalid_type")

        assert result["success"] is False
        assert "无效的决策类型" in result["error"]

    @patch("src.core.base.context.get_context")
    def test_with_limit(self, mock_get_ctx, runner_tools, mock_evolution_engine):
        """测试limit参数"""
        mock_ctx = MagicMock()
        mock_ctx.evolution_engine = mock_evolution_engine
        mock_get_ctx.return_value = mock_ctx

        mock_evolution_engine.get_decision_history.return_value = []

        result = runner_tools.get_decision_history(limit=10)

        assert result["success"] is True
        call_args = mock_evolution_engine.get_decision_history.call_args
        assert call_args.kwargs["limit"] == 10


# ---------------------------------------------------------------------------
# 工具类 execute 测试
# ---------------------------------------------------------------------------


class TestToolExecute:
    """工具类 execute 方法测试"""

    @patch("src.core.base.context.get_context")
    def test_record_feedback_execute(
        self, mock_get_ctx, runner_tools, mock_evolution_engine
    ):
        """测试 RecordFeedbackTool 执行"""
        mock_ctx = MagicMock()
        mock_ctx.evolution_engine = mock_evolution_engine
        mock_get_ctx.return_value = mock_ctx

        outcome = _make_outcome(score=5)
        mock_evolution_engine.record_feedback.return_value = outcome

        tool = RecordFeedbackTool(runner_tools)

        result = asyncio.run(tool.execute(decision_id="dec_test001", score=5))
        parsed = json.loads(result)

        assert parsed["success"] is True
        assert parsed["data"]["user_feedback_score"] == 5

    @patch("src.core.base.context.get_context")
    def test_check_plan_execution_execute(
        self, mock_get_ctx, runner_tools, mock_evolution_engine
    ):
        """测试 CheckPlanExecutionTool 执行"""
        mock_ctx = MagicMock()
        mock_ctx.evolution_engine = mock_evolution_engine
        mock_get_ctx.return_value = mock_ctx

        outcome = _make_outcome(fidelity=0.9)
        mock_evolution_engine.check_plan_execution.return_value = outcome

        tool = CheckPlanExecutionToolDirect(runner_tools)

        result = asyncio.run(tool.execute(decision_id="dec_test001"))
        parsed = json.loads(result)

        assert parsed["success"] is True
        assert parsed["data"]["execution_fidelity"] == 0.9

    @patch("src.core.base.context.get_context")
    def test_check_prediction_accuracy_execute(
        self, mock_get_ctx, runner_tools, mock_evolution_engine
    ):
        """测试 CheckPredictionAccuracyTool 执行"""
        mock_ctx = MagicMock()
        mock_ctx.evolution_engine = mock_evolution_engine
        mock_get_ctx.return_value = mock_ctx

        outcome = OutcomeRecord(
            outcome_id="out_test001",
            decision_id="dec_test001",
            outcome_timestamp=datetime(2026, 5, 20, 10, 0, 0),
            actual_vdot=46.0,
            actual_injury=False,
            execution_fidelity=None,
            user_feedback_score=None,
            user_feedback_text=None,
            prediction_error=2.0,
            prediction_direction="accurate",
            session_id=None,
        )
        stats = PredictionAccuracyStats(
            mae=1.5, total_pairs=8, overestimate_rate=0.2, underestimate_rate=0.1
        )
        mock_evolution_engine.check_prediction_accuracy.return_value = (outcome, stats)

        tool = CheckPredictionAccuracyToolDirect(runner_tools)

        result = asyncio.run(tool.execute(decision_id="dec_test001", actual_vdot=46.0))
        parsed = json.loads(result)

        assert parsed["success"] is True
        assert parsed["data"]["prediction_direction"] == "accurate"
        assert parsed["data"]["mae"] == 1.5
        assert parsed["data"]["total_pairs"] == 8

    @patch("src.core.base.context.get_context")
    def test_get_decision_history_execute(
        self, mock_get_ctx, runner_tools, mock_evolution_engine
    ):
        """测试 GetDecisionHistoryTool 执行"""
        mock_ctx = MagicMock()
        mock_ctx.evolution_engine = mock_evolution_engine
        mock_get_ctx.return_value = mock_ctx

        decisions = [_make_decision_log("dec_001")]
        mock_evolution_engine.get_decision_history.return_value = decisions

        tool = GetDecisionHistoryToolDirect(runner_tools)

        result = asyncio.run(tool.execute(limit=10))
        parsed = json.loads(result)

        assert parsed["success"] is True
        assert len(parsed["data"]) == 1


# ---------------------------------------------------------------------------
# create_tools 注册测试
# ---------------------------------------------------------------------------


class TestCreateToolsRegistration:
    """create_tools 工厂函数注册测试"""

    def test_evolution_tools_registered(self, runner_tools):
        """测试决策追踪工具已注册到 create_tools"""
        tools = create_tools(runner_tools)
        tool_names = [t.name for t in tools]

        assert "record_feedback" in tool_names
        assert "check_plan_execution" in tool_names
        assert "check_prediction_accuracy" in tool_names
        assert "get_decision_history" in tool_names

    def test_tool_descriptions_exist(self):
        """测试决策追踪工具描述已添加"""
        assert "record_feedback" in TOOL_DESCRIPTIONS
        assert "check_plan_execution" in TOOL_DESCRIPTIONS
        assert "check_prediction_accuracy" in TOOL_DESCRIPTIONS
        assert "get_decision_history" in TOOL_DESCRIPTIONS


# ---------------------------------------------------------------------------
# _get_latest_vdot 测试
# ---------------------------------------------------------------------------


class TestGetLatestVdot:
    """_get_latest_vdot 辅助方法测试"""

    def test_success(self, runner_tools):
        """测试从最新session获取VDOT成功"""
        runner_tools.get_vdot_trend = MagicMock(
            return_value=[{"vdot": 45.2, "date": "2026-05-20"}]
        )
        result = runner_tools._get_latest_vdot()
        assert result == 45.2

    def test_empty_trend(self, runner_tools):
        """测试无VDOT趋势数据"""
        runner_tools.get_vdot_trend = MagicMock(return_value=[])
        result = runner_tools._get_latest_vdot()
        assert result == 0.0

    def test_none_vdot(self, runner_tools):
        """测试VDOT为None"""
        runner_tools.get_vdot_trend = MagicMock(return_value=[{"vdot": None}])
        result = runner_tools._get_latest_vdot()
        assert result == 0.0

    def test_exception(self, runner_tools):
        """测试获取VDOT异常"""
        runner_tools.get_vdot_trend = MagicMock(side_effect=Exception("存储错误"))
        result = runner_tools._get_latest_vdot()
        assert result == 0.0


# ---------------------------------------------------------------------------
# v0.25 工具类属性测试
# ---------------------------------------------------------------------------


class TestV025ToolProperties:
    """v0.25工具类属性测试"""

    def test_check_evolution_triggers_tool_name(self, runner_tools):
        """测试 CheckEvolutionTriggersTool 名称"""
        tool = CheckEvolutionTriggersToolDirect(runner_tools)
        assert tool.name == "check_evolution_triggers"

    def test_check_evolution_triggers_tool_description(self, runner_tools):
        """测试 CheckEvolutionTriggersTool 描述"""
        tool = CheckEvolutionTriggersToolDirect(runner_tools)
        assert "进化触发条件" in tool.description

    def test_check_evolution_triggers_tool_parameters(self, runner_tools):
        """测试 CheckEvolutionTriggersTool 参数（无必填参数）"""
        tool = CheckEvolutionTriggersToolDirect(runner_tools)
        params = tool.parameters
        assert "properties" in params
        # 无必填参数
        assert "required" not in params or len(params.get("required", [])) == 0

    def test_get_evolution_report_tool_name(self, runner_tools):
        """测试 GetEvolutionReportTool 名称"""
        tool = GetEvolutionReportToolDirect(runner_tools)
        assert tool.name == "get_evolution_report"

    def test_get_evolution_report_tool_description(self, runner_tools):
        """测试 GetEvolutionReportTool 描述"""
        tool = GetEvolutionReportToolDirect(runner_tools)
        assert "进化报告" in tool.description

    def test_get_evolution_report_tool_parameters(self, runner_tools):
        """测试 GetEvolutionReportTool 参数"""
        tool = GetEvolutionReportToolDirect(runner_tools)
        params = tool.parameters
        assert "month" in params["properties"]

    def test_adjust_prompt_params_tool_name(self, runner_tools):
        """测试 AdjustPromptParamsTool 名称"""
        tool = AdjustPromptParamsToolDirect(runner_tools)
        assert tool.name == "adjust_prompt_params"

    def test_adjust_prompt_params_tool_description(self, runner_tools):
        """测试 AdjustPromptParamsTool 描述"""
        tool = AdjustPromptParamsToolDirect(runner_tools)
        assert "提示参数" in tool.description

    def test_adjust_prompt_params_tool_parameters(self, runner_tools):
        """测试 AdjustPromptParamsTool 参数"""
        tool = AdjustPromptParamsToolDirect(runner_tools)
        params = tool.parameters
        assert "tone" in params["properties"]
        assert "detail" in params["properties"]
        assert "aggressive" in params["properties"]
        assert "data_driven" in params["properties"]


# ---------------------------------------------------------------------------
# v0.25 RunnerTools 方法测试
# ---------------------------------------------------------------------------


def _make_trigger_check_result() -> TriggerCheckResult:
    """构造测试用 TriggerCheckResult"""
    return TriggerCheckResult(
        checked_at=datetime(2026, 5, 22, 10, 0, 0),
        triggered_actions=[],
        skipped_conditions=[{"condition": "vdot_error", "reason": "数据不足"}],
    )


def _make_evolution_report() -> EvolutionReport:
    """构造测试用 EvolutionReport"""
    return EvolutionReport(
        report_id="rpt_test001",
        month="2026-05",
        generated_at=datetime(2026, 5, 22, 10, 0, 0),
        total_decisions=42,
        prediction_accuracy_trend=[],
        decision_acceptance_rate=0.75,
        model_versions={"vdot": "v1.0"},
        personalization_degree=0.6,
        evolution_actions_count=3,
        last_evolution_time=None,
        calibration_summary={},
        prompt_tuning_summary={},
        recommendations=["继续积累数据"],
    )


def _make_prompt_tuning_params() -> PromptTuningParams:
    """构造测试用 PromptTuningParams"""
    return PromptTuningParams(
        tone_intensity=0.7,
        detail_level_score=0.8,
        recommendation_aggressiveness=0.3,
        data_driven_weight=0.6,
        last_updated=datetime(2026, 5, 22, 10, 0, 0),
        update_count=1,
    )


class TestCheckEvolutionTriggers:
    """check_evolution_triggers 方法测试"""

    @patch("src.core.base.context.get_context")
    def test_success(self, mock_get_ctx, runner_tools, mock_evolution_engine):
        """测试检查进化触发条件成功"""
        mock_ctx = MagicMock()
        mock_ctx.evolution_engine = mock_evolution_engine
        mock_get_ctx.return_value = mock_ctx

        trigger_result = _make_trigger_check_result()
        mock_evolution_engine.check_evolution_triggers.return_value = trigger_result

        result = runner_tools.check_evolution_triggers()

        assert result["success"] is True
        assert "checked_at" in result["data"]
        assert result["data"]["skipped_conditions"] == [
            {"condition": "vdot_error", "reason": "数据不足"}
        ]
        mock_evolution_engine.check_evolution_triggers.assert_called_once()

    @patch("src.core.base.context.get_context")
    def test_runtime_error_component_not_injected(
        self, mock_get_ctx, runner_tools, mock_evolution_engine
    ):
        """测试v0.25组件未注入时优雅处理"""
        mock_ctx = MagicMock()
        mock_ctx.evolution_engine = mock_evolution_engine
        mock_get_ctx.return_value = mock_ctx

        mock_evolution_engine.check_evolution_triggers.side_effect = RuntimeError(
            "请先初始化v0.25组件"
        )

        result = runner_tools.check_evolution_triggers()

        assert result["success"] is False
        assert "v0.25组件" in result["error"]

    @patch("src.core.base.context.get_context")
    def test_nanobot_runner_error(
        self, mock_get_ctx, runner_tools, mock_evolution_engine
    ):
        """测试NanobotRunnerError异常"""
        mock_ctx = MagicMock()
        mock_ctx.evolution_engine = mock_evolution_engine
        mock_get_ctx.return_value = mock_ctx

        mock_evolution_engine.check_evolution_triggers.side_effect = NanobotRunnerError(
            "存储错误"
        )

        result = runner_tools.check_evolution_triggers()

        assert result["success"] is False
        assert "存储错误" in result["error"]


class TestGetEvolutionReport:
    """get_evolution_report 方法测试"""

    @patch("src.core.base.context.get_context")
    def test_success_default_month(
        self, mock_get_ctx, runner_tools, mock_evolution_engine
    ):
        """测试获取当月进化报告成功"""
        mock_ctx = MagicMock()
        mock_ctx.evolution_engine = mock_evolution_engine
        mock_get_ctx.return_value = mock_ctx

        report = _make_evolution_report()
        mock_evolution_engine.get_evolution_report.return_value = report

        result = runner_tools.get_evolution_report()

        assert result["success"] is True
        assert result["data"]["report_id"] == "rpt_test001"
        assert result["data"]["month"] == "2026-05"
        assert result["data"]["total_decisions"] == 42
        mock_evolution_engine.get_evolution_report.assert_called_once_with(None)

    @patch("src.core.base.context.get_context")
    def test_success_specific_month(
        self, mock_get_ctx, runner_tools, mock_evolution_engine
    ):
        """测试获取指定月份进化报告"""
        mock_ctx = MagicMock()
        mock_ctx.evolution_engine = mock_evolution_engine
        mock_get_ctx.return_value = mock_ctx

        report = _make_evolution_report()
        mock_evolution_engine.get_evolution_report.return_value = report

        result = runner_tools.get_evolution_report(month="2026-04")

        assert result["success"] is True
        mock_evolution_engine.get_evolution_report.assert_called_once_with("2026-04")

    @patch("src.core.base.context.get_context")
    def test_runtime_error_component_not_injected(
        self, mock_get_ctx, runner_tools, mock_evolution_engine
    ):
        """测试v0.25组件未注入时优雅处理"""
        mock_ctx = MagicMock()
        mock_ctx.evolution_engine = mock_evolution_engine
        mock_get_ctx.return_value = mock_ctx

        mock_evolution_engine.get_evolution_report.side_effect = RuntimeError(
            "请先初始化v0.25组件"
        )

        result = runner_tools.get_evolution_report()

        assert result["success"] is False
        assert "v0.25组件" in result["error"]


class TestAdjustPromptParams:
    """adjust_prompt_params 方法测试"""

    @patch("src.core.base.context.get_context")
    def test_success_all_params(
        self, mock_get_ctx, runner_tools, mock_evolution_engine
    ):
        """测试调整所有提示参数成功"""
        mock_ctx = MagicMock()
        mock_ctx.evolution_engine = mock_evolution_engine
        mock_get_ctx.return_value = mock_ctx

        params = _make_prompt_tuning_params()
        mock_evolution_engine.adjust_prompt_params.return_value = params

        result = runner_tools.adjust_prompt_params(
            tone=0.7, detail=0.8, aggressive=0.3, data_driven=0.6
        )

        assert result["success"] is True
        assert result["data"]["tone_intensity"] == 0.7
        assert result["data"]["detail_level_score"] == 0.8
        assert result["data"]["recommendation_aggressiveness"] == 0.3
        assert result["data"]["data_driven_weight"] == 0.6
        mock_evolution_engine.adjust_prompt_params.assert_called_once_with(
            tone=0.7, detail=0.8, aggressive=0.3, data_driven=0.6
        )

    @patch("src.core.base.context.get_context")
    def test_success_partial_params(
        self, mock_get_ctx, runner_tools, mock_evolution_engine
    ):
        """测试仅调整部分提示参数"""
        mock_ctx = MagicMock()
        mock_ctx.evolution_engine = mock_evolution_engine
        mock_get_ctx.return_value = mock_ctx

        params = _make_prompt_tuning_params()
        mock_evolution_engine.adjust_prompt_params.return_value = params

        result = runner_tools.adjust_prompt_params(tone=0.9)

        assert result["success"] is True
        mock_evolution_engine.adjust_prompt_params.assert_called_once_with(
            tone=0.9, detail=None, aggressive=None, data_driven=None
        )

    @patch("src.core.base.context.get_context")
    def test_runtime_error_component_not_injected(
        self, mock_get_ctx, runner_tools, mock_evolution_engine
    ):
        """测试v0.25组件未注入时优雅处理"""
        mock_ctx = MagicMock()
        mock_ctx.evolution_engine = mock_evolution_engine
        mock_get_ctx.return_value = mock_ctx

        mock_evolution_engine.adjust_prompt_params.side_effect = RuntimeError(
            "请先初始化v0.25组件"
        )

        result = runner_tools.adjust_prompt_params(tone=0.5)

        assert result["success"] is False
        assert "v0.25组件" in result["error"]

    @patch("src.core.base.context.get_context")
    def test_nanobot_runner_error(
        self, mock_get_ctx, runner_tools, mock_evolution_engine
    ):
        """测试NanobotRunnerError异常"""
        mock_ctx = MagicMock()
        mock_ctx.evolution_engine = mock_evolution_engine
        mock_get_ctx.return_value = mock_ctx

        mock_evolution_engine.adjust_prompt_params.side_effect = NanobotRunnerError(
            "参数无效"
        )

        result = runner_tools.adjust_prompt_params(tone=0.5)

        assert result["success"] is False
        assert "参数无效" in result["error"]


# ---------------------------------------------------------------------------
# v0.25 工具类 execute 测试
# ---------------------------------------------------------------------------


class TestV025ToolExecute:
    """v0.25工具类 execute 方法测试"""

    @patch("src.core.base.context.get_context")
    def test_check_evolution_triggers_execute(
        self, mock_get_ctx, runner_tools, mock_evolution_engine
    ):
        """测试 CheckEvolutionTriggersTool 执行"""
        mock_ctx = MagicMock()
        mock_ctx.evolution_engine = mock_evolution_engine
        mock_get_ctx.return_value = mock_ctx

        trigger_result = _make_trigger_check_result()
        mock_evolution_engine.check_evolution_triggers.return_value = trigger_result

        tool = CheckEvolutionTriggersToolDirect(runner_tools)

        result = asyncio.run(tool.execute())
        parsed = json.loads(result)

        assert parsed["success"] is True
        assert "checked_at" in parsed["data"]

    @patch("src.core.base.context.get_context")
    def test_get_evolution_report_execute(
        self, mock_get_ctx, runner_tools, mock_evolution_engine
    ):
        """测试 GetEvolutionReportTool 执行"""
        mock_ctx = MagicMock()
        mock_ctx.evolution_engine = mock_evolution_engine
        mock_get_ctx.return_value = mock_ctx

        report = _make_evolution_report()
        mock_evolution_engine.get_evolution_report.return_value = report

        tool = GetEvolutionReportToolDirect(runner_tools)

        result = asyncio.run(tool.execute(month="2026-05"))
        parsed = json.loads(result)

        assert parsed["success"] is True
        assert parsed["data"]["report_id"] == "rpt_test001"
        assert parsed["data"]["month"] == "2026-05"

    @patch("src.core.base.context.get_context")
    def test_adjust_prompt_params_execute(
        self, mock_get_ctx, runner_tools, mock_evolution_engine
    ):
        """测试 AdjustPromptParamsTool 执行"""
        mock_ctx = MagicMock()
        mock_ctx.evolution_engine = mock_evolution_engine
        mock_get_ctx.return_value = mock_ctx

        params = _make_prompt_tuning_params()
        mock_evolution_engine.adjust_prompt_params.return_value = params

        tool = AdjustPromptParamsToolDirect(runner_tools)

        result = asyncio.run(tool.execute(tone=0.7, detail=0.8))
        parsed = json.loads(result)

        assert parsed["success"] is True
        assert parsed["data"]["tone_intensity"] == 0.7
        assert parsed["data"]["detail_level_score"] == 0.8


# ---------------------------------------------------------------------------
# v0.25 create_tools 注册测试
# ---------------------------------------------------------------------------


class TestV025CreateToolsRegistration:
    """v0.25 create_tools 工厂函数注册测试"""

    def test_v025_tools_registered(self, runner_tools):
        """测试v0.25进化工具已注册到 create_tools"""
        tools = create_tools(runner_tools)
        tool_names = [t.name for t in tools]

        assert "check_evolution_triggers" in tool_names
        assert "get_evolution_report" in tool_names
        assert "adjust_prompt_params" in tool_names

    def test_v025_tool_descriptions_exist(self):
        """测试v0.25进化工具描述已添加"""
        assert "check_evolution_triggers" in TOOL_DESCRIPTIONS
        assert "get_evolution_report" in TOOL_DESCRIPTIONS
        assert "adjust_prompt_params" in TOOL_DESCRIPTIONS
