# 决策追踪引擎（薄编排层）
# 委托DecisionLogger和OutcomeCollector完成决策记录与结果回填
# v0.24新增: 委托ResponseAnalyzer/CalibrationEngine/ModelEvolver完成个性化学习

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.core.base.logger import get_logger
from src.core.evolution.decision_logger import DecisionLogger
from src.core.evolution.models import (
    CalibrationProfile,
    CalibrationReport,
    DecisionLog,
    EvolutionAction,
    EvolutionReport,
    ModelEvolutionResult,
    OutcomeRecord,
    PredictionAccuracyStats,
    PromptTuningParams,
    TrainingResponseReport,
    TriggerCheckResult,
)
from src.core.evolution.outcome_collector import OutcomeCollector
from src.core.plan.ask_user_confirm import ConfirmPrompt

if TYPE_CHECKING:
    from src.core.evolution.calibration_engine import CalibrationEngine
    from src.core.evolution.model_evolver import ModelEvolver
    from src.core.evolution.response_analyzer import ResponseAnalyzer

logger = get_logger(__name__)


class EvolutionEngine:
    """决策追踪引擎（薄编排层）

    v0.24新增: ResponseAnalyzer/CalibrationEngine/ModelEvolver可选注入，
    未注入时调用v0.24方法抛RuntimeError。
    """

    def __init__(
        self,
        decision_logger: DecisionLogger,
        outcome_collector: OutcomeCollector,
        response_analyzer: ResponseAnalyzer | None = None,
        calibration_engine: CalibrationEngine | None = None,
        model_evolver: ModelEvolver | None = None,
        evolution_controller: Any = None,
        prompt_tuner: Any = None,
        evolution_reporter: Any = None,
    ) -> None:
        self._decision_logger = decision_logger
        self._outcome_collector = outcome_collector
        self._response_analyzer = response_analyzer
        self._calibration_engine = calibration_engine
        self._model_evolver = model_evolver
        self._evolution_controller = evolution_controller
        self._prompt_tuner = prompt_tuner
        self._evolution_reporter = evolution_reporter

    @property
    def decision_logger(self) -> DecisionLogger:
        return self._decision_logger

    @property
    def outcome_collector(self) -> OutcomeCollector:
        return self._outcome_collector

    def _require_v024_component(self, component_name: str) -> None:
        """校验v0.24组件是否已注入"""
        component_map = {
            "response_analyzer": self._response_analyzer,
            "calibration_engine": self._calibration_engine,
            "model_evolver": self._model_evolver,
        }
        if component_map.get(component_name) is None:
            raise RuntimeError("请先初始化v0.24组件")

    # ---- v0.23 方法（保持不变） ----

    def log_decision(self, decision: DecisionLog) -> str:
        return self._decision_logger.log_decision(decision)

    def check_plan_execution(self, decision_id: str) -> OutcomeRecord:
        return self._outcome_collector.check_plan_execution(decision_id)

    def check_prediction_accuracy(
        self, decision_id: str, actual_vdot: float
    ) -> tuple[OutcomeRecord, PredictionAccuracyStats]:
        return self._outcome_collector.check_prediction_accuracy(
            decision_id, actual_vdot
        )

    def record_feedback(
        self,
        decision_id: str,
        score: int,
        text: str | None = None,
        accepted: bool | None = None,
    ) -> OutcomeRecord:
        return self._outcome_collector.record_feedback(
            decision_id, score, text=text, accepted=accepted
        )

    def get_decision_history(
        self,
        start_date: Any = None,
        end_date: Any = None,
        decision_type: Any = None,
        limit: int = 100,
    ) -> list[DecisionLog]:
        return self._decision_logger.get_decision_history(
            start_date=start_date,
            end_date=end_date,
            decision_type=decision_type,
            limit=limit,
        )

    def generate_feedback_prompt(self, decision_id: str) -> ConfirmPrompt:
        return self._outcome_collector.generate_feedback_prompt(decision_id)

    # ---- v0.24 新增方法 ----

    def analyze_training_response(self, months: int = 6) -> TrainingResponseReport:
        """分析训练响应性"""
        self._require_v024_component("response_analyzer")
        assert self._response_analyzer is not None
        return self._response_analyzer.analyze(months)

    def run_calibration(
        self,
        model_type: str,
        override_pairs: list[tuple[float, float]] | None = None,
    ) -> CalibrationReport:
        """执行校准"""
        self._require_v024_component("calibration_engine")
        assert self._calibration_engine is not None
        return self._calibration_engine.run_calibration(
            model_type, override_pairs=override_pairs
        )

    def get_calibration_status(
        self, model_type: str | None = None
    ) -> CalibrationProfile | dict[str, Any]:
        """获取校准状态"""
        self._require_v024_component("calibration_engine")
        assert self._calibration_engine is not None
        if model_type is not None:
            return self._calibration_engine.get_profile(model_type)
        status: dict[str, Any] = {}
        for mt in ["vdot", "injury", "training_response"]:
            profile = self._calibration_engine.get_profile(mt)
            status[mt] = profile.to_dict()
        return status

    def evolve_model(self, model_type: str) -> ModelEvolutionResult:
        """进化模型"""
        self._require_v024_component("model_evolver")
        assert self._model_evolver is not None
        evolve_methods = {
            "vdot": self._model_evolver.evolve_vdot_model,
            "injury": self._model_evolver.evolve_injury_model,
            "training_response": self._model_evolver.evolve_training_response_model,
        }
        method = evolve_methods.get(model_type)
        if method is None:
            raise ValueError(f"不支持的模型类型: {model_type}")
        return method()

    def apply_calibration_to_prediction(
        self, model_type: str, raw_value: float
    ) -> float:
        """应用校准到预测值: corrected = raw_value * scale"""
        self._require_v024_component("calibration_engine")
        assert self._calibration_engine is not None
        return self._calibration_engine.apply_calibration(model_type, raw_value)

    def get_evolution_status(self) -> dict[str, Any]:
        """获取决策追踪整体状态（v0.24新增calibration_status字段，v0.25新增evolution_status字段）"""
        all_decisions = self._decision_logger.get_decision_history(limit=10000)

        status_dist: dict[str, int] = {}
        for d in all_decisions:
            status = d.execution_status
            status_dist[status] = status_dist.get(status, 0) + 1

        type_dist: dict[str, int] = {}
        for d in all_decisions:
            dtype = d.decision_type.value
            type_dist[dtype] = type_dist.get(dtype, 0) + 1

        pairs = self._outcome_collector.get_decision_outcome_pairs()
        total_decisions = len(all_decisions)

        outcome_fill_rate = len(pairs) / total_decisions if total_decisions > 0 else 0.0

        fidelities = [
            p[1].execution_fidelity
            for p in pairs
            if p[1].execution_fidelity is not None
        ]
        avg_fidelity = sum(fidelities) / len(fidelities) if fidelities else 0.0

        prediction_errors = [
            p[1].prediction_error for p in pairs if p[1].prediction_error is not None
        ]
        avg_prediction_error = (
            sum(prediction_errors) / len(prediction_errors)
            if prediction_errors
            else 0.0
        )

        feedback_scores = [
            p[1].user_feedback_score
            for p in pairs
            if p[1].user_feedback_score is not None
        ]
        feedback_collection_rate = (
            len(feedback_scores) / total_decisions if total_decisions > 0 else 0.0
        )

        # v0.24新增: calibration_status
        calibration_status: dict[str, Any] = {}
        if self._calibration_engine is not None:
            for mt in ["vdot", "injury", "training_response"]:
                profile = self._calibration_engine.get_profile(mt)
                calibration_status[mt] = profile.to_dict()

        # v0.25新增: evolution_status
        evolution_status: dict[str, Any] = {}
        if self._evolution_controller is not None:
            evolution_status["evolution_actions_count"] = 0
        if self._prompt_tuner is not None:
            params = self._prompt_tuner.get_params()
            evolution_status["prompt_tuning"] = params.to_dict()
            tuning_degree = (
                abs(params.tone_intensity - 0.5)
                + abs(params.detail_level_score - 0.5)
                + abs(params.recommendation_aggressiveness - 0.5)
            ) / 3.0
            evolution_status["personalization_degree"] = round(tuning_degree, 4)

        return {
            "total_decisions": total_decisions,
            "status_distribution": status_dist,
            "type_distribution": type_dist,
            "outcome_fill_rate": round(outcome_fill_rate, 4),
            "avg_fidelity": round(avg_fidelity, 4),
            "avg_prediction_error": round(avg_prediction_error, 4),
            "feedback_collection_rate": round(feedback_collection_rate, 4),
            "calibration_status": calibration_status,
            "evolution_status": evolution_status,
        }

    # ---- v0.25 新增方法 ----

    def _require_v025_component(self, component_name: str) -> None:
        """校验v0.25组件是否已注入"""
        component_map = {
            "evolution_controller": self._evolution_controller,
            "prompt_tuner": self._prompt_tuner,
            "evolution_reporter": self._evolution_reporter,
        }
        if component_map.get(component_name) is None:
            raise RuntimeError("请先初始化v0.25组件")

    def check_evolution_triggers(self) -> TriggerCheckResult:
        """检查进化触发条件（委托给EvolutionController）"""
        self._require_v025_component("evolution_controller")
        assert self._evolution_controller is not None
        return self._evolution_controller.check_triggers()

    def execute_evolution_action(self, action: EvolutionAction) -> EvolutionAction:
        """执行进化动作（委托给EvolutionController）"""
        self._require_v025_component("evolution_controller")
        assert self._evolution_controller is not None
        return self._evolution_controller.execute_action(action)

    def get_evolution_report(self, month: str | None = None) -> EvolutionReport:
        """获取月度进化报告（委托给EvolutionReporter）"""
        self._require_v025_component("evolution_reporter")
        assert self._evolution_reporter is not None
        return self._evolution_reporter.generate_report(month)

    def adjust_prompt_params(
        self,
        tone: float | None = None,
        detail: float | None = None,
        aggressive: float | None = None,
        data_driven: float | None = None,
    ) -> PromptTuningParams:
        """手动调整提示参数（委托给PromptTuner）"""
        self._require_v025_component("prompt_tuner")
        assert self._prompt_tuner is not None
        return self._prompt_tuner.update_params(
            tone=tone, detail=detail, aggressive=aggressive, data_driven=data_driven
        )

    def get_prompt_tuning_params(self) -> PromptTuningParams:
        """获取当前提示调优参数（委托给PromptTuner）"""
        self._require_v025_component("prompt_tuner")
        assert self._prompt_tuner is not None
        return self._prompt_tuner.get_params()

    def reset_prompt_tuning(self) -> PromptTuningParams:
        """重置提示调优参数为默认值（委托给PromptTuner）"""
        self._require_v025_component("prompt_tuner")
        assert self._prompt_tuner is not None
        return self._prompt_tuner.reset_to_default()
