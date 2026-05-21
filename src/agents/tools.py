# Agent 工具集
# 封装为 nanobot-ai 可识别的工具
#
# 工具类已按领域拆分到子模块：
# - tools_stats.py: 统计/分析工具
# - tools_plan.py: 训练计划工具
# - tools_body.py: 身体信号/健康工具
# - tools_twin.py: 数字孪生/预测工具
# - tools_data.py: 数据管理/系统工具
#
# 本文件保留 BaseTool、RunnerTools 和所有工具类的 re-exports，
# 确保 `from src.agents.tools import XxxTool` 向后兼容。

from __future__ import annotations

import json
import logging
from abc import abstractmethod
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.core.personality import UserPreferences

import polars as pl
from nanobot.agent.tools.base import Tool

from src.core.base.context import AppContext, AppContextFactory
from src.core.base.exceptions import NanobotRunnerError
from src.core.tools.weather_training_coordinator import TrainingData

logger = logging.getLogger(__name__)


# ============================================================================
# BaseTool - 工具基类
# ============================================================================


class BaseTool(Tool):
    """工具基类（适配nanobot-ai 0.1.4+）"""

    concurrency_safe: bool = True

    def __init__(self, runner_tools: RunnerTools):
        self.runner_tools = runner_tools

    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述"""
        pass

    @property
    @abstractmethod
    def parameters(self) -> dict[str, Any]:
        """参数schema"""
        pass

    @abstractmethod
    async def execute(self, **kwargs: Any) -> Any:
        """执行工具"""
        pass

    def _run_sync(self, func, *args, **kwargs) -> str:
        """同步调用方法并返回 JSON 字符串

        返回格式：直接返回数据本身（dict/list 等），错误时返回包含 error 字段的 dict
        """
        try:
            logger.info(f"工具调用开始: {func.__name__}, 参数: {kwargs}")
            result = func(*args, **kwargs)
            logger.info(
                f"工具调用成功: {func.__name__}, 结果类型: {type(result)}, 结果: {str(result)[:200]}"
            )

            # 如果结果已经是 dict 且包含 error 字段，直接返回
            if isinstance(result, dict) and "error" in result:
                logger.warning(f"工具返回错误: {result}")
                return json.dumps(result, ensure_ascii=False, default=str)
            # 如果结果是 dict 且仅含 message 字段（如暂无数据），转换为 error 格式
            if (
                isinstance(result, dict)
                and "message" in result
                and "success" not in result
            ):
                logger.info(f"工具返回消息: {result}")
                return json.dumps(
                    {"error": result["message"]}, ensure_ascii=False, default=str
                )
            # 正常返回数据（直接返回，不包装）
            json_result = json.dumps(result, ensure_ascii=False, default=str)
            logger.info(f"工具返回 JSON 长度: {len(json_result)}")
            return json_result
        except NanobotRunnerError as e:
            logger.error(
                f"工具调用异常: {func.__name__}, 错误: {str(e)}", exc_info=True
            )
            return json.dumps({"error": str(e)}, ensure_ascii=False)
        except Exception as e:
            # 工具入口层防御性编程：捕获所有未预期异常，防止框架崩溃
            logger.error(
                f"工具调用未预期异常: {func.__name__}, 错误类型: {type(e).__name__}, 错误: {str(e)}",
                exc_info=True,
            )
            return json.dumps(
                {"error": f"{type(e).__name__}: {str(e)}"}, ensure_ascii=False
            )


# ============================================================================
# RunnerTools - 业务逻辑层
# ============================================================================


class RunnerTools:
    """跑步助理工具集（业务逻辑层）"""

    def __init__(self, context: AppContext | None = None):
        """
        初始化工具集

        Args:
            context: 应用上下文（可选），未提供则使用全局上下文
        """
        if context is None:
            context = AppContextFactory.create()

        self.storage = context.storage
        self.analytics = context.analytics
        self.profile_storage = context.profile_storage

    # ----------------------------------------------------------------
    # 统计/分析方法
    # ----------------------------------------------------------------

    def get_running_stats(
        self, start_date: str | None = None, end_date: str | None = None
    ) -> dict[str, Any]:
        summary = self.analytics.get_running_summary(start_date, end_date)

        if summary.height == 0:
            return {"message": "暂无跑步数据"}

        row = summary.row(0)

        return {
            "total_runs": row[0] if row[0] is not None else 0,
            "total_distance": row[1] if row[1] is not None else 0.0,
            "total_duration": row[2] if row[2] is not None else 0.0,
            "avg_distance": row[3] if row[3] is not None else 0.0,
            "avg_duration": row[4] if row[4] is not None else 0.0,
            "max_distance": row[5] if row[5] is not None else 0.0,
            "avg_heart_rate": row[6] if row[6] is not None else 0.0,
        }

    def get_recent_runs(self, limit: int = 10) -> list[dict[str, Any]]:
        lf = self.storage.read_parquet()

        session_df = (
            lf.group_by("session_start_time")
            .agg(
                [
                    pl.col("session_start_time").first().alias("timestamp"),
                    pl.col("session_total_distance").first().alias("distance"),
                    pl.col("session_total_timer_time").first().alias("duration"),
                    pl.col("session_avg_heart_rate").first().alias("avg_hr"),
                ]
            )
            .sort("timestamp", descending=True)
            .limit(limit)
            .collect()
        )

        runs = []
        for row in session_df.iter_rows(named=True):
            distance_raw = row.get("distance")
            duration_raw = row.get("duration")
            distance = float(distance_raw) if distance_raw is not None else 0.0
            duration = float(duration_raw) if duration_raw is not None else 0.0
            distance_km = distance / 1000
            duration_min = duration / 60
            pace = duration_min / distance_km if distance_km > 0 else 0

            vdot = None
            if distance >= 1500 and duration > 0:
                vdot = self.analytics.calculate_vdot(distance, duration)

            runs.append(
                {
                    "timestamp": str(row.get("timestamp", "N/A")),
                    "distance_km": round(distance_km, 2),
                    "duration_min": round(duration_min, 1),
                    "avg_pace_sec_km": round(pace, 1) if pace > 0 else None,
                    "avg_heart_rate": row.get("avg_hr"),
                    "vdot": round(vdot, 2) if vdot else None,
                }
            )

        return runs

    def calculate_vdot_for_run(self, distance_m: float, time_s: float) -> float:
        return self.analytics.calculate_vdot(distance_m, time_s)

    def get_vdot_trend(self, limit: int = 20) -> list[dict[str, Any]]:
        lf = self.storage.read_parquet()

        session_df = (
            lf.group_by("session_start_time")
            .agg(
                [
                    pl.col("session_start_time").first().alias("timestamp"),
                    pl.col("session_total_distance").first().alias("distance"),
                    pl.col("session_total_timer_time").first().alias("duration"),
                ]
            )
            .sort("timestamp", descending=True)
            .limit(limit)
            .collect()
        )

        vdot_trend = []
        for row in session_df.iter_rows(named=True):
            distance_raw = row.get("distance")
            duration_raw = row.get("duration")
            timestamp = row.get("timestamp")
            distance = float(distance_raw) if distance_raw is not None else 0.0
            duration = float(duration_raw) if duration_raw is not None else 0.0

            if distance >= 1500 and duration > 0:
                vdot = self.analytics.calculate_vdot(distance, duration)

                date_str = "N/A"
                if timestamp is not None:
                    date_str = str(timestamp)[:10]

                duration_min = duration / 60
                hours = int(duration_min // 60)
                minutes = int(duration_min % 60)
                seconds = int(duration % 60)
                duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

                vdot_trend.append(
                    {
                        "date": date_str,
                        "distance_km": distance / 1000,
                        "duration": duration_str,
                        "vdot": vdot,
                    }
                )

        return vdot_trend

    def get_hr_drift_analysis(self, _run_id: str | None = None) -> dict[str, Any]:
        lf = self.storage.read_parquet()
        df = lf.collect()

        if df.height == 0:
            return {"error": "暂无数据"}

        if "heart_rate" not in df.columns:
            return {"error": "暂无心率数据"}

        heart_rate = df.select(pl.col("heart_rate")).to_series().to_list()

        pace_list: list[float] = []
        if "speed" in df.columns:
            speed_values = df.select(pl.col("speed")).to_series().to_list()
            pace_list = [1000 / s for s in speed_values if s and s > 0]
        elif "enhanced_speed" in df.columns:
            speed_values = df.select(pl.col("enhanced_speed")).to_series().to_list()
            pace_list = [1000 / s for s in speed_values if s and s > 0]

        result = self.analytics.analyze_hr_drift(heart_rate, pace_list)
        return result.to_dict()

    def get_training_load(self, days: int = 42) -> dict[str, Any]:
        return self.analytics.get_training_load(days)

    def query_by_date_range(
        self, start_date: str, end_date: str
    ) -> list[dict[str, Any]]:
        """
        按日期范围查询跑步记录（按会话聚合）

        数据模型说明：
        - 存储的数据包含采样点数据和会话数据
        - 需要按 session_start_time 聚合，避免返回重复的采样点数据
        - 使用 session_start_time 进行日期过滤，而不是 timestamp
        - 结束日期包含当天一整天
        """
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
        except ValueError:
            return [{"error": "日期格式错误，应为 YYYY-MM-DD"}]

        lf = self.storage.read_parquet()

        # 检查空数据
        if len(lf.collect_schema()) == 0:
            return []

        # 按会话聚合，使用 session_start_time 进行过滤
        session_df = (
            lf.group_by("session_start_time")
            .agg(
                [
                    pl.col("session_start_time").first().alias("session_start"),
                    pl.col("session_total_distance").first().alias("distance"),
                    pl.col("session_total_timer_time").first().alias("duration"),
                    pl.col("session_avg_heart_rate").first().alias("avg_hr"),
                ]
            )
            .filter(pl.col("session_start").is_between(start_dt, end_dt))
            .sort("session_start", descending=True)
            .collect()
        )

        if session_df.is_empty():
            return []

        results = []
        for row in session_df.iter_rows(named=True):
            distance_raw = row.get("distance")
            duration_raw = row.get("duration")
            avg_hr = row.get("avg_hr")
            distance = float(distance_raw) if distance_raw is not None else 0.0
            duration = float(duration_raw) if duration_raw is not None else 0.0

            distance_km = distance / 1000
            duration_minutes = duration / 60
            pace = duration_minutes / distance_km if distance_km > 0 else 0

            results.append(
                {
                    "timestamp": str(row.get("session_start", "N/A")),
                    "distance": round(distance_km, 2),
                    "duration": duration,
                    "heart_rate": avg_hr if avg_hr is not None else "N/A",
                    "pace": round(pace, 2),
                }
            )

        return results

    def query_by_distance(
        self, min_distance: float, max_distance: float | None = None
    ) -> list[dict[str, Any]]:
        """
        按距离范围查询跑步记录（按会话聚合）

        数据模型说明：
        - 存储的数据包含采样点数据和会话数据
        - 需要按 session_start_time 聚合，避免返回重复的采样点数据
        """
        min_meters = min_distance * 1000
        max_meters = max_distance * 1000 if max_distance else None

        lf = self.storage.read_parquet()

        if max_meters:
            distance_filter = pl.col("session_total_distance").is_between(
                min_meters, max_meters
            )
        else:
            distance_filter = pl.col("session_total_distance") >= min_meters

        # 按会话聚合，避免返回重复的采样点数据
        session_df = (
            lf.filter(distance_filter)
            .group_by("session_start_time")
            .agg(
                [
                    pl.col("session_start_time").first().alias("session_start"),
                    pl.col("session_total_distance").first().alias("distance"),
                    pl.col("session_total_timer_time").first().alias("duration"),
                    pl.col("session_avg_heart_rate").first().alias("avg_hr"),
                ]
            )
            .sort("session_start", descending=True)
            .collect()
        )

        results = []
        for row in session_df.iter_rows(named=True):
            distance_raw = row.get("distance")
            duration_raw = row.get("duration")
            avg_hr = row.get("avg_hr")
            distance = float(distance_raw) if distance_raw is not None else 0.0
            duration = float(duration_raw) if duration_raw is not None else 0.0

            distance_km = distance / 1000
            duration_minutes = duration / 60
            pace = duration_minutes / distance_km if distance_km > 0 else 0

            results.append(
                {
                    "timestamp": str(row.get("session_start", "N/A")),
                    "distance": round(distance_km, 2),
                    "duration": duration,
                    "heart_rate": avg_hr if avg_hr is not None else "N/A",
                    "pace": round(pace, 2),
                }
            )

        return results

    # ----------------------------------------------------------------
    # 数据管理方法
    # ----------------------------------------------------------------

    def update_memory(self, note: str, category: str = "other") -> dict[str, Any]:
        """
        更新 Agent 观察笔记到 MEMORY.md

        Args:
            note: 观察笔记内容
            category: 笔记分类（training/preference/injury/other）

        Returns:
            Dict: 包含成功/失败状态和消息
        """
        try:
            if not note or not note.strip():
                return {"error": "笔记内容不能为空"}

            # 验证分类
            valid_categories = ["training", "preference", "injury", "other"]
            if category not in valid_categories:
                return {
                    "error": f"无效的分类，必须是 {', '.join(valid_categories)} 之一"
                }

            # 格式化笔记内容（添加分类标签）
            category_map = {
                "training": "训练",
                "preference": "偏好",
                "injury": "伤病",
                "other": "其他",
            }
            formatted_note = f"[{category_map.get(category, '其他')}] {note}"

            # 追加到 MEMORY.md
            success = self.profile_storage.save_memory_md(
                f"- @agent {formatted_note}", append=True
            )

            if success:
                return {
                    "success": True,
                    "message": "记忆更新成功",
                    "note": formatted_note,
                }
            else:
                return {"error": "保存 MEMORY.md 失败"}

        except NanobotRunnerError as e:
            logger.error(f"更新记忆失败：{e}")
            return {"error": f"更新记忆失败：{str(e)}"}

    # ----------------------------------------------------------------
    # 训练计划方法
    # ----------------------------------------------------------------

    def generate_training_plan(
        self, goal_distance_km: float, goal_date: str
    ) -> dict[str, Any]:
        """
        生成训练计划

        Args:
            goal_distance_km: 目标比赛距离（公里）
            goal_date: 目标比赛日期（YYYY-MM-DD）

        Returns:
            Dict: 包含训练计划信息
        """
        try:
            from src.core.training_plan import TrainingPlanEngine

            profile = self.profile_storage.load_profile_json()
            if not profile:
                return {"error": "未找到用户画像，请先导入跑步数据"}

            profile_dict = profile.to_dict()
            vdot = profile_dict.get("estimated_vdot", 35.0)
            volume = profile_dict.get("weekly_avg_distance", 30.0)
            age = profile_dict.get("age", 30)
            resting_hr = profile_dict.get("resting_hr", 60)

            engine = TrainingPlanEngine()
            plan = engine.generate_plan(
                user_id="default",
                goal_distance_km=goal_distance_km,
                goal_date=goal_date,
                current_vdot=vdot,
                current_weekly_distance_km=volume,
                age=age,
                resting_hr=resting_hr,
            )

            return {
                "success": True,
                "message": f"已生成{goal_distance_km}km 训练计划，共{len(plan.weeks)}周",
                "fitness_level": plan.fitness_level.value,
                "total_weeks": len(plan.weeks),
                "total_distance": sum(ws.weekly_distance_km for ws in plan.weeks),
            }

        except NanobotRunnerError as e:
            logger.error(f"生成训练计划失败：{e}")
            return {"error": str(e)}

    def record_plan_execution(
        self,
        plan_id: str,
        date: str,
        completion_rate: float | None = None,
        effort_score: int | None = None,
        notes: str = "",
        actual_distance_km: float | None = None,
        actual_duration_min: int | None = None,
        actual_avg_hr: int | None = None,
    ) -> dict[str, Any]:
        """记录计划执行反馈

        Args:
            plan_id: 计划ID
            date: 日期（YYYY-MM-DD）
            completion_rate: 完成度（0.0-1.0）
            effort_score: 体感评分（1-10）
            notes: 反馈备注
            actual_distance_km: 实际距离（公里）
            actual_duration_min: 实际时长（分钟）
            actual_avg_hr: 实际平均心率

        Returns:
            dict: 记录结果
        """
        try:
            from src.core.base.context import get_context

            context = get_context()
            plan_manager = context.plan_manager
            result = plan_manager.record_execution(
                plan_id=plan_id,
                date=date,
                completion_rate=completion_rate,
                effort_score=effort_score,
                notes=notes,
                actual_distance_km=actual_distance_km,
                actual_duration_min=actual_duration_min,
                actual_avg_hr=actual_avg_hr,
            )
            return result
        except NanobotRunnerError as e:
            logger.error(f"记录执行反馈失败：{e}")
            return {"error": str(e)}

    def get_plan_execution_stats(self, plan_id: str) -> dict[str, Any]:
        """获取计划执行统计

        Args:
            plan_id: 计划ID

        Returns:
            dict: 执行统计数据
        """
        try:
            from src.core.base.context import get_context

            context = get_context()
            execution_repo = context.plan_execution_repo
            stats = execution_repo.get_plan_execution_stats(plan_id)
            return stats.to_dict()
        except NanobotRunnerError as e:
            logger.error(f"获取执行统计失败：{e}")
            return {"error": str(e)}

    def analyze_training_response(self, plan_id: str) -> dict[str, Any]:
        """分析训练响应模式

        Args:
            plan_id: 计划ID

        Returns:
            dict: 训练响应分析结果
        """
        try:
            from src.core.base.context import get_context

            context = get_context()
            analyzer = context.training_response_analyzer
            return analyzer.analyze_plan_response(plan_id)
        except NanobotRunnerError as e:
            logger.error(f"训练响应分析失败：{e}")
            return {"error": str(e)}

    def adjust_plan(
        self,
        plan_id: str,
        adjustment_request: str,
        confirmation_required: bool = True,
    ) -> dict[str, Any]:
        """调整训练计划

        Args:
            plan_id: 计划ID
            adjustment_request: 调整请求（自然语言）
            confirmation_required: 是否需要确认

        Returns:
            dict: 调整结果
        """
        try:
            from src.core.base.context import get_context

            context = get_context()
            validator = context.plan_adjustment_validator

            default_adjustment = validator.get_default_adjustment(adjustment_request)

            validation = validator.validate(default_adjustment)

            if not validation.passed:
                violation_msgs = [v.message for v in validation.violations]
                return {
                    "success": False,
                    "error": "调整建议不符合运动科学原则",
                    "violations": violation_msgs,
                }

            if confirmation_required:
                return {
                    "success": True,
                    "plan_id": plan_id,
                    "adjustment": default_adjustment.to_dict(),
                    "validation": {"passed": True},
                    "requires_confirmation": True,
                }

            return {
                "success": True,
                "plan_id": plan_id,
                "adjustment": default_adjustment.to_dict(),
                "validation": {"passed": True},
                "requires_confirmation": False,
            }
        except NanobotRunnerError as e:
            logger.error(f"调整训练计划失败：{e}")
            return {"error": str(e)}

    def get_plan_adjustment_suggestions(self, plan_id: str) -> dict[str, Any]:
        """获取计划调整建议

        Args:
            plan_id: 计划ID

        Returns:
            dict: 调整建议
        """
        try:
            from src.core.base.context import get_context

            context = get_context()
            execution_repo = context.plan_execution_repo
            stats = execution_repo.get_plan_execution_stats(plan_id)

            suggestions: list[dict[str, Any]] = []

            if stats.completion_rate < 0.5:
                suggestions.append(
                    {
                        "suggestion_type": "training",
                        "suggestion_content": "完成率偏低，建议降低训练量或增加恢复日",
                        "priority": "high",
                        "confidence": 0.8,
                    }
                )

            if stats.avg_effort_score > 7:
                suggestions.append(
                    {
                        "suggestion_type": "recovery",
                        "suggestion_content": "体感评分偏高，建议减少高强度训练比例",
                        "priority": "high",
                        "confidence": 0.75,
                    }
                )

            if stats.avg_hr_drift is not None and stats.avg_hr_drift > 5.0:
                suggestions.append(
                    {
                        "suggestion_type": "training",
                        "suggestion_content": "心率漂移较大，建议增加有氧基础训练",
                        "priority": "medium",
                        "confidence": 0.7,
                    }
                )

            if not suggestions:
                suggestions.append(
                    {
                        "suggestion_type": "training",
                        "suggestion_content": "训练状态良好，保持当前计划即可",
                        "priority": "low",
                        "confidence": 0.6,
                    }
                )

            return {
                "success": True,
                "plan_id": plan_id,
                "suggestions": suggestions,
            }
        except NanobotRunnerError as e:
            logger.error(f"获取调整建议失败：{e}")
            return {"error": str(e)}

    def evaluate_goal_achievement(
        self,
        goal_type: str,
        goal_value: float,
        current_vdot: float,
        weeks_available: int | None = None,
    ) -> dict[str, Any]:
        """评估目标达成概率 - v0.12.0新增

        Args:
            goal_type: 目标类型
            goal_value: 目标值
            current_vdot: 当前VDOT
            weeks_available: 可用周数

        Returns:
            dict: 评估结果
        """
        try:
            from src.core.plan.goal_prediction_engine import GoalPredictionEngine

            engine = GoalPredictionEngine()
            evaluation = engine.evaluate_goal(
                goal_type=goal_type,
                goal_value=goal_value,
                current_vdot=current_vdot,
                weeks_available=weeks_available,
            )

            return {
                "success": True,
                "data": evaluation.to_dict(),
            }
        except NanobotRunnerError as e:
            logger.error(f"目标评估失败：{e}")
            return {"success": False, "error": str(e)}

    def create_long_term_plan(
        self,
        plan_name: str,
        current_vdot: float,
        target_vdot: float | None = None,
        target_race: str | None = None,
        target_date: str | None = None,
        total_weeks: int = 16,
        fitness_level: str = "intermediate",
    ) -> dict[str, Any]:
        """创建长期训练规划 - v0.12.0新增

        Args:
            plan_name: 计划名称
            current_vdot: 当前VDOT
            target_vdot: 目标VDOT
            target_race: 目标赛事
            target_date: 目标日期
            total_weeks: 总周数
            fitness_level: 体能水平

        Returns:
            dict: 规划结果
        """
        try:
            from src.core.plan.long_term_plan_generator import LongTermPlanGenerator

            generator = LongTermPlanGenerator()
            plan = generator.generate_plan(
                plan_name=plan_name,
                current_vdot=current_vdot,
                target_vdot=target_vdot,
                target_race=target_race,
                target_date=target_date,
                total_weeks=total_weeks,
                fitness_level=fitness_level,
            )

            return {
                "success": True,
                "data": plan.to_dict(),
            }
        except NanobotRunnerError as e:
            logger.error(f"创建长期规划失败：{e}")
            return {"success": False, "error": str(e)}

    def get_smart_training_advice(
        self,
        current_vdot: float | None = None,
        weekly_volume_km: float = 0.0,
        training_consistency: float = 1.0,
        injury_risk: str = "low",
        goal_type: str | None = None,
    ) -> dict[str, Any]:
        """获取智能训练建议 - v0.12.0新增

        Args:
            current_vdot: 当前VDOT
            weekly_volume_km: 周跑量
            training_consistency: 训练一致性
            injury_risk: 伤病风险
            goal_type: 目标类型

        Returns:
            dict: 建议结果
        """
        try:
            from src.core.plan.smart_advice_engine import SmartAdviceEngine

            engine = SmartAdviceEngine()
            advices = engine.generate_advice(
                current_vdot=current_vdot,
                weekly_volume_km=weekly_volume_km,
                training_consistency=training_consistency,
                injury_risk=injury_risk,
                goal_type=goal_type,
            )

            return {
                "success": True,
                "data": {
                    "advices": [a.to_dict() for a in advices],
                    "total_count": len(advices),
                },
            }
        except NanobotRunnerError as e:
            logger.error(f"获取训练建议失败：{e}")
            return {"success": False, "error": str(e)}

    def get_weather_training_advice(
        self,
        temperature: float = 20.0,
        humidity: float = 50.0,
        weather: str = "晴",
        wind: str = "无风",
        precipitation: float = 0.0,
        uv_index: float = 0.0,
    ) -> dict[str, Any]:
        """获取天气+训练综合建议 - v0.13.0新增

        结合天气数据和训练数据，生成多维度的训练建议。

        Args:
            temperature: 温度（摄氏度）
            humidity: 湿度（百分比）
            weather: 天气状况
            wind: 风力描述
            precipitation: 降水概率
            uv_index: 紫外线指数

        Returns:
            dict: 综合建议结果
        """
        try:
            from src.core.tools.weather_training_coordinator import (
                WeatherData,
                WeatherTrainingCoordinator,
            )

            # 创建天气数据
            weather_data = WeatherData(
                temperature=temperature,
                humidity=humidity,
                weather=weather,
                wind=wind,
                precipitation=precipitation,
                uv_index=uv_index,
            )

            # 获取训练数据摘要
            profile = self.profile_storage.load_profile_json()
            training_data = self._build_training_data_summary(profile)

            # 使用协调器生成建议
            coordinator = WeatherTrainingCoordinator()
            advices = coordinator.generate_advice(weather_data, training_data)

            # 分析天气影响
            weather_impact = coordinator.analyze_weather_impact(weather_data)

            # 格式化建议
            formatted_advice = coordinator.format_advice_for_display(advices)

            return {
                "success": True,
                "data": {
                    "advices": [
                        {
                            "advice_type": a.advice_type,
                            "content": a.content,
                            "priority": a.priority,
                            "reason": a.reason,
                            "weather_impact": a.weather_impact,
                            "training_impact": a.training_impact,
                        }
                        for a in advices
                    ],
                    "total_count": len(advices),
                    "weather_impact": weather_impact,
                    "formatted_advice": formatted_advice,
                },
            }
        except NanobotRunnerError as e:
            logger.error(f"获取天气+训练建议失败：{e}")
            return {"success": False, "error": str(e)}

    def _build_training_data_summary(self, profile: Any) -> TrainingData:
        """构建训练数据摘要

        Args:
            profile: 用户画像数据

        Returns:
            TrainingData: 训练数据摘要
        """
        from src.core.tools.weather_training_coordinator import TrainingData

        # 获取最近一周跑量
        recent_runs = self.get_recent_runs(limit=7)
        recent_distance_km = sum(run.get("distance_km", 0) for run in recent_runs)

        # 获取平均VDOT
        vdot_trend = self.get_vdot_trend(limit=20)
        avg_vdot = None
        if vdot_trend:
            vdot_values: list[float] = [
                v.get("vdot", 0.0) for v in vdot_trend if v.get("vdot") is not None
            ]
            if vdot_values:
                avg_vdot = sum(vdot_values) / len(vdot_values)

        # 获取训练负荷
        training_load_data = self.get_training_load(days=42)
        training_load = training_load_data.get("ctl")

        # 判断恢复状态
        recovery_status = "良好"
        if training_load and training_load > 50:
            recovery_status = "疲劳"
        elif training_load and training_load > 40:
            recovery_status = "一般"

        # 获取最近一次跑步日期
        last_run_date = None
        if recent_runs:
            last_run_date = recent_runs[0].get("timestamp", "")[:10]

        return TrainingData(
            recent_distance_km=recent_distance_km,
            avg_vdot=avg_vdot,
            training_load=training_load,
            recovery_status=recovery_status,
            last_run_date=last_run_date,
        )

    # ----------------------------------------------------------------
    # 诊断/个性化方法
    # ----------------------------------------------------------------

    def diagnose_suggestion(
        self,
        user_query: str,
        suggestion_text: str,
        tools_used: list[str] | None = None,
    ) -> dict[str, Any]:
        """验证AI建议质量 - v0.14.0新增

        Args:
            user_query: 用户原始查询
            suggestion_text: AI生成的建议文本
            tools_used: 使用的工具列表

        Returns:
            dict: 诊断报告
        """
        try:
            from src.core.diagnosis import SelfDiagnosis, SuggestionContext

            diagnosis = SelfDiagnosis()
            context = SuggestionContext(
                user_query=user_query,
                suggestion_text=suggestion_text,
                tools_used=tools_used or [],
            )
            report = diagnosis.validate_suggestion(context)

            return {
                "success": True,
                "data": report.to_dict(),
            }
        except NanobotRunnerError as e:
            logger.error(f"建议诊断失败: {e}")
            return {"success": False, "error": str(e)}

    def diagnose_error(self, error_message: str) -> dict[str, Any]:
        """诊断错误原因 - v0.14.0新增

        Args:
            error_message: 错误信息

        Returns:
            dict: 诊断报告
        """
        try:
            from src.core.diagnosis import SelfDiagnosis

            diagnosis = SelfDiagnosis()
            report = diagnosis.diagnose_error(error_message)

            return {
                "success": True,
                "data": report.to_dict(),
            }
        except NanobotRunnerError as e:
            logger.error(f"错误诊断失败: {e}")
            return {"success": False, "error": str(e)}

    def get_personalized_suggestion(
        self,
        suggestion_text: str,
        suggestion_type: str = "general",
    ) -> dict[str, Any]:
        """获取个性化建议 - v0.14.0新增

        Args:
            suggestion_text: 原始建议文本
            suggestion_type: 建议类型

        Returns:
            dict: 个性化建议
        """
        try:
            from src.core.base.context import get_context
            from src.core.personality import (
                PersonalizationEngine,
                SuggestionType,
            )

            context = get_context()
            preferences = self._load_preferences(context)

            engine = PersonalizationEngine(preferences=preferences)
            st = (
                SuggestionType(suggestion_type)
                if suggestion_type
                else SuggestionType.GENERAL
            )
            suggestion = engine.personalize_suggestion(suggestion_text, st)

            return {
                "success": True,
                "data": suggestion.to_dict(),
            }
        except NanobotRunnerError as e:
            logger.error(f"获取个性化建议失败: {e}")
            return {"success": False, "error": str(e)}

    def record_feedback(
        self,
        feedback_type: str,
        content: str,
        preference_category: str = "communication_style",
        suggestion_id: str = "",
    ) -> dict[str, Any]:
        """记录用户反馈 - v0.14.0新增

        Args:
            feedback_type: 反馈类型
            content: 反馈内容
            preference_category: 偏好类别
            suggestion_id: 关联的建议ID

        Returns:
            dict: 反馈记录结果
        """
        try:
            from src.core.base.context import get_context
            from src.core.personality import (
                FeedbackLoop,
                FeedbackType,
                PreferenceCategory,
                PreferenceLearner,
            )

            context = get_context()
            preferences = self._load_preferences(context)

            learner = PreferenceLearner(preferences=preferences)
            loop = FeedbackLoop(learner)

            ft = FeedbackType(feedback_type)
            pc = PreferenceCategory(preference_category)

            feedback = loop.collect_feedback(
                feedback_type=ft,
                content=content,
                suggestion_id=suggestion_id,
                preference_category=pc,
            )

            new_preferences = loop.process_feedback(feedback)

            self._save_preferences(context, new_preferences)

            return {
                "success": True,
                "data": {
                    "feedback_id": feedback.id,
                    "feedback_type": feedback.feedback_type.value,
                    "preference_updated": True,
                    "current_preferences": new_preferences.to_dict(),
                },
            }
        except NanobotRunnerError as e:
            logger.error(f"记录反馈失败: {e}")
            return {"success": False, "error": str(e)}

    def get_user_preferences(self) -> dict[str, Any]:
        """获取用户偏好 - v0.14.0新增

        Returns:
            dict: 用户偏好
        """
        try:
            from src.core.base.context import get_context

            context = get_context()
            preferences = self._load_preferences(context)

            return {
                "success": True,
                "data": preferences.to_dict(),
            }
        except NanobotRunnerError as e:
            logger.error(f"获取用户偏好失败: {e}")
            return {"success": False, "error": str(e)}

    def update_user_preferences(self, updates: dict[str, str]) -> dict[str, Any]:
        """更新用户偏好 - v0.14.0新增

        Args:
            updates: 偏好更新键值对

        Returns:
            dict: 更新结果
        """
        try:
            from src.core.base.context import get_context
            from src.core.personality import PreferenceLearner

            context = get_context()
            preferences = self._load_preferences(context)

            learner = PreferenceLearner(preferences=preferences)
            new_preferences = learner.update_preference_model(updates)

            self._save_preferences(context, new_preferences)

            return {
                "success": True,
                "data": {
                    "updated_preferences": new_preferences.to_dict(),
                },
            }
        except NanobotRunnerError as e:
            logger.error(f"更新用户偏好失败: {e}")
            return {"success": False, "error": str(e)}

    def _load_preferences(self, context: Any) -> UserPreferences:
        """从存储加载用户偏好

        Args:
            context: 应用上下文

        Returns:
            UserPreferences: 用户偏好
        """
        from src.core.personality import UserPreferences

        try:
            profile = self.profile_storage.load_profile_json()
            if profile is not None:
                profile_dict = profile.to_dict() if hasattr(profile, "to_dict") else {}
                pref_data = profile_dict.get("preferences", {})
                if pref_data:
                    return UserPreferences.from_dict(pref_data)
        except NanobotRunnerError:
            pass

        return UserPreferences.default()

    def _save_preferences(self, context: Any, preferences: UserPreferences) -> None:
        """保存用户偏好到存储

        Args:
            context: 应用上下文
            preferences: 用户偏好
        """
        try:
            profile = self.profile_storage.load_profile_json()
            if profile is not None and hasattr(profile, "to_dict"):
                profile_dict = profile.to_dict()
            else:
                profile_dict = {}

            profile_dict["preferences"] = preferences.to_dict()

            # 将 dict 转换回 RunnerProfile 对象以满足类型要求
            if hasattr(self.profile_storage, "save_profile_json") and hasattr(
                self.profile_storage, "_dict_to_profile"
            ):
                profile_obj = self.profile_storage._dict_to_profile(profile_dict)
                self.profile_storage.save_profile_json(profile_obj)
        except NanobotRunnerError as e:
            logger.warning(f"保存偏好到存储失败: {e}")

    # ----------------------------------------------------------------
    # 透明化方法
    # ----------------------------------------------------------------

    def explain_decision(
        self,
        decision_id: str | None = None,
        detail_level: str = "brief",
    ) -> dict[str, Any]:
        """解释AI决策过程 - v0.15.0新增

        Args:
            decision_id: 决策ID（可选）
            detail_level: 详细程度（brief/detailed）

        Returns:
            dict: 决策解释
        """
        try:
            from src.core.transparency import DetailLevel

            engine = self._get_transparency_engine()
            if engine is None:
                return {
                    "success": False,
                    "error": "透明化引擎未初始化",
                }

            if decision_id is not None:
                decision = engine.get_decision(decision_id)
                if decision is None:
                    return {
                        "success": False,
                        "error": f"决策不存在: {decision_id}",
                    }
            else:
                return {
                    "success": False,
                    "error": "无可用决策记录，请提供decision_id",
                }

            level = (
                DetailLevel.DETAILED
                if detail_level == "detailed"
                else DetailLevel.BRIEF
            )
            explanation = engine.generate_explanation(decision, level)

            return {
                "success": True,
                "data": {
                    "decision_id": explanation.decision_id,
                    "brief_reasons": explanation.brief_reasons,
                    "confidence": explanation.confidence_score,
                    "data_sources": [
                        {
                            "name": ds.name,
                            "type": ds.type.value,
                            "description": ds.description,
                            "quality_score": ds.quality_score,
                        }
                        for ds in explanation.data_sources
                    ],
                    "decision_path": {
                        "steps": [
                            {
                                "name": step.name,
                                "description": step.description,
                                "type": step.step_type,
                            }
                            for step in explanation.decision_path.steps
                        ],
                        "total_duration_ms": explanation.decision_path.total_duration_ms,
                    },
                    "detailed_analysis": explanation.detailed_analysis,
                },
            }
        except NanobotRunnerError as e:
            logger.error(f"解释决策失败: {e}")
            return {"success": False, "error": str(e)}

    def trace_data_sources(
        self,
        decision_id: str | None = None,
    ) -> dict[str, Any]:
        """追溯数据来源 - v0.15.0新增

        Args:
            decision_id: 决策ID（可选）

        Returns:
            dict: 数据来源信息
        """
        try:
            engine = self._get_transparency_engine()
            if engine is None:
                return {
                    "success": False,
                    "error": "透明化引擎未初始化",
                }

            if decision_id is not None:
                sources = engine.trace_data_sources(decision_id)
                if not sources:
                    return {
                        "success": False,
                        "error": f"决策不存在: {decision_id}",
                    }
            else:
                return {
                    "success": False,
                    "error": "无可用决策记录，请提供decision_id",
                }

            return {
                "success": True,
                "data": {
                    "decision_id": decision_id,
                    "sources": [
                        {
                            "name": ds.name,
                            "type": ds.type.value,
                            "description": ds.description,
                            "quality_score": ds.quality_score,
                        }
                        for ds in sources
                    ],
                },
            }
        except NanobotRunnerError as e:
            logger.error(f"追溯数据来源失败: {e}")
            return {"success": False, "error": str(e)}

    def get_transparency_insight(
        self,
        include_metrics: bool = True,
        include_recent_decisions: bool = True,
        recent_limit: int = 5,
    ) -> dict[str, Any]:
        """获取透明化洞察 - v0.15.0新增

        Args:
            include_metrics: 是否包含可观测性指标
            include_recent_decisions: 是否包含最近决策
            recent_limit: 最近决策返回数量

        Returns:
            dict: 透明化洞察信息
        """
        try:
            result: dict[str, Any] = {"success": True, "data": {}}

            if include_metrics:
                manager = self._get_observability_manager()
                if manager is not None:
                    metrics = manager.get_metrics()
                    result["data"]["metrics"] = metrics.to_dict()

            if include_recent_decisions:
                trace_logger = self._get_trace_logger()
                if trace_logger is not None:
                    recent = trace_logger.get_decision_logs(recent_limit)
                    result["data"]["recent_decisions"] = [
                        {
                            "timestamp": str(e.timestamp),
                            "message": e.message,
                            "level": e.level,
                            "context": e.context,
                        }
                        for e in recent
                    ]
                    result["data"]["log_stats"] = trace_logger.get_stats()

            return result
        except NanobotRunnerError as e:
            logger.error(f"获取透明化洞察失败: {e}")
            return {"success": False, "error": str(e)}

    def _get_transparency_engine(self) -> Any:
        """获取透明化引擎实例"""
        if not hasattr(self, "_transparency_engine"):
            from src.core.transparency import TransparencyEngine

            self._transparency_engine: Any = TransparencyEngine()
        return self._transparency_engine

    def _get_observability_manager(self) -> Any:
        """获取可观测性管理器实例"""
        if not hasattr(self, "_observability_manager"):
            from src.core.transparency import ObservabilityManager

            self._observability_manager: Any = ObservabilityManager()
        return self._observability_manager

    def _get_trace_logger(self) -> Any:
        """获取追踪日志记录器实例"""
        if not hasattr(self, "_trace_logger"):
            from src.core.transparency import TraceLogger

            self._trace_logger: Any = TraceLogger()
        return self._trace_logger

    # ----------------------------------------------------------------
    # Subagent 方法
    # ----------------------------------------------------------------

    def spawn_subagent(
        self,
        subagent_type: str,
        user_request: str,
        date_range: str = "",
        report_type: str = "",
    ) -> dict[str, Any]:
        """调用Subagent执行专项任务

        实现"主Agent预查询 + 数据上下文传入"模式：
        1. 根据subagent_type预查询相关数据
        2. 将数据序列化并嵌入task参数
        3. 调用SpawnTool执行Subagent
        4. 返回Subagent执行结果或降级处理结果

        Args:
            subagent_type: Subagent类型 (data_analyst/report_writer)
            user_request: 用户原始请求
            date_range: 日期范围（可选，格式：YYYY-MM-DD ~ YYYY-MM-DD）
            report_type: 报告类型（可选，仅report_writer使用）

        Returns:
            dict: 包含success/data或error/fallback_result的字典
        """
        try:
            # 1. 预查询数据
            context_data = self._prepare_subagent_context(
                subagent_type=subagent_type,
                user_request=user_request,
                date_range=date_range,
                report_type=report_type,
            )

            # 2. 组装task参数（数据上下文格式）
            task = self._build_subagent_task(
                user_request=user_request,
                context_data=context_data,
            )

            # 3. 检查数据上下文大小
            context_size = len(task)
            if context_size > SpawnSubagentTool.MAX_CONTEXT_LENGTH:
                logger.warning(
                    f"Subagent数据上下文过大({context_size}字符)，进行截断处理"
                )
                task = self._truncate_context(task)
                context_size = len(task)

            # 4. 调用Subagent（通过SpawnTool）
            # 注意：SpawnTool由nanobot-ai底座自动注册，这里构建调用参数
            subagent_result = self._invoke_subagent(
                subagent_type=subagent_type,
                task=task,
            )

            return {
                "success": True,
                "data": {
                    "subagent_type": subagent_type,
                    "result": subagent_result,
                    "context_size": context_size,
                    "task_preview": task[:200] + "..." if len(task) > 200 else task,
                },
            }

        except NanobotRunnerError as e:
            logger.error(f"Subagent调用失败: {e}", exc_info=True)
            # 降级处理：返回预查询数据，让主Agent直接处理
            fallback_result = self._prepare_fallback_response(
                subagent_type=subagent_type,
                user_request=user_request,
                date_range=date_range,
                report_type=report_type,
            )
            return {
                "success": False,
                "error": f"Subagent调用失败: {str(e)}",
                "fallback_result": fallback_result,
            }

    def _prepare_subagent_context(
        self,
        subagent_type: str,
        user_request: str,
        date_range: str = "",
        report_type: str = "",
    ) -> dict[str, Any]:
        """预查询Subagent所需数据

        根据Subagent类型预查询相关数据：
        - data_analyst: VDOT趋势、训练负荷、心率漂移、最近跑步记录
        - report_writer: 跑步统计、日期范围查询、VDOT趋势

        Args:
            subagent_type: Subagent类型
            user_request: 用户请求
            date_range: 日期范围
            report_type: 报告类型

        Returns:
            dict: 预查询数据字典
        """
        context: dict[str, Any] = {}

        try:
            if subagent_type == "data_analyst":
                # 数据分析Subagent：预查询VDOT趋势、训练负荷、心率漂移
                context["vdot_trend"] = self.get_vdot_trend(limit=20)
                context["training_load"] = self.get_training_load(days=42)
                context["hr_drift"] = self.get_hr_drift_analysis()
                context["recent_runs"] = self.get_recent_runs(limit=10)
                context["user_request"] = user_request

            elif subagent_type == "report_writer":
                # 报告撰写Subagent：预查询跑步统计、日期范围数据
                if date_range:
                    # 解析日期范围
                    dates = date_range.split(" ~ ")
                    if len(dates) == 2:
                        context["runs_in_range"] = self.query_by_date_range(
                            dates[0], dates[1]
                        )
                    else:
                        context["recent_runs"] = self.get_recent_runs(limit=30)
                else:
                    context["recent_runs"] = self.get_recent_runs(limit=30)

                context["running_stats"] = self.get_running_stats()
                context["vdot_trend"] = self.get_vdot_trend(limit=20)
                context["training_load"] = self.get_training_load(days=42)
                context["report_type"] = report_type or "summary"
                context["user_request"] = user_request

            else:
                logger.warning(f"未知的Subagent类型: {subagent_type}")
                context["user_request"] = user_request
                context["error"] = f"不支持的Subagent类型: {subagent_type}"

        except NanobotRunnerError as e:
            logger.error(f"预查询Subagent数据失败: {e}")
            context["user_request"] = user_request
            context["error"] = f"数据预查询失败: {str(e)}"

        return context

    def _build_subagent_task(
        self,
        user_request: str,
        context_data: dict[str, Any],
    ) -> str:
        """组装Subagent的task参数

        数据上下文格式:
        {user_request}\n---数据上下文---\n{serialized_data}\n---数据上下文结束---

        Args:
            user_request: 用户请求
            context_data: 预查询数据

        Returns:
            str: 组装后的task参数字符串
        """
        # 序列化数据上下文
        serialized_data = json.dumps(
            context_data,
            ensure_ascii=False,
            default=str,
            indent=2,
        )

        # 组装task参数
        task = (
            f"{user_request}"
            f"{SpawnSubagentTool.CONTEXT_SEPARATOR}"
            f"{serialized_data}"
            f"{SpawnSubagentTool.CONTEXT_END}"
        )

        return task

    def _truncate_context(self, task: str) -> str:
        """截断数据上下文至最大长度

        当数据上下文超过MAX_CONTEXT_LENGTH时，保留用户请求部分，
        截断数据上下文部分。

        Args:
            task: 原始task参数

        Returns:
            str: 截断后的task参数
        """
        # 分离用户请求和数据上下文
        parts = task.split(SpawnSubagentTool.CONTEXT_SEPARATOR)
        if len(parts) != 2:
            # 格式异常，直接截断
            return task[: SpawnSubagentTool.MAX_CONTEXT_LENGTH - 3] + "..."

        user_request = parts[0]
        data_context = parts[1]

        # 计算固定开销（分隔符 + 结束标记 + "..."）
        fixed_overhead = (
            len(SpawnSubagentTool.CONTEXT_SEPARATOR)
            + len(SpawnSubagentTool.CONTEXT_END)
            + 3  # "..."长度
        )

        # 计算可用空间
        available_space = (
            SpawnSubagentTool.MAX_CONTEXT_LENGTH - len(user_request) - fixed_overhead
        )

        if available_space <= 0:
            # 用户请求本身已超限，截断用户请求
            # 计算错误消息长度
            error_msg = '{"error": "数据上下文被截断，仅保留用户请求"}'
            max_request_len = (
                SpawnSubagentTool.MAX_CONTEXT_LENGTH - fixed_overhead - len(error_msg)
            )
            return (
                f"{user_request[:max_request_len]}..."
                f"{SpawnSubagentTool.CONTEXT_SEPARATOR}"
                f"{error_msg}"
                f"{SpawnSubagentTool.CONTEXT_END}"
            )

        # 截断数据上下文
        truncated_data = data_context[:available_space] + "..."

        return (
            f"{user_request}"
            f"{SpawnSubagentTool.CONTEXT_SEPARATOR}"
            f"{truncated_data}"
            f"{SpawnSubagentTool.CONTEXT_END}"
        )

    def _invoke_subagent(
        self,
        subagent_type: str,
        task: str,
    ) -> dict[str, Any]:
        """调用Subagent执行

        通过nanobot-ai底座的SpawnTool调用Subagent。
        由于SpawnTool由AgentLoop自动管理，这里构建调用规范并返回预期结果格式。

        Args:
            subagent_type: Subagent类型
            task: 任务描述（包含数据上下文）

        Returns:
            dict: Subagent执行结果
        """
        # 验证Subagent类型
        valid_types = ["data_analyst", "report_writer"]
        if subagent_type not in valid_types:
            return {
                "subagent_type": subagent_type,
                "task": task,
                "label": subagent_type,
                "status": "error",
                "error": f"不支持的Subagent类型: {subagent_type}，支持的类型: {', '.join(valid_types)}",
                "note": (
                    f"Subagent类型 '{subagent_type}' 无效。"
                    f"请使用以下类型之一: {', '.join(valid_types)}"
                ),
            }

        # 构建Subagent调用规范
        # 注意：实际调用由AgentLoop的SpawnTool处理，这里返回调用参数供Agent使用
        return {
            "subagent_type": subagent_type,
            "task": task,
            "label": subagent_type,
            "status": "ready_to_spawn",
            "note": (
                "Subagent调用参数已准备就绪。"
                "实际调用由AgentLoop通过SpawnTool执行，"
                "结果将通过MessageBus注入主Agent会话。"
            ),
        }

    def _prepare_fallback_response(
        self,
        subagent_type: str,
        user_request: str,
        date_range: str = "",
        report_type: str = "",
    ) -> dict[str, Any]:
        """准备降级响应

        当Subagent调用失败时，返回预查询数据让主Agent直接处理。

        Args:
            subagent_type: Subagent类型
            user_request: 用户请求
            date_range: 日期范围
            report_type: 报告类型

        Returns:
            dict: 降级响应数据
        """
        try:
            fallback_data = self._prepare_subagent_context(
                subagent_type=subagent_type,
                user_request=user_request,
                date_range=date_range,
                report_type=report_type,
            )
            return {
                "type": "fallback",
                "subagent_type": subagent_type,
                "data": fallback_data,
                "message": "Subagent调用失败，已返回预查询数据供主Agent处理",
            }
        except NanobotRunnerError as e:
            logger.error(f"降级响应准备失败: {e}")
            return {
                "type": "fallback",
                "subagent_type": subagent_type,
                "error": f"无法准备降级数据: {str(e)}",
                "message": "Subagent调用失败且无法获取预查询数据",
            }

    # ----------------------------------------------------------------
    # 用户确认方法
    # ----------------------------------------------------------------

    def ask_user_confirm(
        self,
        scenario: str,
        prompt_id: str,
        context_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """创建异步用户确认提示 - v0.17.0新增（实验性功能）

        Agent通过此工具输出结构化选项+确认提示，用户在下一轮对话中确认。
        不支持同步阻塞模式（底座不支持）。

        支持场景：
        - training_plan: 训练计划确认
        - rpe_feedback: RPE体感评分
        - injury_risk: 伤病风险调整建议

        Args:
            scenario: 确认场景类型
            prompt_id: 提示ID（plan_id或session_id）
            context_data: 场景相关数据

        Returns:
            dict: 包含确认提示的结果
        """
        try:
            from src.core.base.context import get_context

            context = get_context()
            manager = context.ask_user_confirm_manager

            if scenario == "training_plan":
                plan_summary = context_data or {}
                prompt = manager.create_plan_confirm_prompt(prompt_id, plan_summary)
                return {
                    "success": True,
                    "prompt": prompt.to_dict(),
                    "agent_prompt": prompt.to_agent_prompt(),
                    "requires_user_response": True,
                    "note": "实验性功能：请在下轮对话中回复选项编号确认",
                }

            elif scenario == "rpe_feedback":
                session_summary = context_data or {}
                prompt = manager.create_rpe_prompt(prompt_id, session_summary)
                return {
                    "success": True,
                    "prompt": prompt.to_dict(),
                    "agent_prompt": prompt.to_agent_prompt(),
                    "requires_user_response": True,
                    "note": "实验性功能：请回复1-10分评分",
                }

            elif scenario == "injury_risk":
                risk_level = (
                    context_data.get("risk_level", "medium")
                    if context_data
                    else "medium"
                )
                suggestions = (
                    context_data.get("suggestions", []) if context_data else []
                )
                prompt = manager.create_injury_risk_prompt(
                    prompt_id, risk_level, suggestions
                )
                return {
                    "success": True,
                    "prompt": prompt.to_dict(),
                    "agent_prompt": prompt.to_agent_prompt(),
                    "requires_user_response": True,
                    "note": "实验性功能：请在下轮对话中回复选项确认",
                }

            else:
                return {
                    "success": False,
                    "error": f"不支持的确认场景: {scenario}",
                    "supported_scenarios": [
                        "training_plan",
                        "rpe_feedback",
                        "injury_risk",
                    ],
                }

        except NanobotRunnerError as e:
            logger.error(f"创建确认提示失败: {e}")
            return {"success": False, "error": str(e)}

    def parse_user_confirm_response(
        self,
        prompt_id: str,
        user_input: str,
    ) -> dict[str, Any]:
        """解析用户确认响应 - v0.17.0新增（实验性功能）

        解析用户对确认提示的响应，返回结构化结果。

        Args:
            prompt_id: 提示ID
            user_input: 用户输入

        Returns:
            dict: 解析结果
        """
        try:
            from src.core.base.context import get_context

            context = get_context()
            manager = context.ask_user_confirm_manager

            result = manager.parse_user_response(prompt_id, user_input)

            return {
                "success": True,
                "confirmed": result.is_confirmed,
                "status": result.status.value,
                "selected_key": result.selected_key,
                "selected_label": (
                    result.selected_option.label if result.selected_option else None
                ),
                "raw_input": result.raw_input,
                "result": result.to_dict(),
            }

        except NanobotRunnerError as e:
            logger.error(f"解析用户响应失败: {e}")
            return {"success": False, "error": str(e)}

    def ask_rpe_in_cli(
        self, session_summary: dict[str, Any] | None = None
    ) -> int | None:
        """在CLI中询问RPE评分 - v0.17.0新增

        Args:
            session_summary: 会话摘要

        Returns:
            int | None: RPE评分（1-10），取消返回None
        """
        try:
            from src.core.plan.ask_user_confirm import CLIConfirmHelper

            return CLIConfirmHelper.ask_rpe_in_cli(session_summary)
        except NanobotRunnerError as e:
            logger.error(f"CLI RPE询问失败: {e}")
            return None

    def _get_session_repo(self):
        """获取SessionRepository实例"""
        from src.core.storage.session_repository import SessionRepository

        return SessionRepository(self.storage)

    # ----------------------------------------------------------------
    # 身体信号方法
    # ----------------------------------------------------------------

    def get_hrv_analysis(self, days: int = 30) -> dict[str, Any]:
        """获取HRV分析结果 - v0.19.0新增"""
        try:
            from src.core.body_signal.hrv_analyzer import HRVAnalyzer

            hrv_analyzer = HRVAnalyzer(session_repo=self._get_session_repo())
            hrv_result = hrv_analyzer.analyze_hrv(days=days)
            hrv_metrics = hrv_analyzer.estimate_hrv_metrics()

            result = hrv_result.to_dict()
            result["estimated_hrv_metrics"] = hrv_metrics
            return {"success": True, "data": result}
        except NanobotRunnerError as e:
            logger.error(f"HRV分析失败: {e}")
            return {"success": False, "error": str(e)}

    def get_hr_recovery(self) -> dict[str, Any]:
        """获取心率恢复分析 - v0.19.0新增"""
        try:
            from src.core.body_signal.hrv_analyzer import HRVAnalyzer

            hrv_analyzer = HRVAnalyzer(session_repo=self._get_session_repo())
            recovery_result = hrv_analyzer.analyze_hr_recovery()
            return {"success": True, "data": recovery_result.to_dict()}
        except NanobotRunnerError as e:
            logger.error(f"心率恢复分析失败: {e}")
            return {"success": False, "error": str(e)}

    def get_fatigue_score(self, rpe: int | None = None) -> dict[str, Any]:
        """获取疲劳度评估 - v0.19.0新增"""
        try:
            from src.core.body_signal.fatigue_assessor import FatigueAssessor
            from src.core.calculators.training_load_analyzer import TrainingLoadAnalyzer

            training_load_analyzer = TrainingLoadAnalyzer()
            fatigue_assessor = FatigueAssessor(
                session_repo=self._get_session_repo(),
                training_load_analyzer=training_load_analyzer,
            )
            fatigue_result = fatigue_assessor.assess_fatigue(rpe=rpe)
            return {"success": True, "data": fatigue_result.to_dict()}
        except NanobotRunnerError as e:
            logger.error(f"疲劳度评估失败: {e}")
            return {"success": False, "error": str(e)}

    def get_recovery_status(self) -> dict[str, Any]:
        """获取恢复状态 - v0.19.0新增"""
        try:
            from src.core.body_signal.hrv_analyzer import HRVAnalyzer
            from src.core.body_signal.recovery_monitor import RecoveryMonitor
            from src.core.calculators.training_load_analyzer import TrainingLoadAnalyzer

            training_load_analyzer = TrainingLoadAnalyzer()
            hrv_analyzer = HRVAnalyzer(session_repo=self._get_session_repo())
            recovery_monitor = RecoveryMonitor(
                session_repo=self._get_session_repo(),
                training_load_analyzer=training_load_analyzer,
                hrv_analyzer=hrv_analyzer,
            )
            recovery_result = recovery_monitor.get_recovery_status()
            return {"success": True, "data": recovery_result.to_dict()}
        except NanobotRunnerError as e:
            logger.error(f"恢复状态获取失败: {e}")
            return {"success": False, "error": str(e)}

    def get_body_signal_summary(self, period: str = "daily") -> dict[str, Any]:
        """获取身体信号综合摘要 - v0.19.0新增"""
        try:
            from src.core.body_signal import BodySignalEngine
            from src.core.body_signal.fatigue_assessor import FatigueAssessor
            from src.core.body_signal.hrv_analyzer import HRVAnalyzer
            from src.core.body_signal.recovery_monitor import RecoveryMonitor
            from src.core.calculators.training_load_analyzer import TrainingLoadAnalyzer

            training_load_analyzer = TrainingLoadAnalyzer()
            hrv_analyzer = HRVAnalyzer(session_repo=self._get_session_repo())
            fatigue_assessor = FatigueAssessor(
                session_repo=self._get_session_repo(),
                training_load_analyzer=training_load_analyzer,
            )
            recovery_monitor = RecoveryMonitor(
                session_repo=self._get_session_repo(),
                training_load_analyzer=training_load_analyzer,
                hrv_analyzer=hrv_analyzer,
            )
            engine = BodySignalEngine(
                hrv_analyzer=hrv_analyzer,
                fatigue_assessor=fatigue_assessor,
                recovery_monitor=recovery_monitor,
            )

            if period == "weekly":
                summary = engine.get_weekly_summary()
            else:
                summary = engine.get_daily_summary()

            return {"success": True, "data": summary.to_dict()}
        except NanobotRunnerError as e:
            logger.error(f"身体信号摘要获取失败: {e}")
            return {"success": False, "error": str(e)}

    def compare_training_periods(
        self, period1_days: int = 7, period2_days: int = 7
    ) -> dict[str, Any]:
        """对比两个训练周期的身体信号变化 - v0.19.0新增"""
        try:
            from src.core.body_signal.hrv_analyzer import HRVAnalyzer
            from src.core.body_signal.recovery_monitor import RecoveryMonitor
            from src.core.calculators.training_load_analyzer import TrainingLoadAnalyzer

            training_load_analyzer = TrainingLoadAnalyzer()
            hrv_analyzer = HRVAnalyzer(session_repo=self._get_session_repo())
            recovery_monitor = RecoveryMonitor(
                session_repo=self._get_session_repo(),
                training_load_analyzer=training_load_analyzer,
                hrv_analyzer=hrv_analyzer,
            )

            trend1 = recovery_monitor.get_recovery_trend(days=period1_days)
            trend2 = recovery_monitor.get_recovery_trend(
                days=period2_days + period1_days
            )
            trend2 = trend2[:-period1_days] if len(trend2) > period1_days else []

            avg_tsb1 = sum(p.tsb for p in trend1) / len(trend1) if trend1 else 0.0
            avg_tsb2 = sum(p.tsb for p in trend2) / len(trend2) if trend2 else 0.0

            hrv1 = hrv_analyzer.analyze_hrv(days=period1_days)
            hrv2 = hrv_analyzer.analyze_hrv(days=period2_days + period1_days)

            return {
                "success": True,
                "data": {
                    "period1_days": period1_days,
                    "period2_days": period2_days,
                    "period1": {
                        "avg_tsb": round(avg_tsb1, 2),
                        "data_points": len(trend1),
                        "hrv_data_quality": hrv1.data_quality.value,
                    },
                    "period2": {
                        "avg_tsb": round(avg_tsb2, 2),
                        "data_points": len(trend2),
                        "hrv_data_quality": hrv2.data_quality.value,
                    },
                    "tsb_change": round(avg_tsb1 - avg_tsb2, 2),
                    "comparison_summary": (
                        "近期恢复状态改善"
                        if avg_tsb1 > avg_tsb2
                        else "近期恢复状态下降"
                    ),
                },
            }
        except NanobotRunnerError as e:
            logger.error(f"训练周期对比失败: {e}")
            return {"success": False, "error": str(e)}

    # ----------------------------------------------------------------
    # 预测方法
    # ----------------------------------------------------------------

    def predict_vdot_trend(self, days: int = 30) -> dict[str, Any]:
        """VDOT趋势预测 - v0.20.0新增"""
        try:
            from src.core.base.context import get_context

            context = get_context()
            engine = context.prediction_engine
            result = engine.predict_vdot_trend(days=days)
            return {"success": True, "data": result.to_dict()}
        except NanobotRunnerError as e:
            logger.error(f"VDOT趋势预测失败: {e}")
            return {"success": False, "error": str(e)}

    def predict_race_result(
        self, distance_km: float, race_date: str | None = None
    ) -> dict[str, Any]:
        """比赛成绩预测 - v0.20.0新增"""
        try:
            from src.core.base.context import get_context

            context = get_context()
            engine = context.prediction_engine
            result = engine.predict_race_result(
                distance_km=distance_km, race_date=race_date
            )
            return {"success": True, "data": result.to_dict()}
        except NanobotRunnerError as e:
            logger.error(f"比赛成绩预测失败: {e}")
            return {"success": False, "error": str(e)}

    def predict_injury_risk(self, days: int = 21) -> dict[str, Any]:
        """伤病风险预测 - v0.20.0新增"""
        try:
            from src.core.base.context import get_context

            context = get_context()
            engine = context.prediction_engine
            result = engine.predict_injury_risk(days=days)
            return {"success": True, "data": result.to_dict()}
        except NanobotRunnerError as e:
            logger.error(f"伤病风险预测失败: {e}")
            return {"success": False, "error": str(e)}

    def predict_training_response(
        self, session_type: str, duration_min: int, intensity: str
    ) -> dict[str, Any]:
        """训练响应预测 - v0.20.0新增"""
        try:
            from src.core.base.context import get_context

            context = get_context()
            engine = context.prediction_engine
            result = engine.predict_training_response(
                session_type=session_type,
                duration_min=duration_min,
                intensity=intensity,
            )
            return {"success": True, "data": result.to_dict()}
        except NanobotRunnerError as e:
            logger.error(f"训练响应预测失败: {e}")
            return {"success": False, "error": str(e)}

    def check_prediction_status(self) -> dict[str, Any]:
        """预测数据充足度评估 - v0.20.0新增"""
        try:
            from src.core.base.context import get_context

            context = get_context()
            engine = context.prediction_engine
            result = engine.check_prediction_status()
            return {"success": True, "data": result.to_dict()}
        except NanobotRunnerError as e:
            logger.error(f"预测状态检查失败: {e}")
            return {"success": False, "error": str(e)}

    def report_injury(
        self, injury_type: str, severity: str, date: str
    ) -> dict[str, Any]:
        """伤病报告提交 - v0.20.1新增"""
        try:
            from src.core.base.context import get_context

            context = get_context()
            engine = context.prediction_engine
            result = engine.report_injury(
                injury_type=injury_type,
                severity=severity,
                date=date,
            )
            return {"success": True, "data": result.to_dict()}
        except NanobotRunnerError as e:
            logger.error(f"伤病报告提交失败: {e}")
            return {"success": False, "error": str(e)}

    def manage_prediction_model(self, action: str, model_type: str) -> dict[str, Any]:
        """预测模型管理 - v0.20.1新增"""
        try:
            from src.core.base.context import get_context

            context = get_context()
            engine = context.prediction_engine
            result = engine.manage_model(action=action, model_type=model_type)
            return {"success": True, "data": result.to_dict()}
        except NanobotRunnerError as e:
            logger.error(f"模型管理失败: {e}")
            return {"success": False, "error": str(e)}

    # ----------------------------------------------------------------
    # 数字孪生方法
    # ----------------------------------------------------------------

    def get_twin_snapshot(self) -> dict[str, Any]:
        """获取数字孪生状态快照 - v0.21.0新增"""
        try:
            from src.core.base.context import get_context

            context = get_context()
            engine = context.digital_twin_engine
            result = engine.get_current_snapshot()
            return {"success": True, "data": result.to_dict()}
        except NanobotRunnerError as e:
            logger.error(f"获取数字孪生快照失败: {e}")
            return {"success": False, "error": str(e)}

    def simulate_twin(
        self,
        plan_name: str,
        weeks: list[dict[str, Any]],
        prediction_type: str = "parametric",
    ) -> dict[str, Any]:
        """数字孪生What-If推演 - v0.21.0新增"""
        try:
            from src.core.base.context import get_context
            from src.core.twin.models import HypotheticalPlan

            context = get_context()
            engine = context.digital_twin_engine
            plan = HypotheticalPlan.from_week_dicts(plan_name, weeks, source="agent")
            result = engine.simulate(plan, prediction_type=prediction_type)
            return {"success": True, "data": result.to_dict()}
        except NanobotRunnerError as e:
            logger.error(f"数字孪生推演失败: {e}")
            return {"success": False, "error": str(e)}

    def compare_twin_plans(
        self, plans: list[dict[str, Any]], prediction_type: str = "parametric"
    ) -> dict[str, Any]:
        """数字孪生多计划对比 - v0.21.0新增"""
        try:
            from src.core.base.context import get_context
            from src.core.twin.models import HypotheticalPlan

            context = get_context()
            engine = context.digital_twin_engine
            hypothetical_plans = [
                HypotheticalPlan.from_week_dicts(
                    p.get("name", "未命名"), p.get("weeks", []), source="agent"
                )
                for p in plans
            ]
            result = engine.compare_plans(
                hypothetical_plans, prediction_type=prediction_type
            )
            return {"success": True, "data": result.to_dict()}
        except NanobotRunnerError as e:
            logger.error(f"数字孪生计划对比失败: {e}")
            return {"success": False, "error": str(e)}

    # ----------------------------------------------------------------
    # 决策追踪方法
    # ----------------------------------------------------------------

    def record_decision_feedback(
        self,
        decision_id: str,
        score: int,
        text: str | None = None,
        accepted: bool | None = None,
    ) -> dict[str, Any]:
        """记录用户对AI决策的反馈 - v0.23.0新增

        Args:
            decision_id: 决策唯一标识
            score: 用户反馈评分（1-5）
            text: 用户反馈文本（可选）
            accepted: 推荐是否被采纳（可选）

        Returns:
            dict: 包含success/data或error的字典
        """
        try:
            from src.core.base.context import get_context

            context = get_context()
            engine = context.evolution_engine
            outcome = engine.record_feedback(decision_id, score, text, accepted)
            return {"success": True, "data": outcome.to_dict()}
        except NanobotRunnerError as e:
            logger.error(f"记录决策反馈失败: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"记录决策反馈未预期异常: {e}", exc_info=True)
            return {"success": False, "error": f"{type(e).__name__}: {str(e)}"}

    def check_plan_execution(self, decision_id: str) -> dict[str, Any]:
        """检查计划执行忠实度 - v0.23.0新增

        输出含execution_fidelity/volume_deviation/time_deviation，
        不含intensity_deviation（评审遗留NP-02）。

        Args:
            decision_id: 决策唯一标识

        Returns:
            dict: 包含success/data或error的字典
        """
        try:
            from src.core.base.context import get_context

            context = get_context()
            engine = context.evolution_engine
            outcome = engine.check_plan_execution(decision_id)
            data = outcome.to_dict()
            # 不含intensity_deviation（评审遗留NP-02）
            return {"success": True, "data": data}
        except NanobotRunnerError as e:
            logger.error(f"检查计划执行失败: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"检查计划执行未预期异常: {e}", exc_info=True)
            return {"success": False, "error": f"{type(e).__name__}: {str(e)}"}

    def check_prediction_accuracy(
        self, decision_id: str, actual_vdot: float = 0.0
    ) -> dict[str, Any]:
        """检查预测准确度 - v0.23.0新增

        输出含prediction_error/prediction_direction/mae，
        使用prediction_direction（非error_direction，评审遗留NP-03）。

        Args:
            decision_id: 决策唯一标识
            actual_vdot: 实际VDOT值（默认0.0，0.0时尝试从最新session获取）

        Returns:
            dict: 包含success/data或error的字典
        """
        try:
            from src.core.base.context import get_context

            context = get_context()
            engine = context.evolution_engine

            # actual_vdot为0.0时，尝试从最新session获取
            if actual_vdot == 0.0:
                actual_vdot = self._get_latest_vdot()

            outcome, stats = engine.check_prediction_accuracy(decision_id, actual_vdot)
            data = {
                **outcome.to_dict(),
                "mae": stats.mae,
                "total_pairs": stats.total_pairs,
            }
            return {"success": True, "data": data}
        except NanobotRunnerError as e:
            logger.error(f"检查预测准确度失败: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"检查预测准确度未预期异常: {e}", exc_info=True)
            return {"success": False, "error": f"{type(e).__name__}: {str(e)}"}

    def get_decision_history(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        decision_type_str: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """查询决策历史 - v0.23.0新增

        Args:
            start_date: 起始日期（可选，格式：YYYY-MM-DD）
            end_date: 结束日期（可选，格式：YYYY-MM-DD）
            decision_type_str: 决策类型过滤（可选）
            limit: 返回数量限制（默认50）

        Returns:
            dict: 包含success/data或error的字典
        """
        try:
            from datetime import datetime as dt

            from src.core.base.context import get_context
            from src.core.transparency.models import DecisionType

            context = get_context()
            engine = context.evolution_engine

            # 解析日期字符串
            parsed_start: dt | None = None
            parsed_end: dt | None = None
            if start_date:
                try:
                    parsed_start = dt.strptime(start_date, "%Y-%m-%d")
                except ValueError:
                    return {
                        "success": False,
                        "error": f"起始日期格式错误: {start_date}",
                    }
            if end_date:
                try:
                    parsed_end = dt.strptime(end_date, "%Y-%m-%d")
                except ValueError:
                    return {"success": False, "error": f"结束日期格式错误: {end_date}"}

            # 解析决策类型
            decision_type: DecisionType | None = None
            if decision_type_str:
                try:
                    decision_type = DecisionType(decision_type_str)
                except ValueError:
                    return {
                        "success": False,
                        "error": f"无效的决策类型: {decision_type_str}",
                    }

            history = engine.get_decision_history(
                start_date=parsed_start,
                end_date=parsed_end,
                decision_type=decision_type,
                limit=limit,
            )
            return {
                "success": True,
                "data": [d.to_dict() for d in history],
            }
        except NanobotRunnerError as e:
            logger.error(f"查询决策历史失败: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"查询决策历史未预期异常: {e}", exc_info=True)
            return {"success": False, "error": f"{type(e).__name__}: {str(e)}"}

    def _get_latest_vdot(self) -> float:
        """从最新session获取VDOT值

        Returns:
            float: 最新VDOT值，获取失败返回0.0
        """
        try:
            vdot_trend = self.get_vdot_trend(limit=1)
            if vdot_trend and vdot_trend[0].get("vdot") is not None:
                return float(vdot_trend[0]["vdot"])
        except Exception as e:
            logger.warning(f"获取最新VDOT失败: {e}")
        return 0.0

    def analyze_training_response_v2(self, months: int = 6) -> dict[str, Any]:
        """分析训练响应性 - v0.24.0新增"""
        try:
            from src.core.base.context import get_context

            context = get_context()
            report = context.evolution_engine.analyze_training_response(months=months)
            return {"success": True, "data": report.to_dict()}
        except Exception as e:
            logger.error(f"分析训练响应性失败: {e}", exc_info=True)
            return {"success": False, "error": f"{type(e).__name__}: {str(e)}"}

    def run_calibration(self, model_type: str = "vdot") -> dict[str, Any]:
        """执行预测校准 - v0.24.0新增"""
        try:
            from src.core.base.context import get_context

            context = get_context()
            report = context.evolution_engine.run_calibration(model_type)
            return {"success": True, "data": report.to_dict()}
        except Exception as e:
            logger.error(f"执行预测校准失败: {e}", exc_info=True)
            return {"success": False, "error": f"{type(e).__name__}: {str(e)}"}

    def get_calibration_status(self, model_type: str | None = None) -> dict[str, Any]:
        """获取校准状态 - v0.24.0新增"""
        try:
            from src.core.base.context import get_context

            context = get_context()
            result = context.evolution_engine.get_calibration_status(model_type)
            if isinstance(result, dict):
                return {"success": True, "data": result}
            return {"success": True, "data": result.to_dict()}
        except Exception as e:
            logger.error(f"获取校准状态失败: {e}", exc_info=True)
            return {"success": False, "error": f"{type(e).__name__}: {str(e)}"}


# ============================================================================
# Re-exports: 从子模块导入所有工具类，保持向后兼容
# ============================================================================

# 统计/分析工具
# 身体信号/健康工具
from .tools_body import (  # noqa: E402
    AskUserConfirmTool,
    CompareTrainingPeriodsTool,
    GetBodySignalSummaryTool,
    GetFatigueScoreTool,
    GetHrRecoveryTool,
    GetHrvAnalysisTool,
    GetRecoveryStatusTool,
    ParseUserConfirmTool,
)

# 数据管理/系统工具
from .tools_data import (  # noqa: E402
    DiagnoseErrorTool,
    DiagnoseSuggestionTool,
    ExplainDecisionTool,
    GetPersonalizedSuggestionTool,
    GetTransparencyInsightTool,
    GetUserPreferencesTool,
    RecordFeedbackTool,
    TraceDataSourcesTool,
    UpdateMemoryTool,
    UpdateUserPreferencesTool,
)

# 决策追踪工具
from .tools_evolution import (  # noqa: E402
    AnalyzeTrainingResponseV2Tool,
    CheckPlanExecutionTool,
    CheckPredictionAccuracyTool,
    GetCalibrationStatusTool,
    GetDecisionHistoryTool,
    RunCalibrationTool,
)
from .tools_evolution import (  # noqa: E402
    RecordFeedbackTool as RecordDecisionFeedbackTool,
)

# 训练计划工具
from .tools_plan import (  # noqa: E402
    AdjustPlanTool,
    AnalyzeTrainingResponseTool,
    CreateLongTermPlanTool,
    EvaluateGoalAchievementTool,
    GenerateTrainingPlanTool,
    GetPlanAdjustmentSuggestionsTool,
    GetPlanExecutionStatsTool,
    GetSmartTrainingAdviceTool,
    GetWeatherTrainingAdviceTool,
    RecordPlanExecutionTool,
)
from .tools_stats import (  # noqa: E402
    CalculateVdotForRunTool,
    GetHrDriftAnalysisTool,
    GetRecentRunsTool,
    GetRunningStatsTool,
    GetTrainingLoadTool,
    GetVdotTrendTool,
    QueryByDateRangeTool,
    QueryByDistanceTool,
)

# 数字孪生/预测工具
from .tools_twin import (  # noqa: E402
    CheckPredictionStatusTool,
    CompareTwinPlansTool,
    GetTwinSnapshotTool,
    ManagePredictionModelTool,
    PredictInjuryRiskTool,
    PredictRaceResultTool,
    PredictTrainingResponseTool,
    PredictVdotTrendTool,
    ReportInjuryTool,
    SimulateTwinTool,
    SpawnSubagentTool,
)

# ============================================================================
# 工厂函数
# ============================================================================


def create_tools(runner_tools: RunnerTools) -> list[BaseTool]:
    """创建工具实例列表（供 nanobot-ai 使用）"""
    return [
        GetRunningStatsTool(runner_tools),
        GetRecentRunsTool(runner_tools),
        CalculateVdotForRunTool(runner_tools),
        GetVdotTrendTool(runner_tools),
        GetHrDriftAnalysisTool(runner_tools),
        GetTrainingLoadTool(runner_tools),
        QueryByDateRangeTool(runner_tools),
        QueryByDistanceTool(runner_tools),
        UpdateMemoryTool(runner_tools),
        GenerateTrainingPlanTool(runner_tools),
        RecordPlanExecutionTool(runner_tools),
        GetPlanExecutionStatsTool(runner_tools),
        AnalyzeTrainingResponseTool(runner_tools),
        AdjustPlanTool(runner_tools),
        GetPlanAdjustmentSuggestionsTool(runner_tools),
        EvaluateGoalAchievementTool(runner_tools),
        CreateLongTermPlanTool(runner_tools),
        GetSmartTrainingAdviceTool(runner_tools),
        GetWeatherTrainingAdviceTool(runner_tools),
        SpawnSubagentTool(runner_tools),
        AskUserConfirmTool(runner_tools),
        ParseUserConfirmTool(runner_tools),
        DiagnoseSuggestionTool(runner_tools),
        DiagnoseErrorTool(runner_tools),
        GetPersonalizedSuggestionTool(runner_tools),
        RecordFeedbackTool(runner_tools),
        GetUserPreferencesTool(runner_tools),
        UpdateUserPreferencesTool(runner_tools),
        ExplainDecisionTool(runner_tools),
        TraceDataSourcesTool(runner_tools),
        GetTransparencyInsightTool(runner_tools),
        GetHrvAnalysisTool(runner_tools),
        GetHrRecoveryTool(runner_tools),
        GetFatigueScoreTool(runner_tools),
        GetRecoveryStatusTool(runner_tools),
        GetBodySignalSummaryTool(runner_tools),
        CompareTrainingPeriodsTool(runner_tools),
        PredictVdotTrendTool(runner_tools),
        PredictRaceResultTool(runner_tools),
        PredictInjuryRiskTool(runner_tools),
        PredictTrainingResponseTool(runner_tools),
        CheckPredictionStatusTool(runner_tools),
        ReportInjuryTool(runner_tools),
        ManagePredictionModelTool(runner_tools),
        GetTwinSnapshotTool(runner_tools),
        SimulateTwinTool(runner_tools),
        CompareTwinPlansTool(runner_tools),
        # 决策追踪工具
        RecordDecisionFeedbackTool(runner_tools),
        CheckPlanExecutionTool(runner_tools),
        CheckPredictionAccuracyTool(runner_tools),
        GetDecisionHistoryTool(runner_tools),
        # v0.24.0 个性化学习工具
        AnalyzeTrainingResponseV2Tool(runner_tools),
        RunCalibrationTool(runner_tools),
        GetCalibrationStatusTool(runner_tools),
    ]


# ============================================================================
# 工具描述字典
# ============================================================================


TOOL_DESCRIPTIONS = {
    "get_running_stats": {
        "description": "获取跑步统计数据，包括总次数、总距离、平均距离等。返回JSON格式：{success: true, data: {total_runs: 总次数, total_distance: 总距离(米), total_duration: 总时长(秒), avg_distance: 平均距离(米), avg_duration: 平均时长(秒), max_distance: 最大距离(米), avg_heart_rate: 平均心率}} 或 {success: false, error: 错误信息}",
        "parameters": {
            "start_date": "开始日期（可选，格式：YYYY-MM-DD）",
            "end_date": "结束日期（可选，格式：YYYY-MM-DD）",
        },
    },
    "get_recent_runs": {
        "description": "获取最近的跑步记录列表。返回JSON格式：{success: true, data: [{timestamp: 时间, distance_km: 距离(公里), duration_min: 时长(分钟), avg_pace_sec_km: 配速(秒/公里), avg_heart_rate: 平均心率, vdot: VDOT值}, ...]} 或 {success: false, error: 错误信息}。注意：vdot字段已包含计算好的VDOT值，直接使用即可，不要自己计算",
        "parameters": {"limit": "返回数量限制（默认 10 条）"},
    },
    "calculate_vdot_for_run": {
        "description": "计算单次跑步的VDOT值（跑力值），使用Jack Daniels公式自动计算。注意：VDOT计算公式复杂，请使用此工具计算，不要自己用简单公式计算",
        "parameters": {"distance_m": "距离（米）", "time_s": "用时（秒）"},
    },
    "get_vdot_trend": {
        "description": "获取VDOT（跑力值）趋势变化，自动从历史跑步数据计算每次跑步的VDOT值。当用户询问'我的VDOT是多少'、'我的跑力值'或'查看VDOT趋势'时使用此工具。不需要用户提供任何参数。返回JSON格式：{success: true, data: [{timestamp: 时间, distance: 距离(米), vdot: VDOT值}, ...]} 或 {success: false, error: 错误信息}",
        "parameters": {"limit": "返回数量限制（默认 20 条，可选）"},
    },
    "get_hr_drift_analysis": {
        "description": "分析心率漂移情况",
        "parameters": {"run_id": "活动 ID（可选）"},
    },
    "get_training_load": {
        "description": "获取训练负荷（ATL/CTL）",
        "parameters": {"days": "分析天数（默认 42 天）"},
    },
    "query_by_date_range": {
        "description": "按日期范围查询跑步记录。返回JSON格式：{success: true, data: [{timestamp: 时间, distance: 距离(公里), duration: 时长(秒), heart_rate: 平均心率, pace: 配速(分钟/公里)}, ...]} 或 {success: false, error: 错误信息}",
        "parameters": {
            "start_date": "开始日期（格式：YYYY-MM-DD）",
            "end_date": "结束日期（格式：YYYY-MM-DD）",
        },
    },
    "query_by_distance": {
        "description": "按距离范围查询跑步记录。返回JSON格式：{success: true, data: [{timestamp: 时间, distance: 距离(公里), duration: 时长(秒), heart_rate: 平均心率, pace: 配速(分钟/公里)}, ...]} 或 {success: false, error: 错误信息}",
        "parameters": {
            "min_distance": "最小距离（公里）",
            "max_distance": "最大距离（公里，可选）",
        },
    },
    "update_memory": {
        "description": "更新 Agent 观察笔记到 MEMORY.md",
        "parameters": {
            "note": "观察笔记内容",
            "category": "笔记分类（training/preference/injury/other，默认 other）",
        },
    },
    "record_plan_execution": {
        "description": "记录训练计划执行反馈，包括完成度、体感评分、反馈备注等。返回JSON格式：{success: true, data: {plan_id: 计划ID, date: 日期, message: 反馈消息}} 或 {success: false, error: 错误信息}",
        "parameters": {
            "plan_id": "训练计划ID（必填）",
            "date": "日期，格式YYYY-MM-DD（必填）",
            "completion_rate": "完成度（0.0-1.0，可选）",
            "effort_score": "体感评分（1-10，可选）",
            "notes": "反馈备注（可选）",
            "actual_distance_km": "实际距离（公里，可选）",
            "actual_duration_min": "实际时长（分钟，可选）",
            "actual_avg_hr": "实际平均心率（可选）",
        },
    },
    "get_plan_execution_stats": {
        "description": "获取训练计划执行统计，包括完成率、平均体感评分、总距离等。返回JSON格式：{success: true, data: {plan_id, total_planned_days, completed_days, completion_rate, avg_effort_score, total_distance_km, total_duration_min, avg_hr, avg_hr_drift}} 或 {success: false, error: 错误信息}",
        "parameters": {
            "plan_id": "训练计划ID（必填）",
        },
    },
    "adjust_plan": {
        "description": "调整训练计划。支持自然语言调整指令，如'下周减量'、'把周三的间歇跑改成轻松跑'。返回JSON格式：{success: true, data: {plan_id, adjustment, validation, requires_confirmation}} 或 {success: false, error: 错误信息, violations: 违规列表}",
        "parameters": {
            "plan_id": "训练计划ID（必填）",
            "adjustment_request": "调整请求（自然语言），如'下周减量20%'、'增加间歇跑'（必填）",
            "confirmation_required": "是否需要确认后再执行调整（默认true）",
        },
    },
    "get_plan_adjustment_suggestions": {
        "description": "获取训练计划调整建议。基于训练数据和执行反馈，生成个性化调整建议。返回JSON格式：{success: true, data: {plan_id, suggestions}} 或 {success: false, error: 错误信息}",
        "parameters": {
            "plan_id": "训练计划ID（必填）",
        },
    },
    "evaluate_goal_achievement": {
        "description": "评估目标达成概率。基于当前体能、训练趋势和目标差距，预测目标达成概率和关键风险。返回JSON格式：{success: true, data: {goal_type, goal_value, current_value, achievement_probability, key_risks, improvement_suggestions, estimated_weeks_to_achieve, confidence, gap, achievement_rate}} 或 {success: false, error: 错误信息}",
        "parameters": {
            "goal_type": "目标类型（vdot/5k/10k/half_marathon/marathon，必填）",
            "goal_value": "目标值（VDOT值或秒数，必填）",
            "current_vdot": "当前VDOT值（必填）",
            "weeks_available": "可用训练周数（可选）",
        },
    },
    "create_long_term_plan": {
        "description": "创建长期训练规划。支持年度/赛季/多周期规划，自动生成基础期、提升期、巅峰期、减量期。返回JSON格式：{success: true, data: {plan_name, target_race, target_date, current_vdot, target_vdot, total_weeks, cycles, weekly_volume_range_km, key_milestones}} 或 {success: false, error: 错误信息}",
        "parameters": {
            "plan_name": "计划名称（必填）",
            "current_vdot": "当前VDOT值（必填）",
            "target_vdot": "目标VDOT值（可选）",
            "target_race": "目标赛事名称（可选）",
            "target_date": "目标日期（YYYY-MM-DD，可选）",
            "total_weeks": "总训练周数（默认16）",
            "fitness_level": "体能水平（beginner/intermediate/advanced/elite，默认intermediate）",
        },
    },
    "get_smart_training_advice": {
        "description": "获取智能训练建议。基于训练数据和体能状态，生成训练、恢复、营养、伤病预防等多维度建议。返回JSON格式：{success: true, data: {advices: [{advice_type, content, priority, context, confidence, related_metrics}], total_count}} 或 {success: false, error: 错误信息}",
        "parameters": {
            "current_vdot": "当前VDOT值（可选）",
            "weekly_volume_km": "周跑量（公里，可选）",
            "training_consistency": "训练一致性（0-1，可选）",
            "injury_risk": "伤病风险（low/medium/high，可选）",
            "goal_type": "目标类型（5k/10k/half_marathon/marathon，可选）",
        },
    },
    "get_weather_training_advice": {
        "description": "获取天气+训练综合建议。结合天气数据和训练数据，生成多维度的训练建议。当用户询问'今天适合跑步吗'、'天气对训练的影响'、'综合训练建议'时使用此工具。返回JSON格式：{success: true, data: {advices: [{advice_type, content, priority, reason, weather_impact, training_impact}], total_count, weather_impact, formatted_advice}} 或 {success: false, error: 错误信息}",
        "parameters": {
            "temperature": "温度（摄氏度，必填）",
            "humidity": "湿度（百分比，0-100，必填）",
            "weather": "天气状况（晴/阴/雨/雪等，必填）",
            "wind": "风力描述（可选）",
            "precipitation": "降水概率（百分比，0-100，可选）",
            "uv_index": "紫外线指数（可选）",
        },
    },
    "spawn_subagent": {
        "description": "调用Subagent执行专项任务。支持数据分析(data_analyst)和报告撰写(report_writer)两种Subagent。主Agent会自动预查询相关数据并传入Subagent。当用户需要深度数据分析、生成训练周报/月报时使用此工具。返回JSON格式: {success: true, data: {subagent_type, result, context_size}} 或 {success: false, error: 错误信息, fallback_result: 降级结果}",
        "parameters": {
            "subagent_type": "Subagent类型: data_analyst(数据分析) / report_writer(报告撰写)",
            "user_request": "用户的原始请求描述",
            "date_range": "日期范围（可选，格式：YYYY-MM-DD ~ YYYY-MM-DD）",
            "report_type": "报告类型（可选，仅report_writer使用）：weekly/monthly/summary",
        },
    },
    "ask_user_confirm": {
        "description": "异步用户确认工具（实验性功能）。当需要用户确认训练计划、RPE评分、伤病风险调整建议时使用此工具。工具会生成结构化选项，用户在下轮对话中回复选项编号确认。返回JSON格式: {success: true, prompt: 提示结构, agent_prompt: 展示给用户的文本, requires_user_response: true} 或 {success: false, error: 错误信息}",
        "parameters": {
            "scenario": "确认场景: training_plan(训练计划确认) / rpe_feedback(体感评分) / injury_risk(伤病风险调整)",
            "prompt_id": "提示ID（plan_id或session_id）",
            "context_data": "场景相关数据（可选）。training_plan需要{goal, weeks, weekly_volume_km}；rpe_feedback需要{distance_km, duration_min}；injury_risk需要{risk_level, suggestions}",
        },
    },
    "parse_user_confirm": {
        "description": "解析用户对确认提示的响应（实验性功能）。在ask_user_confirm之后使用，解析用户回复的选项编号或选项名称。返回JSON格式: {success: true, confirmed: 是否确认, status: 状态, selected_key: 选项key, selected_label: 选项标签, raw_input: 原始输入} 或 {success: false, error: 错误信息}",
        "parameters": {
            "prompt_id": "提示ID（与ask_user_confirm中的prompt_id一致）",
            "user_input": "用户的回复内容",
        },
    },
    "diagnose_suggestion": {
        "description": "验证AI建议质量，检查建议的完整性、相关性、安全性和可执行性。当AI需要自我检查建议质量时使用此工具。返回JSON格式：{success: true, data: {id, category, overall_status, pass_count, fail_count, results}} 或 {success: false, error: 错误信息}",
        "parameters": {
            "user_query": "用户原始查询（必填）",
            "suggestion_text": "AI生成的建议文本（必填）",
            "tools_used": "使用的工具列表（可选）",
        },
    },
    "diagnose_error": {
        "description": "诊断错误原因，分析错误根因并给出修复建议。当AI遇到执行错误、工具调用失败时使用此工具进行自我诊断。返回JSON格式：{success: true, data: {id, category, overall_status, results}} 或 {success: false, error: 错误信息}",
        "parameters": {
            "error_message": "错误信息（必填）",
        },
    },
    "get_personalized_suggestion": {
        "description": "根据用户偏好对建议进行个性化调整。当AI需要根据用户偏好调整建议风格、强度、详细程度时使用此工具。返回JSON格式：{success: true, data: {id, original_text, personalized_text, suggestion_type, confidence, preference_factors}} 或 {success: false, error: 错误信息}",
        "parameters": {
            "suggestion_text": "原始建议文本（必填）",
            "suggestion_type": "建议类型（training_plan/recovery_advice/pace_guidance/weather_advice/nutrition_tip/injury_prevention/general，默认general）",
        },
    },
    "record_feedback": {
        "description": "记录用户对AI建议的反馈，用于偏好学习和个性化进化。当用户对建议表达满意、不满或修正意见时使用此工具。返回JSON格式：{success: true, data: {feedback_id, feedback_type, preference_updated, current_preferences}} 或 {success: false, error: 错误信息}",
        "parameters": {
            "feedback_type": "反馈类型（positive/negative/neutral/correction，必填）",
            "content": "反馈内容（必填）",
            "preference_category": "偏好类别（training_time/training_intensity/communication_style/suggestion_frequency/detail_preference/pace_preference/distance_preference/weather_sensitivity，默认communication_style）",
            "suggestion_id": "关联的建议ID（可选）",
        },
    },
    "get_user_preferences": {
        "description": "获取当前用户的偏好设置，包括训练时段、强度偏好、沟通风格等。当AI需要了解用户偏好以提供更个性化的建议时使用此工具。返回JSON格式：{success: true, data: {training_time, training_intensity, communication_style, suggestion_frequency, detail_preference, pace_preference, distance_preference, weather_sensitivity}} 或 {success: false, error: 错误信息}",
        "parameters": {},
    },
    "update_user_preferences": {
        "description": "直接更新用户偏好设置。当用户明确表达偏好变更时使用此工具，如'我喜欢简洁的回答'、'把训练强度调低'。返回JSON格式：{success: true, data: {updated_preferences}} 或 {success: false, error: 错误信息}",
        "parameters": {
            "updates": "偏好更新键值对，key为偏好字段名，value为新值（必填）",
        },
    },
    "explain_decision": {
        "description": "解释AI决策过程，展示思考过程和决策依据。当用户询问'为什么这么建议'、'你是怎么想的'、'解释一下你的建议'时使用此工具。返回JSON格式：{success: true, data: {decision_id, brief_reasons, confidence, data_sources, decision_path}} 或 {success: false, error: 错误信息}",
        "parameters": {
            "decision_id": "决策ID（可选，不提供则解释最近一次决策）",
            "detail_level": "详细程度（brief/detailed，默认brief）",
        },
    },
    "trace_data_sources": {
        "description": "追溯AI决策使用的数据来源，展示决策基于哪些数据做出。当用户询问'你的数据来源是什么'、'这个建议基于什么数据'、'你怎么知道这些'时使用此工具。返回JSON格式：{success: true, data: {decision_id, sources: [{name, type, description, quality_score}]}} 或 {success: false, error: 错误信息}",
        "parameters": {
            "decision_id": "决策ID（可选，不提供则追溯最近一次决策）",
        },
    },
    "get_transparency_insight": {
        "description": "获取AI透明化洞察信息，包括可观测性指标、决策统计、工具可靠性等。当用户询问'AI表现如何'、'你的决策质量怎么样'、'工具调用情况'时使用此工具。返回JSON格式：{success: true, data: {metrics: {total_traces, successful_traces, avg_duration_ms, error_rate, tool_success_rate}, recent_decisions, log_stats}} 或 {success: false, error: 错误信息}",
        "parameters": {
            "include_metrics": "是否包含可观测性指标（默认true）",
            "include_recent_decisions": "是否包含最近决策（默认true）",
            "recent_limit": "最近决策返回数量（默认5）",
        },
    },
    "get_hrv_analysis": {
        "description": "获取HRV（心率变异）分析结果，包括静息心率趋势和估算的HRV指标（RMSSD/SDNN）。当用户询问'HRV是多少'、'心率变异分析'时使用此工具。返回JSON格式：{success: true, data: {resting_hr_trend: [{date, resting_hr, deviation_pct}], data_quality, data_source, estimated_hrv_metrics: {estimated_rmssd, estimated_sdnn, data_source}}} 或 {success: false, error: 错误信息}",
        "parameters": {"days": "分析天数（默认30天）"},
    },
    "get_hr_recovery": {
        "description": "获取心率恢复分析结果，评估训练后心率下降速率和心脏恢复能力。当用户询问'心率恢复'、'恢复能力'时使用此工具。返回JSON格式：{success: true, data: {hr_end, hr_recovery_1min, data_quality}} 或 {success: false, error: 错误信息}",
        "parameters": {},
    },
    "get_fatigue_score": {
        "description": "获取疲劳度评估结果，综合训练负荷、心率偏差、连续训练天数等维度计算疲劳度分数。当用户询问'我累不累'、'疲劳度'时使用此工具。返回JSON格式：{success: true, data: {fatigue_score, recovery_status, consecutive_hard_days, breakdown: {atl_component, hr_deviation_component, consecutive_component, subjective_component}, recommendation, data_quality}} 或 {success: false, error: 错误信息}",
        "parameters": {"rpe": "主观疲劳度 (1-10，可选)"},
    },
    "get_recovery_status": {
        "description": "获取恢复状态评估，包括TSB变化、休息日效果和恢复趋势。当用户询问'恢复得怎么样'、'今天能训练吗'时使用此工具。返回JSON格式：{success: true, data: {recovery_status, rest_day_effect: {resting_hr_change_pct, tsb_change, effect_level, message}, recovery_trend: [{date, tsb, ctl}], data_quality}} 或 {success: false, error: 错误信息}",
        "parameters": {},
    },
    "get_body_signal_summary": {
        "description": "获取身体信号综合摘要，整合HRV、疲劳度和恢复状态三个维度生成每日或每周摘要。当用户询问'今天状态怎么样'、'身体信号'、'综合状态'时使用此工具。返回JSON格式：{success: true, data: {recovery_status, fatigue_score, data_quality, daily_summary, training_advice, alerts: [{alert_type, severity, message, details}]}} 或 {success: false, error: 错误信息}",
        "parameters": {"period": "周期类型（daily/weekly，默认daily）"},
    },
    "compare_training_periods": {
        "description": "对比两个训练周期的身体信号变化，分析恢复状态趋势。当用户询问'最近状态有没有变好'、'对比上周'、'训练趋势'时使用此工具。返回JSON格式：{success: true, data: {period1: {avg_tsb, data_points, hrv_data_quality}, period2: {avg_tsb, data_points, hrv_data_quality}, tsb_change, comparison_summary}} 或 {success: false, error: 错误信息}",
        "parameters": {
            "period1_days": "近期周期天数（默认7天）",
            "period2_days": "对比周期天数（默认7天）",
        },
    },
    "predict_vdot_trend": {
        "description": "预测VDOT（跑力值）趋势，基于训练数据预测未来VDOT变化。当用户询问'VDOT会怎么变'、'跑力趋势预测'、'未来VDOT'时使用此工具。返回JSON格式：{success: true, data: {current_vdot, predicted_vdot, prediction_days, confidence_interval, confidence, trend_slope, key_factors, data_quality, prediction_type}} 或 {success: false, error: 错误信息}",
        "parameters": {"days": "预测天数（默认30天）"},
    },
    "predict_race_result": {
        "description": "预测比赛完赛时间，基于个人化Riegel公式预测不同距离的比赛成绩。当用户询问'全马能跑多少'、'比赛预测'、'完赛时间预测'时使用此工具。返回JSON格式：{success: true, data: {distance_km, predicted_time, predicted_time_seconds, confidence, best_case, worst_case, predicted_vdot, prediction_type}} 或 {success: false, error: 错误信息}",
        "parameters": {
            "distance_km": "比赛距离（公里），如5/10/21.0975/42.195（必填）",
            "race_date": "比赛日期（YYYY-MM-DD，可选）",
        },
    },
    "predict_injury_risk": {
        "description": "预测伤病风险，综合急性/慢性负荷比、训练单调性、身体信号等评估受伤概率。当用户询问'会不会受伤'、'伤病风险'、'训练安全吗'时使用此工具。返回JSON格式：{success: true, data: {risk_score, risk_level, risk_timeline, top_risk_factors, recommendations, data_quality, prediction_type}} 或 {success: false, error: 错误信息}",
        "parameters": {"days": "预测天数（默认21天）"},
    },
    "predict_training_response": {
        "description": "预测单次训练的响应效果，包括VDOT影响、疲劳影响、恢复时间和伤病风险增量。当用户询问'这次训练效果如何'、'跑完会怎样'、'训练影响预测'时使用此工具。返回JSON格式：{success: true, data: {session_type, duration_min, intensity, predicted_vdot_impact, predicted_fatigue_impact, predicted_recovery_hours, predicted_injury_risk_delta, banister_fitness_delta, banister_fatigue_delta, prediction_type}} 或 {success: false, error: 错误信息}",
        "parameters": {
            "session_type": "训练类型（easy/threshold/interval/recovery，必填）",
            "duration_min": "训练时长（分钟，必填）",
            "intensity": "强度（low/moderate/high，必填）",
        },
    },
    "check_prediction_status": {
        "description": "检查预测功能的数据充足度，评估各预测类型是否具备足够数据支撑ML增强预测。当用户询问'预测准不准'、'数据够不够预测'时使用此工具。返回JSON格式：{success: true, data: {vdot_status, race_status, injury_status, overall_ready_count, advice}} 或 {success: false, error: 错误信息}",
        "parameters": {},
    },
    "report_injury": {
        "description": "提交伤病报告，记录伤病类型、严重程度和日期，用于ML模型训练标签。当用户报告受伤、疼痛、不适时使用此工具。返回JSON格式：{success: true, data: {injury_id, injury_type, severity, date, label_type, created_at}} 或 {success: false, error: 错误信息}",
        "parameters": {
            "injury_type": "伤病类型（overuse/acute/chronic/other，必填）",
            "severity": "严重程度（mild/moderate/severe，必填）",
            "date": "伤病日期（YYYY-MM-DD，必填）",
        },
    },
    "manage_prediction_model": {
        "description": "管理预测模型，支持训练(train)、查看状态(status)、回滚(rollback)操作。当用户需要重新训练模型、查看模型状态或回滚模型版本时使用此工具。返回JSON格式：{success: true, data: {action, model_type, success, message}} 或 {success: false, error: 错误信息}",
        "parameters": {
            "action": "操作类型（train/status/rollback，必填）",
            "model_type": "模型类型（vdot_predictor/injury_predictor，必填）",
        },
    },
    "get_twin_snapshot": {
        "description": "获取跑者数字孪生5维状态快照，包括体能(VDOT)、负荷(CTL/ATL/TSB)、身体信号(疲劳/恢复)、风险(伤病/过度训练)、训练模式(跑量/强度分布)。当用户询问'我的数字孪生'、'当前状态快照'、'5维状态'时使用此工具。返回JSON格式：{success: true, data: {fitness, load, body_signal, risk, training_pattern, snapshot_date, data_quality}} 或 {success: false, error: 错误信息}",
        "parameters": {},
    },
    "simulate_twin": {
        "description": "数字孪生What-If推演，基于当前状态模拟训练计划执行后的变化。当用户询问'如果我按这个计划训练会怎样'、'推演训练效果'、'What-If模拟'时使用此工具。返回JSON格式：{success: true, data: {plan_name, initial_state, final_state, snapshots, total_weeks, vdot_delta, peak_injury_risk, avg_tsb}} 或 {success: false, error: 错误信息}",
        "parameters": {
            "plan_name": "计划名称（必填）",
            "weeks": "周计划列表，每项包含weekly_volume_km/easy_ratio/tempo_ratio/interval_ratio/long_run_km/intensity_multiplier（必填）",
            "prediction_type": "预测模式（basic/parametric/ml_enhanced，默认parametric）",
        },
    },
    "compare_twin_plans": {
        "description": "数字孪生多计划对比，对多个训练计划执行推演并按综合评分排序推荐最优方案。当用户询问'哪个计划更好'、'对比训练方案'、'推荐计划'时使用此工具。返回JSON格式：{success: true, data: {plans, best_plan, comparison_dimensions, recommendation}} 或 {success: false, error: 错误信息}",
        "parameters": {
            "plans": "计划列表，每项包含name和weeks（必填）",
            "prediction_type": "预测模式（basic/parametric/ml_enhanced，默认parametric）",
        },
    },
    "record_decision_feedback": {
        "description": "记录用户对AI决策的反馈评分。当用户表达对训练建议的满意度或反馈时使用此工具。返回JSON格式：{success: true, data: {outcome_id, decision_id, user_feedback_score, user_feedback_text, ...}} 或 {success: false, error: 错误信息}",
        "parameters": {
            "decision_id": "决策唯一标识（必填）",
            "score": "用户反馈评分（1-5，必填）",
            "text": "用户反馈文本（可选）",
            "accepted": "推荐是否被采纳（可选）",
        },
    },
    "check_plan_execution": {
        "description": "检查训练计划的执行忠实度。当需要评估用户是否按计划执行训练时使用此工具。返回JSON格式：{success: true, data: {execution_fidelity, volume_deviation, time_deviation, ...}} 或 {success: false, error: 错误信息}",
        "parameters": {
            "decision_id": "决策唯一标识（必填）",
        },
    },
    "check_prediction_accuracy": {
        "description": "检查VDOT预测的准确度。当需要评估AI预测与实际表现的偏差时使用此工具。返回JSON格式：{success: true, data: {prediction_error, prediction_direction, mae, total_pairs, ...}} 或 {success: false, error: 错误信息}",
        "parameters": {
            "decision_id": "决策唯一标识（必填）",
            "actual_vdot": "实际VDOT值（可选，默认从最新session获取）",
        },
    },
    "get_decision_history": {
        "description": "查询AI决策历史记录。当用户询问过去的训练建议或决策记录时使用此工具。返回JSON格式：{success: true, data: [{decision_id, timestamp, decision_type, execution_status, ...}]} 或 {success: false, error: 错误信息}",
        "parameters": {
            "start_date": "起始日期（可选，格式：YYYY-MM-DD）",
            "end_date": "结束日期（可选，格式：YYYY-MM-DD）",
            "type": "决策类型过滤（可选）",
            "limit": "返回数量限制（默认50）",
        },
    },
    "analyze_training_response": {
        "description": "分析不同训练类型对跑者VDOT变化的响应效果，识别最佳/最差训练类型。当用户询问'哪种训练最有效'、'训练效果分析'、'个性化训练建议'时使用此工具。返回JSON格式：{success: true, data: {training_responses, best_type, worst_type, ...}} 或 {success: false, error: 错误信息}",
        "parameters": {
            "months": "分析月数（默认6）",
        },
    },
    "run_calibration": {
        "description": "执行预测校准，检测模型偏差方向和幅度，通过EMA更新scale因子。当需要校准VDOT/伤病/训练响应预测模型时使用此工具。返回JSON格式：{success: true, data: {direction, scale_before, scale_after, mae_before, mae_after, ...}} 或 {success: false, error: 错误信息}",
        "parameters": {
            "model_type": "模型类型（vdot/injury/training_response，默认vdot）",
        },
    },
    "get_calibration_status": {
        "description": "查询预测校准的当前状态，包括scale因子、样本数、MAE等。当用户询问'校准状态'、'模型修正情况'时使用此工具。返回JSON格式：{success: true, data: {...}} 或 {success: false, error: 错误信息}",
        "parameters": {
            "model_type": "模型类型（可选，空则返回所有模型状态）",
        },
    },
}

__all__ = [
    # 基类
    "BaseTool",
    # 业务逻辑层
    "RunnerTools",
    # 工厂函数
    "create_tools",
    # 工具描述
    "TOOL_DESCRIPTIONS",
    # 统计/分析工具
    "GetRunningStatsTool",
    "GetRecentRunsTool",
    "CalculateVdotForRunTool",
    "GetVdotTrendTool",
    "GetHrDriftAnalysisTool",
    "GetTrainingLoadTool",
    "QueryByDateRangeTool",
    "QueryByDistanceTool",
    # 训练计划工具
    "GenerateTrainingPlanTool",
    "RecordPlanExecutionTool",
    "GetPlanExecutionStatsTool",
    "AnalyzeTrainingResponseTool",
    "AdjustPlanTool",
    "GetPlanAdjustmentSuggestionsTool",
    "EvaluateGoalAchievementTool",
    "CreateLongTermPlanTool",
    "GetSmartTrainingAdviceTool",
    "GetWeatherTrainingAdviceTool",
    # 身体信号/健康工具
    "AskUserConfirmTool",
    "ParseUserConfirmTool",
    "GetHrvAnalysisTool",
    "GetHrRecoveryTool",
    "GetFatigueScoreTool",
    "GetRecoveryStatusTool",
    "GetBodySignalSummaryTool",
    "CompareTrainingPeriodsTool",
    # 数字孪生/预测工具
    "PredictVdotTrendTool",
    "PredictRaceResultTool",
    "PredictInjuryRiskTool",
    "PredictTrainingResponseTool",
    "CheckPredictionStatusTool",
    "ReportInjuryTool",
    "ManagePredictionModelTool",
    "GetTwinSnapshotTool",
    "SimulateTwinTool",
    "CompareTwinPlansTool",
    "SpawnSubagentTool",
    # 决策追踪工具
    "RecordDecisionFeedbackTool",
    "CheckPlanExecutionTool",
    "CheckPredictionAccuracyTool",
    "GetDecisionHistoryTool",
    "AnalyzeTrainingResponseV2Tool",
    "GetCalibrationStatusTool",
    "RunCalibrationTool",
    # 数据管理/系统工具
    "UpdateMemoryTool",
    "DiagnoseSuggestionTool",
    "DiagnoseErrorTool",
    "GetPersonalizedSuggestionTool",
    "RecordFeedbackTool",
    "GetUserPreferencesTool",
    "UpdateUserPreferencesTool",
    "ExplainDecisionTool",
    "TraceDataSourcesTool",
    "GetTransparencyInsightTool",
]
