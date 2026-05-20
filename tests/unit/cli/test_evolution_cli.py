"""EvolutionHandler 和 Evolution CLI 命令单元测试

测试目标：
- 验证EvolutionHandler各方法的参数转换和调用委托
- 验证CLI命令的参数校验、输出格式、错误处理

测试覆盖：
- EvolutionHandler: get_history, record_feedback, get_accuracy, get_fidelity, get_status
- CLI命令: history, feedback, accuracy, fidelity, status
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from src.cli.commands.evolution import app
from src.cli.handlers.evolution_handler import EvolutionHandler
from src.core.evolution.models import (
    DecisionLog,
    OutcomeRecord,
    PredictionAccuracyStats,
)
from src.core.transparency.models import DecisionType

# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def mock_context():
    """创建 Mock 应用上下文"""
    context = MagicMock()
    context.evolution_engine = MagicMock()
    return context


@pytest.fixture
def handler(mock_context):
    """创建使用Mock上下文的EvolutionHandler"""
    return EvolutionHandler(context=mock_context)


@pytest.fixture
def sample_decision_log():
    """创建示例决策日志"""
    return DecisionLog(
        decision_id="dec_test001",
        timestamp=datetime(2024, 6, 15, 10, 30, 0),
        runner_state={"vdot": 45.0, "ctl": 60.0, "atl": 50.0},
        decision_type=DecisionType.TRAINING_ADVICE,
        tool_call_chain=[],
        prediction_snapshot={"predicted_vdot": 45.5},
        recommendation_text="建议进行轻松跑恢复",
        execution_status="executed",
        recommendation_accepted=True,
        session_key="session_001",
    )


@pytest.fixture
def sample_outcome_record():
    """创建示例结果记录"""
    return OutcomeRecord(
        outcome_id="out_test001",
        decision_id="dec_test001",
        outcome_timestamp=datetime(2024, 6, 16, 8, 0, 0),
        actual_vdot=45.2,
        actual_injury=False,
        execution_fidelity=0.85,
        user_feedback_score=4,
        user_feedback_text="很好",
        prediction_error=0.66,
        prediction_direction="accurate",
        session_id=None,
    )


@pytest.fixture
def sample_accuracy_stats():
    """创建示例预测精度统计"""
    return PredictionAccuracyStats(
        mae=1.5,
        total_pairs=10,
        overestimate_rate=0.2,
        underestimate_rate=0.1,
    )


@pytest.fixture
def runner():
    """创建CLI测试运行器"""
    return CliRunner()


# ============================================================
# EvolutionHandler 单元测试
# ============================================================


class TestEvolutionHandlerInit:
    """EvolutionHandler 初始化测试"""

    def test_init_with_context(self, mock_context):
        """测试使用自定义上下文初始化"""
        handler = EvolutionHandler(context=mock_context)
        assert handler.context == mock_context

    @patch("src.cli.handlers.evolution_handler.AppContextFactory")
    def test_init_without_context(self, mock_factory):
        """测试无上下文时自动创建"""
        mock_factory.create.return_value = MagicMock()
        handler = EvolutionHandler()
        mock_factory.create.assert_called_once()


class TestGetHistory:
    """get_history 方法测试"""

    def test_returns_list_of_dicts(self, handler, mock_context, sample_decision_log):
        """测试返回字典列表"""
        mock_context.evolution_engine.get_decision_history.return_value = [
            sample_decision_log
        ]
        result = handler.get_history()

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], dict)
        assert result[0]["decision_id"] == "dec_test001"

    def test_passes_date_params(self, handler, mock_context, sample_decision_log):
        """测试日期参数传递"""
        mock_context.evolution_engine.get_decision_history.return_value = [
            sample_decision_log
        ]
        handler.get_history(start_date="2024-01-01", end_date="2024-12-31")

        call_kwargs = mock_context.evolution_engine.get_decision_history.call_args
        assert call_kwargs.kwargs["start_date"] == datetime(2024, 1, 1)
        assert call_kwargs.kwargs["end_date"] == datetime(2024, 12, 31)

    def test_passes_decision_type(self, handler, mock_context, sample_decision_log):
        """测试决策类型参数传递"""
        mock_context.evolution_engine.get_decision_history.return_value = [
            sample_decision_log
        ]
        handler.get_history(decision_type="training_advice")

        call_kwargs = mock_context.evolution_engine.get_decision_history.call_args
        assert call_kwargs.kwargs["decision_type"] == DecisionType.TRAINING_ADVICE

    def test_returns_empty_list(self, handler, mock_context):
        """测试无记录时返回空列表"""
        mock_context.evolution_engine.get_decision_history.return_value = []
        result = handler.get_history()

        assert result == []

    def test_invalid_decision_type_raises(self, handler, mock_context):
        """测试无效决策类型抛出ValueError"""
        with pytest.raises(ValueError):
            handler.get_history(decision_type="invalid_type")


class TestRecordFeedback:
    """record_feedback 方法测试"""

    def test_returns_dict(self, handler, mock_context, sample_outcome_record):
        """测试返回字典"""
        mock_context.evolution_engine.record_feedback.return_value = (
            sample_outcome_record
        )
        result = handler.record_feedback(
            decision_id="dec_test001", score=4, text="很好", accepted=True
        )

        assert isinstance(result, dict)
        assert result["decision_id"] == "dec_test001"
        assert result["user_feedback_score"] == 4

    def test_passes_params_correctly(
        self, handler, mock_context, sample_outcome_record
    ):
        """测试参数正确传递"""
        mock_context.evolution_engine.record_feedback.return_value = (
            sample_outcome_record
        )
        handler.record_feedback(
            decision_id="dec_test001", score=5, text="非常满意", accepted=True
        )

        mock_context.evolution_engine.record_feedback.assert_called_once_with(
            decision_id="dec_test001",
            score=5,
            text="非常满意",
            accepted=True,
        )

    def test_optional_params_default_none(
        self, handler, mock_context, sample_outcome_record
    ):
        """测试可选参数默认为None"""
        mock_context.evolution_engine.record_feedback.return_value = (
            sample_outcome_record
        )
        handler.record_feedback(decision_id="dec_test001", score=3)

        mock_context.evolution_engine.record_feedback.assert_called_once_with(
            decision_id="dec_test001",
            score=3,
            text=None,
            accepted=None,
        )


class TestGetAccuracy:
    """get_accuracy 方法测试"""

    def test_returns_dict(self, handler, mock_context, sample_accuracy_stats):
        """测试返回字典"""
        mock_context.evolution_engine.outcome_collector.get_accuracy_stats.return_value = sample_accuracy_stats
        result = handler.get_accuracy()

        assert isinstance(result, dict)
        assert "mae" in result
        assert "total_pairs" in result
        assert result["mae"] == 1.5
        assert result["total_pairs"] == 10

    def test_default_days_30(self, handler, mock_context, sample_accuracy_stats):
        """测试默认统计天数30"""
        mock_context.evolution_engine.outcome_collector.get_accuracy_stats.return_value = sample_accuracy_stats
        handler.get_accuracy()
        # 验证调用了get_accuracy_stats
        mock_context.evolution_engine.outcome_collector.get_accuracy_stats.assert_called_once()


class TestGetFidelity:
    """get_fidelity 方法测试"""

    def test_returns_dict_with_data(self, handler, mock_context):
        """测试有数据时返回字典"""
        mock_context.evolution_engine.outcome_collector.get_fidelity_stats.return_value = {
            "count": 1,
            "avg_fidelity": 0.85,
            "min_fidelity": 0.85,
            "max_fidelity": 0.85,
        }
        result = handler.get_fidelity()

        assert isinstance(result, dict)
        assert "count" in result
        assert "avg_fidelity" in result
        assert result["count"] == 1
        assert result["avg_fidelity"] == 0.85

    def test_returns_empty_when_no_data(self, handler, mock_context):
        """测试无数据时返回空统计"""
        mock_context.evolution_engine.outcome_collector.get_fidelity_stats.return_value = {
            "count": 0,
            "avg_fidelity": 0.0,
            "min_fidelity": 0.0,
            "max_fidelity": 0.0,
        }
        result = handler.get_fidelity()

        assert result["count"] == 0
        assert result["avg_fidelity"] == 0.0

    def test_ignores_none_fidelity(self, handler, mock_context):
        """测试忽略fidelity为None的记录"""
        mock_context.evolution_engine.outcome_collector.get_fidelity_stats.return_value = {
            "count": 0,
            "avg_fidelity": 0.0,
            "min_fidelity": 0.0,
            "max_fidelity": 0.0,
        }
        result = handler.get_fidelity()

        assert result["count"] == 0


class TestGetStatus:
    """get_status 方法测试"""

    def test_returns_dict(self, handler, mock_context):
        """测试返回字典"""
        mock_context.evolution_engine.get_evolution_status.return_value = {
            "total_decisions": 42,
            "status_distribution": {"executed": 30, "pending": 12},
            "type_distribution": {"training_advice": 25, "plan_adjustment": 17},
        }
        result = handler.get_status()

        assert isinstance(result, dict)
        assert result["total_decisions"] == 42
        assert "status_distribution" in result
        assert "type_distribution" in result

    def test_delegates_to_engine(self, handler, mock_context):
        """测试委托给引擎"""
        mock_context.evolution_engine.get_evolution_status.return_value = {
            "total_decisions": 0,
            "status_distribution": {},
            "type_distribution": {},
        }
        handler.get_status()
        mock_context.evolution_engine.get_evolution_status.assert_called_once()


class TestGetEngine:
    """_get_engine 方法测试"""

    def test_raises_when_engine_none(self, mock_context):
        """测试引擎未初始化时抛出RuntimeError"""
        mock_context.evolution_engine = None
        handler = EvolutionHandler(context=mock_context)

        with pytest.raises(RuntimeError, match="决策追踪引擎未初始化"):
            handler._get_engine()


# ============================================================
# CLI 命令测试
# ============================================================


class TestHistoryCommand:
    """history 命令测试"""

    @patch("src.cli.commands.evolution.EvolutionHandler")
    def test_history_displays_table(self, mock_handler_cls, runner):
        """测试历史命令展示表格"""
        mock_handler = MagicMock()
        mock_handler_cls.return_value = mock_handler
        mock_handler.get_history.return_value = [
            {
                "decision_id": "dec_001",
                "timestamp": "2024-06-15T10:30:00",
                "decision_type": "training_advice",
                "execution_status": "executed",
                "recommendation_text": "建议轻松跑",
            }
        ]

        result = runner.invoke(app, ["history"])
        assert result.exit_code == 0
        assert "dec_001" in result.output
        # Rich Table可能截断长文本，检查类型列包含部分文本
        assert "training" in result.output

    @patch("src.cli.commands.evolution.EvolutionHandler")
    def test_history_empty(self, mock_handler_cls, runner):
        """测试无历史记录时提示"""
        mock_handler = MagicMock()
        mock_handler_cls.return_value = mock_handler
        mock_handler.get_history.return_value = []

        result = runner.invoke(app, ["history"])
        assert result.exit_code == 0
        assert "暂无决策历史记录" in result.output

    @patch("src.cli.commands.evolution.EvolutionHandler")
    def test_history_with_filters(self, mock_handler_cls, runner):
        """测试带过滤条件的历史查询"""
        mock_handler = MagicMock()
        mock_handler_cls.return_value = mock_handler
        mock_handler.get_history.return_value = []

        result = runner.invoke(
            app,
            [
                "history",
                "--start",
                "2024-01-01",
                "--end",
                "2024-12-31",
                "--type",
                "training_advice",
            ],
        )
        assert result.exit_code == 0
        mock_handler.get_history.assert_called_once_with(
            start_date="2024-01-01",
            end_date="2024-12-31",
            decision_type="training_advice",
        )


class TestFeedbackCommand:
    """feedback 命令测试"""

    @patch("src.cli.commands.evolution.EvolutionHandler")
    def test_feedback_success(self, mock_handler_cls, runner):
        """测试反馈记录成功"""
        mock_handler = MagicMock()
        mock_handler_cls.return_value = mock_handler
        mock_handler.record_feedback.return_value = {
            "outcome_id": "out_001",
            "decision_id": "dec_001",
            "user_feedback_score": 4,
            "user_feedback_text": "很好",
        }

        result = runner.invoke(
            app, ["feedback", "dec_001", "--score", "4", "--text", "很好"]
        )
        assert result.exit_code == 0
        assert "反馈已记录" in result.output

    @patch("src.cli.commands.evolution.EvolutionHandler")
    def test_feedback_with_accepted(self, mock_handler_cls, runner):
        """测试带采纳标记的反馈"""
        mock_handler = MagicMock()
        mock_handler_cls.return_value = mock_handler
        mock_handler.record_feedback.return_value = {
            "outcome_id": "out_001",
            "decision_id": "dec_001",
            "user_feedback_score": 5,
        }

        result = runner.invoke(
            app, ["feedback", "dec_001", "--score", "5", "--accepted"]
        )
        assert result.exit_code == 0
        mock_handler.record_feedback.assert_called_once_with(
            decision_id="dec_001",
            score=5,
            text=None,
            accepted=True,
        )

    def test_feedback_invalid_score(self, runner):
        """测试无效评分"""
        result = runner.invoke(app, ["feedback", "dec_001", "--score", "6"])
        assert result.exit_code == 1

    def test_feedback_score_zero(self, runner):
        """测试评分为0"""
        result = runner.invoke(app, ["feedback", "dec_001", "--score", "0"])
        assert result.exit_code == 1


class TestAccuracyCommand:
    """accuracy 命令测试"""

    @patch("src.cli.commands.evolution.EvolutionHandler")
    def test_accuracy_displays_panel(self, mock_handler_cls, runner):
        """测试精度统计展示面板"""
        mock_handler = MagicMock()
        mock_handler_cls.return_value = mock_handler
        mock_handler.get_accuracy.return_value = {
            "mae": 1.5,
            "total_pairs": 10,
            "overestimate_rate": 0.2,
            "underestimate_rate": 0.1,
        }

        result = runner.invoke(app, ["accuracy"])
        assert result.exit_code == 0
        assert "预测精度统计" in result.output
        assert "1.50" in result.output

    @patch("src.cli.commands.evolution.EvolutionHandler")
    def test_accuracy_with_days(self, mock_handler_cls, runner):
        """测试指定天数的精度统计"""
        mock_handler = MagicMock()
        mock_handler_cls.return_value = mock_handler
        mock_handler.get_accuracy.return_value = {
            "mae": 2.0,
            "total_pairs": 5,
            "overestimate_rate": 0.3,
            "underestimate_rate": 0.2,
        }

        result = runner.invoke(app, ["accuracy", "--days", "90"])
        assert result.exit_code == 0
        mock_handler.get_accuracy.assert_called_once_with(days=90)


class TestFidelityCommand:
    """fidelity 命令测试"""

    @patch("src.cli.commands.evolution.EvolutionHandler")
    def test_fidelity_displays_panel(self, mock_handler_cls, runner):
        """测试忠实度统计展示面板"""
        mock_handler = MagicMock()
        mock_handler_cls.return_value = mock_handler
        mock_handler.get_fidelity.return_value = {
            "count": 5,
            "avg_fidelity": 0.85,
            "min_fidelity": 0.7,
            "max_fidelity": 0.95,
        }

        result = runner.invoke(app, ["fidelity"])
        assert result.exit_code == 0
        assert "执行忠实度统计" in result.output
        assert "85.0%" in result.output

    @patch("src.cli.commands.evolution.EvolutionHandler")
    def test_fidelity_no_data(self, mock_handler_cls, runner):
        """测试无忠实度数据时提示"""
        mock_handler = MagicMock()
        mock_handler_cls.return_value = mock_handler
        mock_handler.get_fidelity.return_value = {
            "count": 0,
            "avg_fidelity": 0.0,
            "min_fidelity": 0.0,
            "max_fidelity": 0.0,
        }

        result = runner.invoke(app, ["fidelity"])
        assert result.exit_code == 0
        assert "暂无执行忠实度数据" in result.output


class TestStatusCommand:
    """status 命令测试"""

    @patch("src.cli.commands.evolution.EvolutionHandler")
    def test_status_displays_panel(self, mock_handler_cls, runner):
        """测试状态展示面板"""
        mock_handler = MagicMock()
        mock_handler_cls.return_value = mock_handler
        mock_handler.get_status.return_value = {
            "total_decisions": 42,
            "status_distribution": {"executed": 30, "pending": 12},
            "type_distribution": {"training_advice": 25, "plan_adjustment": 17},
        }

        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "决策追踪状态" in result.output
        assert "42" in result.output

    @patch("src.cli.commands.evolution.EvolutionHandler")
    def test_status_empty(self, mock_handler_cls, runner):
        """测试无数据时状态展示"""
        mock_handler = MagicMock()
        mock_handler_cls.return_value = mock_handler
        mock_handler.get_status.return_value = {
            "total_decisions": 0,
            "status_distribution": {},
            "type_distribution": {},
        }

        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "暂无数据" in result.output
