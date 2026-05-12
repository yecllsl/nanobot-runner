from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from src.core.twin.models import (
    BodySignalDimension,
    DataQuality,
    FitnessDimension,
    HypotheticalPlan,
    IntensityDistribution,
    LoadDimension,
    PlanComparison,
    PlanComparisonMetrics,
    RiskDimension,
    RunnerStateVector,
    SimulationResult,
    StateVectorCache,
    TrainingPatternDimension,
    TwinEngineError,
    WeeklyPlanSpec,
)
from src.core.twin.state_vector_builder import StateVectorBuilder
from src.core.twin.whatif_simulator import WhatIfSimulator

if TYPE_CHECKING:
    from src.core.plan.plan_manager import PlanManager
    from src.core.prediction.baselines.banister_ir import BanisterIRModel
    from src.core.prediction.prediction_engine import PredictionEngine

logger = logging.getLogger(__name__)

CACHE_DIR_NAME = "twin"
CACHE_FILE_NAME = "state_vector.json"


class DigitalTwinEngine:
    """数字孪生引擎 — 薄编排层

    聚合 StateVectorBuilder + WhatIfSimulator，对外提供三个核心方法：
    - get_current_snapshot(): 获取当前跑者状态快照（含TTL=24h缓存）
    - simulate(): What-If 推演
    - compare_plans(): 多计划对比

    依赖注入（架构7.5.4节）：
    - state_vector_builder: 5维状态向量构建器（必需）
    - plan_manager: 训练计划管理器（可选，支持系统计划引用）
    - banister_model: BanisterIRModel（可选，传递给WhatIfSimulator的L2模式）
    - prediction_engine: PredictionEngine（可选，传递给WhatIfSimulator的L1模式）
    """

    def __init__(
        self,
        state_vector_builder: StateVectorBuilder,
        plan_manager: PlanManager | None = None,
        banister_model: BanisterIRModel | None = None,
        prediction_engine: PredictionEngine | None = None,
        cache_dir: Path | None = None,
    ) -> None:
        self._builder = state_vector_builder
        self._plan_manager = plan_manager
        self._simulator = WhatIfSimulator(
            banister_model=banister_model,
            prediction_engine=prediction_engine,
        )
        self._cache_dir = cache_dir
        self._cache: StateVectorCache | None = None

    def get_current_snapshot(self) -> RunnerStateVector:
        """获取当前5维跑者状态向量（含TTL=24h缓存，架构7.1节）"""
        if self._cache is not None and not self._cache.is_expired():
            return self._cache.state

        self._cache = self._load_cache_from_disk()
        if self._cache is not None and not self._cache.is_expired():
            return self._cache.state

        state = self._builder.build()
        self._cache = StateVectorCache(
            state=state,
            created_at=state.snapshot_date + "T00:00:00",
            ttl_hours=24,
        )
        self._save_cache_to_disk(self._cache)
        return state

    def simulate(
        self,
        plan: HypotheticalPlan,
        prediction_type: str = "parametric",
    ) -> SimulationResult:
        """What-If 推演：基于当前状态，推演计划执行后的状态变化"""
        initial_state = self.get_current_snapshot()
        return self._simulator.simulate(initial_state, plan, prediction_type)

    def compare_plans(
        self,
        plans: list[HypotheticalPlan],
        prediction_type: str = "parametric",
    ) -> PlanComparison:
        """多计划对比：对每个计划执行推演，按综合评分排序"""
        if not plans:
            raise TwinEngineError(
                "计划列表不能为空",
                recovery_suggestion="请提供至少一个训练计划进行对比",
            )

        initial_state = self.get_current_snapshot()

        results: list[SimulationResult] = []
        for plan in plans:
            result = self._simulator.simulate(initial_state, plan, prediction_type)
            results.append(result)

        metrics_list: list[PlanComparisonMetrics] = []
        for plan, result in zip(plans, results):
            score = self._compute_score(result)
            min_recovery = result.final_state.body_signal.recovery_status
            metrics_list.append(
                PlanComparisonMetrics(
                    plan_id=plan.plan_id or "",
                    plan_name=result.plan_name,
                    vdot_delta=result.vdot_delta,
                    peak_injury_risk=result.peak_injury_risk,
                    avg_tsb=result.avg_tsb,
                    min_recovery_status=min_recovery,
                    recommendation_score=score,
                )
            )

        sorted_metrics = sorted(
            metrics_list, key=lambda m: m.recommendation_score, reverse=True
        )
        best = sorted_metrics[0]

        return PlanComparison(
            plans=sorted_metrics,
            best_plan=best,
            comparison_dimensions=["vdot_delta", "peak_injury_risk", "avg_tsb"],
            recommendation=f"推荐计划: {best.plan_name} (评分: {best.recommendation_score})",
        )

    def compare_plans_by_ids(
        self,
        plan_ids: list[str],
        prediction_type: str = "parametric",
    ) -> PlanComparison:
        """通过系统计划ID对比多个训练计划（架构7.5.4节）

        Args:
            plan_ids: 系统训练计划ID列表（2-5个）
            prediction_type: 预测模式

        Returns:
            PlanComparison: 计划对比结果

        Raises:
            TwinEngineError: plan_ids数量不在2-5范围时
        """
        if len(plan_ids) < 2:
            raise TwinEngineError(
                "对比计划数量不能少于2个",
                recovery_suggestion="请提供至少2个训练计划ID进行对比",
            )
        if len(plan_ids) > 5:
            raise TwinEngineError(
                "对比计划数量不能超过5个",
                recovery_suggestion="请提供2-5个训练计划ID进行对比",
            )

        plans = [self.load_plan(pid) for pid in plan_ids]
        return self.compare_plans(plans, prediction_type=prediction_type)

    def load_plan(self, plan_id: str) -> HypotheticalPlan:
        """从PlanManager加载系统训练计划（架构7.5.4节 _load_plan）"""
        if self._plan_manager is None:
            raise TwinEngineError(
                "PlanManager未注入，无法加载系统计划",
                recovery_suggestion="请通过CLI手动提供训练计划参数",
            )
        training_plan = self._plan_manager.get_plan(plan_id)
        if training_plan is None:
            raise TwinEngineError(
                f"训练计划不存在: {plan_id}",
                recovery_suggestion="请检查计划ID是否正确",
            )
        return self._convert_training_plan(training_plan)

    @staticmethod
    def _compute_score(result: SimulationResult) -> float:
        """综合评分：0-100归一化 + 权重分配（架构7.7节）

        VDOT提升 40% + 伤病风险 35% + 恢复平衡 25%
        """
        vdot_score = min(100.0, max(0.0, result.vdot_delta * 20.0))
        risk_score = max(0.0, 100.0 - result.peak_injury_risk)
        tsb_part = min(100.0, max(0.0, (result.avg_tsb + 30.0) * 2.0))
        recovery_map = {
            "good": 50.0,
            "moderate": 25.0,
            "fatigued": 0.0,
            "overtrained": 0.0,
        }
        recovery_part = recovery_map.get(
            result.final_state.body_signal.recovery_status, 25.0
        )
        recovery_score = tsb_part * 0.5 + recovery_part * 0.5
        return round(vdot_score * 0.4 + risk_score * 0.35 + recovery_score * 0.25, 2)

    @staticmethod
    def _convert_training_plan(training_plan: object) -> HypotheticalPlan:
        """将TrainingPlan转换为HypotheticalPlan"""
        weeks: list[WeeklyPlanSpec] = []
        if hasattr(training_plan, "weeks"):
            for week in training_plan.weeks:
                week_spec = DigitalTwinEngine._aggregate_week_spec(week)
                if week_spec is not None:
                    weeks.append(week_spec)
        plan_name = getattr(training_plan, "name", "unknown") or "unknown"
        plan_id = getattr(training_plan, "plan_id", "") or ""
        return HypotheticalPlan(
            name=plan_name,
            weeks=weeks,
            source="plan_id",
            plan_id=plan_id,
        )

    @staticmethod
    def _aggregate_week_spec(week: object) -> WeeklyPlanSpec | None:
        """将单周DailyPlans聚合为WeeklyPlanSpec

        基于训练量（距离）而非天数计算强度分布ratio，
        更准确反映实际训练负荷结构。

        Args:
            week: 包含 daily_plans 属性的周计划对象

        Returns:
            WeeklyPlanSpec | None: 聚合后的周规格，总距离为0时返回None
        """
        if not hasattr(week, "daily_plans"):
            return None

        total_km = 0.0
        easy_km = 0.0
        tempo_km = 0.0
        interval_km = 0.0
        long_km = 0.0
        for day in week.daily_plans:
            dist = getattr(day, "distance_km", 0.0) or 0.0
            total_km += dist
            workout = getattr(day, "workout_type", "easy") or "easy"
            if workout in ("recovery", "easy"):
                easy_km += dist
            elif workout in ("tempo", "threshold"):
                tempo_km += dist
            elif workout == "interval":
                interval_km += dist
            elif workout == "long":
                long_km += dist

        if total_km <= 0:
            return None

        return WeeklyPlanSpec(
            weekly_volume_km=round(total_km, 2),
            easy_ratio=round(easy_km / total_km, 4),
            tempo_ratio=round(tempo_km / total_km, 4),
            interval_ratio=round(interval_km / total_km, 4),
            long_run_km=round(long_km, 2),
        )

    def _load_cache_from_disk(self) -> StateVectorCache | None:
        """从磁盘加载缓存"""
        if self._cache_dir is None:
            return None
        cache_file = self._cache_dir / CACHE_DIR_NAME / CACHE_FILE_NAME
        if not cache_file.exists():
            return None
        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            state_dict = data.get("state", {})
            state = RunnerStateVector(
                fitness=self._dict_to_fitness(state_dict.get("fitness", {})),
                load=self._dict_to_load(state_dict.get("load", {})),
                body_signal=self._dict_to_body_signal(
                    state_dict.get("body_signal", {})
                ),
                risk=self._dict_to_risk(state_dict.get("risk", {})),
                training_pattern=self._dict_to_training_pattern(
                    state_dict.get("training_pattern", {})
                ),
                snapshot_date=state_dict.get("snapshot_date", ""),
                data_quality=self._str_to_data_quality(
                    state_dict.get("data_quality", "empty")
                ),
            )
            return StateVectorCache(
                state=state,
                created_at=data.get("created_at", ""),
                ttl_hours=data.get("ttl_hours", 24),
            )
        except Exception as e:
            logger.debug(f"加载状态向量缓存失败: {e}")
            return None

    def _save_cache_to_disk(self, cache: StateVectorCache) -> None:
        """将缓存写入磁盘"""
        if self._cache_dir is None:
            return
        try:
            cache_dir = self._cache_dir / CACHE_DIR_NAME
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = cache_dir / CACHE_FILE_NAME
            cache_file.write_text(
                json.dumps(cache.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.debug(f"保存状态向量缓存失败: {e}")

    @staticmethod
    def _dict_to_fitness(d: dict) -> FitnessDimension:
        return FitnessDimension(
            vdot=float(d.get("vdot", 0.0)),
            vdot_trend=float(d.get("vdot_trend", 0.0)),
            vo2max_estimate=d.get("vo2max_estimate"),
        )

    @staticmethod
    def _dict_to_load(d: dict) -> LoadDimension:
        return LoadDimension(
            ctl=float(d.get("ctl", 0.0)),
            atl=float(d.get("atl", 0.0)),
            tsb=float(d.get("tsb", 0.0)),
            acwr=float(d.get("acwr", 0.0)),
        )

    @staticmethod
    def _dict_to_body_signal(d: dict) -> BodySignalDimension:
        return BodySignalDimension(
            fatigue_score=float(d.get("fatigue_score", 0.0)),
            recovery_status=str(d.get("recovery_status", "unknown")),
            resting_hr=d.get("resting_hr"),
            hrv_rmssd=d.get("hrv_rmssd"),
        )

    @staticmethod
    def _dict_to_risk(d: dict) -> RiskDimension:
        return RiskDimension(
            injury_risk_7d=float(d.get("injury_risk_7d", 0.0)),
            injury_risk_28d=float(d.get("injury_risk_28d", 0.0)),
            overtraining_risk=str(d.get("overtraining_risk", "low")),
        )

    @staticmethod
    def _dict_to_training_pattern(d: dict) -> TrainingPatternDimension:
        dist = d.get("intensity_distribution", {})
        return TrainingPatternDimension(
            weekly_volume_km=float(d.get("weekly_volume_km", 0.0)),
            intensity_distribution=IntensityDistribution(
                zone1_pct=float(dist.get("zone1_pct", 0.0)),
                zone2_pct=float(dist.get("zone2_pct", 0.0)),
                zone3_pct=float(dist.get("zone3_pct", 0.0)),
            ),
            long_run_frequency=int(d.get("long_run_frequency", 0)),
        )

    @staticmethod
    def _str_to_data_quality(s: str) -> DataQuality:
        try:
            return DataQuality(s)
        except ValueError:
            return DataQuality.EMPTY
